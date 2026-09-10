from __future__ import annotations
import hashlib,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1333_workspace_isolation_test_support import WS,active_grant,precondition
from workspace_isolation import create_disposable_workspace,cleanup_disposable_workspace,_record_path
from ordinary_chat_development_campaign import _read_json
BUG='def add(a,b):\n    return a-b\n';WRONG='def add(a,b):\n    return a*b\n';GOOD='def add(a,b):\n    return a+b\n';CHECK='import app,sys\nraise SystemExit(0 if app.add(2,3)==5 else 1)\n'
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()
def fixture(base:Path):
 src=base/'source';src.mkdir();(src/'app.py').write_text(BUG);(src/'check.py').write_text(CHECK);runtime=base/'runtime';grant=active_grant(commands=('shell',));fpre=precondition(runtime,'file_patch');spre=precondition(runtime,'shell');made=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=fpre,mode='filesystem_copy',retention_rule='retain_for_review',runtime_root=runtime,now_unix=101);rec=_read_json(_record_path(made['workspace_id'],runtime));return src,runtime,grant,made['workspace_id'],Path(rec['candidate_private_path']),fpre,spre
def attempts():return [
 {'strategy_digest':'a'*64,'evidence_supports_attempt':True,'relative_path':'app.py','expected_content_digest':sha_text(BUG),'patches':[{'type':'replace_text','old':'return a-b','new':'return a*b'}],'test_argv':[sys.executable,'check.py','attempt1']},
 {'strategy_digest':'b'*64,'evidence_supports_attempt':True,'relative_path':'app.py','expected_content_digest':sha_text(WRONG),'patches':[{'type':'replace_text','old':'return a*b','new':'return a+b'}],'test_argv':[sys.executable,'check.py','attempt2']},
]
def req(v,m):
 if not v:raise AssertionError(m)
def clean(runtime,grant,wid):return cleanup_disposable_workspace(wid,active_grant=grant,discard_owned_changes=True,runtime_root=runtime,now_unix=101)
