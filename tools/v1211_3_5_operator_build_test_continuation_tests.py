from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import conversational_build_test_loop as loop
from ordinary_chat_development_campaign import _atomic_json, _digest, approve_development_campaign_proposal, create_or_resume_development_proposal, process_ordinary_chat_development_turn
from operator_build_test_results import create_or_resume_operator_build_test_result, record_operator_build_test_decision

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def prepared_result(status: str):
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1211-b-"))
    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    approve_development_campaign_proposal(proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime)
    prepared = loop.prepare_conversational_build_test_loop(proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime)
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    result = {
        "ok": status == "conversational_build_test_completed", "schema_version": "1", "contract_version": "v1210.8",
        "status": status, "completed_stage": "complete" if status == "conversational_build_test_completed" else "test",
        "proposal_id": proposal["proposal_id"], "proposal_revision": 1, "proposal_revision_digest": proposal["revision_digest"],
        "loop_digest": prepared["loop_digest"], "project_kind": "new_python_cli_project", "selected_adapter_id": "python",
        "provider_contacted": True, "tests_executed": status != "conversational_build_test_build_blocked",
        "test_passed": status == "conversational_build_test_completed", "cleanup_confirmed": True,
        "attempt_count": 1, "recovery_count": 0,
    }
    result["loop_result_digest"] = _digest(result)
    record.update({"phase": "sealed", "status": status, "result": result, "result_digest": _digest(result)})
    _atomic_json(path, loop._seal(record))
    presented = create_or_resume_operator_build_test_result(
        proposal["proposal_id"], expected_revision=1, expected_loop_digest=prepared["loop_digest"],
        expected_loop_result_digest=result["loop_result_digest"], runtime_root=runtime,
    )
    return runtime, proposal, presented


runtime, proposal, presented = prepared_result("conversational_build_test_tests_failed")
try:
    sealed_loop = loop.load_conversational_build_test_loop(proposal["proposal_id"], 1, runtime_root=runtime)
    ordinary_result = loop.process_conversational_build_test_control(
        loop._authorization_phrase(proposal["proposal_id"], 1, sealed_loop["loop_digest"]),
        runtime_root=runtime,
    )
    require(ordinary_result["active"] is True)
    require(ordinary_result["operator_build_test_result"]["status"] == "operator_build_test_result_review_required")
    require(ordinary_result["operator_build_test_result"]["outcome"] == "tests_failed")
    require("ready for your review" in ordinary_result["conversation_response"])
    phrase = next(value for value in presented["decision_phrases"] if "prepare-next-attempt" in value)
    turn = process_ordinary_chat_development_turn(phrase, runtime_root=runtime)
    require(turn["active"] is True)
    require(turn["event"] == "operator_build_test_decision_recorded", turn)
    continuation = turn["operator_build_test_result"]
    require(continuation["decision"] == "prepare-next-attempt")
    require(continuation["continuation_state"] == "next_attempt_prepared")
    require(continuation["continuation_prepared"] is True)
    require(continuation["provider_contacted"] is False)
    require(continuation["tests_executed"] is False)
    require(continuation["continuation_execution_authorized"] is False)
    require(continuation["test_execution_authorized"] is False)
    require(continuation["diagnosis_authorized"] is False)
    require(continuation["repair_authorized"] is False)
    require(continuation["apply_authorized"] is False)
    require(continuation["release_authorized"] is False)
    require(continuation["authority_granted"] is False)
    replay = process_ordinary_chat_development_turn(phrase, runtime_root=runtime)
    require(replay["operator_build_test_result"]["operation_status"] == "resumed")
    conflict_phrase = next(value for value in presented["decision_phrases"] if "defer" in value)
    conflict = process_ordinary_chat_development_turn(conflict_phrase, runtime_root=runtime)
    require(conflict["event"] == "operator_build_test_conflicting_decision", conflict)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

for status, decision, expected_state in (
    ("conversational_build_test_completed", "accept", "accepted"),
    ("conversational_build_test_completed", "defer", "deferred"),
    ("conversational_build_test_completed", "close", "closed"),
):
    runtime, proposal, presented = prepared_result(status)
    try:
        phrase = next(value for value in presented["decision_phrases"] if f"Record {decision} " in value)
        row = record_operator_build_test_decision(
            proposal["proposal_id"], expected_revision=1, expected_operator_result_digest=presented["operator_result_digest"],
            decision=decision, decision_phrase=phrase, runtime_root=runtime,
        )
        require(row["status"] == "operator_build_test_decision_recorded", row)
        require(row["continuation_state"] == expected_state)
        require(row["continuation_prepared"] is False)
        require(row["provider_contacted"] is False)
        require(row["tests_executed"] is False)
    finally:
        shutil.rmtree(runtime, ignore_errors=True)

inactive = process_ordinary_chat_development_turn("Maybe continue that build later.", runtime_root=Path(tempfile.mkdtemp(prefix="eidolon-v1211-inactive-")))
require(inactive["active"] is False)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1211.5-operator-build-test-continuation"') == 2)
require(release.count("tools/v1211_3_5_operator_build_test_continuation_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1211.5", "checks": len(checks), "passed": sum(checks), "ordinary_chat_control": True, "automatic_continuation": False, "provider_contacted": False, "tests_executed": False, "repair_authorized": False}, sort_keys=True))
