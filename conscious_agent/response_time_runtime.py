from __future__ import annotations

"""Provider-neutral response-time controls for the v1251 performance arc.

This module only selects model-facing context, bounded generation budgets, and
content-free timing telemetry. It never grants approval, executes actions,
contacts a provider on its own, or mutates a project.
"""

from dataclasses import dataclass, asdict
import hashlib
import json
import re
from typing import Any, Mapping

CONTRACT_VERSION = "v1489.0-conversation-repair"
MAX_COMPACT_COGNITIVE_CHARS = 3200
MAX_SECTION_CHARS = 900
AUTHORITY_FLAGS = {
    "approval_granted": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "provider_contact_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}

_DETAIL_CUES = re.compile(
    r"\b(?:explain|detail|detailed|compare|analy[sz]e|review|research|roadmap|plan|architecture|why|how|steps|comprehensive)\b",
    re.I,
)
_SOCIAL_CUES = re.compile(r"^(?:hi|hello|hey|thanks|thank you|cool|nice|great|awesome|lol|haha)[!. ]*$", re.I)
_PLANNING_CUES = re.compile(
    r"\b(?:plan|roadmap|schedule|strategy|milestone|next steps?|priorit(?:y|ize)|design|decide|decision|choice|choices|options?|trade[ -]?offs?|pros? and cons?|what should i|should i|what would you|which (?:one|option)|approach|think through|figure out|what to do next)\b",
    re.I,
)
_DEVELOPMENT_CUES = re.compile(r"\b(?:code|build|implement|fix|bug|test|project|website|python|javascript|java|rust|golang|php|\.net)\b", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _nested_bool(value: Mapping[str, Any] | None, *path: str) -> bool:
    current: Any = value or {}
    for key in path:
        if not isinstance(current, Mapping):
            return False
        current = current.get(key)
    return bool(current)


def _section(value: Mapping[str, Any] | None, *, limit: int = MAX_SECTION_CHARS) -> str:
    text = str((value or {}).get("prompt_section") or "").strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    # Keep whole lines when possible. The projection is advisory prompt context,
    # never an authorization record, so bounded compaction cannot grant authority.
    pieces: list[str] = []
    used = 0
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        addition = len(candidate) + (1 if pieces else 0)
        if used + addition > limit:
            break
        pieces.append(candidate)
        used += addition
    return "\n".join(pieces) or text[:limit].rstrip()


@dataclass(frozen=True)
class TurnRelevance:
    lane: str
    social_only: bool
    planning_relevant: bool
    development_relevant: bool
    action_relevant: bool
    memory_relevant: bool
    detailed_response: bool

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["relevance_digest"] = _digest(row)
        return row


def classify_turn_relevance(
    message: str,
    *,
    action_projection: Mapping[str, Any] | None = None,
    development_campaign: Mapping[str, Any] | None = None,
) -> TurnRelevance:
    text = " ".join(str(message or "").split())
    action = _nested_bool(action_projection, "intent", "action_intent_present")
    development = bool((development_campaign or {}).get("active")) or bool(_DEVELOPMENT_CUES.search(text))
    planning = bool(_PLANNING_CUES.search(text))
    social = bool(_SOCIAL_CUES.fullmatch(text)) and not action and not development and not planning
    detailed = bool(_DETAIL_CUES.search(text)) or len(text) > 320
    memory = not social and bool(re.search(r"\b(?:remember|before|previous|earlier|last time|again|continue|we discussed)\b", text, re.I))
    if action:
        lane = "action"
    elif development:
        lane = "development"
    elif planning:
        lane = "planning"
    elif social:
        lane = "social"
    else:
        lane = "ordinary"
    return TurnRelevance(
        lane=lane,
        social_only=social,
        planning_relevant=planning or development,
        development_relevant=development,
        action_relevant=action,
        memory_relevant=memory,
        detailed_response=detailed,
    )


def build_compact_cognitive_projection(
    message: str,
    *,
    action_projection: Mapping[str, Any] | None,
    development_campaign: Mapping[str, Any] | None,
    cognitive: Mapping[str, Any] | None,
    conversation_policy: Mapping[str, Any] | None,
    conversation_discourse: Mapping[str, Any] | None,
    memory_retrieval: Mapping[str, Any] | None,
    natural_continuity: Mapping[str, Any] | None,
    natural_follow_up: Mapping[str, Any] | None,
    governed_speech: Mapping[str, Any] | None,
    daily_companion: Mapping[str, Any] | None,
    goal_candidate: Mapping[str, Any] | None = None,
    hierarchical_planning: Mapping[str, Any] | None = None,
    plan_simulation: Mapping[str, Any] | None = None,
    persistent_follow_through: Mapping[str, Any] | None = None,
    goal_planning_alpha: Mapping[str, Any] | None = None,
    action_handoff_prompt: str = "",
    developer_campaign_prompt: str = "",
    development_campaign_prompt: str = "",
    supervised_execution_prompt: str = "",
    supervised_result_prompt: str = "",
) -> tuple[str, dict[str, Any]]:
    """Return one relevance-gated model-facing projection.

    Detailed internal cognition still exists in runtime receipts. This function
    deliberately separates internal evidence from the much smaller context the
    local model needs to produce a response.
    """
    relevance = classify_turn_relevance(
        message, action_projection=action_projection, development_campaign=development_campaign,
    )
    sections: list[tuple[str, str]] = []

    def add(label: str, text: str, limit: int = MAX_SECTION_CHARS) -> None:
        compact = "\n".join(line.strip() for line in str(text or "").splitlines() if line.strip())
        if not compact:
            return
        compact = compact[:limit].rstrip()
        if compact:
            sections.append((label, compact))

    ordinary_casual = relevance.lane in {"social", "ordinary"}

    # The response contract and discourse controls are relevant for every turn.
    # Ordinary conversation keeps the model-facing projection intentionally
    # small, while giving the follow-up contract enough room to remain legible.
    add("conversation", _section(conversation_policy, limit=420 if ordinary_casual else 550), 420 if ordinary_casual else 550)
    add("discourse", _section(conversation_discourse, limit=360 if ordinary_casual else 500), 360 if ordinary_casual else 500)
    add("continuity", _section(natural_continuity, limit=320 if ordinary_casual else 380), 320 if ordinary_casual else 380)
    add("follow_up", _section(natural_follow_up, limit=640), 640)

    # Casual turns already receive the protected conversation-quality contract
    # next to the latest message. Repeating broad speech/self-reflection blocks
    # here increased prompt cost and gave small local models competing advice.
    if not ordinary_casual:
        add("speech", _section(governed_speech, limit=300), 300)
        add("cognition", _section(cognitive, limit=450), 450)
        add("companion", _section(daily_companion, limit=250), 250)
    if relevance.memory_relevant:
        add("memory", _section(memory_retrieval, limit=400), 400)

    if relevance.planning_relevant:
        add("goal_candidate", _section(goal_candidate, limit=500), 500)
        add("planning", _section(hierarchical_planning, limit=550), 550)
        add("simulation", _section(plan_simulation, limit=450), 450)
        add("follow_through", _section(persistent_follow_through, limit=450), 450)
        add("planning_alpha", _section(goal_planning_alpha, limit=450), 450)

    if relevance.action_relevant:
        add("action", _section(action_projection, limit=700), 700)
        add("action_handoff", action_handoff_prompt, 700)
        add("execution", supervised_execution_prompt, 600)
        add("result", supervised_result_prompt, 500)

    if relevance.development_relevant:
        add("developer_campaign", developer_campaign_prompt, 700)
        add("development_lifecycle", development_campaign_prompt, 700)

    header = (
        "RUNTIME RESPONSE PROJECTION\n"
        f"lane={relevance.lane}; preserve operator authority; never infer execution, approval, provider contact, or mutation."
    )
    body_parts = [header]
    included: list[str] = []
    for label, text in sections:
        candidate = f"[{label}]\n{text}"
        if sum(len(part) + 2 for part in body_parts) + len(candidate) > MAX_COMPACT_COGNITIVE_CHARS:
            continue
        body_parts.append(candidate)
        included.append(label)
    prompt = "\n\n".join(body_parts)
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "lane": relevance.lane,
        "relevance": relevance.to_dict(),
        "projection_chars": len(prompt),
        "estimated_projection_tokens": max(1, (len(prompt) + 3) // 4),
        "included_sections": included,
        "omitted_planning_by_relevance": not relevance.planning_relevant,
        "omitted_development_by_relevance": not relevance.development_relevant,
        "omitted_action_by_relevance": not relevance.action_relevant,
        "ordinary_casual_projection": ordinary_casual,
        "omitted_redundant_casual_blocks": ordinary_casual,
        "internal_cognition_preserved": True,
        "model_facing_projection_compacted": True,
        "content_free_diagnostics": True,
        **AUTHORITY_FLAGS,
    }
    diagnostics["projection_digest"] = _digest({k: v for k, v in diagnostics.items() if k != "projection_digest"})
    return prompt, diagnostics


def generation_token_budget(message: str, configured_max_tokens: int, *, relevance: TurnRelevance | None = None) -> int:
    """Choose a bounded output ceiling without increasing the configured maximum."""
    configured = max(1, int(configured_max_tokens))
    rel = relevance or classify_turn_relevance(message)
    if rel.social_only:
        target = 96
    elif rel.action_relevant:
        target = 192
    elif rel.detailed_response:
        target = configured
    elif rel.planning_relevant:
        target = 320
    elif len(str(message or "")) < 180:
        target = 192
    else:
        target = 256
    return max(32, min(configured, target))


def trusted_action_acknowledgement(action_projection: Mapping[str, Any] | None) -> str:
    """Immediate deterministic UI feedback for guarded action turns."""
    capability = str(((action_projection or {}).get("grounding") or {}).get("capability_id") or "the requested action")
    capability = capability.replace("_", " ").replace("-", " ").strip() or "the requested action"
    return f"Preparing a supervised proposal for {capability}. Nothing has executed or been approved yet."


def provider_metrics_public(metrics: Mapping[str, Any] | None) -> dict[str, int | float | bool | None]:
    allowed = (
        "load_duration_ns", "prompt_eval_count", "prompt_eval_duration_ns",
        "eval_count", "eval_duration_ns", "total_duration_ns",
    )
    result: dict[str, int | float | bool | None] = {}
    raw = metrics or {}
    for key in allowed:
        value = raw.get(key)
        if isinstance(value, bool):
            result[key] = value
        elif isinstance(value, (int, float)):
            result[key] = value
    eval_count = result.get("eval_count")
    eval_duration = result.get("eval_duration_ns")
    if isinstance(eval_count, (int, float)) and isinstance(eval_duration, (int, float)) and eval_duration > 0:
        result["generation_tokens_per_second"] = round(float(eval_count) / (float(eval_duration) / 1_000_000_000.0), 3)
    result["content_free"] = True
    return result


__all__ = [
    "CONTRACT_VERSION", "AUTHORITY_FLAGS", "TurnRelevance", "classify_turn_relevance",
    "build_compact_cognitive_projection", "generation_token_budget",
    "trusted_action_acknowledgement", "provider_metrics_public",
]
