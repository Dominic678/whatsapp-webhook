from flask import Flask, request
import requests
import datetime
import logging

app = Flask(__name__)

# =========================
# CONFIG
# =========================
VERIFY_TOKEN = "xTE0hXgE"

# simple in-memory storage (replace with DB later)
CONVERSATIONS = {}

# =========================
# LOGGING (IMPORTANT FOR RENDER)
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =========================
# VERIFY WEBHOOK (GET)
# =========================
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    logger.info(f"Verify request: mode={mode}, token={token}")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Invalid token", 403


# =========================
# SEND TEST ENDPOINT
# =========================
@app.route('/send', methods=['POST'])
def send():
    data = request.get_json()

    phone = data.get("phone")
    message = data.get("message")

    logger.info(f"Sending to {phone}: {message}")

    return {"status": "sent"}, 200


# =========================
# RECEIVE MESSAGES (POST)
# =========================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)

    logger.info("🔥 WEBHOOK HIT")
    logger.info(f"Incoming payload: {data}")

    if not data:
        logger.warning("Empty payload received")
        return "No data", 400

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if "messages" not in value:
                    logger.info("Skipping non-message event")
                    continue

                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                contact_name = (
                    contacts[0].get("profile", {}).get("name", "")
                    if contacts else ""
                )

                for message in messages:
                    msg_type = message.get("type")

                    if msg_type != "text":
                        logger.info(f"Skipping non-text message: {msg_type}")
                        continue

                    sender = message.get("from")
                    text = message.get("text", {}).get("body")

                    logger.info(f"Received from {sender}: {text}")

                    if sender and text:
                        process_message(sender, text, contact_name)

    except Exception as e:
        logger.exception(f"Webhook processing error: {e}")

    return "OK", 200


# =========================
# MESSAGE PROCESSOR
# =========================
def process_message(phone, text, contact_name=""):
    time_now = datetime.datetime.utcnow().isoformat()

    if phone not in CONVERSATIONS:
        CONVERSATIONS[phone] = []

    CONVERSATIONS[phone].append({
        "message": text,
        "time": time_now
    })

    logger.info(
        f"Stored conversation for {contact_name or phone} ({phone}): "
        f"{CONVERSATIONS[phone]}"
    )

    # 🔥 SEND EVERY MESSAGE TO ODOO
    forward_to_odoo(phone, text, contact_name)

    trigger_words = ["price", "cost", "interested", "buy", "service"]

    if any(word in text.lower() for word in trigger_words):
        logger.info(f"Trigger word detected for {phone}")


# =========================
# FORWARD TO ODOO (FIXED)
# =========================
def forward_to_odoo(phone, message, contact_name=""):
    logger.info(f"📤 Forwarding to Odoo: {phone}")

    # ✅ STAGING URL (IMPORTANT FIX)
    url = "https://erpbox-sols-finnettrust-staging-30004233.dev.odoo.com/whatsapp/webhook"

    payload = {
        "phone": phone,
        "message": message,
        "contact_name": contact_name,
    }

    try:
        res = requests.post(url, json=payload, timeout=10)

        # 🔥 IMPORTANT DEBUG LOGS
        logger.info(f"Odoo Status Code: {res.status_code}")
        logger.info(f"Odoo Response: {res.text}")

    except Exception as e:
        logger.exception(f"Odoo forward error: {e}")


# =========================
# HEALTH CHECK
# =========================
@app.route('/health', methods=['GET'])
def health():
    return {"status": "ok"}, 200


# =========================
# RUN (LOCAL ONLY)
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
