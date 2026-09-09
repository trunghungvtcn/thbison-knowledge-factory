from datetime import datetime
from urllib.parse import urlparse

from .canonical import exact, require

AST_KEYS = {"op", "args"}
LEAF_KEYS = {"op", "field", "cmp", "value"}


def iso_time(value):
    require(type(value) is str, "TIME_TYPE")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "TIMEZONE_REQUIRED")
    return parsed


def validate_ast(node, depth=0, counter=None):
    counter = counter or [0]
    counter[0] += 1
    require(counter[0] <= 128, "AST_NODE_LIMIT")
    require(depth <= 12, "AST_DEPTH_LIMIT")
    require(type(node) is dict, "AST_TYPE")
    op = node.get("op")
    if op in {"AND", "OR"}:
        exact(node, AST_KEYS, "AST_BRANCH")
        require(type(node["args"]) is list and 2 <= len(node["args"]) <= 16, "AST_ARITY")
        for child in node["args"]:
            validate_ast(child, depth + 1, counter)
    elif op == "NOT":
        exact(node, {"op", "arg"}, "AST_NOT")
        validate_ast(node["arg"], depth + 1, counter)
    elif op == "PREDICATE":
        exact(node, LEAF_KEYS, "AST_LEAF")
        require(type(node["field"]) is str and node["field"], "AST_FIELD")
        require(node["cmp"] in {"EQ", "NE", "GT", "GTE", "LT", "LTE", "IN"}, "AST_COMPARATOR")
    elif op == "UNRESOLVED":
        require(set(node) in ({"op", "reason"}, {"op", "reason", "legacy_tags"}), "KEY_SET_MISMATCH", "AST_UNRESOLVED")
        require(type(node["reason"]) is str and node["reason"].strip(), "AST_REASON")
        if "legacy_tags" in node:
            require(type(node["legacy_tags"]) is list and all(type(x) is str for x in node["legacy_tags"]), "AST_LEGACY_TAGS")
    elif op in {"TRUE", "FALSE"}:
        exact(node, {"op"}, "AST_CONSTANT")
    else:
        require(False, "AST_UNKNOWN_OPERATOR")
    return node


def validate_research_plan(plan):
    exact(plan, {"schema_version", "sources"}, "RESEARCH_PLAN")
    require(plan["schema_version"] == 1 and type(plan["sources"]) is list, "RESEARCH_PLAN_VERSION")
    ids = set()
    for item in plan["sources"]:
        exact(item, {"source_id", "url", "role", "provenance_family"}, "SOURCE")
        require(item["source_id"] not in ids, "DUPLICATE_SOURCE_ID")
        ids.add(item["source_id"])
        parsed = urlparse(item["url"])
        require(parsed.scheme == "https" and parsed.hostname, "PUBLIC_HTTPS_REQUIRED")
        require(type(item["role"]) is str and type(item["provenance_family"]) is str, "SOURCE_TYPE")
    return plan


def validate_run_config(config):
    exact(config, {"schema_version", "data_class", "as_of", "frozen_corpus", "v165_run", "expected_baseline", "target_entity_ids"}, "RUN_CONFIG")
    require(config["schema_version"] == 1, "RUN_CONFIG_VERSION")
    require(config["data_class"] in {"REPOSITORY", "TEST_ONLY"}, "DATA_CLASS")
    iso_time(config["as_of"])
    require(type(config["target_entity_ids"]) is list and len(config["target_entity_ids"]) == len(set(config["target_entity_ids"])), "DUPLICATE_TARGET")
    return config


def validate_trust(config):
    exact(config, {"schema_version", "trusted_pins", "receipts"}, "TRUST_CONFIG")
    require(config["schema_version"] == 1, "TRUST_CONFIG_VERSION")
    require(type(config["trusted_pins"]) is dict and type(config["receipts"]) is dict, "TRUST_TYPE")
    require(set(config["trusted_pins"]) == {"registry", "activation", "adjudication"}, "TRUST_ROOTS_INCOMPLETE")
    require(set(config["receipts"]) == set(config["trusted_pins"]), "RECEIPTS_INCOMPLETE")
    return config
