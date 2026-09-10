from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import requirement_quality_assessment as quality
from v1234_quality_fixture import build_quality_fixture, evidence_spec, requirement_spec


def build_lesson_fixture(seed: str = "v1235", *, evidence_states=None, quality_disposition: str | None = None):
    fixture = build_quality_fixture(seed)
    runtime = fixture["runtime"]
    assessment = quality.prepare_requirement_quality_assessment(
        fixture["resource_assessment"]["assessment_id"],
        expected_resource_assessment_digest=fixture["resource_assessment"]["assessment_digest"],
        resource_review_id=fixture["resource_review"]["review_id"],
        expected_resource_review_digest=fixture["resource_review"]["review_digest"],
        requirements=requirement_spec(),
        evidence=evidence_spec(evidence_states),
        runtime_root=runtime,
    )
    assert assessment.get("ok"), assessment
    if quality_disposition is None:
        quality_disposition = "accept_assessment" if assessment.get("all_required_requirements_satisfied") else "request_remediation"
    review = quality.review_requirement_quality_assessment(
        assessment["assessment_id"], expected_assessment_digest=assessment["assessment_digest"],
        disposition=quality_disposition, runtime_root=runtime,
    )
    assert review.get("ok"), review
    return {**fixture, "quality_assessment": assessment, "quality_review": review}


def clone_runtime(runtime_root, label: str):
    parent = Path(tempfile.mkdtemp(prefix=f"eidolon-{label}-"))
    target = parent / "runtime"
    shutil.copytree(Path(runtime_root), target)
    return target
