import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thbison_v6.harness.lab import Lab


@pytest.fixture
def lab(tmp_path):
    return Lab(mode="REFERENCE_ONLY", root=tmp_path)
