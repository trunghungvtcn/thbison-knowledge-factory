from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from copy import deepcopy
from pathlib import Path

import pytest

from app.adapter import CmsAdapter
from app.errors import AdapterError
from app.fixtures import (
    APPROVAL,
    ARTICLE,
    EVIDENCE,
    PUBLISH_REQ,
    install_staging,
    load_demo_authority,
    seal_article,
    seal_evidence,
)
from app.hashutil import hash_without
from app.runtime_port import RuntimeRetryPort
from app.validate import validate

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "Bearer test-service"
IDEM = "idempotency-key-01"


def make_adapter(tmp_path: Path, **kw) -> CmsAdapter:
    ad = CmsAdapter(str(tmp_path / "ledger.sqlite"), **kw)
    load_demo_authority(ad.authority)
    ad.sim.reset()
    return ad


def req(**over):
    r = deepcopy(PUBLISH_REQ)
    r.update(over)
    return r


def staging_req(art, appr, ev, **over):
    r = req(
        data_class="STAGING",
        mode="STAGING_DRAFT",
        article_id=art["article_id"],
        article_revision=art["article_revision"],
        content_sha256=art["content_sha256"],
        evidence_snapshot_sha256=ev["snapshot_sha256"],
        approval_id=appr["approval_id"],
        destination_id=appr["destination_id"],
    )
    r.update(over)
    return r


def test_cms_01_schema_validate_and_reject_extra_missing():
    validate("PublishRequest", PUBLISH_REQ)
    validate("ArticlePackage", ARTICLE)
    validate("ApprovalRecord", APPROVAL)
    bad = deepcopy(PUBLISH_REQ)
    bad["extra"] = 1
    with pytest.raises(AdapterError) as e:
        validate("PublishRequest", bad)
    assert e.value.code == "VALIDATION_ERROR"
    missing = deepcopy(PUBLISH_REQ)
    del missing["mode"]
    with pytest.raises(AdapterError):
        validate("PublishRequest", missing)
    arr = deepcopy(ARTICLE)
    arr["blocks"] = "not-an-array"
    with pytest.raises(AdapterError):
        validate("ArticlePackage", arr)


def test_cms_02_cross_project_denied(tmp_path):
    ad = make_adapter(tmp_path)
    with pytest.raises(AdapterError) as e:
        ad.publish(req(project_id="other-proj"), IDEM, TOKEN)
    assert e.value.code in {"FORBIDDEN", "PROJECT_MISMATCH", "VALIDATION_ERROR"}


def test_cms_03_forged_and_mock_never_prod(tmp_path):
    ad = make_adapter(tmp_path)
    for tok in ("Bearer forged", "Bearer mock-admin", "Bearer totally-arbitrary", "Basic abc"):
        with pytest.raises(AdapterError) as e:
            ad.publish(req(), IDEM, tok)
        assert e.value.code == "UNAUTHORIZED"
    ad.allow_live = True
    with pytest.raises(AdapterError) as e2:
        ad.publish(req(), IDEM, TOKEN)
    assert e2.value.code == "FORBIDDEN"


def test_cms_04_approval_binds_hashes(tmp_path):
    ad = make_adapter(tmp_path)
    with pytest.raises(AdapterError) as e:
        ad.publish(req(content_sha256="d" * 64), IDEM, TOKEN)
    assert e.value.code == "STALE_APPROVAL"


def test_v5_01_tampered_authority_bytes_rejected(tmp_path):
    ad = make_adapter(tmp_path)
    ad.authority.articles[("test-article-1", 1)]["blocks"][0]["text"] = "Tampered content after approval"
    with pytest.raises(AdapterError) as e:
        ad.publish(req(), "tamper-proof-key01", TOKEN)
    assert e.value.code == "STALE_APPROVAL"
    assert ad.sim.side_effects == 0


def test_v5_01_tampered_evidence_rejected(tmp_path):
    ad = make_adapter(tmp_path)
    snap = ARTICLE["evidence_snapshot_sha256"]
    ad.authority.evidence[snap]["gaps"] = ["injected"]
    with pytest.raises(AdapterError) as e:
        ad.publish(req(), "tamper-ev-key0001", TOKEN)
    assert e.value.code == "STALE_APPROVAL"


