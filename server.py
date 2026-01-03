from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import uuid
import os

poll_open = False
options = ["A", "B", "C", "D", "E"]
counts = {k: 0 for k in options}
votes = {}   # voter_id -> letter

class Handler(SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---------- helpers ----------
    def get_voter_id(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            if part.strip().startswith("voter_id="):
                return part.strip().split("=", 1)[1]
        return None

    def send_voter_cookie(self, voter_id):
        self.send_header(
            "Set-Cookie",
            f"voter_id={voter_id}; Path=/; SameSite=Lax"
        )

    # ---------- GET ----------
    def do_GET(self):
        if self.path == "/state":
            self.respond({"open": poll_open})

        elif self.path == "/results":
            self.respond({
                "open": poll_open,
                "options": options,
                "counts": counts
            })

        elif self.path == "/options":
            self.respond({"options": options})

        else:
            super().do_GET()

    # ---------- POST ----------
    def do_POST(self):
        global poll_open, counts, votes, options

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b""

        payload = None
        if raw:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                payload = None

        voter_id = self.get_voter_id()
        new_voter = False
        if not voter_id:
            voter_id = str(uuid.uuid4())
            new_voter = True

        if self.path == "/set_options":
            if payload and payload.get("options") in (["A","B","C","D"], ["A","B","C","D","E"]):
                options = payload["options"]
                counts = {k: 0 for k in options}
                votes = {}
                poll_open = False
                self.respond({"ok": True, "options": options})
            else:
                self.respond({"ok": False})

        elif self.path == "/open":
            poll_open = True
            counts = {k: 0 for k in options}
            votes = {}
            self.respond({"status": "open"})

        elif self.path == "/close":
            poll_open = False
            self.respond({
                "status": "closed",
                "options": options,
                "counts": counts
            })

        elif self.path == "/vote":
            letter = payload.get("letter") if payload else None
            if poll_open and letter in options:
                if voter_id in votes:
                    old = votes[voter_id]
                    if old in counts:
                        counts[old] -= 1
                votes[voter_id] = letter
                counts[letter] += 1
                self.respond({"ok": True}, voter_id, new_voter)
            else:
                self.respond({"ok": False}, voter_id, new_voter)

        else:
            self.send_error(404)

    # ---------- response ----------
    def respond(self, obj, voter_id=None, set_cookie=False):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if set_cookie and voter_id:
            self.send_voter_cookie(voter_id)
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Poll server running on 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
