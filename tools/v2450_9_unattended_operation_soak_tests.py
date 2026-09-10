from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2450-data-')
from unattended_operation_v2400 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
D='a'*64
policy=build_unattended_policy(policy_id='p1',source_digest=D,allowed_activities=['health_inspection','queue_inspection','isolated_development_preparation'])
req(policy['ok'] and policy['read_only_or_isolated_preparation_only'],'policy_bounded_to_safe_preparation')
req(not build_unattended_policy(policy_id='bad',source_digest=D,allowed_activities=['delete_everything'])['ok'],'unsafe_activity_rejected')
req(not build_unattended_policy(policy_id='bad2',source_digest=D,allowed_activities=['health_inspection'],max_cpu_percent=float('nan'))['ok'],'nonfinite_budget_rejected')
elig=evaluate_unattended_tick(policy=policy,current_source_digest=D,cpu_percent=10,memory_percent=20,queue_depth=1,failure_streak=0,foreground_active=False,quiet_hours_active=False,provider_available=True,operator_paused=False)
req(elig['ok'] and elig['status']=='unattended_tick_preparation_eligible','healthy_tick_eligible')
req(elig['maximum_prepared_tickets']==2 and not elig['job_executed'],'ticket_budget_without_execution')
req(elig['operating_mode']=='active' and not elig['automatic_pause'],'healthy_tick_active_mode')
recovered=evaluate_unattended_tick(policy=policy,current_source_digest=D,cpu_percent=10,memory_percent=20,queue_depth=1,failure_streak=0,foreground_active=False,quiet_hours_active=False,provider_available=True,operator_paused=False,prior_mode='paused')
req(recovered['automatic_recovery'] and recovered['operating_mode']=='active','bounded_automatic_recovery')
alert=evaluate_unattended_tick(policy=policy,current_source_digest=D,cpu_percent=10,memory_percent=20,queue_depth=25,failure_streak=2,foreground_active=False,quiet_hours_active=False,provider_available=True,operator_paused=False)
req(alert['notification_candidate'] and set(alert['notification_reason_codes'])=={'failure_threshold','queue_threshold'} and not alert['notification_sent'],'notification_threshold_prepares_only')
for name,kwargs in [
 ('foreground',{'foreground_active':True}),('quiet',{'quiet_hours_active':True}),('cpu',{'cpu_percent':90}),('memory',{'memory_percent':95}),('queue',{'queue_depth':100}),('failure',{'failure_streak':3}),('operator',{'operator_paused':True})]:
    base=dict(cpu_percent=10,memory_percent=20,queue_depth=1,failure_streak=0,foreground_active=False,quiet_hours_active=False,provider_available=True,operator_paused=False); base.update(kwargs)
    row=evaluate_unattended_tick(policy=policy,current_source_digest=D,**base)
    req(row['status']=='unattended_tick_paused' and row['pause_reasons'],f'{name}_pressure_pauses')
mal=evaluate_unattended_tick(policy=policy,current_source_digest=D,cpu_percent=None,memory_percent=20,queue_depth=1,failure_streak=0,foreground_active=False,quiet_hours_active=False,provider_available=True,operator_paused=False)
req(not mal['ok'] and mal['status']=='unattended_tick_suspended','missing_resource_evidence_suspends')
req(not evaluate_unattended_tick(policy=policy,current_source_digest='b'*64,cpu_percent=1,memory_percent=1,queue_depth=0,failure_streak=0,foreground_active=False,quiet_hours_active=False,provider_available=True,operator_paused=False)['ok'],'source_drift_blocks')
degraded=evaluate_unattended_tick(policy=policy,current_source_digest=D,cpu_percent=1,memory_percent=1,queue_depth=0,failure_streak=0,foreground_active=False,quiet_hours_active=False,provider_available=False,operator_paused=False)
req(degraded['ok'] and degraded['provider_degraded_mode'],'provider_outage_degrades_without_fake_contact')
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2450-runtime-'))
r1=record_health_sample(runtime_root=runtime,event_id='e1',policy_digest=policy['policy_digest'],source_digest=D,sample={'queue_depth':1,'latency_ms':50,'cpu_percent':10})
req(r1['ok'] and r1['status']=='health_sample_recorded','health_sample_recorded')
r2=record_health_sample(runtime_root=runtime,event_id='e1',policy_digest=policy['policy_digest'],source_digest=D,sample={'queue_depth':1,'latency_ms':50,'cpu_percent':10})
req(r2['status']=='health_sample_replayed' and r2['idempotent'],'health_sample_exactly_once')
conflict=record_health_sample(runtime_root=runtime,event_id='e1',policy_digest=policy['policy_digest'],source_digest=D,sample={'queue_depth':999})
req(not conflict['ok'] and conflict['status']=='health_sample_event_conflict','health_sample_conflicting_replay_rejected')
record_health_sample(runtime_root=runtime,event_id='e2',policy_digest=policy['policy_digest'],source_digest=D,sample={'queue_depth':3,'latency_ms':150,'cpu_percent':30})
trend=build_health_trend(runtime_root=runtime)
req(trend['ok'] and trend['sample_count']==2,'health_trend_uses_durable_samples')
req(trend['averages']['queue_depth']==2.0 and trend['averages']['latency_ms']==100.0,'health_trend_averages')
soak=run_accelerated_soak_fixture(policy=policy,source_digest=D,events=[{'cpu_percent':10,'memory_percent':20,'queue_depth':1,'failure_streak':0,'provider_available':True},{'cpu_percent':90,'memory_percent':20,'queue_depth':1,'failure_streak':0,'provider_available':True},{'cpu_percent':10,'memory_percent':20,'queue_depth':1,'failure_streak':0,'provider_available':False}])
req(soak['ok'] and soak['event_count']==3 and soak['paused_count']==1,'accelerated_soak_exercises_pause_recovery')
req(not soak['wall_clock_soak_completed'] and not soak['sleep_resume_native_evidence_collected'],'native_soak_not_manufactured')
ticket={'ticket_id':'bg_test','work_kind':'read_only_inspection','priority_class':'normal','evidence_digest':'7'*64,'status':'prepared_not_executed','execution_authorized':False}
import hashlib as _h, json as _j
ticket['ticket_digest']=_h.sha256(_j.dumps(ticket,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
adm=admit_era6_prepared_ticket(policy=policy,tick=elig,ticket=ticket)
req(adm['ok'] and adm['activity']=='health_inspection' and not adm['execution_authorized'],'era6_ticket_binds_to_unattended_policy')
req(not admit_era6_prepared_ticket(policy=policy,tick=elig,ticket=ticket,admission_ordinal=3)['ok'],'era6_ticket_budget_enforced')
bad_ticket=dict(ticket); bad_ticket['work_kind']='arbitrary_shell'
bad_ticket['ticket_digest']=_h.sha256(_j.dumps({k:v for k,v in bad_ticket.items() if k!='ticket_digest'},sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
req(not admit_era6_prepared_ticket(policy=policy,tick=elig,ticket=bad_ticket)['ok'],'era6_unsafe_ticket_not_admitted')
path=runtime/'era10'/'unattended_health.json'; path.write_text('{bad',encoding='utf-8')
corrupt=build_health_trend(runtime_root=runtime)
req(not corrupt['ok'] and corrupt['status']=='health_store_corrupt','corrupt_health_store_fails_closed')
req(all(not elig[k] for k in ('job_executed','provider_contacted','notification_sent','installation_authorized','authority_expanded')),'unattended_contract_non_authorizing')
print(json.dumps({'suite':'v2450.9-unattended-operation-soak','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
