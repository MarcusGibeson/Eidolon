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
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1087-9-")

import api_server
import conversation_daily_evaluation as evaluation
import conversation_daily_evaluation_checkpoint as checkpoint
import conversation_evaluation_long_session as long_session
import conversation_evaluation_recovery_scenarios as recovery
import conversation_evaluation_trends as trends
import conversation_sessions as sessions
import dashboard
import post_review_development_verify as verify
import release_metadata

PRIVATE_SENTINEL = "PRIVATE_V1087_9_CHECKPOINT_SENTINEL"


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def source_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".git", ".venv", "venv"} for part in path.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def runtime_digest() -> str:
    root = Path(os.environ["EIDOLON_DATA_DIR"])
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def area(report: dict, name: str) -> dict:
    return next(row for row in report["areas"] if row["name"] == name)


def make_evaluation(*, complete_coverage: bool = True, state: str = "completed") -> dict:
    session = sessions.create_conversation_session(title="Daily evaluation checkpoint fixture")
    item = evaluation.start_daily_evaluation(session["id"], operator_confirmed=True)
    signals = []
    if complete_coverage:
        signals = sorted(set(long_session.REQUIRED_LONG_SESSION_SIGNALS) | set(recovery.REQUIRED_RECOVERY_SIGNALS))
    else:
        signals = ["consecutive_use", "provider_outage"]
    item = evaluation.record_operator_observation(
        item["evaluation_id"],
        ratings={"continuity": 5, "relevance": 4, "tone": 4, "responsiveness": 5, "recovery": 4, "usability": 5},
        note=PRIVATE_SENTINEL,
        signals=signals,
        issue_domain="interface",
        severity="minor",
        reproducible=True,
        expected_revision=item["revision"],
        operator_confirmed=True,
    )
    if state in {"completed", "aborted"}:
        item = evaluation.finish_daily_evaluation(
            item["evaluation_id"],
            state=state,
            expected_revision=item["revision"],
            operator_confirmed=True,
        )
    item["fixture_session_id"] = session["id"]
    return item


def test_checkpoint_without_selection_is_ready_and_bounded() -> None:
    report = checkpoint.build_daily_evaluation_checkpoint()
    require(report["checkpoint_status"] == "ready_for_operator_daily_evaluation", "checkpoint not ready")
    require(report["area_count"] == checkpoint.CHECKPOINT_AREA_COUNT == 15, "area count")
    require(report["ready_area_count"] == 15 and report["review_required_area_count"] == 0, "area states")
    require(report["selected_evaluation_status"] == "none_selected", "selection status")


def test_checkpoint_area_names_cover_complete_arc() -> None:
    names = {row["name"] for row in checkpoint.build_daily_evaluation_checkpoint()["areas"]}
    required = {
        "conversation_readiness_bridge", "operator_observation_capture", "session_outcome_classification",
        "privacy_safe_reproduction_packets", "bounded_longitudinal_trends",
        "restart_and_session_resumption_evaluation", "provider_outage_return_and_no_replay",
        "interruption_retry_regeneration_resend", "long_session_daily_use_evaluation",
        "desktop_alpha_evaluation_console", "privacy_safe_review_export",
        "revision_multi_tab_and_exactly_once_safety", "provider_free_non_autonomous_evaluation",
        "private_runtime_source_only_and_redaction", "operator_authority_and_release_boundary",
    }
    require(names == required, "checkpoint arc coverage changed")


def test_selected_complete_evaluation_consolidates_evidence() -> None:
    item = make_evaluation()
    report = checkpoint.build_daily_evaluation_checkpoint(
        evaluation_id=item["evaluation_id"], session_id=item["fixture_session_id"]
    )
    require(report["selected_evaluation_status"] == "available", "selected evaluation unavailable")
    require(report["selected_evaluation_state"] == "completed", "state")
    require(report["selected_outcome"] == "reproducible_defect", "outcome")
    require(area(report, "restart_and_session_resumption_evaluation")["metrics"]["coverage_status"] == "complete", "recovery")
    require(area(report, "long_session_daily_use_evaluation")["metrics"]["coverage_status"] == "complete", "long session")
    require(area(report, "privacy_safe_review_export")["metrics"]["review_digest"], "review digest")


def test_incomplete_evaluation_is_reported_honestly() -> None:
    item = make_evaluation(complete_coverage=False)
    report = checkpoint.build_daily_evaluation_checkpoint(evaluation_id=item["evaluation_id"])
    require(area(report, "restart_and_session_resumption_evaluation")["metrics"]["coverage_status"] == "incomplete", "recovery inflation")
    require(area(report, "long_session_daily_use_evaluation")["metrics"]["coverage_status"] == "incomplete", "long-session inflation")
    require(report["checkpoint_status"] == "ready_for_operator_daily_evaluation", "contract should remain ready")


