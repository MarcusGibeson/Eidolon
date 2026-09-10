from __future__ import annotations
from copy import deepcopy

from conscious_agent.internally_generated_goal_runtime import (
    build_internally_generated_goal_candidate_reliability,
    build_internally_generated_goal_candidate_review_handoff,
    build_internally_generated_goal_candidate_review_projection,
    verify_internally_generated_goal_candidate_diagnostics_strict,
    verify_internally_generated_goal_candidate_reliability,
)
from test_v1170_0_2_internally_generated_goal_candidate_foundations import NOW, _goal


def _bundle(message="The Eidolon tests are failing again.", receipts=None):
    projection = _goal(message)
    review = build_internally_generated_goal_candidate_review_projection(
        projection, prior_goal_candidate_receipts=receipts, now=NOW,
    )
    reliability = build_internally_generated_goal_candidate_reliability(
        projection, review, prior_goal_candidate_receipts=receipts, now=NOW,
    )
    return projection, review, reliability


def _receipt():
    projection = _goal("The Eidolon tests are failing again.")
    return build_internally_generated_goal_candidate_review_handoff(
        projection, provider_completed=True, assistant_memory_committed=True,
    )


def test_1170_6_strict_diagnostics_reject_digest_valid_extra_field():
    projection = _goal("The Eidolon tests are failing again.")
    bad = deepcopy(projection["diagnostics"])
    bad["approved"] = True
    unsigned = {k: v for k, v in bad.items() if k != "diagnostics_digest"}
    from conscious_agent.internally_generated_goal_runtime import _digest
    bad["diagnostics_digest"] = _digest(unsigned)
    assert not verify_internally_generated_goal_candidate_diagnostics_strict(bad)


def test_1170_6_impossible_prior_count_fails_strict_diagnostics():
    projection = _goal("The Eidolon tests are failing again.")
    bad = deepcopy(projection["diagnostics"])
    bad["verified_prior_receipt_count"] = 2
    from conscious_agent.internally_generated_goal_runtime import _digest
    bad["diagnostics_digest"] = _digest({k:v for k,v in bad.items() if k != "diagnostics_digest"})
    assert not verify_internally_generated_goal_candidate_diagnostics_strict(bad)


def test_1170_7_clean_projection_is_reliable_and_content_free():
    _, _, report = _bundle()
    assert verify_internally_generated_goal_candidate_reliability(report)
    assert report["ordinary_conversation_ready"] is True
    assert report["review_available"] is True
    assert "tests are failing" not in str(report).lower()


def test_1170_7_replay_flood_fails_closed_without_amplification():
    receipt = _receipt()
    _, _, report = _bundle(receipts=[receipt] * 80)
    assert verify_internally_generated_goal_candidate_reliability(report)
    assert report["ordinary_conversation_ready"] is False
    assert report["receipt_budget_exceeded"] is True
    assert report["candidate_available"] is False


def test_1170_7_tampered_receipt_fails_closed():
    receipt = _receipt()
    receipt["candidate_type"] = "capability_improvement"
    _, _, report = _bundle(receipts=[receipt])
    assert verify_internally_generated_goal_candidate_reliability(report)
    assert report["ordinary_conversation_ready"] is False
    assert report["tampered_prior_receipt_count"] == 1


def test_1170_7_recovered_projection_cannot_leave_candidate_residue():
    projection, review, _ = _bundle()
    projection["policy"]["policy_recovered"] = True
    report = build_internally_generated_goal_candidate_reliability(projection, review, now=NOW)
    assert verify_internally_generated_goal_candidate_reliability(report)
    assert report["ordinary_conversation_ready"] is False
    assert report["residual_candidate_detected"] is True


def test_1170_8_forged_authority_invalidates_reliability_report():
    _, _, report = _bundle()
    bad = deepcopy(report)
    bad["goal_activated"] = True
    assert not verify_internally_generated_goal_candidate_reliability(bad)


def test_1170_8_streaming_and_non_streaming_share_runtime_key():
    from pathlib import Path
    text = Path("conscious_agent/conversation_runtime.py").read_text()
    assert text.count('"internally_generated_goal_candidate_reliability"') == 2
    assert text.count("build_internally_generated_goal_candidate_reliability(") == 2


def test_1170_8_no_plans_tools_actions_or_training_enabled():
    _, _, report = _bundle()
    for key in ("goal_activated", "plan_created", "tool_routed", "action_executed",
                "source_edited", "autonomous_work_started", "memory_mutated",
                "lesson_committed", "model_trained", "model_weights_changed",
                "installation_performed", "promotion_performed", "certification_performed"):
        assert report[key] is False
