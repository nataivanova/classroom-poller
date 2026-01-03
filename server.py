from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os

poll_open = False

# default option set
options = ["A", "B", "C", "D", "E"]

counts = {k: 0 for k in options}
votes = {}   # device_id -> letter


class Handler(SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---------------- GET ----------------
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
            super().do_GET()

    # ---------------- POST ----------------
    def do_POST(self):
        global poll_open, options, counts, votes

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""

        payload = None
        if raw:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                payload = None

        # ---- admin: set options ----
        if self.path == "/set_options":
            if payload and payload.get("options") in (
                ["A","B","C"],
                ["A","B","C","D"],
                ["A","B","C","D","E"]
            ):
                options = payload["options"]
                counts = {k: 0 for k in options}
                votes = {}
                poll_open = False
                self.respond({"ok": True, "options": options})
            else:
                self.respond({"ok": False})

        # ---- admin: open ----
        elif self.path == "/open":
            poll_open = True
            counts = {k: 0 for k in options}
            votes = {}
            self.respond({"status": "open"})

        # ---- admin: close ----
        elif self.path == "/close":
            poll_open = False
            self.respond({"status": "closed"})

        # ---- student: vote ----
        elif self.path == "/vote":
            if not payload:
                self.respond({"ok": False})
                return

            letter = payload.get("letter")
            device_id = payload.get("device_id")

            if not poll_open or letter not in options or not device_id:
                self.respond({"ok": False})
                return

            # remove previous vote
            if device_id in votes:
                old = votes[device_id]
                if old in counts:
                    counts[old] -= 1

            votes[device_id] = letter
            counts[letter] += 1

            self.respond({"ok": True})

        else:
            self.send_error(404)

    # ---------------- helper ----------------
    def respond(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Poll server running on 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
