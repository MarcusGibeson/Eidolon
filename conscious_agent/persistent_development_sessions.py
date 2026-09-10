from __future__ import annotations

"""v1256.3-v1256.5 integration for persistent development sessions.

Resumption is deliberately *materialization, not execution*: the session is
reconciled against durable v1254/v1255 records, a content-minimized progress
event is appended exactly once for that observed state, and the next existing
operator control is projected.  Provider/test/application/rollback authority is
never synthesized or replayed by the session layer.
"""

import re
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from isolated_coding_execution import load_isolated_coding_execution, public_isolated_coding_execution
from controlled_application_rollback_foundations import load_controlled_application, public_controlled_application
from controlled_application_rollback import load_controlled_rollback
from persistent_development_sessions_foundations import (
    DENIED_AUTHORITY,
    create_or_restore_persistent_development_session,
    load_persistent_development_session,
    public_persistent_development_session,
    refresh_persistent_development_session,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1256.5"
SESSION_RE = re.compile(r"devs_[a-f0-9]{24}", re.I)
REQUEST_RE = re.compile(r"devc_[a-f0-9]{24}", re.I)
_SHOW = re.compile(r"^(?:show|status\s+for)\s+(?:persistent\s+)?development\s+session\s+(?P<session_id>devs_[a-f0-9]{24})[.!?]*$", re.I)
_RESUME = re.compile(r"^resume\s+(?:persistent\s+)?development\s+session\s+(?P<session_id>devs_[a-f0-9]{24})[.!?]*$", re.I)
_TRACK = re.compile(r"^(?:track|resume)\s+development\s+request\s+(?P<request_id>devc_[a-f0-9]{24})[.!?]*$", re.I)


def _event_dir(session_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "persistent_development_session_events" / session_id


def _event_path(session_id: str, sequence: int, runtime_root=None) -> Path:
    return _event_dir(session_id, runtime_root) / f"event-{int(sequence):06d}.json"


def _event_valid(row: Mapping[str, Any]) -> bool:
    supplied = str(row.get("event_digest") or "")
    return bool(supplied and supplied == _digest({key: value for key, value in row.items() if key != "event_digest"}))


def load_persistent_development_session_events(session_id: str, *, runtime_root=None) -> list[dict[str, Any]]:
    session_id = str(session_id or "").lower()
    if not SESSION_RE.fullmatch(session_id):
        return []
    root = _event_dir(session_id, runtime_root)
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    prior = ""
    for path in sorted(root.glob("event-*.json")):
        row = _read_json(path)
        if not row or not _event_valid(row):
            return []
        if int(row.get("sequence") or 0) != len(rows) + 1 or str(row.get("prior_event_digest") or "") != prior:
            return []
        prior = str(row.get("event_digest") or "")
        rows.append(row)
    return rows


def _append_progress_event(record: Mapping[str, Any], event_type: str, *, runtime_root=None) -> dict[str, Any]:
    session_id = str(record.get("session_id") or "")
    request_id = str(record.get("request_id") or "")
    with _proposal_lock(request_id, runtime_root):
        events = load_persistent_development_session_events(session_id, runtime_root=runtime_root)
        identity_digest = _digest({
            "event_type": event_type,
            "session_digest": record.get("session_digest", ""),
            "phase": record.get("phase", ""),
            "next_action": record.get("next_action", ""),
        })
        if events and events[-1].get("identity_digest") == identity_digest:
            return {**events[-1], "operation_status": "restored"}
        sequence = len(events) + 1
        event = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "session_id": session_id,
            "request_id": request_id,
            "sequence": sequence,
            "event_type": event_type,
            "identity_digest": identity_digest,
            "session_digest": str(record.get("session_digest") or ""),
            "snapshot_digest": str(record.get("snapshot_digest") or ""),
            "generation": int(record.get("generation") or 0),
            "phase": str(record.get("phase") or ""),
            "next_action": str(record.get("next_action") or ""),
            "attempt_count": int(record.get("attempt_count") or 0),
            "blocker_count": int(record.get("blocker_count") or 0),
            "completed_work_count": int(record.get("completed_work_count") or 0),
            "prior_event_digest": str(events[-1].get("event_digest") or "") if events else "",
            "content_minimized": True,
            "private_content_included": False,
            "raw_provider_output_included": False,
            "raw_test_output_included": False,
            **DENIED_AUTHORITY,
        }
        event["event_digest"] = _digest(event)
        _atomic_json(_event_path(session_id, sequence, runtime_root), event)
        return {**event, "operation_status": "created"}


def _next_control(record: Mapping[str, Any], *, runtime_root=None) -> dict[str, Any]:
    request_id = str(record.get("request_id") or "")
    phase = str(record.get("phase") or "")
    control = {
        "kind": "none",
        "status": "no_operator_control_required",
        "authorization_phrase": "",
        "digest": "",
        "authority_consumed": False,
    }
    if phase in {"execution_authorization_required", "execution_recovery_required"}:
        execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
        public = public_isolated_coding_execution(execution) if execution else {}
        phrase = str(public.get("authorization_phrase") or execution.get("authorization_phrase") or "")
        if phrase:
            control.update(
                kind="isolated_execution_recovery" if phase == "execution_recovery_required" else "isolated_execution",
                status="expired_lease_recovery_requires_original_exact_authorization" if phase == "execution_recovery_required" else "existing_exact_authorization_required",
                authorization_phrase=phrase, digest=public.get("execution_digest", "") or execution.get("execution_digest", "")
            )
    elif phase in {"application_authorization_required", "application_recovery_required"}:
        application = load_controlled_application(request_id, runtime_root=runtime_root)
        public = public_controlled_application(application) if application else {}
        if public.get("authorization_phrase"):
            control.update(
                kind="controlled_application_recovery" if phase == "application_recovery_required" else "controlled_application",
                status="expired_lease_recovery_requires_original_exact_authorization" if phase == "application_recovery_required" else "existing_exact_authorization_required",
                authorization_phrase=public["authorization_phrase"], digest=public.get("application_digest", "")
            )
    elif phase == "rollback_authorization_required":
        rollback = load_controlled_rollback(request_id, runtime_root=runtime_root)
        phrase = str(rollback.get("authorization_phrase") or "") if rollback.get("phase") == "prepared" else ""
        if phrase:
            control.update(kind="controlled_rollback", status="existing_exact_authorization_required", authorization_phrase=phrase, digest=rollback.get("rollback_digest", ""))
    return control


def resume_persistent_development_session(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    record = refresh_persistent_development_session(session_id, runtime_root=runtime_root)
    if not record.get("ok"):
        return {"active": True, **record, "persistent_session": public_persistent_development_session(record)}
    event = _append_progress_event(record, "session_resumed", runtime_root=runtime_root)
    public = public_persistent_development_session(record)
    control = _next_control(record, runtime_root=runtime_root)
    return {
        "active": True,
        "event": "persistent_development_session_resumed",
        "status": "persistent_development_session_resumed",
        "session_id": str(record.get("session_id") or ""),
        "request_id": str(record.get("request_id") or ""),
        "persistent_session": public,
        "progress_event": {
            "sequence": int(event.get("sequence") or 0),
            "event_digest": str(event.get("event_digest") or ""),
            "operation_status": str(event.get("operation_status") or ""),
        },
        "next_control": control,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "selected_project_modified": False,
        **DENIED_AUTHORITY,
    }


def attach_persistent_development_session(result: Mapping[str, Any], *, runtime_root=None) -> dict[str, Any]:
    row = dict(result)
    request_id = str(row.get("request_id") or row.get("isolated_coding_request_id") or "")
    if not REQUEST_RE.fullmatch(request_id):
        for key in ("isolated_coding_execution", "controlled_application", "controlled_application_result", "controlled_rollback", "controlled_rollback_result"):
            nested = row.get(key)
            if isinstance(nested, Mapping) and REQUEST_RE.fullmatch(str(nested.get("request_id") or "")):
                request_id = str(nested.get("request_id") or "")
                break
    if not REQUEST_RE.fullmatch(request_id):
        return row
    session = create_or_restore_persistent_development_session(request_id.lower(), runtime_root=runtime_root)
    if session.get("ok"):
        session = refresh_persistent_development_session(str(session.get("session_id") or ""), runtime_root=runtime_root)
        event = _append_progress_event(session, "pipeline_progress_observed", runtime_root=runtime_root)
        row["persistent_development_session"] = public_persistent_development_session(session)
        row["persistent_development_session_event_digest"] = str(event.get("event_digest") or "")
    return row


def process_persistent_development_session_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _SHOW.fullmatch(text)
    if match:
        session = load_persistent_development_session(match.group("session_id").lower(), runtime_root=runtime_root)
        if not session:
            return {"active": True, "event": "persistent_development_session_missing", "status": "persistent_session_missing_or_tampered", **DENIED_AUTHORITY}
        public = public_persistent_development_session(session)
        return {"active": True, "event": "persistent_development_session_status", "status": "persistent_development_session_status", "persistent_session": public, "next_control": _next_control(session, runtime_root=runtime_root), **DENIED_AUTHORITY}
    match = _RESUME.fullmatch(text)
    if match:
        try:
            from persistent_development_sessions_reliability import resume_persistent_development_session_reliably
            return resume_persistent_development_session_reliably(match.group("session_id").lower(), runtime_root=runtime_root)
        except Exception:
            return resume_persistent_development_session(match.group("session_id").lower(), runtime_root=runtime_root)
    match = _TRACK.fullmatch(text)
    if match:
        session = create_or_restore_persistent_development_session(match.group("request_id").lower(), runtime_root=runtime_root)
        if not session.get("ok"):
            return {"active": True, "event": "persistent_development_session_track_blocked", **session}
        return resume_persistent_development_session(str(session.get("session_id") or ""), runtime_root=runtime_root)
    return {"active": False, "event": "inactive", "status": "inactive", **DENIED_AUTHORITY}


__all__ = [
    "attach_persistent_development_session", "load_persistent_development_session_events",
    "process_persistent_development_session_control", "resume_persistent_development_session",
]
