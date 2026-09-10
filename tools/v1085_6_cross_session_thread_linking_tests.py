from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path[:0] = [str(AGENT), str(TOOLS)]

from context_cross_session_linking import (
    cross_session_evidence_contains_private_fields,
    link_cross_session_threads,
)
from conversation_context import build_conversation_prompt
import post_review_development_verify as verify
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def sessions() -> list[dict]:
    return [
        {
            "id": "session-atlas",
            "title": "Atlas launch planning",
            "status": "active",
            "thread_key": "atlas",
            "turns": [
                {
                    "user_message": "We discussed the Atlas launch plan.",
                    "assistant_response": "The beta milestone remains open.",
                    "completion_state": "completed",
                    "success": True,
                    "thread_key": "atlas",
                },
                {
                    "user_message": "This request later failed.",
                    "assistant_response": "Partial provider text",
                    "completion_state": "failed",
                    "success": False,
                },
            ],
        }
    ]


def test_explicit_return_with_strong_match_links_complete_turn() -> None:
    rows, evidence = link_cross_session_threads(
        "Return to the Atlas launch plan.", "session-current", sessions()
    )
    require(len(rows) == 1, "explicit return did not link the related completed turn")
    require(evidence.linked_session_count == 1, "linked session count is wrong")
    require(rows[0].evidence_kind == "explicit_return_with_bounded_match", "wrong evidence kind")


def test_unrelated_ordinary_message_does_not_link() -> None:
    rows, evidence = link_cross_session_threads(
        "Tell me what to make for lunch.", "session-current", sessions()
    )
    require(not rows and evidence.linked_turn_count == 0, "unrelated session leaked into context")


def test_explicit_session_or_thread_identity_is_authoritative() -> None:
    rows, _evidence = link_cross_session_threads(
        "Continue there.",
        "session-current",
        sessions(),
        explicit_session_id="session-atlas",
    )
    require(len(rows) == 1 and rows[0].explicit_link, "explicit session identity did not link")


def test_failed_or_partial_cross_session_turns_are_excluded() -> None:
    rows, evidence = link_cross_session_threads(
        "Return to the failed request.",
        "session-current",
        sessions(),
        explicit_session_id="session-atlas",
    )
    require(len(rows) == 1, "failed turn entered the eligible linked set")
    require(evidence.candidate_turn_count == 1, "failed turn counted as a complete candidate")


def test_linked_turn_is_admitted_once_without_merging_sessions() -> None:
    packet = build_conversation_prompt(
        user_message="Return to the Atlas launch plan.",
        self_model={"name": "Eidolon"},
        desires={},
        memories=[],
        project_context="",
        goal_context="",
        task_context="",
        conversation_history=[],
        current_session_id="session-current",
        cross_session_sessions=sessions(),
        context_size=8192,
        max_tokens=256,
    )
    require(packet.prompt.count("RELATED SESSION TURN") == 1, "linked turn not admitted exactly once")
    require(packet.prompt.count("The beta milestone remains open") == 1, "linked content missing or duplicated")
    require(packet.metrics.context_cross_session_turns_included == 1, "admission metric is wrong")


def test_evidence_is_content_free_provider_free_and_non_mutating() -> None:
    _rows, evidence = link_cross_session_threads(
        "Return to the Atlas launch plan.", "session-current", sessions()
    )
    summary = evidence.public_summary()
    require(not cross_session_evidence_contains_private_fields(summary), "link evidence leaked content")
    require(not evidence.provider_invoked and not evidence.writes_state, "linker invoked provider or wrote state")
    require(not evidence.merges_sessions and not evidence.rewrites_history, "linker changed session authority")


def test_release_metadata_and_registration_are_exact() -> None:
    names = [suite.name for suite in verify.select_suites("core")]
    require(names.count("v1085.6-cross-session-thread-linking") == 1, "suite registration is not exact")
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1085, 8), "runtime regressed before v1085.8")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime tag is inconsistent")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1085.8 Context Inspection Console" in history, "v1085.8 historical evidence missing")


TESTS = [
    ("explicit_return_with_strong_match_links_complete_turn", test_explicit_return_with_strong_match_links_complete_turn),
    ("unrelated_ordinary_message_does_not_link", test_unrelated_ordinary_message_does_not_link),
    ("explicit_session_or_thread_identity_is_authoritative", test_explicit_session_or_thread_identity_is_authoritative),
    ("failed_or_partial_cross_session_turns_are_excluded", test_failed_or_partial_cross_session_turns_are_excluded),
    ("linked_turn_is_admitted_once_without_merging_sessions", test_linked_turn_is_admitted_once_without_merging_sessions),
    ("evidence_is_content_free_provider_free_and_non_mutating", test_evidence_is_content_free_provider_free_and_non_mutating),
    ("release_metadata_and_registration_are_exact", test_release_metadata_and_registration_are_exact),
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
    report = {
        "suite": "v1085.6-cross-session-thread-linking",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
