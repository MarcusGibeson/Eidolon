from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_construction import *
from goal_representation import create_goal
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n):checks.append(n);assert v,n
g=create_goal(outcome='feature');c={'goal_digest':g['goal_digest'],'approach_set_id':'a','workspace_digest':'w','source_manifest_digest':'m','approaches':[{'approach_id':'1','approach_code':'minimal_targeted_change'},{'approach_id':'2','approach_code':'boundary_refactor'}]};t={'evaluation_id':'e','tie':False,'recommended_approach_id':'1'}
with tempfile.TemporaryDirectory() as td:
 r=process_ordinary_chat_development_turn('show plan construction',project_state={'planning_goal':g,'candidate_approaches':c,'tradeoff_evaluation':t},runtime_root=td);req(r.get('active') and r.get('ok'),'ordinary_route');p=r['plan'];req(p['selected_approach_id']=='1' and p['selection_source']=='tradeoff_recommendation','tradeoff_selected_for_plan');req(load_plan(p['plan_id'],runtime_root=td).get('step_count')==4,'durable')
print(json.dumps({'suite':'v1324.3-5-plan-construction','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
