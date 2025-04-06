#!/usr/bin/env python3
"""
Minimal DeepSeek Test

This script provides the simplest possible test for the DeepSeek API,
using only the minimal required parameters to help identify issues.
"""

import os
import time
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Get API key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

if not DEEPSEEK_API_KEY:
    print("ERROR: DEEPSEEK_API_KEY not found in environment variables")
    exit(1)

print(f"API Key: {DEEPSEEK_API_KEY[:4]}...")
print(f"API URL: {DEEPSEEK_API_URL}")

# Check OpenAI version
print(f"OpenAI version: {openai.__version__}")

# Initialize client based on OpenAI version
print("Initializing DeepSeek client...")

# OpenAI 1.x client initialization
try:
    # Import the modern client
    from openai import OpenAI
    
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_API_URL
    )
    print("Client initialized successfully with OpenAI 1.x API")
    
    # Test simple completion
    print("\nTesting completion...")
    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello"}]
        )
        duration = time.time() - start_time
        print(f"SUCCESS: Response received in {duration:.2f} seconds")
        print(f"Content: {response.choices[0].message.content}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            print(f"Response body: {getattr(e.response, 'text', 'N/A')}")
    
except (ImportError, TypeError) as e:
    print(f"Modern client initialization failed: {str(e)}")
    print("Falling back to legacy client (v0.x)...")
    
    # Try to install the older version that's compatible
    print("\nThe current OpenAI version (1.x) is not compatible with the legacy API methods.")
    print("You may want to install a compatible version:")
    print("pip install openai==0.28.0")
    
    print("\nOr try running the API diagnostics tool which has additional compatibility code:")
    print("python api_diagnostics.py") 