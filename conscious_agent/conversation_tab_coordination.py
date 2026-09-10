from __future__ import annotations

"""Content-free multi-tab ownership and mutation fencing for dashboard chat.

The coordination record is runtime-private and deliberately excludes drafts, messages,
prompts, generated text, provider payloads, memories, actions, credentials, receipts,
and stack traces. It provides one expiring browser-tab lease plus bounded mutation
claims so competing tabs cannot create duplicate persistent work.
"""

import hashlib
import json
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from paths import DATA_DIR
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic

COORDINATION_SCHEMA_VERSION = "1"
MUTATION_RECEIPT_SCHEMA_VERSION = "1"
TAB_COORDINATION_DIR = DATA_DIR / "conversation_runtime" / "tab_coordination"
TAB_COORDINATION_STATE_FILE = TAB_COORDINATION_DIR / "state.json"
TAB_COORDINATION_MUTATION_DIR = TAB_COORDINATION_DIR / "mutations"
DEFAULT_LEASE_SECONDS = 15.0
MAX_LEASE_SECONDS = 60.0
_COORDINATION_LOCK = threading.RLock()
_TAB_ID_PATTERN = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$")
_BROWSER_ID_PATTERN = _TAB_ID_PATTERN
_INSTANCE_NONCE_PATTERN = re.compile(r"^[A-Za-z0-9-]{16,96}$")
_LEASE_TOKEN_PATTERN = re.compile(r"^[a-f0-9]{32,96}$")
_MUTATION_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{8,128}$")
_MUTATION_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_.:-]{1,63}$")
_SESSION_ID_PATTERN = re.compile(r"^conversation_session_[0-9]{8}T[0-9]{6}_[a-f0-9]{10}$")
_PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_SAFE_RESULT_FIELDS = {
    "operation_id", "session_id", "selected_session_id", "created_session_id",
    "affected_session_id", "fallback_session_id", "status", "action",
    "project_id", "previous_project_id", "target_project_id", "selected_project_id",
}


def _now_epoch() -> float:
    return time.time()


def _iso_from_epoch(value: float) -> str:
    return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_tab_id(value: str) -> str:
    token = str(value or "").strip().lower()
    if not _TAB_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid dashboard tab identifier.")
    return token


def _validate_browser_id(value: str) -> str:
    token = str(value or "").strip().lower()
    if not _BROWSER_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid dashboard browser identifier.")
    return token


def _validate_instance_nonce(value: str, *, required: bool = False) -> str:
    token = str(value or "").strip()
    if not token and not required:
        return ""
    if not _INSTANCE_NONCE_PATTERN.fullmatch(token):
        raise ValueError("Invalid dashboard tab instance nonce.")
    return token


def _validate_lease_token(value: str, *, required: bool = True) -> str:
    token = str(value or "").strip().lower()
    if not token and not required:
        return ""
    if not _LEASE_TOKEN_PATTERN.fullmatch(token):
        raise ValueError("Invalid dashboard ownership token.")
    return token


def _validate_mutation_key(value: str) -> str:
    token = str(value or "").strip()
    if not _MUTATION_KEY_PATTERN.fullmatch(token):
        raise ValueError("Invalid dashboard mutation key.")
    return token


def _validate_mutation_kind(value: str) -> str:
    token = str(value or "").strip().lower()
    if not _MUTATION_KIND_PATTERN.fullmatch(token):
        raise ValueError("Invalid dashboard mutation kind.")
    return token


def _validate_session_id(value: str, *, required: bool = False) -> str:
    token = str(value or "").strip()
    if not token and not required:
        return ""
    if not _SESSION_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation session identifier.")
    return token




def _validate_project_id(value: str, *, required: bool = False) -> str:
    token = str(value or "").strip().lower()
    if not token and not required:
        return ""
    if not _PROJECT_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid project identifier.")
    return token

def _load_json(path: Path) -> dict[str, Any] | None:
    return load_json_file(path, None, expected_type=dict)


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    write_json_atomic(path, value, expected_type=dict, sort_keys=True)


def _empty_state() -> dict[str, Any]:
    return {
        "type": "conversation_tab_coordination",
        "schema_version": COORDINATION_SCHEMA_VERSION,
        "revision": 0,
        "owner": {},
        "selected_session_id": "",
        "selected_project_id": "",
        "last_mutation_kind": "",
        "last_mutation_at": "",
        "updated_at": "",
        "local_private": True,
        "content_free": True,
    }


