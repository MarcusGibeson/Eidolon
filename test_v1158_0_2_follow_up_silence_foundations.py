from conscious_agent.follow_up_silence_policy import (
    MAX_PROMPT_CHARS, build_follow_up_silence_policy, normalize_follow_up_silence_policy,
)


def intent(name="direct_answer", **evidence):
    return {"selected_intent": name, "confidence": "high", "evidence": evidence}


def behavior(posture="none", conflict=False):
    return {"follow_up_posture": posture, "conflicting_context_suppressed": conflict}


def test_explicit_silence_is_literal_only_and_blocks_follow_up():
    result = build_follow_up_silence_policy("Please say nothing and do not respond.", intent("intentional_silence", explicit_silence_request=True), behavior("one_bounded_question"))
    assert result["silence_posture"] == "explicit_requested"
    assert result["follow_up_posture"] == "none"
    assert result["max_follow_up_questions"] == 0
    assert result["silence_may_be_inferred"] is False


def test_clarification_allows_exactly_one_question():
    result = build_follow_up_silence_policy("Which one?", intent("clarification", question_count=1), behavior("one_bounded_question"))
    assert result["follow_up_posture"] == "one_bounded_question"
    assert result["max_follow_up_questions"] == 1


def test_correction_blocks_follow_up_and_silence_inference():
    result = build_follow_up_silence_policy("No, that is wrong.", intent("correction", explicit_correction=True), behavior("optional"))
    assert result["follow_up_posture"] == "none"
    assert result["silence_posture"] == "not_requested"


def test_conflicting_context_suppresses_optional_follow_up():
    result = build_follow_up_silence_policy("Thanks.", intent("acknowledgment"), behavior("optional", True))
    assert result["follow_up_posture"] == "none"


def test_malformed_context_fails_neutral_and_non_authorizing():
    result = build_follow_up_silence_policy("hello", None, "bad")
    assert result["follow_up_posture"] == "none"
    assert result["policy_recovered"] is True
    assert result["approval_granted"] is False
    assert result["execution_permitted"] is False


def test_tampered_policy_normalizes_fail_closed():
    result = normalize_follow_up_silence_policy({"silence_posture": "invented", "follow_up_posture": "many", "approval_granted": True, "execution_permitted": True})
    assert result["silence_posture"] == "not_requested"
    assert result["follow_up_posture"] == "none"
    assert result["approval_granted"] is False
    assert result["execution_permitted"] is False


def test_prompt_is_complete_bounded_and_content_free():
    canary = "PRIVATE_CANARY_1158"
    result = build_follow_up_silence_policy(canary, intent(), behavior())
    prompt = result["prompt_section"]
    assert prompt.startswith('<follow_up_silence_policy data_only="true" authority="none">')
    assert prompt.endswith('</follow_up_silence_policy>')
    assert len(prompt) <= MAX_PROMPT_CHARS
    assert canary not in prompt
    assert canary not in str(result["evidence"])


def test_runtime_uses_shared_policy_for_streaming_and_nonstreaming():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_follow_up_silence_policy(message, response_intent, contextual_behavior)") == 2
    assert source.count('result.cognitive_context["follow_up_silence_policy"]') == 2
    assert source.count('follow_up_silence["prompt_section"]') == 2
