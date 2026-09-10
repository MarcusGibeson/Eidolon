from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import resource_concurrency_governance as resource
from v1233_resource_fixture import build_resource_fixture, resource_claim_spec


def requirement_spec(*, ambiguous: bool = False):
    return [
        {"code": "core_behavior", "category": "functional", "priority": "required", "criterion_state": "ambiguous" if ambiguous else "defined", "criterion_digest": "1" * 64},
        {"code": "acceptance_gate", "category": "acceptance", "priority": "required", "criterion_state": "defined", "criterion_digest": "2" * 64},
        {"code": "rollback_safety", "category": "rollback", "priority": "required", "criterion_state": "defined", "criterion_digest": "3" * 64},
        {"code": "goal_fit", "category": "goal_alignment", "priority": "required", "criterion_state": "defined", "criterion_digest": "4" * 64},
        {"code": "performance_budget", "category": "performance", "priority": "optional", "criterion_state": "defined", "criterion_digest": "5" * 64},
    ]


def evidence_spec(states=None):
    states = dict(states or {})
    rows = []
    defaults = {
        "core_behavior": "supports", "acceptance_gate": "supports", "rollback_safety": "supports",
        "goal_fit": "supports", "performance_budget": "supports",
    }
    for index, code in enumerate(defaults, 1):
        state = states.get(code, defaults[code])
        rows.append({
            "requirement_code": code,
            "evidence_type": "test" if code in {"core_behavior", "acceptance_gate", "performance_budget"} else "inspection",
            "state": state,
            "evidence_digest": f"{index:x}" * 64,
            "source_digest": f"{index + 5:x}" * 64,
        })
    return rows


def build_quality_fixture(seed: str = "v1234"):
    fixture = build_resource_fixture(seed)
    runtime = fixture["runtime"]
    launch = fixture["launch"]
    assessment = resource.prepare_resource_concurrency_governance_assessment(
        launch["launch_id"],
        expected_launch_digest=launch["launch_digest"],
        expected_monitor_digest=fixture["monitor"]["monitor_digest"],
        expected_control_digest=fixture["control"]["control_digest"],
        dependency_assessment_id=fixture["dependency_assessment"]["assessment_id"],
        expected_dependency_assessment_digest=fixture["dependency_assessment"]["assessment_digest"],
        dependency_review_id=fixture["dependency_review"]["review_id"],
        expected_dependency_review_digest=fixture["dependency_review"]["review_digest"],
        concurrency_limit=2,
        resource_claims=resource_claim_spec(),
        runtime_root=runtime,
    )
    assert assessment.get("ok"), assessment
    review = resource.review_resource_concurrency_governance_assessment(
        assessment["assessment_id"], expected_assessment_digest=assessment["assessment_digest"],
        disposition="confirm_admissible", runtime_root=runtime,
    )
    assert review.get("ok"), review
    return {**fixture, "resource_assessment": assessment, "resource_review": review}


def clone_runtime(runtime_root, label: str):
    parent = Path(tempfile.mkdtemp(prefix=f"eidolon-{label}-"))
    target = parent / "runtime"
    shutil.copytree(Path(runtime_root), target)
    return target
