from __future__ import annotations
"""v1339 evidence-first reconciliation of tool outcomes before any retry decision.

This module never invokes or retries a tool. It reconciles a caller's wrapper
observation with sealed durable evidence from v1334-v1338 and reports whether a
retry is epistemically safe. That conclusion never creates execution authority.
"""
import re
from pathlib import Path
from typing import Any, Mapping

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root

CONTRACT_VERSION = "v1339.8"
TOOL_CODES = ("file_patch", "git", "shell", "browser", "service")
WRAPPER_STATES = ("returned", "timeout", "client_error", "disconnected", "unknown")
OUTCOME_CLASSES = ("durable_success", "durable_failure", "still_running", "policy_limited", "partial_or_uncertain", "stale_observation", "unknown")
RECONCILIATION_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "tool_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "release_authorized": False,
    "retry_authorized": False,
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase4_tool_result_reconciliation"


def _path(record_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"reconcile_[a-f0-9]{24}", str(record_id or "")):
        raise ValueError("invalid_reconciliation_id")
    return _root(runtime_root) / "records" / f"{record_id}.json"


def _save(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row.pop("record_digest", None); row["record_digest"] = digest(row); _atomic_json(_path(str(row["reconciliation_id"]), runtime_root), row); return row


def _sealed(path: Path) -> dict[str, Any]:
    row = _read_json(path)
    if not row or row.get("record_digest") != digest({k:v for k,v in row.items() if k!="record_digest"}): return {}
    return row


def _durable(tool_code: str, operation_id: str, runtime_root=None) -> tuple[dict[str, Any], str]:
    if tool_code == "file_patch":
        from structured_file_operations import inspect_file_operation
        result=inspect_file_operation(operation_id,runtime_root=runtime_root); return dict(result.get("file_operation") or {}), str(result.get("status") or "")
    if tool_code == "git":
        from typed_git_operations import inspect_git_operation
        result=inspect_git_operation(operation_id,runtime_root=runtime_root); return dict(result.get("git_operation") or {}), str(result.get("status") or "")
    if tool_code == "shell":
        from typed_process_operations import monitor_candidate_process
        result=monitor_candidate_process(operation_id,runtime_root=runtime_root); return dict(result.get("process_operation") or {}), str(result.get("status") or "")
    if tool_code == "browser":
        from browser_validation import load_browser_validation
        row=load_browser_validation(operation_id,runtime_root=runtime_root); return dict(row or {}), "browser_validation_found" if row else "browser_validation_missing"
    if tool_code == "service":
        from service_orchestration import inspect_service_stack
        result=inspect_service_stack(operation_id,runtime_root=runtime_root); return dict(result.get("service_stack") or {}), str(result.get("status") or "")
    return {}, "tool_code_unknown"


def _workspace_digest(row: Mapping[str, Any]) -> str:
    return str(row.get("source_workspace_digest") or row.get("workspace_digest") or "")


def _state(tool: str, row: Mapping[str, Any]) -> str:
    if not row: return "missing"
    if tool == "file_patch": return "completed" if row.get("action_executed") is True else str(row.get("status") or "observed")
    if tool == "git": return "completed" if row.get("action_executed") is True else str(row.get("status") or "observed")
    if tool == "shell": return str(row.get("process_state") or "unknown")
    if tool == "browser": return str(row.get("validation_status") or "unknown")
    if tool == "service": return str(row.get("stack_state") or "unknown")
    return "unknown"


def _classify(tool: str, row: Mapping[str, Any]) -> tuple[str,str,bool,str]:
    """Return outcome_class, side_effect_state, safe_to_retry, retry_disposition."""
    if not row: return "unknown","unknown",False,"reobserve_before_retry"
    state=_state(tool,row)
    if tool in {"file_patch","git"}:
        # These records exist only after a sealed operation result. Reissuing the
        # exact operation is idempotence checking, but there is nothing useful to retry.
        return "durable_success","durable_completed",False,"retry_not_needed"
    if tool == "shell":
        if state in {"accepted","starting","running","orphan_running"}:
            if state=="orphan_running": return "partial_or_uncertain","uncertain_side_effects",False,"recover_or_escalate"
            return "still_running","active_side_effects",False,"wait_and_monitor"
        if state == "completed" and not row.get("timed_out") and not row.get("log_limit_exceeded"):
            return "durable_success","durable_completed",False,"retry_not_needed"
        if state in {"uncertain","interrupted"} or row.get("timed_out") or row.get("log_limit_exceeded"):
            safe=bool(row.get("safe_retry") is True)
            return "partial_or_uncertain","uncertain_side_effects",safe,"safe_but_requires_fresh_authority" if safe else "recover_or_escalate"
        if state in {"failed","cancelled"}:
            safe=bool(row.get("safe_retry") is True)
            return "durable_failure","possible_partial_side_effects",safe,"safe_but_requires_fresh_authority" if safe else "review_side_effects_before_retry"
        return "unknown","unknown",False,"reobserve_before_retry"
    if tool == "browser":
        if state == "passed": return "durable_success","browser_only",False,"retry_not_needed"
        if state == "policy_limited": return "policy_limited","browser_only",False,"resolve_environment_policy"
        if state == "failed":
            if row.get("failure_domain")=="browser_tool" and row.get("page_rendered") is not True:
                return "durable_failure","browser_only",True,"safe_but_requires_fresh_authority"
            return "durable_failure","possible_local_app_interaction",False,"review_before_retry"
        return "unknown","unknown",False,"reobserve_before_retry"
    if tool == "service":
        if state == "ready": return "durable_success","active_side_effects",False,"retry_not_needed"
        if state == "stopped" and int(row.get("orphaned_service_count") or 0)==0: return "durable_success","cleaned_up",False,"retry_not_needed"
        if state in {"starting"}: return "still_running","active_side_effects",False,"wait_and_monitor"
        if state == "failed":
            if row.get("cleanup_performed") is True and int(row.get("orphaned_service_count") or 0)==0:
                return "durable_failure","possible_candidate_side_effects",False,"review_side_effects_before_retry"
            return "partial_or_uncertain","uncertain_side_effects",False,"recover_or_escalate"
        return "unknown","unknown",False,"reobserve_before_retry"
    return "unknown","unknown",False,"reobserve_before_retry"


def reconcile_tool_result(
    *, tool_code: str, operation_id: str, wrapper_observation: Mapping[str, Any] | None = None,
    current_workspace_digest: str = "", runtime_root=None,
) -> dict[str, Any]:
    tool=str(tool_code or "").strip().lower(); wrapper=dict(wrapper_observation or {}); wrapper_state=str(wrapper.get("wrapper_status") or "unknown")
    if tool not in TOOL_CODES:return {"ok":False,"status":"tool_code_unknown","action_executed":False,**RECONCILIATION_DENIED_AUTHORITY}
    if wrapper_state not in WRAPPER_STATES:wrapper_state="unknown"
    durable,loader_status=_durable(tool,str(operation_id or ""),runtime_root)
    durable_digest=digest(durable) if durable else "";workspace=_workspace_digest(durable)
    supplied_observed_digest=str(wrapper.get("observed_evidence_digest") or "")
    stale=bool(durable and supplied_observed_digest and supplied_observed_digest!=durable_digest)
    if durable and current_workspace_digest and workspace and current_workspace_digest!=workspace:stale=True
    outcome,side_effect,safe,retry=_classify(tool,durable)
    if stale: outcome,side_effect,safe,retry="stale_observation","unknown",False,"reobserve_before_retry"
    duplicate=bool(wrapper.get("duplicate_hint") is True or wrapper.get("operation_executed_this_request") is False and durable)
    wrapper_timeout=wrapper_state=="timeout"
    # A wrapper/client timeout is transport/harness evidence, never by itself
    # proof that the product failed. Durable product evidence is classified
    # separately above.
    wrapper_timeout_product_failure=False
    reconciliation_id="reconcile_"+digest({"contract":CONTRACT_VERSION,"tool":tool,"operation":operation_id,"wrapper_state":wrapper_state,"reported":wrapper.get("reported_status"),"observed_digest":supplied_observed_digest,"durable_digest":durable_digest,"workspace":current_workspace_digest,"duplicate":duplicate})[:24]
    row={
        "contract_version":CONTRACT_VERSION,"reconciliation_id":reconciliation_id,"tool_code":tool,"operation_id_digest":digest(str(operation_id or "")),
        "wrapper_status":wrapper_state,"wrapper_reported_status":str(wrapper.get("reported_status") or "unknown")[:80],"durable_evidence_found":bool(durable),"durable_evidence_digest":durable_digest,
        "durable_loader_status":loader_status[:120],"durable_state":_state(tool,durable),"durable_workspace_digest":workspace,"observation_stale":stale,"duplicate_detected":duplicate,
        "wrapper_timeout_observed":wrapper_timeout,"wrapper_timeout_is_product_failure":wrapper_timeout_product_failure,"outcome_class":outcome,"side_effect_state":side_effect,
        "safe_to_retry":safe,"retry_disposition":retry,"retry_authorized":False,"retry_executed":False,"tool_invoked":False,"action_executed":False,"raw_tool_output_exposed":False,
        "content_free":True,**RECONCILIATION_DENIED_AUTHORITY,
    }
    _save(row,runtime_root)
    return {"ok":bool(durable) and not stale,"status":"tool_result_reconciled" if durable and not stale else "tool_result_reconciliation_incomplete" if not durable else "stale_tool_observation_rejected","reconciliation":public_reconciliation(row),"action_executed":False,**RECONCILIATION_DENIED_AUTHORITY}


def public_reconciliation(row: Mapping[str, Any]) -> dict[str, Any]:
    keys=("contract_version","reconciliation_id","tool_code","operation_id_digest","wrapper_status","wrapper_reported_status","durable_evidence_found","durable_evidence_digest","durable_loader_status","durable_state","durable_workspace_digest","observation_stale","duplicate_detected","wrapper_timeout_observed","wrapper_timeout_is_product_failure","outcome_class","side_effect_state","safe_to_retry","retry_disposition","retry_authorized","retry_executed","tool_invoked","action_executed","raw_tool_output_exposed","content_free")
    out={k:row.get(k) for k in keys};out.update(RECONCILIATION_DENIED_AUTHORITY);return out


def load_reconciliation(record_id: str, *, runtime_root=None) -> dict[str, Any]:
    row=_sealed(_path(str(record_id),runtime_root));return public_reconciliation(row) if row else {}


def process_tool_result_reconciliation_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show tool reconciliation","inspect tool reconciliation","show tool result reconciliation"}:return {"active":False}
    rid=str((project_state or {}).get("tool_reconciliation_id") or "");row=load_reconciliation(rid,runtime_root=runtime_root) if rid else {}
    return {"active":True,"ok":bool(row),"status":"tool_reconciliation_found" if row else "tool_reconciliation_missing","reconciliation":row,"action_executed":False,**RECONCILIATION_DENIED_AUTHORITY}

__all__=["CONTRACT_VERSION","TOOL_CODES","WRAPPER_STATES","OUTCOME_CLASSES","RECONCILIATION_DENIED_AUTHORITY","reconcile_tool_result","public_reconciliation","load_reconciliation","process_tool_result_reconciliation_control"]
