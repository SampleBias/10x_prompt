#!/usr/bin/env python3
"""
API Diagnostics Tool

This standalone script tests Groq and DeepSeek APIs independently to diagnose 
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
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

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

def test_deepseek():
    """Test DeepSeek API"""
    print_separator()
    logger.info("TESTING DEEPSEEK API")
    print_separator()
    
    if not DEEPSEEK_API_KEY:
        logger.error("❌ DEEPSEEK_API_KEY not found in environment variables")
        return False
    
    logger.info(f"API Key (first 4 chars): {DEEPSEEK_API_KEY[:4]}...")
    logger.info(f"API URL: {DEEPSEEK_API_URL}")
    
    # Check OpenAI version for debugging
    import openai
    logger.info(f"OpenAI version: {openai.__version__}")
    
    # Determine if we're using OpenAI 1.x or 0.x
    is_openai_v1 = openai.__version__.startswith('1.')
    logger.info(f"Using OpenAI {'1.x' if is_openai_v1 else '0.x'} API")
    
    if is_openai_v1:
        # OpenAI 1.x API approach
        try:
            logger.info("Initializing with OpenAI 1.x client...")
            from openai import OpenAI
            
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_URL
            )
            logger.info("✅ Client initialized successfully with OpenAI 1.x API")
            
            for model in ["deepseek-chat", "deepseek-coder"]:
                logger.info(f"\nTesting model: {model}")
                try:
                    logger.info("Sending test chat completion request...")
                    start_time = time.time()
                    
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "Say hello"}],
                        max_tokens=5
                    )
                    
                    duration = time.time() - start_time
                    logger.info(f"✅ Response received in {duration:.2f}s")
                    logger.info(f"Content: {response.choices[0].message.content}")
                    return True
                except Exception as e:
                    logger.error(f"❌ Failed with model {model}: {type(e).__name__}: {str(e)}")
                    if hasattr(e, 'response'):
                        try:
                            status = getattr(e.response, 'status_code', 'N/A')
                            body = getattr(e.response, 'text', 'N/A')
                            logger.error(f"Response Status: {status}")
                            logger.error(f"Response Body: {body}")
                        except:
                            pass
        except (ImportError, TypeError, Exception) as e:
            logger.error(f"❌ Failed to initialize with OpenAI 1.x API: {type(e).__name__}: {str(e)}")
    else:
        # OpenAI 0.x API approach
        try:
            logger.info("Initializing with OpenAI 0.x API...")
            
            # Direct configuration for 0.x API
            openai.api_key = DEEPSEEK_API_KEY
            openai.api_base = DEEPSEEK_API_URL
            
            logger.info("✅ API configured successfully with OpenAI 0.x API")
            
            for model in ["deepseek-chat", "deepseek-coder"]:
                logger.info(f"\nTesting model: {model}")
                try:
                    logger.info("Sending test chat completion request...")
                    start_time = time.time()
                    
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=[{"role": "user", "content": "Say hello"}],
                        max_tokens=5
                    )
                    
                    duration = time.time() - start_time
                    logger.info(f"✅ Response received in {duration:.2f}s")
                    logger.info(f"Content: {response['choices'][0]['message']['content']}")
                    return True
                except Exception as e:
                    logger.error(f"❌ Failed with model {model}: {type(e).__name__}: {str(e)}")
                    if hasattr(e, 'response'):
                        try:
                            status = getattr(e.response, 'status_code', 'N/A')
                            body = getattr(e.response, 'text', 'N/A')
                            logger.error(f"Response Status: {status}")
                            logger.error(f"Response Body: {body}")
                        except:
                            pass
        except Exception as e:
            logger.error(f"❌ Failed to initialize with OpenAI 0.x API: {type(e).__name__}: {str(e)}")
    
    # If we reach here, it means all attempts failed
    logger.error("❌ All DeepSeek API initialization attempts failed")
    logger.warning("""
    ⚠️ NOTE: If you're using OpenAI 1.x and having compatibility issues, you can:
    1. Install openai==0.28.0 for compatibility with older code: pip install openai==0.28.0
    2. Or update the application code to use the new OpenAI 1.x API
    """)
    return False

def check_environment():
    """Check environment variables and settings"""
    print_separator()
    logger.info("CHECKING ENVIRONMENT VARIABLES")
    print_separator()
    
    # Check API keys
    logger.info(f"GROQ_API_KEY set: {'Yes' if GROQ_API_KEY else 'No'}")
    logger.info(f"DEEPSEEK_API_KEY set: {'Yes' if DEEPSEEK_API_KEY else 'No'}")
    
    # Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Check installed packages
    try:
        import pkg_resources
        logger.info("Installed packages:")
        for pkg in ["openai", "groq", "flask-session", "requests"]:
            try:
                version = pkg_resources.get_distribution(pkg).version
                logger.info(f"  - {pkg}: {version}")
            except pkg_resources.DistributionNotFound:
                logger.warning(f"  - {pkg}: Not installed")
    except ImportError:
        logger.warning("Could not check installed packages")
    
    # Check connectivity to API endpoints
    import requests
    endpoints = [
        ("Groq API", "https://api.groq.com/health"),
        ("DeepSeek API", "https://api.deepseek.com/")
    ]
    
    for name, url in endpoints:
        try:
            logger.info(f"Testing connectivity to {name} ({url})...")
            start_time = time.time()
            response = requests.get(url, timeout=5)
            duration = time.time() - start_time
            logger.info(f"  - Status: {response.status_code}")
            logger.info(f"  - Response time: {duration:.2f}s")
        except Exception as e:
            logger.error(f"  - Failed to connect: {type(e).__name__}: {str(e)}")

def run_all_tests():
    """Run all diagnostic tests"""
    print_separator()
    logger.info("STARTING API DIAGNOSTICS")
    print_separator()
    
    # Check environment
    check_environment()
    
    # Test Groq with SDK
    groq_sdk_success = test_groq_with_sdk()
    
    # Test Groq with OpenAI client
    groq_openai_success = test_groq_with_openai()
    
    # Test DeepSeek
    deepseek_success = test_deepseek()
    
    # Summary
    print_separator()
    logger.info("DIAGNOSTICS SUMMARY")
    print_separator()
    logger.info(f"Groq API (SDK): {'✅ SUCCESS' if groq_sdk_success else '❌ FAILED'}")
    logger.info(f"Groq API (OpenAI client): {'✅ SUCCESS' if groq_openai_success else '❌ FAILED'}")
    logger.info(f"DeepSeek API: {'✅ SUCCESS' if deepseek_success else '❌ FAILED'}")

if __name__ == "__main__":
    run_all_tests() 