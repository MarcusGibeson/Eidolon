from __future__ import annotations

from typing import Any

from expression_patch_dry_run import (
    build_expression_patch_candidate_summary,
    build_expression_sandbox_diff_preview_summary,
    build_expression_dry_run_verification_plan_summary,
    build_expression_dry_run_review_packet_summary,
)
from identity_expression import classify_identity_expression_request

EXPRESSION_SANDBOX_TRIAL_HARNESS_VERSION = "500.0"

EXPRESSION_SANDBOX_TRIAL_HARNESS_BOUNDARIES = {
    "trial_packet_creates_sandbox": False,
    "trial_packet_executes_sandbox": False,
    "trial_packet_applies_patch": False,
    "workspace_plan_copies_files": False,
    "workspace_plan_writes_files": False,
    "workspace_plan_includes_runtime_private_paths": False,
    "verification_matrix_executes_commands": False,
    "verification_matrix_runs_smoke": False,
    "result_review_promotes_to_live": False,
    "result_review_grants_approval": False,
    "trial_harness_mutates_live_source": False,
    "trial_harness_mutates_memory": False,
    "trial_harness_alters_identity": False,
    "trial_harness_alters_personality": False,
    "trial_harness_rewrites_prompts": False,
    "trial_harness_invokes_models_by_default": False,
    "trial_harness_publishes_releases": False,
    "trial_harness_continues_automatically": False,
    "trial_harness_prep_only": True,
    "trial_harness_review_only": True,
    "trial_harness_requires_operator_approval_before_execution": True,
    "trial_harness_requires_sandbox_isolation": True,
    "trial_harness_requires_separate_promotion_review": True,
}

TRIAL_TARGET_SCOPE_CLASSES = [
    "chat surface candidate",
    "dashboard copy candidate",
    "documentation candidate",
    "API/CLI text candidate",
    "warning/refusal text candidate",
    "metadata candidate",
]

SANDBOX_EXCLUDED_RUNTIME_PATHS = [
    "data/autonomy/",
    "data/self_maintenance/",
    "data/tasks.json",
    "__pycache__/",
    ".pytest_cache/",
    "data/workspaces/runtime/",
]

SANDBOX_VERIFICATION_MATRIX = [
    "python compile over sandbox copy",
    "fast smoke in sandbox copy",
    "dashboard route health probes in sandbox copy",
    "dynamic API/CLI parity checks in sandbox copy",
    "expression regression checks for autonomy, sentience, dependency theater, overconfidence, purpose drift, and self-approval language",
    "package privacy scan over sandbox-generated source-only zip",
    "extracted zip compile and fast smoke",
    "sandbox rollback/reversion check",
]


def _policy_status(request_text: str | None, context: str) -> dict[str, Any]:
    return classify_identity_expression_request(request_text or "", context=context)


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "sandbox execution request": ["run the sandbox", "execute the sandbox", "start sandbox now", "create sandbox now"],
        "live source mutation": ["apply to live", "write live source", "edit chat.py now", "make this live"],
        "promotion inference": ["promote automatically", "sandbox passed so apply", "treat sandbox success as approval"],
        "approval bypass": ["approve yourself", "self-approve", "no operator needed", "skip approval"],
        "private runtime copy risk": ["copy data/autonomy", "copy data/self_maintenance", "copy tasks.json"],
        "command execution request": ["run smoke now", "execute commands", "run tests automatically"],
        "memory/identity/personality mutation": ["mutate memory", "rewrite purpose", "change your identity", "alter personality"],
    }
    flags: list[str] = []
    for label, needles in catalog.items():
        if any(needle in lowered for needle in needles):
            flags.append(label)
    return flags


def _risk_status(policy: dict[str, Any], flags: list[str]) -> str:
    if policy.get("status") == "blocked" or flags:
        return "blocked"
    if policy.get("status") == "warning":
        return "warning"
    return "reviewable"


