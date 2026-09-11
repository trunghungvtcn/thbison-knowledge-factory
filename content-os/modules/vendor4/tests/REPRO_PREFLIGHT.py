from app.staging_preflight import run_preflight
import json
class T:
    def request(self,*args,**kwargs):
        return {"status":200,"body":{"results":[{"id":"row","properties":{"Evidence Sources":{"type":"relation","relation":[{"id":"production-evidence-page"}]}}}],"has_more":False}}
r=run_preflight(transport=T(),live=False)
print(json.dumps({"status":r["status"],"parents_verified":[x["relation_parent_verified"] for x in r["databases"]],"requests":r["requests_attempted"]}))

