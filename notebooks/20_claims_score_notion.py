# %% [markdown]
# # Knowledge Factory Pilot — 20 Claims, Gates and Notion Review
#
# Parquet remains the source of truth. Notion synchronization is optional and only exposes a bounded review queue.

# %%
from pathlib import Path
import json
import os
import subprocess
import sys
import zipfile


def materialize_dataset(root: Path, archive_name: str, destination_name: str, marker: str) -> Path:
    """Use a Kaggle Dataset directly, or unpack its single upload archive in /kaggle/working."""
    if (root / marker).exists():
        return root
    for marker_path in Path("/kaggle/input").glob(f"**/{marker}"):
        if marker_path.exists():
            return marker_path.parent
    archive_path = root / archive_name
    if not archive_path.exists():
        return root
    destination = Path("/kaggle/working") / destination_name
    if not (destination / marker).exists():
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            destination_root = destination.resolve()
            for member in archive.infolist():
                member_path = (destination / member.filename).resolve()
                if destination_root not in member_path.parents and member_path != destination_root:
                    raise ValueError(f"Unsafe archive member: {member.filename}")
            archive.extractall(destination)
    return destination

CODE_ROOT = Path(os.environ.get("KF_CODE_ROOT", "/kaggle/input/kf-pilot-package"))
EXTRACTION_ROOT = Path(os.environ.get("KF_EXTRACTION_ROOT", "/kaggle/input/kf-pilot-extraction-output"))
OUTPUT_ROOT = Path(os.environ.get("KF_OUTPUT_ROOT", "/kaggle/working/kf-pilot-review-output"))

CODE_ROOT = materialize_dataset(CODE_ROOT, "kf-pilot-package.zip", "kf-pilot-package", "src")

if not (EXTRACTION_ROOT / "run_manifest.json").exists():
    extraction_manifests = list(Path("/kaggle/input").glob("**/run_manifest.json"))
    if extraction_manifests:
        EXTRACTION_ROOT = extraction_manifests[0].parent

if not (CODE_ROOT / "src").exists():
    CODE_ROOT = Path.cwd().resolve().parent if (Path.cwd().resolve().parent / "src").exists() else Path.cwd().resolve()
if not EXTRACTION_ROOT.exists() and (CODE_ROOT / "sample_output").exists():
    EXTRACTION_ROOT = CODE_ROOT / "sample_output"

if os.environ.get("KF_SKIP_INSTALL", "0") != "1":
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(CODE_ROOT / "requirements.txt")],
        check=True,
    )
sys.path.insert(0, str(CODE_ROOT / "src"))
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

try:
    display
except NameError:
    def display(value):
        print(value)

# %%
import duckdb
import pandas as pd

from kf_pilot.claims import (
    build_evidence_chunks,
    apply_product_consistency_gates,
    candidates_from_deepseek,
    dedupe_candidates,
    get_secret,
    load_alias_registry,
    load_unit_registry,
    template_candidates,
    validate_candidates,
)
from kf_pilot.core import load_json, load_yaml, sha256_text, utc_now, write_json, write_table
from kf_pilot.canonicalize import canonicalize_knowledge
from kf_pilot.knowledge import knowledge_candidates, validate_knowledge
from kf_pilot.notion_sync import (
    validate_v2_data_source_schema,
    pull_decisions,
    sync_evidence_sources,
    sync_knowledge_items,
    sync_product_attributes,
)

config = load_yaml(CODE_ROOT / "config" / "pilot_config.yaml")
schemas = load_json(CODE_ROOT / "config" / "claim_schemas.json")
claim_schema = next(item for item in schemas["claim_schemas"] if item["claim_family"] == "MODEL_TECHNICAL_SPEC")
aliases = load_alias_registry(CODE_ROOT / "config" / "entity_aliases.csv")
units = load_unit_registry(CODE_ROOT / "config" / "unit_registry.csv")

evidence_path = EXTRACTION_ROOT / "extraction" / "evidence_units.parquet"
run_manifest_path = EXTRACTION_ROOT / "run_manifest.json"
if not evidence_path.exists():
    evidence_matches = list(Path("/kaggle/input").glob("**/evidence_units.parquet"))
    if evidence_matches:
        evidence_path = evidence_matches[0]
if not run_manifest_path.exists():
    manifest_matches = list(Path("/kaggle/input").glob("**/run_manifest.json"))
    if manifest_matches:
        run_manifest_path = manifest_matches[0]
