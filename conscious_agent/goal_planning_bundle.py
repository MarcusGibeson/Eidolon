from __future__ import annotations

"""Lazy goal/planning bundle used by v1253 critical-path deferral.

All historical goal/planning builders remain authoritative for their advisory
records.  This module merely groups their calls behind one lazy import boundary
so ordinary conversation need not import or execute the entire planning stack
before provider contact.
"""

import hashlib
import json
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1253.0"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _imports() -> dict[str, Any]:
    from internally_generated_goal_runtime import (
        build_internally_generated_goal_candidate,
        build_internally_generated_goal_candidate_review_handoff,
        build_internally_generated_goal_candidate_review_projection,
        build_internally_generated_goal_candidate_reliability,
    )
    from hierarchical_planning_runtime import (
        build_hierarchical_planning_projection,
        build_hierarchical_planning_review_handoff,
        build_hierarchical_planning_review_projection,
        build_hierarchical_planning_reliability,
    )
    from plan_simulation_runtime import (
        build_plan_simulation_projection,
        build_plan_simulation_review_handoff,
        build_plan_simulation_review_projection,
        build_plan_simulation_reliability,
    )
    from persistent_follow_through_runtime import (
        build_persistent_follow_through_projection,
        build_persistent_follow_through_handoff,
        build_persistent_follow_through_review_projection,
        build_persistent_follow_through_reliability,
    )
    from goal_and_planning_alpha_runtime import (
        build_goal_and_planning_alpha_projection,
        build_goal_and_planning_alpha_handoff,
        build_goal_and_planning_alpha_review_projection,
        build_goal_and_planning_alpha_reliability,
    )
    return locals()


def build_goal_planning_bundle(
    message: str,
    memory_learning_alpha_projection: Mapping[str, Any],
    *,
    session_history: Sequence[Mapping[str, Any]] = (),
    phase: str = "pre_provider",
) -> dict[str, Any]:
    f = _imports()
    history = list(session_history)
    goal = f["build_internally_generated_goal_candidate"](
        message, memory_learning_alpha_projection,
        observation_rows=history,
        protected_operator_constraints=(
            "literal_current_request_precedence", "no_goal_activation",
            "no_plan_creation", "no_tool_routing", "no_action_execution",
            "operator_review_required",
        ),
        prior_goal_candidate_receipts=history,
    )
    goal_review = f["build_internally_generated_goal_candidate_review_projection"](
        goal, prior_goal_candidate_receipts=history,
    )
    goal_reliability = f["build_internally_generated_goal_candidate_reliability"](
        goal, goal_review, prior_goal_candidate_receipts=history,
    )
    planning = f["build_hierarchical_planning_projection"](
        goal, goal_reliability,
        prior_planning_receipts=history,
        protected_operator_constraints=(
            "literal_current_request_precedence", "no_goal_activation", "no_plan_activation",
            "no_tool_routing", "no_action_execution", "operator_review_required",
        ),
    )
    planning_review = f["build_hierarchical_planning_review_projection"](planning)
    planning_reliability = f["build_hierarchical_planning_reliability"](
        planning, planning_review, prior_planning_receipts=history,
    )
    simulation = f["build_plan_simulation_projection"](
        planning, planning_reliability["report"],
        prior_simulation_receipts=history,
        protected_operator_constraints=(
            "literal_current_request_precedence", "no_plan_activation", "no_alternative_selection",
            "no_tool_routing", "no_action_execution", "operator_review_required",
        ),
    )
    simulation_review = f["build_plan_simulation_review_projection"](simulation)
    simulation_reliability = f["build_plan_simulation_reliability"](
        simulation, simulation_review, prior_simulation_receipts=history,
    )
    follow = f["build_persistent_follow_through_projection"](
        simulation, simulation_review, simulation_reliability,
        prior_follow_through_receipts=history,
        protected_operator_constraints=(
            "literal_current_request_precedence", "no_plan_activation", "no_plan_persistence",
            "no_scheduling", "no_tool_routing", "no_action_execution", "operator_review_required",
        ),
    )
    follow_review = f["build_persistent_follow_through_review_projection"](follow)
    follow_reliability = f["build_persistent_follow_through_reliability"](
        follow, follow_review, prior_follow_through_receipts=history,
    )
    alpha = f["build_goal_and_planning_alpha_projection"](
        goal, goal_reliability,
        planning, planning_review, planning_reliability,
        simulation, simulation_review, simulation_reliability,
        follow, follow_review, follow_reliability,
        prior_goal_planning_alpha_receipts=history,
    )
    alpha_review = f["build_goal_and_planning_alpha_review_projection"](alpha)
    alpha_reliability = f["build_goal_and_planning_alpha_reliability"](
        alpha, alpha_review, prior_goal_planning_alpha_receipts=history,
    )
    bundle = {
        "goal_candidate_projection": goal,
        "goal_candidate_review_projection": goal_review,
        "goal_candidate_reliability": goal_reliability,
        "hierarchical_planning_projection": planning,
        "hierarchical_planning_review_projection": planning_review,
        "hierarchical_planning_reliability": planning_reliability,
        "plan_simulation_projection": simulation,
        "plan_simulation_review_projection": simulation_review,
        "plan_simulation_reliability": simulation_reliability,
        "persistent_follow_through_projection": follow,
        "persistent_follow_through_review_projection": follow_review,
        "persistent_follow_through_reliability": follow_reliability,
        "goal_and_planning_alpha_projection": alpha,
        "goal_and_planning_alpha_review_projection": alpha_review,
        "goal_and_planning_alpha_reliability": alpha_reliability,
        "phase": phase,
        "deferred_stub": False,
    }
    bundle["bundle_digest"] = _digest({k: v for k, v in bundle.items() if k != "bundle_digest"})
    return bundle


