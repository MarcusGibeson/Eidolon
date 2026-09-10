from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(TOOLS))

from conversation_context import build_conversation_prompt
from natural_conversation_foundation import build_identity_relationship_prompt_profile


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def continuity(lane: str = "ordinary", allowed: bool = True):
    return SimpleNamespace(lane=lane, relationship_cues_allowed=allowed)


def relationship(count: int = 0):
    return SimpleNamespace(cue_count=count)


def packet(message: str, history=(), lane: str = "ordinary"):
    profile = SimpleNamespace(
        lane=lane,
        relationship_cues_allowed=lane != "operator",
        relationship_memory_policy="explicit_curation_only",
        personality_stability=None,
        to_prompt_block=lambda: "PERSONALITY AND RELATIONSHIP CONTINUITY\nUse explicit cues only.",
    )
    return build_conversation_prompt(
        user_message=message,
        self_model={"name": "Eidolon"},
        desires={},
        memories=[],
        project_context="",
        goal_context="",
        task_context="",
        conversation_history=history,
        continuity_profile=profile,
        context_size=8192,
        max_tokens=512,
    )


def test_configured_identity_is_stable_and_bounded() -> None:
    profile = build_identity_relationship_prompt_profile(
        {"name": "Eidolon"}, continuity(), relationship(2), []
    )
    require(profile.configured_name == "Eidolon", "configured name lost")
    require(profile.self_introduction_allowed, "first conversation should permit a bounded introduction")
    block = profile.prompt_block()
    require("same configured local AI companion" in block, "identity continuity contract missing")
    require("proven consciousness" in block and "relationship progress" in block, "grounding boundary missing")


def test_existing_history_suppresses_reintroduction() -> None:
    history = [{"user_message": "We were talking about my garden.", "assistant_response": "Tomatoes need full sun."}]
    profile = build_identity_relationship_prompt_profile(
        {"name": "Eidolon"}, continuity(), relationship(), history
    )
    require(profile.history_available and not profile.self_introduction_allowed, "history did not suppress reintroduction")
    require("Do not reintroduce yourself" in profile.prompt_block(), "prompt lacks reintroduction suppression")


def test_operator_lane_suppresses_relationship_cues() -> None:
    profile = build_identity_relationship_prompt_profile(
        {"name": "Eidolon"}, continuity("operator", False), relationship(3), []
    )
    require(profile.interaction_lane == "operator", "operator lane lost")
    require(not profile.relationship_cues_allowed, "operator lane allowed relationship cues")
    require("suppress personal relationship cues" in profile.prompt_block(), "operator relationship boundary missing")


def test_relational_lane_is_user_led_without_inflation() -> None:
    profile = build_identity_relationship_prompt_profile(
        {"name": "Eidolon"}, continuity("relational", True), relationship(1), []
    )
    block = profile.prompt_block()
    require("The user led a relational turn" in block, "user-led relationship guidance missing")
    require(not profile.invented_relationship_progress_allowed, "relationship inflation became allowed")
    require(not profile.transcript_inference_allowed, "transcript inference became allowed")


def test_prompt_integration_and_metrics_are_content_free() -> None:
    packet_value = packet("What do you think about this idea?")
    require("IDENTITY AND RELATIONSHIP FOUNDATION" in packet_value.prompt, "identity foundation absent from prompt")
    metrics = packet_value.metrics.to_dict()
    require(metrics["natural_identity_interaction_lane"] == "ordinary", "identity lane metric missing")
    require(metrics["natural_identity_relationship_cue_count"] == 0, "unexpected relationship cue count")
    require("What do you think" not in json.dumps({key: value for key, value in metrics.items() if key.startswith("natural_identity")}), "message leaked into metrics")


def test_foundation_is_provider_free_and_read_only() -> None:
    summary = build_identity_relationship_prompt_profile(
        {"name": "Eidolon"}, continuity(), relationship(), []
    ).public_summary()
    require(summary["writes_state"] is False and summary["contacts_provider"] is False, "foundation crossed runtime boundary")
    require(summary["identity_reset_allowed"] is False, "identity reset was enabled")


TESTS = [
    ("configured_identity_is_stable_and_bounded", test_configured_identity_is_stable_and_bounded),
    ("existing_history_suppresses_reintroduction", test_existing_history_suppresses_reintroduction),
    ("operator_lane_suppresses_relationship_cues", test_operator_lane_suppresses_relationship_cues),
    ("relational_lane_is_user_led_without_inflation", test_relational_lane_is_user_led_without_inflation),
    ("prompt_integration_and_metrics_are_content_free", test_prompt_integration_and_metrics_are_content_free),
    ("foundation_is_provider_free_and_read_only", test_foundation_is_provider_free_and_read_only),
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
    report = {"suite": "v1102.0-identity-relationship-prompt-foundation", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
