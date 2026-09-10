from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,make_source,active_grant,precondition
from workspace_isolation import create_disposable_workspace,_record_path
from ordinary_chat_development_campaign import _read_json

HTML='''<!doctype html><html><body><label>Name <input id="name"></label><button id="go" onclick="document.getElementById('out').textContent='Hello '+document.getElementById('name').value">Go</button><div id="out">Idle</div></body></html>'''

def browser_candidate(base:Path):
    src=make_source(base);(src/'ui.html').write_text(HTML,encoding='utf-8')
    runtime=base/'runtime';grant=active_grant(commands=('browser',));isopre=precondition(runtime,'file_patch')
    made=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=isopre,mode='filesystem_copy',runtime_root=runtime,now_unix=101)
    assert made['ok'],made
    rec=_read_json(_record_path(made['workspace_id'],runtime));candidate=Path(rec['candidate_private_path']);browserpre=precondition(runtime,'browser')
    return src,runtime,grant,made['workspace_id'],candidate,browserpre
