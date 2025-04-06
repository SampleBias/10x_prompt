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

# Check for Heroku environment
if os.getenv('HEROKU_APP_NAME'):
    logger.info(f"Running on Heroku with app name: {os.getenv('HEROKU_APP_NAME')}")
else:
    logger.info("Running in development environment")

# Model configuration
PRIMARY_MODEL = "mistral-saba-24b"
FALLBACK_MODEL = "llama-3.1-8b-instant"

logger.info(f"Primary Groq model: {PRIMARY_MODEL}")
logger.info(f"Fallback Groq model: {FALLBACK_MODEL}")

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
        
        # For Groq with multiple models
        if name == "Groq":
            self.primary_healthy = False
            self.primary_error = None
            self.fallback_healthy = False
            self.fallback_error = None

# Global API status trackers
groq_status = APIStatus("Groq")

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
    logger.info("=== End API Configuration ===\n")

# Call this right after loading environment variables
log_api_details()

def check_api_health(client, is_groq=True, use_primary_model=True):
    """Check if the API is responsive and working"""
    status = groq_status
    api_name = "Groq"
    
    def health_check():
        try:
            logger.info(f"\n=== Starting {api_name} Health Check ===")
            
            # Select appropriate Groq model
            model = PRIMARY_MODEL if use_primary_model else FALLBACK_MODEL
            logger.info(f"Using model: {model}")
            logger.info(f"API URL: {GROQ_API_URL}")
            logger.info(f"API Key configured: {'Yes' if GROQ_API_KEY else 'No'}")
            logger.info(f"Client initialized: {'Yes' if client else 'No'}")
            
            if not client:
                raise APIError("API client not initialized")
            
            logger.info(f"Sending test request to {api_name} API...")
            start_time = time.time()
            
            # Create a simple test message
            messages = [{"role": "user", "content": "Hello"}]
            
            # Groq client is consistent
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                max_tokens=5  # Minimize token usage for health check
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Request completed in {elapsed_time:.2f} seconds")
            
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
            
            duration = elapsed_time
            logger.info(f"{api_name} API is healthy with model {model} (response time: {duration:.2f}s)")
            
            # Update status
            status.is_healthy = True
            status.last_check_time = time.time()
            status.consecutive_failures = 0
            
            # Update model-specific status for Groq
            if is_groq:
                if use_primary_model:
                    status.primary_healthy = True
                    status.primary_error = None
                else:
                    status.fallback_healthy = True
                    status.fallback_error = None
            
            return True, None
        
        except Exception as e:
            logger.error(f"Error during {api_name} health check: {str(e)}")
            
            # Update status
            status.is_healthy = False
            status.last_check_time = time.time()
            status.last_error = str(e)
            status.consecutive_failures += 1
            
            # Update model-specific status for Groq
            if is_groq:
                if use_primary_model:
                    status.primary_healthy = False
                    status.primary_error = str(e)
                else:
                    status.fallback_healthy = False
                    status.fallback_error = str(e)
            
            return False, str(e)
    
    # Run the health check with retries
    return retry_with_backoff(health_check)

def perform_health_checks():
    """Perform health checks for all APIs"""
    results = {
        "groq": {"healthy": False, "error": None}
    }
    
    # Check Groq Primary
    if groq_client is not None:
        is_healthy, error = check_api_health(groq_client, True, True)
        groq_status.primary_healthy = is_healthy
        groq_status.primary_error = error
        
        results["groq"]["primary_healthy"] = is_healthy
        results["groq"]["primary_error"] = error
        
        # If primary is healthy, overall Groq is healthy
        if is_healthy:
            results["groq"]["healthy"] = True
        else:
            # Try fallback
            is_healthy, error = check_api_health(groq_client, True, False)
            groq_status.fallback_healthy = is_healthy
            groq_status.fallback_error = error
            
            results["groq"]["fallback_healthy"] = is_healthy
            results["groq"]["fallback_error"] = error
            
            # If fallback is healthy, overall Groq is still healthy
            if is_healthy:
                results["groq"]["healthy"] = True
            else:
                results["groq"]["error"] = "Both primary and fallback models failed"
    else:
        results["groq"]["error"] = "Groq client not initialized"
    
    # Update health status objects
    groq_status.is_healthy = results["groq"]["healthy"]
    groq_status.last_check_time = time.time()
    
    if not results["groq"]["healthy"]:
        groq_status.consecutive_failures += 1
        groq_status.last_error = results["groq"]["error"]
    else:
        groq_status.consecutive_failures = 0
        groq_status.last_error = None
    
    detailed_results = {
        "groq": results["groq"]
    }
    
    logger.info(f"Health check complete. Groq: {detailed_results['groq']['healthy']}")
    
    return detailed_results

