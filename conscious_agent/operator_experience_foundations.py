from __future__ import annotations
"""v1279.0-v1279.2 operator-experience projection foundations.

The projection makes the supervised development lineage understandable without
creating a second source of truth or a new authority surface.  It accepts only
content-minimized records that already exist in v1270-v1278 and produces one
bounded dashboard-oriented read model.
"""
import hashlib
import json
import re
from typing import Any, Mapping

CONTRACT_VERSION = "v1279.2"
SCHEMA_VERSION = "1"
MAX_CHANGED_PATHS = 24
MAX_RISKS = 16
MAX_UNCERTAINTIES = 16
MAX_PROGRESS_EVENTS = 16
_SAFE_CODE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
_HEX = re.compile(r"^[a-f0-9]{64}$")

AUTHORITY_FLAGS = {
    "operator_experience_is_execution_authority": False,
    "operator_experience_is_provider_authority": False,
    "operator_experience_is_test_authority": False,
    "operator_experience_is_repair_authority": False,
    "operator_experience_is_update_authority": False,
    "operator_experience_is_application_authority": False,
    "operator_experience_is_rollback_authority": False,
    "operator_experience_is_release_authority": False,
    "dashboard_navigation_is_authorization": False,
    "generic_approval_is_authorization": False,
    "displayed_readiness_is_authorization": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}

