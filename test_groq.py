#!/usr/bin/env python3
"""
Minimal Groq Test

This script provides the simplest possible test for the Groq API,
using only the minimal required parameters to help identify issues.
"""

import os
import time
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Get API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY not found in environment variables")
    exit(1)

print(f"API Key: {GROQ_API_KEY[:4]}...")

# Initialize client
print("Initializing Groq client...")
client = Groq(api_key=GROQ_API_KEY)

# List models
print("\nListing models...")
try:
    models = client.models.list()
    print(f"Available models: {models}")
except Exception as e:
    print(f"ERROR listing models: {type(e).__name__}: {str(e)}")

# Test simple completion
print("\nTesting completion...")
try:
    start_time = time.time()
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Hello"}],
        model="llama-3.1-8b-instant"
    )
    duration = time.time() - start_time
    print(f"SUCCESS: Response received in {duration:.2f} seconds")
    print(f"Content: {response.choices[0].message.content}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    if hasattr(e, 'response'):
        print(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
        print(f"Response body: {getattr(e.response, 'text', 'N/A')}") 