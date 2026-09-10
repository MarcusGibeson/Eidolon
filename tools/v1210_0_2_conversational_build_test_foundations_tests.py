from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from conversational_build_test_loop import prepare_conversational_build_test_loop, public_conversational_build_test_loop
from ordinary_chat_development_campaign import create_or_resume_development_proposal, approve_development_campaign_proposal, process_ordinary_chat_development_turn

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1210-a-"))
try:
    inactive = process_ordinary_chat_development_turn("It would be nice to have a Python utility.", runtime_root=runtime)
    require(inactive["active"] is False)

    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    blocked = prepare_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime,
    )
    require(blocked["status"] == "conversational_build_test_proposal_approval_required", blocked)
    approval = approve_development_campaign_proposal(
        proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime,
    )
    require(approval["status"] == "approval_consumed")
    prepared = prepare_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime,
    )
    require(prepared["ok"] is True, prepared)
    require(prepared["status"] == "conversational_build_test_authorization_required")
    require(prepared["phase"] == "prepared")
    require(prepared["project_kind"] == "new_python_cli_project")
    require(prepared["selected_adapter_id"] == "python")
    require(len(prepared["loop_digest"]) == 64)
    require(prepared["loop_digest"] in prepared["authorization_phrase"])
    require(prepared["tests_executed"] is False)
    require(prepared["provider_contacted"] is False)
    require(prepared["build_authorized"] is False)
    require(prepared["test_execution_authorized"] is False)
    require(prepared["repair_authorized"] is False)
    require(prepared["apply_authorized"] is False)
    require(prepared["release_authorized"] is False)
    require(prepared["authority_granted"] is False)
    resumed = prepare_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime,
    )
    require(resumed["operation_status"] == "resumed")
    require(resumed["loop_digest"] == prepared["loop_digest"])
    public = public_conversational_build_test_loop(prepared)
    encoded = json.dumps(public, sort_keys=True)
    require(str(runtime) not in encoded)
    require("counts words" not in encoded)
    require(public["private_request_exposed"] is False)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)

    # The ordinary approval path prepares the same exact loop and asks for a
    # distinct authorization rather than starting provider/test execution.
    runtime2 = Path(tempfile.mkdtemp(prefix="eidolon-v1210-a-chat-"))
    try:
        created = process_ordinary_chat_development_turn(
            "Build me a Python CLI that counts words",
            action_projection={"intent": {"category": "action_request"}},
            runtime_root=runtime2,
        )
        p = created["proposal"]
        turn = process_ordinary_chat_development_turn(
            f"Approve development proposal {p['proposal_id']} revision 1.", runtime_root=runtime2,
        )
        require(turn["event"] == "approval_consumed", turn)
        require(turn["build_test_loop"]["status"] == "conversational_build_test_authorization_required")
        require("Authorize build and tests" in turn["conversation_response"])
        require(turn["build_test_loop"]["tests_executed"] is False)
    finally:
        shutil.rmtree(runtime2, ignore_errors=True)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1210.2-conversational-build-test-foundations"') == 2)
require(release.count("tools/v1210_0_2_conversational_build_test_foundations_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1210.2", "checks": len(checks), "passed": sum(checks), "provider_contacted": False, "tests_executed": False, "apply_authorized": False, "release_authorized": False}, sort_keys=True))

