from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import operator_repaired_candidate_apply_result_review as apply_review
from v1218_apply_result_review_fixture import build_apply_result_review_fixture


def build_repaired_candidate_rollback_fixture(seed: str = "a") -> dict:
    fixture = build_apply_result_review_fixture(applied=True, seed=seed)
    result, proposal, runtime = fixture["apply_result"], fixture["proposal"], fixture["runtime"]
    review = apply_review.prepare_operator_repaired_candidate_apply_result_review(
        proposal["proposal_id"], expected_revision=1, expected_failed_attempt_number=2,
        expected_execution_digest=result["supervised_repaired_candidate_apply_digest"],
        expected_result_digest=result["supervised_repaired_candidate_apply_result_digest"],
        runtime_root=runtime)
    phrase = next(value for value in review["decision_phrases"] if "propose-rollback" in value)
    decision = apply_review.record_operator_repaired_candidate_apply_result_decision(
        proposal["proposal_id"], expected_revision=1, expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"], decision="propose-rollback",
        decision_phrase=phrase, runtime_root=runtime)
    rollback = apply_review.prepare_bounded_repaired_candidate_rollback_proposal(
        proposal["proposal_id"], expected_revision=1, expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"],
        expected_decision_digest=decision["operator_repaired_candidate_apply_result_decision_digest"],
        runtime_root=runtime)
    if rollback.get("ok") is not True:
        raise AssertionError(rollback)
    return {**fixture, "apply_result_review": review,
            "apply_result_decision": decision, "rollback_proposal": rollback}
