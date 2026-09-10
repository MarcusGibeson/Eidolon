from __future__ import annotations

from copy import deepcopy

from conscious_agent.internally_generated_goal_runtime import (
    build_internally_generated_goal_candidate_review_handoff,
    build_internally_generated_goal_candidate_review_packet,
    build_internally_generated_goal_candidate_review_projection,
    build_internally_generated_goal_candidate_review_state,
    verify_internally_generated_goal_candidate_review_packet,
    verify_internally_generated_goal_candidate_review_state,
)
from test_v1170_0_2_internally_generated_goal_candidate_foundations import NOW, _goal


def _receipt(message: str):
    projection = _goal(message)
    receipt = build_internally_generated_goal_candidate_review_handoff(
        projection, provider_completed=True, assistant_memory_committed=True,
    )
    return projection, receipt


# v1170.3 deterministic review continuity and precedence

def test_1170_3_current_candidate_without_prior_receipt_is_emerging():
    projection = _goal("The Eidolon repository tests are failing again.")
    state = build_internally_generated_goal_candidate_review_state(projection, now=NOW)
    assert verify_internally_generated_goal_candidate_review_state(state)
    assert state["candidate_available"] is True
    assert state["stability_band"] == "emerging"
    assert state["continuity_disposition"] == "review_current_candidate"


def test_1170_3_verified_same_type_receipt_resumes_stable_review():
    projection, receipt = _receipt("The Eidolon repository tests are failing again.")
    current = _goal("The Eidolon runtime is still failing again.")
    state = build_internally_generated_goal_candidate_review_state(
        current, prior_goal_candidate_receipts=[receipt], now=NOW,
    )
    assert verify_internally_generated_goal_candidate_review_state(state)
    assert state["candidate_type"] == "reliability_improvement"
    assert state["stability_band"] == "stable"
    assert state["recurrence_band"] == "repeated"
    assert state["continuity_disposition"] == "resume_verified_same_type_review"


def test_1170_3_conflicting_prior_candidate_fails_closed():
    _, receipt = _receipt("Eidolon cannot inspect this capability yet.")
    current = _goal("The Eidolon tests are failing again.")
    state = build_internally_generated_goal_candidate_review_state(
        current, prior_goal_candidate_receipts=[receipt], now=NOW,
    )
    assert verify_internally_generated_goal_candidate_review_state(state)
    assert state["candidate_available"] is False
    assert state["review_posture"] == "literal_current_request_only_recovery"
    assert state["continuity_disposition"] == "discard_review_continuity"


def test_1170_3_replayed_receipts_do_not_amplify_stability_counts():
    _, receipt = _receipt("The Eidolon tests are failing again.")
    current = _goal("The Eidolon runtime is still failing again.")
    state = build_internally_generated_goal_candidate_review_state(
        current, prior_goal_candidate_receipts=[receipt] * 12, now=NOW,
    )
    assert state["verified_prior_receipt_count"] == 1
    assert state["replayed_prior_receipt_count"] == 11
    assert state["stability_band"] == "stable"


def test_1170_3_tampered_prior_receipt_discards_review_continuity():
    _, receipt = _receipt("The Eidolon tests are failing again.")
    bad = deepcopy(receipt)
    bad["candidate_type"] = "capability_improvement"
    current = _goal("The Eidolon tests are still failing again.")
    state = build_internally_generated_goal_candidate_review_state(
        current, prior_goal_candidate_receipts=[bad], now=NOW,
    )
    assert state["candidate_available"] is False
    assert state["review_posture"] == "literal_current_request_only_recovery"


# v1170.4 bounded operator-review packet

def test_1170_4_review_packet_is_content_free_and_review_only():
    projection = _goal("The Eidolon repository tests are failing again with PRIVATE_CANARY.")
    state = build_internally_generated_goal_candidate_review_state(projection, now=NOW)
    packet = build_internally_generated_goal_candidate_review_packet(projection, state)
    assert verify_internally_generated_goal_candidate_review_packet(packet)
    assert packet["review_disposition"] == "review_available"
    assert "PRIVATE_CANARY" not in str(packet)
    assert packet["operator_review_required"] is True
    assert packet["operator_approval_required"] is True
    assert packet["goal_activated"] is False
    assert packet["plan_created"] is False
    assert packet["tool_routed"] is False
    assert packet["action_executed"] is False


def test_1170_4_no_candidate_produces_no_review_packet():
    projection = _goal("Explain the current checkpoint.")
    state = build_internally_generated_goal_candidate_review_state(projection, now=NOW)
    packet = build_internally_generated_goal_candidate_review_packet(projection, state)
    assert verify_internally_generated_goal_candidate_review_packet(packet)
    assert packet["candidate_available"] is False
    assert packet["review_disposition"] == "no_review_available"
    assert packet["operator_review_required"] is False


def test_1170_4_tampered_state_cannot_expose_candidate_for_review():
    projection = _goal("The Eidolon tests are failing again.")
    state = build_internally_generated_goal_candidate_review_state(projection, now=NOW)
    bad = deepcopy(state)
    bad["goal_activation_permitted"] = True
    packet = build_internally_generated_goal_candidate_review_packet(projection, bad)
    assert verify_internally_generated_goal_candidate_review_packet(packet)
    assert packet["candidate_available"] is False
    assert packet["candidate_digest"] == ""


def test_1170_4_digest_valid_extra_field_is_rejected():
    projection = _goal("The Eidolon tests are failing again.")
    state = build_internally_generated_goal_candidate_review_state(projection, now=NOW)
    state["approved"] = True
    assert not verify_internally_generated_goal_candidate_review_state(state)


# v1170.5 shared prompt and structural integration

def test_1170_5_review_projection_materially_shapes_bounded_prompt():
    projection = _goal("The Eidolon tests are failing again.")
    review = build_internally_generated_goal_candidate_review_projection(projection, now=NOW)
    assert verify_internally_generated_goal_candidate_review_state(review["state"])
    assert verify_internally_generated_goal_candidate_review_packet(review["review_packet"])
    assert '<internally_generated_goal_review data_only="true" authority="none">' in review["prompt_section"]
    assert '"review_disposition":"review_available"' in review["prompt_section"]
    assert "The Eidolon tests are failing" not in review["prompt_section"]


def test_1170_5_recovery_prompt_contains_no_candidate_availability():
    projection = _goal("The Eidolon tests are failing again.")
    projection["policy"]["approval_granted"] = True
    review = build_internally_generated_goal_candidate_review_projection(projection, now=NOW)
    assert review["state"]["candidate_available"] is False
    assert review["review_packet"]["candidate_available"] is False
    assert '"goal_activated":false' in review["prompt_section"]
    assert '"plan_created":false' in review["prompt_section"]
    assert '"tool_routed":false' in review["prompt_section"]
    assert '"action_executed":false' in review["prompt_section"]


def test_1170_5_review_packet_rejects_forged_execution_authority():
    projection = _goal("The Eidolon tests are failing again.")
    review = build_internally_generated_goal_candidate_review_projection(projection, now=NOW)
    bad = deepcopy(review["review_packet"])
    bad["action_executed"] = True
    assert not verify_internally_generated_goal_candidate_review_packet(bad)
