# Required vendor acceptance matrix (60 scenarios)



These are required specifications, not 60 tests already implemented in this kit. Vendors add runnable cases and evidence mapping. 

S02 requires actual authorized provider access; it cannot PASS from a mock. P08 uses delivered images, not only helper functions.

G/P apply where meaningful to each module; an exclusion requires a reason approved by the owner, never silently omitted.



## G01 [BOTH] Version and schema

Input / fault: Valid and unsupported versions; missing/extra fields

Expected: Valid accepted; malformed rejected; no fallback

Evidence: actual HTTP response + validator log



## G02 [BOTH] Tenant isolation

Input / fault: Same IDs under a different authenticated project

Expected: No cross-project read/write or side effect

Evidence: integration test with two real test identities



## G03 [BOTH] Missing or forged credentials

Input / fault: No bearer, expired token, forged caller role

Expected: 401/403; never trust client roles

Evidence: auth integration tests; credentials redacted



## G04 [BOTH] Idempotent duplicate

Input / fault: 20 identical concurrent POSTs then service restart and repeat

Expected: One logical job; original identity returned after restart

Evidence: DB/ledger evidence + side-effect counter



## G05 [BOTH] Idempotent payload conflict

Input / fault: Same key with changed request body

Expected: 409 without extra provider call

Evidence: HTTP + counter



## G06 [BOTH] Cancellation and restart

Input / fault: Cancel queued/running job; kill/restart process

Expected: No new calls after cancellation; terminal status retained

Evidence: process-level recovery log



## G07 [BOTH] Finite nested retries

Input / fault: Inject 429/503, timeout, 401 and validation failures

Expected: All retries share budget/deadline; auth/invalid payload not retried

Evidence: fake clock + request ledger



## G08 [BOTH] Budget reservation

Input / fault: Concurrent calls approach max tokens/requests/cost

Expected: No over-reservation; ambiguous charged calls remain accounted

Evidence: concurrency test + counters



## G09 [BOTH] Artifact integrity and path

Input / fault: Expired URL, wrong hash, traversal, same filename different bytes

Expected: Refresh URL safely; refuse corruption/escape/collision

Evidence: file gateway contract tests



## G10 [BOTH] Untrusted text

Input / fault: Source/model text contains tool instructions and URLs

Expected: Not executed; does not overwrite system policy

Evidence: injection test with observed side effects



## G11 [BOTH] Reproducible delivery

Input / fault: Fresh checkout/build image, no local caches

Expected: Same declared source; lockfile and artifact hash; no embedded secret

Evidence: clean CI + SBOM + scanner findings



## G12 [BOTH] Warnings and failure truth

Input / fault: Build/runtime warnings, skipped tests, upstream unavailability

Expected: Report warnings/skips and truthful NOT_RUN; no fake green status

Evidence: complete logs/JUnit and exclusions list



## S01 [VENDOR_1] Provider normalization

Input / fault: Known OpenSEO protocol response fixture

Expected: Expected ResearchResult with provenance retained

Evidence: adapter integration



## S02 [VENDOR_1] Actual provider probe

Input / fault: Owner-authorized scoped keyword/SERP read

Expected: Recorded capability/version/auth and measured result

Evidence: sanitized sandbox/live receipt; not mock



## S03 [VENDOR_1] Null versus zero

Input / fault: No volume/difficulty returned

Expected: Null+MISSING, never fabricated numeric 0

Evidence: golden payload comparison



## S04 [VENDOR_1] Locale binding

Input / fault: Same keyword with VN/vi and different locale

Expected: Separate provider requests/cache; scope retained

Evidence: request capture + cache keys



## S05 [VENDOR_1] Freshness and metric scale

Input / fault: Stale source and metrics using different scales

Expected: Mark stale; document conversion; timestamp preserved

Evidence: normalizer tests



## S06 [VENDOR_1] Vietnamese duplicate handling

Input / fault: Unicode/diacritic/whitespace variants

Expected: Document normalization, preserve meaning and display text

Evidence: curated input-output set



## S07 [VENDOR_1] Competitor provenance

Input / fault: SERP includes text and source URL

