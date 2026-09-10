from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1334_file_operations_test_support import *
from v1333_workspace_isolation_test_support import precondition
from structured_file_operations import *
from release_authority import WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
req(OPERATION_KINDS==('read','patch','move','generated_update'),'operation_contract')
with tempfile.TemporaryDirectory() as td:
 src,runtime,grant,wid,root=candidate(Path(td));wp=precondition(runtime,'file_patch');d=sha(root/'app.py');r=patch_candidate_file(wid,'app.py',expected_content_digest=d,patches=[{'type':'replace_line_range','start_line':1,'end_line':1,'replacement':'print("line patch")\n'}],active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101)
 req(r['ok'] and b'line patch' in (root/'app.py').read_bytes(),'line_range_patch')
 req(b'hello' in (src/'app.py').read_bytes(),'source_unchanged')
 req(r['command_execution_authorized'] is False and r['provider_contact_authorized'] is False and r['source_mutation_authorized'] is False,'authority_scoped_to_candidate_file_operation')
 req((WORKING_SOURCE_VERSION!='1334.9') or ('v1335' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print({'ok':True,'suite':'v1334.9-file-operations-checkpoint','passed':passed,'total':5})
