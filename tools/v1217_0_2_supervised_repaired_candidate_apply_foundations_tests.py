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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1217-a-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import conversational_supervised_repaired_candidate_apply as repaired_apply
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
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


fixture = build_repaired_candidate_apply_fixture("a-foundation")
runtime = fixture["runtime"]
proposal = fixture["proposal"]
apply_proposal = fixture["apply_proposal"]
source_root = fixture["source_workspace_root"]
repaired_root = fixture["repaired_workspace_root"]
source_before = tree_digest(source_root)
repaired_before = tree_digest(repaired_root)
try:
    prepared = repaired_apply.prepare_supervised_repaired_candidate_apply(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_apply_proposal_digest=apply_proposal["apply_proposal_digest"],
        runtime_root=runtime,
    )
    require(prepared["ok"] is True, prepared)
    require(prepared["status"] == "supervised_repaired_candidate_apply_prepared")
    require(prepared["phase"] == "prepared")
    require(prepared["operation_count"] == 1)
    require(prepared["total_apply_bytes"] > 0)
    require(len(prepared["operation_path_digests"]) == 1)
    require(len(prepared["apply_plan_digest"]) == 64)
    require(len(prepared["supervised_repaired_candidate_apply_digest"]) == 64)
    require(prepared["apply_proposal_digest"] == apply_proposal["apply_proposal_digest"])
    require(prepared["source_workspace_digest"] == apply_proposal["source_workspace_digest"])
    require(prepared["repair_workspace_digest"] == apply_proposal["repair_workspace_digest"])
    require(prepared["repair_loop_result_digest"] == apply_proposal["repair_loop_result_digest"])
    require(prepared["authorization_phrase"] == apply_proposal["authorization_phrase"])
    require(prepared["apply_attempt_number"] == 1)
    require(prepared["apply_attempt_limit"] == 1)
    require(prepared["apply_authorized"] is False)
    require(prepared["rollback_prepared"] is False)
    require(prepared["rollback_authorized"] is False)
    require(prepared["project_modified"] is False)
    require(prepared["selected_project_modified"] is False)
    require(prepared["provider_contacted"] is False)
    require(prepared["tests_executed"] is False)
    require(prepared["release_authorized"] is False)
    require(prepared["authority_granted"] is False)
    require(tree_digest(source_root) == source_before)
    require(tree_digest(repaired_root) == repaired_before)

    replay = repaired_apply.prepare_supervised_repaired_candidate_apply(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_apply_proposal_digest=apply_proposal["apply_proposal_digest"],
        runtime_root=runtime,
    )
    require(replay["operation_status"] == "resumed")
    require(replay["supervised_repaired_candidate_apply_digest"] == prepared["supervised_repaired_candidate_apply_digest"])

    stale = repaired_apply.prepare_supervised_repaired_candidate_apply(
        proposal["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_apply_proposal_digest="0" * 64,
        runtime_root=runtime,
    )
    require(stale["status"] == "supervised_repaired_candidate_apply_stale_authorization")
    require(stale["apply_authorized"] is False)

    public = repaired_apply.public_supervised_repaired_candidate_apply(prepared)
    encoded = json.dumps(public, sort_keys=True)
    require(public["content_free"] is True)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)
    require(public["rollback_content_exposed"] is False)
    require(str(source_root) not in encoded)
    require(str(repaired_root) not in encoded)
    require("tool.py" not in encoded)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

for casual in (
    "It would be nice if the repaired candidate were applied.",
    'She said "Authorize repaired candidate apply proposal".',
    "Could an apply happen someday?",
    "Apply the fix.",
):
    require(repaired_apply.process_supervised_repaired_candidate_apply_control(casual) == {
        "active": False, "event": "inactive"
    })
    require(process_ordinary_chat_development_turn(casual)["active"] is False)

module = (ROOT / "conscious_agent" / "conversational_supervised_repaired_candidate_apply.py").read_text(encoding="utf-8")
require("authorize_and_run_conversational_build_test_loop" not in module)
require("LocalModelClient" not in module)
require('"install_authorized": True' not in module)
require('"promotion_authorized": True' not in module)
require('"release_authorized": True' not in module)
require('"authority_granted": True' not in module)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require(release.count('"v1217.2-supervised-repaired-candidate-apply-foundations"') == 2)
require(release.count("tools/v1217_0_2_supervised_repaired_candidate_apply_foundations_tests.py") == 1)
require('WORKING_SOURCE_VERSION = "1217.9"' in metadata)
require("v1217.0-v1217.2 Supervised Repaired-Candidate Apply Foundations" in metadata)

print(json.dumps({
    "ok": True,
    "version": "1217.2",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "preparation_non_executing": True,
    "exact_v1216_authorization_retained": True,
    "rollback_prepared": False,
    "apply_authorized": False,
    "release_authorized": False,
}, sort_keys=True))
