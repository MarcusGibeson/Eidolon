from __future__ import annotations

"""Strictly read-only v1219.9 supervised repaired-candidate rollback checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from conversational_supervised_repaired_candidate_rollback import CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, ROLLBACK_RESULT_STATUSES, _AUTHORIZATION, public_supervised_repaired_candidate_rollback
from operator_repaired_candidate_apply_result_review import _rollback_authorization_phrase

CONTRACT_VERSION = "v1219.9"
_EXCLUDED = {"data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "reports"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest=hashlib.sha256(); count=0
    for base, dirs, files in os.walk(root):
        dirs[:]=sorted(name for name in dirs if name not in _EXCLUDED)
        for name in sorted(files):
            path=Path(base)/name
            if path.suffix.lower() in {".pyc",".pyo"}: continue
            relative=path.relative_to(root).as_posix(); content=path.read_bytes()
            digest.update(relative.encode()+b"\0"+hashlib.sha256(content).digest()); count+=1
    return digest.hexdigest(),count


def _synthetic_prepared() -> dict[str, Any]:
    proposal_id="devc_"+"1"*24; rollback_digest="a"*64
    row={"ok":True,"schema_version":"1","contract_version":RETAINED_CONTRACT_VERSION,
        "status":"supervised_repaired_candidate_rollback_prepared","proposal_id":proposal_id,
        "proposal_revision":1,"failed_attempt_number":2,"repair_attempt_number":1,
        "apply_attempt_number":1,"rollback_attempt_number":1,"rollback_attempt_limit":1,
        "rollback_proposal_digest":rollback_digest,"supervised_repaired_candidate_apply_digest":"b"*64,
        "supervised_repaired_candidate_apply_result_digest":"c"*64,"source_workspace_digest":"d"*64,
        "repair_workspace_digest":"e"*64,"apply_plan_digest":"f"*64,
        "apply_authorization_receipt_digest":"1"*64,"rollback_manifest_digest":"2"*64,
        "supervised_repaired_candidate_rollback_digest":"3"*64,
        "authorization_phrase":_rollback_authorization_phrase(rollback_digest,proposal_id,1,2),
        "operation_count":1,"operation_path_digests":["4"*64],"phase":"prepared",
        "operator_review_required":True,"rollback_result_review_required":True,
        "runtime_records_external":True,"provider_contacted":False,"tests_executed":False,
        "retest_executed":False,"repair_executed":False,"apply_executed":False,
        "rollback_executed":False,"project_modified":False,"selected_project_modified":False,
        "source_modified":False,"rollback_execution_authorized":False,"rollback_authorized":False,
        "apply_execution_authorized":False,"apply_authorized":False,"repair_execution_authorized":False,
        "provider_contact_authorized":False,"test_execution_authorized":False,"retest_authorized":False,
        "install_authorized":False,"promotion_authorized":False,"release_authorized":False,
        "model_management_authorized":False,"authority_granted":False}
    return public_supervised_repaired_candidate_rollback(row)


def _synthetic_result(prepared: dict[str,Any], *, completed: bool, recovered: bool=False) -> dict[str,Any]:
    if completed:
        status=("supervised_repaired_candidate_rollback_completed_recovered" if recovered
                else "supervised_repaired_candidate_rollback_completed")
    else:
        status=("interrupted_repaired_candidate_rollback_recovered_to_applied_state" if recovered
                else "supervised_repaired_candidate_rollback_failed_applied_state_restored")
    row={**prepared,"ok":completed,"status":status,"phase":"sealed",
        "authorization_receipt_digest":"5"*64,"authorization_consumption_count":1,
        "restored_count":1 if completed else 0,"restored_path_digests":["4"*64] if completed else [],
        "rollback_executed":completed,"project_modified":not completed,
        "selected_project_modified":not completed,"rollback_execution_authorized":True,
        "rollback_authorized":True,"recovery_count":1 if recovered else 0,
        "supervised_repaired_candidate_rollback_result_digest":"6"*64}
    return public_supervised_repaired_candidate_rollback(row)


def build_supervised_repaired_candidate_rollback_checkpoint(*,
        source_root: str|Path|None=None, runtime_root: str|Path|None=None) -> dict[str,Any]:
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime=Path(runtime_root) if runtime_root is not None else None
    runtime_existed=runtime.exists() if runtime is not None else False
    before,count=_tree_signature(source); checks=[]; check=lambda value: checks.append(bool(value))
    prepared=_synthetic_prepared(); completed=_synthetic_result(prepared,completed=True)
    recovered=_synthetic_result(prepared,completed=True,recovered=True)
    failed=_synthetic_result(prepared,completed=False)
    interrupted=_synthetic_result(prepared,completed=False,recovered=True)
    check(prepared.get("ok") is True); check(prepared.get("phase")=="prepared")
    check(prepared.get("rollback_attempt_number")==1); check(prepared.get("rollback_attempt_limit")==1)
    check(_AUTHORIZATION.fullmatch(str(prepared.get("authorization_phrase") or "")) is not None)
    check(prepared.get("rollback_authorized") is False); check(prepared.get("rollback_executed") is False)
    for row in (completed,recovered):
        check(row.get("ok") is True); check(row.get("rollback_authorized") is True)
        check(row.get("rollback_executed") is True); check(row.get("selected_project_modified") is False)
        check(row.get("authorization_consumption_count")==1)
    for row in (failed,interrupted):
        check(row.get("ok") is False); check(row.get("rollback_authorized") is True)
        check(row.get("rollback_executed") is False); check(row.get("selected_project_modified") is True)
        check(row.get("authorization_consumption_count")==1)
    for row in (prepared,completed,recovered,failed,interrupted):
        check(row.get("content_free") is True); check(row.get("private_path_exposed") is False)
        check(row.get("private_content_exposed") is False); check(row.get("rollback_content_exposed") is False)
        check(row.get("provider_contacted") is False); check(row.get("tests_executed") is False)
        check(row.get("install_authorized") is False); check(row.get("promotion_authorized") is False)
        check(row.get("release_authorized") is False); check(row.get("authority_granted") is False)
    check(set(ROLLBACK_RESULT_STATUSES)=={completed["status"],recovered["status"],failed["status"],interrupted["status"]})
    check(RETAINED_CONTRACT_VERSION=="v1219.8")
    module=(source/"conscious_agent"/"conversational_supervised_repaired_candidate_rollback.py").read_text()
    check("process_supervised_repaired_candidate_rollback_control" in (source/"conscious_agent"/"ordinary_chat_development_campaign.py").read_text())
    check("LocalModelClient" not in module); check('"release_authorized": True' not in module)
    registry=inspect_checkpoint_registry(source_root=source)
    descriptor=next((r for r in registry["checkpoints"] if r["checkpoint_id"]=="supervised-repaired-candidate-rollback-checkpoint"),None)
    check(descriptor is not None); check((descriptor or {}).get("contract_version")==CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True); check((descriptor or {}).get("post_available") is False)
    after,after_count=_tree_signature(source); check(after==before and after_count==count)
    check(runtime is None or runtime.exists()==runtime_existed)
    summary={"rollback_result_outcome_count":len(ROLLBACK_RESULT_STATUSES),"rollback_attempt_limit":1,
        "exact_v1218_authorization_required":True,"sealed_v1217_manifest_required":True,
        "selected_project_scope_bound":True,"operator_review_required":True,
        "checkpoint_rollback_executed":False,"authority_preserved":True}
    return {"ok":all(checks),"contract_version":CONTRACT_VERSION,
        "retained_contract_version":RETAINED_CONTRACT_VERSION,"passed":sum(checks),"total":len(checks),
        "summary":summary,"read_only":True,"post_available":False,"synthetic_contract_evaluation":True,
        "runtime_data_read":False,"runtime_mutated":False,"source_modified":after!=before or after_count!=count,
        "source_signature_before":before,"source_signature_after":after,"source_file_count":count,
        "provider_contacted":False,"project_tests_executed":False,"apply_executed":False,
        "rollback_executed":False,"rollback_authorized":False,"install_authorized":False,
        "promotion_authorized":False,"release_authorized":False,"model_management_authorized":False,
        "authority_granted":False,"content_free":True}
