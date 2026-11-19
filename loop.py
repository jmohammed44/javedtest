import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

counter = 0

def background_worker():
    global counter
    while True:
        counter += 1
        print(f"Tick: {counter}", flush=True)
        time.sleep(5)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"OK - count={counter}\n".encode())

    def log_message(self, format, *args):
        return  # keep stdout clean

if __name__ == "__main__":
    threading.Thread(target=background_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()