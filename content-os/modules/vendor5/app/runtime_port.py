"""Vendor 3 owns retry/budget. Adapter does not run an independent retry storm."""
from __future__ import annotations

from app.errors import AdapterError


class RuntimeRetryPort:
    def __init__(self, max_attempts: int = 1, owner: str = "vendor3"):
        if max_attempts < 1:
            raise ValueError("max_attempts")
        self.max_attempts = max_attempts
        self.owner = owner
        self.attempts: list[str] = []

    def run(self, fn):
        last: AdapterError | None = None
        for n in range(1, self.max_attempts + 1):
            try:
                return fn()
            except AdapterError as err:
                self.attempts.append(err.code)
                last = err
                if not err.retryable:
                    raise
                if err.code == "TIMEOUT" and "accepted" in err.message:
                    raise
                if n >= self.max_attempts:
                    raise
        assert last
        raise last
