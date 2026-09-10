from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping
from ordinary_chat_development_campaign import _atomic_json,_digest,_proposal_lock,_read_json,_store_root
from javascript_tool_implementation_foundations import run_or_resume_javascript_tool_implementation, load_javascript_tool_checkpoint
from project_owned_javascript_tests import execute_or_resume_project_javascript_tests,_path as _tests_path,_valid as _tests_valid
SCHEMA_VERSION="1"; CONTRACT_VERSION="v1202.5"; STAGES=("proposal","approval","planning","generation","workspace","validation","project_tests")

def _path(pid:str,rev:int,runtime_root=None)->Path:return _store_root(runtime_root)/"javascript_tool_test_checkpoints"/pid/f"revision-{int(rev)}.json"
def _valid(r:Mapping[str,Any])->bool:
 s=str(r.get("checkpoint_digest") or "");return bool(s and s==_digest({k:v for k,v in r.items() if k!="checkpoint_digest"}))
def run_or_resume_javascript_tool_with_tests(proposal_id:str,*,expected_revision:int,expected_revision_digest:str,runtime_root=None,provider_generate:Callable[[str],str]|None=None,node_executable:str|None=None)->dict[str,Any]:
 base=run_or_resume_javascript_tool_implementation(proposal_id,expected_revision=expected_revision,expected_revision_digest=expected_revision_digest,runtime_root=runtime_root,provider_generate=provider_generate,node_executable=node_executable)
 if not base.get("checkpoint_digest"):return {**base,"failed_stage":base.get("failed_stage","implementation")}
 tests=execute_or_resume_project_javascript_tests(proposal_id,expected_revision=expected_revision,expected_revision_digest=expected_revision_digest,expected_workspace_digest=str(base.get("workspace_digest") or ""),runtime_root=runtime_root,node_executable=node_executable)
 if not tests.get("test_execution_digest") or tests.get("passed") is not True:return {"ok":False,"status":tests.get("status","project_tests_failed"),"failed_stage":"project_tests","test_execution_digest":tests.get("test_execution_digest",""),"repair_authorized":False}
 with _proposal_lock(proposal_id,runtime_root):
  path=_path(proposal_id,expected_revision,runtime_root); existing=_read_json(path)
  if existing:return ({**existing,"operation_status":"resumed"} if _valid(existing) else {"ok":False,"status":"javascript_tool_test_checkpoint_invalid"})
  stages=list(base.get("stage_receipts") or [])
  row={"sequence":7,"stage":"project_tests","status":"project_owned_tests_passed","passed":True,"artifact_digest":tests.get("test_execution_digest")};row["stage_receipt_digest"]=_digest(row);stages.append(row)
  record={k:v for k,v in base.items() if k not in {"checkpoint_digest","operation_status","stage_receipts","stage_count","stage_lineage_digest","status","contract_version"}}
  record.update({"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"ok":True,"status":"javascript_tool_tests_ready_for_operator_review","stage_receipts":stages,"stage_count":7,"stage_lineage_digest":_digest(stages),"project_test_execution_digest":tests.get("test_execution_digest"),"project_test_summary":{"passed":True,"test_file_count":tests.get("test_file_count",0),"command_count":tests.get("command_count",0),"passed_result_count":sum(1 for x in tests.get("results") or [] if x.get("passed"))},"operator_review_required":True,"repair_authorized":False,"apply_authorized":False,"release_authorized":False,"authority_granted":False})
  record["checkpoint_digest"]=_digest(record);_atomic_json(path,record);return {**record,"operation_status":"created"}
def load_javascript_tool_test_checkpoint(pid:str,rev:int,runtime_root=None)->dict[str,Any]:
 r=_read_json(_path(pid,rev,runtime_root));return r if r and _valid(r) else {}
def public_javascript_tool_test_checkpoint(r:Mapping[str,Any])->dict[str,Any]:
 if not r:return {}
 return {"ok":bool(r.get("ok")),"status":str(r.get("status") or ""),"proposal_id":str(r.get("proposal_id") or ""),"proposal_revision":int(r.get("proposal_revision") or 0),"checkpoint_digest":str(r.get("checkpoint_digest") or ""),"stage_count":int(r.get("stage_count") or 0),"stage_lineage_digest":str(r.get("stage_lineage_digest") or ""),"stage_receipts":list(r.get("stage_receipts") or []),"change_summary":dict(r.get("change_summary") or {}),"test_summary":dict(r.get("test_summary") or {}),"project_test_summary":dict(r.get("project_test_summary") or {}),"working_result_available":True,"operator_review_required":True,"private_path_exposed":False,"private_content_exposed":False,"raw_output_exposed":False,"selected_project_modified":False,"source_modified":False,"implementation_applied":False,"repair_authorized":False,"apply_authorized":False,"release_authorized":False,"authority_granted":False}
