from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1216-c-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import conversational_supervised_repair_execution as repair
import operator_repair_result_review as review
from ordinary_chat_development_campaign import _atomic_json, _read_json
from v1216_repair_result_review_fixture import build_repair_result_review_fixture

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


# One exact decision is replayable; a conflicting decision fails closed.
fixture = build_repair_result_review_fixture(passed=True, seed="c-conflict")
try:
    packet = fixture["repair_result_review"]
    accept_phrase = next(value for value in packet["decision_phrases"] if "accept-repair-result" in value)
    accepted = review.process_operator_repair_result_review_control(
        accept_phrase, runtime_root=fixture["runtime"]
    )
    require(accepted["event"] == "operator_repair_result_decision_recorded")
    require(accepted["operator_repair_result_review"]["decision_state"] == "repair_result_accepted")
    replay = review.process_operator_repair_result_review_control(
        accept_phrase, runtime_root=fixture["runtime"]
    )
    require(replay["operator_repair_result_review"]["operation_status"] == "resumed")
    reject_phrase = next(value for value in packet["decision_phrases"] if "reject-repair" in value)
    conflict = review.process_operator_repair_result_review_control(
        reject_phrase, runtime_root=fixture["runtime"]
    )
    require(conflict["event"] == "operator_repair_result_conflicting_decision")
    require(conflict["operator_repair_result_review"]["apply_authorized"] is False)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)


# A tampered review record is rejected and cannot create a decision.
fixture = build_repair_result_review_fixture(passed=True, seed="c-review-tamper")
try:
    packet = fixture["repair_result_review"]
    path = review._review_path(packet["proposal_id"], 1, 2, fixture["runtime"])
    stored = _read_json(path)
    stored["candidate_apply_eligible"] = False
    _atomic_json(path, stored)
    phrase = next(value for value in packet["decision_phrases"] if "propose-apply" in value)
    blocked = review.process_operator_repair_result_review_control(
        phrase, runtime_root=fixture["runtime"]
    )
    require(blocked["event"] == "operator_repair_result_review_record_invalid")
    require("bounded_repaired_candidate_apply_proposal" not in blocked)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)


# A tampered decision record blocks proposal replay.
fixture = build_repair_result_review_fixture(passed=True, seed="c-decision-tamper")
try:
    packet = fixture["repair_result_review"]
    phrase = next(value for value in packet["decision_phrases"] if "propose-apply" in value)
    first = review.process_operator_repair_result_review_control(
        phrase, runtime_root=fixture["runtime"]
    )
    require(first["bounded_repaired_candidate_apply_proposal"]["ok"] is True)
    path = review._decision_path(packet["proposal_id"], 1, 2, fixture["runtime"])
    stored = _read_json(path)
    stored["candidate_apply_eligible"] = False
    _atomic_json(path, stored)
    blocked = review.prepare_bounded_repaired_candidate_apply_proposal(
        packet["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest=packet["review_digest"],
        expected_decision_digest=first["operator_repair_result_review"]["operator_repair_result_decision_digest"],
        runtime_root=fixture["runtime"],
    )
    require(blocked["status"] == "bounded_apply_proposal_decision_invalid")
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)


# A forged passing result cannot be promoted into an eligible review.
fixture = build_repair_result_review_fixture(passed=True, seed="c-result-tamper")
try:
    proposal_id = fixture["proposal"]["proposal_id"]
    path = repair._execution_path(proposal_id, 1, 2, fixture["runtime"])
    stored = _read_json(path)
    forged = dict(stored["result"])
    forged["test_passed"] = False
    stored["result"] = forged
    stored["result_digest"] = review._digest(forged)
    _atomic_json(path, repair._seal(stored))
    blocked = review.prepare_operator_repair_result_review(
        proposal_id,
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest=fixture["repair_result"]["supervised_repair_execution_digest"],
        expected_result_digest=fixture["repair_result"]["supervised_repair_result_digest"],
        runtime_root=fixture["runtime"],
    )
    require(blocked["status"] == "operator_repair_result_review_repair_invalid")
    require(blocked["apply_authorized"] is False)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)


# Cross-attempt and out-of-range repair controls have no usable binding.
fixture = build_repair_result_review_fixture(passed=True, seed="c-cross")
try:
    packet = fixture["repair_result_review"]
    cross = review._review_phrase(
        "propose-apply", packet["review_digest"], packet["proposal_id"], 1, 3
    )
    blocked = review.process_operator_repair_result_review_control(
        cross, runtime_root=fixture["runtime"]
    )
    require(blocked["event"] == "operator_repair_result_review_record_invalid")
    attempt_two = review._review_phrase(
        "propose-apply", packet["review_digest"], packet["proposal_id"], 1, 2, 2
    )
    blocked = review.process_operator_repair_result_review_control(
        attempt_two, runtime_root=fixture["runtime"]
    )
    require(blocked["event"] == "operator_repair_result_decision_not_allowed")
    require(blocked["operator_repair_result_review"]["reason"] == "repair_attempt_limit_exceeded")
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)


# Private exception text and Windows paths collapse to a type-only digest.
fixture = build_repair_result_review_fixture(passed=True, seed="c-private")
try:
    packet = fixture["repair_result_review"]
    phrase = next(value for value in packet["decision_phrases"] if "propose-apply" in value)
    private = r"C:\Users\PrivateUser\Private\candidate.py contains private-marker-value"
    with patch.object(
        review,
        "prepare_bounded_repaired_candidate_apply_proposal",
        side_effect=RuntimeError(private),
    ):
        blocked = review.process_operator_repair_result_review_control(
            phrase, runtime_root=fixture["runtime"]
        )
    encoded = json.dumps(blocked, sort_keys=True)
    require("reason_digest" in encoded)
    require("PrivateUser" not in encoded)
    require("candidate.py" not in encoded)
    require("private-marker-value" not in encoded)
    require(blocked["bounded_repaired_candidate_apply_proposal"]["apply_authorized"] is False)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)


module = (ROOT / "conscious_agent" / "operator_repair_result_review.py").read_text(encoding="utf-8")
require('"apply_authorized": True' not in module)
require('"release_authorized": True' not in module)
require('"authority_granted": True' not in module)
require("authorize_and_run_conversational_build_test_loop" not in module)
require("_workspace_root(" not in module)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1216.8-operator-repair-result-review-reliability"') == 2)
require(release.count("tools/v1216_6_8_operator_repair_result_review_reliability_tests.py") == 1)

print(json.dumps({
    "ok": True,
    "version": "1216.8",
    "checks": len(checks),
    "passed": sum(checks),
    "tamper_rejected": True,
    "conflicting_decision_rejected": True,
    "private_error_suppressed": True,
    "apply_executed": False,
}, sort_keys=True))
