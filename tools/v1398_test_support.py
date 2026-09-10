from __future__ import annotations
from pathlib import Path
from authority_profiles import create_authority_profile
from standing_session_grants import prepare_standing_session,activate_standing_session

def require(c,m):
    if not c: raise AssertionError(m)

def active_grant(now=100):
    p=create_authority_profile(name='bounded_autonomous',workspace_digest='b'*64,max_minutes=10,max_commands=8)
    prepared=prepare_standing_session(p,now_unix=now,duration_minutes=5)
    return activate_standing_session(prepared['grant'],prepared['exact_authorization_phrase'],now_unix=now+1)['grant']

BACKLOG=[
 {'task_id':'backlog_docs_index','kind':'docs_index','action_class':'file_write','value':90,'risk':'low','dependencies':[]},
 {'task_id':'backlog_test_marker','kind':'test_marker','action_class':'test','value':80,'risk':'low','dependencies':['backlog_docs_index']},
 {'task_id':'backlog_cleanup_note','kind':'cleanup_note','action_class':'file_write','value':70,'risk':'low','dependencies':['backlog_test_marker']},
]

def executor_factory(root:Path,fail_kind=''):
    calls=[]
    def execute(task):
        calls.append(task['task_id'])
        if task['kind']==fail_kind:return {'ok':False,'failure_class':'fixture_failure'}
        root.mkdir(parents=True,exist_ok=True);p=root/(task['task_id']+'.done');p.write_text(task['kind'],encoding='utf-8')
        import hashlib
        return {'ok':True,'evidence_digest':hashlib.sha256(p.read_bytes()).hexdigest()}
    return execute,calls
