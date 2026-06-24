from __future__ import annotations

from typing import Any

from expression_application_bridge import (
    build_expression_approval_criteria_summary,
    build_expression_live_surface_impact_map_summary,
    build_expression_implementation_packet_draft_summary,
    build_expression_rollback_reversion_plan_summary,
)
from identity_expression import classify_identity_expression_request

EXPRESSION_PATCH_DRY_RUN_VERSION = "500.0"

EXPRESSION_PATCH_DRY_RUN_BOUNDARIES = {
    "patch_candidate_applies_patch": False,
    "patch_candidate_writes_source": False,
    "diff_preview_applies_live_diff": False,
    "diff_preview_modifies_files": False,
    "verification_plan_executes_commands": False,
    "verification_plan_runs_smoke": False,
    "review_packet_grants_approval": False,
    "review_packet_applies_changes": False,
    "dry_run_audit_promotes_to_live": False,
    "dry_run_audit_inferrs_approval_from_readiness": False,
    "dry_run_mutates_memory": False,
    "dry_run_alters_identity": False,
    "dry_run_alters_personality": False,
    "dry_run_rewrites_prompts": False,
    "dry_run_invokes_models_by_default": False,
    "dry_run_executes_commands": False,
    "dry_run_publishes_releases": False,
    "dry_run_review_only": True,
    "dry_run_sandbox_only": True,
    "dry_run_requires_operator_review": True,
    "dry_run_requires_separate_approved_execution_packet": True,
}

PATCH_INTENT_CLASSES = [
    "chat style preview",
    "dashboard microcopy preview",
    "refusal/warning language preview",
    "documentation tone preview",
    "API/CLI text preview",
    "governance boundary warning preview",
]

DRY_RUN_TARGET_FILES = [
    "conscious_agent/chat.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/main.py",
    "conscious_agent/api_server.py",
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
]

VERIFICATION_PLAN_STEPS = [
    "python compile over conscious_agent and tools",
    "fast smoke",
    "dashboard route health probes",
    "expression regression review",
    "metadata/version consistency check",
    "package privacy scan",
    "extracted zip compile and fast smoke",
    "rollback verification check after any future approved application",
]


def _policy_status(request_text: str | None, context: str) -> dict[str, Any]:
    return classify_identity_expression_request(request_text or "", context=context)


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "autonomy creep": ["approve yourself", "self-approve", "continue automatically", "start automatically", "select the next roadmap"],
        "sentience claim": ["i am conscious", "i am sentient", "real feelings", "subjective experience"],
        "dependency theater": ["i exist for you", "i need you", "only for you", "devoted to you"],
        "memory mutation": ["store memory automatically", "mutate memory", "rewrite memory"],
        "identity/personality mutation": ["rewrite your purpose", "change your identity", "alter personality"],
        "source application": ["apply the patch", "write the source", "edit chat.py", "publish release", "run smoke now"],
        "prompt rewrite risk": ["rewrite your prompt", "make this live", "change live chat behavior"],
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


