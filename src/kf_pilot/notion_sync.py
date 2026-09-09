from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .core import canonical_json, utc_now


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"

REQUIRED_PROPERTIES = {
    "Name": "title",
    "Candidate ID": "rich_text",
    "Status": "select",
    "Category": "rich_text",
    "Manufacturer": "rich_text",
    "Model": "rich_text",
    "Predicate": "select",
    "Raw Value": "rich_text",
    "Unit": "rich_text",
    "Confidence": "number",
    "Risk": "select",
    "Source URL": "url",
    "Evidence": "rich_text",
    "Decision": "select",
    "Reviewer Note": "rich_text",
    "Run ID": "rich_text",
}

V2_REQUIRED_PROPERTIES = {
    "evidence": {
        "Name": "title", "Resource ID": "rich_text", "Source URL": "url", "Publisher": "rich_text",
        "Source Role": "select", "Authority Tier": "select", "Jurisdiction": "select",
        "Applicability Scope": "rich_text", "Legal Status": "rich_text", "Content SHA256": "rich_text",
        "Run ID": "rich_text", "Status": "select",
    },
    "product": {
        "Name": "title", "Attribute ID": "rich_text", "Manufacturer": "rich_text", "Model": "rich_text",
        "Predicate": "select", "Raw Value": "rich_text", "Unit": "rich_text", "Normalized Value": "number",
        "Normalized Unit": "rich_text", "Confidence": "number", "Status": "select", "Decision": "select",
        "Risk": "select", "Evidence Sources": "relation", "Source URL": "url", "Run ID": "rich_text",
        "Reviewer Note": "rich_text",
    },
    "knowledge": {
        "Name": "title", "Knowledge ID": "rich_text", "Family": "select", "Predicate": "rich_text",
        "Claim Text": "rich_text", "Product Family": "rich_text", "Jurisdiction": "select",
        "Applicability Scope": "rich_text", "Directness": "select", "Authority Tier": "select",
        "Legal Status": "rich_text", "Confidence": "number", "Status": "select", "Decision": "select",
        "Risk": "select", "Evidence Sources": "relation", "Source URL": "url", "Run ID": "rich_text",
        "Reviewer Note": "rich_text",
    },
}


