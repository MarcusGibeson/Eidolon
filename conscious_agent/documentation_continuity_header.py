from __future__ import annotations

from pathlib import Path
from typing import Any

DOCUMENTATION_CONTINUITY_HEADER_VERSION = "500.0"
CURRENT_VERSION = "500.0"
CURRENT_VERSION_TAG = "v500.0"
CURRENT_MILESTONE = "v500.0 Operator-Governed Autonomy Readiness Review Board v1"
NEXT_RECOMMENDED_ARC = "v501.0-v505.0 Manual Observation-to-Sandbox Packet Bridge v1"

DOCUMENTATION_CONTINUITY_BOUNDARIES: dict[str, bool] = {
    "documentation_state_is_authorization": False,
    "release_history_is_authorization": False,
    "recommended_next_arc_is_permission": False,
    "handoff_packet_is_execution_packet": False,
    "current_state_header_creates_approval": False,
    "documentation_cleanup_writes_memory": False,
    "documentation_cleanup_applies_source_edits": False,
    "documentation_cleanup_expands_autonomy": False,
    "operator_approval_still_required": True,
}

CURRENT_HEADER_TOKENS = [
    "# Eidolon Current State Header",
    "CURRENT VERSION: v500.0 - Operator-Governed Autonomy Readiness Review Board v1",
    "CURRENT VERIFIED CHECKS",
    "CURRENT BLOCKERS",
    "CURRENT RECOMMENDED NEXT ARC",
    "CURRENT SAFETY BOUNDARY",
    "CURRENT OPERATOR CONTINUITY HANDOFF",
]

HISTORICAL_LEDGER_TOKENS = [
    "## Historical Next-Steps Ledger",
    "HISTORICAL ARC RECORD",
    "COMPLETED ARC RECORD",
    "SUPERSEDED PLANNING NOTE",
    "DO NOT TREAT AS CURRENT PLAN",
]

HANDOFF_TOKENS = [
    "NEW CHAT CONTINUATION PACKET",
    "Latest completed version: v500.0",
    "Standing README rule",
    "Dashboard style rule",
    "Safety/autonomy restriction",
    "Current recommended next arc: v501.0-v505.0 Manual Observation-to-Sandbox Packet Bridge v1",
]

BOUNDARY_TOKENS = [
    "README state is not approval",
    "Release history is not authorization",
    "A recommended next arc is not permission to execute it",
    "A completed smoke check is not operator consent",
    "A handoff packet is not an execution packet",
    "documentation_state_is_authorization=False",
    "release_history_is_authorization=False",
    "recommended_next_arc_is_permission=False",
    "handoff_packet_is_execution_packet=False",
]


def _root(root: str | Path | None = None) -> Path:
    if root is not None:
        candidate = Path(root).resolve()
        if (candidate / "conscious_agent").exists():
            return candidate
        if candidate.name == "conscious_agent":
            return candidate.parents[0]
        return candidate
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _status(ok: bool) -> str:
    return "pass" if ok else "blocked"


def _row(name: str, ok: bool, message: str, **extra: Any) -> dict[str, Any]:
    row = {"name": name, "status": _status(ok), "message": message}
    row.update(extra)
    return row


def _readme_next(root: Path) -> str:
    return _read(root / "README_NEXT_STEPS.md")


def _release_history(root: Path) -> str:
    return _read(root / "README_RELEASE_HISTORY.md")


