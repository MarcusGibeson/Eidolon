from __future__ import annotations

import copy

from conscious_agent.goal_and_planning_alpha_runtime import (
    build_goal_and_planning_alpha_handoff,
    build_goal_and_planning_alpha_projection,
    validate_prior_goal_and_planning_alpha_receipts,
    verify_goal_and_planning_alpha_handoff,
    verify_goal_and_planning_alpha_projection,
)
from conscious_agent.hierarchical_planning_runtime import (
    build_hierarchical_planning_projection,
    build_hierarchical_planning_review_projection,
    build_hierarchical_planning_reliability,
)
from conscious_agent.internally_generated_goal_runtime import (
    build_internally_generated_goal_candidate,
    build_internally_generated_goal_candidate_review_projection,
    build_internally_generated_goal_candidate_reliability,
)
from conscious_agent.plan_simulation_runtime import (
    build_plan_simulation_projection,
    build_plan_simulation_review_projection,
    build_plan_simulation_reliability,
)
from conscious_agent.persistent_follow_through_runtime import (
    build_persistent_follow_through_projection,
    build_persistent_follow_through_review_projection,
    build_persistent_follow_through_reliability,
)
from test_v1170_0_2_internally_generated_goal_candidate_foundations import _goal


def chain(prior_alpha=(), message="The Eidolon tests are failing repeatedly."):
    goal = _goal(message)
    goal_review = build_internally_generated_goal_candidate_review_projection(goal)
    goal_reliability = build_internally_generated_goal_candidate_reliability(goal, goal_review)
    planning = build_hierarchical_planning_projection(goal, goal_reliability)
    planning_review = build_hierarchical_planning_review_projection(planning)
    planning_reliability = build_hierarchical_planning_reliability(planning, planning_review)
    simulation = build_plan_simulation_projection(planning, planning_reliability["report"])
    simulation_review = build_plan_simulation_review_projection(simulation)
    simulation_reliability = build_plan_simulation_reliability(simulation, simulation_review)
    follow = build_persistent_follow_through_projection(
        simulation, simulation_review, simulation_reliability
    )
    follow_review = build_persistent_follow_through_review_projection(follow)
    follow_reliability = build_persistent_follow_through_reliability(follow, follow_review)
    alpha = build_goal_and_planning_alpha_projection(
        goal,
        goal_reliability,
        planning,
        planning_review,
        planning_reliability,
        simulation,
        simulation_review,
        simulation_reliability,
        follow,
        follow_review,
        follow_reliability,
        prior_goal_planning_alpha_receipts=prior_alpha,
    )
    return {
        "goal": goal,
        "goal_reliability": goal_reliability,
        "planning": planning,
        "planning_review": planning_review,
        "planning_reliability": planning_reliability,
        "simulation": simulation,
        "simulation_review": simulation_review,
        "simulation_reliability": simulation_reliability,
        "follow": follow,
        "follow_review": follow_review,
        "follow_reliability": follow_reliability,
        "alpha": alpha,
    }


def test_1174_0_consolidates_four_existing_stages_without_parallel_architecture():
    alpha = chain()["alpha"]
    assert verify_goal_and_planning_alpha_projection(alpha)
    assert alpha["state"]["stage_set"] == [
        "goal_candidate", "hierarchical_planning", "plan_simulation", "persistent_follow_through"
    ]
    assert alpha["state"]["available_stage_count"] == 4
    assert alpha["state"]["coherent_stage_count"] == 4


def test_1174_0_normal_request_is_clean_no_candidate_not_recovery():
    alpha = chain(message="Explain the current memory checkpoint.")["alpha"]
    assert verify_goal_and_planning_alpha_projection(alpha)
    assert alpha["policy"]["policy_recovered"] is False
    assert alpha["state"]["alpha_posture"] == "no_goal_and_planning_candidate"
    assert alpha["state"]["available_stage_count"] == 0


def test_1174_0_exposes_only_structural_counts_categories_and_digests():
    alpha = chain()["alpha"]
    text = repr(alpha).lower()
    for forbidden in (
        "the eidolon tests are failing", "goal_text", "plan_text", "alternative_text",
        "conversation_text", "provider_payload", "private_reasoning", "prompt_envelope",
    ):
        assert forbidden not in text
    assert alpha["state"]["milestone_count"] == 3
    assert alpha["state"]["alternative_count"] == 3
    assert alpha["state"]["risk_count"] == 3


