from __future__ import annotations

"""Operator play/pause over long-running governed research work.

This is a control surface, not a second pause mechanism. Every request it accepts is forwarded to the existing
``cooperative_pause`` contract and the existing governed job runner; nothing here interrupts a provider call, changes
checkpoint semantics, creates a job, forks an activity or grants any authority.

Two halves:

* :func:`affordance` decides, from the activity record the read-only API already serves, what the operator may do
  right now. The decision lives here rather than in the browser so a refresh reflects backend state instead of
  whatever the page last assumed.
* :func:`control` performs one request. Pause writes the cooperative signal the worker reads at its next safe
  boundary. Resume clears that signal and restarts the same job record, which continues the same review from its
  sealed checkpoint after integrity verification.

A paused review is alive and expects to come back. A terminal one never runs again, and this module refuses to
suggest otherwise.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

CONTRACT = "research-control.v1"
RESEARCH_TYPES = ("experiment_review",)

# What the operator may ask for, and nothing else. Cancel is deliberately absent: pausing is reversible and this
# control is a play/pause, not a way to end work from a progress bar.
ACTIONS = ("pause", "resume")

_PAUSABLE = {"running", "preparing", "blocked"}
_TERMINAL = {"complete", "incomplete", "failed", "cancelled"}
# A job whose process died leaves a sealed checkpoint behind. That is interrupted work, not a finished review, so the
# control offers to continue it - but only when the checkpoint actually verifies, and resume still runs the full
# integrity check before any work restarts.
_RECOVERABLE_FAILURES = {"job_process_ended_without_result"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def affordance(activity: Mapping[str, Any], *, recoverable: bool = False) -> dict[str, Any]:
    """The one control this activity should show, as operational fact only.

    ``action`` is what a click would request, ``enabled`` whether it may be clicked, ``pending`` whether the backend
    is already working on a transition the operator asked for. A control with no action is shown disabled or not at
    all; it never offers to resume work that cannot be resumed.
    """
    state = str(activity.get("state") or "")
    kind = str(activity.get("type") or "")
    base = {"contract": CONTRACT, "activity_id": activity.get("activity_id", ""), "state": state,
            "action": "", "icon": "", "label": "", "tip": "", "enabled": False, "pending": False,
            "visible": kind in RESEARCH_TYPES, "reason": ""}
    if kind not in RESEARCH_TYPES:
        return {**base, "reason": "not_research_work"}
    if state in _TERMINAL:
        if recoverable:
            return {**base, "action": "resume", "icon": "play", "label": "Resume research", "enabled": True,
                    "tip": "This research was interrupted. Continue it from its saved checkpoint.",
                    "reason": "interrupted_with_checkpoint"}
        return {**base, "icon": "none", "label": "Research finished",
                "tip": f"This research is {state.replace('_', ' ')} and cannot be resumed.",
                "reason": f"terminal:{state}"}
    if state == "queued":
        return {**base, "icon": "pause", "label": "Pause research",
                "tip": "Research has not started yet.", "reason": "not_started"}
    if state == "pause_requested":
        return {**base, "action": "pause", "icon": "pause", "label": "Pausing…", "pending": True,
                "tip": "Finishing the current step, then saving a checkpoint.", "reason": "pause_in_progress"}
    if state == "paused":
        return {**base, "action": "resume", "icon": "play", "label": "Resume research", "enabled": True,
                "tip": "Continue this research from its saved checkpoint."}
    if state in _PAUSABLE:
        return {**base, "action": "pause", "icon": "pause", "label": "Pause research", "enabled": True,
                "tip": "Finish the current step, save a checkpoint, and stop."}
    return {**base, "reason": f"unknown_state:{state}"}


def resumable_checkpoint(job: Mapping[str, Any], root: str | Path) -> dict[str, Any]:
    """Whether work that stopped without a result still has a checkpoint worth continuing.

    Reports only what the checkpoint says about itself. No binding comparison happens here; ``control`` and the
    reviewer do that, and either may still refuse.
    """
    import cooperative_pause as pause

    status = str(job.get("status") or "")
    if status not in {"failed", "paused"}:
        return {"resumable": False, "reason": "job_not_interrupted"}
    failure = str(job.get("failure") or "")
    if status == "failed" and failure.split(":")[0] not in _RECOVERABLE_FAILURES:
        return {"resumable": False, "reason": "failure_not_recoverable"}
    try:
        controls = _controls_root(job, root)
        record = pause.load_checkpoint(str(job.get("job_id")), controls)
    except Exception as exc:
        return {"resumable": False, "reason": "checkpoint_unreadable:" + type(exc).__name__}
    if not record:
        return {"resumable": False, "reason": "no_checkpoint"}
    if str(record.get("status")) in {"complete", "incomplete", "cancelled"}:
        return {"resumable": False, "reason": "checkpoint_terminal"}
    return {"resumable": True, "completed_units": record.get("completed_unit_count", 0),
            "sequence": record.get("sequence"), "digest": str(record.get("digest") or "")}


def _job_record(job_id: str, root: str | Path) -> dict[str, Any]:
    import conversational_experiment_review as adapter

    record = adapter._read(adapter._job_path(job_id, root))
    if not record:
        raise LookupError("job_not_found")
    return record


def _controls_root(job: Mapping[str, Any], root: str | Path) -> Path:
    import experiment_review_hierarchical as hier

    manifest = str(job.get("manifest_sha256") or "")
    if not manifest:
        raise LookupError("job_has_no_package_binding")
    private = Path(job.get("private_runtime_root") or
                   Path(root) / "research_review_runtimes" / str(job.get("job_id")))
    return private / hier.REVIEW_AREA / hier.work_review_id(manifest, str(job.get("job_id")))


def control(job_id: str, action: str, root: str | Path) -> dict[str, Any]:
    """Perform one operator control request against existing governed work.

    Returns a content-minimized record. Never raises into the caller for an ordinary refusal; a refusal is a result.
    """
    import cooperative_pause as pause

    value = str(action or "").strip().lower()
    if value not in ACTIONS:
        return {"ok": False, "status": "unknown_action", "allowed": list(ACTIONS), "contract": CONTRACT}
    try:
        job = _job_record(str(job_id), root)
    except LookupError as exc:
        return {"ok": False, "status": str(exc), "contract": CONTRACT}
    status = str(job.get("status") or "")
    recovery = resumable_checkpoint(job, root)
    if status in {"completed", "cancelled"} or (status == "failed" and not recovery["resumable"]):
        return {"ok": False, "status": "job_already_terminal", "job_status": status,
                "recovery": recovery.get("reason", ""), "contract": CONTRACT}
    try:
        controls = _controls_root(job, root)
    except LookupError as exc:
        return {"ok": False, "status": str(exc), "contract": CONTRACT}

    if value == "pause":
        if status == "paused":
            return {"ok": True, "status": "already_paused", "job_id": job_id, "expect_state": "paused",
                    "contract": CONTRACT}
        if pause.pending(str(job_id), controls) == "pause":
            # Already asked for. Asking twice must not stack a second request or restart the countdown.
            return {"ok": True, "status": "pause_already_requested", "job_id": job_id,
                    "expect_state": "pause_requested", "contract": CONTRACT}
        pause.request(str(job_id), "pause", controls, note="operator pause from research progress control")
        return {"ok": True, "status": "pause_requested", "job_id": job_id, "expect_state": "pause_requested",
                "requested_at": _now(), "contract": CONTRACT}

    if status != "paused" and not (status == "failed" and recovery["resumable"]):
        return {"ok": False, "status": "job_not_paused", "job_status": status, "contract": CONTRACT}
    pause.clear(str(job_id), controls)
    spawned = _resume(job, root)
    return {"ok": True, "status": "resume_requested", "job_id": job_id, "expect_state": "running",
            "pid": spawned, "recovered_from_interruption": status == "failed",
            "completed_units": recovery.get("completed_units"), "requested_at": _now(), "contract": CONTRACT}


def _resume(job: Mapping[str, Any], root: str | Path) -> int:
    """Restart the same job record. The runner continues the same review from its checkpoint, or fails closed."""
    import conversational_experiment_review as adapter

    argv = [sys.executable, "-B", str(adapter.JOB_RUNNER), str(adapter._job_path(str(job.get("job_id")), root))]
    env = {**os.environ, "EIDOLON_DATA_DIR": str(adapter._root(root)), "PYTHONIOENCODING": "utf-8"}
    return int(adapter.SPAWN(argv, adapter.JOB_RUNNER.parents[1], env))


def decorate(payload: Mapping[str, Any], root: str | Path | None = None) -> dict[str, Any]:
    """Attach the control affordance to an activities API payload, in place of nothing else."""
    out = json.loads(json.dumps(payload))

    def recoverable(row: Mapping[str, Any]) -> bool:
        if root is None or str(row.get("state")) != "failed" or str(row.get("type")) not in RESEARCH_TYPES:
            return False
        try:
            return bool(resumable_checkpoint(_job_record(str(row.get("activity_id")), root), root)["resumable"])
        except Exception:
            return False

    rows = out.get("activities")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                row["control"] = affordance(row, recoverable=recoverable(row))
    row = out.get("activity")
    if isinstance(row, dict):
        row["control"] = affordance(row, recoverable=recoverable(row))
    return out
