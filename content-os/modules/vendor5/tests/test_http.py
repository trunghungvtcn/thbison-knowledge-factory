from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.fixtures import PUBLISH_REQ, load_demo_authority
from app.httpapi import ADAPTER, Handler


def _server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def _url(httpd, path: str) -> str:
    return f"http://127.0.0.1:{httpd.server_address[1]}{path}"


def test_healthz_unauthenticated():
    httpd = _server()
    try:
        with urlopen(_url(httpd, "/healthz")) as r:
            body = json.loads(r.read().decode())
            assert r.status == 200
            assert body["status"] == "ok"
    finally:
        httpd.shutdown()


def test_capabilities_requires_auth():
    httpd = _server()
    try:
        try:
            urlopen(_url(httpd, "/v1/capabilities"))
            assert False
        except HTTPError as e:
            assert e.code == 401
        req = Request(_url(httpd, "/v1/capabilities"), headers={"Authorization": "Bearer test-service"})
        with urlopen(req) as r:
            body = json.loads(r.read().decode())
            assert body["contract_version"] == "1.0.0"
            assert body["mode"] == "MOCK"
    finally:
        httpd.shutdown()


def test_publish_http_dry_run():
    load_demo_authority(ADAPTER.authority)
    httpd = _server()
    try:
        req = Request(
            _url(httpd, "/v1/publications"),
            data=json.dumps(PUBLISH_REQ).encode(),
            headers={
                "Authorization": "Bearer test-service",
                "X-Contract-Version": "1.0.0",
                "Idempotency-Key": "http-idempotency-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(req) as r:
            assert r.status == 202
            body = json.loads(r.read().decode())
            assert body["status"] == "DRY_RUN"
            assert body["actual_side_effects"] == 0
    finally:
        httpd.shutdown()


def test_publish_malformed_json_returns_validation_envelope():
    httpd = _server()
    try:
        req = Request(
            _url(httpd, "/v1/publications"),
            data=b"{not json",
            headers={
                "Authorization": "Bearer test-service",
                "X-Contract-Version": "1.0.0",
                "Idempotency-Key": "malformed-json-01",
                "X-Request-Id": "req-malformed-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            urlopen(req)
            assert False, "malformed JSON must not be accepted"
        except HTTPError as exc:
            assert exc.code == 400
            body = json.loads(exc.read().decode())
            assert body == {
                "contract_version": "1.0.0",
                "request_id": "req-malformed-01",
                "code": "VALIDATION_ERROR",
                "message": "Request body must be valid UTF-8 JSON",
                "retryable": False,
            }
    finally:
        httpd.shutdown()


def test_publish_non_object_json_returns_validation_envelope():
    httpd = _server()
    try:
        req = Request(
            _url(httpd, "/v1/publications"),
            data=b"[]",
            headers={
                "Authorization": "Bearer test-service",
                "X-Contract-Version": "1.0.0",
                "Idempotency-Key": "non-object-json-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            urlopen(req)
            assert False, "non-object JSON must not be accepted"
        except HTTPError as exc:
            assert exc.code == 400
            body = json.loads(exc.read().decode())
            assert body["code"] == "VALIDATION_ERROR"
            assert body["message"] == "Request body must be a JSON object"
    finally:
        httpd.shutdown()
