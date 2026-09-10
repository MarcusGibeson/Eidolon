from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1342_javascript_typescript_test_support import *
from javascript_typescript_implementation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_javascript_typescript_implementation(**args(src,runtime,grant,pres,git));row=r['javascript_typescript_implementation'];req(r['ok'] and row['implementation_state']=='completed','checkpoint_completed');req(row['compatibility_passed'] and row['compatibility_summary']['export_signature_change_count']==0 and row['compatibility_summary']['added_external_dependency_count']==0,'contracts_preserved');req(row['syntax_or_typecheck_passed'] and row['tests_passed'] and row['git_commit_operation_id'],'check_test_commit');req(row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before,'recoverable_source_state');req(row['candidate_only'] and not row['dependency_installed'] and not row['network_contacted'] and not row['release_authorized'],'content_authority_boundaries')
 print({'ok':True,'suite':'v1342.9-javascript-typescript-checkpoint','passed':p[0],'total':5})
if __name__=='__main__':main()
