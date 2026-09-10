from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import execution_outcome_reflection_learning_integration as learning
from v1229_outcome_fixture import build_outcome_fixture


def build_mindful_execution_fixture(seed: str = "v1230", mode: str = "completed"):
    fixture = build_outcome_fixture(seed, mode)
    runtime = fixture["runtime"]
    launch = fixture["launch"]
    monitor = fixture["monitor"]
    control = fixture["control"]
    outcome = learning.prepare_execution_outcome(
        launch["launch_id"],
        outcome_type=mode,
        expected_launch_digest=launch["launch_digest"],
        expected_monitor_digest=monitor["monitor_digest"],
        expected_control_digest=control["control_digest"],
        runtime_root=runtime,
    )
    assert outcome.get("ok"), outcome
    reflection = learning.prepare_execution_outcome_reflection(
        outcome["outcome_id"],
        expected_outcome_digest=outcome["outcome_digest"],
        runtime_root=runtime,
    )
    assert reflection.get("ok"), reflection
    review = learning.review_execution_outcome_lesson(
        reflection["reflection_id"],
        expected_reflection_digest=reflection["reflection_digest"],
        disposition="accept" if not reflection.get("deliberate_silence") else "defer",
        runtime_root=runtime,
    )
    assert review.get("ok"), review
    return {
        **fixture,
        "outcome": outcome,
        "reflection": reflection,
        "lesson_review": review,
    }
