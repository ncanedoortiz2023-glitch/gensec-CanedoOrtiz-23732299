document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const sendBtn = document.getElementById("send-btn");
    const clearBtn = document.getElementById("clear-btn");

    // In-memory conversation history: [{ role: "user" | "assistant", content: string }]
    // Stored in browser memory only; refreshing starts a fresh conversation
    let conversationHistory = [];

    // Limit previous messages sent to backend to prevent oversized requests
    const MAX_HISTORY_MESSAGES = 10;

    /**
     * Appends a message bubble to the chat container.
     * @param {"user" | "assistant"} role
     * @param {string} text
     */
    function appendMessage(role, text) {
        const messageEl = document.createElement("div");
        messageEl.className = `message ${role}`;

        const bubbleEl = document.createElement("div");
        bubbleEl.className = "message-bubble";
        bubbleEl.textContent = text;

        messageEl.appendChild(bubbleEl);
        chatMessages.appendChild(messageEl);

        // Scroll to the latest message
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    /**
     * Clears displayed messages and resets in-memory conversation history.
     */
    function handleClearChat() {
        conversationHistory = [];
        chatMessages.innerHTML = "";
        userInput.value = "";
        userInput.focus();
    }

    /**
     * Sends the user's message and conversation history to the Flask API endpoint.
     */
    async function handleSendMessage() {
        const text = userInput.value.trim();
        // Basic validation for empty messages
        if (!text) {
            return;
        }

        // Prevent duplicate submissions while an active request is in flight
        if (sendBtn.disabled) {
            return;
        }

        // 1. Display user message and clear input
        appendMessage("user", text);
        userInput.value = "";

        // 2. Disable Send button while waiting for response
        sendBtn.disabled = true;

        // Slice recent history to limit request size
        const historyPayload = conversationHistory.slice(-MAX_HISTORY_MESSAGES);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    message: text,
                    history: historyPayload,
                }),
            });

            const data = await response.json().catch(() => null);

            if (!response.ok || !data || data.error) {
                const errorMessage = (data && data.error)
                    ? data.error
                    : "Unable to get a response from the AI assistant. Please try again.";
                appendMessage("assistant", errorMessage);
            } else {
                const aiReply = data.response || "No response received.";
                appendMessage("assistant", aiReply);

                // Update in-memory conversation history on success
                conversationHistory.push({ role: "user", content: text });
                conversationHistory.push({ role: "assistant", content: aiReply });
            }
        } catch (error) {
            // Graceful network or unexpected error display without leaking internal details
            appendMessage("assistant", "A connection error occurred. Please check your network and try again.");
        } finally {
            // Re-enable Send button and refocus input
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    // Handle form submit (covers Send button click and standard form submission)
    chatForm.addEventListener("submit", (event) => {
        event.preventDefault();
        handleSendMessage();
    });

    // Support submitting via Enter key
    userInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            handleSendMessage();
        }
    });

    // Handle Clear Chat button
    if (clearBtn) {
        clearBtn.addEventListener("click", handleClearChat);
    }
});
