from __future__ import annotations

"""Era 10 unattended-operation health, policy, and accelerated-soak contracts.

The portable layer may decide whether bounded background preparation should be
eligible, but it never launches jobs, contacts providers, installs source, or
expands authority. Durable state stores only content-free counters/digests.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v2450.9"
ALLOWED_ACTIVITY = {"health_inspection", "queue_inspection", "read_only_research_plan", "isolated_development_preparation"}
ERA6_WORK_KIND_TO_ACTIVITY = {
    "read_only_inspection": "health_inspection",
    "memory_consolidation_review": "queue_inspection",
    "plan_review": "queue_inspection",
    "proposal_preparation": "isolated_development_preparation",
}
MAX_SAMPLES = 512

_DENIED = {
    "job_executed": False,
    "provider_contacted": False,
    "notification_sent": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "destructive_operation_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> bool:
    s = str(value or "").lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _safe_code(value: Any, *, maximum: int = 160) -> str | None:
    text = str(value or "").strip()
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")
    return text if text and len(text) <= maximum and all(ch in allowed for ch in text) else None


def _finite(value: Any, *, minimum: float = 0.0, maximum: float = 1e12) -> float | None:
    if isinstance(value, bool): return None
    try: f = float(value)
    except (TypeError, ValueError): return None
    if not math.isfinite(f) or not minimum <= f <= maximum: return None
    return f


def build_unattended_policy(
    *, policy_id: str, source_digest: str, allowed_activities: Sequence[str],
    max_prepared_tickets_per_tick: int = 2, max_queue_depth: int = 32,
    max_cpu_percent: float = 70.0, max_memory_percent: float = 80.0,
    max_failure_streak: int = 3, quiet_hours_enabled: bool = True,
    notification_failure_streak: int = 2, notification_queue_depth: int = 24,
) -> dict[str, Any]:
    activities = sorted(set(str(x) for x in allowed_activities if str(x)))
    bad = [x for x in activities if x not in ALLOWED_ACTIVITY]
    numeric = {
        "max_prepared_tickets_per_tick": _finite(max_prepared_tickets_per_tick, minimum=1, maximum=8),
        "max_queue_depth": _finite(max_queue_depth, minimum=1, maximum=10000),
        "max_cpu_percent": _finite(max_cpu_percent, minimum=1, maximum=100),
        "max_memory_percent": _finite(max_memory_percent, minimum=1, maximum=100),
        "max_failure_streak": _finite(max_failure_streak, minimum=1, maximum=100),
        "notification_failure_streak": _finite(notification_failure_streak, minimum=1, maximum=100),
        "notification_queue_depth": _finite(notification_queue_depth, minimum=1, maximum=100000),
    }
    errors = []
    safe_policy_id = _safe_code(policy_id)
    if safe_policy_id is None: errors.append("invalid_policy_id")
    if not _hex64(source_digest): errors.append("invalid_source_digest")
    if not activities or bad: errors.append("invalid_allowed_activity")
    if any(v is None for v in numeric.values()): errors.append("invalid_budget")
    if errors:
        return {"ok": False, "status": "unattended_policy_blocked", "errors": sorted(set(errors)), "content_free": True, **_DENIED}
    result = {
        "ok": True,
        "status": "unattended_policy_ready",
        "contract_version": CONTRACT_VERSION,
        "policy_id": safe_policy_id,
        "source_digest": str(source_digest).lower(),
        "allowed_activities": activities,
        "budgets": {k: int(v) if k in {"max_prepared_tickets_per_tick", "max_queue_depth", "max_failure_streak", "notification_failure_streak", "notification_queue_depth"} else float(v) for k, v in numeric.items()},
        "quiet_hours_enabled": bool(quiet_hours_enabled),
        "read_only_or_isolated_preparation_only": True,
        "content_free": True,
        **_DENIED,
    }
    result["policy_digest"] = _digest(result)
    return result


def evaluate_unattended_tick(
    *, policy: Mapping[str, Any], current_source_digest: str,
    cpu_percent: Any, memory_percent: Any, queue_depth: Any,
    failure_streak: Any, foreground_active: bool, quiet_hours_active: bool,
    provider_available: bool, operator_paused: bool, prior_mode: str = "active",
) -> dict[str, Any]:
    pd = str(policy.get("policy_digest") or "")
    copy = dict(policy); copy.pop("policy_digest", None)
    if not policy.get("ok") or not _hex64(pd) or pd != _digest(copy):
        return {"ok": False, "status": "unattended_tick_blocked", "reason": "policy_invalid_or_tampered", "content_free": True, **_DENIED}
    if not _hex64(current_source_digest) or str(current_source_digest).lower() != str(policy.get("source_digest") or "").lower():
        return {"ok": False, "status": "unattended_tick_blocked", "reason": "source_drift", "content_free": True, **_DENIED}
    cpu = _finite(cpu_percent, minimum=0, maximum=100)
    mem = _finite(memory_percent, minimum=0, maximum=100)
    queue = _finite(queue_depth, minimum=0, maximum=100000)
    failures = _finite(failure_streak, minimum=0, maximum=100000)
    if None in (cpu, mem, queue, failures):
        return {"ok": False, "status": "unattended_tick_suspended", "reason": "resource_evidence_missing_or_malformed", "content_free": True, **_DENIED}
    budgets = dict(policy.get("budgets") or {})
    prior = str(prior_mode or "active").strip().lower()
    if prior not in {"active", "paused", "degraded"}:
        return {"ok": False, "status": "unattended_tick_suspended", "reason": "invalid_prior_mode", "content_free": True, **_DENIED}
    reasons = []
    if operator_paused: reasons.append("operator_paused")
    if foreground_active: reasons.append("foreground_active")
    if quiet_hours_active and policy.get("quiet_hours_enabled"): reasons.append("quiet_hours")
    if cpu > float(budgets["max_cpu_percent"]): reasons.append("cpu_pressure")
    if mem > float(budgets["max_memory_percent"]): reasons.append("memory_pressure")
    if queue > float(budgets["max_queue_depth"]): reasons.append("queue_pressure")
    if failures >= float(budgets["max_failure_streak"]): reasons.append("failure_budget_exhausted")
    status = "unattended_tick_paused" if reasons else "unattended_tick_preparation_eligible"
    mode = "paused" if reasons else ("degraded" if not provider_available else "active")
    notification_reasons = []
    if failures >= float(budgets["notification_failure_streak"]): notification_reasons.append("failure_threshold")
    if queue >= float(budgets["notification_queue_depth"]): notification_reasons.append("queue_threshold")
    result = {
        "ok": True,
        "status": status,
        "policy_digest": pd,
        "pause_reasons": sorted(set(reasons)),
        "provider_available": bool(provider_available),
        "provider_degraded_mode": not bool(provider_available),
        "prior_mode": prior, "operating_mode": mode,
        "automatic_pause": prior != "paused" and mode == "paused",
        "automatic_recovery": prior in {"paused", "degraded"} and mode == "active",
        "notification_candidate": bool(notification_reasons),
        "notification_reason_codes": notification_reasons,
        "eligible_activities": [] if reasons else list(policy.get("allowed_activities") or []),
        "maximum_prepared_tickets": 0 if reasons else int(budgets["max_prepared_tickets_per_tick"]),
        "execution_permitted": False,
        "content_free": True,
        **_DENIED,
    }
    result["tick_digest"] = _digest(result)
    return result




def admit_era6_prepared_ticket(
    *, policy: Mapping[str, Any], tick: Mapping[str, Any], ticket: Mapping[str, Any], admission_ordinal: int = 1,
) -> dict[str, Any]:
    pd = str(policy.get("policy_digest") or ""); pu = dict(policy); pu.pop("policy_digest", None)
    td = str(tick.get("tick_digest") or ""); tu = dict(tick); tu.pop("tick_digest", None)
    kd = str(ticket.get("ticket_digest") or ""); ku = dict(ticket); ku.pop("ticket_digest", None)
    valid = (
        policy.get("ok") is True and _hex64(pd) and pd == _digest(pu)
        and tick.get("ok") is True and _hex64(td) and td == _digest(tu)
        and _hex64(kd) and kd == _digest(ku)
        and ticket.get("status") == "prepared_not_executed"
        and ticket.get("execution_authorized") is False
    )
    if not valid:
        return {"ok": False, "status": "era6_ticket_admission_blocked", "reason": "tampered_or_invalid_lineage", "content_free": True, **_DENIED}
    if tick.get("status") != "unattended_tick_preparation_eligible":
        return {"ok": False, "status": "era6_ticket_admission_blocked", "reason": "unattended_tick_not_eligible", "content_free": True, **_DENIED}
    maximum = tick.get("maximum_prepared_tickets")
    if (
        not isinstance(admission_ordinal, int) or isinstance(admission_ordinal, bool)
        or not isinstance(maximum, int) or isinstance(maximum, bool)
        or admission_ordinal < 1 or admission_ordinal > maximum
    ):
        return {"ok": False, "status": "era6_ticket_admission_blocked", "reason": "preparation_budget_exhausted", "content_free": True, **_DENIED}
    activity = ERA6_WORK_KIND_TO_ACTIVITY.get(str(ticket.get("work_kind") or ""), "")
    if not activity or activity not in set(policy.get("allowed_activities") or []):
        return {"ok": False, "status": "era6_ticket_admission_blocked", "reason": "activity_not_allowed", "content_free": True, **_DENIED}
    result = {
        "ok": True, "status": "era6_ticket_admitted_for_bounded_preparation",
        "policy_digest": pd, "tick_digest": td, "ticket_digest": kd, "activity": activity,
        "admission_ordinal": admission_ordinal,
        "execution_authorized": False, "content_free": True, **_DENIED,
    }
    result["admission_digest"] = _digest(result); return result


def _read_state_strict(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.exists():
        return {}, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "corrupt"
    if not isinstance(value, dict):
        return {}, "corrupt"
    return value, None


def _validated_health_state(path: Path) -> tuple[dict[str, Any], str | None]:
    state, read_error = _read_state_strict(path)
    if read_error or not state:
        return state, read_error
    if (
        state.get("schema_version") != "2"
        or not isinstance(state.get("events"), dict)
        or not isinstance(state.get("samples"), list)
        or not isinstance(state.get("revision"), int)
        or isinstance(state.get("revision"), bool)
        or state.get("revision", -1) < 0
    ):
        return state, "corrupt"
    events = state["events"]
    samples = state["samples"]
    if len(events) > MAX_SAMPLES or len(samples) > MAX_SAMPLES:
        return state, "corrupt"
    seen_events: set[str] = set()
    for event_digest, request_digest in events.items():
        if not _hex64(event_digest) or not _hex64(request_digest):
            return state, "corrupt"
    for row in samples:
        if not isinstance(row, Mapping):
            return state, "corrupt"
        sample_digest = str(row.get("sample_digest") or "")
        unsigned = dict(row); unsigned.pop("sample_digest", None)
        event_digest = str(row.get("event_id_digest") or "")
        request_digest = str(row.get("request_digest") or "")
        metrics = row.get("metrics")
        expected_request_digest = _digest({
            "event_id_digest": event_digest,
            "policy_digest": row.get("policy_digest"),
            "source_digest": row.get("source_digest"),
            "metrics": metrics,
        })
        if (
            not _hex64(sample_digest) or sample_digest != _digest(unsigned)
            or not _hex64(event_digest) or event_digest in seen_events
            or not _hex64(request_digest) or request_digest != expected_request_digest or events.get(event_digest) != request_digest
            or not _hex64(row.get("policy_digest")) or not _hex64(row.get("source_digest"))
            or not isinstance(metrics, Mapping) or not metrics
        ):
            return state, "corrupt"
        for key, value in metrics.items():
            if key not in {"queue_depth", "latency_ms", "failure_count", "recovery_count", "cpu_percent", "memory_percent"} or _finite(value, minimum=0, maximum=1e12) is None:
                return state, "corrupt"
        seen_events.add(event_digest)
    if seen_events != set(events):
        return state, "corrupt"
    return state, None

def _state_path(runtime_root: str | Path) -> Path:
    return Path(runtime_root).expanduser().resolve() / "era10" / "unattended_health.json"


def record_health_sample(
    *, runtime_root: str | Path, event_id: str, policy_digest: str,
    sample: Mapping[str, Any], source_digest: str,
) -> dict[str, Any]:
    if not event_id or not _hex64(policy_digest) or not _hex64(source_digest):
        return {"ok": False, "status": "health_sample_blocked", "reason": "invalid_identity", "content_free": True, **_DENIED}
    allowed = {"queue_depth", "latency_ms", "failure_count", "recovery_count", "cpu_percent", "memory_percent"}
    clean: dict[str, float] = {}
    for key, value in dict(sample or {}).items():
        if key not in allowed:
            return {"ok": False, "status": "health_sample_blocked", "reason": "unsupported_metric", "content_free": True, **_DENIED}
        fv = _finite(value, minimum=0, maximum=1e12)
        if fv is None:
            return {"ok": False, "status": "health_sample_blocked", "reason": "invalid_metric", "content_free": True, **_DENIED}
        clean[key] = fv
    path = _state_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_mutation_lock(path, timeout_seconds=5):
        state, read_error = _validated_health_state(path)
        if read_error:
            return {"ok": False, "status": "health_store_corrupt", "mutation_permitted": False, "content_free": True, **_DENIED}
        state = state or {"schema_version": "2", "events": {}, "samples": [], "revision": 0}
        event_digest = hashlib.sha256(event_id.encode()).hexdigest()
        request_digest = _digest({"event_id_digest": event_digest, "policy_digest": policy_digest, "source_digest": source_digest, "metrics": clean})
        if event_digest in state["events"]:
            if state["events"][event_digest] != request_digest:
                return {"ok": False, "status": "health_sample_event_conflict", "mutation_permitted": False, "content_free": True, **_DENIED}
            return {"ok": True, "status": "health_sample_replayed", "idempotent": True, "revision": state["revision"], "content_free": True, **_DENIED}
        row = {"event_id_digest": event_digest, "request_digest": request_digest, "policy_digest": policy_digest, "source_digest": source_digest, "metrics": clean}
        row["sample_digest"] = _digest(row)
        state["events"][event_digest] = request_digest
        state["samples"] = (state["samples"] + [row])[-MAX_SAMPLES:]
        retained_events = {sample["event_id_digest"] for sample in state["samples"]}
        state["events"] = {key: value for key, value in state["events"].items() if key in retained_events}
        state["revision"] = int(state.get("revision", 0)) + 1
        write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
    return {"ok": True, "status": "health_sample_recorded", "sample_digest": row["sample_digest"], "revision": state["revision"], "content_free": True, **_DENIED}


def build_health_trend(*, runtime_root: str | Path) -> dict[str, Any]:
    path = _state_path(runtime_root)
    state, read_error = _validated_health_state(path)
    if read_error:
        return {"ok": False, "status": "health_store_corrupt", "content_free": True, **_DENIED}
    samples = list(state.get("samples") or []) if isinstance(state, Mapping) else []
    if not samples:
        result = {"ok": True, "status": "health_trend_empty", "sample_count": 0, "averages": {}, "content_free": True, **_DENIED}
        result["trend_digest"] = _digest(result); return result
    totals: dict[str, float] = {}; counts: dict[str, int] = {}
    for row in samples:
        for k, v in dict(row.get("metrics") or {}).items():
            fv = _finite(v, minimum=0, maximum=1e12)
            if fv is None: continue
            totals[k] = totals.get(k, 0.0) + fv; counts[k] = counts.get(k, 0) + 1
    averages = {k: round(totals[k] / counts[k], 4) for k in sorted(totals) if counts[k]}
    result = {"ok": True, "status": "health_trend_ready", "sample_count": len(samples), "averages": averages, "content_free": True, **_DENIED}
    result["trend_digest"] = _digest(result); return result


def run_accelerated_soak_fixture(*, policy: Mapping[str, Any], source_digest: str, events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ticks = []
    prior_mode = "active"
    for event in list(events)[:10000]:
        if not isinstance(event, Mapping):
            return {"ok": False, "status": "soak_fixture_blocked", "reason": "malformed_event", "content_free": True, **_DENIED}
        tick = evaluate_unattended_tick(
            policy=policy, current_source_digest=source_digest,
            cpu_percent=event.get("cpu_percent"), memory_percent=event.get("memory_percent"),
            queue_depth=event.get("queue_depth"), failure_streak=event.get("failure_streak"),
            foreground_active=bool(event.get("foreground_active")), quiet_hours_active=bool(event.get("quiet_hours_active")),
            provider_available=bool(event.get("provider_available", True)), operator_paused=bool(event.get("operator_paused")),
            prior_mode=prior_mode,
        )
        ticks.append(tick)
        if tick.get("ok") and tick.get("operating_mode") in {"active", "paused", "degraded"}:
            prior_mode = str(tick["operating_mode"])
    blocked = sum(1 for t in ticks if not t.get("ok"))
    paused = sum(1 for t in ticks if t.get("status") == "unattended_tick_paused")
    eligible = sum(1 for t in ticks if t.get("status") == "unattended_tick_preparation_eligible")
    degraded = sum(1 for t in ticks if t.get("provider_degraded_mode"))
    recovered = sum(1 for t in ticks if t.get("automatic_recovery"))
    result = {
        "ok": blocked == 0,
        "status": "accelerated_soak_fixture_ready" if blocked == 0 else "accelerated_soak_fixture_degraded",
        "event_count": len(ticks), "paused_count": paused, "eligible_count": eligible,
        "provider_degraded_count": degraded, "automatic_recovery_count": recovered, "blocked_count": blocked,
        "wall_clock_soak_completed": False,
        "sleep_resume_native_evidence_collected": False,
        "gaming_load_native_evidence_collected": False,
        "content_free": True, **_DENIED,
    }
    result["soak_digest"] = _digest(result); return result


__all__ = [
    "CONTRACT_VERSION", "build_unattended_policy", "evaluate_unattended_tick", "record_health_sample",
    "build_health_trend", "run_accelerated_soak_fixture", "admit_era6_prepared_ticket",
]