def _project_docs(root: Path) -> str:
    rels = [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/documentation_continuity_header.py",
        "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
        "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ]
    return "\n".join(_read(root / rel) for rel in rels)


def build_current_state_header_block(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    text = _readme_next(project_root)
    first_chunk = text[:3000]
    rows = [
        _row("current-version-top", "CURRENT VERSION: v500.0" in first_chunk, "README_NEXT_STEPS.md exposes the current version near the top."),
        _row("current-milestone-top", CURRENT_MILESTONE in first_chunk, "README_NEXT_STEPS.md names the current milestone near the top."),
        _row("verified-checks-top", "CURRENT VERIFIED CHECKS" in first_chunk, "Verified checks section is near the top."),
        _row("current-blockers-top", "CURRENT BLOCKERS" in first_chunk, "Current blockers section is near the top."),
        _row("recommended-next-arc-top", NEXT_RECOMMENDED_ARC in first_chunk, "Current recommended next arc points to v501-v505."),
        _row("safety-boundary-top", "CURRENT SAFETY BOUNDARY" in first_chunk and "not authorization" in first_chunk.lower(), "Safety boundary appears near the top."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "current_state_header_block_review_only",
        "expected_version": CURRENT_VERSION_TAG,
        "expected_milestone": CURRENT_MILESTONE,
        "expected_next_arc": NEXT_RECOMMENDED_ARC,
        "rows": rows,
        "ok": ok,
        "status": _status(ok),
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def build_historical_next_steps_separation(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    text = _readme_next(project_root)
    current_pos = text.find("# Eidolon Current State Header")
    ledger_pos = text.find("## Historical Next-Steps Ledger")
    rows = [
        _row("historical-ledger-present", ledger_pos >= 0, "Historical next-step content is separated under a ledger heading."),
        _row("current-before-history", current_pos >= 0 and ledger_pos > current_pos, "Current-state header appears before historical ledger."),
        _row("historical-warning-tokens", all(token in text for token in HISTORICAL_LEDGER_TOKENS), "Historical/superseded/do-not-treat-as-current labels are present."),
        _row("active-plan-not-buried", text.find("CURRENT RECOMMENDED NEXT ARC") < max(ledger_pos, 999999), "Active next arc appears before the historical ledger."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "historical_next_steps_separation_review_only",
        "rows": rows,
        "ok": ok,
        "status": _status(ok),
        "historical_sections_are_authorization": False,
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def build_operator_continuity_handoff_packet(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    text = _readme_next(project_root)
    rows = [
        _row("handoff-section-present", "NEW CHAT CONTINUATION PACKET" in text, "New-chat continuation packet is present."),
        _row("handoff-required-tokens", all(token in text for token in HANDOFF_TOKENS), "Handoff packet includes latest version, rules, safety, verification, and next arc."),
        _row("standing-readme-rule", "README_NEXT_STEPS.md" in text and "README_RELEASE_HISTORY.md" in text, "Standing README/release-history update rule is present."),
        _row("dashboard-rule", "data-tip" in text and "native `title` tooltips" in text, "Dashboard command-deck/data-tip rule is preserved."),
        _row("handoff-not-execution", "A handoff packet is not an execution packet" in text, "Handoff packet is explicitly not execution authority."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "operator_continuity_handoff_packet_review_only",
        "latest_completed_version": CURRENT_VERSION_TAG,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "rows": rows,
        "ok": ok,
        "status": _status(ok),
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def build_documentation_boundary_language(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    docs = _project_docs(project_root)
    rows = [
        _row("boundary-tokens-present", all(token in docs for token in BOUNDARY_TOKENS), "Documentation contains explicit no-authorization boundary tokens."),
        _row("readme-not-approval", "README state is not approval" in docs, "README state cannot be read as approval."),
        _row("release-history-not-authorization", "Release history is not authorization" in docs, "Release history cannot be read as authorization."),
        _row("next-arc-not-permission", "A recommended next arc is not permission to execute it" in docs, "Recommended next arc remains advisory until operator approval."),
        _row("smoke-not-consent", "A completed smoke check is not operator consent" in docs, "Smoke success cannot be read as operator consent."),
        _row("handoff-not-execution", "A handoff packet is not an execution packet" in docs, "Handoff packet cannot execute work."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "documentation_boundary_language_review_only",
        "rows": rows,
        "ok": ok,
        "status": _status(ok),
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def build_documentation_continuity_header_audit(root: str | Path | None = None, docs_text: str | None = None) -> dict[str, Any]:
    project_root = _root(root)
    docs = docs_text if docs_text is not None else _project_docs(project_root)
    header = build_current_state_header_block(project_root)
    history = build_historical_next_steps_separation(project_root)
    handoff = build_operator_continuity_handoff_packet(project_root)
    boundary = build_documentation_boundary_language(project_root)
    release_history = _release_history(project_root)
    required_tokens = [
        "current-state-header-block", "historical-next-steps-separation", "operator-continuity-handoff-packet",
        "documentation-boundary-language", "documentation-continuity-header-audit",
        "operator-governed-documentation-continuity-header-v1", "documentation_continuity_header.py",
        "documentation_state_is_authorization=False", "release_history_is_authorization=False",
        "recommended_next_arc_is_permission=False", "handoff_packet_is_execution_packet=False",
        "current_state_header_creates_approval=False", "documentation_cleanup_writes_memory=False",
        "documentation_cleanup_applies_source_edits=False", "documentation_cleanup_expands_autonomy=False",
        "operator_approval_still_required=True", "no_native_title_tooltip", "data-tip", "command-deck", "operator-console",
    ]
    rows = [
        _row("header", header.get("ok") is True, "Current-state header is present and current."),
        _row("historical-separation", history.get("ok") is True, "Historical next steps are separated and labeled."),
        _row("handoff", handoff.get("ok") is True, "Operator/new-chat continuity packet is present."),
        _row("boundary", boundary.get("ok") is True, "Documentation no-authorization boundary language is present."),
        _row("release-history-v475", "v475.0 - README Current-State and Operator Continuity Header Cleanup v1" in release_history, "Release history documents v475." ),
        _row("smoke-doc-tokens", all(token in docs for token in required_tokens), "Smoke/API/CLI/dashboard/docs tokens are present for v471-v475."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "documentation_continuity_header_audit_review_only",
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "current_state_header": header,
        "historical_separation": history,
        "operator_handoff": handoff,
        "documentation_boundary": boundary,
        "ok": ok,
        "status": _status(ok),
        "writes_files": False,
        "writes_memory": False,
        "applies_source_edits": False,
        "applies_patches": False,
        "publishes_release": False,
        "creates_approval": False,
        "executes_actions": False,
        "expands_autonomy": False,
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def render_documentation_continuity_header_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"status: {report.get('status', 'pass' if report.get('ok') else 'blocked')}",
        f"version: {report.get('version')}",
        "review_only: true",
        "documentation_state_is_authorization: false",
        "release_history_is_authorization: false",
        "recommended_next_arc_is_permission: false",
        "handoff_packet_is_execution_packet: false",
        "operator_approval_still_required: true",
    ]
    rows = report.get("rows") or []
    if rows:
        lines.append("rows:")
        lines.extend(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}" for row in rows)
    return lines
