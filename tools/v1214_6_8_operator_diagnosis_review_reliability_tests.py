from __future__ import annotations

import concurrent.futures
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


def fixture(runtime: Path, seed: str = "f"):
    proposal_id = "devc_" + seed * 24
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
        "outcome_status": "conversational_build_test_continuation_build_blocked",
        "evidence_digest": "6" * 64,
        "diagnosis_digest": "7" * 64,
        "diagnosis_candidates": [{
            "diagnosis_code": "build_stage_blocked",
            "confidence": "high_observation_low_root_cause",
            "supported_conclusion": "isolated_build_did_not_reach_completed_tests",
            "unknowns": ["generation_materialization_or_validation_cause", "required_repair"],
            "suggested_next_step": "operator_review_build_block_before_repair_proposal",
        }],
        "diagnosis_count": 1,
        "root_cause_proven": False,
        "operator_review_required": True,
        "provider_contacted": False,
        "tests_executed": False,
    }
    result["diagnosis_result_digest"] = _digest(result)
    record = diagnosis._seal({
        "schema_version": "1",
        "contract_version": "v1213.8",
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "attempt_number": 2,
        "phase": "sealed",
        "result": result,
        "result_digest": _digest(result),
    })
    _atomic_json(diagnosis._diagnosis_path(proposal_id, 1, 2, runtime), record)
    packet = review.prepare_operator_diagnosis_review(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=2,
        expected_diagnosis_digest=result["diagnosis_digest"],
        expected_diagnosis_result_digest=result["diagnosis_result_digest"],
        runtime_root=runtime,
    )
    return proposal_id, result, packet


