"""HTTP client for actual hops. Transport is injectable (urllib or fake)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class RecordedCall:
    method: str
    url: str
    headers: dict
    body: Any
    status: int


class FakeHttpTransport:
    """In-process HTTP stand-in. Does not contact the network."""

    def __init__(self):
        self.calls: list[RecordedCall] = []
        self.routes: dict[tuple[str, str], Callable] = {}
        self.force_status: int | None = None

    def route(self, method: str, path: str, handler: Callable) -> None:
        self.routes[(method.upper(), path)] = handler

    def request(self, method: str, url: str, headers: dict | None = None, body: Any = None) -> tuple[int, dict | list | str]:
        headers = headers or {}
        path = url.split("://", 1)[-1]
        path = "/" + path.split("/", 1)[-1] if "/" in path.split("://", 1)[-1] else path
        # url like http://vendor4/v1/knowledge/query
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path
        if self.force_status:
            status = self.force_status
            self.force_status = None
            self.calls.append(RecordedCall(method, url, headers, body, status))
            return status, {"code": "FORCED"}
        handler = self.routes.get((method.upper(), path))
        if handler is None:
            self.calls.append(RecordedCall(method, url, headers, body, 404))
            return 404, {"code": "NOT_FOUND", "path": path}
        status, payload = handler(headers, body)
        self.calls.append(RecordedCall(method, url, headers, body, status))
        return status, payload


class UrlLibTransport:
    def request(self, method: str, url: str, headers: dict | None = None, body: Any = None) -> tuple[int, dict | list | str]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(url, data=data, method=method, headers=headers or {})
        try:
            with urlopen(req, timeout=5) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw.decode()) if raw else {}
        except HTTPError as e:
            raw = e.read()
            try:
                payload = json.loads(raw.decode())
            except Exception:
                payload = {"message": str(e)}
            return e.code, payload
        except URLError as e:
            return 0, {"code": "TRANSPORT_ERROR", "message": str(e.reason)}


class HttpJsonClient:
    def __init__(self, base_url: str, transport, token: str | None = None, contract_version: str = "1.0.0"):
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.token = token
        self.contract_version = contract_version
        self.kind = "ACTUAL"
        self.transport_name = type(transport).__name__
        self.verified_component = False

    def _headers(self, extra: dict | None = None) -> dict:
        h = {
            "Content-Type": "application/json",
            "X-Contract-Version": self.contract_version,
            "Accept": "application/json",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    def call(self, method: str, path: str, body: Any = None, extra_headers: dict | None = None) -> tuple[int, Any]:
        return self.transport.request(method, self.base_url + path, self._headers(extra_headers), body)
