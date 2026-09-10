from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1228a-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import execution_session_pause_resume_cancel_recovery as c
import live_execution_monitoring_operator_intervention as m
from v1228_control_fixture import build_control_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_control_fixture('v1228-foundations'); rt=f['runtime']; launch=f['launch']; monitor=f['monitor']; control=f['control']
try:
 for value in [control['ok'] is True,control['session_state']=='active',control['control_id'].startswith('control_'),len(control['control_digest'])==64,control['runtime_namespace_present'] is True,control['fresh_transition_authorization_required'] is True,control['fresh_resume_authorization_required'] is True,control['provider_execution_authorized'] is False,control['command_execution_authorized'] is False,control['test_execution_authorized'] is False,control['workspace_materialization_authorized'] is False,control['project_mutation_authorized'] is False,control['cognition_write_authorized'] is False,control['old_authority_reusable'] is False]: r(value,control)
 resumed=c.prepare_execution_session_control(launch['launch_id'],expected_launch_digest=launch['launch_digest'],runtime_root=rt); r(resumed['operation_status']=='resumed',resumed); r(resumed['control_digest']==control['control_digest'])
 req=m.request_live_execution_intervention('pause',monitor_id=monitor['monitor_id'],expected_monitor_digest=monitor['monitor_digest'],runtime_root=rt); r(req['ok'] is True,req)
 auth=c.prepare_execution_session_transition_authorization('pause',request_id=req['request_id'],expected_request_digest=req['request_digest'],runtime_root=rt); r(auth['ok'] is True,auth)
 for value in [auth['authorization_id'].startswith('transition_auth_'),len(auth['authorization_digest'])==64,auth['action']=='pause',auth['control_id']==control['control_id'],auth['control_digest']==control['control_digest'],auth['request_id']==req['request_id'],auth['authorization_consumed'] is False,auth['pause_applied'] is False,auth['provider_execution_authorized'] is False,auth['project_mutation_authorized'] is False,'Authorize bounded execution pause' in auth['authorize_phrase']]: r(value,auth)
 replay=c.prepare_execution_session_transition_authorization('pause',request_id=req['request_id'],expected_request_digest=req['request_digest'],runtime_root=rt); r(replay['operation_status']=='replayed',replay); r(replay['authorization_digest']==auth['authorization_digest'])
 listed=c.public_execution_session_controls(runtime_root=rt); r(listed['ok'] is True and listed['control_count']==1,listed); r(listed['controls'][0]['private_path_exposed'] is False)
 auths=c.public_execution_session_transition_authorizations(runtime_root=rt); r(auths['ok'] is True and auths['authorization_count']==1,auths)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1228.2','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'separate_transition_authority':True,'execution_started':False},sort_keys=True))
