"""Validate a cross-vendor artifact replay, not a live end-to-end integration."""
import argparse, json
from pathlib import Path
from contracts import validate,check_research,check_bundle,check_article,require
p=argparse.ArgumentParser()
p.add_argument('--planning-dir',type=Path,required=True)
p.add_argument('--content-dir',type=Path,required=True)
p.add_argument('--evidence',type=Path,required=True)
a=p.parse_args()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
r=read(a.planning_dir/'ResearchResult.json'); b=read(a.planning_dir/'ContentBrief.json')
e=read(a.evidence); article=read(a.content_dir/'ArticlePackage.json')
check_research(r);validate('ContentBrief',b);check_bundle(e);check_article(article,e)
require(r['project_id']==b['project_id']==article['project_id'],'PROJECT_MISMATCH')
require(r['data_class']==b['data_class']==article['data_class'],'DATA_CLASS_MISMATCH')
require(b['research_id']==r['research_id'] and b['scope']==r['scope'],'RESEARCH_SCOPE_MISMATCH')
require(article['brief_id']==b['brief_id'] and article['brief_revision']==b['brief_revision'],'BRIEF_MISMATCH')
print(json.dumps({'status':'ARTIFACT_REPLAY_PASS','live_provider_tested':False,'semantic_truth_verified':False,'project_id':b['project_id'],'brief_id':b['brief_id'],'article_id':article['article_id']}))
