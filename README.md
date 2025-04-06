# 10x Prompt

A Flask web application that enhances naive prompts into powerful instructions for large language models.

## Features

- Transform simple prompts into 10x better instructions
- Toggle between user and system prompt enhancement
- Pre-built prompt templates for various use cases
- Clean, minimalist black and white interface
- Copy enhanced prompts with a single click

## Understanding User vs System Prompts

### User Prompts
These are the actual queries or requests you send to an AI. They're like questions you ask or instructions you give in a normal conversation.

**Example:** "Write a blog post about machine learning."

**When to use:** For specific tasks, questions, or content generation that you want the AI to perform or answer.

### System Prompts
These are behind-the-scenes instructions that tell the AI *how* to behave overall. They set the tone, style, and behavior for the AI's responses.

**Example:** "Always explain concepts using simple analogies and avoid technical jargon."

**When to use:** When building your own AI assistant or setting custom instructions in platforms that support system prompts.

## Running the Application

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Set up your environment variables in a .env file:

```
DEEPSEEK_API_KEY=your_api_key_here
API_URL=https://api.deepseek.com/v1
```

3. Run the Flask application:

```bash
python app.py
```

4. Open your browser and navigate to http://localhost:5000

## API Integration

The application uses the DeepSeek-V3 API to enhance prompts. It leverages the OpenAI-compatible API interface that DeepSeek provides. The API integration follows the official DeepSeek documentation for using the "deepseek-chat" model, which accesses the latest DeepSeek-V3 model.

To use a different LLM API, you'll need to modify the API_URL and model name in the application.

## Project Structure

- `app.py` - Main Flask application
- `templates/` - HTML templates
- `static/` - CSS, JavaScript, and other static files
- `requirements.txt` - Required Python packages

## API Diagnostics

If you're experiencing issues with the API not working correctly, you can use the diagnostic scripts to test the individual APIs:

### Testing Groq API
```bash
# Run the minimal Groq API test
python test_groq.py
```

### Testing DeepSeek API
```bash
# Run the minimal DeepSeek API test
python test_deepseek.py
```

### Using the Full Diagnostic Tool
```bash
# Run comprehensive diagnostics on both APIs
python api_diagnostics.py
```

These scripts will help identify:
- If API keys are configured correctly
- If API endpoints are accessible
- If the models are available
- Response times and error messages

## Common Issues

1. **API Keys Not Set**: Ensure both `GROQ_API_KEY` and `DEEPSEEK_API_KEY` are correctly set in your `.env` file
2. **Connection Issues**: Check network connectivity to API endpoints
3. **Model Availability**: Some models may not be available or may have been renamed
4. **Rate Limiting**: Check if you've exceeded your API rate limits

## Environment Variables

The application requires these environment variables:
- `GROQ_API_KEY`: Your Groq API key
- `DEEPSEEK_API_KEY`: Your DeepSeek API key
- `DEEPSEEK_API_URL`: DeepSeek API endpoint (default: https://api.deepseek.com/v1)

## Development

To run the application locally:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your API keys
4. Run `flask run`
