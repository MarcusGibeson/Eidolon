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
sys.path.insert(0, str(ROOT))

from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.operator_diagnosis_review_checkpoint import build_operator_diagnosis_review_checkpoint

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


runtime_parent = Path(tempfile.mkdtemp(prefix="eidolon-v1214-9-"))
runtime = runtime_parent / "must-not-be-created"
try:
    report = build_operator_diagnosis_review_checkpoint(source_root=ROOT, runtime_root=runtime)
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
    require(report["patch_generated"] is False)
    require(report["repair_executed"] is False)
    require(report["project_modified"] is False)
    require(report["dependencies_installed"] is False)
    require(report["repair_execution_authorized"] is False)
    require(report["apply_authorized"] is False)
    require(report["release_authorized"] is False)
    require(report["authority_granted"] is False)
    require(report["global_profile_pass_claimed"] is False)
    require(report["summary"]["review_decision_count"] == 4)
    require(report["summary"]["exact_diagnosis_binding_required"] is True)
    require(report["summary"]["ordinary_chat_review_present"] is True)
    require(report["summary"]["repair_proposal_preparation_present"] is True)
    require(report["summary"]["separate_authorization_required"] is True)
    require(report["summary"]["repair_attempt_limit"] == 1)
    require(report["summary"]["provider_contacted"] is False)
    require(report["summary"]["tests_executed"] is False)
    require(report["summary"]["repair_executed"] is False)
    require(report["summary"]["project_modified"] is False)
    require(report["summary"]["privacy_preserved"] is True)
    require(report["summary"]["repair_execution_authorized"] is False)
    require(report["summary"]["authority_preserved"] is True)
    require(report["source_signature_before"] == report["source_signature_after"])
    require(report["source_file_count"] > 2500)
    require(len(report["structural_digest"]) == 64)
    require(not runtime.exists())
finally:
    shutil.rmtree(runtime_parent, ignore_errors=True)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next(
    (row for row in registry["checkpoints"] if row["checkpoint_id"] == "operator-diagnosis-review-checkpoint"),
    None,
)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1214.9")
require((descriptor or {}).get("module") == "conscious_agent.operator_diagnosis_review_checkpoint")
require((descriptor or {}).get("builder") == "build_operator_diagnosis_review_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)

cli_runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1214-9-cli-"))
try:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "operator-diagnosis-review-checkpoint"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": str(cli_runtime)},
    )
finally:
    shutil.rmtree(cli_runtime, ignore_errors=True)
require(completed.returncode == 0, completed.stderr)
cli = json.loads(completed.stdout.strip().splitlines()[-1])
require(cli["ok"] is True)
require(cli["contract_version"] == "v1214.9")
require(cli["read_only"] is True)
require(cli["repair_executed"] is False)

api = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
route = 'parts == ["cognition", "operator-diagnosis-review-checkpoint"]'
require(api.count(route) == 1)
require("build_operator_diagnosis_review_checkpoint" in api)
require("POST /api/cognition/operator-diagnosis-review-checkpoint" not in api)

html = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("operator-diagnosis-review-checkpoint-panel" in html)
require("/api/cognition/operator-diagnosis-review-checkpoint" in html)
require("repair executed=${{view.repair_executed===true?'yes':'no'}}" in html)
require("Repair Proposal Checkpoint" in html)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1214.9-operator-diagnosis-review-checkpoint"') == 2)
require(release.count("tools/v1214_9_operator_diagnosis_review_checkpoint_tests.py") == 1)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1214.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1213.9"' in metadata)
require("Operator Diagnosis Review and Repair Proposal Checkpoint" in metadata)
require("v1215.0-v1215.2" in metadata)

next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1214.9 Operator Diagnosis Review and Repair Proposal Checkpoint" in next_steps)
require("v1215.0-v1215.2" in next_steps)
require("Completed across v1214.0-v1214.2" in next_steps)
require("Completed across v1214.3-v1214.5" in next_steps)
require("Completed across v1214.6-v1214.8" in next_steps)
require("Completed at v1214.9" in next_steps)
require("v1214.9 Operator Diagnosis Review and Repair Proposal Checkpoint" in history)

print(json.dumps({
    "ok": True,
    "version": "1214.9",
    "checks": len(checks),
    "passed": sum(checks),
    "read_only": True,
    "post_available": False,
    "repair_executed": False,
    "repair_execution_authorized": False,
}, sort_keys=True))
