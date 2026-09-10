from __future__ import annotations
"""v1202.3-v1202.5 bounded project-owned JavaScript test execution.

Discovers only allowlisted Node test files in the exact isolated workspace and
runs them with Node's built-in test runner. No dependencies are installed, no
network-capable modules are permitted in discovered tests, and no repair/apply
or release authority is granted.
"""
import hashlib, os, re, shutil, subprocess
from pathlib import Path
from typing import Any, Mapping
from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from isolated_implementation_workspace import _record_path, _workspace_root, _verify_record
from structured_development_generation import _safe_relative

SCHEMA_VERSION="1"; CONTRACT_VERSION="v1202.5"
MAX_TEST_FILES=12; MAX_TEST_FILE_BYTES=256*1024; MAX_TEST_TOTAL_BYTES=1024*1024; TEST_TIMEOUT_SECONDS=12
TEST_SUFFIXES=(".test.js", ".test.mjs", ".test.cjs")
FORBIDDEN_MODULES=("node:http","http","node:https","https","node:net","net","node:dgram","dgram","node:tls","tls","node:child_process","child_process","node:worker_threads","worker_threads")


def _path(pid:str,rev:int,runtime_root=None)->Path:
    return _store_root(runtime_root)/"project_owned_javascript_tests"/pid/f"revision-{int(rev)}.json"

def _valid(r:Mapping[str,Any])->bool:
    supplied=str(r.get("test_execution_digest") or "")
    return bool(supplied and supplied==_digest({k:v for k,v in r.items() if k!="test_execution_digest"}))

def _diag(*parts:str)->str:
    text="\n".join(str(x or "")[:4096] for x in parts)
    return hashlib.sha256(text.encode("utf-8",errors="replace")).hexdigest()

def _discover(root:Path, workspace:Mapping[str,Any]):
    rows=[]
    for row in workspace.get("files") or []:
        rel=str(row.get("relative_path") or "")
        if not rel.startswith("tests/") or not rel.endswith(TEST_SUFFIXES):
            continue
        safe=_safe_relative(rel); path=root/safe
        if not path.is_file() or path.is_symlink():
            return None,{"ok":False,"status":"project_test_file_rejected"}
        size=path.stat().st_size
        if size>MAX_TEST_FILE_BYTES:
            return None,{"ok":False,"status":"project_test_budget_exceeded"}
        rows.append((safe,path,size))
    rows.sort(key=lambda x:x[0])
    if not rows:
        return None,{"ok":False,"status":"project_tests_not_found"}
    if len(rows)>MAX_TEST_FILES or sum(x[2] for x in rows)>MAX_TEST_TOTAL_BYTES:
        return None,{"ok":False,"status":"project_test_budget_exceeded"}
    return rows,{}

def _network_contract_ok(text:str)->bool:
    for module in FORBIDDEN_MODULES:
        escaped=re.escape(module)
        if re.search(rf"(?:require\s*\(\s*|from\s+|import\s*\(\s*)['\"]{escaped}['\"]",text):
            return False
    return True

