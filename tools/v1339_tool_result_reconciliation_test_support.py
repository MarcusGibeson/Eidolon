from __future__ import annotations
import sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1334_file_operations_test_support import candidate,sha
from structured_file_operations import patch_candidate_file
from v1333_workspace_isolation_test_support import precondition
from v1336_process_operations_test_support import process_candidate,wait_terminal
from typed_process_operations import start_candidate_process

def file_receipt(base:Path):
 src,runtime,grant,wid,cand=candidate(base);fp=precondition(runtime,'file_patch');before=sha(cand/'app.py');r=patch_candidate_file(wid,'app.py',patches=[{'type':'replace_text','old':'hello','new':'reconciled','expected_occurrences':1}],expected_content_digest=before,active_grant=grant,precondition_record_id=fp,runtime_root=runtime,now_unix=101);return src,runtime,grant,wid,cand,r['file_operation']['operation_id']
