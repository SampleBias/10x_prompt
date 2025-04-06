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
from flask_session import Session  # Add Flask-Session import

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
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem session storage for better persistence
app.config['SESSION_FILE_DIR'] = os.getenv('SESSION_FILE_DIR', '/tmp/flask_session')
app.config['SESSION_USE_SIGNER'] = True

# Initialize Flask-Session
Session(app)

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

# API Configuration (with validation)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY environment variable is not set!")

GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1")
logger.info(f"Using Groq API URL: {GROQ_API_URL}")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    logger.error("DEEPSEEK_API_KEY environment variable is not set!")

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")
logger.info(f"Using DeepSeek API URL: {DEEPSEEK_API_URL}")

# Check for OpenAI version compatibility
import openai
openai_version = openai.__version__
logger.info(f"Detected OpenAI version: {openai_version}")

if openai_version.startswith("1."):
    logger.warning("""
    ⚠️ WARNING: You are using OpenAI SDK v1.x, which may have compatibility issues with DeepSeek API.
    If you encounter 'proxies' parameter errors or other initialization issues with DeepSeek, consider:
    
    1. Downgrading to OpenAI SDK v0.28.0: pip install openai==0.28.0
    2. Or request an updated integration example from DeepSeek support
    """)

# Check for Heroku environment
if os.getenv('HEROKU_APP_NAME'):
    logger.info(f"Running on Heroku with app name: {os.getenv('HEROKU_APP_NAME')}")
else:
    logger.info("Running in development environment")

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
    logger.info("\n=== API Configuration ===")
    # Groq Configuration
    if GROQ_API_KEY:
        logger.info("Groq API Key: Configured")
        logger.info(f"Groq API URL: {GROQ_API_URL}")
        # Log first few characters of API key for verification (safely)
        try:
            logger.info(f"Groq API Key Preview: {GROQ_API_KEY[:4]}...")
        except:
            logger.error("Could not log Groq API key preview - key may be invalid")
    else:
        logger.error("Groq API Key: Not configured")
    
    # DeepSeek Configuration
    if DEEPSEEK_API_KEY:
        logger.info("DeepSeek API Key: Configured")
        logger.info(f"DeepSeek API URL: {DEEPSEEK_API_URL}")
        try:
            logger.info(f"DeepSeek API Key Preview: {DEEPSEEK_API_KEY[:4]}...")
        except:
            logger.error("Could not log DeepSeek API key preview - key may be invalid")
    else:
        logger.error("DeepSeek API Key: Not configured")
    logger.info("=== End API Configuration ===\n")

# Call this right after loading environment variables
log_api_details()

