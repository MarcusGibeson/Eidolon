from conscious_agent.natural_follow_up_policy import (
    build_natural_follow_up_for_turn,
    build_natural_follow_up_runtime_projection,
    verify_natural_follow_up_runtime_diagnostics,
)


def canonical(intent="direct_answer"):
    return {"selected_intent": intent, "component_conflict_present": False}


def discourse(relation="respond", correction=False):
    return {"discourse_relation": relation, "address_explicit_correction": correction}


def continuity(relation="fresh_turn", confidence="high", **extra):
    return {"continuity_relation": relation, "continuity_confidence": confidence, "avoid_reasking_answered_question": True, **extra}


def test_v1162_6_punctuation_and_case_normalize_without_content_storage():
    row = build_natural_follow_up_for_turn("KEEP GOING!!!", canonical(), discourse(), continuity())
    assert row["continuation_posture"] == "continue_current_topic"
    assert row["evidence"]["contains_message_content"] is False


def test_v1162_6_negated_cues_do_not_trigger_continuation_or_transition():
    stopped = build_natural_follow_up_for_turn("Do not keep going", canonical(), discourse(), continuity())
    switched = build_natural_follow_up_for_turn("Do not switch to a different topic", canonical(), discourse(), continuity())
    assert stopped["literal_continuation_cue_present"] is False
    assert switched["topic_transition_permitted"] is False


def test_v1162_7_conflicting_closure_and_continuation_fail_closed():
    row = build_natural_follow_up_for_turn("Thanks, keep going", canonical(), discourse("continue"), continuity("continue_thread"))
    assert row["continuation_posture"] == "answer_only"
    assert row["cue_conflict_suppressed"] is True
    assert row["optional_follow_up_suppressed"] is True


def test_v1162_7_low_confidence_suppresses_optional_follow_up():
    row = build_natural_follow_up_for_turn("What next step should I take?", canonical(), discourse(), continuity(confidence="low"))
    assert row["continuation_posture"] == "answer_only"
    assert row["low_confidence_suppressed"] is True
    assert row["recovery_reason"] == "degraded_evidence"


def test_v1162_7_required_clarification_survives_verified_state_only():
    verified = build_natural_follow_up_for_turn("Which one?", canonical("clarification"), discourse("clarify"), continuity())
    degraded = build_natural_follow_up_for_turn("Which one?", canonical("clarification"), discourse("clarify"), continuity(confidence="low"))
    assert verified["maximum_follow_up_questions"] == 1
    assert degraded["maximum_follow_up_questions"] == 0


def test_v1162_8_runtime_diagnostics_digest_verifies_and_detects_tampering():
    projection = build_natural_follow_up_runtime_projection("continue", canonical(), discourse("continue"), continuity("continue_thread"))
    diagnostics = projection["diagnostics"]
    assert verify_natural_follow_up_runtime_diagnostics(diagnostics) is True
    altered = dict(diagnostics)
    altered["continuation_posture"] = "answer_and_offer_one_relevant_next_step"
    assert verify_natural_follow_up_runtime_diagnostics(altered) is False


def test_v1162_8_runtime_projection_remains_authority_free_after_recovery():
    projection = build_natural_follow_up_runtime_projection("Thanks, keep going", canonical(), discourse("continue"), continuity("continue_thread"))
    assert projection["diagnostics"]["authority"] == "none"
    assert projection["policy"]["may_initiate_new_turn"] is False
    assert projection["policy"]["action_execution_permitted"] is False
    assert projection["policy"]["approval_granted"] is False