def test_cms_05_expired_and_revoked(tmp_path):
    ad = make_adapter(tmp_path, clock=lambda: "2030-01-01T00:00:00Z")
    ad.authority.approvals["test-approval-1"]["expires_at"] = "2020-01-01T00:00:00Z"
    with pytest.raises(AdapterError) as e:
        ad.publish(req(), IDEM, TOKEN)
    assert e.value.code == "APPROVAL_EXPIRED"
    ad = make_adapter(tmp_path)
    ad.authority.revoke("test-approval-1")
    with pytest.raises(AdapterError) as e2:
        ad.publish(req(), IDEM + "x", TOKEN)
    assert e2.value.code == "APPROVAL_REVOKED"


def test_v5_02_clock_boundaries(tmp_path):
    def set_window(ad, approved, expires):
        ad.authority.approvals["test-approval-1"]["approved_at"] = approved
        ad.authority.approvals["test-approval-1"]["expires_at"] = expires

    ad = make_adapter(tmp_path, clock=lambda: "2030-01-01T00:00:00Z")
    set_window(ad, "2030-01-01T00:00:00Z", "2030-01-01T00:00:01Z")
    rec = ad.publish(req(), "clk-on-start-00001", TOKEN)
    assert rec["status"] == "DRY_RUN"
    assert rec["created_at"] == "2030-01-01T00:00:00Z"

    ad = make_adapter(tmp_path, clock=lambda: "2030-01-01T00:00:01Z")
    set_window(ad, "2030-01-01T00:00:00Z", "2030-01-01T00:00:01Z")
    with pytest.raises(AdapterError) as e:
        ad.publish(req(), "clk-on-expiry-0001", TOKEN)
    assert e.value.code == "APPROVAL_EXPIRED"

    ad = make_adapter(tmp_path, clock=lambda: "2029-12-31T23:59:59Z")
    set_window(ad, "2030-01-01T00:00:00Z", "2030-01-02T00:00:00Z")
    with pytest.raises(AdapterError) as e2:
        ad.publish(req(), "clk-before-approved", TOKEN)
    assert e2.value.code == "APPROVAL_EXPIRED"


def test_v5_02_default_clock_is_real_utc(tmp_path):
    ad = make_adapter(tmp_path)
    rec = ad.publish(req(), "real-clock-key-01", TOKEN)
    assert rec["created_at"].endswith("Z")
    assert rec["created_at"] != "2030-01-01T00:00:00Z"


def test_cms_06_dry_run_zero_mutations(tmp_path):
    ad = make_adapter(tmp_path)
    rec = ad.publish(req(mode="DRY_RUN"), IDEM, TOKEN)
    assert rec["status"] == "DRY_RUN"
    assert rec["actual_side_effects"] == 0
    assert ad.sim.side_effects == 0
    assert rec["provider_record_id"] is None


def test_cms_07_staging_draft_nonpublic(tmp_path):
    ad = make_adapter(tmp_path)
    ad.allow_staging = True
    art, appr, ev = install_staging(ad.authority)
    rec = ad.publish(staging_req(art, appr, ev, request_id="stg-1"), "idempotency-key-stg", TOKEN, test_run_id="run-1")
    assert rec["actual_side_effects"] == 1
    draft = ad.sim.get(rec["provider_record_id"])
    assert draft is not None and draft.public is False


def test_v5_04_mutation_requires_run_id(tmp_path):
    ad = make_adapter(tmp_path)
    ad.allow_staging = True
    art, appr, ev = install_staging(ad.authority)
    with pytest.raises(AdapterError) as e:
        ad.publish(staging_req(art, appr, ev), "idem-no-run-id-01", TOKEN, test_run_id=None)
    assert e.value.code == "VALIDATION_ERROR"
    assert ad.sim.side_effects == 0


def test_cms_08_live_denied(tmp_path):
    ad = make_adapter(tmp_path)
    with pytest.raises(AdapterError) as e:
        ad.publish(req(mode="LIVE"), IDEM, TOKEN)
    assert e.value.code == "LIVE_DISABLED"
    with pytest.raises(AdapterError) as e2:
        ad.publish(req(data_class="PRODUCTION"), IDEM + "2", TOKEN)
    assert e2.value.code == "LIVE_DISABLED"


def test_cms_09_duplicate_same_receipt(tmp_path):
    ad = make_adapter(tmp_path)
    a = ad.publish(req(), IDEM, TOKEN)
    b = ad.publish(req(), IDEM, TOKEN)
    assert a["publication_id"] == b["publication_id"]
    assert a["actual_side_effects"] == 0


def test_cms_10_same_key_different_payload(tmp_path):
    ad = make_adapter(tmp_path)
    ad.publish(req(), IDEM, TOKEN)
    with pytest.raises(AdapterError) as e:
        ad.publish(req(request_id="other-req"), IDEM, TOKEN)
    assert e.value.code == "IDEMPOTENCY_CONFLICT"


