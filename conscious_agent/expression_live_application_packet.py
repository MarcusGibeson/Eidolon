from __future__ import annotations

from typing import Any

from expression_promotion_packet import (
    build_expression_promotion_evidence_binder_summary,
    build_expression_live_promotion_scope_risk_summary,
    build_expression_promotion_verification_rollback_summary,
    build_expression_promotion_decision_packet_summary,
)
from expression_patch_dry_run import build_expression_sandbox_diff_preview_summary
from expression_application_bridge import build_expression_implementation_packet_draft_summary
from identity_expression import classify_identity_expression_request

EXPRESSION_LIVE_APPLICATION_PACKET_VERSION = "1032.0"
EXPRESSION_LIVE_APPLICATION_PACKET_BOUNDARIES = {
    "eligibility_gate_authorizes_live_writes": False,
    "eligibility_gate_treats_eligibility_as_approval": False,
    "eligibility_gate_reuses_stale_or_vague_consent": False,
    "source_change_manifest_writes_files": False,
    "source_change_manifest_mutates_source": False,
    "source_change_manifest_includes_runtime_private_paths": False,
    "patch_instruction_packet_applies_patch": False,
    "patch_instruction_packet_rewrites_prompts": False,
    "patch_instruction_packet_mutates_identity": False,
    "patch_instruction_packet_mutates_personality": False,
    "patch_instruction_packet_mutates_memory": False,
    "verification_rollback_packet_executes_commands": False,
    "verification_rollback_packet_runs_rollback": False,
    "verification_rollback_packet_publishes_release": False,
    "application_packet_audit_applies_live_source": False,
    "application_packet_audit_executes_hidden_work": False,
    "application_packet_audit_infers_approval_from_eligibility": False,
    "application_packet_review_only": True,
    "application_packet_draft_only": True,
    "fresh_scope_bound_operator_approval_required_for_later_live_execution": True,
}

LIVE_APPLICATION_ELIGIBILITY_FIELDS = [
    "promotion_packet_id",
    "target_version",
    "operator_decision_state",
    "approval_scope",
    "expiration",
    "risk_status",
    "allowed_next_action",
]

LIVE_SOURCE_SURFACES = [
    "chat.py conversational expression surface",
    "dashboard command-deck microcopy",
    "API/CLI user-facing text",
    "README and release history wording",
    "safety/refusal warning language",
    "version markers and project metadata",
]

PROTECTED_LIVE_APPLICATION_PATHS = [
    "data/autonomy",
    "data/self_maintenance",
    "data/tasks.json",
    "memory stores",
    "identity source of truth",
    "personality source of truth",
    "release outputs",
    "generated artifacts",
]

LIVE_APPLICATION_VERIFICATION_REQUIREMENTS = [
    "pre-application source state check",
    "version marker and metadata consistency check",
    "python compile check",
    "fast smoke check",
    "targeted expression smoke checks",
    "dashboard route HTTP probes",
    "dynamic API/CLI parity checks",
    "expression regression review",
    "package privacy scan",
    "source-only package build",
    "extracted zip compile and smoke",
    "rollback verification plan",
    "full install smoke accountability note",
]

APPROVAL_SCOPE_CLASSES = [
    "approve-to-review",
    "approve-to-draft-live-application-packet",
    "approve-to-apply-live-source",
    "approve-to-package-release",
]


