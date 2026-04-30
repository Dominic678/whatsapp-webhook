from flask import Flask, request
import requests
import datetime

app = Flask(__name__)

VERIFY_TOKEN = "xTE0hXgE"

# =========================
# SIMPLE MEMORY STORAGE
# =========================
CONVERSATIONS = {}

# =========================
# HOME ROUTE (Render health check)
# =========================
@app.route('/')
def home():
    return "Webhook is LIVE", 200


# =========================
# VERIFY WEBHOOK (GET)
# =========================
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Invalid token", 403


# =========================
# RECEIVE MESSAGES (POST)
# =========================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    print("📩 Incoming Webhook:", data)

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if "messages" not in value:
                    print("⚠ Skipping non-message event")
                    continue

                for message in value["messages"]:
                    if message.get("type") != "text":
                        continue

                    sender = message.get("from")
                    text = message.get("text", {}).get("body")

                    print(f"💬 Message from {sender}: {text}")

                    process_message(sender, text)

    except Exception as e:
        print("❌ Webhook processing error:", str(e))

    return "OK", 200


# =========================
# CRM LOGIC ENGINE
# =========================
def process_message(phone, text):
    time_now = datetime.datetime.now().isoformat()

    if phone not in CONVERSATIONS:
        CONVERSATIONS[phone] = []

    CONVERSATIONS[phone].append({
        "message": text,
        "time": time_now
    })

    print(f"🧠 Stored conversation for {phone}: {CONVERSATIONS[phone]}")

    trigger_words = ["price", "cost", "interested", "buy", "service"]

    if text and any(word in text.lower() for word in trigger_words):
        create_lead(phone, text)


# =========================
# CREATE LEAD (FIXED SAFE VERSION)
# =========================
def create_lead(phone, message):
    print(f"🚀 Creating lead for {phone}")

    url = "https://erpbox-sols-finnettrust.odoo.com/mail/create"

    payload = {
        "phone": phone,
        "message": message
    }

    try:
        res = requests.post(url, json=payload, timeout=10)

        print("📡 CRM Status Code:", res.status_code)

        # Try JSON first (safe parsing)
        try:
            response_data = res.json()
            print("📦 CRM JSON Response:", response_data)

        except Exception:
            # Avoid dumping full HTML pages into logs
            print("⚠ CRM returned non-JSON response (truncated):")
            print(res.text[:300])

        if res.status_code != 200:
            print("❌ CRM request failed")

    except requests.exceptions.RequestException as e:
        print("❌ CRM Connection Error:", str(e))


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

