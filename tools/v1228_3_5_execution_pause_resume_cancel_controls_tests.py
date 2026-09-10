from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1228b-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import live_execution_monitoring_operator_intervention as m
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1228_control_fixture import build_control_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_control_fixture('v1228-conversation'); rt=f['runtime']; launch=f['launch']; monitor=f['monitor']; initial=f['control']
try:
 shown=process_ordinary_chat_development_turn(f"Show execution session control for bounded development execution session {launch['launch_id']}.",runtime_root=rt); r(shown['active'] is True,shown); r(shown['event']=='execution_session_control_ready',shown); r(shown['execution_session_control']['session_state']=='active')
 req_text=f"Request bounded pause intervention for live execution monitoring {monitor['monitor_id']} digest {monitor['monitor_digest']}."
 req_turn=process_ordinary_chat_development_turn(req_text,runtime_root=rt); r(req_turn['event']=='live_execution_intervention_requested',req_turn); req=req_turn['live_execution_monitoring']
 prep=f"Prepare bounded execution pause authorization for intervention request {req['request_id']} digest {req['request_digest']}."
 auth_turn=process_ordinary_chat_development_turn(prep,runtime_root=rt); r(auth_turn['event']=='execution_session_transition_authorization_ready',auth_turn); auth=auth_turn['execution_session_control']
 apply_turn=process_ordinary_chat_development_turn(auth['authorize_phrase'],runtime_root=rt); r(apply_turn['event']=='execution_session_transition_applied',apply_turn); pause=apply_turn['execution_session_control']; r(pause['action']=='pause' and pause['to_state']=='paused',pause); r(pause['pause_applied'] is True); r(pause['transition_authorization_consumed'] is True)
 replay=process_ordinary_chat_development_turn(auth['authorize_phrase'],runtime_root=rt); r(replay['event']=='execution_session_transition_applied',replay); r(replay['execution_session_control']['operation_status']=='replayed',replay)
 paused=process_ordinary_chat_development_turn(f"Show execution session control for bounded development execution session {launch['launch_id']}.",runtime_root=rt); state=paused['execution_session_control']; r(state['session_state']=='paused',state)
 resume_prep=process_ordinary_chat_development_turn(f"Prepare bounded execution resume authorization for execution session control {state['control_id']} digest {state['control_digest']}.",runtime_root=rt); r(resume_prep['event']=='execution_session_transition_authorization_ready',resume_prep); resume_auth=resume_prep['execution_session_control']
 resumed=process_ordinary_chat_development_turn(resume_auth['authorize_phrase'],runtime_root=rt); r(resumed['event']=='execution_session_transition_applied',resumed); r(resumed['execution_session_control']['to_state']=='active',resumed); r(resumed['execution_session_control']['resume_applied'] is True)
 monitored=process_ordinary_chat_development_turn(f"Show live execution monitoring for bounded development execution session {launch['launch_id']}.",runtime_root=rt); r(monitored['live_execution_monitoring']['session_state']=='active',monitored)
 current_monitor=m.inspect_live_execution_monitoring(launch['launch_id'],runtime_root=rt)
 stop_req=process_ordinary_chat_development_turn(f"Request bounded stop intervention for live execution monitoring {current_monitor['monitor_id']} digest {current_monitor['monitor_digest']}.",runtime_root=rt); r(stop_req['event']=='live_execution_intervention_requested',stop_req); stop=stop_req['live_execution_monitoring']
 cancel_prep=process_ordinary_chat_development_turn(f"Prepare bounded execution cancel authorization for intervention request {stop['request_id']} digest {stop['request_digest']}.",runtime_root=rt); r(cancel_prep['event']=='execution_session_transition_authorization_ready',cancel_prep); cancel_auth=cancel_prep['execution_session_control']
 cancelled=process_ordinary_chat_development_turn(cancel_auth['authorize_phrase'],runtime_root=rt); r(cancelled['event']=='execution_session_transition_applied',cancelled); r(cancelled['execution_session_control']['to_state']=='cancelled',cancelled); r(cancelled['execution_session_control']['cancel_applied'] is True)
 requests=process_ordinary_chat_development_turn('Show live execution intervention requests.',runtime_root=rt); r(requests['live_execution_monitoring']['request_count']==2,requests); r(all(x['request_state']=='resolved_by_v1228' for x in requests['live_execution_monitoring']['requests']),requests)
 controls=process_ordinary_chat_development_turn('Show execution session controls.',runtime_root=rt); r(controls['execution_session_control']['control_count']==1,controls)
 transitions=process_ordinary_chat_development_turn('Show execution session transitions.',runtime_root=rt); r(transitions['execution_session_control']['transition_count']==3,transitions)
 for value in [cancelled['execution_session_control']['provider_contacted'] is False,cancelled['execution_session_control']['commands_executed'] is False,cancelled['execution_session_control']['tests_executed'] is False,cancelled['execution_session_control']['project_modified'] is False,cancelled['execution_session_control']['cognition_written'] is False]: r(value,cancelled)
 r(process_ordinary_chat_development_turn('Please pause it now.',runtime_root=rt).get('event')!='execution_session_transition_applied')
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1228.5','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'pause_resume_cancel_separately_authorized':True,'provider_contacted':False},sort_keys=True))
