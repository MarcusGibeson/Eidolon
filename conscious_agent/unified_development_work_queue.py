from __future__ import annotations

"""Unified, privacy-safe work queue for supervised development transactions.

v1223 derives one queue from the authoritative proposal, v1221 history, and
v1222 resumption records already stored outside the source tree.  Queue records
are content-free indexes.  They never replace those receipts, reuse authority,
execute work, contact a provider, run tests, or modify a selected project.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _read_json,
    _store_root,
    _validate,
)
from transaction_resumption_abandoned_work_reconciliation import (
    build_transaction_resumption_assessment,
    load_transaction_resumption_assessment,
    load_transaction_resumption_decision,
)
from unified_supervised_development_transaction_history import (
    build_unified_supervised_development_transaction_history,
    load_unified_supervised_development_transaction_history,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1223.8"
MAX_QUEUE_ITEMS = 500
MAX_PAGE_SIZE = 50
QUEUE_STATES = (
    "active",
    "awaiting_approval",
    "resumable",
    "blocked",
    "deferred",
    "abandoned",
    "closed",
)
QUEUE_ITEM_ACTIONS = ("focus", "defer", "close", "propose-reopen")
AUTHORITY_FLAGS = {
    "prior_approval_reusable": False,
    "prior_authorization_reusable": False,
    "provider_contact_authorized": False,
    "test_execution_authorized": False,
    "continuation_execution_authorized": False,
    "diagnosis_authorized": False,
    "repair_execution_authorized": False,
    "apply_execution_authorized": False,
    "rollback_execution_authorized": False,
    "install_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "authority_granted": False,
}

_SHOW_QUEUE = re.compile(
    r"^show\s+unified\s+development\s+work\s+queue"
    r"(?:\s+filter\s+(?P<filter>all|active|awaiting-approval|resumable|blocked|deferred|abandoned|closed))?"
    r"(?:\s+page\s+(?P<page>[1-9][0-9]*)\s+size\s+(?P<size>[1-9][0-9]*))?[.!?]*$",
    re.I,
)
_SHOW_AWAITING = re.compile(r"^show\s+development\s+work\s+awaiting\s+approval[.!?]*$", re.I)
_SHOW_STATE = {
    "blocked": re.compile(r"^show\s+blocked\s+development\s+work[.!?]*$", re.I),
    "deferred": re.compile(r"^show\s+deferred\s+development\s+work[.!?]*$", re.I),
    "resumable": re.compile(r"^show\s+resumable\s+development\s+work[.!?]*$", re.I),
}
_SHOW_PROJECT = re.compile(
    r"^show\s+development\s+project\s+state\s+(?P<project_reference>project_[a-f0-9]{16})[.!?]*$",
    re.I,
)
_FOCUS = re.compile(
    r"^focus\s+development\s+work\s+item\s+(?P<item_id>work_[a-f0-9]{24})\s+"
    r"queue\s+(?P<queue_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_ITEM_ACTION = re.compile(
    r"^(?P<verb>record\s+defer|record\s+close|propose\s+reopen)\s+for\s+development\s+work\s+item\s+"
    r"(?P<item_id>work_[a-f0-9]{24})\s+queue\s+(?P<queue_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)


def _queue_path(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "unified_development_work_queues" / "current.json"


def _queue_snapshot_path(generation: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "unified_development_work_queue_snapshots" / f"generation-{int(generation):06d}.json"


def _item_control_path(item_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "unified_development_work_queue_item_controls" / f"{item_id}.json"


def _item_control_snapshot_path(item_id: str, generation: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "unified_development_work_queue_item_control_snapshots"
        / item_id
        / f"generation-{int(generation):06d}.json"
    )


def _focus_path(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "unified_development_work_queue_focus" / "current.json"


def _focus_snapshot_path(generation: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "unified_development_work_queue_focus_snapshots" / f"generation-{int(generation):06d}.json"


def _reopen_proposal_path(item_id: str, generation: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "unified_development_work_queue_reopen_proposals"
        / item_id
        / f"generation-{int(generation):06d}.json"
    )


@contextmanager
def _queue_lock(runtime_root=None):
    lock = _store_root(runtime_root) / "locks" / "unified-development-work-queue.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            lock.mkdir()
            (lock / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 60.0:
                    shutil.rmtree(lock, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for unified development work queue lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(lock, ignore_errors=True)


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
        "queue_is_derivative": True,
        "authoritative_receipts_preserved": True,
        "runtime_records_external": True,
        "operator_review_required": True,
        "old_authority_reuse_forbidden": True,
        "new_approval_required_before_continuation": True,
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
    row["unified_development_work_queue_result_digest"] = _digest(row)
    return row


def _sha(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if len(token) == 64 and all(ch in "0123456789abcdef" for ch in token) else ""


def _project_identity(proposal: Mapping[str, Any]) -> tuple[str, str]:
    target = dict(proposal.get("target") or {})
    binding = {
        "target_digest": _sha(target.get("target_digest")),
        "path_digest": _sha(target.get("path_digest")),
        "project_id_digest": _digest(str(target.get("project_id") or "")) if target.get("project_id") else "",
        "target_mode": str(target.get("mode") or "unknown")[:40],
    }
    if not any(binding[key] for key in ("target_digest", "path_digest", "project_id_digest")):
        binding["proposal_fallback_digest"] = _digest(str(proposal.get("proposal_id") or ""))
    digest = _digest(binding)
    return digest, f"project_{digest[:16]}"


def _latest_status(history: Mapping[str, Any]) -> str:
    events = list(history.get("events") or [])
    return str((events[-1] if events else {}).get("status") or history.get("current_state") or "")


def classify_work_item_state(
    proposal: Mapping[str, Any],
    history: Mapping[str, Any],
    assessment: Mapping[str, Any],
    resumption_decision: Mapping[str, Any] | None = None,
    queue_control: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one transaction into a queue state without granting authority."""

    resumption_decision = dict(resumption_decision or {})
    queue_control = dict(queue_control or {})
    classification = str(assessment.get("classification") or "review_required")
    last_stage = str(assessment.get("last_trustworthy_stage") or history.get("last_observed_stage") or "")
    latest = _latest_status(history).lower()
    lifecycle = str(proposal.get("lifecycle_state") or "").lower()
    decision = str(resumption_decision.get("decision") or "").lower()
    control_action = str(queue_control.get("action") or "").lower()

    if control_action == "close":
        state, pending, next_step = "closed", "none", "none"
    elif control_action == "defer":
        state, pending, next_step = "deferred", "operator_reopen_or_close", "review_deferred_work"
    elif control_action == "propose-reopen":
        state, pending, next_step = "awaiting_approval", "fresh_reopen_approval", "review_fresh_reopen_proposal"
    elif decision == "close-as-abandoned":
        state, pending, next_step = "abandoned", "none", "none"
    elif decision == "defer":
        state, pending, next_step = "deferred", "operator_reopen_or_close", "review_deferred_work"
    elif decision in {"resume-planning", "begin-fresh-attempt"}:
        state, pending, next_step = "awaiting_approval", "fresh_continuation_approval", "review_fresh_continuation_proposal"
    elif classification == "permanently_closed" or history.get("terminal") is True or lifecycle in {"cancelled", "rejected"}:
        state, pending, next_step = "closed", "none", "none"
    elif lifecycle == "awaiting_approval" and proposal.get("approval_consumed") is not True:
        state, pending, next_step = "awaiting_approval", "proposal_approval", "review_current_proposal"
    elif classification == "safely_resumable":
        state, pending, next_step = "resumable", "resumption_disposition", "review_and_prepare_fresh_continuation"
    elif classification == "restart_required":
        state, pending, next_step = "blocked", "fresh_attempt_decision", "review_and_begin_fresh_attempt"
    elif assessment.get("inconsistency_detected") is True:
        state, pending, next_step = "blocked", "inconsistency_investigation", "investigate_transaction_evidence"
    elif any(token in latest for token in ("running", "in_progress", "executing")):
        state, pending, next_step = "active", "none", "await_current_bounded_operation"
    else:
        state, pending, next_step = "blocked", "operator_review", "review_current_transaction_state"

    return {
        "state": state,
        "pending_operator_decision": pending,
        "safe_next_step": next_step,
        "current_stage": last_stage,
        "resumption_classification": classification,
        "fresh_authority_required": state not in {"closed", "abandoned"},
        "old_authority_reusable": False,
    }