def _load_state() -> dict[str, Any]:
    value = _load_json(TAB_COORDINATION_STATE_FILE) or _empty_state()
    if value.get("type") != "conversation_tab_coordination":
        return _empty_state()
    value.setdefault("owner", {})
    value["revision"] = max(0, int(value.get("revision") or 0))
    return value


def _owner_expired(owner: dict[str, Any], now: float) -> bool:
    try:
        expires = float(owner.get("expires_epoch") or 0.0)
    except (TypeError, ValueError):
        expires = 0.0
    return not owner or expires <= now


def _expire_owner(state: dict[str, Any], now: float) -> bool:
    owner = state.get("owner") if isinstance(state.get("owner"), dict) else {}
    if owner and _owner_expired(owner, now):
        state["owner"] = {}
        state["updated_at"] = _iso_from_epoch(now)
        return True
    return False


def _new_owner(tab_id: str, browser_id: str, instance_nonce: str, now: float, lease_seconds: float) -> dict[str, Any]:
    duration = max(3.0, min(MAX_LEASE_SECONDS, float(lease_seconds or DEFAULT_LEASE_SECONDS)))
    return {
        "tab_id": tab_id,
        "browser_id": browser_id,
        "instance_nonce": instance_nonce,
        "lease_token": secrets.token_hex(24),
        "acquired_at": _iso_from_epoch(now),
        "heartbeat_at": _iso_from_epoch(now),
        "expires_at": _iso_from_epoch(now + duration),
        "expires_epoch": now + duration,
        "visible": True,
    }


def _public_state(state: dict[str, Any], *, requester_tab_id: str = "", status: str = "snapshot", message: str = "") -> dict[str, Any]:
    owner = state.get("owner") if isinstance(state.get("owner"), dict) else {}
    requester = str(requester_tab_id or "")
    is_owner = bool(owner and requester and owner.get("tab_id") == requester)
    result = {
        "ok": True,
        "type": "conversation_tab_coordination_status",
        "schema_version": COORDINATION_SCHEMA_VERSION,
        "status": status,
        "revision": max(0, int(state.get("revision") or 0)),
        "selected_session_id": str(state.get("selected_session_id") or ""),
        "selected_project_id": str(state.get("selected_project_id") or ""),
        "owner_present": bool(owner),
        "is_owner": is_owner,
        "owner_expires_at": str(owner.get("expires_at") or ""),
        "last_mutation_kind": str(state.get("last_mutation_kind") or "")[:64],
        "last_mutation_at": str(state.get("last_mutation_at") or ""),
        "message": str(message or "")[:240],
        "local_private": True,
        "content_free": True,
    }
    if is_owner:
        result["lease_token"] = str(owner.get("lease_token") or "")
    return result


def coordination_snapshot(*, tab_id: str = "", now_epoch: float | None = None) -> dict[str, Any]:
    requester = _validate_tab_id(tab_id) if tab_id else ""
    now = _now_epoch() if now_epoch is None else float(now_epoch)
    with _COORDINATION_LOCK:
        state = _load_state()
        changed = _expire_owner(state, now)
        if changed:
            _atomic_write(TAB_COORDINATION_STATE_FILE, state)
        return _public_state(state, requester_tab_id=requester, status="snapshot")


