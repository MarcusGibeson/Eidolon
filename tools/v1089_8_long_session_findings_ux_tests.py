from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1089c-long-findings-")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import api_server
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_long_session as window
from conversation_sessions import create_conversation_session
import dashboard
import post_review_development_verify as verify


def require(value, message):
    if not value:
        raise AssertionError(message)


def tree_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
            continue
        if any(part in {"__pycache__", ".git", ".venv", "venv"} for part in path.parts):
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


_fixture_cache = None


def large_fixture():
    global _fixture_cache
    if _fixture_cache is not None:
        return _fixture_cache
    session = create_conversation_session("Long finding window fixture", select_session=False)
    evaluation = daily.start_daily_evaluation(session["id"], operator_confirmed=True)
    ids = []
    for index in range(205):
        item = finding.create_evaluation_finding(
            finding_title=f"PRIVATE_LONG_FINDING_{index:03d}",
            finding_details=f"PRIVATE_LONG_DETAILS_{index:03d}",
            issue_domain="session_continuity",
            severity="minor" if index % 2 else "major",
            evaluation_id=evaluation["evaluation_id"],
            operator_confirmed=True,
        )
        ids.append(item["finding_id"])
    _fixture_cache = (evaluation["evaluation_id"], ids)
    return _fixture_cache


def test_initial_window_is_bounded_to_eighty_complete_rows():
    evaluation_id, _ = large_fixture()
    report = window.build_evaluation_finding_window(evaluation_id=evaluation_id)
    require(report["total_matching_findings"] == 205, "total")
    require(report["returned_count"] == report["initial_window_limit"] == 80, "initial limit")
    require(report["offset"] == 0 and report["next_offset"] == 80 and report["has_more"], "paging")
    require(len({row["finding_id"] for row in report["findings"]}) == 80, "complete rows")


def test_earlier_windows_are_bounded_to_one_hundred_twenty():
    evaluation_id, _ = large_fixture()
    first = window.build_evaluation_finding_window(evaluation_id=evaluation_id)
    second = window.build_evaluation_finding_window(evaluation_id=evaluation_id, offset=first["next_offset"])
    third = window.build_evaluation_finding_window(evaluation_id=evaluation_id, offset=second["next_offset"])
    require(second["returned_count"] == second["earlier_window_limit"] == 120, "earlier limit")
    require(second["offset"] == 80 and second["next_offset"] == 200 and second["has_more"], "second page")
    require(third["returned_count"] == 5 and third["next_offset"] == 205 and not third["has_more"], "final page")
    combined = first["findings"] + second["findings"] + third["findings"]
    require(len(combined) == 205 and len({row["finding_id"] for row in combined}) == 205, "coverage")


def test_order_and_digest_are_deterministic():
    evaluation_id, _ = large_fixture()
    first = window.build_evaluation_finding_window(evaluation_id=evaluation_id)
    second = window.build_evaluation_finding_window(evaluation_id=evaluation_id)
    require(first == second, "nondeterministic")
    keys = [(row["updated_at"], row["finding_id"]) for row in first["findings"]]
    require(keys == sorted(keys, reverse=True), "ordering")


def test_filters_isolate_the_requested_evaluation():
    evaluation_id, _ = large_fixture()
    other_session = create_conversation_session("Other finding window", select_session=False)
    other_evaluation = daily.start_daily_evaluation(other_session["id"], operator_confirmed=True)
    finding.create_evaluation_finding(
        finding_title="PRIVATE_OTHER_WINDOW_FINDING",
        issue_domain="interface",
        severity="major",
        evaluation_id=other_evaluation["evaluation_id"],
        operator_confirmed=True,
    )
    report = window.build_evaluation_finding_window(evaluation_id=evaluation_id)
    require(report["total_matching_findings"] == 205, "filter")
    require(all(row["evaluation_id"] == evaluation_id for row in report["findings"]), "foreign row")


def test_window_excludes_private_content_and_authority():
    evaluation_id, _ = large_fixture()
    report = window.build_evaluation_finding_window(evaluation_id=evaluation_id)
    encoded = json.dumps(report, sort_keys=True)
    require("PRIVATE_LONG_FINDING_" not in encoded and "PRIVATE_LONG_DETAILS_" not in encoded, "private content")
    require(not window.finding_window_contains_private_fields(report), "private field")
    for key in (
        "provider_invoked",
        "automatic_task_created",
        "automatic_work_item_created",
        "autonomous_prioritization",
        "patch_generated",
        "patch_applied",
        "approval_granted",
        "rollback_authorized",
        "installation_performed",
        "promotion_performed",
        "release_recommendation_produced",
        "release_certified",
        "writes_state",
    ):
        require(report[key] is False, key)


def test_api_route_returns_bounded_earlier_window():
    evaluation_id, _ = large_fixture()
    status, payload = api_server.handle_api_get(
        "/api/conversation/evaluation-finding-window",
        {"evaluation_id": [evaluation_id], "offset": ["80"], "limit": ["999"]},
    )
    data = payload["data"]
    require(status == 200 and data["returned_count"] == 120, "route")
    require(data["limit"] == data["earlier_window_limit"], "clamp")


def test_dashboard_integrates_load_earlier_without_narrow_overflow():
    html = dashboard.render_evaluation_findings_console()
    for token in (
        "data-long-session-findings-version='v1089.8'",
        "finding-load-earlier",
        "next_offset",
        "has_more",
        "offset = Number",
    ):
        require(token in html, f"missing {token}")
    require("@media(max-width:820px)" in html and "grid-template-columns:1fr" in html, "narrow layout")


def test_window_read_is_source_immutable():
    evaluation_id, _ = large_fixture()
    before = tree_digest()
    window.build_evaluation_finding_window(evaluation_id=evaluation_id, offset=80)
    require(before == tree_digest(), "source mutation")


def test_limits_are_explicit_and_bounded():
    require(window.INITIAL_FINDING_WINDOW == 80, "initial")
    require(window.EARLIER_FINDING_WINDOW == 120, "earlier")
    require(window.MAX_LONG_SESSION_FINDINGS == 256, "maximum")
    evaluation_id, _ = large_fixture()
    report = window.build_evaluation_finding_window(evaluation_id=evaluation_id, offset=-10, limit=9999)
    require(report["offset"] == 0 and report["limit"] == 80, "bounds")


def test_route_and_suite_registration_are_exact():
    source = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
    require(source.count('parts == ["conversation", "evaluation-finding-window"]') == 1, "GET route")
    post = source[source.index("def handle_api_post") :]
    require('parts == ["conversation", "evaluation-finding-window"]' not in post, "POST route")
    names = [suite.name for suite in verify.SUITES]
    require(names.count("v1089.8-long-session-findings-ux") == 1, "registration")
    require(names.index("v1089.8-long-session-findings-ux") < names.index("v1089.7-finding-review-export"), "order")


TESTS = [(name.removeprefix("test_"), function) for name, function in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1089.8-long-session-findings-ux",
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
