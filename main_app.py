import itertools
import os
import string
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# --- Configuration (set these as environment variables in Koyeb) ---
URL_TEMPLATE = os.environ.get("URL_TEMPLATE", "https://{slug}-default-rtdb.firebaseio.com/clients.json")

FIREBASE_BOT_TOKEN = os.environ.get("FIREBASE_BOT_TOKEN", "")
FIREBASE_CHAT_ID = os.environ.get("FIREBASE_CHAT_ID", "")

STATUS_BOT_TOKEN = os.environ.get("STATUS_BOT_TOKEN", "")
STATUS_CHAT_ID = os.environ.get("STATUS_CHAT_ID", "")

CHECK_INTERVAL = int(os.environ.get("STATUS_INTERVAL", "1000"))
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "10"))
REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "0.05"))
MAX_LENGTH = int(os.environ.get("MAX_LENGTH", "0"))  # 0 = unlimited
header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"}

def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[Telegram Error] {exc}")


def is_dropped_response(response: requests.Response) -> bool:
    raw_text = response.text.strip()
    if raw_text.lower() == "null":
        return True

    try:
        data = response.json()
    except ValueError:
        # Not valid JSON; check if raw body is literally 'null'
        return raw_text == "null"

    if data is None:
        return True

    if isinstance(data, dict) and "error" in data:
        err_val = str(data["error"]).lower()
        if "404 not found" in err_val or "deactivated" in err_val:
            return True

    return False


def background_worker():
    alphabet = string.ascii_lowercase
    count = 0
    length = 1

    while MAX_LENGTH == 0 or length <= MAX_LENGTH:
        for combo in itertools.product(alphabet, repeat=length):
            slug = "".join(combo)
            target_url = URL_TEMPLATE.format(slug=slug)
            count += 1

            try:
                resp = requests.get(target_url, headers=header timeout=REQUEST_TIMEOUT)
                if not is_dropped_response(resp):
                    send_telegram_message(
                        FIREBASE_BOT_TOKEN,
                        FIREBASE_CHAT_ID,
                        f"Match found ({slug}):\n{target_url} [HTTP {resp.status_code}]",
                    )
            except requests.RequestException as exc:
                print(f"[Request Error] {target_url} -> {exc}")

            if CHECK_INTERVAL > 0 and count % CHECK_INTERVAL == 0:
                status_msg = (
                    f"Status update: {count} strings checked.\n"
                    f"Current URL: {target_url}"
                )
                send_telegram_message(STATUS_BOT_TOKEN, STATUS_CHAT_ID, status_msg)

            if REQUEST_DELAY > 0:
                time.sleep(REQUEST_DELAY)

        length += 1


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK\n")

    def log_message(self, format, *args):
        return  # keep stdout clean


if __name__ == "__main__":
    threading.Thread(target=background_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 8000))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()
