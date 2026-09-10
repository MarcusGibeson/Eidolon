from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1191-9-data-"))

from conscious_agent.action_proposal_handoff import build_action_proposal_handoff
from conscious_agent.api_server import dispatch_api
from conscious_agent.chat_action_router import SUPERVISED_CAPABILITY_REGISTRY
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.developer_campaign_conversation_projection import (
    build_developer_campaign_conversation_projection,
    developer_campaign_conversation_public,
)
from conscious_agent.natural_language_action_routing import build_natural_language_action_projection
from conscious_agent.responsiveness_background_work_checkpoint import (
    CONTRACT_VERSION,
    build_responsiveness_background_work_checkpoint,
)
from conscious_agent.supervised_action_execution import EXECUTION_ELIGIBLE_CAPABILITIES
from conscious_agent.supervised_sandbox_repair_draft_checkpoint import _lineage
from conscious_agent.supervised_sandbox_repair_draft_foundations import draft_supervised_sandbox_repair
from conscious_agent.supervised_sandbox_repair_review_materialization import (
    materialize_reviewed_sandbox_repair,
    review_repair_draft,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


with tempfile.TemporaryDirectory(prefix="eidolon-v1191-9-suite-") as temp:
    report = build_responsiveness_background_work_checkpoint(
        source_root=ROOT, runtime_root=Path(temp) / "runtime",
    )
    for key, value in (
        ("ok", True),
        ("contract_version", "v1191.9"),
        ("checkpoint_id", "responsiveness-background-work:v1191.9"),
        ("read_only", True),
        ("post_available", False),
        ("content_free", True),
        ("source_unchanged", True),
        ("runtime_mutated", False),
        ("production_source_modified", False),
        ("provider_contacted", False),
        ("model_contacted", False),
        ("thread_started", False),
        ("process_started", False),
        ("execution_invoked", False),
        ("queued_work_executed", False),
        ("real_work_cancelled", False),
        ("approval_created", False),
        ("approval_consumed", False),
        ("automatic_continuation", False),
        ("authority_granted", False),
        ("authority_preserved", True),
        ("desktop_verification_deferred_until_v1200", True),
    ):
        require(report.get(key) == value)
    require(report.get("passed") == report.get("total"))
    require(report.get("total", 0) >= 110)
    require(len(str(report.get("structural_digest") or "")) == 64)
    require(len(report.get("limitations") or []) == 5)
    summary = report.get("summary") or {}
    require(summary.get("retained_checkpoint_count") == 3)
    require(summary.get("software_development_routing_case_count") == 3)
    require(summary.get("campaign_conversation_case_count") == 3)
    require(summary.get("campaign_stage_count") == 9)
    require(summary.get("campaign_lineage_surface_count") == 8)
    require(summary.get("windows_newline_materialization_ready") is True)
    require(summary.get("raw_crlf_rollback_preserved") is True)
    require(summary.get("utf8_windows_suite_fix_count") == 2)
    require(summary.get("foreground_conversation_preserved") is True)

for text in (
    "Make me a web page for my dog.",
    "Build me a web page for my dog.",
    "Create a web app for this project.",
):
    projection = build_natural_language_action_projection(text)
    require(projection["intent"]["category"] == "action_request")
    require(projection["grounding"]["grounding_status"] == "matched")
    require(projection["grounding"]["capability_id"] == "software_development")
    require(projection["grounding"]["capability_registered"] is True)
    require(projection["grounding"]["risk_level"] == "medium")
    require(projection["grounding"]["authority_required"] is True)
    handoff = build_action_proposal_handoff(projection, operation_id="v1191-9-routing-test")
    require(handoff["proposal"]["proposal_state"] == "ready_for_operator_review")
    require(handoff["proposal"]["persisted"] is False)
    require(handoff["approval_handoff"]["approval_created"] is False)
    require(handoff["execution_admission"]["admitted"] is False)
    campaign = build_developer_campaign_conversation_projection(
        projection, handoff, project_state={"active": True},
    )
    public = developer_campaign_conversation_public(campaign)
    require(public["status"] == "supervised_campaign_proposal_visible")
    require(public["campaign_connected_to_conversation"] is True)
    require(public["proposal_ready_for_operator_review"] is True)
    require(public["stage_count"] == 9)
    require(public["lineage_surface_count"] == 8)
    require(public["foreground_conversation_preserved"] is True)
    require(public["proposal_persisted"] is False)
    require(public["execution_invoked"] is False)
    require(public["campaign_started"] is False)
    require(public["content_free"] is True)
    require(public["private_campaign_content_included"] is False)
    require(public["authority_granted"] is False)

capability = next(
    (row for row in SUPERVISED_CAPABILITY_REGISTRY if row.get("id") == "software_development"),
    None,
)
require(capability is not None)
require((capability or {}).get("mode") == "direct_function")
require((capability or {}).get("boundary") == "proposal only")
require("software_development" not in EXECUTION_ELIGIBLE_CAPABILITIES)

ordinary = build_natural_language_action_projection("How do web pages work?")
ordinary_handoff = build_action_proposal_handoff(ordinary, operation_id="ordinary")
ordinary_campaign = build_developer_campaign_conversation_projection(ordinary, ordinary_handoff)
require(ordinary["intent"]["category"] == "question")
require(ordinary_campaign["status"] == "inactive")
require(ordinary_campaign["campaign_connected_to_conversation"] is False)

before_lf = "def broken():\n    return False\n"
before_crlf = before_lf.replace("\n", "\r\n").encode("utf-8")
after_lf = "def repaired():\n    return True\n"
lineage = _lineage("pkg/windows_test.py", before_lf, status="failed", error_class="python_compile_failed")
draft = draft_supervised_sandbox_repair(*lineage, before_lf, after_lf)
review = review_repair_draft(draft, decision="approve", operator_actor="windows-test")
with tempfile.TemporaryDirectory(prefix="eidolon-v1191-9-crlf-") as temp:
    root = Path(temp)
    source = root / "source"
    sandbox = root / "sandbox"
    source.mkdir()
    target = sandbox / "pkg" / "windows_test.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(before_crlf)
    result = materialize_reviewed_sandbox_repair(
        draft, review, sandbox_root=sandbox, source_root=source,
        current_target_text=before_lf, replacement_text=after_lf,
    )
    require(result["materialization_status"] == "materialized")
    require(result["newline_normalization_applied"] is True)
    require(result["baseline_target_digest"] == hashlib.sha256(before_lf.encode("utf-8")).hexdigest())
    require(result["physical_baseline_target_digest"] == hashlib.sha256(before_crlf).hexdigest())
    require(result["rollback_artifact_digest"] == hashlib.sha256(before_crlf).hexdigest())
    require(result["rollback_artifact_digest_verified"] is True)
    rollback = sandbox / ".eidolon_repair_rollback" / f"{draft['draft_digest']}.rollback"
    require(rollback.read_bytes() == before_crlf)
    require(target.read_bytes() == after_lf.encode("utf-8"))
    replay = materialize_reviewed_sandbox_repair(
        draft, review, sandbox_root=sandbox, source_root=source,
        current_target_text=before_lf, replacement_text=after_lf,
    )
    require(replay["materialization_status"] == "already_materialized")
    require(replay["sandbox_file_written"] is False)
    require(not any(source.rglob("*")))

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "responsiveness-background-work-checkpoint"),
    None,
)
require(row is not None)
require((row or {}).get("contract_version") == CONTRACT_VERSION)
require((row or {}).get("builder") == "build_responsiveness_background_work_checkpoint")
require(not registry.get("duplicate_checkpoint_ids"))
require(not registry.get("duplicate_builder_targets"))

