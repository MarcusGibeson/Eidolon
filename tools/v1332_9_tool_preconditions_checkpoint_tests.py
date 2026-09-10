import sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1332_tool_preconditions_test_support import fixture
from tool_preconditions import load_tool_preconditions
from release_authority import WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 r=fixture(td);rid=r['tool_preconditions']['precondition_record_id'];p=load_tool_preconditions(rid,runtime_root=td)
 req(bool(p) and p['precondition_record_id']==rid,'sealed_reload')
 rec=next(Path(td).rglob(rid+'.json'));data=json.loads(rec.read_text());data['tool_code']='shell';rec.write_text(json.dumps(data));req(load_tool_preconditions(rid,runtime_root=td)=={},'tamper_rejected')
 req(p['environment_probes_executed'] is False and p['tool_invoked'] is False,'read_only_checkpoint')
 req((WORKING_SOURCE_VERSION!='1332.9') or ('v1333' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
 req(p['approval_granted'] is False and p['independent_authority_granted'] is False,'authority_denied')
print({'ok':True,'suite':'v1332.9-tool-preconditions-checkpoint','passed':passed,'total':5})