# Tampered diagnosis records fail before a review packet is created.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-c-diagnosis-"))
try:
    proposal_id, result, packet = fixture(runtime)
    diagnosis_path = diagnosis._diagnosis_path(proposal_id, 1, 2, runtime)
    damaged = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    damaged["result"]["diagnosis_candidates"][0]["diagnosis_code"] = "forged_private_root_cause"
    _atomic_json(diagnosis_path, damaged)
    require(diagnosis.load_bounded_automatic_diagnosis(proposal_id, 1, 2, runtime_root=runtime) == {})
    blocked = review.prepare_operator_diagnosis_review(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=2,
        expected_diagnosis_digest=result["diagnosis_digest"],
        expected_diagnosis_result_digest=result["diagnosis_result_digest"],
        runtime_root=runtime,
    )
    require(blocked["status"] == "operator_diagnosis_review_diagnosis_invalid")
    require(blocked["repair_execution_authorized"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# Review tampering and stale/cross-attempt controls fail closed.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-c-review-"))
try:
    proposal_id, result, packet = fixture(runtime)
    review_path = review._review_path(proposal_id, 1, 2, runtime)
    damaged = json.loads(review_path.read_text(encoding="utf-8"))
    damaged["repair_execution_authorized"] = True
    _atomic_json(review_path, damaged)
    require(review.load_operator_diagnosis_review(proposal_id, 1, 2, runtime_root=runtime) == {})
    phrase = packet["decision_phrases"][0]
    blocked = review.record_operator_diagnosis_decision(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=2,
        expected_review_digest=packet["review_digest"],
        decision="accept-diagnosis",
        decision_phrase=phrase,
        runtime_root=runtime,
    )
    require(blocked["status"] == "operator_diagnosis_review_record_invalid")
    cross_attempt = review.record_operator_diagnosis_decision(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=3,
        expected_review_digest=packet["review_digest"],
        decision="accept-diagnosis",
        decision_phrase=phrase.replace("attempt 2", "attempt 3"),
        runtime_root=runtime,
    )
    require(cross_attempt["status"] == "operator_diagnosis_review_record_invalid")
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# Concurrent conflicting decisions converge on one durable decision.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-c-race-"))
try:
    proposal_id, result, packet = fixture(runtime)

    def decide(name: str):
        phrase = next(value for value in packet["decision_phrases"] if f"Record {name} " in value)
        return review.record_operator_diagnosis_decision(
            proposal_id,
            expected_revision=1,
            expected_attempt_number=2,
            expected_review_digest=packet["review_digest"],
            decision=name,
            decision_phrase=phrase,
            runtime_root=runtime,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(decide, ["defer", "reject-diagnosis"]))
    require(sum(item.get("ok") is True for item in results) == 1, results)
    require(sum(item.get("status") == "operator_diagnosis_conflicting_decision" for item in results) == 1, results)
    stored = review.load_operator_diagnosis_decision(proposal_id, 1, 2, runtime_root=runtime)
    require(stored["decision"] in {"defer", "reject-diagnosis"})
    require(stored["repair_execution_authorized"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# Decision and repair-proposal record tampering are independently rejected.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-c-proposal-"))
try:
    proposal_id, result, packet = fixture(runtime)
    phrase = next(value for value in packet["decision_phrases"] if "Record propose-repair " in value)
    decision = review.record_operator_diagnosis_decision(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=2,
        expected_review_digest=packet["review_digest"],
        decision="propose-repair",
        decision_phrase=phrase,
        runtime_root=runtime,
    )
    proposal = review.prepare_bounded_repair_proposal(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=2,
        expected_review_digest=packet["review_digest"],
        expected_decision_digest=decision["operator_diagnosis_decision_digest"],
        runtime_root=runtime,
    )
    require(proposal["ok"] is True, proposal)
    require(proposal["operation_status"] == "created")
    stale = review.prepare_bounded_repair_proposal(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=2,
        expected_review_digest=packet["review_digest"],
        expected_decision_digest="8" * 64,
        runtime_root=runtime,
    )
    require(stale["status"] == "bounded_repair_proposal_stale_decision")
    proposal_path = review._repair_proposal_path(proposal_id, 1, 2, runtime)
    damaged = json.loads(proposal_path.read_text(encoding="utf-8"))
    damaged["maximum_repair_attempts"] = 99
    damaged["repair_execution_authorized"] = True
    _atomic_json(proposal_path, damaged)
    require(review.load_bounded_repair_proposal(proposal_id, 1, 2, runtime_root=runtime) == {})
    blocked = review.prepare_bounded_repair_proposal(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=2,
        expected_review_digest=packet["review_digest"],
        expected_decision_digest=decision["operator_diagnosis_decision_digest"],
        runtime_root=runtime,
    )
    require(blocked["status"] == "bounded_repair_proposal_record_invalid")
    require(blocked["repair_execution_authorized"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# A private exception becomes type-only digest evidence.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-c-private-"))
try:
    proposal_id, result, packet = fixture(runtime)
    phrase = next(value for value in packet["decision_phrases"] if "Record propose-repair " in value)
    original = review.prepare_bounded_repair_proposal

    def fail_private(*args, **kwargs):
        raise RuntimeError(r"C:\Users\private\secret-project\prompt-and-code.txt")

    review.prepare_bounded_repair_proposal = fail_private
    try:
        turn = review.process_operator_diagnosis_review_control(phrase, runtime_root=runtime)
    finally:
        review.prepare_bounded_repair_proposal = original
    encoded = json.dumps(turn, sort_keys=True)
    require(turn["bounded_repair_proposal"]["status"] == "bounded_repair_proposal_preparation_blocked")
    require(len(turn["bounded_repair_proposal"]["reason_digest"]) == 64)
    require("Users" not in encoded)
    require("secret-project" not in encoded)
    require("prompt-and-code" not in encoded)
    require(turn["bounded_repair_proposal"]["repair_execution_authorized"] is False)
    require(turn["bounded_repair_proposal"]["authority_granted"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


for casual in (
    "It would be nice if you repaired it.",
    "Maybe propose a repair someday.",
    'She said "Record propose-repair for diagnosis review ..."',
    "Authorize a repair.",
):
    require(review.process_operator_diagnosis_review_control(casual) == {"active": False, "event": "inactive"})

source = (ROOT / "conscious_agent" / "operator_diagnosis_review.py").read_text(encoding="utf-8")
require("provider_generate" not in source)
require("subprocess" not in source)
require('"repair_execution_authorized": True' not in source)
require('"test_execution_authorized": True' not in source)
require('"retest_authorized": True' not in source)
require('"apply_authorized": True' not in source)
require('"release_authorized": True' not in source)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1214.8-operator-diagnosis-review-repair-proposal-reliability"') == 2)
require(release.count("tools/v1214_6_8_operator_diagnosis_review_reliability_tests.py") == 1)
print(json.dumps({
    "ok": True,
    "version": "1214.8",
    "checks": len(checks),
    "passed": sum(checks),
    "conflicting_decisions_blocked": True,
    "tamper_rejected": True,
    "private_error_suppressed": True,
    "repair_execution_authorized": False,
}, sort_keys=True))
