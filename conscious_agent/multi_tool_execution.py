from __future__ import annotations
"""v1340 bounded multi-tool execution checkpoint over Phase 4 contracts.

A campaign creates an owned disposable Git worktree, performs one structured
owned file patch and coherent candidate commit, runs a bounded verification
process, validates candidate UI in a real browser, starts/stops a declared
loopback service stack, reconciles durable results, and cleans the disposable
workspace. Every mutation remains candidate-only and requires the exact active
standing grant plus the lower-layer sealed preconditions.
"""
import hashlib
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from workspace_isolation import create_disposable_workspace, cleanup_disposable_workspace
from structured_file_operations import patch_candidate_file
from typed_git_operations import stage_owned_changes, commit_owned_changes
from typed_process_operations import start_candidate_process, monitor_candidate_process, stop_candidate_process
from browser_validation import validate_browser_candidate
from service_orchestration import start_service_stack, stop_service_stack
from tool_result_reconciliation import reconcile_tool_result

CONTRACT_VERSION = "v1340.8"
REQUIRED_PRECONDITIONS = ("git", "file_patch", "shell", "browser", "service")
TERMINAL_PROCESS_STATES = {"completed","failed","cancelled","interrupted","uncertain"}
MAX_VERIFICATION_WAIT_SECONDS = 30.0
MULTI_TOOL_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "source_mutation_authorized": False,
    "source_application_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase4_multi_tool_execution"


def _path(campaign_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"toolrun_[a-f0-9]{24}", str(campaign_id or "")): raise ValueError("invalid_multi_tool_campaign_id")
    return _root(runtime_root) / "records" / f"{campaign_id}.json"


def _sealed(path: Path) -> dict[str, Any]:
    row=_read_json(path)
    if not row or row.get("record_digest")!=digest({k:v for k,v in row.items() if k!="record_digest"}):return {}
    return row


