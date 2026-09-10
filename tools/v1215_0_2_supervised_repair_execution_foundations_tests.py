from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1215-a-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import conversational_supervised_repair_execution as repair
from v1215_supervised_repair_fixture import build_authorized_repair_fixture

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


fixture = build_authorized_repair_fixture("a")
runtime = fixture["runtime"]
try:
    proposal = fixture["proposal"]
    bounded = fixture["repair_proposal"]
    prepared = repair.prepare_conversational_supervised_repair_execution(
        proposal["proposal_id"],
        expected_revision=1,
        expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"],
        runtime_root=runtime,
    )
    require(prepared["ok"] is True, prepared)
    require(prepared["status"] == "supervised_repair_execution_prepared")
    require(prepared["phase"] == "prepared")
    require(prepared["repair_attempt_number"] == 1)
    require(prepared["repair_attempt_limit"] == 1)
    require(prepared["failed_attempt_number"] == 2)
    require(prepared["failed_attempt_digest"] == bounded["attempt_digest"])
    require(prepared["failed_continuation_result_digest"] == bounded["continuation_result_digest"])
    require(prepared["repair_proposal_digest"] == bounded["repair_proposal_digest"])
    require(prepared["source_workspace_digest"])
    require(prepared["project_kind"] == "new_python_cli_project")
    require(prepared["selected_adapter_id"] == "python")
    require(prepared["authorization_phrase"] == bounded["authorization_phrase"])
    require(prepared["provider_contacted"] is False)
    require(prepared["tests_executed"] is False)
    require(prepared["retest_executed"] is False)
    require(prepared["patch_generated"] is False)
    require(prepared["repair_executed"] is False)
    require(prepared["repair_execution_authorized"] is False)
    require(prepared["provider_contact_authorized"] is False)
    require(prepared["test_execution_authorized"] is False)
    require(prepared["retest_authorized"] is False)
    require(prepared["apply_authorized"] is False)
    require(prepared["release_authorized"] is False)
    require(prepared["authority_granted"] is False)
    replay = repair.prepare_conversational_supervised_repair_execution(
        proposal["proposal_id"],
        expected_revision=1,
        expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"],
        runtime_root=runtime,
    )
    require(replay["operation_status"] == "resumed")
    require(replay["supervised_repair_execution_digest"] == prepared["supervised_repair_execution_digest"])
    public = repair.public_conversational_supervised_repair(prepared)
    encoded = json.dumps(public, sort_keys=True)
    require(public["content_free"] is True)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)
    require("count_words" not in encoded)
    require(str(runtime) not in encoded)
    stale = repair.prepare_conversational_supervised_repair_execution(
        proposal["proposal_id"],
        expected_revision=1,
        expected_attempt_number=2,
        expected_repair_proposal_digest="0" * 64,
        runtime_root=runtime,
    )
    require(stale["status"] == "supervised_repair_stale_authorization")
    require(stale["repair_execution_authorized"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

for casual in (
    "It would be nice if you repaired it.",
    "Maybe authorize a repair someday.",
    'She said "Authorize repair proposal ..."',
    "Authorize repair.",
):
    require(repair.process_conversational_supervised_repair_control(casual) == {"active": False, "event": "inactive"})

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1215.2-supervised-repair-execution-foundations"') == 2)
require(release.count("tools/v1215_0_2_supervised_repair_execution_foundations_tests.py") == 1)

print(json.dumps({
    "ok": True,
    "version": "1215.2",
    "checks": len(checks),
    "passed": sum(checks),
    "repair_prepared": True,
    "provider_contacted": False,
    "tests_executed": False,
    "repair_executed": False,
}, sort_keys=True))
