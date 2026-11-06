import logging
import os
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Maximum number of previous conversation messages to send to prevent oversized requests
MAX_HISTORY_MESSAGES = 20


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request format. JSON body expected."}), 400

    raw_message = data.get("message")
    if raw_message is None or not isinstance(raw_message, str) or not raw_message.strip():
        return jsonify({"error": "Message cannot be empty."}), 400

    user_message = raw_message.strip()

    # Validate and process optional conversation history
    raw_history = data.get("history", [])
    if not isinstance(raw_history, list):
        return jsonify({"error": "Invalid history format. Array expected."}), 400

    # Limit history to the most recent messages
    trimmed_history = raw_history[-MAX_HISTORY_MESSAGES:]

    api_key = os.environ.get("GOOGLE_API_KEY")
    model_name = os.environ.get("GOOGLE_MODEL")

    if not api_key:
        logger.error("Missing GOOGLE_API_KEY environment variable.")
        return jsonify({"error": "AI service is not configured properly."}), 500

    if not model_name:
        logger.error("Missing GOOGLE_MODEL environment variable.")
        return jsonify({"error": "AI service is not configured properly."}), 500

    # Strip optional google. prefix if present in the environment variable
    if model_name.startswith("google."):
        model_name = model_name[7:]

    # Convert conversation history into the format expected by the Google Gen AI SDK
    contents = []
    for entry in trimmed_history:
        if not isinstance(entry, dict):
            continue

        role = entry.get("role")
        content_text = entry.get("content") or entry.get("text")
        if not isinstance(content_text, str) or not content_text.strip():
            continue

        # Map assistant role to Gemini's expected model role
        gemini_role = "model" if role in ("assistant", "model") else "user"
        contents.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=content_text.strip())],
            )
        )

    # Append the new user message if not already present at the end
    if not contents or contents[-1].role != "user" or contents[-1].parts[0].text != user_message:
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)],
            )
        )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
        )

        reply = response.text if response and response.text else "No response generated."
        return jsonify({"response": reply})
    except Exception as exc:
        logger.error("Failed to generate content via Gemini API: %s", exc)
        return jsonify({"error": "Failed to generate AI response. Please try again later."}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
