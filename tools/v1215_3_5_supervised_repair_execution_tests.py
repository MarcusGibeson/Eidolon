from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1215-b-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1215_supervised_repair_fixture import build_authorized_repair_fixture, provider_output

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


fixture = build_authorized_repair_fixture("b")
runtime = fixture["runtime"]
calls: list[dict] = []


def repaired_provider(prompt: str) -> str:
    envelope = json.loads(prompt)
    calls.append(envelope)
    return provider_output(prompt, repaired=True)


try:
    bounded = fixture["repair_proposal"]
    turn = process_ordinary_chat_development_turn(
        bounded["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=repaired_provider,
        python_executable=sys.executable,
    )
    require(turn["active"] is True, turn)
    require(turn["event"] == "supervised_repair_completed", turn)
    public = turn["supervised_repair_execution"]
    require(public["ok"] is True)
    require(public["status"] == "supervised_repair_completed")
    require(public["completed_stage"] == "complete")
    require(public["repair_attempt_number"] == 1)
    require(public["repair_attempt_limit"] == 1)
    require(public["provider_contacted"] is True)
    require(public["tests_executed"] is True)
    require(public["retest_executed"] is True)
    require(public["test_passed"] is True)
    require(public["cleanup_confirmed"] is True)
    require(public["patch_generated"] is True)
    require(public["repair_executed"] is True)
    require(public["repair_execution_authorized"] is True)
    require(public["provider_contact_authorized"] is True)
    require(public["test_execution_authorized"] is True)
    require(public["retest_authorized"] is True)
    require(public["operator_review_required"] is True)
    require(public["repair_result_review_required"] is True)
    require(public["project_modified"] is False)
    require(public["selected_project_modified"] is False)
    require(public["source_modified"] is False)
    require(public["apply_authorized"] is False)
    require(public["install_authorized"] is False)
    require(public["promotion_authorized"] is False)
    require(public["release_authorized"] is False)
    require(public["authority_granted"] is False)
    require(len(public["repair_lineage"]) == 3)
    require(public["repair_lineage"][0]["stage"] == "failed_continuation_artifact")
    require(public["repair_lineage"][1]["stage"] == "authorized_repair_proposal")
    require(public["repair_lineage"][2]["stage"] == "isolated_repair_build_and_test")
    require(public["repair_lineage_digest"])
    require(public["source_workspace_digest"])
    require(public["repair_workspace_digest"])
    require(len(calls) == 1)
    repair_context = calls[0]["repair_context"]
    require(repair_context["repair_proposal_digest"] == bounded["repair_proposal_digest"])
    require(repair_context["source_workspace_digest"] == public["source_workspace_digest"])
    require(any(row["path"] == "tool.py" and "return 0" in row["content"] for row in repair_context["current_files"]))
    require(repair_context["authority_boundary"]["one_isolated_attempt"] is True)
    require(repair_context["authority_boundary"]["apply"] is False)
    serialized = json.dumps(turn, sort_keys=True)
    require("return 0" not in serialized)
    require("count_words" not in serialized)
    require(str(runtime) not in serialized)
    require("ready for operator review" in turn["conversation_response"].lower())
    require("nothing was applied" in turn["conversation_response"].lower())

    replay = process_ordinary_chat_development_turn(
        bounded["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=repaired_provider,
        python_executable=sys.executable,
    )
    require(replay["event"] == "supervised_repair_completed")
    require(replay["supervised_repair_execution"]["operation_status"] == "resumed")
    require(len(calls) == 1)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1215.5-supervised-repair-execution-and-verification"') == 2)
require(release.count("tools/v1215_3_5_supervised_repair_execution_tests.py") == 1)

print(json.dumps({
    "ok": True,
    "version": "1215.5",
    "checks": len(checks),
    "passed": sum(checks),
    "provider_calls": len(calls),
    "retests": 1,
    "repair_executed": True,
    "repair_applied": False,
}, sort_keys=True))
