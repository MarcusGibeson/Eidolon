from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1228c-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import execution_session_pause_resume_cancel_recovery as c
import live_execution_monitoring_operator_intervention as m
from execution_session_authorization_bounded_launch import _runtime_namespace_path
from v1228_control_fixture import build_control_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
# Unsafe-stage pause waits for a safe boundary, then reconciles without minting new authority.
f=build_control_fixture('v1228-safe-boundary'); rt=f['runtime']; launch=f['launch']; monitor=f['monitor']; control=f['control']
try:
 active=m.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='stage_entered',current_stage='provider_step_active',completed_units=1,total_units=4,risk_codes=['operator_attention'],runtime_root=rt); r(active['ok'] is True,active)
 req=m.request_live_execution_intervention('pause',monitor_id=active['monitor_id'],expected_monitor_digest=active['monitor_digest'],runtime_root=rt); r(req['ok'] is True,req)
 auth=c.prepare_execution_session_transition_authorization('pause',request_id=req['request_id'],expected_request_digest=req['request_digest'],runtime_root=rt); r(auth['ok'] is True,auth)
 wrong=c.apply_execution_session_transition(auth['authorization_id'],expected_authorization_digest=auth['authorization_digest'],expected_control_id=auth['control_id'],expected_control_digest=auth['control_digest'],expected_action='cancel',runtime_root=rt); r(wrong['ok'] is False and wrong['reason']=='transition_action_phrase_mismatch',wrong)
 pending=c.apply_execution_session_transition(auth['authorization_id'],expected_authorization_digest=auth['authorization_digest'],expected_control_id=auth['control_id'],expected_control_digest=auth['control_digest'],expected_action='pause',runtime_root=rt); r(pending['ok'] is True and pending['to_state']=='pause_pending_safe_boundary',pending); r(pending['pause_applied'] is False,pending)
 state=c.inspect_execution_session_control(launch['launch_id'],runtime_root=rt); r(state['session_state']=='pause_pending_safe_boundary',state)
 safe=m.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='operator_review_required',current_stage='operator_review_required',completed_units=1,total_units=4,blocker_codes=['operator_decision_required'],risk_codes=['operator_attention'],operator_attention_required=True,runtime_root=rt); r(safe['ok'] is True,safe)
 reconciled=c.reconcile_execution_session_control(state['control_id'],expected_control_digest=state['control_digest'],runtime_root=rt); r(reconciled['ok'] is True and reconciled['session_state']=='paused',reconciled)
 # Missing runtime namespace is detected and can only recover into paused.
 shutil.rmtree(_runtime_namespace_path(launch['launch_id'],rt),ignore_errors=True)
 recovery=c.inspect_execution_session_control(launch['launch_id'],runtime_root=rt); r(recovery['ok'] is True and recovery['session_state']=='recovery_required',recovery)
 rec_auth=c.prepare_execution_session_transition_authorization('recover',control_id=recovery['control_id'],expected_control_digest=recovery['control_digest'],runtime_root=rt); r(rec_auth['ok'] is True,rec_auth)
 recovered=c.apply_execution_session_transition(rec_auth['authorization_id'],expected_authorization_digest=rec_auth['authorization_digest'],expected_control_id=rec_auth['control_id'],expected_control_digest=rec_auth['control_digest'],expected_action='recover',runtime_root=rt); r(recovered['ok'] is True and recovered['to_state']=='paused',recovered); r(recovered['recovery_applied'] is True); r((_runtime_namespace_path(launch['launch_id'],rt)/'session.json').exists())
 # Fresh resume authority is required after recovery.
 old_replay=c.apply_execution_session_transition(auth['authorization_id'],expected_authorization_digest=auth['authorization_digest'],expected_control_id=auth['control_id'],expected_control_digest=auth['control_digest'],expected_action='pause',runtime_root=rt); r(old_replay['operation_status']=='replayed',old_replay); r(old_replay['to_state']=='pause_pending_safe_boundary',old_replay)
 current=c.inspect_execution_session_control(launch['launch_id'],runtime_root=rt); resume=c.prepare_execution_session_transition_authorization('resume',control_id=current['control_id'],expected_control_digest=current['control_digest'],runtime_root=rt); r(resume['ok'] is True,resume)
 # Tamper closes public authorization inventory.
 ap=c._authorization_path(resume['authorization_id'],rt); data=json.loads(ap.read_text()); data['action']='cancel'; ap.write_text(json.dumps(data)); r(c.public_execution_session_transition_authorizations(runtime_root=rt)['ok'] is False)
 blob=json.dumps(c.inspect_execution_session_control(launch['launch_id'],runtime_root=rt),sort_keys=True); r(str(Path(rt)) not in blob and 'provider_step_active' not in blob)
finally: shutil.rmtree(rt,ignore_errors=True)
# Independent control tamper fails closed.
g=build_control_fixture('v1228-tamper'); rt2=g['runtime']; launch2=g['launch']
try:
 cp=c._control_path(launch2['launch_id'],rt2); data=json.loads(cp.read_text()); data['session_state']='cancelled'; cp.write_text(json.dumps(data)); blocked=c.inspect_execution_session_control(launch2['launch_id'],runtime_root=rt2); r(blocked['ok'] is False,blocked); r(blocked['provider_contacted'] is False and blocked['commands_executed'] is False); r(blocked['project_modified'] is False and blocked['old_authority_reusable'] is False)
finally: shutil.rmtree(rt2,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1228.8','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'safe_boundary_pause':True,'recovery_defaults_to_paused':True,'tamper_closed':True},sort_keys=True))
