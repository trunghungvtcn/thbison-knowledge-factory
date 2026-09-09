from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from .canonical import GateError, exact_keys, nonempty, require
from .evidence import SourceStore


def decimal_text(value: str) -> str:
    require(isinstance(value, str) and bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value)),
            "EXPLICIT_DECIMAL_REQUIRED")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise GateError("INVALID_DECIMAL") from exc
    require(number.is_finite() and number >= 0, "INVALID_QUANTITY")
    return format(number.normalize(), "f") if number else "0"


def interpret(candidate: dict, issue: dict, store: SourceStore,
              predicate_contracts: dict, vocabularies: dict) -> dict:
    """Interpret exact supplied spans; never search for a convenient number."""
    context = candidate["context_span"]
    context_text = store.verify(context)
    require(nonempty(issue["source_text"]) and
            " ".join(issue["source_text"].split()) in " ".join(context_text.split()),
            "FULL_LEGACY_CONTEXT_MISSING")
    # Pilot V16.4 remediates OBJECT_VALUE only. No guessing the nine connectives.
    require(issue["issue_type"] == "OBJECT_VALUE_UNSTRUCTURED",
            "CONDITION_REMAINS_NEEDS_MORE_EVIDENCE")
    value, proofs = candidate["interpretation"], candidate["proofs"]
    require(candidate["predicate"] in predicate_contracts, "PREDICATE_CONTRACT_MISSING")
    contract = predicate_contracts[candidate["predicate"]]
    require(isinstance(value, dict) and value.get("kind") in contract["allowed_kinds"],
            "UNSUPPORTED_SEMANTIC_TYPE")
    for proof in proofs.values():
        store.inside(proof, context)
    kind = value["kind"]
    if kind == "quantity":
        exact_keys(value, {"kind", "amount", "unit", "operator"})
        exact_keys(proofs, {"amount", "unit"})
        store.complete_token(proofs["amount"], numeric=True)
        store.complete_token(proofs["unit"])
        amount = decimal_text(value["amount"])
        quoted_amount = decimal_text(proofs["amount"]["quote"])
        require(amount == quoted_amount, "AMOUNT_NOT_PROVEN")
        require(value["operator"] in contract["operators"], "OPERATOR_NOT_IN_CONTRACT")
        units = contract["units"]
        require(value["unit"] in units, "UNIT_NOT_IN_CONTRACT")
        unit = units[value["unit"]]
        require(proofs["unit"]["quote"] in unit["source_literals"], "UNIT_NOT_PROVEN")
        # Exact unit semantics only: year != days; metric t != US short ton.
        # Store Decimal as text to avoid float-dependent content hashes.
        return {"kind": "quantity", "amount": amount, "unit": value["unit"],
                "dimension": unit["dimension"], "operator": value["operator"]}
    if kind == "enum":
        exact_keys(value, {"kind", "code", "vocabulary_id"})
        exact_keys(proofs, {"statement"})
        vocab_id = value["vocabulary_id"]
        require(vocab_id in vocabularies, "AUTHORITATIVE_VOCABULARY_MISSING")
        vocab = vocabularies[vocab_id]
        require(vocab_id in contract["vocabulary_ids"], "VOCABULARY_PREDICATE_MISMATCH")
        require(value["code"] in vocab["entries"], "ENUM_MEMBER_MISSING")
        entry = vocab["entries"][value["code"]]
        require(proofs["statement"]["quote"] in entry["source_literals"],
                "ENUM_POLARITY_NOT_PROVEN")
        # Contract authority is a trust-root concern, not inferred from its hash.
        return {"kind": "enum", "code": value["code"], "vocabulary_id": vocab_id,
                "vocabulary_version": vocab["version"], "definition": entry["definition"]}
    raise GateError("SEMANTIC_TYPE_NOT_IMPLEMENTED", str(kind))

