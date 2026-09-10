from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_TEST_RUNTIME_ROOT = Path(tempfile.mkdtemp(prefix="eidolon-v1185-9-external-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(_TEST_RUNTIME_ROOT)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.persistent_supervised_developer_alpha_checkpoint import (
    build_persistent_supervised_developer_alpha_checkpoint,
)

checks: list[bool] = []
def require(value: object) -> None: checks.append(bool(value))

with tempfile.TemporaryDirectory(prefix="eidolon-v1185-9-tests-") as directory:
    runtime = Path(directory) / "runtime"
    report = build_persistent_supervised_developer_alpha_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report.get("ok") is True)
    require(report.get("passed") == report.get("total"))
    require(int(report.get("total") or 0) >= 300)
    require(report.get("contract_version") == "v1185.9")
    require(report.get("checkpoint_id") == "persistent-supervised-developer-alpha:v1185.9")
    require(report.get("read_only") is True)
    require(report.get("post_available") is False)
    require(report.get("content_free") is True)
    require(report.get("authority_preserved") is True)
    require(report.get("operator_review_required") is True)
    require(report.get("operator_promotion_required") is True)
    require(report.get("desktop_verification_deferred_until_v1200") is True)
    for key in (
        "persistent_supervised_developer_alpha_checkpoint_completed",
        "retained_campaign_foundations_checkpoint_completed",
        "retained_campaign_continuation_checkpoint_completed",
        "retained_campaign_reliability_checkpoint_completed",
        "campaign_scope_goals_limits_and_approval_exercised",
        "bounded_work_ledger_exercised",
        "multi_session_pause_resume_exercised",
        "bounded_operator_work_selection_exercised",
        "all_resource_budget_classes_exercised",
        "stale_work_and_source_drift_exercised",
        "interruption_outage_restart_recovery_exercised",
        "tamper_lineage_privacy_boundaries_exercised",
        "source_runtime_immutability_exercised",
    ): require(report.get(key) is True)
    for key in (
        "production_source_read", "production_source_modified", "source_modified", "sandbox_modified",
        "runtime_mutated", "campaign_state_persisted", "campaign_work_selected_automatically",
        "campaign_work_executed", "durable_resume_performed", "automatic_reselection_performed",
        "provider_reconnected", "raw_source_exposed", "raw_patch_exposed", "raw_test_output_exposed",
        "private_evidence_exposed", "private_reasoning_exposed", "shell_invoked", "registered_tool_invoked",
        "provider_contacted", "model_operation_performed", "production_runtime_mutated", "memory_mutated",
        "automatic_approval_created", "automatic_authorization_granted", "implementation_authorized",
        "source_application_authorized", "installation_performed", "promotion_performed",
        "certification_performed", "release_authorized", "autonomous_action_authorized",
    ): require(report.get(key) is False)
    require(report.get("forbidden_report_value_count") == 0)
    require(len(str(report.get("structural_digest") or "")) == 64)
    require(report.get("source_tree_digest_before") == report.get("source_tree_digest_after"))
    require(report.get("runtime_tree_digest_before") == report.get("runtime_tree_digest_after"))
    summary = report.get("summary") or {}
    require(summary.get("retained_checkpoint_count") == 3)
    require(summary.get("campaign_decision_case_count") == 3)
    require(summary.get("ledger_state_case_count") == 2)
    require(summary.get("selection_decision_case_count") == 3)
    require(summary.get("valid_transition_case_count") == 7)
    require(summary.get("budget_within_limit_case_count") == 1)
    require(summary.get("budget_exhaustion_case_count") == 5)
    require(summary.get("stale_work_case_count") == 5)
    require(summary.get("recovery_reason_case_count") == 4)
    require(int(summary.get("negative_boundary_case_count") or 0) >= 16)
    require(summary.get("public_summary_case_count") == 6)
    require(summary.get("privacy_forbidden_entry_count") == 0)
    require(summary.get("privacy_content_finding_count") == 0)
    require(summary.get("open_limitation_count") == 7)
    require(len(report.get("limitations") or []) == 7)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "persistent-supervised-developer-alpha-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched.get("read_only") is True)
    require(dispatched.get("source_modified") is False)
    require(dispatched.get("runtime_mutated") is False)
    checkpoint_summary = dispatched.get("checkpoint_summary") or {}
    require(checkpoint_summary.get("ok") is True)
    require(checkpoint_summary.get("registered_contract_version") == "v1185.9")
    require(checkpoint_summary.get("reported_contract_version") == "v1185.9")
    require(checkpoint_summary.get("post_available") is False)

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "persistent-supervised-developer-alpha-checkpoint"), None)
require(row is not None)
require((row or {}).get("builder") == "build_persistent_supervised_developer_alpha_checkpoint")
require((row or {}).get("contract_version") == "v1185.9")
require((row or {}).get("read_only") is True)
require((row or {}).get("post_available") is False)
require(not registry.get("duplicate_checkpoint_ids"))
require(not registry.get("duplicate_builder_targets"))