def build_expression_sandbox_trial_packet_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox trial packet prep")
    dry_run_packet = build_expression_dry_run_review_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    diff_preview = build_expression_sandbox_diff_preview_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    flags = _risk_flags(request_text)
    return {
        "version": EXPRESSION_SANDBOX_TRIAL_HARNESS_VERSION,
        "state": "sandbox_trial_packet_prep_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "expression surfaces",
        "source_zip_required": True,
        "sandbox_path": "operator_selected_sandbox_copy_path",
        "operator_approval_status": "not_granted",
        "dry_run_review_packet": dry_run_packet,
        "diff_preview_evidence": diff_preview,
        "target_scope_classes": list(TRIAL_TARGET_SCOPE_CLASSES),
        "risk_flags": flags,
        "status": _risk_status(policy, flags),
        "creates_sandbox": False,
        "executes_sandbox": False,
        "applies_patch": False,
        "writes_source": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_workspace_plan_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox workspace plan")
    candidate_packet = build_expression_patch_candidate_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    flags = _risk_flags(request_text)
    protected = [
        {"path": path, "excluded": True, "reason": "runtime/private state must not be copied into source-only expression sandbox planning"}
        for path in SANDBOX_EXCLUDED_RUNTIME_PATHS
    ]
    return {
        "version": EXPRESSION_SANDBOX_TRIAL_HARNESS_VERSION,
        "state": "sandbox_workspace_plan_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "source_only_copy_plan": True,
        "excluded_runtime_paths": protected,
        "target_scope_classes": list(TRIAL_TARGET_SCOPE_CLASSES),
        "candidate_packet": candidate_packet,
        "metadata_scope_guard": "metadata changes require explicit planned target and later approved execution packet",
        "chat_prompt_scope_guard": "chat or prompt targets are high-risk and operator-gated",
        "risk_flags": flags,
        "status": _risk_status(policy, flags),
        "copies_files": False,
        "writes_files": False,
        "includes_private_runtime_paths": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_verification_matrix_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox verification matrix")
    verification_plan = build_expression_dry_run_verification_plan_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    flags = _risk_flags(request_text)
    return {
        "version": EXPRESSION_SANDBOX_TRIAL_HARNESS_VERSION,
        "state": "sandbox_trial_verification_matrix_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "verification_matrix": list(SANDBOX_VERIFICATION_MATRIX),
        "dry_run_verification_plan": verification_plan,
        "expression_regression_required": True,
        "dashboard_route_trial_checks_required": True,
        "chat_behavior_trial_checks_required_if_chat_touched": True,
        "prompt_safety_checks_required": True,
        "rollback_trial_checks_required": True,
        "trial_result_evidence_schema": ["changed_files", "check_results", "failures", "risk_flags", "rollback_notes", "operator_recommendation"],
        "risk_flags": flags,
        "status": _risk_status(policy, flags),
        "executes_commands": False,
        "runs_smoke": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_result_review_prep_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox result review prep")
    trial_packet = build_expression_sandbox_trial_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    workspace_plan = build_expression_sandbox_workspace_plan_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    verification_matrix = build_expression_sandbox_verification_matrix_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    flags = sorted(set(_risk_flags(request_text)) | set(trial_packet.get("risk_flags", [])) | set(workspace_plan.get("risk_flags", [])) | set(verification_matrix.get("risk_flags", [])))
    return {
        "version": EXPRESSION_SANDBOX_TRIAL_HARNESS_VERSION,
        "state": "sandbox_trial_result_review_prep_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "trial_packet": trial_packet,
        "workspace_plan": workspace_plan,
        "verification_matrix": verification_matrix,
        "failure_classes": ["syntax", "route", "governance", "regression", "privacy", "metadata", "rollback-risk"],
        "operator_decision_options": ["defer", "revise", "reject", "promote-to-review"],
        "promotion_readiness_boundary": "sandbox success may support later review but cannot authorize live promotion",
        "risk_flags": flags,
        "status": _risk_status(policy, flags),
        "promotes_to_live": False,
        "approval_granted": False,
        "infers_promotion_from_success": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_trial_harness_audit_summary(dashboard_text: str = "", profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    trial_packet = build_expression_sandbox_trial_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    workspace_plan = build_expression_sandbox_workspace_plan_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    verification_matrix = build_expression_sandbox_verification_matrix_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    result_review = build_expression_sandbox_result_review_prep_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    routes = [
        "/expression-sandbox-trial-packet",
        "/expression-sandbox-workspace-plan",
        "/expression-sandbox-verification-matrix",
        "/expression-sandbox-result-review-prep",
        "/expression-sandbox-trial-harness-audit",
    ]
    missing_routes = [route for route in routes if dashboard_text and route not in dashboard_text]
    statuses = [trial_packet.get("status"), workspace_plan.get("status"), verification_matrix.get("status"), result_review.get("status")]
    return {
        "version": EXPRESSION_SANDBOX_TRIAL_HARNESS_VERSION,
        "state": "expression_sandbox_trial_harness_audit",
        "expression_sandbox_trial_packet": trial_packet,
        "expression_sandbox_workspace_plan": workspace_plan,
        "expression_sandbox_verification_matrix": verification_matrix,
        "expression_sandbox_result_review_prep": result_review,
        "missing_dashboard_routes": missing_routes,
        "boundaries": dict(EXPRESSION_SANDBOX_TRIAL_HARNESS_BOUNDARIES),
        "status": "blocked" if "blocked" in statuses else "reviewable",
        "creates_sandbox": False,
        "copies_files": False,
        "writes_source": False,
        "executes_commands": False,
        "promotes_to_live": False,
        "approval_granted": False,
        "review_only": True,
    }


def render_expression_sandbox_trial_harness_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, dict):
            status = value.get("status") or value.get("state") or value.get("version") or "nested"
            lines.append(f"- {key}: {status}")
        elif isinstance(value, list):
            lines.append(f"- {key}: {len(value)} item(s)")
        else:
            lines.append(f"- {key}: {value}")
    return lines or ["- No expression sandbox trial harness data available."]