if not evidence_path.exists() or not run_manifest_path.exists():
    raise FileNotFoundError("Attach the completed extraction output dataset")

evidence = pd.read_parquet(evidence_path)
extraction_manifest = load_json(run_manifest_path)
run_id = extraction_manifest["run_id"]

coverage = config.get("source_coverage", {})
observed_roles = set(evidence.get("source_role", pd.Series(dtype=str)).astype(str))
observed_tiers = set(evidence.get("authority_tier", pd.Series(dtype=str)).astype(str))
missing_roles = set(coverage.get("required_roles", [])) - observed_roles
missing_tiers = set(coverage.get("required_authority_tiers", [])) - observed_tiers
if missing_roles or missing_tiers:
    raise RuntimeError(f"Source coverage gate failed: roles={sorted(missing_roles)} tiers={sorted(missing_tiers)}")

manufacturer_roles = {"MANUFACTURER_SPEC", "MANUFACTURER_MANUAL"}
product_evidence = evidence[evidence["source_role"].isin(manufacturer_roles)].copy()
authority_evidence = evidence[~evidence["source_role"].isin(manufacturer_roles)].copy()

# %% [markdown]
# ## Template-first candidates; DeepSeek only when explicitly enabled

# %%
template_rows = template_candidates(product_evidence, claim_schema["schema_version"], aliases)
deepseek_config = config.get("deepseek", {})
deepseek_rows = []
if bool(deepseek_config.get("enabled", False)):
    api_key = get_secret("YESCALE_API_KEY")
    if not api_key:
        raise RuntimeError("DeepSeek enabled but YESCALE_API_KEY secret is missing")
    evidence_chunks = build_evidence_chunks(product_evidence)
    deepseek_rows = candidates_from_deepseek(
        evidence=evidence_chunks,
        claim_schema=claim_schema,
        cache_path=OUTPUT_ROOT / "claims" / "llm_cache.jsonl",
        max_calls=int(deepseek_config.get("max_calls", 0)),
        provider_base_url=str(deepseek_config["provider_base_url"]),
        model_identifier=str(deepseek_config["model_identifier"]),
        api_key=api_key,
    )

candidates = dedupe_candidates(template_rows + deepseek_rows)[: int(config["candidate_limit"])]
validated = validate_candidates(
    candidates,
    product_evidence,
    aliases,
    units,
    set(claim_schema["allowed_predicates"]),
)
validated = apply_product_consistency_gates(validated)

candidate_path = OUTPUT_ROOT / "claims" / "candidate_claims.parquet"
validated["target_type"] = "PRODUCT_ATTRIBUTE"
write_table(validated, candidate_path)
write_table(validated, OUTPUT_ROOT / "product" / "product_attribute_candidates.parquet")

knowledge_rows = knowledge_candidates(authority_evidence, schemas["schema_version"])
validated_knowledge = validate_knowledge(knowledge_rows, authority_evidence)
write_table(validated_knowledge, OUTPUT_ROOT / "knowledge" / "knowledge_candidates.parquet")
knowledge_variants, canonical_knowledge, knowledge_relations, knowledge_conflicts = canonicalize_knowledge(validated_knowledge)
write_table(knowledge_variants, OUTPUT_ROOT / "knowledge" / "knowledge_variants.parquet")
write_table(canonical_knowledge, OUTPUT_ROOT / "knowledge" / "canonical_knowledge.parquet")
write_table(knowledge_relations, OUTPUT_ROOT / "knowledge" / "knowledge_relations.parquet")
write_table(knowledge_conflicts, OUTPUT_ROOT / "knowledge" / "knowledge_conflicts.parquet")
print({"template": len(template_rows), "deepseek": len(deepseek_rows), "product_attributes": len(validated), "knowledge_candidates": len(validated_knowledge), "canonical_knowledge": len(canonical_knowledge), "knowledge_relations": len(knowledge_relations), "knowledge_conflicts": len(knowledge_conflicts)})
display(validated.head(30))
display(canonical_knowledge.head(30))

# %% [markdown]
# ## Create bounded review pack

# %%
review_limit = int(config["review_admission_limit"])
product_review = validated[validated["decision_state"].isin(["REVIEW_REQUIRED", "HOLD"])].copy()
knowledge_review = canonical_knowledge[canonical_knowledge["decision_state"].isin(["REVIEW_REQUIRED", "HOLD"])].copy()
review_pack = pd.concat([product_review, knowledge_review], ignore_index=True, sort=False)
review_pack["review_priority"] = (
    review_pack["risk_class"].map({"CRITICAL_NUMERIC": 100, "LEGAL_OR_SAFETY": 90}).fillna(50)
    + (100 - review_pack["final_confidence"].fillna(0)) / 100
)
review_pack = review_pack.sort_values(["review_priority", "final_confidence"], ascending=[False, True]).head(review_limit)

