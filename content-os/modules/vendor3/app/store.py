"""Durable SQLite ledger for jobs, leases, budgets, audit, receipts."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  operation TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  request_id TEXT NOT NULL,
  data_class TEXT NOT NULL,
  status TEXT NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  payload TEXT NOT NULL,
  error_code TEXT,
  result_artifact TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  deadline_at REAL,
  cancelled INTEGER NOT NULL DEFAULT 0,
  UNIQUE(project_id, operation, idempotency_key)
);

CREATE TABLE IF NOT EXISTS leases (
  lease_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  worker_id TEXT NOT NULL,
  attempt INTEGER NOT NULL,
  expires_at REAL NOT NULL,
  status TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS budgets (
  job_id TEXT PRIMARY KEY,
  max_requests INTEGER NOT NULL,
  max_cost_units REAL NOT NULL,
  reserved_requests INTEGER NOT NULL DEFAULT 0,
  reserved_cost REAL NOT NULL DEFAULT 0,
  consumed_requests INTEGER NOT NULL DEFAULT 0,
  consumed_cost REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  job_id TEXT,
  project_id TEXT,
  event_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  event_hash TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS receipts (
  receipt_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  provider_ref TEXT,
  payload TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS unknown_outcomes (
  outcome_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  lookup_key TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS module_schedule_blocks (
  module TEXT PRIMARY KEY,
  blocked INTEGER NOT NULL DEFAULT 1
);

INSERT OR IGNORE INTO module_schedule_blocks(module, blocked) VALUES
  ('seo-planning', 1),
  ('content-workflow', 1),
  ('knowledge-gateway', 1),
  ('asset-gateway', 1);
"""


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self._lock = threading.RLock()
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout=5000")
        self.migrate()

    def migrate(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def execute(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, args)

    def fetchone(self, sql: str, args: tuple = ()) -> dict[str, Any] | None:
        cur = self.execute(sql, args)
        row = cur.fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        cur = self.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]

    def now(self) -> float:
        return time.time()


def dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
