from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml


MANIFEST_REQUIRED = {
    "resource_id",
    "publisher_id",
    "publisher_name",
    "file_path",
    "content_sha256",
    "license_state",
    "source_role",
    "authority_tier",
    "jurisdiction",
    "applicability_scope",
    "claim_families",
    "legal_status",
}
ALLOWED_LICENSE_STATES = {
    "ALLOWED_INTERNAL",
    "ALLOWED_EXPORT",
    "UNKNOWN",
    "BLOCKED",
}
MAX_FILE_BYTES_DEFAULT = 50 * 1024 * 1024
MAX_PDF_PAGES_DEFAULT = 300


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping in {path}")
    return value


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path, keep_default_na=False)
    if suffix in {".jsonl", ".ndjson"}:
        return pd.read_json(path, lines=True)
    raise ValueError(f"Unsupported table format: {path}")


def write_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"Unsupported output table: {path}")


def safe_resolve(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Path traversal blocked: {relative_path}")
    return candidate


def sniff_mime(path: Path) -> str:
    with path.open("rb") as handle:
        head = handle.read(16)
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"PAR1"):
        return "application/vnd.apache.parquet"
    if head.startswith(b"PK\x03\x04"):
        return "application/zip"
    if head.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        return "text/html"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


@dataclass
class ManifestValidation:
    accepted: pd.DataFrame
    rejected: list[dict[str, Any]]


def validate_manifest(
    manifest: pd.DataFrame,
    files_root: Path,
    max_file_bytes: int = MAX_FILE_BYTES_DEFAULT,
) -> ManifestValidation:
    missing = MANIFEST_REQUIRED - set(manifest.columns)
    if missing:
        raise ValueError(f"Manifest missing fields: {sorted(missing)}")
    if manifest["resource_id"].astype(str).duplicated().any():
        raise ValueError("Manifest resource_id must be unique")

    accepted_rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in manifest.to_dict(orient="records"):
        row = {str(k): v for k, v in raw.items()}
        resource_id = str(row.get("resource_id", ""))
        try:
            if row["license_state"] not in ALLOWED_LICENSE_STATES:
                raise ValueError("invalid license_state")
            if row["license_state"] == "BLOCKED":
                raise ValueError("license blocked")
            path = safe_resolve(files_root, str(row["file_path"]))
            if not path.is_file():
                raise ValueError("file missing")
            size = path.stat().st_size
            if size > max_file_bytes:
                raise ValueError(f"file exceeds {max_file_bytes} bytes")
            actual_hash = sha256_file(path)
            expected_hash = str(row["content_sha256"]).lower()
            if actual_hash != expected_hash:
                raise ValueError("content_sha256 mismatch")
            row["resolved_path"] = str(path)
            row["byte_size"] = size
            row["mime_type_sniffed"] = sniff_mime(path)
            row["resource_version_hash"] = actual_hash
            accepted_rows.append(row)
        except Exception as exc:
            rejected.append(
                {
                    "resource_id": resource_id,
                    "stage": "MANIFEST_VALIDATION",
                    "error_class": type(exc).__name__,
                    "message": str(exc),
                }
            )
    return ManifestValidation(pd.DataFrame(accepted_rows), rejected)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._blocked = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self._blocked += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"} and self._blocked:
            self._blocked -= 1

    def handle_data(self, data: str) -> None:
        if not self._blocked and data.strip():
            self.parts.append(data.strip())


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def make_evidence_id(resource_hash: str, address: dict[str, Any], raw_text: str) -> str:
    return sha256_text(resource_hash + canonical_json(address) + raw_text)


