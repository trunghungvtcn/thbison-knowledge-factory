"""Offline evidence binding driver. Saved read-only reviews; no credentials or transport."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from kf_pilot.v162_remediation.core import BASELINE,canonical,compute,digest,require
from kf_pilot.v163_evidence.sources import source_catalog
from kf_pilot.v163_evidence.binding import review_work,proposals,adjudicate


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def jsonl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]


def run(output,adjudications=None,reviewers=None):
    require(not output.exists(),'new output required')
    v162=runpy.run_path(str(ROOT/'v162/run_remediation.py'))
    v162['verify_assets']()
    old=ROOT/'v162/artifacts/remediation-final'
    for name,h in load(old/'artifact_hashes.json').items():
        require(hashlib.sha256((old/name).read_bytes()).hexdigest()==h,'V162 artifact changed')
    pack=ROOT/'vendor/v163-deployment-pack'
    for line in (pack/'PACKAGE_SHA256SUMS.txt').read_text().splitlines():
        h,name=line.split(maxsplit=1)
        require(hashlib.sha256((pack/name.strip()).read_bytes()).hexdigest()==h,'V163 package changed')
    base=ROOT/'v162/baseline-reproduced';plan=load(base/'notion_typed_update_plan.json')
    require(digest(plan)==BASELINE,'V161 baseline changed')
    versions=jsonl(base/'claim_versions.jsonl');source_issues=jsonl(base/'migration_issues.jsonl')
    ledger=load(old/'v162_issue_ledger.json');queue=load(old/'v162_unresolved_review_queue.json')
    reviews=v162['parse_live'](load(ROOT/'v163/inputs/live_reviews_raw.json'))
    require(set(reviews)=={r['page_id'] for r in plan['operations']},'fresh review coverage differs')
    schema_data=json.loads(load(ROOT/'v163/inputs/schema_raw.json')['content'][0]['text'])['text']
    state=json.loads(re.search(r'<data-source-state>\s*(.*?)\s*</data-source-state>',schema_data,re.S).group(1))
    schema={k:'rich_text' if p['type']=='text' else p['type'] for k,p in state['schema'].items()}
    catalog=source_catalog(ROOT)
    work,spans=review_work(ledger,queue,versions,reviews,catalog)
    candidates=proposals(work,spans)
    decisions=jsonl(adjudications) if adjudications else []
    trusted=load(reviewers) if reviewers else []
    accepted,rejected,evidence=adjudicate(candidates,decisions,work,catalog,trusted)
    result=compute(versions,source_issues,plan['operations'],reviews,schema,evidence)
    rerun=result['v162_issue_ledger.json']['issues']
    require({r['issue_id'] for r in rerun}=={r['issue_id'] for r in ledger['issues']},'reconciliation lost issues')
    accepted_ids={r['issue_id'] for r in accepted}
    unresolved=[dict(w,status='SOURCE_UNAVAILABLE' if w['source_status']=='SOURCE_UNAVAILABLE' else
                    ('AWAITING_HUMAN_ADJUDICATION' if any(c['issue_id']==w['issue_id'] for c in candidates) else 'NEEDS_MORE_EVIDENCE'))
                for w in work if w['issue_id'] not in accepted_ids]
    report=dict(result['v162_readiness_report.json'])
    report.update(authoritative_issue_count=len(work),source_available_count=sum(w['source_status']=='SOURCE_AVAILABLE' for w in work),
        source_unavailable_count=sum(w['source_status']=='SOURCE_UNAVAILABLE' for w in work),
        exact_span_issue_count=sum(bool(w['span_ids']) for w in work),binding_candidate_count=len(candidates),
        reviewer_counts={d:sum(a['decision']==d for a in decisions) for d in ('ACCEPT','REJECT','HOLD','NEEDS_MORE_EVIDENCE')},
        adjudication_pending_count=len(work)-len(decisions),accepted_binding_count=len(accepted),
        fresh_review_count=len(reviews),final_status='V163_CANARY_READY / PHASE_F_NOT_AUTHORIZED' if result['v162_phase_f_canary_plan.json']['records'] else 'V163_BINDING_PIPELINE_PASS / PHASE_F_NOT_AUTHORIZED')
    reconcile={'input_issue_ids':sorted(w['issue_id'] for w in work),'output_issue_ids':sorted(r['issue_id'] for r in rerun),
        'accepted_issue_ids':sorted(accepted_ids),'post_v162_resolution_counts':report['resolution_counts']}
    require(digest(load(base/'notion_typed_update_plan.json'))==BASELINE,'baseline changed after')
    v162['verify_assets']()
    out={'v163_review_pack.jsonl':work,'v163_source_span_index.json':{'sources':catalog,'spans':spans},
        'v163_binding_candidates.jsonl':candidates,'v163_adjudications.jsonl':decisions,
        'v163_accepted_bindings.jsonl':accepted,'v163_rejected_bindings.jsonl':rejected,
        'v163_unresolved_queue.jsonl':unresolved,'v163_resolution_reconciliation.json':reconcile,
        'v163_readiness_report.json':report,'v163_phase_f_canary_plan.json':result['v162_phase_f_canary_plan.json'],
        'v163_v162_evidence_input.json':evidence}
    out.update(result)
    paths=list((ROOT/'v163/inputs').glob('*.json'))+list((ROOT/'src/kf_pilot/v163_evidence').glob('*.py'))+[Path(__file__),old/'artifact_hashes.json']
    if adjudications:paths.append(adjudications)
    if reviewers:paths.append(reviewers)
    out['v163_input_manifest.json']={str(p.resolve().relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    output.mkdir(parents=True)
    for name,data in out.items():
        text=''.join(canonical(r)+'\n' for r in data) if name.endswith('.jsonl') else canonical(data)+'\n'
        with (output/name).open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob('*'))}
    with (output/'artifact_hashes.json').open('x',encoding='utf-8',newline='\n') as f:f.write(canonical(hashes)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--adjudications',type=Path);p.add_argument('--trusted-reviewers',type=Path)
    a=p.parse_args();run(a.output,a.adjudications,a.trusted_reviewers)
