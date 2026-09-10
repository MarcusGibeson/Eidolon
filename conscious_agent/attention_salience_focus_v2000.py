from __future__ import annotations

"""Era 6 attention and salience governance.

Portable, content-free attention scoring and restart-safe focus ownership.  This
module does not execute work.  It chooses and explains what deserves attention
from attributable candidate evidence, persists only digests/codes/factors, and
supports bounded shift/defer/resume/cancel with anti-fixation controls.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from json_storage import AtomicJsonWriteError, load_json_file, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR

CONTRACT_VERSION = "v2025.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era6_attention_focus.json"
MAX_CANDIDATES = 64
MAX_HISTORY = 256
MAX_PROCESSED = 256
FACTOR_NAMES = (
    "urgency", "importance", "novelty", "emotional_relevance",
    "risk", "deadline_pressure", "operator_priority",
)
WEIGHTS = {
    "urgency": 0.21,
    "importance": 0.20,
    "novelty": 0.08,
    "emotional_relevance": 0.08,
    "risk": 0.18,
    "deadline_pressure": 0.13,
    "operator_priority": 0.12,
}

_DENIED = {
    "work_executed": False,
    "provider_contacted": False,
    "message_sent": False,
    "source_modified": False,
    "memory_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _bounded(value: Any, default: float = 0.0) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return round(default, 4)


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
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


def _state_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "attention" / STATE_FILE


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "active_focus": None,
        "deferred": {},
        "selection_history": [],
        "processed_events": [],
        "raw_content_persisted": False,
        "authority_effect": "none",
    }


def _valid_state(value: Any) -> dict[str, Any]:
    state = deepcopy(value) if isinstance(value, dict) else _default_state()
    state.setdefault("revision", 0)
    if not isinstance(state.get("deferred"), dict):
        state["deferred"] = {}
    if not isinstance(state.get("selection_history"), list):
        state["selection_history"] = []
    if not isinstance(state.get("processed_events"), list):
        state["processed_events"] = []
    state["raw_content_persisted"] = False
    state["authority_effect"] = "none"
    return state


def read_focus_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    return _valid_state(load_json_file(_state_path(runtime_root), _default_state(), expected_type=dict))


def _candidate(row: Mapping[str, Any], *, now: datetime, state: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = str(row.get("candidate_id") or row.get("id") or "").strip()[:160]
    evidence_digest = str(row.get("evidence_digest") or "").strip().lower()
    if not candidate_id or len(evidence_digest) != 64 or any(ch not in "0123456789abcdef" for ch in evidence_digest):
        raise ValueError("candidate_id_and_sha256_evidence_digest_required")
    provenance = str(row.get("provenance") or "unknown").strip().lower()[:64]
    factors = {name: _bounded(row.get(name)) for name in FACTOR_NAMES}
    deadline = _parse_time(row.get("deadline_at"))
    if deadline is not None:
        hours = (deadline - now).total_seconds() / 3600.0
        if hours <= 0:
            factors["deadline_pressure"] = max(factors["deadline_pressure"], 1.0)
        elif hours <= 24:
            factors["deadline_pressure"] = max(factors["deadline_pressure"], 0.9)
        elif hours <= 72:
            factors["deadline_pressure"] = max(factors["deadline_pressure"], 0.65)
    freshness = _bounded(row.get("freshness"), 1.0)
    uncertainty = _bounded(row.get("uncertainty"), 0.0)
    base = sum(factors[name] * WEIGHTS[name] for name in FACTOR_NAMES)
    stale_penalty = (1.0 - freshness) * 0.18
    uncertainty_penalty = uncertainty * 0.10
    history = [h for h in state.get("selection_history", []) if isinstance(h, Mapping)]
    recent_same = 0
    for item in reversed(history[-8:]):
        if str(item.get("candidate_id") or "") == candidate_id:
            recent_same += 1
        else:
            break
    fixation_exempt = bool(factors["urgency"] >= 0.85 or factors["risk"] >= 0.85 or factors["operator_priority"] >= 0.9)
    fixation_penalty = 0.0 if fixation_exempt else min(0.24, recent_same * 0.08)
    score = round(max(0.0, min(1.0, base - stale_penalty - uncertainty_penalty - fixation_penalty)), 4)
    return {
        "candidate_id": candidate_id,
        "evidence_digest": evidence_digest,
        "provenance": provenance,
        "factors": factors,
        "freshness": freshness,
        "uncertainty": uncertainty,
        "score": score,
        "fixation_penalty": round(fixation_penalty, 4),
        "fixation_exempt": fixation_exempt,
        "deadline_known": deadline is not None,
        "candidate_digest": _digest({"candidate_id": candidate_id, "evidence_digest": evidence_digest, "factors": factors, "freshness": freshness, "uncertainty": uncertainty}),
    }


def score_salience_candidates(
    candidates: Iterable[Mapping[str, Any]], *, runtime_root: str | Path | None = None, now: datetime | None = None
) -> dict[str, Any]:
    current = _now(now)
    state = read_focus_state(runtime_root=runtime_root)
    rows: list[dict[str, Any]] = []
    for raw in list(candidates)[:MAX_CANDIDATES]:
        if isinstance(raw, Mapping):
            rows.append(_candidate(raw, now=current, state=state))
    deferred = state.get("deferred") or {}
    for row in rows:
        if row["candidate_id"] in deferred:
            row["deferred"] = True
            row["score"] = 0.0
        else:
            row["deferred"] = False
    rows.sort(key=lambda item: (-float(item["score"]), -float(item["factors"]["operator_priority"]), item["candidate_id"]))
    result = {
        "ok": True,
        "status": "salience_scored",
        "contract_version": CONTRACT_VERSION,
        "candidate_count": len(rows),
        "candidates": rows,
        "ranking_digest": _digest(rows),
        "current_focus_id": str((state.get("active_focus") or {}).get("candidate_id") or ""),
        "raw_content_retained": False,
        **_DENIED,
    }
    return result


def _event_seen(state: Mapping[str, Any], event_digest: str) -> bool:
    return any(str(row.get("event_digest") or "") == event_digest for row in state.get("processed_events", []) if isinstance(row, Mapping))


def choose_focus(
    candidates: Iterable[Mapping[str, Any]], *, event_id: str, runtime_root: str | Path | None = None, now: datetime | None = None
) -> dict[str, Any]:
    token = str(event_id or "").strip()
    if not token:
        return {"ok": False, "status": "event_id_required", **_DENIED}
    event_digest = _digest(token)
    path = _state_path(runtime_root)
    current = _now(now)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            if _event_seen(state, event_digest):
                return {"ok": True, "status": "focus_selection_replayed", "state": public_focus_state(state), "idempotent": True, **_DENIED}
            scored = score_salience_candidates(candidates, runtime_root=runtime_root, now=current)
            eligible = [row for row in scored["candidates"] if not row.get("deferred") and float(row.get("score") or 0) > 0.0]
            selected = eligible[0] if eligible else None
            previous = state.get("active_focus") if isinstance(state.get("active_focus"), dict) else None
            if selected:
                focus = {
                    "candidate_id": selected["candidate_id"],
                    "candidate_digest": selected["candidate_digest"],
                    "score": selected["score"],
                    "reason_factors": sorted(selected["factors"], key=lambda key: (-float(selected["factors"][key]), key))[:3],
                    "selected_at": current.isoformat(),
                    "status": "focused",
                }
                state["active_focus"] = focus
                state["selection_history"] = (state.get("selection_history", []) + [{"candidate_id": focus["candidate_id"], "candidate_digest": focus["candidate_digest"], "selected_at": current.isoformat()}])[-MAX_HISTORY:]
                status = "focus_sustained" if previous and previous.get("candidate_id") == focus["candidate_id"] else "focus_shifted"
            else:
                state["active_focus"] = None
                status = "no_eligible_focus"
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = current.isoformat()
            state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "at": current.isoformat()}])[-MAX_PROCESSED:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": status, "state": public_focus_state(state), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "focus_state_write_blocked"), "safe_retry": bool(getattr(error, "safe_retry", True)), **_DENIED}


def update_focus_control(
    action: str, *, candidate_id: str, expected_state_digest: str, event_id: str, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    action = str(action or "").strip().lower()
    if action not in {"defer", "resume", "cancel"}:
        return {"ok": False, "status": "unsupported_focus_control", **_DENIED}
    token = str(event_id or "").strip()
    candidate_id = str(candidate_id or "").strip()[:160]
    if not token or not candidate_id:
        return {"ok": False, "status": "event_and_candidate_required", **_DENIED}
    path = _state_path(runtime_root)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            public = public_focus_state(state)
            if str(expected_state_digest or "") != public["state_digest"]:
                return {"ok": False, "status": "stale_focus_state_digest", "state": public, **_DENIED}
            event_digest = _digest(token)
            if _event_seen(state, event_digest):
                return {"ok": True, "status": "focus_control_replayed", "state": public, "idempotent": True, **_DENIED}
            deferred = dict(state.get("deferred") or {})
            active = state.get("active_focus") if isinstance(state.get("active_focus"), dict) else None
            if action == "defer":
                deferred[candidate_id] = {"deferred_at": _now().isoformat(), "reason_code": "operator_or_policy_defer"}
                if active and active.get("candidate_id") == candidate_id:
                    state["active_focus"] = None
            elif action == "resume":
                deferred.pop(candidate_id, None)
            else:  # cancel focus ownership only; never cancel underlying work
                if active and active.get("candidate_id") == candidate_id:
                    state["active_focus"] = None
            state["deferred"] = deferred
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now().isoformat()
            state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "at": state["updated_at"]}])[-MAX_PROCESSED:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": f"focus_{action}ed", "state": public_focus_state(state), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "focus_control_write_blocked"), "safe_retry": bool(getattr(error, "safe_retry", True)), **_DENIED}


def public_focus_state(state: Mapping[str, Any]) -> dict[str, Any]:
    row = _valid_state(state)
    active = row.get("active_focus") if isinstance(row.get("active_focus"), dict) else None
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": int(row.get("revision") or 0),
        "updated_at": str(row.get("updated_at") or ""),
        "active_focus": deepcopy(active),
        "deferred_candidate_ids": sorted(str(key) for key in (row.get("deferred") or {}).keys())[:MAX_CANDIDATES],
        "selection_count": len(row.get("selection_history", [])),
        "raw_content_persisted": False,
        "authority_effect": "none",
        **_DENIED,
    }
    result["state_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION", "FACTOR_NAMES", "score_salience_candidates", "choose_focus",
    "update_focus_control", "read_focus_state", "public_focus_state",
]
