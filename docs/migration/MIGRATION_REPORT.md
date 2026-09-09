# Migration report

This repository is a sanitized preservation snapshot of the THBISON Knowledge Factory pilot for manual chain hoists, recovered from local V16.x deliveries and Kaggle resources on 2026-09-09.

## Preservation decisions

- The cumulative local source tree is the code baseline.
- Kaggle kernel source, metadata, output, and dataset archives were recovered without running or modifying a kernel.
- Notebook outputs, execution counts, and nonessential metadata were removed in the GitHub copy only.
- Dataset and model-class assets are excluded from Git and handled separately as Notion assets.
- No source on Kaggle was deleted or changed.
- No production deployment, scheduler, training, paid model call, or knowledge approval was performed.

## Current product state

V16.6 remains an evidence-completion/review implementation. Its own delivery report says evidence gaps remain and Phase F/production publication is not authorized. Preserving and testing the source does not change that product status.

The final remote verification result is stored outside the repository to avoid a self-referential commit hash.

## Offline test status

The preserved V16.6 dependency directory contains CPython 3.12 native extensions, while the available local interpreter is Python 3.14. Test collection therefore stops on incompatible NumPy/Pydantic native modules before executing tests. This is recorded as a baseline environment failure, not a migration regression. The previously delivered V16.6 reports and logs are provenance only and are not represented as tests rerun by this migration.
