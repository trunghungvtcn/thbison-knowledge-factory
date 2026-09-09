# %% [markdown]
# # Knowledge Factory Pilot — 10 Extract and OCR
#
# Private Kaggle batch notebook. It validates every input hash, extracts digital text/tables,
# routes low-text PDF pages to OCR, checkpoints output, and never writes to Notion or production systems.

# %%
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import zipfile


def materialize_dataset(root: Path, archive_name: str, destination_name: str, marker: str) -> Path:
    """Use a Kaggle Dataset directly, or unpack its single upload archive in /kaggle/working."""
    if (root / marker).exists():
        return root
    for marker_path in Path("/kaggle/input").glob(f"**/{marker}"):
        if marker_path.exists():
            return marker_path.parent
    archive_path = root / archive_name
    if not archive_path.exists():
        return root
    destination = Path("/kaggle/working") / destination_name
    if not (destination / marker).exists():
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            destination_root = destination.resolve()
            for member in archive.infolist():
                member_path = (destination / member.filename).resolve()
                if destination_root not in member_path.parents and member_path != destination_root:
                    raise ValueError(f"Unsafe archive member: {member.filename}")
            archive.extractall(destination)
    return destination

CODE_ROOT = Path(os.environ.get("KF_CODE_ROOT", "/kaggle/input/kf-pilot-package"))
DATA_ROOT = Path(os.environ.get("KF_DATA_ROOT", "/kaggle/input/kf-pilot-input"))
OUTPUT_ROOT = Path(os.environ.get("KF_OUTPUT_ROOT", "/kaggle/working/kf-pilot-output"))
RESUME_ROOT_TEXT = os.environ.get("KF_RESUME_ROOT", "").strip()
RESUME_ROOT = Path(RESUME_ROOT_TEXT) if RESUME_ROOT_TEXT else None

CODE_ROOT = materialize_dataset(CODE_ROOT, "kf-pilot-package.zip", "kf-pilot-package", "src")
DATA_ROOT = materialize_dataset(DATA_ROOT, "kf-pilot-input.zip", "kf-pilot-input", "resource_manifest.csv")

if not (CODE_ROOT / "src").exists():
    CODE_ROOT = Path.cwd().resolve().parent if (Path.cwd().resolve().parent / "src").exists() else Path.cwd().resolve()
if not DATA_ROOT.exists() and (CODE_ROOT / "sample_input").exists():
    DATA_ROOT = CODE_ROOT / "sample_input"

if os.environ.get("KF_SKIP_INSTALL", "0") != "1":
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(CODE_ROOT / "requirements.txt")],
        check=True,
    )
sys.path.insert(0, str(CODE_ROOT / "src"))

try:
    display
except NameError:
    def display(value):
        print(value)

# %%
import pandas as pd

from kf_pilot.core import (
    append_jsonl,
    checksum_manifest,
    load_yaml,
    new_run_manifest,
    read_table,
    sha256_file,
    sha256_text,
    utc_now,
    validate_manifest,
    write_json,
    write_table,
    extract_resource,
)

CONFIG_PATH = CODE_ROOT / "config" / "pilot_config.yaml"
config = load_yaml(CONFIG_PATH)
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

manifest_candidates = [DATA_ROOT / "resource_manifest.parquet", DATA_ROOT / "resource_manifest.csv"]
manifest_path = next((path for path in manifest_candidates if path.exists()), None)
if manifest_path is None:
    raise FileNotFoundError("resource_manifest.parquet or resource_manifest.csv not found")

input_snapshot_hash = sha256_text(sha256_file(manifest_path) + sha256_file(CONFIG_PATH))
run_manifest_path = OUTPUT_ROOT / "run_manifest.json"
run_manifest = new_run_manifest("EXTRACT_AND_OCR", input_snapshot_hash, config)

# %% [markdown]
# ## Validate manifest and resume state

# %%
manifest = read_table(manifest_path).head(int(config["resource_limit"]))
validation = validate_manifest(
    manifest,
    DATA_ROOT / "files",
    max_file_bytes=int(config["max_file_bytes"]),
)
if validation.rejected:
    append_jsonl(OUTPUT_ROOT / "extraction" / "errors.jsonl", validation.rejected)

