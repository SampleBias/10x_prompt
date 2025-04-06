from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
from urllib.parse import urlencode
import os
import requests
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI
from authlib.integrations.flask_client import OAuth
from functools import wraps
import time
from requests.exceptions import RequestException, Timeout, ConnectionError
import sys

# Configure logging for Heroku
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs go to stdout for Heroku
    ]
)
logger = logging.getLogger(__name__)

# Force all loggers to use this configuration
for log_name, log_obj in logging.Logger.manager.loggerDict.items():
    if isinstance(log_obj, logging.Logger):
        log_obj.handlers = []
        log_obj.addHandler(logging.StreamHandler(sys.stdout))
        log_obj.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.config['SESSION_COOKIE_NAME'] = '10x_prompt_session'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Let Flask set this automatically
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Auth0 configuration
app.config['AUTH0_CLIENT_ID'] = os.getenv('AUTH0_CLIENT_ID')
app.config['AUTH0_CLIENT_SECRET'] = os.getenv('AUTH0_CLIENT_SECRET')
app.config['AUTH0_DOMAIN'] = os.getenv('AUTH0_DOMAIN')

# Determine the environment and set the appropriate callback URL
if os.getenv('HEROKU_APP_NAME'):
    # We're on Heroku
    app.config['AUTH0_CALLBACK_URL'] = f"https://{os.getenv('HEROKU_APP_NAME')}.herokuapp.com/callback"
else:
    # We're in development
    app.config['AUTH0_CALLBACK_URL'] = os.getenv('AUTH0_CALLBACK_URL', 'http://localhost:5000/callback')

logger.info(f"Using Auth0 callback URL: {app.config['AUTH0_CALLBACK_URL']}")

oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=app.config['AUTH0_CLIENT_ID'],
    client_secret=app.config['AUTH0_CLIENT_SECRET'],
    api_base_url=f'https://{app.config["AUTH0_DOMAIN"]}',
    access_token_url=f'https://{app.config["AUTH0_DOMAIN"]}/oauth/token',
    authorize_url=f'https://{app.config["AUTH0_DOMAIN"]}/authorize',
    client_kwargs={
        'scope': 'openid profile email',
        'response_type': 'code'
    },
    server_metadata_url=f'https://{app.config["AUTH0_DOMAIN"]}/.well-known/openid-configuration'
)

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("API_URL", "https://api.deepseek.com/v1")

class APIError(Exception):
    """Custom exception for API-related errors"""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class APIStatus:
    """Track API status and last check time"""
    def __init__(self, name):
        self.name = name
        self.is_healthy = False
        self.last_check_time = None
        self.last_error = None
        self.consecutive_failures = 0

