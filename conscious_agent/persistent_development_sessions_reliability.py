from __future__ import annotations

"""v1256.6-v1256.8 restart, corruption, concurrency and recovery hardening.

The persistent-session record is a projection over sealed v1254/v1255 runtime
artifacts, not a new authority source.  If the projection or its progress-event
chain is damaged, this layer may quarantine the damaged *runtime metadata* and
rebuild the projection from those authoritative artifacts. It never reconstructs
or replays provider output, test output, application authority, or rollback
authority.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from isolated_coding_execution_foundations import load_coding_work_request
from persistent_development_sessions_foundations import (
    DENIED_AUTHORITY,
    _index_path,
    _session_path_for_request,
    _valid,
    _validate_session_id,
    build_persistent_development_session_snapshot,
    create_or_restore_persistent_development_session,
    load_persistent_development_session,
    public_persistent_development_session,
    refresh_persistent_development_session,
)
from persistent_development_sessions import (
    _append_progress_event,
    _event_dir,
    load_persistent_development_session_events,
    resume_persistent_development_session,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1256.8"


def _file_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _quarantine_root(session_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "persistent_development_session_quarantine" / session_id


def _find_valid_session_record(session_id: str, runtime_root=None) -> tuple[str, dict[str, Any]]:
    root = _store_root(runtime_root) / "persistent_development_sessions"
    if not root.is_dir():
        return "", {}
    for path in sorted(root.glob("devc_*.json")):
        row = _read_json(path)
        if row and _valid(row) and str(row.get("session_id") or "") == session_id:
            return str(row.get("request_id") or ""), row
    return "", {}


def inspect_persistent_development_session_health(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    session_id = _validate_session_id(session_id)
    index_path = _index_path(session_id, runtime_root)
    index = _read_json(index_path)
    index_valid = bool(index and str(index.get("index_digest") or "") == _digest({key: value for key, value in index.items() if key != "index_digest"}) and index.get("session_id") == session_id)
    request_id = str(index.get("request_id") or "") if index_valid else ""
    session_path = _session_path_for_request(request_id, runtime_root) if request_id else Path()
    session = _read_json(session_path) if request_id else {}
    session_valid = bool(session and _valid(session) and session.get("session_id") == session_id)
    if not index_valid:
        recovered_request_id, recovered_session = _find_valid_session_record(session_id, runtime_root)
        if recovered_session:
            request_id, session, session_valid = recovered_request_id, recovered_session, True
    event_root = _event_dir(session_id, runtime_root)
    event_files = sorted(event_root.glob("event-*.json")) if event_root.is_dir() else []
    events = load_persistent_development_session_events(session_id, runtime_root=runtime_root)
    event_chain_valid = not event_files or len(events) == len(event_files)
    live_snapshot = build_persistent_development_session_snapshot(request_id, runtime_root=runtime_root) if request_id else {}
    lineage_available = bool(live_snapshot.get("ok"))
    snapshot_current = bool(session_valid and lineage_available and session.get("snapshot_digest") == live_snapshot.get("snapshot_digest"))
    reasons: list[str] = []
    if not index_valid:
        reasons.append("session_index_invalid_or_missing")
    if not session_valid:
        reasons.append("session_record_invalid_or_missing")
    if not event_chain_valid:
        reasons.append("session_event_chain_invalid")
    if session_valid and lineage_available and not snapshot_current:
        reasons.append("session_projection_stale")
    if not lineage_available:
        reasons.append("authoritative_development_lineage_unavailable")
    recoverable = bool((session_valid or (index_valid and request_id)) and lineage_available)
    status = "persistent_session_healthy" if not reasons else ("persistent_session_recovery_available" if recoverable else "persistent_session_recovery_blocked")
    result = {
        "ok": not reasons,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "session_id": session_id,
        "request_id": request_id,
        "index_valid": index_valid,
        "session_valid": session_valid,
        "event_chain_valid": event_chain_valid,
        "event_count": len(events) if event_chain_valid else len(event_files),
        "lineage_available": lineage_available,
        "snapshot_current": snapshot_current,
        "recoverable": recoverable,
        "reasons": reasons,
        "content_minimized": True,
        "private_content_exposed": False,
        "corrupt_content_exposed": False,
        **DENIED_AUTHORITY,
    }
    result["health_digest"] = _digest(result)
    return result


def _restore_index(session_id: str, request_id: str, session: Mapping[str, Any], *, runtime_root=None) -> None:
    index = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "session_id": session_id,
        "request_id": request_id,
        "request_contract_digest": str(session.get("request_contract_digest") or ""),
        "content_minimized": True,
    }
    index["index_digest"] = _digest(index)
    _atomic_json(_index_path(session_id, runtime_root), index)


def recover_persistent_development_session(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    session_id = _validate_session_id(session_id)
    initial = inspect_persistent_development_session_health(session_id, runtime_root=runtime_root)
    if initial.get("ok"):
        record = refresh_persistent_development_session(session_id, runtime_root=runtime_root)
        return {
            "ok": True,
            "status": "persistent_session_recovery_not_required",
            "session_id": session_id,
            "persistent_session": public_persistent_development_session(record),
            "health": initial,
            "quarantined_record_count": 0,
            **DENIED_AUTHORITY,
        }

    request_id = str(initial.get("request_id") or "")
    session = load_persistent_development_session(session_id, runtime_root=runtime_root)
    if not request_id or not session:
        found_request, found_session = _find_valid_session_record(session_id, runtime_root)
        if found_session:
            request_id, session = found_request, found_session
    if not request_id:
        # A valid index can still identify the authoritative request even when
        # the session record itself is corrupted.
        index = _read_json(_index_path(session_id, runtime_root))
        supplied = str(index.get("index_digest") or "") if index else ""
        if index and supplied == _digest({k: v for k, v in index.items() if k != "index_digest"}):
            request_id = str(index.get("request_id") or "")
    request = load_coding_work_request(request_id, runtime_root=runtime_root) if request_id else {}
    if not request:
        return {"ok": False, "status": "persistent_session_recovery_lineage_missing", "session_id": session_id, **DENIED_AUTHORITY}

    with _proposal_lock(request_id, runtime_root):
        quarantine = _quarantine_root(session_id, runtime_root)
        quarantine.mkdir(parents=True, exist_ok=True)
        quarantined = 0
        session_path = _session_path_for_request(request_id, runtime_root)
        raw_session = _read_json(session_path)
        if raw_session and not _valid(raw_session):
            digest = _file_digest(session_path) or _digest({"kind": "corrupt_session", "request_id": request_id})
            os.replace(session_path, quarantine / f"session-{digest[:16]}.json")
            quarantined += 1
        if not _read_json(_index_path(session_id, runtime_root)) or not initial.get("index_valid"):
            if session and _valid(session):
                _restore_index(session_id, request_id, session, runtime_root=runtime_root)
        event_root = _event_dir(session_id, runtime_root)
        if event_root.exists() and not initial.get("event_chain_valid"):
            digest = _digest([_file_digest(path) for path in sorted(event_root.glob("event-*.json"))])
            target = quarantine / f"events-{digest[:16]}"
            if target.exists():
                shutil.rmtree(target)
            os.replace(event_root, target)
            quarantined += 1

    # If a session projection was corrupt it has been quarantined, allowing the
    # canonical request lineage to create it again deterministically.
    record = create_or_restore_persistent_development_session(request_id, runtime_root=runtime_root)
    if not record.get("ok"):
        return {"ok": False, "status": "persistent_session_recovery_rebuild_failed", "session_id": session_id, **DENIED_AUTHORITY}
    if str(record.get("session_id") or "") != session_id:
        return {"ok": False, "status": "persistent_session_recovery_identity_mismatch", "session_id": session_id, **DENIED_AUTHORITY}
    record = refresh_persistent_development_session(session_id, runtime_root=runtime_root)
    event = _append_progress_event(record, "session_recovered_from_authoritative_lineage", runtime_root=runtime_root)
    final_health = inspect_persistent_development_session_health(session_id, runtime_root=runtime_root)
    result = {
        "ok": bool(final_health.get("ok")),
        "status": "persistent_session_recovered" if final_health.get("ok") else "persistent_session_recovery_incomplete",
        "session_id": session_id,
        "request_id": request_id,
        "persistent_session": public_persistent_development_session(record),
        "progress_event_digest": str(event.get("event_digest") or ""),
        "quarantined_record_count": quarantined,
        "health": final_health,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "selected_project_modified": False,
        **DENIED_AUTHORITY,
    }
    result["recovery_digest"] = _digest(result)
    return result


def resume_persistent_development_session_reliably(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    health = inspect_persistent_development_session_health(session_id, runtime_root=runtime_root)
    recovery = None
    if not health.get("ok") and health.get("recoverable"):
        recovery = recover_persistent_development_session(session_id, runtime_root=runtime_root)
        if not recovery.get("ok"):
            return {"active": True, "event": "persistent_development_session_recovery_blocked", **recovery}
    elif not health.get("ok"):
        return {"active": True, "event": "persistent_development_session_recovery_blocked", **health}
    resumed = resume_persistent_development_session(session_id, runtime_root=runtime_root)
    if recovery:
        resumed["recovery"] = {
            "status": recovery.get("status"),
            "recovery_digest": recovery.get("recovery_digest", ""),
            "quarantined_record_count": int(recovery.get("quarantined_record_count") or 0),
        }
    return resumed


def build_persistent_development_session_handoff(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    health = inspect_persistent_development_session_health(session_id, runtime_root=runtime_root)
    record = load_persistent_development_session(session_id, runtime_root=runtime_root)
    public = public_persistent_development_session(record) if record else {}
    handoff = {
        "ok": bool(record) and bool(health.get("ok")),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "persistent_development_session_handoff_ready" if record and health.get("ok") else "persistent_development_session_handoff_blocked",
        "session_id": session_id,
        "request_id": str(public.get("request_id") or ""),
        "generation": int(public.get("generation") or 0),
        "phase": str(public.get("phase") or ""),
        "attempt_count": int(public.get("attempt_count") or 0),
        "blocker_count": int(public.get("blocker_count") or 0),
        "completed_work_count": int(public.get("completed_work_count") or 0),
        "requirements_preserved": bool(public.get("requirements_preserved")),
        "plan_preserved": bool(public.get("plan_preserved")),
        "verification_evidence_preserved": bool(public.get("verification_evidence_preserved")),
        "health_digest": str(health.get("health_digest") or ""),
        "next_action": str(public.get("next_action") or ""),
        "content_minimized": True,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **DENIED_AUTHORITY,
    }
    handoff["handoff_digest"] = _digest(handoff)
    return handoff


__all__ = [
    "build_persistent_development_session_handoff", "inspect_persistent_development_session_health",
    "recover_persistent_development_session", "resume_persistent_development_session_reliably",
]
