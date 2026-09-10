from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1216-a-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import operator_repair_result_review as review
from v1216_repair_result_review_fixture import build_repair_result_review_fixture

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


passing_fixture = build_repair_result_review_fixture(passed=True, seed="a-pass")
failed_fixture = build_repair_result_review_fixture(passed=False, seed="a-fail")
try:
    passing = passing_fixture["repair_result_review"]
    result = passing_fixture["repair_result"]
    require(passing["ok"] is True, passing)
    require(passing["status"] == "operator_repair_result_review_required")
    require(passing["repair_result_status"] == "supervised_repair_completed")
    require(passing["repair_passed"] is True)
    require(passing["candidate_apply_eligible"] is True)
    require(passing["test_passed"] is True)
    require(passing["cleanup_confirmed"] is True)
    require(passing["repair_attempt_number"] == 1)
    require(passing["repair_attempt_limit"] == 1)
    require(passing["failed_attempt_number"] == 2)
    require(passing["supervised_repair_execution_digest"] == result["supervised_repair_execution_digest"])
    require(passing["supervised_repair_result_digest"] == result["supervised_repair_result_digest"])
    require(passing["source_workspace_digest"] == result["source_workspace_digest"])
    require(passing["repair_workspace_digest"] == result["repair_workspace_digest"])
    require(passing["repair_loop_result_digest"] == result["repair_loop_result_digest"])
    require(len(passing["available_decisions"]) == 4)
    require(passing["available_decisions"] == [
        "accept-repair-result", "defer", "reject-repair", "propose-apply"
    ])
    require(len(passing["decision_phrases"]) == 4)
    require(all(passing["review_digest"] in phrase for phrase in passing["decision_phrases"]))
    require(all("failed attempt 2 repair attempt 1" in phrase for phrase in passing["decision_phrases"]))
    require(passing["apply_proposal_created"] is False)
    require(passing["apply_authorization_required"] is False)
    require(passing["provider_contacted"] is False)
    require(passing["tests_executed"] is False)
    require(passing["retest_executed"] is False)
    require(passing["patch_generated"] is False)
    require(passing["repair_executed"] is False)
    require(passing["project_modified"] is False)
    require(passing["selected_project_modified"] is False)
    require(passing["source_modified"] is False)
    require(passing["apply_authorized"] is False)
    require(passing["release_authorized"] is False)
    require(passing["authority_granted"] is False)
    replay = review.prepare_operator_repair_result_review(
        passing["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest=result["supervised_repair_execution_digest"],
        expected_result_digest=result["supervised_repair_result_digest"],
        runtime_root=passing_fixture["runtime"],
    )
    require(replay["operation_status"] == "resumed")
    require(replay["review_digest"] == passing["review_digest"])
    require(len(passing_fixture["provider_calls"]) == 1)

    public = review.public_operator_repair_result_review(passing)
    encoded = json.dumps(public, sort_keys=True)
    require(public["content_free"] is True)
    require(public["private_request_exposed"] is False)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)
    require(public["raw_provider_output_exposed"] is False)
    require(public["raw_test_output_exposed"] is False)
    require("count_words" not in encoded)
    require("return 0" not in encoded)
    require(str(passing_fixture["runtime"]) not in encoded)

    stale_execution = review.prepare_operator_repair_result_review(
        passing["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest="0" * 64,
        expected_result_digest=result["supervised_repair_result_digest"],
        runtime_root=passing_fixture["runtime"],
    )
    require(stale_execution["status"] == "operator_repair_result_review_stale_execution")
    require(stale_execution["apply_authorized"] is False)
    stale_result = review.prepare_operator_repair_result_review(
        passing["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_execution_digest=result["supervised_repair_execution_digest"],
        expected_result_digest="f" * 64,
        runtime_root=passing_fixture["runtime"],
    )
    require(stale_result["status"] == "operator_repair_result_review_stale_result")

    failed = failed_fixture["repair_result_review"]
    require(failed["repair_result_status"] == "supervised_repair_tests_failed")
    require(failed["repair_passed"] is False)
    require(failed["candidate_apply_eligible"] is False)
    require(failed["test_passed"] is False)
    require(failed["available_decisions"] == [
        "accept-repair-result", "defer", "reject-repair"
    ])
    require("propose-apply" not in failed["available_decisions"])
    require(len(failed["decision_phrases"]) == 3)
    require(len(failed_fixture["provider_calls"]) == 1)
finally:
    shutil.rmtree(passing_fixture["runtime"], ignore_errors=True)
    shutil.rmtree(failed_fixture["runtime"], ignore_errors=True)

for casual in (
    "It would be nice to apply the repair.",
    "Maybe we should accept the repair result.",
    'She said "Record propose-apply for repair result review ..."',
    "Record propose-apply.",
):
    require(review.process_operator_repair_result_review_control(casual) == {
        "active": False, "event": "inactive"
    })

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1216.2-operator-repair-result-review-foundations"') == 2)
require(release.count("tools/v1216_0_2_operator_repair_result_review_foundations_tests.py") == 1)

print(json.dumps({
    "ok": True,
    "version": "1216.2",
    "checks": len(checks),
    "passed": sum(checks),
    "passing_candidate_apply_eligible": True,
    "failed_candidate_apply_eligible": False,
    "project_modified": False,
}, sort_keys=True))
