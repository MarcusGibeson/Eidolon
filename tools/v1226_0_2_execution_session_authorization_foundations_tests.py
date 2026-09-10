from __future__ import annotations
import json,os,shutil,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='v1226a-'))
sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import execution_session_authorization_bounded_launch as m
from v1226_launch_fixture import build_launch_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_launch_fixture('v1226-foundations'); rt=f['runtime']; s=f['prepared_session']
try:
 a=m.prepare_bounded_launch_authorization(s['session_id'],expected_session_digest=s['session_digest'],runtime_root=rt)
 for v in [a['ok'] is True,a['status']=='bounded_execution_session_launch_authorization_ready',a['authorization_id'].startswith('launch_auth_'),len(a['authorization_digest'])==64,a['source_session_id']==s['session_id'],a['source_session_digest']==s['session_digest'],a['queue_item_id']==s['queue_item_id'],a['project_reference']==s['project_reference'],a['proposal_id']==s['proposal_id'],a['authorization_consumed'] is False,a['single_use_launch_authorization_required'] is True,a['goal_alignment_review_required'] is True,a['uncertainty_review_required'] is True,a['outcome_reflection_required'] is True,a['execution_session_launch_authorized'] is False,a['provider_execution_authorized'] is False,a['command_execution_authorized'] is False,a['test_execution_authorized'] is False,a['workspace_materialization_authorized'] is False,a['project_mutation_authorized'] is False,a['old_authority_reusable'] is False]: r(v,a)
 r(a['authorize_phrase'].startswith('Authorize bounded launch for prepared development execution session '),a)
 replay=m.prepare_bounded_launch_authorization(s['session_id'],expected_session_digest=s['session_digest'],runtime_root=rt); r(replay['operation_status']=='resumed',replay); r(replay['authorization_digest']==a['authorization_digest'])
 blob=json.dumps(m._public_authorization(a),sort_keys=True); r(f['other_private_path'] not in blob and f['third_private_path'] not in blob); r('Private Project' not in blob)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1226.2','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'single_use_authorization_prepared':True,'execution_launched':False},sort_keys=True))