def test_missing_evaluation_is_bounded_not_found() -> None:
    report = checkpoint.build_daily_evaluation_checkpoint(evaluation_id="daily_eval_20260721T000000_aaaaaaaaaaaa")
    require(report["selected_evaluation_status"] == "not_found", "missing selection")
    require(report["selected_evaluation_id"] == "", "missing id exposed")
    require(report["checkpoint_status"] == "ready_for_operator_daily_evaluation", "contract downgraded")


def test_private_note_and_content_never_enter_checkpoint() -> None:
    item = make_evaluation()
    report = checkpoint.build_daily_evaluation_checkpoint(evaluation_id=item["evaluation_id"])
    encoded = json.dumps(report, sort_keys=True)
    require(PRIVATE_SENTINEL not in encoded, "private note leaked")
    require(not checkpoint.daily_evaluation_checkpoint_contains_private_fields(report), "private field detected")


def test_checkpoint_is_deterministic_for_equivalent_state() -> None:
    item = make_evaluation()
    first = checkpoint.build_daily_evaluation_checkpoint(evaluation_id=item["evaluation_id"])
    second = checkpoint.build_daily_evaluation_checkpoint(evaluation_id=item["evaluation_id"])
    require(first == second, "checkpoint output changed")
    require(first["contract_digest"] == second["contract_digest"], "contract digest")
    require(first["evidence_digest"] == second["evidence_digest"], "evidence digest")
    require(first["areas_digest"] == second["areas_digest"], "areas digest")


def test_checkpoint_reads_runtime_without_mutating_it() -> None:
    item = make_evaluation()
    before = runtime_digest()
    checkpoint.build_daily_evaluation_checkpoint(evaluation_id=item["evaluation_id"])
    after = runtime_digest()
    require(before == after, "checkpoint mutated runtime state")


def test_checkpoint_does_not_mutate_source_tree() -> None:
    item = make_evaluation()
    before = source_digest()
    checkpoint.build_daily_evaluation_checkpoint(evaluation_id=item["evaluation_id"])
    require(before == source_digest(), "checkpoint mutated source")


def test_outcome_probe_preserves_distinct_classifications() -> None:
    metrics = area(checkpoint.build_daily_evaluation_checkpoint(), "session_outcome_classification")["metrics"]
    require(metrics["probe_outcomes"] == {
        "successful_session": "successful_session",
        "minor_friction": "minor_friction",
        "reproducible_defect": "reproducible_defect",
        "provider_failure": "provider_failure",
        "operator_aborted": "operator_aborted",
    }, "classification identities collapsed")
    require(not metrics["note_text_inspected"] and not metrics["transcript_inspected"], "private inspection")


def test_trends_use_current_outcome_field() -> None:
    make_evaluation()
    report = trends.build_daily_evaluation_trends()
    require(report["outcome_counts"].get("reproducible_defect", 0) >= 1, "current outcome omitted")
    require(report["outcome_counts"].get("unclassified", 0) == 0, "valid outcome misclassified")


def test_provider_outage_and_actions_never_enable_replay() -> None:
    report = checkpoint.build_daily_evaluation_checkpoint()
    outage = area(report, "provider_outage_return_and_no_replay")["metrics"]
    actions = area(report, "interruption_retry_regeneration_resend")["metrics"]
    require(not outage["automatic_request_replay"] and not outage["automatic_resend"], "outage replay")
    require(not actions["automatic_retry"] and not actions["automatic_regeneration"] and not actions["automatic_resend"], "action automation")


def test_checkpoint_is_provider_free_and_non_autonomous() -> None:
    report = checkpoint.build_daily_evaluation_checkpoint()
    require(not report["provider_invoked"] and not report["embedding_provider_invoked"] and not report["generation_invoked"], "provider call")
    metrics = area(report, "provider_free_non_autonomous_evaluation")["metrics"]
    require(not metrics["autonomous_scoring"] and not metrics["automatic_release_certification"], "autonomous authority")
    source = (ROOT / "conscious_agent" / "conversation_daily_evaluation_checkpoint.py").read_text(encoding="utf-8")
    require("local_model" not in source and "provider_readiness" not in source, "provider dependency imported")


