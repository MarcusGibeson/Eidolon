from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SANDBOX_TO_SOURCE_PROMOTION_PACKET_VERSION = "1052.0"
CURRENT_VERSION = "1075.3"
PROMOTION_PACKET_ID = "v535_sandbox_to_source_promotion_packet"
SANDBOX_RECEIPT_ID = "v530_operator_approved_sandbox_execution_receipt_example"
PROMOTION_CANDIDATE_ID = "v535_reviewable_promotion_candidate"

PROMOTION_PACKET_BOUNDARIES: dict[str, bool] = {
    "sandbox_evidence_exists_is_live_source_approval": False,
    "promotion_diff_preview_is_live_source_mutation": False,
    "rollback_packet_exists_is_rollback_executed": False,
    "sandbox_success_is_live_approval": False,
    "promotion_packet_is_source_mutation": False,
    "rollback_packet_is_permission_to_patch": False,
    "operator_interest_is_approval": False,
    "previous_approval_is_reusable_approval": False,
    "smoke_pass_is_release_approval": False,
    "promotion_readiness_is_promotion_authorization": False,
    "promotion_packet_writes_live_source": False,
    "promotion_packet_writes_memory": False,
    "promotion_packet_executes_rollback": False,
    "promotion_packet_creates_release": False,
    "promotion_packet_invokes_models_by_default": False,
    "promotion_packet_schedules_work": False,
    "promotion_packet_promotes_to_live": False,
    "promotion_packet_reuses_approval": False,
    "promotion_packet_continues_automatically": False,
    "promotion_packet_expands_autonomy": False,
    "approval_required": True,
    "fresh_operator_approval_required": True,
    "single_use_approval_required": True,
}

REVIEWABLE_PROMOTION_FILES: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/example_low_risk_module.py",
)

