from __future__ import annotations

"""Era 6 portable event loop and background-cognition scheduler contracts.

The scheduler persists content-free job definitions and produces bounded work
*tickets*.  It does not launch threads/processes, call providers, read private
content, mutate memories, or execute tools.  A native v2100 gate may connect
these tickets to already-governed read-only capabilities under explicit policy.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from json_storage import AtomicJsonWriteError, load_json_file, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR

CONTRACT_VERSION = "v2050.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era6_background_scheduler.json"
MAX_JOBS = 64
MAX_EVENTS = 512
MAX_TICKETS = 256
SAFE_WORK_KINDS = {
    "read_only_inspection",
    "memory_consolidation_review",
    "plan_review",
    "proposal_preparation",
}

_DENIED = {
    "job_executed": False,
    "process_started": False,
    "provider_contacted": False,
    "tool_executed": False,
    "memory_modified": False,
    "source_modified": False,
    "message_sent": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _now(value: datetime | None = None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _state_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "background_cognition" / STATE_FILE


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "enabled": False,
        "timezone_offset_minutes": 0,
        "quiet_start_hour": 22,
        "quiet_end_hour": 7,
        "max_tickets_per_tick": 2,
        "jobs": {},
        "tickets": [],
        "processed_events": [],
        "raw_content_persisted": False,
    }


def _valid_state(value: Any) -> dict[str, Any]:
    state = deepcopy(value) if isinstance(value, dict) else _default_state()
    defaults = _default_state()
    for key, default in defaults.items():
        state.setdefault(key, deepcopy(default))
    if not isinstance(state.get("jobs"), dict):
        state["jobs"] = {}
    if not isinstance(state.get("tickets"), list):
        state["tickets"] = []
    if not isinstance(state.get("processed_events"), list):
        state["processed_events"] = []
    state["max_tickets_per_tick"] = max(1, min(8, int(state.get("max_tickets_per_tick") or 2)))
    state["timezone_offset_minutes"] = max(-840, min(840, int(state.get("timezone_offset_minutes") or 0)))
    state["quiet_start_hour"] = max(0, min(23, int(state.get("quiet_start_hour") or 0)))
    state["quiet_end_hour"] = max(0, min(23, int(state.get("quiet_end_hour") or 0)))
    state["raw_content_persisted"] = False
    return state


def read_scheduler_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    return _valid_state(load_json_file(_state_path(runtime_root), _default_state(), expected_type=dict))


def _event_seen(state: Mapping[str, Any], digest: str) -> bool:
    return any(str(row.get("event_digest") or "") == digest for row in state.get("processed_events", []) if isinstance(row, Mapping))


def _public(state: Mapping[str, Any]) -> dict[str, Any]:
    row = _valid_state(state)
    jobs = []
    for job_id, job in sorted((row.get("jobs") or {}).items()):
        if isinstance(job, Mapping):
            jobs.append({
                "job_id": str(job_id),
                "work_kind": str(job.get("work_kind") or ""),
                "interval_minutes": int(job.get("interval_minutes") or 0),
                "priority_class": str(job.get("priority_class") or "normal"),
                "enabled": bool(job.get("enabled")),
                "next_due_at": str(job.get("next_due_at") or ""),
                "job_digest": str(job.get("job_digest") or ""),
            })
    tickets = [
        {
            "ticket_id": str(ticket.get("ticket_id") or ""),
            "job_id": str(ticket.get("job_id") or ""),
            "work_kind": str(ticket.get("work_kind") or ""),
            "status": str(ticket.get("status") or ""),
            "prepared_at": str(ticket.get("prepared_at") or ""),
            "ticket_digest": str(ticket.get("ticket_digest") or ""),
        }
        for ticket in row.get("tickets", [])[-32:] if isinstance(ticket, Mapping)
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": int(row.get("revision") or 0),
        "enabled": bool(row.get("enabled")),
        "timezone_offset_minutes": int(row.get("timezone_offset_minutes") or 0),
        "quiet_start_hour": int(row.get("quiet_start_hour") or 0),
        "quiet_end_hour": int(row.get("quiet_end_hour") or 0),
        "max_tickets_per_tick": int(row.get("max_tickets_per_tick") or 2),
        "jobs": jobs,
        "recent_tickets": tickets,
        "raw_content_persisted": False,
        **_DENIED,
    }
    result["state_digest"] = _digest(result)
    return result


def configure_scheduler(
    *, event_id: str, enabled: bool | None = None, timezone_offset_minutes: int | None = None,
    quiet_start_hour: int | None = None, quiet_end_hour: int | None = None,
    max_tickets_per_tick: int | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    token = str(event_id or "").strip()
    if not token:
        return {"ok": False, "status": "event_id_required", **_DENIED}
    path = _state_path(runtime_root)
    event_digest = _digest(token)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            if _event_seen(state, event_digest):
                return {"ok": True, "status": "scheduler_configuration_replayed", "state": _public(state), "idempotent": True, **_DENIED}
            if enabled is not None:
                state["enabled"] = bool(enabled)
            if timezone_offset_minutes is not None:
                state["timezone_offset_minutes"] = max(-840, min(840, int(timezone_offset_minutes)))
            if quiet_start_hour is not None:
                state["quiet_start_hour"] = max(0, min(23, int(quiet_start_hour)))
            if quiet_end_hour is not None:
                state["quiet_end_hour"] = max(0, min(23, int(quiet_end_hour)))
            if max_tickets_per_tick is not None:
                state["max_tickets_per_tick"] = max(1, min(8, int(max_tickets_per_tick)))
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now().isoformat()
            state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "at": state["updated_at"]}])[-MAX_EVENTS:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": "scheduler_configured", "state": _public(state), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "scheduler_write_blocked"), "safe_retry": bool(getattr(error, "safe_retry", True)), **_DENIED}


def upsert_background_job(
    *, job_id: str, work_kind: str, interval_minutes: int, priority_class: str,
    evidence_digest: str, event_id: str, runtime_root: str | Path | None = None, now: datetime | None = None,
) -> dict[str, Any]:
    job_id = str(job_id or "").strip()[:120]
    work_kind = str(work_kind or "").strip().lower()
    priority_class = str(priority_class or "normal").strip().lower()
    evidence_digest = str(evidence_digest or "").strip().lower()
    if not job_id or work_kind not in SAFE_WORK_KINDS:
        return {"ok": False, "status": "unsupported_or_missing_background_job", **_DENIED}
    if priority_class not in {"low", "normal", "high"}:
        return {"ok": False, "status": "unsupported_priority_class", **_DENIED}
    if len(evidence_digest) != 64 or any(ch not in "0123456789abcdef" for ch in evidence_digest):
        return {"ok": False, "status": "sha256_evidence_digest_required", **_DENIED}
    interval = max(15, min(10080, int(interval_minutes)))
    token = str(event_id or "").strip()
    if not token:
        return {"ok": False, "status": "event_id_required", **_DENIED}
    path = _state_path(runtime_root)
    current = _now(now)
    event_digest = _digest(token)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            if _event_seen(state, event_digest):
                return {"ok": True, "status": "background_job_upsert_replayed", "state": _public(state), "idempotent": True, **_DENIED}
            if job_id not in state["jobs"] and len(state["jobs"]) >= MAX_JOBS:
                return {"ok": False, "status": "background_job_limit_reached", "state": _public(state), **_DENIED}
            job = {
                "job_id": job_id,
                "work_kind": work_kind,
                "interval_minutes": interval,
                "priority_class": priority_class,
                "evidence_digest": evidence_digest,
                "enabled": True,
                "lifecycle_state": "active",
                "updated_at": current.isoformat(),
                "next_due_at": current.isoformat(),
            }
            job["job_digest"] = _digest(job)
            state["jobs"][job_id] = job
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = current.isoformat()
            state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "at": state["updated_at"]}])[-MAX_EVENTS:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": "background_job_upserted", "job": deepcopy(job), "state": _public(state), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "background_job_write_blocked"), **_DENIED}


def _quiet(state: Mapping[str, Any], current: datetime) -> bool:
    local = current + timedelta(minutes=int(state.get("timezone_offset_minutes") or 0))
    hour = local.hour
    start = int(state.get("quiet_start_hour") or 0)
    end = int(state.get("quiet_end_hour") or 0)
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def scheduler_tick(
    *, tick_id: str, runtime_root: str | Path | None = None, now: datetime | None = None,
    foreground_busy: bool = False, provider_available: bool = True, resource_pressure: str = "normal",
) -> dict[str, Any]:
    """Prepare due work tickets; never execute them."""
    token = str(tick_id or "").strip()
    if not token:
        return {"ok": False, "status": "tick_id_required", **_DENIED}
    pressure = str(resource_pressure or "normal").strip().lower()
    if pressure not in {"idle", "normal", "elevated", "critical"}:
        return {"ok": False, "status": "invalid_resource_pressure", **_DENIED}
    path = _state_path(runtime_root)
    current = _now(now)
    event_digest = _digest(token)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            if _event_seen(state, event_digest):
                return {"ok": True, "status": "scheduler_tick_replayed", "state": _public(state), "tickets_prepared": 0, "idempotent": True, **_DENIED}
            reasons: list[str] = []
            allowed = bool(state.get("enabled"))
            if not allowed:
                reasons.append("scheduler_disabled")
            if _quiet(state, current):
                allowed = False; reasons.append("quiet_hours")
            if foreground_busy:
                allowed = False; reasons.append("foreground_busy")
            if pressure in {"elevated", "critical"}:
                allowed = False; reasons.append("resource_pressure")
            # Provider availability is only relevant to proposal preparation; no provider is contacted here.
            prepared: list[dict[str, Any]] = []
            if allowed:
                jobs = []
                for job in state.get("jobs", {}).values():
                    if not isinstance(job, Mapping) or not job.get("enabled"):
                        continue
                    due = _parse_iso(job.get("next_due_at"))
                    if due is None or due <= current:
                        jobs.append(dict(job))
                rank = {"high": 0, "normal": 1, "low": 2}
                jobs.sort(key=lambda row: (rank.get(str(row.get("priority_class") or "normal"), 1), str(row.get("job_id") or "")))
                for job in jobs[: int(state.get("max_tickets_per_tick") or 2)]:
                    if job.get("work_kind") == "proposal_preparation" and not provider_available:
                        continue
                    slot = current.replace(second=0, microsecond=0).isoformat()
                    ticket_key = _digest({"job_digest": job.get("job_digest"), "slot": slot})
                    if any(str(t.get("ticket_key") or "") == ticket_key for t in state.get("tickets", []) if isinstance(t, Mapping)):
                        continue
                    ticket = {
                        "ticket_id": f"bg_{ticket_key[:24]}",
                        "ticket_key": ticket_key,
                        "job_id": job["job_id"],
                        "work_kind": job["work_kind"],
                        "priority_class": job["priority_class"],
                        "evidence_digest": job["evidence_digest"],
                        "prepared_at": current.isoformat(),
                        "status": "prepared_not_executed",
                        "execution_authorized": False,
                    }
                    ticket["ticket_digest"] = _digest(ticket)
                    prepared.append(ticket)
                    state["tickets"].append(ticket)
                    next_due = current + timedelta(minutes=int(job.get("interval_minutes") or 60))
                    state["jobs"][job["job_id"]]["next_due_at"] = next_due.isoformat()
            state["tickets"] = state.get("tickets", [])[-MAX_TICKETS:]
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = current.isoformat()
            state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "at": state["updated_at"]}])[-MAX_EVENTS:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {
                "ok": True,
                "status": "background_tickets_prepared" if prepared else "background_tick_quiet",
                "tickets_prepared": len(prepared),
                "tickets": deepcopy(prepared),
                "suppression_reasons": reasons,
                "state": _public(state),
                "idempotent": False,
                **_DENIED,
            }
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "scheduler_tick_write_blocked"), "safe_retry": bool(getattr(error, "safe_retry", True)), **_DENIED}


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def public_scheduler_state(state: Mapping[str, Any]) -> dict[str, Any]:
    return _public(state)


def control_background_job(
    action: str, *, job_id: str, expected_state_digest: str, event_id: str,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Pause, resume, or cancel a durable job without executing it."""
    action = str(action or "").strip().lower()
    if action not in {"pause", "resume", "cancel"}:
        return {"ok": False, "status": "unsupported_background_job_control", **_DENIED}
    job_id = str(job_id or "").strip()[:120]
    token = str(event_id or "").strip()
    if not job_id or not token:
        return {"ok": False, "status": "job_id_and_event_id_required", **_DENIED}
    path = _state_path(runtime_root)
    event_digest = _digest(token)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            public = _public(state)
            if str(expected_state_digest or "") != str(public.get("state_digest") or ""):
                return {"ok": False, "status": "stale_scheduler_state_digest", "state": public, **_DENIED}
            if _event_seen(state, event_digest):
                return {"ok": True, "status": "background_job_control_replayed", "state": public, "idempotent": True, **_DENIED}
            job = state.get("jobs", {}).get(job_id)
            if not isinstance(job, dict):
                return {"ok": False, "status": "background_job_not_found", "state": public, **_DENIED}
            if action == "cancel":
                job["enabled"] = False
                job["lifecycle_state"] = "cancelled"
            elif action == "pause":
                job["enabled"] = False
                job["lifecycle_state"] = "paused"
            else:
                if str(job.get("lifecycle_state") or "") == "cancelled":
                    return {"ok": False, "status": "cancelled_background_job_not_resumable", "state": public, **_DENIED}
                job["enabled"] = True
                job["lifecycle_state"] = "active"
            job["updated_at"] = _now().isoformat()
            job["job_digest"] = _digest({key: value for key, value in job.items() if key != "job_digest"})
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = job["updated_at"]
            state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "at": state["updated_at"]}])[-MAX_EVENTS:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": f"background_job_{action}d", "state": _public(state), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "background_job_control_write_blocked"), **_DENIED}


def record_background_ticket_outcome(
    *, ticket_id: str, expected_ticket_digest: str, outcome: str, outcome_evidence_digest: str,
    event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Record content-free executor evidence; does not execute the ticket itself."""
    ticket_id = str(ticket_id or "").strip()[:120]
    outcome = str(outcome or "").strip().lower()
    evidence = str(outcome_evidence_digest or "").strip().lower()
    token = str(event_id or "").strip()
    if outcome not in {"completed_read_only", "deferred", "failed", "cancelled"}:
        return {"ok": False, "status": "unsupported_ticket_outcome", **_DENIED}
    if not ticket_id or not token or len(evidence) != 64 or any(ch not in "0123456789abcdef" for ch in evidence):
        return {"ok": False, "status": "ticket_event_and_sha256_evidence_required", **_DENIED}
    path = _state_path(runtime_root)
    event_digest = _digest(token)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            if _event_seen(state, event_digest):
                return {"ok": True, "status": "ticket_outcome_replayed", "state": _public(state), "idempotent": True, **_DENIED}
            ticket = next((row for row in state.get("tickets", []) if isinstance(row, dict) and row.get("ticket_id") == ticket_id), None)
            if ticket is None:
                return {"ok": False, "status": "background_ticket_not_found", "state": _public(state), **_DENIED}
            if str(ticket.get("ticket_digest") or "") != str(expected_ticket_digest or ""):
                return {"ok": False, "status": "stale_background_ticket_digest", "state": _public(state), **_DENIED}
            if str(ticket.get("status") or "") != "prepared_not_executed":
                return {"ok": False, "status": "background_ticket_already_terminal", "state": _public(state), **_DENIED}
            ticket["status"] = outcome
            ticket["outcome_evidence_digest"] = evidence
            ticket["completed_at"] = _now().isoformat()
            ticket["execution_authority_inferred"] = False
            ticket["ticket_digest"] = _digest({key: value for key, value in ticket.items() if key != "ticket_digest"})
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = ticket["completed_at"]
            state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "at": state["updated_at"]}])[-MAX_EVENTS:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": "background_ticket_outcome_recorded", "state": _public(state), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "background_ticket_outcome_write_blocked"), **_DENIED}


__all__ = [
    "CONTRACT_VERSION", "SAFE_WORK_KINDS", "read_scheduler_state", "configure_scheduler",
    "upsert_background_job", "scheduler_tick", "public_scheduler_state", "control_background_job", "record_background_ticket_outcome",
]
