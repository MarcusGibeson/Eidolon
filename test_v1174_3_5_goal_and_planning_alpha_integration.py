from __future__ import annotations

import copy
import hashlib
import json

from conscious_agent.goal_and_planning_alpha_runtime import (
    build_goal_and_planning_alpha_handoff,
    build_goal_and_planning_alpha_review_projection,
    verify_goal_and_planning_alpha_review_packet,
    verify_goal_and_planning_alpha_review_state,
)
from test_v1174_0_2_goal_and_planning_alpha_foundations import chain


def _review(prior=(), message="The Eidolon tests are failing repeatedly."):
    alpha = chain(prior, message=message)["alpha"]
    return alpha, build_goal_and_planning_alpha_review_projection(alpha)


def test_1174_3_current_alpha_is_emerging_review():
    alpha, review = _review()
    assert alpha["diagnostics"]["alpha_available"] is True
    assert verify_goal_and_planning_alpha_review_state(review["state"])
    assert verify_goal_and_planning_alpha_review_packet(review["review_packet"])
    assert review["state"]["review_disposition"] == "emerging_goal_and_planning_alpha_review"
    assert review["state"]["alpha_stability_band"] == "current_turn_only"


def test_1174_3_verified_alpha_handoff_stabilizes_review():
    alpha, _ = _review()
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True
    )
    _, review = _review([{"goal_and_planning_alpha_handoff": handoff}])
    assert review["state"]["review_disposition"] == "stable_goal_and_planning_alpha_review"
    assert review["state"]["verified_prior_receipt_count"] == 1
    assert review["review_packet"]["follow_through_posture"] == "verified_review_continuity"


def test_1174_3_replay_does_not_amplify_review_stability():
    alpha, _ = _review()
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True
    )
    _, review = _review([
        {"goal_and_planning_alpha_handoff": handoff},
        {"goal_and_planning_alpha_handoff": handoff},
    ])
    assert review["state"]["verified_prior_receipt_count"] == 1
    assert review["state"]["replayed_prior_receipt_count"] == 1


def test_1174_3_no_candidate_is_clean_no_review():
    _, review = _review(message="Explain the current memory checkpoint.")
    assert review["state"]["review_disposition"] == "no_goal_and_planning_alpha_review"
    assert review["state"]["alpha_available"] is False
    assert review["review_packet"]["alpha_state_digest"] == ""


def test_1174_3_tampered_projection_fails_closed_without_residue():
    alpha, _ = _review()
    tampered = copy.deepcopy(alpha)
    tampered["state"]["milestone_count"] = 2
    review = build_goal_and_planning_alpha_review_projection(tampered)
    assert review["state"]["review_disposition"] == "literal_current_request_only_recovery"
    assert review["state"]["available_stage_count"] == 0
    assert review["state"]["milestone_count"] == 0
    assert review["review_packet"]["alpha_state_digest"] == ""


def test_1174_4_operator_packet_is_bounded_content_free_and_authority_free():
    _, review = _review()
    packet = review["review_packet"]
    assert packet["stage_set"] == [
        "goal_candidate", "hierarchical_planning", "plan_simulation", "persistent_follow_through"
    ]
    assert packet["stage_coherence_band"] == "four_stage_coherent"
    assert packet["planning_readiness_band"] == "bounded_review_ready"
    assert packet["simulation_risk_posture"] == "bounded_risks_for_operator_comparison"
    for key in (
        "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
        "schedule_created", "tool_routed", "action_executed", "source_edited",
        "autonomous_work_started",
    ):
        assert packet[key] is False
    text = repr(packet).lower()
    for forbidden in ("the eidolon tests are failing", "goal_text", "plan_text", "private_reasoning"):
        assert forbidden not in text


def test_1174_4_unknown_digest_valid_packet_field_is_rejected():
    _, review = _review()
    packet = copy.deepcopy(review["review_packet"])
    packet.pop("review_packet_digest")
    packet["approved"] = True
    packet["review_packet_digest"] = hashlib.sha256(
        json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert verify_goal_and_planning_alpha_review_packet(packet) is False


def test_1174_5_streaming_and_non_streaming_share_alpha_review_projection():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_goal_and_planning_alpha_review_projection(") == 2
    assert source.count('goal_and_planning_alpha_review_projection["prompt_section"]') == 2
    assert source.count('result.cognitive_context["goal_and_planning_alpha_review_state"]') == 2
    assert source.count('result.cognitive_context["goal_and_planning_alpha_review_packet"]') == 2


def test_1174_5_no_v1175_routing_or_execution_surface_added():
    source = open("conscious_agent/goal_and_planning_alpha_runtime.py", encoding="utf-8").read().lower()
    assert "tool_intent" not in source
    assert "route_tool(" not in source
    assert "execute_plan(" not in source
