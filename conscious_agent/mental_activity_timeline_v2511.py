from __future__ import annotations

"""v2511 content-minimized unified mental/activity timeline.

The timeline records accountable state transitions, not model chain-of-thought.
Inputs are structural receipts/projections from retained subsystems. The store
keeps bounded summaries plus source digests and explicitly rejects free-form
reasoning payloads.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v2511.0"
SCHEMA_VERSION = "1"
EVENT_KINDS = frozenset({"cognitive", "memory", "self_model", "planning", "action", "background", "voice"})
MAX_EVENTS = 512


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "sequence": 0,
        "events": [],
        "updated_at": "",
        "authority_boundary": {
            "hidden_reasoning_exposed": False,
            "raw_prompt_stored": False,
            "raw_provider_output_stored": False,
            "tool_arguments_stored": False,
            "can_execute_action": False,
            "can_apply_candidate": False,
            "can_authorize_action": False,
        },
    }


_SUMMARIES = {
    ("cognitive", "cycle_started"): "A bounded cognitive cycle selected one mental operation.",
    ("cognitive", "cycle_completed"): "The cognitive cycle recorded a structural outcome.",
    ("background", "cycle_suppressed"): "Background cognition remained inactive because a governance condition blocked it.",
    ("background", "cycle_completed"): "A bounded background cognitive cycle completed without external action authority.",
    ("memory", "consolidation_candidate"): "Existing memory evidence produced a consolidation or revision candidate.",
    ("self_model", "trait_candidate"): "Repeated evidence produced a developmental self-model candidate.",
    ("planning", "plan_review"): "A retained plan was reviewed against current evidence, assumptions, blockers, and value.",
    ("action", "proposal_ready"): "A capability-bound action candidate became ready for operator review.",
    ("action", "review_waiting"): "A supervised action remains awaiting operator review and has not executed.",
    ("voice", "projection"): "A state-grounded internal-voice projection was emitted from audited cognitive state.",
    ("voice", "foreground_projection"): "A state-grounded foreground internal-voice projection was emitted from minimized runtime state.",
    ("cognitive", "foreground_accepted"): "Foreground conversation cognition accepted one bounded request for processing.",
    ("cognitive", "foreground_context"): "Foreground conversation cognition reviewed minimized current context state.",
    ("cognitive", "foreground_response_complete"): "Foreground conversation cognition reached a bounded response-complete state.",
    ("cognitive", "foreground_saved"): "Foreground conversation continuity recorded the completed turn state.",
}


class MentalActivityTimeline:
    def __init__(self, runtime_root: str | Path, *, clock: Callable[[], str] | None = None):
        self.root = Path(runtime_root).expanduser().resolve()
        self.path = self.root / "mental_activity_timeline_v2511.json"
        self.clock = clock or _now

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        if state.get("schema_version") != SCHEMA_VERSION:
            state = _default()
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        if not isinstance(state.get("events"), list):
            state["events"] = []
        return state

    def append(
        self,
        event_id: str,
        *,
        event_kind: str,
        transition: str,
        source_digest: str,
        subject_ref: str = "",
        outcome_code: str = "",
    ) -> dict[str, Any]:
        eid = " ".join(str(event_id or "").split())[:160]
        kind = str(event_kind or "").strip().lower()
        trans = str(transition or "").strip().lower()[:80]
        digest = str(source_digest or "").strip().lower()
        if not eid:
            raise ValueError("event_id_required")
        if kind not in EVENT_KINDS:
            raise ValueError("unsupported_event_kind")
        if not trans:
            raise ValueError("transition_required")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("source_digest_required")
        summary = _SUMMARIES.get((kind, trans), f"A {kind.replace('_',' ')} state transition was recorded.")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            existing = next((row for row in state["events"] if row.get("event_id") == eid), None)
            if existing:
                return {"ok": True, "status": "timeline_event_replayed", "event": deepcopy(existing), "idempotent": True}
            state["sequence"] = int(state.get("sequence") or 0) + 1
            row = {
                "sequence": state["sequence"],
                "event_id": eid,
                "event_kind": kind,
                "transition": trans,
                "summary": summary[:180],
                "source_digest": digest,
                "subject_ref": str(subject_ref or "")[:120],
                "outcome_code": str(outcome_code or "")[:80],
                "observed_at": self.clock(),
                "hidden_reasoning_exposed": False,
                "raw_content_stored": False,
                "authority_granted": False,
                "action_executed": False,
            }
            row["timeline_event_digest"] = _digest(row)
            state["events"] = (state["events"] + [row])[-MAX_EVENTS:]
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = row["observed_at"]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": "timeline_event_recorded", "event": deepcopy(row), "idempotent": False}

    def recent(self, *, limit: int = 40, kind: str = "") -> dict[str, Any]:
        state = self._load()
        rows = list(state.get("events") or [])
        token = str(kind or "").strip().lower()
        if token:
            if token not in EVENT_KINDS:
                raise ValueError("unsupported_event_kind")
            rows = [row for row in rows if row.get("event_kind") == token]
        rows = rows[-max(1, min(100, int(limit or 40))):]
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "events": deepcopy(rows),
            "event_count": len(rows),
            "hidden_reasoning_exposed": False,
            "raw_content_stored": False,
            "read_only_projection": True,
        }

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        counts = {kind: 0 for kind in sorted(EVENT_KINDS)}
        for row in state.get("events") or []:
            kind = str(row.get("event_kind") or "")
            if kind in counts:
                counts[kind] += 1
        return {
            "ok": True,
            "event_count": len(state.get("events") or []),
            "counts": counts,
            "sequence": int(state.get("sequence") or 0),
            "authority_boundary": deepcopy(state.get("authority_boundary") or {}),
        }


__all__ = ["CONTRACT_VERSION", "EVENT_KINDS", "MentalActivityTimeline"]
