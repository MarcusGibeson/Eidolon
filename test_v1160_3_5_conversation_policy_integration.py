from __future__ import annotations

import json
from pathlib import Path

from conscious_agent.conversation_discourse_policy import (
    MAX_PROMPT_CHARS,
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


def test_v1160_3_continuation_uses_one_brief_reference_without_recap():
    policy = build_conversation_discourse_policy_for_turn(
        "Keep going with the next section",
        _canonical(),
        conversation_history=[{"role": "assistant", "content": "Earlier section"}],
    )
    assert policy["discourse_relation"] == "continue"
    assert policy["opening_move"] == "continue_without_recap"
    assert policy["prior_context_use"] == "one_brief_reference"
    assert policy["maximum_prior_turn_references"] == 1
    assert policy["maximum_recap_sentences"] == 0
    assert policy["generic_closing_offer_allowed"] is False


def test_v1160_3_conflict_removes_prior_context_reference():
    policy = build_conversation_discourse_policy_for_turn(
        "Continue",
        _canonical(component_conflict_present=True),
        conversation_history=[{"role": "assistant", "content": "Earlier"}],
    )
    assert policy["continuity_mode"] == "none"
    assert policy["prior_context_use"] == "none"
    assert policy["maximum_prior_turn_references"] == 0
    assert policy["may_reference_prior_turn"] is False


def test_v1160_4_repair_has_bounded_acknowledge_replace_sequence():
    policy = build_conversation_discourse_policy_for_turn(
        "Actually, that was wrong",
        _canonical(selected_intent="correction"),
        conversation_history=[{"role": "assistant", "content": "Old answer"}],
    )
    assert policy["discourse_relation"] == "repair"
    assert policy["opening_move"] == "acknowledge_correction_then_replace"
    assert policy["repair_sequence"] == "acknowledge_correct_answer"
    assert policy["completion_shape"] == "complete_without_offer"
    assert policy["maximum_prior_turn_references"] == 1


def test_v1160_4_clarification_and_closure_have_distinct_shapes():
    clarification = build_conversation_discourse_policy_for_turn(
        "Which one?",
        _canonical(selected_intent="clarification", output_disposition="ask_one_question"),
        conversation_history=[{"role": "assistant", "content": "Choose a target"}],
    )
    assert clarification["opening_move"] == "ask_missing_information_directly"
    assert clarification["completion_shape"] == "await_required_reply"
    assert clarification["generic_closing_offer_allowed"] is False

    closing = build_conversation_discourse_policy_for_turn(
        "Thanks, got it",
        _canonical(selected_intent="acknowledgment"),
        conversation_history=[{"role": "assistant", "content": "Done"}],
    )
    assert closing["opening_move"] == "brief_acknowledgment"
    assert closing["completion_shape"] == "close_without_offer"
    assert closing["maximum_prior_turn_references"] == 0


def test_v1160_4_verified_silence_has_no_substantive_plan():
    policy = build_conversation_discourse_policy_for_turn(
        "Do not respond",
        _canonical(selected_intent="intentional_silence", output_disposition="intentional_silence"),
    )
    assert policy["opening_move"] == "no_substantive_content"
    assert policy["completion_shape"] == "silent_completion"
    assert policy["prior_context_use"] == "none"
    assert policy["maximum_prior_turn_references"] == 0
    assert policy["generic_closing_offer_allowed"] is False


def test_v1160_5_malformed_evidence_recovers_without_prior_reference_or_authority():
    policy = build_conversation_discourse_policy(None)
    assert policy["policy_recovered"] is True
    assert policy["prior_context_use"] == "none"
    assert policy["maximum_prior_turn_references"] == 0
    assert policy["approval_granted"] is False
    assert policy["authorization_granted"] is False
    assert policy["execution_permitted"] is False
    assert policy["may_initiate_new_turn"] is False


def test_v1160_5_prompt_contains_complete_bounded_response_plan():
    policy = build_conversation_discourse_policy_for_turn(
        "Keep going",
        _canonical(),
        conversation_history=[{"role": "assistant", "content": "Part one"}],
    )
    prompt = policy["prompt_section"]
    assert len(prompt) <= MAX_PROMPT_CHARS
    assert prompt.startswith('<conversation_discourse_policy data_only="true" authority="none">')
    assert prompt.endswith("</conversation_discourse_policy>")
    payload = json.loads(prompt.split(">", 1)[1].rsplit("<", 1)[0])
    assert payload["opening_move"] == "continue_without_recap"
    assert payload["prior_context_use"] == "one_brief_reference"
    assert payload["maximum_prior_turn_references"] == 1
    assert payload["generic_closing_offer_allowed"] is False
    assert payload["approval_granted"] is False


def test_v1160_5_shared_authoritative_paths_keep_one_discourse_projection():
    source = Path("conscious_agent/conversation_runtime.py").read_text(encoding="utf-8")
    assert source.count("build_conversation_discourse_policy_for_turn(") == 2
    assert source.count('conversation_discourse["prompt_section"]') == 2
    assert source.count('result.cognitive_context["conversation_discourse_policy"]') == 2
    assert source.count('result.cognitive_context["conversation_discourse_evidence"]') == 2
