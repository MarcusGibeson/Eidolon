from conscious_agent.daily_companion_cognition import (
    audit_daily_companion_response_shape,
    build_daily_companion_evidence,
    build_daily_companion_policy,
    build_daily_companion_runtime_projection,
    verify_daily_companion_response_audit,
    verify_daily_companion_runtime_diagnostics,
)


def parts(relation="respond", continuation="answer_only", topic="active", speech="reactive_answer_only", **canonical):
    return (
        {"selected_intent": "direct_answer"},
        {"selected_intent": "direct_answer", "intentional_silence_verified": False, **canonical},
        {"discourse_relation": relation},
        {"continuity_relation": "adjacent_turn"},
        {"continuation_posture": continuation, "topic_continuity_posture": topic},
        {"speech_mode": speech, "deliberate_silence_preserved": False},
    )


def projection(message="Keep going", **kwargs):
    return build_daily_companion_runtime_projection(
        message,
        *parts(relation="continue", continuation="continue_current_topic"),
        **kwargs,
    )


def test_v1164_6_duplicate_receipt_replay_forces_literal_recovery():
    prior = projection()["diagnostics"]
    current = projection(prior_companion_receipts=[prior, dict(prior)])
    evidence = current["policy"]["evidence"]
    assert evidence["prior_companion_receipts_verified"] == 1
    assert evidence["prior_companion_receipts_replayed"] == 1
    assert evidence["continuity_health"] == "degraded"
    assert current["policy"]["companion_posture"] == "literal_request_only"
    assert current["policy"]["continuity_disposition"] == "recover_literal_request"


def test_v1164_6_distinct_verified_receipts_remain_bounded_and_resumable():
    first = projection()["diagnostics"]
    second = build_daily_companion_runtime_projection("Continue", *parts(relation="continue", continuation="continue_current_topic"))["diagnostics"]
    assert first["diagnostics_digest"] == second["diagnostics_digest"]
    # A repeated structural receipt is deliberately treated as replay, not stronger evidence.
    current = projection(prior_companion_receipts=[first, second])
    assert current["policy"]["policy_recovered"] is True
    assert current["diagnostics"]["prior_companion_receipts_replayed"] == 1


def test_v1164_6_malformed_receipt_collection_recovers_without_authority():
    current = projection(prior_companion_receipts={"forged": "receipt"})
    policy = current["policy"]
    assert policy["policy_recovered"] is True
    assert policy["may_initiate_new_turn"] is False
    assert policy["memory_rewrite_permitted"] is False
    assert policy["action_execution_permitted"] is False


def test_v1164_7_silence_response_audit_detects_any_emitted_content():
    evidence = build_daily_companion_evidence("", *parts(intentional_silence_verified=True))
    policy = build_daily_companion_policy(evidence)
    audit = audit_daily_companion_response_shape("I should not be here.", policy)
    assert audit["silence_violation"] is True
    assert audit["compliant"] is False
    assert audit["contains_generated_text"] is False
    assert verify_daily_companion_response_audit(audit)


def test_v1164_7_clarification_and_closure_budgets_are_enforced():
    clarify = build_daily_companion_policy(build_daily_companion_evidence("Which one?", *parts(relation="clarify", continuation="ask_one_required_clarification")))
    assert audit_daily_companion_response_shape("Which file?", clarify)["compliant"] is True
    assert audit_daily_companion_response_shape("Which file? What date?", clarify)["clarification_budget_violation"] is True
    close = build_daily_companion_policy(build_daily_companion_evidence("Thanks", *parts(relation="close", continuation="briefly_acknowledge_and_close", topic="complete")))
    assert audit_daily_companion_response_shape("Glad that helped.", close)["compliant"] is True
    assert audit_daily_companion_response_shape("Glad that helped. Anything else?", close)["closure_reopened"] is True


def test_v1164_7_bounded_insight_audit_is_content_free_and_tamper_evident():
    policy = build_daily_companion_policy(build_daily_companion_evidence("What do you notice?", *parts(speech="bounded_user_requested_observation")))
    audit = audit_daily_companion_response_shape("One answer. One bounded observation.", policy)
    assert audit["compliant"] is True
    assert "One answer" not in repr(audit)
    assert verify_daily_companion_response_audit(audit)
    forged = dict(audit)
    forged["compliant"] = False
    assert not verify_daily_companion_response_audit(forged)


def test_v1164_8_runtime_diagnostics_expose_recovery_without_content():
    prior = projection()["diagnostics"]
    runtime = projection(prior_companion_receipts=[prior, prior])
    diagnostics = runtime["diagnostics"]
    assert diagnostics["prior_companion_receipts_replayed"] == 1
    assert diagnostics["policy_recovered"] is True
    assert diagnostics["recovery_reason"] == "invalid_or_degraded_evidence"
    assert diagnostics["content_free"] is True
    assert diagnostics["authority"] == "none"
    assert verify_daily_companion_runtime_diagnostics(diagnostics)


def test_v1164_8_streaming_and_non_streaming_still_share_one_projection_contract():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_daily_companion_runtime_projection(") == 2
    assert source.count("prior_companion_receipts=session_history") == 2
    assert source.count('result.cognitive_context["daily_companion_runtime_diagnostics"]') == 2
