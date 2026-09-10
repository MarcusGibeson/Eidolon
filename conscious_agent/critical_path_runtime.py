from __future__ import annotations

"""v1253.0 critical-path classification for conversational response latency.

The classifier decides which advisory cognition must exist before provider
contact and which work may safely finish after generation.  It never executes
an action, grants approval, contacts a provider, mutates a project, or changes
canonical memory.  Deferred means *later in the same supervised turn* unless a
separately bounded internal-maintenance job is explicitly queued.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1253.0"
AUTHORITY_FLAGS = {
    "approval_granted": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "provider_contact_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class CriticalPathDecision:
    lane: str
    goal_planning_pre_provider: bool
    goal_planning_deferred: bool
    memory_retrieval_pre_provider: bool
    response_policy_pre_provider: bool
    action_routing_pre_provider: bool
    development_routing_pre_provider: bool
    deferred_job_kinds: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["deferred_job_kinds"] = list(self.deferred_job_kinds)
        row["critical_path_digest"] = _digest(row)
        row.update(AUTHORITY_FLAGS)
        return row


def build_critical_path_decision(
    message: str,
    *,
    relevance: Any,
    action_projection: Mapping[str, Any] | None = None,
    development_campaign: Mapping[str, Any] | None = None,
) -> CriticalPathDecision:
    """Classify advisory cognition by whether the current response depends on it.

    Planning is critical only when the relevance classifier says the user is
    planning/developing or the action router found an actionable request.  On
    ordinary/social turns it remains available, but it no longer blocks the
    provider's first token.
    """

    lane = str(getattr(relevance, "lane", "ordinary") or "ordinary")
    planning = bool(getattr(relevance, "planning_relevant", False))
    development = bool(getattr(relevance, "development_relevant", False)) or bool((development_campaign or {}).get("active"))
    action = bool(getattr(relevance, "action_relevant", False)) or bool(((action_projection or {}).get("intent") or {}).get("action_intent_present"))
    goal_planning_pre = bool(planning or development or action)
    deferred_jobs = ("projection_cache_prune", "persistent_index_health_sample")
    return CriticalPathDecision(
        lane=lane,
        goal_planning_pre_provider=goal_planning_pre,
        goal_planning_deferred=not goal_planning_pre,
        memory_retrieval_pre_provider=True,
        response_policy_pre_provider=True,
        action_routing_pre_provider=True,
        development_routing_pre_provider=True,
        deferred_job_kinds=deferred_jobs,
    )


def critical_path_public_receipt(decision: CriticalPathDecision, *, pre_provider_ms: int | None = None) -> dict[str, Any]:
    row = decision.to_dict()
    row.update({
        "contract_version": CONTRACT_VERSION,
        "pre_provider_ms": int(pre_provider_ms) if isinstance(pre_provider_ms, int) else None,
        "provider_contacted_by_classifier": False,
        "canonical_state_mutated_by_classifier": False,
        "content_free": True,
    })
    return row


__all__ = [
    "CONTRACT_VERSION", "AUTHORITY_FLAGS", "CriticalPathDecision",
    "build_critical_path_decision", "critical_path_public_receipt",
]
