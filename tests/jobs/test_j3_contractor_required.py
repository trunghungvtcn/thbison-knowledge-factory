from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from j3_support import CONTRACTOR_PACKAGES, require_contractor


def test_contractor_packages_required() -> None:
    require_contractor()
    for pkg in CONTRACTOR_PACKAGES:
        __import__(pkg)
