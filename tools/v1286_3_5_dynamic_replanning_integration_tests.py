from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from hierarchical_goal_management_foundations import *
from dynamic_replanning import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
i=hashlib.sha256(b'intent').hexdigest();h=build_goal_hierarchy(objective_code='x',original_intent_digest=i,milestone_codes=['inspect','implement','verify']);m=h['milestones'][0];p={'milestones':[{'milestone_code':'inspect','complete':True},{'milestone_code':'implement','complete':False},{'milestone_code':'verify','complete':False}]};e=build_replanning_event(event_kind='interruption',event_code='restart');r=replan_from_goal_progress(hierarchy=h,progress=p,event=e);req(r['completed_milestone_codes']==['inspect'],'progress_bridge');req(r['revised_milestones'][0]['preserved_completed_work'],'completed_preserved');u={'epistemic_state':'suspended','confidence':10,'evidence_codes':['contradiction']};rr=replan_with_uncertainty(hierarchy=h,progress=p,uncertainty_claim=u);req(rr['event_kind']=='failed_assumption','uncertainty_bridge');req(rr['uncertainty_does_not_grant_execution_authority'],'uncertainty_non_authorizing');s=public_replan_summary(rr);req(s['ok'] and s['completed_preserved']==1,'summary');req(not s['raw_event_content_exposed'] and not s['execution_started'],'privacy');print(json.dumps({'ok':True,'suite':'v1286.3-5-dynamic-replanning-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
