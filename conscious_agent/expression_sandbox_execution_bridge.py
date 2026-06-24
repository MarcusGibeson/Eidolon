from __future__ import annotations

from typing import Any

from expression_sandbox_trial_harness import (
    build_expression_sandbox_trial_packet_summary,
    build_expression_sandbox_workspace_plan_summary,
    build_expression_sandbox_verification_matrix_summary,
)
from expression_patch_dry_run import build_expression_sandbox_diff_preview_summary
from identity_expression import classify_identity_expression_request

EXPRESSION_SANDBOX_EXECUTION_BRIDGE_VERSION = "500.0"

EXPRESSION_SANDBOX_EXECUTION_BRIDGE_BOUNDARIES = {
    "approval_gate_grants_approval": False,
    "approval_gate_infers_approval_from_readiness": False,
    "approval_gate_reuses_expired_consent": False,
    "workspace_execution_packet_creates_workspace": False,
    "workspace_execution_packet_copies_files": False,
    "workspace_execution_packet_writes_files": False,
    "patch_bundle_applies_patch": False,
    "patch_bundle_writes_source": False,
    "verification_command_packet_executes_commands": False,
    "verification_command_packet_runs_smoke": False,
    "execution_bridge_executes_sandbox": False,
    "execution_bridge_mutates_live_source": False,
    "execution_bridge_mutates_memory": False,
    "execution_bridge_alters_identity": False,
    "execution_bridge_alters_personality": False,
    "execution_bridge_rewrites_prompts": False,
    "execution_bridge_publishes_releases": False,
    "execution_bridge_continues_automatically": False,
    "execution_bridge_review_only": True,
    "execution_bridge_packet_only": True,
    "execution_bridge_requires_explicit_operator_approval": True,
    "execution_bridge_requires_fresh_scope_bound_approval": True,
    "execution_bridge_forbids_live_promotion": True,
}

APPROVAL_SCOPE_CLASSES = [
    "approve-to-review",
    "approve-to-stage",
    "approve-to-run-sandbox",
    "approve-to-promote-review",
]

WORKSPACE_EXECUTION_STEPS = [
    "select source-only release zip",
    "choose operator-approved sandbox path",
    "extract source files into sandbox copy only",
    "verify excluded runtime/private paths are absent",
    "record sandbox manifest for later review",
    "stop before patch application until separate approval is present",
]

PATCH_BUNDLE_TARGETS = [
    "chat style candidate",
    "dashboard microcopy candidate",
    "README/docs wording candidate",
    "API/CLI text candidate",
    "warning/refusal wording candidate",
    "metadata/version wording candidate",
]

VERIFICATION_COMMAND_DRAFTS = [
    {"command": "python -m py_compile conscious_agent/*.py tools/smoke_check.py", "purpose": "compile check", "manual_run_only": True},
    {"command": "python tools/smoke_check.py --tier fast", "purpose": "fast smoke", "manual_run_only": True},
    {"command": "python tools/smoke_check.py --single operator-governed-expression-sandbox-trial-execution-packet-bridge-v1", "purpose": "targeted v335 bridge smoke", "manual_run_only": True},
    {"command": "python conscious_agent/main.py --operator-governed-expression-sandbox-trial-execution-packet-bridge-v1 --readiness-json", "purpose": "dynamic CLI parity", "manual_run_only": True},
    {"command": "GET /api/expression-sandbox-execution-packet-bridge-audit/layer", "purpose": "dynamic API parity", "manual_run_only": True},
    {"command": "dashboard HTTP probe for v335 routes", "purpose": "dashboard route health", "manual_run_only": True},
    {"command": "package privacy scan", "purpose": "source-only privacy validation", "manual_run_only": True},
]


