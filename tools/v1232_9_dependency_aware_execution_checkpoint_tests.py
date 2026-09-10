from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1232-api-"))

from dependency_aware_execution_checkpoint import build_dependency_aware_execution_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import handle_api_get

checks: list[bool] = []

def check(value):
    checks.append(bool(value))


report = build_dependency_aware_execution_checkpoint(source_root=ROOT)
for value in (
    report.get("ok"),
    report.get("checkpoint_id") == "dependency-aware-execution-checkpoint",
    report.get("contract_version") == "v1232.9",
    report.get("retained_contract_version") == "v1232.8",
    report.get("milestone_name") == "Dependency-Aware Execution",
    report.get("roadmap_path") == "Balanced Mind-and-Action Path 3",
    report.get("read_only") is True,
    report.get("content_free") is True,
    report.get("source_signature_unchanged") is True,
    report.get("source_file_count_before") == report.get("source_file_count_after"),
    report.get("runtime_data_read") is False,
    report.get("runtime_data_written") is False,
    report.get("provider_contacted") is False,
    report.get("commands_executed") is False,
    report.get("tests_executed") is False,
    report.get("project_modified") is False,
    report.get("queue_modified") is False,
    report.get("schedule_modified") is False,
    report.get("source_modified") is False,
    report.get("cognition_written") is False,
    report.get("authority_granted") is False,
    report.get("release_authorized") is False,
    report.get("execution_session_launch_authorized") is False,
    report.get("resume_authorized") is False,
    report.get("old_authority_reusable") is False,
    report.get("passed") == report.get("total"),
):
    check(value)

proc = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "dependency-aware-execution-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=120,
)
check(proc.returncode == 0)
try:
    cli = json.loads(proc.stdout.strip().splitlines()[-1])
    check(cli.get("ok") is True)
    check(cli.get("checkpoint_id") == "dependency-aware-execution-checkpoint")
except Exception:
    check(False)
    check(False)

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "dependency-aware-execution-checkpoint"), {})
check(row.get("contract_version") == "v1232.9")
check(row.get("read_only") is True)
check(row.get("required_input_count") == 0)

for route, expected in (
    ("/api/cognition/dependency-aware-execution-checkpoint", "dependency-aware-execution-checkpoint"),
    ("/api/cognition/dependency-aware-execution-assessments", None),
    ("/api/cognition/dependency-aware-execution-reviews", None),
):
    status, payload = handle_api_get(route)
    check(status == 200)
    check(payload.get("ok") is True)
    data = payload.get("data") or {}
    check(data.get("checkpoint_id") == expected if expected else data.get("content_free") is True)

print(json.dumps({
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
    "internal_passed": report.get("passed"),
    "internal_total": report.get("total"),
}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
