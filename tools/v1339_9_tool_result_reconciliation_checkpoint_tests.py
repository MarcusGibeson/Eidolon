from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1339_tool_result_reconciliation_test_support import *
from tool_result_reconciliation import *

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,cand,op=file_receipt(Path(td));before=sorted((x.relative_to(src).as_posix(),x.read_bytes()) for x in src.rglob('*') if x.is_file())
  r=reconcile_tool_result(tool_code='file_patch',operation_id=op,wrapper_observation={'wrapper_status':'timeout','duplicate_hint':True,'operation_executed_this_request':False},current_workspace_digest='b'*64,runtime_root=runtime);row=r['reconciliation'];req(r['ok'] and row['durable_evidence_found'] and row['outcome_class']=='durable_success','integrated_reconciliation_checkpoint')
  req(row['duplicate_detected'] and row['wrapper_timeout_observed'] and not row['wrapper_timeout_is_product_failure'],'timeout_duplicate_reconciled')
  req(row['safe_to_retry'] is False and row['retry_authorized'] is False and row['retry_executed'] is False,'judgment_never_authority')
  after=sorted((x.relative_to(src).as_posix(),x.read_bytes()) for x in src.rglob('*') if x.is_file());req(before==after,'reconciliation_read_only')
  req(row['content_free'] and not row['raw_tool_output_exposed'] and not row['tool_invoked'],'content_minimized_evidence')
 print({'ok':True,'suite':'v1339.9-tool-result-reconciliation-checkpoint','passed':p[0],'total':5})
if __name__=='__main__':main()
