from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response, flash
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
import redis
from datetime import datetime, timedelta
import random
import string
import traceback

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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_please_change')

# Configure Redis session
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'prompt_enhancer:'

# Get Redis URL from environment or use default for local development
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
app.config['SESSION_REDIS'] = redis.from_url(redis_url)

# Initialize Flask-Session
Session(app)

# Constants
SESSION_DURATION = int(os.environ.get('SESSION_DURATION', 86400))  # 24 hours in seconds

# Track session creation and access times for debugging
session_tracker = {}

# Auth0 Configuration
AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
AUTH0_CALLBACK_URL = os.environ.get('AUTH0_CALLBACK_URL', 'http://localhost:5000/callback')
AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE')
AUTH0_BASE_URL = f'https://{AUTH0_DOMAIN}'

# Authentication decorator
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Debug session info
        logger.info(f"Auth check for path: {request.path}")
        logger.info(f"Current session data: {dict(session)}")
        session_id = request.cookies.get(app.config['SESSION_COOKIE_NAME'])
        logger.info(f"Session ID: {session_id or 'None'}")
        
        # Detailed check for authentication status
        has_profile = 'profile' in session
        has_user_id = has_profile and session.get('profile', {}).get('user_id')
        
        if not has_profile:
            logger.warning("No profile in session, redirecting to login")
            return redirect(url_for('login_page'))
        
        if not has_user_id:
            logger.warning("Invalid profile data in session (missing user_id), clearing session")
            session.clear()
            session.modified = True
            return redirect(url_for('login_page'))
        
        # Log authentication success
        logger.info(f"Auth successful for user: {session['profile'].get('name', 'Unknown')}")
        
        # Ensure session is marked as modified to prevent getting lost
        session.modified = True
        
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    # User is authenticated (ensured by @requires_auth)
    response = make_response(render_template('index.html', profile=session.get('profile', {})))
    # Ensure proper cache headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/login')
def login_page():
    # Log the request to the login page
    logger.info("User accessing login page")
    logger.info(f"Session state: {dict(session)}")
    
    # If user is already logged in, redirect to the main application
    if 'profile' in session and session.get('profile', {}).get('user_id'):
        logger.info(f"User already authenticated: {session['profile'].get('name', 'Unknown')}")
        return redirect(url_for('index'))
    
    # Display login page for unauthenticated users
    return render_template('login.html')

@app.route('/login_with_auth0')
def login_with_auth0():
    # Detailed error handling for Auth0 initialization
    try:
        # Log detailed auth0 configuration for debugging
        logger.info("Auth0 login attempt - checking configuration")
        logger.info(f"AUTH0_DOMAIN: {AUTH0_DOMAIN or 'Not set'}")
        logger.info(f"AUTH0_CLIENT_ID: {'Set' if AUTH0_CLIENT_ID else 'Not set'}")
        logger.info(f"AUTH0_CLIENT_SECRET: {'Set' if AUTH0_CLIENT_SECRET else 'Not set'}")
        
        # Check if Auth0 is properly configured
        if not AUTH0_DOMAIN:
            logger.error("AUTH0_DOMAIN is not configured")
            return render_template('login.html', error="Authentication service configuration error: Missing domain")
            
        if not AUTH0_CLIENT_ID:
            logger.error("AUTH0_CLIENT_ID is not configured")
            return render_template('login.html', error="Authentication service configuration error: Missing client ID")
        
        # Generate a nonce for Auth0 to use
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # Store the nonce in the session
        session['auth0_nonce'] = nonce
        session.modified = True
        
        # Hardcoded callback URL as specified in Auth0 settings
        callback_url = 'https://tenx-prompt-25322b7d0675.herokuapp.com/callback'
        logger.info(f"Using callback URL: {callback_url}")
        
        # Construct the Auth0 authorization URL
        params = {
            'response_type': 'code',
            'client_id': AUTH0_CLIENT_ID,
            'redirect_uri': callback_url,
            'scope': 'openid profile email',
            'nonce': nonce,
            'state': ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        }
        
        # Only add audience if it's configured
        if AUTH0_AUDIENCE:
            params['audience'] = AUTH0_AUDIENCE
        
        # Log the authorization attempt
        logger.info(f"Redirecting to Auth0 for authentication with nonce: {nonce}")
        
        # Construct the Auth0 URL
        auth_url = f'https://{AUTH0_DOMAIN}/authorize?' + urlencode(params)
        logger.info(f"Auth0 URL: {auth_url}")
        
        # Redirect the user to Auth0 for authentication
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error in Auth0 authentication flow: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('login.html', error=f"Authentication error: {str(e)}")

