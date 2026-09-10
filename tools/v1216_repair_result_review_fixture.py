from __future__ import annotations

"""Deterministic private-runtime fixture for focused v1216 tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "conscious_agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "conscious_agent"))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import conversational_supervised_repair_execution as repair
import operator_repair_result_review as result_review
from v1215_supervised_repair_fixture import (
    build_authorized_repair_fixture,
    provider_output,
)


def build_repair_result_review_fixture(*, passed: bool = True, seed: str = "a") -> dict:
    parent = build_authorized_repair_fixture(seed)
    runtime = parent["runtime"]
    proposal = parent["proposal"]
    bounded = parent["repair_proposal"]
    calls: list[str] = []

    def provider(prompt: str) -> str:
        calls.append(prompt)
        return provider_output(prompt, repaired=passed)

    result = repair.authorize_and_run_conversational_supervised_repair(
        proposal["proposal_id"],
        expected_revision=1,
        expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"],
        authorization_phrase=bounded["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    expected_status = (
        "supervised_repair_completed" if passed else "supervised_repair_tests_failed"
    )
    if result.get("status") != expected_status:
        raise AssertionError(result)
    review = result_review.prepare_operator_repair_result_review(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest=result["supervised_repair_execution_digest"],
        expected_result_digest=result["supervised_repair_result_digest"],
        runtime_root=runtime,
    )
    if review.get("status") != "operator_repair_result_review_required":
        raise AssertionError(review)
    return {
        **parent,
        "repair_result": result,
        "repair_result_review": review,
        "provider_calls": calls,
        "passed": passed,
    }
