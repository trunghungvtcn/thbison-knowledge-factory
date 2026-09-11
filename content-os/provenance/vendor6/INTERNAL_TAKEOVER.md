# INTERNAL_TAKEOVER — V6-R2-03 remaining preflight work

Owner: internal integration (not this vendor package).  
Scope file: `src/thbison_v6/staging/preflight.py` function `run_preflight` (frozen R2).  
Transport under test today: `FakeNotionTransport` (synthetic). `verified` must stay false until a trusted live/staging snapshot is supplied.  
Do not delete these obligations because mock tests pass.

Trusted input still required before any live claim: owner-pinned schema snapshot per data_source (id + type + relation destination `data_source_id`), relation allowlist, expected parent mapping, protocol version. Missing trusted input → `BLOCKED_OWNER_INPUT` / `UNKNOWN`. Token absence is `BLOCKED_ACCESS`, not proof that protocol code is complete.

---

## 1. Missing row parent is silent

**Where:** `run_preflight`, after query pagination, lines 300–303.

```
parent = (row.get("parent") or {}).get("data_source_id")
if parent and parent != dsid:
    findings.append({"issue": "WRONG_PARENT_DS", ...})
```

**Current:** finding only if `parent` is truthy and differs. A row with no `parent`, `parent: {}`, or `parent.data_source_id` omitted produces no finding.

**Required:** fail closed. Absent parent on a queried row → finding `MISSING_PARENT` (or `WRONG_PARENT_DS`) and not PREFLIGHT_OK.

**Fixture/input:** query page containing `{ "id": "row-no-parent" }` with no parent object; second row with `parent.data_source_id` equal to the queried DS (control).

**Expected test:** missing-parent row → finding present, status not OK; valid parent → no WRONG_PARENT_DS. Live/staging rows must carry Notion `parent.data_source_id`.

---

## 2. Per-property destination / data_source_id

**Where:** lines 285–290 (schema) and 324 (target page).

Schema dest:
```
dest = (at.get("relation") or {}).get("data_source_id") or at.get("relation_destination")
if spec.get("relation_destination") and dest and dest != spec.get("relation_destination"):
    findings.append(MAPPING_MISMATCH)
```

Target:
```
tparent = (page["json"].get("parent") or {}).get("page_id")
```

**Current:** target check uses `parent.page_id` against a global `expected_relation_parent` / allowlist. It does not compare the related page’s `parent.data_source_id` (or database_id) to the **per-property** relation mapping of that DS. One global hub id is not a per-relation map.

**Required:** for each expected relation property, pin `relation.database_id` / `relation.data_source_id`. Fetch the related page/database and require `parent.data_source_id` (or equivalent) equals that property’s destination. Multiple relation properties on one DS must not share a single expected parent unless the mapping says so.

**Fixture/input:** owner schema snapshot with two relation properties pointing at two destinations; related pages whose parent DS matches vs mismatches each mapping. Staging allowlist of destination DS ids.

**Expected test:** matching dest → no MAPPING_MISMATCH; page parent DS ≠ property dest → BLOCKED_STAGING_RELATIONS / MAPPING_MISMATCH; second property independent of the first.

---

## 3. Targets on later relation pages are not inspected

**Where:** lines 341–345.

```
rel_rows, rerr = _paginate(..., f"/v1/pages/{rel_id}/relations", ...)
if rerr:
    return {status: rerr, hop: "relation_pagination"}
# rel_rows never iterated
```

**Current:** pagination errors fail closed, but successful extra pages are discarded. A bad target only on page 2 of relation children is not classified.

**Required:** iterate every `rel_rows` item (all pages within budget) and apply the same parent/allowlist/`data_source_id` checks as page 1. Cursor loop / missing cursor / page budget already fail closed and must stay fail closed.

**Fixture/input:** relation collection with page_size 2 and ≥3 children; child on page 2 has parent outside allowlist or wrong DS; page 1 children valid.

**Expected test:** finding on the page-2 target; status not PREFLIGHT_OK_FAKE_TRANSPORT. Control: all pages valid → no relation finding.

---

## 4. Schema property ID not compared; missing dest skipped

**Where:** lines 275–290.

Compare is `for name, spec in expected.properties`. Notion properties also have stable `id`. Rename/id swap would not be caught if names still match.

Missing dest:
```
if spec.get("relation_destination") and dest and dest != spec.get("relation_destination"):
```
If the live schema omits `relation.data_source_id` / `relation_destination`, `dest` is falsy and the branch is skipped — no MAPPING_MISMATCH.

**Required:**
- Expected fixture includes property `id` (and name). Actual schema must match id; name-only match is insufficient when ids exist.
- If expected mapping requires a destination and actual dest is missing → MAPPING_MISMATCH (or MISSING_DEST), not silent OK.

**Fixture/input:** expected `{ "Related": { "id": "prop-abc", "type": "relation", "relation": { "data_source_id": "<dest>" } } }`; actual with same name different id; actual relation type with dest omitted.

**Expected test:** id mismatch → SCHEMA_DRIFT / ID_MISMATCH; missing dest → MAPPING_MISMATCH; matching id+dest → no those findings.

---

## 5. Synthetic protocol pin is not a live snapshot

**Where:** `fixtures/staging/protocol.json` provenance.pin `v6-r2-preflight-1`. `run_preflight` sets `verified = False` unconditionally.

**Current:** fixture is vendor-authored synthetic mapping for one DS id from STAGING_ACCESS_MANIFEST. Pin is a label, not a hash of a retrieved Notion schema.

**Required:** owner supplies a retrieved schema dump (GET data_source) with content hash recorded as pin. Preflight compares against that dump. `verified=true` only after live/staging read against that pin under granted allowlist. Until then keep `verified=false`.

**Fixture/input:** out-of-band short-lived token + retrieved JSON + sha256; not committed secrets. Missing dump → BLOCKED_OWNER_INPUT.

**Expected test:** no-dump → BLOCKED_OWNER_INPUT; dump vs drifted GET → DRIFT; fake transport run never sets verified true.

---

## Suggested internal job (not executed here)

Do not silently drop items 1–5. Suggested order: trusted schema snapshot → property id + dest required → row parent required → per-property parent.data_source_id → iterate rel_rows. Keep fake-transport tests as regression, add fixtures that fail today, then optionally a gated live read. INT-26/27 and G1 remain separate gates.
