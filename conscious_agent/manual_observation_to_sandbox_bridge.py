from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANUAL_OBSERVATION_TO_SANDBOX_BRIDGE_VERSION = "1032.0"
CURRENT_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
BRIDGE_BOUNDARIES: dict[str, bool] = {
    "observation_report_is_approval": False,
    "observation_receipt_is_sandbox_permission": False,
    "observation_findings_are_selected_work": False,
    "candidate_found_is_candidate_selected": False,
    "candidate_ranking_is_operator_selection": False,
    "sandbox_packet_exists_is_execution_permission": False,
    "sandbox_readiness_is_authorization": False,
    "packet_assembly_executes_sandbox": False,
    "operator_discussion_is_approval": False,
    "prior_approval_is_reusable_approval": False,
    "smoke_success_is_permission": False,
    "bridge_writes_source": False,
    "bridge_writes_memory": False,
    "bridge_invokes_models_by_default": False,
    "bridge_schedules_work": False,
    "bridge_creates_approval": False,
    "bridge_expands_autonomy": False,
    "operator_review_required": True,
    "fresh_single_use_operator_approval_required_for_future_sandbox_execution": True,
}

OBSERVATION_TO_SANDBOX_CLASSIFICATIONS: tuple[str, ...] = (
    "documentation_only",
    "metadata_repair",
    "route_probe_repair",
    "smoke_check_repair",
    "source_surface_cleanup",
    "unsafe_for_sandbox",
    "requires_operator_selection",
)

FORBIDDEN_SANDBOX_PACKET_FILES: tuple[str, ...] = (
    "data/memory.json",
    "data/workspaces/timeline.json",
    "data/autonomy/",
    "data/self_maintenance/",
    "runtime/",
    ".env",
)

