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
from conscious_agent.natural_language_action_approval_governance_checkpoint import (
    build_natural_language_action_approval_governance_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    report = build_natural_language_action_approval_governance_checkpoint(
        source_root=ROOT, runtime_root=runtime,
    )
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 100)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["natural_language_action_approval_governance_checkpoint_completed"])
    require(report["intent_clarification_proposal_approval_authorization_admission_consolidated"])
    require(report["synthetic_proposal_lifecycle_exercised"])
    require(report["conversation_governance_mutation_blocked"])
    for key in (
        "raw_request_persisted", "raw_argument_values_persisted",
        "raw_operation_identity_persisted", "automatic_proposal_persistence",
        "automatic_approval_requested", "automatic_approval_created",
        "approval_implies_authorization", "conversation_authorization_granted",
        "conversation_execution_admitted", "conversation_action_executed",
        "executor_invoked", "tool_invoked", "provider_contacted",
        "model_operation_performed", "source_edit_performed", "runtime_mutated",
        "memory_mutated", "installation_performed", "promotion_performed",
        "certification_performed", "source_modified",
    ):
        require(report[key] is False)
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)
    summary = report["summary"]
    require(summary["retained_checkpoint_count"] == 2)
    require(summary["lifecycle_case_count"] >= 11)
    require(summary["governed_transition_count"] == 4)
    require(summary["negative_boundary_case_count"] >= 12)
    require(summary["terminal_state_case_count"] >= 4)
    require(summary["conversation_governance_call_count"] == 0)
    require(summary["maximum_proposal_records"] == 64)
    require(summary["maximum_proposal_record_bytes"] == 3072)
    require(summary["maximum_proposal_age_seconds"] == 604800)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "natural-language-action-approval-governance-checkpoint",
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
        if item["checkpoint_id"] == "natural-language-action-approval-governance-checkpoint"
    ),
    None,
)
require(row is not None)
require(row["builder"] == "build_natural_language_action_approval_governance_checkpoint")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "natural-language-action-approval-governance-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=600,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1177.9")

