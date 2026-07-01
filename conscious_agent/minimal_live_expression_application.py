from __future__ import annotations

from typing import Any

from expression_live_execution_prep import build_expression_live_execution_prep_audit_summary
from identity_expression import classify_identity_expression_request

MINIMAL_LIVE_EXPRESSION_APPLICATION_VERSION = "1032.0"
MINIMAL_LIVE_EXPRESSION_APPLICATION_BOUNDARIES = {
    "candidate_selection_applies_change": False,
    "candidate_selection_rewrites_personality": False,
    "candidate_selection_touches_runtime_prompt": False,
    "candidate_selection_selects_high_risk_surface": False,
    "approval_lock_self_approves": False,
    "approval_lock_reuses_expired_approval": False,
    "approval_lock_expands_scope": False,
    "approval_lock_grants_autonomy": False,
    "transaction_builder_writes_files": False,
    "transaction_builder_applies_patch": False,
    "transaction_builder_mutates_memory": False,
    "transaction_builder_changes_identity": False,
    "application_harness_executes_without_confirmation": False,
    "application_harness_continues_automatically": False,
    "application_harness_allows_out_of_scope_files": False,
    "application_harness_treats_preimage_mismatch_as_ok": False,
    "application_audit_publishes_release": False,
    "application_audit_creates_release_candidate": False,
    "application_audit_runs_rollback": False,
    "application_audit_mutates_personality_core": False,
    "minimal_path_operator_approved_only": True,
    "minimal_path_single_use_scope_required": True,
    "minimal_path_reversible": True,
    "minimal_path_no_autonomous_continuation": True,
}

SAFE_MINIMAL_CANDIDATE_TYPES = [
    "dashboard-facing expression status line",
    "README expression governance note",
    "release-history expression governance note",
    "test-only expression fixture wording",
    "non-runtime dashboard microcopy explaining operator approval",
]

FORBIDDEN_MINIMAL_APPLICATION_SURFACES = [
    "runtime prompt behavior",
    "core identity source of truth",
    "personality engine",
    "memory stores",
    "autonomous loop behavior",
    "local model invocation defaults",
    "approval/governance bypass rules",
    "release publishing workflow",
]

MINIMAL_APPROVAL_REQUIRED_FIELDS = [
    "approval_id",
    "approval_scope",
    "approval_expiration",
    "target_version",
    "allowed_files",
    "allowed_change_summary",
    "forbidden_files",
    "rollback_requirement",
    "verification_requirement",
    "single_use",
]

SAFE_MINIMAL_ALLOWED_FILES = [
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/dashboard.py",
    "tools/smoke_check.py",
]

MINIMAL_VERIFICATION_TEXT_COMMANDS = [
    "python -m compileall conscious_agent tools",
    "python tools/smoke_check.py --tier fast --json",
    "python tools/smoke_check.py --check operator-approved-minimal-live-expression-application-audit-v1",
    "manual dashboard route probes for v356-v360 routes",
    "manual dynamic API/CLI parity checks for v356-v360 routes and flags",
    "manual package privacy scan and extracted zip verification",
]


