from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1341_python_implementation_test_support import *
from python_implementation import *

def main():
 p=[0]
 def req(x,n): assert x,n; p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=content_manifest(src);r=run_python_implementation(**implementation_args(src,runtime,grant,pres,git));row=r['python_implementation']
  req(r['ok'] and row['implementation_state']=='completed','python_implementation_checkpoint_completed')
  req(row['compatibility_summary']['removed_public_symbol_count']==0 and row['compatibility_summary']['public_kind_change_count']==0 and row['compatibility_summary']['public_signature_change_count']==0 and row['compatibility_summary']['annotation_regression_count']==0,'public_contract_preserved')
  req(row['compile_passed'] and row['tests_passed'] and row['git_commit_operation_id'],'compiled_tested_committed_candidate')
  req(row['workspace_cleaned'] and row['host_recoverable'] and content_manifest(src)==before,'known_recoverable_source_state')
  req(row['raw_source_exposed'] is False and row['raw_test_command_exposed'] is False and row['candidate_only'] and not row['release_authorized'],'content_minimized_and_authority_bounded')
 print({'ok':True,'suite':'v1341.9-python-implementation-checkpoint','passed':p[0],'total':5})
if __name__=='__main__': main()
