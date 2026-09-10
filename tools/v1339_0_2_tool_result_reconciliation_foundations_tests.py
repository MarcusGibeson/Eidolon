from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1339_tool_result_reconciliation_test_support import *
from tool_result_reconciliation import *

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 req(TOOL_CODES==('file_patch','git','shell','browser','service') and 'timeout' in WRAPPER_STATES,'typed_reconciliation_surface')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,cand,op=file_receipt(Path(td));r=reconcile_tool_result(tool_code='file_patch',operation_id=op,wrapper_observation={'wrapper_status':'timeout','reported_status':'unknown'},current_workspace_digest='b'*64,runtime_root=runtime);row=r['reconciliation'];req(r['ok'] and row['outcome_class']=='durable_success' and row['wrapper_timeout_is_product_failure'] is False,'durable_receipt_overrides_wrapper_timeout')
  req(row['safe_to_retry'] is False and row['retry_disposition']=='retry_not_needed' and row['retry_authorized'] is False,'no_retry_when_result_known')
  stale=reconcile_tool_result(tool_code='file_patch',operation_id=op,wrapper_observation={'wrapper_status':'returned','observed_evidence_digest':'0'*64},current_workspace_digest='b'*64,runtime_root=runtime);req(not stale['ok'] and stale['reconciliation']['observation_stale'] and stale['reconciliation']['outcome_class']=='stale_observation','stale_observation_rejected')
  missing=reconcile_tool_result(tool_code='file_patch',operation_id='fop_'+'0'*24,wrapper_observation={'wrapper_status':'timeout'},runtime_root=runtime);req(not missing['ok'] and missing['reconciliation']['outcome_class']=='unknown' and missing['reconciliation']['safe_to_retry'] is False and missing['reconciliation']['wrapper_timeout_is_product_failure'] is False,'missing_receipt_timeout_remains_unknown')
 print({'ok':True,'suite':'v1339.0-2-tool-result-reconciliation-foundations','passed':p[0],'total':5})
if __name__=='__main__':main()