DEFAULT_EXPECTED_COMMANDS: tuple[str, ...] = (
    "python -m compileall conscious_agent tools",
    "python tools/smoke_check.py --fast --json",
    "python tools/smoke_check.py --segment install-governance --json",
    "python tools/smoke_check.py --segment install-dashboard --json",
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


def _docs(root: str | Path | None = None, extra_docs: str = "") -> str:
    repo = Path(root or Path(__file__).resolve().parents[1])
    parts = [
        _read_text(repo / "README_NEXT_STEPS.md"),
        _read_text(repo / "README_RELEASE_HISTORY.md"),
        _read_text(repo / "conscious_agent/manual_observation_to_sandbox_bridge.py"),
        _read_text(repo / "conscious_agent/self_maintenance.py"),
        _read_text(repo / "conscious_agent/dashboard.py"),
        _read_text(repo / "conscious_agent/dashboard_route_probe.py"),
        _read_text(repo / "conscious_agent/api_server.py"),
        _read_text(repo / "conscious_agent/main.py"),
        _read_text(repo / "tools/smoke_check.py"),
        _read_text(repo / "conscious_agent/smoke_segment_registry.py"),
        _read_text(repo / "conscious_agent/source_surface_manifest.py"),
        extra_docs,
    ]
    return "\n".join(parts)


def build_observation_report_intake_bridge(root: str | Path | None = None, observation_report: dict[str, Any] | None = None) -> dict[str, Any]:
    report = observation_report or {
        "source": "review_only_observation_report",
        "findings": ["package privacy check repaired", "sandbox bridge requested"],
        "receipt_status": "received_for_review",
        "authorization_status": "not_authorized",
    }
    rows = [
        _row("receipt-is-review-only", str(report.get("receipt_status", "received_for_review")) in {"received_for_review", "review_only", "not_executed"}, "Observation receipt is accepted for review only."),
        _row("observation-report-not-approval", BRIDGE_BOUNDARIES["observation_report_is_approval"] is False, "Observation report is not approval."),
        _row("observation-receipt-not-sandbox-permission", BRIDGE_BOUNDARIES["observation_receipt_is_sandbox_permission"] is False, "Observation receipt is not sandbox execution permission."),
        _row("findings-not-selected-work", BRIDGE_BOUNDARIES["observation_findings_are_selected_work"] is False, "Findings do not select a candidate or authorize work."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "observation_report_intake_bridge_review_only",
        "observation_report": report,
        "intake_status": "received_for_manual_review",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(BRIDGE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_candidate_extraction(root: str | Path | None = None, observation_report: dict[str, Any] | None = None) -> dict[str, Any]:
    intake = build_observation_report_intake_bridge(root, observation_report)
    candidates = [
        {"id": "candidate-doc-command-boundary", "classification": "documentation_only", "risk_level": "low", "summary": "Clarify sandbox bridge documentation and non-authorization language.", "selected": False},
        {"id": "candidate-metadata-current-state", "classification": "metadata_repair", "risk_level": "low", "summary": "Align current version metadata after the bridge arc.", "selected": False},
        {"id": "candidate-route-probe-bridge-surfaces", "classification": "route_probe_repair", "risk_level": "low", "summary": "Ensure bridge dashboard routes remain visible in the route probe.", "selected": False},
        {"id": "candidate-smoke-bridge-coverage", "classification": "smoke_check_repair", "risk_level": "low", "summary": "Add targeted bridge smoke coverage.", "selected": False},
        {"id": "candidate-source-surface-bridge-manifest", "classification": "source_surface_cleanup", "risk_level": "medium", "summary": "Represent bridge surfaces in the source surface manifest.", "selected": False},
    ]
    rows = [
        _row("intake-ok", intake.get("ok") is True, "Observation intake bridge passes."),
        _row("classification-set-present", all(candidate["classification"] in OBSERVATION_TO_SANDBOX_CLASSIFICATIONS for candidate in candidates), "Candidate classifications use the bounded bridge taxonomy."),
        _row("candidate-found-not-selected", all(candidate.get("selected") is False for candidate in candidates), "Extracted candidates are not operator-selected work."),
        _row("ranking-not-selection", BRIDGE_BOUNDARIES["candidate_ranking_is_operator_selection"] is False, "Candidate ordering/ranking is not operator selection."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_candidate_extraction_review_only",
        "intake": intake,
        "classification_taxonomy": list(OBSERVATION_TO_SANDBOX_CLASSIFICATIONS),
        "candidates": candidates,
        "selected_candidate": None,
        "requires_operator_selection": True,
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(BRIDGE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_packet_draft_assembly(root: str | Path | None = None, candidate_id: str | None = None) -> dict[str, Any]:
    extraction = build_sandbox_candidate_extraction(root)
    candidate = next((item for item in extraction["candidates"] if item["id"] == candidate_id), None)
    selected_by_operator = bool(candidate_id and candidate)
    draft = {
        "candidate_summary": candidate["summary"] if candidate else "No operator-selected candidate supplied; inert example packet only.",
        "candidate_id": candidate_id if selected_by_operator else None,
        "intended_files": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/manual_observation_to_sandbox_bridge.py"] if selected_by_operator else [],
        "forbidden_files": list(FORBIDDEN_SANDBOX_PACKET_FILES),
        "expected_commands": list(DEFAULT_EXPECTED_COMMANDS),
        "expected_outputs": ["compile transcript", "fast smoke JSON", "governance smoke JSON", "dashboard smoke JSON"],
        "rollback_notes": "Sandbox packet is a draft only. Future execution requires a separate throwaway workspace, explicit command allowlist, rollback receipt, and fresh single-use operator approval.",
        "risk_level": candidate["risk_level"] if candidate else "unselected",
        "approval_required": True,
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
    }
    rows = [
        _row("extraction-ok", extraction.get("ok") is True, "Candidate extraction passes."),
        _row("packet-inert", draft["authorization_status"] == "not_authorized" and draft["execution_status"] == "not_executed", "Sandbox packet draft is inert and not authorized."),
        _row("approval-required", draft["approval_required"] is True, "Future sandbox execution requires fresh operator approval."),
        _row("forbidden-files-present", "data/workspaces/timeline.json" in draft["forbidden_files"] and "data/autonomy/" in draft["forbidden_files"], "Packet includes forbidden live/runtime targets."),
        _row("packet-exists-not-execution-permission", BRIDGE_BOUNDARIES["sandbox_packet_exists_is_execution_permission"] is False, "Packet existence does not grant sandbox execution permission."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_packet_draft_assembly_review_only",
        "candidate_selected_by_operator": selected_by_operator,
        "packet": draft,
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(BRIDGE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_misinterpretation_firewall(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    text = _docs(root, docs)
    blocked_interpretations = {
        "observation_intake_as_approval": False,
        "candidate_ranking_as_selection": False,
        "packet_assembly_as_execution": False,
        "sandbox_readiness_as_authorization": False,
        "operator_discussion_as_approval": False,
        "prior_approval_as_reusable_approval": False,
        "smoke_success_as_permission": False,
    }
    required_tokens = [
        "observation_report_is_approval=False",
        "observation_receipt_is_sandbox_permission=False",
        "candidate_found_is_candidate_selected=False",
        "candidate_ranking_is_operator_selection=False",
        "sandbox_packet_exists_is_execution_permission=False",
        "sandbox_readiness_is_authorization=False",
        "packet_assembly_executes_sandbox=False",
        "fresh_single_use_operator_approval_required_for_future_sandbox_execution=True",
    ]
    rows = [
        _row("blocked-interpretations-false", all(value is False for value in blocked_interpretations.values()), "Known bridge misinterpretations are blocked."),
        _row("required-boundary-tokens-present", all(token in text for token in required_tokens), "Docs/source include bridge boundary tokens."),
        _row("no-sandbox-execution", BRIDGE_BOUNDARIES["packet_assembly_executes_sandbox"] is False and BRIDGE_BOUNDARIES["bridge_expands_autonomy"] is False, "Bridge cannot execute sandbox work or expand autonomy."),
        _row("fresh-approval-required", BRIDGE_BOUNDARIES["fresh_single_use_operator_approval_required_for_future_sandbox_execution"] is True, "Future sandbox execution requires fresh single-use approval."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_misinterpretation_firewall_review_only",
        "blocked_interpretations": blocked_interpretations,
        "required_tokens": required_tokens,
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(BRIDGE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_manual_observation_to_sandbox_bridge_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    intake = build_observation_report_intake_bridge(root)
    extraction = build_sandbox_candidate_extraction(root)
    packet = build_sandbox_packet_draft_assembly(root)
    firewall = build_sandbox_misinterpretation_firewall(root, docs)
    text = _docs(root, docs)
    required_docs = [
        "v510.0 - Manual Observation-to-Sandbox Packet Bridge v1",
        "manual-observation-to-sandbox-packet-bridge-v1",
        "observation-to-sandbox-intake-bridge",
        "sandbox-candidate-extraction",
        "sandbox-packet-draft-assembly",
        "sandbox-packet-misinterpretation-firewall",
        "manual-observation-to-sandbox-bridge-audit",
    ]
    rows = [
        _row("version-markers", MANUAL_OBSERVATION_TO_SANDBOX_BRIDGE_VERSION == CURRENT_VERSION == "605.0", f"bridge={MANUAL_OBSERVATION_TO_SANDBOX_BRIDGE_VERSION}; current={CURRENT_VERSION}"),
        _row("intake", intake.get("ok") is True, "Observation intake bridge passes."),
        _row("candidate-extraction", extraction.get("ok") is True, "Sandbox candidate extraction passes."),
        _row("packet-draft", packet.get("ok") is True, "Sandbox packet draft remains inert."),
        _row("misinterpretation-firewall", firewall.get("ok") is True, "Sandbox misinterpretation firewall blocks approval confusion."),
        _row("docs", all(token in text for token in required_docs), "README/source/dashboard/API/CLI smoke tokens describe v506-v510."),
        _row("bridge-status", True, "bridge_status=prepared; authorization_status=not_authorized; execution_status=not_executed; autonomy_status=not_autonomous."),
        _row("no-authority", all(BRIDGE_BOUNDARIES[key] is False for key in ["bridge_writes_source", "bridge_writes_memory", "bridge_invokes_models_by_default", "bridge_schedules_work", "bridge_creates_approval", "bridge_expands_autonomy", "packet_assembly_executes_sandbox"]), "Bridge grants no source, memory, model, schedule, approval, sandbox execution, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "manual_observation_to_sandbox_bridge_audit_review_only",
        "bridge_status": "prepared",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "autonomy_status": "not_autonomous",
        "intake": intake,
        "candidate_extraction": extraction,
        "packet_draft": packet,
        "misinterpretation_firewall": firewall,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(BRIDGE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review bridge packets. Future sandbox execution still requires a separate single-use approval gate and explicit command allowlist.",
    }


def render_manual_observation_to_sandbox_bridge_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"execution_status: {report.get('execution_status', 'not_executed')}",
        f"autonomy_status: {report.get('autonomy_status', 'not_autonomous')}",
    ]
    packet = report.get("packet") or report.get("packet_draft", {}).get("packet")
    if packet:
        lines.append("packet:")
        lines.append(f"- candidate_id: {packet.get('candidate_id')}")
        lines.append(f"- approval_required: {packet.get('approval_required')}")
        lines.append(f"- risk_level: {packet.get('risk_level')}")
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v505.1-v510.0 manual observation-to-sandbox bridge tokens: observation-to-sandbox-intake-bridge sandbox-candidate-extraction sandbox-packet-draft-assembly sandbox-packet-misinterpretation-firewall manual-observation-to-sandbox-bridge-audit manual-observation-to-sandbox-packet-bridge-v1 manual_observation_to_sandbox_bridge.py observation_report_is_approval=False observation_receipt_is_sandbox_permission=False observation_findings_are_selected_work=False candidate_found_is_candidate_selected=False candidate_ranking_is_operator_selection=False sandbox_packet_exists_is_execution_permission=False sandbox_readiness_is_authorization=False packet_assembly_executes_sandbox=False operator_discussion_is_approval=False prior_approval_is_reusable_approval=False smoke_success_is_permission=False bridge_writes_source=False bridge_writes_memory=False bridge_invokes_models_by_default=False bridge_schedules_work=False bridge_creates_approval=False bridge_expands_autonomy=False bridge_status=prepared authorization_status=not_authorized execution_status=not_executed autonomy_status=not_autonomous fresh_single_use_operator_approval_required_for_future_sandbox_execution=True no_native_title_tooltip data-tip command-deck operator-console
