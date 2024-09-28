from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# In-memory storage for chat messages
messages = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    messages.append({"text": data['text']})
    return jsonify(success=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
