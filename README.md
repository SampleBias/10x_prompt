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
