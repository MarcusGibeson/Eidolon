from __future__ import annotations

import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]

from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from natural_conversation_adaptation import build_correction_preference_propagation_profile
import post_review_development_verify as isolated_verify
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def packet(message: str, history=(), preference=None):
    return build_conversation_prompt(
        user_message=message, self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history,
        response_preferences=preference, context_size=8192, max_tokens=512,
    )


def test_current_explicit_correction_becomes_authoritative() -> None:
    history = [{"user_message": "What color is it?", "assistant_response": "It is blue."}]
    quality = classify_conversation_quality("Actually, it is green.", history)
    profile = build_correction_preference_propagation_profile("Actually, it is green.", history, quality=quality)
    require(profile.explicit_current_correction and profile.corrected_premise_propagates, "current correction did not propagate")
    require(profile.stale_claim_suppression_required, "stale claim suppression missing")
    require("carry the corrected premise" in "\n".join(profile.prompt_lines()), "future-turn propagation guidance missing")


def test_recent_correction_overrides_older_assistant_claim() -> None:
    history = [
        {"user_message": "What color is it?", "assistant_response": "It is blue."},
        {"user_message": "No, it is green.", "assistant_response": "You're right. It is green."},
    ]
    quality = classify_conversation_quality("Would that color work?", history)
    profile = build_correction_preference_propagation_profile("Would that color work?", history, quality=quality)
    require(profile.recent_correction_count == 1, "recent correction not detected")
    require(profile.corrected_premise_propagates and profile.propagation_scope == "current_conversation", "correction did not remain authoritative")


def test_stored_response_preference_propagates_only_in_session() -> None:
    quality = classify_conversation_quality("Explain the route.")
    profile = build_correction_preference_propagation_profile(
        "Explain the route.", [], quality=quality,
        response_preferences={"mode": "technical", "format": "steps", "revision": 2},
    )
    require(profile.stored_preference_applies, "stored preference not applied")
    require(profile.stored_preference_mode == "technical" and profile.stored_preference_format == "steps", "stored preference changed")
    require(profile.propagation_scope == "current_conversation" and not profile.cross_session_propagation_allowed, "preference escaped session scope")


def test_latest_explicit_request_overrides_stored_length() -> None:
    value = packet("Give me a detailed step-by-step explanation.", preference={"mode": "concise", "format": "prose"})
    require(value.metrics.natural_preference_current_override, "current turn override metric missing")
    require(value.metrics.natural_response_resolution_source == "current_turn_explicit", "stored preference beat latest explicit request")
    require("latest turn's explicit request to override" in value.prompt, "override guidance missing")


def test_casual_wording_is_not_silently_persisted() -> None:
    message = "I prefer tomatoes to peppers."
    quality = classify_conversation_quality(message)
    profile = build_correction_preference_propagation_profile(message, [], quality=quality)
    require(not profile.current_turn_preference_cue, "ordinary personal preference became response-control persistence")
    summary = profile.public_summary()
    require(not summary["automatic_memory_write_allowed"] and not summary["writes_state"], "profile silently persisted preference")
    require(not summary["rewrites_transcript"] and not summary["mutates_global_personality"], "profile crossed mutation boundary")


def test_prompt_metrics_registration_version_and_privacy() -> None:
    value = packet("Actually, keep the explanation short.", [{"user_message": "Explain it.", "assistant_response": "Long answer."}])
    require("CORRECTIONS AND PREFERENCE PROPAGATION" in value.prompt, "integrated propagation block missing")
    require(value.metrics.natural_correction_propagates, "content-free correction metric missing")
    names = [suite.name for suite in isolated_verify.SUITES]
    require(names.count("v1102.3-corrections-preference-propagation") == 1, "suite registration wrong")
    require(tuple(map(int, release_metadata.WORKING_SOURCE_VERSION.split("."))) >= (1102, 3), "working source version not advanced")
    forbidden = ("data/memories.json", "data/tasks.json", "data/approvals/", "data/conversation_runtime/", "data/conversation_sessions/")
    files = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime data present")


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]

def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks=[]; passed=0
    for name, fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed += 1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1102.3-corrections-preference-propagation","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report, indent=2)); return 0 if report["ok"] else 1

if __name__ == "__main__": raise SystemExit(main())
