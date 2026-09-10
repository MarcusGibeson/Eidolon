from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import conversational_build_test_continuation as continuation
import conversational_build_test_loop as loop
from operator_build_test_results import create_or_resume_operator_build_test_result, record_operator_build_test_decision
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    approve_development_campaign_proposal,
    create_or_resume_development_proposal,
)

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def setup(prefix="eidolon-v1212-c-"):
    runtime = Path(tempfile.mkdtemp(prefix=prefix))
    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    approve_development_campaign_proposal(proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime)
    parent = loop.prepare_conversational_build_test_loop(proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime)
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    result = {
        "ok": False, "status": "conversational_build_test_test_blocked", "completed_stage": "test",
        "proposal_id": proposal["proposal_id"], "proposal_revision": 1,
        "proposal_revision_digest": proposal["revision_digest"], "loop_digest": parent["loop_digest"],
        "project_kind": "new_python_cli_project", "selected_adapter_id": "python",
        "provider_contacted": True, "tests_executed": False, "test_passed": None,
        "cleanup_confirmed": True, "attempt_count": 1, "recovery_count": 0,
    }
    result["loop_result_digest"] = _digest(result)
    record.update({"phase": "sealed", "status": result["status"], "result": result, "result_digest": _digest(result)})
    _atomic_json(path, loop._seal(record))
    presented = create_or_resume_operator_build_test_result(proposal["proposal_id"], expected_revision=1, expected_loop_digest=parent["loop_digest"], expected_loop_result_digest=result["loop_result_digest"], runtime_root=runtime)
    phrase = next(value for value in presented["decision_phrases"] if "prepare-next-attempt" in value)
    decision = record_operator_build_test_decision(proposal["proposal_id"], expected_revision=1, expected_operator_result_digest=presented["operator_result_digest"], decision="prepare-next-attempt", decision_phrase=phrase, runtime_root=runtime)
    prepared = continuation.prepare_conversational_build_test_continuation(proposal["proposal_id"], expected_revision=1, expected_operator_result_digest=presented["operator_result_digest"], expected_continuation_digest=decision["continuation_digest"], runtime_root=runtime)
    return runtime, proposal, presented, decision, prepared


def run(runtime, proposal, presented, decision, prepared):
    return continuation.authorize_and_run_conversational_build_test_continuation(
        proposal["proposal_id"], expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        expected_continuation_digest=decision["continuation_digest"],
        expected_attempt_digest=prepared["attempt_digest"],
        authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
    )


# A tampered parent attempt record fails before continuation execution.
runtime, proposal, presented, decision, prepared = setup()
try:
    path = continuation._attempt_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["selected_adapter_id"] = "browser_runtime"
    _atomic_json(path, record)
    blocked = run(runtime, proposal, presented, decision, prepared)
    require(blocked["status"] == "build_test_continuation_record_invalid", blocked)
    require(blocked["provider_contacted"] is False)
    require(blocked["tests_executed"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# A live lease blocks duplicate execution without provider or test activity.
runtime, proposal, presented, decision, prepared = setup()
try:
    path = continuation._attempt_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update({"phase": "running", "status": "build_test_continuation_running", "lease_token": "live", "lease_expires_unix": time.time() + 60, "continuation_execution_authorized": True, "provider_contact_authorized": True, "test_execution_authorized": True})
    _atomic_json(path, continuation._seal(record))
    blocked = run(runtime, proposal, presented, decision, prepared)
    require(blocked["status"] == "build_test_continuation_in_progress", blocked)
    require(blocked["provider_contacted"] is False and blocked["tests_executed"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# Private exceptions are reduced to a type digest, sealed, and replayed without
# repeating the failing operation or leaking a Windows-style runtime path.
runtime, proposal, presented, decision, prepared = setup("eidolon-v1212-c-win-")
original_seed = continuation._seed_attempt_runtime
calls: list[int] = []
try:
    def broken_seed(*args, **kwargs):
        calls.append(1)
        raise RuntimeError(f"private C:\\Users\\operator\\project {runtime}")

    continuation._seed_attempt_runtime = broken_seed
    failed = run(runtime, proposal, presented, decision, prepared)
    require(failed["status"] == "conversational_build_test_continuation_internal_error", failed)
    require(len(failed["reason"]) == 64)
    public = continuation.public_conversational_build_test_continuation(failed)
    serialized = json.dumps(public, sort_keys=True)
    require(str(runtime) not in serialized)
    require("C:\\\\Users" not in serialized and "eidolon-v1212-c-win" not in serialized)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)
    replay = run(runtime, proposal, presented, decision, prepared)
    require(replay["operation_status"] == "resumed")
    require(len(calls) == 1)
finally:
    continuation._seed_attempt_runtime = original_seed
    shutil.rmtree(runtime, ignore_errors=True)

# An expired lease is recoverable under the same exact authorization and its
# recovery count is recorded.  A synthetic retained result avoids real provider
# contact while exercising the lease/reconciliation boundary.
runtime, proposal, presented, decision, prepared = setup("eidolon-v1212-c-recovery-")
original_child_prepare = continuation.prepare_conversational_build_test_loop
original_child_run = continuation.authorize_and_run_conversational_build_test_loop
try:
    path = continuation._attempt_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update({"phase": "running", "status": "build_test_continuation_running", "lease_token": "expired", "lease_expires_unix": time.time() - 10, "recovery_count": 0, "continuation_execution_authorized": True, "provider_contact_authorized": True, "test_execution_authorized": True})
    _atomic_json(path, continuation._seal(record))
    continuation.prepare_conversational_build_test_loop = lambda *a, **k: {"ok": True, "loop_digest": "a" * 64, "authorization_phrase": "internal"}
    continuation.authorize_and_run_conversational_build_test_loop = lambda *a, **k: {"ok": True, "status": "conversational_build_test_completed", "loop_result_digest": "b" * 64, "provider_contacted": False, "tests_executed": True, "test_passed": True, "cleanup_confirmed": True}
    recovered = run(runtime, proposal, presented, decision, prepared)
    require(recovered["status"] == "conversational_build_test_continuation_completed", recovered)
    require(recovered["operation_status"] == "recovered")
    require(recovered["recovery_count"] == 1)
    require(recovered["lineage"][1]["loop_digest"] == "a" * 64)
    require(recovered["lineage"][1]["result_digest"] == "b" * 64)
finally:
    continuation.prepare_conversational_build_test_loop = original_child_prepare
    continuation.authorize_and_run_conversational_build_test_loop = original_child_run
    shutil.rmtree(runtime, ignore_errors=True)

source = (ROOT / "conscious_agent" / "conversational_build_test_continuation.py").read_text(encoding="utf-8")
for forbidden in (
    'diagnosis_authorized": True', 'repair_authorized": True', 'apply_authorized": True',
    'rollback_authorized": True', 'install_authorized": True', 'promotion_authorized": True',
    'release_authorized": True', 'model_management_authorized": True', 'authority_granted": True',
):
    require(forbidden not in source)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1212.8-conversational-build-test-continuation-reliability"') == 2)
require(release.count("tools/v1212_6_8_conversational_build_test_continuation_reliability_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1212.8", "checks": len(checks), "passed": sum(checks), "tamper_rejected": True, "duplicate_blocked": True, "expired_lease_recovered": True, "private_error_exposed": False, "automatic_continuation": False, "repair_authorized": False}, sort_keys=True))
