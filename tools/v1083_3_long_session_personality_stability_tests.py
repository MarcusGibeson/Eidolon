from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

from conversation_context import build_conversation_prompt
from personality_stability import build_personality_stability_snapshot
from relationship_continuity import build_relationship_continuity_snapshot
from relationship_personality_continuity import classify_relationship_personality_continuity
import post_review_development_verify as isolated_verify


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def history_fixture() -> list[dict[str, str]]:
    rows = []
    for index in range(8):
        rows.append({
            "user_message": f"ordinary message {index}",
            "assistant_response": "I hear you and I understand the situation." if index < 4 else "As an AI, I do not have memories.",
            "continuity_lane": "ordinary" if index % 2 == 0 else "relational",
        })
    return rows


def test_bounded_history_detects_repetition_and_identity_reset() -> None:
    snapshot = build_personality_stability_snapshot(history_fixture() * 3)
    require(snapshot.history_rows_considered == 12, "history bound not enforced")
    require(snapshot.repeated_opening_runs >= 1, "repeated opening run not detected")
    require(snapshot.identity_reset_signals >= 1, "identity reset signal not detected")
    require(snapshot.drift_risk in {"identity_reset_risk", "repetition_or_tone_drift_risk"}, "drift risk missing")


def test_stability_summary_is_content_free_and_read_only() -> None:
    snapshot = build_personality_stability_snapshot(history_fixture())
    summary = snapshot.public_summary()
    serialized = json.dumps(summary)
    require(summary["writes_state"] is False and summary["mutates_personality"] is False, "guard claims mutation")
    require(summary["contains_message_content"] is False, "content-free flag missing")
    require("ordinary message" not in serialized and "As an AI" not in serialized, "history content leaked")


def test_relationship_profile_includes_one_stability_guard() -> None:
    profile = classify_relationship_personality_continuity("Tell me what you think.", history_fixture())
    prompt = profile.to_prompt_block()
    require(prompt.count("LONG-SESSION PERSONALITY STABILITY") == 1, "stability block count wrong")
    require("Do not reset identity" in prompt and "do not repeat stock openings" in prompt, "guard instructions missing")
    metrics = profile.receipt_metrics()
    require(metrics["personality_stability"]["contains_message_content"] is False, "profile metrics leaked content")


def test_prompt_metrics_expose_only_bounded_stability_counts() -> None:
    history = history_fixture()
    profile = classify_relationship_personality_continuity("Continue naturally.", history)
    relationship = build_relationship_continuity_snapshot([], {"name": "Eidolon", "current_state": {}}, user_message="Continue naturally.", interaction_profile=profile)
    packet = build_conversation_prompt(
        user_message="Continue naturally.", self_model={"name": "Eidolon", "current_state": {}}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history,
        relationship_context=relationship, continuity_profile=profile, context_size=4096, max_tokens=256,
    )
    require(packet.prompt.count("LONG-SESSION PERSONALITY STABILITY") == 1, "prompt stability block wrong")
    metrics = packet.metrics.to_dict()
    require(metrics["personality_history_rows_considered"] == len(history), "history count missing")
    require(metrics["personality_identity_reset_signals"] >= 1, "identity count missing")
    require("ordinary message" not in json.dumps(metrics), "metrics leaked message content")


def test_guard_preserves_operator_and_relationship_boundaries() -> None:
    operator = classify_relationship_personality_continuity("Check the project status", history_fixture())
    relational = classify_relationship_personality_continuity("I missed you", history_fixture())
    require(operator.lane == "operator", "operator lane changed")
    require(relational.lane == "relational", "relational lane changed")
    require(operator.personality_stability is not None and relational.personality_stability is not None, "guard missing by lane")
    require("do not use personal continuity cues" in operator.to_prompt_block().lower(), "operator boundary weakened")
    require("without escalating intimacy" in relational.to_prompt_block().lower(), "relational boundary weakened")


def test_registration_is_exactly_once() -> None:
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1083.3-long-session-personality-stability") == 1, "core registration wrong")
    require(full.count("v1083.3-long-session-personality-stability") == 1, "full registration wrong")
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count("v1083_3_long_session_personality_stability_tests.py") == 1, "release registration wrong")


TESTS = [
    ("bounded_history_detects_repetition_and_identity_reset", test_bounded_history_detects_repetition_and_identity_reset),
    ("stability_summary_is_content_free_and_read_only", test_stability_summary_is_content_free_and_read_only),
    ("relationship_profile_includes_one_stability_guard", test_relationship_profile_includes_one_stability_guard),
    ("prompt_metrics_expose_only_bounded_stability_counts", test_prompt_metrics_expose_only_bounded_stability_counts),
    ("guard_preserves_operator_and_relationship_boundaries", test_guard_preserves_operator_and_relationship_boundaries),
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
    report = {"suite": "v1083.3-long-session-personality-stability", "ok": passed == len(checks), "status": "pass" if passed == len(checks) else "fail", "passed": passed, "total": len(checks), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
