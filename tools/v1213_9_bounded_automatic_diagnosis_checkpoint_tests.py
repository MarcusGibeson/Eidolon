from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from conscious_agent.bounded_automatic_diagnosis_checkpoint import build_bounded_automatic_diagnosis_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


with tempfile.TemporaryDirectory(prefix="eidolon-v1213-9-") as temp:
    runtime = Path(temp) / "must-not-exist"
    report = build_bounded_automatic_diagnosis_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(not runtime.exists())

for key, expected in (
    ("ok", True), ("contract_version", "v1213.9"), ("retained_contract_version", "v1213.8"),
    ("read_only", True), ("post_available", False), ("provider_contacted", False),
    ("project_tests_executed", False), ("diagnosis_runtime_executed", False),
    ("runtime_probed", False), ("runtime_data_read", False), ("runtime_mutated", False),
    ("source_modified", False), ("project_modified", False), ("dependencies_installed", False),
    ("automatic_diagnosis_contract", True), ("automatic_diagnosis_executed", False),
    ("root_cause_proven", False), ("automatic_repair", False), ("retest_authorized", False),
    ("repair_authorized", False), ("apply_authorized", False), ("release_authorized", False),
    ("authority_granted", False), ("global_profile_pass_claimed", False),
):
    require(report.get(key) == expected, (key, report.get(key)))
require(report["passed"] == report["total"])
require(report["source_signature_before"] == report["source_signature_after"])
require(report["summary"]["diagnosable_outcome_count"] == 4)
require(report["summary"]["successful_outcome_excluded"] is True)
require(report["summary"]["exact_continuation_binding_required"] is True)
require(report["summary"]["content_free_evidence_required"] is True)
require(report["summary"]["ordinary_chat_attachment_present"] is True)
require(report["summary"]["provider_free_diagnosis"] is True)
require(report["summary"]["test_free_diagnosis"] is True)
require(report["summary"]["root_cause_proven"] is False)
require(report["summary"]["operator_review_required"] is True)
require(report["summary"]["repair_authorized"] is False)
require(len(report["limitations"]) == 4)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "bounded-automatic-diagnosis-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1213.9")
require((descriptor or {}).get("builder") == "build_bounded_automatic_diagnosis_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "bounded-automatic-diagnosis-checkpoint"],
    cwd=ROOT, text=True, capture_output=True, timeout=120,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1213-9-cli-")},
)
require(process.returncode == 0, process.stderr)
cli = json.loads(process.stdout.strip().splitlines()[-1])
require(cli["contract_version"] == "v1213.9")
require(cli["ok"] is True)
require(cli["diagnosis_runtime_executed"] is False)

api = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
route = 'parts == ["cognition", "bounded-automatic-diagnosis-checkpoint"]'
require(api.count(route) == 1)
require("POST /api/cognition/bounded-automatic-diagnosis-checkpoint" not in api)
html = render_first_use_shell()
require("bounded-automatic-diagnosis-checkpoint-panel" in html)
require("/api/cognition/bounded-automatic-diagnosis-checkpoint" in html)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1213.9-bounded-automatic-diagnosis-checkpoint"') == 2)
require(release.count("tools/v1213_9_bounded_automatic_diagnosis_checkpoint_tests.py") == 1)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1213.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1212.9"' in metadata)

print(json.dumps({
    "ok": True,
    "version": "1213.9",
    "checks": len(checks),
    "passed": sum(checks),
    "read_only": True,
    "diagnosis_runtime_executed": False,
    "provider_contacted": False,
    "project_tests_executed": False,
    "root_cause_proven": False,
    "repair_authorized": False,
    "release_authorized": False,
}, sort_keys=True))