def _policy_status(request_text: str | None, context: str) -> dict[str, Any]:
    return classify_identity_expression_request(request_text or "", context=context)


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "eligibility as approval": ["eligible means approved", "eligibility is approval", "readiness is approval", "draft means approved"],
        "live source write request": ["apply live", "write live source", "edit live source", "change production", "promote release"],
        "prompt rewrite request": ["rewrite prompt now", "edit chat.py now", "change live chat", "rewrite prompts automatically"],
        "memory identity personality mutation": ["mutate memory", "rewrite identity", "change your identity", "alter personality", "rewrite purpose"],
        "command execution request": ["run smoke now", "execute commands", "run rollback", "perform rollback", "build package now"],
        "approval bypass": ["approve yourself", "self-approve", "skip approval", "no operator needed", "reuse old approval"],
        "hidden continuation": ["continue automatically", "start next patch", "schedule hidden work", "daily loop"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(policy: dict[str, Any], flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    if policy.get("status") == "blocked" or flags or blockers:
        return "blocked"
    if policy.get("status") == "warning":
        return "warning"
    return "reviewable"


def build_expression_live_application_eligibility_gate_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    policy = _policy_status(request_text, "expression live application eligibility gate")
    flags = _risk_flags(request_text)
    missing = [field for field in LIVE_APPLICATION_ELIGIBILITY_FIELDS if field not in evidence]
    approval_scope = str(evidence.get("approval_scope") or "approve-to-review")
    blockers: list[str] = []
    if approval_scope not in {"approve-to-draft-live-application-packet", "approve-to-review"}:
        blockers.append("approval scope does not match draft-only live application packet preparation")
    if evidence.get("expiration") in {None, "", "expired"}:
        blockers.append("fresh expiration-bound approval evidence is missing or expired")
    if str(evidence.get("operator_decision_state") or "").lower() not in {"approved-to-draft", "review", "defer", "revise"}:
        blockers.append("operator decision state is not a fresh scoped draft decision")
    return {
        "version": EXPRESSION_LIVE_APPLICATION_PACKET_VERSION,
        "state": "live_application_packet_eligibility_gate_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "future live expression application packet surfaces",
        "required_eligibility_fields": list(LIVE_APPLICATION_ELIGIBILITY_FIELDS),
        "submitted_evidence_fields": sorted(evidence.keys()),
        "missing_eligibility_fields": missing,
        "approval_scope_classes": list(APPROVAL_SCOPE_CLASSES),
        "allowed_next_action": "draft-live-application-packet-only-after-explicit-fresh-operator-scope",
        "forbidden_actions": ["apply-live-source", "publish-release", "mutate-memory", "rewrite-identity", "alter-personality", "self-approve", "continue-automatically"],
        "promotion_packet_bound": build_expression_promotion_decision_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence.get("promotion_packet") if isinstance(evidence.get("promotion_packet"), dict) else {}),
        "expired_or_out_of_scope_findings": blockers,
        "risk_flags": flags,
        "status": _status(policy, flags, blockers),
        "authorizes_live_writes": False,
        "treats_eligibility_as_approval": False,
        "reuses_stale_or_vague_consent": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_live_source_change_manifest_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression live source change manifest")
    flags = _risk_flags(request_text)
    text = (request_text or "").lower()
    protected_mentions = [path for path in PROTECTED_LIVE_APPLICATION_PATHS if path.lower() in text]
    high_risk = []
    if "chat.py" in text or "prompt" in text:
        high_risk.append("chat/prompt surface is high-risk and remains explicitly operator-gated")
    if any(token in text for token in ["memory", "identity", "personality", "purpose"]):
        high_risk.append("identity/personality/memory/purpose surface requires block unless separately approved")
    return {
        "version": EXPRESSION_LIVE_APPLICATION_PACKET_VERSION,
        "state": "live_source_change_manifest_draft_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "live expression application target surfaces",
        "candidate_live_surfaces": list(LIVE_SOURCE_SURFACES),
        "protected_path_guard": list(PROTECTED_LIVE_APPLICATION_PATHS),
        "protected_path_mentions": protected_mentions,
        "chat_surface_manifest": "instruction-only; no edit to chat.py",
        "dashboard_surface_manifest": "instruction-only; command-deck/data-tip/no_native_title_tooltip preserved",
        "api_cli_surface_manifest": "instruction-only; dynamic parity required",
        "documentation_surface_manifest": "README and release history must update if later applied",
        "metadata_surface_manifest": "version markers and project metadata must update only inside later approved application",
        "risk_findings": high_risk,
        "risk_flags": flags,
        "status": _status(policy, flags, high_risk),
        "writes_files": False,
        "mutates_source": False,
        "includes_runtime_private_paths": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_live_patch_instruction_packet_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression live patch instruction packet")
    flags = _risk_flags(request_text)
    manifest = build_expression_live_source_change_manifest_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    diff_preview = build_expression_sandbox_diff_preview_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    implementation_draft = build_expression_implementation_packet_draft_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    blockers = list(manifest.get("risk_findings", []))
    return {
        "version": EXPRESSION_LIVE_APPLICATION_PACKET_VERSION,
        "state": "live_diff_and_patch_instruction_packet_draft_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "live expression application instruction targets",
        "manifest_bound": manifest,
        "dry_run_diff_bound": diff_preview,
        "implementation_packet_bound": implementation_draft,
        "instruction_classes": ["prompt/chat instruction draft", "dashboard/API/CLI instruction draft", "documentation instruction draft", "metadata instruction draft"],
        "patch_conflict_and_scope_review": ["untested surfaces require revision", "excessive personality changes require reduction", "risky prompt wording requires block or operator clarification"],
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(policy, flags, blockers),
        "applies_patch": False,
        "rewrites_prompts": False,
        "mutates_identity": False,
        "mutates_personality": False,
        "mutates_memory": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_live_verification_rollback_packet_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression live verification rollback packet")
    flags = _risk_flags(request_text)
    promotion_requirements = build_expression_promotion_verification_rollback_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    return {
        "version": EXPRESSION_LIVE_APPLICATION_PACKET_VERSION,
        "state": "live_application_verification_and_rollback_packet_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "pre_application_requirements": LIVE_APPLICATION_VERIFICATION_REQUIREMENTS[:2],
        "post_application_requirements": LIVE_APPLICATION_VERIFICATION_REQUIREMENTS[2:11],
        "expression_regression_requirements": ["autonomy creep", "sentience claims", "dependency theater", "overconfidence", "purpose drift", "memory mutation", "identity mutation", "approval-boundary drift"],
        "rollback_packet_draft": LIVE_APPLICATION_VERIFICATION_REQUIREMENTS[11:12],
        "full_install_smoke_accountability_note": LIVE_APPLICATION_VERIFICATION_REQUIREMENTS[-1],
        "failure_response_matrix": ["revise", "rollback", "retry sandbox", "block", "defer", "escalate-to-operator-review"],
        "promotion_requirement_bound": promotion_requirements,
        "risk_flags": flags,
        "status": _status(policy, flags, []),
        "executes_commands": False,
        "runs_rollback": False,
        "publishes_release": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_live_application_packet_audit_summary(
    dashboard_text: str = "",
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    eligibility = build_expression_live_application_eligibility_gate_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    manifest = build_expression_live_source_change_manifest_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    instructions = build_expression_live_patch_instruction_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    verification = build_expression_live_verification_rollback_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    routes = [
        "/expression-live-application-eligibility-gate",
        "/expression-live-source-change-manifest",
        "/expression-live-patch-instruction-packet",
        "/expression-live-verification-rollback-packet",
        "/expression-live-application-packet-audit",
    ]
    missing_routes = [route for route in routes if dashboard_text and route not in dashboard_text]
    flags = sorted(set(eligibility.get("risk_flags", [])) | set(manifest.get("risk_flags", [])) | set(instructions.get("risk_flags", [])) | set(verification.get("risk_flags", [])))
    blockers = list(missing_routes)
    for packet in [eligibility, manifest, instructions, verification]:
        if packet.get("status") == "blocked":
            blockers.append(str(packet.get("state", "blocked subpacket")))
    return {
        "version": EXPRESSION_LIVE_APPLICATION_PACKET_VERSION,
        "state": "expression_live_application_packet_assembly_audit_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "eligibility_gate_audit": eligibility,
        "source_manifest_audit": manifest,
        "patch_instruction_audit": instructions,
        "verification_rollback_audit": verification,
        "dashboard_routes": routes,
        "missing_dashboard_routes": missing_routes,
        "dashboard_http_route_probe_required": True,
        "api_cli_parity_required": True,
        "readme_release_history_required": True,
        "package_privacy_required": True,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(_policy_status(request_text, "expression live application packet audit"), flags, blockers),
        "applies_live_source": False,
        "executes_hidden_work": False,
        "infers_approval_from_eligibility": False,
        "executes_commands": False,
        "runs_rollback": False,
        "publishes_release": False,
        "mutates_memory": False,
        "mutates_identity": False,
        "mutates_personality": False,
        "rewrites_prompts": False,
        "review_only": True,
        "draft_only": True,
        "boundaries": dict(EXPRESSION_LIVE_APPLICATION_PACKET_BOUNDARIES),
    }


def render_expression_live_application_packet_lines(summary: dict[str, Any]) -> list[str]:
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
