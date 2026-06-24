from __future__ import annotations

from pathlib import Path
from typing import Any

LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION = "500.0"

LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_BOUNDARIES: dict[str, bool] = {
    "history_ledger_treats_history_as_permission": False,
    "history_ledger_applies_patches": False,
    "decision_review_changes_future_behavior": False,
    "decision_review_self_approves": False,
    "lesson_candidates_write_memory": False,
    "lesson_candidates_alter_identity": False,
    "lesson_candidates_alter_personality": False,
    "memory_governance_stores_memory": False,
    "memory_governance_expands_authority": False,
    "history_memory_audit_writes_memory": False,
    "history_memory_audit_applies_patches": False,
    "history_memory_audit_reuses_approval": False,
    "history_memory_audit_executes_rollback": False,
    "history_memory_audit_invokes_models": False,
    "history_memory_audit_publishes_release": False,
    "history_memory_audit_creates_release_candidate": False,
    "history_memory_audit_continues_automatically": False,
    "memory_candidates_review_only": True,
    "operator_approval_required_before_memory_storage": True,
    "approval_reuse_forbidden": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

TRIAL_LEDGER_FIELDS = [
    "trial_id",
    "candidate_id",
    "approval_id",
    "transaction_id",
    "application_harness_id",
    "closure_audit_id",
    "changed_files",
    "expected_results",
    "actual_results",
    "operator_decision",
    "approval_burnout_status",
    "rollback_readiness",
]

DECISION_STATES = [
    "approved",
    "blocked",
    "revised",
    "deferred",
    "returned_to_sandbox",
    "rolled_back",
    "reapproved",
    "burned_after_use",
]

MEMORY_CANDIDATE_CHECKS = [
    "factual",
    "scoped",
    "non_sensitive",
    "non_autonomous",
    "operator_approved_before_storage",
    "does_not_mutate_identity",
    "does_not_mutate_personality",
    "does_not_expand_authority",
]


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
        "memory write request": ["write memory", "store memory", "remember automatically", "commit memory"],
        "identity/personality mutation request": ["rewrite identity", "alter personality", "personality engine", "identity prompt"],
        "patch application request": ["apply patch", "edit files", "write source", "make the change"],
        "approval reuse request": ["reuse approval", "same approval", "approval carries forward"],
        "rollback execution request": ["execute rollback", "run rollback", "restore files"],
        "autonomy expansion request": ["continue automatically", "self approve", "auto select", "schedule hidden"],
        "model/release request": ["invoke local model", "publish release", "create release candidate"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    return "blocked" if flags or blockers else "reviewable"


def build_live_patch_trial_history_ledger_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    trial = evidence.get("trial", {}) if isinstance(evidence.get("trial", {}), dict) else {}
    defaults = {
        "trial_id": "trial-v390-review",
        "candidate_id": "candidate-v390-review",
        "approval_id": "approval-v390-review-burned",
        "transaction_id": "transaction-v390-review",
        "application_harness_id": "harness-v390-review",
        "closure_audit_id": "closure-v385-review",
        "changed_files": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "tools/smoke_check.py"],
        "expected_results": "registry-driven tiny patch path remains scoped and verified",
        "actual_results": "operator-reported result is reviewable",
        "operator_decision": "approved",
        "approval_burnout_status": "burned_after_use",
        "rollback_readiness": "reviewed",
    }
    defaults.update(trial)
    missing = [field for field in TRIAL_LEDGER_FIELDS if defaults.get(field) in (None, "", [])]
    blockers = [f"missing:{field}" for field in missing]
    if defaults.get("approval_burnout_status") != "burned_after_use":
        blockers.append("approval burnout not recorded")
    return {
        "version": LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION,
        "state": "live_patch_trial_history_ledger_review_only",
        "ledger_fields": TRIAL_LEDGER_FIELDS,
        "trial_record": defaults,
        "missing_fields": missing,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "treats_history_as_permission": False,
        "applies_patches": False,
        "review_only": True,
    }


def build_operator_decision_pattern_review_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    decisions = _listify(evidence.get("decisions", ["approved", "burned_after_use", "deferred"]))
    unknown = [item for item in decisions if item not in DECISION_STATES]
    blockers = [f"unknown_decision:{item}" for item in unknown]
    patterns = {
        state: decisions.count(state) for state in DECISION_STATES if decisions.count(state)
    }
    return {
        "version": LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION,
        "state": "operator_live_patch_decision_patterns_review_only",
        "decision_states": DECISION_STATES,
        "observed_decisions": decisions,
        "patterns": patterns,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "changes_future_behavior": False,
        "self_approves": False,
        "review_only": True,
    }


def build_supervised_lesson_candidate_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    candidates = _listify(evidence.get("lesson_candidates", [
        "Docs-only patch trials are lower risk when scoped and verified.",
        "Approval burnout prevents successful trials from becoming reusable permission.",
        "Registry-driven scope checks reduce stale gate and route parity risk.",
    ]))
    blockers: list[str] = []
    for lesson in candidates:
        lowered = lesson.lower()
        if any(token in lowered for token in ["always approve", "auto approve", "no approval needed", "store automatically"]):
            blockers.append(f"unsafe_lesson:{lesson}")
    return {
        "version": LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION,
        "state": "live_patch_supervised_lesson_candidates_review_only",
        "lesson_candidates": candidates,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "writes_memory": False,
        "alters_identity": False,
        "alters_personality": False,
        "updates_behavior": False,
        "review_only": True,
    }


def build_memory_candidate_governance_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    flags = _risk_flags(request_text)
    checks = {
        key: bool(evidence.get(key, True)) for key in MEMORY_CANDIDATE_CHECKS
    }
    blockers = [key for key, value in checks.items() if not value]
    if evidence.get("store_now") is True:
        blockers.append("memory storage attempted")
    return {
        "version": LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION,
        "state": "live_patch_memory_candidate_governance_review_only",
        "checks": checks,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(flags, blockers),
        "stores_memory": False,
        "expands_authority": False,
        "operator_approval_required_before_storage": True,
        "review_only": True,
    }


def build_live_patch_history_memory_candidate_audit_summary(root: Path | None = None, dashboard_text: str | None = None, request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    docs = dashboard_text or ""
    default_evidence = dict(evidence or {})
    ledger = build_live_patch_trial_history_ledger_summary(request_text or "review only", default_evidence)
    decision_review = build_operator_decision_pattern_review_summary(request_text or "review only", default_evidence)
    lessons = build_supervised_lesson_candidate_summary(request_text or "review only", default_evidence)
    memory_governance = build_memory_candidate_governance_summary(request_text or "review only", default_evidence)
    doc_checks = {
        "readme_updated": "v395.0 - Live Patch Trial History Ledger and Operator Decision Memory Candidate Prep v1" in docs,
        "release_history_updated": "v395.0 - Live Patch Trial History Ledger and Operator Decision Memory Candidate Prep v1" in docs,
        "version_markers_current": 'LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION = "500.0"' in docs,
        "dashboard_data_tip_present": "data-tip" in docs,
        "command_deck_present": "command-deck" in docs,
        "operator_console_present": "operator-console" in docs,
        "runtime_private_dirs_documented": "data/autonomy/live_patch_history_memory_candidate_audit/" in docs,
    }
    blockers = [key for key, value in doc_checks.items() if not value]
    packets = [ledger, decision_review, lessons, memory_governance]
    ok = all(packet.get("status") == "reviewable" for packet in packets) and not blockers
    return {
        "version": LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION,
        "state": "live_patch_history_memory_candidate_audit",
        "history_ledger": ledger,
        "decision_pattern_review": decision_review,
        "lesson_candidates": lessons,
        "memory_candidate_governance": memory_governance,
        "doc_checks": doc_checks,
        "blockers": blockers,
        "boundaries": dict(LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_BOUNDARIES),
        "boundaries_ok": all(value is False for key, value in LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_BOUNDARIES.items() if key not in {"memory_candidates_review_only", "operator_approval_required_before_memory_storage", "approval_reuse_forbidden", "dashboard_data_tip_required", "native_title_tooltips_forbidden"}) and all(LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_BOUNDARIES[key] is True for key in ["memory_candidates_review_only", "operator_approval_required_before_memory_storage", "approval_reuse_forbidden", "dashboard_data_tip_required", "native_title_tooltips_forbidden"]),
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "safe_next_action": "Operator may review v395 history and memory-candidate packets. No memory write, identity/personality mutation, approval reuse, patch application, rollback execution, model invocation, release creation, or automatic continuation is authorized.",
    }


def render_live_patch_history_memory_candidate_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ["version", "state", "status", "ok", "review_only", "safe_next_action"]:
        if key in summary:
            lines.append(f"- {key}: {summary[key]}")
    if summary.get("blockers"):
        lines.append("- blockers: " + ", ".join(map(str, summary.get("blockers", []))))
    if summary.get("risk_flags"):
        lines.append("- risk_flags: " + ", ".join(map(str, summary.get("risk_flags", []))))
    return lines or ["- no summary details available"]
