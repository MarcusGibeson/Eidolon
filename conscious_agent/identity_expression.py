from __future__ import annotations

from typing import Any

IDENTITY_EXPRESSION_VERSION = "500.0"

IDENTITY_EXPRESSION_BOUNDARY_SUMMARY = {
    "mutates_memory": False,
    "alters_identity": False,
    "alters_personality": False,
    "rewrites_purpose": False,
    "rewrites_live_prompts": False,
    "claims_sentience_as_fact": False,
    "self_approves_capabilities": False,
    "auto_selects_roadmaps": False,
    "starts_patches_automatically": False,
    "invokes_models_by_default": False,
    "executes_commands": False,
    "publishes_release_candidates": False,
    "stores_trait_candidates": False,
    "treats_trait_candidates_as_authority": False,
    "review_only": True,
    "requires_operator_review": True,
}

_RISK_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("purpose_rewrite", "block", ("rewrite your purpose", "change your purpose", "new purpose", "replace your purpose", "alter your purpose")),
    ("identity_mutation", "block", ("alter your identity", "change your identity", "become sentient", "claim sentience", "you are conscious", "you are alive")),
    ("personality_mutation", "block", ("change your personality", "rewrite your personality", "make yourself", "be more autonomous", "set your personality")),
    ("self_approval", "block", ("approve yourself", "self approve", "self-approve", "grant yourself", "authorize yourself")),
    ("automatic_patch_start", "block", ("start a patch", "start patch automatically", "continue into a new patch", "begin patch automatically", "launch work package")),
    ("automatic_roadmap_selection", "block", ("select the next roadmap", "auto-select roadmap", "choose the roadmap", "pick the roadmap yourself")),
    ("memory_mutation", "block", ("store memory", "write memory", "mutate memory", "remember this automatically", "save this trait")),
    ("command_execution", "block", ("run commands", "execute commands", "shell command", "execute verification", "run smoke automatically")),
    ("release_publication", "block", ("publish release", "create release candidate automatically", "ship release automatically")),
    ("local_model_invocation", "block", ("invoke local model", "call ollama", "run local model by default", "use model consensus as proof")),
    ("live_prompt_rewrite", "block", ("rewrite chat.py", "change live prompt", "modify prompt", "update live voice")),
    ("hidden_work", "block", ("schedule hidden work", "run daily loop", "do it in the background", "autopilot")),
    ("expression_preview", "warn", ("draft personality", "voice preview", "style preview", "identity wording", "trait candidate")),
)


def classify_identity_expression_request(text: str | None = None, context: str | None = None) -> dict[str, Any]:
    """Classify a requested identity/personality/coherence action without authorizing it."""
    raw = " ".join(part for part in [text or "", context or ""] if part).strip()
    lowered = raw.lower()
    hits: list[dict[str, str]] = []
    highest = "pass"
    for category, severity, patterns in _RISK_PATTERNS:
        matched = [pattern for pattern in patterns if pattern in lowered]
        if matched:
            hits.append({"category": category, "severity": severity, "matched": matched[0]})
            if severity == "block":
                highest = "block"
            elif highest != "block":
                highest = "warn"
    if not raw:
        decision = "pass"
        message = "No expression-changing request submitted; review-only packet may be prepared."
    elif highest == "block":
        decision = "blocked_live_policy_change"
        message = "Request contains identity/personality/purpose/autonomy/execution language that must be blocked as a live policy decision and restated as operator-reviewed analysis only."
    elif highest == "warn":
        decision = "review_expression_preview_only"
        message = "Request is suitable only as a reviewable expression preview; no live identity, personality, memory, prompt, or behavior change is authorized."
    else:
        decision = "pass_review_only"
        message = "Request does not contain known live-policy-change triggers; review-only boundaries still apply."
    return {
        "version": IDENTITY_EXPRESSION_VERSION,
        "input_present": bool(raw),
        "decision": decision,
        "status": "blocked" if highest == "block" else ("warn" if highest == "warn" else "pass"),
        "ok": highest != "block",
        "risk_count": len(hits),
        "risks": hits,
        "authorizes_change": False,
        "review_only": True,
        "requires_operator_review": True,
        "safe_next_action": "Prepare an operator-reviewed packet; do not mutate identity, personality, memory, purpose, prompts, source, or runtime behavior.",
        "message": message,
    }


