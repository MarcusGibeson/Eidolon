from __future__ import annotations

"""Stable supervised agent loop orchestration.

v6.9 note:
    This module wraps the lifecycle-aware work cycle with a predictable
    operator loop: preflight -> dry-run preview -> optional live run -> saved
    review record. The existing work_cycle.py remains the action engine. This
    layer is intentionally boring, because boring is what keeps "autonomous"
    from becoming "why is my repo smoking?".
"""

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from approval_manager import list_approvals
from paths import DATA_DIR
from settings_manager import load_settings
from task_cycle_policy import choose_next_cycle_decision, list_cycle_candidates
from task_lifecycle import task_lifecycle_summary
from task_recovery import task_recovery_summary
from work_cycle import load_work_cycle, run_supervised_work_cycle, work_cycle_text
from work_queue import summarize_queue
from stable_loop_audit import build_stable_loop_audit, stable_loop_audit_text


STABLE_LOOP_VERSION = "6.9"
STABLE_LOOPS_DIR = DATA_DIR / "stable_loops"
DEFAULT_PROJECT_ID = "eidolon"
MAX_STABLE_LOOP_STEPS = 5


@dataclass
class StableLoopResult:
    ok: bool
    loop_id: str = ""
    project_id: str = DEFAULT_PROJECT_ID
    live: bool = False
    max_steps: int = 1
    stopped_reason: str = ""
    message: str = ""
    error: str = ""
    preflight: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    preview_cycle_id: str = ""
    live_cycle_id: str = ""
    preview_cycle: dict[str, Any] | None = None
    live_cycle: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None
    events: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _ensure_storage() -> None:
    STABLE_LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    readme = STABLE_LOOPS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Stable supervised loops\n\n"
            "Saved v6.9 stable supervised loop audit/review/operator/decision/follow-up/guardrail records. These records wrap work-cycle previews, operator review state, and optional live runs.\n",
            encoding="utf-8",
        )


def _loop_path(loop_id: str) -> Path:
    return STABLE_LOOPS_DIR / f"{loop_id}.json"


