from __future__ import annotations

"""Era 3 restart-safe long-horizon planning.

Plans preserve the original objective, completed work, evidence lineage, failed
strategies, dependencies and revision reasons across interruptions.  This is a
planning/bookkeeping layer only: it never schedules or executes the tasks it
represents.
"""

from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from metadata_mutation_coordination import metadata_mutation_lock
from hierarchical_goal_management_foundations import build_goal_hierarchy
from dynamic_replanning_foundations import build_replanning_event, build_replan_candidate

CONTRACT_VERSION = "v1775.9"
SCHEMA_VERSION = "1"
MAX_MILESTONES = 12
MAX_TASKS = 64
MAX_EVENTS = 96
MAX_FAILED_STRATEGIES = 24

AUTHORITY_FLAGS = {
    "planning_authorized": True,
    "plan_bookkeeping_authorized": True,
    "execution_authorized": False,
    "scheduling_authorized": False,
    "background_work_authorized": False,
    "provider_contact_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "standing_authority_granted": False,
}

_SAFE = re.compile(r"[^a-z0-9_.:-]+")
_SHOW = re.compile(r"^(?:show|inspect) long horizon plan (?P<id>plan_[a-f0-9]{24})[.!?]*$", re.I)
_PAUSE = re.compile(r"^pause long horizon plan (?P<id>plan_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I)
_RESUME = re.compile(r"^resume long horizon plan (?P<id>plan_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _code(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip().lower().replace(" ", "_")
    text = _SAFE.sub("_", text).strip("_")[:128]
    return text or fallback


def _path(plan_id: str, runtime_root: str | Path | None = None) -> Path:
    return _store_root(runtime_root) / "long_horizon_plans" / f"{plan_id}.json"


def _serialized_plan_mutation(function):
    def wrapped(plan_id: str, *args: Any, **kwargs: Any):
        with metadata_mutation_lock(_path(plan_id, kwargs.get("runtime_root"))):
            return function(plan_id, *args, **kwargs)
    return wrapped


def _normalize_milestones(milestones: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    result: list[dict[str, Any]] = []
    errors: list[str] = []
    task_ids: set[str] = set(); milestone_ids: set[str] = set()
    for mi, raw in enumerate(milestones[:MAX_MILESTONES]):
        if not isinstance(raw, Mapping):
            continue
        mid = _code(raw.get("milestone_code") or raw.get("id") or f"milestone_{mi+1}")
        if mid in milestone_ids:
            errors.append("duplicate_milestone_code"); continue
        milestone_ids.add(mid)
        deps = [_code(x) for x in list(raw.get("depends_on") or [])[:MAX_MILESTONES]]
        tasks = []
        for ti, t in enumerate(list(raw.get("tasks") or [])[:MAX_TASKS]):
            if not isinstance(t, Mapping):
                t = {"task_code": t}
            tid = _code(t.get("task_code") or t.get("id") or f"{mid}_task_{ti+1}")
            if tid in task_ids:
                errors.append("duplicate_task_code"); continue
            task_ids.add(tid)
            tasks.append({
                "task_code": tid,
                "description_private": " ".join(str(t.get("description") or tid).split())[:320],
                "depends_on_tasks": [_code(x) for x in list(t.get("depends_on") or [])[:12]],
                "success_codes": [_code(x) for x in list(t.get("success_codes") or [])[:12]],
                "strategy_code": _code(t.get("strategy_code") or tid),
                "estimated_effort": max(1, min(100, int(t.get("estimated_effort") or 1))),
                "status": "pending",
                "evidence_digests": [],
                "attempt_count": 0,
            })
        result.append({
            "milestone_code": mid,
            "depends_on": deps,
            "tasks": tasks,
            "success_codes": [_code(x) for x in list(raw.get("success_codes") or [])[:16]],
            "status": "pending",
        })
    # milestone DAG validation
    seen: set[str] = set()
    for row in result:
        if any(dep not in seen for dep in row["depends_on"]):
            errors.append("milestone_dependency_not_prior_or_unknown")
        seen.add(row["milestone_code"])
    known_tasks = {t["task_code"] for m in result for t in m["tasks"]}
    for m in result:
        for t in m["tasks"]:
            if any(dep not in known_tasks for dep in t["depends_on_tasks"]):
                errors.append("task_dependency_unknown")
    return result, sorted(set(errors))


def _public(record: Mapping[str, Any]) -> dict[str, Any]:
    milestones = []
    for m in record.get("milestones") or []:
        tasks = []
        for t in m.get("tasks") or []:
            tasks.append({
                "task_code": t.get("task_code"), "depends_on_tasks": t.get("depends_on_tasks") or [],
                "success_codes": t.get("success_codes") or [], "strategy_code": t.get("strategy_code"),
                "estimated_effort": t.get("estimated_effort"), "status": t.get("status"),
                "evidence_count": len(t.get("evidence_digests") or []), "attempt_count": int(t.get("attempt_count") or 0),
                "private_description_exposed": False,
            })
        milestones.append({
            "milestone_code": m.get("milestone_code"), "depends_on": m.get("depends_on") or [],
            "success_codes": m.get("success_codes") or [], "status": m.get("status"), "tasks": tasks,
        })
    completed_tasks = sum(1 for m in milestones for t in m["tasks"] if t["status"] == "complete")
    total_tasks = sum(len(m["tasks"]) for m in milestones)
    result = {
        "ok": True, "status": record.get("status", "long_horizon_plan_ready"),
        "contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION,
        "plan_id": record.get("plan_id"), "revision": int(record.get("revision") or 0),
        "objective_digest": record.get("objective_digest"), "original_objective_digest": record.get("original_objective_digest"),
        "milestones": milestones, "milestone_count": len(milestones), "task_count": total_tasks,
        "completed_task_count": completed_tasks, "completion_ratio": round(completed_tasks / max(1, total_tasks), 4),
        "failed_strategy_codes": list(record.get("failed_strategy_codes") or []),
        "stop_condition_codes": list(record.get("stop_condition_codes") or []),
        "resource_codes": list(record.get("resource_codes") or []),
        "deferred_alternative_codes": list(record.get("deferred_alternative_codes") or []),
        "paused": bool(record.get("paused")), "cancelled": bool(record.get("cancelled")),
        "event_count": len(record.get("events") or []),
        "original_objective_preserved": record.get("objective_digest") == record.get("original_objective_digest"),
        "completed_work_preserved": True,
        "private_objective_exposed": False, "private_task_descriptions_exposed": False,
        "created_at": record.get("created_at"), "updated_at": record.get("updated_at"),
        **AUTHORITY_FLAGS,
    }
    result["plan_digest"] = _digest({k: v for k, v in result.items() if k != "plan_digest"})
    return result


def create_long_horizon_plan(
    objective: str,
    milestones: Sequence[Mapping[str, Any]],
    *,
    acceptance_codes: Sequence[str] = (),
    stop_condition_codes: Sequence[str] = (),
    resource_codes: Sequence[str] = (),
    deferred_alternative_codes: Sequence[str] = (),
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    objective_text = " ".join(str(objective or "").split())[:1000]
    normalized, errors = _normalize_milestones(milestones)
    if not objective_text or not normalized or errors:
        return {"ok": False, "status": "long_horizon_plan_invalid", "error_codes": errors or ["objective_or_milestones_required"], **AUTHORITY_FLAGS}
    objective_digest = _digest(objective_text)
    plan_key = _digest({"objective": objective_text, "milestones": [{"code": m["milestone_code"], "tasks": [t["task_code"] for t in m["tasks"]]} for m in normalized]})
    plan_id = f"plan_{plan_key[:24]}"; path = _path(plan_id, runtime_root)
    existing = _read_json(path)
    if existing:
        result = _public(existing); result["status"] = "long_horizon_plan_current"; return result
    now = _now()
    record = {
        "status": "long_horizon_plan_ready", "plan_id": plan_id, "revision": 1,
        "objective_private": objective_text, "objective_digest": objective_digest, "original_objective_digest": objective_digest,
        "acceptance_codes": [_code(x) for x in list(acceptance_codes)[:24]],
        "stop_condition_codes": [_code(x) for x in list(stop_condition_codes)[:24]],
        "resource_codes": [_code(x) for x in list(resource_codes)[:24]],
        "deferred_alternative_codes": [_code(x) for x in list(deferred_alternative_codes)[:24]],
        "milestones": normalized, "events": [], "failed_strategy_codes": [], "paused": False, "cancelled": False,
        "created_at": now, "updated_at": now,
    }
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record); return _public(record)


def inspect_long_horizon_plan(plan_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    record = _read_json(_path(plan_id, runtime_root))
    if not record:
        return {"ok": False, "status": "long_horizon_plan_not_found", "plan_id": plan_id, **AUTHORITY_FLAGS}
    return _public(record)


@_serialized_plan_mutation
def record_task_outcome(
    plan_id: str, expected_digest: str, *, task_code: str, outcome: str, evidence_digest: str,
    strategy_failed: bool = False, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    path = _path(plan_id, runtime_root); record = _read_json(path)
    if not record:
        return {"ok": False, "status": "long_horizon_plan_not_found", **AUTHORITY_FLAGS}
    current = _public(record)["plan_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_long_horizon_plan_digest", "current_digest": current, **AUTHORITY_FLAGS}
    if record.get("paused") or record.get("cancelled"):
        return {"ok": False, "status": "plan_not_active_for_bookkeeping", **AUTHORITY_FLAGS}
    ev = str(evidence_digest or "").lower()
    if not re.fullmatch(r"[a-f0-9]{64}", ev):
        return {"ok": False, "status": "evidence_digest_required", **AUTHORITY_FLAGS}
    task = None
    for m in record.get("milestones") or []:
        for t in m.get("tasks") or []:
            if t.get("task_code") == _code(task_code):
                task = t; milestone = m; break
        if task: break
    if not task:
        return {"ok": False, "status": "task_not_found", **AUTHORITY_FLAGS}
    event_key = _digest({"task": task["task_code"], "outcome": _code(outcome), "evidence": ev})
    if any(e.get("event_key") == event_key for e in record.get("events") or []):
        result = _public(record); result["status"] = "task_outcome_replay"; return result
    outcome_code = _code(outcome)
    task["attempt_count"] = int(task.get("attempt_count") or 0) + 1
    task.setdefault("evidence_digests", []).append(ev); task["evidence_digests"] = task["evidence_digests"][-12:]
    if outcome_code in {"complete", "completed", "success", "passed", "verified"}:
        task["status"] = "complete"
    elif outcome_code in {"failed", "failure", "blocked"}:
        task["status"] = "blocked" if outcome_code == "blocked" else "failed"
    else:
        task["status"] = "in_progress"
    if strategy_failed:
        failed = _code(task.get("strategy_code"))
        if failed not in record["failed_strategy_codes"]:
            record["failed_strategy_codes"].append(failed)
        record["failed_strategy_codes"] = record["failed_strategy_codes"][-MAX_FAILED_STRATEGIES:]
    # milestone complete only when all tasks are complete
    milestone["status"] = "complete" if milestone.get("tasks") and all(t.get("status") == "complete" for t in milestone["tasks"]) else "in_progress"
    record.setdefault("events", []).append({"event_key": event_key, "event_kind": "task_outcome", "task_code": task["task_code"], "outcome": outcome_code, "evidence_digest": ev, "at": _now()})
    record["events"] = record["events"][-MAX_EVENTS:]
    record["revision"] = int(record.get("revision") or 1) + 1; record["updated_at"] = _now()
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record)
    result = _public(record); result["status"] = "task_outcome_recorded"; return result


@_serialized_plan_mutation
def revise_long_horizon_plan(
    plan_id: str, expected_digest: str, *, event_kind: str, event_code: str,
    evidence_codes: Sequence[str] = (), requested_priority_codes: Sequence[str] = (),
    operator_supplied: bool = False, failed_strategy_codes: Sequence[str] = (), runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    path = _path(plan_id, runtime_root); record = _read_json(path)
    if not record:
        return {"ok": False, "status": "long_horizon_plan_not_found", **AUTHORITY_FLAGS}
    current = _public(record)["plan_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_long_horizon_plan_digest", "current_digest": current, **AUTHORITY_FLAGS}
    kind = _code(event_kind)
    if kind not in {"interruption", "new_requirement", "failed_assumption", "new_evidence", "priority_change"}:
        return {"ok": False, "status": "replan_event_invalid", **AUTHORITY_FLAGS}
    if kind == "new_requirement" and not operator_supplied:
        return {"ok": False, "status": "unconfirmed_new_requirement_held", "operator_confirmation_required": True, **AUTHORITY_FLAGS}
    completed_before = {t["task_code"] for m in record.get("milestones") or [] for t in m.get("tasks") or [] if t.get("status") == "complete"}
    failed = set(record.get("failed_strategy_codes") or []) | {_code(x) for x in failed_strategy_codes}
    record["failed_strategy_codes"] = sorted(failed)[:MAX_FAILED_STRATEGIES]
    action_codes = []
    if kind == "interruption":
        record["paused"] = True; action_codes.append("pause_preserve_first_incomplete")
    elif kind == "priority_change":
        priorities = [_code(x) for x in requested_priority_codes]
        order = {code: i for i, code in enumerate(priorities)}
        completed_ms = [m for m in record["milestones"] if m.get("status") == "complete"]
        pending_ms = [m for m in record["milestones"] if m.get("status") != "complete"]
        pending_ms.sort(key=lambda m: (order.get(m["milestone_code"], 999), record["milestones"].index(m)))
        record["milestones"] = completed_ms + pending_ms; action_codes.append("reorder_incomplete_only")
    elif kind == "failed_assumption":
        action_codes.extend(["invalidate_failed_assumption", "require_new_strategy_before_retry"])
    elif kind == "new_evidence":
        action_codes.append("reassess_incomplete_work_only")
    elif kind == "new_requirement":
        action_codes.append("operator_requirement_recorded_for_plan_revision")
    record.setdefault("events", []).append({
        "event_key": _digest({"kind": kind, "code": _code(event_code), "revision": record.get("revision")}),
        "event_kind": kind, "event_code": _code(event_code), "evidence_codes": [_code(x) for x in list(evidence_codes)[:16]],
        "operator_supplied": bool(operator_supplied), "action_codes": action_codes, "at": _now(),
    })
    record["events"] = record["events"][-MAX_EVENTS:]
    record["revision"] = int(record.get("revision") or 1) + 1; record["updated_at"] = _now()
    completed_after = {t["task_code"] for m in record.get("milestones") or [] for t in m.get("tasks") or [] if t.get("status") == "complete"}
    if not completed_before.issubset(completed_after):
        return {"ok": False, "status": "completed_work_preservation_failed", **AUTHORITY_FLAGS}
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record)
    result = _public(record); result.update({"status": "long_horizon_plan_revised", "replan_action_codes": action_codes, "completed_work_preserved": True, "failed_strategies_may_not_repeat": True}); return result


@_serialized_plan_mutation
def set_plan_paused(plan_id: str, expected_digest: str, paused: bool, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    path = _path(plan_id, runtime_root); record = _read_json(path)
    if not record:
        return {"ok": False, "status": "long_horizon_plan_not_found", **AUTHORITY_FLAGS}
    current = _public(record)["plan_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_long_horizon_plan_digest", "current_digest": current, **AUTHORITY_FLAGS}
    if bool(record.get("paused")) == bool(paused):
        result = _public(record); result["status"] = "plan_pause_state_replay"; return result
    record["paused"] = bool(paused); record["revision"] = int(record.get("revision") or 1) + 1; record["updated_at"] = _now()
    record.setdefault("events", []).append({"event_key": _digest({"paused": paused, "revision": record["revision"]}), "event_kind": "pause" if paused else "resume", "at": _now()})
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record)
    result = _public(record); result["status"] = "long_horizon_plan_paused" if paused else "long_horizon_plan_resumed"; return result


def legacy_hierarchy_projection(plan_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    record = _read_json(_path(plan_id, runtime_root))
    if not record:
        return {"ok": False, "status": "long_horizon_plan_not_found", **AUTHORITY_FLAGS}
    return build_goal_hierarchy(
        objective_code="era3_long_horizon_objective", original_intent_digest=record["original_objective_digest"],
        milestone_codes=[m["milestone_code"] for m in record.get("milestones") or []][:6],
        acceptance_codes=record.get("acceptance_codes") or [], risk_codes=record.get("stop_condition_codes") or [],
    )


def process_long_horizon_planning_control(user_text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    text = str(user_text or "").strip(); lowered = text.lower()
    if "long horizon plan" in lowered and any(x in lowered for x in (" and execute", " and install", " and run", " and promote")):
        return {"active": True, "ok": False, "status": "planning_scope_expansion_rejected", **AUTHORITY_FLAGS}
    match = _SHOW.fullmatch(text)
    if match:
        return {"active": True, **inspect_long_horizon_plan(match.group("id").lower(), runtime_root=runtime_root)}
    match = _PAUSE.fullmatch(text)
    if match:
        return {"active": True, **set_plan_paused(match.group("id").lower(), match.group("digest").lower(), True, runtime_root=runtime_root)}
    match = _RESUME.fullmatch(text)
    if match:
        return {"active": True, **set_plan_paused(match.group("id").lower(), match.group("digest").lower(), False, runtime_root=runtime_root)}
    if lowered in {"show long horizon planning requirements", "inspect long horizon planning requirements"}:
        return {"active": True, "ok": True, "status": "long_horizon_planning_requirements", "requirements": [
            "original_objective_preserved", "milestone_dependencies", "task_dependencies", "success_criteria",
            "stop_conditions", "resource_estimates", "deferred_alternatives", "completed_work_preserved_on_replan",
            "failed_strategy_nonrepetition", "restart_safe_bookkeeping",
        ], **AUTHORITY_FLAGS}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "SCHEMA_VERSION", "AUTHORITY_FLAGS", "create_long_horizon_plan", "inspect_long_horizon_plan",
    "record_task_outcome", "revise_long_horizon_plan", "set_plan_paused", "legacy_hierarchy_projection",
    "process_long_horizon_planning_control",
]
