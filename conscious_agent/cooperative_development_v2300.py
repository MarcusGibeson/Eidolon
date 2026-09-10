from __future__ import annotations

"""Era 9 cooperative development coordination and conflict avoidance.

This is advisory coordination over existing execution/approval ownership, not a
second executor or authority path.  It binds work intents and candidates to base
manifests, detects overlap/drift, and prepares safe merge/rebase decisions.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

from json_storage import AtomicJsonWriteError, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR

CONTRACT_VERSION = "v2375.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era9_cooperative_development.json"
OWNERS = {"browser", "desktop_codex", "eidolon", "operator"}

_DENIED = {
    "source_modified": False,
    "candidate_merged": False,
    "candidate_applied": False,
    "tool_executed": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _is_digest(value: Any) -> bool:
    s = str(value or "").lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(runtime_root: str | Path | None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "development" / STATE_FILE


def _default() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "work": {}, "processed_events": [], "event_requests": {}, "raw_content_persisted": False}


def _valid_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _normalize_work_path(value: Any) -> str | None:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/") or "\x00" in raw or len(raw) > 300:
        return None
    parts = PurePosixPath(raw).parts
    if not parts or any(part in {"", ".", ".."} or ":" in part for part in parts):
        return None
    return "/".join(parts)


def _lease_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k != "lease_digest"})


def _valid_work_record(row: Any) -> bool:
    if not isinstance(row, Mapping) or not str(row.get("work_id") or "") or row.get("owner_kind") not in OWNERS:
        return False
    if not _is_digest(row.get("base_manifest_digest")) or not _is_digest(row.get("intent_digest")):
        return False
    if row.get("candidate_digest") and not _is_digest(row.get("candidate_digest")):
        return False
    paths = row.get("touched_paths")
    dependencies = row.get("dependency_digests")
    if not isinstance(paths, list) or len(paths) > 256 or any(_normalize_work_path(path) != path for path in paths):
        return False
    if not isinstance(dependencies, list) or not all(_is_digest(value) for value in dependencies):
        return False
    if row.get("state") not in {"active", "released", "cancelled", "completed", "superseded"} or not _valid_nonnegative_int(row.get("revision")):
        return False
    return _is_digest(row.get("lease_digest")) and row.get("lease_digest") == _lease_digest(row)


def _read_strict(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return _default(), "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "corrupt"
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION or value.get("contract_version") != CONTRACT_VERSION:
        return None, "invalid_shape"
    work = value.get("work")
    events = value.get("processed_events")
    requests = value.get("event_requests", {})
    if not isinstance(work, dict) or not isinstance(events, list) or not isinstance(requests, dict) or not _valid_nonnegative_int(value.get("revision")):
        return None, "invalid_shape"
    if len(events) > 1024 or not all(_is_digest(event) for event in events):
        return None, "invalid_event_state"
    if set(requests) != set(events) or not all(_is_digest(value) for value in requests.values()):
        return None, "invalid_event_request_state"
    if any(str(key) != str(row.get("work_id") or "") or not _valid_work_record(row) for key, row in work.items() if isinstance(row, Mapping)) or any(not isinstance(row, Mapping) for row in work.values()):
        return None, "invalid_work_record"
    value["raw_content_persisted"] = False
    return value, "valid"


def _public(row: Mapping[str, Any]) -> dict[str, Any]:
    return {k: row.get(k) for k in (
        "work_id", "owner_kind", "base_manifest_digest", "intent_digest", "candidate_digest",
        "state", "revision", "dependency_digests", "touched_paths", "lease_digest", "updated_at",
    )}


def inspect_work_coordination(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state, status = _read_strict(_path(runtime_root))
    if state is None:
        return {"ok": False, "status": f"cooperative_store_{status}", "mutation_permitted": False, **_DENIED}
    rows = [_public(r) for r in state["work"].values() if isinstance(r, Mapping)]
    return {
        "ok": True,
        "status": "cooperative_development_state_ready",
        "revision": int(state.get("revision") or 0),
        "work_items": sorted(rows, key=lambda r: str(r.get("work_id"))),
        "work_item_count": len(rows),
        "retained_operation_owner": "ownership_concurrency",
        "coordination_is_advisory_only": True,
        "content_free": True,
        **_DENIED,
    }


def register_work(
    *, work_id: str, owner_kind: str, base_manifest_digest: str, intent_digest: str,
    touched_paths: Sequence[str], dependency_digests: Sequence[str] = (), candidate_digest: str = "",
    event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    wid = str(work_id or "").strip(); owner = str(owner_kind or "").strip().lower(); event = str(event_id or "").strip()
    normalized_paths = [_normalize_work_path(p) for p in touched_paths if str(p).strip()]
    paths = sorted(set(path for path in normalized_paths if path is not None))
    deps = sorted(set(str(d).lower() for d in dependency_digests))
    if not wid or owner not in OWNERS or not event or not _is_digest(base_manifest_digest) or not _is_digest(intent_digest):
        return {"ok": False, "status": "invalid_work_contract", **_DENIED}
    if candidate_digest and not _is_digest(candidate_digest):
        return {"ok": False, "status": "invalid_candidate_digest", **_DENIED}
    if len(paths) > 256 or len(paths) != len(set(str(p).replace("\\", "/").strip() for p in touched_paths if str(p).strip())):
        return {"ok": False, "status": "invalid_work_path_scope", **_DENIED}
    if not all(_is_digest(d) for d in deps):
        return {"ok": False, "status": "invalid_dependency_digest", **_DENIED}
    path = _path(runtime_root); event_digest = _digest(["register-work", event])
    request_digest = _digest([wid, owner, base_manifest_digest.lower(), intent_digest.lower(), paths, deps, candidate_digest.lower()])
    try:
        with metadata_mutation_lock(path, timeout_seconds=15.0):
            state, state_status = _read_strict(path)
            if state is None:
                return {"ok": False, "status": f"cooperative_store_{state_status}", "store_preserved": True, **_DENIED}
            if event_digest in state["processed_events"]:
                if state["event_requests"].get(event_digest) != request_digest:
                    return {"ok": False, "status": "work_event_identity_conflict", **_DENIED}
                return {"ok": True, "status": "work_registration_replayed", "work": _public(state["work"].get(wid, {})), "idempotent": True, **_DENIED}
            existing = state["work"].get(wid)
            if isinstance(existing, Mapping) and existing.get("state") not in {"released", "cancelled", "superseded"}:
                return {"ok": False, "status": "work_identity_already_active", **_DENIED}
            row = {
                "work_id": wid, "owner_kind": owner, "base_manifest_digest": base_manifest_digest.lower(),
                "intent_digest": intent_digest.lower(), "candidate_digest": candidate_digest.lower(),
                "touched_paths": paths, "dependency_digests": deps, "state": "active", "revision": 1, "updated_at": _now(),
            }
            row["lease_digest"] = _lease_digest(row)
            state["work"][wid] = row
            state["processed_events"] = (state["processed_events"] + [event_digest])[-1024:]
            state["event_requests"][event_digest] = request_digest
            state["event_requests"] = {key: state["event_requests"][key] for key in state["processed_events"]}
            state["revision"] = int(state.get("revision") or 0) + 1
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False, replace_retries=12, retry_delay_seconds=0.05)
            return {"ok": True, "status": "work_registered", "work": _public(row), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "work_registration_blocked"), **_DENIED}


def revise_work(*, work_id: str, expected_lease_digest: str, action: str, event_id: str, candidate_digest: str = "", runtime_root: str | Path | None = None) -> dict[str, Any]:
    if action not in {"release", "cancel", "complete", "supersede", "attach_candidate"} or not _is_digest(expected_lease_digest) or not str(event_id or "").strip():
        return {"ok": False, "status": "invalid_work_revision", **_DENIED}
    if action == "attach_candidate" and not _is_digest(candidate_digest):
        return {"ok": False, "status": "candidate_digest_required", **_DENIED}
    path = _path(runtime_root); event_digest = _digest(["revise-work", event_id])
    request_digest = _digest([work_id, expected_lease_digest, action, candidate_digest.lower()])
    try:
        with metadata_mutation_lock(path, timeout_seconds=15.0):
            state, state_status = _read_strict(path)
            if state is None:
                return {"ok": False, "status": f"cooperative_store_{state_status}", "store_preserved": True, **_DENIED}
            if event_digest in state["processed_events"]:
                if state["event_requests"].get(event_digest) != request_digest:
                    return {"ok": False, "status": "work_revision_event_identity_conflict", **_DENIED}
                return {"ok": True, "status": "work_revision_replayed", "idempotent": True, **_DENIED}
            row = state["work"].get(work_id)
            if not isinstance(row, dict): return {"ok": False, "status": "work_not_found", **_DENIED}
            if row.get("lease_digest") != expected_lease_digest: return {"ok": False, "status": "stale_work_lease_digest", **_DENIED}
            if action == "attach_candidate": row["candidate_digest"] = candidate_digest.lower()
            else: row["state"] = {"release":"released", "cancel":"cancelled", "complete":"completed", "supersede":"superseded"}[action]
            row["revision"] = int(row.get("revision") or 0) + 1; row["updated_at"] = _now(); row["lease_digest"] = _lease_digest(row)
            state["processed_events"] = (state["processed_events"] + [event_digest])[-1024:]; state["revision"] = int(state.get("revision") or 0) + 1
            state["event_requests"][event_digest] = request_digest
            state["event_requests"] = {key: state["event_requests"][key] for key in state["processed_events"]}
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False, replace_retries=12, retry_delay_seconds=0.05)
            return {"ok": True, "status": "work_revised", "work": _public(row), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "work_revision_blocked"), **_DENIED}


def compare_work_candidates(left: Mapping[str, Any], right: Mapping[str, Any], *, current_manifest_digest: str = "") -> dict[str, Any]:
    if not _valid_work_record(left) or not _valid_work_record(right):
        return {"ok": False, "status": "invalid_candidate_coordination_evidence", **_DENIED}
    if current_manifest_digest and not _is_digest(current_manifest_digest):
        return {"ok": False, "status": "invalid_current_manifest_digest", **_DENIED}
    lpaths = {str(path).casefold(): str(path) for path in left.get("touched_paths") or []}
    rpaths = {str(path).casefold(): str(path) for path in right.get("touched_paths") or []}
    overlap = sorted(lpaths[key] for key in set(lpaths) & set(rpaths))
    same_intent = left.get("intent_digest") == right.get("intent_digest")
    same_base = left.get("base_manifest_digest") == right.get("base_manifest_digest")
    source_drift = bool(current_manifest_digest) and (left.get("base_manifest_digest") != current_manifest_digest or right.get("base_manifest_digest") != current_manifest_digest)
    if overlap:
        disposition = "manual_conflict_review_required"
    elif source_drift:
        disposition = "rebase_required"
    elif same_intent:
        disposition = "duplicate_intent_review_required"
    elif not same_base:
        disposition = "rebase_required"
    else:
        disposition = "independent_candidates_mergeable_in_principle"
    result = {
        "ok": True, "status": "candidate_coordination_compared", "disposition": disposition,
        "overlap_paths": overlap, "overlap_count": len(overlap), "same_intent": same_intent,
        "same_base": same_base, "source_drift": source_drift,
        "operator_edits_must_be_preserved": True,
        "merge_requires_separate_execution_authority": True,
        "content_free": True,
        **_DENIED,
    }
    result["comparison_digest"] = _digest(result)
    return result


def prepare_merge_plan(*, comparison: Mapping[str, Any], left_candidate_digest: str, right_candidate_digest: str, operator_edit_digest: str = "") -> dict[str, Any]:
    if not _is_digest(left_candidate_digest) or not _is_digest(right_candidate_digest) or (operator_edit_digest and not _is_digest(operator_edit_digest)):
        return {"ok": False, "status": "invalid_merge_evidence_digest", **_DENIED}
    supplied_comparison_digest = str(comparison.get("comparison_digest") or "")
    expected_comparison_digest = _digest({k: v for k, v in comparison.items() if k != "comparison_digest"})
    if not _is_digest(supplied_comparison_digest) or supplied_comparison_digest != expected_comparison_digest or comparison.get("status") != "candidate_coordination_compared":
        return {"ok": False, "status": "invalid_comparison_evidence", **_DENIED}
    disposition = str(comparison.get("disposition") or "")
    permitted = disposition == "independent_candidates_mergeable_in_principle"
    result = {
        "ok": True,
        "status": "merge_plan_prepared" if permitted else "merge_plan_blocked_for_review",
        "merge_preparation_permitted": permitted,
        "disposition": disposition,
        "left_candidate_digest": left_candidate_digest,
        "right_candidate_digest": right_candidate_digest,
        "operator_edit_digest": operator_edit_digest,
        "preserve_operator_edits": bool(operator_edit_digest),
        "actual_merge_performed": False,
        "content_free": True,
        **_DENIED,
    }
    result["merge_plan_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "inspect_work_coordination", "register_work", "revise_work", "compare_work_candidates", "prepare_merge_plan"]
