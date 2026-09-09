# THBISON Knowledge Factory — Manual Chain Hoist Pilot

Sanitized preservation snapshot of the executable Kaggle/Notion pilot, including the cumulative implementation through V16.6. The source was recovered from the local delivery tree and verified against the available Kaggle kernels, datasets, metadata, and saved outputs on 2026-09-09.

GitHub is the source-of-truth for code. Corpus files, datasets, generated outputs, and model-class assets are deliberately kept outside Git and tracked in the migration asset manifest. See `docs/migration/SOURCE_MAP.md` for provenance and limitations.

## Architecture

```text
Private input files + manifest
        ↓
10_extract_and_ocr.ipynb
        ↓
Parquet evidence + checksums
        ↓
20_claims_score_notion.ipynb
        ↓
Parquet/DuckDB truth + optional Notion review queue
        ↓
Versioned review decisions + approved_claims.parquet
```

Notion is the data and knowledge asset layer. It does not replace source control, and candidate knowledge is never auto-approved.

## Included files

- `notebooks/10_extract_and_ocr.ipynb`: hash validation, PDF/HTML/CSV extraction, table extraction, selective EasyOCR and checkpoints.
- `notebooks/20_claims_score_notion.ipynb`: template-first claims, optional DeepSeek, hard gates, DuckDB snapshot and two-way Notion review.
- `src/kf_pilot/`: testable pipeline modules used by both notebooks.
- `config/`: pilot config, claim schemas, exact entity aliases and unit registry.
- `notion/NOTION_SETUP.md`: exact temporary review data-source schema.
- `tests/`: local smoke and safety tests.
- `docs/recovery/`: compact V16.x recovery notes and entrypoints; large run artifacts are excluded.

## Security

- Rotate any API key previously exposed in chat, code or notebook before use.
- Add new keys only as Kaggle Secrets.
- Keep both Kaggle datasets and notebooks private.
- The sample URL uses `.invalid` deliberately and is never fetched.
- Notebook 10 reads only pre-staged files; it is not a crawler.
- DeepSeek and Notion are disabled by default.

## Fast path

1. Create an isolated Python environment and install `requirements.txt`.
2. Run the offline test suite below before configuring any external service.
3. Follow `KAGGLE_START.md` only when a controlled private Kaggle run is explicitly authorized.

## Important defaults

- 100 resources maximum.
- 300 OCR pages maximum.
- 500 candidate claims maximum.
- 200 Notion review rows maximum.
- No automatic publication.
- All critical numeric candidates require review.

## Local tests

```powershell
$env:PYTHONPATH='src'
python -m pytest -q
```

The full notebook requires packages in `requirements.txt`; the lightweight tests use the dependencies already common in Jupyter/Kaggle environments.
