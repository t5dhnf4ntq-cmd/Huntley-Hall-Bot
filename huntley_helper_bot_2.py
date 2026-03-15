"""
The Huntley Helper - GroupMe Bot for Lambert Huntley Hall
Powered by Google Gemini (free API).
"""

import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
GROUPME_BOT_ID = os.environ.get("GROUPME_BOT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
BOT_NAME = "The Huntley Helper"

# ─────────────────────────────────────────────
# AI SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
You are "The Huntley Helper," the official AI assistant for Lambert Huntley Hall (also known as Huntley Hall), a college residence hall.

Your role is to assist residents professionally, warmly, and efficiently.

You specialize in two areas:

1. GENERAL RESIDENT QUESTIONS
   - Hall policies, quiet hours, guest policies, amenities, laundry, parking, common areas
   - Community events, RA office hours, move-in/move-out procedures
   - Campus resources and referrals (housing office, facilities, etc.)

2. MAINTENANCE REQUESTS
   - Acknowledge the issue with empathy
   - Remind them to submit a formal request through the housing portal
   - Routine issues: 2-3 business days. Urgent (no heat, flooding, lockout): contact RA or facilities immediately
   - Emergencies (flooding, fire, electrical hazard): call facilities or 911 immediately

TONE & STYLE:
- Professional but warm and approachable
- Concise — GroupMe messages should be short and easy to read
- Use first names if provided
- Never be dismissive or robotic
- Sign off every message with: — The Huntley Helper 🏠

LIMITATIONS:
- If you don't know the answer, say so honestly and direct them to contact their RA or the housing office
- Do not make promises about maintenance timelines you can't guarantee
- Do not share personal information about other residents
- If a message seems like an emergency, always prioritize safety first

Keep responses under 200 words since this is a group chat.
"""

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def send_groupme_message(text):
    """Post a message to the GroupMe chat as the bot."""
    url = "https://api.groupme.com/v3/bots/post"
    payload = {"bot_id": GROUPME_BOT_ID, "text": text}
    response = requests.post(url, json=payload)
    print(f"[GROUPME STATUS] {response.status_code}")
    return response.status_code


def generate_ai_response(user_message, sender_name):
    """Send the message to Gemini and get a professional response."""
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )

    user_prompt = (
        f"A resident named {sender_name} sent this message in the Huntley Hall group chat:\n\n"
        f"\"{user_message}\"\n\nPlease respond appropriately."
    )

    response = model.generate_content(user_prompt)
    return response.text


def should_respond(message_data):
    """Decide whether the bot should respond to a given message."""
    sender = message_data.get("name", "")
    text = message_data.get("text", "").lower()
    msg_type = message_data.get("sender_type", "")

    # Don't respond to our own messages or system messages
    if sender == BOT_NAME or msg_type == "bot":
        return False

    trigger_words = [
        "help", "question", "maintenance", "broken", "fix", "repair",
        "noise", "quiet", "hours", "guest", "parking", "laundry",
        "event", "meeting", "lockout", "key", "heat", "ac", "hot",
        "cold", "water", "leak", "wifi", "internet", "when", "where",
        "how", "what", "who", "is there", "can i", "are we", "do we",
        "i need", "please", "request", "issue", "problem", "hello",
        "hi huntley", "hey huntley", "@huntley"
    ]

    return any(word in text for word in trigger_words)


# ─────────────────────────────────────────────
# WEBHOOK ENDPOINT
# ─────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive incoming GroupMe messages and respond intelligently."""
    data = request.get_json()

    if not data:
        return jsonify({"status": "no data"}), 400

    sender_name = data.get("name", "Resident")
    message_text = data.get("text", "")

    print(f"[MESSAGE] {sender_name}: {message_text}")
    print(f"[SENDER TYPE] {data.get('sender_type', 'unknown')}")

    if should_respond(data) and message_text.strip():
        try:
            print(f"[GEMINI KEY SET] {'Yes' if GEMINI_API_KEY else 'NO - KEY IS MISSING!'}")
            print(f"[BOT ID SET] {'Yes' if GROUPME_BOT_ID else 'NO - BOT ID IS MISSING!'}")
            ai_response = generate_ai_response(message_text, sender_name)
            print(f"[RESPONSE] {ai_response[:100]}...")
            send_groupme_message(ai_response)
        except Exception as e:
            print(f"[ERROR - FULL DETAILS] {type(e).__name__}: {str(e)}")
            fallback = (
                "Hi! I'm having a little trouble right now. "
                "Please contact your RA directly for assistance. — The Huntley Helper 🏠"
            )
            send_groupme_message(fallback)

    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return "The Huntley Helper is online! 🏠", 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "bot": "The Huntley Helper",
        "gemini_key_set": bool(GEMINI_API_KEY),
        "bot_id_set": bool(GROUPME_BOT_ID)
    }), 200


# ─────────────────────────────────────────────
# RUN THE APP
# ─────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
