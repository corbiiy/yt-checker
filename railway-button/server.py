#!/usr/bin/env python3
"""Railway web service "button": starts a check when the page's "Vérifier maintenant"
button asks for one.

POST /check  starts the "Check for new videos" workflow, at most once every COOLDOWN
             seconds, and answers {"started": bool, "at": when the last check was started}.
             The page then waits for a videos.json checked after "at".
GET  /       health check.

GITHUB_TOKEN is a Railway reference to the trigger service's token: ${{trigger.GITHUB_TOKEN}}.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DISPATCH = "https://api.github.com/repos/corbiiy/yt-checker/actions/workflows/check.yml/dispatches"
ORIGINS = {"https://corbiiy.github.io", "http://localhost:8790"}
COOLDOWN = 120  # seconds; a check takes about a minute, so a second press joins the first

lock = threading.Lock()
last = 0.0  # when the last check was started from here


def dispatch() -> None:
    token = "".join(os.environ["GITHUB_TOKEN"].split())  # a pasted token can carry a newline
    req = urllib.request.Request(DISPATCH, data=b'{"ref":"main"}', method="POST", headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "yt-checker-button",
    })
    urllib.request.urlopen(req, timeout=15).close()


class Handler(BaseHTTPRequestHandler):
    def reply(self, code: int, body: dict | None = None) -> None:
        self.send_response(code)
        origin = self.headers.get("Origin")
        if origin in ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST")
            self.send_header("Vary", "Origin")
        self.send_header("Cache-Control", "no-store")
        data = b""
        if body is not None:
            data = json.dumps(body).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.reply(204)

    def do_GET(self) -> None:
        self.reply(200, {"ok": True})

    def do_POST(self) -> None:
        global last
        if self.path != "/check":
            return self.reply(404, {"error": "not_found"})
        origin = self.headers.get("Origin")
        if origin and origin not in ORIGINS:  # other websites can't press it
            return self.reply(403, {"error": "forbidden"})
        with lock:
            now = time.time()
            started = now - last >= COOLDOWN
            if started:
                try:
                    dispatch()
                except Exception as e:  # noqa: BLE001 - any failure means "not started"
                    print(f"could not start a check: {e}", flush=True)
                    return self.reply(502, {"error": "dispatch_failed"})
                last = now
            at = datetime.fromtimestamp(last, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        print(f"check {'started' if started else 'already started'} at {at}", flush=True)
        self.reply(200, {"started": started, "at": at})

    def log_message(self, *args) -> None:
        pass  # do_POST prints one line per press


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"listening on {port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