prior_evidence = pd.DataFrame()
prior_metrics = pd.DataFrame()
if RESUME_ROOT and RESUME_ROOT.exists():
    prior_manifest_path = RESUME_ROOT / "run_manifest.json"
    if prior_manifest_path.exists():
        prior_manifest = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
        if prior_manifest.get("input_snapshot_hash") != input_snapshot_hash:
            raise ValueError("Resume output belongs to a different input snapshot")
        run_manifest["run_id"] = prior_manifest["run_id"]
    prior_evidence_path = RESUME_ROOT / "extraction" / "evidence_units.parquet"
    prior_metrics_path = RESUME_ROOT / "metrics" / "resource_metrics.parquet"
    if prior_evidence_path.exists():
        prior_evidence = pd.read_parquet(prior_evidence_path)
    if prior_metrics_path.exists():
        prior_metrics = pd.read_parquet(prior_metrics_path)

completed_ids = set(prior_metrics.get("resource_id", pd.Series(dtype=str)).astype(str))
write_json(run_manifest_path, run_manifest)
print({
    "accepted_resources": len(validation.accepted),
    "rejected_resources": len(validation.rejected),
    "resumed_resources": len(completed_ids),
    "run_id": run_manifest["run_id"],
})

# %% [markdown]
# ## Extract, OCR and checkpoint

# %%
evidence_frames = [prior_evidence] if not prior_evidence.empty else []
metric_rows = prior_metrics.to_dict(orient="records") if not prior_metrics.empty else []
error_rows = []
extraction_error_count = 0
total_ocr_pages = int(prior_metrics.get("ocr_pages", pd.Series(dtype=int)).sum()) if not prior_metrics.empty else 0
checkpoint_every = 25

def checkpoint():
    evidence_frame = pd.concat(evidence_frames, ignore_index=True) if evidence_frames else pd.DataFrame()
    metrics_frame = pd.DataFrame(metric_rows)
    if not evidence_frame.empty:
        evidence_frame = evidence_frame.drop_duplicates(subset=["evidence_id"], keep="first")
        write_table(evidence_frame, OUTPUT_ROOT / "extraction" / "evidence_units.parquet")
    if not metrics_frame.empty:
        metrics_frame = metrics_frame.drop_duplicates(subset=["resource_id"], keep="last")
        write_table(metrics_frame, OUTPUT_ROOT / "metrics" / "resource_metrics.parquet")
    if error_rows:
        append_jsonl(OUTPUT_ROOT / "extraction" / "errors.jsonl", error_rows)
        error_rows.clear()

pending = [row for row in validation.accepted.to_dict(orient="records") if str(row["resource_id"]) not in completed_ids]
for index, resource in enumerate(pending, start=1):
    try:
        remaining_ocr = max(0, int(config["ocr_page_limit"]) - total_ocr_pages)
        per_resource_config = dict(config)
        per_resource_config["ocr_page_budget"] = remaining_ocr
        if remaining_ocr == 0:
            per_resource_config["enable_ocr"] = False
        rows, stats = extract_resource(resource, per_resource_config)
        evidence_frames.append(pd.DataFrame(rows))
        metric_rows.append(stats)
        total_ocr_pages += int(stats.get("ocr_pages", 0))
    except Exception as exc:
        extraction_error_count += 1
        error_rows.append({
            "resource_id": str(resource["resource_id"]),
            "stage": "EXTRACTION",
            "error_class": type(exc).__name__,
            "message": str(exc)[:1000],
            "created_at": utc_now(),
        })
    if index % checkpoint_every == 0:
        checkpoint()
        print(f"checkpoint: {index}/{len(pending)} resources")

checkpoint()

# %% [markdown]
# ## Finalize auditable outputs

# %%
evidence_path = OUTPUT_ROOT / "extraction" / "evidence_units.parquet"
metrics_path = OUTPUT_ROOT / "metrics" / "resource_metrics.parquet"
evidence = pd.read_parquet(evidence_path) if evidence_path.exists() else pd.DataFrame()
metrics = pd.read_parquet(metrics_path) if metrics_path.exists() else pd.DataFrame()

run_manifest.update({
    "finished_at": utc_now(),
    "status": "COMPLETED",
    "input_count": len(manifest),
    "accepted_resource_count": len(validation.accepted),
    "failed_resource_count": len(validation.rejected) + extraction_error_count,
    "evidence_count": len(evidence),
    "ocr_page_count": int(metrics.get("ocr_pages", pd.Series(dtype=int)).sum()) if not metrics.empty else 0,
})
write_json(run_manifest_path, run_manifest)

errors_path = OUTPUT_ROOT / "extraction" / "errors.jsonl"
artifact_paths = [path for path in [run_manifest_path, evidence_path, metrics_path, errors_path] if path.exists()]
checksum_lines = checksum_manifest(OUTPUT_ROOT, artifact_paths)
(OUTPUT_ROOT / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

print(json.dumps(run_manifest, indent=2))
display(metrics.head(20))
display(evidence.head(20))
