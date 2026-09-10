from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1218-9-data-"))
sys.path.insert(0, str(ROOT))

from conscious_agent.operator_repaired_candidate_apply_result_review_checkpoint import (
    build_operator_repaired_candidate_apply_result_review_checkpoint,
)

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1218-9-runtime-")) / "absent"
report = build_operator_repaired_candidate_apply_result_review_checkpoint(
    source_root=ROOT, runtime_root=runtime
)
require(report["ok"] is True, report)
require(report["passed"] == report["total"])
require(report["read_only"] is True)
require(report["post_available"] is False)
require(report["runtime_data_read"] is False)
require(report["runtime_mutated"] is False)
require(report["source_modified"] is False)
require(report["provider_contacted"] is False)
require(report["project_tests_executed"] is False)
require(report["apply_executed"] is False)
require(report["rollback_executed"] is False)
require(report["rollback_authorized"] is False)
require(report["release_authorized"] is False)
require(report["authority_granted"] is False)
require(report["source_signature_before"] == report["source_signature_after"])
require(runtime.exists() is False)
require(report["summary"]["apply_result_outcome_count"] == 4)
require(report["summary"]["rollback_eligible_decision_count"] == 4)
require(report["summary"]["separate_rollback_authorization_required"] is True)
require(report["summary"]["checkpoint_rollback_executed"] is False)

cli = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "operator-repaired-candidate-apply-result-review-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=120,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
)
require(cli.returncode == 0, cli.stderr)
payload = json.loads(cli.stdout)
require(payload["ok"] is True)
require(payload["read_only"] is True)
require(payload["rollback_executed"] is False)

api = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require('parts == ["cognition", "operator-repaired-candidate-apply-result-review-checkpoint"]' in api)
require("build_operator_repaired_candidate_apply_result_review_checkpoint" in api)
require("operator-repaired-candidate-apply-result-review-checkpoint-panel" in dashboard)
require("/api/cognition/operator-repaired-candidate-apply-result-review-checkpoint" in dashboard)
require("Operator Repaired-Candidate Apply Result Review and Rollback Proposal Checkpoint" in dashboard)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require(release.count('"v1218.9-operator-repaired-candidate-apply-result-review-checkpoint"') == 2)
require(release.count("tools/v1218_9_operator_repaired_candidate_apply_result_review_checkpoint_tests.py") == 1)
require('WORKING_SOURCE_VERSION = "1218.9"' in metadata)
require("v1218.9 Operator Repaired-Candidate Apply Result Review and Rollback Proposal Checkpoint" in metadata)

print(json.dumps({
    "ok": True,
    "version": "1218.9",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "checkpoint_checks": report["total"],
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "read_only": True,
    "rollback_executed": False,
}, sort_keys=True))