# Global API status trackers
groq_status = APIStatus("Groq")
deepseek_status = APIStatus("DeepSeek")

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """Retry a function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                raise  # Re-raise the last exception
            delay = initial_delay * (2 ** attempt)  # Exponential backoff
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay} seconds: {str(e)}")
            time.sleep(delay)

def log_api_details():
    """Log API configuration details"""
    logger.info("=== API Configuration ===")
    # Groq Configuration
    if GROQ_API_KEY:
        logger.info("Groq API Key: Configured")
        logger.info(f"Groq API URL: {GROQ_API_URL}")
        # Log first few characters of API key for verification (safely)
        logger.info(f"Groq API Key Preview: {GROQ_API_KEY[:4]}...")
    else:
        logger.error("Groq API Key: Not configured")
    
    # DeepSeek Configuration
    if DEEPSEEK_API_KEY:
        logger.info("DeepSeek API Key: Configured")
        logger.info(f"DeepSeek API URL: {DEEPSEEK_API_URL}")
        logger.info(f"DeepSeek API Key Preview: {DEEPSEEK_API_KEY[:4]}...")
    else:
        logger.error("DeepSeek API Key: Not configured")

# Call this right after loading environment variables
load_dotenv()
log_api_details()

def check_api_health(client, is_groq=True):
    """Check if the API is responsive and working"""
    status = groq_status if is_groq else deepseek_status
    api_name = "Groq" if is_groq else "DeepSeek"
    
    def health_check():
        try:
            logger.info(f"\n=== Starting {api_name} Health Check ===")
            # Use different models and prompts for each API
            if is_groq:
                model = "distil-whisper-large-v3-en"
                logger.info(f"Using model: {model}")
            else:
                model = "deepseek-chat"
                logger.info(f"Using model: {model}")
                logger.info(f"API URL: {DEEPSEEK_API_URL}")
            
            logger.info(f"Sending test request to {api_name} API...")
            
            # Then try the chat completion
            if is_groq:
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hi"}
                    ],
                    model=model,
                    max_tokens=10,
                    temperature=1.0,  # Ensuring temperature > 0
                    n=1  # Must be 1 for Groq
                )
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hi"}
                    ],
                    max_tokens=10,
                    stream=False
                )
            
            logger.info(f"{api_name} API Response: {response}")
            
            if not hasattr(response, 'choices') or not response.choices:
                error_msg = "API response missing choices"
                logger.error(f"{api_name} API health check failed: {error_msg}")
                logger.error(f"Raw response: {response}")
                raise APIError(error_msg)
            
            # Update status on success
            status.is_healthy = True
            status.last_check_time = time.time()
            status.last_error = None
            status.consecutive_failures = 0
            
            logger.info(f"{api_name} API health check: SUCCESS")
            logger.info(f"=== {api_name} Health Check Complete ===\n")
            return True, None
        except Exception as e:
            error_msg = f"{api_name} API health check failed: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Full error details: {e.__class__.__name__}: {str(e)}")
            
            # Log detailed error information
            if hasattr(e, 'response'):
                logger.error(f"Response Status: {getattr(e.response, 'status_code', 'N/A')}")
                logger.error(f"Response Body: {getattr(e.response, 'text', 'N/A')}")
            
            # Update status on failure
            status.is_healthy = False
            status.last_check_time = time.time()
            status.last_error = str(e)
            status.consecutive_failures += 1
            
            logger.error(f"=== {api_name} Health Check Failed ===\n")
            return False, error_msg
    return health_check()

def perform_health_checks():
    """Perform health checks on both APIs"""
    results = {
        "groq": {"healthy": False, "error": None},
        "deepseek": {"healthy": False, "error": None}
    }
    
    # Check Groq
    if groq_client is not None:
        is_healthy, error = check_api_health(groq_client, True)
        results["groq"]["healthy"] = is_healthy
        results["groq"]["error"] = error
    else:
        results["groq"]["error"] = "Groq client not initialized"
    
    # Check DeepSeek
    if deepseek_client is not None:
        is_healthy, error = check_api_health(deepseek_client, False)
        results["deepseek"]["healthy"] = is_healthy
        results["deepseek"]["error"] = error
    else:
        results["deepseek"]["error"] = "DeepSeek client not initialized"
    
    return results

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring API status"""
    results = perform_health_checks()
    
    # Determine overall status
    all_healthy = all(api["healthy"] for api in results.values() if api["error"] != "Client not initialized")
    status_code = 200 if all_healthy else 503
    
    response = {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "apis": {
            "groq": {
                "status": "healthy" if results["groq"]["healthy"] else "unhealthy",
                "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(groq_status.last_check_time)) if groq_status.last_check_time else None,
                "consecutive_failures": groq_status.consecutive_failures,
                "error": results["groq"]["error"]
            },
            "deepseek": {
                "status": "healthy" if results["deepseek"]["healthy"] else "unhealthy",
                "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(deepseek_status.last_check_time)) if deepseek_status.last_check_time else None,
                "consecutive_failures": deepseek_status.consecutive_failures,
                "error": results["deepseek"]["error"]
            }
        }
    }
    
    return jsonify(response), status_code

