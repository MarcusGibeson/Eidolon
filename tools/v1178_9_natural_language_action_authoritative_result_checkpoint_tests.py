from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.natural_language_action_authoritative_result_checkpoint import (
    build_natural_language_action_authoritative_result_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    report = build_natural_language_action_authoritative_result_checkpoint(
        source_root=ROOT, runtime_root=runtime,
    )
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 120)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["natural_language_action_authoritative_result_checkpoint_completed"])
    require(report["intent_through_authoritative_result_consolidated"])
    require(report["synthetic_terminal_lifecycle_exercised"])
    require(report["stale_attempt_recovery_exercised_without_reexecution"])
    require(report["conversation_result_presentation_parity_preserved"])
    for key in (
        "raw_request_persisted", "raw_argument_values_persisted",
        "raw_operation_identity_persisted", "raw_output_persisted",
        "automatic_proposal_persistence", "automatic_approval_requested",
        "automatic_approval_created", "automatic_authorization_granted",
        "conversation_execution_admitted", "conversation_action_executed",
        "registered_tool_invoked", "provider_contacted", "model_operation_performed",
        "source_edit_performed", "production_runtime_mutated", "memory_mutated",
        "installation_performed", "promotion_performed", "certification_performed",
        "source_modified", "runtime_mutated",
    ):
        require(report[key] is False)
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)
    summary = report["summary"]
    require(summary["retained_checkpoint_count"] == 1)
    require(summary["terminal_result_case_count"] >= 7)
    require(summary["negative_boundary_case_count"] >= 11)
    require(summary["presentation_case_count"] >= 5)
    require(summary["recovery_case_count"] >= 6)
    require(summary["conversation_execution_call_count"] == 0)
    require(summary["maximum_terminal_result_bytes"] <= 4096)
    require(summary["maximum_presentation_bytes"] <= 4096)
    require(summary["maximum_recovery_receipt_bytes"] <= 4096)
    require(summary["default_stale_after_seconds"] == 300.0)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "natural-language-action-authoritative-result-checkpoint",
        source_root=ROOT,
        runtime_root=runtime,
    )
    require(dispatched["read_only"])
    require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
    require(dispatched["checkpoint_summary"]["ok"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (
        item for item in registry["checkpoints"]
        if item["checkpoint_id"] == "natural-language-action-authoritative-result-checkpoint"
    ),
    None,
)
require(row is not None)
require(row["builder"] == "build_natural_language_action_authoritative_result_checkpoint")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "natural-language-action-authoritative-result-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=600,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1178.9")

from conscious_agent.api_server import dispatch_api
status, payload = dispatch_api(
    "GET", "/api/cognition/natural-language-action-authoritative-result-checkpoint",
)
require(status == 200)
require((payload.get("data") or {}).get("contract_version") == "v1178.9")
post_status, _ = dispatch_api(
    "POST",
    "/api/cognition/natural-language-action-authoritative-result-checkpoint",
    body={"confirm": True},
)
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("natural-language-action-authoritative-result-checkpoint-panel" in dashboard)
require("/api/cognition/natural-language-action-authoritative-result-checkpoint" in dashboard)
require("refreshNaturalLanguageActionAuthoritativeResultCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working_match = __import__("re").search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(bool(working_match) and tuple(map(int, working_match.groups())) >= (1178, 9))
previous_match = __import__("re").search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(bool(previous_match) and tuple(map(int, previous_match.groups())) >= (1178, 8))
require("v1178.9" in metadata or tuple(map(int, working_match.groups())) > (1178, 9))
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
require(("v1178.9" in next_steps or "v1179.2" in next_steps or "v1179.5" in next_steps or "v1179.8" in next_steps or "v1179.9" in next_steps or "v1180.2" in next_steps or "v1180.5" in next_steps or "v1180.8" in next_steps or "v1180.9" in next_steps or "v1181.8" in next_steps) and ("v1179.0-v1179.2" in next_steps or "v1179.3-v1179.5" in next_steps) and "v1200" in next_steps)
require("v1178.9 Natural-Language Action and Authoritative Result" in history)
require(("Current source: v1178.9" in roadmap or "Current source: v1179.2" in roadmap or "Current source: v1179.5" in roadmap or "Current source: v1179.8" in roadmap or "Current source: v1179.9" in roadmap or "Current source: v1180.2" in roadmap or "Current source: v1180.5" in roadmap or "Current source: v1180.8" in roadmap or "Current source: v1180.9" in roadmap or "Current source: v1181.5" in roadmap or "Current source: v1181.8" in roadmap) and "v1179.0-v1179.2" in roadmap and "v1200" in roadmap)
require("v1178.9 Natural-Language Action and Authoritative Result" in readme or "v1179.2 Action Review and Follow-Through" in readme or "v1179.5 Governed Action Follow-Up Continuity" in readme or "v1179.8 Complete Action Loop Reliability" in readme or "v1179.9 Natural-Language Action" in readme or "v1180.2 Supervised Project Inspection" in readme or "v1180.5 Deficiency Review and Specification" in readme or "v1180.8 Supervised Implementation and Test Planning" in readme or "v1180.9 Supervised Project Inspection and Planning" in readme or "v1181.8 Supervised Patch Review and Sandbox Materialization" in readme)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1178.9-natural-language-action-authoritative-result-read-only-checkpoint") == 1)
require(release_verify.count("tools/v1178_9_natural_language_action_authoritative_result_checkpoint_tests.py") == 1)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1178.9-natural-language-action-authoritative-result-read-only-checkpoint",
    "passed": sum(checks),
    "total": len(checks),
    "read_only": True,
    "conversation_execution": False,
    "registered_tool_invoked": False,
}, sort_keys=True))
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
