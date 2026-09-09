from copy import deepcopy
import hashlib
import json
import re

from kf_pilot.v162_remediation.core import digest, require, resolve
from kf_pilot.v16.object_value import normalize_object_value
from kf_pilot.v16.condition_ast import canonicalize_ast, contains_unresolved
from .sources import find_spans, verify_span

DECISIONS={'ACCEPT','REJECT','HOLD','NEEDS_MORE_EVIDENCE'}


def review_work(ledger,queue,versions,reviews,catalog):
    issues=ledger['issues']
    require(len({r['issue_id'] for r in issues})==len(issues),'duplicate issue')
    expected={r['issue_id']:r for r in issues if r['resolution_status']!='RESOLVED'}
    require(len(queue)==len(expected) and {r['issue_id']:r for r in queue}==expected,'missing/duplicate queue issues')
    by_entity={v['claim_entity_id']:v for v in versions}
    work=[]; spans={}
    for iid,issue in sorted(expected.items()):
        v=by_entity[issue['entity_id']]; p=v['semantic_payload']
        require(v['claim_version_id']==issue['version_id'],'issue version mismatch')
        props=reviews.get(issue['page_id'],{}).get('properties',{})
        source_ref=props.get('Source URL');source=catalog.get(source_ref)
        quote=(p.get('condition_ast') or {}).get('raw_text','') if issue['issue_type']=='CONDITION_CONNECTIVE_AMBIGUOUS' else p['object_value'].get('value','')
        found=find_spans(source,quote) if source else []
        for span in found:
            verify_span(span,catalog);spans[digest(span)]=span
        work.append(dict(issue_id=iid,issue_type=issue['issue_type'],record_id=issue['entity_id'],
            version_id=issue['version_id'],page_id=issue['page_id'],predicate=p['predicate'],
            applicability={'scope':p['applicability'],'jurisdiction':p.get('jurisdiction'),
                'condition_ast':json.dumps(p.get('condition_ast',{'op':'TRUE'}),sort_keys=True,separators=(',',':')),
                'exception_ast':json.dumps(p.get('exception_ast',{'op':'FALSE'}),sort_keys=True,separators=(',',':'))},source_issue=deepcopy(issue),
            source_ref=source_ref,source_status='SOURCE_AVAILABLE' if source else 'SOURCE_UNAVAILABLE',
            span_status='EXACT_SPAN_FOUND' if found else 'NEEDS_MORE_EVIDENCE',span_ids=sorted(digest(s) for s in found),
            required_adjudication=True,status='NEEDS_MORE_EVIDENCE' if not found else 'AWAITING_REVIEW'))
    return work,dict(sorted(spans.items()))


def literal_interpretation(text):
    """Full literals only. Never infer a scalar from compound prose or punctuation."""
    q=' '.join(text.split())
    if re.fullmatch(r'-?\d+(?:\.\d+)? [A-Za-z]+',q):
        n,u=q.split(' ')
        try: normalize_object_value({'type':'quantity','amount':n,'unit':u})
        except ValueError:return None
        return {'kind':'quantity','value':n,'unit':u}
    if q in ('true','false'):return {'kind':'boolean','value':q=='true'}
    try:
        v=json.loads(q)
        if isinstance(v,dict) and v.get('op'):
            ast=canonicalize_ast(v)
            return None if contains_unresolved(ast) else {'kind':'condition_ast','ast':ast}
        normalized,issues=normalize_object_value(v)
        if issues:return None
        return {'kind':'structured','value':v}
    except (ValueError,TypeError,KeyError):return None


def proposals(work,spans):
    candidates=[]
    for item in work:
        # Multiple occurrences are presented for reviewer disambiguation, not silently selected.
        if len(item['span_ids'])!=1:continue
        span=spans[item['span_ids'][0]]
        interp=propose_interpretation(span['exact_quote'],item['predicate'])
        if not interp:continue
        if (item['issue_type']=='CONDITION_CONNECTIVE_AMBIGUOUS')!=(interp['kind']=='condition_ast'):continue
        candidate={k:item[k] for k in ('issue_id','issue_type','record_id','version_id','predicate','applicability')}
        candidate.update(source=deepcopy(span),interpretation=interp)
        candidate['binding_id']=digest(candidate)
        candidates.append(candidate)
    return sorted(candidates,key=lambda r:r['issue_id'])


