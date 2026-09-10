from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from app.adapter import CONTRACT_SHA256, CONTRACT_VERSION, CmsAdapter
from app.provenance import code_commit
from app.errors import AdapterError
from app.fixtures import load_demo_authority

LEDGER = os.environ.get("CMS_LEDGER_PATH", "/tmp/v5-ledger.sqlite")
ADAPTER = CmsAdapter(LEDGER)


def load_authority() -> None:
    path = os.environ.get("CMS_AUTHORITY_FIXTURE", "").strip()
    if not path:
        load_demo_authority(ADAPTER.authority)
        return
    payload = json.loads(open(path, encoding="utf-8").read())
    records = (payload["article"], payload["approval"], payload["evidence"])
    if any(record.get("data_class") != "TEST_ONLY" for record in records):
        raise RuntimeError("CMS_AUTHORITY_FIXTURE_ONLY_ACCEPTS_TEST_ONLY")
    ADAPTER.authority.put_article(payload["article"])
    ADAPTER.authority.put_approval(payload["approval"])
    ADAPTER.authority.put_evidence(payload["evidence"])


load_authority()


def public_receipt(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if not k.startswith("_")}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _err(self, exc: AdapterError, request_id: str = "unknown") -> None:
        self._json(exc.http_status, exc.body(request_id))

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/healthz":
                self._json(200, {"status": "ok"})
                return
            if path == "/v1/capabilities":
                auth = self.headers.get("Authorization")
                if not auth:
                    raise AdapterError("UNAUTHORIZED", "capabilities requires service authorization")
                ADAPTER.authenticate(auth, "test-thbison")
                caps = ADAPTER.inspect_capabilities()
                self._json(
                    200,
                    {
                        "contract_version": CONTRACT_VERSION,
                        "service": "cms-adapter",
                        "code_commit": code_commit(),
                        "contract_sha256": CONTRACT_SHA256,
                        "mode": caps["mode"],
                        "enabled_operations": caps["enabled_operations"],
                        "max_json_bytes": 2097152,
                    },
                )
                return
            raise AdapterError("VALIDATION_ERROR", "not found")
        except AdapterError as exc:
            self._err(exc)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/v1/publications":
                if self.headers.get("X-Contract-Version") != CONTRACT_VERSION:
                    raise AdapterError("UNSUPPORTED_CONTRACT", "Unknown contract version")
                idem = self.headers.get("Idempotency-Key")
                if not idem or not (16 <= len(idem) <= 128):
                    raise AdapterError("VALIDATION_ERROR", "Idempotency-Key required 16-128")
                body = self._read_json()
                rec = ADAPTER.publish(
                    body,
                    idem,
                    self.headers.get("Authorization"),
                    self.headers.get("X-Test-Run-Id"),
                )
                self._json(202, public_receipt(rec))
                return
            if path.endswith("/reconcile") and path.startswith("/v1/publications/"):
                ADAPTER.authenticate(self.headers.get("Authorization"), "test-thbison")
                pub = path.split("/")[3]
                self._json(200, ADAPTER.reconcile(pub))
                return
            if path == "/v1/test/rollback":
                ADAPTER.authenticate(self.headers.get("Authorization"), "test-thbison")
                self._json(200, ADAPTER.rollback_own(self.headers.get("X-Test-Run-Id") or ""))
                return
            raise AdapterError("VALIDATION_ERROR", "not found")
        except AdapterError as exc:
            self._err(exc, self.headers.get("X-Request-Id", "unknown"))


def serve(host: str = "127.0.0.1", port: int = 8080):
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    serve(port=int(os.environ.get("PORT", "18085")))
