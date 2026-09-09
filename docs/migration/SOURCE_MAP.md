# Source map

Job: `MCH-MIGRATE-KAGGLE-GITHUB-001`

## Baseline selected

The preserved source baseline is the local `kaggle-pilot-jupyter` delivery tree containing the cumulative implementation through V16.6. It includes the actual Python package, notebook launchers, configuration, tests, and staging utilities.

The V16.6 completion archive is not a complete standalone application. Its file list contains one implementation module, one test, and completion evidence. Those files match the corresponding paths in the cumulative local tree and are retained as provenance, not copied over the tree as a replacement.

## Kaggle inventory snapshot

Account observed: `nguyeble`.

- Kernels: 6 inventoried; source and metadata recovered for all 6.
- Kernel outputs: available outputs recovered for 3 project kernels; 3 older generic notebooks reported no stored output through the current API.
- Datasets: 3 inventoried and recovered with metadata and original archives.
- Pagination: inventory requested with page size 200; returned counts were below the page limit.

The exact originals, outputs, archives, and checksums remain outside this Git repository under the migration workspace.

## Local references

Verified local references include the cumulative V16.6 tree, `V166-completion-delivery.zip`, the V16.6 original handoff archive, `V16.5-code-tests-report.zip`, and the autonomous local delivery. A filename or later timestamp was not used alone to select the baseline.

## Exclusions

Corpus documents, PDF/HTML sources, Parquet/DuckDB outputs, generated run artifacts, dependency directories, caches, logs, credentials, and private audit material are deliberately excluded from GitHub. They belong to the Notion data asset layer or local quarantine.

No Git history was present in the recovered project directory, so this migration preserves an attributed snapshot and does not fabricate earlier commits.

