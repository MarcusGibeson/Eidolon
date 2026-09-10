from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from deliberative_planning_integration import *
from goal_representation import create_goal
checks=[]
def req(v,n):checks.append(n);assert v,n
pu={'workspace_digest':'a'*64,'source_manifest_digest':'b'*64,'manifest_consistent':True};g=create_goal(outcome='small reversible repair',acceptance_criteria=['focused test passes'])
with tempfile.TemporaryDirectory() as td:
 r=build_deliberative_planning_checkpoint(g,pu,decision_context={'risk_level':'low','reversible':True,'blast_radius':2},runtime_root=td)['deliberative_planning'];req(CONTRACT_VERSION=='v1330.8','contract');req(r['candidate_count']==1 and not r['tradeoff_tie'],'small_collapsed');req(r['plan_step_count']==4 and r['efficient_execution_order_preserved'],'ordered_plan');req(r['planning_chain_ready'] and not r['stop_required'],'ready');req(not r['quality_evaluable'],'quality_waits_for_outcome');req(not r['planning_execution_authorized'] and not r['checkpoint_executes_work'],'nonexecuting')
print(json.dumps({'suite':'v1330.0-2-deliberative-planning-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
