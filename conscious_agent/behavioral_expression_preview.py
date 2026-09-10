from __future__ import annotations

from typing import Any

from identity_expression import classify_identity_expression_request
from route_health import ROUTE_HEALTH_VERSION, build_route_health_registry_summary, build_smoke_visibility_summary

BEHAVIORAL_EXPRESSION_PREVIEW_VERSION = "1032.0"
EXPRESSION_PREVIEW_BOUNDARIES = {
    "behavioral_expression_changes_live_chat": False,
    "behavioral_expression_rewrites_prompts": False,
    "behavioral_expression_mutates_memory": False,
    "behavioral_expression_alters_identity": False,
    "behavioral_expression_alters_personality": False,
    "behavioral_expression_applies_style_deltas": False,
    "behavioral_expression_executes_commands": False,
    "behavioral_expression_invokes_models_by_default": False,
    "behavioral_expression_publishes_releases": False,
    "behavioral_expression_infers_approval_from_preview": False,
    "behavioral_expression_review_only": True,
    "behavioral_expression_requires_operator_review": True,
}

_PREVIEW_CONTEXTS = [
    "coding help",
    "governance warning",
    "dashboard microcopy",
    "operator planning",
    "safety refusal",
    "continuity reflection",
]

_STYLE_DELTA_TARGETS = [
    "chat prompt wording preview",
    "dashboard microcopy candidate",
    "README tone candidate",
    "operator-facing warning candidate",
    "refusal voice candidate",
]


def build_behavioral_expression_preview_summary(request_text: str | None = None, style_context: str | None = None) -> dict[str, Any]:
    policy = classify_identity_expression_request(request_text or "", context="behavioral expression preview")
    context = style_context or "operator_review"
    return {
        "version": BEHAVIORAL_EXPRESSION_PREVIEW_VERSION,
        "state": "review_only_behavioral_expression_preview",
        "context": context,
        "available_contexts": _PREVIEW_CONTEXTS,
        "preview_variants": ["neutral", "warm", "direct", "skeptical", "high-personality"],
        "sample_packet_shape": {
            "source_trait": "candidate only",
            "proposed_wording": "preview only",
            "risk": "classified before review",
            "operator_status": "pending review",
        },
        "policy_decision": policy,
        "applies_preview": False,
        "rewrites_live_behavior": False,
        "review_only": True,
    }


def build_style_delta_staging_summary(target_surface: str | None = None, request_text: str | None = None) -> dict[str, Any]:
    policy = classify_identity_expression_request(request_text or "", context="style delta staging")
    return {
        "version": BEHAVIORAL_EXPRESSION_PREVIEW_VERSION,
        "state": "operator_reviewed_style_delta_staging",
        "target_surface": target_surface or "unspecified_review_surface",
        "candidate_targets": _STYLE_DELTA_TARGETS,
        "delta_shape": {
            "target_file": "review only",
            "proposed_change": "preview only",
            "expected_effect": "operator-reviewed hypothesis",
            "rollback_note": "required before any future application packet",
        },
        "risk_classification": "blocked" if policy.get("status") == "blocked" else "reviewable",
        "policy_decision": policy,
        "applies_delta": False,
        "writes_source": False,
        "review_only": True,
    }


def build_expression_runtime_health_audit_summary(dashboard_text: str = "", request_text: str | None = None) -> dict[str, Any]:
    return {
        "version": BEHAVIORAL_EXPRESSION_PREVIEW_VERSION,
        "route_health": build_route_health_registry_summary(dashboard_text=dashboard_text),
        "smoke_visibility": build_smoke_visibility_summary(),
        "behavioral_preview": build_behavioral_expression_preview_summary(request_text=request_text),
        "style_delta_staging": build_style_delta_staging_summary(request_text=request_text),
        "route_health_version": ROUTE_HEALTH_VERSION,
        "boundaries": dict(EXPRESSION_PREVIEW_BOUNDARIES),
        "safe_next_action": "Operator may review previews and route health reports. Any live style, prompt, source, memory, identity, personality, command, release, or roadmap change requires a separate approved execution packet.",
    }


def render_behavioral_expression_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        elif isinstance(value, dict):
            status = value.get("status") or value.get("state") or value.get("version") or f"{len(value)} field(s)"
            lines.append(f"- {key}: {status}")
        else:
            lines.append(f"- {key}: {value}")
    return lines
