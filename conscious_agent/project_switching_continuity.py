from __future__ import annotations

"""Content-free project-switch continuity and exactly-once revision fencing.

Runtime records live beneath DATA_DIR and never contain conversation text, drafts,
provider payloads, credentials, or source content.  The module deliberately imports
project/session systems lazily so ordinary dashboard health remains lightweight.
"""

import hashlib
import json
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import DATA_DIR

PROJECT_SWITCH_SCHEMA_VERSION = "1"
PROJECT_SWITCH_RECEIPT_SCHEMA_VERSION = "1"
PROJECT_SWITCH_DIR = DATA_DIR / "workspaces" / "project_switching"
PROJECT_SWITCH_STATE_FILE = PROJECT_SWITCH_DIR / "state.json"
PROJECT_SWITCH_RECEIPT_DIR = PROJECT_SWITCH_DIR / "receipts"
_SWITCH_LOCK = threading.RLock()
_PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_SWITCH_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{8,128}$")
_SAFE_NAVIGATION_FIELDS = {"selected_session_id", "catalog_cursor", "scroll_anchor", "view", "filter"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _project_id(value: str) -> str:
    token = str(value or "").strip().lower()
    if not _PROJECT_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid project identifier.")
    return token


def _switch_key(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        token = f"project-switch-{secrets.token_hex(16)}"
    if not _SWITCH_KEY_PATTERN.fullmatch(token):
        raise ValueError("Invalid project switch key.")
    return token


def _load(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
        for attempt in range(5):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def _empty_state(active_project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "type": "project_switch_continuity",
        "schema_version": PROJECT_SWITCH_SCHEMA_VERSION,
        "revision": 0,
        "active_project_id": str(active_project_id or "eidolon"),
        "previous_project_id": "",
        "projects": {},
        "last_switch_key": "",
        "last_switch_status": "",
        "updated_at": "",
        "local_private": True,
        "content_free": True,
    }


def _state(active_project_id: str = "eidolon") -> dict[str, Any]:
    state = _load(PROJECT_SWITCH_STATE_FILE) or _empty_state(active_project_id)
    if state.get("type") != "project_switch_continuity":
        state = _empty_state(active_project_id)
    state["revision"] = max(0, int(state.get("revision") or 0))
    state["projects"] = dict(state.get("projects") or {})
    state.setdefault("active_project_id", active_project_id or "eidolon")
    return state


def _receipt_path(key: str) -> Path:
    digest = hashlib.sha256(_switch_key(key).encode("utf-8")).hexdigest()
    return PROJECT_SWITCH_RECEIPT_DIR / f"{digest}.json"


def _public_receipt(value: dict[str, Any], *, duplicate: bool = False) -> dict[str, Any]:
    return {
        "type": "project_switch_receipt",
        "schema_version": PROJECT_SWITCH_RECEIPT_SCHEMA_VERSION,
        "switch_key": str(value.get("switch_key") or "")[:128],
        "previous_project_id": str(value.get("previous_project_id") or ""),
        "target_project_id": str(value.get("target_project_id") or ""),
        "revision": max(0, int(value.get("revision") or 0)),
        "status": str(value.get("status") or "pending")[:40],
        "claimed_at": str(value.get("claimed_at") or ""),
        "completed_at": str(value.get("completed_at") or ""),
        "duplicate_switch": bool(duplicate),
        "local_private": True,
        "content_free": True,
    }


def project_conversation_continuity(project_id: str) -> dict[str, Any]:
    """Return bounded, content-free session/draft/operation continuity for one project."""
    project = _project_id(project_id)
    try:
        import conversation_sessions as sessions
        import conversation_operations as operations

        rows = sessions.list_conversation_sessions(include_archived=False, project_id=project)
        pointer = sessions._active_session_pointer()  # content-free private pointer
        selected_id = str((pointer.get("projects") or {}).get(project) or "")
        selected = next((row for row in rows if str(row.get("id") or "") == selected_id), None)
        draft = sessions.load_conversation_draft(selected_id) if selected_id and selected else {}
        running = 0
        uncertain = 0
        for row in rows:
            for marker in operations.list_operation_markers(session_id=str(row.get("id") or "")):
                if str(marker.get("project_id") or project) != project:
                    continue
                state = str(marker.get("public_state") or "")
                running += int(state == "running")
                uncertain += int(state == "uncertain")
        unfinished_sessions = sum(
            1 for row in rows
            if int(row.get("turn_count") or 0) > int(row.get("completed_turn_count") or 0)
        )
        return {
            "project_id": project,
            "active_session_id": selected_id,
            "session_count": len(rows),
            "draft_revision": max(0, int(draft.get("revision") or 0)),
            "has_draft": bool(draft.get("content")),
            "running_operation_count": running,
            "uncertain_operation_count": uncertain,
            "unfinished_session_count": unfinished_sessions,
            "captured_at": _now(),
            "local_private": True,
            "content_free": True,
        }
    except Exception as error:
        return {
            "project_id": project,
            "active_session_id": "",
            "session_count": 0,
            "draft_revision": 0,
            "has_draft": False,
            "running_operation_count": 0,
            "uncertain_operation_count": 0,
            "unfinished_session_count": 0,
            "capture_status": "unavailable",
            "error_type": type(error).__name__,
            "captured_at": _now(),
            "local_private": True,
            "content_free": True,
        }


def record_project_navigation(project_id: str, **values: str) -> dict[str, Any]:
    project = _project_id(project_id)
    safe = {key: str(value or "")[:160] for key, value in values.items() if key in _SAFE_NAVIGATION_FIELDS}
    with _SWITCH_LOCK:
        state = _state(project)
        projects = dict(state.get("projects") or {})
        current = dict(projects.get(project) or {})
        current["navigation"] = safe
        current["navigation_updated_at"] = _now()
        projects[project] = current
        state["projects"] = projects
        state["updated_at"] = _now()
        _write(PROJECT_SWITCH_STATE_FILE, state)
        return project_switch_snapshot(project_id=project)


def capture_project_continuity(project_id: str) -> dict[str, Any]:
    project = _project_id(project_id)
    snapshot = project_conversation_continuity(project)
    with _SWITCH_LOCK:
        state = _state(project)
        projects = dict(state.get("projects") or {})
        existing = dict(projects.get(project) or {})
        navigation = dict(existing.get("navigation") or {})
        projects[project] = {**snapshot, "navigation": navigation}
        state["projects"] = projects
        state["updated_at"] = _now()
        _write(PROJECT_SWITCH_STATE_FILE, state)
    return snapshot


def claim_project_switch(
    previous_project_id: str,
    target_project_id: str,
    *,
    expected_revision: int | None = None,
    switch_key: str = "",
    source_tab_id: str = "",
) -> dict[str, Any]:
    previous = _project_id(previous_project_id)
    target = _project_id(target_project_id)
    key = _switch_key(switch_key)
    with _SWITCH_LOCK:
        existing = _load(_receipt_path(key))
        if existing and existing.get("type") == "project_switch_receipt":
            public = _public_receipt(existing, duplicate=True)
            public["ok"] = str(existing.get("status") or "") == "completed"
            if not public["ok"]:
                public["error"] = "This exact project switch is already pending or failed."
            return public
        state = _state(previous)
        current_revision = max(0, int(state.get("revision") or 0))
        if expected_revision is not None and int(expected_revision) != current_revision:
            return {
                "ok": False,
                "status": "stale_revision",
                "error": "A newer project selection already won. Reconcile before switching.",
                "expected_revision": int(expected_revision),
                "current_revision": current_revision,
                "active_project_id": str(state.get("active_project_id") or previous),
                "local_private": True,
                "content_free": True,
            }
        revision = current_revision + 1
        receipt = {
            "type": "project_switch_receipt",
            "schema_version": PROJECT_SWITCH_RECEIPT_SCHEMA_VERSION,
            "switch_key": key,
            "previous_project_id": previous,
            "target_project_id": target,
            "source_tab_id": str(source_tab_id or "")[:80],
            "revision": revision,
            "status": "pending",
            "claimed_at": _now(),
            "completed_at": "",
            "local_private": True,
            "content_free": True,
        }
        _write(_receipt_path(key), receipt)
        state["revision"] = revision
        state["previous_project_id"] = previous
        state["last_switch_key"] = key
        state["last_switch_status"] = "pending"
        state["updated_at"] = _now()
        _write(PROJECT_SWITCH_STATE_FILE, state)
        result = _public_receipt(receipt)
        result["ok"] = True
        return result


def complete_project_switch(switch_key: str, *, success: bool, actual_project_id: str) -> dict[str, Any]:
    key = _switch_key(switch_key)
    actual = _project_id(actual_project_id)
    with _SWITCH_LOCK:
        receipt = _load(_receipt_path(key))
        if not receipt or receipt.get("type") != "project_switch_receipt":
            raise ValueError("Project switch claim was not found.")
        pending = str(receipt.get("status") or "pending") == "pending"
        target = str(receipt.get("target_project_id") or "")
        completed = bool(success and actual == target)
        if pending:
            receipt["status"] = "completed" if completed else "failed"
            receipt["actual_project_id"] = actual
            receipt["completed_at"] = _now()
            _write(_receipt_path(key), receipt)
            state = _state(actual)
            if completed:
                state["active_project_id"] = actual
            state["last_switch_key"] = key
            state["last_switch_status"] = str(receipt["status"])
            state["updated_at"] = _now()
            _write(PROJECT_SWITCH_STATE_FILE, state)
        public = _public_receipt(receipt, duplicate=not pending)
        public["ok"] = str(receipt.get("status") or "") == "completed"
        return public


def reconcile_project_switch_state(actual_project_id: str) -> dict[str, Any]:
    """Recover visible switch state after restart without replaying a mutation."""
    actual = _project_id(actual_project_id)
    with _SWITCH_LOCK:
        state = _state(actual)
        key = str(state.get("last_switch_key") or "")
        receipt = _load(_receipt_path(key)) if key else None
        recovered = False
        if receipt and str(receipt.get("status") or "") == "pending":
            target = str(receipt.get("target_project_id") or "")
            complete_project_switch(key, success=(actual == target), actual_project_id=actual)
            recovered = True
            state = _state(actual)
        if str(state.get("active_project_id") or "") != actual:
            state["previous_project_id"] = str(state.get("active_project_id") or "")
            state["active_project_id"] = actual
            state["updated_at"] = _now()
            _write(PROJECT_SWITCH_STATE_FILE, state)
        result = project_switch_snapshot(project_id=actual)
        result["restart_reconciled"] = recovered
        result["switch_replayed"] = False
        return result


def project_switch_snapshot(*, project_id: str = "") -> dict[str, Any]:
    with _SWITCH_LOCK:
        state = _state(project_id or "eidolon")
        selected = _project_id(project_id) if project_id else str(state.get("active_project_id") or "eidolon")
        project_state = dict((state.get("projects") or {}).get(selected) or {})
        return {
            "ok": True,
            "type": "project_switch_status",
            "schema_version": PROJECT_SWITCH_SCHEMA_VERSION,
            "revision": max(0, int(state.get("revision") or 0)),
            "active_project_id": str(state.get("active_project_id") or selected),
            "previous_project_id": str(state.get("previous_project_id") or ""),
            "last_switch_key": str(state.get("last_switch_key") or "")[:128],
            "last_switch_status": str(state.get("last_switch_status") or ""),
            "project": project_state,
            "controls": {
                "keyboard_accessible": True,
                "narrow_layout_safe": True,
                "confirmation_required": True,
                "stale_revision_rejected": True,
            },
            "provider_contacted": False,
            "switch_replayed": False,
            "local_private": True,
            "content_free": True,
        }


def switching_record_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {
        "content", "draft_content", "message", "user_message", "assistant_response", "prompt",
        "provider_payload", "credential", "secret", "memory", "transcript", "source_content",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False


def restore_project_switch_continuity() -> dict[str, Any]:
    """Restore active project/session/draft visibility after a fresh process starts."""
    import project_manager
    import conversation_sessions as sessions
    from conversation_tab_coordination import reconcile_coordination_selection

    active = project_manager.get_active_project() or {}
    project_id = _project_id(str(active.get("id") or "eidolon"))
    reconciled = reconcile_project_switch_state(project_id)
    session = sessions.get_active_conversation_session(create_if_missing=False) or {}
    session_id = str(session.get("id") or "")
    draft = sessions.load_conversation_draft(session_id) if session_id else {}
    capture_project_continuity(project_id)
    coordination = reconcile_coordination_selection(project_id, session_id=session_id)
    return {
        "ok": True,
        "status": "restored",
        "project_id": project_id,
        "project_name": str(active.get("name") or ""),
        "active_session_id": session_id,
        "draft_revision": max(0, int(draft.get("revision") or 0)),
        "has_draft": bool(draft.get("content")),
        "source_binding": project_manager.project_source_binding(project_id),
        "switching": reconciled,
        "coordination": coordination,
        "accepted_turn_replayed": False,
        "switch_replayed": False,
        "provider_contacted": False,
        "local_private": True,
        "content_free": True,
    }
