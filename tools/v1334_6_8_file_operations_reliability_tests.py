from __future__ import annotations
import json,os,sys,tempfile
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
 src,runtime,grant,wid,root=candidate(Path(td));wp=precondition(runtime,'file_patch')
 bad=patch_candidate_file(wid,'app.py',expected_content_digest='0'*64,patches=[{'type':'replace_text','old':'hello','new':'x'}],active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);req(bad['status']=='stale_candidate_content_digest','stale_digest_blocks')
 d=sha(root/'README.md');(root/'docs').mkdir();(root/'docs/README.md').write_text('existing');bad=move_candidate_file(wid,'README.md','docs/README.md',expected_source_digest=d,active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);req(bad['status']=='move_destination_exists','move_collision_blocks')
 d=sha(root/'app.py');first=patch_candidate_file(wid,'app.py',expected_content_digest=d,patches=[{'type':'replace_text','old':'hello','new':'hi'}],active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);again=patch_candidate_file(wid,'app.py',expected_content_digest=d,patches=[{'type':'replace_text','old':'hello','new':'hi'}],active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);req(first['ok'] and again['status']=='candidate_file_patch_restored' and not again['operation_executed_this_request'],'duplicate_converges')
 if hasattr(os,'symlink'):
  try:
   os.symlink(src/'app.py',root/'linked.py');bad=patch_candidate_file(wid,'linked.py',expected_content_digest=sha(src/'app.py'),patches=[{'type':'replace_text','old':'hello','new':'bad'}],active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);req('link_or_junction' in bad['status'],'symlink_rejected')
  except (OSError,NotImplementedError):req(True,'symlink_platform_unavailable_classified')
 else:req(True,'symlink_platform_unavailable_classified')
 opid=first['file_operation']['operation_id'];rec=runtime/'development_campaigns'/'phase4_file_operations'/'records'/f'{opid}.json';data=json.loads(rec.read_text());data['after_digest']='f'*64;rec.write_text(json.dumps(data));req(inspect_file_operation(opid,runtime_root=runtime)['status']=='file_operation_missing_or_invalid','tamper_rejected')
print({'ok':True,'suite':'v1334.6-8-file-operations-reliability','passed':passed,'total':5})
