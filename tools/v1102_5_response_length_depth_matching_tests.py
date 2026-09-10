from __future__ import annotations

import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]

from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from natural_conversation_adaptation import build_response_length_depth_resolution_profile
import post_review_development_verify as isolated_verify


def require(value, message: str) -> None:
    if not value: raise AssertionError(message)


def resolve(message: str, preference=None):
    quality = classify_conversation_quality(message)
    return build_response_length_depth_resolution_profile(message, quality=quality, response_preferences=preference)


def packet(message: str, preference=None):
    return build_conversation_prompt(
        user_message=message, self_model={"name":"Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=[],
        response_preferences=preference, context_size=8192, max_tokens=768,
    )


def test_explicit_brief_request_beats_detailed_session_preference() -> None:
    value = resolve("Briefly explain how DNS works.", {"mode":"detailed", "format":"steps"})
    require(value.effective_length_mode == "brief", "stored detailed preference beat explicit brief request")
    require(value.resolution_source == "current_turn_explicit" and value.current_turn_wins, "current-turn precedence missing")


def test_explicit_detail_request_beats_concise_session_preference() -> None:
    value = resolve("Walk me through this step-by-step in detail.", {"mode":"concise", "format":"prose"})
    require(value.effective_length_mode == "deep" and value.effective_depth_mode == "structured", "explicit detail request lost")
    require(value.effective_format == "steps", "current structure request did not override stored prose")


def test_session_preference_shapes_substantive_turn() -> None:
    concise = resolve("Explain why the API route failed.", {"mode":"concise", "format":"prose"})
    detailed = resolve("Explain why the API route failed.", {"mode":"detailed", "format":"steps"})
    require(concise.resolution_source == "session_preference" and concise.effective_length_mode == "concise", "concise session preference not applied")
    require(detailed.resolution_source == "session_preference" and detailed.effective_length_mode == "detailed", "detailed session preference not applied")
    require(detailed.target_max_words >= concise.target_max_words, "detailed target did not expand")


def test_light_turn_is_not_padded_by_detailed_preference() -> None:
    greeting = resolve("Hello", {"mode":"detailed", "format":"steps"})
    playful = resolve("You're cute.", {"mode":"detailed", "format":"steps"})
    require(greeting.light_turn_protected and greeting.effective_length_mode == "brief", "greeting became an essay")
    require(playful.light_turn_protected and playful.effective_length_mode == "brief", "playful turn became an essay")


def test_current_structure_request_beats_stored_format() -> None:
    prose = resolve("Explain it in plain prose with no bullets.", {"mode":"technical", "format":"steps"})
    bullets = resolve("Give me a short bullet list.", {"mode":"default", "format":"prose"})
    require(prose.explicit_current_structure_cue and prose.effective_format == "prose", "no-bullets request lost")
    require(bullets.explicit_current_structure_cue and bullets.effective_format == "bullets", "bullet request lost")


def test_prompt_metrics_are_resolved_content_free_and_registered_once() -> None:
    value = packet("Give me a detailed explanation.", {"mode":"concise", "format":"prose"})
    require("RESPONSE LENGTH AND DEPTH RESOLUTION" in value.prompt, "integrated resolution block missing")
    require(value.metrics.natural_response_effective_length == "deep", "effective length metric wrong")
    require(value.metrics.natural_response_resolution_source == "current_turn_explicit", "resolution source metric wrong")
    profile = resolve("Explain it.", {"mode":"technical", "format":"steps"}).public_summary()
    require(profile["contains_message_content"] is False and not profile["writes_state"] and not profile["contacts_provider"], "response receipt crossed boundary")
    require(not profile["mutates_personality"] and not profile["word_targets_are_quotas"], "response profile mutated personality or enforced quotas")
    names = [suite.name for suite in isolated_verify.SUITES]
    require(names.count("v1102.5-response-length-depth-matching") == 1, "suite registration wrong")


TESTS=[(name.removeprefix("test_"),fn) for name,fn in list(globals().items()) if name.startswith("test_")]

def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed += 1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1102.5-response-length-depth-matching","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report, indent=2)); return 0 if report["ok"] else 1

if __name__ == "__main__": raise SystemExit(main())
