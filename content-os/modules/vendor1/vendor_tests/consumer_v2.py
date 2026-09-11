"""Vendor 2 fixture client: consume a ContentBrief without renaming fields."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor_kit" / "tools"))
from contracts import validate

REQUIRED = [
    "contract_version","project_id","data_class","brief_id","brief_revision","research_id",
    "scope","title","audience","intent","primary_keyword","secondary_keywords","questions",
    "outline","evidence_requirements","product_refs","proposed_publish_at","editorial_constraints","origin",
]

def consume(path: str) -> dict:
    brief = json.loads(Path(path).read_text(encoding="utf-8"))
    validate("ContentBrief", brief)
    for k in REQUIRED:
        if k not in brief:
            raise SystemExit(f"missing {k}")
    # Must not invent defaults
    return {"accepted": True, "brief_id": brief["brief_id"], "revision": brief["brief_revision"]}

if __name__ == "__main__":
    print(json.dumps(consume(sys.argv[1])))
