from flask import Flask, request
import requests

app = Flask(__name__)

VERIFY_TOKEN = "xTE0hXgE"

@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Invalid token", 403


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Incoming:", data)

    try:
        message = data['entry'][0]['changes'][0]['value']['messages'][0]
        sender = message['from']
        text = message['text']['body']

        print(f"{sender}: {text}")

        send_to_odoo(sender, text)

    except Exception as e:
        print("Error:", e)

    return "OK", 200


def send_to_odoo(phone, message):
    url = "https://erpbox-sols-finnettrust.odoo.com/jsonrpc"

    db = "erpbox-sols-finnettrust"
    username = "YOUR_ODOO_EMAIL"
    password = "YOUR_ODOO_PASSWORD"  # or API key

    headers = {'Content-Type': 'application/json'}

    auth = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "common",
            "method": "login",
            "args": [db, username, password]
        },
        "id": 1
    }

    res = requests.post(url, json=auth, headers=headers)
    uid = res.json()['result']

    payload = {
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

    requests.post(url, json=payload, headers=headers)


if __name__ == "__main__":
    app.run()rewrite all for me correctly 
