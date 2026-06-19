from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from command_runner import run_approved_command
from memory import store_memory
from patch_applier import apply_patch, rollback_patch
from patch_suggester import load_patch_proposal, resolve_patch_id
from paths import DATA_DIR
from task_result_evaluator import apply_task_evaluation, get_task_evaluation, resolve_task_evaluation_id


APPROVALS_DIR = DATA_DIR / "approvals"
APPROVALS_README = APPROVALS_DIR / "README.md"
VALID_STATUSES = {"pending", "approved", "rejected", "failed"}
VALID_ACTION_TYPES = {"apply_patch", "rollback_patch", "apply_task_evaluation", "run_command"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 64) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return (cleaned or "approval")[:max_length].strip("-") or "approval"


def _ensure_storage() -> None:
    APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
    if not APPROVALS_README.exists():
        APPROVALS_README.write_text(
            "Saved approval requests. Pending items require Marcus to inspect, approve, dry-run, execute, or reject them.\n",
            encoding="utf-8",
        )


def _new_approval_id(action_type: str, object_id: str = "") -> str:
    object_slug = _slug(object_id, max_length=40)
    return f"approval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(action_type, 24)}_{object_slug}"


def _approval_path(approval_id: str) -> Path:
    _ensure_storage()
    return APPROVALS_DIR / f"{approval_id}.json"


