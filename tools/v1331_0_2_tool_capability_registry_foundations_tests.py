from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from tool_capability_registry import *
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 r=build_tool_capability_registry(runtime_root=td)['tool_capability_registry'];req(CONTRACT_VERSION=='v1331.8','contract');req(tuple(r['tool_classes'])==TOOL_CLASSES and r['capability_count']==9,'classes');req(all(x['schema'] and x['schema_digest'] for x in r['capabilities']),'schemas');req(any(x['side_effect_codes'] for x in r['capabilities']),'side_effects');req(not r['availability_probes_executed'] and not r['tools_invoked'],'no_probe')
print(json.dumps({'suite':'v1331.0-2-tool-capability-registry','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