SECTION_ORDER = (
    "status", "plan", "changes", "verification", "progress", "authorization",
    "controls", "recovery", "rollback", "uncertainty", "review",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _safe_code(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip().lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_.:-]+", "_", text).strip("_")[:128]
    return text if text and _SAFE_CODE.fullmatch(text) else fallback


def _bounded_rows(values: Any, limit: int) -> list[dict[str, Any]]:
    rows = []
    for value in values or []:
        if isinstance(value, Mapping):
            rows.append(dict(value))
        if len(rows) >= limit:
            break
    return rows


def _authorization_guidance(campaign: Mapping[str, Any], session: Mapping[str, Any], review: Mapping[str, Any], update: Mapping[str, Any]) -> dict[str, Any]:
    phase = str(campaign.get("phase") or "unknown")
    session_state = str(session.get("state") or "unknown")
    if session_state == "cancelled" or phase == "cancelled":
        code, label, required = "none_cancelled", "No execution authorization: campaign cancelled", False
    elif phase == "prepared":
        code, label, required = "v1265_candidate_exact_authorization", "Exact bounded v1265 candidate-mutation authorization required", True
    elif phase == "repair_authorization_required":
        code, label, required = "v1267_test_repair_exact_authorization", "Separate exact v1267 test/repair authorization required", True
    elif phase == "operator_review_required":
        code, label, required = "v1268_review_disposition", "Operator review disposition required; this is consideration only", False
    elif phase == "review_decided" and campaign.get("v1269_consideration_ready") is True and not update:
        code, label, required = "v1269_fresh_preflight_then_exact_update_authorization", "Fresh v1269 preflight, then a new exact one-time update authorization", True
    elif update and str(update.get("phase") or "") == "prepared":
        code, label, required = "v1269_exact_update_authorization", "Exact one-time v1269 self-update authorization required", True
    elif update and str(update.get("phase") or "") == "applied_verified":
        code, label, required = "separate_rollback_authorization_if_requested", "Update verified; rollback remains separately authorized", False
    elif phase == "blocked":
        code, label, required = "operator_reconciliation", "Operator reconciliation required before any further governed action", False
    else:
        code, label, required = "operator_reconciliation", "Review current evidence before selecting the next governed action", False
    return {
        "code": code,
        "label": label,
        "exact_authorization_required": required,
        "authorization_phrase_exposed": False,
        "generic_go_ahead_sufficient": False,
        "approval_from_navigation": False,
        "readiness_is_authority": False,
    }


def _controls(session: Mapping[str, Any], recovery: Mapping[str, Any], update: Mapping[str, Any]) -> dict[str, Any]:
    state = str(session.get("state") or "unknown")
    available: list[str] = []
    if state in {"running", "active", "prepared"}: available.extend(["pause", "cancel"])
    elif state in {"paused", "interrupted", "blocked"}: available.extend(["resume", "cancel"])
    if recovery and str(recovery.get("state") or "") not in {"clean", "complete", "cancelled"}:
        available.append("reconcile_recovery")
    rollback_available = bool(update and str(update.get("phase") or "") == "applied_verified")
    return {
        "available": sorted(set(available)),
        "pause_resume_cancel_are_runtime_controls_only": True,
        "recovery_reconciliation_executes_provider": False,
        "recovery_reconciliation_executes_tests": False,
        "rollback_available": rollback_available,
        "rollback_requires_separate_governed_preparation": rollback_available,
        "rollback_execution_requires_exact_authorization": rollback_available,
    }


def build_operator_experience_projection(
    *,
    campaign: Mapping[str, Any],
    session: Mapping[str, Any],
    observability: Mapping[str, Any],
    recovery: Mapping[str, Any] | None = None,
    ownership: Mapping[str, Any] | None = None,
    review_packet: Mapping[str, Any] | None = None,
    update: Mapping[str, Any] | None = None,
    rollback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    recovery = dict(recovery or {})
    ownership = dict(ownership or {})
    review = dict(review_packet or {})
    update = dict(update or {})
    rollback = dict(rollback or {})
    changed = []
    for row in _bounded_rows(review.get("changed_files"), MAX_CHANGED_PATHS):
        rel = str(row.get("relative_path") or "")
        if rel and not rel.startswith(("/", "\\")) and ".." not in rel.replace("\\", "/").split("/"):
            changed.append({"relative_path": rel[:320], "action": _safe_code(row.get("action"), "modify")})
    risks = [{"risk_code": _safe_code(x.get("risk_code")), "severity": _safe_code(x.get("severity"), "unknown")} for x in _bounded_rows(review.get("risks"), MAX_RISKS)]
    uncertainty = [{"uncertainty_code": _safe_code(x.get("uncertainty_code")), "state": _safe_code(x.get("state"), "unresolved"), "severity": _safe_code(x.get("severity"), "unknown")} for x in _bounded_rows(review.get("unresolved_uncertainty"), MAX_UNCERTAINTIES)]
    events = []
    for row in _bounded_rows(observability.get("recent_events"), MAX_PROGRESS_EVENTS):
        events.append({
            "event_code": _safe_code(row.get("event_code")), "phase": _safe_code(row.get("phase")),
            "outcome": _safe_code(row.get("outcome")), "elapsed_ms": max(0, int(row.get("elapsed_ms") or 0)),
            "phase_budget_ms": max(0, int(row.get("phase_budget_ms") or 0)),
        })
    verification = dict(review.get("verification") or {})
    controls = _controls(session, recovery, update)
    auth = _authorization_guidance(campaign, session, review, update)
    projection = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "operator_experience_ready",
        "observability_id": str(observability.get("observability_id") or ""),
        "session_id": str(session.get("session_id") or ""),
        "campaign_id": str(campaign.get("campaign_id") or ""),
        "section_order": list(SECTION_ORDER),
        "current": {
            "campaign_phase": _safe_code(campaign.get("phase")),
            "session_state": _safe_code(session.get("state")),
            "current_phase": _safe_code(observability.get("current_phase") or session.get("current_phase")),
            "active_source_modified": bool(campaign.get("active_source_modified")),
            "ownership_state": _safe_code(ownership.get("state"), "not_prepared") if ownership else "not_prepared",
            "recovery_state": _safe_code(recovery.get("state"), "not_prepared") if recovery else "not_prepared",
        },
        "plan": {
            "objective_code": _safe_code(campaign.get("selected_objective_code")),
            "strategy_code": _safe_code(campaign.get("selected_strategy_code")),
            "selection_confidence": _safe_code(campaign.get("selection_confidence")),
            "plan_confidence": _safe_code(campaign.get("plan_confidence")),
            "plan_digest_present": bool(campaign.get("plan_digest")),
            "plan_is_authority": False,
        },
        "changes": {
            "state": "reviewed" if review else "pending_review_packet",
            "changed_file_count": int(review.get("changed_file_count") or len(changed)),
            "paths": changed,
            "content_exposed": False,
        },
        "verification": {
            "tests_executed": bool(campaign.get("tests_executed")),
            "selected_test_count": int(campaign.get("selected_test_count") or verification.get("selected_test_count") or 0),
            "test_run_count": int(verification.get("test_run_count") or 0),
            "passed": bool(verification.get("passed")) if verification else bool(campaign.get("tests_executed") and str(campaign.get("phase")) in {"operator_review_required", "review_decided"}),
            "result_digest_present": bool(verification.get("result_digest")),
            "bounded_not_exhaustive": True,
        },
        "progress": {
            "event_count_total": int(observability.get("event_count_total") or 0),
            "failure_count_total": int(observability.get("failure_count_total") or 0),
            "retry_count_total": int(observability.get("retry_count_total") or 0),
            "recovery_count_total": int(observability.get("recovery_count_total") or 0),
            "budget_split_count_total": int(observability.get("budget_split_count_total") or 0),
            "recent_events": events,
            "bounded": True,
        },
        "authorization": auth,
        "controls": controls,
        "recovery": {
            "state": _safe_code(recovery.get("state"), "not_prepared") if recovery else "not_prepared",
            "restart_generation": int(recovery.get("restart_generation") or 0),
            "provider_state": _safe_code(recovery.get("provider_state"), "unknown") if recovery else "unknown",
            "automatic_provider_replay": False,
            "automatic_test_replay": False,
        },
        "rollback": {
            "update_id": str(update.get("update_id") or ""),
            "update_phase": _safe_code(update.get("phase"), "not_prepared") if update else "not_prepared",
            "rollback_prepared": bool(rollback),
            "rollback_authorization_phrase_exposed": False,
            "rollback_is_separately_governed": True,
        },
        "uncertainty": uncertainty,
        "review": {
            "review_id": str(review.get("review_id") or ""),
            "state": "ready" if review else "not_ready",
            "risk_count": len(risks),
            "risks": risks,
            "uncertainty_count": len(uncertainty),
            "operator_decision": _safe_code(campaign.get("operator_decision"), "pending"),
            "approval_for_v1269_is_consideration_only": True,
        },
        "privacy": {
            "content_minimized": True,
            "raw_prompt_exposed": False,
            "raw_response_exposed": False,
            "provider_payload_exposed": False,
            "raw_test_output_exposed": False,
            "authorization_phrase_exposed": False,
        },
        **AUTHORITY_FLAGS,
    }
    projection["projection_digest"] = _digest(projection)
    return projection


def validate_operator_experience_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    expected = _digest({k: v for k, v in row.items() if k != "projection_digest"})
    digest_ok = bool(row.get("projection_digest")) and row.get("projection_digest") == expected
    ids_ok = str(row.get("observability_id") or "").startswith("observability_") and str(row.get("session_id") or "").startswith("longwork_") and str(row.get("campaign_id") or "").startswith("selfalpha_")
    authority_ok = all(row.get(k) is v for k, v in AUTHORITY_FLAGS.items())
    privacy = row.get("privacy") or {}
    privacy_ok = privacy.get("content_minimized") is True and all(privacy.get(k) is False for k in ("raw_prompt_exposed", "raw_response_exposed", "provider_payload_exposed", "raw_test_output_exposed", "authorization_phrase_exposed"))
    sections_ok = list(row.get("section_order") or []) == list(SECTION_ORDER)
    controls = row.get("controls") or {}
    controls_ok = set(controls.get("available") or []).issubset({"pause", "resume", "cancel", "reconcile_recovery"})
    paths_ok = all(isinstance(x, Mapping) and bool(x.get("relative_path")) and not str(x.get("relative_path")).startswith(("/", "\\")) and ".." not in str(x.get("relative_path")).replace("\\", "/").split("/") for x in (row.get("changes") or {}).get("paths") or [])
    auth = row.get("authorization") or {}
    semantics_ok = auth.get("authorization_phrase_exposed") is False and auth.get("generic_go_ahead_sufficient") is False and (row.get("review") or {}).get("approval_for_v1269_is_consideration_only") is True and (row.get("rollback") or {}).get("rollback_is_separately_governed") is True
    ok = digest_ok and ids_ok and authority_ok and privacy_ok and sections_ok and controls_ok and paths_ok and semantics_ok
    return {"ok": ok, "status": "operator_experience_projection_valid" if ok else "operator_experience_projection_invalid", "digest_valid": digest_ok, "ids_valid": ids_ok, "authority_contained": authority_ok, "privacy_contained": privacy_ok, "sections_valid": sections_ok, "controls_valid": controls_ok, "paths_valid": paths_ok, "semantics_valid": semantics_ok}


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "SECTION_ORDER", "build_operator_experience_projection", "validate_operator_experience_projection", "_digest"]
