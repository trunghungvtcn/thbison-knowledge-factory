"""Reference boundary validators, NOT a production auth/publishing implementation."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'contracts' / 'schemas'
BASE = 'https://contracts.invalid/thbison/1.0.0/'
REGISTRY = Registry().with_resources((BASE+p.name, Resource.from_contents(json.loads(p.read_text(encoding='utf-8')))) for p in SCHEMAS.glob('*.json'))

class ContractError(ValueError):
    def __init__(self, code: str):
        self.code=code
        super().__init__(code)

def require(ok: bool, code: str) -> None:
    if not ok: raise ContractError(code)

def canonical_bytes(value: Any) -> bytes:
    # Restricted profile: ASCII schema keys, no floats in hashed content objects.
    return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def hash_without(value: dict, field: str) -> str:
    return digest({k:v for k,v in value.items() if k != field})

def no_invalid_unicode(value: Any) -> None:
    if isinstance(value,str):
        require(not any(0xD800<=ord(c)<=0xDFFF for c in value),'INVALID_UNICODE')
    elif isinstance(value,dict):
        for k,v in value.items(): no_invalid_unicode(k); no_invalid_unicode(v)
    elif isinstance(value,list):
        for v in value: no_invalid_unicode(v)

def validate(name: str, value: dict) -> None:
    no_invalid_unicode(value)
    # Internal assembly fix: preserve schema pin; enforce the documented aware-UTC boundary.
    if name == 'ContentBrief' and isinstance(value, dict):
        proposed = value.get('proposed_publish_at')
        if isinstance(proposed, str):
            try:
                instant(proposed)
            except ContractError:
                raise
            except ValueError:
                raise ContractError('SCHEMA_INVALID:ContentBrief')
    schema=json.loads((SCHEMAS/(name+'.json')).read_text(encoding='utf-8'))
    schema['$id']=BASE+name+'.json'
    errors=list(Draft202012Validator(schema,registry=REGISTRY,format_checker=FormatChecker()).iter_errors(value))
    require(not errors, 'SCHEMA_INVALID:'+name)

def instant(value: str) -> datetime:
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(d.tzinfo is not None,'TIMEZONE_REQUIRED')
    return d.astimezone(timezone.utc)

def check_research(result: dict) -> None:
    validate('ResearchResult',result)
    for k in result['keywords']:
        if k['measurement_status']=='MISSING':
            require(k['volume'] is None and k['difficulty'] is None,'MISSING_METRIC_NOT_NULL')
        if k['measurement_status']=='SYNTHETIC':
            require(result['data_class']=='TEST_ONLY','SYNTHETIC_IN_REAL_DATA')

def check_bundle(bundle: dict) -> None:
    validate('EvidenceBundle',bundle)
    require(bundle['snapshot_sha256']==hash_without(bundle,'snapshot_sha256'),'EVIDENCE_HASH_MISMATCH')
    seen=set()
    for c in bundle['claims']:
        require(c['claim_id'] not in seen,'DUPLICATE_CLAIM_ID'); seen.add(c['claim_id'])
        require(hashlib.sha256(c['quote'].encode('utf-8')).hexdigest()==c['quote_sha256'],'QUOTE_HASH_MISMATCH')
        require(c['status']=='ELIGIBLE' or not c['allowed_uses'],'INELIGIBLE_CLAIM_HAS_USE')

def check_article(article: dict, bundle: dict) -> None:
    validate('ArticlePackage',article); check_bundle(bundle)
    require(article['project_id']==bundle['project_id'],'PROJECT_MISMATCH')
    require(article['data_class']==bundle['data_class'],'DATA_CLASS_MISMATCH')
    require(article['bundle_id']==bundle['bundle_id'],'BUNDLE_MISMATCH')
    require(article['evidence_snapshot_sha256']==bundle['snapshot_sha256'],'SNAPSHOT_MISMATCH')
    require(article['policy_version']==bundle['policy_version'],'POLICY_MISMATCH')
    require(article['content_sha256']==hash_without(article,'content_sha256'),'CONTENT_HASH_MISMATCH')
    claims={c['claim_id']:c for c in bundle['claims']}
    seen=set()
    for b in article['blocks']:
        require(b['block_id'] not in seen,'DUPLICATE_BLOCK_ID'); seen.add(b['block_id'])
        if b['kind']=='FACTUAL': require(bool(b['claim_ids']),'FACT_WITHOUT_CITATION')
        for cid in b['claim_ids']:
            require(cid in claims,'UNKNOWN_CLAIM')
            c=claims[cid]
            require(c['status']=='ELIGIBLE' and 'DRAFT' in c['allowed_uses'],'CLAIM_NOT_DRAFTABLE')
    # This only checks referential integrity, not whether prose entails a source.
    if article['unresolved_claim_ids'] or article['publication_blockers']:
        require(article['status']=='REVIEW_REQUIRED','BLOCKER_NOT_VISIBLE')

def gate_publish(article: dict, bundle: dict, request: dict, approval: dict,
                 *, principal: dict, policy: dict, now: str) -> str:
    """Pure oracle. principal/approval/policy MUST come from trusted server state."""
    validate('PublishRequest',request); validate('ApprovalRecord',approval)
    check_article(article,bundle)
    require(principal.get('project_id')==article['project_id'],'FORBIDDEN')
    require(principal.get('can_publish') is True,'FORBIDDEN')
    require(request['project_id']==article['project_id']==approval['project_id'],'PROJECT_MISMATCH')
    require(request['data_class']==article['data_class']==approval['data_class'],'DATA_CLASS_MISMATCH')
    for field in ['article_id','article_revision','content_sha256','evidence_snapshot_sha256']:
        require(request[field]==article[field]==approval[field],'STALE_APPROVAL')
    require(request['approval_id']==approval['approval_id'],'WRONG_APPROVAL')
    require(request['destination_id']==approval['destination_id'],'WRONG_DESTINATION')
    require(approval['policy_version']==article['policy_version']==policy.get('version'),'POLICY_MISMATCH')
    require(approval['decision']=='APPROVED','APPROVAL_NOT_ACTIVE')
    t=instant(now)
    require(instant(approval['approved_at'])<=t<instant(approval['expires_at']),'APPROVAL_EXPIRED')
    require(not article['publication_blockers'] and not article['unresolved_claim_ids'],'PUBLICATION_BLOCKED')
    require(article['status']=='PREVIEW_READY','ARTICLE_NOT_READY')
    if request['scheduled_at'] is not None: require(instant(request['scheduled_at'])<=t,'NOT_DUE')
    # Pilot excludes safety/legal publication, even if a loose external policy marks them eligible.
    used={cid for b in article['blocks'] for cid in b['claim_ids']}
    for c in bundle['claims']:
        if c['claim_id'] in used:
            require('PUBLISH' in c['allowed_uses'],'CLAIM_NOT_PUBLISHABLE')
            require(c['risk'] not in ['SAFETY','LEGAL'],'RISK_OUT_OF_PILOT_SCOPE')
    if request['mode']=='DRY_RUN': return 'DRY_RUN'
    if request['mode']=='LIVE':
        require(article['data_class']=='PRODUCTION','TEST_DATA_NOT_PUBLISHABLE')
        require(policy.get('allow_live') is True,'LIVE_DISABLED')
    if request['mode']=='STAGING_DRAFT':
        require(article['data_class']=='STAGING','TEST_DATA_NOT_PUBLISHABLE')
        require(policy.get('allow_staging') is True,'STAGING_DISABLED')
    return 'AUTHORIZED'

class ReferenceLedger:
    """In-memory semantics demo ONLY. Vendor MUST implement transactional durable storage."""
    def __init__(self): self.rows={}
    def admit(self, project: str, operation: str, key: str, payload: dict):
        k=(project,operation,key); h=digest(payload)
        if k in self.rows:
            old=self.rows[k]; require(old['hash']==h,'IDEMPOTENCY_CONFLICT')
            return old['id'],False
        jid='demo-job-'+str(len(self.rows)+1)
        self.rows[k]={'hash':h,'id':jid}; return jid,True
