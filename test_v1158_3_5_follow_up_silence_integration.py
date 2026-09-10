from conscious_agent.follow_up_silence_policy import (
    MAX_PROMPT_CHARS, build_follow_up_silence_policy, normalize_follow_up_silence_policy,
)


def intent(name="direct_answer", confidence="high", **evidence):
    return {"selected_intent": name, "confidence": confidence, "evidence": evidence}


def behavior(posture="none", conflict=False):
    return {"follow_up_posture": posture, "conflicting_context_suppressed": conflict}


def test_clarification_requires_one_scoped_question():
    result = build_follow_up_silence_policy("Which file do you mean?", intent("clarification"), behavior("one_bounded_question"))
    assert result["output_disposition"] == "ask_one_question"
    assert result["question_scope"] == "missing_information_only"
    assert result["max_follow_up_questions"] == 1


def test_literal_continue_request_supports_one_current_topic_question():
    result = build_follow_up_silence_policy("Tell me more.", intent("follow_up"), behavior("optional"))
    assert result["follow_up_utility"] == "useful"
    assert result["output_disposition"] == "answer_then_one_question"
    assert result["question_scope"] == "current_topic_only"


def test_answerable_direct_request_suppresses_redundant_follow_up():
    result = build_follow_up_silence_policy("What is two plus two?", intent("direct_answer"), behavior("optional"))
    assert result["follow_up_posture"] == "none"
    assert result["redundancy_avoided"] is True
    assert result["generic_offer_prohibited"] is True


def test_explicit_silence_materially_selects_no_substantive_content():
    result = build_follow_up_silence_policy("Do not respond.", intent("intentional_silence", explicit_silence_request=True), behavior("one_bounded_question"))
    assert result["output_disposition"] == "intentional_silence"
    assert result["emit_no_substantive_content"] is True
    assert result["follow_up_posture"] == "none"


def test_correction_and_conflict_remain_direct():
    correction = build_follow_up_silence_policy("No, correct that.", intent("correction", explicit_correction=True), behavior("optional"))
    conflict = build_follow_up_silence_policy("Thanks.", intent("acknowledgment"), behavior("optional", True))
    assert correction["output_disposition"] == "answer_only"
    assert conflict["output_disposition"] == "answer_only"


def test_tampered_disposition_and_scope_fail_closed():
    result = normalize_follow_up_silence_policy({
        "silence_posture": "not_requested", "follow_up_posture": "none",
        "output_disposition": "initiate_new_turn", "question_scope": "anything",
        "approval_granted": True, "authorization_granted": True,
    })
    assert result["output_disposition"] == "answer_only"
    assert result["question_scope"] == "none"
    assert result["approval_granted"] is False
    assert result["authorization_granted"] is False
    assert result["policy_recovered"] is True


def test_prompt_contains_integrated_directives_without_content():
    canary = "PRIVATE_FOLLOWUP_CANARY_1158_5"
    result = build_follow_up_silence_policy(canary, intent("direct_answer"), behavior("optional"))
    prompt = result["prompt_section"]
    assert len(prompt) <= MAX_PROMPT_CHARS
    assert prompt.endswith("</follow_up_silence_policy>")
    assert '"output_disposition":"answer_only"' in prompt
    assert '"generic_offer_prohibited":true' in prompt
    assert canary not in prompt


def test_runtime_still_uses_one_shared_policy_path():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_follow_up_silence_policy(message, response_intent, contextual_behavior)") == 2
    assert source.count('follow_up_silence["prompt_section"]') == 2
