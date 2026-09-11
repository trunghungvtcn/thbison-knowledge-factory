"""A fixture replay, never a claim of a working vendor app or live integration."""
import json
from pathlib import Path
from contracts import ROOT, validate,check_research,check_bundle,check_article,gate_publish,ReferenceLedger

def load(n): return json.loads((ROOT/'contracts/examples'/f'{n}.json').read_text(encoding='utf-8'))
r,b,e,a,p,ap=[load(x) for x in ['ResearchResult','ContentBrief','EvidenceBundle','ArticlePackage','PublishRequest','ApprovalRecord']]
check_research(r);validate('ContentBrief',b);check_bundle(e);check_article(a,e)
assert b['research_id']==r['research_id'] and a['brief_id']==b['brief_id']
ledger=ReferenceLedger(); first=ledger.admit(a['project_id'],'publish','test-key-00000001',p); second=ledger.admit(a['project_id'],'publish','test-key-00000001',p)
assert first[1] and not second[1] and first[0]==second[0]
result=gate_publish(a,e,p,ap,principal={'project_id':a['project_id'],'can_publish':True},policy={'version':a['policy_version'],'allow_live':False},now='2030-01-01T00:01:00Z')
print(json.dumps({'status':'REFERENCE_DEMO_PASS','vendor_apps_tested':False,'live_providers_tested':False,'trace':['research','brief','evidence','article','approval','publish_dry_run','duplicate_suppressed'],'publication_mode':result,'actual_provider_calls':0,'actual_posts_created':0},indent=2))
