from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from kf_pilot.content_os_gateway import EvidenceMappingError, map_knowledge_output

FIXTURE = json.loads(Path(os.environ["KNOWLEDGE_FIXTURE"]).read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def reply(self, status, body):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, {"status": "ok", "data_class": "TEST_ONLY"})
        return self.reply(404, {"code": "NOT_FOUND"})

    def do_POST(self):
        if self.path != "/v1/knowledge/query":
            return self.reply(404, {"code": "NOT_FOUND"})
        if self.headers.get("Authorization") != "Bearer lab-knowledge-token":
            return self.reply(401, {"code": "UNAUTHORIZED"})
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        try:
            bundle = map_knowledge_output(FIXTURE, expected_project_id=body.get("project_id", ""))
        except EvidenceMappingError as exc:
            return self.reply(409, {"code": str(exc), "blocked": True})
        return self.reply(200, bundle)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PORT", "18084"))), Handler).serve_forever()
