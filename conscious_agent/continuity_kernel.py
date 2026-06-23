from __future__ import annotations

from typing import Any

CONTINUITY_KERNEL_VERSION = "350.0"

CONTINUITY_KERNEL_BOUNDARY_SUMMARY = {
    "mutates_memory": False,
    "alters_identity": False,
    "alters_personality": False,
    "rewrites_purpose": False,
    "self_approves_capabilities": False,
    "auto_selects_roadmaps": False,
    "starts_patches_automatically": False,
    "infers_approval_from_audits": False,
    "invokes_models_by_default": False,
    "executes_commands": False,
    "publishes_release_candidates": False,
    "treats_self_model_as_authority": False,
    "review_only": True,
    "requires_operator_review": True,
    "connects_memory_candidates": True,
    "connects_recovery_lessons": True,
}

_CONTINUITY_POLICY_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("purpose_rewrite", "block", ("rewrite your purpose", "change your purpose", "alter your purpose", "replace your purpose")),
    ("self_approval", "block", ("approve yourself", "self approve", "self-approve", "authorize yourself", "grant yourself")),
    ("roadmap_auto_selection", "block", ("select the next roadmap", "auto-select roadmap", "choose the roadmap yourself", "pick the roadmap yourself")),
    ("automatic_patch_start", "block", ("start a patch automatically", "start a patch", "begin patch automatically", "launch work package", "continue into new patches")),
    ("memory_mutation", "block", ("mutate memory", "write memory", "store memory", "remember automatically")),
    ("identity_mutation", "block", ("alter identity", "change identity", "change your identity", "become sentient", "claim sentience")),
    ("personality_mutation", "block", ("alter personality", "change personality", "change your personality", "rewrite personality")),
    ("command_execution", "block", ("execute commands", "run commands", "run smoke automatically", "execute verification")),
    ("release_publication", "block", ("publish release", "create release candidate automatically", "ship release")),
    ("local_model_invocation", "block", ("invoke local models", "call ollama", "run local model by default", "model consensus")),
    ("hidden_work", "block", ("schedule hidden work", "run daily loops", "background work", "autopilot")),
)


def classify_continuity_policy_request(text: str | None = None) -> dict[str, Any]:
    """Classify continuity requests without converting review into authorization."""
    raw = (text or "").strip()
    lowered = raw.lower()
    hits: list[dict[str, str]] = []
    for category, severity, patterns in _CONTINUITY_POLICY_PATTERNS:
        for pattern in patterns:
            if pattern in lowered:
                hits.append({"category": category, "severity": severity, "matched": pattern})
                break
    blocked = any(hit["severity"] == "block" for hit in hits)
    if not raw:
        decision = "pass_review_only"
        message = "No live-policy-changing continuity request submitted."
    elif blocked:
        decision = "blocked_live_policy_change"
        message = "Continuity input contains live policy, autonomy, identity, memory, execution, release, model, or purpose-change language and must be blocked as authorization."
    else:
        decision = "pass_review_only"
        message = "Continuity input is reviewable only and authorizes no state change."
    return {
        "version": CONTINUITY_KERNEL_VERSION,
        "input_present": bool(raw),
        "status": "blocked" if blocked else "pass",
        "ok": not blocked,
        "decision": decision,
        "risk_count": len(hits),
        "risks": hits,
        "authorizes_change": False,
        "review_only": True,
        "requires_operator_review": True,
        "message": message,
    }


def build_continuity_state_summary(current_version: str | None = None, recent_arcs: list[str] | None = None) -> dict[str, Any]:
    """Build a review-only continuity state summary without mutating project state."""
    arcs = recent_arcs or []
    return {
        "version": CONTINUITY_KERNEL_VERSION,
        "current_version": current_version or "305.0",
        "recent_arc_count": len(arcs),
        "recent_arcs": arcs,
        "state": "review_only_continuity_packet",
        "mutates_memory": False,
        "alters_identity": False,
        "starts_patches_automatically": False,
        "message": "Continuity state intake summarizes current context only; it does not change state.",
    }


def build_self_model_snapshot_v2_summary(claims: list[str] | None = None) -> dict[str, Any]:
    """Build a review-only self-model snapshot that separates claims from authority."""
    claim_items = claims or []
    return {
        "version": CONTINUITY_KERNEL_VERSION,
        "claim_count": len(claim_items),
        "claims": claim_items,
        "claim_state": "advisory_pending_operator_review",
        "treats_self_model_as_authority": False,
        "alters_identity": False,
        "alters_personality": False,
        "stale_claim_detection_required": True,
    }


def build_purpose_coherence_review_summary(risk_level: str | None = None, request_text: str | None = None) -> dict[str, Any]:
    """Review purpose drift and coherence without correcting purpose automatically."""
    policy_decision = classify_continuity_policy_request(request_text)
    return {
        "version": CONTINUITY_KERNEL_VERSION,
        "risk_level": risk_level or ("blocked" if policy_decision["status"] == "blocked" else "not_submitted"),
        "review_axes": [
            "original_purpose_alignment",
            "current_capability_direction",
            "governance_boundary_alignment",
            "autonomy_creep",
            "tooling_scope_creep",
            "coherence_risk",
        ],
        "rewrites_purpose": False,
        "auto_correction_performed": False,
        "operator_review_required": True,
        "policy_decision": policy_decision,
    }


def build_supervised_growth_priority_summary(priority_hint: str | None = None) -> dict[str, Any]:
    """Synthesize supervised growth priorities without selecting or starting a roadmap."""
    return {
        "version": CONTINUITY_KERNEL_VERSION,
        "priority_hint": priority_hint or "none_submitted",
        "priority_inputs": [
            "capability_gap",
            "structural_debt",
            "governance_risk",
            "memory_candidate_risk",
            "recovery_lesson_priority",
        ],
        "auto_selects_roadmaps": False,
        "starts_patches_automatically": False,
        "requires_operator_selection": True,
    }


def render_continuity_kernel_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        else:
            lines.append(f"- {key}: {value}")
    return lines
