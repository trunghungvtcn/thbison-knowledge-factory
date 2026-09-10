# Knowledge output → EvidenceBundle 1.0.0

The integration gateway is `src/kf_pilot/content_os_gateway.py`. It accepts only a normalized `TEST_ONLY` Knowledge envelope. Live Notion rows are not read or inferred here.

| EvidenceBundle field | Knowledge source | Missing/mismatch policy |
|---|---|---|
| `project_id` | envelope `project_id` | reject on requested-project mismatch |
| `data_class` | envelope `data_class` | reject unless exactly `TEST_ONLY` |
| `bundle_id` | SHA-256 of project, Knowledge revision, mapped claims | deterministic; never caller supplied |
| `snapshot_sha256` | canonical SHA-256 of the mapped bundle excluding this field | recomputed by gateway |
| `policy_version` | envelope `policy_version` | reject if missing |
| `as_of` | envelope `as_of` | reject if missing; no invented current time |
| claim identity | `claims[].claim_id` | placeholder identity plus `HOLD` if missing |
| source identity/revision/hash/locator | `claims[].source.{id,revision,sha256,locator}` | claim becomes `HOLD`, no allowed uses, and a gap is recorded |
| quote hash | SHA-256 of `claims[].quote` compared to `quote_sha256` | mismatch becomes `HOLD` |
| status | normalized upstream status | `HUMAN_HOLD`, `REVIEW_REQUIRED`, `HOLD`, and `QUARANTINE` never become eligible |
| allowed uses | derived only after verified provenance and `ELIGIBLE` status | `[DRAFT]` for verified TEST_ONLY claim; otherwise empty |

The committed fixture is synthetic and is not evidence of real Knowledge/Notion integration. Missing real input remains `NOTION_TARGET_MISSING` / `live_data_pass=false`.