def deferred_goal_planning_stub() -> dict[str, Any]:
    policy = {
        "prompt_section": "",
        "state": "deferred_until_after_provider",
        "advisory_only": True,
        "operator_review_required": True,
        "action_execution_authorized": False,
    }
    projection = {
        "policy": dict(policy), "evidence": {"deferred": True},
        "diagnostics": {"deferred": True, "reason": "not_required_for_current_response"},
        "prompt_section": "",
    }
    bundle = {
        "goal_candidate_projection": dict(projection),
        "goal_candidate_review_projection": {"state": {"deferred": True}, "review_packet": {"deferred": True}},
        "goal_candidate_reliability": {"deferred": True, "report": {"deferred": True}},
        "hierarchical_planning_projection": {**projection, "hierarchy": {"deferred": True}},
        "hierarchical_planning_review_projection": {"state": {"deferred": True}, "review_packet": {"deferred": True}},
        "hierarchical_planning_reliability": {"deferred": True, "report": {"deferred": True}},
        "plan_simulation_projection": {**projection, "comparison": {"deferred": True}},
        "plan_simulation_review_projection": {"state": {"deferred": True}, "review_packet": {"deferred": True}},
        "plan_simulation_reliability": {"deferred": True, "report": {"deferred": True}},
        "persistent_follow_through_projection": {**projection, "continuity": {"deferred": True}},
        "persistent_follow_through_review_projection": {"state": {"deferred": True}, "review_packet": {"deferred": True}},
        "persistent_follow_through_reliability": {"deferred": True, "report": {"deferred": True}},
        "goal_and_planning_alpha_projection": {**projection, "state": {"deferred": True}},
        "goal_and_planning_alpha_review_projection": {"state": {"deferred": True}, "review_packet": {"deferred": True}},
        "goal_and_planning_alpha_reliability": {"deferred": True, "report": {"deferred": True}},
        "phase": "deferred_stub",
        "deferred_stub": True,
    }
    bundle["bundle_digest"] = _digest({k: v for k, v in bundle.items() if k != "bundle_digest"})
    return bundle


def unpack_goal_planning_bundle(bundle: Mapping[str, Any]) -> tuple[Any, ...]:
    keys = (
        "goal_candidate_projection", "goal_candidate_review_projection", "goal_candidate_reliability",
        "hierarchical_planning_projection", "hierarchical_planning_review_projection", "hierarchical_planning_reliability",
        "plan_simulation_projection", "plan_simulation_review_projection", "plan_simulation_reliability",
        "persistent_follow_through_projection", "persistent_follow_through_review_projection", "persistent_follow_through_reliability",
        "goal_and_planning_alpha_projection", "goal_and_planning_alpha_review_projection", "goal_and_planning_alpha_reliability",
    )
    return tuple(bundle[key] for key in keys)


