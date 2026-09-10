from __future__ import annotations

"""v1253.9.2 bounded internal maintenance queue with process-safe coalescing.

Only explicitly allowlisted, content-free local housekeeping is accepted. Jobs
have a persisted ``pending``/``running`` lifecycle, stale running jobs are
reconciled only from explicit scheduler/startup hooks, and global housekeeping
is coalesced globally with a short cooldown. The queue cannot contact providers,
execute user tools, mutate projects, consume approvals, or grant authority.
"""

import json
import os
import queue
import threading
import time
import uuid
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import DATA_DIR

CONTRACT_VERSION = "v1253.1"
RUNTIME_REPAIR_VERSION = "v1253.9.2"
SCHEMA_VERSION = "3"
MAX_PENDING_JOBS = 64
GLOBAL_COOLDOWN_SECONDS = 2.0
_ALLOWED = {"projection_cache_prune", "persistent_index_health_sample"}
_GLOBAL_KINDS = frozenset(_ALLOWED)
_Q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=MAX_PENDING_JOBS)
_LOCK = threading.RLock()
_WORKER: threading.Thread | None = None
_SCHEDULED: set[str] = set()
_STATS = {
    "queued": 0,
    "coalesced": 0,
    "cooldown_coalesced": 0,
    "resumed": 0,
    "completed": 0,
    "failed": 0,
    "dropped": 0,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _path() -> Path:
    return DATA_DIR / "performance" / "bounded_internal_maintenance.json"


def _lock_path() -> Path:
    return _path().with_suffix(".lock")


@contextmanager
def _process_lock(timeout_seconds: float = 10.0):
    """Serialize persisted state transitions across dashboard and CLI processes."""
    path = _lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + max(0.1, timeout_seconds)
        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("bounded_internal_maintenance_lock_timeout")
                    time.sleep(0.01)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("bounded_internal_maintenance_lock_timeout")
                    time.sleep(0.01)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "jobs": [],
        "recent_completed": {},
    }


def _normalize_job(row: dict[str, Any]) -> dict[str, Any] | None:
    kind = str(row.get("kind") or "")
    job_id = str(row.get("job_id") or "")
    if kind not in _ALLOWED or not job_id:
        return None
    state = str(row.get("state") or "pending")
    if state not in {"pending", "running"}:
        state = "pending"
    return {
        "job_id": job_id,
        "kind": kind,
        "dedupe_key": str(row.get("dedupe_key") or "global")[:120],
        "state": state,
        "created_at": str(row.get("created_at") or _now()),
        "updated_at": str(row.get("updated_at") or row.get("created_at") or _now()),
        "owner_pid": max(0, int(row.get("owner_pid") or 0)),
        "content_free": True,
    }


def _load() -> dict[str, Any]:
    path = _path()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        value = {}
    if not isinstance(value, dict):
        value = {}
    jobs: list[dict[str, Any]] = []
    for row in value.get("jobs") or []:
        if isinstance(row, dict):
            normalized = _normalize_job(row)
            if normalized is not None:
                jobs.append(normalized)
    recent_raw = value.get("recent_completed") or {}
    recent: dict[str, float] = {}
    if isinstance(recent_raw, dict):
        for key, val in recent_raw.items():
            if isinstance(val, (int, float)):
                recent[str(key)] = float(val)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "jobs": jobs[-MAX_PENDING_JOBS:],
        "recent_completed": recent,
    }


