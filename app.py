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
import re

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
app.config['SESSION_KEY_PREFIX'] = '10x_prompt:'

# Get Redis URL from environment or use default for local development
redis_url = os.environ.get('REDIS_URL')
if redis_url:
    # For Heroku environment - disable SSL certificate verification for Redis
    logger.info(f"Using Redis URL from environment: {redis_url[:15]}...")
    
    # Configure Redis connection with SSL certificate verification disabled
    redis_client = redis.from_url(
        redis_url,
        ssl_cert_reqs=None  # Disable certificate verification
    )
    app.config['SESSION_REDIS'] = redis_client
else:
    # Fallback to filesystem session for local development
    logger.warning("No Redis URL found, using filesystem sessions for development")
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = './flask_session'

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
        logger.info(f"AUTH0_CALLBACK_URL: {AUTH0_CALLBACK_URL or 'Not set'}")
        
        # Check if Auth0 is properly configured
        if not AUTH0_DOMAIN:
            logger.error("AUTH0_DOMAIN is not configured")
            return render_template('login.html', error="Authentication service configuration error: Missing domain")
            
        if not AUTH0_CLIENT_ID:
            logger.error("AUTH0_CLIENT_ID is not configured")
            return render_template('login.html', error="Authentication service configuration error: Missing client ID")
        
        if not AUTH0_CALLBACK_URL:
            logger.error("AUTH0_CALLBACK_URL is not configured")
            return render_template('login.html', error="Authentication service configuration error: Missing callback URL")
        
        # Generate a nonce for Auth0 to use
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # Store the nonce in the session
        session['auth0_nonce'] = nonce
        session.modified = True
        
        # Use the callback URL from environment variables
        logger.info(f"Using callback URL: {AUTH0_CALLBACK_URL}")
        
        # Construct the Auth0 authorization URL
        params = {
            'response_type': 'code',
            'client_id': AUTH0_CLIENT_ID,
            'redirect_uri': AUTH0_CALLBACK_URL,
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
        
        if not AUTH0_CALLBACK_URL:
            logger.error("AUTH0_CALLBACK_URL is not configured")
            return render_template('login.html', error="Authentication service configuration error: Missing callback URL")
        
        # Exchange the authorization code for tokens
        token_url = f'https://{AUTH0_DOMAIN}/oauth/token'
        token_payload = {
            'grant_type': 'authorization_code',
            'client_id': AUTH0_CLIENT_ID,
            'client_secret': AUTH0_CLIENT_SECRET,
            'code': code,
            'redirect_uri': AUTH0_CALLBACK_URL
        }
        
        logger.info(f"Exchanging code for tokens with callback URL: {AUTH0_CALLBACK_URL}")
        
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
        
        # Get start time for performance measurement
        start_time = time.time()
        
        # Prepare the enhancement request based on prompt type
        if prompt_type == 'user':
            system_message = """You are an expert prompt engineer. Your task is to enhance user prompts to make them more effective, specific, and detailed. 
            Make the prompt clearer, add relevant context, improve structure, and ensure it will get better results from AI models.
            
            IMPORTANT INSTRUCTION: Return ONLY the enhanced prompt text itself with absolutely no prefixes, explanations, or commentary.
            DO NOT include phrases like "Here is the enhanced prompt:" or "Enhanced prompt:".
            DO NOT use quotation marks around the prompt.
            DO NOT explain what you did.
            DO NOT add any text before or after the enhanced prompt.
            Your entire response should be ONLY the enhanced prompt that the user can directly copy and paste."""
        elif prompt_type == 'image':
            system_message = """You are an expert image generation prompt engineer specializing in AI image generation models like DALL-E, Midjourney, Stable Diffusion, and others.

            Your task is to convert the provided template-based image generation prompt into a comprehensive, well-structured JSON format that can be easily used with any image generation AI.

            CRITICAL REQUIREMENTS:
            1. Return ONLY valid JSON - no explanations, no prefixes, no commentary
            2. Structure the JSON with clear categories and subcategories
            3. Convert all [option1/option2/option3] brackets into "options" arrays
            4. Make the JSON comprehensive but clean
            5. Include a "final_prompt" field with a natural language summary
            
            JSON Structure should include:
            {
              "prompt_type": "image_generation",
              "category": "portrait/landscape/product/etc",
              "parameters": {
                "subject": {...},
                "style": {...},
                "lighting": {...},
                "composition": {...},
                "technical": {...}
              },
              "options": {
                "style_options": [...],
                "mood_options": [...],
                "technical_options": [...]
              },
              "final_prompt": "A natural language description combining all elements"
            }
            
            Your entire response must be valid JSON that can be parsed directly."""
        else:  # system prompt
            system_message = """You are an expert prompt engineer. Your task is to enhance system prompts that are used to control AI assistant behavior.
            Improve the clarity, specificity, and effectiveness of the system prompt. Make it more detailed, address edge cases, and ensure consistent behavior.
            
            IMPORTANT INSTRUCTION: Return ONLY the enhanced prompt text itself with absolutely no prefixes, explanations, or commentary.
            DO NOT include phrases like "Here is the enhanced prompt:" or "Enhanced prompt:".
            DO NOT use quotation marks around the prompt.
            DO NOT explain what you did.
            DO NOT add any text before or after the enhanced prompt.
            Your entire response should be ONLY the enhanced prompt that the user can directly copy and paste."""
        
        # Try to use Groq API first
        groq_api_key = os.environ.get('GROQ_API_KEY')
        enhanced_prompt = None
        api_provider = None
        api_model = None
        error_message = None
        
        if groq_api_key:
            try:
                # Initialize Groq client with latest model version
                import groq
                client = groq.Client(
                    api_key=groq_api_key,
                    default_headers={
                        "Groq-Model-Version": "latest"  # Use latest compound model features
                    }
                )
                
                # Make the API call using the Groq SDK with compound model
                chat_completion = client.chat.completions.create(
                    model="groq/compound",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": input_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4096
                )
                
                # Extract the enhanced prompt
                enhanced_prompt = chat_completion.choices[0].message.content.strip()
                api_provider = "Groq"
                api_model = "groq/compound"
                
                # Log if compound model used built-in tools (web search, code execution, etc.)
                if hasattr(chat_completion.choices[0].message, 'executed_tools'):
                    executed_tools = chat_completion.choices[0].message.executed_tools
                    if executed_tools:
                        logger.info(f"Compound model executed {len(executed_tools)} tool(s)")
                
            except Exception as groq_err:
                logger.warning(f"Groq API error, will try fallback: {str(groq_err)}")
                error_message = str(groq_err)
        else:
            logger.warning("Groq API key not found, will try fallback")
        
        # Fallback to DeepSeek API if Groq failed or wasn't available
        if not enhanced_prompt:
            deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY')
            deepseek_api_url = os.environ.get('API_URL', 'https://api.deepseek.com/v1')
            
            if deepseek_api_key:
                try:
                    # Make API request to DeepSeek
                    headers = {
                        "Authorization": f"Bearer {deepseek_api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": input_prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4096
                    }
                    
                    response = requests.post(
                        f"{deepseek_api_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    
                    response.raise_for_status()
                    response_data = response.json()
                    
                    # Extract the enhanced prompt from the response
                    enhanced_prompt = response_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    api_provider = "DeepSeek"
                    api_model = "deepseek-chat"
                    
                except Exception as deepseek_err:
                    logger.warning(f"DeepSeek API error, will try local enhancement: {str(deepseek_err)}")
                    if error_message:
                        error_message += f"; DeepSeek error: {str(deepseek_err)}"
                    else:
                        error_message = f"DeepSeek error: {str(deepseek_err)}"
            else:
                logger.warning("DeepSeek API key not found, will try local enhancement")
                if error_message:
                    error_message += "; DeepSeek API key not found"
                else:
                    error_message = "DeepSeek API key not found"
        
        # Last resort: Local enhancement (for resilience when APIs are down/rate limited)
        if not enhanced_prompt:
            logger.warning("All API calls failed, using local enhancement as last resort")
            
            # Create a basic enhancement function
            def local_enhance(prompt, prompt_type):
                if prompt_type == 'user':
                    # Simple enhancement rules for user prompts
                    enhanced = prompt
                    
                    # Add specificity and detail
                    if not any(word in prompt.lower() for word in ['specific', 'detailed', 'in-depth']):
                        enhanced = f"Provide a detailed and specific response about: {enhanced}"
                    
                    # Add output format if none specified
                    if not any(word in prompt.lower() for word in ['format', 'structure', 'organize']):
                        enhanced += "\n\nStructure your response with clear sections and bullet points where appropriate."
                    
                    # Add clarity request
                    if not any(word in prompt.lower() for word in ['clear', 'easy to understand', 'simple language']):
                        enhanced += "\n\nUse clear language and explain any technical terms."
                        
                    return enhanced
                    
                else:  # system prompt
                    # Simple enhancement rules for system prompts
                    enhanced = prompt
                    
                    # Add edge case handling
                    if not any(word in prompt.lower() for word in ['edge case', 'exception', 'special case']):
                        enhanced += "\n\nHandle edge cases and make reasonable assumptions when information is ambiguous."
                    
                    # Add consistency requirement
                    if not any(word in prompt.lower() for word in ['consistent', 'coherent', 'maintain']):
                        enhanced += "\n\nMaintain consistent behavior and tone throughout all interactions."
                        
                    return enhanced
            
            # Apply the local enhancement
            enhanced_prompt = local_enhance(input_prompt, prompt_type)
            api_provider = "Local"
            api_model = "Rule-based"
            
            # Log that we used the local enhancement
            logger.info("Used local enhancement method as fallback")
        
        if not enhanced_prompt:
            logger.error("All enhancement methods failed")
            error_msg = "Failed to enhance prompt (all methods failed)"
            if error_message:
                error_msg += f": {error_message}"
            return jsonify({"error": error_msg}), 500
        
        # Post-process to remove common prefixes, explanations, and think tags
        # Remove complete <think>...</think> blocks (case insensitive, multiline)
        think_pattern = r'<think>.*?</think>'
        enhanced_prompt = re.sub(think_pattern, '', enhanced_prompt, flags=re.DOTALL | re.IGNORECASE)
        
        # Handle incomplete <think> tags by removing everything from <think> to the end
        # This is a simple and safe approach for the most common case
        if '<think>' in enhanced_prompt.lower():
            # Find the position of <think> and remove everything from there
            think_pos = enhanced_prompt.lower().find('<think>')
            if think_pos != -1:
                enhanced_prompt = enhanced_prompt[:think_pos]
        
        # Remove any remaining standalone <think> or </think> tags
        enhanced_prompt = re.sub(r'</?think>', '', enhanced_prompt, flags=re.IGNORECASE)
        
        # Clean up extra whitespace that might be left after removing think tags
        enhanced_prompt = re.sub(r'\n\s*\n\s*\n', '\n\n', enhanced_prompt)  # Replace multiple newlines with double
        enhanced_prompt = enhanced_prompt.strip()
        
        # List of prefixes to remove
        prefixes_to_remove = [
            "Here is the enhanced prompt:", "Enhanced prompt:", "Here's the enhanced prompt:",
            "Here is your enhanced prompt:", "The enhanced prompt is:", "Enhanced version:",
            "Here's your enhanced prompt:", "Improved prompt:", "Enhanced:", "Here you go:",
            "Here is an enhanced version:", "Here's an enhanced version:", "Enhanced user prompt:",
            "Enhanced system prompt:", "Improved version:", "Here's the improved prompt:",
            "Here is the improved prompt:"
        ]
        
        # Remove any of these prefixes (case insensitive)
        for prefix in prefixes_to_remove:
            if enhanced_prompt.lower().startswith(prefix.lower()):
                # Remove the prefix and any whitespace after it
                enhanced_prompt = enhanced_prompt[len(prefix):].lstrip()
                logger.info(f"Removed prefix: '{prefix}' from response")
                
        # More advanced regex-based cleanup for prefixes followed by newlines or colons
        # Try to detect and remove intro sentences that end with a colon followed by text
        intro_pattern = r'^([^:]{5,100}?:)(\s+)(.+)$'
        intro_match = re.match(intro_pattern, enhanced_prompt, re.DOTALL)
        if intro_match:
            # Check if the first part looks like an introduction
            intro = intro_match.group(1).lower()
            if any(keyword in intro for keyword in ['enhance', 'improve', 'here', 'prompt', 'version']):
                enhanced_prompt = intro_match.group(3)
                logger.info(f"Removed intro with regex: '{intro_match.group(1)}'")

        # Remove surrounding quotes if present (single, double, or triple quotes)
        if (enhanced_prompt.startswith('"') and enhanced_prompt.endswith('"')) or \
           (enhanced_prompt.startswith("'") and enhanced_prompt.endswith("'")) or \
           (enhanced_prompt.startswith('"""') and enhanced_prompt.endswith('"""')) or \
           (enhanced_prompt.startswith("'''") and enhanced_prompt.endswith("'''")):
            # Count the quote characters at the start and end
            start_quotes = len(re.match(r'^[\'"]++', enhanced_prompt).group(0))
            end_quotes = len(re.match(r'[\'"]++$', enhanced_prompt[::-1]).group(0))
            enhanced_prompt = enhanced_prompt[start_quotes:-end_quotes]
            logger.info(f"Removed {start_quotes} opening and {end_quotes} closing quotes")
            
        # Remove "```" code blocks that might wrap the response
        if enhanced_prompt.startswith("```") and "```" in enhanced_prompt[3:]:
            # Extract content between first ``` and last ```
            first_marker = enhanced_prompt.find("```")
            last_marker = enhanced_prompt.rfind("```")
            
            # Check if we have actual content between the markers
            if last_marker > first_marker + 3:
                content_start = enhanced_prompt.find("\n", first_marker) + 1
                if content_start > 0 and content_start < last_marker:
                    enhanced_prompt = enhanced_prompt[content_start:last_marker].strip()
                    logger.info("Removed code block markers from response")
        
        # Strip any leading/trailing whitespace once more after all processing
        enhanced_prompt = enhanced_prompt.strip()
        
        # For image prompts, validate JSON format
        if prompt_type == 'image':
            try:
                # Try to parse as JSON to validate
                import json
                json_data = json.loads(enhanced_prompt)
                
                # Ensure it has required fields
                if not isinstance(json_data, dict):
                    raise ValueError("Response is not a valid JSON object")
                
                # Add some basic validation
                if 'prompt_type' not in json_data:
                    json_data['prompt_type'] = 'image_generation'
                
                # Re-serialize to ensure clean JSON
                enhanced_prompt = json.dumps(json_data, indent=2, ensure_ascii=False)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Invalid JSON response for image prompt: {e}")
                logger.error(f"Raw response: {enhanced_prompt}")
                
                # Fallback: create a structured JSON from the text response
                fallback_json = {
                    "prompt_type": "image_generation",
                    "category": "general",
                    "raw_prompt": enhanced_prompt,
                    "final_prompt": enhanced_prompt,
                    "note": "AI returned non-JSON format, wrapped in structured format",
                    "parameters": {
                        "description": enhanced_prompt
                    }
                }
                enhanced_prompt = json.dumps(fallback_json, indent=2, ensure_ascii=False)
        
        # Calculate time taken
        time_taken = time.time() - start_time
        
        # Return the enhanced prompt
        return jsonify({
            "enhanced_prompt": enhanced_prompt,
            "original_prompt": input_prompt,
            "prompt_type": prompt_type,
            "metadata": {
                "provider": api_provider,
                "model": api_model,
                "time_taken": round(time_taken, 2),
                "token_count": len(enhanced_prompt.split()) if prompt_type != 'image' else len(enhanced_prompt)
            }
        })
                
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error enhancing prompt: {error_message}")
        logger.error(traceback.format_exc())
        
        # Handle specific error types more gracefully
        if "Unexpected token '<'" in error_message or "HTML" in error_message:
            error_response = {
                'error': 'The AI service returned an unexpected response format. This may be due to high demand or a temporary service issue.',
                'details': 'Please try again in a moment, or try with a different prompt.',
                'error_type': 'INVALID_RESPONSE_FORMAT'
            }
        elif "timeout" in error_message.lower():
            error_response = {
                'error': 'The request timed out. The AI service may be experiencing high demand.',
                'details': 'Please try again in a moment.',
                'error_type': 'TIMEOUT_ERROR'
            }
        elif "rate limit" in error_message.lower():
            error_response = {
                'error': 'Rate limit exceeded. Please wait a moment before trying again.',
                'details': 'The AI service has temporary usage limits.',
                'error_type': 'RATE_LIMIT_ERROR'
            }
        else:
            error_response = {
                'error': 'Failed to enhance prompt due to an unexpected error.',
                'details': 'Please try again or contact support if the issue persists.',
                'error_type': 'GENERAL_ERROR'
            }
        
        return jsonify(error_response), 500

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