def _request(
    method: str,
    path: str,
    api_key: str,
    body: dict[str, Any] | None = None,
    max_retries: int = 5,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    for attempt in range(max_retries):
        request = urllib.request.Request(
            NOTION_API_BASE + path,
            data=None if body is None else canonical_json(body).encode("utf-8"),
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1500]
            if exc.code in {429, 529} and attempt + 1 < max_retries:
                delay = float(exc.headers.get("Retry-After", "1"))
                time.sleep(max(delay, 1.0))
                continue
            # Retrying an ambiguous page CREATE can produce duplicates.
            # A later run queries the stable ID before attempting creation again.
            if exc.code in {500, 502, 503, 504} and method in {"GET", "PATCH"} and attempt + 1 < max_retries:
                time.sleep(min(2**attempt, 16))
                continue
            raise RuntimeError(f"Notion HTTP {exc.code}: {detail}") from exc
    raise RuntimeError("Notion request exhausted retries")


def retrieve_data_source(api_key: str, data_source_id: str) -> dict[str, Any]:
    return _request("GET", f"/data_sources/{data_source_id}", api_key)


def validate_data_source_schema(api_key: str, data_source_id: str) -> dict[str, str]:
    data_source = retrieve_data_source(api_key, data_source_id)
    actual = {
        name: str(definition.get("type", ""))
        for name, definition in data_source.get("properties", {}).items()
    }
    mismatches = {
        name: f"expected={kind}, actual={actual.get(name, 'MISSING')}"
        for name, kind in REQUIRED_PROPERTIES.items()
        if actual.get(name) != kind
    }
    if mismatches:
        raise ValueError(f"Notion data source schema mismatch: {mismatches}")
    return actual


def validate_v2_data_source_schema(api_key: str, data_source_id: str, kind: str) -> dict[str, str]:
    if kind not in V2_REQUIRED_PROPERTIES:
        raise ValueError(f"Unknown Notion v2 data source kind: {kind}")
    data_source = retrieve_data_source(api_key, data_source_id)
    actual = {name: str(value.get("type", "")) for name, value in data_source.get("properties", {}).items()}
    mismatches = {name: f"expected={expected}, actual={actual.get(name, 'MISSING')}" for name, expected in V2_REQUIRED_PROPERTIES[kind].items() if actual.get(name) != expected}
    if mismatches:
        raise ValueError(f"Notion {kind} data source schema mismatch: {mismatches}")
    return actual


def _rich_text(value: Any, limit: int = 1800) -> dict[str, Any]:
    text = str(value or "")[:limit]
    return {"rich_text": [] if not text else [{"type": "text", "text": {"content": text}}]}


def _title(value: Any, limit: int = 1800) -> dict[str, Any]:
    text = str(value or "Untitled")[:limit]
    return {"title": [{"type": "text", "text": {"content": text}}]}


def _select(value: Any) -> dict[str, Any]:
    text = str(value or "")[:100]
    return {"select": None if not text else {"name": text}}


def _url(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    return {"url": text if text.startswith(("https://", "http://")) else None}


def _number(value: Any) -> dict[str, Any]:
    return {"number": None if value is None or str(value) == "" else float(value)}


def _relation(page_ids: Iterable[str]) -> dict[str, Any]:
    return {"relation": [{"id": str(page_id)} for page_id in page_ids if str(page_id)]}


def candidate_properties(row: dict[str, Any], category_name: str, run_id: str) -> dict[str, Any]:
    evidence = str(row.get("quote", ""))
    candidate_id = str(row.get("candidate_id", ""))
    title = f"{row.get('model_alias', 'Unknown')} · {row.get('predicate', 'claim')} · {row.get('raw_value', '')} {row.get('raw_unit', '')}"
    return {
        "Name": _title(title),
        "Candidate ID": _rich_text(candidate_id),
        "Status": _select(row.get("decision_state", "REVIEW_REQUIRED")),
        "Category": _rich_text(category_name),
        "Manufacturer": _rich_text(row.get("manufacturer_alias", "")),
        "Model": _rich_text(row.get("model_alias", "")),
        "Predicate": _select(row.get("predicate", "UNKNOWN")),
        "Raw Value": _rich_text(row.get("raw_value", "")),
        "Unit": _rich_text(row.get("raw_unit", "")),
        "Confidence": {"number": float(row.get("final_confidence") or 0.0)},
        "Risk": _select(row.get("risk_class", "UNKNOWN")),
        "Source URL": _url(row.get("original_url", "")),
        "Evidence": _rich_text(evidence),
        "Decision": _select("PENDING"),
        "Reviewer Note": _rich_text(""),
        "Run ID": _rich_text(run_id),
    }


def query_pages(
    api_key: str,
    data_source_id: str,
    filter_body: dict[str, Any] | None = None,
) -> Iterable[dict[str, Any]]:
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if filter_body:
            body["filter"] = filter_body
        if cursor:
            body["start_cursor"] = cursor
        response = _request("POST", f"/data_sources/{data_source_id}/query", api_key, body)
        yield from response.get("results", [])
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")


def find_page_by_candidate_id(api_key: str, data_source_id: str, candidate_id: str) -> dict[str, Any] | None:
    pages = list(
        query_pages(
            api_key,
            data_source_id,
            {
                "property": "Candidate ID",
                "rich_text": {"equals": candidate_id},
            },
        )
    )
    if len(pages) > 1:
        raise RuntimeError(f"Duplicate Candidate ID in Notion: {candidate_id}")
    return pages[0] if pages else None


def find_page_by_text_id(api_key: str, data_source_id: str, property_name: str, value: str) -> dict[str, Any] | None:
    pages = list(query_pages(api_key, data_source_id, {"property": property_name, "rich_text": {"equals": value}}))
    if len(pages) > 1:
        raise RuntimeError(f"Duplicate {property_name} in Notion: {value}")
    return pages[0] if pages else None


def _upsert_page(api_key: str, data_source_id: str, id_property: str, item_id: str, properties: dict[str, Any], preserve_review: bool = False) -> tuple[dict[str, Any], str]:
    existing = find_page_by_text_id(api_key, data_source_id, id_property, item_id)
    if existing:
        update = dict(properties)
        if preserve_review:
            update.pop("Decision", None)
            update.pop("Reviewer Note", None)
            update.pop("Status", None)
            # A new hard gate overrides an old status, but never erases review notes.
            if properties.get("Status", {}).get("select", {}).get("name") == "HOLD":
                update["Status"] = properties["Status"]
        return _request("PATCH", f"/pages/{existing['id']}", api_key, {"properties": update}), "UPDATED"
    return _request("POST", "/pages", api_key, {"parent": {"type": "data_source_id", "data_source_id": data_source_id}, "properties": properties}), "CREATED"


def sync_evidence_sources(evidence: pd.DataFrame, api_key: str, data_source_id: str, run_id: str, max_rows: int = 200) -> tuple[pd.DataFrame, dict[str, str]]:
    validate_v2_data_source_schema(api_key, data_source_id, "evidence")
    results, page_map = [], {}
    unique = evidence.drop_duplicates(subset=["resource_id"]).head(max_rows)
    for row in unique.to_dict(orient="records"):
        resource_id = str(row["resource_id"])
        properties = {
            "Name": _title(row.get("publisher_name") or resource_id), "Resource ID": _rich_text(resource_id),
            "Source URL": _url(row.get("original_url")), "Publisher": _rich_text(row.get("publisher_name")),
            "Source Role": _select(row.get("source_role")), "Authority Tier": _select(row.get("authority_tier")),
            "Jurisdiction": _select(row.get("jurisdiction") or "GLOBAL"), "Applicability Scope": _rich_text(row.get("applicability_scope")),
            "Legal Status": _rich_text(row.get("legal_status")), "Content SHA256": _rich_text(row.get("resource_version_hash")),
            "Run ID": _rich_text(run_id), "Status": _select("ACTIVE"),
        }
        response, action = _upsert_page(api_key, data_source_id, "Resource ID", resource_id, properties)
        page_map[resource_id] = response["id"]
        results.append({"resource_id": resource_id, "notion_page_id": response["id"], "action": action, "synced_at": utc_now()})
    return pd.DataFrame(results), page_map


def sync_product_attributes(candidates: pd.DataFrame, api_key: str, data_source_id: str, evidence_page_map: dict[str, str], run_id: str, max_rows: int = 200) -> pd.DataFrame:
    validate_v2_data_source_schema(api_key, data_source_id, "product")
    results = []
    for row in candidates.head(max_rows).to_dict(orient="records"):
        item_id, resource_id = str(row["candidate_id"]), str(row.get("resource_id", ""))
        state = str(row.get("decision_state") or "REVIEW_REQUIRED")
        properties = {
            "Name": _title(f"{row.get('model_alias', 'Unknown')} · {row.get('predicate', 'claim')} · {row.get('raw_value', '')} {row.get('raw_unit', '')}"),
            "Attribute ID": _rich_text(item_id), "Manufacturer": _rich_text(row.get("manufacturer_alias")), "Model": _rich_text(row.get("model_alias")),
            "Predicate": _select(row.get("predicate")), "Raw Value": _rich_text(row.get("raw_value")), "Unit": _rich_text(row.get("raw_unit")),
            "Normalized Value": _number(row.get("normalized_value")), "Normalized Unit": _rich_text(row.get("normalized_unit")),
            "Confidence": _number(row.get("final_confidence", 0)), "Status": _select(state), "Decision": _select("HOLD" if state == "HOLD" else "PENDING"),
            "Risk": _select(row.get("risk_class")), "Evidence Sources": _relation([evidence_page_map.get(resource_id, "")]),
            "Source URL": _url(row.get("original_url")), "Run ID": _rich_text(run_id), "Reviewer Note": _rich_text(""),
        }
        response, action = _upsert_page(api_key, data_source_id, "Attribute ID", item_id, properties, preserve_review=True)
        results.append({"candidate_id": item_id, "notion_page_id": response["id"], "action": action, "synced_at": utc_now()})
    return pd.DataFrame(results)


def sync_knowledge_items(candidates: pd.DataFrame, api_key: str, data_source_id: str, evidence_page_map: dict[str, str], run_id: str, max_rows: int = 200) -> pd.DataFrame:
    validate_v2_data_source_schema(api_key, data_source_id, "knowledge")
    results = []
    for row in candidates.head(max_rows).to_dict(orient="records"):
        item_id = str(row.get("knowledge_id") or row["candidate_id"])
        resource_ids = row.get("resource_ids") or [row.get("resource_id", "")]
        if isinstance(resource_ids, str):
            resource_ids = [resource_ids]
        evidence_pages = [evidence_page_map.get(str(resource_id), "") for resource_id in resource_ids]
        claim_text = row.get("canonical_text") or row.get("claim_text")
        held = str(row.get("decision_state")) == "HOLD"
        properties = {
            "Name": _title(f"{row.get('jurisdiction', 'GLOBAL')} · {row.get('predicate', 'knowledge')} · {str(claim_text or '')[:90]}"),
            "Knowledge ID": _rich_text(item_id), "Family": _select(row.get("claim_family")), "Predicate": _rich_text(row.get("predicate")),
            "Claim Text": _rich_text(claim_text), "Product Family": _rich_text(row.get("subject_product_family")),
            "Jurisdiction": _select(row.get("jurisdiction") or "GLOBAL"), "Applicability Scope": _rich_text(row.get("applicability_scope")),
            "Directness": _select(row.get("applicability_directness")), "Authority Tier": _select(row.get("authority_tier")),
            "Legal Status": _rich_text(row.get("legal_status")), "Confidence": _number(row.get("final_confidence", 0)),
            "Status": _select("HOLD" if held else "REVIEW_REQUIRED"), "Decision": _select("HOLD" if held else "PENDING"), "Risk": _select("LEGAL_OR_SAFETY"),
            "Evidence Sources": _relation(evidence_pages), "Source URL": _url(row.get("original_url")),
            "Run ID": _rich_text(run_id), "Reviewer Note": _rich_text(
                f"Awaiting human review; never auto-approved. Variants={row.get('variant_count', 1)}, evidence={row.get('evidence_count', 1)}."
            ),
        }
        response, action = _upsert_page(api_key, data_source_id, "Knowledge ID", item_id, properties, preserve_review=True)
        results.append({"candidate_id": item_id, "notion_page_id": response["id"], "action": action, "synced_at": utc_now()})
    return pd.DataFrame(results)


def sync_candidates(
    candidates: pd.DataFrame,
    api_key: str,
    data_source_id: str,
    category_name: str,
    run_id: str,
    mapping_path: Path,
    max_rows: int = 200,
) -> pd.DataFrame:
    validate_data_source_schema(api_key, data_source_id)
    results: list[dict[str, Any]] = []
    for row in candidates.head(max_rows).to_dict(orient="records"):
        candidate_id = str(row["candidate_id"])
        properties = candidate_properties(row, category_name, run_id)
        existing = find_page_by_candidate_id(api_key, data_source_id, candidate_id)
        if existing:
            update_properties = dict(properties)
            update_properties.pop("Decision", None)
            update_properties.pop("Reviewer Note", None)
            response = _request(
                "PATCH",
                f"/pages/{existing['id']}",
                api_key,
                {"properties": update_properties},
            )
            action = "UPDATED"
        else:
            response = _request(
                "POST",
                "/pages",
                api_key,
                {
                    "parent": {"type": "data_source_id", "data_source_id": data_source_id},
                    "properties": properties,
                },
            )
            action = "CREATED"
        results.append(
            {
                "candidate_id": candidate_id,
                "notion_page_id": response["id"],
                "action": action,
                "synced_at": utc_now(),
            }
        )
    frame = pd.DataFrame(results)
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_json(mapping_path, orient="records", lines=True, force_ascii=False)
    return frame


def _plain_text(prop: dict[str, Any]) -> str:
    prop_type = prop.get("type")
    if prop_type in {"title", "rich_text"}:
        return "".join(item.get("plain_text", "") for item in prop.get(prop_type, []))
    if prop_type == "select":
        selected = prop.get("select")
        return "" if not selected else str(selected.get("name", ""))
    if prop_type == "number":
        value = prop.get("number")
        return "" if value is None else str(value)
    if prop_type == "url":
        return str(prop.get("url") or "")
    return ""


def pull_decisions(api_key: str, data_source_id: str, run_id: str, id_property: str = "Candidate ID") -> pd.DataFrame:
    pages = query_pages(
        api_key,
        data_source_id,
        {"property": "Run ID", "rich_text": {"equals": run_id}},
    )
    rows: list[dict[str, Any]] = []
    for page in pages:
        props = page.get("properties", {})
        decision = _plain_text(props.get("Decision", {}))
        if decision not in {"APPROVED", "REJECTED", "HOLD", "PENDING"}:
            decision = "PENDING"
        rows.append(
            {
                "candidate_id": _plain_text(props.get(id_property, {})),
                "notion_page_id": page.get("id"),
                "review_decision": decision,
                "reviewer_note": _plain_text(props.get("Reviewer Note", {})),
                "notion_last_edited_time": page.get("last_edited_time"),
                "pulled_at": utc_now(),
            }
        )
    return pd.DataFrame(rows)