def _save(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row.pop("record_digest",None);row["record_digest"]=digest(row);_atomic_json(_path(str(row["campaign_id"]),runtime_root),row);return row


def _public(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version":CONTRACT_VERSION,"campaign_id":row.get("campaign_id"),"source_workspace_digest":row.get("source_workspace_digest"),
        "workspace_id":row.get("workspace_id"),"campaign_state":row.get("campaign_state"),"failure_stage":row.get("failure_stage") or "",
        "file_operation_id":row.get("file_operation_id") or "","git_stage_operation_id":row.get("git_stage_operation_id") or "","git_commit_operation_id":row.get("git_commit_operation_id") or "",
        "verification_process_id":row.get("verification_process_id") or "","verification_reconciliation_id":row.get("verification_reconciliation_id") or "",
        "browser_validation_id":row.get("browser_validation_id") or "","service_stack_id":row.get("service_stack_id") or "","service_reconciliation_id":row.get("service_reconciliation_id") or "",
        "verification_passed":row.get("verification_passed") is True,"browser_passed":row.get("browser_passed") is True,"service_ready":row.get("service_ready") is True,
        "service_stopped":row.get("service_stopped") is True,"workspace_cleaned":row.get("workspace_cleaned") is True,"orphaned_service_count":int(row.get("orphaned_service_count") or 0),
        "host_recoverable":row.get("host_recoverable") is True,"selected_source_content_modified":False,"candidate_only":True,"raw_commands_exposed":False,"raw_patch_content_exposed":False,
        "tool_retry_executed":False,"content_free":True,"action_executed":row.get("action_executed") is True,**MULTI_TOOL_DENIED_AUTHORITY,
    }


def _spec_digest(spec: Mapping[str, Any]) -> str:
    # Content is not persisted; only a stable digest enters campaign identity.
    return digest(spec)


def run_multi_tool_execution(
    *, source_root: str | Path, source_workspace_digest: str, active_grant: Mapping[str, Any], precondition_record_ids: Mapping[str, str],
    file_relative_path: str, expected_content_digest: str, patches: Sequence[Mapping[str, Any]], commit_message: str,
    verification_argv: Sequence[str], browser_target: Mapping[str, Any], browser_interactions: Sequence[Mapping[str, Any]]=(), browser_checks: Sequence[Mapping[str, Any]]=(),
    service_definitions: Sequence[Mapping[str, Any]]=(), runtime_root=None, now_unix: int|None=None, git_executable: str|None=None, browser_executable: str|None=None,
    cleanup_on_complete: bool=True,
) -> dict[str, Any]:
    pres={str(k):str(v) for k,v in precondition_record_ids.items()}
    if any(not pres.get(k) for k in REQUIRED_PRECONDITIONS):return {"ok":False,"status":"complete_phase4_preconditions_required","action_executed":False,**MULTI_TOOL_DENIED_AUTHORITY}
    material={"contract":CONTRACT_VERSION,"source_workspace_digest":source_workspace_digest,"grant":active_grant.get("grant_digest"),"preconditions":pres,
              "file":digest({"path":file_relative_path,"expected":expected_content_digest,"patches":patches}),"commit":hashlib.sha256(str(commit_message).encode()).hexdigest(),
              "verification":_spec_digest({"argv":verification_argv}),"browser":_spec_digest({"target":browser_target,"interactions":browser_interactions,"checks":browser_checks}),
              "services":_spec_digest({"definitions":service_definitions}),"cleanup":bool(cleanup_on_complete)}
    cid="toolrun_"+digest(material)[:24];existing=_sealed(_path(cid,runtime_root))
    if existing:return {"ok":existing.get("campaign_state")=="completed","status":"multi_tool_campaign_already_exists","campaign":_public(existing),"action_executed":False,**MULTI_TOOL_DENIED_AUTHORITY}
    row={"contract_version":CONTRACT_VERSION,"campaign_id":cid,"source_workspace_digest":source_workspace_digest,"grant_digest":active_grant.get("grant_digest"),"precondition_digest":digest(pres),"campaign_state":"starting","failure_stage":"","workspace_id":"","file_operation_id":"","git_stage_operation_id":"","git_commit_operation_id":"","verification_process_id":"","verification_reconciliation_id":"","browser_validation_id":"","service_stack_id":"","service_reconciliation_id":"","verification_passed":False,"browser_passed":False,"service_ready":False,"service_stopped":False,"workspace_cleaned":False,"orphaned_service_count":0,"host_recoverable":False,"action_executed":False,**MULTI_TOOL_DENIED_AUTHORITY};_save(row,runtime_root)
    workspace_id="";service_id="";process_id=""
    def fail(stage: str): row["campaign_state"]="failed";row["failure_stage"]=stage
    try:
        isolated=create_disposable_workspace(source_root=source_root,source_workspace_digest=source_workspace_digest,active_grant=active_grant,precondition_record_id=pres["git"],mode="git_branch_worktree",retention_rule="retain_for_review",runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
        if not isolated.get("ok") or not isolated.get("workspace_created"): raise RuntimeError("workspace_isolation")
        workspace_id=str(isolated["workspace_id"]);row["workspace_id"]=workspace_id;row["action_executed"]=True;_save(row,runtime_root)
        file_result=patch_candidate_file(workspace_id,file_relative_path,expected_content_digest=expected_content_digest,patches=patches,active_grant=active_grant,precondition_record_id=pres["file_patch"],runtime_root=runtime_root,now_unix=now_unix)
        if not file_result.get("ok"): raise RuntimeError("file_operation")
        row["file_operation_id"]=file_result["file_operation"]["operation_id"];_save(row,runtime_root)
        stage=stage_owned_changes(workspace_id,owned_file_operation_ids=[row["file_operation_id"]],active_grant=active_grant,precondition_record_id=pres["git"],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
        if not stage.get("ok"):raise RuntimeError("git_stage")
        row["git_stage_operation_id"]=stage["git_operation"]["operation_id"];_save(row,runtime_root)
        commit=commit_owned_changes(workspace_id,stage_operation_id=row["git_stage_operation_id"],commit_message=commit_message,active_grant=active_grant,precondition_record_id=pres["git"],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
        if not commit.get("ok"):raise RuntimeError("git_commit")
        row["git_commit_operation_id"]=commit["git_operation"]["operation_id"];_save(row,runtime_root)
        process=start_candidate_process(workspace_id,verification_argv,active_grant=active_grant,precondition_record_id=pres["shell"],runtime_root=runtime_root,now_unix=now_unix,timeout_seconds=20,invocation_discriminator=f"v1340:{cid}:verify")
        if not process.get("ok"):raise RuntimeError("verification_start")
        process_id=process["process_operation"]["process_operation_id"];row["verification_process_id"]=process_id;_save(row,runtime_root)
        deadline=time.monotonic()+MAX_VERIFICATION_WAIT_SECONDS;observed={}
        while time.monotonic()<deadline:
            observed=monitor_candidate_process(process_id,runtime_root=runtime_root);state=(observed.get("process_operation") or {}).get("process_state")
            if state in TERMINAL_PROCESS_STATES:break
            time.sleep(.05)
        pr=(observed.get("process_operation") or {});row["verification_passed"]=pr.get("process_state")=="completed" and pr.get("return_code")==0 and not pr.get("timed_out") and not pr.get("log_limit_exceeded")
        reconciled=reconcile_tool_result(tool_code="shell",operation_id=process_id,wrapper_observation={"wrapper_status":"returned","reported_status":pr.get("process_state")},current_workspace_digest=source_workspace_digest,runtime_root=runtime_root);row["verification_reconciliation_id"]=(reconciled.get("reconciliation") or {}).get("reconciliation_id") or "";_save(row,runtime_root)
        if not row["verification_passed"]:raise RuntimeError("verification_failed")
        browser=validate_browser_candidate(workspace_id,target=browser_target,active_grant=active_grant,precondition_record_id=pres["browser"],interactions=browser_interactions,checks=browser_checks,browser_executable=browser_executable,runtime_root=runtime_root,now_unix=now_unix)
        row["browser_validation_id"]=(browser.get("browser_validation") or {}).get("browser_validation_id") or "";row["browser_passed"]=browser.get("ok") is True;_save(row,runtime_root)
        if not row["browser_passed"]:raise RuntimeError("browser_validation")
        if service_definitions:
            service=start_service_stack(workspace_id,service_definitions,active_grant=active_grant,service_precondition_record_id=pres["service"],process_precondition_record_id=pres["shell"],runtime_root=runtime_root,now_unix=now_unix)
            row["service_stack_id"]=(service.get("service_stack") or {}).get("service_stack_id") or "";service_id=row["service_stack_id"];row["service_ready"]=service.get("ok") is True;_save(row,runtime_root)
            if not row["service_ready"]:raise RuntimeError("service_start")
            stopped=stop_service_stack(service_id,active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix);row["service_stopped"]=stopped.get("ok") is True;row["orphaned_service_count"]=int((stopped.get("service_stack") or {}).get("orphaned_service_count") or 0)
            sr=reconcile_tool_result(tool_code="service",operation_id=service_id,wrapper_observation={"wrapper_status":"returned","reported_status":"stopped"},current_workspace_digest=source_workspace_digest,runtime_root=runtime_root);row["service_reconciliation_id"]=(sr.get("reconciliation") or {}).get("reconciliation_id") or "";_save(row,runtime_root)
            if not row["service_stopped"] or row["orphaned_service_count"]:raise RuntimeError("service_cleanup")
        else: row["service_stopped"]=True
        row["campaign_state"]="verified";_save(row,runtime_root)
    except Exception as error:
        fail(str(error));_save(row,runtime_root)
    finally:
        if service_id and not row.get("service_stopped"):
            try:
                stopped=stop_service_stack(service_id,active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix);row["service_stopped"]=stopped.get("ok") is True;row["orphaned_service_count"]=int((stopped.get("service_stack") or {}).get("orphaned_service_count") or 0)
            except Exception:pass
        if process_id and not row.get("verification_passed"):
            try:
                observed=monitor_candidate_process(process_id,runtime_root=runtime_root);state=(observed.get("process_operation") or {}).get("process_state")
                if state not in TERMINAL_PROCESS_STATES:stop_candidate_process(process_id,active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix)
            except Exception:pass
        if workspace_id and cleanup_on_complete:
            try:
                cleaned=cleanup_disposable_workspace(workspace_id,active_grant=active_grant,discard_owned_changes=True,runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable);row["workspace_cleaned"]=cleaned.get("cleaned") is True
            except Exception:row["workspace_cleaned"]=False
        row["host_recoverable"]=bool((not service_id or row.get("service_stopped")) and row.get("orphaned_service_count",0)==0 and (not cleanup_on_complete or row.get("workspace_cleaned")))
        if row.get("campaign_state")=="verified" and row["host_recoverable"]:row["campaign_state"]="completed"
        _save(row,runtime_root)
    ok=row.get("campaign_state")=="completed"
    return {"ok":ok,"status":"multi_tool_execution_completed" if ok else "multi_tool_execution_failed","campaign":_public(row),"action_executed":row.get("action_executed") is True,**MULTI_TOOL_DENIED_AUTHORITY}


def load_multi_tool_execution(campaign_id: str, *, runtime_root=None) -> dict[str, Any]:
    row=_sealed(_path(str(campaign_id),runtime_root));return _public(row) if row else {}


def process_multi_tool_execution_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show tool execution checkpoint","inspect multi tool execution","show multi tool execution"}:return {"active":False}
    cid=str((project_state or {}).get("multi_tool_execution_id") or "");row=load_multi_tool_execution(cid,runtime_root=runtime_root) if cid else {}
    return {"active":True,"ok":bool(row),"status":"multi_tool_execution_found" if row else "multi_tool_execution_missing","campaign":row,"action_executed":False,**MULTI_TOOL_DENIED_AUTHORITY}

__all__=["CONTRACT_VERSION","REQUIRED_PRECONDITIONS","MULTI_TOOL_DENIED_AUTHORITY","run_multi_tool_execution","load_multi_tool_execution","process_multi_tool_execution_control"]
