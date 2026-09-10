from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(TOOLS))

from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from natural_conversation_foundation import build_intent_topic_continuity_profile
import post_review_development_verify as isolated_verify
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def history():
    return [
        {"user_message": "I want to build a simple webpage for my dog.", "assistant_response": "A single HTML file with a photo and short story would work."},
        {"user_message": "My printer is showing an E42 error.", "assistant_response": "Check whether paper is jammed near the rear tray."},
    ]


def packet(message: str, rows):
    return build_conversation_prompt(
        user_message=message, self_model={"name":"Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=rows,
        context_size=8192, max_tokens=512,
    )


def test_deictic_follow_up_continues_latest_thread() -> None:
    quality = classify_conversation_quality("Would that actually fix it?", history())
    require(quality.topic_transition.transition_kind == "continuation", "deictic follow-up became a topic shift")
    require(quality.topic_transition.deictic_follow_up, "deictic evidence missing")
    profile = build_intent_topic_continuity_profile("Would that actually fix it?", quality)
    require(profile.thread_mode == "active" and profile.matched_turn_offset == 0, "active thread resolution failed")


def test_explicit_topic_shift_wins_over_deictic_words() -> None:
    quality = classify_conversation_quality("New topic: is that tomato variety determinate?", history())
    require(quality.topic_transition.transition_kind == "topic_shift", "explicit shift was overridden")
    require(not quality.topic_transition.deictic_follow_up, "shift falsely marked deictic continuation")


def test_older_topic_resumption_remains_distinct() -> None:
    quality = classify_conversation_quality("Would the dog webpage work well on a phone?", history())
    require(quality.topic_transition.transition_kind == "resumption", "older topic was not resumed")
    require(quality.topic_transition.matched_turn_offset == 1, "wrong earlier turn selected")
    profile = build_intent_topic_continuity_profile("Would the dog webpage work well on a phone?", quality)
    require(profile.thread_mode == "resumed", "resumption profile wrong")


def test_intent_remains_primary_over_topic_context() -> None:
    quality = classify_conversation_quality("Can you explain why that would work?", history())
    profile = build_intent_topic_continuity_profile("Can you explain why that would work?", quality)
    require(profile.primary_intent in {"request", "question"}, "current request intent was lost")
    require(profile.current_turn_primary, "current turn is not primary")
    require(not profile.recap_required and not profile.unrelated_thread_merge_allowed, "unwanted recap or merge enabled")


def test_prompt_contains_integrated_continuity_guidance() -> None:
    value = packet("Would that actually fix it?", history())
    require("INTENT AND TOPIC CONTINUITY" in value.prompt, "integrated continuity guidance missing")
    require("Resolve it from the nearest relevant completed exchange" in value.prompt, "deictic resolution guidance missing")
    require(value.metrics.natural_thread_mode == "active", "thread mode metric missing")
    require(value.metrics.natural_thread_deictic_follow_up, "deictic metric missing")
    require("My printer is showing" in value.prompt, "latest complete exchange was not retained")


def test_profile_receipt_is_content_free_provider_free_and_read_only() -> None:
    quality = classify_conversation_quality("Would that work?", history())
    summary = build_intent_topic_continuity_profile("Would that work?", quality).public_summary()
    require(summary["contains_message_content"] is False, "message content leaked into receipt")
    require(summary["writes_state"] is False and summary["contacts_provider"] is False, "continuity classifier crossed boundary")
    require(tuple(map(int, release_metadata.WORKING_SOURCE_VERSION.split("."))) >= (1102, 2), "working source regressed before v1102.2")
    names = [suite.name for suite in isolated_verify.SUITES]
    for name in (
        "v1102.0-identity-relationship-prompt-foundation",
        "v1102.1-greeting-repetition-suppression",
        "v1102.2-intent-topic-continuity",
    ):
        require(names.count(name) == 1, f"focused verifier registration wrong for {name}")
    forbidden = ("data/memories.json", "data/tasks.json", "data/approvals/", "data/conversation_runtime/", "data/conversation_sessions/")
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime data present in source")


TESTS = [
    ("deictic_follow_up_continues_latest_thread", test_deictic_follow_up_continues_latest_thread),
    ("explicit_topic_shift_wins_over_deictic_words", test_explicit_topic_shift_wins_over_deictic_words),
    ("older_topic_resumption_remains_distinct", test_older_topic_resumption_remains_distinct),
    ("intent_remains_primary_over_topic_context", test_intent_remains_primary_over_topic_context),
    ("prompt_contains_integrated_continuity_guidance", test_prompt_contains_integrated_continuity_guidance),
    ("profile_receipt_is_content_free_provider_free_and_read_only", test_profile_receipt_is_content_free_provider_free_and_read_only),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks=[]; passed=0
    for name, fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed+=1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1102.2-intent-topic-continuity","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report,indent=2)); return 0 if report["ok"] else 1


if __name__ == "__main__": raise SystemExit(main())
