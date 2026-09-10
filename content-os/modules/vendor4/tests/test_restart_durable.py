from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_k26_restart_reconcile(tmp_path, monkeypatch):
    monkeypatch.setenv("V4_DATA_DIR", str(tmp_path))
    from app.store import Store

    s1 = Store()
    rec = {
        "upload_id": "up-restart1",
        "asset_id": "ast-restart1",
        "project_id": "test-alpha",
        "filename": "keep.bin",
        "size": 4,
        "sha256": None,
        "state": "PENDING_UPLOAD",
        "data_class": "TEST_ONLY",
    }
    raw = b"blob"
    from app.util import sha256_bytes

    rec["sha256"] = sha256_bytes(raw)
    s1.persist_upload(rec, raw)
    del s1
    s2 = Store()
    assert "up-restart1" in s2.uploads
    assert s2.blobs["up-restart1"] == raw
    assert s2.uploads["up-restart1"]["sha256"] == sha256_bytes(raw)
    assert s2.uploads["up-restart1"]["state"] == "PENDING_UPLOAD"
    # complete without creating a second asset id
    assert s2.assets["ast-restart1"]["asset_id"] == "ast-restart1"
