from __future__ import annotations

import copy

from conscious_agent.persistent_follow_through_runtime import (
    build_persistent_follow_through_handoff,
    build_persistent_follow_through_projection,
    validate_prior_follow_through_receipts,
    verify_persistent_follow_through_handoff,
)


def inputs():
    simulation = {
        "comparison": {"alternative_count": 3, "preferred_alternative_selected": False},
        "policy": {"operator_review_required": True, "alternative_selection_permitted": False},
    }
    review = {"review_packet": {
        "operator_approval_required": True, "alternative_selected": False,
    }}
    reliability = {"report": {
        "reliability_posture": "plan_simulation_context_reliable",
        "ordinary_conversation_ready": True, "simulation_available": True,
    }}
    return simulation, review, reliability


def build(**kwargs):
    return build_persistent_follow_through_projection(*inputs(), **kwargs)


def test_verified_simulation_produces_review_only_follow_through():
    out = build()
    assert out["continuity"]["follow_through_available"] is True
    assert out["continuity"]["milestone_count"] == 3
    assert out["policy"]["plan_persistence_permitted"] is False


def test_foundation_supports_interruptions_restarts_and_priority_changes():
    out = build()
    assert out["evidence"]["interruption_recovery_supported"] is True
    assert out["evidence"]["restart_resume_supported"] is True
    assert out["evidence"]["priority_change_reconciliation_supported"] is True
    assert out["continuity"]["priority_disposition"] == "current_operator_request_controls"


def test_unreliable_simulation_fails_closed():
    s, r, reliability = inputs(); reliability["report"]["ordinary_conversation_ready"] = False
    out = build_persistent_follow_through_projection(s, r, reliability)
    assert out["continuity"]["follow_through_available"] is False
    assert out["policy"]["policy_recovered"] is True


def test_missing_constraint_fails_closed():
    out = build(protected_operator_constraints=("literal_current_request_precedence",))
    assert out["continuity"]["follow_through_available"] is False


def test_handoff_requires_provider_and_memory_commit():
    handoff = build_persistent_follow_through_handoff(build(), provider_completed=True, assistant_memory_committed=False)
    assert verify_persistent_follow_through_handoff(handoff)
    assert handoff["eligible_for_continuity"] is False


def test_verified_handoff_resumes_structural_continuity():
    handoff = build_persistent_follow_through_handoff(build(), provider_completed=True, assistant_memory_committed=True)
    out = build(prior_follow_through_receipts=[{"persistent_follow_through_handoff": handoff}])
    assert out["continuity"]["continuity_disposition"] == "verified_resume_review"
    assert out["evidence"]["verified_receipt_count"] == 1


def test_replay_does_not_amplify_continuity():
    handoff = build_persistent_follow_through_handoff(build(), provider_completed=True, assistant_memory_committed=True)
    state = validate_prior_follow_through_receipts([
        {"persistent_follow_through_handoff": handoff}, {"persistent_follow_through_handoff": handoff},
    ])
    assert state["verified_receipt_count"] == 1
    assert state["replayed_receipt_count"] == 1


def test_tampered_receipt_recovers_without_residue():
    handoff = build_persistent_follow_through_handoff(build(), provider_completed=True, assistant_memory_committed=True)
    bad = copy.deepcopy(handoff); bad["milestone_count"] = 12
    out = build(prior_follow_through_receipts=[{"persistent_follow_through_handoff": bad}])
    assert out["policy"]["policy_recovered"] is True
    assert out["continuity"]["milestone_count"] == 0


def test_receipt_flood_fails_closed():
    handoff = build_persistent_follow_through_handoff(build(), provider_completed=True, assistant_memory_committed=True)
    rows = [{"persistent_follow_through_handoff": handoff} for _ in range(65)]
    out = build(prior_follow_through_receipts=rows)
    assert out["evidence"]["receipt_budget_exceeded"] is True
    assert out["continuity"]["follow_through_available"] is False


def test_digest_valid_authority_smuggling_is_rejected():
    handoff = build_persistent_follow_through_handoff(build(), provider_completed=True, assistant_memory_committed=True)
    handoff["approved"] = True
    assert verify_persistent_follow_through_handoff(handoff) is False


def test_content_free_and_no_execution_authority():
    out = build(); text = repr(out).lower()
    for forbidden in ("plan_text", "conversation_text", "provider_payload", "private_reasoning"):
        assert forbidden not in text
    assert all(out["policy"][key] is False for key in (
        "plan_activation_permitted", "plan_persistence_permitted", "scheduling_permitted",
        "tool_routing_permitted", "action_execution_permitted", "source_editing_permitted",
        "autonomous_work_permitted",
    ))


def test_streaming_and_non_streaming_share_follow_through_projection():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_persistent_follow_through_projection(") == 2
    assert source.count('result.cognitive_context["persistent_follow_through_policy"]') == 2
    assert source.count('result.cognitive_context["persistent_follow_through_continuity"]') == 2
    assert source.count('persistent_follow_through_projection["prompt_section"]') == 2
    assert source.count('result.cognitive_context["persistent_follow_through_handoff"]') == 2


def test_no_v1174_or_tool_execution_surfaces_added():
    source = open("conscious_agent/persistent_follow_through_runtime.py", encoding="utf-8").read().lower()
    assert "goal_and_planning_alpha_checkpoint" not in source
    assert "tool_intent" not in source
    assert "execute_plan(" not in source
    assert "schedule_plan(" not in source
