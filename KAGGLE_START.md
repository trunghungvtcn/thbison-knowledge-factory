# Kaggle start checklist

## A. Create private datasets

Create two private Kaggle Datasets:

1. `kf-pilot-package`: upload this package without real source files.
2. `kf-pilot-input`: upload `resource_manifest.parquet` or `.csv` plus the `files/` directory.

For the first smoke run, `sample_input/` can be used as `kf-pilot-input`.

## B. Run extraction notebook

1. Create a private Kaggle Notebook from `notebooks/10_extract_and_ocr.ipynb`.
2. Attach `kf-pilot-package` and `kf-pilot-input`.
3. Set environment paths if Kaggle slugs differ:

```python
import os
os.environ["KF_CODE_ROOT"] = "/kaggle/input/kf-pilot-package"
os.environ["KF_DATA_ROOT"] = "/kaggle/input/kf-pilot-input"
```

4. Enable GPU only when OCR pages exist. Digital-only smoke tests can use CPU.
5. Run all cells.
6. Confirm `run_manifest.status == COMPLETED`, inspect errors, then save output as private Dataset `kf-pilot-extraction-output`.

## C. Run claims/review notebook

1. Create a private Kaggle Notebook from `notebooks/20_claims_score_notion.ipynb`.
2. Attach `kf-pilot-package` and `kf-pilot-extraction-output`.
3. Run with both `deepseek.enabled: false` and `notion.enabled: false` first.
4. Confirm the sample creates three `REVIEW_REQUIRED` candidates.

## D. Enable DeepSeek

1. Revoke any key previously exposed in chat/notebooks.
2. Add a new Kaggle Secret named `YESCALE_API_KEY`.
3. Set `deepseek.enabled: true` in `config/pilot_config.yaml`.
4. Keep `max_calls: 30` for the first API run.
5. Enable notebook internet only for this stage.

Successful responses are cached by request hash. Re-running the same request uses cached output.

## E. Enable Notion review

1. Build the three v2 data sources described in `notion/NOTION_SETUP.md`.
2. Connect the Notion integration to all three databases.
3. Add Kaggle Secret `NOTION_API_KEY`; data-source IDs are already in private config and can be overridden with the three optional ID secrets.
4. Set `notion.enabled: true`.
5. Run the synchronization cell; review pages in Notion.
6. Change `Decision` to APPROVED, REJECTED or HOLD.
7. Set `KF_PULL_NOTION_DECISIONS=1` and rerun the decision cell.

Only pulled `APPROVED` decisions enter `approved_claims.parquet`.

## F. Stop conditions

Stop the run if:

- input hash mismatch;
- any secret appears in output/log;
- unsupported quote/value reaches review as valid;
- OCR budget exceeds 300 pages;
- review queue exceeds 200 rows;
- Notion schema validation fails;
- Kaggle output cannot be reconciled with `checksums.sha256`.