def test_1174_1_stage_availability_mismatch_fails_closed_without_residue():
    parts = chain()
    broken = copy.deepcopy(parts["follow_reliability"])
    broken["report"]["follow_through_available"] = False
    alpha = build_goal_and_planning_alpha_projection(
        parts["goal"], parts["goal_reliability"],
        parts["planning"], parts["planning_review"], parts["planning_reliability"],
        parts["simulation"], parts["simulation_review"], parts["simulation_reliability"],
        parts["follow"], parts["follow_review"], broken,
    )
    assert alpha["policy"]["policy_recovered"] is True
    assert alpha["state"]["available_stage_count"] == 0
    assert alpha["state"]["milestone_count"] == 0


def test_1174_1_missing_operator_constraint_fails_closed():
    parts = chain()
    alpha = build_goal_and_planning_alpha_projection(
        parts["goal"], parts["goal_reliability"],
        parts["planning"], parts["planning_review"], parts["planning_reliability"],
        parts["simulation"], parts["simulation_review"], parts["simulation_reliability"],
        parts["follow"], parts["follow_review"], parts["follow_reliability"],
        protected_operator_constraints=("literal_current_request_precedence",),
    )
    assert alpha["policy"]["policy_recovered"] is True
    assert alpha["diagnostics"]["alpha_available"] is False


def test_1174_1_alpha_handoff_requires_provider_and_memory_commit():
    alpha = chain()["alpha"]
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=False
    )
    assert verify_goal_and_planning_alpha_handoff(handoff)
    assert handoff["eligible_for_continuity"] is False


def test_1174_1_verified_handoff_resumes_only_structural_alpha_continuity():
    alpha = chain()["alpha"]
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True
    )
    resumed = chain([{"goal_and_planning_alpha_handoff": handoff}])["alpha"]
    assert resumed["state"]["continuity_disposition"] == "verified_alpha_resume"
    assert resumed["evidence"]["verified_receipt_count"] == 1


def test_1174_1_replay_does_not_amplify_alpha_continuity():
    alpha = chain()["alpha"]
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True
    )
    state = validate_prior_goal_and_planning_alpha_receipts([
        {"goal_and_planning_alpha_handoff": handoff},
        {"goal_and_planning_alpha_handoff": handoff},
    ])
    assert state["verified_receipt_count"] == 1
    assert state["replayed_receipt_count"] == 1


def test_1174_1_tampered_receipt_fails_closed():
    alpha = chain()["alpha"]
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True
    )
    handoff["available_stage_count"] = 3
    recovered = chain([{"goal_and_planning_alpha_handoff": handoff}])["alpha"]
    assert recovered["policy"]["policy_recovered"] is True
    assert recovered["state"]["available_stage_count"] == 0


def test_1174_1_receipt_flood_fails_closed():
    alpha = chain()["alpha"]
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True
    )
    recovered = chain([{"goal_and_planning_alpha_handoff": handoff}] * 65)["alpha"]
    assert recovered["evidence"]["receipt_budget_exceeded"] is True
    assert recovered["diagnostics"]["alpha_available"] is False


def test_1174_2_all_authority_remains_denied():
    alpha = chain()["alpha"]
    for key in (
        "goal_activation_permitted", "plan_activation_permitted", "plan_persistence_permitted",
        "alternative_selection_permitted", "scheduling_permitted", "tool_routing_permitted",
        "action_execution_permitted", "source_editing_permitted", "autonomous_work_permitted",
    ):
        assert alpha["policy"][key] is False
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True
    )
    for key in (
        "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
        "schedule_created", "tool_routed", "action_executed", "source_edited",
        "autonomous_work_started",
    ):
        assert handoff[key] is False


def test_1174_2_streaming_and_non_streaming_share_alpha_projection():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_goal_and_planning_alpha_projection(") == 2
    assert source.count('result.cognitive_context["goal_and_planning_alpha_state"]') == 2
    assert source.count('goal_and_planning_alpha_projection["prompt_section"]') == 2
    assert source.count('result.cognitive_context["goal_and_planning_alpha_handoff"]') == 2


def test_1174_2_no_tool_routing_execution_or_v1175_surface_added():
    source = open("conscious_agent/goal_and_planning_alpha_runtime.py", encoding="utf-8").read().lower()
    assert "tool_intent" not in source
    assert "execute_plan(" not in source
    assert "route_tool(" not in source
    assert "natural-language action" not in source
