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
from conscious_agent.clarification_argument_routing_checkpoint import (
    build_clarification_argument_routing_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    report = build_clarification_argument_routing_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 100)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["clarification_argument_routing_checkpoint_completed"])
    require(report["argument_binding_structured_clarification_continuity_consolidated"])
    require(report["streaming_non_streaming_parity_preserved"])
    require(report["ordinary_conversation_clarification_blocked"])
    require(report["synthetic_continuity_contract_exercised"])
    for key in (
        "raw_request_persisted", "raw_answer_persisted", "argument_values_persisted",
        "proposal_persisted", "automatic_approval_created", "approval_granted_by_conversation",
        "conversation_execution_admitted", "conversation_action_executed", "source_edit_performed",
        "runtime_mutated", "memory_mutated", "provider_contacted", "model_operation_performed",
        "installation_performed", "promotion_performed", "certification_performed",
    ):
        require(report[key] is False)
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)
    summary = report["summary"]
    require(summary["projection_case_count"] >= 15)
    require(summary["argument_schema_count"] == 12)
    require(summary["clarification_answer_case_count"] == 5)
    require(summary["proposal_binding_case_count"] == 4)
    require(summary["continuity_case_count"] >= 9)
    require(summary["maximum_pending_continuity_records"] == 32)
    require(summary["maximum_continuity_age_seconds"] == 86400)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "clarification-argument-routing-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched["read_only"])
    require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
    require(dispatched["checkpoint_summary"]["ok"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (item for item in registry["checkpoints"] if item["checkpoint_id"] == "clarification-argument-routing-checkpoint"),
    None,
)
require(row is not None and row["builder"] == "build_clarification_argument_routing_checkpoint")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "clarification-argument-routing-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1176.9")

from conscious_agent.api_server import dispatch_api
status, payload = dispatch_api("GET", "/api/cognition/clarification-argument-routing-checkpoint")
require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1176.9")
post_status, _ = dispatch_api(
    "POST", "/api/cognition/clarification-argument-routing-checkpoint", body={"confirm": True},
)
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("clarification-argument-routing-checkpoint-panel" in dashboard)
require("/api/cognition/clarification-argument-routing-checkpoint" in dashboard)
require("refreshClarificationArgumentRoutingCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require(any(f'WORKING_SOURCE_VERSION = \"{v}\"' in metadata for v in ('1176.9','1177.2','1177.5','1177.8','1177.9','1178.2','1178.5','1178.8','1178.9','1179.2','1179.5','1179.8','1179.9','1180.2','1180.5','1180.8','1180.9','1181.5','1181.8','1181.9','1182.2','1182.5','1182.9')))
require(any(f'PREVIOUS_WORKING_SOURCE_VERSION = \"{v}\"' in metadata for v in ('1176.8','1176.9','1177.2','1177.5','1177.8','1177.9','1178.2','1178.5','1178.8','1178.9','1179.2','1179.5','1179.8','1179.9','1180.2','1180.5','1180.8','1181.2','1181.5','1181.8','1181.9','1182.2','1182.8')))
require("v1177.0-v1177.2" in metadata or "v1177.3-v1177.5" in metadata or "v1177.6-v1177.8" in metadata or "v1177.9" in metadata or "v1178.2" in metadata or "v1178.5" in metadata or "v1178.8" in metadata or "v1178.9" in metadata or "v1179.2" in metadata or "v1179.8" in metadata or "v1179.9" in metadata or "v1180.2" in metadata or "v1180.5" in metadata or "v1180.8" in metadata or "v1180.9" in metadata or "v1181.5" in metadata or "v1181.8" in metadata or "v1181.9" in metadata or "v1182.2" in metadata or "v1182.5" in metadata or "v1182.9" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
require(("v1176.9" in next_steps or "v1177.2" in next_steps or "v1177.5" in next_steps or "v1177.8" in next_steps or "v1177.9" in next_steps or "v1178.2" in next_steps or "v1178.5" in next_steps or "v1178.8" in next_steps or "v1178.9" in next_steps or "v1179.2" in next_steps or "v1179.5" in next_steps or "v1179.8" in next_steps or "v1179.9" in next_steps or "v1180.2" in next_steps or "v1180.5" in next_steps or "v1180.8" in next_steps or "v1180.9" in next_steps or "v1181.5" in next_steps or "v1181.8" in next_steps or "v1181.9" in next_steps or "v1182.2" in next_steps or "v1182.5" in next_steps) and ("v1177.0-v1177.2" in next_steps or "v1177.3-v1177.5" in next_steps or "v1178.3-v1178.5" in next_steps) and "v1200" in next_steps)
require("v1176.9 Clarification and Argument Routing" in history and "Desktop" in history)
require(("Current source: v1176.9" in roadmap or "Current source: v1177.2" in roadmap or "Current source: v1177.5" in roadmap or "Current source: v1177.8" in roadmap or "Current source: v1177.9" in roadmap or "Current source: v1178.2" in roadmap or "Current source: v1178.5" in roadmap or "Current source: v1178.8" in roadmap or "Current source: v1178.9" in roadmap or "Current source: v1179.2" in roadmap or "Current source: v1179.5" in roadmap or "Current source: v1179.8" in roadmap or "Current source: v1179.9" in roadmap or "Current source: v1180.2" in roadmap or "Current source: v1180.5" in roadmap or "Current source: v1180.8" in roadmap or "Current source: v1180.9" in roadmap or "Current source: v1181.5" in roadmap or "Current source: v1181.8" in roadmap or "Current source: v1181.9" in roadmap or "Current source: v1182.2" in roadmap or "Current source: v1182.5" in roadmap) and "v1177.0-v1177.2" in roadmap and "v1200" in roadmap)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1176.9-clarification-argument-routing-read-only-checkpoint",
    "passed": sum(checks),
    "total": len(checks),
    "read_only": True,
    "raw_answer_persisted": False,
    "proposal_persisted": False,
    "automatic_approval": False,
    "conversation_execution": False,
}, sort_keys=True))
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
