from __future__ import annotations

"""Cooperative pause, durable checkpoints and integrity-checked resume for long-running governed work.

This grants no authority and starts nothing. It gives a worker three things:

* a **signal** an operator can raise (``pause`` or ``cancel``) that the worker reads only at its own safe boundaries;
* a **durable checkpoint** written atomically, digest-sealed, and bound to everything that must not have changed;
* a **resume verification** that fails closed on any drift rather than continuing against different inputs.

The contract is deliberately cooperative. Nothing here interrupts a synchronous provider call or kills a thread: a
pause request is observed between atomic units, the unit in flight finishes, its result is checkpointed, and only then
does the work stop. An operator who wants to abandon the work asks for ``cancel``, which is a different, terminal
thing - a paused activity is still alive and expects to be resumed, a cancelled one never runs again.

Lifecycle::

    running -> pause_requested -> (current atomic unit finishes) -> checkpoint written -> paused
            -> [resources released] -> operator resume -> integrity verified -> running

Nothing here is specific to reviews, research runs or any experiment. A worker supplies its own work-unit identifiers
and its own state payload; this module only sequences, seals and verifies them.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from json_storage import write_text_atomic

CONTRACT = "cooperative-pause.v1"
CHECKPOINT_CONTRACT = "work-checkpoint.v1"
CONTROL_AREA = "pause_controls"
CHECKPOINT_AREA = "work_checkpoints"

# What an operator may ask for. ``resume`` clears a pause; ``cancel`` is terminal and is never a pause.
REQUESTS = ("pause", "resume", "cancel")
RUNNING, PAUSE_REQUESTED, PAUSED, CANCELLED = "running", "pause_requested", "paused", "cancelled"


class ResumeRefused(Exception):
    """A checkpoint exists but resuming from it would not be the same work. Never downgrade this to a warning."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest_of(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _safe(name: str) -> str:
    value = "".join(c for c in str(name) if c.isalnum() or c in "-_.")[:120]
    if not value:
        raise ValueError("invalid_work_id")
    return value


def control_path(work_id: str, root: str | Path) -> Path:
    return Path(root) / CONTROL_AREA / f"{_safe(work_id)}.json"


def checkpoint_path(work_id: str, root: str | Path) -> Path:
    return Path(root) / CHECKPOINT_AREA / f"{_safe(work_id)}.json"


