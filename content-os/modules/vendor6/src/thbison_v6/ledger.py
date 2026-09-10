"""Durable file-backed ledger for jobs, approvals, effects, budget, leases."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any


class FileLedger:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, name: str) -> Path:
        return self.root / f"{name}.json"

    def load(self, name: str, default: Any) -> Any:
        p = self._path(name)
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))

    def save(self, name: str, data: Any) -> None:
        with self._lock:
            p = self._path(name)
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp, p)

    def get_map(self, name: str) -> dict:
        data = self.load(name, {})
        if not isinstance(data, dict):
            return {}
        return data

    def put(self, name: str, key: str, value: Any) -> None:
        with self._lock:
            data = self.get_map(name)
            data[key] = value
            self.save(name, data)

    def get(self, name: str, key: str, default: Any = None) -> Any:
        return self.get_map(name).get(key, default)


class Clock:
    """Injectable clock for expiry tests."""

    def __init__(self):
        self._offset = 0.0

    def now(self) -> float:
        return time.time() + self._offset

    def advance(self, seconds: float) -> None:
        self._offset += seconds
