from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from app.adapter import CmsAdapter
from app.errors import AdapterError
from app.fixtures import APPROVAL, ARTICLE, EVIDENCE, PUBLISH_REQ, install_staging, load_demo_authority, seal_article, seal_evidence

TOKEN = "Bearer test-service"


def make_adapter(tmp_path: Path) -> CmsAdapter:
    ad = CmsAdapter(str(tmp_path / "ledger.sqlite"))
    load_demo_authority(ad.authority)
    ad.sim.reset()
    return ad


def req(**over):
    r = deepcopy(PUBLISH_REQ)
    r.update(over)
    return r


def test_r2_policy_mismatch_approval_dry_run_rejected(tmp_path):
    ad = make_adapter(tmp_path)
    ad.authority.approvals["test-approval-1"]["policy_version"] = "different-policy"
    with pytest.raises(AdapterError) as e:
        ad.publish(req(), "policy-mismatch-01", TOKEN)
    assert e.value.code == "POLICY_MISMATCH"
    assert ad.sim.side_effects == 0
    assert ad.sim.create_calls == 0


def test_r2_policy_mismatch_staging_zero_effects(tmp_path):
    ad = make_adapter(tmp_path)
    ad.allow_staging = True
    art, appr, ev = install_staging(ad.authority)
    ad.authority.approvals[appr["approval_id"]]["policy_version"] = "different-policy"
    body = req(
        data_class="STAGING",
        mode="STAGING_DRAFT",
        content_sha256=art["content_sha256"],
        evidence_snapshot_sha256=ev["snapshot_sha256"],
        approval_id=appr["approval_id"],
        destination_id=appr["destination_id"],
    )
    with pytest.raises(AdapterError) as e:
        ad.publish(body, "policy-mismatch-stg", TOKEN, test_run_id="run-pol")
    assert e.value.code == "POLICY_MISMATCH"
    assert ad.sim.side_effects == 0


def test_r2_policy_mismatch_article_vs_approval(tmp_path):
    ad = make_adapter(tmp_path)
    art = deepcopy(ARTICLE)
    art["policy_version"] = "other-policy-1"
    art = seal_article(art)
    appr = deepcopy(APPROVAL)
    appr["content_sha256"] = art["content_sha256"]
    # approval keeps original policy_version
    ad.authority.put_article(art)
    ad.authority.put_approval(appr)
    with pytest.raises(AdapterError) as e:
        ad.publish(req(content_sha256=art["content_sha256"]), "policy-art-01xxxx", TOKEN)
    assert e.value.code == "POLICY_MISMATCH"
    assert ad.sim.side_effects == 0


def test_r2_policy_mismatch_evidence_vs_approval(tmp_path):
    ad = make_adapter(tmp_path)
    ev = deepcopy(EVIDENCE)
    ev["policy_version"] = "other-policy-1"
    ev = seal_evidence(ev)
    art = deepcopy(ARTICLE)
    art["evidence_snapshot_sha256"] = ev["snapshot_sha256"]
    art = seal_article(art)
    appr = deepcopy(APPROVAL)
    appr["content_sha256"] = art["content_sha256"]
    appr["evidence_snapshot_sha256"] = ev["snapshot_sha256"]
    ad.authority.put_evidence(ev)
    ad.authority.put_article(art)
    ad.authority.put_approval(appr)
    with pytest.raises(AdapterError) as e:
        ad.publish(
            req(content_sha256=art["content_sha256"], evidence_snapshot_sha256=ev["snapshot_sha256"]),
            "policy-ev-01xxxxx",
            TOKEN,
        )
    assert e.value.code == "POLICY_MISMATCH"


def test_r2_policy_positive_control_same_policy(tmp_path):
    ad = make_adapter(tmp_path)
    rec = ad.publish(req(), "policy-ok-control01", TOKEN)
    assert rec["status"] == "DRY_RUN"
    assert rec["actual_side_effects"] == 0
    assert ARTICLE["policy_version"] == APPROVAL["policy_version"] == EVIDENCE["policy_version"]


def test_r2_data_class_mismatch(tmp_path):
    ad = make_adapter(tmp_path)
    ad.authority.approvals["test-approval-1"]["data_class"] = "STAGING"
    with pytest.raises(AdapterError) as e:
        ad.publish(req(), "dataclass-mismatch1", TOKEN)
    assert e.value.code == "DATA_CLASS_MISMATCH"
    assert ad.sim.side_effects == 0
