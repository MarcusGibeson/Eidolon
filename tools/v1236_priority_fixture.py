from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import evidence_backed_development_outcome_lessons as lessons
from persistent_motivation import MotivationStore
from v1235_lesson_fixture import build_lesson_fixture


def build_priority_integration_fixture(
    seed: str = "v1236",
    *,
    goal_valence: float = 0.9,
    motivation_valence: float = 0.7,
    goal_urgency: float = 0.95,
    motivation_urgency: float = 0.8,
    confidence: float = 0.9,
    include_goal: bool = True,
    include_motivation: bool = True,
    include_other_project: bool = True,
    accept_lesson: bool = True,
    evidence_states=None,
    quality_disposition: str | None = None,
):
    fixture = build_lesson_fixture(seed, evidence_states=evidence_states, quality_disposition=quality_disposition)
    runtime = Path(fixture["runtime"])
    queue_item_id = fixture["schedule"]["slots"][0]["queue_item_id"]
    priority_item = next(row for row in fixture["ranking"]["items"] if row["queue_item_id"] == queue_item_id)
    project_reference = priority_item["project_reference"]

    candidate = lessons.prepare_evidence_backed_development_lesson(
        fixture["quality_assessment"]["assessment_id"],
        expected_assessment_digest=fixture["quality_assessment"]["assessment_digest"],
        quality_review_id=fixture["quality_review"]["review_id"],
        expected_quality_review_digest=fixture["quality_review"]["review_digest"],
        runtime_root=runtime,
    )
    assert candidate.get("ok"), candidate
    lesson_review = {}
    if accept_lesson:
        lesson_review = lessons.review_evidence_backed_development_lesson(
            candidate["candidate_id"], expected_candidate_digest=candidate["candidate_digest"],
            disposition="accept", runtime_root=runtime,
        )
        assert lesson_review.get("ok"), lesson_review

    store = MotivationStore(runtime / "cognition")
    if include_goal:
        result = store.record_motivation(
            f"{seed}:goal",
            kind="enduring_goal",
            summary="content intentionally omitted from v1236 public evidence",
            cognitive_state="commitment",
            valence=goal_valence,
            urgency=goal_urgency,
            confidence=confidence,
            origin_type="operator_goal_evidence",
            origin_ref=f"{seed}:goal-ref",
            scope_project_id=project_reference,
            motivation_id="mot-v1236-goal",
        )
        assert result.get("ok"), result
    if include_motivation:
        result = store.record_motivation(
            f"{seed}:motivation",
            kind="concern" if motivation_valence < 0 else "preference",
            summary="content intentionally omitted from v1236 public evidence",
            cognitive_state="desire",
            valence=motivation_valence,
            urgency=motivation_urgency,
            confidence=confidence,
            origin_type="bounded_motivation_evidence",
            origin_ref=f"{seed}:motivation-ref",
            scope_project_id=project_reference,
            motivation_id="mot-v1236-motivation",
        )
        assert result.get("ok"), result
    if include_other_project:
        result = store.record_motivation(
            f"{seed}:other-project",
            kind="temporary_goal",
            summary="unrelated project content intentionally omitted",
            cognitive_state="desire",
            valence=1.0,
            urgency=1.0,
            confidence=1.0,
            origin_type="operator_goal_evidence",
            origin_ref=f"{seed}:other-ref",
            scope_project_id="project_other_scope",
            motivation_id="mot-v1236-other-project",
        )
        assert result.get("ok"), result

    return {
        **fixture,
        "queue_item_id": queue_item_id,
        "priority_item": priority_item,
        "project_reference": project_reference,
        "lesson_candidate": candidate,
        "lesson_review": lesson_review,
        "motivation_store": store,
    }


def clone_runtime(runtime_root, label: str):
    parent = Path(tempfile.mkdtemp(prefix=f"eidolon-{label}-"))
    target = parent / "runtime"
    shutil.copytree(Path(runtime_root), target)
    return target
