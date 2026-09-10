from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from operator_experience_foundations import *
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
def denied(row,prefix):
    for k,v in AUTHORITY_FLAGS.items():req(row.get(k) is v,f'{prefix}_{k}')
base_campaign={'campaign_id':'selfalpha_abc','phase':'prepared','selected_objective_code':'review_known_limitation','selected_strategy_code':'bounded_targeted_investigation','selection_confidence':'high','plan_confidence':'medium','plan_digest':'a'*64,'active_source_modified':False,'selected_test_count':4,'tests_executed':False,'operator_decision':'pending'}
base_session={'session_id':'longwork_abc','state':'running','current_phase':'prepared'}
base_obs={'observability_id':'observability_abc','current_phase':'prepared','event_count_total':2,'failure_count_total':0,'retry_count_total':0,'recovery_count_total':0,'budget_split_count_total':0,'recent_events':[{'event_code':'progress_observed','phase':'prepared','outcome':'observed','elapsed_ms':3,'phase_budget_ms':1000}]}
review={'review_id':'review_abc','changed_file_count':2,'changed_files':[{'relative_path':'a.py','action':'modify'},{'relative_path':'../secret','action':'modify'}],'verification':{'selected_test_count':4,'test_run_count':1,'passed':True,'result_digest':'b'*64},'risks':[{'risk_code':'low_surface','severity':'low'}],'unresolved_uncertainty':[{'uncertainty_code':'windows_native','state':'unresolved','severity':'low'}]}
r=build_operator_experience_projection(campaign=base_campaign,session=base_session,observability=base_obs,review_packet=review);req(validate_operator_experience_projection(r)['ok'],'projection_valid');req(r['section_order']==list(SECTION_ORDER),'section_order');req(r['changes']['changed_file_count']==2,'changed_count');req(len(r['changes']['paths'])==1 and r['changes']['paths'][0]['relative_path']=='a.py','unsafe_path_hidden');req(r['authorization']['code']=='v1265_candidate_exact_authorization','candidate_auth_guidance');req(r['authorization']['exact_authorization_required'],'candidate_exact');req(not r['authorization']['authorization_phrase_exposed'],'phrase_hidden');req(not r['authorization']['generic_go_ahead_sufficient'],'generic_no');req(set(r['controls']['available'])=={'pause','cancel'},'running_controls');req(r['privacy']['content_minimized'],'privacy_min');denied(r,'projection_auth')
for phase,expected in [('repair_authorization_required','v1267_test_repair_exact_authorization'),('operator_review_required','v1268_review_disposition')]:
    c=dict(base_campaign,phase=phase);x=build_operator_experience_projection(campaign=c,session=base_session,observability=base_obs);req(x['authorization']['code']==expected,'auth_'+phase)
paused=build_operator_experience_projection(campaign=base_campaign,session=dict(base_session,state='paused'),observability=base_obs);req(set(paused['controls']['available'])=={'resume','cancel'},'paused_controls')
cancelled=build_operator_experience_projection(campaign=dict(base_campaign,phase='cancelled'),session=dict(base_session,state='cancelled'),observability=base_obs);req(cancelled['authorization']['code']=='none_cancelled','cancelled_no_auth');req(cancelled['controls']['available']==[],'cancelled_controls')
reviewed=build_operator_experience_projection(campaign=dict(base_campaign,phase='review_decided',v1269_consideration_ready=True),session=base_session,observability=base_obs,review_packet=review);req(reviewed['authorization']['code']=='v1269_fresh_preflight_then_exact_update_authorization','update_preflight_guidance')
upd=build_operator_experience_projection(campaign=dict(base_campaign,phase='review_decided'),session=base_session,observability=base_obs,review_packet=review,update={'update_id':'selfupdate_x','phase':'prepared'});req(upd['authorization']['code']=='v1269_exact_update_authorization','update_exact_guidance')
applied=build_operator_experience_projection(campaign=dict(base_campaign,phase='review_decided'),session=base_session,observability=base_obs,update={'update_id':'selfupdate_x','phase':'applied_verified'});req(applied['controls']['rollback_available'],'rollback_visible');req(applied['controls']['rollback_execution_requires_exact_authorization'],'rollback_exact')
tampered=dict(r);tampered['authorization']=dict(r['authorization'],generic_go_ahead_sufficient=True);req(not validate_operator_experience_projection(tampered)['ok'],'tamper_blocked')
print(json.dumps({'ok':True,'suite':'v1279.0-2-operator-experience-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
