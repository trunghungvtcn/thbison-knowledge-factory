from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _spawn(data_dir: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["V4_DATA_DIR"] = str(data_dir)
    env["APP_MODE"] = "MOCK"
    env["ALLOW_PRODUCTION"] = "false"
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _wait(port: int, timeout=15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=0.3)
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def _json(method: str, url: str, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer test-token",
            "X-Contract-Version": "1.0.0",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_subprocess_kill_restart_reconcile(tmp_path):
    port = _free_port()
    a = _spawn(tmp_path, port)
    evidence = {"pid_a": a.pid, "port": port}
    try:
        _wait(port)
        payload = "process-restart-bytes"
        status, body = _json(
            "POST",
            f"http://127.0.0.1:{port}/v1/assets/uploads",
            {"project_id": "test-alpha", "filename": "restart.bin", "content": payload},
        )
        assert status == 200
        assert body["state"] == "PENDING_UPLOAD"
        uid = body["upload_id"]
        aid = body["asset_id"]
        digest = body["sha256"]
        assert digest == hashlib.sha256(payload.encode()).hexdigest()
        evidence.update({"upload_id": uid, "asset_id": aid, "sha256": digest})
        a.kill()
        a.wait(timeout=5)
        evidence["exit_a"] = a.returncode
        b = _spawn(tmp_path, port)
        evidence["pid_b"] = b.pid
        assert b.pid != a.pid
        try:
            _wait(port)
            st, got = _json("GET", f"http://127.0.0.1:{port}/v1/assets/{aid}?project_id=test-alpha")
            assert st == 200
            assert got["asset_id"] == aid
            assert got["sha256"] == digest
            assert got["state"] == "PENDING_UPLOAD"
            st, done = _json("POST", f"http://127.0.0.1:{port}/v1/assets/uploads/{uid}/complete", {"sha256": digest})
            assert st == 200
            assert done["asset_id"] == aid
            assert done["sha256"] == digest
            st, again = _json("POST", f"http://127.0.0.1:{port}/v1/assets/uploads/{uid}/complete", {"sha256": digest})
            assert st == 200
            assert again["asset_id"] == aid
        finally:
            b.kill()
            b.wait(timeout=5)
            evidence["exit_b"] = b.returncode
    finally:
        if a.poll() is None:
            a.kill()
            a.wait(timeout=5)
    (tmp_path / "restart_evidence.json").write_text(json.dumps(evidence, indent=2))


def test_crash_window_quarantine(tmp_path, monkeypatch):
    monkeypatch.setenv("V4_DATA_DIR", str(tmp_path))
    folder = tmp_path / "uploads"
    folder.mkdir()
    (folder / "up-partial.bin.tmp").write_bytes(b"incomplete")
    from app.store import Store

    s = Store()
    rec = s.uploads["up-partial"]
    assert rec["state"] == "QUARANTINE_PARTIAL_WRITE"
    assert rec["state"] != "VERIFIED"
    assert rec["state"] != "PENDING_UPLOAD"