@app.route('/health')
def health_check():
    """API health check endpoint"""
    try:
        results = perform_health_checks()
        
        # Build response
        response = {
            "status": "healthy" if results["groq"]["healthy"] else "unhealthy",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "apis": {
                "groq": {
                    "status": "healthy" if results["groq"]["healthy"] else "unhealthy",
                    "primary_model": PRIMARY_MODEL,
                    "fallback_model": FALLBACK_MODEL,
                    "primary_status": "healthy" if results["groq"].get("primary_healthy", False) else "unhealthy",
                    "fallback_status": "healthy" if results["groq"].get("fallback_healthy", False) else "unhealthy",
                    "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(groq_status.last_check_time)) if groq_status.last_check_time else None,
                    "consecutive_failures": groq_status.consecutive_failures,
                    "error": results["groq"]["error"]
                }
            }
        }
        
        # Return with appropriate status code
        is_healthy = results["groq"]["healthy"]
        return jsonify(response), 200 if is_healthy else 503
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }), 500

def initialize_groq_client():
    """Initialize the Groq client with proper error handling using the native Groq client"""
    logger.info("\n=== Initializing Groq Client ===")
    logger.info(f"GROQ_API_URL: {GROQ_API_URL}")
    logger.info(f"API Key Present: {'Yes' if GROQ_API_KEY else 'No'}")
    
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not found in environment variables")
        return None, "Groq API key not configured. Please check your environment variables."
    
    try:
        # Import Groq client directly
        from groq import Groq
        
        # Create native Groq client with minimal parameters
        logger.info("Creating native Groq client...")
        client = Groq(api_key=GROQ_API_KEY)
        
        # Test the client with a simple request
        logger.info("Testing Groq client connection...")
        try:
            # Test chat completion with minimal parameters
            logger.info("Sending test request to Groq API...")
            logger.info("Request parameters:")
            logger.info({
                "model": PRIMARY_MODEL,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            })
            
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                model=PRIMARY_MODEL,
                max_tokens=5
            )
            logger.info("Successfully tested Groq connection")
            logger.info(f"Response: {response}")
        except Exception as e:
            logger.error(f"Failed to test Groq with primary model: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            
            # Try fallback model
            logger.info(f"Attempting with fallback model: {FALLBACK_MODEL}")
            try:
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": "Hi"}],
                    model=FALLBACK_MODEL,
                    max_tokens=5
                )
                logger.info("Successfully tested Groq connection with fallback model")
                logger.info(f"Response: {response}")
            except Exception as e2:
                logger.error("Failed to test Groq connection with fallback model")
                logger.error(f"Error type: {type(e2).__name__}")
                logger.error(f"Error message: {str(e2)}")
                if hasattr(e2, 'response'):
                    logger.error(f"Response Status: {getattr(e2.response, 'status_code', 'N/A')}")
                    logger.error(f"Response Headers: {getattr(e2.response, 'headers', {})}")
                    logger.error(f"Response Body: {getattr(e2.response, 'text', 'N/A')}")
                # Don't raise the exception, return with error message
                return None, f"Groq connection test failed: {str(e2)}"
        
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

# Initialize groq client
groq_client, groq_error = initialize_groq_client()

# Startup Health Check and Logging
logger.info("=== Starting Application Health Check ===")
logger.info("Checking API clients initialization status:")

if groq_client is None:
    logger.error(f"❌ Groq client initialization failed: {groq_error}")
    logger.error("⚠️ WARNING: API client failed to initialize")
else:
    logger.info("✓ Groq client initialized successfully")

# Perform initial health checks
startup_health = perform_health_checks()
logger.info("\n=== Initial API Health Check Results ===")

# Log Groq health status
if "groq" in startup_health:
    if startup_health["groq"]["healthy"]:
        logger.info("✓ Groq API Health Check: PASSED")
    else:
        logger.error(f"❌ Groq API Health Check: FAILED - {startup_health['groq']['error']}")