proc = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "responsiveness-background-work-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1191-9-cli-"),
    },
)
require(proc.returncode == 0)
try:
    cli = json.loads(proc.stdout.strip().splitlines()[-1])
    require(cli.get("ok") is True)
    require(cli.get("contract_version") == "v1191.9")
except Exception:
    require(False)
    require(False)

status, payload = dispatch_api("GET", "/api/cognition/responsiveness-background-work-checkpoint")
require(status == 200)
require(payload.get("ok") is True)
require((payload.get("data") or {}).get("contract_version") == "v1191.9")
status_post, _ = dispatch_api("POST", "/api/cognition/responsiveness-background-work-checkpoint")
require(status_post in {404, 405})

html = render_first_use_shell()
require("responsiveness-background-work-checkpoint-panel" in html)
require("responsive-work-queue-reliability-checkpoint-panel" in html)
require("/api/cognition/responsiveness-background-work-checkpoint" in html)
require("v1192 bounded evidence compaction" in html.lower())

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1191.9-responsiveness-background-work-checkpoint") == 1)
require(release.count("v1191_9_responsiveness_background_work_checkpoint_tests.py") == 1)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1191.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1191.8"' in metadata)
require("v1191.9 Responsiveness and Background Work Checkpoint" in metadata)
require("v1192.0-v1192.2 Bounded Evidence Compaction Foundations" in metadata)
require('WORKING_SOURCE_VERSION = "1191.8"' in metadata)

for name in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md"):
    text = (ROOT / name).read_text(encoding="utf-8")
    require("Current source: v1191.9" in text)
    require("v1191.9 Responsiveness and Background Work Checkpoint" in text)
    require("proposal-only software-development campaign" in text)
    require("Windows CRLF" in text)
    require("v1192.0-v1192.2 Bounded Evidence Compaction Foundations" in text)
    require("v1200" in text)
    require("Current source: v1191.8" in text)

navigation_test = (ROOT / "tools" / "v1190_3_5_unified_experience_navigation_tests.py").read_text(encoding="utf-8")
reliability_test = (ROOT / "tools" / "v1190_6_8_unified_experience_reliability_tests.py").read_text(encoding="utf-8")
require(navigation_test.count('.read_text(encoding="utf-8")') >= 3)
require(reliability_test.count('.read_text(encoding="utf-8")') >= 3)

runtime = (ROOT / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
require(runtime.count("build_developer_campaign_conversation_projection(") == 2)
require(runtime.count("developer_campaign_conversation_prompt(developer_campaign_projection)") == 2)
require(runtime.count('result.cognitive_context["developer_campaign_conversation"]') == 2)
require(runtime.find("build_developer_campaign_conversation_projection(") < runtime.find("client.generate(packet.prompt)"))

result = {
    "suite": "v1191.9-responsiveness-background-work-checkpoint",
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
    "global_profile_pass_claimed": False,
    "production_source_modified_by_checkpoint": False,
    "queued_work_executed": False,
    "authority_expanded": False,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