# --- the operator side -------------------------------------------------------------------------------------------
def request(work_id: str, what: str, root: str | Path, *, note: str = "") -> dict[str, Any]:
    """Raise a control request. Writing one starts, stops and cancels nothing by itself; a worker must observe it."""
    if what not in REQUESTS:
        raise ValueError(f"unknown_request:{what}")
    path = control_path(work_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = read_control(work_id, root)
    history = list(record.get("history") or [])
    history.append({"request": what, "at": _now(), "note": str(note)[:200]})
    payload = {"contract": CONTRACT, "work_id": work_id, "request": what, "requested_at": _now(),
               "note": str(note)[:200], "history": history[-50:]}
    write_text_atomic(path, json.dumps(payload, indent=1, ensure_ascii=False))
    return payload


def read_control(work_id: str, root: str | Path) -> dict[str, Any]:
    path = control_path(work_id, root)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # An unreadable control file must not be silently treated as "keep running"; it is a pause.
        return {"contract": CONTRACT, "work_id": work_id, "request": "pause", "unreadable": True}


def clear(work_id: str, root: str | Path) -> None:
    path = control_path(work_id, root)
    if path.is_file():
        path.unlink()


# --- the worker side ---------------------------------------------------------------------------------------------
def pending(work_id: str, root: str | Path) -> str:
    """What the worker should do at its next safe boundary: "" to continue, otherwise ``pause`` or ``cancel``."""
    what = str(read_control(work_id, root).get("request") or "")
    return what if what in ("pause", "cancel") else ""


class Checkpointer:
    """Writes durable checkpoints for one unit of work and answers whether it is time to stop.

    ``bindings`` are the facts that must still hold when the work resumes: package digests, reviewer version, model
    identity, source state. They are sealed into the checkpoint and compared on resume.
    """

    def __init__(self, work_id: str, root: str | Path, *, bindings: Mapping[str, Any],
                 clock: Callable[[], str] = _now):
        self.work_id = work_id
        self.root = Path(root)
        self.bindings = dict(bindings)
        self.clock = clock
        self.sequence = 0
        self.events: list[dict[str, Any]] = []

    def should_stop(self) -> str:
        """Read the control signal. Called only at a safe boundary, never mid-call."""
        return pending(self.work_id, self.root)

    def write(self, *, position: Mapping[str, Any], completed_units: list[str], next_unit: str,
              state: Mapping[str, Any], status: str = RUNNING) -> dict[str, Any]:
        """Seal one checkpoint atomically. The digest covers everything a resume will trust."""
        self.sequence += 1
        body = {
            "contract": CHECKPOINT_CONTRACT, "work_id": self.work_id, "sequence": self.sequence,
            "written_at": self.clock(), "status": status, "bindings": self.bindings,
            "position": dict(position), "completed_units": list(completed_units), "next_unit": next_unit,
            "completed_unit_count": len(completed_units), "state": dict(state),
            "events": list(self.events),
        }
        record = {**body, "digest": digest_of(body)}
        path = checkpoint_path(self.work_id, self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_atomic(path, json.dumps(record, ensure_ascii=False))
        return record

    def note(self, event: str, **fields: Any) -> None:
        self.events.append({"at": self.clock(), "event": str(event)[:80],
                            **{k: v for k, v in fields.items() if isinstance(v, (str, int, float, bool))}})
        self.events = self.events[-200:]


def load_checkpoint(work_id: str, root: str | Path) -> dict[str, Any] | None:
    """Read a checkpoint and verify its own seal. A corrupt or unsealed checkpoint is refused, never repaired."""
    path = checkpoint_path(work_id, root)
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ResumeRefused(f"checkpoint_unreadable:{type(exc).__name__}") from exc
    if not isinstance(record, dict) or record.get("contract") != CHECKPOINT_CONTRACT:
        raise ResumeRefused("checkpoint_contract_unrecognised")
    sealed = record.get("digest")
    body = {k: v for k, v in record.items() if k != "digest"}
    if not isinstance(sealed, str) or digest_of(body) != sealed:
        raise ResumeRefused("checkpoint_digest_mismatch")
    for field in ("work_id", "sequence", "status", "bindings", "position", "completed_units", "state"):
        if field not in record:
            raise ResumeRefused(f"checkpoint_field_missing:{field}")
    return record


def verify_resume(record: Mapping[str, Any], *, bindings: Mapping[str, Any],
                  terminal_states: tuple[str, ...] = ("complete", "incomplete", "failed", CANCELLED)) -> dict[str, Any]:
    """Decide whether this checkpoint may continue. Any drift refuses; nothing is reconciled or ignored."""
    status = str(record.get("status") or "")
    if status in terminal_states:
        raise ResumeRefused(f"work_already_terminal:{status}")
    if status not in (RUNNING, PAUSE_REQUESTED, PAUSED):
        raise ResumeRefused(f"checkpoint_status_not_resumable:{status}")
    sealed = dict(record.get("bindings") or {})
    drifted = sorted(key for key in set(sealed) | set(bindings) if sealed.get(key) != bindings.get(key))
    if drifted:
        raise ResumeRefused("binding_drift:" + ",".join(drifted[:8]))
    units = record.get("completed_units")
    if not isinstance(units, list) or len(units) != len(set(units)):
        raise ResumeRefused("completed_units_ambiguous")
    return {"resumable": True, "work_id": record.get("work_id"), "sequence": record.get("sequence"),
            "completed_units": list(units), "next_unit": record.get("next_unit"),
            "position": dict(record.get("position") or {})}


# --- releasing local resources ------------------------------------------------------------------------------------
def release_local_model(model: str = "", *, host: str = "", timeout: float = 10.0) -> dict[str, Any]:
    """Ask the local provider to unload a model so a paused run stops holding GPU and RAM.

    Best effort and never fatal: a pause is durable because the checkpoint is written, not because this succeeded.
    """
    endpoint = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    if not model:
        return {"released": False, "reason": "no_model_named"}
    try:
        import urllib.request

        body = json.dumps({"model": model, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request(f"{endpoint}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response.read()
        return {"released": True, "model": model, "endpoint": endpoint}
    except Exception as exc:
        return {"released": False, "model": model, "endpoint": endpoint, "reason": type(exc).__name__}
