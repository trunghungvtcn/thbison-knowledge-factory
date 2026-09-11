import copy, json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from contracts import validate,check_research,check_bundle,check_article,gate_publish,hash_without,ContractError,ReferenceLedger

def load(n): return json.loads((ROOT/'contracts/examples'/f'{n}.json').read_text(encoding='utf-8'))
def rehash(e,a=None):
    e['snapshot_sha256']=hash_without(e,'snapshot_sha256')
    if a:
        a['evidence_snapshot_sha256']=e['snapshot_sha256'];a['content_sha256']=hash_without(a,'content_sha256')

def reseal(a): a['content_sha256']=hash_without(a,'content_sha256')

@pytest.mark.parametrize('name',sorted(p.stem for p in (ROOT/'contracts/examples').glob('*.json')))
def test_example_schemas(name): validate(name,load(name))

def test_happy_article(): check_article(load('ArticlePackage'),load('EvidenceBundle'))

def test_research_missing_must_be_null():
    r=load('ResearchResult');r['keywords'][0]['measurement_status']='MISSING'
    with pytest.raises(ContractError,match='MISSING_METRIC_NOT_NULL'):check_research(r)

def test_missing_not_zero():
    r=load('ResearchResult');r['keywords'][0].update(measurement_status='MISSING',volume=None,difficulty=None)
    check_research(r)

def test_synthetic_cannot_masquerade_as_measured():
    r=load('ResearchResult');r['data_class']='PRODUCTION'
    with pytest.raises(ContractError,match='SYNTHETIC_IN_REAL_DATA'):check_research(r)

def test_unknown_contract():
    b=load('ContentBrief');b['contract_version']='2.0.0'
    with pytest.raises(ContractError):validate('ContentBrief',b)

def test_extra_fields_rejected():
    b=load('ContentBrief');b['auto_approve']=True
    with pytest.raises(ContractError):validate('ContentBrief',b)

def test_naive_date_rejected():
    b=load('ContentBrief');b['proposed_publish_at']='2030-01-01T00:00:00'
    with pytest.raises(ContractError):validate('ContentBrief',b)

def test_unicode_vietnamese_preserved():
    b=load('ContentBrief');before=b['primary_keyword'];validate('ContentBrief',b)
    assert b['primary_keyword']==before and '\u0103' in before

def test_bad_unicode_rejected():
    b=load('ContentBrief');b['title']='bad\ud800'
    with pytest.raises(ContractError,match='INVALID_UNICODE'):validate('ContentBrief',b)

def test_input_hash_changed():
    e=load('EvidenceBundle');e['as_of']='2030-01-01T00:01:00Z'
    with pytest.raises(ContractError,match='EVIDENCE_HASH_MISMATCH'):check_bundle(e)

def test_quote_tampering():
    e=load('EvidenceBundle');e['claims'][0]['quote']='changed';rehash(e)
    with pytest.raises(ContractError,match='QUOTE_HASH_MISMATCH'):check_bundle(e)

def test_duplicate_claim():
    e=load('EvidenceBundle');e['claims'].append(copy.deepcopy(e['claims'][0]));rehash(e)
    with pytest.raises(ContractError,match='DUPLICATE_CLAIM_ID'):check_bundle(e)

def test_hold_with_permission_rejected():
    e=load('EvidenceBundle');e['claims'][0]['status']='HOLD';rehash(e)
    with pytest.raises(ContractError,match='INELIGIBLE_CLAIM_HAS_USE'):check_bundle(e)

@pytest.mark.parametrize('mutation,error',[
    ('project','PROJECT_MISMATCH'),('snapshot','SNAPSHOT_MISMATCH'),('hash','CONTENT_HASH_MISMATCH'),
    ('unknown','UNKNOWN_CLAIM'),('missing','FACT_WITHOUT_CITATION'),('duplicate','DUPLICATE_BLOCK_ID'),
    ('blocker','BLOCKER_NOT_VISIBLE')])
