"""Source-only pytest runner for GitHub CI (JOB J2).

The verify workflow previously claimed to run source-only tests but invoked
the full suite. Six tests then failed with FileNotFoundError on paths that
.gitignore correctly keeps off GitHub (private corpus, generated zip,
farming_input).

This runner deselects those nodeids when the required asset is absent.
Deselected tests are reported as NOT_RUN in a sidecar JSON. They are not
marked skip or xfail, and tests/*.py is not modified.

The inventory is closed and matches GitHub Actions run 34429494332
(6 failed, 413 passed at 3f1f125). New asset-bound tests must be added
here or they will fail CI; that is intentional.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Diagnosed from Actions run 34429494332 / job offline-verify (exit 1).
ASSET_BOUND_TESTS: list[dict[str, Any]] = [
    {
        "asset": "v166/corpus/completion-001/frozen_corpus_manifest.json",
        "reason": "gitignored /v166/corpus/ (private frozen corpus; not shipped on GitHub)",
        "nodeids": [
            "tests/test_machine_admission.py::test_real_legacy_pdf_binding_and_proposal_tamper",
        ],
    },
    {
        "asset": ".kaggle-deploy/v161-no-write/package/v161-no-write.zip",
        "reason": "gitignored *.zip (generated Kaggle no-write package)",
        "nodeids": [
            "tests/test_v161_bootstrap.py::test_generated_bootstrap_matches_local_plan[expanded]",
            "tests/test_v161_bootstrap.py::test_generated_bootstrap_matches_local_plan[archive]",
        ],
    },
    {
        "asset": "farming_input/resource_manifest.csv",
        "reason": "gitignored /farming_input/ (private source corpus)",
        "nodeids": [
            "tests/test_v165_complete_record.py::test_A01_reject_pinned_baseline_change",
            "tests/test_v165_complete_record.py::test_A26_A32_real_no_accept_accounting",
            "tests/test_v165_complete_record.py::test_A30_A31_independent_replay_and_rehashed_tampering",
        ],
    },
]


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "UNKNOWN"
    return result.stdout.strip()


class SourceOnlyPlugin:
    """Deselect asset-bound tests; never skip/xfail them."""

    def __init__(self, root: Path, inventory: list[dict[str, Any]]) -> None:
        self.root = root
        self.inventory = inventory
        self.not_run: list[dict[str, str]] = []
        self.collected: list[str] = []
        self.stale: list[str] = []
        self.deselect: set[str] = set()
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = 0
        self.xfailed = 0
        self.xpassed = 0
        for entry in inventory:
            present = (root / entry["asset"]).exists()
            if present:
                continue
            for nodeid in entry["nodeids"]:
                self.deselect.add(nodeid)
                self.not_run.append(
                    {
                        "nodeid": nodeid,
                        "status": "NOT_RUN",
                        "asset": entry["asset"],
                        "reason": entry["reason"],
                    }
                )

    def pytest_collection_modifyitems(self, config: pytest.Config, items: list[pytest.Item]) -> None:
        self.collected = [item.nodeid for item in items]
        collected_set = set(self.collected)
        for nodeid in sorted({nid for entry in self.inventory for nid in entry["nodeids"]}):
            if nodeid not in collected_set:
                self.stale.append(nodeid)
        if self.stale:
            raise pytest.UsageError(
                "J2 inventory nodeids were not collected (renamed or removed?): "
                + ", ".join(self.stale)
            )
        deselected = []
        remaining = []
        for item in items:
            if item.nodeid in self.deselect:
                deselected.append(item)
            else:
                remaining.append(item)
        items[:] = remaining
        if deselected:
            config.hook.pytest_deselected(items=deselected)

    def pytest_terminal_summary(self, terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
        stats = terminalreporter.stats
        self.passed = len(stats.get("passed", []))
        self.failed = len(stats.get("failed", []))
        self.skipped = len(stats.get("skipped", []))
        self.errors = len(stats.get("error", []))
        self.xfailed = len(stats.get("xfailed", []))
        self.xpassed = len(stats.get("xpassed", []))
        terminalreporter.write_sep("=", "J2 source-only summary")
        terminalreporter.write_line(
            "ran={ran} passed={passed} failed={failed} skipped={skipped} "
            "error={error} xfailed={xfailed} xpassed={xpassed} not_run={not_run}".format(
                ran=self.passed + self.failed + self.skipped + self.errors + self.xfailed + self.xpassed,
                passed=self.passed,
                failed=self.failed,
                skipped=self.skipped,
                error=self.errors,
                xfailed=self.xfailed,
                xpassed=self.xpassed,
                not_run=len(self.not_run),
            )
        )
        for row in self.not_run:
            terminalreporter.write_line("NOT_RUN {nodeid} ({asset})".format(**row))


def annotate_junit(path: Path, head_sha: str, not_run: list[dict[str, str]]) -> None:
    if not path.exists():
        return
    tree = ET.parse(path)
    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        return
    properties = suite.find("properties")
    if properties is None:
        properties = ET.Element("properties")
        suite.insert(0, properties)
    for name, value in (
        ("job_id", "J2"),
        ("head_sha", head_sha),
        ("mode", "source-only"),
        ("not_run_count", str(len(not_run))),
        ("not_run_nodeids", ",".join(row["nodeid"] for row in not_run)),
    ):
        prop = ET.SubElement(properties, "property")
        prop.set("name", name)
        prop.set("value", value)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--junitxml",
        default="j2-junit.xml",
        help="JUnit XML path (pytest --junitxml)",
    )
    parser.add_argument(
        "--summary-json",
        default="j2-summary.json",
        help="Sidecar JSON with NOT_RUN inventory and counts",
    )
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="Repository root (default: inferred from this file)",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra pytest args after --",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    junitxml = Path(args.junitxml)
    if not junitxml.is_absolute():
        junitxml = Path.cwd() / junitxml
    summary_path = Path(args.summary_json)
    if not summary_path.is_absolute():
        summary_path = Path.cwd() / summary_path

    extra = list(args.pytest_args)
    if extra and extra[0] == "--":
        extra = extra[1:]

    plugin = SourceOnlyPlugin(root, ASSET_BOUND_TESTS)
    pytest_args = [
        "-q",
        "--tb=short",
        f"--junitxml={junitxml}",
        "-o",
        "junit_family=xunit2",
        "-o",
        "junit_logging=no",
        *extra,
    ]
    exit_code = pytest.main(pytest_args, plugins=[plugin])
    head_sha = git_head(root)
    annotate_junit(junitxml, head_sha, plugin.not_run)
    ran = plugin.passed + plugin.failed + plugin.skipped + plugin.errors + plugin.xfailed + plugin.xpassed
    summary = {
        "job_id": "J2",
        "head_sha": head_sha,
        "python": sys.version,
        "mode": "source-only",
        "diagnosed_ci_run": "34429494332",
        "collected": len(plugin.collected),
        "ran": ran,
        "passed": plugin.passed,
        "failed": plugin.failed,
        "skipped": plugin.skipped,
        "error": plugin.errors,
        "xfailed": plugin.xfailed,
        "xpassed": plugin.xpassed,
        "not_run_count": len(plugin.not_run),
        "not_run": plugin.not_run,
        "junitxml": str(junitxml),
        "exit_code": int(exit_code),
        "skip_or_xfail_used_by_runner": False,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"j2_summary": str(summary_path), "junitxml": str(junitxml), "exit_code": int(exit_code)}, sort_keys=True))
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
