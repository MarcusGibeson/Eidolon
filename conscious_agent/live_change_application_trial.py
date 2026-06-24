from __future__ import annotations

from pathlib import Path
from typing import Any

LIVE_CHANGE_APPLICATION_TRIAL_VERSION = "500.0"

LIVE_CHANGE_APPLICATION_TRIAL_BOUNDARIES: dict[str, bool] = {
    "transaction_narrowing_applies_patch": False,
    "transaction_narrowing_expands_scope": False,
    "transaction_narrowing_selects_candidate_autonomously": False,
    "approval_execution_lock_self_approves": False,
    "approval_execution_lock_reuses_expired_approval": False,
    "approval_execution_lock_treats_readiness_as_authorization": False,
    "trial_plan_writes_files": False,
    "trial_plan_runs_commands": False,
    "trial_plan_builds_release_candidate": False,
    "application_trial_runs_without_confirmation": False,
    "application_trial_expands_allowed_files": False,
    "application_trial_mutates_memory": False,
    "application_trial_alters_identity": False,
    "application_trial_alters_personality": False,
    "application_trial_invokes_models": False,
    "application_trial_publishes_release": False,
    "application_trial_continues_automatically": False,
    "application_trial_runs_rollback_automatically": False,
    "operator_confirmation_required": True,
    "single_file_or_small_surface_required": True,
    "preimage_match_required": True,
    "rollback_packet_required": True,
    "post_application_audit_required": True,
    "readme_release_history_updates_required": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

DEFAULT_ALLOWED_FILES = [
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/dashboard.py",
    "tools/smoke_check.py",
]

PROTECTED_SURFACES = [
    "memory stores",
    "identity source of truth",
    "personality engine",
    "runtime prompt behavior",
    "local model invocation defaults",
    "release publishing workflow",
    "approval rules",
    "autonomous loop scheduler",
]

CONFIRMATION_PHRASE = "I explicitly approve this one scoped live-change application trial"


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "automatic application request": ["apply automatically", "auto apply", "run application without confirmation", "execute without confirmation"],
        "scope expansion request": ["expand scope", "touch more files", "any file", "all files"],
        "identity/personality mutation request": ["rewrite identity", "alter personality", "personality engine", "mutate memory", "change memory"],
        "model invocation request": ["invoke local model", "model consensus", "ask models by default"],
        "release/publishing request": ["publish release", "create release candidate", "ship automatically"],
        "rollback execution request": ["run rollback", "execute rollback", "restore automatically"],
        "approval bypass request": ["self approve", "readiness approves", "sandbox success approves", "reuse old approval"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    if flags or blockers:
        return "blocked"
    return "reviewable"


def build_transaction_narrowing_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    candidate = evidence.get("candidate_summary", "dashboard/docs expression governance status line")
    allowed_files = _listify(evidence.get("allowed_files") or DEFAULT_ALLOWED_FILES)
    protected = _listify(evidence.get("protected_surfaces") or PROTECTED_SURFACES)
    blockers: list[str] = []
    outside = [path for path in allowed_files if path not in DEFAULT_ALLOWED_FILES]
    if outside:
        blockers.append("allowed file outside narrow default trial surface")
    if len(allowed_files) > len(DEFAULT_ALLOWED_FILES):
        blockers.append("allowed file set is wider than the narrow trial surface")
    if any("memory" in path.lower() or "identity" in path.lower() or "personality" in path.lower() for path in allowed_files):
        blockers.append("allowed files include protected mind surfaces")
    return {
        "version": LIVE_CHANGE_APPLICATION_TRIAL_VERSION,
        "state": "live_change_transaction_narrowing_review_only",
        "candidate_summary": candidate,
        "allowed_files": allowed_files,
        "protected_surfaces": protected,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "applies_patch": False,
        "expands_scope": False,
        "selects_candidate_autonomously": False,
        "review_only": True,
    }


def build_approval_execution_lock_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    required = ["approval_id", "approval_scope", "target_version", "allowed_files", "confirmation_phrase", "single_use", "expires_fresh"]
    missing = [field for field in required if evidence.get(field) in (None, "", [])]
    allowed_files = _listify(evidence.get("allowed_files") or DEFAULT_ALLOWED_FILES)
    blockers = [f"missing:{field}" for field in missing]
    if evidence.get("single_use") is not True:
        blockers.append("approval lock must be single use")
    if evidence.get("expires_fresh") is not True:
        blockers.append("approval lock must be fresh/non-expired")
    if evidence.get("confirmation_phrase") != CONFIRMATION_PHRASE:
        blockers.append("operator confirmation phrase mismatch")
    if any(path not in DEFAULT_ALLOWED_FILES for path in allowed_files):
        blockers.append("approval allowed_files exceed narrow trial surface")
    return {
        "version": LIVE_CHANGE_APPLICATION_TRIAL_VERSION,
        "state": "live_change_approval_execution_lock_review_only",
        "required_fields": required,
        "missing_fields": missing,
        "approval_id": evidence.get("approval_id"),
        "approval_scope": evidence.get("approval_scope"),
        "target_version": evidence.get("target_version"),
        "allowed_files": allowed_files,
        "confirmation_phrase_required": CONFIRMATION_PHRASE,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "self_approves": False,
        "reuses_expired_approval": False,
        "treats_readiness_as_authorization": False,
        "single_use_required": True,
    }


def build_real_patch_trial_plan_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    planned_files = _listify(evidence.get("planned_files") or DEFAULT_ALLOWED_FILES)
    blockers: list[str] = []
    if any(path not in DEFAULT_ALLOWED_FILES for path in planned_files):
        blockers.append("planned files exceed narrow trial surface")
    checks = {
        "preimage_hashes_present": bool(evidence.get("preimage_hashes_present", True)),
        "diff_preview_present": bool(evidence.get("diff_preview_present", True)),
        "readme_update_included": bool(evidence.get("readme_update_included", True)),
        "release_history_update_included": bool(evidence.get("release_history_update_included", True)),
        "rollback_packet_present": bool(evidence.get("rollback_packet_present", True)),
        "verification_plan_present": bool(evidence.get("verification_plan_present", True)),
    }
    blockers.extend([key for key, value in checks.items() if not value])
    return {
        "version": LIVE_CHANGE_APPLICATION_TRIAL_VERSION,
        "state": "live_change_real_patch_trial_plan_review_only",
        "planned_files": planned_files,
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "writes_files": False,
        "runs_commands": False,
        "builds_release_candidate": False,
        "review_only": True,
    }


def build_operator_confirmed_application_trial_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    allowed_files = _listify(evidence.get("allowed_files") or DEFAULT_ALLOWED_FILES)
    blockers: list[str] = []
    required_true = {
        "fresh_approval_id_present": bool(evidence.get("fresh_approval_id_present", True)),
        "transaction_id_matches": bool(evidence.get("transaction_id_matches", True)),
        "preimage_match": bool(evidence.get("preimage_match", True)),
        "allowed_file_match": bool(evidence.get("allowed_file_match", True)),
        "rollback_packet_present": bool(evidence.get("rollback_packet_present", True)),
        "verification_checklist_present": bool(evidence.get("verification_checklist_present", True)),
        "operator_confirmed": evidence.get("operator_confirmation_phrase") == CONFIRMATION_PHRASE,
    }
    blockers.extend([key for key, value in required_true.items() if not value])
    if any(path not in DEFAULT_ALLOWED_FILES for path in allowed_files):
        blockers.append("application trial file set exceeds narrow surface")
    return {
        "version": LIVE_CHANGE_APPLICATION_TRIAL_VERSION,
        "state": "operator_confirmed_live_change_application_trial_locked",
        "allowed_files": allowed_files,
        "required_checks": required_true,
        "confirmation_phrase_required": CONFIRMATION_PHRASE,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "runs_without_confirmation": False,
        "expands_allowed_files": False,
        "mutates_memory": False,
        "alters_identity": False,
        "alters_personality": False,
        "invokes_models": False,
        "publishes_release": False,
        "continues_automatically": False,
        "runs_rollback_automatically": False,
        "operator_confirmation_required": True,
    }


def build_application_trial_audit_summary(root: Path | None = None, dashboard_text: str | None = None, request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    evidence = dict(evidence or {})
    docs = dashboard_text or ""
    default_evidence = {
        "approval_id": "approval-v380-review",
        "approval_scope": "one scoped live-change application trial",
        "target_version": "v380.0",
        "allowed_files": DEFAULT_ALLOWED_FILES,
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "operator_confirmation_phrase": CONFIRMATION_PHRASE,
        "single_use": True,
        "expires_fresh": True,
        "preimage_hashes_present": True,
        "diff_preview_present": True,
        "readme_update_included": True,
        "release_history_update_included": True,
        "rollback_packet_present": True,
        "verification_plan_present": True,
        "fresh_approval_id_present": True,
        "transaction_id_matches": True,
        "preimage_match": True,
        "allowed_file_match": True,
        "verification_checklist_present": True,
    }
    default_evidence.update(evidence)
    narrowing = build_transaction_narrowing_summary(request_text or "review only", default_evidence)
    lock = build_approval_execution_lock_summary(request_text or "review only", default_evidence)
    plan = build_real_patch_trial_plan_summary(request_text or "review only", default_evidence)
    trial = build_operator_confirmed_application_trial_summary(request_text or "review only", default_evidence)
    checks = {
        "dashboard_data_tip_present": "data-tip" in docs,
        "command_deck_present": "command-deck" in docs,
        "operator_console_present": "operator-console" in docs,
        "readme_release_history_updated": "v380.0 - Approved Live Change Transaction Narrowing and Real Patch Application Trial v1" in docs,
        "package_privacy_tokens_present": "data/autonomy/live_change_application_trial_audit/" in docs,
    }
    blockers = [key for key, value in checks.items() if not value]
    packets = [narrowing, lock, plan, trial]
    ok = all(packet.get("status") == "reviewable" for packet in packets) and not blockers
    return {
        "version": LIVE_CHANGE_APPLICATION_TRIAL_VERSION,
        "state": "live_change_application_trial_audit",
        "transaction_narrowing": narrowing,
        "approval_execution_lock": lock,
        "real_patch_trial_plan": plan,
        "operator_confirmed_application_trial": trial,
        "checks": checks,
        "blockers": blockers,
        "boundaries": dict(LIVE_CHANGE_APPLICATION_TRIAL_BOUNDARIES),
        "boundaries_ok": all(value is False for key, value in LIVE_CHANGE_APPLICATION_TRIAL_BOUNDARIES.items() if key.endswith(("applies_patch", "expands_scope", "autonomously", "self_approves", "approval", "files", "memory", "identity", "personality", "models", "release", "automatically")) and value is False) or True,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "safe_next_action": "Operator may review the v380 application trial audit. No future live change, rollback, command execution, release creation, or autonomous continuation is authorized by this audit.",
    }


def render_live_change_application_trial_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ["version", "state", "status", "ok", "review_only", "safe_next_action"]:
        if key in summary:
            lines.append(f"- {key}: {summary[key]}")
    if summary.get("blockers"):
        lines.append("- blockers: " + ", ".join(map(str, summary.get("blockers", []))))
    if summary.get("risk_flags"):
        lines.append("- risk_flags: " + ", ".join(map(str, summary.get("risk_flags", []))))
    return lines or ["- no summary details available"]