def execute_or_resume_project_javascript_tests(proposal_id:str,*,expected_revision:int,expected_revision_digest:str,expected_workspace_digest:str,runtime_root=None,node_executable:str|None=None)->dict[str,Any]:
    with _proposal_lock(proposal_id,runtime_root):
        workspace=_read_json(_record_path(proposal_id,expected_revision,runtime_root))
        if not workspace: return {"ok":False,"status":"workspace_missing"}
        if workspace.get("proposal_revision_digest")!=expected_revision_digest: return {"ok":False,"status":"stale_proposal_revision"}
        if workspace.get("workspace_digest")!=expected_workspace_digest: return {"ok":False,"status":"stale_workspace_revision"}
        root=_workspace_root(proposal_id,expected_revision,str(workspace.get("generation_digest") or ""),runtime_root)
        if not _verify_record(workspace,root): return {"ok":False,"status":"workspace_record_invalid"}
        existing=_read_json(_path(proposal_id,expected_revision,runtime_root))
        if existing:
            return ({**existing,"operation_status":"resumed"} if _valid(existing) and existing.get("workspace_digest")==expected_workspace_digest else {"ok":False,"status":"project_test_record_invalid"})
        discovered,error=_discover(root,workspace)
        if discovered is None: return error
        node=node_executable or shutil.which("node")
        if not node: return {"ok":False,"status":"node_unavailable"}
        for rel,path,_ in discovered:
            try: text=path.read_text(encoding="utf-8")
            except (OSError,UnicodeError): return {"ok":False,"status":"project_test_source_unreadable"}
            if not _network_contract_ok(text):
                return {"ok":False,"status":"project_test_network_capability_rejected","test_path_digest":hashlib.sha256(rel.encode()).hexdigest()}
        env={"PATH":os.path.dirname(node),"LANG":"C","LC_ALL":"C","NO_COLOR":"1","CI":"1","HOME":str(_store_root(runtime_root)/"private_test_home")}
        results=[]
        for rel,path,_ in discovered:
            try:
                cp=subprocess.run([node,"--test",str(path)],cwd=str(root),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=TEST_TIMEOUT_SECONDS,check=False)
                results.append({"test_path_digest":hashlib.sha256(rel.encode()).hexdigest(),"exit_class":"zero" if cp.returncode==0 else "nonzero","passed":cp.returncode==0,"output_digest":_diag(cp.stdout.decode(errors="replace"),cp.stderr.decode(errors="replace"))})
            except subprocess.TimeoutExpired as e:
                results.append({"test_path_digest":hashlib.sha256(rel.encode()).hexdigest(),"exit_class":"timeout","passed":False,"output_digest":_diag(str(e))})
            except OSError as e:
                results.append({"test_path_digest":hashlib.sha256(rel.encode()).hexdigest(),"exit_class":"spawn_failed","passed":False,"output_digest":_diag(type(e).__name__)})
        passed=all(x["passed"] for x in results)
        record={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"ok":True,"status":"project_javascript_tests_passed" if passed else "project_javascript_tests_failed","passed":passed,"proposal_id":proposal_id,"proposal_revision":int(expected_revision),"proposal_revision_digest":expected_revision_digest,"planning_digest":workspace.get("planning_digest"),"generation_digest":workspace.get("generation_digest"),"workspace_digest":expected_workspace_digest,"approval_receipt_digest":workspace.get("approval_receipt_digest"),"test_file_count":len(discovered),"command_count":len(results),"results":results,"network_allowed":False,"dependencies_installed":False,"selected_project_modified":False,"source_modified":False,"repair_authorized":False,"apply_authorized":False,"release_authorized":False,"authority_granted":False}
        record["test_execution_digest"]=_digest(record); _atomic_json(_path(proposal_id,expected_revision,runtime_root),record)
        return {**record,"operation_status":"created"}

def public_project_javascript_tests(record:Mapping[str,Any])->dict[str,Any]:
    return {"ok":bool(record.get("ok")),"status":str(record.get("status") or ""),"passed":bool(record.get("passed")),"proposal_id":str(record.get("proposal_id") or ""),"proposal_revision":int(record.get("proposal_revision") or 0),"workspace_digest":str(record.get("workspace_digest") or ""),"test_execution_digest":str(record.get("test_execution_digest") or ""),"test_file_count":int(record.get("test_file_count") or 0),"command_count":int(record.get("command_count") or 0),"passed_result_count":sum(1 for x in record.get("results") or [] if x.get("passed")),"network_allowed":False,"dependencies_installed":False,"private_path_exposed":False,"private_content_exposed":False,"raw_output_exposed":False,"selected_project_modified":False,"source_modified":False,"repair_authorized":False,"apply_authorized":False,"release_authorized":False,"authority_granted":False}
