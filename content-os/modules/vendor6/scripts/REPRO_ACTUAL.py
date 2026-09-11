import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()/'src'))
from thbison_v6.harness.lab import Lab
from thbison_v6.adapters.registry import AdapterRegistry,HOPS
class Trap:
 def __getattr__(self,name):
  raise RuntimeError('ACTUAL_ADAPTER_WAS_CALLED:'+name)
r=AdapterRegistry('ACTUAL_COMPONENTS')
for hop in HOPS:r.bind(hop,'ACTUAL',Trap(),'probe')
l=Lab(mode='ACTUAL_COMPONENTS',registry=r)
result=l.run_reference_chain()
print(json.dumps({'unexpected_success':True,'reason':'No registered adapter called; trap never raised','trace':result['trace']},indent=2))
sys.exit(1)