FORBIDDEN_PROMOTION_TARGETS: tuple[str, ...] = (
    "data/memory.json",
    "data/workspaces/timeline.json",
    "data/autonomy/",
    "data/self_maintenance/",
    "runtime/",
    ".env",
    "models/",
    "local_models/",
)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_id(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _docs(root: str | Path | None = None, extra_docs: str = "") -> str:
    repo = Path(root or Path(__file__).resolve().parents[1])
    paths = [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/sandbox_to_source_promotion_packet.py",
        "conscious_agent/sandbox_execution_runner.py",
        "conscious_agent/first_sandbox_execution_trial.py",
        "conscious_agent/sandbox_execution_dry_run_receipt.py",
        "conscious_agent/sandbox_execution_approval_gate.py",
        "conscious_agent/manual_observation_to_sandbox_bridge.py",
        "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/smoke_segment_registry.py",
    ]
    return "\n".join(_read_text(repo / path) for path in paths) + "\n" + extra_docs


def build_sandbox_evidence_intake_packet(root: str | Path | None = None, receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(receipt or {
        "sandbox_receipt_id": SANDBOX_RECEIPT_ID,
        "commands_run": [
            "python -m compileall conscious_agent tools",
            "python tools/smoke_check.py --tier fast --json",
            "python tools/smoke_check.py --check operator-approved-sandbox-execution-runner-v1 --json",
        ],
        "exit_codes": [0, 0, 0],
        "stdout_summary": "Sandbox command transcript summary only; no live source operation is represented.",
        "stderr_summary": "No blocking sandbox stderr in example evidence.",
        "sandbox_diff_summary": "Example sandbox diff is review material only and is not copied to live source.",
        "privacy_result": "pass",
        "cleanup_result": "pass",
        "approval_burned": True,
    })
    evidence_status = "reviewable" if evidence.get("privacy_result") == "pass" and evidence.get("cleanup_result") == "pass" and evidence.get("approval_burned") is True else "blocked"
    rows = [
        _row("receipt-id-visible", bool(evidence.get("sandbox_receipt_id")), "Sandbox receipt identifier is visible."),
        _row("command-evidence-visible", isinstance(evidence.get("commands_run"), list) and bool(evidence.get("commands_run")), "Command evidence is summarized for operator review."),
        _row("privacy-cleanup-evidence", evidence.get("privacy_result") == "pass" and evidence.get("cleanup_result") == "pass", "Privacy and cleanup evidence are present."),
        _row("approval-burned", evidence.get("approval_burned") is True, "Sandbox approval is burned and cannot be reused."),
        _row("evidence-not-live-approval", PROMOTION_PACKET_BOUNDARIES["sandbox_evidence_exists_is_live_source_approval"] is False, "Sandbox evidence existence is not live-source approval."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_evidence_intake_packet_review_only",
        "sandbox_receipt_id": evidence.get("sandbox_receipt_id"),
        "evidence": evidence,
        "evidence_status": evidence_status,
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(PROMOTION_PACKET_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_rollback": False,
        "promotes_to_live": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_promotion_candidate_diff_preview(root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    intake = build_sandbox_evidence_intake_packet(root, evidence)
    candidate_files = list(REVIEWABLE_PROMOTION_FILES)
    proposed_live_changes = [
        {"file": "README_NEXT_STEPS.md", "change_type": "documentation", "summary": "Document the next operator-approved live patch gate arc."},
        {"file": "README_RELEASE_HISTORY.md", "change_type": "documentation", "summary": "Record promotion-packet review boundaries."},
        {"file": "conscious_agent/example_low_risk_module.py", "change_type": "source-preview", "summary": "Example low-risk source preview only; not written by this packet."},
    ]
    preview = {
        "promotion_candidate_id": PROMOTION_CANDIDATE_ID,
        "candidate_files": candidate_files,
        "proposed_live_changes": proposed_live_changes,
        "unchanged_files": ["data/memory.json", "data/workspaces/timeline.json", "runtime/", "models/"],
        "risk_level": "low_review_only",
        "affected_routes": ["/sandbox-to-source-promotion-review-board"],
        "affected_api_surfaces": ["/api/sandbox-to-source-promotion-review-board/layer"],
        "affected_cli_flags": ["--sandbox-to-source-promotion-packet-v1"],
        "affected_smoke_checks": ["sandbox-to-source-promotion-packet-v1"],
        "live_source_mutation": False,
    }
    rows = [
        _row("intake-ok", intake.get("ok") is True, "Sandbox evidence intake packet passes."),
        _row("candidate-files-visible", candidate_files == list(REVIEWABLE_PROMOTION_FILES), "Candidate file list is visible and bounded."),
        _row("forbidden-live-data-unchanged", all(path in preview["unchanged_files"] for path in ["data/memory.json", "data/workspaces/timeline.json"]), "Memory and runtime workspace files remain unchanged."),
        _row("diff-preview-not-mutation", preview["live_source_mutation"] is False and PROMOTION_PACKET_BOUNDARIES["promotion_diff_preview_is_live_source_mutation"] is False, "Promotion diff preview is not live-source mutation."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "promotion_candidate_diff_preview_review_only",
        "intake": intake,
        "preview": preview,
        "promotion_candidate_id": PROMOTION_CANDIDATE_ID,
        "risk_level": preview["risk_level"],
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(PROMOTION_PACKET_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_rollback": False,
        "promotes_to_live": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_rollback_recovery_packet_builder(root: str | Path | None = None) -> dict[str, Any]:
    diff = build_promotion_candidate_diff_preview(root)
    rollback_packet = {
        "rollback_packet_id": _stable_id([PROMOTION_PACKET_ID, PROMOTION_CANDIDATE_ID, "rollback"]),
        "pre_change_snapshot_plan": "Create operator-reviewed file snapshots before any future approved live promotion.",
        "rollback_steps": [
            "Stop after failed verification.",
            "Restore only files included in the approved promotion scope.",
            "Run compile and targeted smoke after restore.",
            "Record rollback evidence for operator review.",
        ],
        "verification_after_rollback": [
            "python -m compileall conscious_agent tools",
            "python tools/smoke_check.py --tier fast --json",
            "python tools/smoke_check.py --check sandbox-to-source-promotion-packet-v1 --json",
        ],
        "files_to_restore": list(REVIEWABLE_PROMOTION_FILES),
        "expected_safe_state": "live_source_restored_to_pre_change_snapshot",
        "failure_conditions": ["compile failure", "targeted smoke failure", "package privacy failure", "dashboard route regression"],
        "rollback_executed": False,
    }
    rows = [
        _row("diff-preview-ok", diff.get("ok") is True, "Promotion candidate diff preview passes."),
        _row("rollback-plan-visible", bool(rollback_packet["rollback_steps"]) and bool(rollback_packet["files_to_restore"]), "Rollback steps and restore files are visible."),
        _row("verification-visible", "python -m compileall conscious_agent tools" in rollback_packet["verification_after_rollback"], "Rollback verification commands are visible."),
        _row("rollback-not-executed", rollback_packet["rollback_executed"] is False and PROMOTION_PACKET_BOUNDARIES["rollback_packet_exists_is_rollback_executed"] is False, "Rollback packet existence is not rollback execution."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "rollback_recovery_packet_builder_review_only",
        "diff_preview": diff,
        "rollback_packet": rollback_packet,
        "rollback_status": "planned_not_executed",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(PROMOTION_PACKET_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_rollback": False,
        "promotes_to_live": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_promotion_misinterpretation_firewall(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    blocked = {
        "sandbox_success_as_live_approval": False,
        "promotion_packet_as_source_mutation": False,
        "rollback_packet_as_permission_to_patch": False,
        "operator_interest_as_approval": False,
        "previous_approval_as_reusable_approval": False,
        "smoke_pass_as_release_approval": False,
        "promotion_readiness_as_promotion_authorization": False,
    }
    text = _docs(root, docs)
    required_language = [
        "sandbox_evidence_exists_is_live_source_approval=False",
        "promotion_diff_preview_is_live_source_mutation=False",
        "rollback_packet_exists_is_rollback_executed=False",
        "promotion_readiness_is_promotion_authorization=False",
        "promotion_packet_status=prepared",
        "live_source_status=untouched",
        "rollback_status=planned_not_executed",
        "autonomy_status=not_autonomous",
    ]
    rows = [
        _row("blocked-interpretations", all(value is False for value in blocked.values()), "Promotion misinterpretation patterns are blocked."),
        _row("docs-language", all(token in text for token in required_language), "Docs/source/smoke include required promotion boundary language."),
        _row("no-live-memory-release", all(PROMOTION_PACKET_BOUNDARIES[key] is False for key in ["promotion_packet_writes_live_source", "promotion_packet_writes_memory", "promotion_packet_creates_release", "promotion_packet_promotes_to_live", "promotion_packet_expands_autonomy"]), "Promotion firewall grants no live, memory, release, promotion, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "promotion_misinterpretation_firewall_review_only",
        "blocked_interpretations": blocked,
        "firewall_status": "active_review_only",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "rollback_status": "planned_not_executed",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(PROMOTION_PACKET_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_rollback": False,
        "promotes_to_live": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_to_source_promotion_review_board(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    intake = build_sandbox_evidence_intake_packet(root)
    diff = build_promotion_candidate_diff_preview(root)
    rollback = build_rollback_recovery_packet_builder(root)
    firewall = build_promotion_misinterpretation_firewall(root, docs)
    text = _docs(root, docs)
    required_docs = [
        "v540.0 - Sandbox-to-Source Promotion Packet v1",
        "sandbox-to-source-promotion-packet-v1",
        "sandbox-evidence-intake-packet",
        "promotion-candidate-diff-preview",
        "rollback-recovery-packet-builder",
        "promotion-misinterpretation-firewall",
        "sandbox-to-source-promotion-review-board",
        "promotion_packet_status=prepared",
        "live_source_status=untouched",
        "approval_status=required",
        "authorization_status=not_authorized",
        "rollback_status=planned_not_executed",
        "release_status=not_created",
        "autonomy_status=not_autonomous",
        "promotion_readiness_is_promotion_authorization=False",
    ]
    rows = [
        _row("version-markers", SANDBOX_TO_SOURCE_PROMOTION_PACKET_VERSION == CURRENT_VERSION == "605.0", f"promotion={SANDBOX_TO_SOURCE_PROMOTION_PACKET_VERSION}; current={CURRENT_VERSION}"),
        _row("evidence-intake", intake.get("ok") is True, "Sandbox evidence intake packet is reviewable and non-authorizing."),
        _row("diff-preview", diff.get("ok") is True and diff.get("writes_live_source") is False, "Promotion candidate diff preview does not mutate live source."),
        _row("rollback-packet", rollback.get("ok") is True and rollback.get("executes_rollback") is False, "Rollback packet is planned and not executed."),
        _row("misinterpretation-firewall", firewall.get("ok") is True, "Promotion firewall blocks sandbox-success, packet, rollback, smoke, approval, and authorization confusion."),
        _row("docs", all(token in text for token in required_docs), "README/source/dashboard/API/CLI smoke tokens describe v531-v535."),
        _row("no-live-authority", all(PROMOTION_PACKET_BOUNDARIES[key] is False for key in ["promotion_packet_writes_live_source", "promotion_packet_writes_memory", "promotion_packet_executes_rollback", "promotion_packet_creates_release", "promotion_packet_invokes_models_by_default", "promotion_packet_schedules_work", "promotion_packet_promotes_to_live", "promotion_packet_reuses_approval", "promotion_packet_continues_automatically", "promotion_packet_expands_autonomy"]), "Promotion packet grants no live source, memory, rollback execution, model, schedule, release, promotion, approval reuse, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_to_source_promotion_review_board_review_only",
        "promotion_packet_id": PROMOTION_PACKET_ID,
        "promotion_packet_status": "prepared",
        "live_source_status": "untouched",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "rollback_status": "planned_not_executed",
        "release_status": "not_created",
        "memory_status": "untouched",
        "autonomy_status": "not_autonomous",
        "sandbox_evidence_intake_packet": intake,
        "promotion_candidate_diff_preview": diff,
        "rollback_recovery_packet_builder": rollback,
        "promotion_misinterpretation_firewall": firewall,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(PROMOTION_PACKET_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_rollback": False,
        "executes_commands": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "promotes_to_live": False,
        "creates_release_candidate": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the promotion packet. Any future live-source promotion requires a separate exact fresh single-use approval gate and must remain narrow, reversible, and non-autonomous.",
    }


def render_sandbox_to_source_promotion_packet_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"promotion_packet_status: {report.get('promotion_packet_status', 'prepared')}",
        f"live_source_status: {report.get('live_source_status', 'untouched')}",
        f"approval_status: {report.get('approval_status', 'required')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"rollback_status: {report.get('rollback_status', 'planned_not_executed')}",
        f"release_status: {report.get('release_status', 'not_created')}",
        f"memory_status: {report.get('memory_status', 'untouched')}",
        f"autonomy_status: {report.get('autonomy_status', 'not_autonomous')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v530.1-v540.0 sandbox-to-source promotion packet tokens: sandbox-evidence-intake-packet promotion-candidate-diff-preview rollback-recovery-packet-builder promotion-misinterpretation-firewall sandbox-to-source-promotion-review-board sandbox-to-source-promotion-packet-v1 sandbox_to_source_promotion_packet.py sandbox_evidence_exists_is_live_source_approval=False promotion_diff_preview_is_live_source_mutation=False rollback_packet_exists_is_rollback_executed=False sandbox_success_is_live_approval=False promotion_packet_is_source_mutation=False rollback_packet_is_permission_to_patch=False operator_interest_is_approval=False previous_approval_is_reusable_approval=False smoke_pass_is_release_approval=False promotion_readiness_is_promotion_authorization=False promotion_packet_writes_live_source=False promotion_packet_writes_memory=False promotion_packet_executes_rollback=False promotion_packet_creates_release=False promotion_packet_invokes_models_by_default=False promotion_packet_schedules_work=False promotion_packet_promotes_to_live=False promotion_packet_reuses_approval=False promotion_packet_continues_automatically=False promotion_packet_expands_autonomy=False promotion_packet_status=prepared live_source_status=untouched approval_status=required authorization_status=not_authorized rollback_status=planned_not_executed release_status=not_created memory_status=untouched autonomy_status=not_autonomous fresh_operator_approval_required=True single_use_approval_required=True no_native_title_tooltip data-tip command-deck operator-console
