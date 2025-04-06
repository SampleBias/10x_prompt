#!/usr/bin/env python3
"""
Minimal DeepSeek Test

This script provides the simplest possible test for the DeepSeek API,
using only the minimal required parameters to help identify issues.
"""

import os
import time
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get API key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")

if not DEEPSEEK_API_KEY:
    print("ERROR: DEEPSEEK_API_KEY not found in environment variables")
    exit(1)

print(f"API Key: {DEEPSEEK_API_KEY[:4]}...")
print(f"API URL: {DEEPSEEK_API_URL}")

# Initialize client
print("Initializing DeepSeek client...")
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_API_URL
)

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