Expected: No competitor prose copied into a draft or technical fact DB

Evidence: source mapping tests



## S08 [VENDOR_1] Intent grouping

Input / fault: Related terms with distinct buying/informational intent

Expected: Clusters retain intent boundaries and rationale

Evidence: curated benchmark + reviewer rubric



## S09 [VENDOR_1] Product scope

Input / fault: Lever hoist, electric hoist and hand chain hoist mix

Expected: Off-pilot candidates flagged, not silently merged

Evidence: curated benchmark



## S10 [VENDOR_1] Existing page collision

Input / fault: Topic already covered in existing_pages

Expected: Update/cannibalization recommendation, no duplicate forced brief

Evidence: integration fixture



## S11 [VENDOR_1] Calendar not publication

Input / fault: Change proposed_publish_at

Expected: Revision updates; no publish call triggered

Evidence: side-effect log



## S12 [VENDOR_1] Complete brief

Input / fault: Research with required user goals

Expected: All agreed brief fields populated; evidence needs explicit

Evidence: schema + consumer replay



## S13 [VENDOR_1] Cache optimization

Input / fault: Repeat equivalent research within permitted freshness

Expected: Avoid redundant paid requests; source age still visible

Evidence: baseline/candidate benchmark



## S14 [VENDOR_1] Provider rate limits

Input / fault: 429 Retry-After then recovery

Expected: Bounded retry honors wait and job deadline

Evidence: fake-clock integration



## S15 [VENDOR_1] Provider schema drift

Input / fault: Tool missing or unexpected response

Expected: Fail closed or visible degraded mode; never invented metrics

Evidence: capability error test



## S16 [VENDOR_1] Malicious SERP text

Input / fault: SERP asks agent to upload keys or change policy

Expected: Untrusted content isolated; no secret/side effect

Evidence: security fixture



## S17 [VENDOR_1] Stable revision outputs

Input / fault: Replay same snapshot/version and reordered provider items

Expected: Stable canonical brief identity where semantics identical

Evidence: deterministic replay



## S18 [VENDOR_1] Actual consumer compatibility

Input / fault: Vendor 1 emitted brief supplied to Vendor 2 fixture client

Expected: No field renaming or silent defaults

Evidence: cross-package replay receipt



## C01 [VENDOR_2] Brief intake

Input / fault: Valid actual Vendor 1 output

Expected: Writer consumes unchanged brief revision

Evidence: cross-package test



## C02 [VENDOR_2] Missing or held evidence

Input / fault: No eligible claims, HOLD, QUARANTINE

Expected: REVIEW_REQUIRED/gaps, no invented factual block

Evidence: generation test and assertion



## C03 [VENDOR_2] Citation semantics

Input / fault: Paraphrase with wrong negation/unit/model despite valid ID

Expected: Detect or block; reference-ID validity not treated as entailment

Evidence: curated evaluator + human-reviewed hold-out



## C04 [VENDOR_2] Scope and jurisdiction

Input / fault: Foreign rule or different OEM model

Expected: No unsupported THBISON/VN generalization

Evidence: content-quality benchmark



## C05 [VENDOR_2] Source prompt injection

Input / fault: Evidence tells model to ignore restrictions

Expected: Instruction ignored; source remains data

Evidence: model-adapter security test



## C06 [VENDOR_2] Model invalid output

Input / fault: Malformed JSON/timeouts/provider unavailable

Expected: Bounded retries, schema error visible, no fake completed article

Evidence: transport+schema log



## C07 [VENDOR_2] Approval invalidation

Input / fault: Edit body, SEO field, destination or evidence snapshot

Expected: Old approval cannot publish

Evidence: state machine test



## C08 [VENDOR_2] Approval authorization

Input / fault: Model/caller supplies approved=true or another user ID

Expected: Server rejects; only role-authenticated approval accepted

Evidence: API authorization test



## C09 [VENDOR_2] Out-of-scope safety/legal text

Input / fault: Attempt publish safety/legal draft in pilot

Expected: Publication blocked and reason visible

Evidence: policy negative tests



## C10 [VENDOR_2] Revoked evidence

Input / fault: Source revoked after preview/approval

