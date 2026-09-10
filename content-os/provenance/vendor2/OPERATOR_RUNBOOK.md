# Operator runbook — THBISON Content OS (Vendor 2)

Simulation-first handover. This module does **not** connect to live THBISON
CMS, Knowledge, OpenSEO, Facebook, or production databases. The internal team
configures those adapters after intake.

## Start (preview / mock)

```bash
npm ci
CONTENT_OS_MODE=MOCK npm run dev
```

Listens on `0.0.0.0:8080`.

Health (no auth): `GET /healthz` → `{ "status": "ok" }`.

Capabilities (service token + `X-Contract-Version: 1.0.0`): `GET /v1/capabilities`.

## Demo tokens (TEST_ONLY)

| Role   | Bearer token                         | project_id      | can_publish |
|--------|--------------------------------------|-----------------|-------------|
| editor | `svc_editor_test_thbison_ok12`       | test-thbison    | true        |
| reader | `svc_reader_test_thbison_ok12`       | test-thbison    | false       |
| other  | `svc_editor_other_project_ok12`      | other-thbison   | true        |

Workspace UI identity switcher sets an httpOnly cookie; API uses Bearer.

## Required headers

- `Authorization: Bearer <token>`
- `X-Contract-Version: 1.0.0`
- `Idempotency-Key: <16-128 printable ASCII>` on POST jobs / publications / cancel

## Happy-path UI

1. Open Kế hoạch → brief `test-brief-1`.
2. Tạo bản nháp từ fixture.
3. Mở Bài viết → xem trước (rendered, not JSON).
4. Sửa một khối → lưu revision (approval cũ hết hiệu lực).
5. Duyệt revision mới.
6. Tạo MOCK draft (`DRY_RUN`). LIVE and STAGING flags stay off.

## Docker

```bash
docker compose up --build
```

Runs as non-root user `app` (uid 10001). No privileged mode.

## Rollback

1. Stop the process / compose service.
2. Do not toggle `allow_live`.
3. Restore the previous container image / git tree.
4. MOCK data in PGLite is ephemeral; Neon (when the team sets `DATABASE_URL`) is the durable store.

## Flags (must stay false in this drop)

- `allow_live=false`
- `allow_staging=false`
- `allow_social=false`

## Vendor 3 queue adapter

`POST /v1/content/jobs` and `POST /v1/planning/jobs` persist `QUEUED` and return **202 immediately**. They call `getQueue().dispatch(jobId, kind)` and do not await the processor.

Vendor 3 owns runtime:

1. Implement `QueuePort` (`dispatch` + `drain`).
2. Call `setQueuePort(yourPort)` at process start.
3. From workers, call the registered processor (same `processContentJob` / `processPlanningJob`). Do not fork gate/writer/CMS logic.

Default MOCK port runs the processor on a microtask so GET eventually sees a terminal status.

## Durable-store simulator

`POST /v1/mock/ledger/restart` (service token) serializes all `cos_*` tables to a local JSON snapshot, wipes memory, and reloads. It is **not** a THBISON database. Use it only in MOCK tests.

## What this drop does not do

- Does not call real Knowledge, CMS, OpenSEO, or Facebook.
- Does not deploy to VPS B / canary.
- Does not create public posts (`public_posts_created=0`).
- Does not spend paid API budget (`paid_calls=0`).
- Does not claim KIT_SELF_TEST_PASS, ADAPTER_VERIFIED, or INTEGRATED_CANARY_PASS.
