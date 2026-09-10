#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_TEST_RUNTIME_ROOT = Path(tempfile.mkdtemp(prefix="eidolon-v1186-9-external-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(_TEST_RUNTIME_ROOT)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.durable_campaign_continuation_checkpoint import build_durable_campaign_continuation_checkpoint

checks: list[bool] = []
def require(value: object) -> None:
    checks.append(bool(value))

with tempfile.TemporaryDirectory(prefix="eidolon-v1186-9-tests-") as directory:
    runtime = Path(directory) / "runtime"
    report = build_durable_campaign_continuation_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report.get("ok") is True)
    require(report.get("passed") == report.get("total"))
    require(int(report.get("total") or 0) >= 200)
    require(report.get("contract_version") == "v1186.9")
    require(report.get("checkpoint_id") == "durable-campaign-continuation:v1186.9")
    require(report.get("read_only") is True)
    require(report.get("post_available") is False)
    require(report.get("content_free") is True)
    require(report.get("authority_preserved") is True)
    require(report.get("operator_review_required") is True)
    require(report.get("operator_promotion_required") is True)
    require(report.get("desktop_verification_deferred_until_v1200") is True)
    for key in (
        "durable_campaign_continuation_checkpoint_completed",
        "retained_storage_checkpoint_completed",
        "retained_resume_reconciliation_checkpoint_completed",
        "retained_resume_materialization_checkpoint_completed",
        "atomic_storage_generation_chaining_exercised",
        "restoration_review_decisions_exercised",
        "source_drift_reconciliation_exercised",
        "resume_eligibility_decisions_exercised",
        "exclusive_lease_conflict_exercised",
        "stale_lease_takeover_exercised",
        "resumed_session_materialization_exercised",
        "restart_reconciliation_exercised",
        "operator_reviewed_lease_release_exercised",
        "tamper_lineage_privacy_boundaries_exercised",
        "source_runtime_immutability_exercised",
    ):
        require(report.get(key) is True)
    for key in (
        "production_source_read", "production_source_modified", "source_modified", "sandbox_modified",
        "runtime_mutated", "campaign_work_selected_automatically", "campaign_work_executed", "work_executed",
        "automatic_resume_performed", "automatic_execution_performed", "provider_reconnected",
        "provider_contacted", "model_operation_performed", "model_contacted", "raw_source_exposed",
        "raw_patch_exposed", "raw_test_output_exposed", "private_evidence_exposed",
        "private_reasoning_exposed", "shell_invoked", "registered_tool_invoked",
        "production_runtime_mutated", "memory_mutated", "automatic_approval_created",
        "automatic_authorization_granted", "implementation_authorized", "source_application_authorized",
        "installation_performed", "promotion_performed", "certification_performed", "release_authorized",
        "autonomous_action_authorized",
    ):
        require(report.get(key) is False)
    require(report.get("forbidden_report_value_count") == 0)
    require(len(str(report.get("structural_digest") or "")) == 64)
    require(report.get("source_tree_digest_before") == report.get("source_tree_digest_after"))
    require(report.get("runtime_tree_digest_before") == report.get("runtime_tree_digest_after"))
    require(report.get("source_file_count_before") == report.get("source_file_count_after"))
    require(report.get("runtime_file_count_before") == report.get("runtime_file_count_after"))
    require(not runtime.exists())
    summary = report.get("summary") or {}
    require(summary.get("retained_checkpoint_count") == 3)
    require(summary.get("storage_generation_case_count") == 2)
    require(summary.get("restoration_decision_case_count") == 3)
    require(summary.get("eligibility_decision_case_count") == 3)
    require(summary.get("source_drift_case_count") == 2)
    require(summary.get("lease_conflict_case_count") == 1)
    require(summary.get("stale_takeover_case_count") == 2)
    require(summary.get("restart_reconciliation_case_count") == 1)
    require(summary.get("lease_release_case_count") == 1)
    require(int(summary.get("negative_boundary_case_count") or 0) >= 16)
    require(summary.get("public_summary_case_count") == 3)
    require(summary.get("privacy_forbidden_entry_count") == 0)
    require(summary.get("privacy_content_finding_count") == 0)
    require(summary.get("open_limitation_count") == 7)
    require(len(report.get("limitations") or []) == 7)

    dispatched = dispatch_registered_checkpoint(
        "durable-campaign-continuation-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched.get("read_only") is True)
    require(dispatched.get("source_modified") is False)
    require(dispatched.get("runtime_mutated") is False)
    checkpoint_summary = dispatched.get("checkpoint_summary") or {}
    require(checkpoint_summary.get("ok") is True)
    require(checkpoint_summary.get("registered_contract_version") == "v1186.9")
    require(checkpoint_summary.get("reported_contract_version") == "v1186.9")
    require(checkpoint_summary.get("post_available") is False)
    require(checkpoint_summary.get("invocation_completed") is True)

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "durable-campaign-continuation-checkpoint"), None)
require(row is not None)
require((row or {}).get("builder") == "build_durable_campaign_continuation_checkpoint")
require((row or {}).get("contract_version") == "v1186.9")
require((row or {}).get("read_only") is True)
require((row or {}).get("post_available") is False)
require(not registry.get("duplicate_checkpoint_ids"))
require(not registry.get("duplicate_builder_targets"))

