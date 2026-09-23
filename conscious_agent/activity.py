"""Content-minimized operational activity. Single-writer snapshots, pure reads.

Producers own execution; this module grants no authority and starts no work.
Runtime snapshots are disposable observability, never scientific evidence.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import re
import time
from threading import RLock
from typing import Any

from json_storage import write_text_atomic

CONTRACT = "activity.v1"
TERMINAL = frozenset({"complete", "incomplete", "failed", "cancelled"})
# pause_requested and paused are alive, not terminal: a paused producer expects to be resumed and its record keeps
# accepting events. Cancelled stays terminal and separate - it is the state that means the work will not continue.
PAUSE_STATES = frozenset({"pause_requested", "paused"})
STATES = TERMINAL | PAUSE_STATES | {"queued", "preparing", "running", "blocked"}
AREA = "activities"
MAX_EVENTS = 1000


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _root(root=None) -> Path:
    if root is not None:
        return Path(root)
    from runtime_data_bootstrap import default_runtime_data_dir
    return default_runtime_data_dir()


def _id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise ValueError("invalid_activity_id")
    return value


def progress(completed=0, total=None, unit="units") -> dict:
    if type(completed) is not int or completed < 0:
        raise ValueError("invalid_completed_units")
    if total is not None and (type(total) is not int or total < completed):
        raise ValueError("invalid_total_units")
    return {"completed": completed, "total": total, "unit": str(unit)[:60],
            "percent": round(100 * completed / total, 1) if total else None}


# States during which the clock runs. A paused producer is doing nothing, and counting that as elapsed work told the
# operator a stopped review was still going. Blocked stays active: it means a running producer we have lost contact
# with, which is unresolved rather than deliberately stopped.
ACTIVE_STATES = frozenset({"preparing", "running", "blocked"})


def _stamp(value):
    return datetime.fromisoformat(value)


def project(record: dict, instant: str | None = None) -> dict:
    out = deepcopy(record)
    moment = instant or now()
    try:
        end = _stamp(out.get("finished") or moment)
        start = _stamp(out["started"])
        out["wall_elapsed_seconds"] = max(0, int((end - start).total_seconds()))
    except (ValueError, KeyError, TypeError):
        out["wall_elapsed_seconds"] = None
    if "active_seconds" in out:
        # Accumulated active duration, plus whatever the current running segment has added so far. Wall clock stays
        # available beside it, so the span from start to finish is still reconstructible.
        try:
            seconds = float(out.get("active_seconds") or 0.0)
            since = out.get("active_since")
            if since and out.get("state") not in TERMINAL:
                seconds += max(0.0, (_stamp(moment) - _stamp(since)).total_seconds())
            out["elapsed_seconds"] = max(0, int(seconds))
        except (ValueError, TypeError):
            out["elapsed_seconds"] = None
    else:
        # Records written before active accounting existed keep their original wall-clock reading rather than
        # silently reporting zero.
        out["elapsed_seconds"] = out["wall_elapsed_seconds"]
    out["terminal"] = out.get("state") in TERMINAL
    return out


class Activity:
    """One producer owns one ID. A lock serializes its events and atomic snapshots.

    Fields are explicitly selected by trusted producers; never pass prompts,
    responses, exception text or arbitrary runtime dictionaries as metadata.
    """
    def __init__(self, activity_id, activity_type, title, subject, *, root=None, stages=(),
                 identities=None, governance=None, clock=now, started=None):
        self.root, self.clock, self.lock = _root(root), clock, RLock()
        self.path = self.root / AREA / (_id(activity_id) + ".json")
        self.record = {"contract": CONTRACT, "activity_id": activity_id, "type": activity_type,
                       "title": str(title)[:180], "subject": str(subject)[:180], "state": "queued",
                       "stage": "", "started": started or clock(), "finished": None, "updated": clock(),
                       "progress": progress(), "stage_progress": progress(), "metrics": {},
                       "active_seconds": 0.0, "active_since": None,
                       "warnings": [], "reason": "", "result": "", "identities": dict(identities or {}),
                       "governance": dict(governance or {}), "breakdown": [], "events": [],
                       "events_omitted": 0, "sequence": 0,
                       "stages": [{"name": s, "state": "pending"} for s in stages]}
        if self.path.exists():
            raise FileExistsError("activity_id_already_exists")
        self.update("job_queued")

    @classmethod
    def reopen(cls, activity_id, *, root=None, clock=now):
        """Continue an activity that is still alive, so paused work keeps one identity and one history.

        Refuses a terminal record rather than forking a second activity for the same work: a caller that cannot
        safely continue must say so, not fabricate continuity.
        """
        obj = cls.__new__(cls)
        obj.root, obj.clock, obj.lock = _root(root), clock, RLock()
        obj.path = obj.root / AREA / (_id(activity_id) + ".json")
        if not obj.path.is_file():
            raise FileNotFoundError("activity_not_found")
        obj.record = json.loads(obj.path.read_text(encoding="utf-8"))
        if obj.record.get("state") in TERMINAL:
            raise ValueError("activity_already_terminal")
        return obj

    def _accrue_active_time(self, stamp):
        """Bank the running segment when work stops, and open a new one when it starts.

        Called on every update, before ``updated`` moves, so a segment is measured from the last event that left the
        activity active to the one that stopped it. Pausing closes the segment; resuming opens another; a terminal
        state closes it for good. Nothing accrues while paused, which is the whole point.
        """
        if "active_seconds" not in self.record:
            # A record written before active accounting existed. Start measuring from here rather than inventing a
            # history for it.
            self.record["active_seconds"] = 0.0
            self.record["active_since"] = None
        state, since = self.record["state"], self.record.get("active_since")
        active = state in ACTIVE_STATES
        if since and not active:
            try:
                self.record["active_seconds"] = round(
                    float(self.record["active_seconds"]) + max(0.0, (_stamp(stamp) - _stamp(since)).total_seconds()), 3)
            except (ValueError, TypeError):
                pass
            self.record["active_since"] = None
        elif active and not since:
            self.record["active_since"] = stamp

    def update(self, event, *, state=None, stage=None, units=None, stage_units=None,
               metrics=None, governance=None, breakdown=None, reason=None, result=None, identities=None):
        with self.lock:
            if self.record["state"] in TERMINAL:
                raise ValueError("activity_already_terminal")
            if state is not None and state not in STATES:
                raise ValueError("invalid_activity_state")
            old = self.record["stage"]
            if stage and stage != old:
                for row in self.record["stages"]:
                    if row["name"] == old and row["state"] in {"running", "preparing"}:
                        row["state"] = "complete"
                if stage not in {r["name"] for r in self.record["stages"]}:
                    self.record["stages"].append({"name": stage, "state": "pending"})
                self.record["stage"] = stage
                self.record["stage_progress"] = progress()
            if state:
                self.record["state"] = state
            for row in self.record["stages"]:
                if row["name"] == self.record["stage"]:
                    row["state"] = self.record["state"]
            for field, value in (("progress", units), ("stage_progress", stage_units)):
                if value is not None:
                    self.record[field] = progress(value[0], value[1], value[2])
            if metrics:
                if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in metrics.values()):
                    raise ValueError("metrics_must_be_nonnegative_finite_counts")
                self.record["metrics"].update(metrics)
            for field, value in (("governance", governance), ("identities", identities)):
                if value is not None:
                    self.record[field].update(value)
            for field, value in (("breakdown", breakdown), ("reason", reason), ("result", result)):
                if value is not None:
                    self.record[field] = deepcopy(value)
            stamp = self.clock()
            self._accrue_active_time(stamp)
            self.record["updated"] = stamp
            if self.record["state"] in TERMINAL:
                self.record["finished"] = stamp
            self.record["sequence"] += 1
            self.record["events"].append({"sequence": self.record["sequence"], "at": stamp,
                                          "event": str(event)[:100], "stage": self.record["stage"],
                                          "state": self.record["state"]})
            excess = max(0, len(self.record["events"]) - MAX_EVENTS)
            self.record["events_omitted"] += excess
            self.record["events"] = self.record["events"][-MAX_EVENTS:]
            try:
                content = json.dumps(self.record, ensure_ascii=True, allow_nan=False)
                # Windows readers can briefly deny replacement while holding a file.
                for attempt in range(6):
                    try:
                        write_text_atomic(self.path, content)
                        break
                    except PermissionError:
                        if attempt == 5:
                            raise
                        time.sleep(0.01 * (attempt + 1))
            except Exception:
                if "activity_persistence_failed" not in self.record["warnings"]:
                    self.record["warnings"].append("activity_persistence_failed")
                logging.getLogger(__name__).warning("Activity persistence failed for %s", self.record["activity_id"])
            return project(self.record, stamp)


def _read(path):
    for attempt in range(6):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            return row if isinstance(row, dict) else None
        except PermissionError:
            if attempt < 5:
                time.sleep(0.01 * (attempt + 1))
        except (OSError, ValueError):
            return None
    return None


def _job_projection(job: dict) -> dict:
    """Older jobs are projected, never migrated or rewritten by a read."""
    state = {"starting": "queued", "running": "running", "failed": "failed"}.get(job.get("status"), "incomplete")
    if job.get("status") == "completed":
        state = {"complete": "complete", "mutation_guard_failed": "failed"}.get(job.get("review_status"), "incomplete")
    cov, checks = job.get("coverage") or {}, job.get("checks") or {}
    return {"contract": CONTRACT, "activity_id": job["job_id"], "type": "experiment_review",
            "title": "Independent experiment review", "subject": job.get("package_id", ""), "state": state,
            "stage": "Finished" if state in TERMINAL else "Progress unavailable (legacy job)",
            "started": job.get("started"), "finished": job.get("finished"), "updated": job.get("updated"),
            "progress": progress(cov.get("reviewed_required_parts") or 0, cov.get("required_parts"), "required parts"),
            "stage_progress": progress(), "metrics": {}, "events": [], "stages": [], "breakdown": [],
            "warnings": ["historical_job_without_live_telemetry"], "reason": "review_job_failed" if job.get("failure") else job.get("review_status", ""),
            "result": job.get("review_status", ""), "identities": {k: job.get(k, "") for k in
                ("job_id", "task_id", "package_id", "review_id", "reviewer_contract")},
            "governance": {"non_authoritative": checks.get("non_authoritative"),
                           "mutation_guard": "passed" if checks.get("mutation_guard_passed") is True else
                           "failed" if checks.get("mutation_guard_passed") is False else "unverified"}}


def activities(root=None, *, activity_id=None, limit=100) -> dict[str, Any]:
    """Pure bounded filesystem projection. Never invokes job_status/_refresh.

    An interrupted producer is displayed as blocked after heartbeat staleness,
    not silently completed, failed, resumed or persisted by GET.
    """
    base = _root(root)
    if activity_id:
        _id(activity_id)
    records = {}
    paths = [base / AREA / f"{activity_id}.json"] if activity_id else sorted(
        (base / AREA).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    warnings = []
    for path in paths:
        row = _read(path)
        if row and row.get("contract") == CONTRACT and row.get("activity_id") == path.stem:
            records[path.stem] = row
        elif path.exists():
            warnings.append("unreadable_activity_record")
    jobs = [base / "research_jobs" / f"{activity_id}.json"] if activity_id else sorted(
        (base / "research_jobs").glob("job_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    for path in jobs:
        job = _read(path)
        if not job or job.get("job_id") != path.stem:
            continue
        if path.stem not in records:
            records[path.stem] = _job_projection(job)
        elif job.get("status") in {"completed", "failed"}:
            # Authoritative job terminality wins over interrupted telemetry publishing.
            terminal = _job_projection(job)
            row = records[path.stem]
            if row.get("state") not in TERMINAL:
                row.update({k: terminal[k] for k in ("state", "finished", "reason", "result")})
                row["warnings"] = list(row.get("warnings", [])) + ["terminal_state_reconciled_from_job"]
    stamp = now()
    output = []
    for row in records.values():
        item = project(row, stamp)
        try:
            stale = (datetime.fromisoformat(stamp) - datetime.fromisoformat(item["updated"])).total_seconds() > 90
        except (ValueError, TypeError, KeyError):
            stale = True
        # Staleness is evidence about work that is supposed to be running. A paused producer has finished its unit,
        # sealed a checkpoint and exited on purpose, so its heartbeats stop by design: calling that "execution state
        # unconfirmed" turned a deliberate pause into an apparent fault, and because blocked counts as pausable the
        # operator was offered Pause again instead of Play. Intentionally quiescent is not the same as stale.
        if (stale and item["state"] not in TERMINAL and item["state"] not in PAUSE_STATES
                and item["state"] != "blocked"):
            item.update(state="blocked", reason="progress_heartbeat_stale; execution state unconfirmed")
            item["warnings"] = list(item.get("warnings", [])) + ["stale_telemetry"]
        output.append(item)
    output.sort(key=lambda r: str(r.get("started") or ""), reverse=True)
    active = [r for r in output if not r["terminal"]]
    return {"contract": CONTRACT, "current": active[0] if active else None,
            "active_count": len(active), "activities": output[:limit], "warnings": warnings,
            "observed_at": stamp}
