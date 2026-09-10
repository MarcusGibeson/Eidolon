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


def project(message="Explain it", **kw):
    return build_daily_companion_runtime_projection(message, *parts(**kw))


def test_v1164_0_evidence_is_bounded_content_free_and_does_not_unify_memory():
    evidence = build_daily_companion_evidence("Keep going", *parts(relation="continue", continuation="continue_current_topic"), context_rows=[{"role": "user", "shape": "short"}])
    assert evidence["active_continuity"] is True
    assert evidence["contains_message_content"] is False
    assert evidence["contains_memory_text"] is False
    assert "memory" not in " ".join(evidence.keys()).replace("contains_memory_text", "")


def test_v1164_0_stale_suspicious_malformed_and_authority_state_degrade():
    values = list(parts())
    values[-1] = {"speech_mode": "bounded_user_requested_observation", "may_initiate_new_turn": True}
    evidence = build_daily_companion_evidence("Tell me more", *values, context_rows=[{"status": "stale"}, {"private_chain_of_thought": "x"}])
    assert evidence["evidence_integrity"] == "degraded"
    assert evidence["authority_conflict_suppressed"] is True
    assert evidence["stale_records_ignored"] == 1
    assert evidence["suspicious_records_ignored"] == 1


def test_v1164_1_selects_companion_postures_without_authority():
    assert project()["policy"]["companion_posture"] == "answer_companionably"
    assert project(relation="continue", continuation="continue_current_topic")["policy"]["companion_posture"] == "continue_companionably"
    assert project(relation="repair")["policy"]["companion_posture"] == "repair_and_stabilize"
    assert project(relation="clarify", continuation="ask_one_required_clarification", topic="ambiguous")["policy"]["maximum_clarifying_questions"] == 1
    assert project(relation="close", continuation="briefly_acknowledge_and_close", topic="complete")["policy"]["close_without_reopening"] is True
    p = project()["policy"]
    assert p["may_initiate_new_turn"] is False and p["action_execution_permitted"] is False
    assert p["learning_mutation_permitted"] is False and p["memory_rewrite_permitted"] is False


def test_v1164_1_user_requested_bounded_insight_and_silence_are_distinct():
    expanded = project(speech="bounded_user_requested_observation")["policy"]
    silent = project(relation="close", canonical_silence=True) if False else build_daily_companion_runtime_projection("", *parts(relation="close", intentional_silence_verified=True))
    assert expanded["companion_posture"] == "answer_with_bounded_insight"
    assert expanded["maximum_optional_observations"] == 1
    assert silent["policy"]["companion_posture"] == "preserve_deliberate_silence"
    assert silent["policy"]["emit_no_substantive_content"] is True


def test_v1164_1_tampered_evidence_recovers_to_literal_request_only():
    evidence = build_daily_companion_evidence("Continue", *parts(relation="continue", continuation="continue_current_topic"))
    evidence["active_continuity"] = False
    policy = build_daily_companion_policy(evidence)
    assert policy["companion_posture"] == "literal_request_only"
    assert policy["policy_recovered"] is True


def test_v1164_2_projection_is_bounded_content_free_and_digest_verified():
    projection = project(relation="continue", continuation="continue_current_topic")
    assert projection["prompt_section"].startswith('<daily_companion_cognition data_only="true" authority="none">')
    assert projection["prompt_section"].endswith("</daily_companion_cognition>")
    assert len(projection["prompt_section"]) <= 2400
    assert verify_daily_companion_runtime_diagnostics(projection["diagnostics"])
    tampered = dict(projection["diagnostics"]); tampered["companion_posture"] = "forged"
    assert not verify_daily_companion_runtime_diagnostics(tampered)


def test_v1164_2_streaming_and_non_streaming_share_one_runtime_projection():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_daily_companion_runtime_projection(") == 2
    assert source.count('result.cognitive_context["daily_companion_runtime_diagnostics"]') == 2
    assert source.count('daily_companion_projection["prompt_section"]') == 2
