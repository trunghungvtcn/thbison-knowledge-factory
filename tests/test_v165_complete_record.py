"""Acceptance matrix: same validator/projector for TEST_ONLY and repository paths."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket
import sqlite3
import subprocess

import pytest

from kf_pilot.v16.identity import claim_version_id
from kf_pilot.v164_semantics.canonical import GateError,digest,sha256
from kf_pilot.v164_semantics.evidence import SourceStore,utf8_units
from kf_pilot.v165_complete_record.core import (CONTRACT,CHECKS,CHANGES,ast_paths,build_proposal,
    coverage_hash,dispatch,project,validate_bundle)
from kf_pilot.v165_complete_record.repository import ROOT,offline_guard,produce,verify_files
from kf_pilot.v165_complete_record.cli import gate,write,encode


@pytest.fixture
def case(tmp_path):
    text='TEST ONLY. Inspection interval 3 years when fixed and covered. No exception in TEST corpus. TEST region.'
    raw=text.encode();(tmp_path/'source.txt').write_bytes(raw)
    spec=[dict(source_ref='TEST_ONLY_SOURCE',path='source.txt',raw_sha256=sha256(raw),extractor_id='utf8/v1')]
    store=SourceStore(tmp_path,spec,{'utf8/v1':utf8_units})
    def span(a,b):return dict(source_ref='TEST_ONLY_SOURCE',raw_sha256=sha256(raw),extractor_id='utf8/v1',
        unit_id='text:0',start=a,end=b,quote=text[a:b])
    full=span(0,len(text));pos=text.index('3 years');amount=span(pos,pos+1);unit=span(pos+2,pos+7)
    before=dict(product_family='TEST',subject='TEST',predicate='inspection_interval',
        object_value={'type':'legacy_text','value':text},applicability='TEST_SCOPE',jurisdiction='TEST',
        legal_status='TEST_ONLY',condition_ast={'op':'UNRESOLVED','legacy_tags':['FIXED','COVERED']},exception_ast={'op':'FALSE'})
    entity='00000000-0000-0000-0000-000000000001'
    record=dict(entity_id=entity,version_id=claim_version_id(entity,before),page_id='TEST_PAGE',parent_id='TEST_PARENT',
        semantic_payload=before,canonical_text=text,decision='PENDING',reviewer_note='keep me',system_status='REVIEW_REQUIRED')
    issues=[dict(issue_id='TEST_ISSUE_'+kind,entity_id=entity,version_id=record['version_id'],
        issue_type=kind,before_value_hash=digest(before[field]['value'] if field=='object_value' else before[field]),resolution_status='NEEDS_REVIEW')
        for kind,field in [('OBJECT_VALUE_UNSTRUCTURED','object_value'),('CONDITION_CONNECTIVE_AMBIGUOUS','condition_ast')]]
    after=deepcopy(before);after['object_value']={'type':'quantity','amount':'3','unit':'year','operator':'EQ'}
    after['condition_ast']={'op':'AND','args':[{'op':'COMPARE','field':'covered','comparator':'EQ','value':True},
                                             {'op':'COMPARE','field':'fixed','comparator':'EQ','value':True}]}
    support={k:[digest(full)] for k in ['object_value/operator','applicability','jurisdiction','legal_status','overlap']+
        ast_paths(after['condition_ast'],'condition_ast')+ast_paths(after['exception_ast'],'exception_ast')}
    support.update({'object_value/amount':[digest(amount)],'object_value/unit':[digest(unit)]})
    assessment=dict(quantity='SUPPORTED',conditions='SUPPORTED',exceptions='NO_APPLICABLE_EXCEPTION_IN_REVIEWED_SCOPE',
        applicability='SUPPORTED',jurisdiction='SUPPORTED',legal_status='SUPPORTED',overlap='NO_CONFLICT_IN_REVIEWED_SCOPE',
        reviewed_scope={'corpus':'TEST_ONLY_SOURCE','section':'all','rationale':'Synthetic complete source'})
    p=build_proposal(record,after,issues,[full,amount,unit],support,assessment,'TEST_SPEC',data_class='TEST_ONLY')
    actor=dict(data_class='TEST_ONLY',active=True,roles=['CONTRACT_APPROVER','SEMANTIC_REVIEWER'],
        predicates=['inspection_interval'],entity_ids=[entity],valid_from='2026-01-01T00:00:00Z',valid_until='2027-01-01T00:00:00Z')
    registry={'data_class':'TEST_ONLY','entries':{'TEST_APPROVER':deepcopy(actor),'TEST_REVIEWER':deepcopy(actor)}}
    activation=dict(data_class='TEST_ONLY',contract_spec_hash='TEST_SPEC',activation_id='TEST_ACTIVATION',
        issuer_id='TEST_APPROVER',issuer_role='CONTRACT_APPROVER',decision='APPROVE_LOCAL_SHADOW',
        allowed_predicates=['inspection_interval'],target_entity_ids=[entity],mode='LOCAL_SHADOW',
        valid_from='2026-01-01T00:00:00Z',valid_until='2027-01-01T00:00:00Z',approval_evidence_ref='TEST_RECEIPT',registry_hash=digest(registry))
    review={k:deepcopy(p[k]) for k in ['proposal_hash','contract_spec_hash','entity_id','base_version_id',
        'target_version_id','original_issue_ids','source_coverage_hash']}
    review.update(data_class='TEST_ONLY',reviewer_id='TEST_REVIEWER',registry_hash=digest(registry),
        decided_at='2026-09-01T00:00:00Z',decision='ACCEPT',rationale='TEST ONLY complete bundle',checks={k:True for k in CHECKS})
    roots=dict(registry=registry,activation=activation,adjudication=review)
    kwargs=dict(p=p,records=[record],issues=issues,store=store,spec_hash='TEST_SPEC',data_class='TEST_ONLY',
        roots=roots,pins={k:digest(v) for k,v in roots.items()},as_of='2026-09-05T00:00:00Z',expected_parent='TEST_PARENT',
        schema={k:'rich_text' for k in ['Object Value','Condition AST','Claim Entity ID','Claim Version ID']})
    return kwargs


def reseal(p):
    p['source_coverage_hash']=coverage_hash(p)
    p['proposal_hash']=digest({k:v for k,v in p.items() if k!='proposal_hash'})


def repin(c):
    c['pins']={k:digest(v) for k,v in c['roots'].items()}


def test_A19_A33_atomic_complete_positive_same_runtime(case):
    original=deepcopy((case['records'],case['issues']))
    result=dispatch(CONTRACT,**case)
    assert len(result['events'])==2
    assert all(i['resolution_status']=='RESOLVED' for i in result['issues'])
    assert len({e['target_version_id'] for e in result['events']})==1
    assert result['records'][0]['reviewer_note']=='keep me'
    assert original==(case['records'],case['issues'])
    assert result['authorized_to_execute'] is False
    assert result['publication_review']=='STALE_REQUIRES_TARGET_VERSION_REVIEW'


def test_A03_legacy_prose_remains_incompatible(case):
    r=case['records'][0];text=r['semantic_payload']['object_value']['value']
    issue=dict(entity_id=r['entity_id'],version_id=r['version_id'],issue_type='OBJECT_VALUE_UNSTRUCTURED',source_text=text)
    ev=dict(entity_id=r['entity_id'],version_id=r['version_id'],field='object_value',ref='TEST',
        literal=text,content=text,content_sha256=sha256(text.encode()),authoritative=True,scope_verified=True)
    assert dispatch('legacy_literal/v1',issue=issue,evidence=ev) is None


def test_A04_unknown_route(case):
    with pytest.raises(GateError,match='UNKNOWN_CONTRACT'):dispatch('guess-fallback',**case)


@pytest.mark.parametrize('field,value', [('contract_spec_hash','wrong'),('allowed_predicates',[]),
    ('target_entity_ids',[]),('valid_until','2020-01-01T00:00:00Z'),('issuer_id','invented'),('decision','NOT_APPROVED')])
def test_A06_bad_activation(case,field,value):
    case['roots']['activation'][field]=value;repin(case)
    with pytest.raises(GateError):project(**case)


def test_A05_missing_activation_blocks(case):
    case['roots']['activation']=None;repin(case)
    with pytest.raises(GateError,match='CONTRACT_NOT_ACTIVATED'):project(**case)


def test_A07_test_data_rejected_from_repository(case):
    case['data_class']='REPOSITORY'
    with pytest.raises(GateError,match='TEST_DATA_IN_REPOSITORY'):project(**case)


@pytest.mark.parametrize('assessment', ['conditions','exceptions','legal_status','applicability','overlap'])
def test_A08_A09_A10_A16_A17_incomplete_record(case,assessment):
    case['p']['completeness_assessments'][assessment]='UNKNOWN';reseal(case['p'])
    with pytest.raises(GateError,match='INCOMPLETE_RECORD'):project(**case)


def test_A14_unresolved_condition_cannot_be_complete(case):
    p=case['p'];p['after_semantic_payload']['condition_ast']=deepcopy(p['before_semantic_payload']['condition_ast'])
    p['actual_field_diff']=['object_value'];p['after_semantic_hash']=digest(p['after_semantic_payload']);reseal(p)
    with pytest.raises(GateError,match='INCOMPLETE_RECORD'):project(**case)


def test_A15_missing_ast_leaf_support(case):
    del case['p']['field_support_map']['condition_ast/args/0'];reseal(case['p'])
    with pytest.raises(GateError,match='INCOMPLETE_RECORD'):project(**case)


@pytest.mark.parametrize('field,value',[('amount','31'),('unit','ton'),('operator','LTE')])
def test_A12_wrong_quantity(case,field,value):
    p=case['p'];p['after_semantic_payload']['object_value'][field]=value
    p['after_semantic_hash']=digest(p['after_semantic_payload']);reseal(p)
    with pytest.raises(GateError):project(**case)


@pytest.mark.parametrize('field,value',[('quote','forged'),('unit_id','pdf:page:68'),('extractor_id','different'),('start',9999)])
def test_A01_A11_A13_raw_span_tampering(case,field,value):
    p=case['p'];p['source_bundle'][0][field]=value;reseal(p)
    with pytest.raises(GateError):project(**case)


def test_A18_compound_change_outside_allowlist(case):
    p=case['p'];p['after_semantic_payload']['predicate']='all_safety'
    reseal(p)
    with pytest.raises(GateError,match='UNKNOWN_FIELD_CHANGE'):project(**case)


@pytest.mark.parametrize('field,value',[('target_version_id','old'),('proposal_hash','quantity-only'),
    ('original_issue_ids',['object-only']),('source_coverage_hash','stale')])
def test_A20_A21_stale_whole_record_review(case,field,value):
    case['roots']['adjudication'][field]=value;repin(case)
    with pytest.raises(GateError,match='REVIEW_BINDING_STALE'):project(**case)


def test_A22_missing_review(case):
    case['roots']['adjudication']=None;repin(case)
    with pytest.raises(GateError,match='REVIEW_REQUIRED'):project(**case)


def test_A22_self_review(case):
    registry=case['roots']['registry'];registry['entries']['KF_V165_BUILDER']=registry['entries']['TEST_REVIEWER']
    for name in ('activation','adjudication'):case['roots'][name]['registry_hash']=digest(registry)
    case['roots']['adjudication']['reviewer_id']='KF_V165_BUILDER';repin(case)
    with pytest.raises(GateError,match='SELF_ADJUDICATION'):project(**case)


def test_A23_base_changed(case):
    case['records'][0]['version_id']='another'
    with pytest.raises(GateError,match='BASE_VERSION_CHANGED'):project(**case)


def test_A24_failure_rolls_back_everything(case):
    original=deepcopy((case['records'],case['issues']))
    with pytest.raises(GateError,match='ATOMIC_PROJECTION_FAILED'):project(**case,fail_after_stage=True)
    assert original==(case['records'],case['issues'])


def test_A25_new_blocker_rejects_atomic_projection(case):
    case['p']['new_blockers']=[{'issue_id':'new','reason':'exception unknown'}];reseal(case['p'])
    with pytest.raises(GateError,match='INCOMPLETE_RECORD'):project(**case)


@pytest.mark.parametrize('decision',['HOLD','REJECTED'])
def test_A27_human_hold_wins(case,decision):
    case['records'][0]['decision']=decision
    with pytest.raises(GateError,match='HUMAN_HOLD'):project(**case)


def test_A28_unrelated_record_unchanged(case):
    other=deepcopy(case['records'][0]);other.update(entity_id='another',page_id='ANOTHER_PAGE')
    case['records'].append(other)
    result=project(**case)
    assert result['records'][1]==other


def test_A29_reverse_order(case):
    a=project(**case);case['issues'].reverse()
    b=project(**case)
    assert sorted(a['issues'],key=lambda i:i['issue_id'])==sorted(b['issues'],key=lambda i:i['issue_id'])
    assert a['events']==b['events']


@pytest.mark.parametrize('field,value',[('version_id','stale'),('before_value_hash','forged'),('issue_type','NEW_EXCEPTION_GAP')])
def test_A21_issue_ledger_drift(case,field,value):
    case['issues'][0][field]=value
    with pytest.raises(GateError):project(**case)


def test_A01_raw_hash_tamper(case,tmp_path):
    (tmp_path/'source.txt').write_text('changed raw source')
    with pytest.raises(GateError,match='SOURCE_HASH_MISMATCH'):
        SourceStore(tmp_path,list(case['store'].sources.values()),{'utf8/v1':utf8_units})


def test_A01_reject_pinned_baseline_change(monkeypatch):
    import kf_pilot.v165_complete_record.repository as repository
    monkeypatch.setattr(repository,'BASELINE','changed')
    with pytest.raises(GateError,match='BASELINE_MISMATCH'):repository.produce()


@pytest.mark.parametrize('mutation',['collision','missing','parent','schema'])
def test_A35_mapping_schema_checks(case,mutation):
    if mutation=='collision':case['records'].append(deepcopy(case['records'][0]))
    if mutation=='missing':case['records'][0]['page_id']=None
    if mutation=='parent':case['expected_parent']='wrong'
    if mutation=='schema':case['schema']['Object Value']='number'
    with pytest.raises(GateError):project(**case)


@pytest.mark.parametrize('action',[lambda:socket.socket().connect(('127.0.0.1',9)),
    lambda:sqlite3.connect(':memory:'),lambda:subprocess.Popen(['should-not-run'])])
def test_A36_transport_guard(action):
    with offline_guard() as counters:
        with pytest.raises(RuntimeError,match='FORBIDDEN_TRANSPORT'):action()
    assert sum(counters.values())==1


def test_A26_A32_real_no_accept_accounting():
    with offline_guard():result=produce()
    r=result['readiness_report.json'];original=result['original_issue_lineage.jsonl']
    assert r['apply_status']=='NOT_EXECUTED'
    assert r['total_projected_unresolved']==r['original_unresolved']+r['new_blockers']
    assert r['original_resolved_in_projection']==0
    assert len({i['original_issue_id'] for i in original})==len(original)
    assert all(p['target_version_id'] is None and p['status']=='DRAFT' for p in result['complete_record_proposals.jsonl'])
    assert result['phase_f_canary_plan.json']=={'records':[],'authorized_to_execute':False}
    assert r['mapping_count']==70 and r['new_blockers']==6


def test_A30_A31_independent_replay_and_rehashed_tampering(tmp_path):
    a,b=tmp_path/'a',tmp_path/'b'
    write(a);write(b)
    assert gate(a,b)['replay']=='BYTE_EQUAL'
    for path in (a,b):
        report=json.loads((path/'readiness_report.json').read_text());report['new_blockers']=0
        data=encode('readiness_report.json',report);(path/'readiness_report.json').write_bytes(data)
        manifest=json.loads((path/'artifact_hashes.json').read_text());manifest['readiness_report.json']=sha256(data)
        (path/'artifact_hashes.json').write_bytes(encode('artifact_hashes.json',manifest))
    with pytest.raises(GateError,match='INDEPENDENT_RECOMPUTATION_MISMATCH'):gate(a,b)
