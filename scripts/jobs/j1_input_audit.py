#!/usr/bin/env python3
"""J1 read-only input inventory and hash verifier.

Cross-checks migration_assets.json, legacy Windows/POSIX locator maps, and
runtime paths. Never writes into recovered data, fixtures, or algorithm trees.
Re-running must leave those inputs byte-identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
JOBS = Path(__file__).resolve().parent
if str(JOBS) not in sys.path:
    sys.path.insert(0, str(JOBS))

from j1_runtime_catalog import (  # noqa: E402
    LEGACY_MANIFEST_MODULE,
    MACHINE_ADMISSION_LEGACY,
    MIGRATION_ASSETS,
    POSIX_FILE_MAP_MANIFESTS,
    SAMPLE_INPUT_PATHS,
    TEST_ONLY_FIXTURES,
    V161_PARQUET_EXPECTED_ROOT,
    V161_PARQUET_PINS,
    WINDOWS_LOCATOR_MANIFESTS,
)
from kf_pilot.legacy_manifest import (  # noqa: E402
    LegacyManifestPathError,
    resolve_manifest_entries,
)

SHA256_HEX = 64
WRITE_PREFIXES = ("scripts/jobs/j1_", "tests/jobs/test_j1_", "docs/jobs/J1")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def git_ls_files(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def classify(path: str, destination: str | None = None) -> str:
    posix = path.replace("\\", "/")
    if destination == "NOTION_OR_EXTERNAL_CUSTODY":
        return "REAL_INPUT_EXTERNAL"
    if posix.startswith(("fixtures/", "sample_input/", "staging/")):
        return "SIMULATED"
    if posix.startswith(("src/", "scripts/", "tests/", "notebooks/", "config/")):
        if posix == "config/manual_decisions.csv":
            return "REAL_INPUT_EXTERNAL"
        return "SOURCE"
    if posix.startswith(
        (
            "v16_migration/",
            "v162/",
            "v163/",
            "v164/",
            "v165/",
            "v166/",
            ".kaggle-deploy/",
            "autonomous/artifacts/",
            "vendor/",
        )
    ):
        return "HISTORICAL_ARTIFACT"
    if posix.startswith(
        ("farming_input/", "data/", "datasets/", "recovery/", "data-staging/", "private-audit/")
    ):
        return "REAL_INPUT_EXTERNAL"
    if posix.endswith((".parquet", ".duckdb", ".pdf")):
        return "REAL_INPUT_EXTERNAL"
    return "SOURCE"


def record(
    *,
    path: str,
    status: str,
    provenance: str,
    expected_sha256: str | None = None,
    actual_sha256: str | None = None,
    bytes_count: int | None = None,
    source: str,
    note: str = "",
    runtime_required: bool = False,
) -> dict[str, Any]:
    item = {
        "path": path.replace("\\", "/"),
        "locator": path,
        "status": status,
        "provenance": provenance,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "bytes": bytes_count,
        "source": source,
        "runtime_required": runtime_required,
    }
    if note:
        item["note"] = note
    return item


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == SHA256_HEX and all(
        ch in "0123456789abcdef" for ch in value
    )


def looks_like_path(key: str) -> bool:
    if not isinstance(key, str) or not key:
        return False
    if key in {"corpus_revision", "run_config_sha256", "v165_artifact_manifest_sha256"}:
        return False
    if "\\" in key or "/" in key:
        return True
    return key.endswith((".json", ".jsonl", ".py", ".csv", ".html", ".md", ".sql"))


def extract_locator_map(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    if all(looks_like_path(k) and is_sha256(v) for k, v in payload.items()):
        return {k: v for k, v in payload.items()}
    for key in ("files", "baseline_pins"):
        block = payload.get(key)
        if isinstance(block, dict):
            return {k: v for k, v in block.items() if looks_like_path(k) and is_sha256(v)}
    return {}


def dialect_for(locators: Iterable[str]) -> str:
    return "windows-relative-v1" if any("\\" in item for item in locators) else "posix-relative-v1"


def check_locators(
    repo: Path, locators: dict[str, str], source: str, *, anchor: Path | None = None
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not locators:
        return items
    dialect = dialect_for(locators)
    candidates = [repo]
    if anchor is not None and anchor.resolve() != repo.resolve():
        candidates.append(anchor)

    best_root = repo
    best_resolved: dict[str, Path] | None = None
    best_present = -1
    last_error: str | None = None
    for candidate in candidates:
        try:
            resolved = resolve_manifest_entries(candidate, locators, dialect=dialect)
        except LegacyManifestPathError as exc:
            last_error = str(exc)
            continue
        present = sum(1 for path in resolved.values() if path.is_file())
        if present > best_present:
            best_present = present
            best_root = candidate
            best_resolved = resolved
    if best_resolved is None:
        for locator, expected in locators.items():
            items.append(
                record(
                    path=locator,
                    status="UNSAFE_LOCATOR",
                    provenance=classify(locator),
                    expected_sha256=expected,
                    source=source,
                    note=last_error or "legacy_manifest rejected locator",
                )
            )
        return items
    root_note = ""
    if best_root.resolve() != repo.resolve():
        root_note = f"resolved against {best_root.relative_to(repo).as_posix() or '.'}"
    for locator, expected in locators.items():
        path = best_resolved[locator]
        provenance = classify(locator)
        if not path.is_file():
            items.append(
                record(
                    path=locator,
                    status="MISSING",
                    provenance=provenance,
                    expected_sha256=expected,
                    source=source,
                    note="path resolved inside authorized root but file is absent"
                    + (f"; {root_note}" if root_note else ""),
                )
            )
            continue
        actual = sha256_file(path)
        status = "OK" if actual == expected else "HASH_MISMATCH"
        note = root_note
        if status == "HASH_MISMATCH":
            extra = "nested historical pin; GitHub migrated_sha256 is authoritative for recovered tree"
            note = f"{extra}; {root_note}" if root_note else extra
        items.append(
            record(
                path=str(path.relative_to(repo)) if path.is_relative_to(repo) else locator,
                status=status,
                provenance=classify(str(path.relative_to(repo)) if path.is_relative_to(repo) else locator),
                expected_sha256=expected,
                actual_sha256=actual,
                bytes_count=path.stat().st_size,
                source=source,
                note=note,
            )
        )
    return items


def audit_github_assets(root: Path, manifest: dict[str, Any], tracked: set[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    github_paths: set[str] = set()
    for asset in manifest.get("assets", []):
        dest = asset.get("destination")
        if dest == "GITHUB":
            rel = asset["relative_path"]
            github_paths.add(rel)
            path = root / rel
            expected = asset.get("migrated_sha256")
            provenance = classify(rel, dest)
            if not path.is_file():
                items.append(
                    record(
                        path=rel,
                        status="MISSING",
                        provenance=provenance,
                        expected_sha256=expected,
                        bytes_count=asset.get("bytes"),
                        source=MIGRATION_ASSETS,
                    )
                )
                continue
            actual = sha256_file(path)
            status = "OK" if actual == expected else "HASH_MISMATCH"
            note = ""
            if asset.get("original_sha256") != expected:
                note = "original_sha256 differs from migrated_sha256 (intentional transform recorded)"
            if status == "HASH_MISMATCH":
                note = (
                    "working-tree SHA256 != migrated_sha256; "
                    f"original_sha256={asset.get('original_sha256')}"
                )
            items.append(
                record(
                    path=rel,
                    status=status,
                    provenance=provenance,
                    expected_sha256=expected,
                    actual_sha256=actual,
                    bytes_count=path.stat().st_size,
                    source=MIGRATION_ASSETS,
                    note=note,
                )
            )
        elif dest == "NOTION_OR_EXTERNAL_CUSTODY":
            locator = asset.get("destination_locator") or asset.get("source_ref") or asset.get("asset_id")
            items.append(
                record(
                    path=locator,
                    status="MISSING_EXTERNAL",
                    provenance="REAL_INPUT_EXTERNAL",
                    expected_sha256=asset.get("migrated_sha256") or asset.get("original_sha256"),
                    bytes_count=asset.get("bytes"),
                    source=MIGRATION_ASSETS,
                    note=(
                        f"status={asset.get('status')}; custody={asset.get('source_ref')}; "
                        "do not publish corpus to GitHub"
                    ),
                )
            )
    exempt = {MIGRATION_ASSETS}
    def job_owned(rel: str) -> bool:
        return (
            rel.startswith("scripts/jobs/j1_")
            or rel.startswith("tests/jobs/test_j1_")
            or rel.startswith("docs/jobs/J1")
        )

    for extra in sorted(p for p in github_paths - tracked if not job_owned(p)):
        items.append(
            record(
                path=extra,
                status="EXTRA_IN_MANIFEST",
                provenance=classify(extra),
                source=MIGRATION_ASSETS,
            )
        )
    for missing in sorted(p for p in (tracked - exempt) - github_paths if not job_owned(p)):
        items.append(
            record(
                path=missing,
                status="TRACKED_NOT_IN_MANIFEST",
                provenance=classify(missing),
                source="git-ls-files",
            )
        )
    return items


def audit_runtime(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for role, rel in MACHINE_ADMISSION_LEGACY.items():
        path = root / rel
        provenance = classify(rel)
        if not path.is_file():
            items.append(
                record(
                    path=rel,
                    status="MISSING",
                    provenance=provenance,
                    source="runtime:machine_admission.LEGACY",
                    runtime_required=True,
                    note=f"role={role}",
                )
            )
            continue
        items.append(
            record(
                path=rel,
                status="OK",
                provenance=provenance,
                actual_sha256=sha256_file(path),
                bytes_count=path.stat().st_size,
                source="runtime:machine_admission.LEGACY",
                runtime_required=True,
                note=f"role={role}",
            )
        )
    for rel in (*SAMPLE_INPUT_PATHS, *TEST_ONLY_FIXTURES):
        path = root / rel
        items.append(
            record(
                path=rel,
                status="OK" if path.is_file() else "MISSING",
                provenance=classify(rel),
                actual_sha256=sha256_file(path) if path.is_file() else None,
                bytes_count=path.stat().st_size if path.is_file() else None,
                source="runtime:test_only_or_sample",
                runtime_required=True,
            )
        )
    for name, expected in V161_PARQUET_PINS.items():
        candidate = root / V161_PARQUET_EXPECTED_ROOT / name
        items.append(
            record(
                path=f"{V161_PARQUET_EXPECTED_ROOT}/{name}",
                status="MISSING_EXTERNAL" if not candidate.is_file() else (
                    "OK" if sha256_file(candidate) == expected else "HASH_MISMATCH"
                ),
                provenance="REAL_INPUT_EXTERNAL",
                expected_sha256=expected,
                actual_sha256=sha256_file(candidate) if candidate.is_file() else None,
                source="runtime:v161_parquet_pins",
                runtime_required=True,
                note="outside Git by architecture; independent custody required; do not upload to GitHub",
            )
        )
    decisions = root / "config" / "manual_decisions.csv"
    items.append(
        record(
            path="config/manual_decisions.csv",
            status="MISSING_EXTERNAL" if not decisions.is_file() else "PRESENT_IGNORED_PATH",
            provenance="REAL_INPUT_EXTERNAL",
            actual_sha256=sha256_file(decisions) if decisions.is_file() else None,
            source="runtime:reviewed_decisions",
            runtime_required=True,
            note="gitignored; registered as external:manual_decisions-v2-reviewed.csv",
        )
    )
    return items


def audit_nested_manifests(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in (*WINDOWS_LOCATOR_MANIFESTS, *POSIX_FILE_MAP_MANIFESTS):
        path = root / rel
        if not path.is_file() or rel in seen:
            if not path.is_file():
                items.append(
                    record(
                        path=rel,
                        status="MISSING",
                        provenance=classify(rel),
                        source="nested-manifest-list",
                    )
                )
            continue
        seen.add(rel)
        payload = json.loads(path.read_text(encoding="utf-8"))
        locators = extract_locator_map(payload)
        if not locators:
            items.append(
                record(
                    path=rel,
                    status="NOT_LOCATOR_MAP",
                    provenance=classify(rel),
                    actual_sha256=sha256_file(path),
                    source="nested-manifest-list",
                    note="metadata manifest (hashed names, not filesystem locators)",
                )
            )
            continue
        items.extend(check_locators(root, locators, source=rel, anchor=path.parent))
    return items


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item["status"] for item in items)
    provenance = Counter(item["provenance"] for item in items)
    runtime = [item for item in items if item.get("runtime_required")]
    missing = [
        item
        for item in items
        if item["status"] in {"MISSING", "MISSING_EXTERNAL", "UNSAFE_LOCATOR", "TRACKED_NOT_IN_MANIFEST"}
    ]
    mismatches = [item for item in items if item["status"] == "HASH_MISMATCH"]
    return {
        "item_count": len(items),
        "status_counts": dict(sorted(counts.items())),
        "provenance_counts": dict(sorted(provenance.items())),
        "runtime_required_count": len(runtime),
        "runtime_required_ok": sum(1 for item in runtime if item["status"] == "OK"),
        "missing_count": len(missing),
        "hash_mismatch_count": len(mismatches),
    }


def stable_report(report: dict[str, Any]) -> dict[str, Any]:
    copy = json.loads(json.dumps(report))
    copy.pop("generated_at", None)
    return copy


def fingerprint(report: dict[str, Any]) -> str:
    return sha256_bytes(canonical_dumps(stable_report(report)).encode("utf-8"))


def build_report(root: Path) -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tracked = git_ls_files(root)
    manifest_path = root / MIGRATION_ASSETS
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    items.extend(audit_github_assets(root, manifest, tracked))
    items.extend(audit_runtime(root))
    items.extend(audit_nested_manifests(root))
    items.append(
        record(
            path=LEGACY_MANIFEST_MODULE,
            status="OK" if (root / LEGACY_MANIFEST_MODULE).is_file() else "MISSING",
            provenance="SOURCE",
            actual_sha256=sha256_file(root / LEGACY_MANIFEST_MODULE)
            if (root / LEGACY_MANIFEST_MODULE).is_file()
            else None,
            source="j1_runtime_catalog",
            runtime_required=True,
            note="resolver only; J1 does not change algorithm",
        )
    )
    items.sort(key=lambda item: (item["path"], item["source"], item["status"]))
    exceptions = [
        item
        for item in items
        if item["status"] not in {"OK", "NOT_LOCATOR_MAP"}
        or item.get("runtime_required")
    ]
    missing_precise = [
        {
            "path": item["path"],
            "status": item["status"],
            "expected_sha256": item.get("expected_sha256"),
            "actual_sha256": item.get("actual_sha256"),
            "provenance": item["provenance"],
            "source": item["source"],
            "note": item.get("note", ""),
            "publish_to_github": False if item["provenance"] == "REAL_INPUT_EXTERNAL" else None,
        }
        for item in items
        if item["status"] in {
            "MISSING",
            "MISSING_EXTERNAL",
            "HASH_MISMATCH",
            "UNSAFE_LOCATOR",
            "TRACKED_NOT_IN_MANIFEST",
            "EXTRA_IN_MANIFEST",
        }
    ]
    report = {
        "job_id": "J1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_sha": commit,
        "read_only": True,
        "inputs_mutated": False,
        "migration_job_id": manifest.get("job_id"),
        "legacy_manifest_resolver": LEGACY_MANIFEST_MODULE,
        "summary": summarize(items),
        "exceptions": exceptions,
        "missing_or_mismatch": missing_precise,
        "runtime_required": [item for item in items if item.get("runtime_required")],
        "inventory": items,
        "do_not": [
            "merge",
            "deploy",
            "enable_scheduler",
            "write_notion",
            "call_paid_model",
            "upload_real_corpus_to_github",
        ],
    }
    report["inventory_sha256"] = fingerprint(report)
    return report


def assert_output_allowed(path: Path, root: Path) -> None:
    resolved = path.resolve()
    if not str(resolved).startswith(str(root.resolve())):
        if resolved.parent == Path("/tmp") or "/tmp/" in str(resolved):
            return
        raise SystemExit(f"refusing to write outside repo or tmp: {resolved}")
    rel = resolved.relative_to(root.resolve()).as_posix()
    if rel.startswith(".git/"):
        raise SystemExit("refusing to write .git")
    if any(rel.startswith(prefix) or Path(rel).name.startswith("J1") for prefix in WRITE_PREFIXES):
        return
    if rel.startswith("docs/jobs/") or rel.startswith("scripts/jobs/") or rel.startswith("tests/jobs/"):
        return
    raise SystemExit(f"J1 may only write job-owned paths, got {rel}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="J1 read-only recovered-input audit")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, help="optional JSON report path")
    parser.add_argument("--missing-out", type=Path, help="optional missing/mismatch JSON path")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="omit full inventory array from --out (sha256 still covers the full set)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    before = {}
    sample_targets = [root / rel for rel in (*SAMPLE_INPUT_PATHS, *TEST_ONLY_FIXTURES)]
    sample_targets.append(root / MIGRATION_ASSETS)
    for path in sample_targets:
        if path.is_file():
            before[str(path)] = sha256_file(path)
    report = build_report(root)
    for path, digest in before.items():
        after = sha256_file(Path(path))
        if after != digest:
            raise SystemExit(f"J1 mutated input {path}")
    text = canonical_dumps(report)
    if args.out:
        assert_output_allowed(args.out, root)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = report
        if args.compact:
            payload = dict(report)
            payload["inventory"] = f"omitted:{len(report['inventory'])}_rows; rerun without --compact"
            payload["compact"] = True
        args.out.write_text(canonical_dumps(payload), encoding="utf-8")
    if args.missing_out:
        assert_output_allowed(args.missing_out, root)
        args.missing_out.parent.mkdir(parents=True, exist_ok=True)
        args.missing_out.write_text(canonical_dumps(report["missing_or_mismatch"]), encoding="utf-8")
    if not args.out:
        sys.stdout.write(text)
    print(
        json.dumps(
            {
                "job_id": "J1",
                "status": "AUDIT_COMPLETE",
                "inventory_sha256": report["inventory_sha256"],
                "summary": report["summary"],
                "inputs_mutated": False,
            },
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
