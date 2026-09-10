from __future__ import annotations
import sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1339_tool_result_reconciliation_test_support import *
from tool_result_reconciliation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,cand,pre=process_candidate(Path(td));started=start_candidate_process(wid,[sys.executable,'-c','import time;time.sleep(.8)'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101,invocation_discriminator='reconcile-running');op=started['process_operation']['process_operation_id']
  running=reconcile_tool_result(tool_code='shell',operation_id=op,wrapper_observation={'wrapper_status':'timeout'},current_workspace_digest='b'*64,runtime_root=runtime);rr=running['reconciliation'];req(rr['outcome_class']=='still_running' and rr['retry_disposition']=='wait_and_monitor' and rr['safe_to_retry'] is False,'wrapper_timeout_child_still_running')
  done=wait_terminal(op,runtime,timeout=4);final=reconcile_tool_result(tool_code='shell',operation_id=op,wrapper_observation={'wrapper_status':'timeout'},current_workspace_digest='b'*64,runtime_root=runtime);req(final['reconciliation']['outcome_class']=='durable_success' and final['reconciliation']['wrapper_timeout_is_product_failure'] is False,'late_durable_success_reconciled')
  rid=final['reconciliation']['reconciliation_id'];chat=process_ordinary_chat_development_turn('show tool reconciliation',project_state={'tool_reconciliation_id':rid},runtime_root=runtime);req(chat.get('active') and chat.get('reconciliation',{}).get('reconciliation_id')==rid and chat.get('action_executed') is False,'ordinary_chat_read_only')
  duplicate=reconcile_tool_result(tool_code='shell',operation_id=op,wrapper_observation={'wrapper_status':'returned','duplicate_hint':True,'operation_executed_this_request':False},current_workspace_digest='b'*64,runtime_root=runtime);req(duplicate['reconciliation']['duplicate_detected'] and duplicate['reconciliation']['retry_authorized'] is False,'duplicate_detected_without_retry')
 print({'ok':True,'suite':'v1339.3-5-tool-result-reconciliation-integration','passed':p[0],'total':4})
if __name__=='__main__':main()