def _validated_optional(path: Path, digest_field: str) -> tuple[dict[str, Any], str]:
    row = _read_json(path)
    if not row:
        return {}, ""
    if not _valid(row, digest_field):
        raise ValueError(f"tampered:{path.parent.name}")
    return row, str(row.get(digest_field) or "")


def _proposal_rows(runtime_root=None) -> Iterable[tuple[Path, dict[str, Any]]]:
    root = _store_root(runtime_root) / "proposals"
    if not root.is_dir():
        return ()
    paths = sorted(root.glob("devc_*.json"))
    if len(paths) > MAX_QUEUE_ITEMS:
        raise ValueError("queue_item_limit_exceeded")
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        proposal = _read_json(path)
        if not proposal or not _validate(proposal):
            raise ValueError(f"invalid_proposal:{path.stem}")
        rows.append((path, proposal))
    return tuple(rows)


def _build_item(proposal: Mapping[str, Any], runtime_root=None) -> dict[str, Any]:
    proposal_id = str(proposal.get("proposal_id") or "")
    revision = int(proposal.get("revision") or 0)
    history = build_unified_supervised_development_transaction_history(
        proposal_id, expected_revision=revision, runtime_root=runtime_root
    )
    if history.get("ok") is not True:
        raise ValueError(f"history_blocked:{proposal_id}:{history.get('status')}")
    assessment = build_transaction_resumption_assessment(
        proposal_id, expected_revision=revision, runtime_root=runtime_root
    )
    if assessment.get("ok") is not True:
        raise ValueError(f"assessment_blocked:{proposal_id}:{assessment.get('status')}")
    decision = load_transaction_resumption_decision(proposal_id, revision, runtime_root=runtime_root)
    project_digest, project_reference = _project_identity(proposal)
    item_id = "work_" + _digest({
        "proposal_id": proposal_id,
        "revision": revision,
        "project_identity_digest": project_digest,
    })[:24]
    control, control_digest = _validated_optional(
        _item_control_path(item_id, runtime_root), "unified_development_work_queue_item_control_record_digest"
    )
    state = classify_work_item_state(proposal, history, assessment, decision, control)
    source_binding = {
        "proposal_digest": str(proposal.get("proposal_digest") or ""),
        "history_digest": str(history.get("history_digest") or ""),
        "assessment_digest": str(assessment.get("assessment_digest") or ""),
        "resumption_decision_digest": str(decision.get("transaction_resumption_decision_digest") or ""),
        "queue_control_digest": control_digest,
    }
    item = {
        "queue_item_id": item_id,
        "proposal_id": proposal_id,
        "proposal_revision": revision,
        "project_identity_digest": project_digest,
        "project_reference": project_reference,
        **state,
        "history_generation": int(history.get("generation") or 0),
        "history_digest": str(history.get("history_digest") or ""),
        "assessment_generation": int(assessment.get("assessment_generation") or 0),
        "assessment_digest": str(assessment.get("assessment_digest") or ""),
        "history_event_count": int(history.get("event_count") or 0),
        "history_gap_count": int(history.get("gap_count") or 0),
        "proposal_updated_at": str(proposal.get("updated_at") or proposal.get("created_at") or ""),
        "approval_required": bool(proposal.get("approval_required")),
        "approval_consumed": bool(proposal.get("approval_consumed")),
        "duplicate_active_conflict": False,
        "underlying_state": state["state"],
        "source_binding_digest": _digest(source_binding),
        "control_generation": int(control.get("control_generation") or 0),
        "control_action": str(control.get("action") or ""),
    }
    item["queue_item_digest"] = _digest(item)
    return item


