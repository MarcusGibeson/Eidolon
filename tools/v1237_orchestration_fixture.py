from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import goal_motivation_work_priority_integration as alignment
from v1236_priority_fixture import build_priority_integration_fixture


def tool_spec():
    return [
        {
            "tool_id": "tool_project_inspector",
            "capability_codes": ["inspect_project"],
            "consumes": ["project_reference"],
            "produces": ["project_snapshot"],
            "input_contract_digest": "1" * 64,
            "output_contract_digest": "2" * 64,
            "risk_level": "low",
            "provider_required": False,
            "language_runtime_required": False,
            "mutation_capable": False,
        },
        {
            "tool_id": "tool_source_editor",
            "capability_codes": ["modify_source"],
            "consumes": ["project_snapshot"],
            "produces": ["candidate_snapshot"],
            "input_contract_digest": "3" * 64,
            "output_contract_digest": "4" * 64,
            "risk_level": "high",
            "provider_required": True,
            "language_runtime_required": False,
            "mutation_capable": True,
        },
        {
            "tool_id": "tool_test_dispatcher",
            "capability_codes": ["run_tests"],
            "consumes": ["candidate_snapshot"],
            "produces": ["test_evidence"],
            "input_contract_digest": "5" * 64,
            "output_contract_digest": "6" * 64,
            "risk_level": "medium",
            "provider_required": False,
            "language_runtime_required": True,
            "mutation_capable": False,
        },
        {
            "tool_id": "tool_evidence_reviewer",
            "capability_codes": ["inspect_evidence"],
            "consumes": ["test_evidence"],
            "produces": ["review_evidence"],
            "input_contract_digest": "7" * 64,
            "output_contract_digest": "8" * 64,
            "risk_level": "low",
            "provider_required": False,
            "language_runtime_required": False,
            "mutation_capable": False,
        },
        {
            "tool_id": "tool_proposal_preparer",
            "capability_codes": ["prepare_proposal"],
            "consumes": ["review_evidence"],
            "produces": ["continuation_proposal"],
            "input_contract_digest": "9" * 64,
            "output_contract_digest": "a" * 64,
            "risk_level": "low",
            "provider_required": False,
            "language_runtime_required": False,
            "mutation_capable": False,
        },
    ]


def step_spec():
    return [
        {"step_id": "step_inspect", "ordinal": 1, "tool_id": "tool_project_inspector", "action_code": "inspect_project", "depends_on": [], "consumes": ["project_reference"], "produces": ["project_snapshot"], "input_contract_digest": "1" * 64, "output_contract_digest": "2" * 64},
        {"step_id": "step_edit", "ordinal": 2, "tool_id": "tool_source_editor", "action_code": "modify_source", "depends_on": ["step_inspect"], "consumes": ["project_snapshot"], "produces": ["candidate_snapshot"], "input_contract_digest": "3" * 64, "output_contract_digest": "4" * 64},
        {"step_id": "step_test", "ordinal": 3, "tool_id": "tool_test_dispatcher", "action_code": "run_tests", "depends_on": ["step_edit"], "consumes": ["candidate_snapshot"], "produces": ["test_evidence"], "input_contract_digest": "5" * 64, "output_contract_digest": "6" * 64},
        {"step_id": "step_review", "ordinal": 4, "tool_id": "tool_evidence_reviewer", "action_code": "inspect_evidence", "depends_on": ["step_test"], "consumes": ["test_evidence"], "produces": ["review_evidence"], "input_contract_digest": "7" * 64, "output_contract_digest": "8" * 64},
        {"step_id": "step_propose", "ordinal": 5, "tool_id": "tool_proposal_preparer", "action_code": "prepare_proposal", "depends_on": ["step_review"], "consumes": ["review_evidence"], "produces": ["continuation_proposal"], "input_contract_digest": "9" * 64, "output_contract_digest": "a" * 64},
    ]


def build_orchestration_fixture(seed: str = "v1237"):
    fixture = build_priority_integration_fixture(seed)
    runtime = fixture["runtime"]
    alignment_assessment = alignment.prepare_goal_motivation_work_priority_integration(
        fixture["queue_item_id"],
        expected_prioritization_digest=fixture["ranking"]["prioritization_digest"],
        lesson_review_id=fixture["lesson_review"]["review_id"],
        expected_lesson_review_digest=fixture["lesson_review"]["review_digest"],
        runtime_root=runtime,
    )
    assert alignment_assessment.get("ok"), alignment_assessment
    alignment_review = alignment.review_goal_motivation_work_priority_integration(
        alignment_assessment["assessment_id"],
        expected_assessment_digest=alignment_assessment["assessment_digest"],
        disposition="accept_alignment",
        runtime_root=runtime,
    )
    assert alignment_review.get("ok"), alignment_review
    return {
        **fixture,
        "alignment_assessment": alignment_assessment,
        "alignment_review": alignment_review,
        "tools": tool_spec(),
        "steps": step_spec(),
        "initial_artifact_types": ["project_reference"],
    }


def clone_runtime(runtime_root, label: str):
    parent = Path(tempfile.mkdtemp(prefix=f"eidolon-{label}-"))
    target = parent / "runtime"
    shutil.copytree(Path(runtime_root), target)
    return target