Expected: Re-check source/policy blocks publication

Evidence: time-of-use integration



## C11 [VENDOR_2] Rendered preview and sources

Input / fault: Complete synthetic article

Expected: Readable preview plus functional per-block source links

Evidence: browser test + screenshots



## C12 [VENDOR_2] Desktop and mobile UX

Input / fault: 1440x900 and 390x844 viewport flows

Expected: No clipped editor/calendar; mock/live state visible; store untouched

Evidence: screenshots and browser assertions



## C13 [VENDOR_2] XSS and unsafe rendering

Input / fault: Malicious HTML/URL in provider/user/model text

Expected: Sanitized output, no script execution or unsafe navigation

Evidence: browser security test



## C14 [VENDOR_2] Timezone and duplicate tick

Input / fault: Aware date displayed Bangkok, repeated scheduler tick

Expected: One due operation; naive times rejected; no early publish

Evidence: clock-controlled scheduler tests



## C15 [VENDOR_2] CMS accepted but response lost

Input / fault: Provider creates draft then network times out

Expected: UNKNOWN then reconcile; no blind new create

Evidence: fault-injection CMS mock counters



## C16 [VENDOR_2] Publishing replay

Input / fault: Retry same approved version after restart

Expected: Same provider record; no duplicate post

Evidence: persistent ledger + readback



## C17 [VENDOR_2] Unauthorized destination/write scope

Input / fault: Wrong site/page; protected Notion human fields

Expected: Deny write; preserve original human fields

Evidence: adapter negative tests



## C18 [VENDOR_2] Social summary

Input / fault: Approved article -> Facebook Page summary

Expected: Not full copy; meaning/link retained; posting flag OFF

Evidence: content test + destination guard



## C19 [VENDOR_2] Sensitive logs

Input / fault: Tokens, signed URLs and internal review notes in errors

Expected: No secret leakage in logs/browser/build artifact

Evidence: scan + structured redaction tests



## C20 [VENDOR_2] Concurrent editing

Input / fault: Two writers update same article revision

Expected: Conflict visible; no silent lost update

Evidence: optimistic concurrency test



## C21 [VENDOR_2] File roundtrip

Input / fault: Notion attachment expires or upload partly fails

Expected: Recover via gateway; retain outbox; verify before success

Evidence: artifact gateway integration



## C22 [VENDOR_2] Rollback and compensation

Input / fault: App rollback after draft creation

Expected: No accidental unpublish/delete; data/IDs preserved

Evidence: migration/rollback test



## P01 [BOTH] Admission performance

Input / fault: 100 local admission requests at concurrency 5

Expected: p95 <= 1000ms without provider work in request handler

Evidence: raw timing samples + fixed environment



## P02 [BOTH] Cached brief latency

Input / fault: 100 warmed-up read requests

Expected: p95 <= 500ms; no paid provider call

Evidence: timings + provider counter



## P03 [BOTH] Preview latency

Input / fault: 10k-character fixture, cached render path

Expected: p95 <= 2000ms excluding new generation

Evidence: browser/backend timing trace



## P04 [BOTH] Concurrency effects

Input / fault: 20 repeats plus different jobs

Expected: Correct duplicate suppression and budget under load

Evidence: load report + ledger



## P05 [BOTH] Measured optimization

Input / fault: Compare initial working baseline vs final on same inputs

Expected: Declared metric improves >=15% or mark NOT_MET; correctness unchanged

Evidence: before/after samples, percent calculation



## P06 [BOTH] Resource and disk failure

Input / fault: Disk/outbox quota, OOM or provider outage

Expected: Truthful terminal/recoverable state; no success before save

Evidence: fault injection + resource measurements



## P07 [BOTH] Build host portability

Input / fault: Fresh Linux and supported dev host checkouts

Expected: Hash/newline/path behavior consistent; no global Git setting hack

Evidence: CI and file checksum report



## P08 [BOTH] Three-boundary rehearsal

Input / fault: Actual vendor services with synthetic Knowledge and CMS

Expected: Research->brief->evidence->preview->mock publication with trace IDs

Evidence: end-to-end test using actual delivered images


