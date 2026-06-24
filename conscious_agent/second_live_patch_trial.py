from __future__ import annotations

from pathlib import Path
from typing import Any

SECOND_LIVE_PATCH_TRIAL_VERSION = "500.0"

SECOND_LIVE_PATCH_TRIAL_BOUNDARIES: dict[str, bool] = {
    "candidate_selection_applies_patch": False,
    "candidate_selection_selects_autonomously": False,
    "candidate_selection_allows_runtime_personality_change": False,
    "approval_validation_reuses_approval": False,
    "approval_validation_self_approves": False,
    "approval_validation_expands_scope": False,
    "transaction_lock_writes_files": False,
    "transaction_lock_mutates_source": False,
    "transaction_lock_ignores_preimage": False,
    "application_harness_runs_without_confirmation": False,
    "application_harness_executes_rollback": False,
    "application_harness_mutates_memory": False,
    "application_harness_alters_identity": False,
    "application_harness_alters_personality": False,
    "registry_audit_applies_patch": False,
    "registry_audit_invokes_models": False,
    "registry_audit_publishes_release": False,
    "registry_audit_creates_release_candidate": False,
    "registry_audit_continues_automatically": False,
    "fresh_approval_required": True,
    "single_use_approval_required": True,
    "registry_driven_checks_required": True,
    "preimage_lock_required": True,
    "approval_burnout_required": True,
    "post_trial_closure_required": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

SAFE_SECOND_PATCH_CLASSES = [
    "dashboard status/explanation line",
    "docs-only governance clarification",
    "smoke-visible approval-burnout label",
    "registry-visible metadata note",
]

FORBIDDEN_SECOND_PATCH_CLASSES = [
    "runtime personality changes",
    "identity prompt changes",
    "memory mutation behavior",
    "approval gate weakening",
    "local model invocation defaults",
    "autonomous scheduling",
]

CONFIRMATION_PHRASE = "I explicitly approve this second scoped registry-driven live patch trial"


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
        "autonomous candidate selection": ["choose on your own", "auto select", "select automatically"],
        "approval reuse": ["reuse approval", "same approval", "carry approval forward", "approval still good"],
        "scope expansion": ["expand scope", "more files", "all files", "any file"],
        "runtime personality/identity change": ["runtime personality", "rewrite identity", "identity prompt", "personality engine"],
        "memory mutation": ["mutate memory", "write memory", "store lesson automatically"],
        "model/default invocation": ["invoke local model", "change model default", "ollama default"],
        "automatic execution/recovery": ["run automatically", "execute rollback", "auto fix", "continue automatically"],
        "release request": ["publish release", "create release candidate"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    return "blocked" if flags or blockers else "reviewable"


def build_second_minimal_live_patch_candidate_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    candidate_class = evidence.get("candidate_class", "dashboard status/explanation line")
    allowed = candidate_class in SAFE_SECOND_PATCH_CLASSES
    forbidden_hits = [item for item in FORBIDDEN_SECOND_PATCH_CLASSES if item in str(candidate_class).lower()]
    blockers = []
    if not allowed:
        blockers.append("candidate class is not registry-safe")
    if forbidden_hits:
        blockers.append("candidate class overlaps forbidden patch class")
    if evidence.get("operator_supplied_candidate") is False:
        blockers.append("candidate was not operator supplied")
    return {
        "version": SECOND_LIVE_PATCH_TRIAL_VERSION,
        "state": "second_minimal_live_patch_candidate_review_only",
        "candidate_class": candidate_class,
        "safe_candidate_classes": SAFE_SECOND_PATCH_CLASSES,
        "forbidden_candidate_classes": FORBIDDEN_SECOND_PATCH_CLASSES,
        "operator_supplied_candidate": evidence.get("operator_supplied_candidate", True),
        "registry_safe_candidate": allowed and not forbidden_hits,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "applies_patch": False,
        "selects_autonomously": False,
        "allows_runtime_personality_change": False,
        "review_only": True,
    }


def build_registry_driven_approval_validation_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    checks = {
        "fresh_approval_id_present": bool(evidence.get("fresh_approval_id_present", True)),
        "single_use_token_declared": bool(evidence.get("single_use_token_declared", True)),
        "allowed_file_list_present": bool(evidence.get("allowed_file_list_present", True)),
        "forbidden_file_list_present": bool(evidence.get("forbidden_file_list_present", True)),
        "target_version_bound": bool(evidence.get("target_version_bound", True)),
        "registry_known_surface_metadata_bound": bool(evidence.get("registry_known_surface_metadata_bound", True)),
        "rollback_requirement_present": bool(evidence.get("rollback_requirement_present", True)),
        "verification_requirement_present": bool(evidence.get("verification_requirement_present", True)),
        "expiration_scope_present": bool(evidence.get("expiration_scope_present", True)),
    }
    blockers = [key for key, value in checks.items() if not value]
    if evidence.get("approval_reused") is True:
        blockers.append("approval reuse attempted")
    if evidence.get("scope_expanded") is True:
        blockers.append("scope expansion attempted")
    return {
        "version": SECOND_LIVE_PATCH_TRIAL_VERSION,
        "state": "registry_driven_approval_scope_validation_review_only",
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "reuses_approval": False,
        "self_approves": False,
        "expands_scope": False,
        "registry_driven": True,
        "review_only": True,
    }


def build_registry_driven_transaction_lock_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    expected_changed_files = _listify(evidence.get("expected_changed_files", ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "tools/smoke_check.py"]))
    expected_unchanged_files = _listify(evidence.get("expected_unchanged_files", ["conscious_agent/vector_memory.py", "conscious_agent/local_model_bridge.py", "conscious_agent/identity_expression.py"]))
    checks = {
        "transaction_id_present": bool(evidence.get("transaction_id_present", True)),
        "candidate_id_present": bool(evidence.get("candidate_id_present", True)),
        "approval_id_present": bool(evidence.get("approval_id_present", True)),
        "preimage_lock_present": bool(evidence.get("preimage_lock_present", True)),
        "readme_obligation_present": bool(evidence.get("readme_obligation_present", True)),
        "release_history_obligation_present": bool(evidence.get("release_history_obligation_present", True)),
        "version_marker_obligation_present": bool(evidence.get("version_marker_obligation_present", True)),
        "targeted_smoke_obligation_present": bool(evidence.get("targeted_smoke_obligation_present", True)),
        "package_privacy_obligation_present": bool(evidence.get("package_privacy_obligation_present", True)),
        "dashboard_data_tip_obligation_present": bool(evidence.get("dashboard_data_tip_obligation_present", True)),
    }
    blockers = [key for key, value in checks.items() if not value]
    if evidence.get("writes_files") is True:
        blockers.append("transaction attempted to write files")
    return {
        "version": SECOND_LIVE_PATCH_TRIAL_VERSION,
        "state": "registry_driven_live_patch_transaction_lock_review_only",
        "expected_changed_files": expected_changed_files,
        "expected_unchanged_files": expected_unchanged_files,
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "writes_files": False,
        "mutates_source": False,
        "ignores_preimage": False,
        "preimage_lock_required": True,
        "review_only": True,
    }


def build_second_application_harness_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    checks = {
        "fresh_approval_id_present": bool(evidence.get("fresh_approval_id_present", True)),
        "matching_transaction_id_present": bool(evidence.get("matching_transaction_id_present", True)),
        "preimage_match_required": bool(evidence.get("preimage_match_required", True)),
        "allowed_file_match_required": bool(evidence.get("allowed_file_match_required", True)),
        "operator_confirmation_phrase_required": evidence.get("operator_confirmation_phrase", CONFIRMATION_PHRASE) == CONFIRMATION_PHRASE,
        "rollback_packet_present": bool(evidence.get("rollback_packet_present", True)),
        "verification_packet_present": bool(evidence.get("verification_packet_present", True)),
        "approval_burnout_required": bool(evidence.get("approval_burnout_required", True)),
        "post_trial_closure_required": bool(evidence.get("post_trial_closure_required", True)),
    }
    blockers = [key for key, value in checks.items() if not value]
    forbidden = [
        "approval_reused", "approval_expired", "scope_expanded", "file_outside_scope",
        "preimage_mismatched", "rollback_packet_missing", "verification_packet_missing",
        "identity_mutation_attempted", "personality_mutation_attempted", "memory_mutation_attempted",
        "autonomous_continuation_attempted",
    ]
    blockers.extend(key for key in forbidden if evidence.get(key) is True)
    return {
        "version": SECOND_LIVE_PATCH_TRIAL_VERSION,
        "state": "second_operator_confirmed_application_harness_review_only",
        "required_confirmation_phrase": CONFIRMATION_PHRASE,
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "runs_without_confirmation": False,
        "executes_rollback": False,
        "mutates_memory": False,
        "alters_identity": False,
        "alters_personality": False,
        "review_only": True,
    }


def build_second_live_patch_trial_registry_audit_summary(root: Path | None = None, dashboard_text: str | None = None, request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    docs = dashboard_text or ""
    default_evidence = {
        "candidate_class": "dashboard status/explanation line",
        "operator_supplied_candidate": True,
        "fresh_approval_id_present": True,
        "single_use_token_declared": True,
        "allowed_file_list_present": True,
        "forbidden_file_list_present": True,
        "target_version_bound": True,
        "registry_known_surface_metadata_bound": True,
        "rollback_requirement_present": True,
        "verification_requirement_present": True,
        "expiration_scope_present": True,
        "transaction_id_present": True,
        "candidate_id_present": True,
        "approval_id_present": True,
        "preimage_lock_present": True,
        "matching_transaction_id_present": True,
        "preimage_match_required": True,
        "allowed_file_match_required": True,
        "operator_confirmation_phrase": CONFIRMATION_PHRASE,
        "rollback_packet_present": True,
        "verification_packet_present": True,
        "approval_burnout_required": True,
        "post_trial_closure_required": True,
    }
    default_evidence.update(evidence or {})
    candidate = build_second_minimal_live_patch_candidate_summary(request_text or "review only", default_evidence)
    approval = build_registry_driven_approval_validation_summary(request_text or "review only", default_evidence)
    transaction = build_registry_driven_transaction_lock_summary(request_text or "review only", default_evidence)
    harness = build_second_application_harness_summary(request_text or "review only", default_evidence)
    doc_checks = {
        "readme_updated": "v390.0 - Second Minimal Approved Live Patch Trial with Registry-Driven Execution Checks v1" in docs,
        "release_history_updated": "v390.0 - Second Minimal Approved Live Patch Trial with Registry-Driven Execution Checks v1" in docs,
        "version_markers_current": 'SECOND_LIVE_PATCH_TRIAL_VERSION = "500.0"' in docs,
        "dashboard_data_tip_present": "data-tip" in docs,
        "command_deck_present": "command-deck" in docs,
        "operator_console_present": "operator-console" in docs,
        "runtime_private_dirs_documented": "data/autonomy/second_live_patch_trial_registry_audit/" in docs,
        "approval_burnout_documented": "approval_burnout_required=True" in docs,
        "registry_driven_documented": "registry_driven_checks_required=True" in docs,
    }
    blockers = [key for key, value in doc_checks.items() if not value]
    packets = [candidate, approval, transaction, harness]
    ok = all(packet.get("status") == "reviewable" for packet in packets) and not blockers
    boundaries_false_ok = all(
        value is False for key, value in SECOND_LIVE_PATCH_TRIAL_BOUNDARIES.items()
        if key not in {"fresh_approval_required", "single_use_approval_required", "registry_driven_checks_required", "preimage_lock_required", "approval_burnout_required", "post_trial_closure_required", "dashboard_data_tip_required", "native_title_tooltips_forbidden"}
    )
    boundaries_true_ok = all(
        SECOND_LIVE_PATCH_TRIAL_BOUNDARIES[key] is True
        for key in ["fresh_approval_required", "single_use_approval_required", "registry_driven_checks_required", "preimage_lock_required", "approval_burnout_required", "post_trial_closure_required", "dashboard_data_tip_required", "native_title_tooltips_forbidden"]
    )
    return {
        "version": SECOND_LIVE_PATCH_TRIAL_VERSION,
        "state": "second_live_patch_trial_registry_audit",
        "candidate_selection": candidate,
        "approval_validation": approval,
        "transaction_lock": transaction,
        "application_harness": harness,
        "doc_checks": doc_checks,
        "blockers": blockers,
        "boundaries": dict(SECOND_LIVE_PATCH_TRIAL_BOUNDARIES),
        "boundaries_ok": boundaries_false_ok and boundaries_true_ok,
        "ok": ok and boundaries_false_ok and boundaries_true_ok,
        "status": "pass" if ok and boundaries_false_ok and boundaries_true_ok else "blocked",
        "safe_next_action": "Operator may review the v390 registry-driven second patch trial audit. No additional patch, approval reuse, rollback, source edit, release creation, memory/identity/personality mutation, model invocation, or automatic continuation is authorized.",
    }


def render_second_live_patch_trial_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ["version", "state", "status", "ok", "review_only", "safe_next_action"]:
        if key in summary:
            lines.append(f"- {key}: {summary[key]}")
    if summary.get("blockers"):
        lines.append("- blockers: " + ", ".join(map(str, summary.get("blockers", []))))
    if summary.get("risk_flags"):
        lines.append("- risk_flags: " + ", ".join(map(str, summary.get("risk_flags", []))))
    return lines or ["- no summary details available"]
