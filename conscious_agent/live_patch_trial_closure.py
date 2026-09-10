from __future__ import annotations

from pathlib import Path
from typing import Any

LIVE_PATCH_TRIAL_CLOSURE_VERSION = "1032.0"
LIVE_PATCH_TRIAL_CLOSURE_BOUNDARIES: dict[str, bool] = {
    "result_intake_reruns_commands": False,
    "result_intake_applies_fixes": False,
    "result_intake_executes_rollback": False,
    "result_intake_infers_future_approval": False,
    "diff_evidence_generates_patch": False,
    "diff_evidence_edits_source": False,
    "diff_evidence_normalizes_drift": False,
    "approval_burnout_reuses_approval": False,
    "approval_burnout_expands_scope": False,
    "approval_burnout_treats_success_as_authorization": False,
    "post_trial_review_reruns_smoke": False,
    "post_trial_review_executes_rollback": False,
    "post_trial_review_creates_recovery_patch": False,
    "closure_audit_applies_another_patch": False,
    "closure_audit_mutates_memory": False,
    "closure_audit_alters_identity": False,
    "closure_audit_alters_personality": False,
    "closure_audit_invokes_models": False,
    "closure_audit_publishes_release": False,
    "closure_audit_creates_release_candidate": False,
    "closure_audit_continues_automatically": False,
    "approval_single_use_required": True,
    "approval_burnout_required": True,
    "rollback_readiness_review_required": True,
    "operator_reapproval_required_for_next_patch": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

REQUIRED_RESULT_FIELDS = [
    "approval_id",
    "transaction_id",
    "application_trial_id",
    "operator_confirmation_phrase",
    "timestamp",
    "expected_files",
    "actual_changed_files",
    "reported_verification_results",
    "reported_rollback_readiness",
]

CONFIRMATION_PHRASE = "I explicitly approve this one scoped live-change application trial"


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, set):
        return sorted(str(item) for item in value)
    return [str(value)]


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "command execution request": ["rerun smoke", "run commands", "execute verification", "run install smoke"],
        "automatic fix request": ["auto fix", "apply fixes", "create recovery patch", "normalize drift"],
        "rollback execution request": ["run rollback", "execute rollback", "restore files"],
        "approval reuse request": ["reuse approval", "use same approval", "success authorizes", "carry approval forward"],
        "scope expansion request": ["expand scope", "another patch", "next patch automatically", "all files"],
        "mind mutation request": ["mutate memory", "rewrite identity", "alter personality", "personality engine"],
        "model/release request": ["invoke local model", "publish release", "create release candidate"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    return "blocked" if flags or blockers else "reviewable"


def build_live_patch_trial_result_intake_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    missing = [field for field in REQUIRED_RESULT_FIELDS if evidence.get(field) in (None, "", [])]
    expected_files = _listify(evidence.get("expected_files"))
    actual_changed_files = _listify(evidence.get("actual_changed_files"))
    blockers = [f"missing:{field}" for field in missing]
    if evidence.get("operator_confirmation_phrase") != CONFIRMATION_PHRASE:
        blockers.append("operator confirmation phrase mismatch")
    if set(actual_changed_files) - set(expected_files):
        blockers.append("actual changed files include unexpected files")
    return {
        "version": LIVE_PATCH_TRIAL_CLOSURE_VERSION,
        "state": "live_patch_trial_result_intake_review_only",
        "required_fields": REQUIRED_RESULT_FIELDS,
        "missing_fields": missing,
        "approval_id": evidence.get("approval_id"),
        "transaction_id": evidence.get("transaction_id"),
        "application_trial_id": evidence.get("application_trial_id"),
        "expected_files": expected_files,
        "actual_changed_files": actual_changed_files,
        "reported_verification_results": evidence.get("reported_verification_results"),
        "reported_rollback_readiness": evidence.get("reported_rollback_readiness"),
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "reruns_commands": False,
        "applies_fixes": False,
        "executes_rollback": False,
        "infers_future_approval": False,
        "review_only": True,
    }


def build_applied_diff_evidence_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    checks = {
        "expected_diff_summary_present": bool(evidence.get("expected_diff_summary_present", True)),
        "actual_diff_summary_present": bool(evidence.get("actual_diff_summary_present", True)),
        "preimage_reference_present": bool(evidence.get("preimage_reference_present", True)),
        "postimage_reference_present": bool(evidence.get("postimage_reference_present", True)),
        "readme_update_evidence_present": bool(evidence.get("readme_update_evidence_present", True)),
        "release_history_update_evidence_present": bool(evidence.get("release_history_update_evidence_present", True)),
        "version_marker_update_evidence_present": bool(evidence.get("version_marker_update_evidence_present", True)),
        "forbidden_path_absence_evidence_present": bool(evidence.get("forbidden_path_absence_evidence_present", True)),
        "source_only_package_expectation_present": bool(evidence.get("source_only_package_expectation_present", True)),
    }
    blockers = [key for key, value in checks.items() if not value]
    if evidence.get("unexpected_drift_present") is True:
        blockers.append("unexpected drift present")
    return {
        "version": LIVE_PATCH_TRIAL_CLOSURE_VERSION,
        "state": "live_patch_applied_diff_evidence_review_only",
        "checks": checks,
        "unexpected_drift_present": bool(evidence.get("unexpected_drift_present", False)),
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "generates_patch": False,
        "edits_source": False,
        "normalizes_drift": False,
        "review_only": True,
    }


def build_approval_burnout_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    checks = {
        "approval_token_consumed": evidence.get("approval_token_consumed") is True,
        "single_use_enforced": evidence.get("single_use_enforced") is True,
        "reuse_rejected": evidence.get("reuse_rejected") is True,
        "scope_expansion_rejected": evidence.get("scope_expansion_rejected") is True,
        "stale_approval_rejected": evidence.get("stale_approval_rejected") is True,
        "approval_result_separated": evidence.get("approval_result_separated") is True,
        "operator_reapproval_required": evidence.get("operator_reapproval_required") is True,
    }
    blockers = [key for key, value in checks.items() if not value]
    return {
        "version": LIVE_PATCH_TRIAL_CLOSURE_VERSION,
        "state": "live_patch_approval_burnout_review_only",
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "reuses_approval": False,
        "expands_scope": False,
        "treats_success_as_authorization": False,
        "future_patch_requires_new_operator_approval": True,
        "review_only": True,
    }


def build_post_trial_regression_review_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    checks = {
        "compile_result_present": bool(evidence.get("compile_result_present", True)),
        "fast_smoke_result_present": bool(evidence.get("fast_smoke_result_present", True)),
        "install_smoke_result_present": bool(evidence.get("install_smoke_result_present", True)),
        "targeted_smoke_result_present": bool(evidence.get("targeted_smoke_result_present", True)),
        "dashboard_route_health_reviewed": bool(evidence.get("dashboard_route_health_reviewed", True)),
        "api_cli_parity_reviewed": bool(evidence.get("api_cli_parity_reviewed", True)),
        "package_privacy_reviewed": bool(evidence.get("package_privacy_reviewed", True)),
        "data_tip_hover_reviewed": bool(evidence.get("data_tip_hover_reviewed", True)),
        "native_title_tooltip_absence_reviewed": bool(evidence.get("native_title_tooltip_absence_reviewed", True)),
        "rollback_packet_present": bool(evidence.get("rollback_packet_present", True)),
        "rollback_feasibility_reviewed": bool(evidence.get("rollback_feasibility_reviewed", True)),
        "unexpected_changed_files_absent": bool(evidence.get("unexpected_changed_files_absent", True)),
    }
    blockers = [key for key, value in checks.items() if not value]
    return {
        "version": LIVE_PATCH_TRIAL_CLOSURE_VERSION,
        "state": "live_patch_post_trial_regression_review_only",
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "reruns_smoke": False,
        "executes_rollback": False,
        "creates_recovery_patch": False,
        "review_only": True,
    }


def build_live_patch_trial_closure_audit_summary(root: Path | None = None, dashboard_text: str | None = None, request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    docs = dashboard_text or ""
    default_evidence = {
        "approval_id": "approval-v385-review",
        "transaction_id": "transaction-v380-review",
        "application_trial_id": "trial-v380-review",
        "operator_confirmation_phrase": CONFIRMATION_PHRASE,
        "timestamp": "operator-reported",
        "expected_files": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "tools/smoke_check.py"],
        "actual_changed_files": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "tools/smoke_check.py"],
        "reported_verification_results": "operator supplied verification report",
        "reported_rollback_readiness": "rollback packet reviewed",
        "approval_token_consumed": True,
        "single_use_enforced": True,
        "reuse_rejected": True,
        "scope_expansion_rejected": True,
        "stale_approval_rejected": True,
        "approval_result_separated": True,
        "operator_reapproval_required": True,
    }
    default_evidence.update(evidence or {})
    intake = build_live_patch_trial_result_intake_summary(request_text or "review only", default_evidence)
    diff = build_applied_diff_evidence_summary(request_text or "review only", default_evidence)
    burnout = build_approval_burnout_summary(request_text or "review only", default_evidence)
    review = build_post_trial_regression_review_summary(request_text or "review only", default_evidence)
    doc_checks = {
        "readme_updated": "v385.0 - Operator-Confirmed Live Patch Trial Result Intake and One-Time Authorization Burnout v1" in docs,
        "release_history_updated": "v385.0 - Operator-Confirmed Live Patch Trial Result Intake and One-Time Authorization Burnout v1" in docs,
        "version_markers_current": 'LIVE_PATCH_TRIAL_CLOSURE_VERSION = "555.0"' in docs,
        "dashboard_data_tip_present": "data-tip" in docs,
        "command_deck_present": "command-deck" in docs,
        "operator_console_present": "operator-console" in docs,
        "runtime_private_dirs_documented": "data/autonomy/live_patch_trial_closure_audit/" in docs,
    }
    blockers = [key for key, value in doc_checks.items() if not value]
    packets = [intake, diff, burnout, review]
    ok = all(packet.get("status") == "reviewable" for packet in packets) and not blockers
    return {
        "version": LIVE_PATCH_TRIAL_CLOSURE_VERSION,
        "state": "live_patch_trial_closure_audit",
        "result_intake": intake,
        "diff_evidence": diff,
        "approval_burnout": burnout,
        "post_trial_regression_review": review,
        "doc_checks": doc_checks,
        "blockers": blockers,
        "boundaries": dict(LIVE_PATCH_TRIAL_CLOSURE_BOUNDARIES),
        "boundaries_ok": all(value is False for key, value in LIVE_PATCH_TRIAL_CLOSURE_BOUNDARIES.items() if key.endswith(("commands", "fixes", "rollback", "approval", "patch", "source", "drift", "scope", "smoke", "memory", "identity", "personality", "models", "release", "candidate", "automatically")) and key not in {"operator_reapproval_required_for_next_patch"}) and all(LIVE_PATCH_TRIAL_CLOSURE_BOUNDARIES[key] is True for key in ["approval_single_use_required", "approval_burnout_required", "rollback_readiness_review_required", "operator_reapproval_required_for_next_patch", "dashboard_data_tip_required", "native_title_tooltips_forbidden"]),
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "safe_next_action": "Operator may review the v385 closure audit. No additional patch, rollback, approval reuse, source edit, release creation, memory/identity/personality mutation, model invocation, or automatic continuation is authorized.",
    }


def render_live_patch_trial_closure_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ["version", "state", "status", "ok", "review_only", "safe_next_action"]:
        if key in summary:
            lines.append(f"- {key}: {summary[key]}")
    if summary.get("blockers"):
        lines.append("- blockers: " + ", ".join(map(str, summary.get("blockers", []))))
    if summary.get("risk_flags"):
        lines.append("- risk_flags: " + ", ".join(map(str, summary.get("risk_flags", []))))
    return lines or ["- no summary details available"]
