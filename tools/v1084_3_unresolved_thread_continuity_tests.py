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
from conversation_unresolved_threads import build_unresolved_thread_profile


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def fixture_history() -> list[dict[str, str]]:
    return [
        {
            "user_message": "The migration is blocked waiting on owner approval. We still need to finish the manifest.",
            "assistant_response": "I will review the manifest next.",
        },
        {
            "user_message": "The printer stopped working after the update.",
            "assistant_response": "What error code do you see?",
        },
    ]


def test_tracks_required_bounded_thread_kinds() -> None:
    profile = build_unresolved_thread_profile("It says E42.", fixture_history())
    require(profile.unresolved_question_count == 1, "latest assistant question not tracked")
    require(profile.assistant_commitment_signal_count == 1, "bounded commitment signal not tracked")
    require(profile.blocker_count >= 1, "blocker signal not tracked")
    require(profile.unfinished_subject_count >= 1, "unfinished subject not tracked")
    require(len(profile.items) <= 6 and profile.history_rows_considered == 2, "thread evidence not bounded")


def test_current_turn_matches_relevant_open_question() -> None:
    profile = build_unresolved_thread_profile("It says E42.", fixture_history())
    question = [item for item in profile.items if item.kind == "unresolved_question"]
    require(question and question[0].current_turn_match, "answer to latest question was not matched")
    unrelated = build_unresolved_thread_profile("New topic: tell me about soup.", fixture_history())
    require(unrelated.matching_item_count == 0, "unrelated topic inherited unresolved thread")


def test_commitment_signal_never_becomes_execution_proof() -> None:
    profile = build_unresolved_thread_profile("What happened with that?", fixture_history())
    summary = profile.public_summary()
    require(summary["obligations_inferred"] is False, "commitment signal became obligation")
    guidance = "\n".join(profile.prompt_lines()).lower()
    require("not proof of execution" in guidance and "do not claim completion" in guidance, "execution boundary missing")


def test_classifier_is_idempotent_and_provider_free() -> None:
    first = build_unresolved_thread_profile("It says E42.", fixture_history()).public_summary()
    second = build_unresolved_thread_profile("It says E42.", fixture_history()).public_summary()
    require(first == second, "unresolved evidence changed across reload-equivalent classification")
    require(first["writes_state"] is False and first["contacts_provider"] is False, "classifier crossed state/provider boundary")


def test_public_evidence_is_content_free() -> None:
    summary = build_unresolved_thread_profile("Private current answer E42.", fixture_history()).public_summary()
    serialized = json.dumps(summary)
    for secret in ("migration", "owner approval", "printer", "E42", "manifest"):
        require(secret not in serialized, f"thread receipt leaked content: {secret}")
    require(summary["contains_message_content"] is False, "receipt content boundary missing")


def test_prompt_and_metrics_include_thread_continuity() -> None:
    packet = build_conversation_prompt(
        user_message="It says E42.",
        self_model={"name": "Eidolon"}, desires={}, memories=[], project_context="", goal_context="", task_context="",
        conversation_history=fixture_history(), context_size=4096, max_tokens=256,
    )
    require("UNRESOLVED THREAD CONTINUITY" in packet.prompt, "thread guidance missing from prompt")
    require(packet.metrics.conversation_unresolved_thread_count >= 4, "thread count metric missing")
    require(packet.metrics.conversation_matching_unresolved_threads >= 1, "matching thread metric missing")
    require(packet.metrics.conversation_unresolved_questions == 1, "question metric wrong")


def test_no_raw_history_rewrite_or_mutation_surface() -> None:
    before = json.dumps(fixture_history(), sort_keys=True)
    history = fixture_history()
    classify_conversation_quality("It says E42.", history)
    require(json.dumps(history, sort_keys=True) == before, "history was rewritten")
    source = (AGENT / "conversation_unresolved_threads.py").read_text(encoding="utf-8")
    for forbidden in ("requests.", "urllib", "openai", "ollama", "subprocess", "write_text("):
        require(forbidden not in source, f"unresolved classifier contains forbidden mutation/provider surface: {forbidden}")


TESTS = [
    ("tracks_required_bounded_thread_kinds", test_tracks_required_bounded_thread_kinds),
    ("current_turn_matches_relevant_open_question", test_current_turn_matches_relevant_open_question),
    ("commitment_signal_never_becomes_execution_proof", test_commitment_signal_never_becomes_execution_proof),
    ("classifier_is_idempotent_and_provider_free", test_classifier_is_idempotent_and_provider_free),
    ("public_evidence_is_content_free", test_public_evidence_is_content_free),
    ("prompt_and_metrics_include_thread_continuity", test_prompt_and_metrics_include_thread_continuity),
    ("no_raw_history_rewrite_or_mutation_surface", test_no_raw_history_rewrite_or_mutation_surface),
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
    report = {"suite": "v1084.3-unresolved-thread-continuity", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
