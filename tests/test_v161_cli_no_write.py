import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cli_produces_typed_no_write_artifacts(tmp_path):
    command = [
        sys.executable,
        str(ROOT / "notebooks/30_migrate_v16.py"),
        "--input",
        str(ROOT / "fixtures/v161/legacy_rows.json"),
        "--notion-schema",
        str(ROOT / "fixtures/v161/current_notion_schema.json"),
        "--live-review-snapshot",
        str(ROOT / "fixtures/v161/live_review_snapshot.json"),
        "--output-dir",
        str(tmp_path),
        "--run-id",
        "TEST-NO-WRITE",
    ]
    subprocess.run(command, check=True)
    report = json.loads((tmp_path / "prepublication_validation_report.json").read_text(encoding="utf-8"))
    plan = json.loads((tmp_path / "notion_typed_update_plan.json").read_text(encoding="utf-8"))
    assert report["remote_writes"] == 0
    assert report["production_mutation_authorized"] is False
    assert plan["created_count"] == 0
    assert all(item["operation"] == "UPDATE" for item in plan["operations"])
    assert (tmp_path / "notion_schema_diff.json").exists()
