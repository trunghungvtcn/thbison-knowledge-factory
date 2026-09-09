"""Recompute the real no-accept path from immutable upstream and raw sources."""
from copy import deepcopy
import json
from pathlib import Path
import re
import runpy
import socket
import sqlite3
import subprocess
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from kf_pilot.v162_remediation.core import BASELINE, compute, inventory
from kf_pilot.v163_evidence.sources import source_catalog, verify_span
from kf_pilot.v164_semantics.canonical import digest, sha256, require
from .core import build_proposal, CONTRACT

ROOT=Path(__file__).resolve().parents[3]
PACK=ROOT/'vendor/v165-deployment-pack/v165-codex-handoff'
PRIMARY='0496c4f5-fe89-5d30-b948-34505fb64143'
SECONDARY='59957ace-b4fb-519e-b92d-773bc74ad268'
TARGETS=(PRIMARY,SECONDARY)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def verify_files(directory):
    hashes=load(directory/'artifact_hashes.json')
    require({p.name for p in directory.iterdir() if p.is_file()}==set(hashes)|{'artifact_hashes.json'},'ARTIFACT_FILESET_MISMATCH')
    for name,expected in hashes.items():
        require(Path(name).name==name and sha256((directory/name).read_bytes())==expected,'UPSTREAM_HASH_MISMATCH',name)


@contextmanager
def offline_guard():
    attempts={'network':0,'sql':0,'process':0}
    def deny(kind):
        def blocked(*args,**kwargs):
            attempts[kind]+=1
            raise RuntimeError('FORBIDDEN_TRANSPORT:'+kind)
        return blocked
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket,'connect',deny('network')))
        stack.enter_context(patch.object(socket.socket,'connect_ex',deny('network')))
        stack.enter_context(patch.object(socket.socket,'sendto',deny('network')))
        stack.enter_context(patch.object(sqlite3,'connect',deny('sql')))
        stack.enter_context(patch.object(subprocess,'Popen',deny('process')))
        yield attempts


def immutable_inputs():
    paths=[]
    for directory in ('v162/baseline-reproduced','v163/artifacts/final-002','v163/inputs',
                      'v164/artifacts/final-003','src/kf_pilot/v16','src/kf_pilot/v162_remediation',
                      'src/kf_pilot/v163_evidence','src/kf_pilot/v164_semantics','v165/inputs'):
        paths += [p for p in (ROOT/directory).iterdir() if p.is_file()]
    paths += [ROOT/'v162/run_remediation.py',ROOT/'v163/run_evidence.py',ROOT/'v164/run_semantic.py',
              ROOT/'farming_input/resource_manifest.csv']
    paths += list((ROOT/'farming_input/files').glob('*'))
    paths += [p for p in PACK.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()) for p in sorted(set(paths))}


def span(ref,source,unit,start,end):
    return dict(source_ref=ref,raw_sha256=source['content_sha256'],extractor_id=source['extractor'],
                unit_id=unit,start=start,end=end,quote=source['texts'][unit][start:end])


