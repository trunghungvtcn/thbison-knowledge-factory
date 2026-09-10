"""Durable ledger survives process kill; restore in a new PID (V3-R2-06)."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path


WORKER = textwrap.dedent(
    """
    import json, os, sys
    sys.path.insert(0, os.environ["V3_ROOT"])
    from app.runtime import Runtime
    from app.store import Store
    db = os.environ["V3_DB"]
    action = sys.argv[1]
    rt = Runtime(Store(db))
    if action == "submit":
        code, rec = rt.submit_job(
            project_id="test-alpha", operation="plan", idempotency_key="restart-1",
            request_id="req-rs", data_class="TEST_ONLY", payload={"n": 1}, budget={"max_requests": 4, "max_cost_units": 10},
        )
        print(json.dumps({"pid": os.getpid(), "code": code, "job_id": rec["job_id"], "status": rec["status"]}))
    elif action == "restore":
        job_id = sys.argv[2]
        code, rec = rt.get_job(job_id, "test-alpha")
        print(json.dumps({"pid": os.getpid(), "code": code, "status": rec["status"], "job_id": rec["job_id"]}))
    """
)


def test_subprocess_restart_preserves_queued_job(tmp_path):
    root = Path(__file__).resolve().parents[1]
    db = tmp_path / "ledger.db"
    worker = tmp_path / "worker.py"
    worker.write_text(WORKER)
    env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "V3_ROOT": str(root), "V3_DB": str(db)}
    a = subprocess.run([sys.executable, str(worker), "submit"], capture_output=True, text=True, env=env, check=False)
    assert a.returncode == 0, a.stderr
    rec = json.loads(a.stdout.strip().splitlines()[-1])
    assert rec["status"] == "QUEUED"
    pid_a = rec["pid"]
    b = subprocess.run([sys.executable, str(worker), "restore", rec["job_id"]], capture_output=True, text=True, env=env, check=False)
    assert b.returncode == 0, b.stderr
    rec2 = json.loads(b.stdout.strip().splitlines()[-1])
    assert rec2["pid"] != pid_a
    assert rec2["status"] == "QUEUED"
    assert rec2["job_id"] == rec["job_id"]
    # persist evidence sidecar for command receipt consumers
    ev = tmp_path / "restart_receipt.json"
    ev.write_text(json.dumps({"pid_a": pid_a, "pid_b": rec2["pid"], "stdout_a": a.stdout, "stdout_b": b.stdout, "exit_a": a.returncode, "exit_b": b.returncode}))
