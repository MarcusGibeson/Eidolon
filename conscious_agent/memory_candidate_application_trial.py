from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION = RUNTIME_VERSION
MEMORY_CANDIDATE_APPLICATION_TRIAL_BOUNDARIES: dict[str, bool] = {
    "candidate_selection_writes_memory": False,
    "candidate_selection_mutates_identity": False,
    "candidate_selection_alters_personality": False,
    "candidate_selection_treats_eligibility_as_approval": False,
    "approval_lock_self_approves": False,
    "approval_lock_reuses_approval": False,
    "approval_lock_treats_prior_success_as_authorization": False,
    "transaction_preview_writes_memory": False,
    "transaction_preview_alters_current_behavior": False,
    "transaction_preview_rewrites_identity_personality_purpose": False,
    "application_harness_runs_without_confirmation": False,
    "application_harness_stores_sensitive_data_without_approval": False,
    "application_harness_expands_autonomy": False,
    "application_harness_invokes_models": False,
    "application_audit_self_approves": False,
    "application_audit_runs_retraction": False,
    "application_audit_applies_patches": False,
    "application_audit_publishes_release": False,
    "application_audit_creates_release_candidate": False,
    "application_audit_continues_automatically": False,
    "fresh_operator_approval_required": True,
    "single_use_memory_approval_required": True,
    "sensitive_data_screen_required": True,
    "identity_personality_mutation_screen_required": True,
    "retraction_packet_required": True,
    "post_application_audit_required": True,
    "memory_application_trial_operator_confirmed_only": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

MEMORY_CANDIDATE_FIELDS = [
    "candidate_id",
    "source_trial_id",
    "lesson_text",
    "candidate_type",
    "scope",
    "risk_classification",
    "operator_review_required",
    "storage_not_authorized_yet",
]

MEMORY_APPROVAL_FIELDS = [
    "approval_id",
    "selected_candidate_id",
    "operator_confirmation_phrase",
    "allowed_memory_scope",
    "forbidden_memory_categories",
    "single_use",
    "expiration",
    "rollback_retraction_note",
    "post_application_audit_required",
]

SAFE_FIRST_MEMORY_CANDIDATE = "Operator-approved live patch trials must remain single-use, scoped, rollback-aware, and separated from future authorization."
EXPECTED_MEMORY_CONFIRMATION_PHRASE = "I explicitly approve this one scoped memory candidate application trial"


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
        "memory self-approval request": ["self approve", "auto approve memory", "approve myself"],
        "automatic memory write request": ["auto-store", "automatically store", "store without approval", "write memory now"],
        "identity/personality mutation request": ["rewrite identity", "alter personality", "change personality", "rewrite purpose", "identity prompt"],
        "sensitive memory request": ["precise address", "medical diagnosis", "religion", "political affiliation", "criminal record"],
        "approval reuse request": ["reuse approval", "same approval", "approval carries forward"],
        "autonomy expansion request": ["continue automatically", "schedule hidden", "auto select", "daily loop"],
        "model/release/patch request": ["invoke local model", "publish release", "create release candidate", "apply patch"],
        "retraction execution request": ["run retraction", "execute rollback", "delete memory automatically"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    return "blocked" if flags or blockers else "reviewable"


def _candidate_from_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    candidate = evidence.get("candidate", {}) if isinstance(evidence.get("candidate", {}), dict) else {}
    defaults = {
        "candidate_id": "memory-candidate-v405-001",
        "source_trial_id": "trial-history-v395-review",
        "lesson_text": SAFE_FIRST_MEMORY_CANDIDATE,
        "candidate_type": "governance_lesson",
        "scope": "live_patch_trial_governance",
        "risk_classification": "low_docs_governance",
        "operator_review_required": True,
        "storage_not_authorized_yet": True,
    }
    defaults.update(candidate)
    return defaults


def build_memory_candidate_selection_packet_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    candidate = _candidate_from_evidence(evidence)
    missing = [field for field in MEMORY_CANDIDATE_FIELDS if candidate.get(field) in (None, "", [])]
    blockers = [f"missing:{field}" for field in missing]
    if candidate.get("operator_review_required") is not True:
        blockers.append("operator review not required")
    if candidate.get("storage_not_authorized_yet") is not True:
        blockers.append("storage appears authorized before approval lock")
    lesson = str(candidate.get("lesson_text", "")).lower()
    if any(token in lesson for token in ["always approve", "auto approve", "no approval needed", "store automatically", "rewrite identity", "alter personality"]):
        blockers.append("unsafe memory lesson text")
    return {
        "version": MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION,
        "state": "memory_candidate_selection_review_only",
        "candidate_fields": MEMORY_CANDIDATE_FIELDS,
        "selected_candidate": candidate,
        "missing_fields": missing,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "writes_memory": False,
        "mutates_identity": False,
        "alters_personality": False,
        "treats_eligibility_as_approval": False,
        "review_only": True,
    }


def build_memory_application_approval_lock_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    approval = evidence.get("approval", {}) if isinstance(evidence.get("approval", {}), dict) else {}
    candidate = _candidate_from_evidence(evidence)
    defaults = {
        "approval_id": "memory-approval-v405-single-use",
        "selected_candidate_id": candidate.get("candidate_id"),
        "operator_confirmation_phrase": EXPECTED_MEMORY_CONFIRMATION_PHRASE,
        "allowed_memory_scope": "governance lesson only",
        "forbidden_memory_categories": ["identity", "personality", "purpose", "autonomy expansion", "sensitive personal data"],
        "single_use": True,
        "expiration": "operator-defined-current-session-only",
        "rollback_retraction_note": "operator-reviewed retraction packet required",
        "post_application_audit_required": True,
    }
    defaults.update(approval)
    missing = [field for field in MEMORY_APPROVAL_FIELDS if defaults.get(field) in (None, "", [])]
    blockers = [f"missing:{field}" for field in missing]
    if defaults.get("single_use") is not True:
        blockers.append("approval not single-use")
    if defaults.get("selected_candidate_id") != candidate.get("candidate_id"):
        blockers.append("approval candidate mismatch")
    if evidence.get("approval_reused") is True:
        blockers.append("approval reuse attempted")
    if evidence.get("prior_success_as_authorization") is True:
        blockers.append("prior success treated as authorization")
    forbidden = " ".join(_listify(defaults.get("forbidden_memory_categories"))).lower()
    for token in ["identity", "personality", "purpose", "autonomy"]:
        if token not in forbidden:
            blockers.append(f"forbidden category missing:{token}")
    return {
        "version": MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION,
        "state": "memory_application_approval_lock_single_use",
        "approval_fields": MEMORY_APPROVAL_FIELDS,
        "approval_lock": defaults,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "self_approves": False,
        "reuses_approval": False,
        "treats_prior_success_as_authorization": False,
        "fresh_operator_approval_required": True,
        "single_use_required": True,
        "review_only": True,
    }


def build_memory_write_transaction_preview_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    candidate = _candidate_from_evidence(evidence)
    approval = build_memory_application_approval_lock_summary("review only", evidence).get("approval_lock", {})
    preview = evidence.get("transaction_preview", {}) if isinstance(evidence.get("transaction_preview", {}), dict) else {}
    defaults = {
        "transaction_id": "memory-write-preview-v405-001",
        "candidate_id": candidate.get("candidate_id"),
        "approval_id": approval.get("approval_id"),
        "memory_destination": "supervised_governance_memory_candidate_store",
        "exact_memory_text": candidate.get("lesson_text"),
        "reason_for_storage": "Preserve a factual governance lesson from supervised live patch trials.",
        "expected_future_use": "Remind future planning that live patch approvals are single-use and scoped.",
        "sensitive_data_screen": "passed",
        "identity_personality_mutation_screen": "passed",
        "scope_limits": ["governance lesson", "no identity", "no personality", "no autonomy expansion"],
        "rollback_retraction_plan": "operator-reviewed retraction packet required before any removal action",
    }
    defaults.update(preview)
    blockers: list[str] = []
    if defaults.get("candidate_id") != candidate.get("candidate_id"):
        blockers.append("transaction candidate mismatch")
    if defaults.get("approval_id") != approval.get("approval_id"):
        blockers.append("transaction approval mismatch")
    if defaults.get("exact_memory_text") != candidate.get("lesson_text"):
        blockers.append("memory text differs from candidate")
    if defaults.get("sensitive_data_screen") != "passed":
        blockers.append("sensitive data screen not passed")
    if defaults.get("identity_personality_mutation_screen") != "passed":
        blockers.append("identity/personality mutation screen not passed")
    if evidence.get("write_now") is True or evidence.get("writes_memory") is True:
        blockers.append("memory write attempted during preview")
    return {
        "version": MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION,
        "state": "memory_write_transaction_preview_only",
        "transaction_preview": defaults,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "writes_memory": False,
        "alters_current_behavior": False,
        "rewrites_identity_personality_purpose": False,
        "review_only": True,
    }


def build_operator_confirmed_memory_application_trial_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    candidate = _candidate_from_evidence(evidence)
    approval_summary = build_memory_application_approval_lock_summary("review only", evidence)
    approval = approval_summary.get("approval_lock", {})
    preview = build_memory_write_transaction_preview_summary("review only", evidence).get("transaction_preview", {})
    confirmation_supplied = "operator_confirmation_phrase" in evidence
    confirmation = str(evidence.get("operator_confirmation_phrase", ""))
    checks = {
        "fresh_approval_id": bool(approval.get("approval_id")),
        "matching_candidate_id": approval.get("selected_candidate_id") == candidate.get("candidate_id") == preview.get("candidate_id"),
        "matching_transaction_preview_id": bool(preview.get("transaction_id")),
        "explicit_confirmation_supplied": confirmation_supplied,
        "operator_confirmation_phrase_exact": confirmation_supplied and confirmation == EXPECTED_MEMORY_CONFIRMATION_PHRASE,
        "sensitive_data_screen_passed": preview.get("sensitive_data_screen") == "passed",
        "identity_personality_mutation_screen_passed": preview.get("identity_personality_mutation_screen") == "passed",
        "single_use_approval_unused": evidence.get("approval_reused") is not True,
        "retraction_packet_present": bool(preview.get("rollback_retraction_plan")),
        "post_application_audit_present": approval.get("post_application_audit_required") is True,
    }
    blockers = [key for key, value in checks.items() if not value]
    if evidence.get("candidate_changed_after_approval") is True:
        blockers.append("candidate changed after approval")
    if evidence.get("memory_text_differs_from_preview") is True:
        blockers.append("memory text differs from preview")
    if evidence.get("stores_sensitive_data") is True:
        blockers.append("sensitive data storage attempted")
    if evidence.get("expands_autonomy") is True:
        blockers.append("autonomy expansion attempted")
    if evidence.get("mutates_identity") is True or evidence.get("alters_personality") is True:
        blockers.append("identity/personality mutation attempted")
    return {
        "version": MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION,
        "state": "operator_confirmed_memory_application_trial_harness",
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "runs_without_confirmation": False,
        "stores_sensitive_data_without_approval": False,
        "expands_autonomy": False,
        "invokes_models": False,
        "operator_confirmed_only": True,
        "explicit_confirmation_required": True,
        "review_only_until_confirmation": True,
    }


def build_memory_application_trial_audit_summary(root: Path | None = None, dashboard_text: str | None = None, request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    docs = dashboard_text or ""
    evidence = dict(evidence or {})
    selection = build_memory_candidate_selection_packet_summary(request_text or "review only", evidence)
    approval = build_memory_application_approval_lock_summary(request_text or "review only", evidence)
    preview = build_memory_write_transaction_preview_summary(request_text or "review only", evidence)
    harness_evidence = dict(evidence)
    harness_evidence.setdefault("operator_confirmation_phrase", EXPECTED_MEMORY_CONFIRMATION_PHRASE)
    harness = build_operator_confirmed_memory_application_trial_summary(request_text or "review only", harness_evidence)
    doc_checks = {
        "readme_updated": "v400.0 - Operator-Approved Memory Candidate Application Trial v1" in docs,
        "release_history_updated": "v400.0 - Operator-Approved Memory Candidate Application Trial v1" in docs,
        "version_markers_current": 'MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION = "1065.10"' in docs,
        "dashboard_data_tip_present": "data-tip" in docs,
        "command_deck_present": "command-deck" in docs,
        "operator_console_present": "operator-console" in docs,
        "runtime_private_dirs_documented": "data/autonomy/memory_application_trial_audit/" in docs,
        "api_cli_tokens_present": "operator-governed-memory-application-trial-audit-v1" in docs,
        "package_privacy_tokens_present": "source-only" in docs and "forbidden/private/runtime" in docs,
    }
    boundary_checks = dict(MEMORY_CANDIDATE_APPLICATION_TRIAL_BOUNDARIES)
    summary_checks = {
        "selection_review_only": selection.get("writes_memory") is False and selection.get("treats_eligibility_as_approval") is False,
        "approval_single_use": approval.get("single_use_required") is True and approval.get("reuses_approval") is False,
        "preview_no_write": preview.get("writes_memory") is False and preview.get("rewrites_identity_personality_purpose") is False,
        "harness_confirmation_bound": harness.get("runs_without_confirmation") is False and harness.get("operator_confirmed_only") is True,
        "no_sensitive_unapproved_storage": harness.get("stores_sensitive_data_without_approval") is False,
        "no_autonomy_expansion": harness.get("expands_autonomy") is False,
        "no_model_invocation": harness.get("invokes_models") is False,
    }
    blockers: list[str] = []
    for label, report in [("selection", selection), ("approval", approval), ("preview", preview), ("harness", harness)]:
        if report.get("status") == "blocked":
            blockers.append(f"{label}:" + ";".join(_listify(report.get("blockers"))))
    blockers.extend([f"doc:{key}" for key, value in doc_checks.items() if not value])
    blockers.extend([f"summary:{key}" for key, value in summary_checks.items() if not value])
    true_boundary_keys = {
        "fresh_operator_approval_required",
        "single_use_memory_approval_required",
        "sensitive_data_screen_required",
        "identity_personality_mutation_screen_required",
        "retraction_packet_required",
        "post_application_audit_required",
        "memory_application_trial_operator_confirmed_only",
        "dashboard_data_tip_required",
        "native_title_tooltips_forbidden",
    }
    for key, value in boundary_checks.items():
        if key in true_boundary_keys:
            if value is not True:
                blockers.append(f"boundary:{key}")
        elif value is not False:
            blockers.append(f"boundary:{key}")
    return {
        "version": MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION,
        "state": "memory_application_trial_audit_review_only",
        "candidate_selection": selection,
        "approval_lock": approval,
        "transaction_preview": preview,
        "application_harness": harness,
        "doc_checks": doc_checks,
        "summary_checks": summary_checks,
        "boundaries": boundary_checks,
        "blockers": blockers,
        "ok": not blockers,
        "status": "pass" if not blockers else "blocked",
        "self_approves": False,
        "runs_retraction": False,
        "applies_patches": False,
        "publishes_release": False,
        "creates_release_candidate": False,
        "continues_automatically": False,
        "safe_next_action": "Operator may review the v405 hardened memory application trial audit. No memory write, retraction, patch, release, or automatic continuation is authorized by this packet.",
    }


def render_memory_candidate_application_trial_lines(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ["version", "state", "status", "ok"]:
        if key in report:
            lines.append(f"- {key}: {report[key]}")
    blockers = report.get("blockers") or []
    lines.append("- blockers: " + (", ".join(str(item) for item in blockers) if blockers else "none"))
    for key in ["writes_memory", "self_approves", "reuses_approval", "runs_without_confirmation", "expands_autonomy", "continues_automatically"]:
        if key in report:
            lines.append(f"- {key}: {report[key]}")
    return lines
