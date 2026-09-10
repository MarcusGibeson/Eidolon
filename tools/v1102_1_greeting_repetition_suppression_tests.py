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
from natural_conversation_foundation import build_greeting_repetition_profile


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def packet(message: str, history=()):
    return build_conversation_prompt(
        user_message=message,
        self_model={"name": "Eidolon"},
        desires={}, memories=[], project_context="", goal_context="", task_context="",
        conversation_history=history,
        context_size=8192, max_tokens=512,
    )


def test_first_greeting_is_brief_not_intake() -> None:
    profile = build_greeting_repetition_profile("Hello!", [])
    require(profile.greeting_kind == "first_greeting", "first greeting missed")
    guidance = "\n".join(profile.prompt_lines())
    require("brief natural greeting" in guidance and "intake form" in guidance, "first greeting guidance incomplete")
    require(not profile.suppress_self_introduction, "first turn incorrectly forbade all introduction")


def test_returning_greeting_does_not_reset_identity() -> None:
    history = [{"user_message": "Tell me about basil.", "assistant_response": "Basil likes warmth."}]
    profile = build_greeting_repetition_profile("Hey", history)
    require(profile.greeting_kind == "returning_greeting", "returning greeting missed")
    require(profile.suppress_self_introduction, "returning greeting allowed reintroduction")
    require("ongoing conversation" in "\n".join(profile.prompt_lines()), "ongoing conversation guidance missing")


def test_repeated_greeting_avoids_same_formula() -> None:
    history = [{"user_message": "Hello", "assistant_response": "Hello! Nice to see you."}]
    profile = build_greeting_repetition_profile("Hello again", history)
    require(profile.greeting_kind == "repeated_greeting", "repeated returning greeting missed")
    require(profile.variation_required, "repeated greeting did not require variation")


def test_non_greeting_starts_with_substance() -> None:
    profile = build_greeting_repetition_profile("Why do tomatoes split?", [])
    require(profile.greeting_kind == "none" and profile.suppress_new_greeting, "ordinary turn allowed fresh greeting")
    require("Start with its substance" in "\n".join(profile.prompt_lines()), "substance-first guidance missing")


def test_repeated_stock_openings_are_detected() -> None:
    history = [
        {"user_message": "One", "assistant_response": "Of course, here is one answer."},
        {"user_message": "Two", "assistant_response": "Of course, here is another answer."},
    ]
    profile = build_greeting_repetition_profile("And three?", history)
    require(profile.repeated_opening_runs >= 1, "repeated opening run missed")
    require(profile.variation_required, "opening variation was not required")


def test_prompt_integration_exposes_content_free_metrics() -> None:
    history = [{"user_message": "Hello", "assistant_response": "Hello!"}]
    value = packet("Hello", history)
    require("GREETING AND REPETITION CONTROL" in value.prompt, "greeting control absent from prompt")
    require(value.metrics.natural_greeting_kind == "repeated_greeting", "greeting metric wrong")
    require(value.metrics.natural_greeting_suppress_self_introduction, "self-introduction suppression metric missing")
    summary = build_greeting_repetition_profile("Hello", history).public_summary()
    require(summary["contains_message_content"] is False and summary["writes_state"] is False and summary["contacts_provider"] is False, "greeting receipt crossed boundary")


TESTS = [
    ("first_greeting_is_brief_not_intake", test_first_greeting_is_brief_not_intake),
    ("returning_greeting_does_not_reset_identity", test_returning_greeting_does_not_reset_identity),
    ("repeated_greeting_avoids_same_formula", test_repeated_greeting_avoids_same_formula),
    ("non_greeting_starts_with_substance", test_non_greeting_starts_with_substance),
    ("repeated_stock_openings_are_detected", test_repeated_stock_openings_are_detected),
    ("prompt_integration_exposes_content_free_metrics", test_prompt_integration_exposes_content_free_metrics),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks=[]; passed=0
    for name, fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed+=1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1102.1-greeting-repetition-suppression","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report,indent=2)); return 0 if report["ok"] else 1


if __name__ == "__main__": raise SystemExit(main())