def check_api_health(client, is_groq=True):
    """Check if the API is responsive and working"""
    status = groq_status if is_groq else deepseek_status
    api_name = "Groq" if is_groq else "DeepSeek"
    
    def health_check():
        try:
            logger.info(f"\n=== Starting {api_name} Health Check ===")
            
            # Use different models for each API
            if is_groq:
                # Use Groq's most reliable model
                model = "llama-3.1-8b-instant"
                logger.info(f"Using model: {model}")
                logger.info(f"API URL: {GROQ_API_URL}")
                logger.info(f"API Key configured: {'Yes' if GROQ_API_KEY else 'No'}")
                logger.info(f"Client initialized: {'Yes' if client else 'No'}")
            else:
                model = "deepseek-chat"
                logger.info(f"Using model: {model}")
                logger.info(f"API URL: {DEEPSEEK_API_URL}")
                logger.info(f"API Key configured: {'Yes' if DEEPSEEK_API_KEY else 'No'}")
                logger.info(f"Client initialized: {'Yes' if client else 'No'}")
            
            if not client:
                raise APIError("API client not initialized")
            
            logger.info(f"Sending test request to {api_name} API...")
            start_time = time.time()
            
            # Create a simple test message
            messages = [{"role": "user", "content": "Hello"}]
            
            try:
                if is_groq:
                    # Groq client is consistent
                    response = client.chat.completions.create(
                        messages=messages,
                        model=model,
                        max_tokens=5  # Minimize token usage for health check
                    )
                else:
                    # DeepSeek client might be using different OpenAI versions
                    # Determine client type and call appropriately
                    if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):
                        # Modern OpenAI client (v1.x)
                        logger.info("Using OpenAI 1.x client for health check")
                        response = client.chat.completions.create(
                            model=model,
                            messages=messages,
                            max_tokens=5
                        )
                    elif hasattr(client, 'ChatCompletion'):
                        # Legacy OpenAI client with object (v0.x)
                        logger.info("Using OpenAI 0.x ChatCompletion object for health check")
                        response = client.ChatCompletion.create(
                            model=model,
                            messages=messages,
                            max_tokens=5
                        )
                    else:
                        # Direct module call for older versions
                        logger.info("Using direct module call for health check")
                        import openai
                        response = openai.ChatCompletion.create(
                            model=model,
                            messages=messages,
                            max_tokens=5
                        )
                
                # Log detailed response information
                logger.info(f"Response type: {type(response)}")
                
                # Extract content based on response type
                if hasattr(response, 'choices') and hasattr(response.choices[0], 'message'):
                    # Modern OpenAI response object
                    content = response.choices[0].message.content
                    logger.info(f"Content: {content}")
                elif isinstance(response, dict) and 'choices' in response:
                    # Dictionary response from older OpenAI versions
                    content = response['choices'][0]['message']['content']
                    logger.info(f"Content: {content}")
                else:
                    # Log full response for unexpected formats
                    logger.info(f"Full response: {response}")
                
                duration = time.time() - start_time
                logger.info(f"{api_name} API is healthy (response time: {duration:.2f}s)")
                
                # Update status
                status.is_healthy = True
                status.last_check_time = time.time()
                status.consecutive_failures = 0
                
                return True, None
            
            except Exception as e:
                # Log the exception details
                logger.error(f"{api_name} API health check failed: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                
                # Log detailed error information if available
                if hasattr(e, 'response'):
                    logger.error(f"Response Status: {getattr(e.response, 'status_code', 'N/A')}")
                    logger.error(f"Response Body: {getattr(e.response, 'text', 'N/A')}")
                
                status.is_healthy = False
                status.last_check_time = time.time()
                status.last_error = str(e)
                status.consecutive_failures += 1
                
                return False, str(e)
        
        except Exception as e:
            logger.error(f"Error during {api_name} health check: {str(e)}")
            status.is_healthy = False
            status.last_check_time = time.time()
            status.last_error = str(e)
            status.consecutive_failures += 1
            return False, str(e)
    
    # Run the health check with retries
    return retry_with_backoff(health_check)

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
    logger.info("\n=== Initializing Groq Client ===")
    logger.info(f"GROQ_API_URL: {GROQ_API_URL}")
    logger.info(f"API Key Present: {'Yes' if GROQ_API_KEY else 'No'}")
    
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not found in environment variables")
        return None, "Groq API key not configured. Please check your environment variables."
    
    try:
        # Define a clean client class that only accepts specific parameters
        class CleanOpenAI(OpenAI):
            def __init__(self, api_key, base_url):
                super().__init__(api_key=api_key, base_url=base_url)
        
        # Create client with Groq configuration
        logger.info("Creating Groq client with clean parameters...")
        client = CleanOpenAI(
            api_key=GROQ_API_KEY,
            base_url=GROQ_API_URL
        )
        
        # Test the client with a simple request
        logger.info("Testing Groq client connection...")
        try:
            # Test chat completion with minimal parameters
            logger.info("Sending test request to Groq API...")
            logger.info("Request parameters:")
            logger.info({
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            })
            
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                model="llama-3.1-8b-instant",
                max_tokens=5
            )
            logger.info("Successfully tested Groq connection")
            logger.info(f"Response: {response}")
        except Exception as e:
            logger.error("Failed to test Groq connection")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response Status: {getattr(e.response, 'status_code', 'N/A')}")
                logger.error(f"Response Headers: {getattr(e.response, 'headers', {})}")
                logger.error(f"Response Body: {getattr(e.response, 'text', 'N/A')}")
            # Don't raise the exception, return with error message
            return None, f"Groq connection test failed: {str(e)}"
        
        logger.info("=== Groq Client Initialization Complete ===\n")
        return client, None
    except Exception as e:
        error_msg = f"Failed to initialize Groq client: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Error type: {type(e).__name__}")
        if hasattr(e, 'response'):
            logger.error(f"Response Status: {getattr(e.response, 'status_code', 'N/A')}")
            logger.error(f"Response Headers: {getattr(e.response, 'headers', {})}")
            logger.error(f"Response Body: {getattr(e.response, 'text', 'N/A')}")
        logger.error("=== Groq Client Initialization Failed ===\n")
        return None, error_msg

