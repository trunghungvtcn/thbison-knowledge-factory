from __future__ import annotations

from datetime import datetime, timezone

from .canonical import exact_keys, nonempty, require

REQUIRED_CHECKS = frozenset({"source_context", "predicate", "value", "unit_or_vocabulary",
                             "applicability", "conditions", "exceptions", "no_omitted_requirements"})
DECISIONS = frozenset({"ACCEPT", "REJECT", "HOLD", "NEEDS_MORE_EVIDENCE"})


def utc_datetime(value: str) -> datetime:
    require(nonempty(value), "REVIEW_TIME_MISSING")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        require(False, "INVALID_REVIEW_TIME")
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "REVIEW_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def validate_adjudication(adjudication: dict, proposal: dict, reviewer_registry: dict,
                          *, data_class: str, as_of: str) -> str:
    exact_keys(adjudication, {"proposal_hash", "issue_id", "entity_id", "base_version_id",
                              "target_version_id", "decision", "reviewer_id", "decided_at",
                              "rationale", "checks", "data_class"})
    for name in ("proposal_hash", "issue_id", "entity_id", "base_version_id", "target_version_id"):
        require(adjudication[name] == proposal[name], "ADJUDICATION_BINDING_MISMATCH", name)
    require(adjudication["data_class"] == data_class, "TEST_DATA_CLASS_MISMATCH")
    decision = adjudication["decision"]
    require(decision in DECISIONS, "UNKNOWN_ADJUDICATION_DECISION")
    reviewer = reviewer_registry.get(adjudication["reviewer_id"])
    require(reviewer is not None, "REVIEWER_NOT_TRUSTED")
    require(reviewer.get("active") is True, "REVIEWER_INACTIVE")
    require(reviewer.get("data_class") == data_class, "TEST_REVIEWER_REJECTED")
    require("SEMANTIC_REVIEWER" in reviewer.get("roles", []), "REVIEWER_ROLE_MISSING")
    require(proposal["predicate"] in reviewer.get("predicates", []), "REVIEWER_SCOPE_MISMATCH")
    require(adjudication["reviewer_id"] != proposal["proposer_id"], "SELF_ADJUDICATION_REJECTED")
    require(nonempty(adjudication["rationale"]), "REVIEW_RATIONALE_MISSING")
    reviewed_at, cutoff = utc_datetime(adjudication["decided_at"]), utc_datetime(as_of)
    require(reviewed_at <= cutoff, "REVIEW_FROM_FUTURE")
    require(reviewed_at >= utc_datetime(reviewer["valid_from"]), "REVIEWER_NOT_YET_VALID")
    require(cutoff <= utc_datetime(reviewer["valid_until"]), "REVIEWER_EXPIRED")
    require(isinstance(adjudication["checks"], dict), "REVIEW_CHECKS_INVALID")
    if decision == "ACCEPT":
        require(set(adjudication["checks"]) == REQUIRED_CHECKS and
                all(value is True for value in adjudication["checks"].values()),
                "INCOMPLETE_SEMANTIC_REVIEW")
    return decision


