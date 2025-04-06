#!/usr/bin/env python3
"""
API Diagnostics Tool

This standalone script tests the Groq API to diagnose 
connection issues and provide detailed debugging information.
"""

import os
import json
import time
import logging
import sys
from dotenv import load_dotenv
from openai import OpenAI
from groq import Groq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("api_diagnostics")

# Load environment variables
load_dotenv()

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1")

def print_separator():
    """Print a separator line for better log readability"""
    print("\n" + "=" * 80 + "\n")

def test_groq_with_sdk():
    """Test Groq API with the official Groq SDK"""
    print_separator()
    logger.info("TESTING GROQ API WITH OFFICIAL SDK")
    print_separator()
    
    if not GROQ_API_KEY:
        logger.error("❌ GROQ_API_KEY not found in environment variables")
        return False
    
    logger.info(f"API Key (first 4 chars): {GROQ_API_KEY[:4]}...")
    
    try:
        logger.info("Initializing Groq client...")
        client = Groq(api_key=GROQ_API_KEY)
        
        # Test available models
        try:
            logger.info("Fetching available models...")
            models = client.models.list()
            logger.info(f"Available models: {models}")
        except Exception as e:
            logger.error(f"❌ Failed to list models: {type(e).__name__}: {str(e)}")
        
        # Test with different models
        test_models = [
            "llama-3.1-8b-instant",
            "llama-3.1-70b-instant",
            "llama-3.1-8b",
            "mixtral-8x7b-32768"
        ]
        
        for model in test_models:
            logger.info(f"\nTesting model: {model}")
            try:
                logger.info("Sending test chat completion request...")
                start_time = time.time()
                
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": "Say hello"}],
                    model=model,
                    max_tokens=5
                )
                
                duration = time.time() - start_time
                logger.info(f"✅ Response received in {duration:.2f}s")
                logger.info(f"Response: {response}")
                logger.info(f"Content: {response.choices[0].message.content}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed with model {model}: {type(e).__name__}: {str(e)}")
                if hasattr(e, 'response'):
                    try:
                        status = getattr(e.response, 'status_code', 'N/A')
                        headers = getattr(e.response, 'headers', {})
                        body = getattr(e.response, 'text', 'N/A')
                        logger.error(f"Response Status: {status}")
                        logger.error(f"Response Headers: {headers}")
                        logger.error(f"Response Body: {body}")
                    except:
                        pass
        
        return False
    except Exception as e:
        logger.error(f"❌ Failed to initialize Groq client: {type(e).__name__}: {str(e)}")
        return False

def test_groq_with_openai():
    """Test Groq API using the OpenAI client (compatibility mode)"""
    print_separator()
    logger.info("TESTING GROQ API WITH OPENAI CLIENT")
    print_separator()
    
    if not GROQ_API_KEY:
        logger.error("❌ GROQ_API_KEY not found in environment variables")
        return False
    
    logger.info(f"API Key (first 4 chars): {GROQ_API_KEY[:4]}...")
    logger.info(f"API URL: {GROQ_API_URL}")
    
    try:
        logger.info("Initializing OpenAI client for Groq...")
        client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url=GROQ_API_URL,
            timeout=30.0,
            max_retries=1
        )
        
        # Test with different models
        test_models = [
            "llama-3.1-8b-instant",
            "llama-3.1-70b-instant",
            "llama-3.1-8b",
            "mixtral-8x7b-32768"
        ]
        
        for model in test_models:
            logger.info(f"\nTesting model: {model}")
            try:
                logger.info("Sending test chat completion request...")
                start_time = time.time()
                
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": "Say hello"}],
                    model=model,
                    max_tokens=5
                )
                
                duration = time.time() - start_time
                logger.info(f"✅ Response received in {duration:.2f}s")
                logger.info(f"Response: {response}")
                logger.info(f"Content: {response.choices[0].message.content}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed with model {model}: {type(e).__name__}: {str(e)}")
                if hasattr(e, 'response'):
                    try:
                        status = getattr(e.response, 'status_code', 'N/A')
                        headers = getattr(e.response, 'headers', {})
                        body = getattr(e.response, 'text', 'N/A')
                        logger.error(f"Response Status: {status}")
                        logger.error(f"Response Headers: {headers}")
                        logger.error(f"Response Body: {body}")
                    except:
                        pass
        
        return False
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI client for Groq: {type(e).__name__}: {str(e)}")
        return False

def check_environment():
    """Check environment variables and dependencies"""
    print_separator()
    logger.info("CHECKING ENVIRONMENT")
    print_separator()
    
    # Check API keys
    api_keys = {
        "GROQ_API_KEY": GROQ_API_KEY
    }
    
    for key, value in api_keys.items():
        if value:
            logger.info(f"✅ {key} is set (first 4 chars: {value[:4]}...)")
        else:
            logger.error(f"❌ {key} is not set")
    
    # Check Python version
    import platform
    logger.info(f"Python Version: {platform.python_version()}")
    
    # Check OpenAI version
    try:
        import openai
        logger.info(f"OpenAI Version: {openai.__version__}")
    except ImportError:
        logger.error("❌ OpenAI package not installed")
    
    # Check Groq version
    try:
        import groq
        logger.info(f"Groq Version: {groq.__version__}")
    except ImportError:
        logger.error("❌ Groq package not installed")
    
    # Check network connectivity
    try:
        import requests
        response = requests.get("https://api.groq.com", timeout=5)
        logger.info(f"✅ Can reach Groq API endpoint. Status: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Cannot reach Groq API endpoint: {str(e)}")

def run_all_tests():
    """Run all diagnostic tests"""
    print_separator()
    logger.info("RUNNING API DIAGNOSTICS")
    print_separator()
    
    # Check environment
    check_environment()
    
    # Test Groq API
    groq_sdk_success = test_groq_with_sdk()
    if not groq_sdk_success:
        groq_openai_success = test_groq_with_openai()
    else:
        groq_openai_success = True
        logger.info("Skipping OpenAI client Groq test as SDK test was successful")
    
    # Results summary
    print_separator()
    logger.info("DIAGNOSTIC RESULTS SUMMARY")
    print_separator()
    
    logger.info(f"Groq API with SDK: {'✅ PASSED' if groq_sdk_success else '❌ FAILED'}")
    if not groq_sdk_success:
        logger.info(f"Groq API with OpenAI client: {'✅ PASSED' if groq_openai_success else '❌ FAILED'}")
    
    # Overall status
    groq_success = groq_sdk_success or groq_openai_success
    
    print_separator()
    if groq_success:
        logger.info("✅ API DIAGNOSTICS SUCCESSFUL: At least one API is operational")
        logger.info("You can use the application normally.")
    else:
        logger.error("❌ API DIAGNOSTICS FAILED: No working API connections")
        logger.error("Please check your API keys, network connectivity, and server status.")
    print_separator()

if __name__ == "__main__":
    run_all_tests() 