/**
 * Chat interface functionality
 */

let cryDetails = null;

// Load data on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadCryDetails();
    await loadChatHistory();

    // Hide example prompts after first message
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages.children.length > 0) {
        document.getElementById('examplePrompts').style.display = 'none';
    }
});

// Load cry details
async function loadCryDetails() {
    try {
        const response = await fetch(`${window.ROOT_PATH}/api/cries/${cryId}`);
        if (!response.ok) throw new Error('Failed to load cry details');

        cryDetails = await response.json();

        // Render summary
        const summaryEl = document.getElementById('crySummary');

        // Check if photo exists
        const photoHtml = cryDetails.photo_file_path ? `
            <div style="margin-top: 15px;">
                <img src="${window.ROOT_PATH}/api/cries/${cryId}/photo" alt="Baby photo" style="max-width: 300px; max-height: 300px; border-radius: 8px; border: 2px solid #ddd; cursor: pointer;" onclick="window.open('${window.ROOT_PATH}/api/cries/${cryId}/photo', '_blank')">
            </div>
        ` : '';

        summaryEl.innerHTML = `
            <h3>Cry Details</h3>
            <div class="cry-details">
                <div class="detail-item">
                    <div class="detail-label">Reason:</div>
                    <div class="detail-value">
                        ${cryDetails.reason || 'Not labeled'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Solution:</div>
                    <div class="detail-value">
                        ${cryDetails.solution || 'Not recorded'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Time:</div>
                    <div class="detail-value">${cryDetails.recorded_at_formatted}</div>
                </div>
            </div>
            ${cryDetails.notes ? `<div style="margin-top: 15px;"><strong>Notes:</strong> ${cryDetails.notes}</div>` : ''}
            ${photoHtml}
        `;
    } catch (error) {
        console.error('Failed to load cry details:', error);
        showNotification('Failed to load cry details', 'error');
    }
}

// Load chat history
async function loadChatHistory() {
    try {
        const response = await fetch(`${window.ROOT_PATH}/api/chat/${cryId}/history`);
        if (!response.ok) throw new Error('Failed to load chat history');

        const messages = await response.json();

        const messagesEl = document.getElementById('chatMessages');
        messagesEl.innerHTML = '';

        messages.forEach(msg => {
            appendMessage(msg.sender, msg.message_text, msg.timestamp, false);
        });

        // Scroll to bottom
        scrollToBottom();
    } catch (error) {
        console.error('Failed to load chat history:', error);
        showNotification('Failed to load chat history', 'error');
    }
}

// Example prompt click handlers
document.querySelectorAll('.example-prompt').forEach(button => {
    button.addEventListener('click', () => {
        const prompt = button.dataset.prompt;
        document.getElementById('messageInput').value = prompt;
        document.getElementById('messageInput').focus();
    });
});

// Chat form submit handler
document.getElementById('chatForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message) return;

    // Hide example prompts after first message
    document.getElementById('examplePrompts').style.display = 'none';

    // Append user message immediately
    appendMessage('user', message, new Date().toISOString(), true);

    // Clear input
    input.value = '';

    // Disable form while processing
    const submitBtn = document.querySelector('.btn-send');
    submitBtn.disabled = true;
    input.disabled = true;

    // Show typing indicator
    document.getElementById('typingIndicator').style.display = 'flex';

    try {
        const response = await fetch(`${window.ROOT_PATH}/api/chat/${cryId}/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send message');
        }

        const result = await response.json();

        // Hide typing indicator
        document.getElementById('typingIndicator').style.display = 'none';

        // Append bot response
        appendMessage('bot', result.bot_response, result.timestamp, true);

    } catch (error) {
        console.error('Failed to send message:', error);
        showNotification('Failed to send message: ' + error.message, 'error');

        // Hide typing indicator
        document.getElementById('typingIndicator').style.display = 'none';
    } finally {
        // Re-enable form
        submitBtn.disabled = false;
        input.disabled = false;
        input.focus();
    }
});

// Append message to chat
function appendMessage(sender, text, timestamp, scroll = true) {
    const messagesEl = document.getElementById('chatMessages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;

    const time = new Date(timestamp);
    const timeStr = time.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });

    messageDiv.innerHTML = `
        <div class="message-bubble">
            ${text}
            <div class="message-time">${timeStr}</div>
        </div>
    `;

    messagesEl.appendChild(messageDiv);

    if (scroll) {
        scrollToBottom();
    }
}

// Scroll to bottom of chat
function scrollToBottom() {
    const messagesEl = document.getElementById('chatMessages');
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// Handle Enter key in textarea (Shift+Enter for new line, Enter to send)
document.getElementById('messageInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        document.getElementById('chatForm').dispatchEvent(new Event('submit'));
    }
});
