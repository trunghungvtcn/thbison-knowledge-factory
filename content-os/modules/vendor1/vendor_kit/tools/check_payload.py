"""Validate a supplied boundary object. No network or provider calls."""
import argparse, json, sys
from pathlib import Path
from contracts import validate, check_research, check_bundle, check_article
p=argparse.ArgumentParser()
p.add_argument('schema'); p.add_argument('file',type=Path)
p.add_argument('--evidence',type=Path)
a=p.parse_args()
try:
    value=json.loads(a.file.read_text(encoding='utf-8')); validate(a.schema,value)
    if a.schema=='ResearchResult': check_research(value)
    if a.schema=='EvidenceBundle': check_bundle(value)
    if a.schema=='ArticlePackage':
        if a.evidence is None: raise ValueError('--evidence is required for ArticlePackage')
        check_article(value,json.loads(a.evidence.read_text(encoding='utf-8')))
    print(json.dumps({'status':'PAYLOAD_CONFORMANT','schema':a.schema,'scope':'structural/reference integrity; not factual truth or live readiness'}))
except Exception as e:
    print(json.dumps({'status':'FAIL','error':str(e)})); sys.exit(1)
