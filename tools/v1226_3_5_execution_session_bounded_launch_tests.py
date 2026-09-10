from __future__ import annotations
import json,os,shutil,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1226b-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import execution_session_authorization_bounded_launch as m
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1226_launch_fixture import build_launch_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_launch_fixture('v1226-launch'); rt=f['runtime']; s=f['prepared_session']
try:
 cmd=f"Prepare bounded launch authorization for prepared development execution session {s['session_id']} digest {s['session_digest']}."
 turn=process_ordinary_chat_development_turn(cmd,runtime_root=rt); r(turn['active'] is True,turn); r(turn['event']=='bounded_execution_session_launch_authorization_ready',turn)
 a=turn['execution_session_bounded_launch']; r('exact authorization phrase' in turn['conversation_response'].lower(),turn)
 launched=process_ordinary_chat_development_turn(a['authorize_phrase'],runtime_root=rt); r(launched['event']=='bounded_development_execution_session_launched',launched); row=launched['execution_session_bounded_launch']
 for v in [row['launch_id'].startswith('launch_'),len(row['launch_digest'])==64,row['session_state']=='active',row['authorization_consumed'] is True,row['execution_session_launch_authorized'] is True,row['execution_session_launched'] is True,row['session_runtime_namespace_created'] is True,row['project_workspace_materialized'] is False,row['mindful_launch_gate_passed'] is True,row['goal_alignment_review_required'] is True,row['uncertainty_review_required'] is True,row['outcome_reflection_required'] is True,row['fresh_step_authorization_required'] is True,row['provider_execution_authorized'] is False,row['command_execution_authorized'] is False,row['test_execution_authorized'] is False,row['workspace_materialization_authorized'] is False,row['project_mutation_authorized'] is False,row['provider_contacted'] is False,row['commands_executed'] is False,row['tests_executed'] is False,row['cognition_written'] is False]: r(v,row)
 replay=process_ordinary_chat_development_turn(a['authorize_phrase'],runtime_root=rt); r(replay['event']=='bounded_development_execution_session_launched',replay); r(replay['execution_session_bounded_launch']['operation_status']=='replayed',replay)
 listed=process_ordinary_chat_development_turn('Show bounded development execution sessions.',runtime_root=rt); r(listed['event']=='bounded_development_execution_session_list_ready',listed); r(listed['execution_session_bounded_launch']['session_count']==1,listed)
 shown=process_ordinary_chat_development_turn(f"Show bounded development execution session {row['launch_id']}.",runtime_root=rt); r(shown['event']=='bounded_development_execution_session_launched',shown)
 r(m.process_execution_session_authorization_bounded_launch_control('It would be nice to launch something eventually.',runtime_root=rt)['active'] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1226.5','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'single_use_launch_consumed':True,'step_execution_authorized':False},sort_keys=True))
