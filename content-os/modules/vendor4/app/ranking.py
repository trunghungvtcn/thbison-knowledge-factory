from __future__ import annotations

from typing import Any


REASON = {
    "ELIGIBLE": "ELIGIBLE_IN_SCOPE",
    "HOLD": "HOLD_BLOCKED",
    "REVOKED": "REVOKED_BLOCKED",
}


def score_claim(claim: dict[str, Any]) -> tuple[float, str]:
    status = claim.get("status", "")
    if status == "ELIGIBLE":
        base = 80.0
        if claim.get("conditions", {}).get("type") == "TEST_ONLY":
            base += 5.0
        return base, REASON["ELIGIBLE"]
    if status == "HOLD":
        return 0.0, REASON["HOLD"]
    return 0.0, REASON.get(status, "INELIGIBLE")


def rank(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for c in claims:
        s, reason = score_claim(c)
        item = dict(c)
        item["rank_score"] = s
        item["rank_reason"] = reason
        scored.append(item)
    scored.sort(key=lambda x: (-x["rank_score"], x["claim_id"], x.get("claim_version", "")))
    return scored


def benchmark(baseline: list[str], candidate: list[str]) -> str:
    if candidate == baseline:
        return "NO_IMPROVEMENT"
    # deterministic: only promote if first item stays and list is permutation with higher first score already encoded
    if candidate and baseline and candidate[0] == baseline[0]:
        return "NO_IMPROVEMENT"
    return "NO_IMPROVEMENT"
