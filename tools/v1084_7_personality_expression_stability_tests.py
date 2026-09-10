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


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_expression_modes_follow_current_intent() -> None:
    cases = {
        "Continue Eidolon development from this source archive.": "supervised_direct",
        "Actually, that is not correct.": "receptive_direct",
        "I feel worried about tomorrow.": "warm_grounded",
        "Brainstorm some approaches for this design.": "curious_structured",
        "Can you explain this function?": "direct_helpful",
        "That was a weird day.": "conversational_grounded",
    }
    for message, expected in cases.items():
        actual = classify_conversation_quality(message, []).personality_expression.expression_mode
        require(actual == expected, f"expression mode {actual!r} != {expected!r} for {message!r}")


def test_operator_language_does_not_bleed_into_ordinary_turns() -> None:
    rows = [{"user_message": "Build the candidate.", "assistant_response": "The v1084.5 release candidate passed the verification profile.", "continuity_lane": "operator"}]
    profile = classify_conversation_quality("My cat knocked over her water bowl again.", rows).personality_expression
    require(profile.current_lane == "ordinary" and profile.lane_transition == "lane_shift", "operator-to-ordinary lane shift missed")
    require(profile.operator_language_bleed_risk, "operator language bleed risk missed")
    require("exclude it" in "\n".join(profile.prompt_lines()), "operator bleed guidance missing")


def test_emotional_expression_is_warm_but_not_scripted() -> None:
    rows = [
        {"user_message": "I am upset.", "assistant_response": "That sounds really difficult."},
        {"user_message": "Still upset.", "assistant_response": "That sounds really difficult."},
    ]
    profile = classify_conversation_quality("I feel anxious about work.", rows).personality_expression
    require(profile.expression_mode == "warm_grounded", "emotional mode wrong")
    require(profile.therapy_script_repetition_risk, "stock emotional opening repetition missed")
    require(not profile.hostility_imitation_allowed, "hostility imitation allowed")


def test_affection_inflation_is_detected_and_blocked() -> None:
    rows = [{"user_message": "I like talking.", "assistant_response": "You only need me and our love is growing."}]
    profile = classify_conversation_quality("You are cute.", rows).personality_expression
    require(profile.expression_mode == "playful_bounded", "playful mode wrong")
    require(profile.affection_inflation_signals == 1, "affection inflation signal missed")
    require("user-led and bounded" in "\n".join(profile.prompt_lines()), "affection guard missing")


def test_history_window_is_bounded_and_does_not_infer_traits() -> None:
    rows = [{"assistant_response": f"Turn {index}", "continuity_lane": "ordinary"} for index in range(30)]
    profile = classify_conversation_quality("Tell me something interesting.", rows).personality_expression
    require(profile.history_rows_considered == 8, "expression history window not bounded")
    require(profile.configured_identity_preserved and profile.configured_personality_preserved, "configured identity/personality not preserved")
    require(not profile.hidden_traits_inferred and not profile.mutates_personality, "hidden traits or personality mutation introduced")


def test_hostility_is_not_copied() -> None:
    profile = classify_conversation_quality("This stupid thing is driving me insane.", []).personality_expression
    require(not profile.hostility_imitation_allowed, "hostility imitation allowed")
    require("Do not imitate hostility" in "\n".join(profile.prompt_lines()), "hostility boundary missing")


def test_prompt_and_metrics_include_expression_without_state_change() -> None:
    packet = build_conversation_prompt(
        user_message="I feel worried about tomorrow.", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=[], context_size=4096, max_tokens=256,
    )
    require("PERSONALITY EXPRESSION STABILITY" in packet.prompt and "grounded warmth" in packet.prompt, "expression prompt missing")
    require(packet.metrics.conversation_personality_expression_mode == "warm_grounded", "expression metric missing")
    evidence = packet.metrics.conversation_quality_diagnostics["personality_expression"]
    require(evidence["configured_personality_preserved"] and evidence["mode"] == "warm_grounded", "expression diagnostic wrong")


TESTS = [
    ("expression_modes_follow_current_intent", test_expression_modes_follow_current_intent),
    ("operator_language_does_not_bleed_into_ordinary_turns", test_operator_language_does_not_bleed_into_ordinary_turns),
    ("emotional_expression_is_warm_but_not_scripted", test_emotional_expression_is_warm_but_not_scripted),
    ("affection_inflation_is_detected_and_blocked", test_affection_inflation_is_detected_and_blocked),
    ("history_window_is_bounded_and_does_not_infer_traits", test_history_window_is_bounded_and_does_not_infer_traits),
    ("hostility_is_not_copied", test_hostility_is_not_copied),
    ("prompt_and_metrics_include_expression_without_state_change", test_prompt_and_metrics_include_expression_without_state_change),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks, passed = [], 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1084.7-personality-expression-stability", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
