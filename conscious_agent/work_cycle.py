from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from memory import store_memory
from paths import DATA_DIR
from patch_suggester import list_patch_proposals, load_patch_proposal
from work_queue import (
    WorkItem,
    add_work_item,
    find_work_item,
    get_next_work_item,
    list_work_items,
    summarize_queue,
)
from task_work_executor import execute_task_work_item, task_work_execution_text
from task_patch_bridge import create_patch_followup_tasks


WORK_CYCLES_DIR = DATA_DIR / "work_cycles"
DEFAULT_PROJECT_ID = "eidolon"


@dataclass
class WorkCycleResult:
    ok: bool
    cycle_id: str = ""
    project_id: str = DEFAULT_PROJECT_ID
    dry_run: bool = True
    steps_requested: int = 1
    steps_completed: int = 0
    stopped_reason: str = ""
    message: str = ""
    error: str = ""
    created_work_ids: list[str] | None = None
    created_followup_work_ids: list[str] | None = None
    executed_work_ids: list[str] | None = None
    patch_ids: list[str] | None = None
    events: list[dict[str, Any]] | None = None
    summary_before: dict[str, Any] | None = None
    summary_after: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_storage() -> None:
    WORK_CYCLES_DIR.mkdir(parents=True, exist_ok=True)
    readme = WORK_CYCLES_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Work cycles\n\nSaved v5.0 supervised autonomous work-cycle records.\n",
            encoding="utf-8",
        )


def _cycle_path(cycle_id: str) -> Path:
    return WORK_CYCLES_DIR / f"{cycle_id}.json"


def save_work_cycle(record: dict[str, Any]) -> None:
    _ensure_storage()
    with _cycle_path(record["id"]).open("w", encoding="utf-8") as file:
        json.dump(record, file, indent=2)