def test_operator_authority_remains_explicit() -> None:
    metrics = area(checkpoint.build_daily_evaluation_checkpoint(), "operator_authority_and_release_boundary")["metrics"]
    require(metrics["release_decision"] == "operator_only", "release authority")
    for key in ("approval_granted", "rollback_authorized", "installation_performed", "promotion_performed", "release_certified", "checkpoint_writes_state"):
        require(metrics[key] is False, key)


def test_api_get_route_returns_checkpoint() -> None:
    item = make_evaluation()
    status, payload = api_server.handle_api_get(
        "/api/conversation/daily-evaluation-checkpoint",
        {"evaluation_id": [item["evaluation_id"]], "session_id": [item["fixture_session_id"]]},
    )
    require(status == 200 and payload.get("ok"), "GET route")
    require(payload["data"]["type"] == "desktop_alpha_daily_evaluation_checkpoint", "route payload")


def test_checkpoint_has_no_post_or_mutation_route() -> None:
    source = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
    post = source[source.index("def handle_api_post"):]
    require('parts == ["conversation", "daily-evaluation-checkpoint"]' not in post, "POST route added")
    require("GET /api/conversation/daily-evaluation-checkpoint" in source, "API index missing")


def test_existing_console_javascript_and_narrow_layout_remain_valid() -> None:
    html = dashboard.render_daily_evaluation_console()
    require("@media(max-width:820px)" in html and "grid-template-columns:1fr" in html, "narrow layout")
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    script = next((item for item in scripts if "/api/conversation/evaluation-review-export" in item), None)
    require(script is not None, "console script missing")
    path = Path(tempfile.mkdtemp(prefix="eidolon-v1087-9-js-")) / "console.js"
    path.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, result.stderr)


def test_observation_mutations_still_require_confirmation_and_revision() -> None:
    session = sessions.create_conversation_session(title="Mutation guard fixture")
    try:
        evaluation.start_daily_evaluation(session["id"], operator_confirmed=False)
    except evaluation.DailyEvaluationError:
        pass
    else:
        raise AssertionError("start confirmation bypassed")
    item = evaluation.start_daily_evaluation(session["id"], operator_confirmed=True)
    updated = evaluation.record_operator_observation(
        item["evaluation_id"], ratings={"tone": 4}, expected_revision=item["revision"], operator_confirmed=True
    )
    try:
        evaluation.record_operator_observation(
            item["evaluation_id"], ratings={"tone": 5}, expected_revision=item["revision"], operator_confirmed=True
        )
    except evaluation.DailyEvaluationError:
        pass
    else:
        raise AssertionError("stale revision accepted")
    require(updated["revision"] == item["revision"] + 1, "revision did not advance")


def test_release_metadata_and_operator_guides_close_arc() -> None:
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1087, 9), "runtime version")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime tag")
    if current == (1087, 9):
        require(release_metadata.PREVIOUS_RUNTIME_VERSION == "1087.8", "previous version")
    if current == (1087, 9):
        for filename in ("README.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"):
            text = (ROOT / filename).read_text(encoding="utf-8")
            require("v1087.9" in text, f"{filename} missing checkpoint")
    else:
        history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        require(f"v{release_metadata.RUNTIME_VERSION}" in history, "release history missing current checkpoint")


def test_registration_is_exact_and_profiles_remain_bounded() -> None:
    names = [suite.name for suite in verify.SUITES]
    require(names.count("v1087.9-desktop-alpha-daily-evaluation-checkpoint") == 1, "registration")
    historical = verify.SUITES[names.index("v1087.9-desktop-alpha-daily-evaluation-checkpoint"):]
    core = [suite for suite in historical if "core" in suite.profiles]
    full = [suite for suite in historical if "full" in suite.profiles]
    require(len(core) == 72, f"historical core count {len(core)}")
    require(len(full) == 89, f"historical full count {len(full)}")


def test_source_only_privacy_boundaries() -> None:
    forbidden_exact = {
        "data/projects.json", "data/tasks.json", "data/memories.json", "data/conversations.json",
        "data/conversation_evaluations", ".git", ".venv", "venv",
    }
    relative_paths = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")}
    require(not (forbidden_exact & relative_paths), f"forbidden paths: {sorted(forbidden_exact & relative_paths)}")
    for path in ROOT.rglob("*"):
        parts = set(path.relative_to(ROOT).parts)
        require("__pycache__" not in parts, "bytecode cache in source tree")
        require(path.suffix not in {".pyc", ".pyo", ".zip"}, f"forbidden source artifact {path}")


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
        "suite": "v1087.9-desktop-alpha-daily-evaluation-checkpoint",
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