def test_cms_11_concurrent_one_draft(tmp_path):
    ad = make_adapter(tmp_path)
    results = []
    errors = []

    def worker():
        try:
            d = ad.sim.create_draft(
                {
                    "project_id": "test-thbison",
                    "destination_id": "test-cms",
                    "external_key": "same-ext",
                    "article_id": "test-article-1",
                    "article_revision": 1,
                    "content_sha256": ARTICLE["content_sha256"],
                    "body": "x",
                    "test_run_id": "run-11",
                }
            )
            results.append(d.provider_record_id)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(set(results)) == 1
    assert ad.sim.side_effects == 1


def test_cms_12_timeout_after_accept_lookup(tmp_path):
    ad = make_adapter(tmp_path)
    ad.allow_staging = True
    art, appr, ev = install_staging(ad.authority)
    ad.sim.set_fault("timeout-after-accept")
    with pytest.raises(AdapterError) as e:
        ad.publish(staging_req(art, appr, ev), IDEM, TOKEN, test_run_id="run-12")
    assert e.value.code == "TIMEOUT"
    assert ad.sim.side_effects == 1
    owned = ad.ledger.list_by_run("run-12")
    assert len(owned) == 1
    ad.sim.set_fault("none")
    rec = ad.publish(staging_req(art, appr, ev), IDEM + "b", TOKEN, test_run_id="run-12")
    assert rec["actual_side_effects"] == 0
    assert ad.sim.side_effects == 1


def test_cms_13_unknown_persists(tmp_path):
    ad = make_adapter(tmp_path)
    ad.ledger.put_unknown("pub-unknown-1", "k", 1, "UNKNOWN")
    out = ad.reconcile("pub-unknown-1")
    assert out["attempts"] == 2
    ad.ledger.put_unknown("pub-unknown-1", "k", 5, "UNKNOWN")
    with pytest.raises(AdapterError) as e:
        ad.reconcile("pub-unknown-1")
    assert e.value.code == "PUBLICATION_UNKNOWN"


def test_cms_14_retryable_bounded_under_vendor3_port(tmp_path):
    ad = make_adapter(tmp_path, runtime=RuntimeRetryPort(max_attempts=3))
    ad.sim.set_fault("rate_limited")
    with pytest.raises(AdapterError) as e:
        ad.sim.create_draft(
            {
                "project_id": "test-thbison",
                "destination_id": "test-cms",
                "external_key": "k",
                "article_id": "a",
                "article_revision": 1,
                "content_sha256": "a" * 64,
                "body": "b",
            }
        )
    assert e.value.code == "RATE_LIMITED" and e.value.retryable
    ad.sim.set_fault("unavailable")
    with pytest.raises(AdapterError):
        ad._dispatch_create(
            {
                "project_id": "test-thbison",
                "destination_id": "test-cms",
                "external_key": "k2",
                "article_id": "a",
                "article_revision": 1,
                "content_sha256": "a" * 64,
                "body": "b",
            }
        )
    assert ad.runtime.attempts.count("PROVIDER_ERROR") == 3


def test_cms_14_default_no_nested_retry(tmp_path):
    ad = make_adapter(tmp_path)
    ad.sim.set_fault("unavailable")
    with pytest.raises(AdapterError):
        ad._dispatch_create(
            {
                "project_id": "test-thbison",
                "destination_id": "test-cms",
                "external_key": "k2b",
                "article_id": "a",
                "article_revision": 1,
                "content_sha256": "a" * 64,
                "body": "b",
            }
        )
    assert ad.runtime.attempts.count("PROVIDER_ERROR") == 1
    assert ad.runtime.owner == "vendor3"


def test_cms_15_nonretryable_4xx(tmp_path):
    ad = make_adapter(tmp_path, runtime=RuntimeRetryPort(max_attempts=3))
    ad.sim.set_fault("4xx")
    with pytest.raises(AdapterError) as e:
        ad._dispatch_create(
            {
                "project_id": "test-thbison",
                "destination_id": "test-cms",
                "external_key": "k3",
                "article_id": "a",
                "article_revision": 1,
                "content_sha256": "a" * 64,
                "body": "b",
            }
        )
    assert e.value.retryable is False
    assert ad.runtime.attempts == ["VALIDATION_ERROR"]