def evidence_row(
    resource: dict[str, Any],
    evidence_type: str,
    raw_text: str,
    address: dict[str, Any],
    extraction_method: str,
    extraction_confidence: float,
    mapping_confidence: float | None = None,
    raw_value: Any = None,
) -> dict[str, Any]:
    normalized = normalize_space(raw_text)
    row = {
        "evidence_id": make_evidence_id(resource["resource_version_hash"], address, normalized),
        "resource_id": str(resource["resource_id"]),
        "resource_version_hash": resource["resource_version_hash"],
        "publisher_id": str(resource.get("publisher_id", "")),
        "publisher_name": str(resource.get("publisher_name", "")),
        "original_url": str(resource.get("original_url", "")),
        "source_role": str(resource.get("source_role", "")),
        "authority_tier": str(resource.get("authority_tier", "")),
        "jurisdiction": str(resource.get("jurisdiction", "")),
        "applicability_scope": str(resource.get("applicability_scope", "")),
        "claim_families": str(resource.get("claim_families", "")),
        "legal_status": str(resource.get("legal_status", "")),
        "evidence_type": evidence_type,
        "page_no": address.get("page_no"),
        "block_id": address.get("block_id"),
        "table_id": address.get("table_id"),
        "row_key": address.get("row_key"),
        "column_key": address.get("column_key"),
        "bbox_json": canonical_json(address.get("bbox")) if address.get("bbox") else None,
        "raw_text": normalized,
        "raw_value_json": canonical_json(raw_value) if raw_value is not None else None,
        "extraction_method": extraction_method,
        "extraction_confidence": float(max(0.0, min(1.0, extraction_confidence))),
        "mapping_confidence": None if mapping_confidence is None else float(max(0.0, min(1.0, mapping_confidence))),
        "worker_digest": "kf-pilot-core-0.2.0",
        "created_at": utc_now(),
    }
    row["evidence_hash"] = sha256_text(canonical_json(row))
    return row


