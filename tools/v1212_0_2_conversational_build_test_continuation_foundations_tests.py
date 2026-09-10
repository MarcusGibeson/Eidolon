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
from conversational_build_test_continuation import prepare_conversational_build_test_continuation
from operator_build_test_results import create_or_resume_operator_build_test_result, record_operator_build_test_decision
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


def prepared_parent():
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1212-a-"))
    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    approve_development_campaign_proposal(
        proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    prepared = loop.prepare_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    result = {
        "ok": False,
        "schema_version": "1",
        "contract_version": "v1210.8",
        "status": "conversational_build_test_tests_failed",
        "completed_stage": "test",
        "proposal_id": proposal["proposal_id"],
        "proposal_revision": 1,
        "proposal_revision_digest": proposal["revision_digest"],
        "loop_digest": prepared["loop_digest"],
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "provider_contacted": True,
        "tests_executed": True,
        "test_passed": False,
        "cleanup_confirmed": True,
        "attempt_count": 1,
        "recovery_count": 0,
    }
    result["loop_result_digest"] = _digest(result)
    record.update({"phase": "sealed", "status": result["status"], "result": result, "result_digest": _digest(result)})
    _atomic_json(path, loop._seal(record))
    presented = create_or_resume_operator_build_test_result(
        proposal["proposal_id"], expected_revision=1, expected_loop_digest=prepared["loop_digest"],
        expected_loop_result_digest=result["loop_result_digest"], runtime_root=runtime,
    )
    decision_phrase = next(value for value in presented["decision_phrases"] if "prepare-next-attempt" in value)
    decision = record_operator_build_test_decision(
        proposal["proposal_id"], expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        decision="prepare-next-attempt", decision_phrase=decision_phrase, runtime_root=runtime,
    )
    return runtime, proposal, prepared, presented, decision


runtime, proposal, parent, presented, decision = prepared_parent()
try:
    prepared = prepare_conversational_build_test_continuation(
        proposal["proposal_id"], expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        expected_continuation_digest=decision["continuation_digest"], runtime_root=runtime,
    )
    require(prepared["ok"] is True, prepared)
    require(prepared["status"] == "build_test_continuation_authorization_required")
    require(prepared["attempt_number"] == 2)
    require(prepared["parent_loop_digest"] == parent["loop_digest"])
    require(prepared["operator_result_digest"] == presented["operator_result_digest"])
    require(prepared["continuation_digest"] == decision["continuation_digest"])
    require(len(prepared["attempt_digest"]) == 64)
    require(prepared["attempt_digest"] in prepared["authorization_phrase"])
    require(prepared["provider_contacted"] is False)
    require(prepared["tests_executed"] is False)
    require(prepared["continuation_execution_authorized"] is False)
    require(prepared["provider_contact_authorized"] is False)
    require(prepared["test_execution_authorized"] is False)
    require(prepared["diagnosis_authorized"] is False)
    require(prepared["repair_authorized"] is False)
    require(prepared["apply_authorized"] is False)
    require(prepared["release_authorized"] is False)
    require(prepared["authority_granted"] is False)
    replay = prepare_conversational_build_test_continuation(
        proposal["proposal_id"], expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        expected_continuation_digest=decision["continuation_digest"], runtime_root=runtime,
    )
    require(replay["operation_status"] == "resumed")
    require(replay["attempt_digest"] == prepared["attempt_digest"])
    stale = prepare_conversational_build_test_continuation(
        proposal["proposal_id"], expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        expected_continuation_digest="0" * 64, runtime_root=runtime,
    )
    require(stale["status"] == "build_test_continuation_stale_decision")
    require(stale["provider_contacted"] is False and stale["tests_executed"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# The ordinary chat decision path prepares and presents the exact v1212 control.
runtime, proposal, parent, presented, decision = prepared_parent()
try:
    phrase = next(value for value in presented["decision_phrases"] if "prepare-next-attempt" in value)
    # Replace the direct decision fixture with a new runtime so this is the first
    # ordinary-chat decision rather than an idempotent direct replay.
finally:
    shutil.rmtree(runtime, ignore_errors=True)

runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1212-a-chat-"))
try:
    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    approve_development_campaign_proposal(proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime)
    parent = loop.prepare_conversational_build_test_loop(proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime)
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    result = {"ok": False, "status": "conversational_build_test_build_blocked", "completed_stage": "build", "proposal_id": proposal["proposal_id"], "proposal_revision": 1, "proposal_revision_digest": proposal["revision_digest"], "loop_digest": parent["loop_digest"], "project_kind": "new_python_cli_project", "selected_adapter_id": "python", "provider_contacted": True, "tests_executed": False, "test_passed": None, "cleanup_confirmed": None, "attempt_count": 1, "recovery_count": 0}
    result["loop_result_digest"] = _digest(result)
    record.update({"phase": "sealed", "status": result["status"], "result": result, "result_digest": _digest(result)})
    _atomic_json(path, loop._seal(record))
    presented = create_or_resume_operator_build_test_result(proposal["proposal_id"], expected_revision=1, expected_loop_digest=parent["loop_digest"], expected_loop_result_digest=result["loop_result_digest"], runtime_root=runtime)
    phrase = next(value for value in presented["decision_phrases"] if "prepare-next-attempt" in value)
    turn = process_ordinary_chat_development_turn(phrase, runtime_root=runtime)
    require(turn["active"] is True)
    require(turn["build_test_continuation"]["status"] == "build_test_continuation_authorization_required", turn)
    require(turn["build_test_continuation"]["provider_contacted"] is False)
    require("Authorize continuation build and tests" in turn["conversation_response"])
finally:
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1212.2-conversational-build-test-continuation-foundations"') == 2)
require(release.count("tools/v1212_0_2_conversational_build_test_continuation_foundations_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1212.2", "checks": len(checks), "passed": sum(checks), "continuation_prepared": True, "provider_contacted": False, "tests_executed": False, "automatic_continuation": False, "repair_authorized": False}, sort_keys=True))
