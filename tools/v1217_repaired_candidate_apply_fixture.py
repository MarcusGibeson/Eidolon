from __future__ import annotations

"""Deterministic private-runtime fixture for focused v1217 tests."""

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "conscious_agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "conscious_agent"))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from conversational_build_test_continuation import _attempt_runtime_root
from conversational_supervised_repair_execution import _repair_runtime_root
from isolated_implementation_workspace import _record_path, _workspace_root
import operator_repair_result_review as result_review
from ordinary_chat_development_campaign import _read_json
from v1216_repair_result_review_fixture import build_repair_result_review_fixture


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def workspace_material(
    proposal_id: str,
    *,
    revision: int,
    failed_attempt: int,
    repaired: bool,
    runtime_root: Path,
) -> tuple[dict, Path]:
    child = (
        _repair_runtime_root(proposal_id, revision, failed_attempt, runtime_root)
        if repaired
        else _attempt_runtime_root(proposal_id, revision, failed_attempt, runtime_root)
    )
    record = _read_json(_record_path(proposal_id, revision, child)) or {}
    root = _workspace_root(
        proposal_id, revision, str(record.get("generation_digest") or ""), child
    )
    return record, root


def build_repaired_candidate_apply_fixture(seed: str = "a") -> dict:
    fixture = build_repair_result_review_fixture(passed=True, seed=seed)
    runtime = fixture["runtime"]
    proposal = fixture["proposal"]
    review = fixture["repair_result_review"]
    phrase = next(
        value for value in review["decision_phrases"] if "propose-apply" in value
    )
    decision = result_review.record_operator_repair_result_decision(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"],
        decision="propose-apply",
        decision_phrase=phrase,
        runtime_root=runtime,
    )
    apply_proposal = result_review.prepare_bounded_repaired_candidate_apply_proposal(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_review_digest=review["review_digest"],
        expected_decision_digest=decision["operator_repair_result_decision_digest"],
        runtime_root=runtime,
    )
    if apply_proposal.get("status") != "bounded_repaired_candidate_apply_proposal_authorization_required":
        raise AssertionError(apply_proposal)
    source_record, source_root = workspace_material(
        proposal["proposal_id"],
        revision=1,
        failed_attempt=2,
        repaired=False,
        runtime_root=runtime,
    )
    repaired_record, repaired_root = workspace_material(
        proposal["proposal_id"],
        revision=1,
        failed_attempt=2,
        repaired=True,
        runtime_root=runtime,
    )
    return {
        **fixture,
        "repair_result_decision": decision,
        "apply_proposal": apply_proposal,
        "source_workspace_record": source_record,
        "source_workspace_root": source_root,
        "repaired_workspace_record": repaired_record,
        "repaired_workspace_root": repaired_root,
        "source_tree_digest": tree_digest(source_root),
        "repaired_tree_digest": tree_digest(repaired_root),
    }
