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

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
app.config['AUTH0_CALLBACK_URL'] = os.getenv('AUTH0_CALLBACK_URL', 'https://tenx-prompt-25322b7d0675.herokuapp.com/callback')

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

# DeepSeek API constants from environment variables
API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_URL = os.getenv("API_URL", "https://api.deepseek.com")  # Base URL as per documentation

class APIError(Exception):
    """Custom exception for API-related errors"""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

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

def check_api_health(client):
    """Check if the DeepSeek API is responsive and working"""
    def health_check():
        try:
            # Send a minimal request to test the API
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hi"}
                ],
                max_tokens=10,  # Minimize tokens for health check
                stream=False
            )
            if not hasattr(response, 'choices') or not response.choices:
                raise APIError("API response missing choices")
            logger.info("DeepSeek API health check: SUCCESS")
            return True, None
        except (ConnectionError, Timeout) as e:
            error_msg = f"Connection error during health check: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg)
        except RequestException as e:
            error_msg = f"Request failed during health check: {str(e)}"
            logger.error(error_msg)
            if hasattr(e, 'response'):
                logger.error(f"Response Status: {e.response.status_code}")
                logger.error(f"Response Body: {e.response.text}")
            raise APIError(error_msg, getattr(e.response, 'status_code', None), e.response)
        except Exception as e:
            error_msg = f"Unexpected error during health check: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg)

    try:
        retry_with_backoff(health_check)
        return True, None
    except APIError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Health check failed after retries: {str(e)}"

def initialize_client():
    """Initialize the OpenAI client with proper error handling"""
    if not API_KEY:
        logger.error("DEEPSEEK_API_KEY not found in environment variables")
        return None, "API key not configured. Please check your environment variables."
    
    def create_client():
        try:
            # Try creating client with full configuration
            return OpenAI(
                api_key=API_KEY,
                base_url=API_URL,
                timeout=60.0,
                max_retries=2
            )
        except TypeError:
            # Fall back to minimal configuration if full config fails
            logger.warning("Falling back to minimal client configuration")
            return OpenAI(
                api_key=API_KEY,
                base_url=API_URL
            )

    try:
        # Create client with retry logic
        client = retry_with_backoff(create_client)
        
        # Verify the client works with a health check
        is_healthy, health_error = check_api_health(client)
        if not is_healthy:
            raise APIError(f"Health check failed: {health_error}")
        
        logger.info("Client initialized and health check passed")
        return client, None
        
    except APIError as e:
        error_msg = f"API Error during initialization: {str(e)}"
        logger.error(error_msg)
        if hasattr(e, 'response'):
            logger.error(f"Response Status: {e.status_code}")
            logger.error(f"Response Body: {e.response}")
        return None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during initialization: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

# Initialize the client
client, client_error = initialize_client()

if client is None:
    logger.error(f"Failed to initialize client: {client_error}")
else:
    logger.info("Successfully initialized OpenAI client")

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
    # Check if client is properly initialized
    if client is None:
        error_message = client_error or "API client not properly initialized"
        logger.error(error_message)
        return jsonify({"error": error_message}), 503
    
    try:
        # Verify API health before processing request
        is_healthy, health_error = check_api_health(client)
        if not is_healthy:
            logger.error(f"API health check failed before processing request: {health_error}")
            return jsonify({"error": f"API is currently unavailable: {health_error}"}), 503
            
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
        
        # Log the request
        logger.info(f"Sending request to DeepSeek API with {prompt_type} prompt")
        logger.debug(f"Request payload: {json.dumps(messages)}")
        
        def make_api_call():
            return client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            
        try:
            # Call DeepSeek API with retry logic
            response = retry_with_backoff(make_api_call)
            
            # Extract the enhanced prompt from the response
            if not hasattr(response, 'choices') or not response.choices:
                logger.error("Invalid API response format")
                logger.error(f"Full response: {json.dumps(response)}")
                return jsonify({"error": "Invalid response from API"}), 500
                
            enhanced_prompt = response.choices[0].message.content
            
            if not enhanced_prompt:
                logger.warning("Empty response from API")
                return jsonify({"error": "API returned an empty response"}), 500
            
            logger.info("Successfully enhanced prompt")
            logger.debug(f"Enhanced prompt: {enhanced_prompt}")
            
            return jsonify({"enhanced_prompt": enhanced_prompt})
            
        except (ConnectionError, Timeout) as e:
            logger.error(f"Connection error: {str(e)}")
            return jsonify({"error": "Failed to connect to the API. Please try again."}), 503
        except RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response Status: {e.response.status_code}")
                logger.error(f"Response Body: {e.response.text}")
            
            status_code = getattr(e.response, 'status_code', 500)
            if status_code == 401:
                return jsonify({"error": "Authentication failed. Please check your API key."}), 401
            elif status_code == 404:
                return jsonify({"error": "API endpoint not found. Please check the API URL."}), 404
            elif status_code == 429:
                return jsonify({"error": "Too many requests. Please try again later."}), 429
            else:
                return jsonify({"error": f"API request failed: {str(e)}"}), status_code
                
    except Exception as e:
        logger.exception("Unexpected error in enhance_prompt")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 