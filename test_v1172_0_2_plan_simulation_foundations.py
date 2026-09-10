from __future__ import annotations

import copy

from conscious_agent.plan_simulation_runtime import (
    build_plan_simulation_projection,
    build_plan_simulation_review_handoff,
    validate_prior_plan_simulation_receipts,
    verify_plan_simulation_review_handoff,
)


def planning_inputs():
    hierarchy = {
        "plan_candidate_available": True, "milestone_count": 3, "dependency_count": 2,
        "stopping_condition_count": 3,
    }
    projection = {
        "hierarchy": hierarchy,
        "policy": {"operator_review_required": True, "plan_activation_permitted": False, "action_execution_permitted": False},
    }
    reliability = {
        "reliability_posture": "hierarchical_planning_context_reliable",
        "ordinary_conversation_ready": True,
        "plan_candidate_available": True,
    }
    return projection, reliability


def test_verified_plan_produces_three_review_only_alternatives():
    p, r = planning_inputs()
    out = build_plan_simulation_projection(p, r)
    assert out["comparison"]["alternative_count"] == 3
    assert out["comparison"]["preferred_alternative_selected"] is False
    assert out["policy"]["alternative_selection_permitted"] is False


def test_structural_risks_are_bounded_and_content_free():
    p, r = planning_inputs()
    out = build_plan_simulation_projection(p, r)
    assert set(out["comparison"]["risk_categories"]) == {"insufficient_evidence", "dependency_failure", "verification_gap"}
    text = repr(out).lower()
    for forbidden in ("conversation_text", "prompt_payload", "private_reasoning", "plan_text"):
        assert forbidden not in text


def test_unreliable_plan_fails_closed():
    p, r = planning_inputs(); r["ordinary_conversation_ready"] = False
    out = build_plan_simulation_projection(p, r)
    assert out["comparison"]["alternative_count"] == 0
    assert out["policy"]["policy_recovered"] is True


def test_missing_constraint_fails_closed():
    p, r = planning_inputs()
    out = build_plan_simulation_projection(p, r, protected_operator_constraints=("literal_current_request_precedence",))
    assert out["comparison"]["alternative_count"] == 0


def test_handoff_requires_provider_and_memory_commit():
    p, r = planning_inputs(); out = build_plan_simulation_projection(p, r)
    handoff = build_plan_simulation_review_handoff(out, provider_completed=True, assistant_memory_committed=False)
    assert verify_plan_simulation_review_handoff(handoff)
    assert handoff["eligible_for_review_continuity"] is False


def test_verified_handoff_round_trip():
    p, r = planning_inputs(); out = build_plan_simulation_projection(p, r)
    handoff = build_plan_simulation_review_handoff(out, provider_completed=True, assistant_memory_committed=True)
    assert verify_plan_simulation_review_handoff(handoff)
    assert handoff["eligible_for_review_continuity"] is True


def test_tampered_handoff_recovers():
    p, r = planning_inputs(); out = build_plan_simulation_projection(p, r)
    handoff = build_plan_simulation_review_handoff(out, provider_completed=True, assistant_memory_committed=True)
    bad = copy.deepcopy(handoff); bad["alternative_count"] = 99
    state = validate_prior_plan_simulation_receipts([{"plan_simulation_review_handoff": bad}])
    assert state["recovered"] is True and state["verified_receipt_count"] == 0


def test_replay_does_not_amplify_continuity():
    p, r = planning_inputs(); out = build_plan_simulation_projection(p, r)
    handoff = build_plan_simulation_review_handoff(out, provider_completed=True, assistant_memory_committed=True)
    state = validate_prior_plan_simulation_receipts([
        {"plan_simulation_review_handoff": handoff}, {"plan_simulation_review_handoff": handoff}
    ])
    assert state["verified_receipt_count"] == 1 and state["replayed_receipt_count"] == 1


def test_receipt_flood_fails_closed():
    p, r = planning_inputs(); out = build_plan_simulation_projection(p, r)
    handoff = build_plan_simulation_review_handoff(out, provider_completed=True, assistant_memory_committed=True)
    rows = [{"plan_simulation_review_handoff": handoff} for _ in range(65)]
    state = validate_prior_plan_simulation_receipts(rows)
    assert state["receipt_budget_exceeded"] is True and state["recovered"] is True


def test_no_authority_surfaces():
    p, r = planning_inputs(); out = build_plan_simulation_projection(p, r)
    policy = out["policy"]
    assert policy["authority"] == "none"
    assert all(policy[k] is False for k in (
        "alternative_selection_permitted", "plan_activation_permitted", "plan_persistence_permitted",
        "scheduling_permitted", "tool_routing_permitted", "action_execution_permitted",
        "source_editing_permitted", "autonomous_work_permitted",
    ))
