from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import dashboard_chat_console
from conversation_context import build_conversation_prompt
from emotional_continuity_guard import build_emotional_continuity_guard
from mood_moment_continuity import build_mood_moment_continuity_snapshot
from relationship_continuity import build_relationship_continuity_snapshot
from relationship_personality_continuity import classify_relationship_personality_continuity
import post_review_development_verify as isolated_verify


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def memories_fixture() -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    return [
        {"type": "user_mood", "content": "calm today", "mood_state": "current", "observed_at": now.isoformat(), "relationship_eligible": True},
        {"type": "user_mood", "content": "worried yesterday", "mood_state": "cleared", "observed_at": (now-timedelta(days=1)).isoformat(), "relationship_eligible": True},
        {"type": "user_mood", "content": "angry last month", "observed_at": (now-timedelta(days=40)).isoformat(), "relationship_eligible": True},
        {"type": "important_moment", "content": "finished a difficult milestone", "moment_state": "open", "occurred_at": now.isoformat(), "relationship_eligible": True},
        {"type": "relationship", "content": "values direct conversation", "relationship_eligible": True},
    ]


def test_only_one_current_mood_is_used_and_old_moods_do_not_accumulate() -> None:
    snapshot = build_mood_moment_continuity_snapshot(memories_fixture(), {"current_state": {}}, user_message="How am I doing?")
    require(snapshot.user_mood is not None and snapshot.user_mood.text == "calm today", "current mood not selected")
    require(snapshot.stale_moods_omitted >= 2, "old moods accumulated")
    rendered = "\n".join(snapshot.to_prompt_lines())
    require("worried yesterday" not in rendered and "angry last month" not in rendered, "old mood leaked")


def test_emotional_guard_blocks_affection_and_progress_inflation() -> None:
    for lane in ("ordinary", "operator", "relational", "mixed"):
        guard = build_emotional_continuity_guard(memories_fixture(), interaction_lane=lane)
        require(guard.single_current_mood_only and guard.old_moods_do_not_accumulate, "mood accumulation guard missing")
        require(guard.affection_escalation_allowed is False, "affection escalation allowed")
        require(guard.new_relationship_progress_claim_allowed is False, "relationship progress claim allowed")
        require(guard.user_led_warmth_allowed is (lane in {"relational", "mixed"}), "user-led warmth policy wrong")


def test_relationship_prompt_contains_one_noninflation_guard() -> None:
    profile = classify_relationship_personality_continuity("I missed you", [])
    snapshot = build_relationship_continuity_snapshot(memories_fixture(), {"current_state": {}}, user_message="I missed you", interaction_profile=profile)
    prompt = snapshot.to_prompt_block()
    require(prompt.count("EMOTIONAL CONTINUITY WITHOUT INFLATION") == 1, "emotional guard count wrong")
    require("do not exceed it with unsupported affection" in prompt, "affection boundary missing")
    require("older and cleared moods do not accumulate" in prompt, "mood accumulation boundary missing")
    summary = snapshot.public_summary(include_cues=False)
    require(summary["emotional_guard"]["contains_cue_content"] is False, "guard summary not content-free")


def test_prompt_metrics_remain_content_free_and_block_progress_claims() -> None:
    history = [{"user_message": "I missed you", "assistant_response": "I am glad you are here.", "continuity_lane": "relational"}]
    profile = classify_relationship_personality_continuity("I missed you", history)
    relationship = build_relationship_continuity_snapshot(memories_fixture(), {"name": "Eidolon", "current_state": {}}, user_message="I missed you", interaction_profile=profile)
    packet = build_conversation_prompt(
        user_message="I missed you", self_model={"name": "Eidolon", "current_state": {}}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history,
        relationship_context=relationship, continuity_profile=profile, context_size=4096, max_tokens=256,
    )
    metrics = packet.metrics.to_dict()
    require(metrics["emotional_current_mood_count"] == 1, "current mood count wrong")
    require(metrics["emotional_affection_escalation_allowed"] is False, "metrics allowed affection escalation")
    require(metrics["emotional_progress_claim_allowed"] is False, "metrics allowed relationship progress")
    require("calm today" not in json.dumps(metrics), "mood content leaked into receipt metrics")


def test_operator_lane_suppresses_personal_cues_but_keeps_guard() -> None:
    profile = classify_relationship_personality_continuity("Check the project status", [])
    relationship = build_relationship_continuity_snapshot(memories_fixture(), {"current_state": {}}, user_message="Check the project status", interaction_profile=profile)
    require(profile.lane == "operator", "operator lane not detected")
    require(relationship.cue_count == 0, "operator lane exposed personal cues")
    require(relationship.emotional_guard.affection_escalation_allowed is False, "operator emotional guard missing")
    require("EMOTIONAL CONTINUITY WITHOUT INFLATION" in relationship.to_prompt_block(), "guard omitted in operator lane")


def test_dashboard_presents_guard_without_provider_or_receipt_details() -> None:
    source = Path(dashboard_chat_console.__file__).read_text(encoding="utf-8")
    for token in ("Old moods do not accumulate", "affection escalation blocked", "new relationship-progress claims blocked"):
        require(token in source, f"dashboard guard wording missing: {token}")
    require("raw_events" not in source[source.find("emotional_status"):source.find("emotional_status")+700], "private receipt detail added")


def test_registration_is_exactly_once() -> None:
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1083.4-mood-continuity-without-inflation") == 1, "core registration wrong")
    require(full.count("v1083.4-mood-continuity-without-inflation") == 1, "full registration wrong")
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count("v1083_4_mood_continuity_without_inflation_tests.py") == 1, "release registration wrong")


TESTS = [
    ("only_one_current_mood_is_used_and_old_moods_do_not_accumulate", test_only_one_current_mood_is_used_and_old_moods_do_not_accumulate),
    ("emotional_guard_blocks_affection_and_progress_inflation", test_emotional_guard_blocks_affection_and_progress_inflation),
    ("relationship_prompt_contains_one_noninflation_guard", test_relationship_prompt_contains_one_noninflation_guard),
    ("prompt_metrics_remain_content_free_and_block_progress_claims", test_prompt_metrics_remain_content_free_and_block_progress_claims),
    ("operator_lane_suppresses_personal_cues_but_keeps_guard", test_operator_lane_suppresses_personal_cues_but_keeps_guard),
    ("dashboard_presents_guard_without_provider_or_receipt_details", test_dashboard_presents_guard_without_provider_or_receipt_details),
    ("registration_is_exactly_once", test_registration_is_exactly_once),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            checks.append({"name": name, "status": "pass", "message": ""})
    passed = sum(row["status"] == "pass" for row in checks)
    report = {"suite": "v1083.4-mood-continuity-without-inflation", "ok": passed == len(checks), "status": "pass" if passed == len(checks) else "fail", "passed": passed, "total": len(checks), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
