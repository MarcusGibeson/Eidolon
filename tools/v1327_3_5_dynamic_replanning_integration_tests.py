from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from evidence_dynamic_replanning import replan_from_evidence
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'a'},{'step_code':'b','depends_on':['a'],'mutation_expected':True}],'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:
 r=replan_from_evidence(plan,completed_step_codes=['a'],evidence_change={},runtime_root=td);req(r['status']=='plan_retained' and not r['dynamic_replanning']['route_changed'],'no_change_retained')
 chat=process_ordinary_chat_development_turn('replan from evidence',project_state={'constructed_plan':plan,'completed_planning_steps':['a'],'planning_evidence_change':{'evidence_digests':['new']}},runtime_root=td);req(chat.get('active') and chat.get('status')=='plan_revised','ordinary_route');req(chat['dynamic_replanning']['completed_step_codes']==['a'],'ordinary_preserves');req(not chat.get('planning_execution_authorized'),'no_authority')
print(json.dumps({'suite':'v1327.3-5-dynamic-replanning','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
