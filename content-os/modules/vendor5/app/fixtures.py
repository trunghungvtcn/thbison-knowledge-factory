from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from app.hashutil import hash_without

_EX = Path(__file__).resolve().parents[1] / "contracts" / "examples"

ARTICLE = json.loads((_EX / "ArticlePackage.json").read_text(encoding="utf-8"))
APPROVAL = json.loads((_EX / "ApprovalRecord.json").read_text(encoding="utf-8"))
EVIDENCE = json.loads((_EX / "EvidenceBundle.json").read_text(encoding="utf-8"))
PUBLISH_REQ = json.loads((_EX / "PublishRequest.json").read_text(encoding="utf-8"))
APPROVAL["approved_at"] = "2020-01-01T00:00:00Z"
APPROVAL["expires_at"] = "2099-01-01T00:00:00Z"


def seal_article(article: dict) -> dict:
    a = deepcopy(article)
    a["content_sha256"] = hash_without(a, "content_sha256")
    return a


def seal_evidence(ev: dict) -> dict:
    e = deepcopy(ev)
    e["snapshot_sha256"] = hash_without(e, "snapshot_sha256")
    return e


def load_demo_authority(store) -> None:
    store.put_article(deepcopy(ARTICLE))
    store.put_approval(deepcopy(APPROVAL))
    store.put_evidence(deepcopy(EVIDENCE))
    store.put_asset(
        "asset-1",
        "c" * 64,
        "https://cdn.test.thbison.local/a.bin?sig=fresh",
        "2030-01-01T01:00:00Z",
    )


def install_staging(store, article=None, approval=None, evidence=None):
    art = deepcopy(article or ARTICLE)
    appr = deepcopy(approval or APPROVAL)
    ev = deepcopy(evidence or EVIDENCE)
    art["data_class"] = "STAGING"
    appr["data_class"] = "STAGING"
    ev["data_class"] = "STAGING"
    ev = seal_evidence(ev)
    art["evidence_snapshot_sha256"] = ev["snapshot_sha256"]
    art = seal_article(art)
    appr["content_sha256"] = art["content_sha256"]
    appr["evidence_snapshot_sha256"] = ev["snapshot_sha256"]
    store.put_article(art)
    store.put_approval(appr)
    store.put_evidence(ev)
    return art, appr, ev