def _save_approval(approval: dict[str, Any]) -> None:
    _ensure_storage()
    with _approval_path(approval["id"]).open("w", encoding="utf-8") as file:
        json.dump(approval, file, indent=2)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_approvals(status: str = "", include_closed: bool = True) -> list[dict[str, Any]]:
    _ensure_storage()
    approvals: list[dict[str, Any]] = []
    for path in APPROVALS_DIR.glob("*.json"):
        data = _load_json_file(path)
        if not data:
            continue
        if status and data.get("status") != status:
            continue
        if not include_closed and data.get("status") != "pending":
            continue
        approvals.append(data)
    return sorted(approvals, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_approval_id(approval_id: str) -> str:
    token = (approval_id or "").strip()
    token_lower = token.lower()
    approvals = list_approvals()

    if token_lower in {"latest", "last"}:
        return approvals[0].get("id", "") if approvals else ""

    alias_status = {
        "latest-pending": "pending",
        "last-pending": "pending",
        "latest-approved": "approved",
        "last-approved": "approved",
        "latest-rejected": "rejected",
        "last-rejected": "rejected",
        "latest-failed": "failed",
        "last-failed": "failed",
    }

    if token_lower in alias_status:
        matches = [item for item in approvals if item.get("status") == alias_status[token_lower]]
        return matches[0].get("id", "") if matches else ""

    if token_lower.startswith("latest-"):
        desired_type = token_lower.replace("latest-", "", 1).replace("-", "_")
        matches = [item for item in approvals if item.get("action_type") == desired_type]
        return matches[0].get("id", "") if matches else ""

    return token


def get_approval(approval_id: str) -> dict[str, Any] | None:
    resolved = resolve_approval_id(approval_id)
    if not resolved:
        return None
    path = _approval_path(resolved)
    if path.exists():
        return _load_json_file(path)
    for approval in list_approvals():
        if approval.get("id") == resolved:
            return approval
    return None


def _find_duplicate_pending(action_type: str, object_id: str = "", command: str = "") -> dict[str, Any] | None:
    for approval in list_approvals(status="pending"):
        if approval.get("action_type") != action_type:
            continue
        if object_id and approval.get("object_id") == object_id:
            return approval
        if command and approval.get("command") == command:
            return approval
    return None


def create_approval(
    action_type: str,
    summary: str,
    object_id: str = "",
    command: str = "",
    risk_level: str = "medium",
    source: str = "manual",
    reason: str = "",
    metadata: dict[str, Any] | None = None,
    dedupe: bool = True,
) -> dict[str, Any]:
    action_type = action_type.strip().lower()
    if action_type not in VALID_ACTION_TYPES:
        raise ValueError(f"Unsupported approval action type: {action_type}")

    if dedupe:
        existing = _find_duplicate_pending(action_type, object_id=object_id, command=command)
        if existing:
            existing["deduped_at"] = _now()
            existing.setdefault("notes", []).append(f"Duplicate approval request avoided at {_now()} from {source}.")
            _save_approval(existing)
            return existing

    approval = {
        "id": _new_approval_id(action_type, object_id or command or summary),
        "type": "approval_request",
        "created_at": _now(),
        "updated_at": _now(),
        "status": "pending",
        "action_type": action_type,
        "summary": summary,
        "reason": reason,
        "object_id": object_id,
        "command": command,
        "risk_level": risk_level,
        "source": source,
        "metadata": metadata or {},
        "notes": [],
        "result": {},
        "useful_commands": [],
    }
    approval["useful_commands"] = _approval_commands(approval)
    _save_approval(approval)

    store_memory({
        "type": "approval_request_created",
        "content": f"Created approval request {approval['id']} for {action_type}: {summary}",
        "source": "approval_manager",
        "approval_id": approval["id"],
        "action_type": action_type,
        "object_id": object_id,
        "status": "pending",
    })
    return approval


def create_approval_from_dev_step(
    step: str,
    object_id: str,
    source: str = "dev_cycle",
    reason: str = "",
) -> dict[str, Any] | None:
    step = (step or "").strip()
    object_id = (object_id or "").strip()

    if step == "review-proposed-patch" and object_id:
        patch_id = resolve_patch_id(object_id, status="proposed") or object_id
        patch = load_patch_proposal(patch_id) or {}
        target = patch.get("target_file", "unknown file")
        return create_approval(
            action_type="apply_patch",
            object_id=patch_id,
            summary=f"Apply proposed patch {patch_id} to {target}",
            command=f"python conscious_agent/main.py --apply-patch {patch_id}",
            risk_level=patch.get("risk_level", "medium"),
            source=source,
            reason=reason or "A proposed patch needs explicit approval before writing files.",
            metadata={"target_file": target},
        )

    if step == "awaiting-rollback-approval" and object_id:
        patch_id = resolve_patch_id(object_id, status="applied") or object_id
        patch = load_patch_proposal(patch_id) or {}
        target = patch.get("target_file", "unknown file")
        return create_approval(
            action_type="rollback_patch",
            object_id=patch_id,
            summary=f"Rollback applied patch {patch_id} for {target}",
            command=f"python conscious_agent/main.py --rollback-patch {patch_id}",
            risk_level="medium",
            source=source,
            reason=reason or "A review recommended rollback, which requires explicit approval.",
            metadata={"target_file": target},
        )

    return None


def _approval_commands(approval: dict[str, Any]) -> list[str]:
    approval_id = approval.get("id", "latest-pending")
    commands = [
        f"python conscious_agent/main.py --show-approval {approval_id}",
        f"python conscious_agent/main.py --approve {approval_id} --dry-run",
        f"python conscious_agent/main.py --approve {approval_id}",
        f"python conscious_agent/main.py --reject {approval_id} --approval-note \"Reason here\"",
    ]
    return commands


def _result_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    if isinstance(result, dict):
        return dict(result)
    return {"value": str(result)}


def _linked_task_id(approval: dict[str, Any]) -> str:
    metadata = approval.get("metadata") if isinstance(approval.get("metadata"), dict) else {}
    task_id = str(metadata.get("task_id") or "").strip()
    object_id = str(approval.get("object_id") or "").strip()
    if task_id:
        return task_id
    if object_id.startswith("task_"):
        return object_id
    command = str(approval.get("command") or "")
    marker = "--execute-task-work-id"
    if marker in command:
        parts = command.split()
        try:
            return parts[parts.index(marker) + 1]
        except (ValueError, IndexError):
            return ""
    return ""


def _sync_linked_task_approval(
    approval: dict[str, Any],
    approval_status: str,
    result: dict[str, Any] | None = None,
    note: str = "",
) -> None:
    task_id = _linked_task_id(approval)
    if not task_id:
        return
    metadata = {
        "approval_id": approval.get("id", ""),
        "approval_status": approval_status,
        "approval_action_type": approval.get("action_type", ""),
    }
    if result is not None:
        metadata["approval_result"] = result
    try:
        from task_queue import update_task_fields

        if approval_status == "rejected":
            update_task_fields(
                task_id,
                status="blocked",
                blocked_reason=f"Approval rejected: {note or approval.get('id', '')}",
                metadata=metadata,
            )
        elif approval_status == "failed":
            update_task_fields(
                task_id,
                status="blocked",
                blocked_reason=f"Approval execution failed: {approval.get('id', '')}",
                metadata=metadata,
            )
        else:
            update_task_fields(task_id, metadata=metadata)
    except Exception as error:
        approval.setdefault("notes", []).append(f"Could not sync linked task {task_id}: {error}")


def approve_approval(approval_id: str = "latest-pending", dry_run: bool = False) -> dict[str, Any]:
    approval = get_approval(approval_id)
    if not approval:
        return {"ok": False, "error": f"Approval not found: {approval_id}"}

    if approval.get("status") != "pending":
        return {
            "ok": False,
            "error": f"Approval status is {approval.get('status')}, not pending.",
            "approval_id": approval.get("id"),
        }

    action_type = approval.get("action_type", "")
    object_id = approval.get("object_id", "")
    command = approval.get("command", "")

    if action_type == "apply_patch":
        result = apply_patch(object_id or "latest-proposed", dry_run=dry_run)
    elif action_type == "rollback_patch":
        result = rollback_patch(object_id or "latest-applied", dry_run=dry_run)
    elif action_type == "apply_task_evaluation":
        if dry_run:
            evaluation = get_task_evaluation(object_id or "latest")
            result = {
                "ok": bool(evaluation),
                "message": "Dry run passed. Task evaluation exists and can be applied." if evaluation else "Task evaluation not found.",
                "evaluation_id": object_id,
            }
        else:
            result = apply_task_evaluation(object_id or "latest")
    elif action_type == "run_command":
        result = run_approved_command(command, dry_run=dry_run)
    else:
        return {"ok": False, "error": f"Unsupported approval action type: {action_type}"}

    result_data = _result_dict(result)
    ok = bool(result_data.get("ok"))

    if dry_run:
        approval["updated_at"] = _now()
        approval["last_dry_run_at"] = _now()
        approval["last_dry_run_result"] = result_data
        _save_approval(approval)
        return {
            "ok": ok,
            "dry_run": True,
            "approval_id": approval.get("id"),
            "status": approval.get("status"),
            "result": result_data,
        }

    approval["updated_at"] = _now()
    approval["resolved_at"] = _now()
    approval["status"] = "approved" if ok else "failed"
    approval["result"] = result_data
    _sync_linked_task_approval(approval, approval["status"], result=result_data)
    _save_approval(approval)

    store_memory({
        "type": "approval_request_resolved",
        "content": f"Approval {approval.get('id')} resolved with status {approval['status']} for action {action_type}.",
        "source": "approval_manager",
        "approval_id": approval.get("id"),
        "action_type": action_type,
        "status": approval["status"],
        "ok": ok,
    })

    return {
        "ok": ok,
        "dry_run": False,
        "approval_id": approval.get("id"),
        "status": approval.get("status"),
        "result": result_data,
    }


def reject_approval(approval_id: str = "latest-pending", note: str = "") -> dict[str, Any]:
    approval = get_approval(approval_id)
    if not approval:
        return {"ok": False, "error": f"Approval not found: {approval_id}"}

    if approval.get("status") != "pending":
        return {
            "ok": False,
            "error": f"Approval status is {approval.get('status')}, not pending.",
            "approval_id": approval.get("id"),
        }

    approval["updated_at"] = _now()
    approval["resolved_at"] = _now()
    approval["status"] = "rejected"
    approval.setdefault("notes", []).append(note or "Rejected without note.")
    _sync_linked_task_approval(approval, "rejected", note=note)
    _save_approval(approval)

    store_memory({
        "type": "approval_request_rejected",
        "content": f"Rejected approval {approval.get('id')}: {note or 'No note provided.'}",
        "source": "approval_manager",
        "approval_id": approval.get("id"),
        "action_type": approval.get("action_type"),
        "status": "rejected",
    })

    return {
        "ok": True,
        "approval_id": approval.get("id"),
        "status": "rejected",
        "message": "Approval rejected.",
    }


def approval_text(approval: dict[str, Any], full: bool = False) -> str:
    if not approval:
        return "Approval not found."

    lines = [
        f"# Approval: {approval.get('id')}",
        f"Status: {approval.get('status')}",
        f"Created: {approval.get('created_at')}",
        f"Updated: {approval.get('updated_at')}",
        f"Action: {approval.get('action_type')}",
        f"Risk: {approval.get('risk_level')}",
        f"Source: {approval.get('source')}",
        f"Object: {approval.get('object_id') or '[none]'}",
        "",
        "## Summary",
        approval.get("summary", ""),
    ]

    if approval.get("reason"):
        lines.extend(["", "## Reason", approval.get("reason", "")])

    if approval.get("command"):
        lines.extend(["", "## Command", approval.get("command", "")])

    useful = approval.get("useful_commands", []) or _approval_commands(approval)
    if useful:
        lines.extend(["", "## Useful commands"])
        lines.extend(command for command in useful if command)

    result = approval.get("last_dry_run_result") if approval.get("status") == "pending" else approval.get("result")
    if result:
        lines.extend(["", "## Latest result", json.dumps(result, indent=2)])

    notes = approval.get("notes", []) or []
    if notes:
        lines.extend(["", "## Notes"])
        lines.extend(f"- {note}" for note in notes)

    if full:
        lines.extend(["", "## Raw approval", json.dumps(approval, indent=2)])

    return "\n".join(lines)


def print_approval_inbox(status: str = "pending", include_closed: bool = False) -> None:
    approvals = list_approvals(status=status if status else "", include_closed=include_closed)
    if not approvals:
        print("No approval requests found." if include_closed else "No pending approval requests found.")
        return

    for approval in approvals:
        print(
            f"{approval.get('id')} | status={approval.get('status')} | "
            f"action={approval.get('action_type')} | risk={approval.get('risk_level')} | {approval.get('summary')}"
        )
        if approval.get("reason"):
            print(f"  Reason: {approval.get('reason')}")
        if approval.get("command"):
            print(f"  Command: {approval.get('command')}")


def print_approval(approval_id: str = "latest-pending", full: bool = False) -> None:
    approval = get_approval(approval_id)
    if not approval:
        print(f"Approval not found: {approval_id}")
        return
    print(approval_text(approval, full=full))


def print_approve(approval_id: str = "latest-pending", dry_run: bool = False) -> None:
    result = approve_approval(approval_id, dry_run=dry_run)
    if not result.get("ok"):
        print("Approval action did not complete successfully.")
        print(f"Reason: {result.get('error') or result.get('result', {}).get('error')}")
        return

    if result.get("dry_run"):
        print("Approval dry run passed.")
        print("No approval was marked approved and no lasting action was taken.")
    else:
        print("Approval executed.")
        print(f"New status: {result.get('status')}")

    action_result = result.get("result", {}) or {}
    for key in ["message", "error", "patch_id", "target_file", "backup_path", "evaluation_id", "task_id", "command", "return_code"]:
        if action_result.get(key) not in {None, ""}:
            print(f"{key.replace('_', ' ').title()}: {action_result.get(key)}")


def print_reject(approval_id: str = "latest-pending", note: str = "") -> None:
    result = reject_approval(approval_id, note=note)
    if not result.get("ok"):
        print("Approval was not rejected.")
        print(f"Reason: {result.get('error')}")
        return
    print("Approval rejected.")
    print(f"Approval: {result.get('approval_id')}")
    if note:
        print(f"Note: {note}")