def extract_html(resource: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    parser = VisibleTextParser()
    parser.feed(text)
    rows = []
    for index, part in enumerate(parser.parts):
        clean = normalize_space(part)
        if len(clean) < 2:
            continue
        rows.append(
            evidence_row(
                resource,
                "HTML_BLOCK",
                clean,
                {"block_id": f"html-{index}"},
                "html.parser",
                0.99,
            )
        )
    return rows


def extract_csv(resource: dict[str, Any], path: Path, max_rows: int = 10000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_index, item in enumerate(reader):
            if row_index >= max_rows:
                break
            for column, value in item.items():
                clean = normalize_space(str(value or ""))
                if not clean:
                    continue
                rows.append(
                    evidence_row(
                        resource,
                        "CSV_CELL",
                        clean,
                        {"row_key": str(row_index + 2), "column_key": str(column)},
                        "csv.DictReader",
                        1.0,
                        1.0,
                        raw_value=value,
                    )
                )
    return rows


def _easyocr_reader(languages: list[str], gpu: bool) -> Any:
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError("easyocr is unavailable; install requirements or disable OCR") from exc
    return easyocr.Reader(languages, gpu=gpu, verbose=False)


def extract_pdf(
    resource: dict[str, Any],
    path: Path,
    config: dict[str, Any],
    ocr_reader: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    import fitz

    max_pages = int(config.get("max_pdf_pages", MAX_PDF_PAGES_DEFAULT))
    min_text_chars = int(config.get("digital_text_min_chars", 40))
    enable_tables = bool(config.get("extract_tables", True))
    enable_ocr = bool(config.get("enable_ocr", True))
    render_dpi = int(config.get("ocr_dpi", 180))
    ocr_page_budget = int(config.get("ocr_page_budget", config.get("ocr_page_limit", 300)))
    language_codes = list(config.get("ocr_languages", ["en"]))
    gpu = bool(config.get("ocr_gpu", False))
    document = fitz.open(path)
    if document.page_count > max_pages:
        document.close()
        raise ValueError(f"PDF has {document.page_count} pages; max is {max_pages}")
    page_scope = str(resource.get("page_scope", "ALL")).strip().upper()
    selected_pages: set[int] | None = None
    if page_scope and page_scope != "ALL":
        selected_pages = set()
        for part in page_scope.split("|"):
            bounds = part.strip().split("-", 1)
            start = int(bounds[0])
            end = int(bounds[1]) if len(bounds) == 2 else start
            if start < 1 or end < start or end > document.page_count:
                raise ValueError(f"Invalid page_scope {page_scope} for {document.page_count} pages")
            selected_pages.update(range(start, end + 1))

    evidence: list[dict[str, Any]] = []
    stats = {"pages": 0, "digital_pages": 0, "ocr_pages": 0, "ocr_unavailable_pages": 0}

    if enable_tables:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                for page_no, page in enumerate(pdf.pages, start=1):
                    if selected_pages is not None and page_no not in selected_pages:
                        continue
                    for table_index, table in enumerate(page.extract_tables() or []):
                        for row_index, row in enumerate(table or []):
                            for column_index, value in enumerate(row or []):
                                clean = normalize_space(str(value or ""))
                                if clean:
                                    evidence.append(
                                        evidence_row(
                                            resource,
                                            "PDF_TABLE_CELL",
                                            clean,
                                            {
                                                "page_no": page_no,
                                                "table_id": f"T{table_index + 1}",
                                                "row_key": str(row_index),
                                                "column_key": str(column_index),
                                            },
                                            "pdfplumber",
                                            0.97,
                                            0.90,
                                            raw_value=value,
                                        )
                                    )
        except Exception:
            pass

    for page_index in range(document.page_count):
        if selected_pages is not None and page_index + 1 not in selected_pages:
            continue
        stats["pages"] += 1
        page = document.load_page(page_index)
        blocks = page.get_text("blocks") or []
        page_text = normalize_space(" ".join(str(block[4]) for block in blocks if len(block) >= 5))
        if len(page_text) >= min_text_chars:
            stats["digital_pages"] += 1
            for block_index, block in enumerate(blocks):
                if len(block) < 5:
                    continue
                clean = normalize_space(str(block[4]))
                if not clean:
                    continue
                evidence.append(
                    evidence_row(
                        resource,
                        "PDF_TEXT_BLOCK",
                        clean,
                        {
                            "page_no": page_index + 1,
                            "block_id": f"b{block_index}",
                            "bbox": [float(x) for x in block[:4]],
                        },
                        "pymupdf-text",
                        0.99,
                    )
                )
            continue

        if not enable_ocr or stats["ocr_pages"] >= ocr_page_budget:
            stats["ocr_unavailable_pages"] += 1
            continue
        if ocr_reader is None:
            try:
                ocr_reader = _easyocr_reader(language_codes, gpu)
            except RuntimeError:
                stats["ocr_unavailable_pages"] += 1
                continue
        pixmap = page.get_pixmap(dpi=render_dpi, alpha=False)
        import numpy as np
        image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
        results = ocr_reader.readtext(image, detail=1, paragraph=False)
        stats["ocr_pages"] += 1
        for block_index, result in enumerate(results):
            bbox, text, confidence = result
            clean = normalize_space(str(text))
            if not clean:
                continue
            evidence.append(
                evidence_row(
                    resource,
                    "PDF_OCR_BLOCK",
                    clean,
                    {
                        "page_no": page_index + 1,
                        "block_id": f"ocr-{block_index}",
                        "bbox": bbox,
                    },
                    "easyocr",
                    float(confidence),
                )
            )
    document.close()
    return evidence, stats


def extract_resource(
    resource: dict[str, Any],
    config: dict[str, Any],
    ocr_reader: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = Path(resource["resolved_path"])
    mime = resource["mime_type_sniffed"]
    started = time.monotonic()
    if mime == "application/pdf":
        rows, stats = extract_pdf(resource, path, config, ocr_reader)
    elif mime == "text/html":
        rows, stats = extract_html(resource, path), {"pages": 0, "digital_pages": 0, "ocr_pages": 0}
    elif path.suffix.lower() == ".csv":
        rows, stats = extract_csv(resource, path), {"pages": 0, "digital_pages": 0, "ocr_pages": 0}
    else:
        raise ValueError(f"Unsupported pilot MIME: {mime}")
    stats.update(
        {
            "resource_id": str(resource["resource_id"]),
            "evidence_count": len(rows),
            "elapsed_seconds": round(time.monotonic() - started, 4),
        }
    )
    return rows, stats


def new_run_manifest(stage: str, input_snapshot_hash: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": str(uuid.uuid4()),
        "stage": stage,
        "schema_version": str(config.get("schema_version", "2.0.0")),
        "worker_digest": "kf-pilot-core-0.2.0",
        "input_snapshot_hash": input_snapshot_hash,
        "config_hash": sha256_text(canonical_json(config)),
        "started_at": utc_now(),
        "finished_at": None,
        "status": "RUNNING",
    }


def checksum_manifest(root: Path, paths: Iterable[Path]) -> list[str]:
    lines = []
    root = root.resolve()
    for path in sorted(paths, key=lambda value: str(value)):
        resolved = path.resolve()
        lines.append(f"{sha256_file(resolved)}  {resolved.relative_to(root)}")
    return lines
