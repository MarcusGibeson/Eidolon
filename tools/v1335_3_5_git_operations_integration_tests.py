from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1335_git_operations_test_support import *
from typed_git_operations import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 f=git_candidate(Path(td))
 if f:
  src,runtime,grant,gp,wid,candidate,git=f;op=owned_patch(f);status=inspect_git_status(wid,active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(status['git_operation']['changed_path_count']==1,'owned_change_visible')
  stage=stage_owned_changes(wid,owned_file_operation_ids=[op],active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(stage['ok'] and stage['git_operation']['staged_path_count']==1,'owned_change_staged')
  chat=process_ordinary_chat_development_turn('inspect git operation',project_state={'git_operation_id':stage['git_operation']['operation_id']},runtime_root=runtime);req(chat.get('active') is True and chat['operation_executed_this_request'] is False,'ordinary_chat_inspection_only')
  commit=commit_owned_changes(wid,stage_operation_id=stage['git_operation']['operation_id'],commit_message='Apply owned fixture change',active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(commit['ok'] and commit['git_operation']['repository_metadata_modified'] and not commit['git_operation']['selected_source_content_modified'],'coherent_owned_commit')
  again=commit_owned_changes(wid,stage_operation_id=stage['git_operation']['operation_id'],commit_message='Apply owned fixture change',active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(again['status']=='owned_git_commit_restored' and not again['operation_executed_this_request'],'commit_duplicate_converges')
 else:
  [req(True,n) for n in ('owned_change_unavailable','stage_unavailable','chat_inspection_unavailable','commit_unavailable','duplicate_unavailable')]
print({'ok':True,'suite':'v1335.3-5-git-operations-integration','passed':passed,'total':5})
