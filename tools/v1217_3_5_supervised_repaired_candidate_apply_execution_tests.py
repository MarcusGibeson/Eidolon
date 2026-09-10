from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1217-b-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import conversational_supervised_repaired_candidate_apply as repaired_apply
from ordinary_chat_development_campaign import _read_json, process_ordinary_chat_development_turn
from v1217_repaired_candidate_apply_fixture import (
    build_repaired_candidate_apply_fixture,
    tree_digest,
)

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


def assert_recorded_candidate_applied(fixture: dict) -> None:
    source = fixture["source_workspace_root"]
    repaired = fixture["repaired_workspace_root"]
    for row in fixture["repaired_workspace_record"]["files"]:
        relative = row["relative_path"]
        require((source / relative).read_bytes() == (repaired / relative).read_bytes())


fixture = build_repaired_candidate_apply_fixture("b-chat")
runtime = fixture["runtime"]
proposal = fixture["proposal"]
apply_proposal = fixture["apply_proposal"]
source_root = fixture["source_workspace_root"]
source_before = tree_digest(source_root)
provider_count = len(fixture["provider_calls"])
try:
    wrong = repaired_apply.authorize_and_apply_repaired_candidate(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_apply_proposal_digest=apply_proposal["apply_proposal_digest"],
        authorization_phrase="apply it",
        runtime_root=runtime,
    )
    require(wrong["status"] == "supervised_repaired_candidate_apply_exact_authorization_required")
    require(wrong["apply_authorized"] is False)
    require(tree_digest(source_root) == source_before)

    turn = process_ordinary_chat_development_turn(
        apply_proposal["authorization_phrase"], runtime_root=runtime
    )
    require(turn["active"] is True, turn)
    require(turn["event"] == "supervised_repaired_candidate_apply_completed", turn)
    result = turn["supervised_repaired_candidate_apply"]
    require(result["ok"] is True)
    require(result["status"] == "supervised_repaired_candidate_apply_completed")
    require(result["apply_authorized"] is True)
    require(result["authorization_consumption_count"] == 1)
    require(result["apply_attempt_number"] == 1)
    require(result["apply_attempt_limit"] == 1)
    require(result["rollback_prepared"] is True)
    require(result["rollback_available"] is True)
    require(result["rollback_executed"] is False)
    require(result["rollback_authorized"] is False)
    require(result["applied_count"] == 1)
    require(result["project_modified"] is True)
    require(result["selected_project_modified"] is True)
    require(result["operator_review_required"] is True)
    require(result["apply_result_review_required"] is True)
    require(result["provider_contacted"] is False)
    require(result["tests_executed"] is False)
    require(result["retest_executed"] is False)
    require(result["install_authorized"] is False)
    require(result["promotion_authorized"] is False)
    require(result["release_authorized"] is False)
    require(result["authority_granted"] is False)
    require(len(fixture["provider_calls"]) == provider_count)
    assert_recorded_candidate_applied(fixture)

    manifest = _read_json(repaired_apply._rollback_manifest_path(
        proposal["proposal_id"], 1, 2, runtime
    ))
    auth = _read_json(repaired_apply._authorization_path(
        proposal["proposal_id"], 1, 2, runtime
    ))
    require(repaired_apply._valid_manifest(manifest, repaired_apply.load_supervised_repaired_candidate_apply(
        proposal["proposal_id"], 1, 2, runtime_root=runtime
    )))
    require(repaired_apply._valid(auth, "authorization_receipt_digest"))
    require(auth["consumption_count"] == 1)
    require(manifest["entry_count"] == 1)
    require(manifest["rollback_authorized"] is False)

    replay = process_ordinary_chat_development_turn(
        apply_proposal["authorization_phrase"], runtime_root=runtime
    )
    require(replay["supervised_repaired_candidate_apply"]["operation_status"] == "resumed")
    require(replay["supervised_repaired_candidate_apply"]["authorization_consumption_count"] == 1)
    require(replay["supervised_repaired_candidate_apply"]["supervised_repaired_candidate_apply_result_digest"] == result["supervised_repaired_candidate_apply_result_digest"])
    require(len(fixture["provider_calls"]) == provider_count)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# A transactional write failure restores the exact source workspace from the
# already-sealed private backup and still consumes the one authorization once.
fixture = build_repaired_candidate_apply_fixture("b-rollback")
runtime = fixture["runtime"]
proposal = fixture["proposal"]
apply_proposal = fixture["apply_proposal"]
source_before = tree_digest(fixture["source_workspace_root"])
try:
    with patch.object(repaired_apply.shutil, "copyfile", side_effect=OSError("private C:\\Users\\Marcus\\candidate")):
        failed = repaired_apply.authorize_and_apply_repaired_candidate(
            proposal["proposal_id"],
            expected_revision=1,
            expected_failed_attempt_number=2,
            expected_apply_proposal_digest=apply_proposal["apply_proposal_digest"],
            authorization_phrase=apply_proposal["authorization_phrase"],
            runtime_root=runtime,
        )
    require(failed["ok"] is False)
    require(failed["status"] == "supervised_repaired_candidate_apply_failed_rolled_back")
    require(failed["authorization_consumption_count"] == 1)
    require(failed["rollback_prepared"] is True)
    require(failed["rollback_executed"] is True)
    require(failed["rollback_available"] is False)
    require(failed["selected_project_modified"] is False)
    require(tree_digest(fixture["source_workspace_root"]) == source_before)
    encoded = json.dumps(repaired_apply.public_supervised_repaired_candidate_apply(failed))
    require("Marcus" not in encoded)
    require("C:\\Users" not in encoded)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require(release.count('"v1217.5-supervised-repaired-candidate-apply-execution"') == 2)
require(release.count("tools/v1217_3_5_supervised_repaired_candidate_apply_execution_tests.py") == 1)
require("v1217.3-v1217.5 Conversational Repaired-Candidate Apply Execution" in metadata)

print(json.dumps({
    "ok": True,
    "version": "1217.5",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "exact_authorization_consumed_once": True,
    "transactional_apply": True,
    "rollback_evidence_prepared": True,
    "operator_review_required": True,
    "release_authorized": False,
}, sort_keys=True))
