from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1227c-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import live_execution_monitoring_operator_intervention as m
from ordinary_chat_development_campaign import create_or_resume_development_proposal
from unified_development_work_queue import build_unified_development_work_queue
from v1227_monitoring_fixture import build_monitoring_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_monitoring_fixture('v1227-reliability'); rt=f['runtime']; launch=f['launch']
try:
 monitor=m.prepare_live_execution_monitoring(launch['launch_id'],expected_launch_digest=launch['launch_digest'],runtime_root=rt); r(monitor['ok'] is True,monitor)
 stale=m.request_live_execution_intervention('pause',monitor_id=monitor['monitor_id'],expected_monitor_digest='0'*64,runtime_root=rt); r(stale['ok'] is False and stale['reason']=='stale_live_execution_monitor_digest',stale)
 req=m.request_live_execution_intervention('pause',monitor_id=monitor['monitor_id'],expected_monitor_digest=monitor['monitor_digest'],runtime_root=rt); r(req['ok'] is True,req); r(req['intervention_type']=='pause'); r(req['operator_intervention_applied'] is False)
 current=m.inspect_live_execution_monitoring(launch['launch_id'],runtime_root=rt); r(current['ok'] is True,current); r(current['latest_intervention_request_digest']==req['request_digest'])
 conflict=m.request_live_execution_intervention('stop',monitor_id=current['monitor_id'],expected_monitor_digest=current['monitor_digest'],runtime_root=rt); r(conflict['ok'] is False and conflict['reason']=='conflicting_pending_intervention_request',conflict)
 replay=m.request_live_execution_intervention('pause',monitor_id=monitor['monitor_id'],expected_monitor_digest=monitor['monitor_digest'],runtime_root=rt); r(replay['ok'] is True and replay['operation_status']=='replayed',replay)
 p=m._request_path(req['request_id'],rt); data=json.loads(p.read_text()); data['intervention_type']='stop'; p.write_text(json.dumps(data)); r(m.public_live_execution_intervention_requests(runtime_root=rt)['ok'] is False)
 # Restore request, then tamper the monitor and prove fail closed.
 p.write_text(json.dumps(req,sort_keys=True))
 mp=m._monitor_path(launch['launch_id'],rt); md=json.loads(mp.read_text()); md['progress_percent']=99; mp.write_text(json.dumps(md)); r(m.load_live_execution_monitoring(launch['launch_id'],runtime_root=rt)=={})
 blocked=m.inspect_live_execution_monitoring(launch['launch_id'],runtime_root=rt); r(blocked['ok'] is False,blocked); r(blocked['provider_contacted'] is False and blocked['commands_executed'] is False); r(blocked['tests_executed'] is False and blocked['project_modified'] is False); r(blocked['operator_intervention_applied'] is False)
 # Independent lineage proves queue staleness expires monitoring.
 g=build_monitoring_fixture('v1227-stale'); rt2=g['runtime']; launch2=g['launch']
 try:
  mon2=m.prepare_live_execution_monitoring(launch2['launch_id'],expected_launch_digest=launch2['launch_digest'],runtime_root=rt2); r(mon2['ok'] is True,mon2)
  create_or_resume_development_proposal('Build another monitored utility',project_state={'id':'project-new','name':'Private New','path':str(Path(rt2)/'private-new')},runtime_root=rt2); q=build_unified_development_work_queue(runtime_root=rt2); r(q['generation']>=2,q)
  expired=m.inspect_live_execution_monitoring(launch2['launch_id'],runtime_root=rt2); r(expired['ok'] is False and expired['status']=='live_execution_monitoring_expired',expired)
  blob=json.dumps(expired,sort_keys=True); r('private-new' not in blob and str(Path(rt2)) not in blob); r(expired['pause_authorized'] is False and expired['stop_authorized'] is False)
 finally: shutil.rmtree(rt2,ignore_errors=True)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1227.8','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'stale_and_tamper_closed':True,'intervention_applied':False},sort_keys=True))
