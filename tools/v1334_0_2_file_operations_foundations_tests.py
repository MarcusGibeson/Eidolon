from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1334_file_operations_test_support import *
from v1333_workspace_isolation_test_support import precondition
from structured_file_operations import *
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 src,runtime,grant,wid,root=candidate(Path(td));readpre=precondition(runtime,'file_read');writepre=precondition(runtime,'file_patch')
 r=read_candidate_file(wid,'app.py',active_grant=grant,precondition_record_id=readpre,runtime_root=runtime,now_unix=101,include_content=True);req(r['ok'] and 'hello' in r['content'],'structured_read')
 req(r['file_operation']['encoding_code']=='utf8' and r['file_operation']['newline_code']=='lf','encoding_newline_detected')
 before=sha(root/'app.py');p=patch_candidate_file(wid,'app.py',expected_content_digest=before,patches=[{'type':'replace_text','old':'hello','new':'goodbye','expected_occurrences':1}],active_grant=grant,precondition_record_id=writepre,runtime_root=runtime,now_unix=101);req(p['ok'] and b'goodbye' in (root/'app.py').read_bytes(),'structured_patch')
 req(b'hello' in (src/'app.py').read_bytes(),'selected_source_unchanged')
 req(p['file_operation']['raw_content_exposed'] is False and p['file_operation']['raw_path_exposed'] is False,'public_evidence_content_minimized')
print({'ok':True,'suite':'v1334.0-2-file-operations-foundations','passed':passed,'total':5})
