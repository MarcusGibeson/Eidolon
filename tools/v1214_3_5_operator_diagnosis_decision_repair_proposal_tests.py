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
from ordinary_chat_development_campaign import _atomic_json, _digest, process_ordinary_chat_development_turn

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def prepared_review(runtime: Path, seed: str):
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
        "outcome_status": "conversational_build_test_continuation_tests_failed",
        "evidence_digest": "6" * 64,
        "diagnosis_digest": "7" * 64,
        "diagnosis_posture": "diagnosis_candidates_require_operator_review",
        "diagnosis_candidates": [{
            "diagnosis_code": "test_failure_observed",
            "confidence": "high_observation_low_root_cause",
            "supported_conclusion": "reviewed_tests_executed_and_did_not_pass",
            "unknowns": ["failing_assertion_or_runtime_cause", "required_repair"],
            "suggested_next_step": "operator_review_test_failure_before_repair_proposal",
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
    return proposal_id, packet


for index, decision in enumerate(review.REVIEW_DECISIONS):
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-b-"))
    try:
        proposal_id, packet = prepared_review(runtime, "abcdef0123456789"[index])
        phrase = next(value for value in packet["decision_phrases"] if f"Record {decision} " in value)
        recorded = review.record_operator_diagnosis_decision(
            proposal_id,
            expected_revision=1,
            expected_attempt_number=2,
            expected_review_digest=packet["review_digest"],
            decision=decision,
            decision_phrase=phrase,
            runtime_root=runtime,
        )
        require(recorded["ok"] is True, recorded)
        require(recorded["status"] == "operator_diagnosis_decision_recorded")
        require(recorded["decision"] == decision)
        require(recorded["repair_proposal_requested"] is (decision == "propose-repair"))
        require(recorded["provider_contacted"] is False)
        require(recorded["tests_executed"] is False)
        require(recorded["retest_executed"] is False)
        require(recorded["patch_generated"] is False)
        require(recorded["repair_executed"] is False)
        require(recorded["project_modified"] is False)
        require(recorded["repair_execution_authorized"] is False)
        require(recorded["authority_granted"] is False)
        replay = review.record_operator_diagnosis_decision(
            proposal_id,
            expected_revision=1,
            expected_attempt_number=2,
            expected_review_digest=packet["review_digest"],
            decision=decision,
            decision_phrase=phrase,
            runtime_root=runtime,
        )
        require(replay["operation_status"] == "resumed")
        require(replay["operator_diagnosis_decision_digest"] == recorded["operator_diagnosis_decision_digest"])
        turn = process_ordinary_chat_development_turn(phrase, runtime_root=runtime)
        require(turn["active"] is True, turn)
        require(turn["operator_diagnosis_review"]["decision"] == decision)
        if decision == "propose-repair":
            proposal = turn["bounded_repair_proposal"]
            require(proposal["status"] == "bounded_repair_proposal_authorization_required", turn)
            require(proposal["repair_scope"] == "one_bounded_isolated_attempt")
            require(proposal["repair_target"] == "exact_failed_continuation_artifact")
            require(proposal["maximum_repair_attempts"] == 1)
            require(proposal["requires_exact_authorization"] is True)
            require(proposal["repair_proposal_created"] is True)
            require(proposal["repair_authorization_required"] is True)
            require(proposal["repair_execution_authorized"] is False)
            require(proposal["provider_contacted"] is False)
            require(proposal["tests_executed"] is False)
            require(proposal["patch_generated"] is False)
            require(proposal["repair_executed"] is False)
            require(proposal["selected_project_modified"] is False)
            require(proposal["source_modified"] is False)
            require(proposal["authority_granted"] is False)
            require(proposal["repair_proposal_digest"] in proposal["authorization_phrase"])
            require("Authorize repair proposal" in turn["conversation_response"])
            stored = review.load_bounded_repair_proposal(proposal_id, 1, 2, runtime_root=runtime)
            require(stored["repair_proposal_digest"] == proposal["repair_proposal_digest"])
            proposal_replay = review.prepare_bounded_repair_proposal(
                proposal_id,
                expected_revision=1,
                expected_attempt_number=2,
                expected_review_digest=packet["review_digest"],
                expected_decision_digest=recorded["operator_diagnosis_decision_digest"],
                runtime_root=runtime,
            )
            require(proposal_replay["operation_status"] == "resumed")
        else:
            require("bounded_repair_proposal" not in turn)
            missing = review.load_bounded_repair_proposal(proposal_id, 1, 2, runtime_root=runtime)
            require(missing == {})
            blocked = review.prepare_bounded_repair_proposal(
                proposal_id,
                expected_revision=1,
                expected_attempt_number=2,
                expected_review_digest=packet["review_digest"],
                expected_decision_digest=recorded["operator_diagnosis_decision_digest"],
                runtime_root=runtime,
            )
            require(blocked["status"] == "bounded_repair_proposal_not_requested")
    finally:
        shutil.rmtree(runtime, ignore_errors=True)

runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-b-exact-"))
try:
    proposal_id, packet = prepared_review(runtime, "e")
    exact = next(value for value in packet["decision_phrases"] if "Record defer " in value)
    almost = exact.replace("Record defer", "Please record defer")
    inactive = review.process_operator_diagnosis_review_control(almost, runtime_root=runtime)
    require(inactive == {"active": False, "event": "inactive"})
    stale = review.record_operator_diagnosis_decision(
        proposal_id,
        expected_revision=1,
        expected_attempt_number=2,
        expected_review_digest="0" * 64,
        decision="defer",
        decision_phrase=exact,
        runtime_root=runtime,
    )
    require(stale["status"] == "operator_diagnosis_decision_stale_review")
    require(stale["repair_execution_authorized"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1214.5-operator-diagnosis-decision-repair-proposal"') == 2)
require(release.count("tools/v1214_3_5_operator_diagnosis_decision_repair_proposal_tests.py") == 1)
print(json.dumps({
    "ok": True,
    "version": "1214.5",
    "checks": len(checks),
    "passed": sum(checks),
    "decisions": len(review.REVIEW_DECISIONS),
    "repair_proposals": 1,
    "provider_contacted": False,
    "tests_executed": False,
    "repair_executed": False,
}, sort_keys=True))
