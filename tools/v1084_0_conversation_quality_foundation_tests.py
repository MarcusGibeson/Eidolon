from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from conversation_quality_signals import build_conversation_quality_signals
from conversation_turn_intent import classify_turn_intent


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_relevance_distinguishes_current_and_recent_thread() -> None:
    history = [{"user_message": "My cat skipped dinner.", "assistant_response": "Keep an eye on her appetite and energy."}]
    follow = classify_conversation_quality("what about that?", history).quality_signals
    fresh = classify_conversation_quality("Explain binary search.", history).quality_signals
    require(follow.relevance_mode == "recent_thread_relevant" and follow.continuity_needed, "short follow-up lost continuity")
    require(fresh.relevance_mode == "current_turn_primary" and not fresh.continuity_needed, "unrelated turn forced a callback")


def test_clarity_is_bounded_without_invented_context() -> None:
    ambiguous = classify_conversation_quality("what about that?").quality_signals
    bounded = classify_conversation_quality("What causes rainbows?").quality_signals
    require(ambiguous.clarity_risk == "ambiguous_without_context", "missing-context ambiguity not detected")
    require(bounded.clarity_risk == "bounded", "clear question marked ambiguous")


def test_repetition_signal_uses_bounded_structure() -> None:
    history = [
        {"user_message": f"turn {i}", "assistant_response": "That makes sense, and here is a grounded reply."}
        for i in range(3)
    ]
    signals = classify_conversation_quality("continue", history).quality_signals
    require(signals.repetition_risk, "repeated assistant opening not detected")
    require(signals.history_rows_considered == 3, "history count wrong")


def test_question_signals_cover_current_and_open_exchange() -> None:
    history = [{"user_message": "I am deciding.", "assistant_response": "Which option matters most to you?"}]
    signals = classify_conversation_quality("What are the tradeoffs?", history).quality_signals
    require(signals.current_question_count == 1, "current question not counted")
    require(signals.open_assistant_question_signals == 1, "open assistant question not represented")


def test_appropriateness_lanes_remain_separate() -> None:
    cases = {
        "I feel anxious tonight": "emotional",
        "Actually, I meant Tuesday": "correction",
        "Brainstorm some names for this": "brainstorming",
        "Review conscious_agent/conversation_context.py": "operator",
        "That was funny": "ordinary",
    }
    for message, expected in cases.items():
        profile = classify_conversation_quality(message)
        require(profile.quality_signals.appropriateness_lane == expected, f"wrong lane for {message!r}")


def test_prompt_and_receipt_metrics_are_content_free() -> None:
    history = [{"user_message": "private previous question", "assistant_response": "private previous answer?"}]
    profile = classify_conversation_quality("why?", history)
    receipt = profile.receipt_metrics()
    serialized = json.dumps(receipt, sort_keys=True)
    require("private previous" not in serialized and "why?" not in serialized, "quality receipt leaked conversation content")
    packet = build_conversation_prompt(
        user_message="why?",
        self_model={"name": "Eidolon", "active_goals": []}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history,
        context_size=4096, max_tokens=256,
    )
    require("CONVERSATION QUALITY SIGNALS" in packet.prompt, "quality guidance missing from prompt")
    metrics = packet.metrics.to_dict()
    require(metrics["conversation_quality_relevance"] == "recent_thread_relevant", "quality relevance missing from metrics")
    require(metrics["conversation_open_question_signals"] == 1, "open-question metric missing")


def test_signal_builder_is_provider_free_and_read_only() -> None:
    intent = classify_turn_intent("What do you think?")
    signals = build_conversation_quality_signals("What do you think?", [], intent=intent, short_follow_up=False, operator_context_relevant=False)
    require(signals.writes_state is False and signals.contacts_provider is False, "signal builder crossed provider/state boundary")
    require(signals.contains_message_content is False, "signal summary claims content")


TESTS = [
    ("relevance_distinguishes_current_and_recent_thread", test_relevance_distinguishes_current_and_recent_thread),
    ("clarity_is_bounded_without_invented_context", test_clarity_is_bounded_without_invented_context),
    ("repetition_signal_uses_bounded_structure", test_repetition_signal_uses_bounded_structure),
    ("question_signals_cover_current_and_open_exchange", test_question_signals_cover_current_and_open_exchange),
    ("appropriateness_lanes_remain_separate", test_appropriateness_lanes_remain_separate),
    ("prompt_and_receipt_metrics_are_content_free", test_prompt_and_receipt_metrics_are_content_free),
    ("signal_builder_is_provider_free_and_read_only", test_signal_builder_is_provider_free_and_read_only),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks=[]; passed=0
    for name, fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed+=1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1084.0-conversation-quality-foundation","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report,indent=2)); return 0 if report["ok"] else 1

if __name__ == "__main__": raise SystemExit(main())
