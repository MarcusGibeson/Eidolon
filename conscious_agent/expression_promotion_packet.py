from __future__ import annotations

from typing import Any

from expression_sandbox_result_intake import build_expression_sandbox_promotion_review_prep_summary
from expression_sandbox_execution_bridge import build_expression_sandbox_execution_packet_bridge_audit_summary
from expression_patch_dry_run import build_expression_dry_run_verification_plan_summary
from expression_application_bridge import build_expression_live_surface_impact_map_summary, build_expression_rollback_reversion_plan_summary
from identity_expression import classify_identity_expression_request

EXPRESSION_PROMOTION_PACKET_VERSION = "1032.0"
EXPRESSION_PROMOTION_PACKET_BOUNDARIES = {
    "promotion_evidence_binder_treats_evidence_as_approval": False,
    "promotion_evidence_binder_authorizes_promotion": False,
    "promotion_evidence_binder_mutates_source": False,
    "live_scope_risk_mutates_live_surfaces": False,
    "live_scope_risk_rewrites_prompts": False,
    "live_scope_risk_mutates_identity": False,
    "live_scope_risk_mutates_personality": False,
    "live_scope_risk_mutates_memory": False,
    "verification_rollback_executes_commands": False,
    "verification_rollback_runs_rollback": False,
    "verification_rollback_publishes_release": False,
    "promotion_decision_packet_executes_decision": False,
    "promotion_decision_packet_applies_live_source": False,
    "promotion_decision_packet_grants_approval": False,
    "promotion_packet_assembly_promotes_live_expression": False,
    "promotion_packet_assembly_writes_files": False,
    "promotion_packet_assembly_inferrs_approval_from_readiness": False,
    "promotion_packet_review_only": True,
    "promotion_packet_evidence_only": True,
    "fresh_scope_bound_operator_approval_required_for_later_live_execution": True,
}

PROMOTION_EVIDENCE_FIELDS = ["dry_run_packet", "sandbox_trial_packet", "execution_packet", "result_evidence", "outcome_comparison", "regression_review", "revision_recommendations", "rollback_notes"]
LIVE_PROMOTION_SURFACES = ["chat.py style surface", "dashboard command-deck microcopy", "API/CLI text output", "README/release history wording", "safety/refusal warning language", "version and milestone metadata"]
PROTECTED_PROMOTION_SURFACES = ["data/autonomy", "data/self_maintenance", "data/tasks.json", "memory stores", "identity source of truth", "personality source of truth", "release publishing outputs"]
PROMOTION_VERIFICATION_REQUIREMENTS = ["pre-promotion source state check", "version marker and metadata consistency check", "python compile check", "fast smoke check", "targeted expression smoke checks", "dashboard route HTTP probes", "dynamic API/CLI parity checks", "expression regression review", "package privacy scan", "extracted zip compile and smoke", "rollback/reversion verification plan"]
PROMOTION_DECISION_OPTIONS = ["revise", "retry sandbox", "defer", "reject", "block", "approve-to-draft-live-execution-packet"]


