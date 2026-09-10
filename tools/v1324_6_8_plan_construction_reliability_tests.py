from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_construction import *
from goal_representation import create_goal
from project_evidence_store import evidence_root
checks=[]
def req(v,n):checks.append(n);assert v,n
g=create_goal(outcome='feature');c={'goal_digest':g['goal_digest'],'approach_set_id':'a','workspace_digest':'w','source_manifest_digest':'m','approaches':[{'approach_id':'1','approach_code':'x'},{'approach_id':'2','approach_code':'y'}]}
with tempfile.TemporaryDirectory() as td:
 blocked=build_plan(g,c,tradeoff_evaluation={'tie':True},runtime_root=td);req(not blocked['ok'] and blocked['status']=='tradeoff_tie','tie_blocks_silent_choice')
 try:build_plan(g,c,selected_approach_id='missing',runtime_root=td);ok=False
 except ValueError:ok=True
 req(ok,'unknown_choice_rejected');r=build_plan(g,c,selected_approach_id='1',runtime_root=td)['plan'];p=evidence_root('plan_construction',td)/'records'/f"{r['plan_id']}.json";o=json.loads(p.read_text());o['step_count']=99;p.write_text(json.dumps(o));req(load_plan(r['plan_id'],runtime_root=td)=={},'tamper_rejected')
print(json.dumps({'suite':'v1324.6-8-plan-construction','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
