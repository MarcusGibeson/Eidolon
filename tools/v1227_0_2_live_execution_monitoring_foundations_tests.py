from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1227a-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import live_execution_monitoring_operator_intervention as m
from v1227_monitoring_fixture import build_monitoring_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_monitoring_fixture('v1227-foundations'); rt=f['runtime']; launch=f['launch']
try:
 stale=m.prepare_live_execution_monitoring(launch['launch_id'],expected_launch_digest='0'*64,runtime_root=rt); r(stale['ok'] is False and stale['reason']=='stale_bounded_launch_digest',stale)
 monitor=m.prepare_live_execution_monitoring(launch['launch_id'],expected_launch_digest=launch['launch_digest'],runtime_root=rt); r(monitor['ok'] is True,monitor)
 for value in [monitor['monitor_id'].startswith('monitor_'),len(monitor['monitor_digest'])==64,monitor['launch_id']==launch['launch_id'],monitor['launch_digest']==launch['launch_digest'],monitor['generation']==1,monitor['current_stage']=='launched_waiting_for_step_authorization',monitor['progress_percent']==0,monitor['blocker_codes']==['authorization_required'],monitor['risk_codes']==['none'],monitor['monitoring_state']=='active',monitor['session_state']=='active',monitor['fresh_step_authorization_required'] is True,monitor['mindful_progress_reporting'] is True,monitor['operator_intervention_applied'] is False,monitor['pause_authorized'] is False,monitor['stop_authorized'] is False,monitor['provider_execution_authorized'] is False,monitor['command_execution_authorized'] is False,monitor['test_execution_authorized'] is False,monitor['workspace_materialization_authorized'] is False,monitor['project_mutation_authorized'] is False,monitor['cognition_written'] is False]: r(value,monitor)
 resumed=m.prepare_live_execution_monitoring(launch['launch_id'],expected_launch_digest=launch['launch_digest'],runtime_root=rt); r(resumed['operation_status']=='resumed',resumed); r(resumed['monitor_digest']==monitor['monitor_digest'])
 update=m.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='progress_updated',current_stage='step_authorization_review',completed_units=1,total_units=4,blocker_codes=['authorization_required'],risk_codes=['uncertainty_high'],operator_attention_required=True,runtime_root=rt); r(update['ok'] is True,update)
 for value in [update['generation']==2,update['progress_percent']==25,update['current_stage']=='step_authorization_review',update['operator_attention_required'] is True,update['risk_codes']==['uncertainty_high'],update['last_event_digest']!=monitor['last_event_digest'],m._validate_monitor(m.load_live_execution_monitoring(launch['launch_id'],runtime_root=rt))]: r(value,update)
 invalid=m.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='progress_updated',current_stage='blocked',completed_units=1,total_units=4,runtime_root=rt); r(invalid['ok'] is False and invalid['reason']=='blocked_stage_requires_blocker',invalid)
 listed=m.public_live_execution_monitoring_sessions(runtime_root=rt); r(listed['ok'] is True and listed['monitor_count']==1,listed); r(listed['monitors'][0]['private_path_exposed'] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1227.2','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'monitoring_content_free':True,'step_execution_authorized':False},sort_keys=True))
