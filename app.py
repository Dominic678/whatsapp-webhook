from flask import Flask, request
import requests
import datetime

app = Flask(__name__)

VERIFY_TOKEN = "xTE0hXgE"

# =========================
# MEMORY STORE (temporary)
# =========================
CONVERSATIONS = {}

# =========================
# ODOO CONFIG (CHANGE THESE)
# =========================
ODOO_URL = "https://erpbox-sols-finnettrust.odoo.com"
ODOO_DB = "YOUR_DB_NAME"
ODOO_EMAIL = "YOUR_EMAIL"
ODOO_PASSWORD = "YOUR_PASSWORD"


# =========================
# HOME ROUTE (Render check)
# =========================
@app.route('/')
def home():
    return "Webhook is LIVE", 200


# =========================
# VERIFY WEBHOOK (WhatsApp)
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
    print("📩 Incoming:", data)

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if "messages" not in value:
                    continue

                for message in value["messages"]:
                    if message.get("type") != "text":
                        continue

                    phone = message.get("from")
                    text = message.get("text", {}).get("body")

                    print(f"💬 {phone}: {text}")

                    process_message(phone, text)

    except Exception as e:
        print("❌ Webhook error:", str(e))

    return "OK", 200


# =========================
# MESSAGE PROCESSOR
# =========================
def process_message(phone, text):
    time_now = datetime.datetime.now().isoformat()

    if phone not in CONVERSATIONS:
        CONVERSATIONS[phone] = []

    CONVERSATIONS[phone].append({
        "message": text,
        "time": time_now
    })

    print("🧠 Stored:", CONVERSATIONS[phone])

    trigger_words = ["price", "cost", "buy", "interested", "service"]

    if text and any(word in text.lower() for word in trigger_words):
        create_lead(phone, text)


# =========================
# GET ODOO UID (LOGIN)
# =========================
def get_uid():
    url = f"{ODOO_URL}/jsonrpc"

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "common",
            "method": "login",
            "args": [
                ODOO_DB,
                ODOO_EMAIL,
                ODOO_PASSWORD
            ]
        },
        "id": 1
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.json().get("result")

    except Exception as e:
        print("❌ Login error:", str(e))
        return None


# =========================
# CREATE LEAD IN ODOO
# =========================
def create_lead(phone, message):
    print(f"🚀 Creating Odoo lead for {phone}")

    uid = get_uid()

    if not uid:
        print("❌ Cannot create lead (no UID)")
        return

    url = f"{ODOO_URL}/jsonrpc"

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "crm.lead",
                "create",
                [{
                    "name": f"WhatsApp Lead {phone}",
                    "phone": phone,
                    "description": message
                }]
            ]
        },
        "id": 1
    }

    try:
        res = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print("📡 Status:", res.status_code)

        try:
            print("📦 Response:", res.json())
        except Exception:
            print("⚠ Non-JSON response (truncated):", res.text[:300])

    except Exception as e:
        print("❌ Lead creation error:", str(e))


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