def _is_open(state: str) -> bool:
    return state not in {"closed", "abandoned", "deferred"}


def _apply_project_conflicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(str(item["project_identity_digest"]), []).append(item)
    for group in groups.values():
        open_items = [item for item in group if _is_open(str(item.get("state") or ""))]
        if len(open_items) > 1:
            for item in open_items:
                item["duplicate_active_conflict"] = True
                item["state"] = "blocked"
                item["pending_operator_decision"] = "duplicate_active_work_resolution"
                item["safe_next_step"] = "review_conflicting_project_transactions"
                item["queue_item_digest"] = _digest({key: value for key, value in item.items() if key != "queue_item_digest"})
    return items


def _current_item(group: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        group,
        key=lambda row: (
            str(row.get("proposal_updated_at") or ""),
            int(row.get("proposal_revision") or 0),
            str(row.get("proposal_id") or ""),
        ),
    )[-1]


def _project_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(str(item["project_identity_digest"]), []).append(item)
    projects: list[dict[str, Any]] = []
    for digest, group in sorted(groups.items()):
        current = _current_item(group)
        open_count = sum(1 for row in group if _is_open(str(row.get("state") or "")))
        conflict = any(row.get("duplicate_active_conflict") is True for row in group)
        row = {
            "project_identity_digest": digest,
            "project_reference": str(current.get("project_reference") or ""),
            "work_item_count": len(group),
            "open_work_item_count": open_count,
            "current_queue_item_id": str(current.get("queue_item_id") or ""),
            "current_proposal_id": str(current.get("proposal_id") or ""),
            "current_proposal_revision": int(current.get("proposal_revision") or 0),
            "project_state": "blocked" if conflict else str(current.get("state") or "blocked"),
            "pending_operator_decision": str(current.get("pending_operator_decision") or ""),
            "safe_next_step": str(current.get("safe_next_step") or ""),
            "duplicate_active_conflict": conflict,
        }
        row["project_state_digest"] = _digest(row)
        projects.append(row)
    return projects


