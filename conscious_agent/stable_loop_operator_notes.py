from __future__ import annotations

"""Post-run checklist and operator notes for stable-loop records.

v6.7 note:
    v6.3 made stable loops auditable. v6.4 turned that audit into an
    operator-review workflow: checklist items, manual notes, and a final
    keep/fix/rollback decision saved directly on the stable-loop JSON record.
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from stable_supervised_loop import load_stable_loop, save_stable_loop
from stable_loop_audit import build_stable_loop_audit

OPERATOR_NOTES_VERSION = "6.9"

VALID_FINAL_DECISIONS = {
    "undecided",
    "keep",
    "fix_forward",
    "rollback",
    "needs_review",
}

FINAL_DECISION_LABELS = {
    "undecided": "Undecided",
    "keep": "Keep result",
    "fix_forward": "Fix forward",
    "rollback": "Rollback recommended",
    "needs_review": "Needs more review",
}

CHECK_STATUS_LABELS = {
    "pending": "Pending",
    "done": "Done",
    "skipped": "Skipped",
}


@dataclass
class StableLoopOperatorResult:
    ok: bool
    loop_id: str = ""
    message: str = ""
    error: str = ""
    operator_notes: dict[str, Any] | None = None
    loop: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str, fallback: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return token[:48] or fallback


def normalize_final_decision(decision: str | None) -> str:
    token = str(decision or "undecided").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "": "undecided",
        "ok": "keep",
        "accept": "keep",
        "accepted": "keep",
        "good": "keep",
        "keep_result": "keep",
        "keep_live": "keep",
        "fix": "fix_forward",
        "fixforward": "fix_forward",
        "forward_fix": "fix_forward",
        "patch_forward": "fix_forward",
        "roll_back": "rollback",
        "revert": "rollback",
        "needs_more_review": "needs_review",
        "review": "needs_review",
        "hold": "needs_review",
    }
    token = aliases.get(token, token)
    return token if token in VALID_FINAL_DECISIONS else "undecided"


def _ensure_audit(loop: dict[str, Any]) -> dict[str, Any]:
    audit = loop.get("audit") if isinstance(loop.get("audit"), dict) else None
    if not audit or audit.get("version") != OPERATOR_NOTES_VERSION:
        audit = build_stable_loop_audit(loop)
        loop["audit"] = audit
    return audit


def _check_item(item_id: str, label: str, command: str = "", required: bool = True, source: str = "default") -> dict[str, Any]:
    return {
        "id": item_id,
        "label": label,
        "command": command,
        "required": bool(required),
        "source": source,
        "status": "pending",
        "completed_at": "",
        "completed_by": "",
        "note": "",
    }


def build_default_checklist(loop: dict[str, Any]) -> list[dict[str, Any]]:
    audit = _ensure_audit(loop)
    checks: list[dict[str, Any]] = []
    checks.append(_check_item("status", "Run general status check", "python conscious_agent/main.py --status", True, "standard"))
    checks.append(_check_item("settings_health", "Run settings health check", "python conscious_agent/main.py --settings-health", True, "standard"))
    checks.append(_check_item("task_summary", "Review task/work summary", "python conscious_agent/main.py --task-work summary", True, "standard"))
    checks.append(_check_item("stable_preflight", "Run stable loop preflight", "python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop", True, "standard"))

    for command in audit.get("check_commands") or []:
        command_text = str(command or "").strip()
        if not command_text:
            continue
        item_id = _slug(command_text, f"check_{len(checks) + 1}")
        if any(item.get("command") == command_text for item in checks):
            continue
        checks.append(_check_item(item_id, f"Run recommended check: {command_text}", command_text, False, "audit"))

    for patch in audit.get("patches") or []:
        if not isinstance(patch, dict):
            continue
        patch_id = str(patch.get("id") or "").strip()
        if not patch_id:
            continue
        if patch.get("rollback_dry_run_command"):
            checks.append(_check_item(
                f"rollback_dry_run_{_slug(patch_id, 'patch')}",
                f"Preview rollback for patch {patch_id}",
                str(patch.get("rollback_dry_run_command") or ""),
                False,
                "rollback",
            ))
        if patch.get("rollback_command"):
            checks.append(_check_item(
                f"rollback_ready_{_slug(patch_id, 'patch')}",
                f"Rollback command recorded for patch {patch_id}",
                str(patch.get("rollback_command") or ""),
                False,
                "rollback",
            ))

    # De-duplicate ids while preserving order.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in checks:
        base = str(item.get("id") or f"check_{len(unique) + 1}")
        item_id = base
        counter = 2
        while item_id in seen:
            item_id = f"{base}_{counter}"
            counter += 1
        item["id"] = item_id
        seen.add(item_id)
        unique.append(item)
    return unique


def _merge_checklists(existing: list[Any], defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in defaults:
        by_id[str(item.get("id"))] = dict(item)
    for item in existing:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        merged = by_id.get(item_id, {})
        merged.update(item)
        merged.setdefault("status", "pending")
        merged.setdefault("completed_at", "")
        merged.setdefault("completed_by", "")
        merged.setdefault("note", "")
        by_id[item_id] = merged
    default_ids = [str(item.get("id")) for item in defaults]
    extra_ids = [item_id for item_id in by_id if item_id not in default_ids]
    return [by_id[item_id] for item_id in default_ids + extra_ids]


def ensure_operator_notes(loop: dict[str, Any], save: bool = False) -> dict[str, Any]:
    notes = loop.get("operator_notes") if isinstance(loop.get("operator_notes"), dict) else {}
    defaults = build_default_checklist(loop)
    existing_checks = notes.get("checklist") if isinstance(notes.get("checklist"), list) else []
    now = _now()
    created_at = notes.get("created_at") or now
    notes.setdefault("version", OPERATOR_NOTES_VERSION)
    notes["version"] = OPERATOR_NOTES_VERSION
    notes.setdefault("created_at", created_at)
    notes.setdefault("updated_at", "")
    notes.setdefault("final_decision", "undecided")
    notes["final_decision"] = normalize_final_decision(notes.get("final_decision"))
    notes.setdefault("decision_note", "")
    notes.setdefault("decision_at", "")
    notes.setdefault("decision_by", "")
    notes.setdefault("notes", [])
    notes["checklist"] = _merge_checklists(existing_checks, defaults)
    notes["summary"] = summarize_operator_notes(notes)
    loop["operator_notes"] = notes
    if save:
        save_stable_loop(loop)
    return notes


def summarize_operator_notes(notes: dict[str, Any] | None) -> dict[str, Any]:
    notes = notes if isinstance(notes, dict) else {}
    checklist = notes.get("checklist") if isinstance(notes.get("checklist"), list) else []
    total = len(checklist)
    done = sum(1 for item in checklist if isinstance(item, dict) and item.get("status") == "done")
    skipped = sum(1 for item in checklist if isinstance(item, dict) and item.get("status") == "skipped")
    pending = total - done - skipped
    required = [item for item in checklist if isinstance(item, dict) and item.get("required")]
    required_done = sum(1 for item in required if item.get("status") == "done")
    required_pending = sum(1 for item in required if item.get("status") == "pending")
    final_decision = normalize_final_decision(notes.get("final_decision"))
    return {
        "check_total": total,
        "check_done": done,
        "check_skipped": skipped,
        "check_pending": pending,
        "required_total": len(required),
        "required_done": required_done,
        "required_pending": required_pending,
        "final_decision": final_decision,
        "final_decision_label": FINAL_DECISION_LABELS.get(final_decision, final_decision),
        "complete": pending == 0 and final_decision != "undecided",
        "ready_for_keep_decision": required_pending == 0,
    }


def get_stable_loop_operator_notes(loop_id: str = "latest", ensure: bool = True, save: bool = False) -> StableLoopOperatorResult:
    loop = load_stable_loop(loop_id)
    if not loop:
        return StableLoopOperatorResult(False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")
    notes = ensure_operator_notes(loop, save=save) if ensure else loop.get("operator_notes") if isinstance(loop.get("operator_notes"), dict) else {}
    return StableLoopOperatorResult(True, str(loop.get("id") or loop_id), "Stable loop operator notes loaded.", operator_notes=notes, loop=loop)


def add_stable_loop_operator_note(loop_id: str, note: str, reviewer: str = "operator") -> StableLoopOperatorResult:
    loop = load_stable_loop(loop_id)
    if not loop:
        return StableLoopOperatorResult(False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")
    notes = ensure_operator_notes(loop, save=False)
    now = _now()
    entries = notes.get("notes") if isinstance(notes.get("notes"), list) else []
    entries.append({"at": now, "by": reviewer or "operator", "note": str(note or "").strip()})
    notes["notes"] = entries
    notes["updated_at"] = now
    notes["summary"] = summarize_operator_notes(notes)
    loop["operator_notes"] = notes
    save_stable_loop(loop)
    return StableLoopOperatorResult(True, str(loop.get("id") or loop_id), "Operator note added.", operator_notes=notes, loop=loop)


def update_stable_loop_check(
    loop_id: str,
    check_id: str,
    status: str = "done",
    note: str = "",
    reviewer: str = "operator",
) -> StableLoopOperatorResult:
    loop = load_stable_loop(loop_id)
    if not loop:
        return StableLoopOperatorResult(False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")
    notes = ensure_operator_notes(loop, save=False)
    checklist = notes.get("checklist") if isinstance(notes.get("checklist"), list) else []
    normalized_status = str(status or "done").strip().lower().replace(" ", "_").replace("-", "_")
    if normalized_status in {"complete", "completed"}:
        normalized_status = "done"
    if normalized_status not in {"pending", "done", "skipped"}:
        normalized_status = "done"
    target = None
    for item in checklist:
        if isinstance(item, dict) and str(item.get("id")) == str(check_id):
            target = item
            break
    if not target:
        return StableLoopOperatorResult(False, str(loop.get("id") or loop_id), error=f"Checklist item not found: {check_id}", operator_notes=notes, loop=loop)
    now = _now()
    target["status"] = normalized_status
    target["note"] = note or target.get("note", "")
    target["completed_by"] = reviewer or "operator"
    target["completed_at"] = now if normalized_status in {"done", "skipped"} else ""
    notes["updated_at"] = now
    notes["summary"] = summarize_operator_notes(notes)
    loop["operator_notes"] = notes
    save_stable_loop(loop)
    return StableLoopOperatorResult(True, str(loop.get("id") or loop_id), f"Checklist item {check_id} marked {CHECK_STATUS_LABELS.get(normalized_status, normalized_status)}.", operator_notes=notes, loop=loop)


def set_stable_loop_final_decision(
    loop_id: str,
    decision: str,
    note: str = "",
    reviewer: str = "operator",
) -> StableLoopOperatorResult:
    loop = load_stable_loop(loop_id)
    if not loop:
        return StableLoopOperatorResult(False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")
    notes = ensure_operator_notes(loop, save=False)
    normalized = normalize_final_decision(decision)
    now = _now()
    notes["final_decision"] = normalized
    notes["decision_note"] = note or notes.get("decision_note", "")
    notes["decision_at"] = now
    notes["decision_by"] = reviewer or "operator"
    entries = notes.get("notes") if isinstance(notes.get("notes"), list) else []
    if note:
        entries.append({"at": now, "by": reviewer or "operator", "note": f"Final decision: {FINAL_DECISION_LABELS.get(normalized, normalized)}. {note}"})
    notes["notes"] = entries
    notes["updated_at"] = now
    notes["summary"] = summarize_operator_notes(notes)
    loop["operator_notes"] = notes
    save_stable_loop(loop)
    return StableLoopOperatorResult(True, str(loop.get("id") or loop_id), f"Final decision saved: {FINAL_DECISION_LABELS.get(normalized, normalized)}.", operator_notes=notes, loop=loop)


def stable_loop_operator_notes_text(data: dict[str, Any] | StableLoopOperatorResult | None, full: bool = False) -> str:
    if isinstance(data, StableLoopOperatorResult):
        loop = data.loop or {}
        notes = data.operator_notes or {}
        ok = data.ok
        error = data.error
    else:
        loop = data or {}
        notes = ensure_operator_notes(loop, save=False) if loop else {}
        ok = bool(loop)
        error = "" if loop else "No stable loop found."

    summary = notes.get("summary") if isinstance(notes.get("summary"), dict) else summarize_operator_notes(notes)
    final_decision = normalize_final_decision(notes.get("final_decision"))
    lines = [
        "# Stable loop operator notes",
        "",
        f"OK: {ok}",
        f"Loop: {loop.get('id', '')}",
        f"Live: {loop.get('live', '')}",
        f"Final decision: {FINAL_DECISION_LABELS.get(final_decision, final_decision)}",
        f"Checklist: {summary.get('check_done', 0)} done / {summary.get('check_total', 0)} total; {summary.get('check_pending', 0)} pending",
        f"Required checks: {summary.get('required_done', 0)} done / {summary.get('required_total', 0)} total",
        f"Ready for keep decision: {summary.get('ready_for_keep_decision')}",
    ]
    if error:
        lines.append(f"Error: {error}")
    if notes.get("decision_note"):
        lines.append(f"Decision note: {notes.get('decision_note')}")

    lines.extend(["", "## Checklist"])
    checklist = notes.get("checklist") if isinstance(notes.get("checklist"), list) else []
    if checklist:
        for item in checklist:
            if not isinstance(item, dict):
                continue
            required = "required" if item.get("required") else "optional"
            line = f"- [{item.get('status', 'pending')}] {item.get('id')}: {item.get('label', '')} ({required})"
            lines.append(line)
            if item.get("command"):
                lines.append(f"  command: {item.get('command')}")
            if item.get("note"):
                lines.append(f"  note: {item.get('note')}")
    else:
        lines.append("- No checklist items.")

    note_entries = notes.get("notes") if isinstance(notes.get("notes"), list) else []
    if note_entries:
        lines.extend(["", "## Operator notes"])
        for entry in note_entries[-12:]:
            if isinstance(entry, dict):
                lines.append(f"- {entry.get('at', '')} [{entry.get('by', '')}] {entry.get('note', '')}")
            else:
                lines.append(f"- {entry}")

    if full:
        lines.extend(["", "## Raw operator notes", json.dumps(notes, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_stable_loop_operator_notes(loop_id: str = "latest", full: bool = False) -> None:
    result = get_stable_loop_operator_notes(loop_id, ensure=True, save=True)
    print(stable_loop_operator_notes_text(result, full=full))


def print_add_stable_loop_operator_note(loop_id: str, note: str, full: bool = False) -> None:
    result = add_stable_loop_operator_note(loop_id, note=note, reviewer="cli")
    print(stable_loop_operator_notes_text(result, full=full))


def print_update_stable_loop_check(loop_id: str, check_id: str, status: str = "done", note: str = "", full: bool = False) -> None:
    result = update_stable_loop_check(loop_id, check_id=check_id, status=status, note=note, reviewer="cli")
    print(stable_loop_operator_notes_text(result, full=full))


def print_set_stable_loop_final_decision(loop_id: str, decision: str, note: str = "", full: bool = False) -> None:
    result = set_stable_loop_final_decision(loop_id, decision=decision, note=note, reviewer="cli")
    print(stable_loop_operator_notes_text(result, full=full))