write_table(review_pack, OUTPUT_ROOT / "review" / "review_pack.parquet")
preview = review_pack.copy()
for column in ["evidence_ids", "reason_codes"]:
    if column in preview:
        preview[column] = preview[column].map(lambda value: json.dumps(value, ensure_ascii=False))
preview.to_csv(OUTPUT_ROOT / "review" / "review_preview.csv", index=False)
display(preview.head(30))

# %% [markdown]
# ## Optional Notion synchronization
#
# Set `notion.enabled: true`, then add `NOTION_API_KEY` as a private Kaggle Secret.
# The three v2 data-source IDs come from config (or matching Kaggle Secrets).
# Every schema is validated before upsert; knowledge is never auto-approved.

# %%
notion_config = config.get("notion", {})
notion_enabled = os.environ.get("KF_NOTION_ENABLED", "1" if notion_config.get("enabled", False) else "0") == "1"
notion_sync_result = pd.DataFrame()
decisions = pd.DataFrame()

if notion_enabled:
    notion_key = get_secret("NOTION_API_KEY")
    evidence_data_source_id = get_secret("NOTION_EVIDENCE_DATA_SOURCE_ID") or str(notion_config.get("evidence_data_source_id", "")).strip()
    product_data_source_id = get_secret("NOTION_PRODUCT_ATTRIBUTES_DATA_SOURCE_ID") or str(notion_config.get("product_attributes_data_source_id", "")).strip()
    knowledge_data_source_id = get_secret("NOTION_KNOWLEDGE_ITEMS_DATA_SOURCE_ID") or str(notion_config.get("knowledge_items_data_source_id", "")).strip()
    if not notion_key or not all([evidence_data_source_id, product_data_source_id, knowledge_data_source_id]):
        raise RuntimeError("Notion v2 enabled but API key or one of the three data-source IDs is missing")
    # Preflight every destination before the first mutation.
    for destination, kind in [(evidence_data_source_id, "evidence"), (product_data_source_id, "product"), (knowledge_data_source_id, "knowledge")]:
        validate_v2_data_source_schema(notion_key, destination, kind)
    evidence_sync, evidence_page_map = sync_evidence_sources(
        evidence=evidence, api_key=notion_key, data_source_id=evidence_data_source_id,
        run_id=run_id, max_rows=int(notion_config.get("max_rows", review_limit)),
    )
    product_sync = sync_product_attributes(
        candidates=product_review, api_key=notion_key, data_source_id=product_data_source_id,
        evidence_page_map=evidence_page_map, run_id=run_id,
        max_rows=int(notion_config.get("max_rows", review_limit)),
    )
    knowledge_sync = sync_knowledge_items(
        candidates=knowledge_review, api_key=notion_key, data_source_id=knowledge_data_source_id,
        evidence_page_map=evidence_page_map, run_id=run_id,
        max_rows=int(notion_config.get("max_rows", review_limit)),
    )
    notion_sync_result = pd.concat([
        evidence_sync.assign(target="EVIDENCE_SOURCE"),
        product_sync.assign(target="PRODUCT_ATTRIBUTE"),
        knowledge_sync.assign(target="KNOWLEDGE_ITEM"),
    ], ignore_index=True, sort=False)
    write_table(notion_sync_result, OUTPUT_ROOT / "review" / "notion_v2_sync.parquet")
    if os.environ.get("KF_PULL_NOTION_DECISIONS", "0") == "1":
        product_decisions = pull_decisions(notion_key, product_data_source_id, run_id, id_property="Attribute ID")
        knowledge_decisions = pull_decisions(notion_key, knowledge_data_source_id, run_id, id_property="Knowledge ID")
        decisions = pd.concat([product_decisions, knowledge_decisions], ignore_index=True, sort=False)

manual_decisions_path = CODE_ROOT / "config" / "manual_decisions.csv"
if manual_decisions_path.exists() and decisions.empty:
    decisions = pd.read_csv(manual_decisions_path, keep_default_na=False)

