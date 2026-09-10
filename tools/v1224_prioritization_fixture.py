from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from ordinary_chat_development_campaign import create_or_resume_development_proposal
from v1223_work_queue_fixture import build_work_queue_fixture


def build_prioritization_fixture(seed: str = "v1224") -> dict:
    fixture = build_work_queue_fixture(seed)
    runtime = fixture["runtime"]
    third_path = str(Path(runtime) / "private-project-three")
    third = create_or_resume_development_proposal(
        "Build a small Python report utility",
        project_state={"id": "project-three", "name": "Private Project Three", "path": third_path},
        runtime_root=runtime,
    )
    if not third.get("proposal_id"):
        raise AssertionError(third)
    return {**fixture, "third_proposal": third, "third_private_path": third_path}
