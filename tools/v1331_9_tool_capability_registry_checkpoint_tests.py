from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from tool_capability_registry import *
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:r=build_tool_capability_registry(runtime_root=td)['tool_capability_registry'];req(r['capability_count']==9 and r['schemas_declared'],'checkpoint');req(not r['registry_is_authority'] and not r['planning_execution_authorized'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1331,9),'metadata');req(any(v=='1331.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1331.9') or ('v1332' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1331.9-tool-capability-registry-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
