from __future__ import annotations
import json,os,shutil,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1226c-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import execution_session_authorization_bounded_launch as m
from ordinary_chat_development_campaign import create_or_resume_development_proposal
from unified_development_work_queue import build_unified_development_work_queue
from v1226_launch_fixture import build_launch_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_launch_fixture('v1226-reliability'); rt=f['runtime']; s=f['prepared_session']
try:
 stale=m.prepare_bounded_launch_authorization(s['session_id'],expected_session_digest='0'*64,runtime_root=rt); r(stale['ok'] is False and stale['reason']=='stale_prepared_session_digest',stale)
 a=m.prepare_bounded_launch_authorization(s['session_id'],expected_session_digest=s['session_digest'],runtime_root=rt); r(a['ok'] is True,a)
 bad=m.launch_bounded_development_execution_session(a['authorization_id'],expected_authorization_digest='0'*64,expected_session_id=s['session_id'],expected_session_digest=s['session_digest'],runtime_root=rt); r(bad['ok'] is False and bad['reason']=='stale_launch_authorization_digest',bad)
 wrong=m.launch_bounded_development_execution_session(a['authorization_id'],expected_authorization_digest=a['authorization_digest'],expected_session_id=s['session_id'],expected_session_digest='f'*64,runtime_root=rt); r(wrong['ok'] is False and wrong['reason']=='launch_session_digest_mismatch',wrong)
 row=m.launch_bounded_development_execution_session(a['authorization_id'],expected_authorization_digest=a['authorization_digest'],expected_session_id=s['session_id'],expected_session_digest=s['session_digest'],runtime_root=rt); r(row['ok'] is True,row)
 cp=m._authorization_consumption_path(a['authorization_id'],rt); consumption=json.loads(cp.read_text()); r(consumption['consumption_count']==1); r(consumption['authorization_consumed'] is True); r(consumption['old_authority_reusable'] is False)
 replay=m.launch_bounded_development_execution_session(a['authorization_id'],expected_authorization_digest=a['authorization_digest'],expected_session_id=s['session_id'],expected_session_digest=s['session_digest'],runtime_root=rt); r(replay['operation_status']=='replayed',replay); r(json.loads(cp.read_text())['consumption_count']==1)
 create_or_resume_development_proposal('Build another bounded utility',project_state={'id':'project-four','name':'Private Four','path':str(Path(rt)/'private-four')},runtime_root=rt); q=build_unified_development_work_queue(runtime_root=rt); r(q['generation']>=2,q)
 expired=m.inspect_bounded_development_execution_session(row['launch_id'],runtime_root=rt); r(expired['ok'] is False and expired['status']=='bounded_development_execution_session_expired',expired); r(expired['provider_execution_authorized'] is False and expired['project_mutation_authorized'] is False)
 p=m._launch_path(row['launch_id'],rt); data=json.loads(p.read_text()); data['priority_level']='critical'; p.write_text(json.dumps(data)); r(m.load_bounded_development_execution_session(row['launch_id'],runtime_root=rt)=={})
 blocked=m.inspect_bounded_development_execution_session(row['launch_id'],runtime_root=rt); r(blocked['ok'] is False,blocked); blob=json.dumps(blocked,sort_keys=True); r(f['other_private_path'] not in blob and f['third_private_path'] not in blob and 'private-four' not in blob); r(blocked['provider_contacted'] is False and blocked['commands_executed'] is False); r(blocked['tests_executed'] is False and blocked['cognition_written'] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1226.8','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'replay_and_tamper_closed':True,'old_authority_reusable':False},sort_keys=True))
