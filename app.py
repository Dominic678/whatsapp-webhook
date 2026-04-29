from flask import Flask, request
import requests

app = Flask(__name__)

# =========================
# META VERIFY TOKEN
# =========================
VERIFY_TOKEN = "xTE0hXgE"


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
    print("Incoming:", data)

    try:
        entry = data.get("entry", [])

        for e in entry:
            changes = e.get("changes", [])

            for change in changes:
                value = change.get("value", {})

                # =========================
                # ONLY REAL USER MESSAGES
                # =========================
                if "messages" not in value:
                    print("Skipped non-message event")
                    continue

                messages = value["messages"]

                for message in messages:
                    msg_type = message.get("type")

                    # only text messages
                    if msg_type != "text":
                        continue

                    sender = message.get("from")
                    text = message.get("text", {}).get("body")

                    print(f"{sender}: {text}")

                    send_to_odoo(sender, text)

    except Exception as e:
        print("Webhook Error:", e)

    return "OK", 200


# =========================
# SEND TO ODOO CRM
# =========================
def send_to_odoo(phone, message):
    try:
        url = "https://erpbox-sols-finnettrust.odoo.com/jsonrpc"

        db = "erpbox-sols-finnettrust"
        username = "YOUR_ODOO_EMAIL"
        password = "YOUR_ODOO_PASSWORD_OR_API_KEY"

        headers = {"Content-Type": "application/json"}

        # -------------------------
        # LOGIN
        # -------------------------
        auth_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [db, username, password]
            },
            "id": 1
        }

        res = requests.post(url, json=auth_payload, headers=headers)
        result = res.json().get("result")

        if not result:
            print("❌ Odoo login failed:", res.json())
            return

        uid = result

        # -------------------------
        # CREATE CRM LEAD
        # -------------------------
        lead_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    db, uid, password,
                    "crm.lead", "create",
                    [{
                        "name": f"WhatsApp: {phone}",
                        "description": message
                    }]
                ]
            },
            "id": 2
        }

        create_res = requests.post(url, json=lead_payload, headers=headers)
        print("Odoo Response:", create_res.json())

    except Exception as e:
        print("Odoo Error:", e)


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run()