def initialize_groq_client():
    """Initialize the Groq client with proper error handling using OpenAI client"""
    logger.info("Initializing Groq client...")
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not found in environment variables")
        return None, "Groq API key not configured. Please check your environment variables."
    
    try:
        # Create client with Groq configuration using OpenAI client
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY,
            # Add reasonable timeout and max retries
            timeout=60.0,
            max_retries=2
        )
        
        # Test the client with a simple request
        logger.info("Testing Groq client connection...")
        try:
            # Test chat completion with supported parameters only
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                model="distil-whisper-large-v3-en",
                max_tokens=10,
                temperature=1.0,  # Ensuring temperature > 0
                n=1  # Must be 1 for Groq
            )
            logger.info("Successfully tested Groq connection")
        except Exception as e:
            logger.error(f"Failed to test Groq connection: {str(e)}")
        
        return client, None
    except Exception as e:
        error_msg = f"Failed to initialize Groq client: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

def initialize_deepseek_client():
    """Initialize the DeepSeek client as fallback"""
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY not found in environment variables")
        return None, "DeepSeek API key not configured. Please check your environment variables."
    
    try:
        # Create client with DeepSeek configuration
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_API_URL,
            timeout=60.0,
            max_retries=2
        )
        return client, None
    except Exception as e:
        error_msg = f"Failed to initialize DeepSeek client: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

# Initialize both clients
groq_client, groq_error = initialize_groq_client()
deepseek_client, deepseek_error = initialize_deepseek_client()

# Startup Health Check and Logging
logger.info("=== Starting Application Health Check ===")
logger.info("Checking API clients initialization status:")

if groq_client is None:
    logger.error(f"❌ Groq client initialization failed: {groq_error}")
    if deepseek_client is None:
        logger.error("❌ DeepSeek client initialization failed: {deepseek_error}")
        logger.error("⚠️ WARNING: Both API clients failed to initialize")
    else:
        logger.info("✓ DeepSeek client initialized successfully")
        logger.info("ℹ️ Using DeepSeek as primary due to Groq initialization failure")
else:
    logger.info("✓ Groq client initialized successfully")
    if deepseek_client is not None:
        logger.info("✓ DeepSeek client initialized successfully (fallback ready)")
    else:
        logger.warning("⚠️ DeepSeek client failed to initialize, no fallback available")

# Perform initial health checks
startup_health = perform_health_checks()
logger.info("\n=== Initial API Health Check Results ===")

# Log Groq health status
if "groq" in startup_health:
    if startup_health["groq"]["healthy"]:
        logger.info("✓ Groq API Health Check: PASSED")
    else:
        logger.error(f"❌ Groq API Health Check: FAILED - {startup_health['groq']['error']}")

# Log DeepSeek health status
if "deepseek" in startup_health:
    if startup_health["deepseek"]["healthy"]:
        logger.info("✓ DeepSeek API Health Check: PASSED")
    else:
        logger.error(f"❌ DeepSeek API Health Check: FAILED - {startup_health['deepseek']['error']}")

# Log overall system status
healthy_apis = [api for api, status in startup_health.items() if status["healthy"]]
logger.info("\n=== System Status Summary ===")
logger.info(f"Total APIs available: {len(startup_health)}")
logger.info(f"Healthy APIs: {len(healthy_apis)}")
if len(healthy_apis) == 0:
    logger.critical("⚠️ CRITICAL: No healthy APIs available!")
elif len(healthy_apis) < len(startup_health):
    logger.warning("⚠️ WARNING: Some APIs are unhealthy")
else:
    logger.info("✓ All APIs are healthy")

logger.info("=== Health Check Complete ===\n")

# System prompts for different prompt types
USER_PROMPT_OPTIMIZER = (
    'As an expert AI prompt engineer who knows how to interpret an average humans prompt and rewrite it in a '
    'way that increases the probability of the model generating the most useful possible response to any specific '
    'human prompt. In response to the user prompts, you do not respond as an AI assistant. You only respond with an '
    'improved variation of the users prompt, with no explanations before or after the prompt of why it is better. Do '
    'not generate anything but the expert prompt engineers modified version of the users prompt. If the prompt is in a '
    'conversation with more than one human prompt, the whole conversation will be given as context for you to evaluate '
    'how to construct the best possible response in that part of the conversation. Do not generate anything besides '
    'the optimized prompt with no headers or explanations of the optimized prompt.'
)