with tempfile.TemporaryDirectory(prefix="eidolon-v1186-9-cli-") as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "durable-campaign-continuation-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=900, check=False,
    )
    require(cli.returncode == 0)
    if cli.returncode == 0:
        cli_payload = json.loads(cli.stdout)
        require(cli_payload.get("contract_version") == "v1186.9")
        require(cli_payload.get("ok") is True)
        require(cli_payload.get("read_only") is True)
        require(cli_payload.get("post_available") is False)

status, payload = dispatch_api("GET", "/api/cognition/durable-campaign-continuation-checkpoint")
require(status == 200)
require((payload.get("data") or {}).get("contract_version") == "v1186.9")
require((payload.get("data") or {}).get("ok") is True)
post_status, _ = dispatch_api("POST", "/api/cognition/durable-campaign-continuation-checkpoint", body={"confirm": True})
require(post_status in (404, 405))

source_dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
for token in (
    "durable-campaign-continuation-checkpoint-panel",
    "/api/cognition/durable-campaign-continuation-checkpoint",
    "refreshDurableCampaignContinuationCheckpoint",
    "refreshDurableCampaignContinuationCheckpoint();",
    "v1187.0-v1187.2",
):
    require(token in source_dashboard)
require(re.search(r"async function refreshDurableCampaignContinuationCheckpoint\(\)\{\{.*?/api/cognition/durable-campaign-continuation-checkpoint.*?\n\}\}", source_dashboard, re.S) is not None)
html = render_first_use_shell()
require("durable-campaign-continuation-checkpoint-panel" in html)
require("/api/cognition/durable-campaign-continuation-checkpoint" in html)
script_match = re.search(r"<script>(.*?)</script>", html, re.S)
require(script_match is not None)
if script_match is not None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1186-9-js-") as directory:
        js = Path(directory) / "dashboard.js"
        js.write_text(script_match.group(1), encoding="utf-8")
        node = subprocess.run(["node", "--check", str(js)], text=True, capture_output=True, timeout=60, check=False)
        require(node.returncode == 0)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1186.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1186.8"' in metadata)
require("v1186.9 Durable Campaign Continuation Checkpoint" in metadata)
require("v1187.0-v1187.2" in metadata)
for name in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md"):
    text = (ROOT / name).read_text(encoding="utf-8")
    require("v1186.9 Durable Campaign Continuation Checkpoint" in text)
    require("Current source: v1186.9" in text)
    require("v1187.0-v1187.2" in text)
    require("v1200" in text)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1186.9-durable-campaign-continuation-read-only-checkpoint") == 1)
require(release_verify.count("tools/v1186_9_durable_campaign_continuation_checkpoint_tests.py") == 1)

print(json.dumps({"suite":"v1186.9-durable-campaign-continuation-checkpoint","passed":sum(checks),"total":len(checks),"ok":all(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
