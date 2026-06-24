from __future__ import annotations

from pathlib import Path
from typing import Any

from minimal_live_expression_application import build_minimal_live_expression_application_audit_summary
from self_maintenance_refactor_registry import build_self_maintenance_refactor_audit_summary

MINIMAL_LIVE_CHANGE_REPLAY_VERSION = "500.0"

MINIMAL_LIVE_CHANGE_REPLAY_BOUNDARIES: dict[str, bool] = {
    "replay_packet_applies_change": False,
    "replay_packet_replays_automatically": False,
    "replay_packet_mutates_source": False,
    "expected_actual_writes_files": False,
    "expected_actual_runs_verification": False,
    "expected_actual_treats_match_as_approval": False,
    "regression_detector_changes_behavior": False,
    "regression_detector_auto_fixes": False,
    "regression_detector_invokes_models": False,
    "recovery_recommendation_executes_rollback": False,
    "recovery_recommendation_edits_files": False,
    "recovery_recommendation_reruns_commands": False,
    "recovery_recommendation_creates_release_candidate": False,
    "replay_audit_mutates_memory": False,
    "replay_audit_alters_identity": False,
    "replay_audit_alters_personality": False,
    "replay_audit_publishes_release": False,
    "replay_audit_continues_automatically": False,
    "minimal_replay_review_only": True,
    "minimal_replay_expected_actual_required": True,
    "minimal_replay_recovery_is_recommendation_only": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

REPLAY_REQUIRED_FIELDS = [
    "original_candidate_id",
    "approval_lock_id",
    "transaction_id",
    "application_harness_id",
    "audit_id",
    "expected_touched_files",
    "expected_unchanged_files",
    "expected_readme_update",
    "expected_release_history_update",
    "expected_version_update",
    "expected_smoke_checks",
    "expected_rollback_packet",
]

EXPECTED_TOUCHED_FILES = [
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/dashboard.py",
    "tools/smoke_check.py",
]

EXPECTED_UNCHANGED_SURFACES = [
    "memory stores",
    "identity source of truth",
    "personality engine",
    "runtime prompt behavior",
    "local model invocation defaults",
    "release publishing workflow",
]

RECOVERY_ACTIONS = [
    "manual rollback",
    "manual patch correction",
    "return to sandbox",
    "operator review",
    "block further live-change attempts",
    "rerun targeted verification",
    "prepare a narrower candidate",
]


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _missing_fields(evidence: dict[str, Any], required: list[str]) -> list[str]:
    missing: list[str] = []
    for field in required:
        value = evidence.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)
    return missing


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "automatic replay request": ["replay automatically", "auto replay", "run replay now"],
        "source mutation request": ["write files", "edit source", "apply patch", "change files now"],
        "rollback execution request": ["execute rollback", "run rollback", "restore files now"],
        "autonomy expansion request": ["self approve", "continue automatically", "hidden loop", "daily loop"],
        "identity/personality mutation request": ["rewrite identity", "alter personality", "personality engine", "mutate memory"],
        "release/publishing request": ["publish release", "create release candidate", "ship automatically"],
        "model invocation request": ["invoke local model", "ask model by default", "model consensus approves"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    if flags or blockers:
        return "blocked"
    return "reviewable"


def build_minimal_live_change_replay_packet_summary(
    request_text: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    missing = _missing_fields(evidence, REPLAY_REQUIRED_FIELDS)
    expected_touched = _listify(evidence.get("expected_touched_files") or EXPECTED_TOUCHED_FILES)
    unexpected_allowed = [path for path in expected_touched if path not in EXPECTED_TOUCHED_FILES]
    blockers: list[str] = []
    if unexpected_allowed:
        blockers.append("replay packet includes touched files outside the minimal approved surface")
    blockers.extend(f"missing:{field}" for field in missing)
    return {
        "version": MINIMAL_LIVE_CHANGE_REPLAY_VERSION,
        "state": "minimal_live_change_replay_packet_review_only",
        "required_fields": list(REPLAY_REQUIRED_FIELDS),
        "submitted_evidence_fields": sorted(evidence.keys()),
        "missing_fields": missing,
        "original_candidate_id": evidence.get("original_candidate_id"),
        "approval_lock_id": evidence.get("approval_lock_id"),
        "transaction_id": evidence.get("transaction_id"),
        "application_harness_id": evidence.get("application_harness_id"),
        "audit_id": evidence.get("audit_id"),
        "expected_touched_files": expected_touched,
        "expected_unchanged_files": _listify(evidence.get("expected_unchanged_files") or EXPECTED_UNCHANGED_SURFACES),
        "expected_smoke_checks": _listify(evidence.get("expected_smoke_checks") or ["fast", "install", "v360 targeted", "v370 targeted"]),
        "expected_rollback_packet": evidence.get("expected_rollback_packet"),
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "applies_change": False,
        "replays_automatically": False,
        "mutates_source": False,
        "review_only": True,
    }


def build_minimal_live_change_expected_actual_comparison_summary(
    request_text: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    expected_changed = set(_listify(evidence.get("expected_changed_files") or EXPECTED_TOUCHED_FILES))
    actual_changed = set(_listify(evidence.get("actual_changed_files") or EXPECTED_TOUCHED_FILES))
    unexpected_changed = sorted(actual_changed - expected_changed)
    missing_expected = sorted(expected_changed - actual_changed)
    checks = {
        "readme_updated": bool(evidence.get("readme_updated", True)),
        "release_history_updated": bool(evidence.get("release_history_updated", True)),
        "version_markers_updated": bool(evidence.get("version_markers_updated", True)),
        "dashboard_api_cli_healthy": bool(evidence.get("dashboard_api_cli_healthy", True)),
        "smoke_checks_passing": bool(evidence.get("smoke_checks_passing", True)),
        "package_privacy_clean": bool(evidence.get("package_privacy_clean", True)),
    }
    blockers = []
    if unexpected_changed:
        blockers.append("unexpected files changed")
    if missing_expected:
        blockers.append("expected files did not change")
    blockers.extend([key for key, value in checks.items() if not value])
    return {
        "version": MINIMAL_LIVE_CHANGE_REPLAY_VERSION,
        "state": "minimal_live_change_expected_vs_actual_comparison_review_only",
        "expected_changed_files": sorted(expected_changed),
        "actual_changed_files": sorted(actual_changed),
        "unexpected_changed_files": unexpected_changed,
        "missing_expected_changed_files": missing_expected,
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "writes_files": False,
        "runs_verification": False,
        "treats_match_as_approval": False,
        "review_only": True,
    }


def build_minimal_live_change_regression_drift_detector_summary(
    dashboard_text: str | None = None,
    request_text: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    text = dashboard_text or ""
    checks = {
        "approval_boundaries_preserved": bool(evidence.get("approval_boundaries_preserved", True)),
        "forbidden_autonomy_claims_absent": bool(evidence.get("forbidden_autonomy_claims_absent", True)),
        "route_api_cli_parity_preserved": bool(evidence.get("route_api_cli_parity_preserved", True)),
        "registry_entries_preserved": bool(evidence.get("registry_entries_preserved", True)),
        "source_only_package_rules_preserved": bool(evidence.get("source_only_package_rules_preserved", True)),
        "data_tip_present": "data-tip" in text,
        "native_title_tooltips_absent": bool(evidence.get("native_title_tooltips_absent", True)),
        "stable_json_write_behavior_preserved": bool(evidence.get("stable_json_write_behavior_preserved", True)),
        "old_gate_compatibility_preserved": bool(evidence.get("old_gate_compatibility_preserved", True)),
    }
    blockers = [key for key, value in checks.items() if not value]
    return {
        "version": MINIMAL_LIVE_CHANGE_REPLAY_VERSION,
        "state": "minimal_live_change_regression_drift_detector_review_only",
        "checks": checks,
        "drift_detected": bool(blockers),
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "changes_behavior": False,
        "auto_fixes": False,
        "invokes_models": False,
        "review_only": True,
    }


def build_minimal_live_change_recovery_recommendation_summary(
    request_text: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    detected_issues = _listify(evidence.get("detected_issues") or [])
    recommended = _listify(evidence.get("recommended_actions") or (RECOVERY_ACTIONS[:3] if detected_issues else ["operator review"]))
    invalid_actions = [action for action in recommended if action not in RECOVERY_ACTIONS]
    blockers = []
    if invalid_actions:
        blockers.append("recommended action outside recovery recommendation catalog")
    return {
        "version": MINIMAL_LIVE_CHANGE_REPLAY_VERSION,
        "state": "minimal_live_change_recovery_recommendation_only",
        "detected_issues": detected_issues,
        "recommended_actions": recommended,
        "invalid_actions": invalid_actions,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "executes_rollback": False,
        "edits_files": False,
        "reruns_commands": False,
        "creates_release_candidate": False,
        "recommendation_only": True,
    }


def build_minimal_live_change_replay_regression_audit_summary(
    root: Path | None = None,
    dashboard_text: str | None = None,
    request_text: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    root = root or Path(__file__).resolve().parents[1]
    replay = build_minimal_live_change_replay_packet_summary(request_text, evidence)
    comparison = build_minimal_live_change_expected_actual_comparison_summary(request_text, evidence)
    drift = build_minimal_live_change_regression_drift_detector_summary(dashboard_text, request_text, evidence)
    recovery = build_minimal_live_change_recovery_recommendation_summary(request_text, evidence)
    minimal_application = build_minimal_live_expression_application_audit_summary(dashboard_text=dashboard_text, request_text="review only", evidence={
        "candidate_type": "dashboard-facing expression status line",
        "candidate_files": ["conscious_agent/dashboard.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "tools/smoke_check.py"],
        "approval_id": "approval",
        "approval_scope": "approve-one-minimal-expression-adjacent-source-change",
        "approval_expiration": "fresh",
        "target_version": "v360.0",
        "allowed_files": ["conscious_agent/dashboard.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "tools/smoke_check.py"],
        "allowed_change_summary": "status line",
        "forbidden_files": ["conscious_agent/chat.py", "data/autonomy/", "memory stores"],
        "rollback_requirement": "required",
        "verification_requirement": "required",
        "single_use": True,
        "transaction_id": "tx",
        "preimage_match": True,
        "allowed_file_match": True,
        "operator_confirmation_phrase": "I explicitly approve this one minimal scoped expression-adjacent source change",
        "rollback_packet_present": True,
        "verification_checklist_present": True,
    })
    refactor = build_self_maintenance_refactor_audit_summary(root, "385.0")
    false_ok = all(value is False for key, value in MINIMAL_LIVE_CHANGE_REPLAY_BOUNDARIES.items() if key.startswith(("replay_packet_", "expected_actual_", "regression_detector_", "recovery_recommendation_", "replay_audit_")))
    true_ok = all(MINIMAL_LIVE_CHANGE_REPLAY_BOUNDARIES[key] is True for key in ["minimal_replay_review_only", "minimal_replay_expected_actual_required", "minimal_replay_recovery_is_recommendation_only", "dashboard_data_tip_required", "native_title_tooltips_forbidden"])
    ok = all(packet.get("status") == "reviewable" for packet in [replay, comparison, drift, recovery]) and false_ok and true_ok and bool(minimal_application.get("ok", True)) and bool(refactor.get("boundaries_ok", True))
    return {
        "version": MINIMAL_LIVE_CHANGE_REPLAY_VERSION,
        "state": "minimal_live_change_replay_and_regression_hardening_audit",
        "replay_packet": replay,
        "expected_actual_comparison": comparison,
        "regression_drift_detector": drift,
        "recovery_recommendation": recovery,
        "minimal_application_baseline": minimal_application,
        "self_maintenance_refactor_baseline": refactor,
        "boundaries": dict(MINIMAL_LIVE_CHANGE_REPLAY_BOUNDARIES),
        "boundaries_ok": false_ok and true_ok,
        "ok": ok,
        "mutates_memory": False,
        "alters_identity": False,
        "alters_personality": False,
        "publishes_release": False,
        "continues_automatically": False,
        "safe_next_action": "Operator may review replay/regression hardening results. No replay, source edit, rollback, command execution, identity/personality/memory mutation, release creation, or autonomous continuation is authorized.",
    }


def render_minimal_live_change_replay_lines(summary: dict[str, Any]) -> list[str]:
    lines = []
    for key in ["version", "state", "status", "ok", "boundaries_ok", "review_only", "recommendation_only", "drift_detected", "safe_next_action"]:
        if key in summary:
            lines.append(f"- {key}: {summary[key]}")
    if summary.get("blockers"):
        lines.append("- blockers: " + ", ".join(map(str, summary.get("blockers", []))))
    return lines or ["- no summary details available"]
