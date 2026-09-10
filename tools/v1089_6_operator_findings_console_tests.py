from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1089c-console-")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import api_server
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_console as console
import conversation_evaluation_finding_repair_candidates as repairs
import conversation_evaluation_finding_reproducibility as repro
import conversation_evaluation_finding_triage as triage
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


def make_finding(marker: str = "CONSOLE"):
    session = create_conversation_session(f"Finding console {marker}", select_session=False)
    evaluation = daily.start_daily_evaluation(session["id"], operator_confirmed=True)
    item = finding.create_evaluation_finding(
        finding_title=f"PRIVATE_{marker}_TITLE",
        finding_details=f"PRIVATE_{marker}_DETAILS",
        issue_domain="interface",
        severity="major",
        evaluation_id=evaluation["evaluation_id"],
        operator_confirmed=True,
    )
    attempt = repro.record_reproduction_attempt(
        item["finding_id"],
        outcome="reproduced",
        environment_kind="same_environment",
        environment_label=f"PRIVATE_{marker}_ENVIRONMENT",
        note=f"PRIVATE_{marker}_REPRO_NOTE",
        expected_revision=item["revision"],
        operator_confirmed=True,
    )
    refs = repairs.add_repair_candidate_reference(
        item["finding_id"],
        reference_kind="patch_candidate",
        reference_value=f"PRIVATE_{marker}_PATCH_REFERENCE",
        label=f"PRIVATE_{marker}_PATCH_LABEL",
        expected_revision=attempt["finding_revision"],
        operator_confirmed=True,
    )
    review = triage.start_evaluation_finding_triage(
        item["finding_id"],
        note=f"PRIVATE_{marker}_TRIAGE_NOTE",
        expected_revision=refs["finding_revision"],
        operator_confirmed=True,
    )
    review = triage.set_evaluation_finding_triage_disposition(
        item["finding_id"],
        disposition="repair_candidate_review",
        expected_revision=review["finding_revision"],
        operator_confirmed=True,
    )
    return item["finding_id"], evaluation["evaluation_id"]


def test_console_without_selection_is_read_only():
    before = tree_digest()
    report = console.build_evaluation_finding_console_state()
    require(report["selection_status"] == "none_selected", "selection")
    require(report["finding_window"]["window_kind"] == "initial", "initial window")
    require(not report["writes_state"] and report["content_free"] and report["redacted"], "boundary")
    require(before == tree_digest(), "source mutation")


def test_console_combines_redacted_finding_evidence():
    finding_id, evaluation_id = make_finding("CONSOLE_COMBINED")
    report = console.build_evaluation_finding_console_state(
        finding_id=finding_id,
        evaluation_id=evaluation_id,
    )
    require(report["selection_status"] == "available", "selection")
    for key in ("selected_finding", "reproducibility", "repair_candidates", "triage", "aggregation", "finding_window"):
        require(report[key] is not None, f"missing {key}")
    encoded = json.dumps(report, sort_keys=True)
    for secret in (
        "PRIVATE_CONSOLE_COMBINED_TITLE",
        "PRIVATE_CONSOLE_COMBINED_DETAILS",
        "PRIVATE_CONSOLE_COMBINED_ENVIRONMENT",
        "PRIVATE_CONSOLE_COMBINED_REPRO_NOTE",
        "PRIVATE_CONSOLE_COMBINED_PATCH_REFERENCE",
        "PRIVATE_CONSOLE_COMBINED_PATCH_LABEL",
        "PRIVATE_CONSOLE_COMBINED_TRIAGE_NOTE",
    ):
        require(secret not in encoded, f"private value leaked: {secret}")


def test_console_optional_comparison_is_descriptive():
    first, _ = make_finding("CONSOLE_COMPARE_A")
    second, _ = make_finding("CONSOLE_COMPARE_B")
    report = console.build_evaluation_finding_console_state(
        finding_id=first,
        comparison_finding_ids=[first, second],
    )
    comparison = report["comparison"]
    require(comparison and comparison["finding_count"] == 2, "comparison")
    require(not comparison["findings_ranked"] and not comparison["winner_selected"], "ranking")


def test_api_get_console_route_is_provider_free():
    finding_id, evaluation_id = make_finding("CONSOLE_API")
    status, payload = api_server.handle_api_get(
        "/api/conversation/evaluation-finding-console",
        {"finding_id": [finding_id], "evaluation_id": [evaluation_id]},
    )
    data = payload["data"]
    require(status == 200 and data["selection_status"] == "available", "route")
    require(not data["provider_invoked"] and not data["generation_invoked"], "provider")


def test_dashboard_has_explicit_controls_export_and_narrow_layout():
    html = dashboard.render_evaluation_findings_console()
    for token in (
        "data-evaluation-findings-console-version='v1089.6'",
        "/api/conversation/evaluation-finding",
        "operator_confirmed: true",
        "window.confirm",
        "record_reproduction_attempt",
        "add_repair_candidate",
        "set_triage_disposition",
        "/api/conversation/evaluation-finding-review-export",
    ):
        require(token in html, f"missing {token}")
    require("@media(max-width:820px)" in html and "grid-template-columns:1fr" in html, "narrow layout")


def test_dashboard_javascript_has_valid_syntax():
    html = dashboard.render_evaluation_findings_console()
    script = next(
        (item for item in re.findall(r"<script>(.*?)</script>", html, re.S) if "/api/conversation/evaluation-finding-review-export" in item),
        None,
    )
    require(script is not None, "script missing")
    path = Path(tempfile.mkdtemp()) / "findings-console.js"
    path.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, result.stderr)


def test_console_grants_no_task_patch_or_release_authority():
    finding_id, _ = make_finding("CONSOLE_AUTHORITY")
    report = console.build_evaluation_finding_console_state(finding_id=finding_id)
    for key in (
        "automatic_task_created",
        "automatic_work_item_created",
        "autonomous_prioritization",
        "patch_generated",
        "patch_reviewed",
        "patch_applied",
        "approval_granted",
        "rollback_authorized",
        "installation_performed",
        "promotion_performed",
        "release_recommendation_produced",
        "release_certified",
    ):
        require(report[key] is False, f"authority {key}")


def test_mutations_still_require_explicit_confirmation_and_revision():
    session = create_conversation_session("Finding confirmation fixture", select_session=False)
    evaluation = daily.start_daily_evaluation(session["id"], operator_confirmed=True)
    try:
        finding.create_evaluation_finding(
            finding_title="PRIVATE_CONFIRMATION",
            issue_domain="interface",
            severity="major",
            evaluation_id=evaluation["evaluation_id"],
            operator_confirmed=False,
        )
    except finding.EvaluationFindingError:
        pass
    else:
        raise AssertionError("confirmation bypassed")


def test_dashboard_route_and_suite_registration_are_exact():
    source = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
    require(source.count('elif path == "/evaluation-findings-console":') == 1, "dashboard route")
    names = [suite.name for suite in verify.SUITES]
    require(names.count("v1089.6-operator-findings-console") == 1, "registration")
    require(names.index("v1089.6-operator-findings-console") < names.index("v1089.5-bounded-repair-intake-comparison"), "order")


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
        "suite": "v1089.6-operator-findings-console",
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
