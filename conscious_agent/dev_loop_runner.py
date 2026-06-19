from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from autonomous_dev_cycle import (
    advance_dev_cycle,
    create_dev_cycle,
    dev_cycle_text,
)
from approval_manager import create_approval_from_dev_step
from memory import store_memory
from paths import DATA_DIR
from settings_manager import get_setting


DEV_LOOPS_DIR = DATA_DIR / "dev_loops"
DEV_LOOPS_README = DEV_LOOPS_DIR / "README.md"
APPROVAL_REQUIRED_STEPS = {"review-proposed-patch", "awaiting-rollback-approval"}
MANUAL_REVIEW_STEPS = {"manual-review", "patch-looks-safe"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_storage() -> None:
    DEV_LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    if not DEV_LOOPS_README.exists():
        DEV_LOOPS_README.write_text(
            "Saved bounded autonomous development loop records. "
            "Each loop advances Eidolon a limited number of safe supervised steps and stops before risky actions unless explicitly approved.\n",
            encoding="utf-8",
        )


def _new_loop_id() -> str:
    return f"devloop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _loop_path(loop_id: str) -> Path:
    _ensure_storage()
    return DEV_LOOPS_DIR / f"{loop_id}.json"


def _save_loop(loop: dict[str, Any]) -> None:
    _ensure_storage()
    with _loop_path(loop["id"]).open("w", encoding="utf-8") as file:
        json.dump(loop, file, indent=2)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_dev_loops() -> list[dict[str, Any]]:
    _ensure_storage()
    loops: list[dict[str, Any]] = []
    for path in DEV_LOOPS_DIR.glob("*.json"):
        data = _load_json_file(path)
        if data:
            loops.append(data)
    return sorted(loops, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_dev_loop_id(loop_id: str) -> str:
    token = (loop_id or "").strip()
    token_lower = token.lower()
    loops = list_dev_loops()

    if token_lower in {"latest", "last"}:
        return loops[0].get("id", "") if loops else ""

    if token_lower.startswith("latest-"):
        desired = token_lower.replace("latest-", "", 1)
        matches = [loop for loop in loops if str(loop.get("stopped_reason", "")).lower() == desired]
        return matches[0].get("id", "") if matches else ""

    return token


def get_dev_loop(loop_id: str) -> dict[str, Any] | None:
    resolved = resolve_dev_loop_id(loop_id)
    if not resolved:
        return None
    for loop in list_dev_loops():
        if loop.get("id") == resolved:
            return loop
    return None


def _decision_signature(cycle: dict[str, Any]) -> str:
    decision = cycle.get("decision", {}) or {}
    state = cycle.get("state", {}) or {}
    return "|".join([
        str(decision.get("step", "")),
        str(decision.get("object_id", "")),
        str(state.get("proposed_patch_id", "")),
        str(state.get("applied_patch_id", "")),
        str(state.get("ready_task_id", "")),
        str(state.get("latest_patch_report_id", "")),
        str(state.get("latest_patch_review_id", "")),
    ])


def _new_loop_record(
    task_id: str,
    max_steps: int,
    dry_run: bool,
    approve_apply: bool,
    apply_evaluation: bool,
    use_ai: bool,
) -> dict[str, Any]:
    return {
        "id": _new_loop_id(),
        "type": "bounded_autonomous_dev_loop",
        "created_at": _now(),
        "task_id": task_id,
        "max_steps": max_steps,
        "dry_run": dry_run,
        "approve_apply": approve_apply,
        "apply_evaluation": apply_evaluation,
        "use_ai": use_ai,
        "ok": True,
        "steps": [],
        "stopped_reason": "not_started",
        "stopped_message": "",
        "next_command": "",
        "useful_commands": [],
    }


def _create_approval_for_loop_step(step: str, object_id: str, reason: str) -> dict[str, Any] | None:
    return create_approval_from_dev_step(
        step=step,
        object_id=object_id,
        source="dev_loop_runner",
        reason=reason,
    )


def run_dev_loop(
    task_id: str = "latest-ready",
    max_steps: int = 3,
    dry_run: bool = False,
    approve_apply: bool = False,
    apply_evaluation: bool = False,
    use_ai: bool = True,
) -> dict[str, Any]:
    """
    Runs a bounded supervised autonomous development loop.

    The loop advances at most `max_steps` dev-cycle steps and stops when:
    - a patch apply or rollback would require explicit approval,
    - a manual review step is reached,
    - an action fails,
    - dry-run mode would repeat the same state,
    - the same decision signature appears twice,
    - the max step count is reached.
    """

    max_cap = int(get_setting("max_dev_loop_steps", 10))
    max_steps = max(1, min(int(max_steps), max_cap))
    loop = _new_loop_record(
        task_id=task_id,
        max_steps=max_steps,
        dry_run=dry_run,
        approve_apply=approve_apply,
        apply_evaluation=apply_evaluation,
        use_ai=use_ai,
    )

    seen_signatures: set[str] = set()

    for index in range(max_steps):
        preview = create_dev_cycle(task_id=task_id)
        decision = preview.get("decision", {}) or {}
        step = decision.get("step", "")
        signature = _decision_signature(preview)

        step_record: dict[str, Any] = {
            "index": index + 1,
            "preview_cycle_id": preview.get("id", ""),
            "decision_step": step,
            "decision_reason": decision.get("reason", ""),
            "object_id": decision.get("object_id", ""),
            "next_command_before_action": decision.get("next_command", ""),
            "action": {},
        }

        if signature in seen_signatures:
            loop["stopped_reason"] = "repeated_state"
            loop["stopped_message"] = "The same dev-cycle state appeared again, so the loop stopped to avoid spinning."
            loop["steps"].append(step_record)
            break
        seen_signatures.add(signature)

        if step in APPROVAL_REQUIRED_STEPS and not approve_apply:
            approval = _create_approval_for_loop_step(
                step=step,
                object_id=decision.get("object_id", ""),
                reason=decision.get("reason", "Approval is required before this action can continue."),
            )
            if approval:
                step_record["approval_id"] = approval.get("id", "")
                loop["approval_id"] = approval.get("id", "")
            loop["stopped_reason"] = "approval_required"
            loop["stopped_message"] = decision.get("reason", "Approval is required before this action can continue.")
            loop["next_command"] = f"python conscious_agent/main.py --show-approval {approval.get('id')}" if approval else (decision.get("approval_command") or decision.get("next_command", ""))
            loop["steps"].append(step_record)
            break

        if step in MANUAL_REVIEW_STEPS:
            loop["stopped_reason"] = "manual_review"
            loop["stopped_message"] = decision.get("reason", "Manual review is safer than continuing automatically.")
            loop["next_command"] = decision.get("next_command", "")
            loop["steps"].append(step_record)
            break

        advanced = advance_dev_cycle(
            task_id=task_id,
            dry_run=dry_run,
            approve_apply=approve_apply,
            apply_evaluation=apply_evaluation,
            use_ai=use_ai,
        )
        action = advanced.get("action_result", {}) or {}
        step_record["advanced_cycle_id"] = advanced.get("id", "")
        step_record["action"] = action
        step_record["next_command_after_action"] = advanced.get("next_command", "")
        step_record["next_decision"] = advanced.get("next_decision", {})
        loop["steps"].append(step_record)

        if not advanced.get("ok", True) or action.get("ok") is False:
            loop["ok"] = False
            loop["stopped_reason"] = "action_failed"
            loop["stopped_message"] = action.get("error") or action.get("message") or "The dev-cycle action failed."
            loop["next_command"] = advanced.get("next_command", "")
            break

        if dry_run:
            loop["stopped_reason"] = "dry_run_complete"
            loop["stopped_message"] = "Dry-run mode stops after one safe preview/action to avoid repeating unchanged state."
            loop["next_command"] = advanced.get("next_command", "")
            break

        refreshed_decision = advanced.get("next_decision", {}) or {}
        refreshed_step = refreshed_decision.get("step", "")
        if refreshed_step in APPROVAL_REQUIRED_STEPS and not approve_apply:
            approval = _create_approval_for_loop_step(
                step=refreshed_step,
                object_id=refreshed_decision.get("object_id", ""),
                reason=refreshed_decision.get("reason", "Approval is required before continuing."),
            )
            if approval:
                step_record["approval_id"] = approval.get("id", "")
                loop["approval_id"] = approval.get("id", "")
            loop["stopped_reason"] = "approval_required"
            loop["stopped_message"] = refreshed_decision.get("reason", "Approval is required before continuing.")
            loop["next_command"] = f"python conscious_agent/main.py --show-approval {approval.get('id')}" if approval else (refreshed_decision.get("approval_command") or refreshed_decision.get("next_command", ""))
            break
        if refreshed_step in MANUAL_REVIEW_STEPS:
            loop["stopped_reason"] = "manual_review"
            loop["stopped_message"] = refreshed_decision.get("reason", "Manual review is safer than continuing automatically.")
            loop["next_command"] = refreshed_decision.get("next_command", "")
            break

        loop["next_command"] = refreshed_decision.get("next_command") or advanced.get("next_command", "")

    if loop["stopped_reason"] == "not_started":
        loop["stopped_reason"] = "max_steps_reached"
        loop["stopped_message"] = f"Reached the configured limit of {max_steps} step(s)."
        if not loop.get("next_command"):
            loop["next_command"] = "python conscious_agent/main.py --dev-loop"

    loop["finished_at"] = _now()
    loop["step_count"] = len(loop.get("steps", []))
    loop["useful_commands"] = [
        "python conscious_agent/main.py --dev-loop --dry-run --no-ai-dev-loop",
        "python conscious_agent/main.py --dev-loop",
        "python conscious_agent/main.py --show-dev-loop latest --dev-loop-full",
        loop.get("next_command", ""),
    ]

    _save_loop(loop)
    store_memory({
        "type": "bounded_autonomous_dev_loop",
        "content": (
            f"Ran bounded autonomous dev loop {loop['id']} for {loop['step_count']} step(s). "
            f"Stopped because: {loop['stopped_reason']}."
        ),
        "source": "dev_loop_runner",
        "dev_loop_id": loop["id"],
        "stopped_reason": loop["stopped_reason"],
        "step_count": loop["step_count"],
    })
    return loop


def dev_loop_text(loop: dict[str, Any], full: bool = False) -> str:
    if not loop:
        return "Dev loop not found."

    lines = [
        f"# Bounded Dev Loop: {loop.get('id')}",
        f"Created: {loop.get('created_at')}",
        f"Finished: {loop.get('finished_at', '')}",
        f"OK: {loop.get('ok')}",
        f"Steps run: {loop.get('step_count', len(loop.get('steps', [])))} / {loop.get('max_steps')}",
        f"Dry run: {loop.get('dry_run')}",
        f"Approve apply/rollback: {loop.get('approve_apply')}",
        f"Apply task evaluation: {loop.get('apply_evaluation')}",
        f"Stopped reason: {loop.get('stopped_reason')}",
        f"Stopped message: {loop.get('stopped_message')}",
    ]

    if loop.get("approval_id"):
        lines.append(f"Approval: {loop.get('approval_id')}")
    if loop.get("next_command"):
        lines.append(f"Next command: {loop.get('next_command')}")

    steps = loop.get("steps", [])
    if steps:
        lines.append("")
        lines.append("## Steps")
        for step in steps:
            action = step.get("action", {}) or {}
            lines.append(f"{step.get('index')}. {step.get('decision_step')} | object={step.get('object_id') or '[none]'}")
            if step.get("decision_reason"):
                lines.append(f"   Reason: {step.get('decision_reason')}")
            if step.get("approval_id"):
                lines.append(f"   Approval: {step.get('approval_id')}")
            if action:
                lines.append(f"   Action: {action.get('action')} | ok={action.get('ok')}")
                if action.get("message"):
                    lines.append(f"   Message: {action.get('message')}")
                if action.get("error"):
                    lines.append(f"   Error: {action.get('error')}")
            elif step.get("next_command_before_action"):
                lines.append(f"   Next command: {step.get('next_command_before_action')}")

    useful = [command for command in loop.get("useful_commands", []) if command]
    if useful:
        lines.append("")
        lines.append("## Useful commands")
        for command in useful:
            lines.append(command)

    if full:
        lines.append("")
        lines.append("## Raw loop record")
        lines.append(json.dumps(loop, indent=2))

    return "\n".join(lines)


def print_dev_loop(
    task_id: str = "latest-ready",
    max_steps: int = 3,
    dry_run: bool = False,
    approve_apply: bool = False,
    apply_evaluation: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    loop = run_dev_loop(
        task_id=task_id,
        max_steps=max_steps,
        dry_run=dry_run,
        approve_apply=approve_apply,
        apply_evaluation=apply_evaluation,
        use_ai=use_ai,
    )
    print(dev_loop_text(loop, full=full))


def print_dev_loops() -> None:
    loops = list_dev_loops()
    if not loops:
        print("No dev loop records found.")
        return
    for loop in loops:
        print(
            f"{loop.get('id')} | steps={loop.get('step_count')} | ok={loop.get('ok')} | "
            f"stopped={loop.get('stopped_reason')} | dry_run={loop.get('dry_run')}"
        )


def print_saved_dev_loop(loop_id: str = "latest", full: bool = False) -> None:
    loop = get_dev_loop(loop_id)
    if not loop:
        print(f"Dev loop not found: {loop_id}")
        return
    print(dev_loop_text(loop, full=full))