def produce():
    before=immutable_inputs()
    runpy.run_path(str(PACK/'scripts/verify_handoff.py'))['verify']()
    v162=runpy.run_path(str(ROOT/'v162/run_remediation.py'))
    v162['verify_assets']()
    v164=runpy.run_path(str(ROOT/'v164/run_semantic.py'))
    v164['verify_checkpoint']()
    final=ROOT/'v164/artifacts/final-003'
    replay=ROOT/'v164/artifacts/replay-003'
    verify_files(final);verify_files(replay)
    require(sha256((final/'artifact_hashes.json').read_bytes())==
        'd154b411445d239a3a4167cf0b52e0158dffe6f49946baa40fe476cd38148aaf','V164_CHECKPOINT_MISMATCH')
    for name in [p.name for p in final.iterdir() if p.is_file()]:
        require((final/name).read_bytes()==(replay/name).read_bytes(),'V164_REPLAY_MISMATCH',name)
    for rel,h in load(final/'v164_code_manifest.json').items():
        require(sha256((ROOT/rel).read_bytes())==h,'V164_CODE_MANIFEST_MISMATCH',rel)
    base=ROOT/'v162/baseline-reproduced'
    plan=load(base/'notion_typed_update_plan.json')
    require(digest(plan)==BASELINE,'BASELINE_MISMATCH')
    versions=rows(base/'claim_versions.jsonl')
    source_issues=rows(base/'migration_issues.jsonl')
    recomputed_issues=inventory(versions,source_issues)
    old=ROOT/'v163/artifacts/final-002'
    original=load(old/'v162_issue_ledger.json')['issues']
    require({i['issue_id'] for i in original}=={i['issue_id'] for i in recomputed_issues},'ISSUE_SET_CHANGED')
    reviews=v162['parse_live'](load(ROOT/'v163/inputs/live_reviews_raw.json'))
    fresh=load(ROOT/'v165/inputs/pilot_reviews.json')
    current=v162['parse_live'](fresh['responses'])
    schema_text=json.loads(fresh['schema']['content'][0]['text'])['text']
    state=json.loads(re.search(r'<data-source-state>\s*(.*?)\s*</data-source-state>',schema_text,re.S).group(1))
    schema={k:'rich_text' if v['type']=='text' else v['type'] for k,v in state['schema'].items()}
    combined=deepcopy(reviews);combined.update(current)
    reconciliation=compute(versions,source_issues,plan['operations'],combined,schema,{})
    require(reconciliation['v162_issue_ledger.json']['issues']==original,'LIVE_REVIEW_CHANGED_REQUIRES_REBASE')
    catalog=source_catalog(ROOT)
    pinned=load(old/'v163_source_span_index.json')
    require(catalog==pinned['sources'],'SOURCE_EXTRACTION_CHANGED')
    for s in pinned['spans'].values():verify_span(s,catalog)
    maps=rows(final/'v164_mapping_snapshot.jsonl')
    human=rows(final/'v164_human_audit_snapshot.jsonl')
    by_map={r['entity_id']:r for r in maps};by_human={r['entity_id']:r for r in human}
    records=[]
    for v in versions:
        entity=v['claim_entity_id'];m=by_map[entity];h=by_human[entity]
        require(m['version_id']==v['claim_version_id'],'MAPPING_VERSION_MISMATCH')
        require(combined[m['page_id']]['parent']==m['parent_id'],'PARENT_MISMATCH')
        records.append(dict(m,semantic_payload=deepcopy(v['semantic_payload']),canonical_text=v['canonical_text'],
            decision=combined[m['page_id']]['properties']['Decision'],
            reviewer_note=combined[m['page_id']]['properties'].get('Reviewer Note',''),system_status=h['system_status']))
    require(len({r['page_id'] for r in records})==len(records),'MAPPING_COLLISION')
    spec_bytes=(PACK/'contracts/COMPLETE_RECORD_V1.md').read_bytes()
    spec_hash=sha256(spec_bytes)
    proposals=[];blockers=[];support_maps={};coverage={};overlap=[]
    v164proposals={p['entity_id']:p for p in rows(final/'v164_semantic_proposals.jsonl')}
    for entity in TARGETS:
        record=next(r for r in records if r['entity_id']==entity)
        prior=v164proposals[entity]
        ref=prior['context_span']['source_ref'];source=catalog[ref]
        unit=prior['context_span']['unit_id']
        require(unit=='pdf:page:67' and source['extractor']=='pymupdf:1.28.2:sort=True','LOCATOR_BASE_AMBIGUOUS')
        text=source['texts'][unit]
        require(re.match(r'\s*68\s',text) is not None,'PRINTED_PAGE_LABEL_MISMATCH')
        section=span(ref,source,unit,text.index('10. THỜI HẠN KIỂM ĐỊNH'),len(text))
        scope_unit='pdf:page:62';scope_text=source['texts'][scope_unit]
        scope=span(ref,source,scope_unit,0,len(scope_text))
        # Retain every page of the pinned QTKD scope as context, including definitions.
        context_spans=[span(ref,source,u,0,len(t)) for u,t in sorted(source['texts'].items()) if t.strip()]
        evidence=context_spans+[section,scope,prior['context_span'],prior['proofs']['amount'],prior['proofs']['unit']]
        evidence=list({digest(s):s for s in evidence}.values())
        support={'object_value/amount':[digest(prior['proofs']['amount'])],
            'object_value/unit':[digest(prior['proofs']['unit'])],
            'object_value/operator':[digest(prior['context_span'])],
            'condition_ast':[digest(prior['context_span'])], 'exception_ast':[digest(section)],
            'applicability':[digest(scope)],'jurisdiction':[digest(scope)],'legal_status':[],
            'overlap':[digest(section)]}
        assessments=dict(quantity='SUPPORTED',conditions='UNKNOWN',exceptions='UNKNOWN',
            applicability='SUPPORTED',jurisdiction='SUPPORTED',legal_status='UNKNOWN',overlap='UNRESOLVED',
            reviewed_scope={'corpus_sha256':source['content_sha256'],
                'units':sorted(source['texts']),'sections':['1','2','3','10.1','10.2','10.3','10.4'],
                'limitations':'Source-text audit only; cross-reference current validity and semantic review outstanding.'})
        local_blockers=[]
        for code,reason in [
            ('EXCEPTION_COVERAGE_UNKNOWN','Sections 10.2-10.4 contain shorter-interval and QCVN provisions; inherited FALSE is unproven.'),
            ('RULE_OVERLAP_UNRESOLVED','Fixed covered equipment older than 12 years is a review scenario potentially covered by both intervals; no approved precedence.'),
            ('LEGAL_STATUS_UNVERIFIED','No pinned authoritative 19/2025 reference/current amendment corpus establishes inherited current-validity flag.')]:
            b=dict(issue_id='v165_'+digest([entity,code,source['content_sha256']]),entity_id=entity,
                issue_type=code,resolution_status='NEEDS_REVIEW',reason=reason,source_ref=ref,
                discovered_from=sorted(i['issue_id'] for i in original if i['entity_id']==entity))
            local_blockers.append(b)
        blockers.extend(local_blockers)
        after=deepcopy(record['semantic_payload'])
        q=prior['target_semantic_payload']['object_value']
        after['object_value']={'type':'quantity','amount':q['amount'],'unit':q['unit'],'operator':q['operator']}
        dependency=next(r for r in records if r['entity_id'] in TARGETS and r['entity_id']!=entity)
        p=build_proposal(record,after,original,evidence,support,assessments,spec_hash,
            dependencies=[{'entity_id':dependency['entity_id'],'version_id':dependency['version_id'],'record_hash':digest(dependency)}],
            upstream=[prior['proposal_hash']],blockers=local_blockers)
        proposals.append(p);support_maps[entity]=support
        coverage[entity]={'raw_sha256':source['content_sha256'],'source_ref':ref,'extractor_id':source['extractor'],
            'source_path':source['path'],'page_ordinal':67,'pdf_zero_based_index':66,'printed_page_label':68,
            'page_mapping_verified':True,'assessments':assessments,'spans':p['source_bundle'],
            'cross_references_pending':['QCVN 7:2012/BLDTBXH','TCVN 4244:2005','TCVN 5207:1990',
                                        '19/2025/TT-BNV and subsequent amendments'],
            'visual_audit':['v165/audit/interval-page.png','v165/audit/scope-page.png']}
        overlap.append({'entity_id':entity,'other_entity_id':dependency['entity_id'],'status':'UNRESOLVED',
            'review_scenario':{'fixed':True,'covered':True,'age_over_12_years':True},
            'three_year_rule_match':'REVIEW_HYPOTHESIS','one_year_rule_match':'REVIEW_HYPOTHESIS',
            'precedence':None,'semantic_truth_table':'NOT_CERTIFIED','support_span':digest(section)})
    projected=sorted(deepcopy(original)+blockers,key=lambda i:i['issue_id'])
    unresolved=sum(i['resolution_status']!='RESOLVED' for i in original)
    total=sum(i['resolution_status']!='RESOLVED' for i in projected)
    require(total==unresolved+len(blockers),'LEDGER_ACCOUNTING_MISMATCH')
    record_plan=[]
    for r in sorted(records,key=lambda r:r['entity_id']):
        related=[i for i in projected if i['entity_id']==r['entity_id'] and i['resolution_status']!='RESOLVED']
        record_plan.append(dict(entity_id=r['entity_id'],page_id=r['page_id'],parent_id=r['parent_id'],
            base_version_id=r['version_id'],target_version_id=None,operation='NO_CHANGE',
            blockers=[i['issue_id'] for i in related],decision=r['decision'],
            publication_review='NOT_EVALUATED_NO_TARGET',eligible=False))
    report=dict(status='V165_CODE_PASS_WAITING_INPUTS / PHASE_F_NOT_AUTHORIZED',mode='LOCAL / NO_WRITE',
        data_class='REPOSITORY',apply_status='NOT_EXECUTED',apply_reason='DRAFT_EVIDENCE_CONTRACT_AND_ADJUDICATION_MISSING',
        original_unresolved=unresolved,original_resolved_in_projection=0,new_blockers=len(blockers),
        total_projected_unresolved=total,complete_records_projected=0,draft_proposals=len(proposals),
        activation='NOT_SUPPLIED',adjudications=0,unrelated_record_deltas=0,
        eligible_production_records=None,eligibility_status='NOT_EVALUATED_NO_COMPLETE_RECORD',
        canary_records=0,authorized_to_execute=False,baseline_before=BASELINE,baseline_after=digest(plan),
        live_review_scope='TWO_PILOT_PAGES_ONLY',live_review_count=len(current),
        other_reviews='PINNED_V163_SNAPSHOT_NOT_REFRESHED',mapping_count=len(records),
        mapping_collisions=0,missing_mappings=0,mutation_counters_status='OBSERVED_OFFLINE_TRANSPORT_GUARD',
        human_field_writes=0,production_writes=0,create_operations=0,sql_executions=0,schema_mutations=0,scheduler_actions=0)
    review_md='# V16.5 complete-record review pack\n\nDRAFT — no real activation/adjudication.\n\n'
    for p in proposals:
        review_md+=f"## {p['entity_id']}\n\nProposal hash: `{p['proposal_hash']}`\n\nTarget version: null (DRAFT).\n\n"
        review_md+='Issues: '+', '.join(p['original_issue_ids'])+'\n\n'
        review_md+='```json\n'+json.dumps({'before':p['before_semantic_payload'],'after':p['after_semantic_payload'],
            'assessments':p['completeness_assessments'],'blockers':p['new_blockers']},ensure_ascii=False,indent=2)+'\n```\n\n'
    outputs={'baseline_verification.json':{'status':'PASS','canonical_sha256':BASELINE,'v162_empty_recompute':'PASS',
            'legacy_issue_count':len(original),'human_snapshot_sha256':digest(human),'mapping_sha256':digest(maps)},
        'source_coverage.json':coverage,'field_support_map.json':support_maps,'rule_overlap_review.json':overlap,
        'contract_spec.json':{'contract_id':CONTRACT,'sha256':spec_hash,'status':'DRAFT_FOR_REVIEW','text':spec_bytes.decode('utf-8')},
        'contract_activation_status.json':{'status':'NOT_SUPPLIED','spec_hash':spec_hash,'template_is_approval':False},
        'complete_record_proposals.jsonl':proposals,'review_pack.md':review_md,'adjudications.jsonl':[],
        'projection_events.jsonl':[],
        'original_issue_lineage.jsonl':[{'original_issue_id':i['issue_id'],'before_value_hash':i['before_value_hash'],
            'entity_id':i['entity_id'],'version_id':i['version_id'],'projection':'UNCHANGED'} for i in sorted(original,key=lambda x:x['issue_id'])],
        'new_blockers.jsonl':sorted(blockers,key=lambda x:x['issue_id']),
        'projected_issue_ledger.json':{'mode':'LOCAL_SHADOW','apply_status':'NOT_EXECUTED','issues':projected},
        'projected_record_plan.json':{'records':record_plan,'authorized_to_execute':False},
        'readiness_report.json':report,'phase_f_canary_plan.json':{'records':[],'authorized_to_execute':False},
        'input_manifest.json':{'files':before,'as_of':fresh['retrieved_at'],'review_scope':fresh['scope']}}
    require(before==immutable_inputs(),'INPUT_MUTATION_DETECTED')
    return outputs
