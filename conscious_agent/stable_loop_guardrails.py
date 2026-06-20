from __future__ import annotations

"""Closure-aware guardrails for stable supervised loop live runs.

v6.9 note:
    v6.8 made stable-loop follow-up completion state reportable. This module
    turns that report into a live-run safety gate so unresolved follow-up chains
    can block new live advancement until the operator closes, resolves, archives,
    or intentionally bypasses the guardrail. A tiny brake pedal, because agents
    without brakes are just bugs with ambition.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from stable_loop_followup_completion import (
    FOLLOWUP_COMPLETION_VERSION,
    list_stable_loop_followup_completion_rows,
    stable_loop_followup_completion_summary,
)

STABLE_LOOP_GUARDRAIL_VERSION = "6.9"
DEFAULT_LIVE_BLOCK_FILTER = "unresolved"


@dataclass
class StableLoopGuardrailResult:
    ok: bool
    version: str = STABLE_LOOP_GUARDRAIL_VERSION
    checked_at: str = ""
    project_id: str = "eidolon"
    ok_for_preview: bool = True
    ok_for_live: bool = True
    bypassed: bool = False
    block_live: bool = False
    unresolved_count: int = 0
    missing_followup_count: int = 0
    open_followup_chain_count: int = 0
    ready_to_resolve_count: int = 0
    resolved_count: int = 0
    cleanup_candidate_count: int = 0
    blocker_ids: list[str] | None = None
    blockers: list[dict[str, Any]] | None = None
    warnings: list[str] | None = None
    recommended_actions: list[str] | None = None
    message: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_loop_guardrail_summary(
    project_id: str | None = None,
    bypass: bool = False,
    include_archived: bool = False,
    limit: int = 25,
) -> dict[str, Any]:
    """Return a read-only closure guardrail summary.

    The guardrail only blocks live stable loops. Preview/preflight remains
    allowed so the operator can see what would happen next.
    """
    project = (project_id or "eidolon").strip() or "eidolon"
    report = stable_loop_followup_completion_summary(
        completion_filter=DEFAULT_LIVE_BLOCK_FILTER,
        include_archived=include_archived,
    )
    blockers = list_stable_loop_followup_completion_rows(
        completion_filter=DEFAULT_LIVE_BLOCK_FILTER,
        include_archived=include_archived,
        limit=max(1, min(int(limit or 25), 100)),
    )
    unresolved_count = int(report.get("unresolved_count") or len(blockers) or 0)
    missing_count = int(report.get("missing_followup_count") or 0)
    open_count = int(report.get("open_followup_chain_count") or 0)
    ready_count = int(report.get("ready_to_resolve_count") or 0)
    resolved_count = int(report.get("resolved_count") or 0)
    cleanup_count = int(report.get("cleanup_candidate_count") or 0)

    block_live = unresolved_count > 0 and not bypass
    warnings: list[str] = []
    recommended_actions: list[str] = []

    if unresolved_count:
        warnings.append(
            f"{unresolved_count} unresolved stable-loop follow-up chain(s) exist. Live stable-loop advancement is blocked unless explicitly bypassed."
        )
    if missing_count:
        recommended_actions.append("Create missing follow-up tasks for action-required stable-loop decisions.")
    if open_count:
        recommended_actions.append("Complete or cancel open stable-loop follow-up tasks before new live advancement.")
    if ready_count:
        recommended_actions.append("Resolve ready-to-resolve follow-up chains from the dashboard or CLI.")
    if cleanup_count:
        recommended_actions.append("Archive resolved follow-up completion records during routine cleanup.")
    if not recommended_actions:
        recommended_actions.append("No closure blockers found. Live stable-loop advancement may proceed after normal preview/review.")

    message = (
        "Live stable-loop guardrail bypassed by operator."
        if unresolved_count and bypass
        else (
            "Live stable-loop advancement blocked by unresolved follow-up chains."
            if block_live
            else "Stable-loop closure guardrails are clear."
        )
    )

    return StableLoopGuardrailResult(
        ok=not block_live,
        checked_at=_now(),
        project_id=project,
        ok_for_preview=True,
        ok_for_live=not block_live,
        bypassed=bool(bypass),
        block_live=block_live,
        unresolved_count=unresolved_count,
        missing_followup_count=missing_count,
        open_followup_chain_count=open_count,
        ready_to_resolve_count=ready_count,
        resolved_count=resolved_count,
        cleanup_candidate_count=cleanup_count,
        blocker_ids=[str(row.get("id") or "") for row in blockers if row.get("id")],
        blockers=blockers,
        warnings=warnings,
        recommended_actions=recommended_actions,
        message=message,
        error="Unresolved stable-loop follow-up chains block live advancement." if block_live else "",
    ).to_dict() | {
        "followup_completion_version": FOLLOWUP_COMPLETION_VERSION,
        "followup_completion_report": report,
    }


def stable_loop_guardrails_text(data: dict[str, Any] | None = None, full: bool = False) -> str:
    guardrails = data or stable_loop_guardrail_summary()
    lines = [
        "# Stable-loop closure guardrails",
        "",
        f"Version: {guardrails.get('version', STABLE_LOOP_GUARDRAIL_VERSION)}",
        f"Project: {guardrails.get('project_id', 'eidolon')}",
        f"OK for preview: {guardrails.get('ok_for_preview')}",
        f"OK for live: {guardrails.get('ok_for_live')}",
        f"Bypassed: {guardrails.get('bypassed')}",
        f"Unresolved follow-up chains: {guardrails.get('unresolved_count', 0)}",
        f"Missing follow-up tasks: {guardrails.get('missing_followup_count', 0)}",
        f"Open follow-up chains: {guardrails.get('open_followup_chain_count', 0)}",
        f"Ready to resolve: {guardrails.get('ready_to_resolve_count', 0)}",
        f"Resolved: {guardrails.get('resolved_count', 0)}",
        f"Cleanup candidates: {guardrails.get('cleanup_candidate_count', 0)}",
        f"Message: {guardrails.get('message', '')}",
    ]
    if guardrails.get("error"):
        lines.append(f"Error: {guardrails.get('error')}")
    warnings = guardrails.get("warnings") or []
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {item}" for item in warnings)
    actions = guardrails.get("recommended_actions") or []
    if actions:
        lines.extend(["", "## Recommended actions"])
        lines.extend(f"- {item}" for item in actions)
    blockers = guardrails.get("blockers") or []
    if blockers:
        lines.extend(["", "## Blocking records"])
        for row in blockers[:25]:
            lines.append(
                f"- {row.get('id')} | {row.get('completion_status_label')} | "
                f"decision={row.get('final_decision_label')} | tasks={row.get('task_count')} open={row.get('open_task_count')} | "
                f"next={row.get('recommended_action')}"
            )
    if full:
        lines.extend(["", "## Raw guardrails", json.dumps(guardrails, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_stable_loop_guardrails(project_id: str = "eidolon", bypass: bool = False, include_archived: bool = False, full: bool = False) -> None:
    data = stable_loop_guardrail_summary(project_id=project_id, bypass=bypass, include_archived=include_archived)
    print(stable_loop_guardrails_text(data, full=full))
