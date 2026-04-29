from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN = "xTE0hXgE"

# store conversations locally (simple CRM inbox)
conversations = []


@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Invalid token", 403


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Incoming:", data)

    try:
        entry = data.get("entry", [])

        for e in entry:
            changes = e.get("changes", [])

            for change in changes:
                value = change.get("value", {})

                # =========================
                # HANDLE ONLY REAL MESSAGES
                # =========================
                if "messages" not in value:
                    print("Skipping non-message event")
                    continue

                for msg in value["messages"]:

                    if msg.get("type") != "text":
                        continue

                    phone = msg.get("from")
                    text = msg.get("text", {}).get("body")

                    print(f"{phone}: {text}")

                    # store locally (mini CRM inbox)
                    conversations.append({
                        "phone": phone,
                        "message": text,
                        "time": datetime.utcnow().isoformat()
                    })

                    print("Stored conversation:", conversations)

                    # SEND TO ODOO MODULE (NEW WAY)
                    send_to_odoo_module(phone, text)

    except Exception as e:
        print("Webhook error:", e)

    return "OK", 200


def send_to_odoo_module(phone, message):
    try:
        url = "https://erpbox-sols-finnettrust.odoo.com/whatsapp/incoming"

        payload = {
            "phone": phone,
            "message": message,
            "status": "received"
        }

        r = requests.post(url, json=payload)
        print("Odoo module response:", r.text)

    except Exception as e:
        print("Odoo send error:", e)


if __name__ == "__main__":
    app.run()
