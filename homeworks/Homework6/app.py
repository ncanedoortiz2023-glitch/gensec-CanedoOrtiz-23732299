import logging
import os
from flask import Flask, jsonify, render_template, request
from google import genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


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

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=user_message,
        )

        reply = response.text if response and response.text else "No response generated."
        return jsonify({"response": reply})
    except Exception as exc:
        logger.error("Failed to generate content via Gemini API: %s", exc)
        return jsonify({"error": "Failed to generate AI response. Please try again later."}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
