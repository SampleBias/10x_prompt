#!/bin/bash
# Fix DeepSeek Compatibility Issues by downgrading OpenAI SDK

echo "Checking current OpenAI SDK version..."
CURRENT_VERSION=$(pip list | grep openai | awk '{print $2}')
echo "Current OpenAI SDK version: $CURRENT_VERSION"

if [[ "$CURRENT_VERSION" = 1* ]]; then
    echo "Detected OpenAI SDK v1.x, which may have compatibility issues with DeepSeek."
    echo "Downgrading to OpenAI SDK v0.28.0 for better DeepSeek compatibility..."
    
    pip install openai==0.28.0
    
    NEW_VERSION=$(pip list | grep openai | awk '{print $2}')
    echo "OpenAI SDK version after downgrade: $NEW_VERSION"
    
    echo "Fix complete! Please restart your application."
else
    echo "You're already using OpenAI SDK v0.x, which should be compatible with DeepSeek."
    echo "No changes needed."
fi

echo ""
echo "To test DeepSeek API compatibility, run: python test_deepseek.py" 