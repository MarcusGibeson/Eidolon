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


def test_explicit_recent_callback_is_selected() -> None:
    history = [{"user_message": "The chair keeps squeaking.", "assistant_response": "Tighten the seat bolts first."}]
    profile = classify_conversation_quality("What about that?", history).callbacks
    require(profile.explicit_callback_cue and profile.selected_count >= 1, "explicit recent callback not selected")
    require(all(candidate.turn_offset == 0 for candidate in profile.candidates), "callback escaped latest turn")


def test_relevant_older_topic_callback_is_selected() -> None:
    history = [
        {"user_message": "I am planning a vegetable garden with tomatoes and basil.", "assistant_response": "Use a sunny, well-drained bed."},
        {"user_message": "My printer is showing an error.", "assistant_response": "Check its status panel."},
    ]
    quality = classify_conversation_quality("How much sun do the tomatoes need?", history)
    require(quality.topic_transition.transition_kind == "resumption", "older topic was not resumed")
    require(any(candidate.turn_offset == 1 for candidate in quality.callbacks.candidates), "older relevant callback missing")


def test_unrelated_topic_does_not_force_callback() -> None:
    history = [{"user_message": "The chair keeps squeaking.", "assistant_response": "Tighten the bolts."}]
    profile = classify_conversation_quality("New topic: what is the capital of Norway?", history).callbacks
    require(profile.selected_count == 0, "unrelated turn forced callback")


def test_correction_does_not_callback_stale_assistant_claim() -> None:
    history = [{"user_message": "The meeting is Thursday.", "assistant_response": "Thursday is confirmed."}]
    profile = classify_conversation_quality("Actually, it is Tuesday, not Thursday.", history).callbacks
    require(profile.selected_count >= 1, "correction lost useful user callback")
    require(all(candidate.source_role != "assistant" for candidate in profile.candidates), "stale assistant claim reintroduced")


def test_stale_history_and_emotional_inflation_are_blocked() -> None:
    history = [
        {"user_message": "My old bicycle is blue.", "assistant_response": "Blue is a practical color."},
        *[
            {"user_message": f"Recent unrelated topic {index} about cooking.", "assistant_response": "Here is a cooking answer."}
            for index in range(6)
        ],
    ]
    profile = classify_conversation_quality("Back to my old blue bicycle.", history).callbacks
    require(all(candidate.turn_offset <= 5 for candidate in profile.candidates), "stale callback exceeded bounded window")
    require(profile.stale_callback_allowed is False, "stale callbacks allowed")
    require(profile.forced_emotional_significance is False, "callback assigned emotional significance")
    require(profile.recap_allowed is False, "callback allowed recap")


def test_callback_evidence_is_content_free_and_provider_free() -> None:
    history = [{"user_message": "My private code is cedar.", "assistant_response": "I noted the topic."}]
    profile = classify_conversation_quality("What about that?", history).callbacks
    serialized = json.dumps(profile.public_summary())
    require("cedar" not in serialized and "private code" not in serialized, "callback receipt leaked content")
    require(profile.writes_state is False and profile.contacts_provider is False, "callback classifier crossed boundary")


def test_prompt_uses_minimal_callback_guidance_and_metrics() -> None:
    history = [{"user_message": "The chair keeps squeaking.", "assistant_response": "Tighten the seat bolts first."}]
    packet = build_conversation_prompt(
        user_message="What about that?", self_model={"name": "Eidolon"}, desires={}, memories=[], project_context="", goal_context="", task_context="",
        conversation_history=history, context_size=4096, max_tokens=256,
    )
    require("NATURAL CONVERSATIONAL CALLBACKS" in packet.prompt, "callback prompt block missing")
    require("minimum detail" in packet.prompt and "Do not recap" in packet.prompt, "minimal callback boundary missing")
    require(packet.metrics.conversation_callbacks_selected >= 1, "callback metric missing")


TESTS = [
    ("explicit_recent_callback_is_selected", test_explicit_recent_callback_is_selected),
    ("relevant_older_topic_callback_is_selected", test_relevant_older_topic_callback_is_selected),
    ("unrelated_topic_does_not_force_callback", test_unrelated_topic_does_not_force_callback),
    ("correction_does_not_callback_stale_assistant_claim", test_correction_does_not_callback_stale_assistant_claim),
    ("stale_history_and_emotional_inflation_are_blocked", test_stale_history_and_emotional_inflation_are_blocked),
    ("callback_evidence_is_content_free_and_provider_free", test_callback_evidence_is_content_free_and_provider_free),
    ("prompt_uses_minimal_callback_guidance_and_metrics", test_prompt_uses_minimal_callback_guidance_and_metrics),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks = []
    passed = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1084.4-natural-conversational-callbacks", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