def initialize_deepseek_client():
    """Initialize the DeepSeek client as fallback"""
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY not found in environment variables")
        return None, "DeepSeek API key not configured. Please check your environment variables."
    
    try:
        # Log OpenAI version for debugging
        import openai
        logger.info(f"OpenAI version: {openai.__version__}")
        is_openai_v1 = openai.__version__.startswith('1.')
        logger.info(f"Using OpenAI {'1.x' if is_openai_v1 else '0.x'} API")
        
        try:
            # Try modern OpenAI client method (1.x) with DeepSeek's documented URL format
            logger.info("Attempting to initialize DeepSeek client with OpenAI 1.x API...")
            # Use only required parameters to avoid compatibility issues
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_URL  # No /v1 suffix as per DeepSeek docs
            )
            logger.info("DeepSeek client initialized successfully with OpenAI 1.x API")
            return client, None
        except TypeError as e:
            # Handle proxies argument error common in some environments
            logger.warning(f"Modern client initialization failed: {str(e)}")
            if "unexpected keyword argument 'proxies'" in str(e):
                logger.warning("Detected 'proxies' keyword argument error, this is a known issue")
                logger.warning("Consider downgrading OpenAI library to 0.28.0 for better compatibility")
                return None, f"DeepSeek client initialization failed: {str(e)}"
            
            # Try direct configuration for pre-1.0 OpenAI
            if not is_openai_v1:
                logger.info("Attempting direct configuration for OpenAI 0.x...")
                openai.api_key = DEEPSEEK_API_KEY
                openai.api_base = DEEPSEEK_API_URL
                logger.info("Using direct configuration method for DeepSeek")
                return openai, None
            else:
                return None, f"Failed to initialize DeepSeek client: {str(e)}"
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
    # Clear any existing session to prevent state mismatches
    session.clear()
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
        logger.info(f"Session ID: {request.cookies.get(app.config['SESSION_COOKIE_NAME'], 'None')}")
        
        # Force session save
        session.modified = True
        
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        logger.error(f"Full error details: {e.__class__.__name__}: {str(e)}")
        logger.error(f"Request: {request.url}")
        logger.error(f"Request cookies: {request.cookies}")
        return redirect(url_for('login'))

