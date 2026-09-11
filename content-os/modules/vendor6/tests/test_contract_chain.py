"""Regression: reviewer reproduce.py must exit 0 on this source. Old source failed."""

from pathlib import Path
import json
from jsonschema import Draft202012Validator, FormatChecker

from thbison_v6.harness.lab import Lab
from thbison_v6.contract_validate import validate_payload, assert_valid


ROOT = Path(__file__).resolve().parents[1]
NAMES = [
    ("brief", "ContentBrief"),
    ("bundle", "EvidenceBundle"),
    ("article", "ArticlePackage"),
    ("approval", "ApprovalRecord"),
    ("receipt", "PublicationReceipt"),
]


def test_reference_chain_payloads_match_frozen_schemas(tmp_path):
    chain = Lab(mode="REFERENCE_ONLY", root=tmp_path).run_reference_chain()
    for key, name in NAMES:
        errors = validate_payload(name, chain[key])
        assert errors == [], (name, errors)


def test_cross_hop_bindings(tmp_path):
    chain = Lab(mode="REFERENCE_ONLY", root=tmp_path).run_reference_chain()
    brief, bundle, article, approval, receipt = (
        chain["brief"],
        chain["bundle"],
        chain["article"],
        chain["approval"],
        chain["receipt"],
    )
    assert article["brief_id"] == brief["brief_id"]
    assert article["brief_revision"] == brief["brief_revision"]
    assert article["bundle_id"] == bundle["bundle_id"]
    assert article["evidence_snapshot_sha256"] == bundle["snapshot_sha256"]
    assert approval["article_id"] == article["article_id"]
    assert approval["article_revision"] == article["article_revision"]
    assert approval["content_sha256"] == article["content_sha256"]
    assert approval["evidence_snapshot_sha256"] == article["evidence_snapshot_sha256"]
    assert receipt["article_id"] == article["article_id"]
    assert receipt["article_revision"] == article["article_revision"]
    assert receipt["content_sha256"] == article["content_sha256"]
    assert receipt["destination_id"] == approval["destination_id"]
    # metadata must not leak into contract objects
    for obj in (brief, bundle, article, approval, receipt):
        assert not any(k.startswith("_") for k in obj)


def test_reviewer_reproduce_script_exit_zero(tmp_path):
    # inlined reproduce.py logic
    chain = Lab(mode="REFERENCE_ONLY", root=tmp_path).run_reference_chain()
    report = {}
    for key, name in NAMES:
        schema = json.loads(next(p for p in ROOT.rglob(name + ".json") if p.parent.name == "schemas").read_text())
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(chain[key]))
        report[name] = {"errors": len(errors)}
    assert all(v["errors"] == 0 for v in report.values()), report
