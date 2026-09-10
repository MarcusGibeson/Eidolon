from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1218-b-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import operator_repaired_candidate_apply_result_review as apply_review
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1218_apply_result_review_fixture import build_apply_result_review_fixture

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


fixture = build_apply_result_review_fixture(applied=True, seed="b-chat")
runtime = fixture["runtime"]
result = fixture["apply_result"]
proposal = fixture["proposal"]
try:
    review = apply_review.prepare_operator_repaired_candidate_apply_result_review(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest=result["supervised_repaired_candidate_apply_digest"],
        expected_result_digest=result["supervised_repaired_candidate_apply_result_digest"],
        runtime_root=runtime,
    )
    phrase = next(value for value in review["decision_phrases"] if "propose-rollback" in value)
    turn = process_ordinary_chat_development_turn(phrase, runtime_root=runtime)
    decision = turn["operator_repaired_candidate_apply_result_review"]
    rollback = turn["bounded_repaired_candidate_rollback_proposal"]
    require(turn["active"] is True, turn)
    require(decision["decision"] == "propose-rollback")
    require(decision["rollback_proposal_requested"] is True)
    require(rollback["ok"] is True, rollback)
    require(rollback["status"] == "bounded_repaired_candidate_rollback_proposal_authorization_required")
    require(rollback["rollback_scope"] == "one_selected_project_rollback_attempt")
    require(rollback["rollback_target"] == "exact_pre_apply_project_state")
    require(rollback["maximum_rollback_attempts"] == 1)
    require(rollback["rollback_manifest_digest"] == result["rollback_manifest_digest"])
    require(rollback["rollback_authorized"] is False)
    require(rollback["rollback_executed"] is False)
    require(rollback["project_modified"] is False)
    require(rollback["provider_contacted"] is False)
    require(rollback["tests_executed"] is False)
    require(rollback["release_authorized"] is False)
    require(rollback["authority_granted"] is False)
    require(rollback["rollback_proposal_digest"] in rollback["authorization_phrase"])
    require("Authorize repaired candidate rollback proposal" in rollback["authorization_phrase"])
    replay = process_ordinary_chat_development_turn(phrase, runtime_root=runtime)
    require(replay["bounded_repaired_candidate_rollback_proposal"]["operation_status"] == "resumed")
    require(replay["bounded_repaired_candidate_rollback_proposal"]["rollback_proposal_digest"] == rollback["rollback_proposal_digest"])
    conflict_phrase = next(value for value in review["decision_phrases"] if "accept-apply-result" in value)
    conflict = process_ordinary_chat_development_turn(conflict_phrase, runtime_root=runtime)
    require(conflict["operator_repaired_candidate_apply_result_review"]["status"] == "operator_repaired_candidate_apply_result_conflicting_decision")
    encoded = json.dumps(turn, sort_keys=True)
    require(str(fixture["source_workspace_root"]) not in encoded)
    require("tool.py" not in encoded)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

for casual in (
    "It would be nice to undo that someday.",
    'She said "Record propose-rollback".',
    "Could we roll it back?",
    "Rollback the fix.",
):
    require(apply_review.process_operator_repaired_candidate_apply_result_review_control(casual) == {"active": False, "event": "inactive"})
    require(process_ordinary_chat_development_turn(casual)["active"] is False)

module = (ROOT / "conscious_agent" / "operator_repaired_candidate_apply_result_review.py").read_text(encoding="utf-8")
require("LocalModelClient" not in module)
require('"rollback_authorized": True' not in module)
require('"release_authorized": True' not in module)
require('"authority_granted": True' not in module)

print(json.dumps({
    "ok": True,
    "version": "1218.5",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "ordinary_chat_integrated": True,
    "rollback_proposal_non_executing": True,
}, sort_keys=True))
