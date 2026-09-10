from __future__ import annotations

"""v1155.3-v1155.8 persisted continuity for consolidated reasoning state.

Stores only the bounded public reasoning projection after an authoritative turn
commits. Persistence is recoverable and idempotent. The ledger never stores
private chain-of-thought, raw evidence, prompts, provider payloads, decisions,
or executable actions.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1155.8"
SCHEMA_VERSION = "2"
MAX_RECORDS = 500
MAX_PENDING = 100
STALE_AFTER_DAYS = 7
_ALLOWED_QUALITY = {"no_decision", "insufficient_evidence", "bounded_candidate"}
_ALLOWED_OUTCOMES = {"requires_more_evidence", "provisional_leader_only"}
_ALLOWED_BOUNDARIES = {"no_decision", "more_evidence_required", "candidate_recommendation"}
_ALLOWED_TRANSITIONS = {"first_observation", "evidence_improved", "evidence_degraded", "candidate_emerged", "candidate_withdrawn", "stable"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _runtime_root() -> Path:
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()


def _path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else _runtime_root() / "cognition"
    return root / "reasoning_alpha_states.json"


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _is_stale(row: Mapping[str, Any], now: datetime | None = None) -> bool:
    created = _parse_time(row.get("created_at"))
    return created is None or (now or datetime.now(timezone.utc)) - created > timedelta(days=STALE_AFTER_DAYS)


def _bounded_int(value: Any, maximum: int) -> int:
    try:
        return max(0, min(maximum, int(value or 0)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _bounded_projection(state: Mapping[str, Any]) -> dict[str, Any]:
    cases = []
    source_cases = state.get("cases") if isinstance(state.get("cases"), list) else []
    for case in source_cases[:2]:
        if not isinstance(case, Mapping):
            continue
        outcome = str(case.get("outcome") or "requires_more_evidence")[:80]
        if outcome not in _ALLOWED_OUTCOMES:
            outcome = "requires_more_evidence"
        cases.append({
            "case_digest": str(case.get("case_digest") or "")[:128],
            "outcome": outcome,
            "provisional_leader_option_id": str(case.get("provisional_leader_option_id") or "")[:120],
            "completed_step_count": _bounded_int(case.get("completed_step_count"), 4),
            "step_count": _bounded_int(case.get("step_count"), 4),
            "resolution_permitted": False,
        })
    boundaries = []
    source_boundaries = state.get("decision_boundaries") if isinstance(state.get("decision_boundaries"), list) else []
    for row in source_boundaries[:2]:
        if not isinstance(row, Mapping):
            continue
        boundary_state = str(row.get("state") or "no_decision")[:80]
        if boundary_state not in _ALLOWED_BOUNDARIES:
            boundary_state = "no_decision"
        boundaries.append({
            "boundary_id": str(row.get("boundary_id") or "")[:120],
            "state": boundary_state,
            "candidate_option_id": str(row.get("candidate_option_id") or "")[:120],
            "evidence_sufficient": bool(row.get("evidence_sufficient")),
            "prerequisites_complete": bool(row.get("prerequisites_complete")),
            "operator_approval_required": bool(row.get("operator_approval_required", True)),
            "decision_created": False,
            "execution_permitted": False,
        })
    quality = str(state.get("reasoning_quality") or "no_decision")[:80]
    if quality not in _ALLOWED_QUALITY:
        quality = "no_decision"
    transition = str(state.get("reasoning_transition") or "first_observation")[:80]
    if transition not in _ALLOWED_TRANSITIONS:
        transition = "stable"
    return {
        "reasoning_quality": quality,
        "belief_conflict_count": _bounded_int(state.get("belief_conflict_count"), 10000),
        "quarantined_conflict_count": _bounded_int(state.get("quarantined_conflict_count"), 10000),
        "cases": cases,
        "decision_boundaries": boundaries,
        "missing_evidence_explicit": bool(state.get("missing_evidence_explicit")),
        "candidate_recommendation_present": bool(state.get("candidate_recommendation_present")),
        "goal_context_count": _bounded_int(state.get("goal_context_count"), 1000),
        "reasoning_transition": transition,
        "decision_created": False,
        "execution_permitted": False,
        "authority": "none",
    }


def _candidate_digest_from_parts(operation: str, session_digest: str, projection: dict[str, Any]) -> str:
    return _digest({
        "operation_id": str(operation or ""),
        "session_digest": str(session_digest or ""),
        "projection": projection,
    })


def _record_integrity_ok(row: Any) -> bool:
    if not isinstance(row, dict) or not isinstance(row.get("projection"), dict):
        return False
    expected = _digest({k: v for k, v in row.items() if k != "record_digest"})
    if str(row.get("record_digest") or "") != expected:
        return False
    projection = row["projection"]
    if projection != _bounded_projection(projection):
        return False
    if str(row.get("candidate_digest") or "") != _candidate_digest_from_parts(
        str(row.get("operation_id") or ""),
        str(row.get("session_digest") or ""),
        projection,
    ):
        return False
    if _parse_time(row.get("created_at")) is None:
        return False
    return (
        str(row.get("contract_version") or "") == CONTRACT_VERSION
        and str(row.get("type") or "") == "reasoning_alpha_state"
        and bool(str(row.get("operation_id") or "").strip())
        and bool(str(row.get("session_digest") or "").strip())
        and projection.get("authority") == "none"
        and not projection.get("decision_created")
        and not projection.get("execution_permitted")
        and not row.get("private_chain_of_thought_stored")
        and not row.get("raw_evidence_stored")
        and not row.get("prompt_content_stored")
        and not row.get("provider_payload_stored")
        and not row.get("decision_created")
        and not row.get("action_executed")
        and not row.get("authority_broadened")
    )


def _pending_integrity_ok(row: Any) -> bool:
    if not isinstance(row, dict) or not isinstance(row.get("record"), dict):
        return False
    record = row["record"]
    return (
        _record_integrity_ok(record)
        and str(row.get("operation_id") or "") == str(record.get("operation_id") or "")
        and str(row.get("session_digest") or "") == str(record.get("session_digest") or "")
        and str(row.get("candidate_digest") or "") == str(record.get("candidate_digest") or "")
        and _parse_time(row.get("created_at")) is not None
        and row.get("content_free") is True
        and row.get("authority") == "none"
    )


def _empty_store() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "records": [], "pending": []}


def _load_store(path: Path) -> dict[str, Any]:
    data = load_json_file(path, _empty_store(), expected_type=dict)
    if not isinstance(data, dict):
        raise ValueError("reasoning state registry is malformed")
    # v1 compatibility: no pending list.
    if str(data.get("schema_version") or "1") == "1" and "pending" not in data:
        data["pending"] = []
    if not isinstance(data.get("records"), list) or not isinstance(data.get("pending"), list):
        raise ValueError("reasoning state registry is malformed")
    return data


def _candidate_digest(operation: str, session_id: str, projection: dict[str, Any]) -> str:
    return _candidate_digest_from_parts(operation, _digest(str(session_id))[:24], projection)


def _build_record(operation: str, session_id: str, projection: dict[str, Any]) -> dict[str, Any]:
    record = {
        "contract_version": CONTRACT_VERSION,
        "type": "reasoning_alpha_state",
        "operation_id": operation,
        "session_digest": _digest(str(session_id))[:24],
        "created_at": _now(),
        "candidate_digest": _candidate_digest(operation, session_id, projection),
        "projection": projection,
        "private_chain_of_thought_stored": False,
        "raw_evidence_stored": False,
        "prompt_content_stored": False,
        "provider_payload_stored": False,
        "decision_created": False,
        "action_executed": False,
        "authority_broadened": False,
    }
    record["record_digest"] = _digest({k: v for k, v in record.items() if k != "record_digest"})
    return record


def record_reasoning_state(*, operation_id: str, session_id: str, state: Mapping[str, Any], runtime_root: str | Path | None = None) -> dict[str, Any]:
    """Stage and finalize one content-free reasoning continuity record.

    A pending journal is written before finalization. Clean retries complete once;
    tampered completed or pending rows fail closed.
    """
    operation = str(operation_id or "").strip()[:180]
    if not operation:
        raise ValueError("operation_id is required")
    projection = _bounded_projection(state)
    candidate = _build_record(operation, session_id, projection)
    candidate_digest = str(candidate["candidate_digest"])
    path = _path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_mutation_lock(path):
        data = _load_store(path)
        existing = next((r for r in data["records"] if isinstance(r, dict) and r.get("operation_id") == operation), None)
        if existing:
            if not _record_integrity_ok(existing):
                raise ValueError("existing reasoning state integrity mismatch")
            # Completed operations retain historical operation-level idempotency.
            # Exact candidate matching is enforced while recovering pending state.
            return deepcopy(existing)

        pending = next((r for r in data["pending"] if isinstance(r, dict) and r.get("operation_id") == operation), None)
        if pending:
            pending_record = pending.get("record")
            if not _pending_integrity_ok(pending):
                raise ValueError("pending reasoning state integrity mismatch")
            if str(pending.get("candidate_digest") or "") != candidate_digest or str(pending_record.get("candidate_digest") or "") != candidate_digest:
                raise ValueError("pending reasoning state candidate mismatch")
            record = deepcopy(pending_record)
        else:
            pending = {
                "operation_id": operation,
                "session_digest": candidate["session_digest"],
                "candidate_digest": candidate_digest,
                "created_at": _now(),
                "record": deepcopy(candidate),
                "content_free": True,
                "authority": "none",
            }
            data["pending"].append(pending)
            data["pending"] = data["pending"][-MAX_PENDING:]
            data["schema_version"] = SCHEMA_VERSION
            data["updated_at"] = _now()
            write_json_atomic(path, data)
            record = candidate

        data = _load_store(path)
        current_pending = next((r for r in data["pending"] if isinstance(r, dict) and r.get("operation_id") == operation), None)
        if not current_pending or not _pending_integrity_ok(current_pending):
            raise ValueError("pending reasoning state unavailable or malformed")
        if str(current_pending.get("candidate_digest") or "") != candidate_digest:
            raise ValueError("pending reasoning state candidate mismatch")
        data["records"].append(deepcopy(record))
        data["records"] = data["records"][-MAX_RECORDS:]
        data["pending"] = [r for r in data["pending"] if not (isinstance(r, dict) and r.get("operation_id") == operation)]
        data["schema_version"] = SCHEMA_VERSION
        data["updated_at"] = _now()
        write_json_atomic(path, data)
    return deepcopy(record)


def load_prior_reasoning_state(*, session_id: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    path = _path(runtime_root)
    empty = {"contract_version": CONTRACT_VERSION, "prior_state_present": False, "prior_state_stale": False, "malformed_store": False, "pending_recovery_count": 0}
    if not path.exists():
        return empty
    try:
        data = _load_store(path)
    except (ValueError, TypeError, json.JSONDecodeError):
        return {**empty, "malformed_store": True}
    malformed_pending = any(not _pending_integrity_ok(row) for row in data["pending"])
    session_digest = _digest(str(session_id))[:24]
    rows = [r for r in data["records"] if isinstance(r, dict) and r.get("session_digest") == session_digest]
    malformed_rows = any(not isinstance(r, dict) for r in data["records"])
    if not rows:
        return {**empty, "malformed_store": malformed_rows or malformed_pending, "pending_recovery_count": len(data["pending"])}
    row = rows[-1]
    if not _record_integrity_ok(row):
        return {**empty, "malformed_store": True, "pending_recovery_count": len(data["pending"])}
    stale = _is_stale(row)
    return {
        "contract_version": CONTRACT_VERSION,
        "prior_state_present": not stale,
        "prior_state_stale": stale,
        "malformed_store": malformed_rows or malformed_pending,
        "pending_recovery_count": len(data["pending"]),
        "projection": deepcopy(row["projection"]) if not stale else {},
        "record_digest": str(row.get("record_digest") or "") if not stale else "",
        "authority": "none",
    }


def inspect_reasoning_state_continuity(runtime_root: str | Path | None = None) -> dict[str, Any]:
    path = _path(runtime_root)
    base = {"contract_version": CONTRACT_VERSION, "record_count": 0, "pending_count": 0, "stale_count": 0, "malformed": False, "content_free": True, "authority_preserved": True}
    if not path.exists():
        return base
    try:
        data = _load_store(path)
    except (ValueError, TypeError, json.JSONDecodeError):
        return {**base, "malformed": True}
    valid = [r for r in data["records"] if _record_integrity_ok(r)]
    valid_pending = [r for r in data["pending"] if _pending_integrity_ok(r)]
    malformed = len(valid) != len(data["records"]) or len(valid_pending) != len(data["pending"])
    return {
        "contract_version": CONTRACT_VERSION,
        "record_count": len(valid),
        "pending_count": len(valid_pending),
        "stale_count": sum(1 for r in valid if _is_stale(r)),
        "malformed": malformed,
        "content_free": True,
        "authority_preserved": True,
        "registry_digest": _digest([str(r.get("record_digest") or "") for r in valid]),
        "pending_digest": _digest([str(r.get("candidate_digest") or "") for r in valid_pending]),
        "private_records_exposed": False,
        "session_identifiers_exposed": False,
        "operation_identifiers_exposed": False,
    }