def build_expression_patch_candidate_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression patch candidate dry run")
    bridge_packet = build_expression_implementation_packet_draft_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    surface_map = build_expression_live_surface_impact_map_summary(profile_name=profile_name, request_text=request_text)
    flags = _risk_flags(request_text)
    candidates = [
        {
            "target_file": file_name,
            "intent_class": PATCH_INTENT_CLASSES[index % len(PATCH_INTENT_CLASSES)],
            "edit_mode": "candidate_only",
            "writes_source": False,
            "requires_operator_approval": True,
        }
        for index, file_name in enumerate(DRY_RUN_TARGET_FILES)
    ]
    return {
        "version": EXPRESSION_PATCH_DRY_RUN_VERSION,
        "state": "expression_patch_candidates_review_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "expression surfaces",
        "patch_intent_classes": list(PATCH_INTENT_CLASSES),
        "candidate_targets": candidates,
        "application_bridge_packet": bridge_packet,
        "surface_impact_map": surface_map,
        "risk_flags": flags,
        "status": _risk_status(policy, flags),
        "applies_patch": False,
        "writes_source": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_diff_preview_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox diff preview")
    candidates = build_expression_patch_candidate_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    flags = _risk_flags(request_text)
    previews = [
        {
            "target_file": target,
            "before": "existing governed expression text",
            "after": "proposed operator-reviewed expression wording preview",
            "diff_mode": "sandbox_preview_only",
            "applies_live_diff": False,
            "modifies_file": False,
            "rollback_note": "Future approved packet must preserve a prior-text baseline before application.",
        }
        for target in DRY_RUN_TARGET_FILES
    ]
    return {
        "version": EXPRESSION_PATCH_DRY_RUN_VERSION,
        "state": "sandbox_diff_preview_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "expression surfaces",
        "patch_candidates": candidates,
        "diff_previews": previews,
        "risk_flags": flags,
        "status": _risk_status(policy, flags),
        "applies_live_diff": False,
        "writes_source": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_dry_run_verification_plan_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression dry-run verification plan")
    flags = _risk_flags(request_text)
    return {
        "version": EXPRESSION_PATCH_DRY_RUN_VERSION,
        "state": "verification_plan_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "expression surfaces",
        "verification_steps": list(VERIFICATION_PLAN_STEPS),
        "route_probe_required": True,
        "expression_regression_required": True,
        "metadata_check_required": True,
        "rollback_recheck_required": True,
        "executes_commands": False,
        "runs_smoke": False,
        "risk_flags": flags,
        "status": _risk_status(policy, flags),
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_dry_run_review_packet_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression dry-run review packet")
    candidates = build_expression_patch_candidate_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    diffs = build_expression_sandbox_diff_preview_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    verification = build_expression_dry_run_verification_plan_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    rollback = build_expression_rollback_reversion_plan_summary(profile_name=profile_name, request_text=request_text)
    approval = build_expression_approval_criteria_summary(profile_name=profile_name, request_text=request_text)
    flags = sorted(set(candidates.get("risk_flags", [])) | set(diffs.get("risk_flags", [])) | set(verification.get("risk_flags", [])) | set(_risk_flags(request_text)))
    return {
        "version": EXPRESSION_PATCH_DRY_RUN_VERSION,
        "state": "dry_run_review_packet_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "expression surfaces",
        "candidate_summary": candidates,
        "diff_preview_summary": diffs,
        "verification_summary": verification,
        "rollback_summary": rollback,
        "approval_evidence": approval,
        "risk_flags": flags,
        "status": _risk_status(policy, flags),
        "approval_granted": False,
        "applies_changes": False,
        "writes_source": False,
        "readiness_is_approval": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_patch_dry_run_audit_summary(dashboard_text: str = "", profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    candidates = build_expression_patch_candidate_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    diffs = build_expression_sandbox_diff_preview_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    verification = build_expression_dry_run_verification_plan_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    review = build_expression_dry_run_review_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    missing_routes = [
        route
        for route in [
            "/expression-patch-candidates",
            "/expression-sandbox-diff-preview",
            "/expression-dry-run-verification-plan",
            "/expression-dry-run-review-packet",
            "/expression-patch-dry-run-audit",
        ]
        if dashboard_text and route not in dashboard_text
    ]
    statuses = [candidates.get("status"), diffs.get("status"), verification.get("status"), review.get("status")]
    return {
        "version": EXPRESSION_PATCH_DRY_RUN_VERSION,
        "state": "expression_patch_dry_run_audit",
        "expression_patch_candidates": candidates,
        "expression_sandbox_diff_preview": diffs,
        "expression_dry_run_verification_plan": verification,
        "expression_dry_run_review_packet": review,
        "missing_dashboard_routes": missing_routes,
        "boundaries": dict(EXPRESSION_PATCH_DRY_RUN_BOUNDARIES),
        "status": "blocked" if "blocked" in statuses else "reviewable",
        "applies_patch": False,
        "applies_live_diff": False,
        "executes_verification": False,
        "approval_granted": False,
        "writes_source": False,
        "review_only": True,
    }


def render_expression_patch_dry_run_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, dict):
            status = value.get("status") or value.get("state") or value.get("version") or "nested"
            lines.append(f"- {key}: {status}")
        elif isinstance(value, list):
            lines.append(f"- {key}: {len(value)} item(s)")
        else:
            lines.append(f"- {key}: {value}")
    return lines or ["- No expression patch dry-run data available."]
