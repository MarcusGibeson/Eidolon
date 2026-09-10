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
import conversational_build_test_continuation as continuation
import conversational_build_test_loop as loop
from operator_build_test_results import (
    create_or_resume_operator_build_test_result,
    record_operator_build_test_decision,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    approve_development_campaign_proposal,
    create_or_resume_development_proposal,
    process_ordinary_chat_development_turn,
)

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def setup(status: str):
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1213-b-"))
    proposal = create_or_resume_development_proposal(
        "Build me a Python CLI that counts words", runtime_root=runtime
    )
    approve_development_campaign_proposal(
        proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    parent = loop.prepare_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"], runtime_root=runtime,
    )
    parent_path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    parent_record = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_result = {
        "ok": False,
        "status": "conversational_build_test_tests_failed",
        "completed_stage": "test",
        "proposal_id": proposal["proposal_id"],
        "proposal_revision": 1,
        "proposal_revision_digest": proposal["revision_digest"],
        "loop_digest": parent["loop_digest"],
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "provider_contacted": True,
        "tests_executed": True,
        "test_passed": False,
        "cleanup_confirmed": True,
        "attempt_count": 1,
        "recovery_count": 0,
    }
    parent_result["loop_result_digest"] = _digest(parent_result)
    parent_record.update({
        "phase": "sealed", "status": parent_result["status"],
        "result": parent_result, "result_digest": _digest(parent_result),
    })
    _atomic_json(parent_path, loop._seal(parent_record))
    presented = create_or_resume_operator_build_test_result(
        proposal["proposal_id"], expected_revision=1,
        expected_loop_digest=parent["loop_digest"],
        expected_loop_result_digest=parent_result["loop_result_digest"], runtime_root=runtime,
    )
    phrase = next(value for value in presented["decision_phrases"] if "prepare-next-attempt" in value)
    decision = record_operator_build_test_decision(
        proposal["proposal_id"], expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        decision="prepare-next-attempt", decision_phrase=phrase, runtime_root=runtime,
    )
    prepared = continuation.prepare_conversational_build_test_continuation(
        proposal["proposal_id"], expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        expected_continuation_digest=decision["continuation_digest"], runtime_root=runtime,
    )
    attempt_path = continuation._attempt_path(proposal["proposal_id"], 1, runtime)
    attempt_record = json.loads(attempt_path.read_text(encoding="utf-8"))
    stage = "internal" if "internal_error" in status else ("build" if "build_blocked" in status else "test")
    result = {
        "ok": False,
        "schema_version": "1",
        "contract_version": "v1212.8",
        "status": status,
        "completed_stage": stage,
        "proposal_id": proposal["proposal_id"],
        "proposal_revision": 1,
        "proposal_revision_digest": proposal["revision_digest"],
        "operator_result_digest": presented["operator_result_digest"],
        "continuation_digest": decision["continuation_digest"],
        "attempt_number": 2,
        "attempt_digest": prepared["attempt_digest"],
        "parent_loop_digest": parent["loop_digest"],
        "parent_loop_result_digest": parent_result["loop_result_digest"],
        "continuation_loop_digest": "c" * 64,
        "continuation_loop_result_digest": "d" * 64,
        "lineage": [
            {"attempt_number": 1, "attempt_kind": "initial", "loop_digest": parent["loop_digest"], "result_digest": parent_result["loop_result_digest"]},
            {"attempt_number": 2, "attempt_kind": "operator_authorized_continuation", "loop_digest": "c" * 64, "result_digest": "d" * 64},
        ],
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "provider_contacted": True,
        "tests_executed": "tests_failed" in status,
        "test_passed": False if "tests_failed" in status else None,
        "cleanup_confirmed": True,
        "operator_review_required": True,
        "automatic_continuation": False,
        "selected_project_modified": False,
        "source_modified": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
    result["lineage_digest"] = _digest(result["lineage"])
    result["continuation_result_digest"] = _digest(result)
    attempt_record.update({
        "phase": "sealed", "status": status,
        "result": result, "result_digest": _digest(result),
        "lease_token": "", "lease_expires_unix": 0.0,
    })
    _atomic_json(attempt_path, continuation._seal(attempt_record))
    return runtime, proposal, prepared, result


for status, expected_code in (
    ("conversational_build_test_continuation_tests_failed", "test_failure_observed"),
    ("conversational_build_test_continuation_test_blocked", "test_execution_blocked"),
    ("conversational_build_test_continuation_build_blocked", "build_stage_blocked"),
    ("conversational_build_test_continuation_internal_error", "continuation_pipeline_error_observed"),
):
    runtime, proposal, prepared, source_result = setup(status)
    try:
        result = diagnosis.run_or_resume_bounded_automatic_diagnosis(
            proposal["proposal_id"], expected_revision=1,
            expected_attempt_digest=prepared["attempt_digest"],
            expected_continuation_result_digest=source_result["continuation_result_digest"],
            runtime_root=runtime,
        )
        require(result["ok"] is True, result)
        require(result["status"] == "bounded_automatic_diagnosis_completed")
        require(result["diagnosis_performed"] is True)
        require(result["automatic_diagnosis"] is True)
        require(result["diagnosis_authorized"] is True)
        require(result["operator_authorized_diagnosis"] is False)
        require(result["diagnosis_count"] == 1)
        require(result["diagnosis_candidates"][0]["diagnosis_code"] == expected_code)
        require(result["diagnosis_candidates"][0]["confidence"] == "high_observation_low_root_cause")
        require(len(result["diagnosis_candidates"][0]["unknowns"]) == 2)
        require(result["root_cause_proven"] is False)
        require(result["operator_review_required"] is True)
        require(result["provider_contacted"] is False)
        require(result["tests_executed"] is False)
        require(result["repair_authorized"] is False)
        require(result["retest_authorized"] is False)
        require(result["apply_authorized"] is False)
        require(result["release_authorized"] is False)
        require(result["authority_granted"] is False)
        public = diagnosis.public_bounded_automatic_diagnosis(result)
        serialized = json.dumps(public, sort_keys=True)
        require(public["content_free"] is True)
        require(public["private_path_exposed"] is False)
        require("stdout" not in serialized.lower() and "stderr" not in serialized.lower())
        replay = diagnosis.run_or_resume_bounded_automatic_diagnosis(
            proposal["proposal_id"], expected_revision=1,
            expected_attempt_digest=prepared["attempt_digest"],
            expected_continuation_result_digest=source_result["continuation_result_digest"],
            runtime_root=runtime,
        )
        require(replay["operation_status"] == "resumed")
        require(replay["diagnosis_result_digest"] == result["diagnosis_result_digest"])
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


# The ordinary chat continuation result automatically receives one bounded
# diagnosis packet, with no new operator phrase and no repair authority.
runtime, proposal, prepared, source_result = setup(
    "conversational_build_test_continuation_tests_failed"
)
try:
    turn = process_ordinary_chat_development_turn(
        prepared["authorization_phrase"], runtime_root=runtime
    )
    require(turn["active"] is True)
    require(turn["event"] == "conversational_build_test_continuation_tests_failed")
    require(turn["build_test_continuation"]["operation_status"] == "resumed")
    automatic = turn["bounded_automatic_diagnosis"]
    require(automatic["status"] == "bounded_automatic_diagnosis_completed", turn)
    require(automatic["automatic_diagnosis"] is True)
    require(automatic["diagnosis_candidates"][0]["diagnosis_code"] == "test_failure_observed")
    require(automatic["root_cause_proven"] is False)
    require(automatic["repair_authorized"] is False)
    require("root cause is not proven" in turn["conversation_response"].lower())
    require("Authorize repair" not in turn["conversation_response"])
finally:
    shutil.rmtree(runtime, ignore_errors=True)


release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1213.5-bounded-automatic-diagnosis-execution"') == 2)
require(release.count("tools/v1213_3_5_bounded_automatic_diagnosis_execution_tests.py") == 1)
print(json.dumps({
    "ok": True,
    "version": "1213.5",
    "checks": len(checks),
    "passed": sum(checks),
    "automatic_diagnosis": True,
    "ordinary_chat_attached": True,
    "provider_calls": 0,
    "test_dispatches": 0,
    "root_cause_proven": False,
    "repair_authorized": False,
}, sort_keys=True))