SYSTEM_PROMPT_OPTIMIZER = (
    'As an expert AI prompt engineer specialized in system prompt design, your task is to improve system prompts that '
    'control AI behavior. System prompts are instructions that define how an AI assistant behaves, responds, and '
    'processes information.\n\n'
    'When given a basic system prompt, enhance it to be more effective by:\n'
    '1. Making it more precise and specific\n'
    '2. Ensuring consistency in tone and behavior\n'
    '3. Adding necessary constraints or freedoms\n'
    '4. Improving clarity and reducing ambiguity\n'
    '5. Ensuring the instructions are comprehensive\n\n'
    'Only respond with the enhanced system prompt. Do not include explanations, headers, or any other text. '
    'Your response should be ready to copy and paste as a system prompt.'
)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        logger.info(f"Checking auth for path: {request.path}")
        logger.info(f"Current session data: {dict(session)}")
        
        if 'profile' not in session:
            logger.warning("No profile in session, redirecting to login")
            return redirect(url_for('login'))
            
        # Verify session data is valid
        profile = session.get('profile', {})
        if not profile.get('user_id'):
            logger.warning("Invalid profile data in session, redirecting to login")
            session.clear()
            return redirect(url_for('login'))
            
        logger.info(f"Auth successful for user: {profile.get('name', 'Unknown')}")
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    response = make_response(render_template('index.html'))
    # Ensure proper cache headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=app.config['AUTH0_CALLBACK_URL'])

@app.route('/callback')
def callback_handling():
    try:
        # Get the authorization code
        token = auth0.authorize_access_token()
        logger.info("Received access token from Auth0")
        
        # Get the user info
        resp = auth0.get('userinfo')
        userinfo = resp.json()
        logger.info(f"Received user info from Auth0: {userinfo.get('name', 'Unknown')}")
        
        # Clear any existing session
        session.clear()
        
        # Make session permanent and set cookie options
        session.permanent = True
        
        # Store user info in session
        session['jwt_payload'] = userinfo
        session['profile'] = {
            'user_id': userinfo['sub'],
            'name': userinfo.get('name', ''),
            'picture': userinfo.get('picture', '')
        }
        
        # Add a session test value
        session['test'] = 'test_value'
        
        logger.info("Session data set successfully")
        logger.info(f"Current session: {dict(session)}")
        
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        logger.error(f"Full error details: {e.__class__.__name__}: {str(e)}")
        return redirect(url_for('login'))

@app.before_request
def before_request():
    logger.info(f"Request path: {request.path}")
    logger.info(f"Session contents: {session}")
    if 'profile' in session:
        logger.info(f"User authenticated: {session['profile'].get('name', 'Unknown')}")
    else:
        logger.info("No user profile in session")

@app.after_request
def after_request(response):
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response headers: {response.headers}")
    return response