def _validate_queue(record: Mapping[str, Any]) -> bool:
    return (
        _valid(record, "unified_development_work_queue_record_digest")
        and str(record.get("queue_digest") or "")
        == _digest({
            "generation": int(record.get("generation") or 0),
            "previous_queue_digest": str(record.get("previous_queue_digest") or ""),
            "source_set_digest": str(record.get("source_set_digest") or ""),
            "item_digests": [str(row.get("queue_item_digest") or "") for row in record.get("items") or []],
            "project_digests": [str(row.get("project_state_digest") or "") for row in record.get("projects") or []],
            "focus_item_id": str(record.get("focus_item_id") or ""),
        })
    )


def build_unified_development_work_queue(*, runtime_root=None) -> dict[str, Any]:
    try:
        with _queue_lock(runtime_root):
            items = [_build_item(proposal, runtime_root) for _, proposal in _proposal_rows(runtime_root)]
            items = _apply_project_conflicts(items)
            items.sort(key=lambda row: (str(row["project_reference"]), str(row["queue_item_id"])))
            focus, focus_digest = _validated_optional(
                _focus_path(runtime_root), "unified_development_work_queue_focus_record_digest"
            )
            focus_item_id = str(focus.get("queue_item_id") or "")
            if focus_item_id and not any(row["queue_item_id"] == focus_item_id for row in items):
                raise ValueError("focus_item_missing")
            projects = _project_rows(items)
            source_set_digest = _digest({
                "item_sources": [str(row["source_binding_digest"]) for row in items],
                "focus_digest": focus_digest,
            })
            path = _queue_path(runtime_root)
            existing = _read_json(path)
            if existing:
                if not _validate_queue(existing):
                    return _failure("unified_development_work_queue_record_invalid", "persisted_queue_tampered_or_malformed")
                if str(existing.get("source_set_digest") or "") == source_set_digest:
                    return {**existing, "operation_status": "resumed"}
                generation = int(existing.get("generation") or 0) + 1
                previous = str(existing.get("queue_digest") or "")
            else:
                generation, previous = 1, ""
            queue_digest = _digest({
                "generation": generation,
                "previous_queue_digest": previous,
                "source_set_digest": source_set_digest,
                "item_digests": [str(row["queue_item_digest"]) for row in items],
                "project_digests": [str(row["project_state_digest"]) for row in projects],
                "focus_item_id": focus_item_id,
            })
            for item in items:
                item["focus_phrase"] = f"Focus development work item {item['queue_item_id']} queue {queue_digest}."
                item["defer_phrase"] = (
                    f"Record defer for development work item {item['queue_item_id']} queue {queue_digest}."
                    if item["state"] not in {"closed", "abandoned", "deferred"} else ""
                )
                item["close_phrase"] = (
                    f"Record close for development work item {item['queue_item_id']} queue {queue_digest}."
                    if item["state"] not in {"closed", "abandoned"} else ""
                )
                item["reopen_phrase"] = (
                    f"Propose reopen for development work item {item['queue_item_id']} queue {queue_digest}."
                    if item["state"] == "deferred" else ""
                )
            counts = {state: sum(1 for row in items if row.get("state") == state) for state in QUEUE_STATES}
            row = {
                "ok": True,
                "status": "unified_development_work_queue_ready",
                "generation": generation,
                "previous_queue_digest": previous,
                "queue_digest": queue_digest,
                "source_set_digest": source_set_digest,
                "item_count": len(items),
                "project_count": len(projects),
                "state_counts": counts,
                "focus_item_id": focus_item_id,
                "items": items,
                "projects": projects,
                **_base(),
            }
            row = _sealed(row, "unified_development_work_queue_record_digest")
            _atomic_json(_queue_snapshot_path(generation, runtime_root), row)
            _atomic_json(path, row)
            return {**row, "operation_status": "created" if generation == 1 else "refreshed"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("unified_development_work_queue_blocked", str(exc))


def load_unified_development_work_queue(*, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_queue_path(runtime_root))
    return row if row and _validate_queue(row) else {}


def _public_item(item: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "queue_item_id", "proposal_id", "proposal_revision", "project_identity_digest",
        "project_reference", "state", "pending_operator_decision", "safe_next_step",
        "current_stage", "resumption_classification", "fresh_authority_required",
        "old_authority_reusable", "history_generation", "history_digest",
        "assessment_generation", "assessment_digest", "history_event_count",
        "history_gap_count", "approval_required", "approval_consumed",
        "duplicate_active_conflict", "underlying_state", "queue_item_digest",
        "control_generation", "control_action", "focus_phrase", "defer_phrase",
        "close_phrase", "reopen_phrase",
    }
    return {key: item.get(key) for key in allowed if key in item}


def public_unified_development_work_queue(
    record: Mapping[str, Any], *, state_filter: str = "all", page: int = 1, size: int = 20,
    project_reference: str = "",
) -> dict[str, Any]:
    if record.get("ok") is not True:
        return {key: record.get(key) for key in ("ok", "status", "reason") if key in record} | _base()
    state_filter = str(state_filter or "all").replace("-", "_")
    if state_filter == "awaiting_approval":
        state_token = "awaiting_approval"
    else:
        state_token = state_filter
    items = [dict(row) for row in record.get("items") or []]
    if project_reference:
        items = [row for row in items if row.get("project_reference") == project_reference]
    if state_token != "all":
        items = [row for row in items if row.get("state") == state_token]
    page = max(1, int(page or 1)); size = max(1, min(MAX_PAGE_SIZE, int(size or 20)))
    start = (page - 1) * size
    projects = [dict(row) for row in record.get("projects") or []]
    if project_reference:
        projects = [row for row in projects if row.get("project_reference") == project_reference]
    public = {
        "ok": True,
        "status": "unified_development_work_queue_ready",
        "generation": int(record.get("generation") or 0),
        "queue_digest": str(record.get("queue_digest") or ""),
        "item_count": len(items),
        "project_count": len(projects),
        "total_queue_item_count": int(record.get("item_count") or 0),
        "total_project_count": int(record.get("project_count") or 0),
        "state_counts": dict(record.get("state_counts") or {}),
        "focus_item_id": str(record.get("focus_item_id") or ""),
        "filter": state_token,
        "page": page,
        "page_size": size,
        "has_more": start + size < len(items),
        "items": [_public_item(row) for row in items[start:start + size]],
        "projects": projects,
        **_base(),
    }
    public["public_unified_development_work_queue_digest"] = _digest(public)
    return public


def _find_item(queue: Mapping[str, Any], item_id: str) -> dict[str, Any]:
    return next((dict(row) for row in queue.get("items") or [] if row.get("queue_item_id") == item_id), {})


def _reopen_proposal(item: Mapping[str, Any], control_generation: int, queue_digest: str, runtime_root=None) -> dict[str, Any]:
    binding = {
        "contract_version": CONTRACT_VERSION,
        "queue_item_id": str(item.get("queue_item_id") or ""),
        "proposal_id": str(item.get("proposal_id") or ""),
        "proposal_revision": int(item.get("proposal_revision") or 0),
        "project_identity_digest": str(item.get("project_identity_digest") or ""),
        "source_queue_digest": queue_digest,
        "control_generation": int(control_generation),
        "fresh_authority_required": True,
        "prior_authority_reusable": False,
    }
    digest = _digest(binding)
    row = {
        "ok": True,
        "status": "unified_development_work_queue_reopen_proposal_ready",
        **binding,
        "reopen_proposal_digest": digest,
        "approval_phrase": f"Approve development work queue reopen proposal {digest} item {binding['queue_item_id']}.",
        "approval_consumed": False,
        "continuation_executed": False,
        **_base(),
    }
    row = _sealed(row, "unified_development_work_queue_reopen_proposal_record_digest")
    _atomic_json(_reopen_proposal_path(binding["queue_item_id"], control_generation, runtime_root), row)
    return row


def record_unified_development_work_queue_item_action(
    item_id: str, *, action: str, expected_queue_digest: str, exact_phrase: str, runtime_root=None
) -> dict[str, Any]:
    item_id = str(item_id or "").lower(); action = str(action or "").lower()
    if action not in {"defer", "close", "propose-reopen"}:
        return _failure("unified_development_work_queue_action_invalid", "unsupported_action")
    path = _item_control_path(item_id, runtime_root)
    existing = _read_json(path)
    if existing:
        if not _valid(existing, "unified_development_work_queue_item_control_record_digest"):
            return _failure("unified_development_work_queue_action_record_invalid", "persisted_control_tampered")
        if (
            existing.get("action") == action
            and existing.get("source_queue_digest") == expected_queue_digest
            and existing.get("exact_phrase") == exact_phrase
        ):
            return {**existing, "operation_status": "resumed"}
    queue = build_unified_development_work_queue(runtime_root=runtime_root)
    if queue.get("ok") is not True or str(queue.get("queue_digest") or "") != str(expected_queue_digest or "").lower():
        return _failure("unified_development_work_queue_action_stale", "current_queue_digest_mismatch")
    item = _find_item(queue, item_id)
    if not item:
        return _failure("unified_development_work_queue_action_item_missing", "queue_item_not_found")
    state = str(item.get("state") or "")
    allowed = {
        "defer": state not in {"closed", "abandoned", "deferred"},
        "close": state not in {"closed", "abandoned"},
        "propose-reopen": state == "deferred",
    }[action]
    if not allowed:
        return _failure("unified_development_work_queue_action_not_allowed", f"action_not_allowed_from_{state}")
    expected_phrase = {
        "defer": str(item.get("defer_phrase") or ""),
        "close": str(item.get("close_phrase") or ""),
        "propose-reopen": str(item.get("reopen_phrase") or ""),
    }[action]
    if exact_phrase != expected_phrase:
        return _failure("unified_development_work_queue_action_phrase_invalid", "exact_current_phrase_required")
    with _queue_lock(runtime_root):
        current = _read_json(path)
        generation = int(current.get("control_generation") or 0) + 1 if current else 1
        previous = str(current.get("control_digest") or "") if current else ""
        binding = {
            "contract_version": CONTRACT_VERSION,
            "queue_item_id": item_id,
            "proposal_id": str(item.get("proposal_id") or ""),
            "proposal_revision": int(item.get("proposal_revision") or 0),
            "project_identity_digest": str(item.get("project_identity_digest") or ""),
            "action": action,
            "control_generation": generation,
            "previous_control_digest": previous,
            "source_queue_digest": str(expected_queue_digest).lower(),
            "source_queue_item_digest": str(item.get("queue_item_digest") or ""),
            "exact_phrase": exact_phrase,
        }
        control_digest = _digest(binding)
        row = {
            "ok": True,
            "status": "unified_development_work_queue_item_action_recorded",
            **binding,
            "control_digest": control_digest,
            "decision_state": {
                "defer": "queue_item_deferred",
                "close": "queue_item_closed",
                "propose-reopen": "fresh_reopen_proposed",
            }[action],
            **_base(),
        }
        if action == "propose-reopen":
            row["reopen_proposal"] = _reopen_proposal(item, generation, expected_queue_digest, runtime_root)
        row = _sealed(row, "unified_development_work_queue_item_control_record_digest")
        _atomic_json(_item_control_snapshot_path(item_id, generation, runtime_root), row)
        _atomic_json(path, row)
    refreshed = build_unified_development_work_queue(runtime_root=runtime_root)
    return {**row, "operation_status": "created", "refreshed_queue_digest": str(refreshed.get("queue_digest") or "")}


def record_unified_development_work_queue_focus(
    item_id: str, *, expected_queue_digest: str, exact_phrase: str, runtime_root=None
) -> dict[str, Any]:
    path = _focus_path(runtime_root)
    existing = _read_json(path)
    if existing:
        if not _valid(existing, "unified_development_work_queue_focus_record_digest"):
            return _failure("unified_development_work_queue_focus_record_invalid", "persisted_focus_tampered")
        if (
            existing.get("queue_item_id") == item_id
            and existing.get("source_queue_digest") == expected_queue_digest
            and existing.get("exact_phrase") == exact_phrase
        ):
            return {**existing, "operation_status": "resumed"}
    queue = build_unified_development_work_queue(runtime_root=runtime_root)
    if queue.get("ok") is not True or str(queue.get("queue_digest") or "") != str(expected_queue_digest or "").lower():
        return _failure("unified_development_work_queue_focus_stale", "current_queue_digest_mismatch")
    item = _find_item(queue, item_id)
    if not item or exact_phrase != str(item.get("focus_phrase") or ""):
        return _failure("unified_development_work_queue_focus_invalid", "exact_current_item_phrase_required")
    with _queue_lock(runtime_root):
        current = _read_json(path)
        generation = int(current.get("focus_generation") or 0) + 1 if current else 1
        binding = {
            "contract_version": CONTRACT_VERSION,
            "focus_generation": generation,
            "previous_focus_digest": str(current.get("focus_digest") or "") if current else "",
            "queue_item_id": item_id,
            "proposal_id": str(item.get("proposal_id") or ""),
            "proposal_revision": int(item.get("proposal_revision") or 0),
            "project_identity_digest": str(item.get("project_identity_digest") or ""),
            "source_queue_digest": str(expected_queue_digest).lower(),
            "source_queue_item_digest": str(item.get("queue_item_digest") or ""),
            "exact_phrase": exact_phrase,
        }
        row = {
            "ok": True,
            "status": "unified_development_work_queue_focus_recorded",
            **binding,
            "focus_digest": _digest(binding),
            **_base(),
        }
        row = _sealed(row, "unified_development_work_queue_focus_record_digest")
        _atomic_json(_focus_snapshot_path(generation, runtime_root), row)
        _atomic_json(path, row)
    refreshed = build_unified_development_work_queue(runtime_root=runtime_root)
    return {**row, "operation_status": "created", "refreshed_queue_digest": str(refreshed.get("queue_digest") or "")}


def unified_development_work_queue_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "unified_development_work_queue_ready":
        items = list(record.get("items") or [])
        if not items:
            return "The supervised development work queue is empty. No authority or project state changed."
        summary = ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in (record.get("state_counts") or {}).items() if value)
        visible = "; ".join(
            f"{row.get('queue_item_id')} {row.get('project_reference')} is {str(row.get('state')).replace('_', ' ')}; next: {str(row.get('safe_next_step')).replace('_', ' ')}"
            for row in items[:10]
        )
        return f"Unified development work queue: {summary or 'no classified items'}. {visible} No queue item grants execution authority."
    if status == "unified_development_work_queue_focus_recorded":
        return "The work item is now the conversational focus. No approval was reused and no development work executed."
    if status == "unified_development_work_queue_item_action_recorded":
        suffix = " A new approval-gated reopen proposal was prepared." if record.get("action") == "propose-reopen" else ""
        return f"The queue action {record.get('action')} was recorded exactly once.{suffix} No project files or execution authority changed."
    return "The work-queue request was blocked by stale, malformed, conflicting, or tampered evidence. No project or authority changed."