def test_article_negative(mutation,error):
    a,e=load('ArticlePackage'),load('EvidenceBundle')
    if mutation=='project':a['project_id']='other'
    if mutation=='snapshot':a['evidence_snapshot_sha256']='f'*64
    if mutation=='hash':a['title']='edited'
    if mutation=='unknown':a['blocks'][0]['claim_ids']=['fake-claim']
    if mutation=='missing':a['blocks'][0]['claim_ids']=[]
    if mutation=='duplicate':a['blocks'].append(copy.deepcopy(a['blocks'][0]))
    if mutation=='blocker':a['publication_blockers']=['source-expired']
    if mutation!='hash':reseal(a)
    with pytest.raises(ContractError,match=error):check_article(a,e)

def publish_inputs():
    a,e,r,p=[load(x) for x in ['ArticlePackage','EvidenceBundle','PublishRequest','ApprovalRecord']]
    kwargs={'principal':{'project_id':a['project_id'],'can_publish':True},'policy':{'version':a['policy_version'],'allow_live':False},'now':'2030-01-01T00:01:00Z'}
    return a,e,r,p,kwargs

def test_publish_dryrun():
    a,e,r,p,k=publish_inputs();assert gate_publish(a,e,r,p,**k)=='DRY_RUN'

@pytest.mark.parametrize('mutation,error',[
    ('no_role','FORBIDDEN'),('expired','APPROVAL_EXPIRED'),('revoked','APPROVAL_NOT_ACTIVE'),
    ('revision','STALE_APPROVAL'),('destination','WRONG_DESTINATION'),('policy','POLICY_MISMATCH'),
    ('live_test','TEST_DATA_NOT_PUBLISHABLE'),('staging_test','TEST_DATA_NOT_PUBLISHABLE'),('not_due','NOT_DUE')])
def test_publish_negative(mutation,error):
    a,e,r,p,k=publish_inputs()
    if mutation=='no_role':k['principal']['can_publish']=False
    if mutation=='expired':k['now']='2030-01-03T00:00:00Z'
    if mutation=='revoked':p['decision']='REVOKED'
    if mutation=='revision':p['article_revision']=2
    if mutation=='destination':r['destination_id']='other-cms'
    if mutation=='policy':k['policy']['version']='other-policy'
    if mutation=='live_test':r['mode']='LIVE'
    if mutation=='staging_test':r['mode']='STAGING_DRAFT'
    if mutation=='not_due':r['scheduled_at']='2030-01-01T00:02:00Z'
    with pytest.raises(ContractError,match=error):gate_publish(a,e,r,p,**k)

def test_edited_body_invalidates_approval():
    a,e,r,p,k=publish_inputs();a['blocks'][0]['text']+=' Additional editorial text.';reseal(a);r['content_sha256']=a['content_sha256']
    with pytest.raises(ContractError,match='STALE_APPROVAL'):gate_publish(a,e,r,p,**k)

def test_authoritative_new_evidence_invalidates_approval():
    a,e,r,p,k=publish_inputs();e['policy_version']='new-policy';rehash(e)
    with pytest.raises(ContractError):gate_publish(a,e,r,p,**k)

def test_hold_not_used_in_draft():
    a,e=load('ArticlePackage'),load('EvidenceBundle');e['claims'][0].update(status='HOLD',allowed_uses=[]);rehash(e,a)
    with pytest.raises(ContractError,match='CLAIM_NOT_DRAFTABLE'):check_article(a,e)

def test_idempotency_same_returns_same():
    l=ReferenceLedger();a=l.admit('p','op','k',{'x':1});b=l.admit('p','op','k',{'x':1})
    assert a[0]==b[0] and a[1] and not b[1]

def test_idempotency_conflict():
    l=ReferenceLedger();l.admit('p','op','k',{'x':1})
    with pytest.raises(ContractError,match='IDEMPOTENCY_CONFLICT'):l.admit('p','op','k',{'x':2})

def test_idempotency_tenant_isolation():
    l=ReferenceLedger();a=l.admit('p1','op','k',{});b=l.admit('p2','op','k',{})
    assert a[0]!=b[0] and a[1] and b[1]

def test_openapi_has_only_resolvable_local_refs():
    spec=json.loads((ROOT/'contracts/openapi.json').read_text())
    def walk(v):
        if isinstance(v,dict):
            if '$ref' in v:
                target=spec
                for part in v['$ref'].removeprefix('#/').split('/'):target=target[part]
            for value in v.values():walk(value)
        elif isinstance(v,list):
            for value in v:walk(value)
    walk(spec)
