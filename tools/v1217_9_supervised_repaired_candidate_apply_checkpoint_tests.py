from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1217-9-data-"))
sys.path.insert(0, str(ROOT))

from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.supervised_repaired_candidate_apply_checkpoint import (
    build_supervised_repaired_candidate_apply_checkpoint,
)

CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


runtime_parent = Path(tempfile.mkdtemp(prefix="eidolon-v1217-9-"))
runtime = runtime_parent / "must-not-be-created"
try:
    report = build_supervised_repaired_candidate_apply_checkpoint(
        source_root=ROOT, runtime_root=runtime
    )
    require(report["ok"] is True, report)
    require(report["passed"] == report["total"])
    require(report["read_only"] is True)
    require(report["post_available"] is False)
    require(report["synthetic_contract_evaluation"] is True)
    require(report["runtime_data_read"] is False)
    require(report["runtime_mutated"] is False)
    require(report["source_modified"] is False)
    require(report["provider_contacted"] is False)
    require(report["project_tests_executed"] is False)
    require(report["retest_executed"] is False)
    require(report["repair_executed"] is False)
    require(report["apply_prepared_operationally"] is False)
    require(report["apply_executed"] is False)
    require(report["rollback_prepared_operationally"] is False)
    require(report["rollback_executed"] is False)
    require(report["project_modified"] is False)
    require(report["dependencies_installed"] is False)
    require(report["apply_authorized"] is False)
    require(report["rollback_authorized"] is False)
    require(report["release_authorized"] is False)
    require(report["authority_granted"] is False)
    require(report["global_profile_pass_claimed"] is False)
    require(report["summary"]["apply_result_outcome_count"] == 4)
    require(report["summary"]["apply_attempt_limit"] == 1)
    require(report["summary"]["exact_v1216_authorization_required"] is True)
    require(report["summary"]["rollback_evidence_required_before_write"] is True)
    require(report["summary"]["selected_project_scope_bound"] is True)
    require(report["summary"]["operator_review_required"] is True)
    require(report["summary"]["rollback_separately_authorized"] is True)
    require(report["summary"]["checkpoint_apply_executed"] is False)
    require(report["summary"]["authority_preserved"] is True)
    require(report["source_signature_before"] == report["source_signature_after"])
    require(report["source_file_count"] > 2640)
    require(len(report["structural_digest"]) == 64)
    require(not runtime.exists())
finally:
    shutil.rmtree(runtime_parent, ignore_errors=True)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((
    row for row in registry["checkpoints"]
    if row["checkpoint_id"] == "supervised-repaired-candidate-apply-checkpoint"
), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1217.9")
require((descriptor or {}).get("module") == "conscious_agent.supervised_repaired_candidate_apply_checkpoint")
require((descriptor or {}).get("builder") == "build_supervised_repaired_candidate_apply_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)

cli_runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1217-9-cli-"))
try:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "supervised-repaired-candidate-apply-checkpoint"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "EIDOLON_DATA_DIR": str(cli_runtime),
        },
    )
finally:
    shutil.rmtree(cli_runtime, ignore_errors=True)
require(completed.returncode == 0, completed.stderr)
cli = json.loads(completed.stdout.strip().splitlines()[-1])
require(cli["ok"] is True)
require(cli["contract_version"] == "v1217.9")
require(cli["read_only"] is True)
require(cli["apply_executed"] is False)
require(cli["rollback_executed"] is False)

api = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
route = 'parts == ["cognition", "supervised-repaired-candidate-apply-checkpoint"]'
require(api.count(route) == 1)
require("build_supervised_repaired_candidate_apply_checkpoint" in api)
require("POST /api/cognition/supervised-repaired-candidate-apply-checkpoint" not in api)

html = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("supervised-repaired-candidate-apply-checkpoint-panel" in html)
require("/api/cognition/supervised-repaired-candidate-apply-checkpoint" in html)
require("rollback evidence=${{view.rollback_evidence_required_before_write===true?'required':'review'}}" in html)
require("Conversational Supervised Repaired-Candidate Apply Checkpoint" in html)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1217.9-supervised-repaired-candidate-apply-checkpoint"') == 2)
require(release.count("tools/v1217_9_supervised_repaired_candidate_apply_checkpoint_tests.py") == 1)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1217.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1216.9"' in metadata)
require("Conversational Supervised Repaired-Candidate Apply Checkpoint" in metadata)
require("v1218.0-v1218.2" in metadata)

next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1217.9 Conversational Supervised Repaired-Candidate Apply Checkpoint" in next_steps)
require("v1218.0-v1218.2" in next_steps)
require("Completed across v1217.0-v1217.2" in next_steps)
require("Completed across v1217.3-v1217.5" in next_steps)
require("Completed across v1217.6-v1217.8" in next_steps)
require("Completed at v1217.9" in next_steps)
require("v1217.9 Conversational Supervised Repaired-Candidate Apply Checkpoint" in history)

print(json.dumps({
    "ok": True,
    "version": "1217.9",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "read_only": True,
    "post_available": False,
    "apply_executed": False,
    "rollback_executed": False,
    "apply_authorized": False,
}, sort_keys=True))
