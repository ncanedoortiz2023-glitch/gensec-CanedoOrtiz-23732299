document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const sendBtn = document.getElementById("send-btn");

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
     * Sends the user's message to the Flask API endpoint and displays the response.
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

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ message: text }),
            });

            const data = await response.json().catch(() => null);

            if (!response.ok || !data || data.error) {
                const errorMessage = (data && data.error)
                    ? data.error
                    : "Unable to get a response from the AI assistant. Please try again.";
                appendMessage("assistant", errorMessage);
            } else {
                appendMessage("assistant", data.response || "No response received.");
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
});
