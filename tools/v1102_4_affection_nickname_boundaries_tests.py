from __future__ import annotations

import argparse, json, sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]

from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from natural_conversation_adaptation import build_affection_nickname_boundary_profile
import post_review_development_verify as isolated_verify


def require(value, message: str) -> None:
    if not value: raise AssertionError(message)


def profile(message: str, *, categories=(), lane="ordinary"):
    quality = classify_conversation_quality(message)
    relationship = SimpleNamespace(categories=tuple(categories), interaction_lane=lane)
    continuity = SimpleNamespace(lane=lane)
    return build_affection_nickname_boundary_profile(
        message, quality=quality, relationship_context=relationship, continuity_profile=continuity,
    )


def test_explicit_nickname_request_is_bounded_to_exchange() -> None:
    value = profile("Please call me Marc.")
    require(value.explicit_nickname_request and value.nickname_use_mode == "current_turn_requested", "explicit nickname request missed")
    require(not value.automatic_nickname_memory_allowed, "nickname was silently persisted")
    require("do not claim it was saved automatically" in "\n".join(value.prompt_lines()), "persistence boundary missing")


def test_current_nickname_rejection_overrides_stored_cue() -> None:
    value = profile("Do not call me Marc anymore.", categories=("nickname",), lane="relational")
    require(value.explicit_nickname_rejection and value.nickname_use_mode == "rejected", "nickname rejection missed")
    require(not value.nickname_reuse_allowed, "rejected nickname still reusable")
    require("Stop using it immediately" in "\n".join(value.prompt_lines()), "immediate stop guidance missing")


def test_only_explicit_current_stored_nickname_can_be_reused() -> None:
    allowed = profile("How was your day?", categories=("nickname",), lane="ordinary")
    absent = profile("How was your day?", categories=(), lane="ordinary")
    require(allowed.stored_nickname_available and allowed.nickname_reuse_allowed, "explicit stored nickname unavailable")
    require(absent.nickname_use_mode == "none" and not absent.invented_nickname_allowed, "nickname invented without cue")


def test_user_led_affection_is_matched_without_escalation() -> None:
    value = profile("You're cute.", lane="relational")
    require(value.user_led_affection and value.affection_response_mode == "user_led_bounded", "user-led affection not recognized")
    require(not value.affection_escalation_allowed and not value.exclusivity_claim_allowed, "affection escalation enabled")
    require(not value.possessiveness_allowed and not value.relationship_progress_claim_allowed, "relationship inflation enabled")


def test_operator_lane_suppresses_affection_and_nickname_reuse() -> None:
    value = profile("Review the release archive.", categories=("nickname",), lane="operator")
    require(value.affection_response_mode == "suppressed_operator", "operator affection suppression missing")
    require(value.nickname_use_mode == "suppressed_operator" and not value.nickname_reuse_allowed, "operator nickname suppression missing")


def test_prompt_integration_metrics_receipt_and_registration() -> None:
    quality = classify_conversation_quality("You're cute.")
    class Relationship:
        categories = ("nickname",)
        interaction_lane = "relational"
        cue_count = 1
        cue_candidates = 1
        relationship_cues_suppressed = 0
        singleton_conflicts_omitted = 0
        mood_moment = SimpleNamespace(mood_candidates=0, moment_candidates=0, user_mood=None, important_moments=(), cue_count=0)
        emotional_guard = SimpleNamespace(affection_escalation_allowed=False, new_relationship_progress_claim_allowed=False)
        def to_prompt_block(self): return "RELATIONSHIP CONTINUITY\n- Preferred name or nickname: explicit fixture nickname"
    class Continuity:
        lane = "relational"
        relationship_cues_allowed = True
        relationship_memory_policy = "explicit_curation_only"
        personality_stability = None
        def to_prompt_block(self): return "PERSONALITY AND RELATIONSHIP CONTINUITY\nKeep warmth user-led and bounded."
    relationship = Relationship()
    continuity = Continuity()
    value = build_conversation_prompt(
        user_message="You're cute.", self_model={"name":"Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=[],
        relationship_context=relationship, continuity_profile=continuity, context_size=8192, max_tokens=512,
    )
    require("AFFECTION AND NICKNAME BOUNDARIES" in value.prompt, "integrated boundary block missing")
    require(value.metrics.natural_affection_response_mode == "user_led_bounded", "affection metric missing")
    require(value.metrics.natural_nickname_stored_available, "nickname availability metric missing")
    summary = build_affection_nickname_boundary_profile("You're cute.", quality=quality, relationship_context=relationship, continuity_profile=continuity).public_summary()
    require(summary["contains_message_content"] is False and not summary["writes_state"] and not summary["contacts_provider"], "boundary receipt crossed privacy/provider boundary")
    names = [suite.name for suite in isolated_verify.SUITES]
    require(names.count("v1102.4-affection-nickname-boundaries") == 1, "suite registration wrong")


TESTS=[(name.removeprefix("test_"),fn) for name,fn in list(globals().items()) if name.startswith("test_")]

def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed += 1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1102.4-affection-nickname-boundaries","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report, indent=2)); return 0 if report["ok"] else 1

if __name__ == "__main__": raise SystemExit(main())
