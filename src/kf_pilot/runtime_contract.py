from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import subprocess
import time


class ContractError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class RunContract:
    job_id: str
    task_type: str
    domain: str
    repository: str
    code_commit: str
    dataset_snapshot_id: str
    input_manifest_sha256: str
    mode: str
    allowed_outputs: tuple[str, ...]
    attempt_budget: int
    timeout_seconds: int
    prompt_version: str = "NOT_APPLICABLE"
    schema_version: str = "v16"
    policy_version: str = "v16"
    model_version: str = "NOT_APPLICABLE"
    token_budget: int = 0
    cost_budget_usd: float = 0.0

    @classmethod
    def load(cls, path: Path) -> "RunContract":
        raw = json.loads(path.read_text(encoding="utf-8"))
        required = {
            "job_id", "task_type", "domain", "repository", "code_commit",
            "dataset_snapshot_id", "input_manifest_sha256", "mode",
            "allowed_outputs", "attempt_budget", "timeout_seconds",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ContractError(f"missing contract fields: {missing}")
        raw["allowed_outputs"] = tuple(raw["allowed_outputs"])
        contract = cls(**raw)
        contract.validate()
        return contract

    def validate(self) -> None:
        if self.mode != "TEST_ONLY":
            raise ContractError("only TEST_ONLY mode is authorized by this launcher")
        if len(self.code_commit) != 40 or any(c not in "0123456789abcdef" for c in self.code_commit.lower()):
            raise ContractError("code_commit must be a full 40-character SHA")
        if len(self.input_manifest_sha256) != 64:
            raise ContractError("input_manifest_sha256 must be SHA256")
        if self.attempt_budget < 1 or self.attempt_budget > 3:
            raise ContractError("attempt_budget must be between 1 and 3")
        if self.timeout_seconds < 1 or self.timeout_seconds > 300:
            raise ContractError("timeout_seconds must be between 1 and 300")
        if not self.allowed_outputs:
            raise ContractError("allowed_outputs must not be empty")

    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_bytes(asdict(self))).hexdigest()


def current_commit(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


def resolve_verified_asset(snapshot_path: Path, expected_sha256: str) -> Path:
    resolved = snapshot_path.resolve(strict=True)
    actual = sha256_file(resolved)
    if actual != expected_sha256.lower():
        raise ContractError(f"snapshot hash mismatch: expected {expected_sha256}, got {actual}")
    return resolved


def execute_test_only(contract: RunContract, repo: Path, snapshot_path: Path, output_dir: Path) -> dict[str, Any]:
    started = time.monotonic()
    actual_commit = current_commit(repo)
    if actual_commit != contract.code_commit:
        raise ContractError(f"commit mismatch: expected {contract.code_commit}, got {actual_commit}")
    asset = resolve_verified_asset(snapshot_path, contract.input_manifest_sha256)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "submission-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {}
    key = contract.fingerprint()
    if key in ledger:
        return {"status": "DUPLICATE_NOOP", "fingerprint": key, "receipt": ledger[key]}
    if time.monotonic() - started > contract.timeout_seconds:
        raise TimeoutError("run timeout exceeded")
    report = {
        "status": "TEST_ONLY_COMPLETE",
        "job_id": contract.job_id,
        "code_commit": actual_commit,
        "dataset_snapshot_id": contract.dataset_snapshot_id,
        "input_sha256": sha256_file(asset),
        "input_bytes": asset.stat().st_size,
        "processor": "existing-source-integrity-pass",
        "production_writes": False,
        "notion_sync_plan": "DRY_RUN",
        "fingerprint": key,
    }
    report_path = output_dir / "run-report.json"
    report_path.write_bytes(canonical_bytes(report) + b"\n")
    ledger[key] = {"report": report_path.name, "report_sha256": sha256_file(report_path)}
    ledger_path.write_bytes(canonical_bytes(ledger) + b"\n")
    return report

