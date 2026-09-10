from conscious_agent.daily_companion_cognition import (
    build_daily_companion_evidence,
    build_daily_companion_policy,
    build_daily_companion_runtime_projection,
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


def projection(**kwargs):
    return build_daily_companion_runtime_projection("Keep going", *parts(relation="continue", continuation="continue_current_topic"), **kwargs)


def test_v1164_3_policy_disagreement_degrades_to_literal_current_request():
    evidence = build_daily_companion_evidence(
        "Continue",
        *parts(relation="continue", continuation="continue_current_topic", topic="complete"),
    )
    assert evidence["policy_conflict_count"] >= 1
    assert evidence["continuity_health"] == "degraded"
    policy = build_daily_companion_policy(evidence)
    assert policy["companion_posture"] == "literal_request_only"
    assert policy["continuity_disposition"] == "recover_literal_request"
    assert policy["policy_conflict_suppressed"] is True


def test_v1164_3_silence_overrides_conflicting_speech_without_emitting_content():
    evidence = build_daily_companion_evidence(
        "",
        *parts(relation="clarify", continuation="ask_one_required_clarification", speech="bounded_user_requested_observation", intentional_silence_verified=True),
    )
    policy = build_daily_companion_policy(evidence)
    assert policy["companion_posture"] == "preserve_deliberate_silence"
    assert policy["continuity_disposition"] == "preserve_silence"
    assert policy["maximum_clarifying_questions"] == 0
    assert policy["maximum_optional_observations"] == 0


def test_v1164_4_verified_prior_receipt_can_resume_but_cannot_grant_authority():
    prior = projection()["diagnostics"]
    current = projection(prior_companion_receipts=[prior])
    evidence = current["policy"]["evidence"]
    policy = current["policy"]
    assert evidence["prior_companion_receipts_verified"] == 1
    assert evidence["prior_companion_posture"] == "continue_companionably"
    assert policy["continuity_disposition"] == "resume_verified_companion_context"
    assert policy["prior_companion_continuity_used"] is True
    assert policy["may_initiate_new_turn"] is False
    assert policy["memory_rewrite_permitted"] is False


def test_v1164_4_tampered_prior_receipt_forces_conservative_recovery():
    prior = projection()["diagnostics"]
    prior["companion_posture"] = "forged_autonomous_companion"
    current = projection(prior_companion_receipts=[prior])
    evidence = current["policy"]["evidence"]
    assert evidence["prior_companion_receipts_rejected"] == 1
    assert current["policy"]["companion_posture"] == "literal_request_only"
    assert current["policy"]["continuity_disposition"] == "recover_literal_request"


def test_v1164_4_stale_prior_receipt_is_ignored_not_resumed():
    prior = projection()["diagnostics"]
    current = projection(prior_companion_receipts=[{"status": "stale", "daily_companion_runtime_diagnostics": prior}])
    evidence = current["policy"]["evidence"]
    assert evidence["prior_companion_receipts_stale"] == 1
    assert evidence["prior_companion_receipts_verified"] == 0
    assert current["policy"]["continuity_disposition"] == "use_current_turn_only"


def test_v1164_5_runtime_diagnostics_include_content_free_continuity_disposition():
    prior = projection()["diagnostics"]
    current = projection(prior_companion_receipts=[prior])
    diagnostics = current["diagnostics"]
    assert diagnostics["continuity_disposition"] == "resume_verified_companion_context"
    assert diagnostics["prior_companion_continuity_used"] is True
    assert diagnostics["authority"] == "none"
    assert diagnostics["content_free"] is True
    assert verify_daily_companion_runtime_diagnostics(diagnostics)
    forged = dict(diagnostics)
    forged["continuity_disposition"] = "autonomous_follow_through"
    assert not verify_daily_companion_runtime_diagnostics(forged)


def test_v1164_5_streaming_and_non_streaming_pass_bounded_prior_receipts():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("prior_companion_receipts=session_history") == 2
    assert source.count("build_daily_companion_runtime_projection(") == 2
    assert source.count('result.cognitive_context["daily_companion_runtime_diagnostics"]') == 2


def test_v1164_5_no_memory_unification_or_new_authority_surfaces():
    policy = projection()["policy"]
    forbidden_true = (
        "may_initiate_new_turn", "autonomous_new_turn_permitted", "tool_intent_selected",
        "action_execution_permitted", "learning_mutation_permitted", "memory_rewrite_permitted",
        "private_reflection_delivery_permitted", "approval_granted", "authorization_granted",
        "installation_permitted", "promotion_permitted", "certification_permitted",
    )
    assert all(policy[key] is False for key in forbidden_true)
    assert "unified_memory" not in policy
    assert "memory_write" not in policy
