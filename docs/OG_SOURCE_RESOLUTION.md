# OG source investigation

Status: USER_AUTHORIZED_REPLACEMENT_SNAPSHOT. Not G1_REMEDIATED; tests delegated to Grok.

On 2026-09-11 the project owner explicitly approved these located source files and instructed Codex to put the fix on GitHub and send the package to Grok. This is recorded authorization to use this replacement snapshot for THBISON V1/V2 source and audit handoff. It is not an upstream license claim, proof of original authorship, or evidence that the two earlier vendor ZIPs contained identical bytes. The prior original-export gate is explicitly superseded for this selected snapshot by the owner's acceptance; all compatibility tests remain required. No open-source license is invented.

Eight original files are copied unchanged into each module, with 16/16 SHA256 comparisons matching the ZIP entries. AGENTS.project.md clarifies audit-only scope without editing the archived AGENTS.md. External author/license metadata remains unverified and must be described that way in receipts.

Bounded local archive inspection on 2026-09-11 found .grok/skills/og (7 files) and AGENTS.md in `sa644cLfyIxEcCqz-grok-workspace.zip` in the user's Downloads directory. Archive SHA256: c29aa0b50bcf3cc4ea3eac33e8158e0933b58f350588c0d5019da7889d654d6c.

This differs from both pinned original inputs: V1 59myUKePj4CqLjQO-grok-workspace.zip (f75df682bcfc79937ea570b656b760f43cc3638049fd8ef92f53b44243b7b493), V2 rMV0WKtcBenVD2mM-grok-workspace.zip (2feea5b65c89a90af37cb59c1ae00d46b2e651ef1d634a385ad33d78a8ce9013). Therefore it cannot be silently substituted for those snapshots.

| Entry | Bytes | SHA256 |
|---|---:|---|
| .grok/skills/og/SKILL.md | 6555 | 5c6ff71e42840f38db61fb5173836485de4a53418c99d1f34d77ecefaed46d28 |
| .grok/skills/og/references/brand-pass.md | 2568 | 68019a3afe8ae75b94599de354245c9a0d068cae5ff054841ac75cc055058afe |
| .grok/skills/og/references/custom-card.md | 5988 | 97c0efccce4daf47486f8caa65723db2fd0435ccaa68be90004a6c1ad15cb954 |
| .grok/skills/og/references/favicon-and-icons.md | 1959 | bc95ed577825a411571f4680f992799a26811dd72af6714375dc49800e216db6 |
| .grok/skills/og/references/og-type-contract.md | 1749 | 2743a8a9a6c1eafb8aec5ae8c83f2202533df6a55649582684d2bce18a52ea2f |
| .grok/skills/og/references/placeholder-card.md | 887 | c21551f098562c8ff49004885596f71848c09af13b19237f1babe820e4f7e957 |
| .grok/skills/og/references/x-banner.md | 2339 | 0f6f5b8c381c40e26514439575a004ef0560b379fd069b76fc940c9f803e0733 |
| AGENTS.md | 18904 | 09f7b09f35660596cc4c22612a7893b0dea41e28c187168076b9c59302d0f610 |

No OG-specific license file was listed in this archive; package.json has no license or repository field. Licenses for other skills do not establish OG licensing. The master archive THBISON-CODEX-VPS-B-MASTER.zip (28aab4ee4c5448d57ffa84ce2021e01b05fe17e176dd26055be232e15fe3a8ba) does not contain the OG skill tree.

At the initial investigation no files were copied. Following the explicit owner authorization above, only the eight listed text files were copied into each module. No template setup or asset-generation instructions were executed. The Notion project, handoff and custody pages do not independently bind this ZIP to an upstream snapshot. These hashes establish observed content identity, not authorship or original-version equivalence.

Origin supplied by owner: local Grok workspace export, archive name/hash above. A public original-export URL is unavailable. The immutable Git commit containing this document and files is the new project snapshot; cite that full SHA in the handoff. Grok must verify all file hashes and run the original OG tests without changes. No test PASS is inferred from the owner's approval.
