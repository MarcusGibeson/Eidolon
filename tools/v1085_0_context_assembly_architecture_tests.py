from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

from context_assembly_architecture import (
    CONTEXT_LANE_ORDER,
    build_context_assembly_plan,
    context_assembly_contains_private_fields,
)
from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def fake_relationship() -> SimpleNamespace:
    mood = SimpleNamespace(
        user_mood=SimpleNamespace(text="private current mood"),
        important_moments=(SimpleNamespace(text="private important moment"), SimpleNamespace(text="another moment")),
    )
    return SimpleNamespace(mood_moment=mood)


def test_fixed_seven_lane_contract_and_protected_current_turn() -> None:
    quality = classify_conversation_quality("Continue with the project.", [])
    plan = build_context_assembly_plan(
        quality=quality, history_count=0, recent_history_count=0,
        curated_memory_count=0, relationship_context=None,
    )
    require(plan.lane_order == CONTEXT_LANE_ORDER, "context lane order drifted")
    require(len(plan.lanes) == 7, "context architecture does not expose seven lanes")
    require(plan.lane("current_turn").protected, "current turn is not protected")
    require(plan.lane("current_turn").admission_policy == "always_protected", "current-turn policy wrong")


def test_correction_lane_requires_explicit_correction() -> None:
    history = [{"user_message": "Where is the office?", "assistant_response": "It is in Dayton."}]
    explicit = classify_conversation_quality("Actually, it is in Columbus.", history)
    ordinary = classify_conversation_quality("No idea where lunch should be.", history)
    explicit_plan = build_context_assembly_plan(
        quality=explicit, history_count=1, recent_history_count=1, curated_memory_count=0,
    )
    ordinary_plan = build_context_assembly_plan(
        quality=ordinary, history_count=1, recent_history_count=1, curated_memory_count=0,
    )
    require(explicit_plan.lane("correction_evidence").candidate_count == 1, "explicit correction lane missing")
    require(explicit_plan.lane("correction_evidence").protected, "explicit correction lane is not protected")
    require(ordinary_plan.lane("correction_evidence").candidate_count == 0, "ordinary conversation inferred as correction")


def test_active_thread_lane_uses_bounded_match_offset() -> None:
    quality = SimpleNamespace(
        topic_transition=SimpleNamespace(transition_kind="return", matched_turn_offset=7),
        unresolved_threads=SimpleNamespace(items=()),
        correction_handling=SimpleNamespace(explicit_correction=False),
    )
    plan = build_context_assembly_plan(
        quality=quality, history_count=8, recent_history_count=6, curated_memory_count=0,
    )
    require(plan.active_thread_offset == 7, "active-thread offset missing")
    require(plan.lane("active_thread").candidate_count == 1, "active-thread lane not enabled")
    require(plan.lane("active_thread").item_limit == 1, "active-thread lane is unbounded")


def test_mood_and_important_moments_are_distinct_lanes() -> None:
    quality = classify_conversation_quality("Continue naturally.", [])
    plan = build_context_assembly_plan(
        quality=quality, history_count=0, recent_history_count=0,
        curated_memory_count=2, relationship_context=fake_relationship(),
    )
    require(plan.lane("mood").candidate_count == 1, "current mood lane wrong")
    require(plan.lane("important_moments").candidate_count == 2, "important-moment lane wrong")
    require(plan.lane("curated_memory").candidate_count == 2, "curated-memory lane wrong")


def test_prompt_metrics_expose_content_free_lane_evidence() -> None:
    packet = build_conversation_prompt(
        user_message="Explain the garden plan.", self_model={"name": "Eidolon"}, desires={},
        memories=[{"type": "preference", "content": "Private garden preference", "importance": "high"}],
        project_context="", goal_context="", task_context="", conversation_history=[],
        context_size=4096, max_tokens=256,
    )
    metrics = packet.metrics.to_dict()
    require(tuple(metrics["context_lane_order"]) == CONTEXT_LANE_ORDER, "lane metrics absent")
    require(metrics["context_lane_candidates"]["current_turn"] == 1, "current-turn lane count wrong")
    rendered = json.dumps(metrics).lower()
    require("private garden preference" not in rendered, "lane metrics leaked memory content")
    require(not metrics["context_assembly_writes_state"], "assembly metrics claim state writes")


def test_older_active_thread_is_admitted_once_outside_recent_suffix() -> None:
    history = [
        {"user_message": "My tomato garden needs spacing advice.", "assistant_response": "Keep tomato rows well spaced."},
        *[
            {"user_message": f"Unrelated printer detail {index}", "assistant_response": f"Printer response {index}"}
            for index in range(1, 8)
        ],
    ]
    packet = build_conversation_prompt(
        user_message="Go back to the tomato garden spacing topic.", self_model={"name": "Eidolon"}, desires={},
        memories=[], project_context="", goal_context="", task_context="", conversation_history=history,
        context_size=8192, max_tokens=256,
    )
    require(packet.metrics.context_active_thread_offset == 7, "older active thread not identified")
    require(packet.prompt.count("ACTIVE THREAD TURN") == 1, "older active thread not admitted exactly once")
    require(packet.prompt.count("My tomato garden needs spacing advice") == 1, "active thread duplicated")


def test_plan_is_read_only_provider_free_and_private() -> None:
    quality = classify_conversation_quality("Actually, continue the private topic.", [])
    summary = build_context_assembly_plan(
        quality=quality, history_count=4, recent_history_count=4,
        curated_memory_count=3, relationship_context=fake_relationship(),
    ).public_summary()
    require(summary["read_only"] and not summary["provider_invoked"], "plan contacted provider or is not read-only")
    require(not summary["writes_state"] and not summary["mutates_memory"], "plan mutates state")
    require(not context_assembly_contains_private_fields(summary), "plan contains private fields")
    rendered = json.dumps(summary).lower()
    require("private current mood" not in rendered and "private important moment" not in rendered, "plan leaked content")


TESTS = [
    ("fixed_seven_lane_contract_and_protected_current_turn", test_fixed_seven_lane_contract_and_protected_current_turn),
    ("correction_lane_requires_explicit_correction", test_correction_lane_requires_explicit_correction),
    ("active_thread_lane_uses_bounded_match_offset", test_active_thread_lane_uses_bounded_match_offset),
    ("mood_and_important_moments_are_distinct_lanes", test_mood_and_important_moments_are_distinct_lanes),
    ("prompt_metrics_expose_content_free_lane_evidence", test_prompt_metrics_expose_content_free_lane_evidence),
    ("older_active_thread_is_admitted_once_outside_recent_suffix", test_older_active_thread_is_admitted_once_outside_recent_suffix),
    ("plan_is_read_only_provider_free_and_private", test_plan_is_read_only_provider_free_and_private),
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
    report = {"suite": "v1085.0-context-assembly-architecture", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
