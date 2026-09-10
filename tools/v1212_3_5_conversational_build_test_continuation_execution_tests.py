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


def setup():
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1212-b-"))
    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    approve_development_campaign_proposal(proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime)
    parent = loop.prepare_conversational_build_test_loop(proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime)
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    result = {
        "ok": False, "schema_version": "1", "contract_version": "v1210.8",
        "status": "conversational_build_test_tests_failed", "completed_stage": "test",
        "proposal_id": proposal["proposal_id"], "proposal_revision": 1,
        "proposal_revision_digest": proposal["revision_digest"], "loop_digest": parent["loop_digest"],
        "project_kind": "new_python_cli_project", "selected_adapter_id": "python",
        "provider_contacted": True, "tests_executed": True, "test_passed": False,
        "cleanup_confirmed": True, "attempt_count": 1, "recovery_count": 0,
    }
    result["loop_result_digest"] = _digest(result)
    record.update({"phase": "sealed", "status": result["status"], "result": result, "result_digest": _digest(result)})
    _atomic_json(path, loop._seal(record))
    presented = create_or_resume_operator_build_test_result(proposal["proposal_id"], expected_revision=1, expected_loop_digest=parent["loop_digest"], expected_loop_result_digest=result["loop_result_digest"], runtime_root=runtime)
    phrase = next(value for value in presented["decision_phrases"] if "prepare-next-attempt" in value)
    decision = record_operator_build_test_decision(proposal["proposal_id"], expected_revision=1, expected_operator_result_digest=presented["operator_result_digest"], decision="prepare-next-attempt", decision_phrase=phrase, runtime_root=runtime)
    continuation = prepare_conversational_build_test_continuation(proposal["proposal_id"], expected_revision=1, expected_operator_result_digest=presented["operator_result_digest"], expected_continuation_digest=decision["continuation_digest"], runtime_root=runtime)
    return runtime, proposal, continuation


provider_calls: list[int] = []
dispatch_calls: list[int] = []


def provider(prompt: str) -> str:
    provider_calls.append(1)
    contract = json.loads(prompt)
    content = {
        "main.py": "import argparse\nfrom tool import count_words\np=argparse.ArgumentParser()\np.add_argument('text', nargs='*')\na=p.parse_args()\nprint(count_words(' '.join(a.text)))\n",
        "tool.py": "def count_words(text):\n    return len(str(text).split())\n",
        "tests/test_tool.py": "import unittest\nfrom tool import count_words\nclass Tests(unittest.TestCase):\n    def test_words(self): self.assertEqual(count_words('one two'), 2)\n",
        "README.md": "# Word counter\n",
    }
    return json.dumps({"authority": contract["authority"], "files": [{"path": path, "operation": "create", "content": content[path]} for path in contract["planned_paths"]]})


original_dispatch = loop.run_or_resume_selected_test_adapter


def passing_dispatch(request, **kwargs):
    dispatch_calls.append(1)
    require(request["status"] == "test_adapter_execution_prepared", request)
    require(request["authority"]["execution_authorized"] is True)
    return {
        "status": "test_adapter_execution_completed", "tests_executed": True,
        "outcome": {"state": "passed", "passed": True, "evidence_digest": "e" * 64},
        "cleanup": {"state": "confirmed", "cleanup_confirmed": True},
        "reliability": {"failure_class": None, "retry_disposition": "not_needed"},
        "authority": {"execution_authorized": True, "repair_authorized": False, "apply_authorized": False, "release_authorized": False, "authority_granted": False},
    }


loop.run_or_resume_selected_test_adapter = passing_dispatch
runtime, proposal, continuation = setup()
try:
    turn = process_ordinary_chat_development_turn(
        continuation["authorization_phrase"], runtime_root=runtime, provider_generate=provider,
        python_executable=sys.executable,
    )
    require(turn["active"] is True)
    require(turn["event"] == "conversational_build_test_continuation_completed", turn)
    public = turn["build_test_continuation"]
    require(public["ok"] is True)
    require(public["attempt_number"] == 2)
    require(public["completed_stage"] == "complete")
    require(public["provider_contacted"] is True)
    require(public["tests_executed"] is True)
    require(public["test_passed"] is True)
    require(public["cleanup_confirmed"] is True)
    require(public["continuation_execution_authorized"] is True)
    require(public["provider_contact_authorized"] is True)
    require(public["test_execution_authorized"] is True)
    require(public["diagnosis_authorized"] is False)
    require(public["repair_authorized"] is False)
    require(public["apply_authorized"] is False)
    require(public["release_authorized"] is False)
    require(public["authority_granted"] is False)
    require(public["selected_project_modified"] is False)
    require(len(public["lineage"]) == 2)
    require(public["lineage"][0]["attempt_kind"] == "initial")
    require(public["lineage"][1]["attempt_kind"] == "operator_authorized_continuation")
    require(public["lineage"][1]["result_digest"] == public["continuation_loop_result_digest"])
    require(len(public["lineage_digest"]) == 64)
    require(len(provider_calls) == 1)
    require(len(dispatch_calls) == 1)
    replay = process_ordinary_chat_development_turn(
        continuation["authorization_phrase"], runtime_root=runtime, provider_generate=provider,
        python_executable=sys.executable,
    )
    require(replay["event"] == "conversational_build_test_continuation_completed")
    require(replay["build_test_continuation"]["operation_status"] == "resumed")
    require(len(provider_calls) == 1 and len(dispatch_calls) == 1)
    stale_phrase = continuation["authorization_phrase"].replace(continuation["attempt_digest"], "0" * 64)
    stale = process_ordinary_chat_development_turn(stale_phrase, runtime_root=runtime, provider_generate=provider)
    require(stale["event"] == "build_test_continuation_stale_authorization", stale)
    require(len(provider_calls) == 1 and len(dispatch_calls) == 1)
finally:
    loop.run_or_resume_selected_test_adapter = original_dispatch
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1212.5-conversational-build-test-continuation-execution"') == 2)
require(release.count("tools/v1212_3_5_conversational_build_test_continuation_execution_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1212.5", "checks": len(checks), "passed": sum(checks), "provider_calls": len(provider_calls), "test_dispatches": len(dispatch_calls), "attempt_lineage": 2, "selected_project_modified": False, "repair_authorized": False, "apply_authorized": False}, sort_keys=True))
