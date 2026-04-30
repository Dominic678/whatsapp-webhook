from flask import Flask, request
import requests
import datetime

app = Flask(__name__)

VERIFY_TOKEN = "xTE0hXgE"

# =========================
# SEND TO ODOO MODULE
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
        print("Odoo response:", res.text)
    except Exception as e:
        print("Odoo error:", e)


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
# RECEIVE EVENTS (POST)
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
                # HANDLE USER MESSAGES
                # =========================
                if "messages" in value:
                    for msg in value["messages"]:
                        if msg.get("type") != "text":
                            continue

                        phone = msg.get("from")
                        text = msg.get("text", {}).get("body")

                        print(f"{phone}: {text}")

                        # Send to Odoo
                        send_to_odoo_module(phone, text, "received")

                # =========================
                # HANDLE STATUS UPDATES
                # =========================
                if "statuses" in value:
                    for s in value["statuses"]:
                        phone = s.get("recipient_id")
                        status = s.get("status")

                        print(f"STATUS {phone}: {status}")

                        send_to_odoo_module(
                            phone,
                            "STATUS UPDATE",
                            status
                        )

    except Exception as e:
        print("Webhook Error:", e)

    return "OK", 200


# =========================
# ROOT ROUTE (FOR RENDER HEALTH CHECK)
# =========================
@app.route('/')
def home():
    return "WhatsApp Webhook Running ✅", 200


# =========================
# RUN LOCAL ONLY
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