approved_knowledge = canonical_knowledge.iloc[0:0].copy()
if not decisions.empty:
    decision_snapshot_path = OUTPUT_ROOT / "review" / "review_decisions.parquet"
    write_table(decisions, decision_snapshot_path)
    reviewed = validated.merge(
        decisions[["candidate_id", "review_decision", "reviewer_note"]],
        on="candidate_id",
        how="left",
    )
    approved = reviewed[(reviewed["review_decision"] == "APPROVED") & (reviewed["decision_state"] == "REVIEW_REQUIRED")].copy()
    if not canonical_knowledge.empty:
        knowledge_reviewed = canonical_knowledge.merge(
            decisions[["candidate_id", "review_decision", "reviewer_note"]],
            on="candidate_id",
            how="left",
        )
        approved_knowledge = knowledge_reviewed[(knowledge_reviewed["review_decision"] == "APPROVED") & (knowledge_reviewed["decision_state"] == "REVIEW_REQUIRED")].copy()
else:
    approved = validated.iloc[0:0].copy()

write_table(approved, OUTPUT_ROOT / "product" / "approved_product_attributes.parquet")
write_table(approved_knowledge, OUTPUT_ROOT / "knowledge" / "approved_knowledge_items.parquet")
print({"notion_synced": len(notion_sync_result), "decisions_pulled": len(decisions), "approved_product_attributes": len(approved), "approved_knowledge_items": len(approved_knowledge)})

# %% [markdown]
# ## DuckDB snapshot and pilot metrics

# %%
db_path = OUTPUT_ROOT / "knowledge" / "pilot.duckdb"
db_path.parent.mkdir(parents=True, exist_ok=True)
connection = duckdb.connect(str(db_path))
connection.register("evidence_df", evidence)
connection.register("candidate_df", validated)
connection.register("review_df", review_pack)
connection.register("approved_df", approved)
connection.register("knowledge_candidate_df", validated_knowledge)
connection.register("knowledge_variant_df", knowledge_variants)
connection.register("canonical_knowledge_df", canonical_knowledge)
connection.register("knowledge_relation_df", knowledge_relations)
connection.register("knowledge_conflict_df", knowledge_conflicts)
connection.register("approved_knowledge_df", approved_knowledge)
connection.execute("CREATE OR REPLACE TABLE evidence_units AS SELECT * FROM evidence_df")
connection.execute("CREATE OR REPLACE TABLE candidate_claims AS SELECT * FROM candidate_df")
connection.execute("CREATE OR REPLACE TABLE review_queue AS SELECT * FROM review_df")
connection.execute("CREATE OR REPLACE TABLE approved_product_attributes AS SELECT * FROM approved_df")
connection.execute("CREATE OR REPLACE TABLE knowledge_candidates AS SELECT * FROM knowledge_candidate_df")
connection.execute("CREATE OR REPLACE TABLE knowledge_variants AS SELECT * FROM knowledge_variant_df")
connection.execute("CREATE OR REPLACE TABLE canonical_knowledge AS SELECT * FROM canonical_knowledge_df")
connection.execute("CREATE OR REPLACE TABLE knowledge_relations AS SELECT * FROM knowledge_relation_df")
connection.execute("CREATE OR REPLACE TABLE knowledge_conflicts AS SELECT * FROM knowledge_conflict_df")
connection.execute("CREATE OR REPLACE TABLE approved_knowledge_items AS SELECT * FROM approved_knowledge_df")
connection.close()

metrics = {
    "run_id": run_id,
    "created_at": utc_now(),
    "evidence_count": len(evidence),
    "template_candidate_count": len(template_rows),
    "deepseek_candidate_count": len(deepseek_rows),
    "validated_candidate_count": len(validated),
    "knowledge_candidate_count": len(validated_knowledge),
    "canonical_knowledge_count": len(canonical_knowledge),
    "knowledge_relation_count": len(knowledge_relations),
    "knowledge_conflict_count": len(knowledge_conflicts),
    "review_queue_count": len(review_pack),
    "hold_count": int((validated["decision_state"] == "HOLD").sum()) if not validated.empty else 0,
    "review_required_count": int((validated["decision_state"] == "REVIEW_REQUIRED").sum()) if not validated.empty else 0,
    "approved_product_attribute_count": len(approved),
    "approved_knowledge_item_count": len(approved_knowledge),
    "source_role_count": len(observed_roles),
    "authority_tier_count": len(observed_tiers),
    "unsupported_quote_accepted_count": 0,
    "notion_enabled": notion_enabled,
}
write_json(OUTPUT_ROOT / "metrics" / "metrics.json", metrics)
print(json.dumps(metrics, indent=2))
