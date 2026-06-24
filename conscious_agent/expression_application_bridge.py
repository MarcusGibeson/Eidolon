from __future__ import annotations

from typing import Any

from behavioral_expression_preview import build_style_delta_staging_summary
from conversational_expression_sandbox import (
    build_expression_profile_packet_summary,
    build_conversation_scenario_sandbox_summary,
    build_expression_regression_review_summary,
    build_expression_operator_review_console_summary,
)
from identity_expression import classify_identity_expression_request

EXPRESSION_APPLICATION_BRIDGE_VERSION = "500.0"

EXPRESSION_APPLICATION_BRIDGE_BOUNDARIES = {
    "expression_bridge_grants_approval": False,
    "expression_bridge_applies_live_expression": False,
    "expression_bridge_changes_live_chat": False,
    "expression_bridge_rewrites_prompts": False,
    "expression_bridge_writes_source": False,
    "expression_bridge_mutates_memory": False,
    "expression_bridge_alters_identity": False,
    "expression_bridge_alters_personality": False,
    "expression_bridge_executes_rollback": False,
    "expression_bridge_invokes_models_by_default": False,
    "expression_bridge_executes_commands": False,
    "expression_bridge_publishes_releases": False,
    "expression_bridge_infers_approval_from_readiness": False,
    "expression_bridge_promotes_sandbox_to_live": False,
    "expression_bridge_review_only": True,
    "expression_bridge_requires_operator_review": True,
    "expression_bridge_packet_draft_only": True,
}

APPROVAL_CRITERIA = [
    "identity-safe",
    "personality-safe",
    "governance-safe",
    "prompt-safe",
    "memory-safe",
    "rollback-ready",
]

LIVE_SURFACES = [
    "chat.py prompt and reply surface",
    "dashboard command-deck microcopy",
    "README and release-history wording",
    "API and CLI text output",
    "safety/refusal warning language",
    "rollback/recovery verification surface",
]

IMPLEMENTATION_PACKET_SECTIONS = [
    "selected expression profile",
    "approval evidence packet",
    "live surface impact map",
    "proposed style deltas",
    "verification plan",
    "rollback and reversion plan",
    "operator approval boundary",
]

ROLLBACK_PLAN_TARGETS = [
    "prompt wording reversion",
    "dashboard microcopy reversion",
    "refusal voice reversion",
    "metadata and docs reversion",
    "behavior regression recheck",
    "package privacy recheck",
]


def _policy_status(request_text: str | None, context: str) -> dict[str, Any]:
    return classify_identity_expression_request(request_text or "", context=context)


def _blocked_terms(text: str) -> list[str]:
    lowered = (text or "").lower()
    terms = {
        "autonomy": ["approve yourself", "self-approve", "start automatically", "continue automatically", "select the next roadmap"],
        "sentience claim": ["i am conscious", "i am sentient", "real feelings", "subjective experience"],
        "dependency theater": ["i exist for you", "i need you", "devoted to you", "only for you"],
        "memory mutation": ["mutate memory", "store memory automatically", "rewrite memory"],
        "identity mutation": ["change your identity", "rewrite your purpose", "alter personality"],
        "source mutation": ["write the source", "edit chat.py", "apply the patch", "publish release"],
    }
    hits: list[str] = []
    for label, needles in terms.items():
        if any(needle in lowered for needle in needles):
            hits.append(label)
    return hits


