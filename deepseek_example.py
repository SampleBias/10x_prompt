#!/usr/bin/env python3
"""
DeepSeek Example from Documentation

Modified to handle different versions of the OpenAI SDK.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use the API key from environment variables
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("ERROR: DEEPSEEK_API_KEY not found in environment variables")
    exit(1)

print(f"Using DeepSeek API key: {api_key[:4]}...")

# Check OpenAI version
import openai
print(f"OpenAI version: {openai.__version__}")

try:
    # Method 1: Try the documented approach with no extra parameters
    print("\nMethod 1: Trying with OpenAI client constructor, no extra params...")
    from openai import OpenAI
    client = OpenAI(
        api_key=api_key, 
        base_url="https://api.deepseek.com"
    )
    
    print("Client initialized successfully, sending request...")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ],
        stream=False
    )
    print("\nResponse received:")
    print(response.choices[0].message.content)
    
except Exception as e:
    print(f"Method 1 failed: {type(e).__name__}: {str(e)}")
    
    try:
        # Method 2: Try with httpx configuration (for older versions)
        print("\nMethod 2: Trying with httpx_client=None...")
        try:
            from httpx import HTTPTransport
            # Configure transport without proxies
            transport = HTTPTransport()
            print("Created HTTP transport")
        except ImportError:
            transport = None
            print("HTTPTransport not available")
            
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key, 
            base_url="https://api.deepseek.com",
            http_client=None
        )
        
        print("Client initialized successfully, sending request...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello"},
            ],
            stream=False
        )
        print("\nResponse received:")
        print(response.choices[0].message.content)
        
    except Exception as e2:
        print(f"Method 2 failed: {type(e2).__name__}: {str(e2)}")
        
        try:
            # Method 3: Direct module access for OpenAI 0.x
            print("\nMethod 3: Trying with direct module configuration (OpenAI 0.x)...")
            openai.api_key = api_key
            openai.api_base = "https://api.deepseek.com"
            
            print("API configured, sending request...")
            try:
                # For OpenAI 0.x
                response = openai.ChatCompletion.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": "Hello"},
                    ]
                )
                print("\nResponse received:")
                print(response["choices"][0]["message"]["content"])
                
            except AttributeError:
                print("ChatCompletion not found, OpenAI 0.x API not available")
                print("\nSuggested solution:")
                print("pip install openai==0.28.0")
                print("Or update DeepSeek client code to work with OpenAI 1.x")
        
        except Exception as e3:
            print(f"Method 3 failed: {type(e3).__name__}: {str(e3)}")
            print("\nAll methods failed. You may need to downgrade the OpenAI package:")
            print("pip install openai==0.28.0")

print("\nDiagnostic information:")
print(f"Python version: {sys.version}")
print(f"OpenAI package path: {openai.__file__}")
try:
    import httpx
    print(f"httpx version: {httpx.__version__}")
except ImportError:
    print("httpx not installed") 