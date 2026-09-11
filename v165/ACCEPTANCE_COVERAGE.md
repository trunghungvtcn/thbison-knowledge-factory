# Acceptance matrix mapping

The source of the requirements is the unchanged handoff acceptance matrix.
All positive ACCEPT/activation examples in tests are explicitly TEST_ONLY and use
the same validator/projector as the repository path. No fixture is copied to real inputs.

| Matrix | Evidence |
|---|---|
| A01 | Raw hash, baseline pin and span tampering tests; upstream manifest checks |
| A02 | Captured before/after full-suite logs |
| A03–A07 | Legacy no-fallback, route, activation scope/time/issuer and data-class tests |
| A08–A18 | Completeness, unresolved AST, missing support, quantities, contexts, allowlist tests; real source audit |
| A19–A24 | Same-runtime atomic projection, binding drift, self/missing review, base drift, injected failure tests |
| A25–A28 | New blockers, full ledger accounting, human HOLD and unrelated-record tests |
| A29–A31 | Reverse-order result, byte-equal replay and rehashed-report tampering test |
| A32 | Real no-accept test; every original issue retains identity and lineage |
| A33–A34 | TEST_ONLY complete-bundle ACCEPT uses `core.project`, no alternate validator |
| A35 | Explicit parent/schema, missing mapping and collision tests |
| A36 | Network/SQL/process calls denied by exercised transport guards |

Semantic truth is not implied by automated tests. The overlap example and inherited
legal validity remain review questions. Clauses 10.2–10.4 are present in source
coverage and prevent treating inherited exception FALSE as a verified absence.
