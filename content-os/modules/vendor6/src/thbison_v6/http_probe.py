"""Loopback health probe using stdlib only."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class _H(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        if self.path == "/healthz":
            body = json.dumps({"status": "ok"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def serve_background() -> tuple[HTTPServer, Thread]:
    httpd = HTTPServer(("127.0.0.1", 0), _H)
    t = Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, t