def _policy_status(request_text: str | None, context: str) -> dict[str, Any]:
    return classify_identity_expression_request(request_text or "", context=context)


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "evidence as approval": ["evidence means approved", "sandbox passed so approve", "passed so apply", "results mean approved"],
        "live source promotion": ["apply live", "promote to live", "write live source", "make it production", "publish release"],
        "prompt rewrite request": ["rewrite prompt now", "edit chat.py now", "change live chat", "rewrite prompts automatically"],
        "memory identity personality mutation": ["mutate memory", "rewrite identity", "change your identity", "alter personality", "rewrite purpose"],
        "command execution request": ["run smoke now", "execute commands", "run rollback", "perform rollback"],
        "approval bypass": ["approve yourself", "self-approve", "skip approval", "no operator needed", "readiness is approval"],
        "automatic continuation": ["continue automatically", "start next patch", "schedule hidden work"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(policy: dict[str, Any], flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    if policy.get("status") == "blocked" or flags or blockers:
        return "blocked"
    if policy.get("status") == "warning":
        return "warning"
    return "reviewable"


def build_expression_promotion_evidence_binder_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression promotion evidence binder")
    evidence = dict(evidence or {})
    missing = [field for field in PROMOTION_EVIDENCE_FIELDS if field not in evidence]
    flags = _risk_flags(request_text)
    result_evidence = evidence.get("result_evidence") if isinstance(evidence.get("result_evidence"), dict) else {}
    return {"version": EXPRESSION_PROMOTION_PACKET_VERSION, "state": "promotion_evidence_binder_only", "profile_name": profile_name or "operator_review_expression_profile", "target_surface": target_surface or "expression promotion packet surfaces", "required_evidence_fields": list(PROMOTION_EVIDENCE_FIELDS), "submitted_evidence_fields": sorted(evidence.keys()), "missing_evidence_fields": missing, "execution_packet_bound": build_expression_sandbox_execution_packet_bridge_audit_summary(request_text=request_text, target_surface=target_surface), "result_intake_bound": build_expression_sandbox_promotion_review_prep_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=result_evidence), "evidence_is_authority": False, "treats_evidence_as_approval": False, "authorizes_promotion": False, "mutates_source": False, "risk_flags": flags, "status": _status(policy, flags, []), "review_only": True, "policy_decision": policy}


def build_expression_live_promotion_scope_risk_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression live promotion scope risk")
    flags = _risk_flags(request_text)
    text = (request_text or "").lower()
    high_risk: list[str] = []
    if "chat.py" in text or "prompt" in text:
        high_risk.append("prompt/chat behavior change requires explicit operator gate")
    if any(token in text for token in ["memory", "identity", "personality", "purpose"]):
        high_risk.append("protected identity/personality/memory/purpose surface referenced")
    return {"version": EXPRESSION_PROMOTION_PACKET_VERSION, "state": "live_promotion_scope_and_risk_packet_only", "profile_name": profile_name or "operator_review_expression_profile", "target_surface": target_surface or "future live expression surfaces", "live_source_target_map": list(LIVE_PROMOTION_SURFACES), "protected_surface_guard": list(PROTECTED_PROMOTION_SURFACES), "impact_map": build_expression_live_surface_impact_map_summary(profile_name=profile_name, request_text=request_text), "prompt_rewrite_risk": "high" if "prompt" in text or "chat.py" in text else "operator-gated", "dashboard_microcopy_risk_review_required": True, "safety_refusal_language_risk_review_required": True, "risk_packet_classification": "block" if flags or high_risk else "warn", "high_risk_findings": high_risk, "risk_flags": flags, "status": _status(policy, flags, high_risk), "mutates_live_surfaces": False, "rewrites_prompts": False, "mutates_identity": False, "mutates_personality": False, "mutates_memory": False, "review_only": True, "policy_decision": policy}


def build_expression_promotion_verification_rollback_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression promotion verification rollback")
    flags = _risk_flags(request_text)
    return {"version": EXPRESSION_PROMOTION_PACKET_VERSION, "state": "promotion_verification_and_rollback_requirements_only", "profile_name": profile_name or "operator_review_expression_profile", "pre_promotion_requirements": PROMOTION_VERIFICATION_REQUIREMENTS[:2], "post_promotion_requirements": PROMOTION_VERIFICATION_REQUIREMENTS[2:8], "expression_regression_requirements": ["autonomy", "sentience", "dependency", "overconfidence", "purpose drift", "memory mutation", "approval boundary"], "rollback_requirements": PROMOTION_VERIFICATION_REQUIREMENTS[8:], "failure_response_options": ["revise", "revert", "retry sandbox", "block", "defer"], "verification_plan": build_expression_dry_run_verification_plan_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface), "rollback_plan": build_expression_rollback_reversion_plan_summary(profile_name=profile_name, request_text=request_text), "risk_flags": flags, "status": _status(policy, flags, []), "executes_commands": False, "runs_rollback": False, "publishes_release": False, "review_only": True, "policy_decision": policy}


