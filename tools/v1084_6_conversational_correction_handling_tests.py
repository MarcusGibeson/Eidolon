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


def history() -> list[dict[str, str]]:
    return [
        {"user_message": "What color is the case?", "assistant_response": "The case is blue.", "continuity_lane": "ordinary"},
    ]


def test_explicit_update_targets_latest_assistant_claim() -> None:
    profile = classify_conversation_quality("Actually, the case is green.", history()).correction_handling
    require(profile.explicit_correction, "explicit correction missed")
    require(profile.correction_kind == "factual_update", "factual update kind wrong")
    require(profile.target_scope == "latest_assistant_claim" and profile.target_turn_offset == 0, "correction target wrong")
    require(profile.stale_claim_suppression_required, "stale assistant claim was not suppressed")


def test_clarification_and_replacement_are_distinct() -> None:
    clarification = classify_conversation_quality("I meant Tuesday, not Thursday.", history()).correction_handling
    replacement = classify_conversation_quality("Not blue but green.", history()).correction_handling
    require(clarification.correction_kind == "clarification", "clarification kind missed")
    require(replacement.correction_kind == "explicit_replacement", "replacement kind missed")


def test_ordinary_ambiguity_is_not_a_correction() -> None:
    profile = classify_conversation_quality("No idea what to cook tonight.", history()).correction_handling
    require(not profile.explicit_correction, "ordinary no-prefixed sentence became correction")
    require(profile.correction_kind == "none" and not profile.ambiguous_correction_inferred, "ambiguous correction inferred")


def test_acknowledge_once_without_defense_or_transcript_rewrite() -> None:
    quality = classify_conversation_quality("No, that is not correct. It is green.", history())
    prompt = quality.response_instruction("Eidolon")
    require("CONVERSATIONAL CORRECTION HANDLING" in prompt, "correction guidance missing")
    require("briefly once" in prompt and "without arguing" in prompt, "acknowledgment boundary missing")
    require(not quality.correction_handling.defensive_repetition_allowed, "defensive repetition allowed")
    require(not quality.correction_handling.rewrites_transcript and not quality.correction_handling.mutates_memory, "correction mutated history or memory")


def test_recent_acknowledgment_suppresses_ceremonial_repetition() -> None:
    rows = history() + [{"user_message": "That was wrong.", "assistant_response": "You're right, my mistake. It is green."}]
    profile = classify_conversation_quality("Actually, it is emerald green.", rows).correction_handling
    require(profile.repeated_acknowledgment_risk, "recent correction acknowledgment not detected")
    require("avoid another ceremonial apology" in "\n".join(profile.prompt_lines()), "repeated apology guard missing")


def test_restart_equivalent_classification_is_idempotent() -> None:
    first = classify_conversation_quality("Actually, the case is green.", history()).correction_handling.public_summary()
    second = classify_conversation_quality("Actually, the case is green.", list(history())).correction_handling.public_summary()
    require(first == second, "reload-equivalent correction evidence changed")
    require(not first["contacts_provider"] and not first["writes_state"], "correction classification contacted provider or wrote state")


def test_prompt_context_metrics_are_content_free() -> None:
    packet = build_conversation_prompt(
        user_message="Actually, the case is green.", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history(), context_size=4096, max_tokens=256,
    )
    require(packet.metrics.conversation_correction_kind == "factual_update", "correction metric missing")
    require(packet.metrics.conversation_stale_claim_suppression, "stale suppression metric missing")
    diagnostic = packet.metrics.conversation_quality_diagnostics
    require(diagnostic["correction"]["explicit"] and diagnostic["correction"]["kind"] == "factual_update", "diagnostic correction evidence missing")
    require("blue" not in json.dumps(diagnostic).lower() and "green" not in json.dumps(diagnostic).lower(), "diagnostic exposed correction content")


TESTS = [
    ("explicit_update_targets_latest_assistant_claim", test_explicit_update_targets_latest_assistant_claim),
    ("clarification_and_replacement_are_distinct", test_clarification_and_replacement_are_distinct),
    ("ordinary_ambiguity_is_not_a_correction", test_ordinary_ambiguity_is_not_a_correction),
    ("acknowledge_once_without_defense_or_transcript_rewrite", test_acknowledge_once_without_defense_or_transcript_rewrite),
    ("recent_acknowledgment_suppresses_ceremonial_repetition", test_recent_acknowledgment_suppresses_ceremonial_repetition),
    ("restart_equivalent_classification_is_idempotent", test_restart_equivalent_classification_is_idempotent),
    ("prompt_context_metrics_are_content_free", test_prompt_context_metrics_are_content_free),
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
    report = {"suite": "v1084.6-conversational-correction-handling", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
