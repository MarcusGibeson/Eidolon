from __future__ import annotations

"""Content-free unified history for one supervised development transaction.

The history is a derived, read-only index over existing authoritative receipts.
It never replaces those receipts and never grants execution authority. Runtime
records are read only from a bounded whitelist of lifecycle directories. Public
records contain statuses, decisions, counts, timestamps, and digests, never
requests, project paths, file names, generated contents, provider output, test
output, rollback contents, or private runtime locations.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1221.8"
MAX_PAGE_SIZE = 50

AUTHORITY_FLAGS = {
    "provider_contact_authorized": False,
    "test_execution_authorized": False,
    "continuation_execution_authorized": False,
    "diagnosis_authorized": False,
    "repair_execution_authorized": False,
    "apply_execution_authorized": False,
    "apply_authorized": False,
    "rollback_execution_authorized": False,
    "rollback_authorized": False,
    "install_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "authority_granted": False,
}


@dataclass(frozen=True)
class StageSpec:
    stage: str
    directory: str
    mode: str = "revision_tree"


STAGE_SPECS: tuple[StageSpec, ...] = (
    StageSpec("campaign-event", "events", "event_tree"),
    StageSpec("approval", "approvals", "revision_file"),
    StageSpec("grounded-planning", "planning", "revision_file"),
    StageSpec("build-test", "conversational_build_test_loops", "revision_file"),
    StageSpec("build-test-review", "operator_build_test_results", "revision_file"),
    StageSpec("continuation-decision", "operator_build_test_continuations", "revision_file"),
    StageSpec("continuation-execution", "conversational_build_test_continuations", "revision_file"),
    StageSpec("automatic-diagnosis", "bounded_automatic_diagnoses"),
    StageSpec("diagnosis-review", "operator_diagnosis_reviews"),
    StageSpec("diagnosis-decision", "operator_diagnosis_decisions"),
    StageSpec("repair-proposal", "bounded_repair_proposals"),
    StageSpec("repair-execution", "conversational_supervised_repair_executions"),
    StageSpec("repair-result-review", "operator_repair_result_reviews"),
    StageSpec("repair-result-decision", "operator_repair_result_decisions"),
    StageSpec("apply-proposal", "bounded_repaired_candidate_apply_proposals"),
    StageSpec("apply-authorization", "conversational_supervised_repaired_candidate_apply_authorizations"),
    StageSpec("apply-execution", "conversational_supervised_repaired_candidate_applies"),
    StageSpec("apply-result-review", "operator_repaired_candidate_apply_result_reviews"),
    StageSpec("apply-result-decision", "operator_repaired_candidate_apply_result_decisions"),
    StageSpec("rollback-proposal", "bounded_repaired_candidate_rollback_proposals"),
    StageSpec("rollback-authorization", "conversational_supervised_repaired_candidate_rollback_authorizations"),
    StageSpec("rollback-execution", "conversational_supervised_repaired_candidate_rollbacks"),
    StageSpec("rollback-result-review", "operator_repaired_candidate_rollback_result_reviews"),
    StageSpec("rollback-result-decision", "operator_repaired_candidate_rollback_result_decisions"),
)
STAGE_ORDER = {spec.stage: index for index, spec in enumerate(STAGE_SPECS)}

_HISTORY_CONTROL = re.compile(
    r"^show\s+(?:unified\s+)?supervised\s+development\s+transaction\s+"
    r"(?P<mode>history|status)\s+proposal\s+(?P<proposal_id>devc_[a-f0-9]{24})\s+"
    r"revision\s+(?P<revision>[1-9][0-9]*)"
    r"(?:\s+page\s+(?P<page>[1-9][0-9]*)\s+size\s+(?P<size>[1-9][0-9]*))?[.!?]*$",
    re.I,
)

_SAFE_VALUE_FIELDS = (
    "status", "phase", "lifecycle_state", "planning_status", "event_type",
    "decision", "decision_state", "outcome_class", "completed_stage",
    "continuation_state", "diagnosis_code", "result_state",
)
_SAFE_TIME_FIELDS = (
    "created_at", "updated_at", "completed_at", "consumed_at", "recorded_at",
)
_SAFE_COUNT_FIELDS = (
    "attempt_number", "attempt_count", "failed_attempt_number",
    "repair_attempt_number", "apply_attempt_number", "rollback_attempt_number",
    "approval_consumption_count", "authorization_consumption_count",
    "consumption_count", "file_count", "command_count", "restored_count",
    "operation_count", "passed_command_count", "failed_command_count",
)
_PREFERRED_DIGEST_FIELDS = (
    "operator_repaired_candidate_rollback_result_decision_digest",
    "operator_repaired_candidate_rollback_result_review_record_digest",
    "supervised_repaired_candidate_rollback_result_digest",
    "supervised_repaired_candidate_rollback_digest",
    "bounded_repaired_candidate_rollback_proposal_record_digest",
    "operator_repaired_candidate_apply_result_decision_digest",
    "operator_repaired_candidate_apply_result_review_record_digest",
    "supervised_repaired_candidate_apply_result_digest",
    "supervised_repaired_candidate_apply_digest",
    "operator_repair_result_decision_digest",
    "operator_repair_result_review_record_digest",
    "supervised_repair_result_digest",
    "supervised_repair_execution_digest",
    "operator_diagnosis_decision_digest",
    "operator_diagnosis_review_record_digest",
    "diagnosis_result_digest", "diagnosis_digest", "continuation_result_digest",
    "continuation_digest", "loop_result_digest", "loop_digest",
    "approval_receipt_digest", "planning_digest", "event_digest",
)


def _history_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "unified_supervised_development_transaction_histories"
        / proposal_id
        / f"revision-{int(revision)}.json"
    )


def _snapshot_path(
    proposal_id: str, revision: int, generation: int, runtime_root=None
) -> Path:
    return (
        _store_root(runtime_root)
        / "unified_supervised_development_transaction_history_snapshots"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"generation-{int(generation):06d}.json"
    )


def _sha256(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if len(token) == 64 and all(ch in "0123456789abcdef" for ch in token) else ""


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(
        supplied
        and supplied == _digest({key: value for key, value in record.items() if key != field})
    )


def _base(proposal_id: str = "", revision: int = 0) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "history_is_derivative": True,
        "authoritative_receipts_preserved": True,
        "read_only_inspection": True,
        "runtime_records_external": True,
        "provider_contacted": False,
        "tests_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        "rollback_content_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, *, reason: str = "", proposal_id: str = "", revision: int = 0) -> dict[str, Any]:
    row = {
        "ok": False,
        "status": status,
        "reason": reason,
        **_base(proposal_id, revision),
    }
    row["unified_supervised_development_transaction_history_result_digest"] = _digest(row)
    return row


def _candidate_paths(base: Path, spec: StageSpec, proposal_id: str, revision: int) -> Iterable[Path]:
    root = base / spec.directory / proposal_id
    if spec.mode == "revision_file":
        path = root / f"revision-{int(revision)}.json"
        return (path,) if path.is_file() else ()
    if spec.mode == "event_tree":
        return tuple(sorted(root.glob("*.json"))) if root.is_dir() else ()
    revision_root = root / f"revision-{int(revision)}"
    return tuple(sorted(revision_root.rglob("*.json"))) if revision_root.is_dir() else ()


def _record_digest(record: Mapping[str, Any]) -> tuple[str, str]:
    for field in _PREFERRED_DIGEST_FIELDS:
        value = _sha256(record.get(field))
        if value:
            return field, value
    for field in sorted(record):
        if field.endswith("_digest"):
            value = _sha256(record.get(field))
            if value:
                return field, value
    return "canonical_record_digest", _digest(record)


def _safe_status(record: Mapping[str, Any]) -> tuple[str, str]:
    for field in _SAFE_VALUE_FIELDS:
        value = record.get(field)
        if isinstance(value, (str, int, float, bool)) and str(value).strip():
            return field, str(value)
    return "", "recorded"


def _safe_time(record: Mapping[str, Any]) -> str:
    for field in _SAFE_TIME_FIELDS:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _safe_counts(record: Mapping[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for field in _SAFE_COUNT_FIELDS:
        value = record.get(field)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value >= 0:
            counts[field] = value
    return counts


def _validate_binding(record: Mapping[str, Any], proposal_id: str, revision: int) -> bool:
    bound_id = str(record.get("proposal_id") or "").strip().lower()
    bound_revision = int(record.get("proposal_revision") or record.get("revision") or 0)
    if bound_id and bound_id != proposal_id:
        return False
    if bound_revision and bound_revision != int(revision):
        return False
    return True


def _source_event(spec: StageSpec, record: Mapping[str, Any], source_index: int) -> dict[str, Any]:
    status_field, status = _safe_status(record)
    digest_field, artifact_digest = _record_digest(record)
    event = {
        "stage": spec.stage,
        "stage_rank": STAGE_ORDER[spec.stage],
        "source_index": int(source_index),
        "status_field": status_field,
        "status": status,
        "recorded_at": _safe_time(record),
        "artifact_digest_field": digest_field,
        "artifact_digest": artifact_digest,
        "canonical_record_digest": _digest(record),
        "counts": _safe_counts(record),
        "authority_consumed": bool(
            record.get("approval_consumed_once") is True
            or int(record.get("approval_consumption_count") or 0) > 0
            or int(record.get("authorization_consumption_count") or 0) > 0
            or int(record.get("consumption_count") or 0) > 0
        ),
        "operator_decision": str(record.get("decision") or ""),
        "decision_state": str(record.get("decision_state") or ""),
    }
    event["event_identity_digest"] = _digest(event)
    return event


def _collect_events(proposal_id: str, revision: int, runtime_root=None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    base = _store_root(runtime_root)
    events: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for spec in STAGE_SPECS:
        for index, path in enumerate(_candidate_paths(base, spec, proposal_id, revision), start=1):
            record = _read_json(path)
            if not record:
                return [], _failure(
                    "unified_supervised_development_transaction_history_source_invalid",
                    reason=f"invalid_json_or_empty_receipt:{spec.stage}",
                    proposal_id=proposal_id,
                    revision=revision,
                )
            if not _validate_binding(record, proposal_id, revision):
                return [], _failure(
                    "unified_supervised_development_transaction_history_source_binding_invalid",
                    reason=f"receipt_binding_mismatch:{spec.stage}",
                    proposal_id=proposal_id,
                    revision=revision,
                )
            event = _source_event(spec, record, index)
            source_key = f"{spec.stage}:{event['canonical_record_digest']}"
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            events.append(event)
    events.sort(key=lambda row: (
        int(row["stage_rank"]), str(row.get("recorded_at") or ""),
        int(row.get("source_index") or 0), str(row["canonical_record_digest"]),
    ))
    for sequence, event in enumerate(events, start=1):
        event["sequence"] = sequence
        event["transaction_event_digest"] = _digest({
            key: value for key, value in event.items() if key != "transaction_event_digest"
        })
    return events, None


def _coverage(events: list[Mapping[str, Any]]) -> dict[str, Any]:
    stages = []
    for event in events:
        stage = str(event.get("stage") or "")
        if stage and stage not in stages:
            stages.append(stage)
    ranks = sorted({STAGE_ORDER[stage] for stage in stages if stage in STAGE_ORDER})
    gaps: list[str] = []
    if ranks:
        observed = set(ranks)
        for rank in range(min(ranks), max(ranks) + 1):
            if rank not in observed:
                gaps.append(STAGE_SPECS[rank].stage)
    return {
        "observed_stages": stages,
        "observed_stage_count": len(stages),
        "first_observed_stage": stages[0] if stages else "",
        "last_observed_stage": stages[-1] if stages else "",
        "missing_intermediate_stages": gaps,
        "gap_count": len(gaps),
    }


def _current_state(events: list[Mapping[str, Any]]) -> tuple[str, bool]:
    if not events:
        return "no_transaction_receipts_found", False
    last = events[-1]
    decision_state = str(last.get("decision_state") or "")
    decision = str(last.get("operator_decision") or "")
    status = str(last.get("status") or "recorded")
    state = decision_state or decision or status
    terminal = str(last.get("stage") or "") == "rollback-result-decision" and decision in {
        "accept-rollback-result", "reject-rollback-result"
    }
    return state, terminal


def _validate_history_record(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "unified_supervised_development_transaction_history_record_digest"):
        return False
    events = record.get("events")
    if not isinstance(events, list):
        return False
    for expected, event in enumerate(events, start=1):
        if not isinstance(event, Mapping) or int(event.get("sequence") or 0) != expected:
            return False
        supplied = str(event.get("transaction_event_digest") or "")
        calculated = _digest({
            key: value for key, value in event.items() if key != "transaction_event_digest"
        })
        if supplied != calculated:
            return False
    source_set = [
        {"stage": event["stage"], "canonical_record_digest": event["canonical_record_digest"]}
        for event in events
    ]
    if str(record.get("source_set_digest") or "") != _digest(source_set):
        return False
    binding = {
        "contract_version": str(record.get("contract_version") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
        "proposal_revision": int(record.get("proposal_revision") or 0),
        "generation": int(record.get("generation") or 0),
        "previous_history_digest": str(record.get("previous_history_digest") or ""),
        "source_set_digest": str(record.get("source_set_digest") or ""),
        "event_count": len(events),
        "current_state": str(record.get("current_state") or ""),
        "terminal": bool(record.get("terminal")),
    }
    return str(record.get("history_digest") or "") == _digest(binding)


def build_unified_supervised_development_transaction_history(
    proposal_id: str,
    *,
    expected_revision: int,
    runtime_root=None,
) -> dict[str, Any]:
    """Build or refresh one durable derived history without changing project state."""

    proposal_id = str(proposal_id or "").strip().lower()
    revision = int(expected_revision or 0)
    if not re.fullmatch(r"devc_[a-f0-9]{24}", proposal_id) or revision < 1:
        return _failure(
            "unified_supervised_development_transaction_history_invalid_request",
            reason="valid_proposal_and_revision_required",
            proposal_id=proposal_id,
            revision=revision,
        )
    events, failure = _collect_events(proposal_id, revision, runtime_root)
    if failure:
        return failure
    if not events:
        return _failure(
            "unified_supervised_development_transaction_history_not_found",
            reason="no_authoritative_receipts_found",
            proposal_id=proposal_id,
            revision=revision,
        )
    source_set = [
        {"stage": event["stage"], "canonical_record_digest": event["canonical_record_digest"]}
        for event in events
    ]
    source_set_digest = _digest(source_set)
    coverage = _coverage(events)
    current_state, terminal = _current_state(events)
    path = _history_path(proposal_id, revision, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _validate_history_record(existing):
                return _failure(
                    "unified_supervised_development_transaction_history_record_invalid",
                    reason="persisted_history_tampered_or_malformed",
                    proposal_id=proposal_id,
                    revision=revision,
                )
            if str(existing.get("source_set_digest") or "") == source_set_digest:
                return {**existing, "operation_status": "resumed"}
            generation = int(existing.get("generation") or 0) + 1
            previous_history_digest = str(existing.get("history_digest") or "")
        else:
            generation = 1
            previous_history_digest = ""
        binding = {
            "contract_version": CONTRACT_VERSION,
            "proposal_id": proposal_id,
            "proposal_revision": revision,
            "generation": generation,
            "previous_history_digest": previous_history_digest,
            "source_set_digest": source_set_digest,
            "event_count": len(events),
            "current_state": current_state,
            "terminal": terminal,
        }
        row = {
            "ok": True,
            "status": "unified_supervised_development_transaction_history_ready",
            **binding,
            "history_digest": _digest(binding),
            "events": events,
            "coverage": coverage,
            "stage_count": coverage["observed_stage_count"],
            "gap_count": coverage["gap_count"],
            **_base(proposal_id, revision),
        }
        row = _sealed(row, "unified_supervised_development_transaction_history_record_digest")
        _atomic_json(_snapshot_path(proposal_id, revision, generation, runtime_root), row)
        _atomic_json(path, row)
    return {**row, "operation_status": "created" if generation == 1 else "refreshed"}


def load_unified_supervised_development_transaction_history(
    proposal_id: str, revision: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_history_path(proposal_id, revision, runtime_root)) or {}
    return record if record and _validate_history_record(record) else {}


def public_unified_supervised_development_transaction_history(
    record: Mapping[str, Any], *, page: int = 1, page_size: int = 20, include_events: bool = True
) -> dict[str, Any]:
    if not record:
        return {}
    page = max(1, int(page or 1))
    page_size = max(1, min(MAX_PAGE_SIZE, int(page_size or 20)))
    events = list(record.get("events") or []) if include_events else []
    start = (page - 1) * page_size
    selected = events[start:start + page_size]
    allowed = {
        "ok", "status", "reason", "schema_version", "contract_version", "proposal_id",
        "proposal_revision", "generation", "previous_history_digest", "source_set_digest",
        "history_digest", "event_count", "stage_count", "gap_count", "coverage",
        "current_state", "terminal", "history_is_derivative", "authoritative_receipts_preserved",
        "read_only_inspection", "runtime_records_external", "provider_contacted",
        "tests_executed", "repair_executed", "apply_executed", "rollback_executed",
        "project_modified", "selected_project_modified", "source_modified",
        "operation_status", *AUTHORITY_FLAGS.keys(),
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "page": page,
        "page_size": page_size,
        "page_event_count": len(selected),
        "has_previous_page": page > 1,
        "has_next_page": start + page_size < int(record.get("event_count") or 0),
        "events": selected,
        "events_included": include_events,
        "content_free": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        "rollback_content_exposed": False,
    })
    public["public_unified_supervised_development_transaction_history_digest"] = _digest(public)
    return public


def transaction_history_response(record: Mapping[str, Any]) -> str:
    if record.get("ok") is not True:
        return (
            "The supervised development transaction history could not be built from valid "
            "authoritative receipts. No execution authority or project change was created."
        )
    coverage = record.get("coverage") or {}
    gap_note = (
        f" {record.get('gap_count')} intermediate lifecycle stage(s) are not represented."
        if int(record.get("gap_count") or 0) else ""
    )
    return (
        f"Transaction {record.get('proposal_id')} revision {record.get('proposal_revision')} "
        f"has {record.get('event_count')} content-free events across {record.get('stage_count')} "
        f"stages. Current state: {record.get('current_state')}. "
        f"History generation: {record.get('generation')}; page {record.get('page')} contains "
        f"{record.get('page_event_count')} events.{gap_note} The underlying receipts remain authoritative, "
        "and this history grants no execution permission."
    )


def process_unified_supervised_development_transaction_history_control(
    user_text: str, *, runtime_root=None
) -> dict[str, Any]:
    match = _HISTORY_CONTROL.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    page = int(match.group("page") or 1)
    size = int(match.group("size") or 20)
    if size > MAX_PAGE_SIZE:
        result = _failure(
            "unified_supervised_development_transaction_history_page_invalid",
            reason=f"page_size_must_not_exceed_{MAX_PAGE_SIZE}",
            proposal_id=match.group("proposal_id").lower(),
            revision=int(match.group("revision")),
        )
    else:
        result = build_unified_supervised_development_transaction_history(
            match.group("proposal_id").lower(),
            expected_revision=int(match.group("revision")),
            runtime_root=runtime_root,
        )
    public = public_unified_supervised_development_transaction_history(
        result,
        page=page,
        page_size=size,
        include_events=match.group("mode").lower() == "history",
    )
    return {
        "active": True,
        "event": str(result.get("status") or "unified_supervised_development_transaction_history_blocked"),
        "unified_supervised_development_transaction_history": public,
        "conversation_response": transaction_history_response(public),
        "public_digest": _digest(public),
    }


def attach_unified_supervised_development_transaction_history(
    turn: Mapping[str, Any], *, runtime_root=None
) -> dict[str, Any]:
    """Attach a one-page current summary after a terminal rollback-result decision."""

    output = dict(turn)
    decision = output.get("operator_repaired_candidate_rollback_result_review")
    if not isinstance(decision, Mapping) or str(decision.get("status") or "") != (
        "operator_repaired_candidate_rollback_result_decision_recorded"
    ):
        return output
    result = build_unified_supervised_development_transaction_history(
        str(decision.get("proposal_id") or ""),
        expected_revision=int(decision.get("proposal_revision") or 0),
        runtime_root=runtime_root,
    )
    public = public_unified_supervised_development_transaction_history(
        result, page=1, page_size=10, include_events=False
    )
    output["unified_supervised_development_transaction_history"] = public
    if result.get("ok") is True:
        output["conversation_response"] = " ".join(
            part for part in (
                str(output.get("conversation_response") or "").strip(),
                transaction_history_response(public),
            ) if part
        )
    output["public_digest"] = _digest({
        key: value for key, value in output.items()
        if key not in {"conversation_response", "public_digest"}
    })
    return output