@app.route('/logout')
def logout():
    session.clear()
    params = {
        'returnTo': url_for('login', _external=True),
        'client_id': app.config['AUTH0_CLIENT_ID']
    }
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@app.route('/enhance', methods=['POST'])
@requires_auth
def enhance_prompt():
    try:
        # Check API health before processing
        api_health = perform_health_checks()
        
        # Log API health status
        logger.info("API Health Status:")
        logger.info(f"Groq: {'healthy' if api_health['groq']['healthy'] else 'unhealthy'}")
        logger.info(f"DeepSeek: {'healthy' if api_health['deepseek']['healthy'] else 'unhealthy'}")
        
        if not api_health["groq"]["healthy"] and not api_health["deepseek"]["healthy"]:
            logger.error("Both APIs are unhealthy")
            return jsonify({"error": "All APIs are currently unavailable"}), 503
        
        data = request.json
        if not data:
            logger.warning("No JSON data received")
            return jsonify({"error": "No data provided"}), 400

        prompt_text = data.get('prompt', '')
        prompt_type = data.get('type', 'user')
        
        if not prompt_text:
            logger.warning("Empty prompt received")
            return jsonify({"error": "No prompt provided"}), 400
        
        # Select the appropriate system message based on prompt type
        system_message = SYSTEM_PROMPT_OPTIMIZER if prompt_type == 'system' else USER_PROMPT_OPTIMIZER
        
        # Prepare the messages for the API
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt_text}
        ]
        
        def try_api_call(client, is_groq=True):
            try:
                model = "distil-whisper-large-v3-en" if is_groq else "deepseek-chat"
                logger.info(f"Attempting request with {'Groq' if is_groq else 'DeepSeek'} API using model: {model}")
                
                if is_groq:
                    response = client.chat.completions.create(
                        messages=messages,
                        model=model,
                        temperature=1.0,  # Ensuring temperature > 0
                        n=1  # Must be 1 for Groq
                    )
                else:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        stream=False
                    )
                
                # Log the raw response for debugging
                logger.info(f"API Response from {model}: {response}")
                
                if not hasattr(response, 'choices') or not response.choices:
                    raise APIError("Invalid API response format")
                
                # Update health status on successful call
                status = groq_status if is_groq else deepseek_status
                status.is_healthy = True
                status.last_check_time = time.time()
                status.consecutive_failures = 0
                
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"{'Groq' if is_groq else 'DeepSeek'} API call failed: {str(e)}")
                # Log detailed error information
                if hasattr(e, 'response'):
                    logger.error(f"Response Status: {getattr(e.response, 'status_code', 'N/A')}")
                    logger.error(f"Response Body: {getattr(e.response, 'text', 'N/A')}")
                
                # Update health status on failed call
                status = groq_status if is_groq else deepseek_status
                status.is_healthy = False
                status.last_check_time = time.time()
                status.last_error = str(e)
                status.consecutive_failures += 1
                raise

        # Try Groq first if it's healthy, otherwise try DeepSeek
        try:
            if groq_client is not None and api_health["groq"]["healthy"]:
                enhanced_prompt = try_api_call(groq_client, True)
                logger.info("Successfully enhanced prompt using Groq API")
            elif deepseek_client is not None and api_health["deepseek"]["healthy"]:
                enhanced_prompt = try_api_call(deepseek_client, False)
                logger.info("Successfully enhanced prompt using DeepSeek API (fallback)")
            else:
                return jsonify({"error": "No healthy API clients available"}), 503
            
            return jsonify({"enhanced_prompt": enhanced_prompt})
            
        except Exception as e:
            # If primary API fails, try the other one if it's healthy
            if (groq_client is not None and deepseek_client is not None and 
                ((api_health["groq"]["healthy"] and not api_health["deepseek"]["healthy"]) or 
                 (not api_health["groq"]["healthy"] and api_health["deepseek"]["healthy"]))):
                try:
                    # Try the other API
                    if api_health["deepseek"]["healthy"]:
                        enhanced_prompt = try_api_call(deepseek_client, False)
                        logger.info("Successfully enhanced prompt using DeepSeek API (fallback)")
                    else:
                        enhanced_prompt = try_api_call(groq_client, True)
                        logger.info("Successfully enhanced prompt using Groq API (fallback)")
                    return jsonify({"enhanced_prompt": enhanced_prompt})
                except Exception as fallback_e:
                    logger.error(f"Both APIs failed. Primary error: {str(e)}, Fallback error: {str(fallback_e)}")
                    return jsonify({"error": "All API attempts failed"}), 503
            else:
                logger.error(f"API call failed and no healthy fallback available: {str(e)}")
                return jsonify({"error": "API request failed"}), 503
                
    except Exception as e:
        logger.exception("Unexpected error in enhance_prompt")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 