def apply_goal_planning_context(context: dict[str, Any], bundle: Mapping[str, Any]) -> None:
    (
        goal, goal_review, goal_rel, planning, planning_review, planning_rel,
        simulation, simulation_review, simulation_rel, follow, follow_review, follow_rel,
        alpha, alpha_review, alpha_rel,
    ) = unpack_goal_planning_bundle(bundle)
    context["internally_generated_goal_candidate_policy"] = dict(goal.get("policy") or {})
    context["internally_generated_goal_candidate_evidence"] = dict(goal.get("evidence") or {})
    context["internally_generated_goal_candidate_runtime_diagnostics"] = dict(goal.get("diagnostics") or {})
    context["internally_generated_goal_candidate_review_state"] = dict(goal_review.get("state") or {})
    context["internally_generated_goal_candidate_review_packet"] = dict(goal_review.get("review_packet") or {})
    context["internally_generated_goal_candidate_reliability"] = dict(goal_rel)
    context["hierarchical_planning_policy"] = dict(planning.get("policy") or {})
    context["hierarchical_planning_evidence"] = dict(planning.get("evidence") or {})
    context["hierarchical_planning_hierarchy"] = dict(planning.get("hierarchy") or {})
    context["hierarchical_planning_runtime_diagnostics"] = dict(planning.get("diagnostics") or {})
    context["hierarchical_planning_review_state"] = dict(planning_review.get("state") or {})
    context["hierarchical_planning_review_packet"] = dict(planning_review.get("review_packet") or {})
    context["hierarchical_planning_reliability"] = dict(planning_rel.get("report") or planning_rel)
    context["plan_simulation_policy"] = dict(simulation.get("policy") or {})
    context["plan_simulation_evidence"] = dict(simulation.get("evidence") or {})
    context["plan_simulation_comparison"] = dict(simulation.get("comparison") or {})
    context["plan_simulation_runtime_diagnostics"] = dict(simulation.get("diagnostics") or {})
    context["plan_simulation_review_state"] = dict(simulation_review.get("state") or {})
    context["plan_simulation_review_packet"] = dict(simulation_review.get("review_packet") or {})
    context["plan_simulation_reliability"] = dict(simulation_rel.get("report") or simulation_rel)
    context["persistent_follow_through_policy"] = dict(follow.get("policy") or {})
    context["persistent_follow_through_evidence"] = dict(follow.get("evidence") or {})
    context["persistent_follow_through_continuity"] = dict(follow.get("continuity") or {})
    context["persistent_follow_through_runtime_diagnostics"] = dict(follow.get("diagnostics") or {})
    context["persistent_follow_through_review_state"] = dict(follow_review.get("state") or {})
    context["persistent_follow_through_review_packet"] = dict(follow_review.get("review_packet") or {})
    context["persistent_follow_through_reliability"] = dict(follow_rel.get("report") or follow_rel)
    context["goal_and_planning_alpha_policy"] = dict(alpha.get("policy") or {})
    context["goal_and_planning_alpha_evidence"] = dict(alpha.get("evidence") or {})
    context["goal_and_planning_alpha_state"] = dict(alpha.get("state") or {})
    context["goal_and_planning_alpha_runtime_diagnostics"] = dict(alpha.get("diagnostics") or {})
    context["goal_and_planning_alpha_review_state"] = dict(alpha_review.get("state") or {})
    context["goal_and_planning_alpha_review_packet"] = dict(alpha_review.get("review_packet") or {})
    context["goal_and_planning_alpha_reliability"] = dict(alpha_rel.get("report") or alpha_rel)
    context["goal_planning_critical_path"] = {
        "phase": str(bundle.get("phase") or ""),
        "deferred_stub": bool(bundle.get("deferred_stub")),
        "bundle_digest": str(bundle.get("bundle_digest") or ""),
        "authority_granted": False,
    }


def apply_goal_planning_handoffs(context: dict[str, Any], bundle: Mapping[str, Any]) -> None:
    f = _imports()
    (
        goal, _, _, planning, _, _, simulation, _, _, follow, _, _, alpha, _, _,
    ) = unpack_goal_planning_bundle(bundle)
    context["internally_generated_goal_candidate_review_handoff"] = f["build_internally_generated_goal_candidate_review_handoff"](
        goal, provider_completed=True, assistant_memory_committed=True,
    )
    context["hierarchical_planning_review_handoff"] = f["build_hierarchical_planning_review_handoff"](
        planning, provider_completed=True, assistant_memory_committed=True,
    )
    context["plan_simulation_review_handoff"] = f["build_plan_simulation_review_handoff"](
        simulation, provider_completed=True, assistant_memory_committed=True,
    )
    context["persistent_follow_through_handoff"] = f["build_persistent_follow_through_handoff"](
        follow, provider_completed=True, assistant_memory_committed=True,
    )
    context["goal_and_planning_alpha_handoff"] = f["build_goal_and_planning_alpha_handoff"](
        alpha, provider_completed=True, assistant_memory_committed=True,
    )


__all__ = [
    "CONTRACT_VERSION", "build_goal_planning_bundle", "deferred_goal_planning_stub",
    "unpack_goal_planning_bundle", "apply_goal_planning_context", "apply_goal_planning_handoffs",
]
