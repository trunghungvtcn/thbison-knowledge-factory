# Notion v2 review setup

Notion is a temporary review surface. Parquet outputs remain the pilot source of truth.

## Required secrets

Create these Kaggle Secrets only after rotating any credential previously exposed in chat or notebooks:

- `NOTION_API_KEY`
- `NOTION_EVIDENCE_DATA_SOURCE_ID` (optional override; otherwise config is used)
- `NOTION_PRODUCT_ATTRIBUTES_DATA_SOURCE_ID` (optional override)
- `NOTION_KNOWLEDGE_ITEMS_DATA_SOURCE_ID` (optional override)
- `YESCALE_API_KEY` only when DeepSeek is enabled

The integration must be connected to the parent database/data source.

## Required Notion databases

The pipeline validates and writes three separate data sources:

- `Evidence Sources`: upserted by `Resource ID`.
- `Product Attributes`: upserted by `Attribute ID`, related to Evidence Sources.
- `Knowledge Items`: upserted by `Knowledge ID`, related to Evidence Sources.

Exact IDs and property contracts are recorded in `config/pilot_config.yaml` and checked before any write. A mismatch stops synchronization.

## Review flow

1. Notebook upserts sources, then product and knowledge candidates within the admission limit.
2. Reviewer changes `Decision` and adds `Reviewer Note`.
3. Notebook pulls a versioned decision snapshot.
4. Only `APPROVED` rows are exported to the corresponding approved Parquet file.
5. Notion deletion or edits never delete raw evidence or candidate history.
6. Resync preserves existing human `Status`, `Decision`, and `Reviewer Note`.

## API compatibility

The integration uses `Notion-Version: 2026-03-11`, `data_source_id` as the page parent, and the data-source query endpoint. Do not substitute the visible database URL for the data source ID.
