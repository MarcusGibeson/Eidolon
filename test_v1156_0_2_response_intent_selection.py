from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from response_intent_selection import (
    build_response_intent_evidence,
    build_response_intent_selection,
    generate_response_intent_candidates,
    response_intent_prompt_section,
    select_response_intent,
)


def test_v1156_0_evidence_is_bounded_content_free_and_provider_free():
    evidence = build_response_intent_evidence(
        "Explain why this failed?",
        reasoning_state={"reasoning_quality": "bounded", "reasoning_state_digest": "abc"},
        conversation_history=[{"role": "user", "content": "private"}],
        explicit_corrections=[{"content": "secret", "operator_correction": True}],
        protected_operator_constraints=["no_automatic_authority"],
    )
    public = evidence.public_summary()
    encoded = json.dumps(public, sort_keys=True)
    assert public["question_count"] == 1
    assert public["prior_reasoning_present"] is True
    assert public["explicit_correction_count"] == 1
    assert public["provider_contacted"] is False
    assert public["runtime_mutated"] is False
    assert "\"content\": \"private\"" not in encoded and "secret" not in encoded
    assert public["contains_private_chain_of_thought"] is False


def test_v1156_0_malformed_context_falls_back_deterministically():
    a = build_response_intent_selection("Tell me the result", reasoning_state=None, conversation_history=None)
    b = build_response_intent_selection("Tell me the result", reasoning_state=None, conversation_history=None)
    assert a["selected_intent"] == "direct_answer"
    assert a["evidence"]["malformed_context_fallback"] is True
    assert a["selection_digest"] == b["selection_digest"]


def test_v1156_0_action_and_conversation_intents_are_separate():
    result = build_response_intent_selection("Explain how to install it, but do not execute anything", reasoning_state={}, conversation_history=[])
    assert result["evidence"]["action_intent_present"] is True
    assert result["action_intent_separated"] is True
    assert result["execution_permitted"] is False


def test_v1156_1_literal_current_correction_wins():
    result = build_response_intent_selection("Actually, that is not correct. I meant the second option.", reasoning_state={}, conversation_history=[])
    assert result["selected_intent"] == "correction"
    assert result["current_message_precedence"] is True


def test_v1156_1_candidate_set_is_small_and_explicit_about_ambiguity():
    evidence = build_response_intent_evidence("Maybe this", reasoning_state={}, conversation_history=[])
    candidates = generate_response_intent_candidates("Maybe this", evidence)
    selection = select_response_intent("Maybe this", evidence)
    assert 1 <= len(candidates) <= 5
    assert selection["confidence"] in {"low", "medium", "high"}
    assert isinstance(selection["ambiguous"], bool)


def test_v1156_1_no_provider_needed_to_choose_intent():
    result = build_response_intent_selection("Summarize the previous result", reasoning_state={}, conversation_history=[])
    assert result["selected_intent"] == "summary"
    assert result["provider_contacted"] is False
    assert result["runtime_mutated"] is False


def test_v1156_1_explicit_silence_is_available_but_not_inferred():
    silent = build_response_intent_selection("Do not respond; remain silent.", reasoning_state={}, conversation_history=[])
    normal = build_response_intent_selection("I am thinking about this.", reasoning_state={}, conversation_history=[])
    assert silent["selected_intent"] == "intentional_silence"
    assert normal["selected_intent"] != "intentional_silence"


def test_v1156_2_prompt_projection_is_authority_free_and_bounded():
    result = build_response_intent_selection("Explain the tradeoff", reasoning_state={}, conversation_history=[])
    prompt = result["prompt_section"]
    assert len(prompt) <= 900
    assert 'authority="none"' in prompt
    assert "grants no approval" in prompt
    assert "Explain the tradeoff" not in prompt


def test_v1156_2_runtime_has_one_shared_streaming_and_nonstreaming_seam():
    text = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
    assert text.count("response_intent = build_response_intent_selection(") == 2
    assert text.count('cognitive_context=cognitive["prompt_section"] + "\\n" + response_intent["prompt_section"]') == 2
    assert "client.generate(packet.prompt)" in text
    assert "client.stream(packet.prompt)" in text


def test_v1156_2_diagnostics_are_content_free_and_non_authorizing():
    result = build_response_intent_selection("Request operator approval before applying the patch", reasoning_state={}, conversation_history=[])
    public = {k: v for k, v in result.items() if k != "prompt_section"}
    encoded = json.dumps(public, sort_keys=True)
    assert result["selected_intent"] == "governed_approval_request"
    assert result["approval_granted"] is False
    assert result["authorization_granted"] is False
    assert result["execution_permitted"] is False
    assert "applying the patch" not in encoded
