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
from operator_build_test_results import (
    DECISIONS_BY_OUTCOME,
    create_or_resume_operator_build_test_result,
    project_operator_build_test_result,
    public_operator_build_test_record,
)

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def synthetic_loop(status: str, *, proposal_id: str = "devc_" + "a" * 24, revision: int = 1):
    result = {
        "ok": status == "conversational_build_test_completed",
        "schema_version": "1",
        "contract_version": "v1210.8",
        "status": status,
        "completed_stage": "complete" if status == "conversational_build_test_completed" else "test",
        "proposal_id": proposal_id,
        "proposal_revision": revision,
        "proposal_revision_digest": "b" * 64,
        "loop_digest": "c" * 64,
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "provider_contacted": True,
        "tests_executed": status not in {"conversational_build_test_build_blocked", "conversational_build_test_internal_error"},
        "test_passed": True if status == "conversational_build_test_completed" else (False if status == "conversational_build_test_tests_failed" else None),
        "cleanup_confirmed": True,
        "attempt_count": 1,
        "recovery_count": 0,
        "private_payload": "must never be projected",
    }
    result["loop_result_digest"] = _digest(result)
    record = {
        "proposal_id": proposal_id,
        "proposal_revision": revision,
        "loop_digest": "c" * 64,
        "phase": "sealed",
        "result": result,
        "result_digest": _digest(result),
    }
    return record


statuses = {
    "conversational_build_test_completed": "passed",
    "conversational_build_test_tests_failed": "tests_failed",
    "conversational_build_test_test_blocked": "test_blocked",
    "conversational_build_test_build_blocked": "build_blocked",
    "conversational_build_test_internal_error": "internal_error",
}
for status, outcome in statuses.items():
    projected = project_operator_build_test_result(synthetic_loop(status))
    require(projected["ok"] is True, projected)
    require(projected["outcome"] == outcome)
    require(projected["available_decisions"] == list(DECISIONS_BY_OUTCOME[outcome]))
    require(len(projected["operator_result_digest"]) == 64)
    require(len(projected["operator_result_record_digest"]) == 64)
    require(len(projected["decision_phrases"]) == 3)
    require(all(projected["operator_result_digest"] in phrase for phrase in projected["decision_phrases"]))
    encoded = json.dumps(public_operator_build_test_record(projected), sort_keys=True)
    require("must never be projected" not in encoded)
    require(projected["continuation_execution_authorized"] is False)
    require(projected["diagnosis_authorized"] is False)
    require(projected["repair_authorized"] is False)
    require(projected["apply_authorized"] is False)
    require(projected["release_authorized"] is False)
    require(projected["authority_granted"] is False)

runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1211-a-"))
try:
    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    approve_development_campaign_proposal(proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime)
    prepared = loop.prepare_conversational_build_test_loop(proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime)
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    sealed = synthetic_loop("conversational_build_test_completed", proposal_id=proposal["proposal_id"])
    sealed["loop_digest"] = prepared["loop_digest"]
    sealed["result"]["loop_digest"] = prepared["loop_digest"]
    sealed["result"]["proposal_revision_digest"] = proposal["revision_digest"]
    sealed["result"]["loop_result_digest"] = _digest({k: v for k, v in sealed["result"].items() if k != "loop_result_digest"})
    record.update({"phase": "sealed", "status": sealed["result"]["status"], "result": sealed["result"], "result_digest": _digest(sealed["result"])})
    _atomic_json(path, loop._seal(record))
    result = create_or_resume_operator_build_test_result(
        proposal["proposal_id"], expected_revision=1, expected_loop_digest=prepared["loop_digest"],
        expected_loop_result_digest=sealed["result"]["loop_result_digest"], runtime_root=runtime,
    )
    require(result["status"] == "operator_build_test_result_review_required", result)
    require(result["operation_status"] == "created")
    resumed = create_or_resume_operator_build_test_result(
        proposal["proposal_id"], expected_revision=1, expected_loop_digest=prepared["loop_digest"],
        expected_loop_result_digest=sealed["result"]["loop_result_digest"], runtime_root=runtime,
    )
    require(resumed["operation_status"] == "resumed")
    require(resumed["operator_result_digest"] == result["operator_result_digest"])
    require(str(runtime) not in json.dumps(public_operator_build_test_record(result), sort_keys=True))
finally:
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1211.2-operator-build-test-results-foundations"') == 2)
require(release.count("tools/v1211_0_2_operator_build_test_results_foundations_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1211.2", "checks": len(checks), "passed": sum(checks), "outcome_states": len(statuses), "provider_contacted": False, "tests_executed": False, "repair_authorized": False, "apply_authorized": False}, sort_keys=True))
