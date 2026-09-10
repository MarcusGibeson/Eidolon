from __future__ import annotations

"""Deterministic private-runtime fixture for focused v1218 tests."""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "conscious_agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "conscious_agent"))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import conversational_supervised_repaired_candidate_apply as repaired_apply
from v1217_repaired_candidate_apply_fixture import build_repaired_candidate_apply_fixture


def build_apply_result_review_fixture(*, applied: bool = True, seed: str = "a") -> dict:
    fixture = build_repaired_candidate_apply_fixture(seed)
    apply_proposal = fixture["apply_proposal"]
    proposal = fixture["proposal"]
    kwargs = {
        "proposal_id": proposal["proposal_id"],
        "expected_revision": 1,
        "expected_failed_attempt_number": 2,
        "expected_apply_proposal_digest": apply_proposal["apply_proposal_digest"],
        "authorization_phrase": apply_proposal["authorization_phrase"],
        "runtime_root": fixture["runtime"],
    }
    if applied:
        result = repaired_apply.authorize_and_apply_repaired_candidate(**kwargs)
    else:
        with patch.object(
            repaired_apply.shutil,
            "copyfile",
            side_effect=RuntimeError("private C:\\operator\\apply-error.txt"),
        ):
            result = repaired_apply.authorize_and_apply_repaired_candidate(**kwargs)
    if str(result.get("status") or "") not in repaired_apply.APPLY_RESULT_STATUSES:
        raise AssertionError(result)
    execution = repaired_apply.load_supervised_repaired_candidate_apply(
        proposal["proposal_id"], 1, 2, runtime_root=fixture["runtime"]
    )
    if execution.get("phase") != "sealed":
        raise AssertionError(execution)
    return {
        **fixture,
        "apply_result": result,
        "apply_execution": execution,
    }