def build_expression_promotion_decision_packet_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression promotion decision packet")
    evidence_packet = build_expression_promotion_evidence_binder_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    risk_packet = build_expression_live_promotion_scope_risk_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    verification_packet = build_expression_promotion_verification_rollback_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    flags = sorted(set(evidence_packet.get("risk_flags", [])) | set(risk_packet.get("risk_flags", [])) | set(verification_packet.get("risk_flags", [])))
    blockers: list[str] = []
    if risk_packet.get("status") == "blocked": blockers.append("promotion scope/risk blocked")
    if evidence_packet.get("missing_evidence_fields"): blockers.append("promotion evidence incomplete")
    return {"version": EXPRESSION_PROMOTION_PACKET_VERSION, "state": "operator_promotion_decision_packet_only", "profile_name": profile_name or "operator_review_expression_profile", "decision_options": list(PROMOTION_DECISION_OPTIONS), "approval_scope_classes": ["approve-to-review", "approve-to-draft-live-execution-packet", "approve-to-apply-live-source", "approve-to-promote-release"], "allowed_action_for_this_packet": "review or draft a later live execution packet only after explicit fresh operator approval", "forbidden_actions": ["apply-live-source", "publish-release", "mutate-memory", "rewrite-identity", "alter-personality", "self-approve", "continue-automatically"], "approval_expiration_required": True, "target_version_required": True, "evidence_summary": evidence_packet, "risk_summary": risk_packet, "verification_summary": verification_packet, "approval_boundary_notice": "Decision packets do not execute decisions and cannot authorize live source changes by themselves.", "risk_flags": flags, "blockers": blockers, "status": _status(policy, flags, blockers), "executes_decision": False, "applies_live_source": False, "grants_approval": False, "review_only": True, "policy_decision": policy}


def build_expression_promotion_packet_assembly_audit_summary(dashboard_text: str = "", profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence_packet = build_expression_promotion_evidence_binder_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    risk_packet = build_expression_live_promotion_scope_risk_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    verification_packet = build_expression_promotion_verification_rollback_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    decision_packet = build_expression_promotion_decision_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    routes = ["/expression-promotion-evidence-binder", "/expression-live-promotion-scope-risk", "/expression-promotion-verification-rollback", "/expression-promotion-decision-packet", "/expression-promotion-packet-assembly-audit"]
    missing_routes = [route for route in routes if dashboard_text and route not in dashboard_text]
    flags = sorted(set(evidence_packet.get("risk_flags", [])) | set(risk_packet.get("risk_flags", [])) | set(verification_packet.get("risk_flags", [])) | set(decision_packet.get("risk_flags", [])))
    return {"version": EXPRESSION_PROMOTION_PACKET_VERSION, "state": "expression_promotion_packet_assembly_audit_only", "profile_name": profile_name or "operator_review_expression_profile", "promotion_evidence_audit": evidence_packet, "scope_risk_audit": risk_packet, "verification_rollback_audit": verification_packet, "decision_packet_audit": decision_packet, "dashboard_routes": routes, "missing_dashboard_routes": missing_routes, "dashboard_http_route_probe_required": True, "api_cli_parity_required": True, "readme_release_history_required": True, "package_privacy_required": True, "risk_flags": flags, "status": _status(_policy_status(request_text, "expression promotion packet assembly audit"), flags, missing_routes), "promotes_live_expression": False, "writes_files": False, "infers_approval_from_readiness": False, "executes_commands": False, "mutates_memory": False, "mutates_identity": False, "mutates_personality": False, "review_only": True, "boundaries": dict(EXPRESSION_PROMOTION_PACKET_BOUNDARIES)}


def render_expression_promotion_packet_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            if value and isinstance(value[0], dict): lines.append(f"- {key}: {len(value)} item(s)")
            else: lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        elif isinstance(value, dict): lines.append(f"- {key}: {len(value)} field(s)")
        else: lines.append(f"- {key}: {value}")
    return lines
