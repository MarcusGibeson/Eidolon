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
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1089c-export-")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import api_server
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_repair_candidates as repairs
import conversation_evaluation_finding_reproducibility as repro
import conversation_evaluation_finding_review_export as export
import conversation_evaluation_finding_triage as triage
from conversation_sessions import create_conversation_session
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


def fixture():
    session = create_conversation_session("Finding export fixture", select_session=False)
    evaluation = daily.start_daily_evaluation(session["id"], operator_confirmed=True)
    item = finding.create_evaluation_finding(
        finding_title="PRIVATE_FINDING_EXPORT_TITLE",
        finding_details="PRIVATE_FINDING_EXPORT_DETAILS",
        issue_domain="provider_transport",
        severity="blocking",
        evaluation_id=evaluation["evaluation_id"],
        operator_confirmed=True,
    )
    attempt = repro.record_reproduction_attempt(
        item["finding_id"],
        outcome="reproduced",
        environment_kind="clean_restart",
        environment_label="PRIVATE_FINDING_EXPORT_ENVIRONMENT",
        note="PRIVATE_FINDING_EXPORT_REPRO_NOTE",
        evidence_digest="a" * 64,
        expected_revision=item["revision"],
        operator_confirmed=True,
    )
    refs = repairs.add_repair_candidate_reference(
        item["finding_id"],
        reference_kind="source_archive",
        reference_value="PRIVATE_FINDING_EXPORT_ARCHIVE",
        label="PRIVATE_FINDING_EXPORT_REFERENCE_LABEL",
        expected_revision=attempt["finding_revision"],
        operator_confirmed=True,
    )
    review = triage.start_evaluation_finding_triage(
        item["finding_id"],
        note="PRIVATE_FINDING_EXPORT_TRIAGE_NOTE",
        expected_revision=refs["finding_revision"],
        operator_confirmed=True,
    )
    review = triage.set_evaluation_finding_triage_disposition(
        item["finding_id"],
        disposition="repair_candidate_review",
        expected_revision=review["finding_revision"],
        operator_confirmed=True,
    )
    review = triage.complete_evaluation_finding_triage(
        item["finding_id"],
        expected_revision=review["finding_revision"],
        operator_confirmed=True,
    )
    return item["finding_id"]


def test_export_is_deterministic_and_hash_bound():
    finding_id = fixture()
    first = export.build_evaluation_finding_review_export(finding_id)
    second = export.build_evaluation_finding_review_export(finding_id)
    require(first == second, "nondeterministic")
    require(hashlib.sha256(first["document"].encode()).hexdigest() == first["document_sha256"], "hash")


def test_export_contains_bounded_repair_intake_evidence():
    finding_id = fixture()
    document = export.build_evaluation_finding_review_export(finding_id)["review"]
    require(document["reproducibility_status"] == "confirmed", "reproducibility")
    require(document["reproduction_attempt_count"] == 1, "attempt count")
    require(document["repair_candidate_reference_count"] == 1, "reference count")
    require(document["triage_state"] == "completed" and document["triage_disposition"] == "repair_candidate_review", "triage")


def test_export_excludes_all_private_values_and_fields():
    finding_id = fixture()
    report = export.build_evaluation_finding_review_export(finding_id)
    encoded = json.dumps(report, sort_keys=True)
    for secret in (
        "PRIVATE_FINDING_EXPORT_TITLE",
        "PRIVATE_FINDING_EXPORT_DETAILS",
        "PRIVATE_FINDING_EXPORT_ENVIRONMENT",
        "PRIVATE_FINDING_EXPORT_REPRO_NOTE",
        "PRIVATE_FINDING_EXPORT_ARCHIVE",
        "PRIVATE_FINDING_EXPORT_REFERENCE_LABEL",
        "PRIVATE_FINDING_EXPORT_TRIAGE_NOTE",
    ):
        require(secret not in encoded, f"leaked {secret}")
    require(not export.finding_review_export_contains_private_fields(report), "private field")


def test_export_has_explicit_exclusion_and_operator_authority_flags():
    finding_id = fixture()
    document = export.build_evaluation_finding_review_export(finding_id)["review"]
    for key in (
        "finding_ranking_included",
        "priority_included",
        "statistical_significance_claimed",
        "automatic_task_created",
        "automatic_work_item_created",
        "patch_generated",
        "patch_reviewed",
        "patch_applied",
        "approval_granted",
        "rollback_authorized",
        "installation_performed",
        "promotion_performed",
        "release_recommendation_produced",
        "release_certified",
        "transcript_included",
        "prompt_included",
        "private_finding_content_included",
        "private_reproduction_notes_included",
        "private_environment_labels_included",
        "private_repair_reference_values_included",
        "private_triage_notes_included",
        "memory_content_included",
        "provider_payload_included",
        "credentials_included",
        "vectors_included",
        "hidden_reasoning_included",
        "provider_invoked",
        "generation_invoked",
    ):
        require(document[key] is False, key)
    require(document["repair_decision"] == "operator_only" and document["release_decision"] == "operator_only", "operator authority")


def test_get_route_returns_client_download_without_server_write():
    finding_id = fixture()
    before = tree_digest()
    status, payload = api_server.handle_api_get(
        "/api/conversation/evaluation-finding-review-export",
        {"finding_id": [finding_id]},
    )
    data = payload["data"]
    require(status == 200 and data["client_download_ready"], "route")
    require(not data["server_file_written"] and not data["writes_state"], "server write")
    require(before == tree_digest(), "source mutation")


def test_filename_is_bounded_and_content_free():
    finding_id = fixture()
    report = export.build_evaluation_finding_review_export(finding_id)
    require(report["filename"].endswith("_privacy_safe_repair_intake_review.json"), "filename")
    require("/" not in report["filename"] and "\\" not in report["filename"], "path")
    require("PRIVATE" not in report["filename"], "private filename")


def test_no_post_export_route_and_exact_registration():
    source = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
    post = source[source.index("def handle_api_post") :]
    require('parts == ["conversation", "evaluation-finding-review-export"]' not in post, "POST export route")
    names = [suite.name for suite in verify.SUITES]
    require(names.count("v1089.7-finding-review-export") == 1, "registration")
    require(names.index("v1089.7-finding-review-export") < names.index("v1089.6-operator-findings-console"), "order")


def test_export_route_rejects_missing_finding():
    status, payload = api_server.dispatch_api(
        "GET",
        "/api/conversation/evaluation-finding-review-export",
        query={"finding_id": ["eval_finding_20000101T000000_000000000000"]},
    )
    require(status == 404 and payload["ok"] is False, "missing finding")


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
        "suite": "v1089.7-finding-review-export",
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
