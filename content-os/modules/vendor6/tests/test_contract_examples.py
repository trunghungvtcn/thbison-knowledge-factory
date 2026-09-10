from pathlib import Path
import json
from thbison_v6.contract_validate import validate_payload, assert_valid
from thbison_v6.hashutil import evidence_snapshot_sha256, article_content_sha256

ROOT = Path(__file__).resolve().parents[1]


def test_examples_validate_against_frozen_schemas():
    for p in (ROOT / "contracts" / "examples").glob("*.json"):
        payload = json.loads(p.read_text(encoding="utf-8"))
        errors = validate_payload(p.stem, payload)
        assert errors == [], (p.name, errors)


def test_example_hashes_match_behavior_profile():
    bundle = json.loads((ROOT / "contracts/examples/EvidenceBundle.json").read_text())
    assert evidence_snapshot_sha256(bundle) == bundle["snapshot_sha256"]
    article = json.loads((ROOT / "contracts/examples/ArticlePackage.json").read_text())
    assert article_content_sha256(article) == article["content_sha256"]


def test_openapi_present():
    spec = json.loads((ROOT / "contracts" / "openapi.json").read_text(encoding="utf-8"))
    assert spec.get("info", {}).get("version") or spec.get("openapi")
