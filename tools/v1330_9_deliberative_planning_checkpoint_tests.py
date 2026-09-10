from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from deliberative_planning_integration import *
from goal_representation import create_goal
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
pu={'workspace_digest':'a'*64,'source_manifest_digest':'b'*64,'manifest_consistent':True};g=create_goal(outcome='small repair',acceptance_criteria=['pass'])
with tempfile.TemporaryDirectory() as td:r=build_deliberative_planning_checkpoint(g,pu,decision_context={'risk_level':'low','reversible':True},runtime_root=td)['deliberative_planning'];req(r['planning_chain_ready'] and r['faithful_stop_behavior'],'checkpoint');req(not r['planning_execution_authorized'] and not r['action_executed'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1330,9),'metadata');req(any(v=='1330.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1330.9') or ('v1331' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1330.9-deliberative-planning-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
