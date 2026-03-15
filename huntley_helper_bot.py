"""
The Huntley Helper - GroupMe Bot for Lambert Huntley Hall
----------------------------------------------------------
A professional AI-powered bot that responds to resident questions
and maintenance requests in the Huntley Hall GroupMe chat.

SETUP INSTRUCTIONS:
1. Go to https://dev.groupme.com and log in
2. Click "Bots" → "Create Bot"
3. Name it: The Huntley Helper
4. Set Callback URL to your deployed server URL + /webhook
   (e.g., https://your-app.onrender.com/webhook)
5. Copy your Bot ID and paste it below
6. Get your Anthropic API key from https://console.anthropic.com
7. Deploy to Render.com (free) — see README below
"""

import os
import requests
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION — Fill these in before deploying
# ─────────────────────────────────────────────
GROUPME_BOT_ID = os.environ.get("GROUPME_BOT_ID", "YOUR_BOT_ID_HERE")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY_HERE")
BOT_NAME = "The Huntley Helper"  # So the bot doesn't reply to itself

# ─────────────────────────────────────────────
# AI SYSTEM PROMPT — Defines the bot's behavior
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
   - Remind them to submit a formal request at: https://www.myhousingportal.com (they should replace this with their actual portal)
   - Provide estimated response times: routine = 2-3 business days, urgent (no heat, flooding, lockout) = contact RA or facilities immediately
   - For emergencies (flooding, fire, electrical hazard), direct them to call facilities or 911 immediately

TONE & STYLE:
- Professional but warm and approachable
- Concise — GroupMe messages should be short and easy to read
- Use first names if provided
- Never be dismissive or robotic
- Sign off every message with: — The Huntley Helper 🏠

LIMITATIONS:
- If you don't know the answer, say so honestly and direct them to contact their RA or the housing office directly
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
    payload = {
        "bot_id": GROUPME_BOT_ID,
        "text": text
    }
    response = requests.post(url, json=payload)
    return response.status_code


def generate_ai_response(user_message, sender_name):
    """Send the message to Claude and get a professional response."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_prompt = f"A resident named {sender_name} sent this message in the Huntley Hall group chat:\n\n\"{user_message}\"\n\nPlease respond appropriately."

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    return message.content[0].text


def should_respond(message_data):
    """
    Decide whether the bot should respond to a given message.
    - Skip messages sent by the bot itself
    - Skip system messages
    - Only respond to messages that seem like questions or requests
    """
    sender = message_data.get("name", "")
    text = message_data.get("text", "").lower()
    msg_type = message_data.get("sender_type", "")

    # Don't respond to our own messages or system messages
    if sender == BOT_NAME or msg_type == "bot":
        return False

    # Trigger words — respond to messages that look like questions or requests
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
# WEBHOOK ENDPOINT — GroupMe sends messages here
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

    # Only respond if the message warrants it
    if should_respond(data) and message_text.strip():
        try:
            ai_response = generate_ai_response(message_text, sender_name)
            send_groupme_message(ai_response)
            print(f"[RESPONSE SENT] {ai_response[:80]}...")
        except Exception as e:
            print(f"[ERROR] {e}")
            # Fallback message if AI fails
            fallback = (
                "Hi! I'm having a little trouble right now. "
                "Please contact your RA directly for assistance. — The Huntley Helper 🏠"
            )
            send_groupme_message(fallback)

    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return "The Huntley Helper is online! 🏠", 200


# ─────────────────────────────────────────────
# RUN THE APP
# ─────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
