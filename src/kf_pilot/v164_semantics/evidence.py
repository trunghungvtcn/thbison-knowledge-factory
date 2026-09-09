from __future__ import annotations

from pathlib import Path
from typing import Callable

from .canonical import confined_path, exact_keys, nonempty, require, sha256, unique_index

# Integration supplies the EXISTING V16.3 extractor, keyed by pinned identity.
# It returns exact text units keyed by a locator, e.g. "pdf_page:67".
Extractor = Callable[[bytes], dict[str, str]]


def utf8_units(raw: bytes) -> dict[str, str]:
    return {"text:0": raw.decode("utf-8", errors="strict")}


class SourceStore:
    def __init__(self, root: Path, manifest: list[dict], extractors: dict[str, Extractor]):
        self.sources = unique_index(manifest, "source_ref")
        self.texts: dict[str, dict[str, str]] = {}
        for ref, spec in sorted(self.sources.items()):
            exact_keys(spec, {"source_ref", "path", "raw_sha256", "extractor_id"})
            path = confined_path(root, spec["path"])
            raw = path.read_bytes()
            require(sha256(raw) == spec["raw_sha256"], "SOURCE_HASH_MISMATCH", ref)
            require(spec["extractor_id"] in extractors, "EXTRACTOR_NOT_CONNECTED", ref)
            # Never trust supplied extracted-text caches as proof of raw content.
            units = extractors[spec["extractor_id"]](raw)
            require(isinstance(units, dict) and bool(units), "INVALID_EXTRACTION", ref)
            require(all(nonempty(k) and isinstance(v, str) for k, v in units.items()),
                    "INVALID_EXTRACTION", ref)
            self.texts[ref] = units

    def verify(self, span: dict) -> str:
        exact_keys(span, {"source_ref", "raw_sha256", "extractor_id", "unit_id",
                          "start", "end", "quote"})
        ref = span["source_ref"]
        require(ref in self.sources, "SOURCE_NOT_PINNED", str(ref))
        spec = self.sources[ref]
        require(span["raw_sha256"] == spec["raw_sha256"], "SPAN_HASH_MISMATCH")
        require(span["extractor_id"] == spec["extractor_id"], "EXTRACTOR_ID_MISMATCH")
        require(span["unit_id"] in self.texts[ref], "LOCATOR_UNIT_MISMATCH")
        text = self.texts[ref][span["unit_id"]]
        start, end = span["start"], span["end"]
        require(type(start) is int and type(end) is int, "LOCATOR_OFFSETS_INVALID")
        require(0 <= start < end <= len(text), "LOCATOR_OFFSETS_INVALID")
        require(nonempty(span["quote"]) and text[start:end] == span["quote"],
                "EXACT_QUOTE_MISMATCH")
        return span["quote"]

    def inside(self, child: dict, parent: dict) -> None:
        self.verify(child)
        self.verify(parent)
        require(all(child[k] == parent[k] for k in
                    ("source_ref", "raw_sha256", "extractor_id", "unit_id")),
                "EVIDENCE_CONTEXT_MISMATCH")
        require(parent["start"] <= child["start"] < child["end"] <= parent["end"],
                "EVIDENCE_OUTSIDE_CONTEXT")

    def complete_token(self, span: dict, *, numeric: bool = False) -> None:
        self.verify(span)
        text = self.texts[span["source_ref"]][span["unit_id"]]
        before = text[span["start"] - 1] if span["start"] else ""
        after = text[span["end"]] if span["end"] < len(text) else ""
        left_punctuation, right_punctuation = (".,+-_", ".,%_") if numeric else ("_", "_")
        require(not (before and (before.isalnum() or before in left_punctuation)), "CLIPPED_LITERAL")
        require(not (after and (after.isalnum() or after in right_punctuation)), "CLIPPED_LITERAL")