from conscious_agent.api_server import dispatch_api
status, payload = dispatch_api(
    "GET", "/api/cognition/natural-language-action-approval-governance-checkpoint",
)
require(status == 200)
require((payload.get("data") or {}).get("contract_version") == "v1177.9")
post_status, _ = dispatch_api(
    "POST",
    "/api/cognition/natural-language-action-approval-governance-checkpoint",
    body={"confirm": True},
)
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("natural-language-action-approval-governance-checkpoint-panel" in dashboard)
require("/api/cognition/natural-language-action-approval-governance-checkpoint" in dashboard)
require("refreshNaturalLanguageActionApprovalGovernanceCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1177.9"' in metadata or 'WORKING_SOURCE_VERSION = "1178.2"' in metadata or 'WORKING_SOURCE_VERSION = "1178.5"' in metadata or 'WORKING_SOURCE_VERSION = "1178.8"' in metadata or 'WORKING_SOURCE_VERSION = "1178.9"' in metadata or 'WORKING_SOURCE_VERSION = "1179.2"' in metadata or 'WORKING_SOURCE_VERSION = "1179.5"' in metadata or 'WORKING_SOURCE_VERSION = "1179.8"' in metadata or 'WORKING_SOURCE_VERSION = "1179.9"' in metadata or 'WORKING_SOURCE_VERSION = "1180.2"' in metadata or 'WORKING_SOURCE_VERSION = "1180.5"' in metadata or 'WORKING_SOURCE_VERSION = "1180.8"' in metadata or 'WORKING_SOURCE_VERSION = "1180.9"' in metadata or 'WORKING_SOURCE_VERSION = "1181.5"' in metadata or 'WORKING_SOURCE_VERSION = "1181.8"' in metadata or 'WORKING_SOURCE_VERSION = "1181.9"' in metadata or 'WORKING_SOURCE_VERSION = "1182.2"' in metadata or 'WORKING_SOURCE_VERSION = "1182.5"' in metadata or 'WORKING_SOURCE_VERSION = "1182.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1177.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1177.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1178.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1178.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1178.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1178.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1179.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1179.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1179.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1179.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1180.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1180.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1180.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1181.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1181.5"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1181.8"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1181.9"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1182.2"' in metadata or 'PREVIOUS_WORKING_SOURCE_VERSION = "1182.8"' in metadata)
require("v1177.9 Natural-Language Action and Approval Governance Read-Only Checkpoint" in metadata or "v1178.2 Authoritative Supervised Execution Result Foundations" in metadata or "v1178.5 Supervised Result Presentation and Conversation Integration" in metadata or "v1178.8 Supervised Result Reliability and Recovery" in metadata or "v1178.9 Natural-Language Action and Authoritative Result Read-Only Checkpoint" in metadata or "v1179.2 Action Review and Follow-Through Foundations" in metadata or "v1179.5 Governed Action Follow-Up Continuity" in metadata or "v1179.8 Complete Action Loop Reliability" in metadata or "v1179.9 Natural-Language Action Read-Only Checkpoint" in metadata or "v1180.2 Supervised Project Inspection Foundations" in metadata or "v1180.5 Deficiency Review and Specification Foundations" in metadata or "v1180.8 Supervised Implementation and Test Planning Foundations" in metadata or "v1180.9 Supervised Project Inspection and Planning Read-Only Checkpoint" in metadata or "v1181.5 Supervised Patch Draft Foundations" in metadata or "v1181.8 Supervised Patch Review and Sandbox Materialization Foundations" in metadata or "v1181.9 Supervised Implementation Read-Only Checkpoint" in metadata or "v1182.2 Supervised Sandbox Test Execution Foundations" in metadata or "v1182.5 Sandbox Test Evidence and Diagnosis Foundations" in metadata or "v1182.9 Supervised Sandbox Testing and Repair Checkpoint" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
require(("v1177.9" in next_steps or "v1178.2" in next_steps or "v1178.5" in next_steps or "v1178.8" in next_steps or "v1178.9" in next_steps or "v1179.2" in next_steps or "v1179.5" in next_steps or "v1179.8" in next_steps or "v1179.9" in next_steps or "v1180.2" in next_steps or "v1180.5" in next_steps or "v1180.8" in next_steps or "v1180.9" in next_steps or "v1181.8" in next_steps or "v1181.9" in next_steps or "v1182.2" in next_steps or "v1182.5" in next_steps) and ("v1178.0-v1178.2" in next_steps or "v1178.3-v1178.5" in next_steps) and "v1200" in next_steps)
require("v1177.9 Natural-Language Action and Approval Governance" in history)
require(("Current source: v1177.9" in roadmap or "Current source: v1178.2" in roadmap or "Current source: v1178.5" in roadmap or "Current source: v1178.8" in roadmap or "Current source: v1178.9" in roadmap or "Current source: v1179.2" in roadmap or "Current source: v1179.5" in roadmap or "Current source: v1179.8" in roadmap or "Current source: v1179.9" in roadmap or "Current source: v1180.2" in roadmap or "Current source: v1180.5" in roadmap or "Current source: v1180.8" in roadmap or "Current source: v1180.9" in roadmap or "Current source: v1181.5" in roadmap or "Current source: v1181.8" in roadmap or "Current source: v1181.9" in roadmap or "Current source: v1182.2" in roadmap or "Current source: v1182.5" in roadmap) and "v1178.0-v1178.2" in roadmap and "v1200" in roadmap)
require("v1177.9 Natural-Language Action and Approval Governance" in readme or "v1178.2 Authoritative Supervised Execution Result Foundations" in readme or "v1178.5 Supervised Result Presentation and Conversation Integration" in readme or "v1178.8 Supervised Result Reliability and Recovery" in readme or "v1178.9 Natural-Language Action and Authoritative Result" in readme or "v1179.2 Action Review and Follow-Through" in readme or "v1179.5 Governed Action Follow-Up Continuity" in readme or "v1179.8 Complete Action Loop Reliability" in readme or "v1179.9 Natural-Language Action" in readme or "v1180.2 Supervised Project Inspection" in readme or "v1180.5 Deficiency Review and Specification" in readme or "v1180.8 Supervised Implementation and Test Planning" in readme or "v1180.9 Supervised Project Inspection and Planning" in readme or "v1181.8 Supervised Patch Review and Sandbox Materialization" in readme or "v1181.9 Supervised Implementation" in readme or "v1182.2 Supervised Sandbox Test Execution" in readme or "v1182.5 Sandbox Test Evidence and Diagnosis" in readme)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1177.9-natural-language-action-approval-governance-read-only-checkpoint") == 1)
require(release_verify.count("tools/v1177_9_natural_language_action_approval_governance_checkpoint_tests.py") == 1)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1177.9-natural-language-action-approval-governance-read-only-checkpoint",
    "passed": sum(checks),
    "total": len(checks),
    "read_only": True,
    "automatic_approval": False,
    "conversation_authorization": False,
    "execution_performed": False,
}, sort_keys=True))
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
