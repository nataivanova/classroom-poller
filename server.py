from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import time

# -------------------------
# Configuration
# -------------------------
ADMIN_PIN = "4312"   # CHANGE THIS

# -------------------------
# Global state
# -------------------------
poll_open = False
poll_started = False          # False until /open has been used at least once
session_closed = False
session_closed_at = None      # unix seconds when END SESSION was pressed

options = ["A", "B", "C", "D", "E"]
counts = {k: 0 for k in options}
votes = {}                    # voter_id -> letter


class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/state":
            self.respond({
                "open": poll_open,
                "poll_started": poll_started,
                "session_closed": session_closed,
                "session_closed_at": session_closed_at
            })

        elif self.path == "/options":
            self.respond({"options": options})

        elif self.path == "/results":
            self.respond({
                "open": poll_open,
                "poll_started": poll_started,
                "session_closed": session_closed,
                "session_closed_at": session_closed_at,
                "options": options,
                "counts": counts
            })

        else:
            super().do_GET()

    def do_POST(self):
        global poll_open, poll_started, session_closed, session_closed_at, options, counts, votes

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
                # Do NOT force poll_started True here; only /open means "started"
                poll_started = False

                session_closed = False
                session_closed_at = None

                self.respond({"ok": True})
            else:
                self.respond({"ok": False})

        # ---------- admin: open poll ----------
        elif self.path == "/open":
            poll_open = True
            poll_started = True

            counts = {k: 0 for k in options}
            votes = {}

            session_closed = False
            session_closed_at = None

            self.respond({"ok": True})

        # ---------- admin: close poll (show results) ----------
        elif self.path == "/close":
            poll_open = False
            self.respond({"ok": True})

        # ---------- admin: end session ----------
        elif self.path == "/end_session":
            poll_open = False
            session_closed = True
            session_closed_at = time.time()
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

            # best-effort: one vote per (IP + UA)
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

    from socketserver import ThreadingMixIn

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True
        request_queue_size = 100
        allow_reuse_address = True
        

    ThreadedHTTPServer(("0.0.0.0", port), Handler).serve_forever()