def propose_interpretation(text,predicate):
    """Proposals are not approvals. Extract only an explicit interval or unqualified prohibition.

    Full source quote and applicability stay bound; a separate condition issue stays open.
    The unchanged V16.2 bridge may still reject prose-to-scalar conversion.
    """
    exact=literal_interpretation(text)
    if exact:return exact
    q=' '.join(text.split())
    if predicate=='inspection_interval':
        matches=re.findall(r'[Tt]hời hạn kiểm định định kỳ (\d+) năm',q)
        if len(matches)==1:return {'kind':'quantity','value':matches[0],'unit':'year'}
    prohibitions={
        ('overload_prohibition','Capacity must not be exceeded.'),
        ('overload_prohibition','Do not exceed a hoist load limit.'),
        ('people_lifting_prohibition','Do not use hoisting equipment for lifting or moving people.')}
    if (predicate,q) in prohibitions:return {'kind':'boolean','value':True}
    return None


def adjudicate(bindings,adjudications,work,catalog,trusted_reviewers):
    """Only independently supplied trusted human decisions can become ACCEPT.

    The binding hash covers source, interpretation and applicability. Neither a model
    proposal nor a fabricated review row can implicitly approve a binding.
    """
    by_issue={r['issue_id']:r for r in work}
    require(len({b['issue_id'] for b in bindings})==len(bindings),'duplicate binding')
    require(len({a['binding_id'] for a in adjudications})==len(adjudications),'duplicate adjudication')
    require({a['binding_id'] for a in adjudications}<={b['binding_id'] for b in bindings},'unmatched adjudication')
    decisions={a['binding_id']:a for a in adjudications};accepted=[];rejected=[];evidence={}
    for b in sorted(bindings,key=lambda r:r['issue_id']):
        require(b['issue_id'] in by_issue,'issue identity mismatch')
        item=by_issue[b['issue_id']]
        require(b['binding_id']==digest({k:v for k,v in b.items() if k!='binding_id'}),'binding hash mismatch')
        for k in ('issue_type','record_id','version_id','predicate','applicability'):
            require(b[k]==item[k] and b[k] is not None,'binding identity/scope mismatch')
        require(b['source']['source_ref']==item['source_ref'],'source reference mismatch')
        verify_span(b['source'],catalog)
        interp=propose_interpretation(b['source']['exact_quote'],item['predicate'])
        require(interp is not None and interp==b['interpretation'],'unsupported/ambiguous typed interpretation')
        if interp['kind']=='structured' and interp['value'].get('type')=='enum':
            # The existing binding schema has no hashed vocabulary version/locator contract.
            # Do not equate an arbitrary enum string to a controlled vocabulary.
            raise ValueError('controlled vocabulary proof required; enum binding unsupported until supplied')
        require((item['issue_type']=='CONDITION_CONNECTIVE_AMBIGUOUS')==(interp['kind']=='condition_ast'),'interpretation type mismatch')
        a=decisions.get(b['binding_id'])
        if a is None:
            rejected.append(dict(binding=b,reason='AWAITING_HUMAN_ADJUDICATION'));continue
        require(a.get('decision') in DECISIONS,'invalid adjudication')
        require(a.get('issue_id')==b['issue_id'],'adjudication mismatch')
        require(a.get('reviewer_id') in trusted_reviewers and a.get('reviewed_at') and a.get('rationale'),'untrusted/missing reviewer')
        if a['decision']!='ACCEPT':
            rejected.append(dict(binding=b,review=a,reason=a['decision']));continue
        source=b['source'];literal=' '.join(source['exact_quote'].split())
        ev=dict(entity_id=b['record_id'],version_id=b['version_id'],
            field='condition_ast' if interp['kind']=='condition_ast' else 'object_value',
            ref=source['source_ref']+'#'+source['locator'],content=literal,literal=literal,
            content_sha256=hashlib.sha256(literal.encode()).hexdigest(),scope_verified=True,authoritative=True,
            original_source_sha256=source['content_sha256'],binding_id=b['binding_id'])
        require(resolve(item['source_issue'],ev) is not None,'V162_CONTRACT_INCOMPATIBLE: no bypass allowed')
        accepted.append(dict(b,review={k:a[k] for k in ('decision','reviewer_id','reviewed_at','rationale')}))
        evidence[b['issue_id']]=ev
    return accepted,rejected,evidence
