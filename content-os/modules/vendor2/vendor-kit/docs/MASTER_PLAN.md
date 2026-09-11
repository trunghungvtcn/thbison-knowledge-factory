# Delegation and integration plan

## Decision

Run two vendor workstreams in parallel, retain the Knowledge V16 project internally.
This is not an instruction to restart V16, create another content strategy, or build two competing dashboards.
The product milestone is one real brief -> evidence-bound preview -> approved staging draft.

## Ownership matrix

| Boundary | Producer / owner | Consumer | Acceptance artifact |
|---|---|---|---|
| SEO observations | Vendor 1 via OpenSEO adapter | Planning backend | ResearchResult + provenance |
| Brief revisions | Vendor 1; user changes through Content OS UI | Vendor 2 writer | ContentBrief |
| Evidence snapshots | Internal Knowledge team | Vendor 2 writer | EvidenceBundle |
| Article/approval/publication state | Vendor 2 | User + publisher | ArticlePackage + ApprovalRecord + PublicationReceipt |
| Authentication / policy authority | Internal operator, using declared roles | Both modules | trusted identity and capability probe |
| Long-lived data/files | Notion through approved internal gateway | Both modules | stable ID + verified hash |
| Scheduler tick / worker leases | VPS B coordinator | Content OS job handlers | durable receipts, no duplicate logical action |
| UI shell and all integrated screens | Vendor 2 | User | approved UX + screenshot/test evidence |

Planning's proposed publication date is NOT authority to publish. Only Vendor 2's approved release state
can be executed after an authorized scheduler tick. No second independent publishing cron is allowed.
No module may directly alter Knowledge Status, Decision or Reviewer Note.

## Repository strategy (proposal, not a claim repositories have been created)

Use two CLEAN private vendor repositories owned by THBISON:
`thbison-seo-planning` and `thbison-content-os`.
Do not invite external teams into the full V16 repo just to work on two branches: it contains history
that has previously been classified as potentially sensitive. Git branches are workflow partitions,
not a promised data-disclosure boundary.
Teams get only the contract kit, synthetic fixtures and explicitly approved sanitized inputs.
No external collaborator invitations are sent by this handoff.

Vendor 1 branch `vendor/seo-planning`; Vendor 2 branch `vendor/content-workflow`.
One reviewed release per module. After acceptance, import clean source or use versioned images/packages
from these repositories; do NOT merge two unrelated app roots and overwrite lockfiles.
Keep independent lockfiles/build contexts; shared DTOs are generated or consumed from the exact contract release.
Internal integration mapping: `services/seo-planning/`, `apps/content-os/`, `packages/content-contracts/`
is a proposed placement only; adapt once to the actual repository without moving Knowledge IDs or files.

## Sequence with stop conditions

D0 Owner freezes this contract, SOW, synthetic benchmark, credentials policy and test IDs.
D1 Vendors deliver repository inventory, architecture map and a minimal runnable contract skeleton.
D2 Both independently build against the same fixtures/mock ports. Vendor 2 MUST NOT wait for live V16.
D3 Vendors run full own unit/integration/security/UI/regression tests plus the common contract suite and matrix.
D4 Each delivers exact commit, locked build artifact, SBOM/license inventory, logs, test IDs, benchmark
   baseline/candidate and independent sanitized real-provider probe where authorized.
D5 Internal team swaps mock ports for real adapters using only env/capability configuration and validates
   cross-vendor payloads. Contract failure is assigned to its owner; do not rewrite the other consumer to hide it.
D6 Eight assembly checks in `ASSEMBLY.md`; only then `INTEGRATED_CANARY_PASS`.
Production enabling is a distinct authorization, not part of these deliveries.

No performance or quality number may be fabricated. If optimization fails to improve the agreed metric,
return NO_IMPROVEMENT and retain the baseline. A functional baseline can still be accepted, but the contractually
requested optimization is not claimed accomplished. Freeze target metric and threshold at D0.

## Internal prerequisites retained by THBISON

- Close actual V16 blocking repair; do not export private history to vendors.
- Supply a contract-compatible evidence exporter preserving canonical claim IDs, source spans and status.
- Supply Notion artifact gateway with re-fetch/verified download, tenant isolation, rate-limit handling and outbox.
- Supply staging identity, role/capability tokens and destination IDs. Never use caller JSON as an approval authority.
- Identify actual CMS and staging route; WordPress may be the candidate adapter, not assumed verified.
- Map deployment/backup/rollback on VPS B after host-specific audit. Do not alter VPS A or thbison.vn storefront UI.
These are REAL remaining integration tasks. Shared mocks do not mean the internal platform already exists.

## Change control

Schema, semantic rule or endpoint change requires a change request and updated tests for BOTH producer and consumer.
Do not alter frozen V16 manifests. Only contract release owners may version this kit.
One bounded issue inventory then implementation; regroup related integration errors in one report rather than
one defect per new job. No self-created daily repair loops or version ladders.
