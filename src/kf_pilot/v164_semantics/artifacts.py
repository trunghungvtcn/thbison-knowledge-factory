from __future__ import annotations

from pathlib import Path

from .canonical import canonical_bytes, digest, load_json, require, sha256


def output_bytes(name: str, value: object) -> bytes:
    if name.endswith(".jsonl"):
        return b"".join(canonical_bytes(row) + b"\n" for row in value)
    return canonical_bytes(value) + b"\n"


def write_artifacts(path: Path, outputs: dict, code_manifest: dict) -> None:
    require(not path.exists(), "OUTPUT_ALREADY_EXISTS", str(path))
    path.mkdir(parents=True)
    manifest = {}
    values = dict(outputs, **{"v164_code_manifest.json": code_manifest})
    for name, value in sorted(values.items()):
        require(Path(name).name == name and name.endswith((".json", ".jsonl")), "INVALID_ARTIFACT_NAME")
        data = output_bytes(name, value)
        (path / name).write_bytes(data)
        manifest[name] = sha256(data)
    (path / "artifact_hashes.json").write_bytes(canonical_bytes(manifest) + b"\n")


def verify_artifacts(path: Path) -> dict:
    manifest = load_json(path / "artifact_hashes.json")
    require(isinstance(manifest, dict), "INVALID_ARTIFACT_MANIFEST")
    actual_files = {p.name for p in path.iterdir() if p.is_file()}
    require(actual_files == set(manifest) | {"artifact_hashes.json"}, "ARTIFACT_ACCOUNTING_MISMATCH")
    for name, expected in manifest.items():
        require(Path(name).name == name, "INVALID_ARTIFACT_NAME")
        require(sha256((path / name).read_bytes()) == expected, "ARTIFACT_HASH_MISMATCH", name)
    report = load_json(path / "v164_readiness_report.json")
    canary = load_json(path / "v164_phase_f_canary_plan.json")
    require(report["authorized_to_execute"] is False and canary["authorized_to_execute"] is False,
            "PHASE_F_AUTHORIZATION_FORBIDDEN")
    require(canary["records"] == [], "REFERENCE_CANARY_MUST_BE_EMPTY")
    return {"file_count": len(manifest), "manifest_sha256": digest(manifest)}


def replay_gate(first: Path, second: Path) -> dict:
    verify_artifacts(first)
    verify_artifacts(second)
    left, right = {p.name for p in first.iterdir()}, {p.name for p in second.iterdir()}
    require(left == right, "REPLAY_FILESET_MISMATCH")
    for name in sorted(left):
        require((first / name).read_bytes() == (second / name).read_bytes(), "REPLAY_BYTES_MISMATCH", name)
    return {"status": "BYTE_AND_HASH_EQUALITY_PASS", "files": len(left)}


