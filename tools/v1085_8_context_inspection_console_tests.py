from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path[:0] = [str(AGENT), str(TOOLS)]

from api_server import ApiError, handle_api_get, handle_api_post
from context_inspection_console import (
    build_context_inspection_console,
    build_context_inspection_for_session,
    context_inspection_contains_private_fields,
)
from context_stale_summary_detection import content_digest
from conversation_context import build_conversation_prompt
import post_review_development_verify as verify


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def packet():
    old = "The Atlas office is in Dayton."
    return build_conversation_prompt(
        user_message="Return to the Atlas office plan.",
        self_model={"name": "Eidolon"},
        desires={},
        memories=[
            {
                "id": "new-memory",
                "type": "fact",
                "content": "The Atlas office is in Columbus.",
                "importance": "high",
                "provenance": {"origin": "operator_explicit"},
                "superseded_content_digests": [content_digest(old)],
            }
        ],
        continuity_summaries=[
            {"id": "old-summary", "content": old, "content_digest": content_digest(old)},
        ],
        project_context="",
        goal_context="",
        task_context="",
        conversation_history=[
            {"user_message": "Atlas office planning", "assistant_response": "The location needs confirmation."}
        ],
        current_session_id="current",
        cross_session_sessions=[
            {
                "id": "other",
                "title": "Atlas office plan",
                "status": "active",
                "turns": [
                    {
                        "user_message": "We planned the Atlas office move.",
                        "assistant_response": "The move remains open.",
                        "completion_state": "completed",
                        "success": True,
                    }
                ],
            }
        ],
        context_size=8192,
        max_tokens=256,
    )


def test_console_exposes_lane_budget_and_omission_evidence() -> None:
    console = build_context_inspection_console(packet().metrics, session_id="current")
    require(console["read_only"] and console["offline_available"], "console is not read-only/offline-safe")
    require(console["lane_order"] and "allocated_tokens" in console, "lane or budget evidence missing")
    require("inclusion_reasons" in console and "omission_reasons" in console, "admission reasons missing")


def test_console_exposes_topic_ranking_correction_and_provenance_states() -> None:
    console = build_context_inspection_console(packet().metrics)
    require("topic" in console and "ranking" in console and "corrections" in console, "context sections missing")
    require(console["provenance_states"].get("operator_explicit") == 1, "provenance state count missing")


def test_console_exposes_cross_session_and_stale_summary_counts() -> None:
    console = build_context_inspection_console(packet().metrics)
    require(console["cross_session"]["linked_turns"] == 1, "cross-session evidence missing")
    require(console["cross_session"]["turns_included"] == 1, "cross-session admission missing")
    require(console["stale_summaries"]["suppressed"] == 1, "stale-summary evidence missing")


def test_console_contains_no_private_context_or_hidden_reasoning() -> None:
    console = build_context_inspection_console(packet().metrics)
    rendered = json.dumps(console).casefold()
    require(not context_inspection_contains_private_fields(console), "console contains forbidden private fields")
    require("dayton" not in rendered and "columbus" not in rendered, "console leaked context content")
    require(not console["contains_hidden_reasoning"], "console claims hidden reasoning")


def test_session_inspection_remains_available_without_provider() -> None:
    console = build_context_inspection_for_session("missing-session")
    require(console["read_only"] and not console["provider_invoked"], "session inspection contacted provider")
    require(console["session_found"] is False, "missing session was invented")


def test_get_route_is_read_only_and_no_post_route_exists() -> None:
    status, payload = handle_api_get("/api/conversation/context-inspection", {"session_id": ["missing"]})
    require(status == 200 and payload.get("ok"), "GET context inspection route failed")
    try:
        handle_api_post("/api/conversation/context-inspection", {})
    except ApiError as error:
        require(error.status in {404, 405}, "unexpected POST error status")
    else:
        raise AssertionError("context inspection unexpectedly exposes a POST mutation route")


def test_suite_registration_is_exact() -> None:
    names = [suite.name for suite in verify.select_suites("core")]
    require(names.count("v1085.8-context-inspection-console") == 1, "suite registration is not exact")


TESTS = [
    ("console_exposes_lane_budget_and_omission_evidence", test_console_exposes_lane_budget_and_omission_evidence),
    ("console_exposes_topic_ranking_correction_and_provenance_states", test_console_exposes_topic_ranking_correction_and_provenance_states),
    ("console_exposes_cross_session_and_stale_summary_counts", test_console_exposes_cross_session_and_stale_summary_counts),
    ("console_contains_no_private_context_or_hidden_reasoning", test_console_contains_no_private_context_or_hidden_reasoning),
    ("session_inspection_remains_available_without_provider", test_session_inspection_remains_available_without_provider),
    ("get_route_is_read_only_and_no_post_route_exists", test_get_route_is_read_only_and_no_post_route_exists),
    ("suite_registration_is_exact", test_suite_registration_is_exact),
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
        "suite": "v1085.8-context-inspection-console",
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
