from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_local.sh"


def _run(inject: str, tmp_path: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["VERIFY_LOGDIR"] = str(tmp_path / "ev")
    env["VERIFY_INJECT_FAIL"] = inject
    (tmp_path / "ev").mkdir()
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, cwd=str(ROOT), timeout=180)


def test_verify_inject_pip_check_no_success_receipt(tmp_path):
    r = _run("pip_check", tmp_path)
    assert r.returncode != 0
    receipt = tmp_path / "ev" / "verify_local.receipt"
    assert not receipt.exists()


def test_verify_inject_worker_no_success_receipt(tmp_path):
    r = _run("worker", tmp_path)
    assert r.returncode != 0
    assert not (tmp_path / "ev" / "verify_local.receipt").exists()


def test_verify_inject_restart_assert_no_success_receipt(tmp_path):
    r = _run("restart_assert", tmp_path)
    assert r.returncode != 0
    assert not (tmp_path / "ev" / "verify_local.receipt").exists()
