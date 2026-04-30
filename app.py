from flask import Flask, request
import requests
import datetime

app = Flask(__name__)

VERIFY_TOKEN = "xTE0hXgE"

# Memory storage (temporary)
CONVERSATIONS = {}


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
# RECEIVE MESSAGES
# =========================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Incoming:", data)

    # Forward full payload (optional logging endpoint)
    send_whatsapp_payload(data)

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # -------------------------
                # HANDLE STATUS UPDATES
                # -------------------------
                if "statuses" in value:
                    for s in value["statuses"]:
                        send_to_odoo_module(
                            phone=s.get("recipient_id"),
                            message="STATUS UPDATE",
                            status=s.get("status")
                        )

                # -------------------------
                # HANDLE MESSAGES
                # -------------------------
                if "messages" not in value:
                    continue

                for message in value["messages"]:
                    if message.get("type") != "text":
                        continue

                    sender = message.get("from")
                    text = message.get("text", {}).get("body")

                    print(f"{sender}: {text}")

                    process_message(sender, text)

                    # Send to Odoo module
                    send_to_odoo_module(sender, text, "received")

    except Exception as e:
        print("Webhook Error:", e)

    return "OK", 200


# =========================
# FORWARD RAW PAYLOAD
# =========================
def send_whatsapp_payload(payload):
    try:
        url = "https://www.finnettrust.com/wa/receive"
        headers = {"Content-Type": "application/json"}
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print("Forward Error:", e)


# =========================
# SEND TO ODOO MODULE
# =========================
def send_to_odoo_module(phone, message, status="received"):
    try:
        url = "https://erpbox-sols-finnettrust.odoo.com/whatsapp/incoming"

        payload = {
            "phone": phone,
            "message": message,
            "status": status
        }

        res = requests.post(url, json=payload)
        print("Odoo module response:", res.text)

    except Exception as e:
        print("Odoo Module Error:", e)


# =========================
# CRM LOGIC
# =========================
def process_message(phone, text):
    time_now = datetime.datetime.now().isoformat()

    if phone not in CONVERSATIONS:
        CONVERSATIONS[phone] = []

    CONVERSATIONS[phone].append({
        "message": text,
        "time": time_now
    })

    print("Stored conversation:", CONVERSATIONS[phone])

    trigger_words = ["price", "cost", "interested", "buy", "service"]

    if any(word in text.lower() for word in trigger_words):
        create_lead(phone, text)


# =========================
# CREATE LEAD
# =========================
def create_lead(phone, message):
    try:
        url = "https://erpbox-sols-finnettrust.odoo.com/mail/create"

        payload = {
            "phone": phone,
            "message": message
        }

        res = requests.post(url, json=payload)
        print("Lead created:", res.text)

    except Exception as e:
        print("Lead Error:", e)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
