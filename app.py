from flask import Flask, request, jsonify
import requests
import datetime
import logging

app = Flask(__name__)

# =========================
# CONFIG
# =========================
VERIFY_TOKEN = "xTE0hXgE"

# ODOO STAGING ENDPOINT (IMPORTANT)
ODOO_URL = "https://erpbox-sols-finnettrust-staging-30004233.dev.odoo.com/whatsapp/incoming"

# simple in-memory storage (replace with DB later)
CONVERSATIONS = {}

# =========================
# LOGGING
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =========================
# HEALTH CHECK
# =========================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


# =========================
# WEBHOOK VERIFICATION (META)
# =========================
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    logger.info(f"VERIFY REQUEST: mode={mode}, token={token}")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Invalid token", 403


# =========================
# RECEIVE WHATSAPP MESSAGES
# =========================
@app.route('/webhook', methods=['POST'])
def receive_message():
    data = request.get_json(silent=True)

    logger.info("🔥 WEBHOOK RECEIVED")
    logger.info(data)

    if not data:
        return "No data", 400

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                messages = value.get("messages", [])

                for msg in messages:
                    msg_type = msg.get("type")

                    if msg_type != "text":
                        continue

                    phone = msg.get("from")
                    text = msg.get("text", {}).get("body")

                    logger.info(f"FROM {phone}: {text}")

                    if phone and text:
                        store_message(phone, text)
                        send_to_odoo(phone, text)

    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")

    return "OK", 200


# =========================
# STORE MESSAGE (LOCAL MEMORY)
# =========================
def store_message(phone, text):
    now = datetime.datetime.utcnow().isoformat()

    if phone not in CONVERSATIONS:
        CONVERSATIONS[phone] = []

    CONVERSATIONS[phone].append({
        "message": text,
        "time": now
    })

    logger.info(f"Stored: {phone} -> {text}")


# =========================
# SEND TO ODOO
# =========================
def send_to_odoo(phone, message):
    payload = {
        "phone": phone,
        "message": message
    }

    try:
        res = requests.post(ODOO_URL, json=payload, timeout=10)

        logger.info(f"ODOO RESPONSE: {res.status_code} {res.text}")

    except Exception as e:
        logger.exception(f"Odoo send failed: {e}")


# =========================
# SEND MESSAGE BACK (OPTIONAL)
# =========================
@app.route('/send', methods=['POST'])
def send_message():
    data = request.get_json()

    phone = data.get("phone")
    message = data.get("message")

    logger.info(f"SEND REQUEST -> {phone}: {message}")

    # HERE you would call WhatsApp Cloud API
    # (placeholder for now)

    return jsonify({
        "status": "sent",
        "phone": phone,
        "message": message
    }), 200


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