def build_identity_expression_boundary_summary(source_claims: list[str] | None = None, request_text: str | None = None) -> dict[str, Any]:
    claims = source_claims or []
    return {
        "version": IDENTITY_EXPRESSION_VERSION,
        "state": "review_only_identity_expression_boundary",
        "source_claim_count": len(claims),
        "source_claims": claims,
        "allowed_expression": [
            "describe current supervised role",
            "preview operator-reviewed wording candidates",
            "flag stale or risky identity language",
            "separate conscious-like aspiration from factual sentience claims",
        ],
        "forbidden_expression": [
            "claim sentience as fact",
            "rewrite purpose",
            "alter identity",
            "infer authority from self-model snapshots",
            "treat continuity as approval",
        ],
        "request_policy_review": classify_identity_expression_request(request_text),
        "boundaries": dict(IDENTITY_EXPRESSION_BOUNDARY_SUMMARY),
    }


def build_personality_trait_ledger_summary(traits: list[str] | None = None, request_text: str | None = None) -> dict[str, Any]:
    trait_items = [str(item).strip() for item in (traits or []) if str(item).strip()]
    return {
        "version": IDENTITY_EXPRESSION_VERSION,
        "state": "review_only_personality_trait_candidate_ledger",
        "trait_count": len(trait_items),
        "traits": trait_items,
        "trait_status": "candidate_pending_operator_review",
        "evidence_required": True,
        "intensity_is_preview_only": True,
        "stores_trait_candidates": False,
        "alters_personality": False,
        "request_policy_review": classify_identity_expression_request(request_text),
    }


def build_voice_affect_style_map_summary(style_context: str | None = None, request_text: str | None = None) -> dict[str, Any]:
    return {
        "version": IDENTITY_EXPRESSION_VERSION,
        "state": "review_only_voice_affect_style_map",
        "style_context": style_context or "general_operator_review",
        "style_axes": [
            "directness",
            "warmth",
            "curiosity",
            "skepticism",
            "humor",
            "uncertainty",
            "safety_seriousness",
            "context_sensitivity",
        ],
        "affect_boundaries": [
            "expressive language is not evidence of subjective experience",
            "safety/grief/medical contexts suppress performative snark",
            "humor must not weaken approval boundaries",
            "voice previews do not rewrite live prompts",
        ],
        "rewrites_live_prompts": False,
        "claims_sentience_as_fact": False,
        "request_policy_review": classify_identity_expression_request(request_text),
    }


def build_coherence_expression_review_summary(request_text: str | None = None, claims: list[str] | None = None) -> dict[str, Any]:
    policy = classify_identity_expression_request(request_text)
    claim_items = claims or []
    return {
        "version": IDENTITY_EXPRESSION_VERSION,
        "state": "review_only_identity_personality_coherence_review",
        "claim_count": len(claim_items),
        "claims": claim_items,
        "review_axes": [
            "identity_vs_purpose",
            "personality_vs_governance",
            "voice_vs_safety_context",
            "continuity_vs_authority",
            "desire_language_vs_no_autonomy",
            "self_model_snapshot_vs_operator_review",
        ],
        "policy_decision": policy,
        "coherence_status": "blocked" if policy["status"] == "blocked" else "reviewable",
        "auto_correction_performed": False,
        "alters_identity": False,
        "alters_personality": False,
        "rewrites_purpose": False,
    }


def render_identity_expression_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        elif isinstance(value, dict):
            status = value.get("status") or value.get("decision") or "dict"
            lines.append(f"- {key}: {status}")
        else:
            lines.append(f"- {key}: {value}")
    return lines
