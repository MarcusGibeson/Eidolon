from __future__ import annotations
import sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1339_tool_result_reconciliation_test_support import *
from tool_result_reconciliation import *
from typed_process_operations import *

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,cand,pre=process_candidate(Path(td));timed=start_candidate_process(wid,[sys.executable,'-c','import time;time.sleep(2)'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101,timeout_seconds=.2,invocation_discriminator='reconcile-timeout');op=timed['process_operation']['process_operation_id'];wait_terminal(op,runtime);r=reconcile_tool_result(tool_code='shell',operation_id=op,wrapper_observation={'wrapper_status':'returned','reported_status':'failed'},runtime_root=runtime);row=r['reconciliation'];req(row['outcome_class']=='partial_or_uncertain' and row['side_effect_state']=='uncertain_side_effects','tool_timeout_partial_not_clean_failure')
  req(row['safe_to_retry'] is False and row['retry_authorized'] is False,'uncertain_side_effect_blocks_retry')
  wrong=reconcile_tool_result(tool_code='shell',operation_id=op,wrapper_observation={'wrapper_status':'returned'},current_workspace_digest='c'*64,runtime_root=runtime);req(wrong['reconciliation']['observation_stale'] and wrong['reconciliation']['retry_disposition']=='reobserve_before_retry','workspace_lineage_stale')
  unknown=reconcile_tool_result(tool_code='shell',operation_id='proc_'+'f'*24,wrapper_observation={'wrapper_status':'disconnected'},runtime_root=runtime);req(unknown['reconciliation']['outcome_class']=='unknown' and not unknown['reconciliation']['durable_evidence_found'],'disconnected_missing_evidence_unknown')
  req(unknown['reconciliation']['raw_tool_output_exposed'] is False and unknown['reconciliation']['tool_invoked'] is False and unknown['reconciliation']['release_authorized'] is False,'content_minimized_no_authority')
 print({'ok':True,'suite':'v1339.6-8-tool-result-reconciliation-reliability','passed':p[0],'total':5})
if __name__=='__main__':main()
