from __future__ import annotations

from release_metadata import RUNTIME_VERSION

"""Audit and rollback notes for stable supervised loop records.

v6.7 note:
    Stable loop live runs should leave an operator-friendly audit trail. This
    module is read-mostly: it inspects a stable-loop record and its linked work
    cycle, task, approval, and patch records, then produces rollback/check notes
    without mutating project state unless explicitly asked to refresh a saved
    record's audit block.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from approval_manager import get_approval
from patch_suggester import load_patch_proposal
from task_queue import get_task
from work_cycle import load_work_cycle

AUDIT_VERSION = RUNTIME_VERSION
@dataclass
class StableLoopAuditResult:
    ok: bool
    loop_id: str = ""
    message: str = ""
    error: str = ""
    audit: dict[str, Any] | None = None
    loop: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _cycle_from_loop(loop: dict[str, Any], prefer_live: bool = True) -> dict[str, Any]:
    """Return the cycle most relevant for audit.

    Live runs audit the live cycle. Preview-only records audit the preview cycle,
    mostly to explain that there were no live mutations.
    """
    if prefer_live and loop.get("live"):
        cycle = loop.get("live_cycle") if isinstance(loop.get("live_cycle"), dict) else None
        if cycle:
            return cycle
        return load_work_cycle(str(loop.get("live_cycle_id") or "")) or {}

    cycle = loop.get("preview_cycle") if isinstance(loop.get("preview_cycle"), dict) else None
    if cycle:
        return cycle
    return load_work_cycle(str(loop.get("preview_cycle_id") or "")) or {}


def _collect_event_details(cycle: dict[str, Any]) -> dict[str, Any]:
    executed: list[str] = []
    approvals: list[str] = []
    patches: list[str] = []
    commands: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []

    for event in _as_list(cycle.get("events")):
        if not isinstance(event, dict):
            continue
        action_result = event.get("action_result") if isinstance(event.get("action_result"), dict) else {}
        decision = event.get("decision") if isinstance(event.get("decision"), dict) else {}
        task_id = str(action_result.get("executed_task_id") or action_result.get("task_id") or decision.get("task_id") or "").strip()
        action = str(action_result.get("action") or decision.get("action") or event.get("type") or "").strip()
        if task_id and action in {"execute_task", "execute_approved_task"}:
            executed.append(task_id)
        if action_result.get("approval_id"):
            approvals.append(action_result.get("approval_id"))
        if action_result.get("patch_id"):
            patches.append(action_result.get("patch_id"))
        for patch_id in _as_list(action_result.get("created_followup_task_ids")):
            pass

        execution = action_result.get("execution") if isinstance(action_result.get("execution"), dict) else {}
        command = _extract_command_from_execution(execution)
        if command:
            commands.append({
                "task_id": task_id,
                "action": action,
                "command": command,
                "ok": execution.get("ok"),
                "dry_run": execution.get("dry_run"),
                "error": execution.get("error", ""),
            })

        actions.append({
            "event_type": event.get("type", ""),
            "action": action,
            "task_id": task_id,
            "ok": action_result.get("ok"),
            "blocked": action_result.get("blocked"),
            "stopped_reason": action_result.get("stopped_reason", ""),
            "approval_id": action_result.get("approval_id", ""),
            "patch_id": action_result.get("patch_id", ""),
        })

    return {
        "executed_task_ids": _unique(executed),
        "approval_ids": _unique(approvals),
        "patch_ids": _unique(patches),
        "commands": commands,
        "actions": actions,
    }


def _extract_command_from_execution(execution: dict[str, Any]) -> str:
    metadata = execution.get("metadata") if isinstance(execution.get("metadata"), dict) else {}
    for key in ["command", "approved_command", "approval_command"]:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value

    result = str(execution.get("result") or "")
    for line in result.splitlines():
        if line.lower().startswith("command:"):
            return line.split(":", 1)[1].strip()
    return ""


def _approval_rows(approval_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for approval_id in approval_ids:
        approval = get_approval(approval_id)
        if not approval:
            rows.append({"id": approval_id, "found": False})
            continue
        metadata = approval.get("metadata") if isinstance(approval.get("metadata"), dict) else {}
        rows.append({
            "id": approval.get("id", approval_id),
            "found": True,
            "status": approval.get("status", ""),
            "action_type": approval.get("action_type", ""),
            "risk_level": approval.get("risk_level", ""),
            "object_id": approval.get("object_id", ""),
            "summary": approval.get("summary", ""),
            "command": approval.get("command", "") or metadata.get("approved_command", ""),
        })
    return rows


def _task_rows(task_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task_id in task_ids:
        task = get_task(task_id)
        if not task:
            rows.append({"id": task_id, "found": False})
            continue
        metadata = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}
        rows.append({
            "id": task.get("id", task_id),
            "found": True,
            "title": task.get("title", ""),
            "status": task.get("status", ""),
            "risk": task.get("risk", ""),
            "requires_approval": bool(task.get("requires_approval")),
            "patch_id": task.get("patch_id", "") or metadata.get("patch_id", ""),
            "approval_id": metadata.get("approval_id", ""),
            "action_type": metadata.get("action_type", ""),
        })
    return rows


def _patch_rows(patch_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for patch_id in patch_ids:
        patch = load_patch_proposal(patch_id)
        if not patch:
            rows.append({
                "id": patch_id,
                "found": False,
                "rollback_available": False,
                "rollback_notes": [f"Patch record not found: {patch_id}"],
            })
            continue
        backup_path = str(patch.get("backup_path") or "").strip()
        backup_exists = bool(backup_path and Path(backup_path).exists())
        status = str(patch.get("status") or "")
        rollback_available = status == "applied" and bool(backup_path)
        notes: list[str] = []
        if status != "applied":
            notes.append(f"Patch status is {status!r}; rollback command is only valid for applied patches.")
        if status == "applied" and not backup_path:
            notes.append("Applied patch has no backup_path. Manual inspection required before rollback.")
        if backup_path and not backup_exists:
            notes.append("Backup path is recorded but was not found from this runtime. Verify path before rollback.")
        rows.append({
            "id": patch.get("id", patch_id),
            "found": True,
            "status": status,
            "target_file": patch.get("target_file", ""),
            "risk_level": patch.get("risk_level", ""),
            "backup_path": backup_path,
            "backup_exists": backup_exists,
            "rollback_available": rollback_available,
            "rollback_dry_run_command": f"python conscious_agent/main.py --rollback-patch {patch_id} --dry-run" if rollback_available else "",
            "rollback_command": f"python conscious_agent/main.py --rollback-patch {patch_id}" if rollback_available else "",
            "rollback_notes": notes,
        })
    return rows


def _check_commands(loop: dict[str, Any], audit_patch_rows: list[dict[str, Any]]) -> list[str]:
    commands = [
        "python conscious_agent/main.py --status",
        "python conscious_agent/main.py --settings-health",
        "python conscious_agent/main.py --task-work summary",
        "python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop",
        "python conscious_agent/main.py --list-applied-patches",
    ]
    loop_id = str(loop.get("id") or "").strip()
    if loop_id:
        commands.append(f"python conscious_agent/main.py --show-stable-loop-audit {loop_id} --stable-loop-audit-full")
    for patch in audit_patch_rows:
        if patch.get("rollback_dry_run_command"):
            commands.append(str(patch["rollback_dry_run_command"]))
    return _unique(commands)


def build_stable_loop_audit(loop: dict[str, Any] | None) -> dict[str, Any]:
    loop = loop or {}
    loop_id = str(loop.get("id") or "")
    live = bool(loop.get("live"))
    cycle = _cycle_from_loop(loop, prefer_live=True)
    event_details = _collect_event_details(cycle)

    created_task_ids = _unique(_as_list(cycle.get("created_task_ids")) + _as_list(cycle.get("created_work_ids")))
    created_followup_task_ids = _unique(_as_list(cycle.get("created_followup_task_ids")) + _as_list(cycle.get("created_followup_work_ids")))
    executed_task_ids = _unique(_as_list(cycle.get("executed_task_ids")) + _as_list(cycle.get("executed_work_ids")) + event_details["executed_task_ids"])
    approval_ids = _unique(_as_list(cycle.get("approval_ids")) + event_details["approval_ids"])
    patch_ids = _unique(_as_list(cycle.get("patch_ids")) + event_details["patch_ids"])
    recovered_task_ids = _unique(_as_list(cycle.get("recovered_task_ids")) + _as_list(cycle.get("recovered_work_ids")))

    changed_task_ids = _unique(created_task_ids + created_followup_task_ids + executed_task_ids + recovered_task_ids)
    task_rows = _task_rows(changed_task_ids)
    approval_rows = _approval_rows(approval_ids)
    patch_rows = _patch_rows(patch_ids)

    warnings: list[str] = []
    if not live:
        warnings.append("This is a preview-only stable loop record. No live task mutations should have occurred.")
    if live and not loop.get("live_cycle_id"):
        warnings.append("Record is marked live but has no live_cycle_id.")
    if live and not approval_ids and bool(loop.get("approve_work_execution")):
        warnings.append("Live run allowed approval-gated execution but no approval IDs were recorded.")
    for patch in patch_rows:
        warnings.extend(str(note) for note in _as_list(patch.get("rollback_notes")))

    return {
        "version": AUDIT_VERSION,
        "generated_at": _now(),
        "loop_id": loop_id,
        "project_id": loop.get("project_id", ""),
        "live": live,
        "ok": bool(loop.get("ok")),
        "stopped_reason": loop.get("stopped_reason", ""),
        "cycle_id": cycle.get("id", ""),
        "cycle_dry_run": cycle.get("dry_run", None),
        "changed_task_ids": changed_task_ids,
        "created_task_ids": created_task_ids,
        "created_followup_task_ids": created_followup_task_ids,
        "executed_task_ids": executed_task_ids,
        "recovered_task_ids": recovered_task_ids,
        "approval_ids": approval_ids,
        "patch_ids": patch_ids,
        "commands": event_details["commands"],
        "actions": event_details["actions"],
        "tasks": task_rows,
        "approvals": approval_rows,
        "patches": patch_rows,
        "check_commands": _check_commands(loop, patch_rows),
        "warnings": _unique(warnings),
        "summary": _audit_summary_text(live=live, changed=len(changed_task_ids), approvals=len(approval_ids), patches=len(patch_ids), warnings=len(warnings)),
    }


def _audit_summary_text(live: bool, changed: int, approvals: int, patches: int, warnings: int) -> str:
    mode = "Live" if live else "Preview"
    return f"{mode} stable-loop audit: {changed} changed task id(s), {approvals} approval id(s), {patches} patch id(s), {warnings} warning(s)."


def stable_loop_audit_text(audit_or_loop: dict[str, Any] | None, full: bool = False) -> str:
    if not audit_or_loop:
        return "# Stable loop audit\n\nNo stable loop audit data found."
    audit = audit_or_loop.get("audit") if isinstance(audit_or_loop.get("audit"), dict) else audit_or_loop
    if not isinstance(audit, dict) or "changed_task_ids" not in audit:
        audit = build_stable_loop_audit(audit_or_loop)

    lines = [
        "# Stable loop audit",
        "",
        f"Loop: {audit.get('loop_id', '')}",
        f"Version: {audit.get('version', AUDIT_VERSION)}",
        f"Generated: {audit.get('generated_at', '')}",
        f"Project: {audit.get('project_id', '')}",
        f"Live: {audit.get('live')}",
        f"OK: {audit.get('ok')}",
        f"Cycle: {audit.get('cycle_id', '')}",
        f"Summary: {audit.get('summary', '')}",
        "",
        "## Changed task ids",
    ]
    changed = _as_list(audit.get("changed_task_ids"))
    lines.extend(f"- {task_id}" for task_id in changed) if changed else lines.append("- None recorded")

    approvals = _as_list(audit.get("approvals"))
    lines.append("")
    lines.append("## Approval ids used / created")
    if approvals:
        for approval in approvals:
            lines.append(f"- {approval.get('id')} | {approval.get('status', '')} | {approval.get('risk_level', '')} | {approval.get('summary', '')}")
            if approval.get("command"):
                lines.append(f"  command: {approval.get('command')}")
    else:
        lines.append("- None recorded")

    patches = _as_list(audit.get("patches"))
    lines.append("")
    lines.append("## Patch rollback notes")
    if patches:
        for patch in patches:
            lines.append(f"- {patch.get('id')} | {patch.get('status', '')} | {patch.get('target_file', '')}")
            if patch.get("backup_path"):
                lines.append(f"  backup: {patch.get('backup_path')} | exists={patch.get('backup_exists')}")
            if patch.get("rollback_dry_run_command"):
                lines.append(f"  dry-run rollback: {patch.get('rollback_dry_run_command')}")
            if patch.get("rollback_command"):
                lines.append(f"  rollback: {patch.get('rollback_command')}")
            for note in _as_list(patch.get("rollback_notes")):
                lines.append(f"  note: {note}")
    else:
        lines.append("- No patch ids recorded for this loop.")

    warnings = _as_list(audit.get("warnings"))
    if warnings:
        lines.append("")
        lines.append("## Warnings")
        lines.extend(f"- {warning}" for warning in warnings)

    checks = _as_list(audit.get("check_commands"))
    lines.append("")
    lines.append("## Recommended check commands")
    lines.extend(f"- {command}" for command in checks) if checks else lines.append("- None")

    if full:
        lines.extend(["", "## Raw audit", json.dumps(audit, indent=2, default=str)])
    return "\n".join(lines).strip()


def refresh_stable_loop_audit(loop_id: str = "latest") -> StableLoopAuditResult:
    from stable_supervised_loop import load_stable_loop, save_stable_loop

    loop = load_stable_loop(loop_id)
    if not loop:
        return StableLoopAuditResult(False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")
    audit = build_stable_loop_audit(loop)
    loop["audit"] = audit
    save_stable_loop(loop)
    return StableLoopAuditResult(True, loop_id=str(loop.get("id") or loop_id), message="Stable loop audit refreshed.", audit=audit, loop=loop)


def print_stable_loop_audit(loop_id: str = "latest", refresh: bool = False, full: bool = False) -> None:
    from stable_supervised_loop import load_stable_loop

    if refresh:
        result = refresh_stable_loop_audit(loop_id)
        if not result.ok:
            print(f"Stable loop audit failed: {result.error}")
            return
        print(stable_loop_audit_text(result.audit, full=full))
        return

    loop = load_stable_loop(loop_id)
    if not loop:
        print(f"Stable loop not found: {loop_id}")
        return
    audit = loop.get("audit") if isinstance(loop.get("audit"), dict) else build_stable_loop_audit(loop)
    print(stable_loop_audit_text(audit, full=full))
