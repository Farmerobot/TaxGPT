import os
from openai import AzureOpenAI

client = AzureOpenAI(azure_endpoint=os.getenv("AZURE_OPENAI_API_BASE"),
api_key=os.getenv("AZURE_OPENAI_API_KEY"),
api_version="2023-03-15-preview")
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# In-memory storage for chat messages
messages = []

# Configure Azure OpenAI with environment variables
  # Replace with the API version you're using

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_message = data['text']

    # Add user's message to messages
    messages.append({"text": user_message, "sender": "user"})

    # Get response from Azure OpenAI using ChatCompletion
    try:
        response = client.chat.completions.create(model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ],
        max_tokens=150)

        # Extract the assistant's response
        ai_response = response.choices[0].message.content.strip()
        messages.append({"text": ai_response, "sender": "bot"})
    except Exception as e:
        ai_response = "Sorry, there was an error processing your request: " + str(e)
        messages.append({"text": ai_response, "sender": "bot"})

    return jsonify(success=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
