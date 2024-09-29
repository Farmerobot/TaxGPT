/**
 * Asynchronously fetches and loads messages from the server.
 * This function clears the existing message container and populates it with new messages.
 * Also ensures the container scrolls to the latest message.
 */
async function loadMessages() {
    try {
        // Fetch the messages from the server
        const response = await fetch('/get_messages');
        const data = await response.json();

        // Reference to the messages container in the DOM
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML = ''; // Clear existing messages

        // Append each message to the messages container
        data.forEach((message) => {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            messageDiv.textContent = message.text;

            // Add appropriate class based on the sender
            if (message.sender === 'user') {
                messageDiv.classList.add('user-message');
            } else {
                messageDiv.classList.add('bot-message');
            }

            messagesDiv.appendChild(messageDiv);
        });

        // Scroll to the bottom of the message container to show the latest message
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (error) {
        console.error("Error loading messages:", error);
    }
}

/**
 * Sends a user's message to the server and updates the UI accordingly.
 * This function:
 *  - Appends the user's message immediately to the chat.
 *  - Clears the input box after sending.
 *  - Appends a placeholder message ("...") for the bot.
 *  - Sends the message to the server and then loads the updated messages.
 */
async function sendMessage() {
    // Get the input box element and extract the text
    const messageBox = document.getElementById('message-box');
    const messageText = messageBox.value.trim();

    // Do not proceed if the message is empty
    if (messageText === '') return;

    // Display user's message immediately in the chat
    appendMessage(messageText, 'user');

    // Clear the input field right after sending the message
    messageBox.value = '';

    // Display a placeholder response ("...") to indicate that the bot is generating a response
    appendMessage("...", "bot");

    try {
        // Send the user's message to the server using a POST request
        await fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: messageText })
        });

        // Load updated messages from the server to replace the placeholder
        loadMessages();
    } catch (error) {
        console.error("Error sending message:", error);
        // Update the placeholder with an error message in case of failure
        updateLastBotMessage("An error occurred while processing your request. Please try again.");
    }
}

/**
 * Appends a new message to the messages container in the UI.
 * This function adds the message to the chat and scrolls to the latest message.
 *
 * @param {string} text - The message text to be added.
 * @param {string} sender - The sender of the message ('user' or 'bot').
 */
function appendMessage(text, sender) {
    // Get the messages container from the DOM
    const messagesDiv = document.getElementById('messages');
    
    // Create a new message div
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message'; // Base class for styling
    messageDiv.textContent = text; // Set the text content of the message

    // Add additional class based on the sender type for styling
    if (sender === 'user') {
        messageDiv.classList.add('user-message');
    } else {
        messageDiv.classList.add('bot-message');
    }

    // Append the message to the container
    messagesDiv.appendChild(messageDiv);

    // Scroll to the bottom of the container to ensure the latest message is visible
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/**
 * Updates the last bot message in the UI with new text.
 * This is used to replace the placeholder ("...") once the actual response is available.
 *
 * @param {string} newText - The new text to replace the placeholder.
 */
function updateLastBotMessage(newText) {
    // Get all bot messages from the DOM
    const messagesDiv = document.getElementById('messages');
    const botMessages = messagesDiv.getElementsByClassName('bot-message');

    // Update the content of the last bot message
    if (botMessages.length > 0) {
        botMessages[botMessages.length - 1].textContent = newText;
    }
}

// Event listener for the "Send" button click event
document.getElementById('send-button').addEventListener('click', sendMessage);

// Event listener for the "Enter" key in the message input box
document.getElementById('message-box').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// Load messages periodically every 2 seconds to keep the chat updated
setInterval(loadMessages, 2000);

// Initial load of messages when the page is first loaded
loadMessages();
