from flask import Flask, request
import requests
import datetime

app = Flask(__name__)

VERIFY_TOKEN = "xTE0hXgE"

# =========================
# SIMPLE MEMORY STORAGE (TEMP)
# =========================
CONVERSATIONS = {}

# =========================
# SEND DATA TO ODOO MODULE
# =========================
def send_to_odoo_module(phone, message, status="received"):
    url = "https://erpbox-sols-finnettrust.odoo.com/whatsapp/incoming"

    payload = {
        "phone": phone,
        "message": message,
        "status": status
    }

    try:
        res = requests.post(url, json=payload)
        print("✅ Odoo Response:", res.text)
    except Exception as e:
        print("❌ Odoo Error:", e)


# =========================
# VERIFY WEBHOOK
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
# RECEIVE WEBHOOK EVENTS
# =========================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Incoming:", data)

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # =========================
                # HANDLE STATUS UPDATES
                # =========================
                if "statuses" in value:
                    for s in value["statuses"]:
                        send_to_odoo_module(
                            s.get("recipient_id"),
                            "STATUS UPDATE",
                            s.get("status")  # sent / delivered / read
                        )
                    continue

                # =========================
                # HANDLE USER MESSAGES
                # =========================
                if "messages" not in value:
                    print("Skipping non-message event")
                    continue

                for message in value["messages"]:
                    if message.get("type") != "text":
                        continue

                    sender = message.get("from")
                    text = message.get("text", {}).get("body")

                    print(f"{sender}: {text}")

                    process_message(sender, text)

    except Exception as e:
        print("Webhook Error:", e)

    return "OK", 200


# =========================
# CRM LOGIC ENGINE
# =========================
def process_message(phone, text):
    time_now = datetime.datetime.now().isoformat()

    # STORE CONVERSATION (LOCAL TEMP)
    if phone not in CONVERSATIONS:
        CONVERSATIONS[phone] = []

    CONVERSATIONS[phone].append({
        "message": text,
        "time": time_now
    })

    print("📌 Stored conversation:", CONVERSATIONS[phone])

    # SEND TO ODOO
    send_to_odoo_module(phone, text, "received")

    # =========================
    # LEAD TRIGGER LOGIC
    # =========================
    trigger_words = ["price", "cost", "interested", "buy", "service"]

    if any(word in text.lower() for word in trigger_words):
        create_lead(phone, text)


# =========================
# CREATE LEAD (OPTIONAL FALLBACK)
# =========================
def create_lead(phone, message):
    print("🚀 Creating lead for:", phone)

    url = "https://erpbox-sols-finnettrust.odoo.com/mail/create"

    payload = {
        "phone": phone,
        "message": message
    }

    try:
        res = requests.post(url, json=payload)
        print("CRM Response:", res.text)
    except Exception as e:
        print("CRM Error:", e)


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
