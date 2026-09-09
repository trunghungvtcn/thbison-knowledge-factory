from copy import deepcopy
import hashlib
import json
import pytest
from kf_pilot.v162_remediation.core import *


def fixture(text='2 kg', tags=None, decision='PENDING'):
    payload = dict(product_family='hoist', subject='hoist', predicate='capacity', applicability='test',
                   object_value={'type': 'legacy_text', 'value': text}, condition_ast=tags or {'op': 'TRUE'})
    entity='entity-1'; version=claim_version_id(entity,payload)
    versions=[dict(claim_entity_id=entity,claim_version_id=version,legacy_canonical_id='legacy-1',semantic_payload=payload)]
    issues=[dict(claim_entity_id=entity,code='OBJECT_VALUE_UNSTRUCTURED')]
    if contains_unresolved(payload['condition_ast']):
        issues.append(dict(claim_entity_id=entity,code='CONDITION_CONNECTIVE_UNRESOLVED'))
    ops=[dict(claim_entity_id=entity,page_id='page-1',operation='UPDATE')]
    reviews={'page-1':dict(parent=PARENT, properties={'Decision':decision,'Reviewer Note':'KEEP','Knowledge ID':'legacy-1'})}
    schema={k:'rich_text' for k in SYSTEM}
    return versions,issues,ops,reviews,schema


def evidence_for(issue, literal=None):
    literal=literal if literal is not None else issue['source_text']
    return dict(entity_id=issue['entity_id'],version_id=issue['version_id'],
                field='object_value' if issue['issue_type']=='OBJECT_VALUE_UNSTRUCTURED' else 'condition_ast',
                ref='fixture://authoritative/source',content=literal,literal=literal,
                content_sha256=hashlib.sha256(literal.encode()).hexdigest(),scope_verified=True,authoritative=True)


def computed(text='2 kg',decision='PENDING'):
    args=fixture(text,decision=decision); issue=inventory(*args[:2])[0]
    return args, {issue['issue_id']:evidence_for(issue)}


def test_inventory_all_accounted():
    args=fixture(tags={'op':'UNRESOLVED','legacy_tags':['A','B']})
    assert len(inventory(*args[:2]))==2
    with pytest.raises(ValueError): inventory(args[0],args[1][:-1])


@pytest.mark.parametrize('tamper',['duplicate','missing','evidence','rule','hash','decision','note'])
def test_ledger_fail_closed(tamper):
    args,e= computed(); i=inventory(*args[:2]); pages={'entity-1':'page-1'}
    ledger=ledger_for(i,args[3],pages,e)
    if tamper=='duplicate': ledger.append(deepcopy(ledger[0]))
    elif tamper=='missing': ledger=[]
    else: ledger[0][{'evidence':'source_evidence_refs','rule':'resolution_rule','hash':'after_value_hash','decision':'decision_snapshot','note':'reviewer_note_snapshot'}[tamper]]=None
    with pytest.raises(ValueError):gate_ledger(ledger,i,args[3],pages,e)


@pytest.mark.parametrize('text,kind',[('2 kg','quantity'),('true','boolean'),('false','boolean'),('{"type":"enum","value":"TEST"}','enum')])
def test_exact_literals(text,kind):
    args,e=computed(text); result=compute(*args,e)
    assert result['v162_issue_ledger.json']['issues'][0]['structured_value']['type']==kind


def test_exact_enum():
    args,e=computed('VERTICAL'); ev=next(iter(e.values()))
    ev.update(controlled_vocabulary=['VERTICAL'],vocabulary_ref='fixture://vocab',vocabulary_sha256=digest(['VERTICAL']))
    assert compute(*args,e)['v162_issue_ledger.json']['issues'][0]['resolution_status']=='RESOLVED'


@pytest.mark.parametrize('text',['2 tons','2','about 2 kg','2 kg if outdoors','TRUE unless loaded'])
def test_ambiguous_value_not_resolved(text):
    args,e=computed(text)
    assert compute(*args,e)['v162_issue_ledger.json']['issues'][0]['resolution_status']=='NEEDS_REVIEW'


def test_ambiguous_condition_stays_unresolved():
    args=fixture(tags={'op':'UNRESOLVED','legacy_tags':['A','B']})
    assert compute(*args)['v162_readiness_report.json']['unresolved_issue_count']==2


