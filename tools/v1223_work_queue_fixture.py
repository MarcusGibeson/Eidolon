from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from ordinary_chat_development_campaign import create_or_resume_development_proposal
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture


def build_work_queue_fixture(seed: str = "v1223") -> dict:
    fixture = build_rollback_result_review_fixture(seed)
    runtime = fixture["runtime"]
    other_path = str(Path(runtime) / "private-project-two")
    other = create_or_resume_development_proposal(
        "Build a small JavaScript calculator",
        project_state={"id": "project-two", "name": "Private Project Two", "path": other_path},
        runtime_root=runtime,
    )
    if not other.get("proposal_id"):
        raise AssertionError(other)
    return {**fixture, "other_proposal": other, "other_private_path": other_path}
