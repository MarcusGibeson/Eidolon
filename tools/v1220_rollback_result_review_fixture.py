from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1219_repaired_candidate_rollback_fixture import build_repaired_candidate_rollback_fixture


def build_rollback_result_review_fixture(seed: str = "a") -> dict:
    fixture = build_repaired_candidate_rollback_fixture(seed)
    runtime = fixture["runtime"]
    proposal = fixture["proposal"]
    rollback_proposal = fixture["rollback_proposal"]
    turn = process_ordinary_chat_development_turn(
        rollback_proposal["authorization_phrase"], runtime_root=runtime
    )
    result = turn.get("supervised_repaired_candidate_rollback") or {}
    review = turn.get("operator_repaired_candidate_rollback_result_review") or {}
    if result.get("ok") is not True or review.get("ok") is not True:
        raise AssertionError({"turn": turn})
    return {
        **fixture,
        "rollback_turn": turn,
        "rollback_result": result,
        "rollback_result_review": review,
    }
