from __future__ import annotations

"""Era 6 resource budgets and cooperative background suspension.

Portable policy only: evaluates operator-configured CPU/memory/disk/provider/
concurrency/thermal/time budgets and persists resumable ticket suspension state.
It does not sample the OS by itself and cannot kill, pause, or launch processes.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from json_storage import AtomicJsonWriteError, load_json_file, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR

CONTRACT_VERSION = "v2099.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era6_resource_cooperation.json"
PRIORITY_CLASSES = ("foreground", "high", "normal", "low")

DEFAULT_BUDGETS = {
    "cpu_percent": 35.0,
    "memory_percent": 35.0,
    "disk_percent": 20.0,
    "provider_concurrency": 1.0,
    "background_concurrency": 1.0,
    "thermal_percent": 70.0,
    "time_minutes": 20.0,
}

_DENIED = {
    "process_paused": False,
    "process_killed": False,
    "process_started": False,
    "provider_contacted": False,
    "tool_executed": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, number) if math.isfinite(number) else default


def _measurement(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0.0 else None


def _state_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "background_cognition" / STATE_FILE


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "budgets": deepcopy(DEFAULT_BUDGETS),
        "ticket_states": {},
        "processed_events": [],
        "raw_content_persisted": False,
    }


def _valid_state(value: Any) -> dict[str, Any]:
    state = deepcopy(value) if isinstance(value, dict) else _default_state()
    if not isinstance(state.get("budgets"), dict):
        state["budgets"] = deepcopy(DEFAULT_BUDGETS)
    for key, default in DEFAULT_BUDGETS.items():
        state["budgets"][key] = _number(state["budgets"].get(key), default)
    if not isinstance(state.get("ticket_states"), dict):
        state["ticket_states"] = {}
    if not isinstance(state.get("processed_events"), list):
        state["processed_events"] = []
    state["raw_content_persisted"] = False
    return state


def read_resource_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    return _valid_state(load_json_file(_state_path(runtime_root), _default_state(), expected_type=dict))


def configure_resource_budgets(
    *, budgets: Mapping[str, Any], event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    token = str(event_id or "").strip()
    if not token:
        return {"ok": False, "status": "event_id_required", **_DENIED}
    unknown = sorted(set(budgets) - set(DEFAULT_BUDGETS))
    if unknown:
        return {"ok": False, "status": "unsupported_budget_dimension", "unsupported": unknown, **_DENIED}
    path = _state_path(runtime_root)
    event_digest = _digest(token)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            if any(str(row.get("event_digest") or "") == event_digest for row in state["processed_events"] if isinstance(row, Mapping)):
                return {"ok": True, "status": "resource_budget_configuration_replayed", "state": public_resource_state(state), "idempotent": True, **_DENIED}
            for key, value in budgets.items():
                number = _number(value, state["budgets"][key])
                if key.endswith("percent"):
                    number = max(1.0, min(100.0, number))
                elif "concurrency" in key:
                    number = max(1.0, min(16.0, number))
                else:
                    number = max(1.0, min(1440.0, number))
                state["budgets"][key] = round(number, 3)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now().isoformat()
            state["processed_events"] = (state["processed_events"] + [{"event_digest": event_digest, "at": state["updated_at"]}])[-256:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": "resource_budgets_configured", "state": public_resource_state(state), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "resource_budget_write_blocked"), **_DENIED}


def assess_resource_pressure(
    measurements: Mapping[str, Any], *, priority_class: str = "normal", runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    priority = str(priority_class or "normal").strip().lower()
    if priority not in PRIORITY_CLASSES:
        return {"ok": False, "status": "unsupported_priority_class", **_DENIED}
    state = read_resource_state(runtime_root=runtime_root)
    budgets = state["budgets"]
    ratios: dict[str, float] = {}
    exceeded: list[str] = []
    observed_dimensions: list[str] = []
    invalid_dimensions: list[str] = []
    for key, limit in budgets.items():
        observed_value = _measurement(measurements.get(key)) if key in measurements else None
        if key in measurements and observed_value is None:
            invalid_dimensions.append(key)
        if observed_value is not None:
            observed_dimensions.append(key)
        observed = observed_value if observed_value is not None else 0.0
        ratio = observed / max(0.001, float(limit))
        ratios[key] = round(ratio, 4)
        if ratio > 1.0:
            exceeded.append(key)
    foreground_busy = bool(measurements.get("foreground_busy"))
    gaming_or_heavy_foreground = bool(measurements.get("foreground_high_load"))
    provider_outage = bool(measurements.get("provider_outage"))
    measurement_evidence_sufficient = bool(
        observed_dimensions or foreground_busy or gaming_or_heavy_foreground or provider_outage
    ) and not invalid_dimensions
    worst = max(ratios.values(), default=0.0)

    if priority == "foreground":
        mode = "permit"
    elif not measurement_evidence_sufficient:
        mode = "suspend"
    elif foreground_busy or gaming_or_heavy_foreground or worst >= 1.25 or "thermal_percent" in exceeded:
        mode = "suspend"
    elif exceeded or worst >= 0.85 or provider_outage:
        mode = "degrade"
    else:
        mode = "permit"
    # Provider outage cannot block read-only/no-provider work by itself, but it must
    # degrade the general background lane so provider-dependent tickets are held.
    result = {
        "ok": True,
        "status": "resource_pressure_assessed" if measurement_evidence_sufficient else "resource_measurements_insufficient",
        "contract_version": CONTRACT_VERSION,
        "priority_class": priority,
        "mode": mode,
        "ratios": ratios,
        "exceeded_dimensions": exceeded,
        "foreground_busy": foreground_busy,
        "foreground_high_load": gaming_or_heavy_foreground,
        "provider_outage": provider_outage,
        "observed_dimensions": sorted(observed_dimensions),
        "invalid_dimensions": sorted(invalid_dimensions),
        "measurement_evidence_sufficient": measurement_evidence_sufficient,
        "background_should_yield": mode in {"degrade", "suspend"},
        "measurement_source_required": True,
        "os_sampled_here": False,
        **_DENIED,
    }
    result["assessment_digest"] = _digest(result)
    return result


def apply_cooperative_suspension(
    ticket_ids: Iterable[str], *, assessment: Mapping[str, Any], event_id: str,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Persist logical ticket state only; never suspend a process."""
    token = str(event_id or "").strip()
    if not token:
        return {"ok": False, "status": "event_id_required", **_DENIED}
    mode = str(assessment.get("mode") or "").strip().lower()
    if mode not in {"permit", "degrade", "suspend"}:
        return {"ok": False, "status": "valid_resource_assessment_required", **_DENIED}
    expected = str(assessment.get("assessment_digest") or "")
    check = dict(assessment)
    check.pop("assessment_digest", None)
    if expected != _digest(check):
        return {"ok": False, "status": "resource_assessment_digest_invalid", **_DENIED}
    ids = sorted({str(item or "").strip()[:120] for item in ticket_ids if str(item or "").strip()})[:64]
    path = _state_path(runtime_root)
    event_digest = _digest(token)
    current = _now().isoformat()
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            if any(str(row.get("event_digest") or "") == event_digest for row in state["processed_events"] if isinstance(row, Mapping)):
                return {"ok": True, "status": "cooperative_suspension_replayed", "state": public_resource_state(state), "idempotent": True, **_DENIED}
            status = {"permit": "eligible", "degrade": "degraded", "suspend": "suspended"}[mode]
            for ticket_id in ids:
                previous = state["ticket_states"].get(ticket_id) if isinstance(state["ticket_states"].get(ticket_id), dict) else {}
                state["ticket_states"][ticket_id] = {
                    "ticket_id": ticket_id,
                    "status": status,
                    "assessment_digest": expected,
                    "updated_at": current,
                    "resume_count": int(previous.get("resume_count") or 0) + (1 if previous.get("status") in {"suspended", "degraded"} and status == "eligible" else 0),
                    "execution_started": False,
                }
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = current
            state["processed_events"] = (state["processed_events"] + [{"event_digest": event_digest, "at": current}])[-256:]
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": f"background_tickets_{status}", "state": public_resource_state(state), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "resource_state_write_blocked"), **_DENIED}


def public_resource_state(state: Mapping[str, Any]) -> dict[str, Any]:
    row = _valid_state(state)
    tickets = [deepcopy(value) for _, value in sorted(row.get("ticket_states", {}).items()) if isinstance(value, Mapping)][-64:]
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": int(row.get("revision") or 0),
        "updated_at": str(row.get("updated_at") or ""),
        "budgets": deepcopy(row["budgets"]),
        "ticket_states": tickets,
        "raw_content_persisted": False,
        **_DENIED,
    }
    result["state_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION", "DEFAULT_BUDGETS", "configure_resource_budgets", "assess_resource_pressure",
    "apply_cooperative_suspension", "read_resource_state", "public_resource_state",
]
