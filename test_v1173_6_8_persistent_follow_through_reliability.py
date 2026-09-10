from __future__ import annotations
import copy
from conscious_agent.persistent_follow_through_runtime import (
    build_persistent_follow_through_handoff,
    build_persistent_follow_through_projection,
    build_persistent_follow_through_review_projection,
    build_persistent_follow_through_reliability,
    verify_persistent_follow_through_diagnostics_strict,
    verify_persistent_follow_through_reliability,
)


def inputs():
    simulation={"comparison":{"alternative_count":3,"preferred_alternative_selected":False},"policy":{"operator_review_required":True,"alternative_selection_permitted":False}}
    review={"review_packet":{"operator_approval_required":True,"alternative_selected":False}}
    reliability={"report":{"reliability_posture":"plan_simulation_context_reliable","ordinary_conversation_ready":True,"simulation_available":True}}
    return simulation,review,reliability


def projection(prior=()):
    return build_persistent_follow_through_projection(*inputs(), prior_follow_through_receipts=prior)


def reliability(prior=(), p=None):
    p=p or projection(prior)
    return build_persistent_follow_through_reliability(p, build_persistent_follow_through_review_projection(p), prior_follow_through_receipts=prior)


def test_clean_reliability_is_valid_and_content_free():
    out=reliability(); report=out["report"]
    assert report["reliability_posture"] == "persistent_follow_through_context_reliable"
    assert report["follow_through_available"] is True
    assert verify_persistent_follow_through_reliability(report)
    assert "milestone_categories" not in out["prompt_section"]


def test_digest_valid_unknown_diagnostic_field_is_rejected():
    d=copy.deepcopy(projection()["diagnostics"]); d["approved"]=True
    assert verify_persistent_follow_through_diagnostics_strict(d) is False


def test_replay_does_not_amplify_verified_continuity():
    p=projection(); h=build_persistent_follow_through_handoff(p,provider_completed=True,assistant_memory_committed=True)
    rows=[{"persistent_follow_through_handoff":h}]*8
    report=reliability(rows)["report"]
    assert report["verified_prior_receipt_count"] == 1
    assert report["replayed_prior_receipt_count"] == 7


def test_receipt_budget_flood_fails_closed():
    p=projection(); h=build_persistent_follow_through_handoff(p,provider_completed=True,assistant_memory_committed=True)
    rows=[{"persistent_follow_through_handoff":copy.deepcopy(h)} for _ in range(65)]
    report=reliability(rows)["report"]
    assert report["ordinary_conversation_ready"] is False
    assert report["follow_through_available"] is False


def test_tampered_receipt_fails_closed():
    p=projection(); h=build_persistent_follow_through_handoff(p,provider_completed=True,assistant_memory_committed=True)
    h["milestone_count"]=63
    report=reliability([{"persistent_follow_through_handoff":h}])["report"]
    assert report["prior_continuity_valid"] is False
    assert report["review_available"] is False


def test_recovered_projection_residue_is_detected():
    p=projection(); p=copy.deepcopy(p)
    p["policy"]["policy_recovered"]=True
    p["diagnostics"]["integrity_digest"]="0"*64
    report=reliability(p=p)["report"]
    assert report["ordinary_conversation_ready"] is False
    assert report["residual_follow_through_detected"] is True


def test_forged_reliability_authority_is_rejected():
    report=copy.deepcopy(reliability()["report"]); report["plan_activated"]=True
    assert verify_persistent_follow_through_reliability(report) is False


def test_streaming_and_non_streaming_share_reliability():
    source=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert source.count("build_persistent_follow_through_reliability(") == 2
    assert source.count('persistent_follow_through_reliability["prompt_section"]') == 2
    assert source.count('result.cognitive_context["persistent_follow_through_reliability"]') == 2


def test_no_v1174_checkpoint_or_v1175_tools_added():
    source=open("conscious_agent/persistent_follow_through_runtime.py",encoding="utf-8").read().lower()
    assert "goal_and_planning_alpha_checkpoint" not in source
    assert "tool_intent" not in source
    assert "execute_plan(" not in source
