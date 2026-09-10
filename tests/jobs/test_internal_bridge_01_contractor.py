"""Contractor pin is required. Missing packages fail hard (no importorskip)."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from j3_support import CONTRACTOR_PACKAGES, ensure_contractor_path, require_contractor

from kf_pilot.contractor_bridge.mapping import CONTRACTOR_BASELINE


def test_contractor_packages_required_no_importorskip() -> None:
    require_contractor()
    for pkg in CONTRACTOR_PACKAGES:
        __import__(pkg)


def test_contractor_git_sha_matches_pin() -> None:
    ensure_contractor_path()
    import os

    root = os.environ.get("CONTRACTOR_ROOT") or "/tmp/j3/contractor"
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert sha == CONTRACTOR_BASELINE
    assert sha == "afac091e60bb6c8a0f0630964e43f5e80951267c"
