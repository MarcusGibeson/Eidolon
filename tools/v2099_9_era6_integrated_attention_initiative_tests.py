from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2099-int-data-')
from background_cognition_scheduler_v2000 import configure_scheduler,upsert_background_job
from era6_attention_initiative import build_era6_attention_snapshot,prepare_era6_background_cycle,process_era6_attention_control
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2099-int-runtime-'))
configure_scheduler(event_id='cfg',enabled=True,quiet_start_hour=23,quiet_end_hour=6,runtime_root=runtime)
upsert_background_job(job_id='review-plan',work_kind='plan_review',interval_minutes=60,priority_class='normal',evidence_digest='e'*64,event_id='job',runtime_root=runtime)
snap=build_era6_attention_snapshot(runtime_root=runtime)
req(snap['ok'] and snap['status']=='era6_attention_snapshot','integrated_snapshot_builds')
req(snap['scheduler']['enabled'] is True and snap['scheduler']['job_count']==1,'scheduler_visible_in_snapshot')
req(snap['raw_attention_content_exposed'] is False and snap['private_runtime_content_exposed'] is False,'integrated_snapshot_content_free')
req(snap['background_work_executed'] is False and snap['message_sent'] is False,'integrated_snapshot_nonexecuting')
cycle=prepare_era6_background_cycle(cycle_id='cycle-a',runtime_root=runtime,foreground_busy=False,provider_available=True,resource_pressure='normal')
req(cycle['ok'] and cycle['status']=='era6_background_cycle_prepared','integrated_cycle_prepares')
req(cycle['tickets_prepared']==1 and len(cycle['ticket_ids'])==1,'integrated_cycle_prepares_ticket')
req(cycle['background_work_executed'] is False and cycle['provider_contacted'] is False,'prepared_cycle_no_execution')
pressure_cycle=prepare_era6_background_cycle(cycle_id='cycle-pressure',runtime_root=runtime,resource_measurements={'foreground_high_load':True,'cpu_percent':90})
req(pressure_cycle['tickets_prepared']==0 and pressure_cycle['resource_mode']=='suspend','resource_measurements_directly_suppress_background')
req(pressure_cycle['resource_assessment_digest'] and pressure_cycle['resource_state_status'].startswith('background_tickets_'),'resource_assessment_integrated')
unknown_cycle=prepare_era6_background_cycle(cycle_id='cycle-unknown-resource',runtime_root=runtime,resource_measurements={})
req(unknown_cycle['tickets_prepared']==0 and unknown_cycle['resource_mode']=='suspend','missing_resource_evidence_fails_closed')
replay=prepare_era6_background_cycle(cycle_id='cycle-a',runtime_root=runtime)
req(replay['tickets_prepared']==0,'integrated_cycle_replay_no_duplicate_ticket')
ctrl=process_era6_attention_control('inspect attention and initiative',runtime_root=runtime)
req(ctrl['active'] is True and ctrl['ok'] is True,'ordinary_chat_inspection_control')
resource=process_era6_attention_control('show resource budgets',runtime_root=runtime)
req(resource['active'] is True and resource['status']=='era6_resource_budgets_inspected','resource_control')
proactive=process_era6_attention_control('show proactive communication queue',runtime_root=runtime)
req(proactive['active'] is True and proactive['delivery_authorized'] is False,'proactive_queue_inspection_non_authorizing')
blocked=process_era6_attention_control('inspect attention and initiative and install it',runtime_root=runtime)
req(blocked['active'] is True and blocked['status']=='era6_read_only_scope_expansion_rejected','compound_scope_expansion_rejected')
ordinary=(ROOT/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
req('process_era6_attention_control' in ordinary,'era6_uses_existing_ordinary_chat_boundary')
req(cycle['installation_authorized'] is False and cycle['authority_expanded'] is False,'era6_preserves_authority')
print(json.dumps({'suite':'v2099.9-era6-integrated-attention-initiative','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
