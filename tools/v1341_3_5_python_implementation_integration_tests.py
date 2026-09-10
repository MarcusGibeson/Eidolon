from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1341_python_implementation_test_support import *
from python_implementation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn

def main():
 p=[0]
 def req(x,n): assert x,n; p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=content_manifest(src);args=implementation_args(src,runtime,grant,pres,git);r=run_python_implementation(**args);row=r['python_implementation']
  req(r['ok'] and row['implementation_state']=='completed' and row['action_executed'],'candidate_python_change_completed')
  req(row['syntax_valid'] and row['compatibility_passed'] and row['compile_passed'] and row['tests_passed'],'python_verification_chain_passed')
  req(row['file_operation_id'] and row['git_stage_operation_id'] and row['git_commit_operation_id'] and row['compile_reconciliation_id'] and row['test_reconciliation_id'],'evidence_lineage_present')
  req(row['workspace_cleaned'] and row['host_recoverable'] and content_manifest(src)==before and row['selected_source_content_modified'] is False,'candidate_cleanup_and_source_immutability')
  chat=process_ordinary_chat_development_turn('show python implementation checkpoint',project_state={'python_implementation_id':row['python_implementation_id']},runtime_root=runtime);req(chat['active'] and chat['ok'] and chat['action_executed'] is False and chat['python_implementation']['python_implementation_id']==row['python_implementation_id'],'ordinary_chat_read_only_inspection')
  again=run_python_implementation(**args);req(again['status']=='python_implementation_already_exists' and again['action_executed'] is False,'duplicate_operation_not_reexecuted')
 print({'ok':True,'suite':'v1341.3-5-python-implementation-integration','passed':p[0],'total':6})
if __name__=='__main__': main()
