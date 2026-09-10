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
from conscious_agent.natural_language_action_execution_checkpoint import (
    build_natural_language_action_execution_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    report = build_natural_language_action_execution_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 130)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["natural_language_action_execution_checkpoint_completed"])
    require(report["intent_grounding_proposal_approval_execution_results_consolidated"])
    require(report["streaming_non_streaming_parity_preserved"])
    require(report["ordinary_conversation_execution_blocked"])
    require(report["synthetic_executor_contract_exercised"])
    require(report["real_tool_execution_performed"] is False)
    for key in (
        "proposal_persisted", "automatic_approval_created", "approval_granted_by_conversation",
        "conversation_execution_admitted", "conversation_action_executed", "source_edit_performed",
        "runtime_mutated", "memory_mutated", "provider_contacted", "model_operation_performed",
        "installation_performed", "promotion_performed", "certification_performed",
    ):
        require(report[key] is False)
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)
    summary = report["summary"]
    require(summary["intent_projection_case_count"] == 17)
    require(summary["proposal_handoff_case_count"] == 17)
    require(summary["execution_admission_case_count"] == 5)
    require(summary["synthetic_result_case_count"] == 7)
    require(summary["execution_eligible_capability_count"] == 3)
    require(summary["authoritative_conversation_path_count"] == 2)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)
    evidence = report["evidence"]["synthetic_contracts"]
    require(evidence["projection_summaries"]["question"]["category"] == "question")
    require(not evidence["projection_summaries"]["question"]["action_intent_present"])
    require(evidence["projection_summaries"]["correction"]["category"] == "correction")
    require(evidence["projection_summaries"]["diagnostics"]["capability_id"] == "diagnostics")
    require(evidence["projection_summaries"]["patch"]["capability_id"] == "patch_proposal")
    require(evidence["projection_summaries"]["uncertain"]["requires_clarification"])
    require(evidence["projection_summaries"]["hypothetical"]["hypothetical_language_present"])
    require(evidence["projection_summaries"]["quoted"]["quoted_command_present"])
    require(evidence["projection_summaries"]["resolved_follow_up"]["capability_id"] == "diagnostics")
    require(evidence["projection_summaries"]["resolved_follow_up"]["authorization_state"] == "not_granted")
    require(evidence["projection_summaries"]["authoritative_result"]["authoritative_receipt_present"])
    require(evidence["handoff_summaries"]["diagnostics"]["proposal_state"] == "ready_for_operator_review")
    require(not evidence["handoff_summaries"]["diagnostics"]["persisted"])
    require(not evidence["handoff_summaries"]["diagnostics"]["approval_granted"])
    require(not evidence["handoff_summaries"]["diagnostics"]["executed"])
    require(evidence["execution_summaries"]["admitted"]["admitted"])
    require(not evidence["execution_summaries"]["admitted"]["conversation_can_execute"])
    require(evidence["execution_summaries"]["replay"]["replay_detected"])
    require(not evidence["execution_summaries"]["blocked_patch"]["admitted"])
    require(evidence["result_summaries"]["success"]["state"] == "succeeded")
    require(evidence["result_summaries"]["timeout"]["state"] == "timed_out")
    require(evidence["result_summaries"]["cancelled"]["state"] == "cancelled")
    require(evidence["result_summaries"]["exception"]["error_kind"] == "executor_exception")
    require(not runtime.exists())
    dispatched = dispatch_registered_checkpoint(
        "natural-language-action-execution-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched["read_only"])
    require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
    require(dispatched["checkpoint_summary"]["ok"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (item for item in registry["checkpoints"] if item["checkpoint_id"] == "natural-language-action-execution-checkpoint"),
    None,
)
require(row is not None and row["builder"] == "build_natural_language_action_execution_checkpoint")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "natural-language-action-execution-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1175.9")

from conscious_agent.api_server import dispatch_api
status, payload = dispatch_api("GET", "/api/cognition/natural-language-action-execution-checkpoint")
require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1175.9")
post_status, _ = dispatch_api(
    "POST", "/api/cognition/natural-language-action-execution-checkpoint", body={"confirm": True},
)
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("natural-language-action-execution-checkpoint-panel" in dashboard)
require("/api/cognition/natural-language-action-execution-checkpoint" in dashboard)
require("refreshNaturalLanguageActionExecutionCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1175.9"' in metadata or 'WORKING_SOURCE_VERSION = "1176.2"' in metadata or 'WORKING_SOURCE_VERSION = "1176.5"' in metadata or 'WORKING_SOURCE_VERSION = "1176.8"' in metadata or 'WORKING_SOURCE_VERSION = "1176.9"' in metadata or 'WORKING_SOURCE_VERSION = "1177.2"' in metadata or 'WORKING_SOURCE_VERSION = "1177.5"' in metadata or 'WORKING_SOURCE_VERSION = "1177.8"' in metadata or 'WORKING_SOURCE_VERSION = "1177.9"' in metadata or 'WORKING_SOURCE_VERSION = "1178.2"' in metadata or 'WORKING_SOURCE_VERSION = "1178.5"' in metadata or 'WORKING_SOURCE_VERSION = "1178.8"' in metadata or 'WORKING_SOURCE_VERSION = "1178.9"' in metadata or 'WORKING_SOURCE_VERSION = "1179.2"' in metadata or 'WORKING_SOURCE_VERSION = "1179.5"' in metadata or 'WORKING_SOURCE_VERSION = "1179.8"' in metadata or 'WORKING_SOURCE_VERSION = "1179.9"' in metadata or 'WORKING_SOURCE_VERSION = "1180.2"' in metadata or 'WORKING_SOURCE_VERSION = "1180.5"' in metadata or 'WORKING_SOURCE_VERSION = "1180.8"' in metadata or 'WORKING_SOURCE_VERSION = "1180.9"' in metadata or 'WORKING_SOURCE_VERSION = "1181.5"' in metadata or 'WORKING_SOURCE_VERSION = "1181.8"' in metadata or 'WORKING_SOURCE_VERSION = "1181.9"' in metadata or 'WORKING_SOURCE_VERSION = "1182.2"' in metadata or 'WORKING_SOURCE_VERSION = "1182.5"' in metadata or 'WORKING_SOURCE_VERSION = "1182.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1175.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1175.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1176.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1176.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1176.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1176.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1177.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1177.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1177.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1177.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1178.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1178.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1178.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1178.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1179.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1179.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1179.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1179.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1180.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1180.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1180.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1181.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1181.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1181.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1181.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1182.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1182.8"' in metadata)
require("v1176.0-v1176.2" in metadata or "v1176.3-v1176.5" in metadata or "v1176.6-v1176.8" in metadata or "v1176.9" in metadata or "v1177.3-v1177.5" in metadata or "v1177.6-v1177.8" in metadata or "v1177.9" in metadata or "v1178.2" in metadata or "v1178.5" in metadata or "v1178.8" in metadata or "v1178.9" in metadata or "v1179.2" in metadata or "v1179.8" in metadata or "v1179.9" in metadata or "v1180.2" in metadata or "v1180.5" in metadata or "v1180.8" in metadata or "v1180.9" in metadata or "v1181.5" in metadata or "v1181.8" in metadata or "v1181.9" in metadata or "v1182.2" in metadata or "v1182.5" in metadata or "v1182.9" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
require(("v1175.9" in next_steps or "v1176.5" in next_steps or "v1176.8" in next_steps or ("v1176.9" in next_steps or "v1177.2" in next_steps or "v1177.5" in next_steps or "v1177.8" in next_steps or "v1177.9" in next_steps or "v1178.2" in next_steps or "v1178.5" in next_steps or "v1178.8" in next_steps or "v1178.9" in next_steps or "v1179.2" in next_steps or "v1179.5" in next_steps or "v1179.8" in next_steps or "v1179.9" in next_steps or "v1180.2" in next_steps or "v1180.5" in next_steps or "v1180.8" in next_steps or "v1180.9" in next_steps or "v1181.5" in next_steps or "v1181.8" in next_steps or "v1181.9" in next_steps or "v1182.2" in next_steps or "v1182.5" in next_steps)) and ("v1176.0-v1176.2" in next_steps or "v1176.6-v1176.8" in next_steps or ("v1176.9" in next_steps or "v1177.2" in next_steps) or "v1177.0-v1177.2" in next_steps or "v1177.3-v1177.5" in next_steps or "v1178.3-v1178.5" in next_steps) and "v1200" in next_steps)
require("v1175.9 Natural-Language Action" in history and "Desktop" in history)
require(("Current source: v1175.9" in roadmap or "Current source: v1176.2" in roadmap or "Current source: v1176.5" in roadmap or "Current source: v1176.8" in roadmap or ("Current source: v1176.9" in roadmap or "Current source: v1177.2" in roadmap or "Current source: v1177.5" in roadmap or "Current source: v1177.8" in roadmap or "Current source: v1177.9" in roadmap or "Current source: v1178.2" in roadmap or "Current source: v1178.5" in roadmap or "Current source: v1178.8" in roadmap or "Current source: v1178.9" in roadmap or "Current source: v1179.2" in roadmap or "Current source: v1179.5" in roadmap or "Current source: v1179.8" in roadmap or "Current source: v1179.9" in roadmap or "Current source: v1180.2" in roadmap or "Current source: v1180.5" in roadmap or "Current source: v1180.8" in roadmap or "Current source: v1180.9" in roadmap or "Current source: v1181.5" in roadmap or "Current source: v1181.8" in roadmap or "Current source: v1181.9" in roadmap or "Current source: v1182.2" in roadmap or "Current source: v1182.5" in roadmap)) and "v1200" in roadmap)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1175.9-natural-language-action-execution-read-only-checkpoint",
    "passed": sum(checks),
    "total": len(checks),
    "read_only": True,
    "real_tool_execution_performed": False,
    "conversation_execution": False,
    "automatic_approval": False,
}, sort_keys=True))
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
