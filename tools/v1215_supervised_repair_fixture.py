from __future__ import annotations

"""Deterministic private-runtime fixture for focused v1215 tests."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "conscious_agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "conscious_agent"))

import bounded_automatic_diagnosis as diagnosis
import conversational_build_test_continuation as continuation
import conversational_build_test_loop as loop
import operator_diagnosis_review as review
from operator_build_test_results import (
    create_or_resume_operator_build_test_result,
    record_operator_build_test_decision,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    approve_development_campaign_proposal,
    create_or_resume_development_proposal,
)


def provider_output(prompt: str, *, repaired: bool) -> str:
    contract = json.loads(prompt)
    content = {
        "main.py": (
            "import argparse\nfrom tool import count_words\n"
            "p=argparse.ArgumentParser()\np.add_argument('text', nargs='*')\n"
            "a=p.parse_args()\nprint(count_words(' '.join(a.text)))\n"
        ),
        "tool.py": (
            "def count_words(text):\n    return len(str(text).split())\n"
            if repaired
            else "def count_words(text):\n    return 0\n"
        ),
        "tests/test_tool.py": (
            "import unittest\nfrom tool import count_words\n"
            "class Tests(unittest.TestCase):\n"
            "    def test_words(self): self.assertEqual(count_words('one two'), 2)\n"
        ),
        "README.md": "# Word counter\n",
    }
    return json.dumps({
        "authority": contract["authority"],
        "files": [
            {
                "path": path,
                "operation": "create",
                "content": content[path],
            }
            for path in contract["planned_paths"]
        ],
    })


def build_authorized_repair_fixture(seed: str = "a") -> dict:
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1215-fixture-"))
    proposal = create_or_resume_development_proposal(
        "Build me a Python CLI that counts words", runtime_root=runtime
    )
    approve_development_campaign_proposal(
        proposal["proposal_id"],
        revision=1,
        revision_digest=proposal["revision_digest"],
        runtime_root=runtime,
    )
    parent = loop.prepare_conversational_build_test_loop(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime,
    )
    parent_path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    parent_record = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_result = {
        "ok": False,
        "schema_version": "1",
        "contract_version": "v1210.8",
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
        "phase": "sealed",
        "status": parent_result["status"],
        "result": parent_result,
        "result_digest": _digest(parent_result),
    })
    _atomic_json(parent_path, loop._seal(parent_record))

    presented = create_or_resume_operator_build_test_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_loop_digest=parent["loop_digest"],
        expected_loop_result_digest=parent_result["loop_result_digest"],
        runtime_root=runtime,
    )
    continuation_phrase = next(
        phrase for phrase in presented["decision_phrases"]
        if "prepare-next-attempt" in phrase
    )
    continuation_decision = record_operator_build_test_decision(
        proposal["proposal_id"],
        expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        decision="prepare-next-attempt",
        decision_phrase=continuation_phrase,
        runtime_root=runtime,
    )
    prepared_continuation = continuation.prepare_conversational_build_test_continuation(
        proposal["proposal_id"],
        expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        expected_continuation_digest=continuation_decision["continuation_digest"],
        runtime_root=runtime,
    )
    failed = continuation.authorize_and_run_conversational_build_test_continuation(
        proposal["proposal_id"],
        expected_revision=1,
        expected_operator_result_digest=presented["operator_result_digest"],
        expected_continuation_digest=continuation_decision["continuation_digest"],
        expected_attempt_digest=prepared_continuation["attempt_digest"],
        authorization_phrase=prepared_continuation["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=lambda prompt: provider_output(prompt, repaired=False),
        python_executable=sys.executable,
    )
    if failed.get("status") != "conversational_build_test_continuation_tests_failed":
        raise AssertionError(failed)

    diagnosed = diagnosis.run_or_resume_bounded_automatic_diagnosis(
        proposal["proposal_id"],
        expected_revision=1,
        expected_attempt_digest=prepared_continuation["attempt_digest"],
        expected_continuation_result_digest=failed["continuation_result_digest"],
        runtime_root=runtime,
    )
    packet = review.prepare_operator_diagnosis_review(
        proposal["proposal_id"],
        expected_revision=1,
        expected_attempt_number=2,
        expected_diagnosis_digest=diagnosed["diagnosis_digest"],
        expected_diagnosis_result_digest=diagnosed["diagnosis_result_digest"],
        runtime_root=runtime,
    )
    review_phrase = next(
        phrase for phrase in packet["decision_phrases"]
        if "Record propose-repair " in phrase
    )
    repair_decision = review.record_operator_diagnosis_decision(
        proposal["proposal_id"],
        expected_revision=1,
        expected_attempt_number=2,
        expected_review_digest=packet["review_digest"],
        decision="propose-repair",
        decision_phrase=review_phrase,
        runtime_root=runtime,
    )
    repair_proposal = review.prepare_bounded_repair_proposal(
        proposal["proposal_id"],
        expected_revision=1,
        expected_attempt_number=2,
        expected_review_digest=packet["review_digest"],
        expected_decision_digest=repair_decision["operator_diagnosis_decision_digest"],
        runtime_root=runtime,
    )
    return {
        "runtime": runtime,
        "proposal": proposal,
        "failed": failed,
        "diagnosis": diagnosed,
        "review": packet,
        "decision": repair_decision,
        "repair_proposal": repair_proposal,
        "seed": seed,
    }