def _policy_status(request_text: str | None, context: str) -> dict[str, Any]:
    return classify_identity_expression_request(request_text or "", context=context)


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "runtime prompt mutation request": ["runtime prompt", "rewrite prompt", "change live chat", "edit chat.py prompt"],
        "identity/personality mutation request": ["rewrite identity", "alter personality", "personality engine", "change core identity", "mutate memory"],
        "autonomy expansion request": ["grant autonomy", "self approve", "continue automatically", "schedule hidden work", "daily loop"],
        "unscoped source mutation request": ["any file", "whole codebase", "out of scope", "skip scope", "change everything"],
        "command execution request": ["run smoke now", "execute commands", "build package now", "run rollback"],
        "release/publishing request": ["publish release", "create release candidate", "ship automatically"],
        "approval bypass": ["no approval needed", "reuse expired approval", "approval vibes", "sandbox success is approval"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(policy: dict[str, Any], flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    if policy.get("status") == "blocked" or flags or blockers:
        return "blocked"
    if policy.get("status") == "warning":
        return "warning"
    return "reviewable"


def _missing_fields(evidence: dict[str, Any], required: list[str]) -> list[str]:
    missing: list[str] = []
    for field in required:
        value = evidence.get(field)
        if value is None or value == "" or value == [] or str(value).lower() in {"expired", "stale", "out-of-scope"}:
            missing.append(field)
    return missing


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def build_minimal_live_expression_change_candidate_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    policy = _policy_status(request_text, "minimal live expression change candidate")
    flags = _risk_flags(request_text)
    proposed_type = str(evidence.get("candidate_type") or target_surface or "dashboard-facing expression status line")
    proposed_files = _listify(evidence.get("candidate_files") or ["conscious_agent/dashboard.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"])
    blockers: list[str] = []
    if proposed_type not in SAFE_MINIMAL_CANDIDATE_TYPES:
        blockers.append("candidate type must be a tiny expression-adjacent docs/dashboard/test wording change")
    forbidden_hits = [surface for surface in FORBIDDEN_MINIMAL_APPLICATION_SURFACES if surface.lower() in (request_text or "").lower()]
    if forbidden_hits:
        blockers.append("forbidden high-risk surface requested")
    out_of_scope_files = [path for path in proposed_files if path not in SAFE_MINIMAL_ALLOWED_FILES]
    if out_of_scope_files:
        blockers.append("candidate file outside minimal safe allowed file list")
    return {
        "version": MINIMAL_LIVE_EXPRESSION_APPLICATION_VERSION,
        "state": "minimal_live_expression_change_candidate_selection_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "dashboard/docs expression governance status line",
        "safe_candidate_types": list(SAFE_MINIMAL_CANDIDATE_TYPES),
        "forbidden_surfaces": list(FORBIDDEN_MINIMAL_APPLICATION_SURFACES),
        "recommended_first_candidate": "Add or update a dashboard-facing expression status line: Expression application remains operator-approved, scoped, reversible, and non-autonomous.",
        "proposed_candidate_type": proposed_type,
        "proposed_files": proposed_files,
        "out_of_scope_files": out_of_scope_files,
        "forbidden_surface_hits": forbidden_hits,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(policy, flags, blockers),
        "applies_change": False,
        "rewrites_personality": False,
        "touches_runtime_prompt": False,
        "selects_high_risk_surface": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_minimal_live_expression_approval_lock_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    policy = _policy_status(request_text, "minimal live expression approval lock")
    flags = _risk_flags(request_text)
    missing = _missing_fields(evidence, MINIMAL_APPROVAL_REQUIRED_FIELDS)
    allowed_files = _listify(evidence.get("allowed_files"))
    forbidden_files = _listify(evidence.get("forbidden_files"))
    blockers: list[str] = []
    if str(evidence.get("approval_scope") or "").lower() != "approve-one-minimal-expression-adjacent-source-change":
        blockers.append("approval scope must be one minimal expression-adjacent source change")
    if str(evidence.get("single_use") or "").lower() not in {"true", "yes", "1"} and evidence.get("single_use") is not True:
        blockers.append("approval lock must be single-use")
    outside_allowed = [path for path in allowed_files if path not in SAFE_MINIMAL_ALLOWED_FILES]
    if outside_allowed:
        blockers.append("allowed_files contains path outside minimal safe list")
    if not forbidden_files:
        blockers.append("forbidden_files must explicitly deny high-risk surfaces")
    return {
        "version": MINIMAL_LIVE_EXPRESSION_APPLICATION_VERSION,
        "state": "minimal_live_expression_approval_scope_lock_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "required_fields": list(MINIMAL_APPROVAL_REQUIRED_FIELDS),
        "submitted_evidence_fields": sorted(evidence.keys()),
        "missing_fields": missing,
        "approval_id": evidence.get("approval_id"),
        "approval_scope": evidence.get("approval_scope"),
        "approval_expiration": evidence.get("approval_expiration"),
        "target_version": evidence.get("target_version"),
        "allowed_files": allowed_files,
        "forbidden_files": forbidden_files,
        "single_use": evidence.get("single_use"),
        "scope_rules": ["fresh approval", "single-use", "exact file list", "exact change summary", "rollback required", "verification required"],
        "risk_flags": flags,
        "blockers": blockers + [f"missing:{field}" for field in missing],
        "status": _status(policy, flags, blockers + missing),
        "self_approves": False,
        "reuses_expired_approval": False,
        "expands_scope": False,
        "grants_autonomy": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_minimal_live_expression_patch_transaction_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    policy = _policy_status(request_text, "minimal live expression patch transaction")
    flags = _risk_flags(request_text)
    files = _listify(evidence.get("allowed_files") or ["conscious_agent/dashboard.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "tools/smoke_check.py"])
    blockers = ["transaction requires matching approval lock"] if not evidence.get("approval_id") else []
    out_of_scope = [path for path in files if path not in SAFE_MINIMAL_ALLOWED_FILES]
    if out_of_scope:
        blockers.append("transaction file outside locked minimal scope")
    return {
        "version": MINIMAL_LIVE_EXPRESSION_APPLICATION_VERSION,
        "state": "minimal_live_expression_patch_transaction_preview_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "dashboard/docs expression governance status line",
        "approval_id": evidence.get("approval_id"),
        "preimage_requirements": ["path", "hash before change", "exact expected edit purpose", "rollback anchor", "docs/version obligation"],
        "exact_file_list": files,
        "out_of_scope_files": out_of_scope,
        "diff_preview": ["Add/update expression status line only", "Update README_NEXT_STEPS substages", "Update README_RELEASE_HISTORY", "Add targeted smoke token coverage"],
        "rollback_diff": ["Remove/restore expression status line", "Restore README/release-history/version metadata preimage", "Restore smoke token expectation preimage"],
        "post_apply_verification_plan_as_text": list(MINIMAL_VERIFICATION_TEXT_COMMANDS),
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(policy, flags, blockers),
        "writes_files": False,
        "applies_patch": False,
        "mutates_memory": False,
        "changes_identity": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_minimal_live_expression_application_harness_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    policy = _policy_status(request_text, "minimal live expression application harness")
    flags = _risk_flags(request_text)
    required = ["approval_id", "transaction_id", "preimage_match", "allowed_file_match", "operator_confirmation_phrase", "rollback_packet_present", "verification_checklist_present"]
    missing = _missing_fields(evidence, required)
    blockers: list[str] = []
    if evidence.get("preimage_match") is not True:
        blockers.append("preimage must match before any future application")
    if evidence.get("allowed_file_match") is not True:
        blockers.append("allowed file list must match approval lock")
    if str(evidence.get("operator_confirmation_phrase") or "") != "I explicitly approve this one minimal scoped expression-adjacent source change":
        blockers.append("operator confirmation phrase must match exactly")
    if evidence.get("rollback_packet_present") is not True:
        blockers.append("rollback packet must be present")
    if evidence.get("verification_checklist_present") is not True:
        blockers.append("verification checklist must be present")
    return {
        "version": MINIMAL_LIVE_EXPRESSION_APPLICATION_VERSION,
        "state": "minimal_live_expression_application_harness_confirmation_gate",
        "profile_name": profile_name or "operator_review_expression_profile",
        "required_fields": required,
        "missing_fields": missing,
        "operator_confirmation_phrase_required": "I explicitly approve this one minimal scoped expression-adjacent source change",
        "hard_block_conditions": ["approval expired", "file outside scope", "preimage mismatch", "missing rollback", "missing verification", "runtime personality mutation", "memory mutation", "autonomous continuation"],
        "risk_flags": flags,
        "blockers": blockers + [f"missing:{field}" for field in missing],
        "status": _status(policy, flags, blockers + missing),
        "executes_without_confirmation": False,
        "continues_automatically": False,
        "allows_out_of_scope_files": False,
        "treats_preimage_mismatch_as_ok": False,
        "review_only_until_explicit_execution": True,
        "policy_decision": policy,
    }


def build_minimal_live_expression_application_audit_summary(
    dashboard_text: str = "",
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    sample_evidence = dict(evidence)
    candidate = build_minimal_live_expression_change_candidate_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=sample_evidence)
    approval = build_minimal_live_expression_approval_lock_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=sample_evidence)
    transaction = build_minimal_live_expression_patch_transaction_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=sample_evidence)
    harness = build_minimal_live_expression_application_harness_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=sample_evidence)
    prep_reference = build_expression_live_execution_prep_audit_summary(dashboard_text=dashboard_text, request_text="review minimal application path only", evidence={"operator_approval_id": "fresh", "approval_scope": "approve-to-execution-prep-only", "approval_expiration": "fresh", "target_version": "v355.0", "v345_promotion_packet_id": "promo", "v350_live_application_packet_id": "live", "approved_surfaces": ["docs"], "approval_purpose": "prepare execution-prep packet only"})
    routes = [
        "/minimal-live-expression-change-candidate",
        "/minimal-live-expression-approval-lock",
        "/minimal-live-expression-patch-transaction",
        "/minimal-live-expression-application-harness",
        "/minimal-live-expression-application-audit",
    ]
    missing_routes = [route for route in routes if dashboard_text and route not in dashboard_text]
    flags = sorted(set(candidate.get("risk_flags", [])) | set(approval.get("risk_flags", [])) | set(transaction.get("risk_flags", [])) | set(harness.get("risk_flags", [])))
    blockers = list(missing_routes)
    for packet in [candidate, approval, transaction, harness]:
        if packet.get("status") == "blocked":
            blockers.append(str(packet.get("state", "blocked subpacket")))
    return {
        "version": MINIMAL_LIVE_EXPRESSION_APPLICATION_VERSION,
        "state": "minimal_live_expression_application_audit_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "candidate_selection_audit": candidate,
        "approval_lock_audit": approval,
        "patch_transaction_audit": transaction,
        "application_harness_audit": harness,
        "v355_execution_prep_reference_audit": prep_reference,
        "dashboard_routes": routes,
        "missing_dashboard_routes": missing_routes,
        "application_path_verifies": ["candidate tiny", "approval scoped", "transaction matches scope", "preimage matched", "README updated", "release history updated", "version markers updated", "smoke passed", "rollback plan exists", "no forbidden paths", "no core personality mutation", "no autonomous continuation"],
        "safe_first_change": "dashboard/docs expression governance status line",
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(_policy_status(request_text, "minimal live expression application audit"), flags, blockers),
        "publishes_release": False,
        "creates_release_candidate": False,
        "runs_rollback": False,
        "mutates_personality_core": False,
        "applies_memory_mutation": False,
        "continues_automatically": False,
        "operator_approved_only": True,
        "single_use_scope_required": True,
        "reversible": True,
        "boundaries": dict(MINIMAL_LIVE_EXPRESSION_APPLICATION_BOUNDARIES),
        "safe_next_action": "Operator may review the minimal live expression application path. Any actual source application still requires the exact scoped confirmation phrase and matching transaction evidence.",
    }


def render_minimal_live_expression_application_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            if value and isinstance(value[0], dict):
                lines.append(f"- {key}: {len(value)} item(s)")
            else:
                lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        elif isinstance(value, dict):
            lines.append(f"- {key}: {len(value)} field(s)")
        else:
            lines.append(f"- {key}: {value}")
    return lines
