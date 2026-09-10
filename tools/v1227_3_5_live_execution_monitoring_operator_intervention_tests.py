from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1227b-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import live_execution_monitoring_operator_intervention as m
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1227_monitoring_fixture import build_monitoring_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_monitoring_fixture('v1227-conversation'); rt=f['runtime']; launch=f['launch']
try:
 cmd=f"Prepare live execution monitoring for bounded development execution session {launch['launch_id']} digest {launch['launch_digest']}."
 turn=process_ordinary_chat_development_turn(cmd,runtime_root=rt); r(turn['active'] is True,turn); r(turn['event']=='live_execution_monitoring_ready',turn)
 monitor=turn['live_execution_monitoring']; r('grants no execution or intervention authority' in turn['conversation_response'].lower(),turn)
 shown=process_ordinary_chat_development_turn(f"Show live execution monitoring for bounded development execution session {launch['launch_id']}.",runtime_root=rt); r(shown['event']=='live_execution_monitoring_ready',shown); r(shown['live_execution_monitoring']['monitor_id']==monitor['monitor_id'])
 listed=process_ordinary_chat_development_turn('Show live execution monitoring sessions.',runtime_root=rt); r(listed['event']=='live_execution_monitoring_session_list_ready',listed); r(listed['live_execution_monitoring']['monitor_count']==1,listed)
 request_text=f"Request bounded operator review intervention for live execution monitoring {monitor['monitor_id']} digest {monitor['monitor_digest']}."
 requested=process_ordinary_chat_development_turn(request_text,runtime_root=rt); r(requested['event']=='live_execution_intervention_requested',requested)
 req=requested['live_execution_monitoring']
 for value in [req['request_id'].startswith('intervention_'),len(req['request_digest'])==64,req['request_state']=='pending_v1228_action',req['intervention_type']=='operator_review',req['operator_intervention_applied'] is False,req['pause_authorized'] is False,req['stop_authorized'] is False,req['resume_authorized'] is False,req['cancel_authorized'] is False,req['provider_execution_authorized'] is False,req['command_execution_authorized'] is False,req['test_execution_authorized'] is False,req['project_mutation_authorized'] is False,req['fresh_v1228_authorization_required'] is True]: r(value,req)
 r('fresh v1228 control remains required' in requested['conversation_response'].lower(),requested)
 replay=process_ordinary_chat_development_turn(request_text,runtime_root=rt); r(replay['event']=='live_execution_intervention_requested',replay); r(replay['live_execution_monitoring']['operation_status']=='replayed',replay)
 requests=process_ordinary_chat_development_turn('Show live execution intervention requests.',runtime_root=rt); r(requests['event']=='live_execution_intervention_request_list_ready',requests); r(requests['live_execution_monitoring']['request_count']==1,requests)
 r(m.process_live_execution_monitoring_operator_intervention_control('It would be nice to watch execution more closely.',runtime_root=rt)['active'] is False)
 r(m.process_live_execution_monitoring_operator_intervention_control('Please pause it.',runtime_root=rt)['active'] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1227.5','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'intervention_requested_only':True,'v1228_transition_required':True},sort_keys=True))
