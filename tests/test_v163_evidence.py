from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from kf_pilot.v162_remediation.core import digest
from kf_pilot.v163_evidence.binding import *
from kf_pilot.v163_evidence.sources import verify_span


def case(text='2 kg',typ='OBJECT_VALUE_UNSTRUCTURED'):
    source_ref='fixture://source'
    h=hashlib.sha256(text.encode()).hexdigest()
    source=dict(source_ref=source_ref,content_sha256=h,texts={'text:line:1':text})
    issue=dict(issue_id='issue-1',issue_type=typ,entity_id='entity-1',version_id='version-1',
               source_text=text,resolution_status='NEEDS_REVIEW',page_id='page-1')
    payload={'predicate':'capacity','applicability':'TEST','jurisdiction':'TEST','object_value':{'type':'legacy_text','value':text}}
    if typ=='CONDITION_CONNECTIVE_AMBIGUOUS':payload['condition_ast']={'op':'UNRESOLVED','legacy_tags':['TEST'], 'raw_text':text}
    versions=[dict(claim_entity_id='entity-1',claim_version_id='version-1',semantic_payload=payload)]
    review={'page-1':{'properties':{'Source URL':source_ref}}}
    work,spans=review_work({'issues':[issue]},[issue],versions,review,{source_ref:source})
    candidates=proposals(work,spans)
    return work,spans,candidates,{source_ref:source}


def decision(b,kind='ACCEPT'):
    return dict(binding_id=b['binding_id'],issue_id=b['issue_id'],decision=kind,reviewer_id='human-test',reviewed_at='2026-09-04T00:00:00Z',rationale='Explicit fixture approval')


def test_real_79_shape_accounting():
    root=Path(__file__).resolve().parents[1]
    ledger=json.loads((root/'v162/artifacts/remediation-final/v162_issue_ledger.json').read_text(encoding='utf-8'))
    queue=json.loads((root/'v162/artifacts/remediation-final/v162_unresolved_review_queue.json').read_text(encoding='utf-8'))
    versions=[json.loads(x) for x in (root/'v162/baseline-reproduced/claim_versions.jsonl').read_text(encoding='utf-8').splitlines()]
    work,_=review_work(ledger,queue,versions,{}, {})
    assert len(work)==len(queue)==len(ledger['issues'])==79
    assert {w['issue_id'] for w in work}=={r['issue_id'] for r in queue}
    assert all(w['source_status']=='SOURCE_UNAVAILABLE' for w in work)
    for broken in (queue[:-1],queue+[queue[0]]):
        with pytest.raises(ValueError):review_work(ledger,broken,versions,{}, {})


@pytest.mark.parametrize('bad',['hash','quote','locator','record','version','predicate','scope','duplicate','identity','binding_hash'])
def test_binding_tamper_rejected(bad):
    work,spans,b,catalog=case();b=deepcopy(b)
    if bad=='hash':b[0]['source']['content_sha256']='0'*64
    if bad=='quote':b[0]['source']['exact_quote']='3 kg'
    if bad=='locator':b[0]['source']['locator']='text:line:1:chars:1:4'
    if bad=='record':b[0]['record_id']='other'
    if bad=='version':b[0]['version_id']='other'
    if bad=='predicate':b[0]['predicate']='other'
    if bad=='scope':b[0]['applicability']={'scope':'other'}
    if bad=='identity':b[0]['issue_id']='other'
    if bad!='binding_hash':b[0]['binding_id']=digest({k:v for k,v in b[0].items() if k!='binding_id'})
    else:b[0]['binding_id']='bad'
    if bad=='duplicate':b.append(deepcopy(b[0]))
    with pytest.raises(ValueError):adjudicate(b,[],work,catalog,[])


@pytest.mark.parametrize('text',['2 tons','2','true if outdoors','Title of inspection procedure','inspect daily and record monthly'])
def test_ambiguous_or_compound_not_scalar(text):
    assert not case(text)[2]


def test_enum_requires_vocabulary():
    work,_,b,catalog=case('{"type":"enum","value":"ANY_STRING"}')
    with pytest.raises(ValueError,match='vocabulary'):adjudicate(b,[decision(b[0])],work,catalog,['human-test'])


@pytest.mark.parametrize('text',['2 kg','true','false'])
def test_explicit_accept_enters_v162_contract(text):
    work,_,b,catalog=case(text)
    accepted,_,ev=adjudicate(b,[decision(b[0])],work,catalog,['human-test'])
    assert len(accepted)==len(ev)==1


@pytest.mark.parametrize('ast',[{'op':'AND','args':[{'op':'TRUE'},{'op':'FALSE'}]}, {'op':'OR','args':[{'op':'TRUE'},{'op':'FALSE'}]}, {'op':'NOT','arg':{'op':'TRUE'}}])
def test_explicit_ast_accept(ast):
    work,_,b,catalog=case(json.dumps(ast),typ='CONDITION_CONNECTIVE_AMBIGUOUS')
    assert len(adjudicate(b,[decision(b[0])],work,catalog,['human-test'])[0])==1


def test_ambiguous_ast_rejected():
    assert not case('{"op":"UNRESOLVED","legacy_tags":["A","B"]}',typ='CONDITION_CONNECTIVE_AMBIGUOUS')[2]


@pytest.mark.parametrize('d',['REJECT','HOLD','NEEDS_MORE_EVIDENCE'])
def test_nonaccept_excluded(d):
    work,_,b,catalog=case()
    accepted,rejected,ev=adjudicate(b,[decision(b[0],d)],work,catalog,['human-test'])
    assert accepted==[] and ev=={} and rejected[0]['reason']==d


def test_missing_human_no_approval():
    work,_,b,catalog=case()
    assert not adjudicate(b,[],work,catalog,[])[0]
    with pytest.raises(ValueError):adjudicate(b,[decision(b[0])],work,catalog,[])
    a=decision(b[0]);a['issue_id']='other'
    with pytest.raises(ValueError):adjudicate(b,[a],work,catalog,['human-test'])


def test_source_reverified():
    work,spans,b,catalog=case();catalog['fixture://source']['texts']['text:line:1']='3 kg'
    with pytest.raises(ValueError):verify_span(next(iter(spans.values())),catalog)


def test_prose_proposal_not_silently_bridged():
    work,spans,_,catalog=case('Capacity must not be exceeded.')
    work[0]['predicate']='overload_prohibition';b=proposals(work,spans)
    assert len(b)==1
    with pytest.raises(ValueError,match='V162_CONTRACT_INCOMPATIBLE'):
        adjudicate(b,[decision(b[0])],work,catalog,['human-test'])


def test_reverse_order_locality_and_immutable_inputs():
    work,spans,b,catalog=case();original=deepcopy(work)
    second=deepcopy(work[0]);second.update(issue_id='issue-2',record_id='entity-2')
    work.append(second);before=proposals(work,spans)
    assert before==proposals(work[::-1],dict(reversed(list(spans.items()))))
    work[0]['predicate']='new predicate';after=proposals(work,spans)
    assert before[1]==after[1] and before[0]!=after[0]
    assert original[0]['version_id']==work[0]['version_id']


def test_local_no_network(monkeypatch):
    import socket
    monkeypatch.setattr(socket,'socket',lambda *a,**k:(_ for _ in ()).throw(AssertionError('network')))
    work,_,b,catalog=case();assert not adjudicate(b,[],work,catalog,[])[0]
