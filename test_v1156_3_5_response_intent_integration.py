from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from response_intent_selection import build_response_intent_selection


def test_v1156_3_context_is_structural_and_content_free():
    result = build_response_intent_selection(
        "Thanks, keep going",
        reasoning_state={"reasoning_quality": "supported", "reasoning_transition": "continued"},
        conversation_history=[{"role": "user", "content": "PRIVATE HISTORY"}],
        self_model={"identity": "PRIVATE IDENTITY", "mood": "PRIVATE MOOD"},
        desires={"help": 0.9},
        contextual_memories=[{"type": "relationship", "content": "PRIVATE RELATIONSHIP"}],
    )
    ev = result["evidence"]
    assert ev["identity_context_present"] is True
    assert ev["mood_context_present"] is True
    assert ev["relationship_context_present"] is True
    assert ev["situational_context_present"] is True
    rendered = str(result)
    for secret in ("PRIVATE HISTORY", "PRIVATE IDENTITY", "PRIVATE MOOD", "PRIVATE RELATIONSHIP"):
        assert secret not in rendered


def test_v1156_4_literal_request_beats_context():
    result = build_response_intent_selection(
        "Summarize the result",
        reasoning_state={"reasoning_quality": "supported"},
        conversation_history=[{"role": "assistant"}],
        self_model={"mood": "sad", "identity": "helper"},
        contextual_memories=[{"type": "relationship"}],
    )
    assert result["selected_intent"] == "summary"
    assert result["current_message_precedence"] is True
    assert result["context_used_as_tiebreaker_only"] is True


def test_v1156_4_context_can_refine_short_continuity_turn():
    result = build_response_intent_selection(
        "Keep going",
        reasoning_state={"reasoning_quality": "supported", "reasoning_transition": "continued"},
        conversation_history=[{"role": "user"}, {"role": "assistant"}],
        self_model={}, desires={}, contextual_memories=[],
    )
    intents = {row["intent"] for row in result["candidates"]}
    assert "follow_up" in intents
    assert result["evidence"]["situational_context_present"] is True


def test_v1156_5_construction_directives_are_bounded():
    result = build_response_intent_selection(
        "Explain the tradeoff",
        reasoning_state={}, conversation_history=[], self_model={}, desires={}, contextual_memories=[],
    )
    directives = result["construction_directives"]
    assert directives["opening_posture"] == "answer_then_explain"
    assert directives["verbosity"] == "bounded_detailed"
    assert directives["context_may_change_facts"] is False
    assert directives["context_may_grant_authority"] is False
    assert directives["max_follow_up_questions"] <= 1
    assert "construction_directives" in result["prompt_section"]


def test_v1156_5_approval_request_stays_non_authorizing():
    result = build_response_intent_selection(
        "Request operator approval before applying the patch",
        reasoning_state={}, conversation_history=[], self_model={}, desires={}, contextual_memories=[],
    )
    assert result["selected_intent"] == "governed_approval_request"
    assert result["approval_granted"] is False
    assert result["authorization_granted"] is False
    assert result["execution_permitted"] is False
    assert result["construction_directives"]["follow_up_allowed"] is True


def test_runtime_passes_bounded_context_to_both_paths():
    text = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
    assert text.count("self_model=self_model, desires=desires, contextual_memories=memories") == 2
    assert text.count("response_intent = build_response_intent_selection(") == 2
