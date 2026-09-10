from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from tool_capability_registry import *
from project_evidence_store import atomic_json,evidence_root
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 r=build_tool_capability_registry(availability_evidence={'shell':{'available':True}},runtime_root=td)['tool_capability_registry'];shell=next(x for x in r['capabilities'] if x['tool_code']=='shell');req(shell['availability_state']=='declared_not_probed','claim_requires_evidence')
 req(not inspect_tool_capability(r,'unknown')['ok'],'unknown_closed')
 raw=load_tool_capability_registry(r['registry_id'],runtime_root=td,include_private=True);raw['tools_invoked']=True;atomic_json(evidence_root('tool_capability_registry',td)/'records'/f"{r['registry_id']}.json",raw);req(load_tool_capability_registry(r['registry_id'],runtime_root=td)=={},'tamper_rejected');req(not r['planning_execution_authorized'],'registry_not_authority')
print(json.dumps({'suite':'v1331.6-8-tool-capability-registry','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