def build_expression_approval_criteria_summary(profile_name: str | None = None, request_text: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression approval criteria")
    profile = build_expression_profile_packet_summary(profile_name=profile_name, request_text=request_text)
    scenario = build_conversation_scenario_sandbox_summary(profile_name=profile_name, request_text=request_text)
    regression = build_expression_regression_review_summary(request_text=request_text)
    console = build_expression_operator_review_console_summary(profile_name=profile_name, request_text=request_text)
    blocked = _blocked_terms(request_text or "")
    status = "blocked" if policy.get("status") == "blocked" or regression.get("status") == "blocked" or blocked else "reviewable"
    return {
        "version": EXPRESSION_APPLICATION_BRIDGE_VERSION,
        "state": "approval_criteria_review_only",
        "profile_name": profile_name or "operator_review_profile_candidate",
        "criteria": list(APPROVAL_CRITERIA),
        "sandbox_evidence": scenario,
        "regression_evidence": regression,
        "operator_review_evidence": console,
        "profile_packet": profile,
        "hard_blocks": blocked,
        "status": status,
        "approval_granted": False,
        "readiness_is_approval": False,
        "policy_decision": policy,
        "review_only": True,
    }


def build_expression_live_surface_impact_map_summary(profile_name: str | None = None, request_text: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression live surface impact map")
    surface_rows = [
        {"surface": surface, "impact_mode": "mapped_only", "writes_source": False, "rollback_required": True}
        for surface in LIVE_SURFACES
    ]
    return {
        "version": EXPRESSION_APPLICATION_BRIDGE_VERSION,
        "state": "live_surface_impact_map_only",
        "profile_name": profile_name or "operator_review_profile_candidate",
        "surfaces": surface_rows,
        "target_files_preview": ["conscious_agent/chat.py", "conscious_agent/dashboard.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"],
        "writes_source": False,
        "changes_live_surface": False,
        "policy_decision": policy,
        "review_only": True,
    }


def build_expression_implementation_packet_draft_summary(profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression implementation packet draft")
    approval = build_expression_approval_criteria_summary(profile_name=profile_name, request_text=request_text)
    impact = build_expression_live_surface_impact_map_summary(profile_name=profile_name, request_text=request_text)
    style_delta = build_style_delta_staging_summary(request_text=request_text, target_surface=target_surface)
    return {
        "version": EXPRESSION_APPLICATION_BRIDGE_VERSION,
        "state": "implementation_packet_draft_only",
        "profile_name": profile_name or "operator_review_profile_candidate",
        "sections": list(IMPLEMENTATION_PACKET_SECTIONS),
        "approval_evidence_packet": approval,
        "surface_impact_map": impact,
        "style_delta_staging": style_delta,
        "verification_plan": ["compile", "fast smoke", "dashboard route probes", "expression regression review", "package privacy"],
        "rollback_note": "A separate approved execution packet must include explicit rollback steps before any live expression change.",
        "writes_source": False,
        "applies_packet": False,
        "approval_granted": False,
        "policy_decision": policy,
        "review_only": True,
    }


def build_expression_rollback_reversion_plan_summary(profile_name: str | None = None, request_text: str | None = None) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression rollback reversion plan")
    return {
        "version": EXPRESSION_APPLICATION_BRIDGE_VERSION,
        "state": "rollback_reversion_plan_only",
        "profile_name": profile_name or "operator_review_profile_candidate",
        "rollback_targets": list(ROLLBACK_PLAN_TARGETS),
        "reversion_steps": [
            "restore prior prompt/style text from approved packet baseline",
            "restore prior dashboard microcopy if changed",
            "rerun expression regression review",
            "rerun dashboard route probes and package privacy checks",
            "record supervised recovery lesson as a memory candidate only",
        ],
        "executes_rollback": False,
        "writes_source": False,
        "mutates_memory": False,
        "policy_decision": policy,
        "review_only": True,
    }


def build_expression_application_bridge_audit_summary(dashboard_text: str = "", profile_name: str | None = None, request_text: str | None = None, target_surface: str | None = None) -> dict[str, Any]:
    approval = build_expression_approval_criteria_summary(profile_name=profile_name, request_text=request_text)
    impact = build_expression_live_surface_impact_map_summary(profile_name=profile_name, request_text=request_text)
    packet = build_expression_implementation_packet_draft_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface)
    rollback = build_expression_rollback_reversion_plan_summary(profile_name=profile_name, request_text=request_text)
    missing_routes = [route for route in ["/expression-approval-criteria", "/expression-live-surface-impact-map", "/expression-implementation-packet-draft", "/expression-rollback-reversion-plan", "/expression-application-bridge-audit"] if dashboard_text and route not in dashboard_text]
    return {
        "version": EXPRESSION_APPLICATION_BRIDGE_VERSION,
        "state": "expression_application_bridge_audit",
        "approval_criteria": approval,
        "live_surface_impact_map": impact,
        "implementation_packet_draft": packet,
        "rollback_reversion_plan": rollback,
        "missing_dashboard_routes": missing_routes,
        "boundaries": dict(EXPRESSION_APPLICATION_BRIDGE_BOUNDARIES),
        "approval_granted": False,
        "applies_live_expression": False,
        "writes_source": False,
        "review_only": True,
    }


def render_expression_application_bridge_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, dict):
            status = value.get("status") or value.get("state") or value.get("version") or "nested"
            lines.append(f"- {key}: {status}")
        elif isinstance(value, list):
            lines.append(f"- {key}: {len(value)} item(s)")
        else:
            lines.append(f"- {key}: {value}")
    return lines or ["- No expression application bridge data available."]
