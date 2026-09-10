from __future__ import annotations
import subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1340_multi_tool_execution_test_support import *
from multi_tool_execution import *

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=content_manifest(src);r=run_multi_tool_execution(**campaign_args(src,runtime,grant,pres,git));row=r['campaign'];req(r['ok'] and row['campaign_state']=='completed','phase4_integrated_checkpoint')
  req(row['verification_passed'] and row['browser_passed'] and row['service_ready'] and row['service_stopped'],'multi_tool_exit_criteria')
  req(row['verification_reconciliation_id'] and row['service_reconciliation_id'],'reconciliation_evidence_present')
  req(row['workspace_cleaned'] and row['host_recoverable'] and row['orphaned_service_count']==0,'known_recoverable_host_state')
  req(content_manifest(src)==before and row['candidate_only'] and not row['source_application_authorized'] and not row['release_authorized'],'source_and_authority_boundaries')
 print({'ok':True,'suite':'v1340.9-multi-tool-execution-checkpoint','passed':p[0],'total':5})
if __name__=='__main__':main()
