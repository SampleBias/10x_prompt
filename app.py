from flask import Flask, render_template, request, jsonify
import os
import requests
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# DeepSeek API constants from environment variables
API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_URL = os.getenv("API_URL", "https://api.deepseek.com/v1")

if not API_KEY:
    logger.error("API key not found in environment variables")
    raise ValueError("API_KEY environment variable is not set. Please check your .env file.")

# Initialize OpenAI client with DeepSeek API URL
client = OpenAI(api_key=API_KEY, base_url=API_URL)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/enhance', methods=['POST'])
def enhance_prompt():
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
        
        # Call DeepSeek API using OpenAI SDK
        response = client.chat.completions.create(
            model="deepseek-chat",  # Using DeepSeek-V3 model as per documentation
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        # Extract the enhanced prompt from the response
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
    app.run(debug=True) 