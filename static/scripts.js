async function loadMessages() {
    const response = await fetch('/get_messages');
    const data = await response.json();

    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = '';

    data.forEach((message) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        messageDiv.textContent = message.text;

        if (message.sender === 'user') {
            messageDiv.classList.add('user-message');
        } else {
            messageDiv.classList.add('bot-message');
        }

        messagesDiv.appendChild(messageDiv);
    });

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendMessage() {
    const messageBox = document.getElementById('message-box');
    const messageText = messageBox.value.trim();
    if (messageText === '') return;

    await fetch('/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: messageText })
    });

    messageBox.value = '';
    loadMessages();
}

document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('message-box').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});


// Load messages every 2 seconds
setInterval(loadMessages, 2000);
loadMessages();