def save_stable_loop(record: dict[str, Any]) -> None:
    """Persist a stable-loop record with an atomic replace and short lock retries.

    Dashboard live-refresh on Windows can briefly hold the destination JSON open.
    Writing to a temp file first avoids truncating the final record, and retrying
    os.replace() lets the smoke suite and dashboard coexist instead of fighting
    over a tiny JSON file like raccoons in a server closet.
    """
    _ensure_storage()
    path = _loop_path(record["id"])
    tmp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            tmp_name = file.name
            json.dump(record, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        last_error: OSError | None = None
        for attempt in range(8):
            try:
                os.replace(tmp_name, path)
                return
            except PermissionError as error:
                last_error = error
                time.sleep(0.05 * (attempt + 1))
            except OSError as error:
                last_error = error
                time.sleep(0.05 * (attempt + 1))
        if last_error is not None:
            raise last_error
    finally:
        if tmp_name:
            try:
                tmp_path = Path(tmp_name)
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass


def list_stable_loops() -> list[dict[str, Any]]:
    _ensure_storage()
    loops: list[dict[str, Any]] = []
    for path in sorted(STABLE_LOOPS_DIR.glob("*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            loops.append(data)
    return loops


def resolve_stable_loop_id(loop_id: str = "latest") -> str:
    token = str(loop_id or "latest").strip()
    if token.lower() not in {"latest", "last"}:
        return token
    loops = list_stable_loops()
    return str(loops[0].get("id", "")) if loops else ""


def load_stable_loop(loop_id: str = "latest") -> dict[str, Any] | None:
    resolved = resolve_stable_loop_id(loop_id)
    if not resolved:
        return None
    path = _loop_path(resolved)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def build_stable_loop_preflight(project_id: Optional[str] = None, max_steps: int = 1) -> dict[str, Any]:
    """Build a read-only stability snapshot before a supervised loop run."""
    project = (project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    issues: list[str] = []
    warnings: list[str] = []
    settings = load_settings()
    safe_mode = str(settings.get("safe_mode") or "").strip().lower()
    if safe_mode != "strict":
        issues.append(f"safe_mode is {safe_mode!r}; stable loop expects 'strict'.")

    requested_steps = max(1, int(max_steps or 1))
    if requested_steps > MAX_STABLE_LOOP_STEPS:
        warnings.append(f"Requested {requested_steps} step(s); stable loop will cap at {MAX_STABLE_LOOP_STEPS}.")

    queue_summary = summarize_queue(project_id=project)
    lifecycle_summary = task_lifecycle_summary(project=project)
    recovery_summary = task_recovery_summary(project=project)
    try:
        from stable_loop_guardrails import stable_loop_guardrail_summary

        closure_guardrails = stable_loop_guardrail_summary(project_id=project)
    except Exception as guardrail_error:
        closure_guardrails = {
            "ok": False,
            "ok_for_preview": True,
            "ok_for_live": False,
            "error": str(guardrail_error),
            "message": "Stable-loop closure guardrails could not be evaluated.",
        }
    approvals = list_approvals(status="pending", include_closed=False)
    candidates = list_cycle_candidates(project=project)
    decision = choose_next_cycle_decision(project=project)

    if not candidates and not queue_summary.get("total"):
        warnings.append("No open task candidates found. Stable loop may seed safe starter tasks if enabled.")

    if lifecycle_summary.get("needs_attention", 0):
        warnings.append(f"{lifecycle_summary.get('needs_attention')} task(s) need attention before ordinary ready work.")

    if recovery_summary.get("recoverable", 0):
        warnings.append(f"{recovery_summary.get('recoverable')} task(s) have recovery recommendations.")

    if closure_guardrails.get("block_live"):
        warnings.append(str(closure_guardrails.get("message") or "Closure guardrails would block a live stable-loop run."))

    return {
        "ok": not issues,
        "version": STABLE_LOOP_VERSION,
        "checked_at": _now(),
        "project_id": project,
        "settings_version": settings.get("settings_version"),
        "safe_mode": settings.get("safe_mode"),
        "requested_steps": requested_steps,
        "max_steps_cap": MAX_STABLE_LOOP_STEPS,
        "effective_steps": min(requested_steps, MAX_STABLE_LOOP_STEPS),
        "issues": issues,
        "warnings": warnings,
        "pending_approval_count": len(approvals),
        "queue_summary": queue_summary,
        "lifecycle_summary": lifecycle_summary,
        "recovery_summary": recovery_summary,
        "closure_guardrails": closure_guardrails,
        "candidate_count": len(candidates),
        "next_decision": decision.to_dict(),
    }


def _saved_cycle(cycle_id: str) -> dict[str, Any] | None:
    return load_work_cycle(cycle_id) if cycle_id else None


def run_stable_supervised_loop(
    project_id: Optional[str] = None,
    max_steps: int = 1,
    live: bool = False,
    use_ai: bool = True,
    approve_work_execution: bool = False,
    seed_if_empty: bool = True,
    auto_create_patch_followups: bool = True,
    auto_request_approvals: bool = True,
    auto_retry_recovery: bool = False,
    bypass_closure_guardrails: bool = False,
) -> StableLoopResult:
    """Run the stable supervised loop.

    Default mode is review-only. A live run must be requested explicitly with
    `live=True`, and even then it first saves a dry-run preview cycle so the
    operator can see what the policy selected.
    """
    project = (project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    effective_steps = max(1, min(int(max_steps or 1), MAX_STABLE_LOOP_STEPS))
    loop_id = f"stableloop_{_timestamp_id()}"
    events: list[dict[str, Any]] = []
    error = ""
    stopped_reason = ""
    ok = True

    preflight = build_stable_loop_preflight(project_id=project, max_steps=max_steps)
    closure_guardrails = preflight.get("closure_guardrails") if isinstance(preflight.get("closure_guardrails"), dict) else {}
    if bypass_closure_guardrails:
        try:
            from stable_loop_guardrails import stable_loop_guardrail_summary

            closure_guardrails = stable_loop_guardrail_summary(project_id=project, bypass=True)
            preflight["closure_guardrails"] = closure_guardrails
        except Exception as guardrail_error:
            closure_guardrails = {
                "ok": False,
                "ok_for_preview": True,
                "ok_for_live": False,
                "error": str(guardrail_error),
                "message": "Stable-loop closure guardrails could not be evaluated during bypass refresh.",
            }
            preflight["closure_guardrails"] = closure_guardrails
    events.append({"type": "preflight", "at": _now(), "preflight": preflight, "closure_guardrails": closure_guardrails})

    decision = preflight.get("next_decision") or choose_next_cycle_decision(project=project).to_dict()
    if not preflight.get("ok"):
        ok = False
        error = "; ".join(str(item) for item in preflight.get("issues", []))
        stopped_reason = "preflight_failed"

    preview_result = None
    preview_cycle = None
    live_result = None
    live_cycle = None

    if ok:
        preview_result = run_supervised_work_cycle(
            project_id=project,
            max_steps=effective_steps,
            dry_run=True,
            use_ai=use_ai,
            approve_work_execution=False,
            seed_if_empty=seed_if_empty,
            auto_create_patch_followups=auto_create_patch_followups,
            auto_request_approvals=auto_request_approvals,
            auto_retry_recovery=False,
        )
        preview_cycle = _saved_cycle(preview_result.cycle_id)
        events.append({
            "type": "preview_cycle",
            "at": _now(),
            "cycle_id": preview_result.cycle_id,
            "ok": preview_result.ok,
            "stopped_reason": preview_result.stopped_reason,
            "message": preview_result.message,
        })
        if not preview_result.ok:
            ok = False
            error = preview_result.error or "Dry-run preview failed."
            stopped_reason = "preview_failed"
        elif not live:
            stopped_reason = "preview_only"
        elif closure_guardrails.get("block_live") and not bypass_closure_guardrails:
            ok = False
            error = str(closure_guardrails.get("error") or closure_guardrails.get("message") or "Stable-loop closure guardrails blocked live advancement.")
            stopped_reason = "closure_guardrail_blocked"
            events.append({
                "type": "closure_guardrail_blocked",
                "at": _now(),
                "closure_guardrails": closure_guardrails,
                "message": error,
            })
        else:
            live_result = run_supervised_work_cycle(
                project_id=project,
                max_steps=effective_steps,
                dry_run=False,
                use_ai=use_ai,
                approve_work_execution=approve_work_execution,
                seed_if_empty=seed_if_empty,
                auto_create_patch_followups=auto_create_patch_followups,
                auto_request_approvals=auto_request_approvals,
                auto_retry_recovery=auto_retry_recovery,
            )
            live_cycle = _saved_cycle(live_result.cycle_id)
            events.append({
                "type": "live_cycle",
                "at": _now(),
                "cycle_id": live_result.cycle_id,
                "ok": live_result.ok,
                "stopped_reason": live_result.stopped_reason,
                "message": live_result.message,
            })
            ok = bool(live_result.ok)
            error = live_result.error or ""
            stopped_reason = live_result.stopped_reason or "live_complete"

    if not stopped_reason:
        stopped_reason = "complete"

    message = _stable_loop_message(
        live=live,
        ok=ok,
        stopped_reason=stopped_reason,
        preview_cycle_id=(preview_result.cycle_id if preview_result else ""),
        live_cycle_id=(live_result.cycle_id if live_result else ""),
    )

    record = {
        "id": loop_id,
        "version": STABLE_LOOP_VERSION,
        "created_at": _now(),
        "project_id": project,
        "live": live,
        "max_steps": effective_steps,
        "use_ai": use_ai,
        "approve_work_execution": approve_work_execution,
        "seed_if_empty": seed_if_empty,
        "auto_create_patch_followups": auto_create_patch_followups,
        "auto_request_approvals": auto_request_approvals,
        "auto_retry_recovery": auto_retry_recovery,
        "bypass_closure_guardrails": bypass_closure_guardrails,
        "closure_guardrails": closure_guardrails,
        "ok": ok,
        "stopped_reason": stopped_reason,
        "message": message,
        "error": error,
        "preflight": preflight,
        "decision": decision,
        "preview_cycle_id": preview_result.cycle_id if preview_result else "",
        "live_cycle_id": live_result.cycle_id if live_result else "",
        "preview_cycle": preview_cycle,
        "live_cycle": live_cycle,
        "events": events,
        "review": {
            "status": "unreviewed",
            "updated_at": "",
            "reviewed_by": "",
            "notes": [],
        },
    }
    record["audit"] = build_stable_loop_audit(record)
    try:
        from stable_loop_operator_notes import ensure_operator_notes

        record["operator_notes"] = ensure_operator_notes(record, save=False)
    except Exception as error:
        record["operator_notes_error"] = str(error)
    save_stable_loop(record)

    return StableLoopResult(
        ok=ok,
        loop_id=loop_id,
        project_id=project,
        live=live,
        max_steps=effective_steps,
        stopped_reason=stopped_reason,
        message=message,
        error=error,
        preflight=preflight,
        decision=decision,
        preview_cycle_id=record["preview_cycle_id"],
        live_cycle_id=record["live_cycle_id"],
        preview_cycle=preview_cycle,
        live_cycle=live_cycle,
        audit=record.get("audit"),
        events=events,
    )


def _stable_loop_message(live: bool, ok: bool, stopped_reason: str, preview_cycle_id: str = "", live_cycle_id: str = "") -> str:
    mode = "Live stable loop" if live else "Stable loop preview"
    parts = [f"{mode} saved. ok={ok}. stopped={stopped_reason}."]
    if preview_cycle_id:
        parts.append(f"Preview cycle: {preview_cycle_id}.")
    if live_cycle_id:
        parts.append(f"Live cycle: {live_cycle_id}.")
    if not live:
        parts.append("No live task mutations were requested.")
    return " ".join(parts)


def stable_loop_text(record_or_result: dict[str, Any] | StableLoopResult, full: bool = False) -> str:
    data = record_or_result.to_dict() if isinstance(record_or_result, StableLoopResult) else record_or_result
    preflight = data.get("preflight") or {}
    decision = data.get("decision") or {}
    lines = [
        "# Stable supervised agent loop",
        "",
        f"Loop: {data.get('loop_id') or data.get('id', '')}",
        f"Version: {data.get('version', STABLE_LOOP_VERSION)}",
        f"Project: {data.get('project_id', '')}",
        f"Live run: {data.get('live')}",
        f"OK: {data.get('ok')}",
        f"Stopped: {data.get('stopped_reason', '')}",
        f"Preview cycle: {data.get('preview_cycle_id', '')}",
        f"Live cycle: {data.get('live_cycle_id', '')}",
    ]
    review = data.get("review") if isinstance(data.get("review"), dict) else {}
    review_status = str(review.get("status") or "unreviewed")
    lines.extend([
        f"Review status: {review_status}",
        f"Review updated: {review.get('updated_at', '')}",
    ])
    if review.get("live_loop_id"):
        lines.append(f"Review live loop: {review.get('live_loop_id')}")
    audit = data.get("audit") if isinstance(data.get("audit"), dict) else {}
    if audit:
        lines.append(f"Audit summary: {audit.get('summary', '')}")
        lines.append(f"Audit warnings: {len(audit.get('warnings') or [])}")
    guardrails = data.get("closure_guardrails") or preflight.get("closure_guardrails") or {}
    if guardrails:
        lines.append(f"Closure guardrails live-ready: {guardrails.get('ok_for_live')}")
        lines.append(f"Closure blockers: {guardrails.get('unresolved_count', 0)}")
    if data.get("message"):
        lines.append(f"Message: {data.get('message')}")
    if data.get("error"):
        lines.append(f"Error: {data.get('error')}")

    lines.extend([
        "",
        "## Preflight",
        f"Safe mode: {preflight.get('safe_mode', '')}",
        f"Pending approvals: {preflight.get('pending_approval_count', 0)}",
        f"Open lifecycle tasks: {(preflight.get('lifecycle_summary') or {}).get('open', 0)}",
        f"Needs attention: {(preflight.get('lifecycle_summary') or {}).get('needs_attention', 0)}",
        f"Recoverable tasks: {(preflight.get('recovery_summary') or {}).get('recoverable', 0)}",
        f"Cycle candidates: {preflight.get('candidate_count', 0)}",
    ])
    guardrails = preflight.get("closure_guardrails") if isinstance(preflight.get("closure_guardrails"), dict) else {}
    if guardrails:
        lines.append(f"Closure guardrails live-ready: {guardrails.get('ok_for_live')}")
        lines.append(f"Closure blockers: {guardrails.get('unresolved_count', 0)}")

    issues = preflight.get("issues") or []
    warnings = preflight.get("warnings") or []
    if issues:
        lines.append("Issues:")
        lines.extend(f"- {item}" for item in issues)
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings)

    lines.extend([
        "",
        "## Selected lifecycle decision",
        f"Action: {decision.get('action', '')}",
        f"Task: {decision.get('task_id', '')} | {decision.get('title', '')}",
        f"Stage: {decision.get('stage_label', decision.get('stage', ''))}",
        f"Reason: {decision.get('reason', '')}",
    ])

    if full:
        preview = data.get("preview_cycle") or {}
        live = data.get("live_cycle") or {}
        if preview:
            lines.extend(["", "## Preview cycle", work_cycle_text(preview, full=False)])
        if live:
            lines.extend(["", "## Live cycle", work_cycle_text(live, full=False)])
        audit = data.get("audit") if isinstance(data.get("audit"), dict) else {}
        if audit:
            lines.extend(["", stable_loop_audit_text(audit, full=False)])
        lines.extend(["", "## Raw record", json.dumps(data, indent=2, default=str)])

    return "\n".join(lines).strip()


def print_stable_loop_preflight(project_id: Optional[str] = None, max_steps: int = 1, full: bool = False) -> None:
    data = build_stable_loop_preflight(project_id=project_id, max_steps=max_steps)
    print(stable_preflight_text(data, full=full))


def stable_preflight_text(data: dict[str, Any], full: bool = False) -> str:
    lines = [
        "# Stable loop preflight",
        "",
        f"Project: {data.get('project_id')}",
        f"OK: {data.get('ok')}",
        f"Safe mode: {data.get('safe_mode')}",
        f"Settings version: {data.get('settings_version')}",
        f"Effective steps: {data.get('effective_steps')} / cap {data.get('max_steps_cap')}",
        f"Pending approvals: {data.get('pending_approval_count')}",
        f"Cycle candidates: {data.get('candidate_count')}",
    ]
    lifecycle = data.get("lifecycle_summary") or {}
    recovery = data.get("recovery_summary") or {}
    lines.append(f"Open lifecycle tasks: {lifecycle.get('open', 0)}")
    lines.append(f"Needs attention: {lifecycle.get('needs_attention', 0)}")
    lines.append(f"Recoverable tasks: {recovery.get('recoverable', 0)}")
    guardrails = data.get("closure_guardrails") if isinstance(data.get("closure_guardrails"), dict) else {}
    if guardrails:
        lines.append(f"Closure guardrails live-ready: {guardrails.get('ok_for_live')}")
        lines.append(f"Closure blockers: {guardrails.get('unresolved_count', 0)}")

    decision = data.get("next_decision") or {}
    lines.extend([
        "",
        "Next decision:",
        f"- action: {decision.get('action', '')}",
        f"- task: {decision.get('task_id', '')} | {decision.get('title', '')}",
        f"- stage: {decision.get('stage_label', decision.get('stage', ''))}",
    ])

    if data.get("issues"):
        lines.append("Issues:")
        lines.extend(f"- {item}" for item in data.get("issues", []))
    if data.get("warnings"):
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in data.get("warnings", []))
    if full:
        lines.extend(["", "## Raw preflight", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_stable_loop(
    project_id: Optional[str] = None,
    max_steps: int = 1,
    live: bool = False,
    use_ai: bool = True,
    approve_work_execution: bool = False,
    seed_if_empty: bool = True,
    auto_create_patch_followups: bool = True,
    auto_request_approvals: bool = True,
    auto_retry_recovery: bool = False,
    bypass_closure_guardrails: bool = False,
    full: bool = False,
) -> None:
    result = run_stable_supervised_loop(
        project_id=project_id,
        max_steps=max_steps,
        live=live,
        use_ai=use_ai,
        approve_work_execution=approve_work_execution,
        seed_if_empty=seed_if_empty,
        auto_create_patch_followups=auto_create_patch_followups,
        auto_request_approvals=auto_request_approvals,
        auto_retry_recovery=auto_retry_recovery,
        bypass_closure_guardrails=bypass_closure_guardrails,
    )
    print(stable_loop_text(result, full=full))


def print_stable_loops(limit: int = 25) -> None:
    loops = list_stable_loops()[: max(1, min(limit, 100))]
    if not loops:
        print("No stable loop records found.")
        return
    for loop in loops:
        print(
            f"{loop.get('id')} | ok={loop.get('ok')} | live={loop.get('live')} | "
            f"preview={loop.get('preview_cycle_id', '')} | live_cycle={loop.get('live_cycle_id', '')} | stopped={loop.get('stopped_reason')}"
        )


def print_saved_stable_loop(loop_id: str = "latest", full: bool = False) -> None:
    loop = load_stable_loop(loop_id)
    if not loop:
        print(f"Stable loop not found: {loop_id}")
        return
    print(stable_loop_text(loop, full=full))