def register_dashboard_tab(
    tab_id: str,
    browser_id: str,
    *,
    instance_nonce: str = "",
    visible: bool = True,
    lease_seconds: float = DEFAULT_LEASE_SECONDS,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    tab = _validate_tab_id(tab_id)
    browser = _validate_browser_id(browser_id)
    instance = _validate_instance_nonce(instance_nonce)
    now = _now_epoch() if now_epoch is None else float(now_epoch)
    with _COORDINATION_LOCK:
        state = _load_state()
        _expire_owner(state, now)
        owner = state.get("owner") if isinstance(state.get("owner"), dict) else {}
        if not owner:
            state["owner"] = _new_owner(tab, browser, instance, now, lease_seconds)
            state["owner"]["visible"] = bool(visible)
            state["updated_at"] = _iso_from_epoch(now)
            _atomic_write(TAB_COORDINATION_STATE_FILE, state)
            return _public_state(state, requester_tab_id=tab, status="ownership_acquired", message="This tab controls conversation changes.")
        if owner.get("tab_id") == tab:
            owner_instance = str(owner.get("instance_nonce") or "")
            if owner_instance and instance and owner_instance != instance:
                result = _public_state(
                    state,
                    requester_tab_id="",
                    status="identity_conflict",
                    message="This duplicated tab needs a fresh identity before it can control conversation changes.",
                )
                result["renew_tab_id"] = True
                return result
            if instance and not owner_instance:
                owner["instance_nonce"] = instance
            duration = max(3.0, min(MAX_LEASE_SECONDS, float(lease_seconds or DEFAULT_LEASE_SECONDS)))
            owner["heartbeat_at"] = _iso_from_epoch(now)
            owner["expires_at"] = _iso_from_epoch(now + duration)
            owner["expires_epoch"] = now + duration
            owner["visible"] = bool(visible)
            state["updated_at"] = _iso_from_epoch(now)
            _atomic_write(TAB_COORDINATION_STATE_FILE, state)
            return _public_state(state, requester_tab_id=tab, status="ownership_retained", message="This tab controls conversation changes.")
        return _public_state(state, requester_tab_id=tab, status="following", message="Another tab controls changes. This tab stays synchronized.")


def heartbeat_dashboard_tab(
    tab_id: str,
    lease_token: str,
    *,
    instance_nonce: str = "",
    visible: bool = True,
    lease_seconds: float = DEFAULT_LEASE_SECONDS,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    tab = _validate_tab_id(tab_id)
    token = _validate_lease_token(lease_token)
    instance = _validate_instance_nonce(instance_nonce)
    now = _now_epoch() if now_epoch is None else float(now_epoch)
    with _COORDINATION_LOCK:
        state = _load_state()
        expired = _expire_owner(state, now)
        owner = state.get("owner") if isinstance(state.get("owner"), dict) else {}
        if expired or not owner:
            _atomic_write(TAB_COORDINATION_STATE_FILE, state)
            return _public_state(state, requester_tab_id=tab, status="ownership_expired", message="Conversation control is available.")
        if owner.get("tab_id") != tab or not secrets.compare_digest(str(owner.get("lease_token") or ""), token):
            return _public_state(state, requester_tab_id=tab, status="following", message="Another tab controls changes. This tab stays synchronized.")
        owner_instance = str(owner.get("instance_nonce") or "")
        if owner_instance and instance and owner_instance != instance:
            result = _public_state(state, requester_tab_id="", status="identity_conflict", message="This duplicated tab no longer owns conversation control.")
            result["renew_tab_id"] = True
            return result
        if instance and not owner_instance:
            owner["instance_nonce"] = instance
        duration = max(3.0, min(MAX_LEASE_SECONDS, float(lease_seconds or DEFAULT_LEASE_SECONDS)))
        owner["heartbeat_at"] = _iso_from_epoch(now)
        owner["expires_at"] = _iso_from_epoch(now + duration)
        owner["expires_epoch"] = now + duration
        owner["visible"] = bool(visible)
        state["updated_at"] = _iso_from_epoch(now)
        _atomic_write(TAB_COORDINATION_STATE_FILE, state)
        return _public_state(state, requester_tab_id=tab, status="ownership_retained", message="This tab controls conversation changes.")


def acquire_dashboard_tab_ownership(
    tab_id: str,
    browser_id: str,
    *,
    lease_token: str = "",
    instance_nonce: str = "",
    visible: bool = True,
    force: bool = False,
    same_browser_only: bool = False,
    lease_seconds: float = DEFAULT_LEASE_SECONDS,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    tab = _validate_tab_id(tab_id)
    browser = _validate_browser_id(browser_id)
    supplied_token = _validate_lease_token(lease_token, required=False)
    instance = _validate_instance_nonce(instance_nonce)
    now = _now_epoch() if now_epoch is None else float(now_epoch)
    with _COORDINATION_LOCK:
        state = _load_state()
        _expire_owner(state, now)
        owner = state.get("owner") if isinstance(state.get("owner"), dict) else {}
        if owner and owner.get("tab_id") != tab:
            same_browser_hidden_transfer = bool(
                visible
                and owner.get("browser_id") == browser
                and not bool(owner.get("visible", True))
            )
            explicit_transfer = bool(
                force
                and (not same_browser_only or owner.get("browser_id") == browser)
            )
            if same_browser_hidden_transfer or explicit_transfer:
                state["owner"] = _new_owner(tab, browser, instance, now, lease_seconds)
                state["updated_at"] = _iso_from_epoch(now)
                _atomic_write(TAB_COORDINATION_STATE_FILE, state)
                return _public_state(
                    state,
                    requester_tab_id=tab,
                    status="ownership_transferred",
                    message="Conversation control moved to this tab.",
                )
            return _public_state(state, requester_tab_id=tab, status="ownership_conflict", message="Another visible tab is still active. Control can transfer when it closes or becomes hidden.")
        if owner and supplied_token and not secrets.compare_digest(str(owner.get("lease_token") or ""), supplied_token):
            return _public_state(state, requester_tab_id=tab, status="ownership_conflict", message="This tab's ownership token is stale. Reconcile before changing anything.")
        if not owner:
            state["owner"] = _new_owner(tab, browser, instance, now, lease_seconds)
        else:
            owner_instance = str(owner.get("instance_nonce") or "")
            if owner_instance and instance and owner_instance != instance:
                result = _public_state(state, requester_tab_id="", status="identity_conflict", message="This duplicated tab needs a fresh identity before taking control.")
                result["renew_tab_id"] = True
                return result
            if instance and not owner_instance:
                owner["instance_nonce"] = instance
            duration = max(3.0, min(MAX_LEASE_SECONDS, float(lease_seconds or DEFAULT_LEASE_SECONDS)))
            owner["heartbeat_at"] = _iso_from_epoch(now)
            owner["expires_at"] = _iso_from_epoch(now + duration)
            owner["expires_epoch"] = now + duration
            owner["visible"] = bool(visible)
        state["updated_at"] = _iso_from_epoch(now)
        _atomic_write(TAB_COORDINATION_STATE_FILE, state)
        return _public_state(state, requester_tab_id=tab, status="ownership_acquired", message="This tab controls conversation changes.")


def release_dashboard_tab_ownership(
    tab_id: str,
    lease_token: str,
    *,
    instance_nonce: str = "",
    now_epoch: float | None = None,
) -> dict[str, Any]:
    tab = _validate_tab_id(tab_id)
    token = _validate_lease_token(lease_token)
    instance = _validate_instance_nonce(instance_nonce)
    now = _now_epoch() if now_epoch is None else float(now_epoch)
    with _COORDINATION_LOCK:
        state = _load_state()
        _expire_owner(state, now)
        owner = state.get("owner") if isinstance(state.get("owner"), dict) else {}
        owner_instance = str(owner.get("instance_nonce") or "")
        same_instance = not owner_instance or not instance or owner_instance == instance
        if owner and owner.get("tab_id") == tab and same_instance and secrets.compare_digest(str(owner.get("lease_token") or ""), token):
            state["owner"] = {}
            state["updated_at"] = _iso_from_epoch(now)
            _atomic_write(TAB_COORDINATION_STATE_FILE, state)
            return _public_state(state, requester_tab_id=tab, status="ownership_released", message="Conversation control was released.")
        return _public_state(state, requester_tab_id=tab, status="following", message="This tab did not own conversation control.")


def _mutation_path(mutation_key: str) -> Path:
    validated = _validate_mutation_key(mutation_key)
    filename = hashlib.sha256(validated.encode("utf-8")).hexdigest()
    return TAB_COORDINATION_MUTATION_DIR / f"{filename}.json"


def _public_receipt(value: dict[str, Any], *, duplicate: bool = False) -> dict[str, Any]:
    return {
        "mutation_key": str(value.get("mutation_key") or "")[:128],
        "mutation_kind": str(value.get("mutation_kind") or "")[:64],
        "session_id": str(value.get("session_id") or ""),
        "project_id": str(value.get("project_id") or ""),
        "revision": max(0, int(value.get("revision") or 0)),
        "status": str(value.get("status") or "pending")[:40],
        "duplicate_mutation": bool(duplicate),
        "result": dict(value.get("result") or {}),
        "local_private": True,
        "content_free": True,
    }


def claim_dashboard_tab_mutation(
    *,
    tab_id: str,
    lease_token: str,
    mutation_key: str,
    mutation_kind: str,
    session_id: str = "",
    project_id: str = "",
    expected_revision: int | None = None,
    advance_revision: bool = True,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    tab = _validate_tab_id(tab_id)
    token = _validate_lease_token(lease_token, required=False)
    key = _validate_mutation_key(mutation_key)
    kind = _validate_mutation_kind(mutation_kind)
    session = _validate_session_id(session_id)
    project = _validate_project_id(project_id)
    now = _now_epoch() if now_epoch is None else float(now_epoch)
    with _COORDINATION_LOCK:
        existing = _load_json(_mutation_path(key))
        if existing and existing.get("type") == "conversation_tab_mutation":
            result = _public_receipt(existing, duplicate=True)
            existing_status = str(existing.get("status") or "pending")
            if existing_status == "completed":
                result.update({"ok": True, "coordination": coordination_snapshot(tab_id=tab, now_epoch=now)})
            elif existing_status == "pending":
                result.update({
                    "ok": False,
                    "status": "mutation_in_progress",
                    "error": "This exact dashboard mutation is already in progress.",
                    "coordination": coordination_snapshot(tab_id=tab, now_epoch=now),
                })
            else:
                result.update({
                    "ok": False,
                    "status": "mutation_previously_failed",
                    "error": "This exact dashboard mutation already failed and was not repeated.",
                    "coordination": coordination_snapshot(tab_id=tab, now_epoch=now),
                })
            return result
        state = _load_state()
        _expire_owner(state, now)
        owner = state.get("owner") if isinstance(state.get("owner"), dict) else {}
        valid_owner = bool(
            owner
            and owner.get("tab_id") == tab
            and secrets.compare_digest(str(owner.get("lease_token") or ""), token)
            and not _owner_expired(owner, now)
        )
        if not valid_owner:
            if not owner:
                _atomic_write(TAB_COORDINATION_STATE_FILE, state)
            return {
                "ok": False,
                "status": "ownership_required",
                "error": "This tab does not own conversation control.",
                "coordination": _public_state(state, requester_tab_id=tab, status="ownership_required", message="Take control before changing conversation state."),
            }
        if project:
            try:
                from project_manager import get_active_project
                active = get_active_project() or {}
                active_project_id = str(active.get("id") or "eidolon").strip().lower()
            except Exception:
                active_project_id = "eidolon"
            if project != active_project_id:
                return {
                    "ok": False,
                    "status": "stale_project",
                    "error": "A newer active-project selection already won.",
                    "project_id": project,
                    "active_project_id": active_project_id,
                    "coordination": _public_state(state, requester_tab_id=tab, status="stale_project", message="Reconcile the active project before changing conversation state."),
                }
            if session:
                try:
                    from conversation_sessions import load_conversation_session, _session_project_id
                    session_record = load_conversation_session(session, include_turns=False)
                    session_project_id = _session_project_id(session_record)
                except Exception:
                    session_project_id = project
                if session_project_id != project:
                    return {
                        "ok": False,
                        "status": "session_project_mismatch",
                        "error": "The selected conversation belongs to a different project.",
                        "project_id": project,
                        "session_project_id": session_project_id,
                        "coordination": _public_state(state, requester_tab_id=tab, status="session_project_mismatch", message="Select a conversation from the active project."),
                    }
        current_revision = max(0, int(state.get("revision") or 0))
        if advance_revision and expected_revision is not None and int(expected_revision) != current_revision:
            return {
                "ok": False,
                "status": "stale_revision",
                "error": "A newer dashboard mutation already won.",
                "coordination": _public_state(state, requester_tab_id=tab, status="stale_revision", message="A newer change was preserved. Reconcile before trying again."),
            }
        revision = current_revision + 1 if advance_revision else current_revision
        if advance_revision:
            state["revision"] = revision
            state["last_mutation_kind"] = kind
            state["last_mutation_at"] = _iso_from_epoch(now)
            state["updated_at"] = _iso_from_epoch(now)
            _atomic_write(TAB_COORDINATION_STATE_FILE, state)
        receipt = {
            "type": "conversation_tab_mutation",
            "schema_version": MUTATION_RECEIPT_SCHEMA_VERSION,
            "mutation_key": key,
            "mutation_kind": kind,
            "session_id": session,
            "project_id": project,
            "tab_id": tab,
            "revision": revision,
            "status": "pending",
            "claimed_at": _iso_from_epoch(now),
            "completed_at": "",
            "result": {},
            "local_private": True,
            "content_free": True,
        }
        _atomic_write(_mutation_path(key), receipt)
        result = _public_receipt(receipt)
        result.update({"ok": True, "coordination": _public_state(state, requester_tab_id=tab, status="mutation_claimed")})
        return result


def complete_dashboard_tab_mutation(
    mutation_key: str,
    *,
    success: bool,
    selected_session_id: str = "",
    selected_project_id: str = "",
    result: dict[str, Any] | None = None,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    key = _validate_mutation_key(mutation_key)
    selected = _validate_session_id(selected_session_id) if selected_session_id else ""
    selected_project = _validate_project_id(selected_project_id)
    now = _now_epoch() if now_epoch is None else float(now_epoch)
    with _COORDINATION_LOCK:
        receipt = _load_json(_mutation_path(key))
        if not receipt or receipt.get("type") != "conversation_tab_mutation":
            raise ValueError("Dashboard mutation claim was not found.")
        was_pending = str(receipt.get("status") or "pending") == "pending"
        if was_pending:
            safe_result = {
                str(field): str(value)[:160]
                for field, value in dict(result or {}).items()
                if str(field) in _SAFE_RESULT_FIELDS and isinstance(value, (str, int, float, bool))
            }
            receipt["status"] = "completed" if success else "failed"
            receipt["completed_at"] = _iso_from_epoch(now)
            receipt["result"] = safe_result
            _atomic_write(_mutation_path(key), receipt)
            state = _load_state()
            if selected:
                state["selected_session_id"] = selected
            if selected_project:
                state["selected_project_id"] = selected_project
            state["updated_at"] = _iso_from_epoch(now)
            _atomic_write(TAB_COORDINATION_STATE_FILE, state)
        return _public_receipt(receipt, duplicate=not was_pending)


def execute_coordinated_mutation(
    *,
    tab_id: str,
    lease_token: str,
    mutation_key: str,
    mutation_kind: str,
    callback: Callable[[], Any],
    session_id: str = "",
    project_id: str = "",
    expected_revision: int | None = None,
    advance_revision: bool = True,
    selected_session_resolver: Callable[[Any], str] | None = None,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    claim = claim_dashboard_tab_mutation(
        tab_id=tab_id,
        lease_token=lease_token,
        mutation_key=mutation_key,
        mutation_kind=mutation_kind,
        session_id=session_id,
        project_id=project_id,
        expected_revision=expected_revision,
        advance_revision=advance_revision,
        now_epoch=now_epoch,
    )
    if not claim.get("ok"):
        return {"ok": False, "coordination_rejected": True, **claim}
    if claim.get("duplicate_mutation"):
        return {
            "ok": True,
            "duplicate_mutation": True,
            "value": dict(claim.get("result") or {}),
            "claim": claim,
            "receipt": claim,
            "coordination": claim.get("coordination") or coordination_snapshot(tab_id=tab_id, now_epoch=now_epoch),
        }
    try:
        value = callback()
    except Exception:
        complete_dashboard_tab_mutation(mutation_key, success=False, now_epoch=now_epoch)
        raise
    selected = selected_session_resolver(value) if selected_session_resolver else ""
    receipt = complete_dashboard_tab_mutation(
        mutation_key,
        success=True,
        selected_session_id=selected,
        selected_project_id=project_id,
        result=value if isinstance(value, dict) else {},
        now_epoch=now_epoch,
    )
    return {"ok": True, "value": value, "claim": claim, "receipt": receipt, "coordination": coordination_snapshot(tab_id=tab_id, now_epoch=now_epoch)}


def coordination_record_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {
        "content", "text", "message", "message_text", "user_message", "assistant_response",
        "prompt", "prompts", "partial", "partial_tokens", "memory", "memories", "action_payload",
        "provider", "model", "endpoint", "credentials", "secret", "stack_trace", "traceback",
        "raw_response", "draft", "draft_content", "receipt_payload",
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


def reconcile_coordination_selection(project_id: str, *, session_id: str = "") -> dict[str, Any]:
    """Restore content-free selected project/session state after dashboard restart.

    This does not claim ownership, advance a revision, or replay any mutation.
    """
    project = _validate_project_id(project_id, required=True)
    session = _validate_session_id(session_id) if session_id else ""
    now = _now_epoch()
    with _COORDINATION_LOCK:
        state = _load_state()
        _expire_owner(state, now)
        state["selected_project_id"] = project
        if session:
            state["selected_session_id"] = session
        state["updated_at"] = _iso_from_epoch(now)
        _atomic_write(TAB_COORDINATION_STATE_FILE, state)
        return _public_state(state, status="restart_reconciled", message="Project and conversation selection were restored without replaying a mutation.")
