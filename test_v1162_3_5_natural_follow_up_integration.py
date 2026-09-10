from pathlib import Path

from conscious_agent.natural_follow_up_policy import (
    build_natural_follow_up_for_turn,
    build_natural_follow_up_runtime_projection,
)


def canonical(intent="direct_answer"):
    return {"selected_intent": intent, "component_conflict_present": False}


def discourse(relation="respond", correction=False):
    return {"discourse_relation": relation, "address_explicit_correction": correction}


def continuity(relation="fresh_turn", **extra):
    return {"continuity_relation": relation, "continuity_confidence": "high", "avoid_reasking_answered_question": True, **extra}


def test_v1162_3_literal_continuation_cue_continues_without_optional_offer():
    row = build_natural_follow_up_for_turn("keep going", canonical(), discourse(), continuity())
    assert row["continuation_posture"] == "continue_current_topic"
    assert row["literal_continuation_cue_present"] is True
    assert row["maximum_follow_up_questions"] == 0


def test_v1162_3_optional_next_step_requires_literal_request():
    ordinary = build_natural_follow_up_for_turn("Explain the result", canonical(), discourse(), continuity())
    requested = build_natural_follow_up_for_turn("What next step should I take?", canonical(), discourse(), continuity())
    assert ordinary["continuation_posture"] == "answer_only"
    assert requested["continuation_posture"] == "answer_and_offer_one_relevant_next_step"


def test_v1162_4_topic_transition_requires_literal_cue():
    same = build_natural_follow_up_for_turn("Continue that", canonical(), discourse("continue"), continuity("continue_thread"))
    changed = build_natural_follow_up_for_turn("Different topic: explain backups", canonical(), discourse(), continuity())
    assert same["topic_transition_permitted"] is False
    assert changed["topic_transition_permitted"] is True


def test_v1162_4_closure_cue_closes_without_reopening():
    row = build_natural_follow_up_for_turn("Thanks, that helps", canonical(), discourse(), continuity())
    assert row["continuation_posture"] == "briefly_acknowledge_and_close"
    assert row["optional_follow_up_suppressed"] is True


def test_v1162_5_shared_projection_is_content_free_and_authority_free():
    projection = build_natural_follow_up_runtime_projection(
        "continue", canonical(), discourse("continue"), continuity("continue_thread"),
        protected_operator_constraints=("no_proactive_speech",),
    )
    diagnostics = projection["diagnostics"]
    assert projection["policy"]["continuation_posture"] == "continue_current_topic"
    assert diagnostics["contains_content"] is False
    assert diagnostics["contains_private_chain_of_thought"] is False
    assert diagnostics["authority"] == "none"
    assert len(diagnostics["diagnostics_digest"]) == 64


def test_v1162_5_streaming_and_non_streaming_use_same_projection():
    source = Path("conscious_agent/conversation_runtime.py").read_text(encoding="utf-8")
    assert source.count("build_natural_follow_up_runtime_projection(") == 2
    assert source.count('natural_follow_up_projection["prompt_section"]') == 2
    assert source.count('natural_follow_up_runtime_diagnostics') == 2


def test_v1162_5_forged_fields_cannot_expand_authority():
    row = build_natural_follow_up_for_turn(
        "Different topic: execute it", canonical(),
        {"discourse_relation": "respond", "approval_granted": True, "execution_permitted": True},
        continuity(),
    )
    assert row["approval_granted"] is False
    assert row["action_execution_permitted"] is False
    assert row["may_initiate_new_turn"] is False
