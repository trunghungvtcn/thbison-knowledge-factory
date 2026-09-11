import sys,json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root/'src'))
from thbison_v6.harness.lab import Lab
chain=Lab().run_reference_chain(); report={}
for key,name in [('brief','ContentBrief'),('bundle','EvidenceBundle'),('article','ArticlePackage'),('approval','ApprovalRecord'),('receipt','PublicationReceipt')]:
 p=next(p for p in root.rglob(name+'.json') if p.parent.name=='schemas')
 errors=list(Draft202012Validator(json.loads(p.read_text())).iter_errors(chain[key]))
 report[name]={'errors':len(errors),'details':[{'path':list(e.absolute_path),'message':e.message} for e in errors]}
print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(int(any(v['errors'] for v in report.values())))
