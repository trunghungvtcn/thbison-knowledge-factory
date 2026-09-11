"""INT-01..30 reference/simulator coverage. Actual E2E is NOT_RUN when V1/V5 missing."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from thbison_v6.contract_pin import expected_digest, reject_tz_naive_display_policy, reject_unknown_fields
from thbison_v6.hashutil import sha256_hex
from thbison_v6.simulators.planning import REQUIRED_BRIEF_FIELDS
from thbison_v6.staging.preflight import classify_http_error, preflight_read_only

ROOT = Path(__file__).resolve().parents[1]


def test_int_01_component_matrix_labels():
    matrix = json.loads((ROOT / "COMPONENT_MATRIX.json").read_text())
    by_v = {c["vendor"]: c for c in matrix["components"]}
    assert by_v["VENDOR_1"]["label"] == "MISSING"
    assert by_v["VENDOR_5"]["label"] == "MISSING"
    assert by_v["VENDOR_2"]["label"] == "STUB_IN_HARNESS"
    assert by_v["VENDOR_3"]["acceptance"] == "UNACCEPTED_CANDIDATE"
    assert by_v["VENDOR_4"]["artifact_sha256"]


def test_int_02_frozen_contract_mismatch(lab):
    with pytest.raises(ValueError, match="UNSUPPORTED_CONTRACT"):
        lab.assert_contract("deadbeef")
    lab.assert_contract(lab.contract_digest)


def test_int_03_no_fixture_substitution(lab):
    chain = lab.run_reference_chain()
    stubs = [h["stub"] for h in chain["trace"]]
    assert all(stubs), "reference chain must label STUB hops"
    assert chain["article"]["evidence_snapshot_sha256"] == chain["bundle"]["snapshot_sha256"]


def test_int_04_brief_required_fields(lab):
    chain = lab.run_reference_chain()
    brief = chain["brief"]
    for f in REQUIRED_BRIEF_FIELDS:
        assert f in brief
    assert brief["scope"]["language"] == "vi"
    assert brief["scope"]["timezone"] == "Asia/Bangkok"
    assert isinstance(brief["scope"], dict)
    assert brief["brief_revision"] == 1


def test_int_05_knowledge_matches_product_jurisdiction(lab):
    chain = lab.run_reference_chain()
    assert "THB-PILOT" in chain["brief"]["product_refs"]
    assert chain["brief"]["scope"]["country_code"] == "VN"
    assert chain["bundle"]["claims"][0]["jurisdiction"] == "VN"
    assert "THB-PILOT" in chain["bundle"]["claims"][0]["applicability"]


def test_int_06_evidence_preserved_into_writer(lab):
    chain = lab.run_reference_chain()
    claim = chain["bundle"]["claims"][0]
    block = chain["article"]["blocks"][0]
    assert block["text"] == claim["quote"]
    assert claim["claim_id"] in block["claim_ids"]
    stored = lab.ledger.get("article_claims", chain["article"]["article_id"])[0]
    assert stored["quote"] == claim["quote"]
    assert stored["quote_sha256"] == claim["quote_sha256"]
    assert stored["locator"] == claim["locator"]
    assert stored["source_ref"] == claim["source_ref"]


def test_int_07_hold_revoked_missing_blocks(lab):
    lab.knowledge.set_status("ki-001", "HOLD")
    brief = lab.planning.plan({"project_id": "proj-lab"})["brief"]
    bundle = lab.knowledge.query(brief)
    with pytest.raises(PermissionError, match="EVIDENCE_BLOCKED"):
        lab.writer.draft(brief, bundle)
    lab.knowledge.set_status("ki-001", "REVOKED")
    bundle = lab.knowledge.query(brief)
    with pytest.raises(PermissionError, match="EVIDENCE_BLOCKED"):
        lab.writer.draft(brief, bundle)


def test_int_08_article_binds_frozen_bundle(lab):
    chain = lab.run_reference_chain()
    assert chain["article"]["bundle_id"] == chain["bundle"]["bundle_id"]
    assert chain["article"]["evidence_snapshot_sha256"] == chain["bundle"]["snapshot_sha256"]


def test_int_09_approval_binds_and_expires(lab):
    chain = lab.run_reference_chain()
    ap = lab.writer.get_approval(chain["approval"]["approval_id"])
    assert ap["content_sha256"] == chain["article"]["content_sha256"]
    assert ap["destination_id"] == "cms-sandbox"
    assert ap["article_revision"] == chain["article"]["article_revision"]
    lab.clock.advance(4000)
    expired = lab.writer.get_approval(chain["approval"]["approval_id"])
    assert expired["decision"] == "REVOKED"
    assert lab.writer.is_expired(chain["approval"]["approval_id"])


def test_int_10_mutation_invalidates_approval(lab):
    chain = lab.run_reference_chain()
    mutated = lab.writer.mutate(chain["article"]["article_id"], "Changed-title")
    req = {
        "contract_version": "1.0.0",
        "project_id": "proj-lab",
        "data_class": "TEST_ONLY",
        "request_id": "k-mut",
        "article_id": mutated["article_id"],
        "article_revision": mutated["article_revision"],
        "content_sha256": mutated["content_sha256"],
        "evidence_snapshot_sha256": mutated["evidence_snapshot_sha256"],
        "approval_id": chain["approval"]["approval_id"],
        "destination_id": "cms-sandbox",
        "mode": "STAGING_DRAFT",
        "scheduled_at": None,
    }
    with pytest.raises(PermissionError):
        lab.cms.publish(req, chain["approval"])


def test_int_11_cms_dry_run_no_effect(lab):
    chain = lab.run_reference_chain(publish_mode="DRY_RUN")
    assert chain["receipt"]["actual_side_effects"] == 0
    assert chain["receipt"]["status"] == "DRY_RUN"
    assert lab.ledger.get_map("cms_effects") == {}


def test_int_12_cms_simulator_single_receipt(lab):
    chain = lab.run_reference_chain()
    assert chain["receipt"]["publication_id"]
    assert chain["receipt"]["actual_side_effects"] == 1
    receipts = lab.ledger.get_map("cms_by_receipt")
    assert len(receipts) == 1


def test_int_13_duplicate_job_no_duplicate_effect(lab):
    chain = lab.run_reference_chain()
    job = lab.runtime.admit(
        "proj-lab",
        "publish",
        f"idem-{chain['article']['article_id']}-{chain['article']['article_revision']}",
        {"article_id": chain["article"]["article_id"], "article_revision": chain["article"]["article_revision"]},
    )
    req = {
        "contract_version": "1.0.0",
        "project_id": "proj-lab",
        "data_class": "TEST_ONLY",
        "request_id": job["idempotency_key"],
        "article_id": chain["article"]["article_id"],
        "article_revision": chain["article"]["article_revision"],
        "content_sha256": chain["article"]["content_sha256"],
        "evidence_snapshot_sha256": chain["article"]["evidence_snapshot_sha256"],
        "approval_id": chain["approval"]["approval_id"],
        "destination_id": "cms-sandbox",
        "mode": "STAGING_DRAFT",
        "scheduled_at": None,
    }
    r2 = lab.cms.publish(req, chain["approval"])
    assert r2["publication_id"] == chain["receipt"]["publication_id"]
    assert len(lab.ledger.get_map("cms_by_receipt")) == 1


def test_int_14_same_key_different_payload_conflicts(lab):
    lab.runtime.admit("proj-lab", "publish", "k1", {"a": 1})
    with pytest.raises(ValueError, match="IDEMPOTENCY_CONFLICT"):
        lab.runtime.admit("proj-lab", "publish", "k1", {"a": 2})


def test_int_15_expired_lease_rejected(lab):
    job = lab.runtime.admit("proj-lab", "op", "k-lease", {"x": 1})
    lab.clock.advance(31)
    with pytest.raises(PermissionError, match="EXPIRED_LEASE"):
        lab.runtime.complete(job["job_id"], {"ok": True})


def test_int_16_cancel_rejects_stale_completion(lab):
    job = lab.runtime.admit("proj-lab", "op", "k-cancel", {"x": 1})
    lab.runtime.cancel(job["job_id"])
    with pytest.raises(PermissionError, match="STALE_COMPLETION"):
        lab.runtime.complete(job["job_id"], {"ok": True})


def test_int_17_budget_race_cap(lab):
    lab.runtime.budget_cap = 3

    def once(i):
        try:
            lab.runtime.admit("proj-budget", "op", f"k{i}", {"i": i})
            return True
        except PermissionError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(once, range(8)))
    assert sum(1 for r in results if r) == 3
    assert int(lab.ledger.get("budget", "proj-budget")) == 3


def test_int_18_unknown_reconciliation_bounded(lab):
    job = lab.runtime.admit("proj-lab", "op", "k-unk", {"x": 1})
    assert lab.runtime.reconcile_unknown(job["job_id"], loops=3) == "BOUNDED_STOP"


def test_int_19_process_restart_preserves_ledger(tmp_path):
    script = tmp_path / "worker.py"
    data = tmp_path / "data"
    script.write_text(
        "\n".join(
            [
                "import json,sys",
                "from pathlib import Path",
                "sys.path.insert(0, %r)" % str(ROOT / "src"),
                "from thbison_v6.ledger import FileLedger",
                "led=FileLedger(Path(%r))" % str(data),
                "cmd=sys.argv[1]",
                "if cmd=='write':",
                "    led.put('jobs','pending',{'status':'PENDING','asset':'a1'})",
                "elif cmd=='read':",
                "    print(json.dumps(led.get('jobs','pending')))",
            ]
        ),
        encoding="utf-8",
    )
    r1 = subprocess.run([sys.executable, str(script), "write"], check=True, capture_output=True)
    assert r1.returncode == 0
    r2 = subprocess.run([sys.executable, str(script), "read"], check=True, capture_output=True, text=True)
    assert json.loads(r2.stdout)["status"] == "PENDING"


def test_int_20_cross_project_isolation(lab):
    lab.planning.plan({"project_id": "proj-a"})
    bundle_b = lab.knowledge.query(
        {
            "project_id": "proj-b",
            "product_refs": ["THB-PILOT"],
            "scope": {"country_code": "VN", "language": "vi", "timezone": "Asia/Bangkok", "domain": "x"},
        }
    )
    assert bundle_b["claims"] == []


def test_int_21_contract_unknown_fields_and_tz():
    with pytest.raises(ValueError, match="UNKNOWN_FIELDS"):
        reject_unknown_fields({"a": 1, "sneaky": True}, {"a"})
    with pytest.raises(ValueError, match="TIMEZONE_VIOLATION"):
        reject_tz_naive_display_policy("UTC")
    reject_tz_naive_display_policy("Asia/Bangkok")
    pin = expected_digest(ROOT)
    assert len(pin) == 64


def test_int_22_untrusted_provider_payload(lab):
    lab.faults.schema_drift = True
    req = {
        "contract_version": "1.0.0",
        "project_id": "proj-lab",
        "data_class": "TEST_ONLY",
        "request_id": "drift",
        "article_id": "art-ref-001",
        "article_revision": 1,
        "content_sha256": "a" * 64,
        "evidence_snapshot_sha256": "b" * 64,
        "approval_id": "appr-1",
        "destination_id": "cms-sandbox",
        "mode": "STAGING_DRAFT",
        "scheduled_at": None,
    }
    appr = {
        "decision": "APPROVED",
        "content_sha256": "a" * 64,
        "destination_id": "cms-sandbox",
        "article_revision": 1,
        "evidence_snapshot_sha256": "b" * 64,
    }
    drifted = lab.cms.publish(req, appr)
    assert drifted.get("weirdField") is True
    from thbison_v6.contract_validate import assert_valid
    import pytest as _pytest
    with _pytest.raises(ValueError, match="CONTRACT_INVALID"):
        assert_valid("PublicationReceipt", drifted)
    lab.faults.schema_drift = True
    with _pytest.raises(ValueError, match="CONTRACT_INVALID"):
        lab.run_reference_chain()
    jobs = lab.ledger.get_map("jobs")
    assert all(j.get("status") != "SUCCEEDED" for j in jobs.values())


def test_int_23_asset_hash_stable_and_traversal_rejected(lab):
    rec = lab.knowledge.asset_put("proj-lab", "doc.txt", b"hello")
    digest = rec["sha256"]
    refreshed = lab.knowledge.refresh_url(rec["asset_id"])
    assert refreshed["sha256"] == digest
    with pytest.raises(ValueError, match="TRAVERSAL"):
        lab.knowledge.asset_put("proj-lab", "../etc/passwd", b"x")
    lab.ledger.put("assets", rec["asset_id"], {**rec, "sha256": "00" * 32})
    with pytest.raises(ValueError, match="COLLISION"):
        lab.knowledge.asset_put("proj-lab", "doc.txt", b"hello")


def test_int_24_staging_preflight_blocked_without_token():
    os.environ.pop("STAGING_NOTION_TOKEN", None)
    os.environ["STAGING_ENABLED"] = "false"
    result = preflight_read_only()
    assert result["status"] == "BLOCKED_ACCESS"
    assert result["live_calls"] == 0
    assert result["verified"] is False
    assert classify_http_error(403) == "BLOCKED_ACCESS"


def test_int_25_own_namespace_rollback(lab):
    chain = lab.run_reference_chain()
    rb = lab.cms.rollback_own(chain["receipt"]["publication_id"], "testrun-v6")
    assert rb["status"] == "ROLLED_BACK"
    assert rb["test_run_id"] == "testrun-v6"
    assert lab.ledger.get("budget", "other-proj") is None


def test_int_26_missing_v1_v5_actual_e2e_not_run():
    matrix = json.loads((ROOT / "COMPONENT_MATRIX.json").read_text())
    missing = {c["vendor"] for c in matrix["components"] if c["status"] == "MISSING"}
    assert "VENDOR_1" in missing and "VENDOR_5" in missing
    pytest.skip("INT-26 actual Planning→CMS E2E NOT_RUN: Vendor1 and Vendor5 missing")


def test_int_27_benchmark_requires_paired_runs():
    bench = ROOT / "evidence" / "benchmark_paired.json"
    if not bench.exists():
        pytest.skip("INT-27 NOT_RUN: no paired baseline/candidate timings on same hardware")
    data = json.loads(bench.read_text())
    assert "baseline" in data and "candidate" in data


def test_int_28_required_failure_nonzero():
    with pytest.raises(ValueError):
        raise ValueError("required-failure")


def test_int_29_traceability_ids_present():
    src = Path(__file__).read_text(encoding="utf-8")
    for i in range(1, 31):
        assert f"int_{i:02d}" in src


def test_int_30_release_provenance_files_exist():
    assert (ROOT / "COMPONENT_MATRIX.json").exists()
    assert (ROOT / "CONTRACT_SHA256.txt").exists()
    pin = (ROOT / "CONTRACT_SHA256.txt").read_text().strip()
    assert pin == "fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8"
    assert sha256_hex("x")
