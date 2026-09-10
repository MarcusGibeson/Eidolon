from __future__ import annotations
import copy
from conscious_agent.persistent_follow_through_runtime import (
    build_persistent_follow_through_handoff, build_persistent_follow_through_projection,
    build_persistent_follow_through_review_projection, verify_persistent_follow_through_review_packet,
    verify_persistent_follow_through_review_state,
)


def inputs():
    simulation={"comparison":{"alternative_count":3,"preferred_alternative_selected":False},"policy":{"operator_review_required":True,"alternative_selection_permitted":False}}
    review={"review_packet":{"operator_approval_required":True,"alternative_selected":False}}
    reliability={"report":{"reliability_posture":"plan_simulation_context_reliable","ordinary_conversation_ready":True,"simulation_available":True}}
    return simulation,review,reliability


def projection(prior=()):
    return build_persistent_follow_through_projection(*inputs(), prior_follow_through_receipts=prior)


def test_emerging_review_packet_is_bounded_and_valid():
    out=build_persistent_follow_through_review_projection(projection())
    assert out["state"]["review_disposition"] == "emerging_follow_through_review"
    assert verify_persistent_follow_through_review_state(out["state"])
    assert verify_persistent_follow_through_review_packet(out["review_packet"])


def test_verified_receipt_stabilizes_review():
    p=projection(); h=build_persistent_follow_through_handoff(p,provider_completed=True,assistant_memory_committed=True)
    out=build_persistent_follow_through_review_projection(projection([{"persistent_follow_through_handoff":h}]))
    assert out["state"]["review_disposition"] == "stable_follow_through_review"
    assert out["state"]["continuity_stability_band"] == "verified_cross_turn"


def test_tamper_fails_closed_without_review_residue():
    p=projection(); h=build_persistent_follow_through_handoff(p,provider_completed=True,assistant_memory_committed=True)
    bad=copy.deepcopy(h); bad["milestone_count"]=9
    out=build_persistent_follow_through_review_projection(projection([{"persistent_follow_through_handoff":bad}]))
    assert out["state"]["follow_through_available"] is False
    assert out["review_packet"]["milestone_categories"] == []


def test_digest_valid_unknown_review_field_is_rejected():
    out=build_persistent_follow_through_review_projection(projection())
    packet=copy.deepcopy(out["review_packet"]); packet["approved"]=True
    assert verify_persistent_follow_through_review_packet(packet) is False


def test_review_packet_denies_authority():
    packet=build_persistent_follow_through_review_projection(projection())["review_packet"]
    assert packet["operator_approval_required"] is True
    assert all(packet[k] is False for k in ("plan_activated","plan_persisted","schedule_created","tool_routed","action_executed","source_edited","autonomous_work_started"))


def test_prompt_is_content_free():
    prompt=build_persistent_follow_through_review_projection(projection())["prompt_section"].lower()
    for forbidden in ("plan_text","conversation_text","provider_payload","private_reasoning"):
        assert forbidden not in prompt


def test_streaming_and_non_streaming_share_review_projection():
    source=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert source.count("build_persistent_follow_through_review_projection(") == 2
    assert source.count('result.cognitive_context["persistent_follow_through_review_state"]') == 2
    assert source.count('result.cognitive_context["persistent_follow_through_review_packet"]') == 2
    assert source.count('persistent_follow_through_review_projection["prompt_section"]') == 2


def test_no_v1174_or_tool_execution_added():
    source=open("conscious_agent/persistent_follow_through_runtime.py",encoding="utf-8").read().lower()
    assert "goal_and_planning_alpha_checkpoint" not in source
    assert "execute_plan(" not in source
    assert "tool_intent" not in source
