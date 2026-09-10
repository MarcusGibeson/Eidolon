from __future__ import annotations

import copy
import hashlib
import json

from conscious_agent.goal_and_planning_alpha_runtime import (
    build_goal_and_planning_alpha_handoff,
    build_goal_and_planning_alpha_reliability,
    build_goal_and_planning_alpha_review_projection,
    verify_goal_and_planning_alpha_diagnostics_strict,
    verify_goal_and_planning_alpha_reliability,
)
from test_v1174_0_2_goal_and_planning_alpha_foundations import chain


def _alpha_review(message: str = "The Eidolon tests are failing repeatedly."):
    alpha = chain(message=message)["alpha"]
    return alpha, build_goal_and_planning_alpha_review_projection(alpha)


def _reliability(message: str = "The Eidolon tests are failing repeatedly.", prior=()):
    alpha, review = _alpha_review(message)
    reliability = build_goal_and_planning_alpha_reliability(
        alpha, review, prior_goal_planning_alpha_receipts=prior,
    )
    return alpha, review, reliability


def test_1174_6_clean_alpha_reliability_is_content_free_and_authority_free():
    alpha, review, reliability = _reliability()
    report = reliability["report"]
    assert verify_goal_and_planning_alpha_diagnostics_strict(alpha["diagnostics"])
    assert verify_goal_and_planning_alpha_reliability(report)
    assert report["ordinary_conversation_ready"] is True
    assert report["reliability_posture"] == "goal_and_planning_alpha_context_reliable"
    assert report["alpha_available"] is True
    assert report["review_available"] is True
    assert report["fault_count"] == 0
    text = repr(reliability).lower()
    for forbidden in ("the eidolon tests are failing", "goal_text", "plan_text", "private_reasoning"):
        assert forbidden not in text


def test_1174_6_no_candidate_remains_reliable_without_availability():
    _, _, reliability = _reliability(message="Explain the current memory checkpoint.")
    report = reliability["report"]
    assert verify_goal_and_planning_alpha_reliability(report)
    assert report["ordinary_conversation_ready"] is True
    assert report["alpha_available"] is False
    assert report["review_available"] is False
    assert report["fault_count"] == 0


def test_1174_6_digest_valid_unknown_diagnostics_field_is_rejected():
    alpha, review = _alpha_review()
    tampered = copy.deepcopy(alpha)
    tampered["diagnostics"]["approved"] = True
    assert verify_goal_and_planning_alpha_diagnostics_strict(tampered["diagnostics"]) is False
    reliability = build_goal_and_planning_alpha_reliability(tampered, review)["report"]
    assert reliability["ordinary_conversation_ready"] is False
    assert reliability["alpha_available"] is False


def test_1174_6_impossible_diagnostics_counts_are_rejected():
    alpha, review = _alpha_review()
    tampered = copy.deepcopy(alpha)
    tampered["diagnostics"]["available_stage_count"] = 5
    reliability = build_goal_and_planning_alpha_reliability(tampered, review)["report"]
    assert reliability["diagnostics_valid"] is False
    assert reliability["ordinary_conversation_ready"] is False


def test_1174_7_replay_is_counted_without_amplifying_continuity():
    alpha, review = _alpha_review()
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True,
    )
    prior = [
        {"goal_and_planning_alpha_handoff": handoff},
        {"goal_and_planning_alpha_handoff": handoff},
    ]
    report = build_goal_and_planning_alpha_reliability(
        alpha, review, prior_goal_planning_alpha_receipts=prior,
    )["report"]
    assert verify_goal_and_planning_alpha_reliability(report)
    assert report["verified_prior_receipt_count"] == 1
    assert report["replayed_prior_receipt_count"] == 1
    assert report["fault_count"] == 0


def test_1174_7_receipt_flood_fails_closed():
    alpha, review = _alpha_review()
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True,
    )
    report = build_goal_and_planning_alpha_reliability(
        alpha,
        review,
        prior_goal_planning_alpha_receipts=[{"goal_and_planning_alpha_handoff": handoff}] * 65,
    )["report"]
    assert report["receipt_budget_exceeded"] is True
    assert report["ordinary_conversation_ready"] is False
    assert report["alpha_available"] is False
    assert report["review_available"] is False


def test_1174_7_tampered_receipt_fails_closed():
    alpha, review = _alpha_review()
    handoff = build_goal_and_planning_alpha_handoff(
        alpha, provider_completed=True, assistant_memory_committed=True,
    )
    handoff["available_stage_count"] = 3
    report = build_goal_and_planning_alpha_reliability(
        alpha, review, prior_goal_planning_alpha_receipts=[{"goal_and_planning_alpha_handoff": handoff}],
    )["report"]
    assert report["tampered_prior_receipt_count"] == 1
    assert report["prior_continuity_valid"] is False
    assert report["ordinary_conversation_ready"] is False


def test_1174_7_recovered_projection_with_residue_is_suppressed():
    alpha, review = _alpha_review()
    recovered = copy.deepcopy(alpha)
    recovered["policy"]["policy_recovered"] = True
    report = build_goal_and_planning_alpha_reliability(recovered, review)["report"]
    assert report["recovered_projection"] is True
    assert report["residual_alpha_detected"] is True
    assert report["alpha_available"] is False
    assert report["review_available"] is False


def test_1174_8_forged_authority_field_is_rejected_even_with_new_digest():
    _, _, reliability = _reliability()
    report = copy.deepcopy(reliability["report"])
    report.pop("reliability_digest")
    report["goal_activated"] = True
    report["reliability_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert verify_goal_and_planning_alpha_reliability(report) is False


def test_1174_8_streaming_and_non_streaming_share_reliability_projection():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_goal_and_planning_alpha_reliability(") == 2
    assert source.count('goal_and_planning_alpha_reliability["prompt_section"]') == 2
    assert source.count('result.cognitive_context["goal_and_planning_alpha_reliability"]') == 2


def test_1174_8_no_v1175_tool_routing_or_execution_surface_added():
    source = open("conscious_agent/goal_and_planning_alpha_runtime.py", encoding="utf-8").read().lower()
    assert "tool_intent" not in source
    assert "route_tool(" not in source
    assert "execute_plan(" not in source
    assert "natural-language action" not in source
