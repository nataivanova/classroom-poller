from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os

# -------------------------
# Configuration
# -------------------------
ADMIN_PIN = "1793"   

# -------------------------
# Global state
# -------------------------
poll_open = False
session_closed = False

options = ["A", "B", "C", "D", "E"]
counts = {k: 0 for k in options}
votes = {}   # voter_id -> letter


class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/state":
            self.respond({
                "open": poll_open,
                "session_closed": session_closed
            })

        elif self.path == "/options":
            self.respond({"options": options})

        elif self.path == "/results":
            self.respond({
                "open": poll_open,
                "session_closed": session_closed,
                "options": options,
                "counts": counts
            })

        else:
            super().do_GET()

    def do_POST(self):
        global poll_open, session_closed, options, counts, votes

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""

        payload = None
        if raw:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                payload = None

        # ---------- admin auth ----------
        if self.path == "/admin_auth":
            if payload and payload.get("pin") == ADMIN_PIN:
                self.respond({"ok": True})
            else:
                self.respond({"ok": False})

        # ---------- admin: set options ----------
        elif self.path == "/set_options":
            if payload and payload.get("options") in (
                ["A", "B", "C"],
                ["A", "B", "C", "D"],
                ["A", "B", "C", "D", "E"]
            ):
                options = payload["options"]
                counts = {k: 0 for k in options}
                votes = {}
                poll_open = False
                session_closed = False
                self.respond({"ok": True})
            else:
                self.respond({"ok": False})

        # ---------- admin: open poll ----------
        elif self.path == "/open":
            poll_open = True
            session_closed = False
            counts = {k: 0 for k in options}
            votes = {}
            self.respond({"ok": True})

        # ---------- admin: close poll (show results) ----------
        elif self.path == "/close":
            poll_open = False
            self.respond({"ok": True})

        # ---------- admin: end session ----------
        elif self.path == "/end_session":
            poll_open = False
            session_closed = True
            self.respond({"ok": True})

        # ---------- student: vote ----------
        elif self.path == "/vote":
            if not payload:
                self.respond({"ok": False})
                return

            letter = payload.get("letter")

            if not poll_open or letter not in options:
                self.respond({"ok": False})
                return

            # one vote per browser session
            voter_id = self.client_address[0] + ":" + self.headers.get("User-Agent", "")

            if voter_id in votes:
                old = votes[voter_id]
                if old in counts:
                    counts[old] -= 1

            votes[voter_id] = letter
            counts[letter] += 1

            self.respond({"ok": True})

        else:
            self.send_error(404)

    def respond(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Poll server running on 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
