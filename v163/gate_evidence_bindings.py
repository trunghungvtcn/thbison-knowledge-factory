"""Repository-aware independent artifact gate. Re-extract source bytes; no writes."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from kf_pilot.v163_evidence.sources import source_catalog,verify_span
from kf_pilot.legacy_manifest import LegacyManifestPathError,resolve_manifest_entries
from kf_pilot.v163_evidence.binding import review_work,proposals,adjudicate
from kf_pilot.v162_remediation.core import require,gate_readiness,digest,BASELINE

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]

def main(output,trusted_reviewers=None):
    v162=runpy.run_path(str(ROOT/'v162/run_remediation.py'))
    v162['verify_assets']()
    for n,h in load(output/'artifact_hashes.json').items():
        require(hashlib.sha256((output/n).read_bytes()).hexdigest()==h,'artifact hash mismatch')
    source_manifest=load(output/'v163_input_manifest.json')
    try:
        source_paths=resolve_manifest_entries(ROOT,source_manifest,dialect='windows-relative-v1')
    except LegacyManifestPathError as exc:
        require(False,'input/code path unsafe:'+str(exc))
    for n,h in source_manifest.items():
        require(hashlib.sha256(source_paths[n].read_bytes()).hexdigest()==h,'input/code hash changed')
    old=ROOT/'v162/artifacts/remediation-final';base=ROOT/'v162/baseline-reproduced'
    require(digest(load(base/'notion_typed_update_plan.json'))==BASELINE,'baseline changed')
    catalog=source_catalog(ROOT)
    reviews=v162['parse_live'](load(ROOT/'v163/inputs/live_reviews_raw.json'))
    work,spans=review_work(load(old/'v162_issue_ledger.json'),load(old/'v162_unresolved_review_queue.json'),rows(base/'claim_versions.jsonl'),reviews,catalog)
    require(rows(output/'v163_review_pack.jsonl')==work,'review pack accounting mismatch')
    require(load(output/'v163_source_span_index.json')=={'sources':catalog,'spans':spans},'source index mismatch')
    for span in spans.values():verify_span(span,catalog)
    candidates=proposals(work,spans)
    require(rows(output/'v163_binding_candidates.jsonl')==candidates,'proposal mismatch')
    decisions=rows(output/'v163_adjudications.jsonl')
    trusted=load(trusted_reviewers) if trusted_reviewers else []
    if decisions:
        require(trusted_reviewers is not None,'explicit reviewer registry required')
        key=str(trusted_reviewers.resolve().relative_to(ROOT))
        require(load(output/'v163_input_manifest.json').get(key)==hashlib.sha256(trusted_reviewers.read_bytes()).hexdigest(),'reviewer registry mismatch')
    accepted,rejected,evidence=adjudicate(candidates,decisions,work,catalog,trusted)
    require(rows(output/'v163_accepted_bindings.jsonl')==accepted,'unapproved acceptance')
    require(rows(output/'v163_rejected_bindings.jsonl')==rejected,'rejected binding mismatch')
    require(load(output/'v163_v162_evidence_input.json')==evidence,'evidence adapter mismatch')
    report=load(output/'v163_readiness_report.json');canary=load(output/'v163_phase_f_canary_plan.json')
    gate_readiness(report,canary,load(output/'v162_canonical_plan.json')['records'])
    require(canary==load(output/'v162_phase_f_canary_plan.json'),'V162 canary bypass')
    print(f'V163_SOURCE_BINDING_ACCOUNTING_GATE_PASS issues={len(work)} candidates={len(candidates)} accepted={len(accepted)}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--trusted-reviewers',type=Path)
    a=p.parse_args();main(a.output,a.trusted_reviewers)
