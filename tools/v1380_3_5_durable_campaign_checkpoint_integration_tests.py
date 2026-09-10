import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from durable_campaign_checkpoint import *
from campaign_records import build_campaign_record
from crash_safe_campaign_checkpoints import build_step_checkpoint
from dependency_scheduling import build_dependency_schedule
from bounded_parallelism import build_bounded_parallel_plan
from long_task_heartbeats import record_heartbeat
from partial_result_retention import retain_partial_result
from multi_day_continuity import build_continuity_capsule
from conflict_reconciliation import assess_campaign_conflicts,prepare_reconciliation_disposition
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1380_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 c=build_campaign_record(campaign_id='camp',source_manifest_digest=D('s'),workspace_digest=D('w'),standing_grant_digest=D('grant'),standing_session_active=True,goal_digest=D('g'),plan_digest=D('p'),budget_digest=D('b'),current_step_id='step2',total_steps=3,completed_steps=1);cr=c['campaign_record'];req(c['ok'],'campaign');N+=1
 step=build_step_checkpoint(campaign_id='camp',campaign_record_digest=cr['record_digest'],step_id='step1',attempt_id='a1',state='completed',operation_id='op',result_digest=D('result'),result_confirmed=True)['step_checkpoint']
 sched=build_dependency_schedule(campaign_record_digest=cr['record_digest'],tasks=[{'task_id':'a','status':'completed'},{'task_id':'b','depends_on':['a']}])['dependency_schedule']
 par=build_bounded_parallel_plan(campaign_record_digest=cr['record_digest'],tasks=[{'task_id':'read','kind':'read'},{'task_id':'test','kind':'test'}])['parallel_plan']
 hb=record_heartbeat(campaign_record_digest=cr['record_digest'],task_id_digest=D('task'),sequence=1,progress_units=1,total_units=3,observed_at_unix=3600,runtime_root=td)['heartbeat']
 pr=retain_partial_result(campaign_record_digest=cr['record_digest'],task_id_digest=D('task'),artifact_id='partial',artifact_kind='report',artifact_bytes=b'private',remaining_check_codes=['verify'],retention_authorized=True,producer_evidence_digest=D('producer'),runtime_root=td)['partial_result']
 cont=build_continuity_capsule(campaign_id='camp',campaign_record_digest=cr['record_digest'],goal_digest=D('g'),plan_digest=D('p'),budget_digest=D('b'),current_step_digest=D('step2'),source_digest=D('s'),workspace_digest=D('w'),upstream_digest=D('u'),completed_steps=1,total_steps=3,state='paused',last_active_unix=3600)['continuity_capsule']
 cf=assess_campaign_conflicts(campaign_record_digest=cr['record_digest'],candidate_digest=D('candidate'),baseline_source_digest=D('s'),current_source_digest=D('s2'),baseline_workspace_digest=D('w'),current_workspace_digest=D('w2'),expected_upstream_digest=D('u'),current_upstream_digest=D('u'),owner_session_digest=D('owner'),observed_changes=[{'path_digest':D('path'),'change_digest':D('chg'),'origin':'operator','kind':'modified'}])['conflict_assessment']
 rd=prepare_reconciliation_disposition(conflict_assessment=cf,expected_assessment_digest=cf['assessment_digest'],disposition='rebuild_candidate',operator_reviewed=True)['reconciliation']
 k=kwargs();k.update(campaign_record_digest=cr['record_digest'],step_checkpoint_digest=step['checkpoint_digest'],dependency_schedule_digest=sched['record_digest'],parallel_plan_digest=par['record_digest'],heartbeat_digest=hb['record_digest'],partial_result_digest=pr['record_digest'],continuity_capsule_digest=cont['capsule_digest'],resume_assessment_digest=D('resume'),conflict_assessment_digest=cf['assessment_digest'],reconciliation_disposition_digest=rd['disposition_digest'],final_result_digest=D('final'))
 r=build_durable_campaign_checkpoint(**k);x=r['durable_campaign_checkpoint'];req(r['ok'],'checkpoint');N+=1
 v=validate_durable_campaign_checkpoint(x,expected_checkpoint_digest=x['checkpoint_digest']);req(v['ok'] and v['passed']==v['total'],'validate');N+=1
 req(x['operator_change_preserved'] and not x['duplicate_side_effect_replay'],'preserve');N+=1
 q=process_ordinary_chat_development_turn('show durable campaign checkpoint',project_state={'durable_campaign_checkpoint':x});req(q.get('active') and q.get('ok') and not q['action_executed'],'chat');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1380-integration'})
