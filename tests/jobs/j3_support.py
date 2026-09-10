"""Shared J3 test helpers. Missing contractor is a hard failure, not a skip."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import hashlib
import os
import subprocess
import sys

from kf_pilot.runtime_contract import RunContract

CONTRACTOR_PACKAGES = (
    "grok_locator",
    "grok_asset_store",
    "grok_job_ledger",
    "grok_notion_projection",
)


def ensure_contractor_path() -> None:
    root = os.environ.get("CONTRACTOR_ROOT")
    if not root:
        candidate = Path("/tmp/j3/contractor")
        if candidate.is_dir():
            root = str(candidate)
    if not root:
        raise RuntimeError(
            "BLOCKED_INPUT: CONTRACTOR_ROOT unset and /tmp/j3/contractor missing"
        )
    for name in ("m1_locator", "m2_asset_store", "m3_job_ledger", "m4_notion_projection"):
        src = str(Path(root) / name / "src")
        if src not in sys.path:
            sys.path.insert(0, src)


def require_contractor() -> None:
    ensure_contractor_path()
    missing = []
    for pkg in CONTRACTOR_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        raise RuntimeError(
            "BLOCKED_INPUT: contractor packages not importable: " + ", ".join(missing)
        )


def contract(repo: Path, snapshot: Path, **changes) -> RunContract:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception:
        commit = "3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b"
    if len(commit) != 40:
        commit = "3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b"
    base = RunContract(
        job_id="J3-SHADOW-001",
        task_type="VALIDATE_SCORE",
        domain="manual-chain-hoist",
        repository="trunghungvtcn/thbison-knowledge-factory",
        code_commit=commit,
        dataset_snapshot_id="TEST_ONLY-j3-fixture",
        input_manifest_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        mode="TEST_ONLY",
        allowed_outputs=("shadow-receipt.json",),
        attempt_budget=1,
        timeout_seconds=30,
    )
    return replace(base, **changes) if changes else base


PIN_KW = {
    "j1_commit_sha": "b9e291fb84ddf99a6e6dd662ae122f39326f4d41",
    "j1_input_hash": "1" * 64,
    "j2_commit_sha": "5e6161914f519403059ce13a1568d58ac7162f28",
    "j2_input_hash": "2" * 64,
}
