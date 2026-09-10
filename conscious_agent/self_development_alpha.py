from __future__ import annotations

"""v1270.3-v1270.5 integration for the supervised self-development alpha loop."""

from pathlib import Path
from typing import Any, Callable, Mapping

from intelligent_test_selection_foundations import prepare_intelligent_test_selection
from isolated_self_modification import execute_isolated_self_modification
from iterative_self_repair import execute_iterative_self_repair
from iterative_self_repair_foundations import prepare_iterative_self_repair
from operator_review_handoff import build_v1269_review_handoff, record_operator_review_decision
from operator_review_handoff_foundations import prepare_operator_review_handoff
from self_development_alpha_foundations import (
    ALPHA_DENIED_AUTHORITY, _campaign_path, _record_digest, _runtime_root, _stage_root, _write_json,
    load_self_development_alpha_campaign, validate_self_development_alpha_campaign,
)

CONTRACT_VERSION = "v1270.5"


def execute_self_development_alpha_candidate(
    campaign_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    authorization_phrase: str,
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    record = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
    if not record or not validate_self_development_alpha_campaign(record).get("ok"):
        raise ValueError("valid_self_development_alpha_campaign_required")
    if record.get("phase") in {"repair_authorization_required", "operator_review_required", "review_decided"}:
        return {**record, "operation_status": "restored"}
    result = execute_isolated_self_modification(
        str(record.get("candidate_operation_id") or ""), source_root, runtime_root=_stage_root(runtime, "v1265"),
        authorization_phrase=authorization_phrase, provider=provider,
    )
    if result.get("status") == "isolated_self_modification_exact_authorization_required":
        return {**result, "campaign_id": campaign_id, "campaign_phase": record.get("phase"), "operation_status": "authorization_required"}
    if result.get("phase") != "sealed":
        blocked = dict(record); blocked.update({"phase": "blocked", "status": "self_development_alpha_candidate_blocked", "candidate_provider_executed": bool(result.get("provider_contacted")), "active_source_modified": False})
        blocked["record_digest"] = _record_digest(blocked); _write_json(_campaign_path(campaign_id, runtime), blocked); return blocked
    selection = prepare_intelligent_test_selection(str(result.get("operation_id") or ""), source_root, self_modification_runtime_root=_stage_root(runtime, "v1265"), runtime_root=_stage_root(runtime, "v1266"))
    repair = prepare_iterative_self_repair(selection["selection_id"], source_root, self_modification_runtime_root=_stage_root(runtime, "v1265"), test_selection_runtime_root=_stage_root(runtime, "v1266"), runtime_root=_stage_root(runtime, "v1267"))
    updated = dict(record); updated.update({
        "contract_version": CONTRACT_VERSION, "phase": "repair_authorization_required", "status": "self_development_alpha_repair_authorization_required",
        "candidate_provider_executed": True, "test_selection_id": selection.get("selection_id", ""), "repair_id": repair.get("repair_id", ""),
        "selected_test_count": selection.get("selected_test_count", 0), "repair_authorization_phrase": repair.get("authorization_phrase", ""),
        "active_source_modified": False, **ALPHA_DENIED_AUTHORITY,
    })
    updated["record_digest"] = _record_digest(updated); _write_json(_campaign_path(campaign_id, runtime), updated)
    return {**updated, "operation_status": "candidate_ready"}


def execute_self_development_alpha_verification_and_review(
    campaign_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    repair_authorization_phrase: str,
    repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    record = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
    if not record or not validate_self_development_alpha_campaign(record).get("ok"):
        raise ValueError("valid_self_development_alpha_campaign_required")
    if record.get("phase") in {"operator_review_required", "review_decided"}:
        return {**record, "operation_status": "restored"}
    if record.get("phase") != "repair_authorization_required":
        raise ValueError("self_development_alpha_candidate_stage_required")
    repair = execute_iterative_self_repair(
        str(record.get("repair_id") or ""), source_root,
        self_modification_runtime_root=_stage_root(runtime, "v1265"), test_selection_runtime_root=_stage_root(runtime, "v1266"),
        runtime_root=_stage_root(runtime, "v1267"), authorization_phrase=repair_authorization_phrase, provider=repair_provider,
    )
    if repair.get("status") == "iterative_self_repair_exact_authorization_required":
        return {**repair, "campaign_id": campaign_id, "campaign_phase": record.get("phase"), "operation_status": "authorization_required"}
    if repair.get("phase") != "passed":
        blocked = dict(record); blocked.update({"phase": "blocked", "status": "self_development_alpha_verification_blocked", "tests_executed": bool(repair.get("tests_executed")), "repair_attempt_count": len(repair.get("attempts") or []), "active_source_modified": False})
        blocked["record_digest"] = _record_digest(blocked); _write_json(_campaign_path(campaign_id, runtime), blocked); return blocked
    packet = prepare_operator_review_handoff(
        str(record.get("repair_id") or ""), source_root,
        self_modification_runtime_root=_stage_root(runtime, "v1265"), test_selection_runtime_root=_stage_root(runtime, "v1266"),
        repair_runtime_root=_stage_root(runtime, "v1267"), runtime_root=_stage_root(runtime, "v1268"),
    )
    updated = dict(record); updated.pop("repair_authorization_phrase", None); updated.update({
        "contract_version": CONTRACT_VERSION, "phase": "operator_review_required", "status": "self_development_alpha_operator_review_ready",
        "tests_executed": True, "repair_attempt_count": len(repair.get("attempts") or []), "review_id": packet.get("review_id", ""),
        "review_packet_digest": packet.get("record_digest", ""), "verified_candidate_manifest_digest": packet.get("candidate_manifest_digest", ""),
        "review_changed_file_count": packet.get("changed_file_count", 0), "review_risk_count": len(packet.get("risks") or []),
        "review_uncertainty_count": len(packet.get("unresolved_uncertainty") or []), "operator_review_required": True,
        "operator_decision": "pending", "v1269_consideration_ready": False, "active_source_modified": False, **ALPHA_DENIED_AUTHORITY,
    })
    updated["record_digest"] = _record_digest(updated); _write_json(_campaign_path(campaign_id, runtime), updated)
    return {**updated, "operation_status": "review_ready"}


def record_self_development_alpha_review_decision(
    campaign_id: str,
    *,
    runtime_root: str | Path | None,
    decision: str,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    record = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
    if not record or record.get("phase") not in {"operator_review_required", "review_decided"}:
        raise ValueError("self_development_alpha_review_not_ready")
    decision_record = record_operator_review_decision(str(record.get("review_id") or ""), packet_digest=str(record.get("review_packet_digest") or ""), decision=decision, runtime_root=_stage_root(runtime, "v1268"))
    handoff = build_v1269_review_handoff(str(record.get("review_id") or ""), runtime_root=_stage_root(runtime, "v1268")) if decision == "approve_for_v1269_consideration" else {"ok": False}
    updated = dict(record); updated.update({
        "phase": "review_decided", "status": "self_development_alpha_review_decided", "operator_decision": decision,
        "review_decision_digest": decision_record.get("record_digest", ""), "v1269_consideration_ready": bool(handoff.get("ok")),
        "self_update_authorized": False, "active_source_modified": False,
    })
    updated["record_digest"] = _record_digest(updated); _write_json(_campaign_path(campaign_id, runtime), updated)
    return {**updated, "operation_status": "review_decided"}


__all__ = ["CONTRACT_VERSION", "execute_self_development_alpha_candidate", "execute_self_development_alpha_verification_and_review", "record_self_development_alpha_review_decision"]