@pytest.mark.parametrize('ast',[{'op':'AND','args':[{'op':'TRUE'},{'op':'FALSE'}]}, {'op':'OR','args':[{'op':'TRUE'},{'op':'FALSE'}]}, {'op':'NOT','arg':{'op':'TRUE'}}])
def test_explicit_ast_only(ast):
    args=fixture(tags={'op':'UNRESOLVED','legacy_tags':['A','B']})
    issue=next(r for r in inventory(*args[:2]) if r['issue_type']=='CONDITION_CONNECTIVE_AMBIGUOUS')
    assert resolve(issue,evidence_for(issue,canonical(ast)))['condition_ast']==canonicalize_ast(ast)


@pytest.mark.parametrize('decision',['HOLD','REJECTED'])
def test_live_decisions_preserved(decision):
    args,e=computed(decision=decision); r=compute(*args,e)
    assert not r['v162_eligible_subset.json']
    assert r['v162_canonical_plan.json']['records'][0]['decision_binding']['Reviewer Note']=='KEEP'
    assert r['v162_canonical_plan.json']['records'][0]['live_decision']==decision


@pytest.mark.parametrize('bad',['CREATE','human','missing','collision','schema','parent'])
def test_eligibility_guards(bad):
    args,e=computed(); args=list(deepcopy(args))
    if bad=='CREATE': args[2][0]['operation']='CREATE'
    if bad=='human': args[2][0]['typed_properties']={'Decision':{}}
    if bad=='missing':args[2][0]['page_id']=None
    if bad=='collision':args[2].append(dict(args[2][0],claim_entity_id='entity-2'))
    if bad=='schema':args[4]['Object Value']='number'
    if bad=='parent':args[3]['page-1']['parent']='PRODUCTION_OTHER'
    if bad in ('CREATE','human'):
        with pytest.raises(ValueError):compute(*args,e)
    else: assert not compute(*args,e)['v162_eligible_subset.json']


def test_reverse_replay_and_locality():
    args,e=computed(); args=list(deepcopy(args))
    v=deepcopy(args[0][0]);v['claim_entity_id']='entity-2';v['legacy_canonical_id']='legacy-2'
    v['claim_version_id']=claim_version_id('entity-2',v['semantic_payload']);args[0].append(v)
    args[1].append(dict(claim_entity_id='entity-2',code='OBJECT_VALUE_UNSTRUCTURED'))
    args[2].append(dict(claim_entity_id='entity-2',page_id='page-2',operation='UPDATE'))
    args[3]['page-2']=deepcopy(args[3]['page-1']);args[3]['page-2']['properties']['Knowledge ID']='legacy-2'
    before=compute(*args);after=compute(*args,e)
    assert before['v162_canonical_plan.json']['records'][1]==after['v162_canonical_plan.json']['records'][1]
    assert before['v162_canonical_plan.json']['records'][0]['version_id']!=after['v162_canonical_plan.json']['records'][0]['version_id']
    assert after==compute(args[0][::-1],args[1][::-1],args[2][::-1],args[3],args[4],e)


@pytest.mark.parametrize('bad',['authorized','size','human','create','hold','baseline','counter','missing_counter','hash'])
def test_readiness_fail_closed(bad):
    args,e=computed();r=compute(*args,e);report=deepcopy(r['v162_readiness_report.json']);canary=deepcopy(r['v162_phase_f_canary_plan.json']);records=r['v162_canonical_plan.json']['records']
    assert len(canary['records'])==1
    if bad=='authorized':canary['authorized_to_execute']=True
    if bad=='size':canary['records']*=4
    if bad=='human':canary['records'][0]['field_delta']['Decision']={}
    if bad=='create':canary['records'][0]['operation']='CREATE'
    if bad=='hold':canary['records'][0]['live_decision']='HOLD'
    if bad=='baseline':report['v161_baseline_hash_after']='bad'
    if bad=='counter':report['production_write_count']=1
    if bad=='missing_counter':del report['production_write_count']
    if bad=='hash':canary['records'][0]['rollback_hash']='bad'
    with pytest.raises(ValueError):gate_readiness(report,canary,records)


def test_no_network_or_writes(monkeypatch):
    import socket
    monkeypatch.setattr(socket,'socket',lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden')))
    assert compute(*fixture())['v162_phase_f_canary_plan.json']=={'authorized_to_execute':False,'records':[]}


@pytest.mark.parametrize('field,value',[('content_sha256','bad'),('scope_verified',False),('authoritative',False),('entity_id','other'),('version_id','other'),('literal','1 kg')])
def test_unverified_evidence_never_resolves(field,value):
    args,e=computed();next(iter(e.values()))[field]=value
    assert compute(*args,e)['v162_issue_ledger.json']['issues'][0]['resolution_status']=='NEEDS_REVIEW'
