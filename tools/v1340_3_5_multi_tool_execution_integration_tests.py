from __future__ import annotations
import subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1340_multi_tool_execution_test_support import *
from multi_tool_execution import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=content_manifest(src);r=run_multi_tool_execution(**campaign_args(src,runtime,grant,pres,git));row=r['campaign'];req(r['ok'] and row['campaign_state']=='completed','real_multi_tool_campaign')
  req(bool(row['file_operation_id'] and row['git_stage_operation_id'] and row['git_commit_operation_id']),'file_and_git_receipts')
  req(row['verification_passed'] and row['verification_process_id'] and row['verification_reconciliation_id'],'process_and_reconciliation')
  req(row['browser_passed'] and row['browser_validation_id'],'real_browser_validation')
  req(row['service_ready'] and row['service_stopped'] and row['service_stack_id'] and row['orphaned_service_count']==0,'service_lifecycle_clean')
  req(row['workspace_cleaned'] and row['host_recoverable'] and content_manifest(src)==before,'workspace_cleanup_source_immutable')
  chat=process_ordinary_chat_development_turn('show multi tool execution',project_state={'multi_tool_execution_id':row['campaign_id']},runtime_root=runtime);req(chat.get('active') and chat.get('campaign',{}).get('campaign_id')==row['campaign_id'] and chat.get('action_executed') is False,'ordinary_chat_read_only')
 print({'ok':True,'suite':'v1340.3-5-multi-tool-execution-integration','passed':p[0],'total':7})
if __name__=='__main__':main()
