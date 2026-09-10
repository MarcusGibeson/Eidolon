from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2050-data-')
from background_cognition_scheduler_v2000 import configure_scheduler,upsert_background_job,scheduler_tick,read_scheduler_state,public_scheduler_state,control_background_job,record_background_ticket_outcome
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2050-runtime-'))
base=datetime(2026,8,23,12,0,tzinfo=timezone.utc)
conf=configure_scheduler(event_id='config-1',enabled=True,timezone_offset_minutes=0,quiet_start_hour=22,quiet_end_hour=7,max_tickets_per_tick=2,runtime_root=runtime)
req(conf['ok'] and conf['state']['enabled'] is True,'scheduler_enable_persisted')
req(conf['job_executed'] is False and conf['provider_contacted'] is False,'configuration_nonexecuting')
for idx,kind in enumerate(('read_only_inspection','plan_review','proposal_preparation')):
    row=upsert_background_job(job_id=f'job-{idx}',work_kind=kind,interval_minutes=60,priority_class='high' if idx==0 else 'normal',evidence_digest=str(idx+1)*64,event_id=f'job-event-{idx}',runtime_root=runtime,now=base)
    req(row['ok'] and row['job']['work_kind']==kind,f'job_{idx}_durable')
req(upsert_background_job(job_id='bad',work_kind='delete_files',interval_minutes=60,priority_class='normal',evidence_digest='f'*64,event_id='bad',runtime_root=runtime)['ok'] is False,'unsafe_job_kind_rejected')
tick=scheduler_tick(tick_id='tick-1',runtime_root=runtime,now=base,foreground_busy=False,provider_available=True,resource_pressure='normal')
req(tick['ok'] and tick['tickets_prepared']==2,'bounded_ticket_budget')
req(all(row['status']=='prepared_not_executed' and row['execution_authorized'] is False for row in tick['tickets']),'tickets_are_not_execution')
req(tick['process_started'] is False and tick['tool_executed'] is False,'tick_cannot_execute')
state_before=public_scheduler_state(read_scheduler_state(runtime_root=runtime))
pause=control_background_job('pause',job_id='job-2',expected_state_digest=state_before['state_digest'],event_id='pause-job-2',runtime_root=runtime)
req(pause['ok'] and next(row for row in pause['state']['jobs'] if row['job_id']=='job-2')['enabled'] is False,'digest_bound_job_pause')
stale=control_background_job('resume',job_id='job-2',expected_state_digest=state_before['state_digest'],event_id='stale-resume',runtime_root=runtime)
req(stale['status']=='stale_scheduler_state_digest','stale_job_control_rejected')
current_state=pause['state']
resume=control_background_job('resume',job_id='job-2',expected_state_digest=current_state['state_digest'],event_id='resume-job-2',runtime_root=runtime)
req(resume['ok'] and next(row for row in resume['state']['jobs'] if row['job_id']=='job-2')['enabled'] is True,'job_resume')
first_ticket=tick['tickets'][0]
outcome=record_background_ticket_outcome(ticket_id=first_ticket['ticket_id'],expected_ticket_digest=first_ticket['ticket_digest'],outcome='completed_read_only',outcome_evidence_digest='9'*64,event_id='ticket-result-1',runtime_root=runtime)
req(outcome['ok'] and any(row['status']=='completed_read_only' for row in outcome['state']['recent_tickets']),'digest_bound_ticket_outcome')
outcome_replay=record_background_ticket_outcome(ticket_id=first_ticket['ticket_id'],expected_ticket_digest=first_ticket['ticket_digest'],outcome='completed_read_only',outcome_evidence_digest='9'*64,event_id='ticket-result-1',runtime_root=runtime)
req(outcome_replay['status']=='ticket_outcome_replayed','ticket_outcome_exactly_once')
replay=scheduler_tick(tick_id='tick-1',runtime_root=runtime,now=base)
req(replay['status']=='scheduler_tick_replayed' and replay['tickets_prepared']==0,'tick_exactly_once')
quiet=scheduler_tick(tick_id='tick-quiet',runtime_root=runtime,now=datetime(2026,8,23,23,0,tzinfo=timezone.utc))
req(quiet['tickets_prepared']==0 and 'quiet_hours' in quiet['suppression_reasons'],'quiet_hours_honored')
busy=scheduler_tick(tick_id='tick-busy',runtime_root=runtime,now=datetime(2026,8,24,12,0,tzinfo=timezone.utc),foreground_busy=True)
req(busy['tickets_prepared']==0 and 'foreground_busy' in busy['suppression_reasons'],'foreground_load_suppresses_background')
pressure=scheduler_tick(tick_id='tick-pressure',runtime_root=runtime,now=datetime(2026,8,24,13,0,tzinfo=timezone.utc),resource_pressure='critical')
req(pressure['tickets_prepared']==0 and 'resource_pressure' in pressure['suppression_reasons'],'resource_pressure_suppresses_background')
state=read_scheduler_state(runtime_root=runtime)
req(len(state['jobs'])==3 and len(state['tickets'])==2,'restart_state_durable')
req(state['raw_content_persisted'] is False,'scheduler_state_content_free')
print(json.dumps({'suite':'v2050.9-background-scheduler','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