@app.before_request
def before_request():
    logger.info(f"Request path: {request.path}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Session contents: {session}")
    logger.info(f"Session ID: {request.cookies.get(app.config['SESSION_COOKIE_NAME'], 'None')}")
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
        data = request.json
        if not data:
            logger.warning("No JSON data received")
            return jsonify({"error": "No data provided"}), 400

        prompt_text = data.get('prompt', '')
        prompt_type = data.get('type', 'user')
        
        if not prompt_text:
            logger.warning("Empty prompt received")
            return jsonify({"error": "No prompt provided"}), 400
        
        logger.info(f"Received enhance request - prompt length: {len(prompt_text)}, type: {prompt_type}")
        
        # Check API health before processing
        api_health = perform_health_checks()
        
        # Log API health status
        logger.info("\n=== API Health Status for Enhance Request ===")
        logger.info(f"Groq: {'healthy' if api_health['groq']['healthy'] else 'unhealthy'}")
        logger.info(f"DeepSeek: {'healthy' if api_health['deepseek']['healthy'] else 'unhealthy'}")
        
        if not api_health["groq"]["healthy"] and not api_health["deepseek"]["healthy"]:
            logger.error("Both APIs are unhealthy")
            # Try one more health check with fresh clients
            logger.info("Attempting to reinitialize API clients for one more attempt")
            
            try:
                # Reinitialize Groq client
                new_groq_client, _ = initialize_groq_client()
                if new_groq_client:
                    logger.info("Successfully reinitialized Groq client, attempting health check")
                    groq_health, _ = check_api_health(new_groq_client, True)
                    if groq_health:
                        logger.info("Groq API is now healthy after reinitialization")
                        global groq_client
                        groq_client = new_groq_client
                        api_health["groq"]["healthy"] = True
            except Exception as e:
                logger.error(f"Error reinitializing Groq client: {str(e)}")
            
            # If still no healthy APIs, return error
            if not api_health["groq"]["healthy"] and not api_health["deepseek"]["healthy"]:
                return jsonify({"error": "All APIs are currently unavailable. Please try again later."}), 503
        
        # Select the appropriate system message based on prompt type
        if prompt_type == 'system':
            system_message = "You are an expert at improving system prompts for AI models. Rewrite the provided system prompt to be more precise, effective, and clear."
        else:
            system_message = "You are an expert at improving user prompts for AI models. Rewrite the provided prompt to be clearer and more effective at getting the desired response."
        
        # Prepare the messages for the API
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt_text}
        ]
        
        def try_api_call(client, is_groq=True):
            try:
                model = "llama-3.1-8b-instant" if is_groq else "deepseek-chat"
                logger.info(f"Attempting enhance request with {'Groq' if is_groq else 'DeepSeek'} API")
                logger.info(f"Using model: {model}")
                logger.info(f"Prompt length: {len(prompt_text)} characters")
                
                # Capture start time for timing
                start_time = time.time()
                
                # Check client type and use appropriate calling method
                if is_groq:
                    # Groq client is consistent
                    response = client.chat.completions.create(
                        messages=messages,
                        model=model
                    )
                else:
                    # DeepSeek client might be using different OpenAI versions
                    # Determine client type and call appropriately
                    if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):
                        # Modern OpenAI client (v1.x)
                        logger.info("Using OpenAI 1.x client for DeepSeek")
                        response = client.chat.completions.create(
                            model=model,
                            messages=messages
                        )
                    elif hasattr(client, 'ChatCompletion'):
                        # Legacy OpenAI client with object (v0.x)
                        logger.info("Using OpenAI 0.x ChatCompletion object for DeepSeek")
                        response = client.ChatCompletion.create(
                            model=model,
                            messages=messages
                        )
                    else:
                        # Direct module call for older versions
                        logger.info("Using direct module call for DeepSeek")
                        import openai
                        response = openai.ChatCompletion.create(
                            model=model,
                            messages=messages
                        )
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Log success
                logger.info(f"API request successful with {model} in {duration:.2f}s")
                logger.info(f"Response type: {type(response)}")
                
                # Update health status on successful call
                status = groq_status if is_groq else deepseek_status
                status.is_healthy = True
                status.last_check_time = time.time()
                status.consecutive_failures = 0
                
                # Extract content based on response type
                if hasattr(response, 'choices') and hasattr(response.choices[0], 'message'):
                    # Modern OpenAI response object
                    return response.choices[0].message.content
                elif isinstance(response, dict) and 'choices' in response:
                    # Dictionary response from older OpenAI versions
                    return response['choices'][0]['message']['content']
                else:
                    # Fallback for unexpected response format
                    logger.warning(f"Unexpected response format: {type(response)}")
                    return str(response)
                
            except Exception as e:
                logger.error(f"{'Groq' if is_groq else 'DeepSeek'} API call failed: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                
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
        enhanced_prompt = None
        error_message = None
        
        # Try primary API
        if groq_client is not None and api_health["groq"]["healthy"]:
            try:
                enhanced_prompt = try_api_call(groq_client, True)
                logger.info("Successfully enhanced prompt using Groq API")
            except Exception as e:
                error_message = str(e)
                logger.error(f"Groq API failed, trying fallback: {error_message}")
        
        # If Groq failed or is unhealthy, try DeepSeek
        if enhanced_prompt is None and deepseek_client is not None and api_health["deepseek"]["healthy"]:
            try:
                enhanced_prompt = try_api_call(deepseek_client, False)
                logger.info("Successfully enhanced prompt using DeepSeek API (fallback)")
            except Exception as e:
                if error_message:
                    error_message += f" | DeepSeek error: {str(e)}"
                else:
                    error_message = str(e)
                logger.error(f"DeepSeek API also failed: {str(e)}")
        
        # Return result or error
        if enhanced_prompt:
            return jsonify({"enhanced_prompt": enhanced_prompt})
        else:
            logger.error("All API attempts failed")
            return jsonify({"error": "API request failed: " + (error_message or "Unknown error")}), 503
                
    except Exception as e:
        logger.exception(f"Unexpected error in enhance_prompt: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/system-health')
def system_health():
    """Comprehensive system health check endpoint for monitoring"""
    try:
        # Check environment variables
        env_check = {
            "GROQ_API_KEY": bool(GROQ_API_KEY),
            "DEEPSEEK_API_KEY": bool(DEEPSEEK_API_KEY),
            "AUTH0_CLIENT_ID": bool(app.config.get('AUTH0_CLIENT_ID')),
            "AUTH0_DOMAIN": bool(app.config.get('AUTH0_DOMAIN')),
            "SESSION_CONFIGURED": bool(app.config.get('SESSION_TYPE'))
        }
        
        # Check API health
        api_health = perform_health_checks()
        
        # Check session configuration
        session_info = {
            "session_type": app.config.get('SESSION_TYPE', 'unknown'),
            "cookie_secure": app.config.get('SESSION_COOKIE_SECURE', False),
            "file_dir": app.config.get('SESSION_FILE_DIR', 'unknown') if app.config.get('SESSION_TYPE') == 'filesystem' else None
        }
        
        # Check system resource information
        import psutil
        try:
            system_resources = {
                "memory_percent": psutil.virtual_memory().percent,
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "disk_percent": psutil.disk_usage('/').percent
            }
        except:
            system_resources = {"error": "Could not get system resource info"}
        
        # Determine overall status
        apis_healthy = any(api["healthy"] for api in api_health.values())
        env_healthy = all(env_check.values())
        
        overall_status = "healthy" if apis_healthy and env_healthy else "degraded"
        if not apis_healthy:
            overall_status = "critical"
        
        # Create response
        response = {
            "status": overall_status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "environment": env_check,
            "apis": {
                "groq": {
                    "status": "healthy" if api_health["groq"]["healthy"] else "unhealthy",
                    "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(groq_status.last_check_time)) if groq_status.last_check_time else None,
                    "consecutive_failures": groq_status.consecutive_failures,
                    "error": api_health["groq"]["error"]
                },
                "deepseek": {
                    "status": "healthy" if api_health["deepseek"]["healthy"] else "unhealthy",
                    "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(deepseek_status.last_check_time)) if deepseek_status.last_check_time else None,
                    "consecutive_failures": deepseek_status.consecutive_failures,
                    "error": api_health["deepseek"]["error"]
                }
            },
            "session": session_info,
            "system_resources": system_resources
        }
        
        status_code = 200 if overall_status == "healthy" else 503 if overall_status == "critical" else 207
        
        return jsonify(response), status_code
    except Exception as e:
        logger.exception(f"Error in system health check: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 