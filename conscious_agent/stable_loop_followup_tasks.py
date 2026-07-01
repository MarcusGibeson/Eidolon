from __future__ import annotations

"""Decision-aware follow-up task creation for stable-loop records.

v6.7 note:
    v6.5 made stable-loop final decisions searchable. v6.7 turns the action-
    required decisions (fix_forward, rollback, needs_review) into canonical
    task-backed follow-ups so operator decisions become trackable work instead
    of decorative JSON fossils with opinions.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from stable_supervised_loop import list_stable_loops, load_stable_loop, save_stable_loop
from stable_loop_decision_report import (
    ACTION_REQUIRED_DECISIONS,
    DECISION_FILTER_LABELS,
    decision_label,
    final_decision_for_loop,
    list_stable_loop_decision_rows,
    normalize_decision_filter,
    stable_loop_decision_row,
    stable_loop_matches_decision_filter,
)
from stable_loop_operator_notes import ensure_operator_notes
from task_queue import add_task, list_tasks, update_task_fields

FOLLOWUP_TASK_VERSION = "1032.0"
FOLLOWUP_SOURCE = "stable_loop_decision"
FOLLOWUP_CATEGORY = "stable_loop_followup"
FOLLOWUP_ACTION_DECISIONS = set(ACTION_REQUIRED_DECISIONS)


@dataclass
class StableLoopFollowupResult:
    ok: bool
    dry_run: bool = True
    loop_id: str = ""
    decision: str = "undecided"
    created_task_ids: list[str] | None = None
    existing_task_ids: list[str] | None = None
    planned_followups: list[dict[str, Any]] | None = None
    message: str = ""
    error: str = ""
    loop: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StableLoopFollowupBatchResult:
    ok: bool
    dry_run: bool = True
    decision_filter: str = "action_required"
    selected_loop_ids: list[str] | None = None
    created_task_ids: list[str] | None = None
    existing_task_ids: list[str] | None = None
    results: list[dict[str, Any]] | None = None
    message: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str, fallback: str = "item") -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "")).strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned[:48] or fallback


def _audit(loop: dict[str, Any]) -> dict[str, Any]:
    return loop.get("audit") if isinstance(loop.get("audit"), dict) else {}


def _operator_followups(loop: dict[str, Any]) -> list[dict[str, Any]]:
    notes = ensure_operator_notes(loop, save=False)
    items = notes.get("decision_followups") if isinstance(notes.get("decision_followups"), list) else []
    return [item for item in items if isinstance(item, dict)]


def _existing_followup_tasks(loop_id: str, decision: str = "", followup_kind: str = "") -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for task in list_tasks(include_cancelled=True):
        metadata = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}
        if metadata.get("source") != FOLLOWUP_SOURCE:
            continue
        if str(metadata.get("stable_loop_id") or "") != loop_id:
            continue
        if decision and str(metadata.get("final_decision") or "") != decision:
            continue
        if followup_kind and str(metadata.get("followup_kind") or "") != followup_kind:
            continue
        matches.append(task)
    return matches


def _command_from_audit(audit: dict[str, Any], key: str) -> str:
    commands = audit.get("check_commands") if isinstance(audit.get("check_commands"), list) else []
    for command in commands:
        command_text = str(command or "").strip()
        if key in command_text:
            return command_text
    return ""


def _build_followup_specs(loop: dict[str, Any], decision: str) -> list[dict[str, Any]]:
    loop_id = str(loop.get("id") or "")
    project_id = str(loop.get("project_id") or "eidolon") or "eidolon"
    decision_row = stable_loop_decision_row(loop)
    audit = _audit(loop)
    specs: list[dict[str, Any]] = []

    base_metadata = {
        "version": FOLLOWUP_TASK_VERSION,
        "source": FOLLOWUP_SOURCE,
        "stable_loop_id": loop_id,
        "final_decision": decision,
        "review_status": decision_row.get("review_status", ""),
        "live": bool(loop.get("live")),
        "created_by": "stable_loop_followup_tasks",
    }

    if decision == "needs_review":
        specs.append({
            "kind": "needs_review_inspection",
            "title": f"Review stable loop decision: {loop_id}",
            "description": (
                "Inspect this stable-loop record, finish any required checklist items, "
                "add operator notes, then choose keep, fix_forward, or rollback."
            ),
            "priority": "medium",
            "risk": "low",
            "requires_approval": False,
            "command": f"python conscious_agent/main.py --show-stable-loop {loop_id} --stable-loop-full",
            "next_action": f"python conscious_agent/main.py --show-stable-loop-operator-notes {loop_id}",
            "metadata": {**base_metadata, "followup_kind": "needs_review_inspection"},
        })
        return specs

    if decision == "fix_forward":
        specs.append({
            "kind": "fix_forward_plan",
            "title": f"Plan fix-forward work after stable loop {loop_id}",
            "description": (
                "The stable-loop final decision is fix_forward. Inspect the audit, operator notes, "
                "and affected tasks/patches, then create a targeted patch or task plan to fix forward."
            ),
            "priority": "high",
            "risk": "medium",
            "requires_approval": True,
            "command": f"python conscious_agent/main.py --show-stable-loop-audit {loop_id}",
            "next_action": f"python conscious_agent/main.py --show-stable-loop-operator-notes {loop_id}",
            "metadata": {**base_metadata, "followup_kind": "fix_forward_plan"},
        })
        return specs

    if decision == "rollback":
        specs.append({
            "kind": "rollback_review",
            "title": f"Review rollback plan for stable loop {loop_id}",
            "description": (
                "The stable-loop final decision is rollback. Review the audit rollback notes and "
                "confirm which patch or task change should be rolled back before any live rollback command is run."
            ),
            "priority": "critical",
            "risk": "medium",
            "requires_approval": True,
            "command": f"python conscious_agent/main.py --show-stable-loop-audit {loop_id} --stable-loop-audit-full",
            "next_action": f"python conscious_agent/main.py --show-stable-loop-operator-notes {loop_id}",
            "metadata": {**base_metadata, "followup_kind": "rollback_review"},
        })
        patches = audit.get("patches") if isinstance(audit.get("patches"), list) else []
        for patch in patches:
            if not isinstance(patch, dict):
                continue
            patch_id = str(patch.get("id") or "").strip()
            dry_command = str(patch.get("rollback_dry_run_command") or "").strip()
            if not patch_id or not dry_command:
                continue
            specs.append({
                "kind": f"rollback_dry_run_{_slug(patch_id, 'patch')}",
                "title": f"Dry-run rollback for patch {patch_id}",
                "description": (
                    f"Preview rollback for patch {patch_id} linked to stable loop {loop_id}. "
                    "Only run the live rollback after inspecting the dry-run output and approval state."
                ),
                "priority": "critical",
                "risk": "medium",
                "requires_approval": True,
                "command": dry_command,
                "next_action": str(patch.get("rollback_command") or "").strip(),
                "metadata": {
                    **base_metadata,
                    "followup_kind": f"rollback_dry_run_{_slug(patch_id, 'patch')}",
                    "patch_id": patch_id,
                    "rollback_command": str(patch.get("rollback_command") or ""),
                    "rollback_dry_run_command": dry_command,
                },
            })
        return specs

    return specs


def _record_followups_on_loop(loop: dict[str, Any], task_ids: list[str], existing_ids: list[str], decision: str, dry_run: bool) -> None:
    if dry_run:
        return
    if not task_ids and not existing_ids:
        return
    notes = ensure_operator_notes(loop, save=False)
    current = notes.get("decision_followups") if isinstance(notes.get("decision_followups"), list) else []
    seen = {str(item.get("task_id") or "") for item in current if isinstance(item, dict)}
    now = _now()
    for task_id in task_ids + existing_ids:
        if not task_id or task_id in seen:
            continue
        current.append({
            "task_id": task_id,
            "decision": decision,
            "created_at": now,
            "source": FOLLOWUP_SOURCE,
        })
        seen.add(task_id)
    notes["decision_followups"] = current
    notes["updated_at"] = now
    loop["operator_notes"] = notes
    save_stable_loop(loop)


def plan_stable_loop_followups(loop_id: str = "latest", force: bool = False) -> StableLoopFollowupResult:
    loop = load_stable_loop(loop_id)
    if not loop:
        return StableLoopFollowupResult(False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")
    resolved = str(loop.get("id") or loop_id)
    decision = final_decision_for_loop(loop)
    if decision not in FOLLOWUP_ACTION_DECISIONS and not force:
        return StableLoopFollowupResult(
            True,
            dry_run=True,
            loop_id=resolved,
            decision=decision,
            planned_followups=[],
            created_task_ids=[],
            existing_task_ids=[task.get("id", "") for task in _existing_followup_tasks(resolved)],
            message=f"No follow-up tasks are required for decision: {decision_label(decision)}.",
            loop=loop,
        )
    specs = _build_followup_specs(loop, decision)
    existing_ids: list[str] = []
    planned: list[dict[str, Any]] = []
    for spec in specs:
        kind = str(spec.get("kind") or "")
        existing = _existing_followup_tasks(resolved, decision=decision, followup_kind=kind)
        if existing:
            existing_ids.extend(str(task.get("id")) for task in existing if task.get("id"))
            continue
        planned.append(spec)
    return StableLoopFollowupResult(
        True,
        dry_run=True,
        loop_id=resolved,
        decision=decision,
        planned_followups=planned,
        created_task_ids=[],
        existing_task_ids=sorted(set(existing_ids)),
        message=f"Planned {len(planned)} follow-up task(s) for {decision_label(decision)} decision.",
        loop=loop,
    )


def create_stable_loop_followup_tasks(
    loop_id: str = "latest",
    dry_run: bool = True,
    force: bool = False,
    reviewer: str = "operator",
) -> StableLoopFollowupResult:
    planned = plan_stable_loop_followups(loop_id=loop_id, force=force)
    if not planned.ok:
        return planned
    planned.dry_run = dry_run
    if dry_run:
        planned.message = f"Dry-run would create {len(planned.planned_followups or [])} follow-up task(s)."
        return planned

    loop = planned.loop or load_stable_loop(loop_id)
    if not loop:
        return StableLoopFollowupResult(False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")

    created_ids: list[str] = []
    errors: list[str] = []
    for spec in planned.planned_followups or []:
        metadata = spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {}
        metadata.update({
            "created_at": _now(),
            "created_by": reviewer or "operator",
        })
        result = add_task(
            title=str(spec.get("title") or "Stable loop follow-up task"),
            description=str(spec.get("description") or ""),
            priority=str(spec.get("priority") or "medium"),
            status="planned",
            project=str(loop.get("project_id") or "eidolon"),
            command=str(spec.get("command") or ""),
            next_action=str(spec.get("next_action") or ""),
            risk=str(spec.get("risk") or "low"),
            source=FOLLOWUP_SOURCE,
            source_id=str(loop.get("id") or ""),
            source_category=FOLLOWUP_CATEGORY,
            requires_approval=bool(spec.get("requires_approval", False)),
            metadata=metadata,
        )
        if result.ok and result.task:
            task_id = str(result.task.get("id") or "")
            created_ids.append(task_id)
            update_task_fields(
                task_id,
                metadata={
                    "stable_loop_followup_created_at": _now(),
                    "stable_loop_followup_reviewer": reviewer or "operator",
                },
            )
        else:
            errors.append(result.error or result.message or "Unknown task creation error")

    existing_ids = planned.existing_task_ids or []
    _record_followups_on_loop(loop, created_ids, existing_ids, planned.decision, dry_run=False)
    ok = not errors
    return StableLoopFollowupResult(
        ok,
        dry_run=False,
        loop_id=planned.loop_id,
        decision=planned.decision,
        planned_followups=planned.planned_followups,
        created_task_ids=created_ids,
        existing_task_ids=existing_ids,
        message=f"Created {len(created_ids)} follow-up task(s); {len(existing_ids)} already existed.",
        error="; ".join(errors),
        loop=load_stable_loop(planned.loop_id),
    )


def stable_loop_followup_summary(
    decision_filter: str = "action_required",
    include_archived: bool = False,
    include_live: bool = True,
) -> dict[str, Any]:
    token = normalize_decision_filter(decision_filter or "action_required")
    loops = [
        loop for loop in list_stable_loops()
        if stable_loop_matches_decision_filter(loop, token, include_archived=include_archived, include_live=include_live)
    ]
    rows: list[dict[str, Any]] = []
    missing_count = 0
    existing_count = 0
    for loop in loops:
        plan = plan_stable_loop_followups(str(loop.get("id") or ""))
        planned_count = len(plan.planned_followups or [])
        existing_ids = plan.existing_task_ids or []
        missing_count += planned_count
        existing_count += len(existing_ids)
        rows.append({
            "loop_id": str(loop.get("id") or ""),
            "decision": plan.decision,
            "decision_label": decision_label(plan.decision),
            "planned_count": planned_count,
            "existing_count": len(existing_ids),
            "existing_task_ids": existing_ids,
            "recommended_action": stable_loop_decision_row(loop).get("recommended_action", ""),
        })
    return {
        "version": FOLLOWUP_TASK_VERSION,
        "generated_at": _now(),
        "decision_filter": token,
        "decision_filter_label": DECISION_FILTER_LABELS.get(token, token),
        "include_archived": include_archived,
        "include_live": include_live,
        "loop_count": len(loops),
        "missing_followup_count": missing_count,
        "existing_followup_count": existing_count,
        "rows": rows,
    }


def create_stable_loop_followups_for_decisions(
    decision_filter: str = "action_required",
    dry_run: bool = True,
    include_archived: bool = False,
    include_live: bool = True,
    limit: int = 25,
    force: bool = False,
    reviewer: str = "operator",
) -> StableLoopFollowupBatchResult:
    token = normalize_decision_filter(decision_filter or "action_required")
    loops = [
        loop for loop in list_stable_loops()
        if stable_loop_matches_decision_filter(loop, token, include_archived=include_archived, include_live=include_live)
    ][: max(1, min(int(limit or 25), 250))]
    results: list[dict[str, Any]] = []
    created_ids: list[str] = []
    existing_ids: list[str] = []
    selected_ids: list[str] = []
    for loop in loops:
        loop_id = str(loop.get("id") or "")
        if not loop_id:
            continue
        selected_ids.append(loop_id)
        result = create_stable_loop_followup_tasks(loop_id, dry_run=dry_run, force=force, reviewer=reviewer)
        data = result.to_dict()
        results.append(data)
        created_ids.extend(result.created_task_ids or [])
        existing_ids.extend(result.existing_task_ids or [])
    return StableLoopFollowupBatchResult(
        ok=all(bool(item.get("ok")) for item in results) if results else True,
        dry_run=dry_run,
        decision_filter=token,
        selected_loop_ids=selected_ids,
        created_task_ids=created_ids,
        existing_task_ids=sorted(set(existing_ids)),
        results=results,
        message=(
            f"Dry-run planned follow-up tasks for {len(selected_ids)} stable-loop decision record(s)."
            if dry_run else f"Created {len(created_ids)} follow-up task(s) for {len(selected_ids)} stable-loop decision record(s)."
        ),
    )


def followup_result_text(result: StableLoopFollowupResult | dict[str, Any], full: bool = False) -> str:
    data = result.to_dict() if isinstance(result, StableLoopFollowupResult) else result
    lines = [
        "# Stable loop decision follow-up tasks",
        "",
        f"OK: {data.get('ok')}",
        f"Dry-run: {data.get('dry_run')}",
        f"Loop: {data.get('loop_id', '')}",
        f"Decision: {decision_label(str(data.get('decision') or 'undecided'))}",
        f"Created tasks: {len(data.get('created_task_ids') or [])}",
        f"Existing tasks: {len(data.get('existing_task_ids') or [])}",
        f"Planned tasks: {len(data.get('planned_followups') or [])}",
        f"Message: {data.get('message', '')}",
    ]
    if data.get("error"):
        lines.append(f"Error: {data.get('error')}")
    if data.get("created_task_ids"):
        lines.extend(["", "Created task IDs:"])
        lines.extend(f"- {task_id}" for task_id in data.get("created_task_ids") or [])
    if data.get("existing_task_ids"):
        lines.extend(["", "Existing task IDs:"])
        lines.extend(f"- {task_id}" for task_id in data.get("existing_task_ids") or [])
    planned = data.get("planned_followups") if isinstance(data.get("planned_followups"), list) else []
    if planned:
        lines.extend(["", "Planned follow-ups:"])
        for item in planned:
            if not isinstance(item, dict):
                continue
            lines.append(f"- {item.get('title')} | priority={item.get('priority')} | risk={item.get('risk')} | kind={item.get('kind')}")
            if item.get("command"):
                lines.append(f"  command: {item.get('command')}")
    if full:
        import json
        lines.extend(["", "## Raw follow-up result", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()


def followup_batch_text(result: StableLoopFollowupBatchResult | dict[str, Any], full: bool = False) -> str:
    data = result.to_dict() if isinstance(result, StableLoopFollowupBatchResult) else result
    lines = [
        "# Stable loop decision follow-up batch",
        "",
        f"OK: {data.get('ok')}",
        f"Dry-run: {data.get('dry_run')}",
        f"Decision filter: {DECISION_FILTER_LABELS.get(str(data.get('decision_filter') or ''), data.get('decision_filter'))}",
        f"Selected loops: {len(data.get('selected_loop_ids') or [])}",
        f"Created tasks: {len(data.get('created_task_ids') or [])}",
        f"Existing tasks: {len(data.get('existing_task_ids') or [])}",
        f"Message: {data.get('message', '')}",
    ]
    if data.get("created_task_ids"):
        lines.extend(["", "Created task IDs:"])
        lines.extend(f"- {task_id}" for task_id in data.get("created_task_ids") or [])
    if full:
        import json
        lines.extend(["", "## Raw batch result", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()


def followup_summary_text(summary: dict[str, Any] | None = None, full: bool = False) -> str:
    data = summary or stable_loop_followup_summary()
    lines = [
        "# Stable loop follow-up task summary",
        "",
        f"Version: {data.get('version', FOLLOWUP_TASK_VERSION)}",
        f"Generated: {data.get('generated_at', '')}",
        f"Decision filter: {data.get('decision_filter_label', data.get('decision_filter', 'action_required'))}",
        f"Matching loops: {data.get('loop_count', 0)}",
        f"Missing follow-up tasks: {data.get('missing_followup_count', 0)}",
        f"Existing follow-up tasks: {data.get('existing_followup_count', 0)}",
    ]
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    if rows:
        lines.extend(["", "## Matching stable loops"])
        for row in rows[:25]:
            lines.append(
                f"- {row.get('loop_id')} | {row.get('decision_label')} | "
                f"planned={row.get('planned_count')} | existing={row.get('existing_count')} | {row.get('recommended_action')}"
            )
    if full:
        import json
        lines.extend(["", "## Raw summary", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_stable_loop_followup_summary(
    decision_filter: str = "action_required",
    include_archived: bool = False,
    include_live: bool = True,
    full: bool = False,
) -> None:
    print(followup_summary_text(stable_loop_followup_summary(decision_filter, include_archived, include_live), full=full))


def print_create_stable_loop_followups(
    loop_id: str = "latest",
    dry_run: bool = True,
    force: bool = False,
    full: bool = False,
) -> None:
    result = create_stable_loop_followup_tasks(loop_id=loop_id, dry_run=dry_run, force=force)
    print(followup_result_text(result, full=full))


def print_create_stable_loop_followups_for_decisions(
    decision_filter: str = "action_required",
    dry_run: bool = True,
    include_archived: bool = False,
    include_live: bool = True,
    limit: int = 25,
    force: bool = False,
    full: bool = False,
) -> None:
    result = create_stable_loop_followups_for_decisions(
        decision_filter=decision_filter,
        dry_run=dry_run,
        include_archived=include_archived,
        include_live=include_live,
        limit=limit,
        force=force,
    )
    print(followup_batch_text(result, full=full))
