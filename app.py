from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from urllib.parse import urlencode
import os
import requests
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI
from authlib.integrations.flask_client import OAuth
from functools import wraps

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
app.config['SESSION_COOKIE_DOMAIN'] = os.getenv('SESSION_COOKIE_DOMAIN', None)
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
API_URL = os.getenv("API_URL", "https://api.deepseek.com/v1")

def initialize_client():
    """Initialize the OpenAI client with proper error handling"""
    if not API_KEY:
        logger.error("DEEPSEEK_API_KEY not found in environment variables")
        return None, "API key not configured. Please check your environment variables."
    
    try:
        # Initialize with minimal configuration
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_URL
        )
        
        # Simple models list request to test connection
        try:
            # Just initialize the client without testing
            logger.info("Successfully initialized OpenAI client")
            return client, None
        except Exception as e:
            logger.error(f"Failed to test OpenAI client connection: {str(e)}")
            return None, f"Failed to connect to API: {str(e)}"
    except Exception as e:
        error_msg = f"Failed to initialize OpenAI client: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

# Initialize the client
client, client_error = initialize_client()

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
        if 'profile' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=app.config['AUTH0_CALLBACK_URL'])

@app.route('/callback')
def callback_handling():
    try:
        token = auth0.authorize_access_token()
        resp = auth0.get('userinfo')
        userinfo = resp.json()
        
        # Make session permanent
        session.permanent = True
        
        # Store user info in session
        session['jwt_payload'] = userinfo
        session['profile'] = {
            'user_id': userinfo['sub'],
            'name': userinfo.get('name', ''),
            'picture': userinfo.get('picture', '')
        }
        
        logger.info(f"Successfully authenticated user: {userinfo.get('name', 'Unknown')}")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        return redirect(url_for('login'))

@app.before_request
def before_request():
    if 'profile' in session:
        logger.debug(f"User authenticated: {session['profile'].get('name', 'Unknown')}")
    else:
        logger.debug("No user profile in session")

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
    
    data = request.json
    prompt_text = data.get('prompt', '')
    prompt_type = data.get('type', 'user')
    
    if not prompt_text:
        logger.warning("Empty prompt received")
        return jsonify({"error": "No prompt provided"}), 400
    
    try:
        # Select the appropriate system message based on prompt type
        if prompt_type == 'system':
            system_message = SYSTEM_PROMPT_OPTIMIZER
        else:  # Default to user prompt optimizer
            system_message = USER_PROMPT_OPTIMIZER
        
        # Prepare the messages for the API
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt_text}
        ]
        
        # Log the request
        logger.info(f"Sending request to DeepSeek API with {prompt_type} prompt of length {len(prompt_text)}")
        
        # Call DeepSeek API using OpenAI SDK with better parameters
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=4000,  # Increased max tokens
            stream=False,
            timeout=30  # Added timeout
        )
        
        # Log the raw response for debugging
        logger.debug(f"Raw API response: {response}")
        
        # Extract the enhanced prompt from the response
        if not response.choices or len(response.choices) == 0:
            logger.error("API response contains no choices")
            return jsonify({"error": "Invalid API response format"}), 500
            
        enhanced_prompt = response.choices[0].message.content
        
        if not enhanced_prompt:
            logger.warning("Empty response from API")
            return jsonify({"error": "API returned an empty response"}), 500
        
        logger.info(f"Successfully enhanced {prompt_type} prompt, new length: {len(enhanced_prompt)}")
        return jsonify({"enhanced_prompt": enhanced_prompt})
    
    except Exception as e:
        # Handle all exceptions
        error_type = type(e).__name__
        error_message = str(e)
        logger.exception(f"Error {error_type}: {error_message}")
        
        # Provide user-friendly error message
        if "401" in error_message:
            return jsonify({"error": "Authentication error. Please check your API key."}), 401
        elif "404" in error_message:
            return jsonify({"error": "API endpoint not found. Please check your API URL."}), 404
        elif "429" in error_message:
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        elif "timeout" in error_message.lower() or "timed out" in error_message.lower():
            return jsonify({"error": "Request timed out. Please try again later."}), 504
        elif "connection" in error_message.lower():
            return jsonify({"error": "Connection error. Please check your internet connection."}), 503
        else:
            return jsonify({"error": f"An error occurred: {error_message}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 