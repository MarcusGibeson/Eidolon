from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'implement_change','mutation_expected':True}],'checkpoint_count':0,'verification_step_count':0,'rollback_step_count':0,'acceptance_criterion_count':0,'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:
 r=process_ordinary_chat_development_turn('show plan critique',project_state={'plan':plan,'goal':{'goal_digest':'g','acceptance_criteria_digests':['a']},'impact_analysis':{'analysis_id':'i','affected_path_count':12,'candidate_test_count':2,'protected_authority_surface_predicted':True}},runtime_root=td);req(r.get('active') and r.get('ok'),'ordinary_route');c=r['plan_critique'];req(c['blocking_count']>=3 and not c['plan_acceptable_for_next_planning_stage'],'findings_block');req({x['category'] for x in c['findings']}>= {'missing_requirements','unsafe_authority','weak_verification'},'categories_found')
print(json.dumps({'suite':'v1325.3-5-plan-critique','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
