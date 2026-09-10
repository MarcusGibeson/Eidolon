from __future__ import annotations

"""Operator-governed work prioritization and bounded schedule preparation.

v1224 derives recommendations from the authoritative v1223 queue. Rankings,
overrides, reviews, and schedules are content-free planning evidence. They never
reuse approval, grant execution authority, contact providers, run tests, or
modify a selected project.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from unified_development_work_queue import (
    AUTHORITY_FLAGS as QUEUE_AUTHORITY_FLAGS,
    QUEUE_STATES,
    build_unified_development_work_queue,
    load_unified_development_work_queue,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1224.8"
MAX_PRIORITY_ITEMS = 500
MAX_SCHEDULE_SLOTS = 20
PRIORITY_LEVELS = {"low": 20, "normal": 50, "high": 80, "critical": 100}
REVIEW_DECISIONS = ("accept", "reject")
SCHEDULE_REVIEW_DECISIONS = ("accept", "reject", "revise")
SCHEDULABLE_STATES = ("active", "awaiting_approval", "resumable")

AUTHORITY_FLAGS = {
    **QUEUE_AUTHORITY_FLAGS,
    "ranking_execution_authorized": False,
    "schedule_execution_authorized": False,
    "work_dispatch_authorized": False,
    "background_execution_authorized": False,
}

_SHOW_PRIORITIES = re.compile(r"^(?:show development work priorities|what should we work on next|prioritize the development work queue)[.!?]*$", re.I)
_SHOW_SCHEDULE = re.compile(r"^show development work schedule[.!?]*$", re.I)
_SET_PRIORITY = re.compile(
    r"^set development work priority (?P<level>low|normal|high|critical) for item "
    r"(?P<item>work_[a-f0-9]{24}) prioritization (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)
_PIN = re.compile(
    r"^(?P<verb>pin|unpin) development work item (?P<item>work_[a-f0-9]{24}) "
    r"prioritization (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)
_DEPENDENCY = re.compile(
    r"^(?P<verb>add|remove) development work dependency (?P<item>work_[a-f0-9]{24}) "
    r"on (?P<dependency>work_[a-f0-9]{24}) prioritization (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)
_REVIEW = re.compile(
    r"^(?P<decision>accept|reject) development work prioritization (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)
_PREPARE_SCHEDULE = re.compile(
    r"^prepare development work schedule from prioritization (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)
_SCHEDULE_REVIEW = re.compile(
    r"^(?P<decision>accept|reject|revise) development work schedule (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)


def _prioritization_path(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_governed_work_prioritizations" / "current.json"


def _prioritization_snapshot_path(generation: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_governed_work_prioritization_snapshots" / f"generation-{generation:06d}.json"


def _override_path(item_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_governed_work_priority_overrides" / f"{item_id}.json"


def _override_snapshot_path(item_id: str, generation: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_governed_work_priority_override_snapshots" / item_id / f"generation-{generation:06d}.json"


def _review_path(prioritization_digest: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_governed_work_prioritization_reviews" / f"{prioritization_digest}.json"


def _schedule_path(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_governed_work_schedules" / "current.json"


def _schedule_snapshot_path(generation: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_governed_work_schedule_snapshots" / f"generation-{generation:06d}.json"


def _schedule_review_path(schedule_digest: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_governed_work_schedule_reviews" / f"{schedule_digest}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _store_root(runtime_root) / "locks" / "operator-governed-work-prioritization.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for prioritization lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "prioritization_is_derivative": True,
        "schedule_is_planning_evidence_only": True,
        "authoritative_queue_preserved": True,
        "runtime_records_external": True,
        "operator_review_required": True,
        "old_authority_reuse_forbidden": True,
        "provider_contacted": False,
        "tests_executed": False,
        "continuation_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_name_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["operator_governed_work_prioritization_result_digest"] = _digest(row)
    return row


def _load_overrides(runtime_root=None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    root = _store_root(runtime_root) / "operator_governed_work_priority_overrides"
    rows: dict[str, dict[str, Any]] = {}
    digests: list[str] = []
    if not root.exists():
        return rows, digests
    for path in sorted(root.glob("work_*.json")):
        row = _read_json(path)
        if not row or not _valid(row, "operator_governed_work_priority_override_record_digest"):
            raise ValueError("priority_override_tampered_or_malformed")
        item_id = str(row.get("queue_item_id") or "")
        if path.stem != item_id:
            raise ValueError("priority_override_item_binding_invalid")
        rows[item_id] = row
        digests.append(str(row["operator_governed_work_priority_override_record_digest"]))
    return rows, digests


def _state_score(state: str) -> int:
    return {
        "active": 80,
        "awaiting_approval": 75,
        "resumable": 70,
        "deferred": 25,
        "blocked": -100,
        "abandoned": -200,
        "closed": -250,
    }.get(str(state), -150)


def _dependency_cycles(graph: Mapping[str, list[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            try:
                cycles.update(trail[trail.index(node):])
            except ValueError:
                cycles.add(node)
            return
        if node in visited:
            return
        visiting.add(node)
        trail.append(node)
        for dep in graph.get(node, []):
            if dep in graph:
                visit(dep, trail)
        trail.pop()
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node, [])
    return cycles


def _rank_items(queue: Mapping[str, Any], overrides: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    source_items = {str(row.get("queue_item_id")): dict(row) for row in queue.get("items") or []}
    graph: dict[str, list[str]] = {}
    for item_id, item in source_items.items():
        override = dict(overrides.get(item_id) or {})
        dependencies = sorted(set(str(value) for value in override.get("dependency_item_ids") or []))
        if item_id in dependencies or any(dep not in source_items for dep in dependencies):
            raise ValueError("priority_dependency_binding_invalid")
        graph[item_id] = dependencies
    cycles = _dependency_cycles(graph)
    rows: list[dict[str, Any]] = []
    for item_id, item in source_items.items():
        override = dict(overrides.get(item_id) or {})
        level = str(override.get("priority_level") or "normal")
        if level not in PRIORITY_LEVELS:
            raise ValueError("priority_level_invalid")
        pinned = bool(override.get("pinned"))
        dependencies = graph[item_id]
        unsatisfied = [dep for dep in dependencies if source_items[dep].get("state") != "closed"]
        state = str(item.get("state") or "blocked")
        duplicate_conflict = bool(item.get("duplicate_active_conflict"))
        risk_penalty = (100 if duplicate_conflict else 0) + min(50, 10 * int(item.get("history_gap_count") or 0))
        fairness_credit = 10 if state == "deferred" else 0
        readiness_credit = 10 if state == "awaiting_approval" else (8 if state == "resumable" else 5 if state == "active" else 0)
        heuristic_score = _state_score(state) + PRIORITY_LEVELS[level] + fairness_credit + readiness_credit - risk_penalty
        if pinned:
            heuristic_score += 1000
        dependency_cycle = item_id in cycles
        schedulable = (
            state in SCHEDULABLE_STATES
            and not duplicate_conflict
            and not dependency_cycle
        )
        reasons = [f"state:{state}", f"operator_priority:{level}"]
        if pinned:
            reasons.append("operator_pin")
        if dependencies:
            reasons.append("dependencies_present")
        if unsatisfied:
            reasons.append("dependencies_require_ordering")
        if duplicate_conflict:
            reasons.append("duplicate_active_conflict")
        if dependency_cycle:
            reasons.append("dependency_cycle")
        if state not in SCHEDULABLE_STATES:
            reasons.append("state_not_schedulable")
        row = {
            "rank": 0,
            "queue_item_id": item_id,
            "proposal_id": str(item.get("proposal_id") or ""),
            "project_reference": str(item.get("project_reference") or ""),
            "queue_item_digest": str(item.get("queue_item_digest") or ""),
            "state": state,
            "current_stage": str(item.get("current_stage") or ""),
            "pending_operator_decision": str(item.get("pending_operator_decision") or ""),
            "safe_next_step": str(item.get("safe_next_step") or ""),
            "priority_level": level,
            "priority_value": PRIORITY_LEVELS[level],
            "pinned": pinned,
            "dependency_item_ids": dependencies,
            "unsatisfied_dependency_item_ids": unsatisfied,
            "dependency_cycle": dependency_cycle,
            "duplicate_active_conflict": duplicate_conflict,
            "schedule_eligible": schedulable,
            "heuristic_score": heuristic_score,
            "objective_evidence": {
                "queue_state": state,
                "history_gap_count": int(item.get("history_gap_count") or 0),
                "approval_required": bool(item.get("approval_required")),
                "approval_consumed": bool(item.get("approval_consumed")),
                "duplicate_active_conflict": duplicate_conflict,
            },
            "heuristic_reasons": reasons,
            "estimated_effort": "unknown",
            "urgency_evidence": "operator_override_only" if level != "normal" else "not_available",
            "risk_evidence": "queue_conflict_or_gap" if risk_penalty else "no_known_queue_conflict",
            "old_authority_reusable": False,
            "fresh_authority_required": True,
            "override_generation": int(override.get("generation") or 0),
            "override_digest": str(override.get("operator_governed_work_priority_override_record_digest") or ""),
        }
        row["priority_item_digest"] = _digest(row)
        rows.append(row)
    rows.sort(key=lambda row: (-int(row["pinned"]), -int(row["schedule_eligible"]), -int(row["heuristic_score"]), str(row["queue_item_id"])))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
        row["priority_item_digest"] = _digest({key: value for key, value in row.items() if key != "priority_item_digest"})
    return rows


def _validate_prioritization(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "operator_governed_work_prioritization_record_digest"):
        return False
    items = list(record.get("items") or [])
    if len(items) > MAX_PRIORITY_ITEMS:
        return False
    expected = _digest({
        "generation": int(record.get("generation") or 0),
        "previous_prioritization_digest": str(record.get("previous_prioritization_digest") or ""),
        "source_queue_digest": str(record.get("source_queue_digest") or ""),
        "source_set_digest": str(record.get("source_set_digest") or ""),
        "item_digests": [str(row.get("priority_item_digest") or "") for row in items],
    })
    return str(record.get("prioritization_digest") or "") == expected


def build_operator_governed_work_prioritization(*, runtime_root=None) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            queue = build_unified_development_work_queue(runtime_root=runtime_root)
            if queue.get("ok") is not True:
                raise ValueError("source_queue_unavailable")
            overrides, override_digests = _load_overrides(runtime_root)
            rows = _rank_items(queue, overrides)
            source_set_digest = _digest({
                "source_queue_digest": str(queue.get("queue_digest") or ""),
                "override_digests": override_digests,
            })
            existing = _read_json(_prioritization_path(runtime_root))
            if existing:
                if not _validate_prioritization(existing):
                    return _failure("operator_governed_work_prioritization_record_invalid", "persisted_prioritization_tampered_or_malformed")
                if str(existing.get("source_set_digest") or "") == source_set_digest:
                    return {**existing, "operation_status": "resumed"}
                generation = int(existing.get("generation") or 0) + 1
                previous = str(existing.get("prioritization_digest") or "")
            else:
                generation, previous = 1, ""
            prioritization_digest = _digest({
                "generation": generation,
                "previous_prioritization_digest": previous,
                "source_queue_digest": str(queue.get("queue_digest") or ""),
                "source_set_digest": source_set_digest,
                "item_digests": [str(row["priority_item_digest"]) for row in rows],
            })
            recommended = next((row for row in rows if row["schedule_eligible"]), {})
            row = {
                "ok": True,
                "status": "operator_governed_work_prioritization_ready",
                "generation": generation,
                "previous_prioritization_digest": previous,
                "prioritization_digest": prioritization_digest,
                "source_queue_generation": int(queue.get("generation") or 0),
                "source_queue_digest": str(queue.get("queue_digest") or ""),
                "source_set_digest": source_set_digest,
                "item_count": len(rows),
                "eligible_item_count": sum(1 for item in rows if item["schedule_eligible"]),
                "blocked_item_count": sum(1 for item in rows if not item["schedule_eligible"]),
                "recommended_queue_item_id": str(recommended.get("queue_item_id") or ""),
                "recommended_project_reference": str(recommended.get("project_reference") or ""),
                "items": rows,
                "accept_phrase": f"Accept development work prioritization {prioritization_digest}.",
                "reject_phrase": f"Reject development work prioritization {prioritization_digest}.",
                "prepare_schedule_phrase": f"Prepare development work schedule from prioritization {prioritization_digest}.",
                **_base(),
            }
            row = _sealed(row, "operator_governed_work_prioritization_record_digest")
            _atomic_json(_prioritization_snapshot_path(generation, runtime_root), row)
            _atomic_json(_prioritization_path(runtime_root), row)
            return {**row, "operation_status": "created" if generation == 1 else "refreshed"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("operator_governed_work_prioritization_blocked", str(exc))


def load_operator_governed_work_prioritization(*, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_prioritization_path(runtime_root))
    return row if row and _validate_prioritization(row) else {}


def _current_prioritization(expected_digest: str, runtime_root=None) -> tuple[dict[str, Any], dict[str, Any]]:
    prioritization = load_operator_governed_work_prioritization(runtime_root=runtime_root)
    queue = build_unified_development_work_queue(runtime_root=runtime_root)
    if not prioritization:
        raise ValueError("prioritization_missing_or_invalid")
    if str(prioritization.get("prioritization_digest") or "") != str(expected_digest or ""):
        raise ValueError("stale_prioritization_digest")
    if not queue or str(queue.get("queue_digest") or "") != str(prioritization.get("source_queue_digest") or ""):
        raise ValueError("stale_source_queue")
    return prioritization, queue


def record_work_priority_override(
    item_id: str, *, expected_prioritization_digest: str, priority_level: str | None = None,
    pinned: bool | None = None, dependency_item_id: str = "", dependency_action: str = "",
    exact_phrase: str = "", runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            prioritization, _ = _current_prioritization(expected_prioritization_digest, runtime_root)
            item_id = str(item_id or "").lower()
            if not any(row.get("queue_item_id") == item_id for row in prioritization.get("items") or []):
                raise ValueError("priority_item_missing")
            path = _override_path(item_id, runtime_root)
            existing = _read_json(path)
            if existing and not _valid(existing, "operator_governed_work_priority_override_record_digest"):
                raise ValueError("priority_override_tampered")
            level = str(priority_level or (existing or {}).get("priority_level") or "normal").lower()
            if level not in PRIORITY_LEVELS:
                raise ValueError("priority_level_invalid")
            pin_value = bool((existing or {}).get("pinned")) if pinned is None else bool(pinned)
            dependencies = set(str(value) for value in (existing or {}).get("dependency_item_ids") or [])
            dep = str(dependency_item_id or "").lower()
            if dependency_action:
                if dep == item_id or not any(row.get("queue_item_id") == dep for row in prioritization.get("items") or []):
                    raise ValueError("priority_dependency_binding_invalid")
                if dependency_action == "add":
                    dependencies.add(dep)
                elif dependency_action == "remove":
                    dependencies.discard(dep)
                else:
                    raise ValueError("priority_dependency_action_invalid")
            generation = int((existing or {}).get("generation") or 0) + 1
            row = {
                "ok": True,
                "status": "operator_governed_work_priority_override_recorded",
                "queue_item_id": item_id,
                "generation": generation,
                "previous_override_digest": str((existing or {}).get("operator_governed_work_priority_override_record_digest") or ""),
                "source_prioritization_digest": expected_prioritization_digest,
                "priority_level": level,
                "pinned": pin_value,
                "dependency_item_ids": sorted(dependencies),
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                **_base(),
            }
            row = _sealed(row, "operator_governed_work_priority_override_record_digest")
            _atomic_json(_override_snapshot_path(item_id, generation, runtime_root), row)
            _atomic_json(path, row)
        refreshed = build_operator_governed_work_prioritization(runtime_root=runtime_root)
        return {**row, "refreshed_prioritization": public_operator_governed_work_prioritization(refreshed)}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("operator_governed_work_priority_override_blocked", str(exc))


def record_work_prioritization_review(
    decision: str, *, expected_prioritization_digest: str, exact_phrase: str = "", runtime_root=None,
) -> dict[str, Any]:
    decision = str(decision or "").lower()
    if decision not in REVIEW_DECISIONS:
        return _failure("operator_governed_work_prioritization_review_invalid", "unsupported_decision")
    try:
        prioritization, _ = _current_prioritization(expected_prioritization_digest, runtime_root)
        path = _review_path(expected_prioritization_digest, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "operator_governed_work_prioritization_review_record_digest"):
                raise ValueError("prioritization_review_tampered")
            if existing.get("decision") == decision:
                return {**existing, "operation_status": "replayed"}
            raise ValueError("conflicting_prioritization_review")
        row = {
            "ok": True,
            "status": f"operator_governed_work_prioritization_{decision}ed",
            "decision": decision,
            "source_prioritization_generation": int(prioritization.get("generation") or 0),
            "source_prioritization_digest": expected_prioritization_digest,
            "source_queue_digest": str(prioritization.get("source_queue_digest") or ""),
            "exact_phrase_digest": _digest(str(exact_phrase or "")),
            "schedule_preparation_allowed": decision == "accept",
            **_base(),
        }
        row = _sealed(row, "operator_governed_work_prioritization_review_record_digest")
        _atomic_json(path, row)
        return {**row, "operation_status": "created"}
    except (OSError, ValueError) as exc:
        return _failure("operator_governed_work_prioritization_review_blocked", str(exc))


def _validate_schedule(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "operator_governed_work_schedule_record_digest"):
        return False
    slots = list(record.get("slots") or [])
    expected = _digest({
        "generation": int(record.get("generation") or 0),
        "previous_schedule_digest": str(record.get("previous_schedule_digest") or ""),
        "source_prioritization_digest": str(record.get("source_prioritization_digest") or ""),
        "slot_digests": [str(row.get("schedule_slot_digest") or "") for row in slots],
    })
    return len(slots) <= MAX_SCHEDULE_SLOTS and str(record.get("schedule_digest") or "") == expected


def prepare_operator_governed_work_schedule(*, expected_prioritization_digest: str, runtime_root=None) -> dict[str, Any]:
    try:
        prioritization, queue = _current_prioritization(expected_prioritization_digest, runtime_root)
        review = _read_json(_review_path(expected_prioritization_digest, runtime_root))
        if not review or not _valid(review, "operator_governed_work_prioritization_review_record_digest"):
            raise ValueError("accepted_prioritization_review_required")
        if review.get("decision") != "accept":
            raise ValueError("prioritization_not_accepted")
        if any(bool(row.get("dependency_cycle")) for row in prioritization.get("items") or []):
            raise ValueError("dependency_cycle_blocks_schedule")
        item_by_id = {str(row["queue_item_id"]): dict(row) for row in prioritization.get("items") or []}
        eligible = {item_id for item_id, row in item_by_id.items() if row.get("schedule_eligible")}
        ordered: list[dict[str, Any]] = []
        remaining = set(eligible)
        while remaining and len(ordered) < MAX_SCHEDULE_SLOTS:
            candidates = []
            for item_id in remaining:
                deps = set(item_by_id[item_id].get("dependency_item_ids") or [])
                unresolved = [dep for dep in deps if dep in remaining]
                invalid = [dep for dep in deps if dep not in eligible and next((q for q in queue.get("items") or [] if q.get("queue_item_id") == dep and q.get("state") == "closed"), None) is None]
                if not unresolved and not invalid:
                    candidates.append(item_by_id[item_id])
            if not candidates:
                break
            candidates.sort(key=lambda row: (int(row["rank"]), str(row["queue_item_id"])))
            chosen = candidates[0]
            remaining.remove(str(chosen["queue_item_id"]))
            slot = {
                "slot": len(ordered) + 1,
                "queue_item_id": str(chosen["queue_item_id"]),
                "project_reference": str(chosen["project_reference"]),
                "priority_rank": int(chosen["rank"]),
                "priority_level": str(chosen["priority_level"]),
                "dependency_item_ids": list(chosen.get("dependency_item_ids") or []),
                "safe_next_step": str(chosen.get("safe_next_step") or ""),
                "fresh_authority_required": True,
                "execution_authorized": False,
            }
            slot["schedule_slot_digest"] = _digest(slot)
            ordered.append(slot)
        path = _schedule_path(runtime_root)
        existing = _read_json(path)
        if existing:
            if not _validate_schedule(existing):
                raise ValueError("persisted_schedule_tampered_or_malformed")
            if str(existing.get("source_prioritization_digest") or "") == expected_prioritization_digest:
                return {**existing, "operation_status": "resumed"}
            generation = int(existing.get("generation") or 0) + 1
            previous = str(existing.get("schedule_digest") or "")
        else:
            generation, previous = 1, ""
        schedule_digest = _digest({
            "generation": generation,
            "previous_schedule_digest": previous,
            "source_prioritization_digest": expected_prioritization_digest,
            "slot_digests": [str(row["schedule_slot_digest"]) for row in ordered],
        })
        row = {
            "ok": True,
            "status": "operator_governed_work_schedule_ready",
            "generation": generation,
            "previous_schedule_digest": previous,
            "schedule_digest": schedule_digest,
            "source_prioritization_generation": int(prioritization.get("generation") or 0),
            "source_prioritization_digest": expected_prioritization_digest,
            "source_queue_digest": str(prioritization.get("source_queue_digest") or ""),
            "planning_horizon_slots": MAX_SCHEDULE_SLOTS,
            "slot_count": len(ordered),
            "unscheduled_eligible_item_ids": sorted(remaining),
            "slots": ordered,
            "accept_phrase": f"Accept development work schedule {schedule_digest}.",
            "reject_phrase": f"Reject development work schedule {schedule_digest}.",
            "revise_phrase": f"Revise development work schedule {schedule_digest}.",
            **_base(),
        }
        row = _sealed(row, "operator_governed_work_schedule_record_digest")
        _atomic_json(_schedule_snapshot_path(generation, runtime_root), row)
        _atomic_json(path, row)
        return {**row, "operation_status": "created" if generation == 1 else "refreshed"}
    except (OSError, ValueError) as exc:
        return _failure("operator_governed_work_schedule_blocked", str(exc))


def load_operator_governed_work_schedule(*, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_schedule_path(runtime_root))
    return row if row and _validate_schedule(row) else {}


def record_operator_governed_work_schedule_review(
    decision: str, *, expected_schedule_digest: str, exact_phrase: str = "", runtime_root=None,
) -> dict[str, Any]:
    decision = str(decision or "").lower()
    if decision not in SCHEDULE_REVIEW_DECISIONS:
        return _failure("operator_governed_work_schedule_review_invalid", "unsupported_decision")
    try:
        schedule = load_operator_governed_work_schedule(runtime_root=runtime_root)
        if not schedule or schedule.get("schedule_digest") != expected_schedule_digest:
            raise ValueError("stale_schedule_digest")
        current = load_operator_governed_work_prioritization(runtime_root=runtime_root)
        if not current or current.get("prioritization_digest") != schedule.get("source_prioritization_digest"):
            raise ValueError("stale_schedule_prioritization")
        path = _schedule_review_path(expected_schedule_digest, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "operator_governed_work_schedule_review_record_digest"):
                raise ValueError("schedule_review_tampered")
            if existing.get("decision") == decision:
                return {**existing, "operation_status": "replayed"}
            raise ValueError("conflicting_schedule_review")
        row = {
            "ok": True,
            "status": {"accept": "operator_governed_work_schedule_accepted", "reject": "operator_governed_work_schedule_rejected", "revise": "operator_governed_work_schedule_revised"}[decision],
            "decision": decision,
            "source_schedule_generation": int(schedule.get("generation") or 0),
            "source_schedule_digest": expected_schedule_digest,
            "source_prioritization_digest": str(schedule.get("source_prioritization_digest") or ""),
            "exact_phrase_digest": _digest(str(exact_phrase or "")),
            "bounded_work_order_approved": decision == "accept",
            "schedule_revision_requested": decision == "revise",
            "execution_authorized": False,
            **_base(),
        }
        row = _sealed(row, "operator_governed_work_schedule_review_record_digest")
        _atomic_json(path, row)
        return {**row, "operation_status": "created"}
    except (OSError, ValueError) as exc:
        return _failure("operator_governed_work_schedule_review_blocked", str(exc))


def _public_item(row: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "rank", "queue_item_id", "proposal_id", "project_reference", "state", "current_stage",
        "pending_operator_decision", "safe_next_step", "priority_level", "priority_value", "pinned",
        "dependency_item_ids", "unsatisfied_dependency_item_ids", "dependency_cycle",
        "duplicate_active_conflict", "schedule_eligible", "heuristic_score", "objective_evidence",
        "heuristic_reasons", "estimated_effort", "urgency_evidence", "risk_evidence",
        "old_authority_reusable", "fresh_authority_required", "priority_item_digest",
    }
    return {key: row.get(key) for key in allowed if key in row}


def public_operator_governed_work_prioritization(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("ok") is not True:
        return {key: record.get(key) for key in ("ok", "status", "reason") if key in record} | _base()
    row = {
        "ok": True,
        "status": "operator_governed_work_prioritization_ready",
        "generation": int(record.get("generation") or 0),
        "prioritization_digest": str(record.get("prioritization_digest") or ""),
        "source_queue_generation": int(record.get("source_queue_generation") or 0),
        "source_queue_digest": str(record.get("source_queue_digest") or ""),
        "item_count": int(record.get("item_count") or 0),
        "eligible_item_count": int(record.get("eligible_item_count") or 0),
        "blocked_item_count": int(record.get("blocked_item_count") or 0),
        "recommended_queue_item_id": str(record.get("recommended_queue_item_id") or ""),
        "recommended_project_reference": str(record.get("recommended_project_reference") or ""),
        "items": [_public_item(item) for item in record.get("items") or []],
        "accept_phrase": str(record.get("accept_phrase") or ""),
        "reject_phrase": str(record.get("reject_phrase") or ""),
        "prepare_schedule_phrase": str(record.get("prepare_schedule_phrase") or ""),
        **_base(),
    }
    row["public_operator_governed_work_prioritization_digest"] = _digest(row)
    return row


def public_operator_governed_work_schedule(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("ok") is not True:
        return {key: record.get(key) for key in ("ok", "status", "reason") if key in record} | _base()
    row = {
        "ok": True,
        "status": "operator_governed_work_schedule_ready",
        "generation": int(record.get("generation") or 0),
        "schedule_digest": str(record.get("schedule_digest") or ""),
        "source_prioritization_digest": str(record.get("source_prioritization_digest") or ""),
        "planning_horizon_slots": int(record.get("planning_horizon_slots") or 0),
        "slot_count": int(record.get("slot_count") or 0),
        "unscheduled_eligible_item_ids": list(record.get("unscheduled_eligible_item_ids") or []),
        "slots": list(record.get("slots") or []),
        "accept_phrase": str(record.get("accept_phrase") or ""),
        "reject_phrase": str(record.get("reject_phrase") or ""),
        "revise_phrase": str(record.get("revise_phrase") or ""),
        **_base(),
    }
    row["public_operator_governed_work_schedule_digest"] = _digest(row)
    return row


def operator_governed_work_prioritization_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if record.get("ok") is not True:
        return f"Work prioritization was blocked: {record.get('reason', status or 'invalid evidence')}."
    if status == "operator_governed_work_prioritization_ready":
        recommended = record.get("recommended_queue_item_id") or "none"
        return (
            f"The governed work prioritization contains {record.get('item_count', 0)} items; "
            f"{record.get('eligible_item_count', 0)} are schedule-eligible. Recommended next item: {recommended}. "
            "The ranking is advisory and grants no execution authority."
        )
    if status == "operator_governed_work_schedule_ready":
        return (
            f"The bounded work schedule contains {record.get('slot_count', 0)} planning slots. "
            "It is planning evidence only and does not start any work."
        )
    return f"The governed work control recorded: {status}. No development work was executed."


def process_operator_governed_work_prioritization_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match_priority = _SET_PRIORITY.fullmatch(text)
    match_pin = _PIN.fullmatch(text)
    match_dep = _DEPENDENCY.fullmatch(text)
    match_review = _REVIEW.fullmatch(text)
    match_prepare = _PREPARE_SCHEDULE.fullmatch(text)
    match_schedule_review = _SCHEDULE_REVIEW.fullmatch(text)
    if _SHOW_PRIORITIES.fullmatch(text):
        result = public_operator_governed_work_prioritization(build_operator_governed_work_prioritization(runtime_root=runtime_root))
    elif _SHOW_SCHEDULE.fullmatch(text):
        schedule = load_operator_governed_work_schedule(runtime_root=runtime_root)
        result = public_operator_governed_work_schedule(schedule) if schedule else _failure("operator_governed_work_schedule_missing")
    elif match_priority:
        result = record_work_priority_override(
            match_priority.group("item").lower(), expected_prioritization_digest=match_priority.group("digest").lower(),
            priority_level=match_priority.group("level").lower(), exact_phrase=text, runtime_root=runtime_root,
        )
    elif match_pin:
        result = record_work_priority_override(
            match_pin.group("item").lower(), expected_prioritization_digest=match_pin.group("digest").lower(),
            pinned=match_pin.group("verb").lower() == "pin", exact_phrase=text, runtime_root=runtime_root,
        )
    elif match_dep:
        result = record_work_priority_override(
            match_dep.group("item").lower(), expected_prioritization_digest=match_dep.group("digest").lower(),
            dependency_item_id=match_dep.group("dependency").lower(), dependency_action=match_dep.group("verb").lower(),
            exact_phrase=text, runtime_root=runtime_root,
        )
    elif match_review:
        result = record_work_prioritization_review(
            match_review.group("decision").lower(), expected_prioritization_digest=match_review.group("digest").lower(),
            exact_phrase=text, runtime_root=runtime_root,
        )
    elif match_prepare:
        result = prepare_operator_governed_work_schedule(
            expected_prioritization_digest=match_prepare.group("digest").lower(), runtime_root=runtime_root,
        )
        result = public_operator_governed_work_schedule(result)
    elif match_schedule_review:
        result = record_operator_governed_work_schedule_review(
            match_schedule_review.group("decision").lower(), expected_schedule_digest=match_schedule_review.group("digest").lower(),
            exact_phrase=text, runtime_root=runtime_root,
        )
    else:
        return {"active": False, "event": "inactive"}
    public = result
    if result.get("refreshed_prioritization"):
        public = {key: value for key, value in result.items() if key != "exact_phrase"}
    public.update(_base())
    return {
        "active": True,
        "event": str(result.get("status") or "operator_governed_work_prioritization_blocked"),
        "operator_governed_work_prioritization": public,
        "conversation_response": operator_governed_work_prioritization_response(public),
    }
