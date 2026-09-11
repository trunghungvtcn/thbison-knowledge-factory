from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS idempotency (
  ledger_key TEXT PRIMARY KEY,
  payload_hash TEXT NOT NULL,
  receipt_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
  provider_record_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  destination_id TEXT NOT NULL,
  external_key TEXT NOT NULL,
  article_id TEXT NOT NULL,
  article_revision INTEGER NOT NULL,
  content_sha256 TEXT NOT NULL,
  revision INTEGER NOT NULL,
  body TEXT NOT NULL,
  public INTEGER NOT NULL DEFAULT 0,
  test_run_id TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(project_id, destination_id, external_key)
);
CREATE TABLE IF NOT EXISTS mutations (
  mutation_id TEXT PRIMARY KEY,
  test_run_id TEXT NOT NULL,
  provider_record_id TEXT NOT NULL,
  action TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT,
  rolled_back INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS unknown_outcomes (
  publication_id TEXT PRIMARY KEY,
  ledger_key TEXT NOT NULL,
  attempts INTEGER NOT NULL,
  last_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sim_drafts (
  provider_record_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  destination_id TEXT NOT NULL,
  external_key TEXT NOT NULL,
  article_id TEXT NOT NULL,
  article_revision INTEGER NOT NULL,
  content_sha256 TEXT NOT NULL,
  revision INTEGER NOT NULL,
  body TEXT NOT NULL,
  public INTEGER NOT NULL DEFAULT 0,
  test_run_id TEXT,
  created_at TEXT NOT NULL,
  human_edited INTEGER NOT NULL DEFAULT 0,
  UNIQUE(project_id, destination_id, external_key)
);
CREATE TABLE IF NOT EXISTS sim_meta (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
"""


class Ledger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        last = None
        for _ in range(80):
            try:
                self._conn.execute("PRAGMA busy_timeout=30000")
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.executescript(SCHEMA)
                self._conn.commit()
                last = None
                break
            except sqlite3.OperationalError as exc:
                last = exc
                time.sleep(0.05)
        if last:
            raise last

    def close(self) -> None:
        self._conn.close()

    def get_idem(self, key: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload_hash, receipt_json FROM idempotency WHERE ledger_key=?", (key,)
            ).fetchone()
            if not row:
                return None
            return {"payload_hash": row["payload_hash"], "receipt": json.loads(row["receipt_json"])}

    def put_idem(self, key: str, payload_hash: str, receipt: dict, created_at: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO idempotency(ledger_key,payload_hash,receipt_json,created_at) VALUES(?,?,?,?)",
                (key, payload_hash, json.dumps(receipt, ensure_ascii=True, separators=(",", ":")), created_at),
            )
            self._conn.commit()

    def put_draft(self, draft: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO drafts(
                    provider_record_id,project_id,destination_id,external_key,article_id,
                    article_revision,content_sha256,revision,body,public,test_run_id,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    draft["provider_record_id"],
                    draft["project_id"],
                    draft["destination_id"],
                    draft["external_key"],
                    draft["article_id"],
                    draft["article_revision"],
                    draft["content_sha256"],
                    draft["revision"],
                    draft["body"],
                    1 if draft.get("public") else 0,
                    draft.get("test_run_id"),
                    draft["created_at"],
                ),
            )
            self._conn.commit()

    def get_draft(self, provider_record_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM drafts WHERE provider_record_id=?", (provider_record_id,)
            ).fetchone()
            return dict(row) if row else None

    def lookup(self, project_id: str, destination_id: str, external_key: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM drafts WHERE project_id=? AND destination_id=? AND external_key=?",
                (project_id, destination_id, external_key),
            ).fetchone()
            return dict(row) if row else None

    def list_by_run(self, test_run_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM drafts WHERE test_run_id=?", (test_run_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_draft(self, provider_record_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM drafts WHERE provider_record_id=?", (provider_record_id,))
            self._conn.commit()

    def record_mutation(self, rec: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO mutations(mutation_id,test_run_id,provider_record_id,action,before_json,after_json,rolled_back) VALUES(?,?,?,?,?,?,?)",
                (
                    rec["mutation_id"],
                    rec["test_run_id"],
                    rec["provider_record_id"],
                    rec["action"],
                    json.dumps(rec.get("before")),
                    json.dumps(rec.get("after")),
                    1 if rec.get("rolled_back") else 0,
                ),
            )
            self._conn.commit()

    def mark_rolled_back(self, mutation_id: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE mutations SET rolled_back=1 WHERE mutation_id=?", (mutation_id,))
            self._conn.commit()

    def put_unknown(self, publication_id: str, ledger_key: str, attempts: int, status: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO unknown_outcomes(publication_id,ledger_key,attempts,last_status) VALUES(?,?,?,?)",
                (publication_id, ledger_key, attempts, status),
            )
            self._conn.commit()

    def get_unknown(self, publication_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM unknown_outcomes WHERE publication_id=?", (publication_id,)
            ).fetchone()
            return dict(row) if row else None

    # --- durable simulator ---
    def sim_get(self, rid: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM sim_drafts WHERE provider_record_id=?", (rid,)).fetchone()
            return dict(row) if row else None

    def sim_lookup(self, project_id: str, destination_id: str, external_key: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM sim_drafts WHERE project_id=? AND destination_id=? AND external_key=?",
                (project_id, destination_id, external_key),
            ).fetchone()
            return dict(row) if row else None

    def sim_put(self, d: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO sim_drafts(
                    provider_record_id,project_id,destination_id,external_key,article_id,
                    article_revision,content_sha256,revision,body,public,test_run_id,created_at,human_edited
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    d["provider_record_id"], d["project_id"], d["destination_id"], d["external_key"],
                    d["article_id"], d["article_revision"], d["content_sha256"], d["revision"],
                    d["body"], 1 if d.get("public") else 0, d.get("test_run_id"), d["created_at"],
                    1 if d.get("human_edited") else 0,
                ),
            )
            self._conn.commit()

    def sim_delete(self, rid: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sim_drafts WHERE provider_record_id=?", (rid,))
            self._conn.commit()

    def sim_clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sim_drafts")
            self._conn.execute("DELETE FROM sim_meta")
            self._conn.commit()

    def sim_meta_get(self, k: str, default: str = "0") -> str:
        with self._lock:
            row = self._conn.execute("SELECT v FROM sim_meta WHERE k=?", (k,)).fetchone()
            return row["v"] if row else default

    def sim_meta_set(self, k: str, v: str) -> None:
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO sim_meta(k,v) VALUES(?,?)", (k, v))
            self._conn.commit()

    def sim_incr(self, k: str) -> int:
        with self._lock:
            cur = int(self.sim_meta_get(k, "0"))
            cur += 1
            self._conn.execute("INSERT OR REPLACE INTO sim_meta(k,v) VALUES(?,?)", (k, str(cur)))
            self._conn.commit()
            return cur
