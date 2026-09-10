from __future__ import annotations

import copy

from conscious_agent.plan_simulation_runtime import (
    build_plan_simulation_projection,
    build_plan_simulation_review_handoff,
    build_plan_simulation_review_projection,
    verify_plan_simulation_review_packet,
    verify_plan_simulation_review_state,
)


def inputs():
    projection = {
        "hierarchy": {"plan_candidate_available": True, "milestone_count": 3, "dependency_count": 2, "stopping_condition_count": 3},
        "policy": {"operator_review_required": True, "plan_activation_permitted": False, "action_execution_permitted": False},
    }
    reliability = {"reliability_posture": "hierarchical_planning_context_reliable", "ordinary_conversation_ready": True, "plan_candidate_available": True}
    return projection, reliability


def current_projection(prior=()):
    p, r = inputs()
    return build_plan_simulation_projection(p, r, prior_simulation_receipts=prior)


def test_emerging_simulation_review_packet_is_content_free_and_non_selecting():
    review = build_plan_simulation_review_projection(current_projection())
    assert review["state"]["review_disposition"] == "emerging_simulation_review"
    assert verify_plan_simulation_review_state(review["state"])
    assert verify_plan_simulation_review_packet(review["review_packet"])
    assert review["review_packet"]["alternative_selected"] is False


def test_verified_prior_handoff_produces_stable_review():
    first = current_projection()
    receipt = build_plan_simulation_review_handoff(first, provider_completed=True, assistant_memory_committed=True)
    second = current_projection([{"plan_simulation_review_handoff": receipt}])
    review = build_plan_simulation_review_projection(second)
    assert review["state"]["review_disposition"] == "stable_simulation_review"
    assert review["state"]["verified_prior_receipt_count"] == 1


def test_replay_does_not_amplify_stability():
    first = current_projection()
    receipt = build_plan_simulation_review_handoff(first, provider_completed=True, assistant_memory_committed=True)
    second = current_projection([{"plan_simulation_review_handoff": receipt}, {"plan_simulation_review_handoff": receipt}])
    review = build_plan_simulation_review_projection(second)
    assert review["state"]["verified_prior_receipt_count"] == 1
    assert review["state"]["replayed_prior_receipt_count"] == 1


def test_tampered_comparison_recovers_without_reviewable_alternatives():
    value = current_projection()
    value = copy.deepcopy(value)
    value["comparison"]["alternative_count"] = 2
    review = build_plan_simulation_review_projection(value)
    assert review["state"]["review_disposition"] == "literal_current_request_only_recovery"
    assert review["review_packet"]["alternative_classes"] == []


def test_digest_valid_unknown_review_packet_field_is_rejected():
    review = build_plan_simulation_review_projection(current_projection())
    packet = copy.deepcopy(review["review_packet"])
    packet["approved"] = True
    packet.pop("review_packet_digest")
    import hashlib, json
    packet["review_packet_digest"] = hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert not verify_plan_simulation_review_packet(packet)


def test_prompt_is_bounded_structural_and_authority_free():
    review = build_plan_simulation_review_projection(current_projection())
    prompt = review["prompt_section"]
    assert len(prompt) <= 2048
    assert 'authority="none"' in prompt
    for forbidden in ("plan_text", "conversation_text", "private_reasoning", "provider_payload"):
        assert forbidden not in prompt


def test_no_selection_activation_or_execution_authority():
    packet = build_plan_simulation_review_projection(current_projection())["review_packet"]
    assert all(packet[k] is False for k in (
        "alternative_selected", "plan_activated", "plan_persisted", "schedule_created",
        "tool_routed", "action_executed", "source_edited", "autonomous_work_started",
    ))


def test_streaming_and_non_streaming_share_review_projection_source():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_plan_simulation_review_projection(") == 2
    assert source.count('result.cognitive_context["plan_simulation_review_state"]') == 2
    assert source.count('result.cognitive_context["plan_simulation_review_packet"]') == 2
    assert source.count('plan_simulation_review_projection["prompt_section"]') == 2


def test_no_v1173_or_execution_surfaces_added():
    source = open("conscious_agent/plan_simulation_runtime.py", encoding="utf-8").read().lower()
    assert "persistent_follow_through" not in source
    assert "execute_plan(" not in source
    assert "select_preferred_alternative(" not in source
