from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

VENDOR = Path(__file__).resolve().parents[2] / "modules" / "vendor3"
sys.path.insert(0, str(VENDOR))
from app.runtime import Runtime  # noqa: E402
from app.store import Store  # noqa: E402

runtime = Runtime(Store(os.environ["RUNTIME_DB"]))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def reply(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")

    def auth(self):
        return self.headers.get("X-Service-Id") == "v6-lab" and self.headers.get("X-Project-Id") == "test-thbison"

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, {"status": "ok"})
        match = re.fullmatch(r"/v1/jobs/([^/]+)", self.path)
        if match and self.auth():
            code, body = runtime.get_job(match.group(1), "test-thbison")
            return self.reply(code, body)
        return self.reply(404, {"code": "NOT_FOUND"})

    def do_POST(self):
        if not self.auth():
            return self.reply(401, {"code": "UNAUTHORIZED"})
        body = self.body()
        if self.path == "/v1/jobs":
            code, out = runtime.submit_job(project_id="test-thbison", operation=body["operation"], idempotency_key=body["idempotency_key"], request_id=body["request_id"], data_class=body.get("data_class", "TEST_ONLY"), payload=body.get("payload", {}), budget=body.get("budget"))
            return self.reply(code, out)
        if self.path == "/v1/leases/claim":
            code, out = runtime.claim(project_id="test-thbison", worker_id=body.get("worker_id", "v6-worker"), request_id=body.get("request_id", "claim-request"))
            return self.reply(code, out)
        match = re.fullmatch(r"/v1/leases/([^/]+)/complete", self.path)
        if match:
            code, out = runtime.complete(match.group(1), "test-thbison", body.get("worker_id", "v6-worker"), success=body.get("success", True), retryable=body.get("retryable", False), error_code=body.get("error_code"), artifact=body.get("artifact"))
            return self.reply(code, out)
        return self.reply(404, {"code": "NOT_FOUND"})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PORT", "18083"))), Handler).serve_forever()
