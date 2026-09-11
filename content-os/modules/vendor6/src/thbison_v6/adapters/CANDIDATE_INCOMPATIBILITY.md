# Candidate interface notes (unaccepted; not production)

## Vendor 4 (artifact 21231e3e…)
- FastAPI: POST `/v1/knowledge/query`, GET `/v1/evidence/{bundle_id}`, assets upload/refresh.
- Auth: `Authorization: Bearer`, `X-Contract-Version: 1.0.0`, POST `Idempotency-Key`.
- Query body uses `project_id`, `product_id`, `jurisdiction`, `locale` — **not** a ContentBrief object.
- Mapping PROPOSED: harness sends ContentBrief; adapter must extract product_refs[0] → product_id and scope.country_code → jurisdiction. Owner must confirm; not silently remapped as compatible.
- No pinned start command or lab endpoint in handoff COMPONENT inputs. Cannot launch ACTUAL in this package.

## Vendor 3 (artifact 031ab548…)
- Routes: POST `/v1/jobs`, leases, reconcile. Auth via `X-Service-Id` / `X-Project-Id` headers, not Bearer.
- Incompatible with V4 Bearer scheme. MIXED actual wiring needs an explicit header map (PROPOSED).

## Vendor 2
- Candidate zip is a large UI/app tree; no verified THBISON adapter listen address in the kit.

## Vendor 1 / Vendor 5
- Missing from handoff. ACTUAL_COMPONENTS must fail closed with MISSING_ADAPTER:planning and MISSING_ADAPTER:cms.
