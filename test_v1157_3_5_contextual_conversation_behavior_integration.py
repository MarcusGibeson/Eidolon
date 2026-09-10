from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from contextual_conversation_behavior import build_contextual_conversation_behavior, MAX_PROMPT_CHARS
from response_intent_selection import build_response_intent_selection


def _intent(message="Keep going", history=None, memories=None):
    return build_response_intent_selection(
        message,
        reasoning_state={},
        conversation_history=history or [],
        self_model={"identity": "companion"},
        contextual_memories=memories or [],
    )


def test_v1157_3_low_relevance_suppresses_context_application():
    result = build_contextual_conversation_behavior(
        _intent("Give me the number"),
        self_model={"mood": "anxious", "identity": "PRIVATE"},
        contextual_memories=[{"type": "relationship", "content": "PRIVATE"}],
        conversation_history=[],
    )
    assert result["context_application"] == "implicit" or result["context_application"] == "suppressed"
    assert "PRIVATE" not in str(result)
    assert result["context_may_change_facts"] is False


def test_v1157_3_high_relevance_allows_bounded_explicit_context():
    history = [{"role": "user"}, {"role": "assistant"}]
    memories = [{"type": "relationship", "relationship_relevance": True, "sensitive": True}]
    intent = _intent("Can you explain why?", history=history, memories=memories)
    result = build_contextual_conversation_behavior(
        intent,
        self_model={"mood": "worried", "identity": "companion"},
        contextual_memories=memories,
        conversation_history=history,
    )
    assert result["context_application"] == "bounded_explicit"
    assert result["emotional_calibration"] == "gentle"
    assert result["reassurance"] == "light"


def test_v1157_4_clarification_allows_exactly_one_question():
    intent = _intent("What do you mean by that?", history=[{"role": "assistant"}])
    result = build_contextual_conversation_behavior(intent, conversation_history=[{"role": "assistant"}])
    assert result["follow_up_posture"] == "one_bounded_question"
    assert result["max_follow_up_questions"] == 1


def test_v1157_4_correction_blocks_follow_up_and_unearned_reassurance():
    history = [{"role": "user"}, {"role": "assistant"}]
    result = build_contextual_conversation_behavior(
        _intent("Actually, that is not correct", history=history),
        self_model={"mood": "sad"},
        contextual_memories=[{"type": "relationship", "sensitive": True}],
        conversation_history=history,
    )
    assert result["correction_sensitive"] is True
    assert result["follow_up_posture"] == "none"
    assert result["max_follow_up_questions"] == 0
    assert result["reassurance"] == "none"
    assert result["avoid_unearned_reassurance"] is True


def test_v1157_4_continuity_reference_is_bounded_not_invented():
    history = [{"role": "user"}, {"role": "assistant"}]
    result = build_contextual_conversation_behavior(
        _intent("Thanks, keep going", history=history),
        contextual_memories=[{"type": "relationship", "relationship_relevance": True}],
        conversation_history=history,
    )
    assert result["continuity_reference"] in {"implicit", "brief_explicit"}
    assert result["avoid_false_familiarity"] is True
    assert result["avoid_repetitive_acknowledgment"] is True


def test_v1157_5_prompt_materially_contains_integration_directives():
    result = build_contextual_conversation_behavior(
        _intent("What do you mean?", history=[{"role": "assistant"}]),
        conversation_history=[{"role": "assistant"}],
    )
    prompt = result["prompt_section"]
    assert len(prompt) <= MAX_PROMPT_CHARS
    assert prompt.endswith("</contextual_conversation_behavior>")
    for key in ("context_application", "continuity_reference", "follow_up_posture", "max_follow_up_questions", "emotional_calibration"):
        assert f'"{key}"' in prompt


def test_v1157_5_streaming_and_nonstreaming_still_share_single_behavior_path():
    text = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
    assert text.count("contextual_behavior = build_contextual_conversation_behavior(") == 2
    assert text.count('contextual_behavior["prompt_section"]') == 2
    assert text.count("client.generate(packet.prompt)") == 1
    assert text.count("client.stream(packet.prompt)") == 1
