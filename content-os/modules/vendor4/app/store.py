from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path

from .util import sha256_bytes, sha256_text

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "synthetic"


def data_dir() -> Path:
    return Path(os.environ.get("V4_DATA_DIR") or (ROOT / "var")).resolve()


class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.knowledge = []
        self.assets = {}
        self.uploads = {}
        self.blobs = {}
        self.bundles = {}
        self.cache = {}
        self.idempotency = {}
        self.mutations = []
        self.rate = {"remain": 3, "force_429": False}
        self.clock_offset = 0
        self.revoked_sources = set()
        self.hold_claims = set()
        self.revision = "rev-synthetic-1"
        self.schema_revision = "schema-1.0.0"
        self.load()
        self.restore_durable()

    def _ledger(self) -> Path:
        p = data_dir() / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def persist_upload(self, rec: dict, raw: bytes) -> None:
        uid = rec["upload_id"]
        folder = self._ledger()
        blob = folder / f"{uid}.bin"
        meta = folder / f"{uid}.json"
        tmp_b = folder / f"{uid}.bin.tmp"
        tmp_m = folder / f"{uid}.json.tmp"
        tmp_b.write_bytes(raw)
        tmp_b.replace(blob)
        tmp_m.write_text(json.dumps(rec, ensure_ascii=True, indent=2), encoding="utf-8")
        tmp_m.replace(meta)
        self.blobs[uid] = raw
        self.uploads[uid] = rec
        self.assets[rec["asset_id"]] = rec

    def restore_durable(self) -> None:
        folder = self._ledger()
        for tmp in list(folder.glob("*.tmp")):
            uid = tmp.name.split(".")[0]
            rec = {
                "upload_id": uid,
                "asset_id": f"ast-quarantine-{uid[:8]}",
                "state": "QUARANTINE_PARTIAL_WRITE",
                "data_class": "TEST_ONLY",
            }
            self.uploads[uid] = rec
            tmp.rename(folder / f"{uid}.quarantine")
        for meta in folder.glob("*.json"):
            try:
                rec = json.loads(meta.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                uid = meta.stem
                rec = {"upload_id": uid, "asset_id": f"ast-badmeta-{uid[:8]}", "state": "QUARANTINE_BAD_META", "data_class": "TEST_ONLY"}
                self.uploads[uid] = rec
                continue
            blob = folder / f"{rec['upload_id']}.bin"
            if blob.is_file():
                raw = blob.read_bytes()
                rec_hash = rec.get("sha256")
                if rec_hash and rec_hash != sha256_bytes(raw):
                    rec["state"] = "HASH_MISMATCH"
                self.blobs[rec["upload_id"]] = raw
            else:
                rec["state"] = "QUARANTINE_MISSING_BLOB"
            self.uploads[rec["upload_id"]] = rec
            self.assets[rec["asset_id"]] = rec

    def load(self) -> None:
        raw = json.loads((FIXTURES / "knowledge.json").read_text())
        for row in raw:
            row = dict(row)
            row["quote_sha256"] = sha256_text(row["quote"])
            row["data_class"] = "TEST_ONLY"
            self.knowledge.append(row)
        assets = json.loads((FIXTURES / "assets.json").read_text())
        for a in assets:
            a = dict(a)
            a["data_class"] = "TEST_ONLY"
            self.assets[a["asset_id"]] = a

    def snapshot(self):
        with self.lock:
            return deepcopy(
                {
                    "knowledge": self.knowledge,
                    "assets": self.assets,
                    "uploads": self.uploads,
                    "blobs": {k: v for k, v in self.blobs.items()},
                    "bundles": self.bundles,
                    "cache": self.cache,
                    "revision": self.revision,
                }
            )


STORE = Store()
