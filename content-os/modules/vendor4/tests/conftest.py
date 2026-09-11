import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def _isolate_data_dir(tmp_path_factory):
    os.environ["V4_DATA_DIR"] = str(tmp_path_factory.mktemp("v4data"))
    yield


def pytest_configure():
    os.environ.setdefault("V4_DATA_DIR", str(ROOT / "var-test"))
    Path(os.environ["V4_DATA_DIR"]).mkdir(parents=True, exist_ok=True)
