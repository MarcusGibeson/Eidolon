from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import bounded_automatic_diagnosis as diagnosis
import operator_diagnosis_review as review
from ordinary_chat_development_campaign import _atomic_json, _digest

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def seal_diagnosis(runtime: Path, *, status: str, code: str):
    proposal_id = "devc_" + "a" * 24
    result = {
        "ok": True,
        "schema_version": "1",
        "contract_version": "v1213.8",
        "status": "bounded_automatic_diagnosis_completed",
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "proposal_revision_digest": "1" * 64,
        "attempt_number": 2,
        "attempt_digest": "2" * 64,
        "continuation_result_digest": "3" * 64,
        "continuation_loop_result_digest": "4" * 64,
        "lineage_digest": "5" * 64,
        "outcome_status": status,
        "evidence_digest": "6" * 64,
        "diagnosis_digest": "7" * 64,
        "diagnosis_posture": "diagnosis_candidates_require_operator_review",
        "diagnosis_candidates": [{
            "diagnosis_code": code,
            "confidence": "high_observation_low_root_cause",
            "supported_conclusion": "content_free_observation",
            "unknowns": ["exact_cause", "required_repair"],
            "suggested_next_step": "operator_review_before_repair_proposal",
        }],
        "diagnosis_count": 1,
        "root_cause_proven": False,
        "operator_review_required": True,
        "provider_contacted": False,
        "tests_executed": False,
        "private_payload": "C:/Users/private/project/raw-output",
    }
    result["diagnosis_result_digest"] = _digest(result)
    record = {
        "schema_version": "1",
        "contract_version": "v1213.8",
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "attempt_number": 2,
        "diagnosis_digest": result["diagnosis_digest"],
        "phase": "sealed",
        "result": result,
        "result_digest": _digest(result),
    }
    path = diagnosis._diagnosis_path(proposal_id, 1, 2, runtime)
    _atomic_json(path, diagnosis._seal(record))
    return proposal_id, result


outcomes = {
    "conversational_build_test_continuation_tests_failed": "test_failure_observed",
    "conversational_build_test_continuation_test_blocked": "test_execution_blocked",
    "conversational_build_test_continuation_build_blocked": "build_stage_blocked",
    "conversational_build_test_continuation_internal_error": "continuation_pipeline_error_observed",
}

for status, code in outcomes.items():
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-a-"))
    try:
        proposal_id, diagnosed = seal_diagnosis(runtime, status=status, code=code)
        packet = review.prepare_operator_diagnosis_review(
            proposal_id,
            expected_revision=1,
            expected_attempt_number=2,
            expected_diagnosis_digest=diagnosed["diagnosis_digest"],
            expected_diagnosis_result_digest=diagnosed["diagnosis_result_digest"],
            runtime_root=runtime,
        )
        require(packet["ok"] is True, packet)
        require(packet["status"] == "operator_diagnosis_review_required")
        require(packet["operation_status"] == "created")
        require(packet["diagnosis_code"] == code)
        require(packet["diagnosis_confidence"] == "high_observation_low_root_cause")
        require(packet["root_cause_proven"] is False)
        require(packet["unknown_count"] == 2)
        require(packet["available_decisions"] == list(review.REVIEW_DECISIONS))
        require(len(packet["decision_phrases"]) == 4)
        require(all(packet["review_digest"] in phrase for phrase in packet["decision_phrases"]))
        require(all(proposal_id in phrase for phrase in packet["decision_phrases"]))
        require(packet["repair_proposal_created"] is False)
        require(packet["repair_execution_authorized"] is False)
        require(packet["provider_contacted"] is False)
        require(packet["tests_executed"] is False)
        require(packet["retest_executed"] is False)
        require(packet["project_modified"] is False)
        require(packet["source_modified"] is False)
        require(packet["authority_granted"] is False)
        public = review.public_operator_diagnosis_review(packet)
        encoded = json.dumps(public, sort_keys=True)
        require("C:/Users/private" not in encoded)
        require("raw-output" not in encoded)
        require(public["content_free"] is True)
        require(public["private_path_exposed"] is False)
        require(len(public["public_operator_diagnosis_digest"]) == 64)
        resumed = review.prepare_operator_diagnosis_review(
            proposal_id,
            expected_revision=1,
            expected_attempt_number=2,
            expected_diagnosis_digest=diagnosed["diagnosis_digest"],
            expected_diagnosis_result_digest=diagnosed["diagnosis_result_digest"],
            runtime_root=runtime,
        )
        require(resumed["operation_status"] == "resumed")
        require(resumed["review_digest"] == packet["review_digest"])
        stale_diagnosis = review.prepare_operator_diagnosis_review(
            proposal_id,
            expected_revision=1,
            expected_attempt_number=2,
            expected_diagnosis_digest="8" * 64,
            expected_diagnosis_result_digest=diagnosed["diagnosis_result_digest"],
            runtime_root=runtime,
        )
        require(stale_diagnosis["status"] == "operator_diagnosis_review_stale_diagnosis")
        stale_result = review.prepare_operator_diagnosis_review(
            proposal_id,
            expected_revision=1,
            expected_attempt_number=2,
            expected_diagnosis_digest=diagnosed["diagnosis_digest"],
            expected_diagnosis_result_digest="9" * 64,
            runtime_root=runtime,
        )
        require(stale_result["status"] == "operator_diagnosis_review_stale_result")
    finally:
        shutil.rmtree(runtime, ignore_errors=True)

runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-a-attach-"))
try:
    proposal_id, diagnosed = seal_diagnosis(
        runtime,
        status="conversational_build_test_continuation_tests_failed",
        code="test_failure_observed",
    )
    public_diagnosis = diagnosis.public_bounded_automatic_diagnosis(diagnosed)
    turn = review.attach_operator_diagnosis_review(
        {
            "active": True,
            "bounded_automatic_diagnosis": public_diagnosis,
            "conversation_response": "The tests failed and the bounded diagnosis is complete.",
        },
        runtime_root=runtime,
    )
    require(turn["operator_diagnosis_review"]["status"] == "operator_diagnosis_review_required", turn)
    require("root cause is not proven" in turn["conversation_response"])
    require("Record propose-repair" in turn["conversation_response"])
    require(len(turn["public_digest"]) == 64)
    untouched = review.attach_operator_diagnosis_review({"active": True}, runtime_root=runtime)
    require("operator_diagnosis_review" not in untouched)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1214.2-operator-diagnosis-review-foundations"') == 2)
require(release.count("tools/v1214_0_2_operator_diagnosis_review_foundations_tests.py") == 1)
print(json.dumps({
    "ok": True,
    "version": "1214.2",
    "checks": len(checks),
    "passed": sum(checks),
    "diagnosable_outcomes": len(outcomes),
    "review_decisions": len(review.REVIEW_DECISIONS),
    "repair_proposal_created": False,
    "repair_execution_authorized": False,
}, sort_keys=True))
