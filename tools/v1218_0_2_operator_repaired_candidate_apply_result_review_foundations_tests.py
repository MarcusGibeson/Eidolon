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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1218-a-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import operator_repaired_candidate_apply_result_review as apply_review
from v1218_apply_result_review_fixture import build_apply_result_review_fixture

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


for applied, expected_choices in ((True, 4), (False, 3)):
    fixture = build_apply_result_review_fixture(
        applied=applied, seed=f"a-{'applied' if applied else 'restored'}"
    )
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
        require(review["ok"] is True, review)
        require(review["status"] == "operator_repaired_candidate_apply_result_review_required")
        require(len(review["available_decisions"]) == expected_choices)
        require(len(review["decision_phrases"]) == expected_choices)
        require(review["rollback_eligible"] is applied)
        require(review["rollback_available"] is applied)
        require(("propose-rollback" in review["available_decisions"]) is applied)
        require(review["apply_result_status"] == result["status"])
        require(review["supervised_repaired_candidate_apply_result_digest"] == result["supervised_repaired_candidate_apply_result_digest"])
        require(review["rollback_manifest_digest"] == result["rollback_manifest_digest"])
        require(review["rollback_authorized"] is False)
        require(review["rollback_executed"] is False)
        require(review["provider_contacted"] is False)
        require(review["tests_executed"] is False)
        require(review["source_modified"] is False)
        replay = apply_review.prepare_operator_repaired_candidate_apply_result_review(
            proposal["proposal_id"],
            expected_revision=1,
            expected_failed_attempt_number=2,
            expected_execution_digest=result["supervised_repaired_candidate_apply_digest"],
            expected_result_digest=result["supervised_repaired_candidate_apply_result_digest"],
            runtime_root=runtime,
        )
        require(replay["operation_status"] == "resumed")
        require(replay["review_digest"] == review["review_digest"])
        public = apply_review.public_operator_repaired_candidate_apply_result_review(review)
        encoded = json.dumps(public, sort_keys=True)
        require(public["content_free"] is True)
        require(public["private_path_exposed"] is False)
        require(public["rollback_content_exposed"] is False)
        require(str(fixture["source_workspace_root"]) not in encoded)
        require("tool.py" not in encoded)
    finally:
        shutil.rmtree(runtime, ignore_errors=True)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1218.9"' in metadata)
require("v1218.0-v1218.2 Operator Repaired-Candidate Apply Result Review Foundations" in metadata)
require(release.count('"v1218.2-operator-repaired-candidate-apply-result-review-foundations"') == 2)

print(json.dumps({
    "ok": True,
    "version": "1218.2",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "review_non_executing": True,
    "rollback_separately_authorized": True,
}, sort_keys=True))
