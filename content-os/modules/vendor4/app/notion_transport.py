from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TransportError(RuntimeError):
    def __init__(self, code: str, status: int | None = None, message: str = ""):
        super().__init__(message or code)
        self.code = code
        self.status = status


class HttpTransport:
    def request(self, method: str, url: str, headers: dict, body: bytes | None = None, timeout: float = 10.0) -> dict:
        req = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                return {"status": getattr(resp, "status", 200), "body": json.loads(raw.decode("utf-8") or "{}")}
        except HTTPError as e:
            raise TransportError("HTTP_ERROR", e.code, str(e))
        except URLError as e:
            raise TransportError("TIMEOUT_OR_NETWORK", None, str(e.reason))
        except TimeoutError as e:
            raise TransportError("TIMEOUT_OR_NETWORK", None, str(e))


class MockTransport:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.allowlist: set[str] = set()
        self.script: list[Any] = []

    def queue(self, item: Any) -> None:
        self.script.append(item)

    def request(self, method: str, url: str, headers: dict, body: bytes | None = None, timeout: float = 10.0) -> dict:
        self.calls.append({"method": method, "url": url, "headers": {k: v for k, v in headers.items() if k.lower() != "authorization"}})
        ds = None
        if "/data_sources/" in url:
            ds = url.split("/data_sources/")[1].split("/")[0]
        if ds and self.allowlist and ds not in self.allowlist:
            raise TransportError("OUTSIDE_ALLOWLIST", 403, ds)
        if not self.script:
            raise TransportError("NO_SCRIPT", None, "mock exhausted")
        item = self.script.pop(0)
        if isinstance(item, TransportError):
            raise item
        return item
