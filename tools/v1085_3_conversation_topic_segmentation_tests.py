from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

from context_topic_segmentation import segment_conversation_topics, topic_segmentation_contains_private_fields
from conversation_context import build_conversation_prompt
from conversation_topic_transition import classify_topic_transition


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def history() -> list[dict]:
    return [
        {"user_message": "My tomato garden needs wider spacing.", "assistant_response": "Use wide tomato rows."},
        {"user_message": "The tomato seedlings need support stakes.", "assistant_response": "Stake the seedlings early."},
        {"user_message": "The printer toner is nearly empty.", "assistant_response": "Replace the toner cartridge."},
        {"user_message": "The printer tray keeps jamming.", "assistant_response": "Clean the tray rollers."},
    ]


def test_consecutive_unrelated_topics_form_distinct_segments() -> None:
    rows = history()
    transition = classify_topic_transition("Continue with the printer tray problem.", rows)
    selected, plan = segment_conversation_topics("Continue with the printer tray problem.", rows, transition=transition)
    require(plan.segment_count == 2, "unrelated topic groups were not separated")
    require(len(selected) == 2, "active printer segment size wrong")
    require(all("printer" in json.dumps(row).lower() for row in selected), "unrelated garden turn leaked into active segment")


def test_explicit_return_selects_older_matching_segment() -> None:
    rows = history()
    transition = classify_topic_transition("Back to the tomato garden spacing.", rows)
    selected, plan = segment_conversation_topics("Back to the tomato garden spacing.", rows, transition=transition)
    require(plan.selection_reason == "matched_prior_segment", "explicit return did not select matched segment")
    require(len(selected) == 2, "older topic segment incomplete")
    require(all("tomato" in json.dumps(row).lower() or "seedling" in json.dumps(row).lower() for row in selected), "wrong segment selected")


def test_topic_shift_excludes_prior_history_from_prompt() -> None:
    packet = build_conversation_prompt(
        user_message="New topic: explain bicycle tire pressure.", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history(), context_size=4096, max_tokens=256,
    )
    require("tomato garden" not in packet.prompt.lower(), "old garden topic leaked after explicit shift")
    require("printer toner" not in packet.prompt.lower(), "old printer topic leaked after explicit shift")
    require(packet.metrics.context_topic_unrelated_turns_excluded == 4, "topic-shift exclusion evidence wrong")


def test_prompt_return_includes_only_matching_topic() -> None:
    packet = build_conversation_prompt(
        user_message="Go back to the tomato garden spacing.", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history(), context_size=4096, max_tokens=256,
    )
    lowered = packet.prompt.lower()
    require("tomato garden" in lowered, "matching older topic absent")
    require("printer toner" not in lowered and "printer tray" not in lowered, "unrelated newer topic leaked")
    require(packet.metrics.context_topic_active_turn_count == 2, "active segment metrics wrong")


def test_segmentation_is_bounded_and_restart_stable() -> None:
    rows = [
        {"user_message": f"Topic {index} detail unique-{index}", "assistant_response": f"Response unique-{index}"}
        for index in range(50)
    ]
    first_rows, first = segment_conversation_topics("Topic 49 detail", rows)
    second_rows, second = segment_conversation_topics("Topic 49 detail", list(rows))
    require(first.bounded_history_rows == 32, "history segmentation window is not bounded")
    require(first.public_summary() == second.public_summary(), "segmentation changed across restart-equivalent input")
    require(first_rows == second_rows, "selected rows changed across reload")


def test_public_evidence_is_content_free_provider_free_and_read_only() -> None:
    selected, plan = segment_conversation_topics("Return to private tomato details.", history())
    summary = plan.public_summary()
    rendered = json.dumps(summary).lower()
    require(selected, "test fixture selected no topic")
    require("private tomato" not in rendered and "printer toner" not in rendered, "segmentation evidence leaked content")
    require(not topic_segmentation_contains_private_fields(summary), "private field names present")
    require(summary["read_only"] and not summary["provider_invoked"] and not summary["writes_state"], "segmentation mutates state or contacts provider")


def test_metrics_expose_bounded_topic_evidence() -> None:
    packet = build_conversation_prompt(
        user_message="Continue with the printer tray problem.", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history(), context_size=4096, max_tokens=256,
    )
    metrics = packet.metrics.to_dict()
    require(metrics["context_topic_segment_count"] == 2, "segment count metric absent")
    require(metrics["context_topic_unrelated_turns_excluded"] == 2, "excluded-turn metric wrong")
    require(not metrics["context_topic_provider_invoked"], "topic metrics claim provider use")


TESTS = [
    ("consecutive_unrelated_topics_form_distinct_segments", test_consecutive_unrelated_topics_form_distinct_segments),
    ("explicit_return_selects_older_matching_segment", test_explicit_return_selects_older_matching_segment),
    ("topic_shift_excludes_prior_history_from_prompt", test_topic_shift_excludes_prior_history_from_prompt),
    ("prompt_return_includes_only_matching_topic", test_prompt_return_includes_only_matching_topic),
    ("segmentation_is_bounded_and_restart_stable", test_segmentation_is_bounded_and_restart_stable),
    ("public_evidence_is_content_free_provider_free_and_read_only", test_public_evidence_is_content_free_provider_free_and_read_only),
    ("metrics_expose_bounded_topic_evidence", test_metrics_expose_bounded_topic_evidence),
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
    report = {"suite": "v1085.3-conversation-topic-segmentation", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
