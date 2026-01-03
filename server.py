from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import uuid
import os

# --------------------
# Global poll state
# --------------------

poll_open = False

# Default option set: A–E
options = ["A", "B", "C", "D", "E"]

counts = {k: 0 for k in options}
votes = {}   # voter_id -> letter


class Handler(SimpleHTTPRequestHandler):

    # --------------------
    # CORS / preflight
    # --------------------
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # --------------------
    # Cookie helpers
    # --------------------
    def get_voter_id(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("voter_id="):
                return part.split("=", 1)[1]
        return None

    def send_voter_cookie(self, voter_id):
        self.send_header(
            "Set-Cookie",
            f"voter_id={voter_id}; Path=/; SameSite=Lax"
        )

    # --------------------
    # GET handlers
    # --------------------
    def do_GET(self):
        if self.path == "/state":
            self.respond({"open": poll_open})

        elif self.path == "/options":
            self.respond({"options": options})

        elif self.path == "/results":
            self.respond({
                "open": poll_open,
                "options": options,
                "counts": counts
            })

        else:
            # static files: admin.html, vote.html, index.html
            super().do_GET()

    # --------------------
    # POST handlers
    # --------------------
    def do_POST(self):
        global poll_open, options, counts, votes

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

        # ---- admin: set options ----
        if self.path == "/set_options":
            if payload and payload.get("options") in (
                ["A", "B", "C"],
                ["A", "B", "C", "D"],
                ["A", "B", "C", "D", "E"]
            ):
                options = payload["options"]
                counts = {k: 0 for k in options}
                votes = {}
                poll_open = False
                self.respond({"ok": True, "options": options})
            else:
                self.respond({"ok": False})

        # ---- admin: open poll ----
        elif self.path == "/open":
            poll_open = True
            counts = {k: 0 for k in options}
            votes = {}
            self.respond({"status": "open"})

        # ---- admin: close poll ----
        elif self.path == "/close":
            poll_open = False
            self.respond({
                "status": "closed",
                "options": options,
                "counts": counts
            })

        # ---- student: vote ----
        elif self.path == "/vote":
            letter = payload.get("letter") if payload else None

            if poll_open and letter in options:
                # remove previous vote
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
            self.send_error(404, "Not found")

    # --------------------
    # Response helper
    # --------------------
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


# --------------------
# Server entry point
# --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Poll server running on 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