def _write(state: dict[str, Any]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _execute(job: dict[str, Any]) -> None:
    kind = str(job.get("kind") or "")
    if kind == "projection_cache_prune":
        try:
            from runtime_projection_cache import prune_projection_cache
        except ImportError:
            from runtime_projection_cache import prune_projection_cache
        prune_projection_cache()
        return
    if kind == "persistent_index_health_sample":
        try:
            from persistent_state_index import persistent_state_index_status
            persistent_state_index_status(DATA_DIR)
        except (ImportError, AttributeError):
            return
        return
    raise ValueError("unsupported_internal_maintenance_kind")


def _finish(job_id: str, ok: bool) -> None:
    with _LOCK:
        with _process_lock():
            state = _load()
            state["jobs"] = [row for row in state["jobs"] if str(row.get("job_id") or "") != job_id]
            state["recent_completed"][job_id] = time.time()
            cutoff = time.time() - max(30.0, GLOBAL_COOLDOWN_SECONDS * 10.0)
            state["recent_completed"] = {
                key: stamp for key, stamp in state["recent_completed"].items() if stamp >= cutoff
            }
            _write(state)
            _SCHEDULED.discard(job_id)
            _STATS["completed" if ok else "failed"] += 1


def _worker() -> None:
    while True:
        job = _Q.get()
        job_id = str(job.get("job_id") or "")
        ok = True
        try:
            _execute(job)
        except Exception:
            ok = False
        finally:
            try:
                _finish(job_id, ok)
            finally:
                _Q.task_done()


def _ensure_worker_locked() -> None:
    global _WORKER
    if _WORKER is None or not _WORKER.is_alive():
        _WORKER = threading.Thread(target=_worker, name="eidolon-bounded-maintenance", daemon=True)
        _WORKER.start()


def _schedule_persisted_locked(*, reconcile_stale_running: bool) -> int:
    _ensure_worker_locked()
    state = _load()
    changed = False
    to_queue: list[dict[str, Any]] = []
    available_slots = max(0, MAX_PENDING_JOBS - _Q.qsize())
    for row in state["jobs"]:
        job_id = str(row.get("job_id") or "")
        if not job_id or str(row.get("kind") or "") not in _ALLOWED:
            continue
        if row.get("state") == "running" and job_id not in _SCHEDULED and reconcile_stale_running:
            owner_pid = int(row.get("owner_pid") or 0)
            if not _pid_is_alive(owner_pid):
                row["state"] = "pending"
                row["owner_pid"] = 0
                row["updated_at"] = _now()
                changed = True
                _STATS["resumed"] += 1
        if row.get("state") != "pending" or job_id in _SCHEDULED:
            continue
        if len(to_queue) >= available_slots:
            break
        row["state"] = "running"
        row["owner_pid"] = os.getpid()
        row["updated_at"] = _now()
        _SCHEDULED.add(job_id)
        to_queue.append(deepcopy(row))
        changed = True
    # Persist the running transition before exposing a job to the worker. The
    # worker blocks on _LOCK in _finish(), so it cannot remove a job and then
    # be resurrected by a stale scheduler write.
    if changed:
        _write(state)
    for row in to_queue:
        job_id = str(row.get("job_id") or "")
        try:
            _Q.put_nowait(row)
        except queue.Full:
            # Extremely defensive fallback: restore the persisted state to
            # pending so a later explicit scheduler hook can retry it.
            _SCHEDULED.discard(job_id)
            retry_state = _load()
            for persisted in retry_state["jobs"]:
                if str(persisted.get("job_id") or "") == job_id:
                    persisted["state"] = "pending"
                    persisted["owner_pid"] = 0
                    persisted["updated_at"] = _now()
                    break
            _write(retry_state)
            _STATS["dropped"] += 1
    return len(to_queue)


def resume_pending_internal_maintenance() -> dict[str, Any]:
    """Explicit startup/scheduler hook for restart-persisted housekeeping."""
    with _LOCK:
        with _process_lock():
            count = _schedule_persisted_locked(reconcile_stale_running=True)
    return {
        "ok": True,
        "scheduled": count,
        "restart_persistent": True,
        "restart_resume_hook": True,
        "content_free": True,
        "authority_granted": False,
    }


def enqueue_internal_maintenance(kind: str, *, dedupe_key: str = "global") -> dict[str, Any]:
    token = str(kind or "").strip()
    if token not in _ALLOWED:
        raise ValueError("internal_maintenance_kind_not_allowlisted")
    key = "global" if token in _GLOBAL_KINDS else str(dedupe_key or "global")[:120]
    job_id = f"{token}:{key}"
    now_epoch = time.time()
    with _LOCK:
        with _process_lock():
            state = _load()
            if any(str(row.get("job_id") or "") == job_id for row in state["jobs"]):
                _STATS["coalesced"] += 1
                _schedule_persisted_locked(reconcile_stale_running=False)
                return {"ok": True, "status": "coalesced", "job_id": job_id, "kind": token, "content_free": True, "authority_granted": False}
            completed_at = state["recent_completed"].get(job_id)
            if isinstance(completed_at, (int, float)) and now_epoch - float(completed_at) < GLOBAL_COOLDOWN_SECONDS:
                _STATS["coalesced"] += 1
                _STATS["cooldown_coalesced"] += 1
                return {"ok": True, "status": "cooldown_coalesced", "job_id": job_id, "kind": token, "content_free": True, "authority_granted": False}
            state["jobs"].append({
                "job_id": job_id,
                "kind": token,
                "dedupe_key": key,
                "state": "pending",
                "created_at": _now(),
                "updated_at": _now(),
                "owner_pid": 0,
                "content_free": True,
            })
            state["jobs"] = state["jobs"][-MAX_PENDING_JOBS:]
            _write(state)
            _STATS["queued"] += 1
            _schedule_persisted_locked(reconcile_stale_running=False)
    return {"ok": True, "status": "queued", "job_id": job_id, "kind": token, "content_free": True, "authority_granted": False}


def schedule_post_turn_housekeeping(session_id: str = "") -> dict[str, Any]:
    del session_id  # Both current jobs are global; session-scoped keys would defeat coalescing.
    receipts = []
    for kind in ("projection_cache_prune", "persistent_index_health_sample"):
        try:
            receipts.append(enqueue_internal_maintenance(kind, dedupe_key="global"))
        except Exception as error:
            receipts.append({"ok": False, "kind": kind, "error_type": type(error).__name__, "content_free": True, "authority_granted": False})
    return {"ok": all(row.get("ok") for row in receipts), "receipts": receipts, "content_free": True, "authority_granted": False}


def internal_maintenance_status() -> dict[str, Any]:
    with _LOCK:
        with _process_lock():
            state = _load()
            pending = sum(1 for row in state["jobs"] if row.get("state") == "pending")
            running = sum(1 for row in state["jobs"] if row.get("state") == "running")
            return {
                "ok": True,
                "contract_version": CONTRACT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "pending": pending,
                "running": running,
                "persisted_jobs": len(state["jobs"]),
                "max_pending": MAX_PENDING_JOBS,
                "allowed_kinds": sorted(_ALLOWED),
                "global_cooldown_seconds": GLOBAL_COOLDOWN_SECONDS,
                "stats": dict(_STATS),
                "restart_persistent": True,
                "restart_resume_hook": True,
                "exact_pending_running_lifecycle": True,
                "global_housekeeping_coalesced": True,
                "cross_process_coalescing": True,
                "content_free_jobs": True,
                "provider_contact_authorized": False,
                "tool_execution_authorized": False,
                "project_mutation_authorized": False,
                "approval_granted": False,
                "independent_authority_granted": False,
            }


__all__ = [
    "CONTRACT_VERSION", "SCHEMA_VERSION", "MAX_PENDING_JOBS", "GLOBAL_COOLDOWN_SECONDS",
    "enqueue_internal_maintenance", "resume_pending_internal_maintenance",
    "schedule_post_turn_housekeeping", "internal_maintenance_status",
]
