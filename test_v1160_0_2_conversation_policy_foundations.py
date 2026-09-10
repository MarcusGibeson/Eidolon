from __future__ import annotations

import json
from pathlib import Path

from conscious_agent.conversation_discourse_policy import (
    MAX_HISTORY_RECORDS,
    MAX_PROMPT_CHARS,
    build_conversation_discourse_evidence,
    build_conversation_discourse_policy,
    build_conversation_discourse_policy_for_turn,
)


def _canonical(**overrides):
    value = {
        "selected_intent": "direct_answer",
        "output_disposition": "answer_only",
        "component_conflict_present": False,
    }
    value.update(overrides)
    return value


def test_v1160_0_evidence_is_bounded_structural_and_content_free():
    secret = "PRIVATE_CANARY_DO_NOT_EXPOSE"
    history = [{"role": "assistant", "content": secret + "?"}, {"role": "user", "content": secret}]
    evidence = build_conversation_discourse_evidence(
        "Please continue with the explanation " + secret,
        _canonical(),
        conversation_history=history,
        explicit_corrections=[{"operator_correction": True, "content": secret}],
    )
    assert evidence["literal_continuation_cue"] is True
    assert evidence["prior_assistant_question_present"] is True
    assert evidence["explicit_correction_present"] is True
    assert evidence["contains_message_content"] is False
    assert evidence["contains_conversation_text"] is False
    assert secret not in json.dumps(evidence)


def test_v1160_0_malformed_and_oversized_history_fail_bounded():
    evidence = build_conversation_discourse_evidence("Answer this", _canonical(), conversation_history="bad")
    assert evidence["history_malformed"] is True
    rows = ({"role": "user", "content": "x"} for _ in range(10_000))
    bounded = build_conversation_discourse_evidence("Answer", _canonical(), conversation_history=rows)
    assert bounded["history_count"] == MAX_HISTORY_RECORDS
    assert bounded["history_truncated"] is True


def test_v1160_1_correction_and_continuation_create_distinct_obligations():
    correction = build_conversation_discourse_policy_for_turn(
        "Actually, that is wrong", _canonical(selected_intent="correction"),
        conversation_history=[{"role": "assistant", "content": "Earlier answer"}],
    )
    assert correction["discourse_relation"] == "repair"
    assert correction["primary_obligation"] == "address_correction_first"
    assert correction["address_explicit_correction"] is True

    continuation = build_conversation_discourse_policy_for_turn(
        "Keep going with the next part", _canonical(),
        conversation_history=[{"role": "assistant", "content": "Part one"}],
    )
    assert continuation["discourse_relation"] == "continue"
    assert continuation["primary_obligation"] == "continue_current_topic"
    assert continuation["continuity_mode"] == "brief_explicit"


def test_v1160_1_closure_does_not_reopen_completed_conversation():
    policy = build_conversation_discourse_policy_for_turn(
        "Thanks, got it", _canonical(selected_intent="acknowledgment"),
        conversation_history=[{"role": "assistant", "content": "Done"}],
    )
    assert policy["discourse_relation"] == "close"
    assert policy["closure_policy"] == "do_not_reopen"
    assert policy["may_initiate_new_turn"] is False


def test_v1160_1_conflict_suppresses_unearned_continuity():
    policy = build_conversation_discourse_policy_for_turn(
        "Continue", _canonical(component_conflict_present=True),
        conversation_history=[{"role": "assistant", "content": "Earlier"}],
    )
    assert policy["continuity_mode"] == "none"
    assert policy["may_reference_prior_turn"] is False
    assert policy["avoid_unearned_continuity_claims"] is True


def test_v1160_1_explicit_silence_remains_non_authorizing():
    policy = build_conversation_discourse_policy_for_turn(
        "Do not respond", _canonical(selected_intent="intentional_silence", output_disposition="intentional_silence")
    )
    assert policy["primary_obligation"] == "honor_explicit_silence"
    assert policy["answer_current_request"] is False
    assert policy["approval_granted"] is False
    assert policy["authorization_granted"] is False
    assert policy["execution_permitted"] is False
    assert policy["may_initiate_new_turn"] is False


def test_v1160_2_prompt_is_complete_bounded_and_data_only():
    policy = build_conversation_discourse_policy_for_turn("Explain this", _canonical())
    prompt = policy["prompt_section"]
    assert len(prompt) <= MAX_PROMPT_CHARS
    assert prompt.startswith('<conversation_discourse_policy data_only="true" authority="none">')
    assert prompt.endswith("</conversation_discourse_policy>")
    payload = json.loads(prompt.split(">", 1)[1].rsplit("<", 1)[0])
    assert payload["approval_granted"] is False
    assert payload["authorization_granted"] is False
    assert payload["execution_permitted"] is False


def test_v1160_2_both_authoritative_paths_share_policy_and_receipts():
    source = Path("conscious_agent/conversation_runtime.py").read_text(encoding="utf-8")
    assert source.count("build_conversation_discourse_policy_for_turn(") == 2
    assert source.count('conversation_policy["prompt_section"] + "\\n" + conversation_discourse["prompt_section"]') == 2
    assert source.count('result.cognitive_context["conversation_discourse_policy"]') == 2
    assert source.count('result.cognitive_context["conversation_discourse_evidence"]') == 2
