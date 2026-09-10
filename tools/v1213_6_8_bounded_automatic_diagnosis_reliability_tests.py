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

import bounded_automatic_diagnosis as diagnosis
import conversational_build_test_continuation as continuation
from ordinary_chat_development_campaign import _atomic_json, _digest

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def setup(prefix="eidolon-v1213-c-"):
    runtime = Path(tempfile.mkdtemp(prefix=prefix))
    proposal_id = "devc_" + "2" * 24
    lineage = [
        {"attempt_number": 1, "attempt_kind": "initial", "loop_digest": "a" * 64, "result_digest": "b" * 64},
        {"attempt_number": 2, "attempt_kind": "operator_authorized_continuation", "loop_digest": "c" * 64, "result_digest": "d" * 64},
    ]
    result = {
        "ok": False,
        "schema_version": "1",
        "contract_version": "v1212.8",
        "status": "conversational_build_test_continuation_test_blocked",
        "completed_stage": "test",
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "proposal_revision_digest": "3" * 64,
        "attempt_number": 2,
        "attempt_digest": "4" * 64,
        "parent_loop_result_digest": "b" * 64,
        "continuation_loop_result_digest": "d" * 64,
        "lineage": lineage,
        "lineage_digest": _digest(lineage),
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "provider_contacted": True,
        "tests_executed": False,
        "test_passed": None,
        "cleanup_confirmed": True,
        "operator_review_required": True,
        "automatic_continuation": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
    result["continuation_result_digest"] = _digest(result)
    continuation_record = {
        "phase": "sealed",
        "status": result["status"],
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "attempt_number": 2,
        "attempt_digest": result["attempt_digest"],
        "result": result,
        "result_digest": _digest(result),
    }
    continuation_path = continuation._attempt_path(proposal_id, 1, runtime)
    _atomic_json(continuation_path, continuation._seal(continuation_record))
    prepared = diagnosis.prepare_bounded_automatic_diagnosis(
        proposal_id, expected_revision=1,
        expected_attempt_digest=result["attempt_digest"],
        expected_continuation_result_digest=result["continuation_result_digest"],
        runtime_root=runtime,
    )
    return runtime, proposal_id, result, prepared, continuation_path


def run(runtime, proposal_id, source_result):
    return diagnosis.run_or_resume_bounded_automatic_diagnosis(
        proposal_id, expected_revision=1,
        expected_attempt_digest=source_result["attempt_digest"],
        expected_continuation_result_digest=source_result["continuation_result_digest"],
        runtime_root=runtime,
    )


# A tampered prepared diagnosis fails closed.
runtime, proposal_id, source_result, prepared, _ = setup()
try:
    path = diagnosis._diagnosis_path(proposal_id, 1, 2, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["selected_adapter_id"] = "browser_runtime"
    _atomic_json(path, record)
    blocked = run(runtime, proposal_id, source_result)
    require(blocked["status"] == "bounded_automatic_diagnosis_record_invalid", blocked)
    require(blocked["diagnosis_performed"] is False)
    require(blocked["provider_contacted"] is False and blocked["tests_executed"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# A live lease blocks a duplicate without running diagnosis twice.
runtime, proposal_id, source_result, prepared, _ = setup()
try:
    path = diagnosis._diagnosis_path(proposal_id, 1, 2, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update({
        "phase": "running", "status": "bounded_automatic_diagnosis_running",
        "lease_token": "live", "lease_expires_unix": time.time() + 60,
        "automatic_diagnosis": True, "diagnosis_authorized": True,
    })
    _atomic_json(path, diagnosis._seal(record))
    blocked = run(runtime, proposal_id, source_result)
    require(blocked["status"] == "bounded_automatic_diagnosis_in_progress", blocked)
    require(blocked["diagnosis_performed"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# An expired lease resumes under the same evidence digest.
runtime, proposal_id, source_result, prepared, _ = setup("eidolon-v1213-c-recovery-")
try:
    path = diagnosis._diagnosis_path(proposal_id, 1, 2, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update({
        "phase": "running", "status": "bounded_automatic_diagnosis_running",
        "lease_token": "expired", "lease_expires_unix": time.time() - 10,
        "recovery_count": 0, "automatic_diagnosis": True, "diagnosis_authorized": True,
    })
    _atomic_json(path, diagnosis._seal(record))
    recovered = run(runtime, proposal_id, source_result)
    require(recovered["status"] == "bounded_automatic_diagnosis_completed", recovered)
    require(recovered["operation_status"] == "recovered")
    require(recovered["recovery_count"] == 1)
    require(recovered["evidence_digest"] == prepared["evidence_digest"])
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# Private exceptions collapse to a type-only digest and replay without another
# diagnostic operation or a Windows/private runtime path leak.
runtime, proposal_id, source_result, prepared, _ = setup("eidolon-v1213-c-win-")
original_diagnose = diagnosis._diagnose_evidence
calls: list[int] = []
try:
    def broken_diagnosis(evidence):
        calls.append(1)
        raise RuntimeError(f"private C:\\Users\\operator\\secret {runtime}")

    diagnosis._diagnose_evidence = broken_diagnosis
    failed = run(runtime, proposal_id, source_result)
    require(failed["status"] == "bounded_automatic_diagnosis_internal_error", failed)
    require(len(failed["reason"]) == 64)
    public = diagnosis.public_bounded_automatic_diagnosis(failed)
    serialized = json.dumps(public, sort_keys=True)
    require(str(runtime) not in serialized)
    require("C:\\\\Users" not in serialized)
    require("secret" not in serialized)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)
    require(public["repair_authorized"] is False)
    replay = run(runtime, proposal_id, source_result)
    require(replay["operation_status"] == "resumed")
    require(len(calls) == 1)
finally:
    diagnosis._diagnose_evidence = original_diagnose
    shutil.rmtree(runtime, ignore_errors=True)


# Continuation tampering or a changed evidence binding blocks replay.
runtime, proposal_id, source_result, prepared, continuation_path = setup("eidolon-v1213-c-stale-")
try:
    continuation_record = json.loads(continuation_path.read_text(encoding="utf-8"))
    continuation_record["result"]["selected_adapter_id"] = "browser_runtime"
    _atomic_json(continuation_path, continuation_record)
    blocked = run(runtime, proposal_id, source_result)
    require(blocked["status"] == "bounded_automatic_diagnosis_continuation_invalid", blocked)
    require(blocked["repair_authorized"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


source = (ROOT / "conscious_agent" / "bounded_automatic_diagnosis.py").read_text(encoding="utf-8")
for forbidden in (
    'repair_authorized": True', 'retest_authorized": True', 'apply_authorized": True',
    'rollback_authorized": True', 'install_authorized": True', 'promotion_authorized": True',
    'release_authorized": True', 'model_management_authorized": True', 'authority_granted": True',
):
    require(forbidden not in source)
require("provider_generate" not in source)
require("subprocess" not in source)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1213.8-bounded-automatic-diagnosis-reliability"') == 2)
require(release.count("tools/v1213_6_8_bounded_automatic_diagnosis_reliability_tests.py") == 1)
print(json.dumps({
    "ok": True,
    "version": "1213.8",
    "checks": len(checks),
    "passed": sum(checks),
    "tamper_rejected": True,
    "duplicate_blocked": True,
    "expired_lease_recovered": True,
    "private_error_exposed": False,
    "root_cause_proven": False,
    "repair_authorized": False,
}, sort_keys=True))