@app.route('/callback')
def callback():
    # This route handles the callback from Auth0
    try:
        # Get the authorization code from the callback
        code = request.args.get('code')
        
        if not code:
            logger.error("No authorization code received from Auth0")
            return render_template('login.html', error="Authentication failed. Please try again.")
        
        # Check if Auth0 is properly configured
        if not AUTH0_DOMAIN or not AUTH0_CLIENT_ID or not AUTH0_CLIENT_SECRET:
            logger.error("Auth0 configuration is incomplete for token exchange")
            return render_template('login.html', error="Authentication service is not properly configured.")
        
        # Set the callback URL to match what's configured in Auth0
        callback_url = 'https://tenx-prompt-25322b7d0675.herokuapp.com/callback'
        
        # Exchange the authorization code for tokens
        token_url = f'https://{AUTH0_DOMAIN}/oauth/token'
        token_payload = {
            'grant_type': 'authorization_code',
            'client_id': AUTH0_CLIENT_ID,
            'client_secret': AUTH0_CLIENT_SECRET,
            'code': code,
            'redirect_uri': callback_url
        }
        
        logger.info(f"Exchanging code for tokens with callback URL: {callback_url}")
        
        # Make the token exchange request
        token_response = requests.post(token_url, json=token_payload)
        
        # Check if token exchange was successful
        if token_response.status_code != 200:
            logger.error(f"Failed to exchange code for tokens: {token_response.text}")
            return render_template('login.html', error="Failed to complete authentication. Please try again.")
        
        # Extract tokens from the response
        tokens = token_response.json()
        access_token = tokens.get('access_token')
        
        if not access_token:
            logger.error("No access token received from Auth0")
            return render_template('login.html', error="Authentication failed. No access token received.")
        
        # Use the access token to get user information
        user_info_url = f'https://{AUTH0_DOMAIN}/userinfo'
        user_info_response = requests.get(
            user_info_url,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        # Check if user info request was successful
        if user_info_response.status_code != 200:
            logger.error(f"Failed to get user info: {user_info_response.text}")
            return render_template('login.html', error="Failed to retrieve user information.")
        
        # Extract user information
        user_info = user_info_response.json()
        
        # Ensure we have a user_id
        if not user_info.get('sub'):
            logger.error("No user ID (sub) in user info response")
            return render_template('login.html', error="User identification failed.")
        
        # Store user information in the session
        session['profile'] = {
            'user_id': user_info.get('sub'),
            'name': user_info.get('name', 'Unknown'),
            'email': user_info.get('email', ''),
            'picture': user_info.get('picture', ''),
            'login_time': datetime.now().isoformat()
        }
        
        # Force session to be saved
        session.modified = True
        
        # Log successful authentication
        logger.info(f"User authenticated successfully: {user_info.get('name')}")
        
        # Redirect to the main application
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error in Auth0 callback: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('login.html', error="Authentication error. Please try again later.")

@app.route('/logout')
def logout():
    # Capture user info for logging before clearing
    user_name = session.get('profile', {}).get('name', 'Unknown')
    session_id = request.cookies.get(app.config['SESSION_COOKIE_NAME'], 'None')
    
    # Clear user session completely
    session.clear()
    
    # Ensure session is marked as modified
    session.modified = True
    
    # Log the logout action with user details
    logger.info(f"User logged out: {user_name} (Session ID: {session_id})")
    
    # Get the Auth0 domain
    if not AUTH0_DOMAIN or not AUTH0_CLIENT_ID:
        logger.warning("Auth0 configuration incomplete, cannot redirect to Auth0 logout")
        return redirect(url_for('login_page'))
    
    # Construct the Auth0 logout URL
    params = {
        'returnTo': 'https://tenx-prompt-25322b7d0675.herokuapp.com/login',
        'client_id': AUTH0_CLIENT_ID
    }
    logout_url = f'https://{AUTH0_DOMAIN}/v2/logout?' + urlencode(params)
    
    # Log the logout URL
    logger.info(f"Redirecting to Auth0 logout: {logout_url}")
    
    # Redirect to Auth0 logout endpoint
    return redirect(logout_url)

@app.route('/enhance', methods=['POST'])
@requires_auth
def enhance_prompt():
    """Enhance a prompt using the selected API"""
    try:
        # Check session again inside the route
        if 'profile' not in session or not session.get('profile', {}).get('user_id'):
            logger.warning("Session lost between auth decorator and route function")
            return jsonify({"error": "Authentication required", "code": "SESSION_LOST"}), 401
        
        # Force session save at the beginning of the request
        session.modified = True
        
        # Extract data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        input_prompt = data.get('prompt', '').strip()
        prompt_type = data.get('type', 'user').lower()  # Default to user prompt
        
        if not input_prompt:
            return jsonify({"error": "No prompt provided"}), 400
            
        # Log the user making the request
        logger.info(f"Enhancement requested by: {session['profile'].get('name')} (User ID: {session['profile'].get('user_id')})")
        
        # For demo purposes, add some delay to simulate processing
        time.sleep(1)
        
        # Return a simple enhanced version (placeholder for actual API integration)
        enhanced_prompt = f"Enhanced ({prompt_type}): {input_prompt}"
        
        # Return the enhanced prompt
        return jsonify({
            "enhanced_prompt": enhanced_prompt,
            "original_prompt": input_prompt,
            "prompt_type": prompt_type,
            "metadata": {
                "provider": "Demo",
                "model": "Mock-GPT",
                "time_taken": 1.0,
                "token_count": len(enhanced_prompt.split())
            }
        })
                
    except Exception as e:
        logger.error(f"Error enhancing prompt: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to enhance prompt'}), 500

@app.route('/system-health')
def system_health():
    """Endpoint to check system health including Redis connection"""
    health = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis": {
                "status": "unknown"
            },
            "auth0": {
                "configured": bool(AUTH0_DOMAIN and AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET)
            },
            "session": {
                "type": app.config['SESSION_TYPE'],
                "active": True
            }
        }
    }
    
    # Check Redis connection if using Redis
    if app.config['SESSION_TYPE'] == 'redis':
        try:
            redis_client = app.config['SESSION_REDIS']
            redis_client.ping()
            health["components"]["redis"]["status"] = "connected"
        except Exception as e:
            health["components"]["redis"]["status"] = "error"
            health["components"]["redis"]["error"] = str(e)
            health["status"] = "degraded"
    
    return jsonify(health)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 