def test_cms_16_optimistic_revision(tmp_path):
    ad = make_adapter(tmp_path)
    d = ad.sim.create_draft(
        {
            "project_id": "test-thbison",
            "destination_id": "test-cms",
            "external_key": "k4",
            "article_id": "a",
            "article_revision": 1,
            "content_sha256": "a" * 64,
            "body": "orig",
        }
    )
    ad.sim.mark_human_edit(d.provider_record_id)
    with pytest.raises(AdapterError) as e:
        ad.update_draft(d.provider_record_id, 1, "new", "b" * 64)
    assert e.value.code == "STALE_REVISION"
    assert ad.sim.get(d.provider_record_id).body == "orig"


def test_cms_17_os_process_restart(tmp_path):
    ledger = tmp_path / "ledger.sqlite"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["CMS_LEDGER_PATH"] = str(ledger)
    env["STAGING_WRITE_ENABLED"] = "true"
    worker = ROOT / "scripts" / "process_worker.py"
    r1 = subprocess.run([sys.executable, str(worker), "publish"], env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    first = json.loads(r1.stdout)
    r2 = subprocess.run([sys.executable, str(worker), "publish"], env=env, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    second = json.loads(r2.stdout)
    assert first["publication_id"] == second["publication_id"]
    assert first["provider_record_id"] == second["provider_record_id"]
    st = subprocess.run([sys.executable, str(worker), "stats"], env=env, capture_output=True, text=True)
    assert st.returncode == 0, st.stderr
    stats = json.loads(st.stdout)
    assert stats["side_effects"] == 1


def test_cms_17_crash_after_accept_then_reconcile(tmp_path):
    ledger = tmp_path / "ledger.sqlite"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["CMS_LEDGER_PATH"] = str(ledger)
    env["STAGING_WRITE_ENABLED"] = "true"
    env["CMS_CRASH_AFTER_ACCEPT"] = "1"
    worker = ROOT / "scripts" / "process_worker.py"
    crashed = subprocess.run([sys.executable, str(worker), "publish"], env=env, capture_output=True, text=True)
    assert crashed.returncode == 99
    env.pop("CMS_CRASH_AFTER_ACCEPT")
    replay = subprocess.run([sys.executable, str(worker), "publish"], env=env, capture_output=True, text=True)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    rec = json.loads(replay.stdout)
    assert rec["actual_side_effects"] == 0
    assert rec["provider_record_id"]


def test_cms_17_two_process_contention(tmp_path):
    ledger = tmp_path / "ledger.sqlite"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["CMS_LEDGER_PATH"] = str(ledger)
    env["STAGING_WRITE_ENABLED"] = "true"
    worker = ROOT / "scripts" / "process_worker.py"
    procs = [
        subprocess.Popen([sys.executable, str(worker), "publish"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(2)
    ]
    outs = []
    for p in procs:
        stdout, stderr = p.communicate(timeout=30)
        assert p.returncode == 0, stderr
        outs.append(json.loads(stdout))
    assert outs[0]["publication_id"] == outs[1]["publication_id"]
    assert outs[0]["provider_record_id"] == outs[1]["provider_record_id"]
    st = subprocess.run([sys.executable, str(worker), "stats"], env=env, capture_output=True, text=True)
    stats = json.loads(st.stdout)
    assert stats["side_effects"] == 1


def test_cms_18_unsafe_html(tmp_path):
    ad = make_adapter(tmp_path)
    art = deepcopy(ARTICLE)
    art["blocks"][0]["text"] = "<script>alert(1)</script> [claim:test-claim-1]"
    art = seal_article(art)
    appr = deepcopy(APPROVAL)
    appr["content_sha256"] = art["content_sha256"]
    ad.authority.put_article(art)
    ad.authority.put_approval(appr)
    with pytest.raises(AdapterError) as e:
        ad.publish(req(content_sha256=art["content_sha256"]), IDEM, TOKEN)
    assert e.value.code == "UNSAFE_CONTENT"


def test_cms_19_asset_refresh(tmp_path):
    ad = make_adapter(tmp_path)
    url = ad.authority.refresh_asset("asset-1", "c" * 64)
    assert url.startswith("https://cdn.test.thbison.local/")
    with pytest.raises(AdapterError) as e:
        ad.authority.refresh_asset("asset-1", "d" * 64)
    assert e.value.code == "ASSET_HASH_MISMATCH"


def test_cms_20_destination_allowlist(tmp_path):
    ad = make_adapter(tmp_path)
    with pytest.raises(AdapterError) as e:
        ad.publish(req(destination_id="evil-cms"), IDEM, TOKEN)
    assert e.value.code == "DESTINATION_DENIED"
    from app.sanitize import assert_safe_url
    with pytest.raises(AdapterError):
        assert_safe_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(AdapterError):
        assert_safe_url("https://evil.example/redirect")


def test_cms_21_timezone_and_planning_date(tmp_path):
    ad = make_adapter(tmp_path)
    with pytest.raises(AdapterError) as e:
        ad.publish(req(scheduled_at="2030-01-01T00:00:00"), IDEM, TOKEN)
    assert e.value.code in {"SCHEDULE_INVALID", "VALIDATION_ERROR"}
    with pytest.raises(AdapterError) as e2:
        ad.publish(req(scheduled_at="2030-01-01T00:00:00Z"), IDEM + "z", TOKEN)
    assert "auto-publish" in e2.value.message


def test_cms_22_capability_discovery(tmp_path):
    ad = make_adapter(tmp_path)
    caps = ad.inspect_capabilities()
    assert caps["native_cms_status"] == "MOCK"
    assert caps["code_commit"]
    ad.app_mode = "LIVE"
    ad.cms_base = "https://example.invalid"
    ad.cms_token = "x"
    caps2 = ad.inspect_capabilities()
    assert caps2["native_cms_status"] == "CONFIGURED_UNVERIFIED"
    ad.cms_base = ""
    caps3 = ad.inspect_capabilities()
    assert caps3["native_cms_status"] == "BLOCKED_MISSING_INPUT"
    ad.app_mode = "MOCK"
    ad.sim.set_fault("schema_drift")
    with pytest.raises(AdapterError) as e:
        ad.inspect_capabilities()
    assert e.value.code == "CAPABILITY_MISMATCH"


def test_cms_23_staging_requires_run_id_and_receipt(tmp_path):
    ad = make_adapter(tmp_path)
    ad.allow_staging = True
    art, appr, ev = install_staging(ad.authority)
    rec = ad.publish(staging_req(art, appr, ev), IDEM, TOKEN, test_run_id="run-23")
    assert rec["provider_record_id"]
    rb = ad.rollback_own("run-23")
    assert rb["count"] == 1


def test_cms_24_cleanup_only_own(tmp_path):
    ad = make_adapter(tmp_path)
    ad.sim.create_draft(
        {
            "project_id": "test-thbison",
            "destination_id": "test-cms",
            "external_key": "foreign",
            "article_id": "other",
            "article_revision": 1,
            "content_sha256": "a" * 64,
            "body": "keep",
            "test_run_id": "someone-else",
        }
    )
    mine = ad.sim.create_draft(
        {
            "project_id": "test-thbison",
            "destination_id": "test-cms",
            "external_key": "mine",
            "article_id": "mine",
            "article_revision": 1,
            "content_sha256": "b" * 64,
            "body": "drop",
            "test_run_id": "run-24",
        }
    )
    ad.ledger.put_draft(
        {
            "provider_record_id": mine.provider_record_id,
            "project_id": "test-thbison",
            "destination_id": "test-cms",
            "external_key": "mine",
            "article_id": "mine",
            "article_revision": 1,
            "content_sha256": "b" * 64,
            "revision": 1,
            "body": "drop",
            "public": False,
            "test_run_id": "run-24",
            "created_at": "2030-01-01T00:00:00Z",
        }
    )
    ad.rollback_own("run-24")
    assert ad.sim.lookup("test-thbison", "test-cms", "foreign") is not None
    assert ad.sim.lookup("test-thbison", "test-cms", "mine") is None


def test_cms_25_schema_drift_fail_closed(tmp_path):
    ad = make_adapter(tmp_path)
    ad.sim.set_fault("schema_drift")
    with pytest.raises(AdapterError) as e:
        ad.sim.create_draft(
            {
                "project_id": "test-thbison",
                "destination_id": "test-cms",
                "external_key": "d",
                "article_id": "a",
                "article_revision": 1,
                "content_sha256": "a" * 64,
                "body": "b",
            }
        )
    assert e.value.code == "SCHEMA_DRIFT"


def test_cms_26_receipt_hashes(tmp_path):
    ad = make_adapter(tmp_path)
    rec = ad.publish(req(), IDEM, TOKEN)
    assert rec["_source_revision"]
    assert rec["_contract_sha256"] == "fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8"
    assert len(rec["_payload_sha256"]) == 64
    public = {k: v for k, v in rec.items() if not k.startswith("_")}
    validate("PublicationReceipt", public)
    assert hash_without(ARTICLE, "content_sha256") == ARTICLE["content_sha256"]