def process_unified_development_work_queue_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    queue_match = _SHOW_QUEUE.fullmatch(text)
    state_filter = "all"; page = 1; size = 20; project_reference = ""
    if queue_match:
        state_filter = str(queue_match.group("filter") or "all")
        page = int(queue_match.group("page") or 1); size = int(queue_match.group("size") or 20)
        result = public_unified_development_work_queue(
            build_unified_development_work_queue(runtime_root=runtime_root),
            state_filter=state_filter, page=page, size=size,
        )
    elif _SHOW_AWAITING.fullmatch(text):
        result = public_unified_development_work_queue(
            build_unified_development_work_queue(runtime_root=runtime_root), state_filter="awaiting_approval"
        )
    else:
        matched_state = next((state for state, pattern in _SHOW_STATE.items() if pattern.fullmatch(text)), "")
        project_match = _SHOW_PROJECT.fullmatch(text)
        focus_match = _FOCUS.fullmatch(text)
        action_match = _ITEM_ACTION.fullmatch(text)
        if matched_state:
            result = public_unified_development_work_queue(
                build_unified_development_work_queue(runtime_root=runtime_root), state_filter=matched_state
            )
        elif project_match:
            project_reference = project_match.group("project_reference").lower()
            result = public_unified_development_work_queue(
                build_unified_development_work_queue(runtime_root=runtime_root), project_reference=project_reference
            )
        elif focus_match:
            result = record_unified_development_work_queue_focus(
                focus_match.group("item_id").lower(),
                expected_queue_digest=focus_match.group("queue_digest").lower(),
                exact_phrase=text, runtime_root=runtime_root,
            )
        elif action_match:
            action = {
                "record defer": "defer",
                "record close": "close",
                "propose reopen": "propose-reopen",
            }[action_match.group("verb").lower()]
            result = record_unified_development_work_queue_item_action(
                action_match.group("item_id").lower(), action=action,
                expected_queue_digest=action_match.group("queue_digest").lower(),
                exact_phrase=text, runtime_root=runtime_root,
            )
        else:
            return {"active": False, "event": "inactive"}
    public = result if "public_unified_development_work_queue_digest" in result else {
        key: value for key, value in result.items()
        if key not in {"exact_phrase", "reopen_proposal"}
    }
    if result.get("reopen_proposal"):
        reopen = dict(result["reopen_proposal"])
        public["reopen_proposal"] = {
            key: reopen.get(key) for key in (
                "status", "queue_item_id", "proposal_id", "proposal_revision",
                "reopen_proposal_digest", "approval_phrase", "fresh_authority_required",
                "prior_authority_reusable", "approval_consumed", "continuation_executed",
            )
        }
    public.update(_base())
    return {
        "active": True,
        "event": str(result.get("status") or "unified_development_work_queue_blocked"),
        "unified_development_work_queue": public,
        "conversation_response": unified_development_work_queue_response(public),
    }
