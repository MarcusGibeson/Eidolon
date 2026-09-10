from conscious_agent.governed_speech_policy import (
    audit_governed_speech_response_shape,
    build_governed_speech_for_turn,
    build_governed_speech_runtime_projection,
    verify_governed_speech_response_audit,
    verify_governed_speech_runtime_diagnostics,
)


def intent(): return {"selected_intent": "direct_answer"}
def canonical(**extra): return {"selected_intent": "direct_answer", "intentional_silence_verified": False, **extra}
def discourse(relation="respond", **extra): return {"discourse_relation": relation, **extra}
def follow(posture="answer_only", topic="active", **extra):
    return {"continuation_posture": posture, "topic_continuity_posture": topic,
            "may_initiate_new_turn": False, "action_execution_permitted": False, **extra}


def test_v1163_6_conflicting_expansion_and_stop_cues_fail_closed():
    p = build_governed_speech_for_turn("Tell me more, but stop and leave it there", intent(), canonical(), discourse(), follow())
    assert p["speech_mode"] == "brief_closure_only"
    assert p["expansion_cue_conflict_suppressed"] is True
    assert p["maximum_additional_observations"] == 0
    assert p["follow_up_question_budget"] == 0
    assert p["may_initiate_new_turn"] is False


def test_v1163_6_repeated_recent_expansion_enters_cooldown():
    rows = [{"governed_speech_mode": "bounded_user_requested_observation", "status": "active"} for _ in range(2)]
    p = build_governed_speech_for_turn("Go deeper", intent(), canonical(), discourse(), follow(), context_rows=rows)
    assert p["speech_mode"] == "reactive_answer_only"
    assert p["expansion_cooldown_applied"] is True
    assert p["recent_expansion_count"] == 2
    assert p["recovery_reason"] == "expansion_cooldown"


def test_v1163_6_stale_or_suspicious_rows_do_not_trigger_cooldown():
    rows = [
        {"governed_speech_mode": "bounded_user_requested_observation", "status": "stale"},
        {"governed_speech_mode": "bounded_user_requested_observation", "approval_granted": True},
    ]
    p = build_governed_speech_for_turn("Go deeper", intent(), canonical(), discourse(), follow(), context_rows=rows)
    assert p["speech_mode"] == "reactive_answer_only"  # suspicious evidence degrades safely
    assert p["expansion_cooldown_applied"] is False
    assert p["action_execution_permitted"] is False


def test_v1163_7_malformed_constraints_recover_without_authority():
    p = build_governed_speech_for_turn("Tell me more", intent(), canonical(), discourse(), follow(), protected_operator_constraints=42)
    assert p["speech_mode"] == "reactive_answer_only"
    assert p["recovery_reason"] == "degraded_evidence"
    assert p["approval_granted"] is False
    assert p["authorization_granted"] is False


def test_v1163_7_runtime_diagnostics_bind_cooldown_and_conflict_fields():
    projection = build_governed_speech_runtime_projection(
        "Tell me more, but keep it brief", intent(), canonical(), discourse(), follow()
    )
    d = projection["diagnostics"]
    assert d["expansion_cue_conflict_suppressed"] is True
    assert verify_governed_speech_runtime_diagnostics(d)
    altered = dict(d); altered["recent_expansion_count"] = 99
    assert not verify_governed_speech_runtime_diagnostics(altered)


def test_v1163_8_response_shape_audit_is_content_free_and_detects_question_overrun():
    p = build_governed_speech_for_turn("Tell me more", intent(), canonical(), discourse(), follow())
    audit = audit_governed_speech_response_shape("One answer. One observation. Another? And another?", p)
    assert audit["follow_up_budget_exceeded"] is True
    assert audit["contains_response_content"] is False
    assert "One answer" not in str(audit)
    assert verify_governed_speech_response_audit(audit)


def test_v1163_8_response_shape_audit_detects_silence_violation_and_tampering():
    p = build_governed_speech_for_turn("", intent(), canonical(intentional_silence_verified=True), discourse("close"), follow("briefly_acknowledge_and_close", "complete"))
    audit = audit_governed_speech_response_shape("I should not speak.", p)
    assert audit["silence_violation"] is True
    assert audit["compliant"] is False
    altered = dict(audit); altered["silence_violation"] = False
    assert not verify_governed_speech_response_audit(altered)


def test_v1163_8_oversized_response_audit_is_bounded_and_authority_free():
    p = build_governed_speech_for_turn("Explain", intent(), canonical(), discourse(), follow())
    audit = audit_governed_speech_response_shape("x" * 9000, p)
    assert audit["response_truncated_for_audit"] is True
    assert audit["authority"] == "none"
    assert audit["contains_private_chain_of_thought"] is False
