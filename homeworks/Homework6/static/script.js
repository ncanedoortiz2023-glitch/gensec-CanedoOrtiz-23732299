document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");

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
     * Sends the current user message and displays the placeholder response.
     */
    function handleSendMessage() {
        const text = userInput.value.trim();
        if (!text) {
            return;
        }

        // 1. Display user message and clear input
        appendMessage("user", text);
        userInput.value = "";
        userInput.focus();

        // 2. Display placeholder assistant response
        setTimeout(() => {
            appendMessage("assistant", "AI responses will be available soon.");
        }, 300);
    }

    // Handle form submit (Send button click or standard form submission)
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