def _policy_status(request_text: str | None, context: str) -> dict[str, Any]:
    return classify_identity_expression_request(request_text or "", context=context)


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "approval inference": ["readiness means approved", "treat ready as approved", "safe enough so run"],
        "expired consent reuse": ["reuse old approval", "last approval still counts", "use prior consent", "stale approval"],
        "sandbox execution request": ["run sandbox now", "execute sandbox now", "create workspace now", "copy files now"],
        "live source mutation": ["apply to live", "write live source", "edit chat.py now", "make it live"],
        "patch application request": ["apply patch now", "apply the patch", "write the patch"],
        "command execution request": ["run smoke now", "execute commands", "run tests automatically", "run compile now"],
        "promotion inference": ["promote automatically", "sandbox passed so apply", "success means promote"],
        "approval bypass": ["approve yourself", "self-approve", "skip approval", "no operator needed"],
        "memory/identity/personality mutation": ["mutate memory", "rewrite purpose", "change your identity", "alter personality"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(policy: dict[str, Any], flags: list[str]) -> str:
    if policy.get("status") == "blocked" or flags:
        return "blocked"
    if policy.get("status") == "warning":
        return "warning"
    return "reviewable"


def build_expression_sandbox_execution_approval_gate_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox execution approval gate")
    flags = _risk_flags(request_text)
    return {
        "version": EXPRESSION_SANDBOX_EXECUTION_BRIDGE_VERSION,
        "state": "sandbox_execution_approval_gate_packet_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "expression sandbox trial surfaces",
        "approval_status": "not_granted",
        "operator_identity_required": True,
        "scope_bound_approval_required": True,
        "approval_expiration_required": True,
        "target_version_required": "335.0",
        "approval_scope_classes": list(APPROVAL_SCOPE_CLASSES),
        "trial_packet_evidence": build_expression_sandbox_trial_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface),
        "operator_decision_options": ["defer", "revise", "reject", "approve-to-run-sandbox-later"],
        "risk_flags": flags,
        "status": _status(policy, flags),
        "grants_approval": False,
        "infers_approval_from_readiness": False,
        "reuses_expired_consent": False,
        "executes_sandbox": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_workspace_execution_packet_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox workspace execution packet draft")
    flags = _risk_flags(request_text)
    return {
        "version": EXPRESSION_SANDBOX_EXECUTION_BRIDGE_VERSION,
        "state": "workspace_execution_packet_draft_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "source_zip": "operator_supplied_source_only_zip",
        "sandbox_target_path": "operator_selected_sandbox_path",
        "directory_naming_plan": "Eidolon_expression_sandbox_<version>_<packet_id>",
        "execution_steps": list(WORKSPACE_EXECUTION_STEPS),
        "workspace_plan_evidence": build_expression_sandbox_workspace_plan_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface),
        "file_scope_manifest_required": True,
        "private_runtime_exclusion_check_required": True,
        "manual_execution_notes_required": True,
        "risk_flags": flags,
        "status": _status(policy, flags),
        "creates_workspace": False,
        "copies_files": False,
        "writes_files": False,
        "executes_commands": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_patch_bundle_packet_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox patch bundle packet")
    flags = _risk_flags(request_text)
    return {
        "version": EXPRESSION_SANDBOX_EXECUTION_BRIDGE_VERSION,
        "state": "sandbox_patch_bundle_packet_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "candidate_id": "operator_selected_expression_patch_candidate",
        "patch_targets": list(PATCH_BUNDLE_TARGETS),
        "target_manifest_required": True,
        "approved_expression_surfaces_only": True,
        "conflict_detection_required": True,
        "rollback_file_map_required": True,
        "diff_preview_evidence": build_expression_sandbox_diff_preview_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface),
        "trial_packet_evidence": build_expression_sandbox_trial_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface),
        "risk_flags": flags,
        "status": _status(policy, flags),
        "applies_patch": False,
        "writes_source": False,
        "mutates_live_source": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_verification_command_packet_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression sandbox verification command packet draft")
    flags = _risk_flags(request_text)
    return {
        "version": EXPRESSION_SANDBOX_EXECUTION_BRIDGE_VERSION,
        "state": "verification_command_packet_draft_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "command_drafts": [dict(item) for item in VERIFICATION_COMMAND_DRAFTS],
        "verification_matrix_evidence": build_expression_sandbox_verification_matrix_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface),
        "manual_run_boundary": "Commands are listed for operator review only and are not executed by this layer.",
        "risk_flags": flags,
        "status": _status(policy, flags),
        "executes_commands": False,
        "runs_smoke": False,
        "starts_server": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_sandbox_execution_packet_bridge_audit_summary(dashboard_text: str = "", profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    approval = build_expression_sandbox_execution_approval_gate_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    workspace = build_expression_sandbox_workspace_execution_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    patch_bundle = build_expression_sandbox_patch_bundle_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    verification = build_expression_sandbox_verification_command_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    flags = sorted(set(approval.get("risk_flags", [])) | set(workspace.get("risk_flags", [])) | set(patch_bundle.get("risk_flags", [])) | set(verification.get("risk_flags", [])))
    routes = [
        "/expression-sandbox-execution-approval-gate",
        "/expression-sandbox-workspace-execution-packet",
        "/expression-sandbox-patch-bundle-packet",
        "/expression-sandbox-verification-command-packet",
        "/expression-sandbox-execution-packet-bridge-audit",
    ]
    missing = [route for route in routes if dashboard_text and route not in dashboard_text]
    return {
        "version": EXPRESSION_SANDBOX_EXECUTION_BRIDGE_VERSION,
        "state": "sandbox_execution_packet_bridge_audit_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "approval_gate": approval,
        "workspace_execution_packet": workspace,
        "patch_bundle_packet": patch_bundle,
        "verification_command_packet": verification,
        "dashboard_routes": routes,
        "missing_dashboard_tokens": missing,
        "route_health_registration_required": True,
        "smoke_coverage_required": True,
        "api_cli_parity_required": True,
        "package_privacy_required": True,
        "risk_flags": flags,
        "status": "blocked" if flags or missing else "reviewable",
        "grants_approval": False,
        "creates_workspace": False,
        "copies_files": False,
        "applies_patch": False,
        "executes_commands": False,
        "runs_smoke": False,
        "mutates_live_source": False,
        "promotes_to_live": False,
        "review_only": True,
        "boundaries": dict(EXPRESSION_SANDBOX_EXECUTION_BRIDGE_BOUNDARIES),
    }


def render_expression_sandbox_execution_bridge_lines(summary: dict[str, Any]) -> list[str]:
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
