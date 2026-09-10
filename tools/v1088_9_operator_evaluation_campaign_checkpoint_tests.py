from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1088-9-runtime-")
sys.path[:0] = [str(AGENT), str(TOOLS)]

import api_server
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_checkpoint as checkpoint
import conversation_evaluation_campaign_comparison as comparison
import conversation_evaluation_campaign_console as console
import conversation_evaluation_campaign_enrollment as enrollment
import conversation_evaluation_campaign_followups as followups
import conversation_evaluation_campaign_issues as issues
import conversation_evaluation_campaign_review as review
import conversation_evaluation_campaign_review_export as review_export
import dashboard
import post_review_development_verify as verify
import release_metadata

PRIVATE_CAMPAIGN_LABEL = "PRIVATE_CAMPAIGN_LABEL_V1088_9"
PRIVATE_CAMPAIGN_OBJECTIVE = "PRIVATE_CAMPAIGN_OBJECTIVE_V1088_9"
PRIVATE_REVIEW_NOTE = "PRIVATE_REVIEW_NOTE_V1088_9"
PRIVATE_EXTERNAL_REFERENCE = "PRIVATE_EXTERNAL_REFERENCE_V1088_9"


def require(value, message):
    if not value:
        raise AssertionError(message)


def source_digest():
    h = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in {"__pycache__", ".git", ".venv", "venv"} for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        h.update(path.relative_to(ROOT).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def runtime_digest():
    root = Path(os.environ["EIDOLON_DATA_DIR"])
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            h.update(path.relative_to(root).as_posix().encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def make_campaign(label=PRIVATE_CAMPAIGN_LABEL):
    return campaign.create_evaluation_campaign(
        campaign_label=label,
        objective=PRIVATE_CAMPAIGN_OBJECTIVE,
        focus_areas=["conversation_quality", "restart_and_resumption"],
        target_evaluation_count=2,
        minimum_completed_evaluations=1,
        planned_duration_days=7,
        required_signals=["consecutive_use", "restart_resume"],
        operator_confirmed=True,
    )


def area(report, name):
    return next(item for item in report["areas"] if item["name"] == name)


def test_checkpoint_has_fifteen_bounded_areas():
    report = checkpoint.build_operator_evaluation_campaign_checkpoint()
    require(report["checkpoint_status"] == "ready_for_operator_campaign_evaluation", "checkpoint not ready")
    require(report["area_count"] == checkpoint.CHECKPOINT_AREA_COUNT == 15, "area count")
    require(len({item["name"] for item in report["areas"]}) == 15, "area names")
    require(all(item["state"] == "ready" for item in report["areas"]), "area state")


def test_checkpoint_consumes_daily_evaluation_and_campaign_protocols():
    report = checkpoint.build_operator_evaluation_campaign_checkpoint()
    daily = area(report, "daily_evaluation_foundation")["metrics"]
    protocol = area(report, "campaign_protocol_and_bounds")["metrics"]
    require(daily["checkpoint_status"] == "ready_for_operator_daily_evaluation" and daily["area_count"] == 15, "daily foundation")
    require(protocol["protocol_status"] == "ready" and protocol["maximum_campaign_evaluations"] == 32, "campaign protocol")
    require(len(daily["contract_digest"]) == 64 and len(protocol["protocol_digest"]) == 64, "digests")


def test_selected_campaign_evidence_is_bounded_and_private_values_do_not_leak():
    item = make_campaign()
    report = checkpoint.build_operator_evaluation_campaign_checkpoint(campaign_id=item["campaign_id"])
    selected = area(report, "selected_campaign_evidence")["metrics"]
    encoded = json.dumps(report, sort_keys=True)
    require(selected["selection_status"] == "available" and selected["campaign_revision"] == 1, "selection")
    require(PRIVATE_CAMPAIGN_LABEL not in encoded and PRIVATE_CAMPAIGN_OBJECTIVE not in encoded, "private plan leaked")
    require(not selected["private_content_returned"], "private content flag")
    require(not checkpoint.operator_evaluation_campaign_checkpoint_contains_private_fields(report), "private key")


def test_missing_campaign_is_content_free_and_does_not_downgrade_contract():
    report = checkpoint.build_operator_evaluation_campaign_checkpoint(campaign_id="eval_campaign_20000101T000000_000000000000")
    require(report["selected_campaign_status"] == "not_found", "missing selection")
    require(report["checkpoint_status"] == "ready_for_operator_campaign_evaluation", "contract downgraded")
    selected = area(report, "selected_campaign_evidence")["metrics"]
    require(selected["campaign_id"] == "" and selected["campaign_revision"] == 0, "missing identity exposed")


def test_checkpoint_is_deterministic_for_equivalent_state():
    item = make_campaign()
    first = checkpoint.build_operator_evaluation_campaign_checkpoint(campaign_id=item["campaign_id"])
    second = checkpoint.build_operator_evaluation_campaign_checkpoint(campaign_id=item["campaign_id"])
    require(first == second, "checkpoint changed")
    for key in ("contract_digest", "evidence_digest", "areas_digest"):
        require(len(first[key]) == 64 and first[key] == second[key], key)


def test_checkpoint_reads_runtime_without_mutating_it():
    item = make_campaign()
    before = runtime_digest()
    checkpoint.build_operator_evaluation_campaign_checkpoint(campaign_id=item["campaign_id"])
    require(before == runtime_digest(), "runtime mutated")


def test_checkpoint_does_not_mutate_source_tree():
    item = make_campaign()
    before = source_digest()
    checkpoint.build_operator_evaluation_campaign_checkpoint(campaign_id=item["campaign_id"])
    require(before == source_digest(), "source mutated")


def test_lifecycle_and_enrollment_remain_explicit():
    metrics = area(checkpoint.build_operator_evaluation_campaign_checkpoint(), "private_campaign_lifecycle")["metrics"]
    enroll = area(checkpoint.build_operator_evaluation_campaign_checkpoint(), "explicit_enrollment_and_completion")["metrics"]
    require(metrics["operator_confirmation_required"] and metrics["optimistic_revision_required"], "lifecycle guards")
    require(not metrics["automatic_campaign_launch"] and metrics["private_plan_runtime_only"], "lifecycle automation")
    require(enroll["operator_completion_required"] and not enroll["automatic_evaluation_creation"], "enrollment authority")
    require(not enroll["automatic_evaluation_enrollment"] and not enroll["automatic_campaign_completion"], "enrollment automation")


def test_issue_aggregation_is_descriptive_and_non_autonomous():
    metrics = area(checkpoint.build_operator_evaluation_campaign_checkpoint(), "privacy_safe_issue_aggregation")["metrics"]
    require(metrics["descriptive_counts_only"], "not descriptive")
    require(not metrics["autonomous_prioritization"] and not metrics["automatic_task_created"], "autonomy")
    require(not metrics["statistical_significance_claimed"] and not metrics["private_notes_inspected"], "claim/private read")


def test_follow_up_references_never_create_tasks_or_expose_values():
    metrics = area(checkpoint.build_operator_evaluation_campaign_checkpoint(), "explicit_follow_up_references")["metrics"]
    require(metrics["maximum_follow_ups"] == 64 and "external_work_item" in metrics["reference_kinds"], "follow-up bounds")
    require(not metrics["private_reference_values_returned"], "private ref")
    require(not metrics["automatic_task_created"] and not metrics["automatic_work_item_created"], "automatic work")


def test_campaign_comparison_is_bounded_and_declares_no_winner():
    first = make_campaign("comparison one")
    second = make_campaign("comparison two")
    report = checkpoint.build_operator_evaluation_campaign_checkpoint(
        comparison_campaign_ids=[first["campaign_id"], second["campaign_id"]]
    )
    metrics = area(report, "bounded_campaign_comparison")["metrics"]
    require(metrics["comparison_status"] == "available" and metrics["compared_campaign_count"] == 2, "comparison unavailable")
    require(len(metrics["comparison_digest"]) == 64, "comparison digest")
    for key in ("campaign_ranking_included", "winner_declared", "statistical_significance_claimed", "release_recommendation_produced"):
        require(metrics[key] is False, key)


def test_review_workflow_remains_explicit_and_private():
    item = make_campaign()
    started = review.start_evaluation_campaign_review(item["campaign_id"], expected_revision=item["revision"], operator_confirmed=True)
    disposition = review.set_evaluation_campaign_review_disposition(
        item["campaign_id"], finding_kind="campaign_summary", finding_value="overall",
        disposition="acknowledged", note=PRIVATE_REVIEW_NOTE,
        expected_revision=started["campaign_revision"], operator_confirmed=True,
    )
    report = checkpoint.build_operator_evaluation_campaign_checkpoint(campaign_id=item["campaign_id"])
    metrics = area(report, "explicit_campaign_review_workflow")["metrics"]
    require(disposition["review_state"] == "in_review", "review state")
    require(PRIVATE_REVIEW_NOTE not in json.dumps(report, sort_keys=True), "review note leaked")
    require("follow_up_required" in metrics["review_dispositions"] and not metrics["automatic_review_completion"], "review contract")


def test_console_and_dashboard_javascript_remain_valid_and_narrow():
    report = checkpoint.build_operator_evaluation_campaign_checkpoint()
    metrics = area(report, "operator_campaign_console")["metrics"]
    require(metrics["maximum_campaign_rows"] == 64 and metrics["read_routes_only_for_evidence"], "console evidence")
    html = dashboard.render_evaluation_campaign_console()
    require("@media(max-width:820px)" in html and "grid-template-columns:1fr" in html, "narrow layout")
    match = re.search(r"<script>(.*?)</script>", html, re.S)
    require(match, "console script")
    path = Path(tempfile.mkdtemp(prefix="eidolon-v1088-9-js-")) / "campaign-console.js"
    path.write_text(match.group(1), encoding="utf-8")
    result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, result.stderr)


def test_review_export_remains_client_side_and_content_free():
    item = make_campaign()
    report = checkpoint.build_operator_evaluation_campaign_checkpoint(campaign_id=item["campaign_id"])
    metrics = area(report, "privacy_safe_campaign_review_export")["metrics"]
    require(metrics["selected_export_status"] == "available" and len(metrics["selected_document_sha256"]) == 64, "export evidence")
    for key in ("server_file_written", "transcript_included", "prompt_included", "private_campaign_plan_included", "private_follow_up_values_included", "private_review_notes_included", "private_evaluation_notes_included"):
        require(metrics[key] is False, key)


def test_existing_campaign_mutations_still_require_confirmation_and_revision():
    try:
        campaign.create_evaluation_campaign(
            campaign_label="blocked", objective="", focus_areas=["conversation_quality"],
            target_evaluation_count=1, minimum_completed_evaluations=1,
            planned_duration_days=1, operator_confirmed=False,
        )
    except campaign.EvaluationCampaignError:
        pass
    else:
        raise AssertionError("unconfirmed campaign created")
    item = make_campaign()
    active = campaign.activate_evaluation_campaign(item["campaign_id"], expected_revision=item["revision"], operator_confirmed=True)
    try:
        campaign.abort_evaluation_campaign(item["campaign_id"], expected_revision=item["revision"], operator_confirmed=True)
    except campaign.EvaluationCampaignError:
        pass
    else:
        raise AssertionError("stale revision accepted")
    require(active["revision"] == item["revision"] + 1, "revision did not advance")


def test_checkpoint_is_provider_free_and_never_replays():
    report = checkpoint.build_operator_evaluation_campaign_checkpoint()
    for key in ("provider_invoked", "embedding_provider_invoked", "generation_invoked", "automatic_provider_request", "automatic_replay", "automatic_resend"):
        require(report[key] is False, key)
    metrics = area(report, "provider_outage_and_no_replay_boundary")["metrics"]
    require(not metrics["provider_invoked"] and not metrics["automatic_replay"] and not metrics["automatic_resend"], "provider boundary")
    source = (AGENT / "conversation_evaluation_campaign_checkpoint.py").read_text(encoding="utf-8")
    require("local_model" not in source and "provider_readiness" not in source, "provider dependency")


def test_operator_authority_remains_explicit():
    report = checkpoint.build_operator_evaluation_campaign_checkpoint()
    metrics = area(report, "operator_authority_and_checkpoint_boundary")["metrics"]
    require(metrics["release_decision"] == "operator_only", "release decision")
    for key in ("approval_granted", "rollback_authorized", "installation_performed", "promotion_performed", "release_certified", "model_management", "provider_switching", "generation_settings_changed", "autonomous_scoring", "autonomous_prioritization", "automatic_task_created", "checkpoint_writes_state"):
        require(metrics[key] is False, key)


def test_api_get_route_returns_checkpoint():
    item = make_campaign()
    status, payload = api_server.handle_api_get(
        "/api/conversation/evaluation-campaign-checkpoint",
        {"campaign_id": [item["campaign_id"]]},
    )
    require(status == 200 and payload.get("ok"), "GET route")
    require(payload["data"]["type"] == "desktop_alpha_operator_evaluation_campaign_checkpoint", "route payload")


def test_checkpoint_has_no_post_or_mutation_route():
    source = (AGENT / "api_server.py").read_text(encoding="utf-8")
    post = source[source.index("def handle_api_post"):]
    require('parts == ["conversation", "evaluation-campaign-checkpoint"]' not in post, "POST route")
    require("GET /api/conversation/evaluation-campaign-checkpoint" in source, "API index")


def test_content_free_detector_rejects_private_shapes():
    require(checkpoint.operator_evaluation_campaign_checkpoint_contains_private_fields({"private_note": "secret"}), "private note missed")
    require(checkpoint.operator_evaluation_campaign_checkpoint_contains_private_fields({"document": "private export"}), "document missed")
    require(not checkpoint.operator_evaluation_campaign_checkpoint_contains_private_fields(checkpoint.build_operator_evaluation_campaign_checkpoint()), "false private detection")


def test_release_metadata_and_guides_close_campaign_arc():
    require(tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split(".")) >= (1088, 9), "runtime version")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime tag")
    require(bool(release_metadata.PREVIOUS_RUNTIME_VERSION), "previous version")
    for filename in ("README.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        require("v1088.9" in text, f"{filename} missing checkpoint")
        require("v1087.9" in text, f"{filename} lost daily-evaluation checkpoint")


def test_registration_is_exact_and_profiles_remain_bounded():
    names = [suite.name for suite in verify.SUITES]
    name = "v1088.9-desktop-alpha-operator-evaluation-campaign-checkpoint"
    require(names.count(name) == 1, "registration")
    require(names.index(name) < names.index("v1088.8-campaign-review-export"), "suite order")
    historical = verify.SUITES[names.index("v1088.9-desktop-alpha-operator-evaluation-campaign-checkpoint"):]
    core = [suite for suite in historical if "core" in suite.profiles]
    full = [suite for suite in historical if "full" in suite.profiles]
    require(len(core) == 82, f"historical core count {len(core)}")
    require(len(full) == 99, f"historical full count {len(full)}")


def test_source_only_privacy_boundaries():
    forbidden_exact = {
        "data/projects.json", "data/tasks.json", "data/memories.json", "data/conversations.json",
        "data/conversation_evaluation_campaigns", "data/conversation_evaluations", ".git", ".venv", "venv",
    }
    relative = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")}
    require(not (forbidden_exact & relative), f"forbidden paths: {sorted(forbidden_exact & relative)}")
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        require("__pycache__" not in rel.parts, "bytecode cache")
        require(path.suffix not in {".pyc", ".pyo", ".zip"}, f"forbidden artifact {rel}")


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
        "suite": "v1088.9-desktop-alpha-operator-evaluation-campaign-checkpoint",
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