def load_work_cycle(cycle_id: str) -> dict[str, Any] | None:
    resolved = resolve_work_cycle_id(cycle_id)
    if not resolved:
        return None
    path = _cycle_path(resolved)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_work_cycles() -> list[dict[str, Any]]:
    _ensure_storage()
    cycles: list[dict[str, Any]] = []
    for path in sorted(WORK_CYCLES_DIR.glob("*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            cycles.append(data)
    return cycles


def resolve_work_cycle_id(cycle_id: str) -> str:
    token = (cycle_id or "").strip()
    if token.lower() not in {"latest", "last"}:
        return token
    cycles = list_work_cycles()
    return str(cycles[0].get("id", "")) if cycles else ""


def _short_item(item: WorkItem | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "id": item.id,
        "title": item.title,
        "status": item.status,
        "project_id": item.project_id,
        "priority": item.priority,
        "risk": item.risk,
        "requires_approval": item.requires_approval,
        "metadata": item.metadata or {},
    }


def _patch_followups_already_exist(patch_id: str) -> bool:
    for item in list_work_items(include_done=True):
        metadata = item.metadata or {}
        if metadata.get("patch_id") != patch_id:
            continue
        title = item.title.lower()
        relationship = str(metadata.get("patch_relationship") or "").lower()
        if "patch_followup" in relationship or title.startswith(("review patch", "apply patch", "run tests after patch")):
            return True
    proposal = load_patch_proposal(patch_id)
    linked = proposal.get("linked_work_items") if proposal else []
    if isinstance(linked, list):
        return any(
            isinstance(entry, dict) and entry.get("relationship") == "patch_followup"
            for entry in linked
        )
    return False


def _unfollowed_patch_ids(limit: int = 5) -> list[str]:
    ids: list[str] = []
    for patch in list_patch_proposals():
        patch_id = str(patch.get("id") or "").strip()
        if not patch_id:
            continue
        if patch.get("status") != "proposed":
            continue
        if _patch_followups_already_exist(patch_id):
            continue
        ids.append(patch_id)
        if len(ids) >= limit:
            break
    return ids


def _seed_definitions(project_id: str) -> list[dict[str, Any]]:
    return [
        {
            "title": "Review README_NEXT_STEPS.md for the next safe Eidolon step",
            "description": "Inspect the project README and summarize the next safe action. This is read-only and gives the cycle context before making changes.",
            "project_id": project_id,
            "priority": 6,
            "risk": "low",
            "source": "system",
            "requires_approval": False,
            "metadata": {
                "action_type": "review_file",
                "target_file": "README_NEXT_STEPS.md",
                "cycle_seed": True,
            },
        },
        {
            "title": "Run general Eidolon test workflow",
            "description": "Run the approved default test workflow through the task work executor.",
            "project_id": project_id,
            "priority": 5,
            "risk": "low",
            "source": "system",
            "requires_approval": False,
            "metadata": {
                "action_type": "test_project",
                "cycle_seed": True,
            },
        },
    ]


def _create_seed_items(project_id: str, dry_run: bool) -> tuple[list[str], list[dict[str, Any]]]:
    definitions = _seed_definitions(project_id)
    if dry_run:
        return [], definitions

    created_ids: list[str] = []
    for definition in definitions:
        item = add_work_item(**definition)
        created_ids.append(item.id)
    return created_ids, definitions


def run_supervised_work_cycle(
    project_id: Optional[str] = None,
    max_steps: int = 1,
    dry_run: bool = True,
    use_ai: bool = True,
    approve_work_execution: bool = False,
    seed_if_empty: bool = True,
    auto_create_patch_followups: bool = True,
) -> WorkCycleResult:
    project = (project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    max_steps = max(1, min(int(max_steps or 1), 10))
    cycle_id = f"workcycle_{_timestamp_id()}"
    events: list[dict[str, Any]] = []
    created_work_ids: list[str] = []
    created_followup_work_ids: list[str] = []
    executed_work_ids: list[str] = []
    patch_ids: list[str] = []
    stopped_reason = ""
    ok = True
    error = ""

    summary_before = summarize_queue(project_id=project)
    events.append({"type": "observe_queue", "at": _now(), "summary": summary_before})

    if auto_create_patch_followups:
        pending_patch_ids = _unfollowed_patch_ids()
        if pending_patch_ids:
            events.append({
                "type": "patch_followup_scan",
                "at": _now(),
                "patch_ids": pending_patch_ids,
                "dry_run": dry_run,
            })
        for patch_id in pending_patch_ids:
            if dry_run:
                continue
            followups = create_patch_followup_tasks(patch_id, project_id=project)
            if followups.ok:
                ids = followups.created_task_ids or followups.created_work_ids or []
                created_followup_work_ids.extend(ids)
                events.append({
                    "type": "patch_followups_created",
                    "at": _now(),
                    "patch_id": patch_id,
                    "created_work_ids": ids,
                })
            else:
                ok = False
                error = followups.error
                events.append({
                    "type": "patch_followup_failed",
                    "at": _now(),
                    "patch_id": patch_id,
                    "error": followups.error,
                })
                stopped_reason = "patch_followup_failed"
                break

    next_item = get_next_work_item(project_id=project)
    if not next_item and seed_if_empty and not stopped_reason:
        ids, definitions = _create_seed_items(project, dry_run=dry_run)
        created_work_ids.extend(ids)
        events.append({
            "type": "seed_queue",
            "at": _now(),
            "dry_run": dry_run,
            "created_work_ids": ids,
            "proposed_items": definitions if dry_run else [],
        })
        if dry_run:
            stopped_reason = "dry_run_seed_preview"
        else:
            next_item = get_next_work_item(project_id=project)

    steps_completed = 0
    if not stopped_reason:
        for step_index in range(max_steps):
            item = get_next_work_item(project_id=project)
            if not item:
                stopped_reason = "no_pending_work"
                break

            execution = execute_task_work_item(
                item.id,
                dry_run=dry_run,
                allow_approval_required=approve_work_execution,
                use_ai=use_ai,
            )
            executed_work_ids.append(item.id)
            steps_completed += 1
            event = {
                "type": "execute_task_work",
                "at": _now(),
                "step": step_index + 1,
                "work_item": _short_item(item),
                "execution": execution.to_dict(),
            }
            events.append(event)

            patch_id = ""
            if execution.metadata:
                patch_id = str(execution.metadata.get("patch_id") or "")
            refreshed_item = find_work_item(item.id)
            if not patch_id and refreshed_item and isinstance(refreshed_item.metadata, dict):
                patch_id = str(refreshed_item.metadata.get("patch_id") or "")
            if patch_id:
                patch_ids.append(patch_id)

            if patch_id and auto_create_patch_followups and not dry_run:
                followups = create_patch_followup_tasks(patch_id, project_id=project)
                if followups.ok:
                    ids = followups.created_task_ids or followups.created_work_ids or []
                    created_followup_work_ids.extend(ids)
                    events.append({
                        "type": "patch_followups_created",
                        "at": _now(),
                        "patch_id": patch_id,
                        "created_work_ids": ids,
                    })
                else:
                    ok = False
                    error = followups.error
                    stopped_reason = "patch_followup_failed"
                    events.append({
                        "type": "patch_followup_failed",
                        "at": _now(),
                        "patch_id": patch_id,
                        "error": followups.error,
                    })
                    break

            if dry_run:
                stopped_reason = "dry_run_preview_complete"
                break

            if execution.blocked:
                stopped_reason = "task_blocked"
                break
            if not execution.ok:
                ok = False
                error = execution.error
                stopped_reason = "task_failed"
                break

        if not stopped_reason:
            stopped_reason = "step_limit_reached"

    summary_after = summarize_queue(project_id=project)
    message = _cycle_message(dry_run, steps_completed, created_work_ids, created_followup_work_ids, stopped_reason)

    record = {
        "id": cycle_id,
        "version": "5.7",
        "created_at": _now(),
        "project_id": project,
        "dry_run": dry_run,
        "use_ai": use_ai,
        "approve_work_execution": approve_work_execution,
        "seed_if_empty": seed_if_empty,
        "auto_create_patch_followups": auto_create_patch_followups,
        "steps_requested": max_steps,
        "steps_completed": steps_completed,
        "stopped_reason": stopped_reason,
        "ok": ok,
        "error": error,
        "message": message,
        "created_work_ids": created_work_ids,
        "created_task_ids": created_work_ids,
        "created_followup_work_ids": created_followup_work_ids,
        "created_followup_task_ids": created_followup_work_ids,
        "executed_work_ids": executed_work_ids,
        "executed_task_ids": executed_work_ids,
        "patch_ids": patch_ids,
        "summary_before": summary_before,
        "summary_after": summary_after,
        "events": events,
    }
    save_work_cycle(record)

    store_memory({
        "type": "supervised_work_cycle_event",
        "content": f"Ran supervised work cycle {cycle_id}. dry_run={dry_run} steps={steps_completed} stopped={stopped_reason}",
        "source": "work_cycle",
        "cycle_id": cycle_id,
        "project_id": project,
        "ok": ok,
        "dry_run": dry_run,
        "stopped_reason": stopped_reason,
    })

    return WorkCycleResult(
        ok=ok,
        cycle_id=cycle_id,
        project_id=project,
        dry_run=dry_run,
        steps_requested=max_steps,
        steps_completed=steps_completed,
        stopped_reason=stopped_reason,
        message=message,
        error=error,
        created_work_ids=created_work_ids,
        created_followup_work_ids=created_followup_work_ids,
        executed_work_ids=executed_work_ids,
        patch_ids=patch_ids,
        events=events,
        summary_before=summary_before,
        summary_after=summary_after,
    )


def _cycle_message(
    dry_run: bool,
    steps_completed: int,
    created_work_ids: list[str],
    created_followup_work_ids: list[str],
    stopped_reason: str,
) -> str:
    mode = "Dry-run preview" if dry_run else "Work cycle"
    parts = [f"{mode} finished after {steps_completed} step(s)."]
    if created_work_ids:
        parts.append(f"Created {len(created_work_ids)} seed task(s).")
    if created_followup_work_ids:
        parts.append(f"Created {len(created_followup_work_ids)} patch follow-up task(s).")
    if stopped_reason:
        parts.append(f"Stopped: {stopped_reason}.")
    return " ".join(parts)


def work_cycle_text(record_or_result: dict[str, Any] | WorkCycleResult, full: bool = False) -> str:
    if isinstance(record_or_result, WorkCycleResult):
        data = record_or_result.to_dict()
    else:
        data = record_or_result

    lines = [
        "# Supervised autonomous task cycle",
        "",
        f"Cycle: {data.get('cycle_id') or data.get('id', '')}",
        f"Project: {data.get('project_id', '')}",
        f"Version: {data.get('version', '5.7')}",
        f"Dry run: {data.get('dry_run')}",
        f"OK: {data.get('ok')}",
        f"Steps: {data.get('steps_completed', 0)} / {data.get('steps_requested', 0)}",
        f"Stopped: {data.get('stopped_reason', '')}",
    ]
    if data.get("message"):
        lines.append(f"Message: {data.get('message')}")
    if data.get("error"):
        lines.append(f"Error: {data.get('error')}")

    def _join_ids(label: str, ids: Any) -> None:
        if ids:
            lines.append(f"{label}: {', '.join(str(item) for item in ids)}")

    _join_ids("Created tasks", data.get("created_task_ids") or data.get("created_work_ids"))
    _join_ids("Created follow-up tasks", data.get("created_followup_task_ids") or data.get("created_followup_work_ids"))
    _join_ids("Executed tasks", data.get("executed_task_ids") or data.get("executed_work_ids"))
    _join_ids("Patches", data.get("patch_ids"))

    events = data.get("events") or []
    if events:
        lines.extend(["", "## Events"])
        for event in events[:20]:
            event_type = event.get("type", "event")
            lines.append(f"- {event_type} at {event.get('at', '')}")
            if event_type in {"execute_task_work", "execute_work_item"}:
                execution = event.get("execution") or {}
                item = event.get("work_item") or {}
                lines.append(f"  - task: {item.get('id', '')} | {item.get('title', '')}")
                lines.append(f"  - action: {execution.get('action_type', '')} | ok={execution.get('ok')} | blocked={execution.get('blocked')}")
                if execution.get("error"):
                    lines.append(f"  - error: {execution.get('error')}")
            elif event_type == "seed_queue" and event.get("dry_run"):
                proposed = event.get("proposed_items") or []
                for item in proposed:
                    lines.append(f"  - proposed: {item.get('title', '')}")
            elif event.get("patch_id"):
                lines.append(f"  - patch: {event.get('patch_id')}")

    if full:
        lines.extend(["", "## Raw record", json.dumps(data, indent=2, default=str)])

    return "\n".join(lines).strip()


def print_work_cycle(
    project_id: Optional[str] = None,
    max_steps: int = 1,
    dry_run: bool = True,
    use_ai: bool = True,
    approve_work_execution: bool = False,
    seed_if_empty: bool = True,
    auto_create_patch_followups: bool = True,
    full: bool = False,
) -> None:
    result = run_supervised_work_cycle(
        project_id=project_id,
        max_steps=max_steps,
        dry_run=dry_run,
        use_ai=use_ai,
        approve_work_execution=approve_work_execution,
        seed_if_empty=seed_if_empty,
        auto_create_patch_followups=auto_create_patch_followups,
    )
    print(work_cycle_text(result, full=full))


def print_work_cycles(limit: int = 25) -> None:
    cycles = list_work_cycles()[: max(1, min(limit, 100))]
    if not cycles:
        print("No work cycles found.")
        return
    for cycle in cycles:
        print(
            f"{cycle.get('id')} | ok={cycle.get('ok')} | dry_run={cycle.get('dry_run')} | "
            f"steps={cycle.get('steps_completed')}/{cycle.get('steps_requested')} | stopped={cycle.get('stopped_reason')}"
        )


def print_saved_work_cycle(cycle_id: str = "latest", full: bool = False) -> None:
    cycle = load_work_cycle(cycle_id)
    if not cycle:
        print(f"Work cycle not found: {cycle_id}")
        return
    print(work_cycle_text(cycle, full=full))
