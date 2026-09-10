from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from contextual_conversation_behavior import (
    MAX_PROMPT_CHARS,
    build_contextual_conversation_behavior,
    normalize_contextual_behavior,
)
from response_intent_selection import build_response_intent_selection


def _intent(message="Keep going", **kwargs):
    return build_response_intent_selection(message, reasoning_state={}, conversation_history=[], **kwargs)


def test_v1157_0_evidence_is_structural_and_content_free():
    result = build_contextual_conversation_behavior(
        _intent(),
        self_model={"identity": "PRIVATE IDENTITY", "mood": "anxious"},
        contextual_memories=[{"type": "relationship", "content": "PRIVATE MEMORY", "sensitive": True}],
        conversation_history=[{"role": "user", "content": "PRIVATE HISTORY"}],
    )
    evidence = result["evidence"]
    assert evidence["identity_style_available"] is True
    assert evidence["mood_signal"] == "distressed"
    assert evidence["relationship_signal"] == "relevant"
    rendered = str(result)
    for secret in ("PRIVATE IDENTITY", "PRIVATE MEMORY", "PRIVATE HISTORY"):
        assert secret not in rendered


def test_v1157_0_malformed_inputs_fall_back_deterministically():
    a = build_contextual_conversation_behavior("bad", self_model="bad", contextual_memories=42, conversation_history=object())
    b = build_contextual_conversation_behavior("bad", self_model="bad", contextual_memories=42, conversation_history=object())
    assert a["evidence"]["malformed_context_fallback"] is True
    assert a["policy_digest"] == b["policy_digest"]
    assert a["approval_granted"] is False


def test_v1157_1_distress_changes_posture_not_facts_or_authority():
    result = build_contextual_conversation_behavior(
        _intent("Explain the result"),
        self_model={"mood": "worried"},
        contextual_memories=[{"type": "relationship", "emotional_relevance": True}],
        conversation_history=[{"role": "user"}, {"role": "assistant"}],
    )
    assert result["warmth"] == "gently_supportive"
    assert result["reassurance"] == "light"
    assert result["pacing"] == "deliberate"
    assert result["context_may_change_facts"] is False
    assert result["context_may_suppress_request"] is False
    assert result["context_may_grant_authority"] is False


def test_v1157_1_literal_correction_remains_direct():
    result = build_contextual_conversation_behavior(
        _intent("Actually, that is not correct"),
        self_model={"mood": "sad"},
        contextual_memories=[{"type": "relationship", "sensitive": True}],
        conversation_history=[{"role": "assistant"}],
    )
    assert result["correction_sensitive"] is True
    assert result["directness"] == "direct"
    assert result["reassurance"] == "none"
    assert result["literal_request_precedence"] is True


def test_v1157_1_intentional_silence_blocks_contextual_embellishment():
    result = build_contextual_conversation_behavior(
        _intent("Do not respond"),
        self_model={"mood": "excited", "identity": "helper"},
        contextual_memories=[{"type": "relationship"}],
        conversation_history=[{"role": "user"}, {"role": "assistant"}],
    )
    assert result["warmth"] == "neutral"
    assert result["familiarity"] == "ordinary"
    assert result["pacing"] == "compact"
    assert result["acknowledge_continuity"] is False


def test_v1157_1_normalization_fails_closed():
    result = normalize_contextual_behavior({
        "warmth": "manipulative",
        "familiarity": "invented_history",
        "context_may_grant_authority": True,
        "approval_granted": True,
        "execution_permitted": True,
    })
    assert result["warmth"] == "neutral"
    assert result["familiarity"] == "ordinary"
    assert result["behavior_recovered"] is True
    assert result["approval_granted"] is False
    assert result["execution_permitted"] is False


def test_v1157_2_prompt_is_bounded_complete_and_authority_free():
    result = build_contextual_conversation_behavior(_intent("Explain this"), self_model={"mood": "hopeful"})
    prompt = result["prompt_section"]
    assert prompt.startswith('<contextual_conversation_behavior data_only="true" authority="none">')
    assert prompt.endswith("</contextual_conversation_behavior>")
    assert len(prompt) <= MAX_PROMPT_CHARS
    assert '"approval_granted":false' in prompt
    assert '"execution_permitted":false' in prompt


def test_v1157_2_both_authoritative_paths_share_behavior_projection():
    text = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
    assert text.count("contextual_behavior = build_contextual_conversation_behavior(") == 2
    assert text.count('result.cognitive_context["contextual_conversation_behavior"]') == 2
    assert text.count('contextual_behavior["prompt_section"]') == 2
    assert text.count("client.generate(packet.prompt)") == 1
    assert text.count("client.stream(packet.prompt)") == 1