with tempfile.TemporaryDirectory(prefix="eidolon-v1185-9-cli-") as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "persistent-supervised-developer-alpha-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=900, check=False,
    )
    require(cli.returncode == 0)
    cli_payload = json.loads(cli.stdout)
    require(cli_payload.get("contract_version") == "v1185.9")
    require(cli_payload.get("ok") is True)
    require(cli_payload.get("read_only") is True)
    require(cli_payload.get("post_available") is False)

status, payload = dispatch_api("GET", "/api/cognition/persistent-supervised-developer-alpha-checkpoint")
require(status == 200)
require((payload.get("data") or {}).get("contract_version") == "v1185.9")
require((payload.get("data") or {}).get("ok") is True)
post_status, _ = dispatch_api("POST", "/api/cognition/persistent-supervised-developer-alpha-checkpoint", body={"confirm": True})
require(post_status in (404, 405))

source_dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
for token in (
    "persistent-supervised-developer-alpha-checkpoint-panel",
    "/api/cognition/persistent-supervised-developer-alpha-checkpoint",
    "refreshPersistentSupervisedDeveloperAlphaCheckpoint",
    "refreshPersistentSupervisedDeveloperAlphaCheckpoint();",
    "v1186.0-v1186.2 Durable Campaign Storage",
): require(token in source_dashboard)
require(re.search(r"async function refreshPersistentSupervisedDeveloperAlphaCheckpoint\(\)\{\{.*?/api/cognition/persistent-supervised-developer-alpha-checkpoint.*?\n\}\}", source_dashboard, re.S) is not None)
html = render_first_use_shell()
require("persistent-supervised-developer-alpha-checkpoint-panel" in html)
require("/api/cognition/persistent-supervised-developer-alpha-checkpoint" in html)
script_match = re.search(r"<script>(.*?)</script>", html, re.S)
require(script_match is not None)
if script_match is not None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1185-9-js-") as directory:
        js = Path(directory) / "dashboard.js"
        js.write_text(script_match.group(1), encoding="utf-8")
        node = subprocess.run(["node", "--check", str(js)], text=True, capture_output=True, timeout=60, check=False)
        require(node.returncode == 0)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1185.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1185.8"' in metadata)
require("v1185.9 Persistent Supervised Developer Alpha Checkpoint" in metadata)
require("v1186.0-v1186.2 Durable Campaign Storage" in metadata)
for name in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md"):
    text = (ROOT / name).read_text(encoding="utf-8")
    require("v1185.9 Persistent Supervised Developer Alpha Checkpoint" in text)
    require("Current source: v1185.9" in text)
    require("v1186.0-v1186.2" in text)
    require("v1200" in text)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1185.9-persistent-supervised-developer-alpha-read-only-checkpoint") == 1)
require(release_verify.count("tools/v1185_9_persistent_supervised_developer_alpha_checkpoint_tests.py") == 1)

print(json.dumps({"suite":"v1185.9-persistent-supervised-developer-alpha-checkpoint","passed":sum(checks),"total":len(checks),"ok":all(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