# Log overall system status
healthy_apis = [api for api, status in startup_health.items() if status["healthy"]]
logger.info("\n=== System Status Summary ===")
logger.info(f"Total APIs available: {len(startup_health)}")
logger.info(f"Healthy APIs: {len(healthy_apis)}")
if len(healthy_apis) == 0:
    logger.critical("⚠️ CRITICAL: No healthy APIs available!")
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
    """Enhance a prompt using the selected API"""
    try:
        # Extract data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        input_prompt = data.get('prompt', '').strip()
        prompt_type = data.get('type', 'user').lower()  # Default to user prompt
        
        if not input_prompt:
            return jsonify({"error": "No prompt provided"}), 400
            
        # Select system prompt based on prompt type
        if prompt_type == 'system':
            system_prompt = SYSTEM_PROMPT_OPTIMIZER
            logger.info("Using SYSTEM prompt optimizing template")
        else:
            system_prompt = USER_PROMPT_OPTIMIZER
            logger.info("Using USER prompt optimizing template")
        
        # Set up the prompt for processing
        logger.info(f"Received {prompt_type} prompt enhancement request ({len(input_prompt)} chars)")
        
        # Max tokens settings
        max_tokens = min(len(input_prompt) * 2, 4000)  # Double input length but cap at 4000
        
        # Set maximum time allowed for API call
        max_api_time = 30  # seconds
        
        # Health check (quick) before processing
        if groq_client is None:
            return jsonify({"error": "No API clients available"}), 503
            
        # Prep for API calls with multiple potential clients
        is_using_groq = True
        client = groq_client
        model = PRIMARY_MODEL  # Default to primary model
        
        # Check if primary Groq model is healthy
        if not getattr(groq_status, 'primary_healthy', False):
            # Try fallback model if available
            if getattr(groq_status, 'fallback_healthy', False):
                logger.info("Primary Groq model unhealthy, using fallback model")
                model = FALLBACK_MODEL
            else:
                return jsonify({"error": "No healthy API providers available"}), 503
        
        def try_api_call(client, is_groq=True, model=None):
            """Make an API call with the given client"""
            # If using Groq, specify the model explicitly
            if is_groq:
                logger.info(f"Using Groq API with model: {model}")
                
                # Set up messages for Groq
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_prompt}
                ]
                
                # Execute the API call with timeout via request
                start_time = time.time()
                
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    top_p=0.95
                )
                
                # Extract the response
                enhanced_prompt = response.choices[0].message.content.strip()
                
                # Track API call time
                api_time = time.time() - start_time
                
                return enhanced_prompt, api_time
        
        # Initialize variables for result tracking
        enhanced_prompt = None
        api_time = None
        provider_used = None
        model_used = None
        error = None
        
        # Try API call with retry and timeout protection
        try:
            logger.info(f"Attempting to use {'Groq' if is_using_groq else 'Unknown'} API...")
            start_time = time.time()
            
            # Wrap in a timeout controller
            if time.time() - start_time > max_api_time:
                raise TimeoutError(f"API request took too long (> {max_api_time}s)")
                
            # Make the API call with retry
            enhanced_prompt, api_time = retry_with_backoff(
                lambda: try_api_call(client, is_using_groq, model),
                max_retries=2,
                initial_delay=1
            )
            
            # Record which provider and model was used
            provider_used = "Groq" if is_using_groq else "Unknown"
            model_used = model if is_using_groq else "Unknown"
            
            # Log successful completion
            logger.info(f"Enhancement successful with {provider_used} ({model_used}) in {api_time:.2f}s")
            
        except Exception as e:
            # Log the error
            logger.error(f"Error during enhancement: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Set error info
            error = str(e)
            
            # Return error response
            return jsonify({
                "error": "Enhancement failed",
                "details": str(e)
            }), 500
        
        # Check if we have a valid enhanced prompt
        if not enhanced_prompt:
            return jsonify({
                "error": "No enhanced prompt generated",
                "details": error or "Unknown error"
            }), 500
            
        # Return the enhanced prompt with metadata
        response_data = {
            "enhanced_prompt": enhanced_prompt,
            "original_prompt": input_prompt,
            "prompt_type": prompt_type,
            "metadata": {
                "provider": provider_used,
                "model": model_used,
                "time_taken": api_time,
                "token_count": len(enhanced_prompt.split())
            }
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Unexpected error in enhance_prompt: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/system-health')
def system_health():
    """Detailed system health endpoint"""
    results = perform_health_checks()
    
    # Build response
    response = {
        "status": "healthy" if results["groq"]["healthy"] else "unhealthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "apis": {
            "groq": {
                "status": "healthy" if results["groq"]["healthy"] else "unhealthy", 
                "primary_model": PRIMARY_MODEL,
                "fallback_model": FALLBACK_MODEL,
                "primary_status": "healthy" if results["groq"].get("primary_healthy", False) else "unhealthy",
                "fallback_status": "healthy" if results["groq"].get("fallback_healthy", False) else "unhealthy",
                "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(groq_status.last_check_time)) if groq_status.last_check_time else None,
                "consecutive_failures": groq_status.consecutive_failures,
                "error": results["groq"]["error"]
            }
        },
        "app_info": {
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": "production" if os.getenv('HEROKU_APP_NAME') else "development"
        }
    }
    
    # Return with appropriate status code
    is_healthy = results["groq"]["healthy"]
    return jsonify(response), 200 if is_healthy else 503

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 