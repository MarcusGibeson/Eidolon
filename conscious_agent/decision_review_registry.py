from __future__ import annotations

"""Reliable governed recommendation registry and read-only approval previews.

The registry persists bounded candidate recommendations after an authoritative
conversation commit. It never creates or grants approval, decisions, intentions,
plans, or executable actions. Approval previews are exact-digest review objects
only and carry no mutation or authorization capability.
"""

from datetime import datetime, timezone, timedelta
import hashlib, json, os
from pathlib import Path
from typing import Any, Mapping

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1154.9"
SCHEMA_VERSION = "2"
MAX_RECORDS = 500
MAX_TEXT = 260
STALE_AFTER_DAYS = 14
_CANDIDATE_IMMUTABLE_KEYS = (
    "boundary_id", "candidate_option_id", "candidate_proposition", "risk_level",
    "reversibility", "estimated_cost", "resource_demand", "rollback_plan_quality",
    "evidence_sufficient", "prerequisites_complete",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    return (Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data") / "cognition").resolve()


def _path(runtime_root: str | Path | None = None) -> Path:
    return _root(runtime_root) / "decision_review_registry.json"


def _clean(value: Any, limit: int = MAX_TEXT) -> str:
    return " ".join(str(value or "").split())[:limit]


def _estimate_cost_and_resources(proposition: str, risk: str) -> tuple[str, str]:
    text = proposition.lower()
    if any(term in text for term in ("deploy", "install", "replace", "purchase", "delete", "publish")) or risk == "high":
        return "material", "material"
    if any(term in text for term in ("test", "sandbox", "simulate", "inspect", "preview", "review")):
        return "low", "low"
    return "unknown", "unknown"


def _rollback_quality(proposition: str, reversibility: str) -> str:
    text = proposition.lower()
    if reversibility == "high" and any(term in text for term in ("sandbox", "preview", "draft", "read-only", "simulate")):
        return "sufficient_for_review"
    if any(term in text for term in ("rollback", "restore", "revert")):
        return "stated"
    return "missing"


def _parse_time(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _is_stale(record: Mapping[str, Any], now: datetime | None = None) -> bool:
    created = _parse_time(record.get("created_at"))
    if created is None:
        return True
    current = now or datetime.now(timezone.utc)
    return current - created > timedelta(days=STALE_AFTER_DAYS)


def _candidate_digest_for_item(item: Mapping[str, Any]) -> str:
    return _digest({key: item.get(key) for key in _CANDIDATE_IMMUTABLE_KEYS})


def _candidate_integrity_valid(item: Mapping[str, Any]) -> bool:
    stored = str(item.get("candidate_digest") or "")
    return bool(stored) and stored == _candidate_digest_for_item(item)


def _record_integrity_valid(record: Mapping[str, Any]) -> bool:
    stored = str(record.get("record_digest") or "")
    return bool(stored) and stored == _digest({key: value for key, value in record.items() if key != "record_digest"})


def _review_record_integrity_valid(record: Mapping[str, Any]) -> bool:
    items = record.get("review_items")
    if not isinstance(items, list) or len(items) > 2 or not all(isinstance(item, Mapping) for item in items):
        return False
    try:
        declared = int(record.get("review_item_count", -1))
    except (TypeError, ValueError):
        return False
    return (
        declared == len(items)
        and _record_integrity_valid(record)
        and all(_candidate_integrity_valid(item) for item in items)
        and not any(bool(record.get(key)) for key in (
            "approval_request_created", "decision_created", "action_executed", "authority_broadened"
        ))
    )


def _candidate_payload(operation_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    proposition = _clean(row.get("candidate_proposition"))
    risk = _clean(row.get("risk_level"), 32) or "unknown"
    reversibility = _clean(row.get("reversibility"), 32) or "unknown"
    cost, resources = _estimate_cost_and_resources(proposition, risk)
    rollback = _rollback_quality(proposition, reversibility)
    ready = bool(row.get("evidence_sufficient") and row.get("prerequisites_complete") and rollback != "missing" and cost != "unknown" and resources != "unknown")
    immutable = {
        "boundary_id": _clean(row.get("boundary_id"), 120),
        "candidate_option_id": _clean(row.get("candidate_option_id"), 120),
        "candidate_proposition": proposition,
        "risk_level": risk,
        "reversibility": reversibility,
        "estimated_cost": cost,
        "resource_demand": resources,
        "rollback_plan_quality": rollback,
        "evidence_sufficient": bool(row.get("evidence_sufficient")),
        "prerequisites_complete": bool(row.get("prerequisites_complete")),
    }
    candidate_digest = _candidate_digest_for_item(immutable)
    return {
        "review_item_id": "decision-review-" + _digest({"op": operation_id, "candidate": candidate_digest})[:24],
        **immutable,
        "candidate_digest": candidate_digest,
        "review_readiness": "ready_for_operator_review" if ready else "blocked_for_more_detail",
        "approval_request_created": False,
        "approval_granted": False,
        "decision_created": False,
        "execution_permitted": False,
        "action_authority": False,
    }


def _default_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "records": [], "pending": []}


def _valid_state(state: Any) -> bool:
    return isinstance(state, dict) and isinstance(state.get("records", []), list) and isinstance(state.get("pending", []), list)


def record_decision_review_candidates(*, operation_id: str, session_id: str, boundary: Mapping[str, Any], runtime_root: str | Path | None = None) -> dict[str, Any]:
    operation_id = _clean(operation_id, 180)
    if not operation_id:
        raise ValueError("operation_id is required")
    candidates = [row for row in (boundary.get("cases") or []) if isinstance(row, Mapping) and row.get("state") == "candidate_recommendation"]
    review_items = [_candidate_payload(operation_id, row) for row in candidates[:2]]
    record = {
        "contract_version": CONTRACT_VERSION,
        "type": "decision_review_record",
        "operation_id": operation_id,
        "session_digest": _digest(str(session_id))[:24],
        "created_at": _now(),
        "review_item_count": len(review_items),
        "review_items": review_items,
        "operator_review_required": bool(review_items),
        "approval_request_created": False,
        "decision_created": False,
        "action_executed": False,
        "authority_broadened": False,
    }
    record["record_digest"] = _digest({k: v for k, v in record.items() if k != "record_digest"})
    path = _path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_mutation_lock(path):
        state = load_json_file(path, _default_state(), expected_type=dict)
        if not _valid_state(state):
            raise ValueError("decision review registry is malformed")
        records = state.setdefault("records", [])
        existing = next((row for row in records if isinstance(row, dict) and row.get("operation_id") == operation_id), None)
        if existing:
            if not _review_record_integrity_valid(existing):
                raise ValueError("existing decision review integrity mismatch")
            return dict(existing)
        pending = state.setdefault("pending", [])
        staged = next((row for row in pending if isinstance(row, dict) and row.get("operation_id") == operation_id), None)
        if staged is None:
            pending.append({"operation_id": operation_id, "record": record, "staged_at": _now(), "content_free": False})
            state["updated_at"] = _now()
            write_json_atomic(path, state)
        else:
            staged_record = staged.get("record")
            staged_items = staged_record.get("review_items", []) if isinstance(staged_record, dict) else []
            current_digests = [item.get("candidate_digest") for item in review_items]
            staged_digests = [item.get("candidate_digest") for item in staged_items if isinstance(item, dict)]
            if not isinstance(staged_record, dict) or staged_digests != current_digests:
                raise ValueError("pending decision review digest mismatch")
            if not _review_record_integrity_valid(staged_record):
                raise ValueError("pending decision review integrity mismatch")
            record = dict(staged_record)
        state = load_json_file(path, _default_state(), expected_type=dict)
        records = state.setdefault("records", [])
        if not any(isinstance(row, dict) and row.get("operation_id") == operation_id for row in records):
            records.append(record)
        state["records"] = records[-MAX_RECORDS:]
        state["pending"] = [row for row in state.get("pending", []) if not (isinstance(row, dict) and row.get("operation_id") == operation_id)]
        state["schema_version"] = SCHEMA_VERSION
        state["updated_at"] = _now()
        write_json_atomic(path, state)
        return dict(record)


def build_operator_approval_preview(*, operation_id: str, review_item_id: str, expected_candidate_digest: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    """Return a read-only exact-candidate review preview; never create approval."""
    path = _path(runtime_root)
    if not path.exists():
        return {"contract_version": CONTRACT_VERSION, "status": "not_found", "approval_created": False, "authority_broadened": False}
    state = load_json_file(path, _default_state(), expected_type=dict)
    if not _valid_state(state):
        return {"contract_version": CONTRACT_VERSION, "status": "malformed_registry", "approval_created": False, "authority_broadened": False}
    record = next((row for row in state["records"] if isinstance(row, dict) and row.get("operation_id") == _clean(operation_id, 180)), None)
    if not record:
        return {"contract_version": CONTRACT_VERSION, "status": "not_found", "approval_created": False, "authority_broadened": False}
    record_items = record.get("review_items")
    try:
        declared_count = int(record.get("review_item_count", -1))
    except (TypeError, ValueError):
        declared_count = -1
    record_structure_valid = (
        isinstance(record_items, list)
        and len(record_items) <= 2
        and all(isinstance(row, Mapping) for row in record_items)
        and declared_count == len(record_items)
        and not any(bool(record.get(key)) for key in (
            "approval_request_created", "decision_created", "action_executed", "authority_broadened"
        ))
    )
    if not _record_integrity_valid(record) or not record_structure_valid:
        return {"contract_version": CONTRACT_VERSION, "status": "record_integrity_mismatch", "approval_created": False, "authority_broadened": False}
    if _is_stale(record):
        return {"contract_version": CONTRACT_VERSION, "status": "stale_candidate", "approval_created": False, "authority_broadened": False}
    item = next((row for row in record.get("review_items", []) if isinstance(row, dict) and row.get("review_item_id") == _clean(review_item_id, 180)), None)
    if not item:
        return {"contract_version": CONTRACT_VERSION, "status": "not_found", "approval_created": False, "authority_broadened": False}
    actual = str(item.get("candidate_digest") or "")
    if not _candidate_integrity_valid(item):
        return {"contract_version": CONTRACT_VERSION, "status": "candidate_integrity_mismatch", "approval_created": False, "authority_broadened": False}
    if actual != str(expected_candidate_digest or ""):
        return {"contract_version": CONTRACT_VERSION, "status": "candidate_digest_mismatch", "approval_created": False, "authority_broadened": False}
    if item.get("review_readiness") != "ready_for_operator_review":
        return {"contract_version": CONTRACT_VERSION, "status": "blocked_for_more_detail", "candidate_digest": actual, "approval_created": False, "authority_broadened": False}
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "ready_for_operator_review",
        "review_item_id": item.get("review_item_id"),
        "candidate_digest": actual,
        "preview_digest": _digest({"record": record.get("record_digest"), "candidate": actual, "mode": "approval_preview"}),
        "exact_candidate_bound": True,
        "read_only": True,
        "approval_request_created": False,
        "approval_created": False,
        "approval_granted": False,
        "decision_created": False,
        "execution_permitted": False,
        "action_authority": False,
        "authority_broadened": False,
    }


def inspect_decision_review_registry(runtime_root: str | Path | None = None) -> dict[str, Any]:
    path = _path(runtime_root)
    base = {
        "contract_version": CONTRACT_VERSION,
        "record_count": 0,
        "review_item_count": 0,
        "ready_count": 0,
        "blocked_count": 0,
        "stale_count": 0,
        "pending_count": 0,
        "approval_request_count": 0,
        "record_integrity_mismatch_count": 0,
        "candidate_integrity_mismatch_count": 0,
        "malformed": False,
        "review_required": False,
        "content_exposed": False,
        "authority_preserved": True,
        "registry_digest": _digest([])[:32],
    }
    if not path.exists():
        return base
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {**base, "malformed": True, "review_required": True}
    if not _valid_state(raw):
        return {**base, "malformed": True, "review_required": True}
    rows = [r for r in raw.get("records", []) if isinstance(r, dict)]
    malformed_rows = len(raw.get("records", [])) - len(rows)
    items = [i for r in rows for i in (r.get("review_items") or []) if isinstance(i, dict)]
    stale = sum(1 for r in rows if _is_stale(r))
    record_integrity_mismatches = sum(1 for row in rows if not _review_record_integrity_valid(row))
    candidate_integrity_mismatches = sum(1 for item in items if not _candidate_integrity_valid(item))
    authority = all(not i.get("approval_granted") and not i.get("decision_created") and not i.get("execution_permitted") and not i.get("action_authority") for i in items)
    return {
        **base,
        "record_count": len(rows),
        "review_item_count": len(items),
        "ready_count": sum(1 for i in items if i.get("review_readiness") == "ready_for_operator_review"),
        "blocked_count": sum(1 for i in items if i.get("review_readiness") != "ready_for_operator_review"),
        "stale_count": stale,
        "pending_count": len([p for p in raw.get("pending", []) if isinstance(p, dict)]),
        "malformed": bool(malformed_rows or record_integrity_mismatches or candidate_integrity_mismatches),
        "review_required": bool(malformed_rows or record_integrity_mismatches or candidate_integrity_mismatches),
        "record_integrity_mismatch_count": record_integrity_mismatches,
        "candidate_integrity_mismatch_count": candidate_integrity_mismatches,
        "approval_request_count": sum(1 for i in items if i.get("approval_request_created")),
        "content_exposed": False,
        "authority_preserved": authority,
        "registry_digest": _digest([{k: v for k, v in r.items() if k not in {"review_items", "operation_id"}} for r in rows])[:32],
    }
