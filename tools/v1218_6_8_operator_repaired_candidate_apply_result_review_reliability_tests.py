from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1218-c-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import operator_repaired_candidate_apply_result_review as apply_review
from ordinary_chat_development_campaign import _atomic_json, _read_json
from v1218_apply_result_review_fixture import build_apply_result_review_fixture

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


fixture = build_apply_result_review_fixture(applied=False, seed="c-ineligible")
runtime = fixture["runtime"]
result = fixture["apply_result"]
proposal = fixture["proposal"]
try:
    review = apply_review.prepare_operator_repaired_candidate_apply_result_review(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest=result["supervised_repaired_candidate_apply_digest"],
        expected_result_digest=result["supervised_repaired_candidate_apply_result_digest"],
        runtime_root=runtime,
    )
    require(review["rollback_eligible"] is False)
    require("propose-rollback" not in review["available_decisions"])
    forged = apply_review.record_operator_repaired_candidate_apply_result_decision(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"],
        decision="propose-rollback",
        decision_phrase=apply_review._review_phrase(
            "propose-rollback", review["review_digest"], proposal["proposal_id"], 1, 2
        ),
        runtime_root=runtime,
    )
    require(forged["status"] == "operator_repaired_candidate_apply_result_decision_not_allowed")
    require(forged["rollback_authorized"] is False)
    stale = apply_review.record_operator_repaired_candidate_apply_result_decision(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest="0" * 64,
        decision="defer",
        decision_phrase=apply_review._review_phrase("defer", "0" * 64, proposal["proposal_id"], 1, 2),
        runtime_root=runtime,
    )
    require(stale["status"] == "operator_repaired_candidate_apply_result_decision_stale_review")
    path = apply_review._review_path(proposal["proposal_id"], 1, 2, runtime)
    tampered = _read_json(path)
    tampered["rollback_eligible"] = True
    _atomic_json(path, tampered)
    blocked = apply_review.record_operator_repaired_candidate_apply_result_decision(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"],
        decision="defer",
        decision_phrase=apply_review._review_phrase("defer", review["review_digest"], proposal["proposal_id"], 1, 2),
        runtime_root=runtime,
    )
    require(blocked["status"] == "operator_repaired_candidate_apply_result_review_record_invalid")
finally:
    shutil.rmtree(runtime, ignore_errors=True)

fixture = build_apply_result_review_fixture(applied=True, seed="c-tamper")
runtime = fixture["runtime"]
result = fixture["apply_result"]
proposal = fixture["proposal"]
try:
    wrong_execution = apply_review.prepare_operator_repaired_candidate_apply_result_review(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest="0" * 64,
        expected_result_digest=result["supervised_repaired_candidate_apply_result_digest"],
        runtime_root=runtime,
    )
    require(wrong_execution["status"] == "operator_repaired_candidate_apply_result_review_stale_execution")
    wrong_result = apply_review.prepare_operator_repaired_candidate_apply_result_review(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest=result["supervised_repaired_candidate_apply_digest"],
        expected_result_digest="0" * 64,
        runtime_root=runtime,
    )
    require(wrong_result["status"] == "operator_repaired_candidate_apply_result_review_stale_result")
    review = apply_review.prepare_operator_repaired_candidate_apply_result_review(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest=result["supervised_repaired_candidate_apply_digest"],
        expected_result_digest=result["supervised_repaired_candidate_apply_result_digest"],
        runtime_root=runtime,
    )
    phrase = next(value for value in review["decision_phrases"] if "propose-rollback" in value)
    decision = apply_review.record_operator_repaired_candidate_apply_result_decision(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"],
        decision="propose-rollback",
        decision_phrase=phrase,
        runtime_root=runtime,
    )
    stale_proposal = apply_review.prepare_bounded_repaired_candidate_rollback_proposal(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"],
        expected_decision_digest="0" * 64,
        runtime_root=runtime,
    )
    require(stale_proposal["status"] == "bounded_rollback_proposal_stale_decision")
    proposal_row = apply_review.prepare_bounded_repaired_candidate_rollback_proposal(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"],
        expected_decision_digest=decision["operator_repaired_candidate_apply_result_decision_digest"],
        runtime_root=runtime,
    )
    require(proposal_row["ok"] is True, proposal_row)
    require(proposal_row["rollback_authorized"] is False)
    require(proposal_row["project_modified"] is False)
    encoded = json.dumps(proposal_row, sort_keys=True)
    require("C:\\operator" not in encoded)
    require(str(fixture["source_workspace_root"]) not in encoded)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

print(json.dumps({
    "ok": True,
    "version": "1218.8",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "tamper_rejected": True,
    "ineligible_rollback_rejected": True,
    "privacy_preserved": True,
}, sort_keys=True))
