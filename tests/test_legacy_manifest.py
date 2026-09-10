from pathlib import Path

import pytest

from kf_pilot.legacy_manifest import LegacyManifestPathError, resolve_manifest_entries


def test_windows_legacy_locator_maps_inside_root(tmp_path: Path):
    target = tmp_path / "src" / "pkg" / "item.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"legacy")
    result = resolve_manifest_entries(
        tmp_path, {r"src\pkg\item.py": "expected"}, dialect="windows-relative-v1"
    )
    assert result[r"src\pkg\item.py"].read_bytes() == b"legacy"


@pytest.mark.parametrize(
    "locator",
    [r"..\outside", r"C:\outside", r"C:outside", r"\\server\share\x", "/outside", "a\x00b"],
)
def test_legacy_locator_rejects_unsafe_paths(tmp_path: Path, locator: str):
    with pytest.raises(LegacyManifestPathError):
        resolve_manifest_entries(tmp_path, {locator: "x"}, dialect="windows-relative-v1")


def test_legacy_manifest_rejects_cross_platform_aliases(tmp_path: Path):
    with pytest.raises(LegacyManifestPathError, match="PATH_COLLISION"):
        resolve_manifest_entries(
            tmp_path,
            {r"A\item.txt": "x", r"a\ITEM.txt": "y"},
            dialect="windows-relative-v1",
        )
