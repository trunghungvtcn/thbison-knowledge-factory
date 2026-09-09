"""The only V16.6 module allowed to use the network."""
import mimetypes
import time
from pathlib import Path

from .canonical import bytes_for, load, require, sha256
from .schemas import iso_time, validate_research_plan

MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_ATTEMPTS = 2


def validate_public_url(url):
    """Fail closed for non-HTTPS and any DNS answer in a non-public range."""
    from kf_pilot.machine_admission.transport import resolve
    resolve(url, time.monotonic() + 30)
    return url


def fetch_public_https(url, timeout=30, budget=None):
    from kf_pilot.machine_admission.transport import fetch
    return fetch(url, timeout=timeout, budget=budget)


def _new_dir(path):
    path = Path(path)
    require(not path.exists(), "OUTPUT_ALREADY_EXISTS")
    path.mkdir(parents=True)
    return path


def discover(plan_path, output, accessed_at):
    plan = validate_research_plan(load(plan_path))
    iso_time(accessed_at)
    out = _new_dir(output)
    raw_dir = out / "raw"
    raw_dir.mkdir()
    log = []
    from kf_pilot.machine_admission.storage import Budget, Store
    budget = Budget(Store(out / 'checkpoint'))
    for index, source in enumerate(plan["sources"]):
        row = dict(source, accessed_at=accessed_at, status="ACCESS_BLOCKED", final_url=None,
                   http_status=None, mime_type=None, size=None, sha256=None, local_path=None, error=None)
        try:
            response, data = fetch_public_https(source["url"], budget=budget)
            suffix = Path(response.geturl()).suffix.lower() or mimetypes.guess_extension(response.headers.get_content_type()) or ".bin"
            name = f"{index:03d}-{source['source_id']}{suffix}"
            (raw_dir / name).write_bytes(data)
            row.update(status="FETCHED", accessed_at=response.fetched_at, final_url=response.geturl(), http_status=response.status,
                       mime_type=response.headers.get_content_type(), size=len(data), sha256=sha256(data),
                       local_path="raw/" + name)
        except Exception as exc:
            row["error"] = type(exc).__name__ + ":" + str(exc)[:300]
        log.append(row)
    (out / "discovery_log.jsonl").write_bytes(b"".join(bytes_for(row) + b"\n" for row in log))
    (out / "acquisition_manifest.json").write_bytes(bytes_for({"schema_version": 1, "accessed_at": accessed_at, "sources": log}) + b"\n")
    return {"fetched": sum(r["status"] == "FETCHED" for r in log), "blocked": sum(r["status"] != "FETCHED" for r in log)}


def freeze(acquisition_dir, as_of, output):
    iso_time(as_of)
    source = Path(acquisition_dir).resolve()
    manifest = load(source / "acquisition_manifest.json")
    out = _new_dir(output)
    corpus = out / "corpus"
    corpus.mkdir()
    frozen = []
    for row in manifest["sources"]:
        item = dict(row)
        if row["status"] == "FETCHED":
            src = source / row["local_path"]
            require(src.is_file() and sha256(src.read_bytes()) == row["sha256"], "ACQUISITION_HASH_MISMATCH")
            dest = corpus / src.name
            dest.write_bytes(src.read_bytes())
            item["local_path"] = "corpus/" + dest.name
        frozen.append(item)
    frozen_manifest = {"schema_version": 1, "as_of": as_of, "sources": frozen}
    frozen_manifest["corpus_revision"] = sha256(bytes_for(frozen_manifest))
    (out / "frozen_corpus_manifest.json").write_bytes(bytes_for(frozen_manifest) + b"\n")
    (out / "discovery_log.jsonl").write_bytes((source / "discovery_log.jsonl").read_bytes())
    return {"corpus_revision": frozen_manifest["corpus_revision"], "fetched": sum(r["status"] == "FETCHED" for r in frozen)}
