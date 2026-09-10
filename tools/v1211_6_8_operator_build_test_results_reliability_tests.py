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
from ordinary_chat_development_campaign import _atomic_json, _digest, approve_development_campaign_proposal, create_or_resume_development_proposal
import operator_build_test_results as results

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def setup(runtime_prefix="eidolon-v1211-c-"):
    runtime = Path(tempfile.mkdtemp(prefix=runtime_prefix))
    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    approve_development_campaign_proposal(proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime)
    prepared = loop.prepare_conversational_build_test_loop(proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime)
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    result = {
        "ok": False, "schema_version": "1", "contract_version": "v1210.8", "status": "conversational_build_test_tests_failed",
        "completed_stage": "test", "proposal_id": proposal["proposal_id"], "proposal_revision": 1,
        "proposal_revision_digest": proposal["revision_digest"], "loop_digest": prepared["loop_digest"],
        "project_kind": "new_python_cli_project", "selected_adapter_id": "python", "provider_contacted": True,
        "tests_executed": True, "test_passed": False, "cleanup_confirmed": True, "attempt_count": 1, "recovery_count": 0,
    }
    result["loop_result_digest"] = _digest(result)
    record.update({"phase": "sealed", "status": result["status"], "result": result, "result_digest": _digest(result)})
    _atomic_json(path, loop._seal(record))
    presented = results.create_or_resume_operator_build_test_result(
        proposal["proposal_id"], expected_revision=1, expected_loop_digest=prepared["loop_digest"],
        expected_loop_result_digest=result["loop_result_digest"], runtime_root=runtime,
    )
    return runtime, proposal, prepared, result, presented


runtime, proposal, prepared, loop_result, presented = setup()
try:
    stale = results.create_or_resume_operator_build_test_result(
        proposal["proposal_id"], expected_revision=1, expected_loop_digest="0" * 64,
        expected_loop_result_digest=loop_result["loop_result_digest"], runtime_root=runtime,
    )
    require(stale["status"] == "operator_build_test_result_stale_loop")
    stale_result = results.create_or_resume_operator_build_test_result(
        proposal["proposal_id"], expected_revision=1, expected_loop_digest=prepared["loop_digest"],
        expected_loop_result_digest="0" * 64, runtime_root=runtime,
    )
    require(stale_result["status"] == "operator_build_test_result_stale_result")
    path = results._result_path(proposal["proposal_id"], 1, runtime)
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["outcome"] = "passed"
    _atomic_json(path, tampered)
    blocked = results.record_operator_build_test_decision(
        proposal["proposal_id"], expected_revision=1, expected_operator_result_digest=presented["operator_result_digest"],
        decision="prepare-next-attempt", decision_phrase=presented["decision_phrases"][0], runtime_root=runtime,
    )
    require(blocked["status"] == "operator_build_test_result_record_invalid", blocked)
    require(blocked["provider_contacted"] is False)
    require(blocked["tests_executed"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

runtime, proposal, prepared, loop_result, presented = setup("eidolon-v1211-c-win-")
try:
    phrase = presented["decision_phrases"][0]
    created = results.record_operator_build_test_decision(
        proposal["proposal_id"], expected_revision=1, expected_operator_result_digest=presented["operator_result_digest"],
        decision="prepare-next-attempt", decision_phrase=phrase, runtime_root=runtime,
    )
    require(created["operation_status"] == "created")
    path = results._decision_path(proposal["proposal_id"], 1, runtime)
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["decision"] = "defer"
    _atomic_json(path, stored)
    replay = results.record_operator_build_test_decision(
        proposal["proposal_id"], expected_revision=1, expected_operator_result_digest=presented["operator_result_digest"],
        decision="prepare-next-attempt", decision_phrase=phrase, runtime_root=runtime,
    )
    require(replay["status"] == "operator_build_test_continuation_record_invalid")
    public = json.dumps(results.public_operator_build_test_record(created), sort_keys=True)
    require(str(runtime) not in public)
    require("counts words" not in public)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

source = (ROOT / "conscious_agent" / "operator_build_test_results.py").read_text(encoding="utf-8")
for forbidden in (
    'continuation_execution_authorized": True', 'provider_contact_authorized": True',
    'test_execution_authorized": True', 'diagnosis_authorized": True',
    'repair_authorized": True', 'apply_authorized": True', 'release_authorized": True',
):
    require(forbidden not in source)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1211.8-operator-build-test-results-reliability"') == 2)
require(release.count("tools/v1211_6_8_operator_build_test_results_reliability_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1211.8", "checks": len(checks), "passed": sum(checks), "stale_rejected": True, "tamper_rejected": True, "private_content_exposed": False, "automatic_continuation": False, "repair_authorized": False}, sort_keys=True))
