from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import socket
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from approval_manager import create_approval
from command_runner import run_approved_command, validate_command
from conversation_quality import classify_conversation_quality
from conversational_capability_boundary import is_supervised_capability_catalog_request
from memory import store_memory
from paths import DATA_DIR
from conversation_surface_contracts import ACTION_CANCEL, ACTION_RETRY
try:
    from persistent_state_index import list_indexed_action_ids, lookup_indexed_action_ids, rebuild_action_index, update_action_index
    from persistent_state_projection_cache import cached_projection
except ImportError:
    from persistent_state_index import list_indexed_action_ids, lookup_indexed_action_ids, rebuild_action_index, update_action_index
    from persistent_state_projection_cache import cached_projection


def suggest_patch(*args: Any, **kwargs: Any) -> Any:
    """Lazy compatibility wrapper; importing the router must not seed runtime settings."""
    from patch_suggester import suggest_patch as implementation
    return implementation(*args, **kwargs)


CHAT_ACTIONS_DIR = DATA_DIR / "chat_actions"
CHAT_ACTIONS_README = CHAT_ACTIONS_DIR / "README.md"
_CHAT_ACTION_LOCK = threading.RLock()
_CHAT_ACTION_INTERPROCESS_STATE = threading.local()
_CHAT_ACTION_LOCK_WAIT_SECONDS = 15.0
_CHAT_ACTION_STALE_LOCK_SECONDS = 300.0
_CHAT_ACTION_INTERRUPTED_CLAIM_SECONDS = 240.0
_CHAT_ACTION_CLAIM_LEASE_SECONDS = 240.0
_CHAT_ACTION_MAX_CLAIM_LEASE_SECONDS = 900.0
_MAX_EXECUTION_ATTEMPTS = 12
_MAX_ACTION_EVENTS = 40

DIRECT_COMMAND = "direct_command"
DIRECT_FUNCTION = "direct_function"
APPROVAL = "approval"
BLOCKED = "blocked"
INFO = "info"

_CLAIMANT_LABELS = {
    "dashboard": "the dashboard",
    "api": "the local API",
    "cli": "the command line",
    "conversation": "the conversation console",
    "process": "another Eidolon process",
}

SMALL_TALK_ONLY_PATTERNS = (
    r"^(hi|hello|hey|yo|howdy)[!. ]*$",
    r"^(good morning|good afternoon|good evening|good night)[!. ]*$",
    r"^(thanks|thank you|cool|nice|awesome|sweet)[!. ]*$",
)

ACTION_FOLLOW_UP_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "status",
        re.compile(
            r"^(?:please\s+)?(?:did (?:that|it) finish|is (?:that|it) (?:done|finished|still running)|"
            r"what happened(?: with (?:that|it))?|how did (?:that|it) go|did (?:that|it) work|"
            r"show me (?:the )?(?:result|status)|what(?:'s| is) the (?:result|status)|"
            r"why did (?:that|it) fail|what were we working on|"
            r"did (?:the )?[a-z0-9 _-]{3,80} finish|is (?:the )?[a-z0-9 _-]{3,80} (?:done|finished|still running)|"
            r"what happened with (?:the )?[a-z0-9 _-]{3,80}|how did (?:the )?[a-z0-9 _-]{3,80} go|"
            r"show me (?:the )?[a-z0-9 _-]{3,80} (?:result|status)|why did (?:the )?[a-z0-9 _-]{3,80} fail)\s*[?.!]*$",
            re.I,
        ),
    ),
    (
        "retry",
        re.compile(
            r"^(?:please\s+)?(?:try|retry|run|do) (?:(?:that|it)(?: again| one more time)?|"
            r"(?:the )?[a-z0-9 _-]{3,80}(?: again| one more time))\s*[?.!]*$",
            re.I,
        ),
    ),
    (
        "cancel",
        re.compile(
            r"^(?:please\s+)?(?:do not|don't|dont) run (?:that|it)(?: yet)?\s*[?.!]*$|"
            r"^(?:please\s+)?(?:cancel|stop|hold) (?:(?:that|it)(?: for now)?|(?:the )?[a-z0-9 _-]{3,80})\s*[?.!]*$",
            re.I,
        ),
    ),
    (
        "approval",
        re.compile(
            r"^(?:please\s+)?(?:approve (?:that|it)|"
            r"(?:review the approval for|show the approval for) (?:(?:that|it)|(?:the )?[a-z0-9 _-]{3,80})|"
            r"approve (?:the )?[a-z0-9 _-]{3,64} (?:approval|request|action))\s*[?.!]*$",
            re.I,
        ),
    ),
)


def _is_small_talk_only(request: str) -> bool:
    lowered = request.strip().lower()
    if not lowered:
        return False
    return any(re.fullmatch(pattern, lowered) for pattern in SMALL_TALK_ONLY_PATTERNS)


def _quote_cli_value(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

SELF_DEVELOPMENT_REQUEST_MARKERS = (
    "self development cycle",
    "self-development cycle",
    "begin self development",
    "begin work on a self development cycle",
    "begin work on a self-development cycle",
    "controlled self-development loop",
    "what should you improve next",
    "plan your own next development step",
    "identify what needs to be improved next",
    "improve yourself next",
    "own next development step",
    "start improving yourself",
    "figure out what you should work on next",
    "begin your own development loop",
    "review your project and make a task",
    "look at your failed actions and plan the next fix",
    "failed actions and plan",
    "what should be the next thing we work on you for",
    "what should we work on you next",
    "what should we work on next for you",
    "what should we work on next for eidolon",
)





def _is_self_development_patch_application_approval_request(request: str) -> bool:
    return bool(re.fullmatch(r"Approve applying self-development patch draft [A-Za-z0-9_.:-]+", request.strip()))

def _self_development_patch_application_command(request: str) -> str:
    safe_phrase = request.strip().replace('"', '\"')
    return f'python conscious_agent/main.py --self-development-patch-application "{safe_phrase}" --self-development-full'

def _is_self_development_patch_draft_approval_request(request: str) -> bool:
    return bool(re.fullmatch(r"Approve drafting a patch proposal for self-development task [A-Za-z0-9_.:-]+", request.strip()))

def _self_development_patch_draft_command(request: str) -> str:
    safe_phrase = request.strip().replace('"', '\"')
    return f'python conscious_agent/main.py --self-development-patch-draft "{safe_phrase}" --self-development-full'

def _is_self_development_cycle_request(lowered: str) -> bool:
    compact = lowered.replace("-", " ")
    if any(marker in lowered or marker.replace("-", " ") in compact for marker in SELF_DEVELOPMENT_REQUEST_MARKERS):
        return True
    if "self" in compact and "development" in compact and any(term in compact for term in ["cycle", "loop", "next", "plan", "improve"]):
        return True
    if "own project" in compact and any(term in compact for term in ["inspect", "improve", "next development", "development step"]):
        return True
    return False


@dataclass
class ChatActionExecutionResult:
    ok: bool
    chat_action_id: str
    message: str = ""
    status: str = ""
    result: dict[str, Any] | None = None
    error: str = ""
    dry_run: bool = False
    replayed: bool = False


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_claimant(value: str) -> str:
    token = re.sub(r"[^a-z0-9_-]+", "-", str(value or "process").strip().lower()).strip("-")
    return token[:40] or "process"


def _claimant_label(value: str) -> str:
    token = _normalize_claimant(value)
    return _CLAIMANT_LABELS.get(token, "another Eidolon process")


def _redacted_text(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _redacted_result_summary(action: dict[str, Any], status: str, result_data: dict[str, Any] | None = None) -> str:
    title = _redacted_text(action.get("title") or "Supervised action", 120)
    normalized = str(status or "").lower()
    if normalized in {"executed", "completed", "success", "succeeded", "info"}:
        return f"{title} completed successfully. Detailed output remains in the governed action record."
    if normalized in {"approval_created", "approval_required", "awaiting_approval"}:
        return f"{title} created an operator-controlled approval request."
    if normalized in {"timed_out", "timeout"}:
        return f"{title} reached its bounded timeout. Original evidence remains available for review."
    if normalized == "interrupted":
        return f"{title} was interrupted after its execution claim. It did not receive a terminal result."
    if normalized in {"cancelled", "canceled"}:
        return f"{title} was cancelled before execution."
    if normalized in {"blocked"}:
        return f"{title} remains blocked by supervised-operation boundaries."
    if normalized in {"running", "claimed"}:
        owner = action.get("claim_owner") if isinstance(action.get("claim_owner"), dict) else {}
        return f"{title} is currently running through {_claimant_label(str(owner.get('scope') or 'process'))}."
    return f"{title} failed safely. Original evidence remains available for review."


def _redacted_attempt_result(status: str, result_data: dict[str, Any], summary: str) -> dict[str, Any]:
    return {
        "ok": bool(result_data.get("ok")) and str(status) in {"executed", "completed", "approval_created"},
        "status": str(status or "failed")[:40],
        "summary": _redacted_text(summary, 280),
        "return_code": result_data.get("return_code") if isinstance(result_data.get("return_code"), int) else None,
        "redacted": True,
    }


def _append_action_event(
    action: dict[str, Any],
    event_type: str,
    status: str,
    summary: str,
    *,
    attempt_number: int = 0,
    owner_scope: str = "",
) -> None:
    events = [dict(item) for item in action.get("action_events", []) if isinstance(item, dict)]
    sequence = max(int(action.get("event_sequence") or 0), max((int(item.get("sequence") or 0) for item in events), default=0)) + 1
    event = {
        "event_id": f"{action.get('id')}:event:{sequence}",
        "sequence": sequence,
        "type": _redacted_text(event_type, 48),
        "status": _redacted_text(status, 40),
        "summary": _redacted_text(summary, 280),
        "occurred_at": _now(),
        "attempt_number": max(0, int(attempt_number or 0)),
        "owner_scope": _normalize_claimant(owner_scope) if owner_scope else "",
        "redacted": True,
    }
    events.append(event)
    action["event_sequence"] = sequence
    action["action_events"] = events
    _compact_action_events(action)


def _compact_action_events(action: dict[str, Any]) -> None:
    events = [dict(item) for item in action.get("action_events", []) if isinstance(item, dict)]
    if len(events) <= _MAX_ACTION_EVENTS:
        action["action_events"] = events
        return
    pruned = events[:-_MAX_ACTION_EVENTS]
    summary = dict(action.get("event_history_summary") or {})
    counts = dict(summary.get("status_counts") or {})
    for event in pruned:
        key = str(event.get("status") or "unknown")[:40]
        counts[key] = int(counts.get(key) or 0) + 1
    summary.update({
        "pruned_event_count": int(summary.get("pruned_event_count") or 0) + len(pruned),
        "status_counts": counts,
        "first_pruned_at": str(summary.get("first_pruned_at") or pruned[0].get("occurred_at") or "")[:40],
        "last_pruned_at": str(pruned[-1].get("occurred_at") or "")[:40],
        "last_pruned_type": str(pruned[-1].get("type") or "")[:48],
        "redacted": True,
    })
    action["event_history_summary"] = summary
    action["action_events"] = events[-_MAX_ACTION_EVENTS:]


def _sanitize_execution_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    status = str(attempt.get("status") or "")[:40]
    result = attempt.get("result") if isinstance(attempt.get("result"), dict) else {}
    summary = str(result.get("summary") or result.get("message") or result.get("error") or "")
    return {
        "attempt_id": str(attempt.get("attempt_id") or "")[:160],
        "attempt_number": max(0, int(attempt.get("attempt_number") or 0)),
        "status": status,
        "started_at": str(attempt.get("started_at") or "")[:40],
        "completed_at": str(attempt.get("completed_at") or "")[:40],
        "retry_of_attempt_id": str(attempt.get("retry_of_attempt_id") or "")[:160],
        "claimant_scope": _normalize_claimant(str(attempt.get("claimant_scope") or "process")),
        "result": _redacted_attempt_result(status, result, summary or f"Attempt is {status or 'unknown'}."),
    }


def _compact_execution_attempts(action: dict[str, Any]) -> None:
    attempts = [_sanitize_execution_attempt(dict(item)) for item in action.get("execution_attempts", []) if isinstance(item, dict)]
    if len(attempts) <= _MAX_EXECUTION_ATTEMPTS:
        action["execution_attempts"] = attempts
        return
    pruned = attempts[:-_MAX_EXECUTION_ATTEMPTS]
    summary = dict(action.get("execution_history_summary") or {})
    counts = dict(summary.get("status_counts") or {})
    latest_failure = dict(summary.get("latest_pruned_failure") or {})
    for attempt in pruned:
        key = str(attempt.get("status") or "unknown")[:40]
        counts[key] = int(counts.get(key) or 0) + 1
        if key in {"failed", "timed_out", "interrupted"}:
            latest_failure = {
                "attempt_number": int(attempt.get("attempt_number") or 0),
                "status": key,
                "completed_at": str(attempt.get("completed_at") or "")[:40],
                "summary": _redacted_text((attempt.get("result") or {}).get("summary"), 240),
                "redacted": True,
            }
    summary.update({
        "pruned_attempt_count": int(summary.get("pruned_attempt_count") or 0) + len(pruned),
        "status_counts": counts,
        "first_pruned_attempt": int(summary.get("first_pruned_attempt") or pruned[0].get("attempt_number") or 0),
        "last_pruned_attempt": int(pruned[-1].get("attempt_number") or 0),
        "latest_pruned_failure": latest_failure,
        "redacted": True,
    })
    action["execution_history_summary"] = summary
    action["execution_attempts"] = attempts[-_MAX_EXECUTION_ATTEMPTS:]


def _prepare_action_for_storage(action: dict[str, Any]) -> None:
    action.pop("effective_status", None)
    action.pop("claim_interrupted", None)
    _compact_action_events(action)
    _compact_execution_attempts(action)


def _slug(text: str, max_length: int = 56) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return (cleaned or "chat-action")[:max_length].strip("-") or "chat-action"


def _ensure_storage() -> None:
    CHAT_ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not CHAT_ACTIONS_README.exists():
        try:
            with CHAT_ACTIONS_README.open("x", encoding="utf-8") as file:
                file.write(
                    "Saved chat-to-action proposals. These translate plain-English requests into safe commands, patch suggestions, or approval requests.\n"
                )
        except FileExistsError:
            pass


def _new_chat_action_id(intent: str) -> str:
    return f"chat_action_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{_slug(intent, 36)}"


def _chat_action_path(chat_action_id: str) -> Path:
    _ensure_storage()
    return CHAT_ACTIONS_DIR / f"{chat_action_id}.json"


def _chat_action_lock_path(lock_key: str) -> Path:
    _ensure_storage()
    locks_dir = CHAT_ACTIONS_DIR / ".locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    normalized = str(lock_key or "chat-action")
    digest = hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()[:24]
    readable = _slug(normalized, 32)
    return locks_dir / f"{readable}-{digest}.lock"


def _held_interprocess_locks() -> dict[str, int]:
    held = getattr(_CHAT_ACTION_INTERPROCESS_STATE, "held", None)
    if not isinstance(held, dict):
        held = {}
        _CHAT_ACTION_INTERPROCESS_STATE.held = held
    return held


@contextmanager
def _chat_action_interprocess_lock(lock_key: str, *, timeout_seconds: float | None = None):
    """Bound one cross-process action-store mutation with an atomic lock file.

    The lock is held only for short read/check/write critical sections, never for
    provider generation or command execution. Reentrant calls in the same thread
    reuse the already-owned lock so save helpers can remain defensive.
    """
    lock_path = _chat_action_lock_path(lock_key)
    lock_token = f"{os.getpid()}:{threading.get_ident()}:{uuid.uuid4().hex}"
    held = _held_interprocess_locks()
    lock_id = str(lock_path.resolve())
    if held.get(lock_id, 0):
        held[lock_id] += 1
        try:
            yield
        finally:
            held[lock_id] -= 1
            if held[lock_id] <= 0:
                held.pop(lock_id, None)
        return

    wait_seconds = _CHAT_ACTION_LOCK_WAIT_SECONDS if timeout_seconds is None else float(timeout_seconds)
    deadline = time.monotonic() + max(0.1, wait_seconds)
    acquired = False
    while not acquired:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age_seconds = max(0.0, time.time() - lock_path.stat().st_mtime)
            except FileNotFoundError:
                continue
            if age_seconds >= _CHAT_ACTION_STALE_LOCK_SECONDS:
                stale_path = lock_path.with_name(f"{lock_path.name}.stale.{uuid.uuid4().hex}")
                try:
                    lock_path.replace(stale_path)
                except FileNotFoundError:
                    continue
                except OSError:
                    pass
                else:
                    try:
                        stale_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for chat-action interprocess lock: {lock_key}")
            time.sleep(0.02)
            continue
        try:
            payload = json.dumps({"token": lock_token, "pid": os.getpid(), "created_at": _now()})
            os.write(descriptor, payload.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        acquired = True

    held[lock_id] = 1
    try:
        yield
    finally:
        held.pop(lock_id, None)
        try:
            current = lock_path.read_text(encoding="utf-8")
        except OSError:
            current = ""
        if lock_token in current:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


@contextmanager
def _chat_action_storage_lock(lock_key: str):
    with _CHAT_ACTION_LOCK:
        with _chat_action_interprocess_lock(lock_key):
            yield


def save_chat_action(action: dict[str, Any]) -> None:
    _ensure_storage()
    action_id = str(action["id"])
    with _chat_action_storage_lock(f"action:{action_id}"):
        _prepare_action_for_storage(action)
        path = _chat_action_path(action_id)
        temporary = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(action, file, indent=2)
                file.flush()
                os.fsync(file.fileno())
            temporary.replace(path)
            try:
                update_action_index(CHAT_ACTIONS_DIR, action)
            except Exception:
                pass
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_chat_actions(status: str = "", include_closed: bool = True) -> list[dict[str, Any]]:
    if not CHAT_ACTIONS_DIR.exists():
        return []
    try:
        action_ids = cached_projection(
            CHAT_ACTIONS_DIR, "action", ("list", str(status or ""), bool(include_closed)),
            lambda: list_indexed_action_ids(CHAT_ACTIONS_DIR, status=status, include_closed=include_closed),
            ttl_seconds=20.0,
        )
        actions = [data for action_id in action_ids if (data := _load_json_file(_chat_action_path(action_id)))]
        return actions
    except Exception:
        actions: list[dict[str, Any]] = []
        for path in CHAT_ACTIONS_DIR.glob("*.json"):
            data = _load_json_file(path)
            if not data:
                continue
            if status and data.get("status") != status:
                continue
            if not include_closed and data.get("status") not in {"proposed", "approval_required"}:
                continue
            actions.append(data)
        return sorted(actions, key=lambda item: item.get("created_at", ""), reverse=True)


def lookup_chat_actions(*, action_ids: tuple[str, ...] = (), deduplication_keys: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Load only action receipts explicitly referenced by the current prompt history."""
    if not CHAT_ACTIONS_DIR.exists():
        return []
    try:
        ids = lookup_indexed_action_ids(
            CHAT_ACTIONS_DIR, action_ids=action_ids, deduplication_keys=deduplication_keys,
        )
        return [data for action_id in ids if (data := _load_json_file(_chat_action_path(action_id)))]
    except Exception:
        wanted_ids = {str(value) for value in action_ids if str(value or '').strip()}
        wanted_dedup = {str(value) for value in deduplication_keys if str(value or '').strip()}
        return [
            action for action in list_chat_actions(include_closed=True)
            if str(action.get('id') or '') in wanted_ids or str(action.get('deduplication_key') or '') in wanted_dedup
        ]


def resolve_chat_action_id(chat_action_id: str) -> str:
    token = (chat_action_id or "").strip()
    lowered = token.lower()

    alias_status = {
        "latest-proposed": "proposed",
        "last-proposed": "proposed",
        "latest-executed": "executed",
        "last-executed": "executed",
        "latest-approved": "approval_created",
        "last-approved": "approval_created",
        "latest-approval": "approval_created",
        "last-approval": "approval_created",
        "latest-blocked": "blocked",
        "last-blocked": "blocked",
        "latest-failed": "failed",
        "last-failed": "failed",
    }

    # Only an alias needs the catalogue. A concrete identifier resolves to itself,
    # and loading every action first made a single lookup read the whole
    # directory - once per transcript turn, for a value it already had.
    if not (lowered in {"latest", "last"} or lowered in alias_status or lowered.startswith("latest-")):
        return token

    actions = list_chat_actions(include_closed=True)

    if lowered in {"latest", "last"}:
        return actions[0].get("id", "") if actions else ""

    if lowered in alias_status:
        matches = [item for item in actions if item.get("status") == alias_status[lowered]]
        return matches[0].get("id", "") if matches else ""

    if lowered.startswith("latest-"):
        desired_intent = lowered.replace("latest-", "", 1).replace("-", "_")
        matches = [item for item in actions if item.get("intent") == desired_intent]
        return matches[0].get("id", "") if matches else ""

    return token


def load_chat_action(chat_action_id: str) -> dict[str, Any] | None:
    if not CHAT_ACTIONS_DIR.exists():
        return None
    resolved = resolve_chat_action_id(chat_action_id)
    if not resolved:
        return None
    path = _chat_action_path(resolved)
    if path.exists():
        return _load_json_file(path)
    for action in list_chat_actions(include_closed=True):
        if action.get("id") == resolved:
            return action
    return None


def _normalize_request(user_request: str) -> str:
    return re.sub(r"\s+", " ", user_request.strip())


def _looks_like_path(value: str) -> bool:
    return bool(re.search(r"\.(py|json|md|txt|js|ts|java|kt|cs|php|html|css|gd)\b", value, re.IGNORECASE))


def _normalize_project_path(path_text: str) -> str:
    path_text = path_text.strip().strip('"\'`.,')
    path_text = path_text.replace("\\", "/")
    if not path_text:
        return ""
    if "/" not in path_text and _looks_like_path(path_text):
        return f"conscious_agent/{path_text}"
    return path_text


def _extract_file_path(text: str) -> str:
    # Prefer explicit paths first.
    match = re.search(r"([\w./\\-]+\.(?:py|json|md|txt|js|ts|java|kt|cs|php|html|css|gd))", text, re.IGNORECASE)
    if match:
        return _normalize_project_path(match.group(1))
    return ""


def _make_action(
    user_request: str,
    intent: str,
    title: str,
    summary: str,
    execution_mode: str,
    risk_level: str = "low",
    command: str = "",
    function_name: str = "",
    function_args: dict[str, Any] | None = None,
    approval_action_type: str = "",
    approval_object_id: str = "",
    approval_command: str = "",
    blocked_reason: str = "",
    explanation: str = "",
    source: str = "chat_action_router",
    target_action_id: str = "",
    control_kind: str = "",
) -> dict[str, Any]:
    action = {
        "id": _new_chat_action_id(intent),
        "type": "chat_action",
        "created_at": _now(),
        "updated_at": _now(),
        "status": "proposed" if execution_mode not in {BLOCKED, INFO} else execution_mode,
        "user_request": user_request,
        "intent": intent,
        "title": title,
        "summary": summary,
        "explanation": explanation or summary,
        "execution_mode": execution_mode,
        "risk_level": risk_level,
        "command": command,
        "function_name": function_name,
        "function_args": function_args or {},
        "approval_action_type": approval_action_type,
        "approval_object_id": approval_object_id,
        "approval_command": approval_command,
        "blocked_reason": blocked_reason,
        "source": source,
        "target_action_id": str(target_action_id or "")[:120],
        "control_kind": str(control_kind or "")[:40],
        "result": {},
        "approval_id": "",
        "useful_commands": [],
        "action_events": [],
        "event_sequence": 0,
        "result_summary": "",
        "result_summary_status": "",
    }
    action["useful_commands"] = _chat_action_commands(action)
    initial_status = str(action.get("status") or "proposed")
    initial_type = "proposal_created" if initial_status == "proposed" else ("action_blocked" if initial_status == BLOCKED else "information_ready")
    initial_summary = (
        "A supervised action proposal was created."
        if initial_status == "proposed"
        else _redacted_result_summary(action, initial_status, {})
    )
    action["result_summary"] = initial_summary
    action["result_summary_status"] = initial_status
    _append_action_event(action, initial_type, initial_status, initial_summary)
    return action


def _chat_action_commands(action: dict[str, Any]) -> list[str]:
    action_id = action.get("id", "latest")
    commands = [
        f"python conscious_agent/main.py --show-chat-action {action_id}",
    ]
    if action.get("execution_mode") in {DIRECT_COMMAND, DIRECT_FUNCTION, APPROVAL, ACTION_RETRY, ACTION_CANCEL}:
        commands.extend([
            f"python conscious_agent/main.py --execute-chat-action {action_id} --dry-run",
            f"python conscious_agent/main.py --execute-chat-action {action_id}",
        ])
    return commands


def _direct_command(user_request: str, intent: str, title: str, summary: str, command: str, risk: str = "low") -> dict[str, Any]:
    validation = validate_command(command)
    if not validation.ok:
        return _make_action(
            user_request=user_request,
            intent=intent,
            title=title,
            summary=f"The matched command was blocked by command safety: {validation.reason}",
            execution_mode=BLOCKED,
            risk_level="medium",
            command=command,
            blocked_reason=validation.reason,
        )
    return _make_action(
        user_request=user_request,
        intent=intent,
        title=title,
        summary=summary,
        execution_mode=DIRECT_COMMAND,
        risk_level=risk,
        command=command,
        explanation="This maps to an approved read-only or low-risk command.",
    )


SUPERVISED_CAPABILITY_REGISTRY: tuple[dict[str, str], ...] = (
    {"id": "diagnostics", "label": "diagnostics and system health", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "maintenance", "label": "maintenance scans", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "settings_health", "label": "settings and configured-model health", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "approvals", "label": "approval inbox review", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "task_project", "label": "task and project status", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "memory", "label": "memory status", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "attention_center", "label": "redacted operator attention center", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "notifications", "label": "notifications and bounded watch checks", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "planning", "label": "session planning", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "file_review", "label": "safe static file review", "mode": DIRECT_COMMAND, "boundary": "allowlisted read"},
    {"id": "patch_proposal", "label": "patch proposals without automatic application", "mode": DIRECT_FUNCTION, "boundary": "proposal only"},
    {"id": "self_development", "label": "proposal-only supervised self-development", "mode": DIRECT_COMMAND, "boundary": "proposal only"},
    {"id": "software_development", "label": "supervised software-development campaign proposals", "mode": DIRECT_FUNCTION, "boundary": "proposal only"},
    {"id": "bounded_web_research", "label": "session-authorized public web research", "mode": DIRECT_FUNCTION, "boundary": "bounded GET/HEAD research"},
    {"id": "experiment_review", "label": "independent read-only review of an installed experiment package", "mode": DIRECT_FUNCTION, "boundary": "proposal only"},
)


def registered_supervised_capabilities() -> tuple[str, ...]:
    return tuple(item["label"] for item in SUPERVISED_CAPABILITY_REGISTRY)


def supervised_capability_summary() -> str:
    direct = [item["label"] for item in SUPERVISED_CAPABILITY_REGISTRY if item["boundary"] == "allowlisted read"]
    proposals = [item["label"] for item in SUPERVISED_CAPABILITY_REGISTRY if item["boundary"] == "proposal only"]
    research = [item["label"] for item in SUPERVISED_CAPABILITY_REGISTRY if item["boundary"] == "bounded GET/HEAD research"]
    return (
        "Currently registered supervised capabilities: allowlisted reads for "
        + "; ".join(direct)
        + ". Proposal-only capabilities: "
        + "; ".join(proposals)
        + ". Session-authorized read-only research: "
        + "; ".join(research)
        + ". Modifications remain approval-governed; unrestricted shell access, model management, provider switching, and release promotion are not registered chat capabilities."
    )


_EXPERIMENT_REVIEW_LIST = re.compile(
    r"\b(?:what|which) experiments?(?: packages?)? can you review\b|\bwhat can you review\b|"
    r"\blist (?:the )?(?:eligible |installed |reviewable )?experiment packages\b",
)
_EXPERIMENT_REVIEW_STATUS = re.compile(
    r"\b(?:review|job) status\b|\bstatus of (?:the |my )?(?:experiment )?review\b|\bis the (?:experiment )?review (?:done|finished|running)\b|"
    r"\bhow is the (?:experiment )?review (?:going|doing)\b",
)
_EXPERIMENT_REVIEW_START = re.compile(
    r"^(?:please\s+)?(?:can you\s+)?(?:independently\s+)?review (?:the\s+)?(?:experiment\s+)?(?P<name>[A-Za-z][A-Za-z0-9 _-]{1,60}?)"
    r"(?:\s+independently)?\s*[.?!]*$",
    re.IGNORECASE,
)


def _is_any_experiment_review_request(request: str) -> bool:
    """True only for the three explicit review phrasings, so ordinary conversation stays conversation."""
    lowered = " ".join(str(request or "").split()).lower()
    return bool(_is_experiment_review_list_request(lowered) or _is_experiment_review_status_request(lowered) or _experiment_review_target(request))


_REVIEW_CONFIRMATION = re.compile(
    r"^(?:please\s+)?(?:confirm(?:ed|\s+it)?|yes(?:,?\s+please)?|(?:yes,?\s+)?go\s+ahead|approved?|start\s+it)\s*[.!]*$",
    re.I,
)


def pending_review_action() -> dict[str, Any] | None:
    """The most recent saved review proposal still waiting to run, or None.

    A confirmation means nothing on its own: it is a control over a persisted proposal, so it resolves against the
    saved action record rather than against anything the conversation remembers.
    """
    try:
        rows = [row for row in list_chat_actions(include_closed=False)
                if str(row.get("intent") or "") == "experiment_review_start" and str(row.get("status") or "") == "proposed"]
    except Exception:
        return None
    rows.sort(key=lambda row: (str(row.get("created") or ""), str(row.get("id") or "")))
    return rows[-1] if rows else None


def is_review_confirmation(request: str) -> bool:
    """True only for a bare confirmation that follows a saved review proposal still waiting to run."""
    if not _REVIEW_CONFIRMATION.fullmatch(" ".join(str(request or "").split())):
        return False
    return pending_review_action() is not None


def is_experiment_review_question(request: str) -> bool:
    """True only for the two question-shaped review phrasings: what can be reviewed, and how a review is going.

    The start phrasing is deliberately excluded.  An explicit "review <name>" already reads as an action request on
    the conversation path, and its pattern is broad enough to also match ordinary conversation such as "can you
    review my thoughts on this", which must stay conversation.
    """
    lowered = " ".join(str(request or "").split()).lower()
    return bool(_is_experiment_review_list_request(lowered) or _is_experiment_review_status_request(lowered))


def _is_experiment_review_list_request(lowered: str) -> bool:
    return bool(_EXPERIMENT_REVIEW_LIST.search(lowered))


def _is_experiment_review_status_request(lowered: str) -> bool:
    return bool(_EXPERIMENT_REVIEW_STATUS.search(lowered))


def _experiment_review_target(request: str) -> str:
    """The package name in an explicit review request, or "". Never a path, a file or a free-form instruction."""
    match = _EXPERIMENT_REVIEW_START.match(" ".join(str(request or "").split()))
    if not match:
        return ""
    name = match.group("name").strip()
    if _looks_like_path(name) or any(ch in name for ch in "/\\.*?"):
        return ""
    return "" if name.lower() in {"it", "this", "that", "them", "everything", "the code", "my code"} else name


def classify_chat_action_follow_up(user_request: str) -> str:
    request = _normalize_request(user_request)
    for kind, pattern in ACTION_FOLLOW_UP_PATTERNS:
        if pattern.fullmatch(request):
            return kind
    return ""


_FOLLOW_UP_STOPWORDS = {
    "a", "again", "approval", "approve", "cancel", "check", "did", "do", "does", "done", "don", "dont", "finish", "finished",
    "for", "happen", "happened", "hold", "how", "is", "it", "me", "of", "one", "please", "result", "retry",
    "not", "review", "run", "running", "show", "status", "still", "stop", "that", "the", "this", "time", "try", "what", "why", "with", "yet",
}
_FOLLOW_UP_TOKEN_ALIASES = {
    "maintainence": "maintenance",
    "maintenence": "maintenance",
    "check": "scan",
    "healthcheck": "health",
    "diagnostic": "diagnostics",
    "configuration": "settings",
    "config": "settings",
    "memories": "memory",
    "projects": "project",
    "tasks": "task",
}


def _follow_up_descriptor_tokens(user_request: str) -> set[str]:
    lowered = _normalize_request(user_request).lower()
    tokens: set[str] = set()
    for token in re.findall(r"[a-z0-9_-]+", lowered):
        normalized = _FOLLOW_UP_TOKEN_ALIASES.get(token, token)
        if normalized in _FOLLOW_UP_STOPWORDS or len(normalized) < 3:
            continue
        tokens.add(normalized)
    return tokens


def _action_match_tokens(action: dict[str, Any]) -> set[str]:
    text = " ".join([
        str(action.get("intent") or ""),
        str(action.get("title") or ""),
        str(action.get("summary") or ""),
    ]).lower()
    result: set[str] = set()
    for token in re.findall(r"[a-z0-9_-]+", text):
        normalized = _FOLLOW_UP_TOKEN_ALIASES.get(token, token)
        if len(normalized) >= 3:
            result.add(normalized)
    return result


def _follow_up_candidate_eligible(kind: str, action: dict[str, Any]) -> bool:
    from conversation_action_portal import build_action_portal_state

    portal = build_action_portal_state(action, action.get("result") if isinstance(action.get("result"), dict) else None) or {}
    status = str(portal.get("status") or action.get("status") or "")
    if kind == "retry":
        return bool(status in {"failed", "timed_out", "interrupted"} and action.get("execution_mode") == DIRECT_COMMAND and action.get("risk_level") == "low")
    if kind == "cancel":
        return str(action.get("status") or "") in {"proposed", "approval_required"}
    if kind == "approval":
        return bool(status == "awaiting_approval" or portal.get("approval_id"))
    return True


def select_follow_up_target(
    user_request: str,
    candidate_actions: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any] | None, str]:
    """Resolve a short action follow-up only when its target is unambiguous.

    Returns ``(target, reason)`` where reason is resolved, ambiguous, or none.
    Raw commands and prior user prompts are deliberately excluded from matching.
    """
    kind = classify_chat_action_follow_up(user_request)
    if not kind:
        return None, "none"
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidate_actions:
        target = resolve_follow_up_target(candidate)
        action_id = str((target or {}).get("id") or "")
        if not target or not action_id or action_id in seen or not _follow_up_candidate_eligible(kind, target):
            continue
        seen.add(action_id)
        unique.append(target)
    if not unique:
        return None, "none"

    descriptor = _follow_up_descriptor_tokens(user_request)
    if not descriptor:
        return (unique[0], "resolved") if len(unique) == 1 else (None, "ambiguous")

    scored: list[tuple[int, dict[str, Any]]] = []
    for action in unique:
        haystack = _action_match_tokens(action)
        score = len(descriptor.intersection(haystack))
        if score:
            scored.append((score, action))
    if not scored:
        return None, "none"
    top_score = max(score for score, _action in scored)
    top = [action for score, action in scored if score == top_score]
    return (top[0], "resolved") if len(top) == 1 else (None, "ambiguous")


def propose_ambiguous_chat_action_follow_up(
    user_request: str,
    kind: str,
    candidate_actions: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    save: bool = True,
    deduplication_key: str = "",
    conversation_session_id: str = "",
) -> dict[str, Any]:
    titles: list[str] = []
    for candidate in candidate_actions:
        target = resolve_follow_up_target(candidate)
        title = _redacted_text((target or {}).get("title"), 80)
        if title and title not in titles:
            titles.append(title)
        if len(titles) >= 3:
            break
    hint = "; ".join(titles)
    action = _make_action(
        user_request=user_request,
        intent="action_follow_up_ambiguous",
        title="Action follow-up needs a specific target",
        summary=(
            f"More than one recent supervised action could match this {kind} request. Name the action explicitly. Recent choices: {hint}."
            if hint else
            f"More than one recent supervised action could match this {kind} request. Name the action explicitly."
        ),
        execution_mode=BLOCKED,
        risk_level="low",
        blocked_reason="Ambiguous action references never authorize execution, retry, cancellation, or approval handling.",
        explanation="The control portal refused to guess which persisted action the user meant.",
        control_kind=kind,
    )
    action["ambiguity_count"] = max(2, len(candidate_actions))
    dedupe_key = str(deduplication_key or "").strip()[:120]
    if dedupe_key:
        action["deduplication_key"] = dedupe_key
    if conversation_session_id:
        action["conversation_session_id"] = str(conversation_session_id or "")[:120]
    if save:
        lock_key = f"dedupe:{dedupe_key}" if dedupe_key else f"action:{action['id']}"
        with _chat_action_storage_lock(lock_key):
            if dedupe_key:
                existing = next((item for item in list_chat_actions(include_closed=True) if item.get("deduplication_key") == dedupe_key), None)
                if existing:
                    return existing
            save_chat_action(action)
            store_memory({
                "type": "chat_action_follow_up_ambiguous",
                "content": f"Refused ambiguous redacted action follow-up {action['id']}. Kind: {kind}.",
                "source": "chat_action_router",
                "chat_action_id": action["id"],
                "conversation_operation_id": dedupe_key,
                "use_in_conversation": False,
            }, vectorize=False)
    return action


def resolve_follow_up_target(action: dict[str, Any] | None) -> dict[str, Any] | None:
    """Collapse bounded status/control cards back to their governed target action."""
    current = action if isinstance(action, dict) else None
    seen: set[str] = set()
    for _ in range(4):
        if not current:
            return None
        action_id = str(current.get("id") or "")
        if not action_id or action_id in seen:
            return current
        seen.add(action_id)
        target_id = str(current.get("target_action_id") or "").strip()
        if not target_id:
            return current
        current = load_chat_action(target_id)
    return current


def propose_chat_action_follow_up(
    user_request: str,
    target_action: dict[str, Any] | None,
    *,
    save: bool = True,
    deduplication_key: str = "",
    conversation_session_id: str = "",
) -> dict[str, Any] | None:
    """Create one bounded action-thread control card from an exact short follow-up."""
    kind = classify_chat_action_follow_up(user_request)
    target = resolve_follow_up_target(target_action)
    if not kind or not target or not target.get("id"):
        return None
    dedupe_key = str(deduplication_key or "").strip()[:120]
    if save and dedupe_key:
        with _CHAT_ACTION_LOCK:
            existing = next((item for item in list_chat_actions(include_closed=True) if item.get("deduplication_key") == dedupe_key), None)
        if existing:
            return existing

    from conversation_action_portal import build_action_portal_state

    portal = build_action_portal_state(target, target.get("result") if isinstance(target.get("result"), dict) else None) or {}
    target_id = str(target.get("id") or "")
    target_title = str(portal.get("title") or target.get("title") or "supervised action")
    target_status = str(portal.get("status") or target.get("status") or "proposed")
    status_label = str(portal.get("status_label") or target_status)
    message = str(portal.get("message") or portal.get("summary") or "Persisted action evidence is available.")

    if kind == "status":
        action = _make_action(
            user_request=user_request,
            intent="action_follow_up_status",
            title=f"Status of {target_title}",
            summary=f"Persisted status: {status_label}. {message}",
            execution_mode=INFO,
            risk_level="low",
            explanation="This status is reconstructed from persisted governed evidence. It does not execute or retry the target action.",
            target_action_id=target_id,
            control_kind=kind,
        )
    elif kind == "retry":
        retry_allowed = bool(
            target_status in {"failed", "timed_out", "interrupted"}
            and target.get("execution_mode") == DIRECT_COMMAND
            and target.get("risk_level") == "low"
        )
        action = _make_action(
            user_request=user_request,
            intent="action_follow_up_retry" if retry_allowed else "action_follow_up_retry_blocked",
            title=f"Retry {target_title}" if retry_allowed else f"Retry unavailable for {target_title}",
            summary=(
                "Retry the exact failed, timed-out, or interrupted low-risk action once while preserving every earlier attempt record."
                if retry_allowed
                else f"The persisted action is {status_label.lower()}, so a safe retry is not currently permitted."
            ),
            execution_mode=ACTION_RETRY if retry_allowed else BLOCKED,
            risk_level="low" if retry_allowed else "medium",
            blocked_reason="Only failed, timed-out, or interrupted low-risk direct commands can be retried from conversation." if not retry_allowed else "",
            explanation="The retry is linked to the original action and cannot duplicate a running or completed execution.",
            target_action_id=target_id,
            control_kind=kind,
        )
    elif kind == "cancel":
        cancellable = str(target.get("status") or "") in {"proposed", "approval_required"}
        action = _make_action(
            user_request=user_request,
            intent="action_follow_up_cancel" if cancellable else "action_follow_up_cancel_blocked",
            title=f"Hold {target_title}" if cancellable else f"Cannot cancel {target_title}",
            summary=(
                "Cancel the still-pending action before execution. No command or approval will be performed."
                if cancellable
                else f"The persisted action is {status_label.lower()}; conversation control will not pretend it can stop or erase work already running or terminal."
            ),
            execution_mode=ACTION_CANCEL if cancellable else BLOCKED,
            risk_level="low" if cancellable else "medium",
            blocked_reason="Only a still-pending proposal can be cancelled safely through this control." if not cancellable else "",
            explanation="Cancellation is an atomic state transition on the exact pending action, not a shell or provider operation.",
            target_action_id=target_id,
            control_kind=kind,
        )
    else:
        action = _make_action(
            user_request=user_request,
            intent="action_follow_up_approval_review",
            title=f"Approval review for {target_title}",
            summary=(
                "The linked action has an operator-controlled approval item. Review it through the approval inbox or its visible card."
                if portal.get("approval_id") or target_status == "awaiting_approval"
                else "The linked action does not currently have a persisted approval item to approve."
            ),
            execution_mode=INFO,
            risk_level="low",
            explanation="Conversational follow-up never grants approval or performs the protected action automatically.",
            target_action_id=target_id,
            control_kind=kind,
        )

    if dedupe_key:
        action["deduplication_key"] = dedupe_key
    if conversation_session_id:
        action["conversation_session_id"] = str(conversation_session_id or "")[:120]
    if save:
        lock_key = f"dedupe:{dedupe_key}" if dedupe_key else f"action:{action['id']}"
        with _chat_action_storage_lock(lock_key):
            if dedupe_key:
                existing = next((item for item in list_chat_actions(include_closed=True) if item.get("deduplication_key") == dedupe_key), None)
                if existing:
                    return existing
            save_chat_action(action)
            store_memory({
                "type": "chat_action_follow_up",
                "content": f"Created redacted action follow-up {action['id']} for target {target_id}. Kind: {kind}.",
                "source": "chat_action_router",
                "chat_action_id": action["id"],
                "target_chat_action_id": target_id,
                "conversation_operation_id": dedupe_key,
                "use_in_conversation": False,
            }, vectorize=False)
    return action


def propose_chat_action(
    user_request: str,
    save: bool = True,
    *,
    save_unknown: bool = True,
    deduplication_key: str = "",
    conversation_session_id: str = "",
) -> dict[str, Any]:
    request = _normalize_request(user_request)
    lowered = request.lower()
    quality = classify_conversation_quality(request)
    dedupe_key = str(deduplication_key or "").strip()[:120]
    if save and dedupe_key:
        with _CHAT_ACTION_LOCK:
            existing = next((item for item in list_chat_actions(include_closed=True) if item.get("deduplication_key") == dedupe_key), None)
        if existing:
            return existing

    try:
        from conversational_research_actions import parse_conversational_research_request
    except ImportError:
        from conversational_research_actions import parse_conversational_research_request

    research_request = parse_conversational_research_request(request)

    if not request:
        action = _make_action(
            user_request=user_request,
            intent="empty_request",
            title="Empty request",
            summary="No request was provided.",
            execution_mode=BLOCKED,
            risk_level="low",
            blocked_reason="Empty request.",
        )
        if save:
            save_chat_action(action)
        return action

    if research_request:
        research_intent = str(research_request.get("intent") or "")
        research_blocked = bool(research_request.get("blocked"))
        research_titles = {
            "bounded_research_create": "Prepare bounded public-web research",
            "bounded_research_authorize_execute": "Run authorized bounded public-web research",
            "bounded_research_cancel": "Cancel bounded public-web research",
            "bounded_research_status": "Inspect bounded research status",
            "bounded_research_history": "Inspect bounded research history",
            "bounded_research_compare": "Compare bounded research evidence",
            "bounded_research_export": "Export bounded cited research report",
        }
        research_summaries = {
            "bounded_research_create": "Prepare one private, budgeted research session without contacting the web.",
            "bounded_research_authorize_execute": "Authorize and execute the exact GET/HEAD-only research session once without per-page approvals.",
            "bounded_research_cancel": "Cancel the exact non-terminal research session without starting another source request.",
            "bounded_research_status": "Inspect content-minimized research progress and evidence counters without contacting the web.",
            "bounded_research_history": "Inspect digest-bound terminal research history without contacting the web or exposing private research state.",
            "bounded_research_compare": "Compare two exact completed research sessions by content-free evidence structure without contacting the web or declaring a winner.",
            "bounded_research_export": "Export one exact completed digest-bound report to local Markdown without uploading, transmitting, or exposing private runtime state.",
        }
        action = _make_action(
            user_request=request,
            intent=research_intent,
            title=research_titles.get(research_intent, "Bounded public-web research"),
            summary=research_summaries.get(research_intent, "Use the supervised bounded research lifecycle."),
            execution_mode=BLOCKED if research_blocked else DIRECT_FUNCTION,
            risk_level="high" if research_blocked else "low",
            function_name=str(research_request.get("function_name") or ""),
            function_args=dict(research_request.get("function_args") or {}),
            blocked_reason="Research chat controls cannot post, publish, upload, message, purchase, authenticate, or create accounts." if research_blocked else "",
            explanation="Research remains session-bounded, public-network-only, GET/HEAD-only, content-minimized, and exactly-once. It grants no standing web or write authority.",
        )
    elif _is_small_talk_only(request):
        action = _make_action(
            user_request=request,
            intent="small_talk",
            title="Conversation only",
            summary="This message is conversational and does not request a project action.",
            execution_mode=INFO,
            risk_level="low",
            explanation="No command, approval, patch, release, memory mutation, or autonomy action is needed for this greeting.",
        )
    # Narrow self-development patch application approval. This prepares a preimage/application receipt only; it does not publish, release, or expand autonomy.
    elif _is_self_development_patch_application_approval_request(request):
        action = _direct_command(
            request,
            "operator_approved_self_development_patch_application_trial",
            "Prepare Self Development patch application trial receipt",
            "Validate the exact patch application approval phrase, capture preimage hashes, enforce the low-risk file allowlist, and stop when no concrete diff exists.",
            _self_development_patch_application_command(request),
            risk="low",
        )
    # Narrow self-development patch draft approval. This prepares a review packet only; it does not apply a patch.
    elif _is_self_development_patch_draft_approval_request(request):
        action = _direct_command(
            request,
            "operator_approved_self_development_patch_draft",
            "Prepare Self Development patch draft packet",
            "Prepare a review-only patch draft packet for the explicitly named low-risk Self Development task; no source edits are applied.",
            _self_development_patch_draft_command(request),
            risk="low",
        )
    # Approval-gated writes.
    elif re.search(r"\b(apply|approve|install)\b.*\bpatch\b", lowered) or re.search(r"\bapply\b.*\blatest\b", lowered):
        action = _make_action(
            user_request=request,
            intent="request_apply_patch",
            title="Request approval to apply latest proposed patch",
            summary="Applying a patch writes to a project file, so this becomes an approval request.",
            execution_mode=APPROVAL,
            risk_level="medium",
            approval_action_type="apply_patch",
            approval_object_id="latest-proposed",
            approval_command="python conscious_agent/main.py --apply-patch latest-proposed",
            explanation="File edits require approval. Executing this chat action creates an approval inbox item; it does not apply the patch directly.",
        )
    elif re.search(r"\b(rollback|undo|revert)\b.*\b(patch|latest|change)\b", lowered):
        action = _make_action(
            user_request=request,
            intent="request_rollback_patch",
            title="Request approval to rollback latest applied patch",
            summary="Rolling back writes to a project file, so this becomes an approval request.",
            execution_mode=APPROVAL,
            risk_level="medium",
            approval_action_type="rollback_patch",
            approval_object_id="latest-applied",
            approval_command="python conscious_agent/main.py --rollback-patch latest-applied",
            explanation="Rollback changes files and requires explicit approval.",
        )
    elif "apply task evaluation" in lowered or "apply evaluation" in lowered:
        action = _make_action(
            user_request=request,
            intent="request_apply_task_evaluation",
            title="Request approval to apply latest task evaluation",
            summary="Applying a task evaluation may change task status, so this becomes an approval request.",
            execution_mode=APPROVAL,
            risk_level="low",
            approval_action_type="apply_task_evaluation",
            approval_object_id="latest",
            approval_command="python conscious_agent/main.py --apply-task-evaluation latest",
            explanation="Task status changes are routed through the approval system from chat actions.",
        )
    elif _is_self_development_cycle_request(lowered):
        action = _direct_command(
            request,
            "self_development_cycle",
            "Begin Self Development Cycle",
            "Run a dedicated proposal-only self-development cycle that inspects, ranks at least three candidates, creates one safe work item, defines verification, and stops before source edits.",
            "python conscious_agent/main.py --self-development-cycle --self-development-create-task --no-ai-self-development --self-development-prompt " + _quote_cli_value(request),
            risk="low",
        )
    elif re.search(r"\b(?:install|delete|remove|download|pull|switch|change|replace|select)\b[^\n]{0,100}\b(?:model|provider)\b", lowered):
        action = _make_action(
            user_request=request,
            intent="blocked_model_provider_management",
            title="Model or provider management is not available through chat",
            summary="Chat cannot install, remove, select, replace, or silently switch models or providers.",
            execution_mode=BLOCKED,
            risk_level="high",
            blocked_reason="Model and provider management remains an explicit operator-controlled settings or installation workflow.",
            explanation="No model or provider state was changed. Use the existing operator-controlled configuration workflow outside conversational action execution.",
        )
    elif re.search(r"\b(?:run|execute|open)\s+(?:an?\s+)?(?:shell|terminal|command prompt|powershell|cmd)(?:\s+command)?\b", lowered):
        action = _make_action(
            user_request=request,
            intent="blocked_unrestricted_shell",
            title="Unrestricted shell access is blocked",
            summary="Chat can use only registered allowlisted supervised actions, not arbitrary terminal commands.",
            execution_mode=BLOCKED,
            risk_level="high",
            blocked_reason="Arbitrary shell execution is outside the supervised chat-action allowlist.",
            explanation="No command was executed. Use a registered low-risk action or an existing approval-gated workflow.",
        )
    elif __import__("release_self_knowledge").is_grouped_release_inspection(request):
        action = _make_action(
            user_request=request,
            intent="release_summary",
            title="Inspect current release evidence",
            summary="Read the allowlisted release authority and README files and report only verified current-release facts.",
            execution_mode=DIRECT_FUNCTION,
            risk_level="low",
            function_name="release_summary",
            explanation="This provider-free inspection reads four allowlisted source files, changes nothing, and grants no release authority.",
        )
    elif not quality.should_analyze_action and not _is_any_experiment_review_request(request) and not is_review_confirmation(request):
        action = _make_action(
            user_request=request,
            intent="conversation_only",
            title="Conversation only",
            summary="This message belongs to the current conversation and does not contain an explicit operator action request.",
            execution_mode=INFO,
            risk_level="low",
            explanation="No command, approval, patch, provider change, model operation, release action, memory mutation, or autonomous workflow is implied.",
        )
    elif "compact memory" in lowered or "compress memory" in lowered:
        action = _make_action(
            user_request=request,
            intent="manual_memory_compaction",
            title="Memory compaction requires manual command",
            summary="Memory compaction archives and rewrites memory files. Use the existing dry-run/explicit command flow.",
            execution_mode=BLOCKED,
            risk_level="medium",
            blocked_reason="Chat-to-action does not execute memory compaction yet. Run --compact-memory --dry-run first.",
            explanation="This is blocked from chat actions because it rewrites memory files.",
        )
    # Patch suggestion: safe proposal creation, no file edit.
    elif any(term in lowered for term in ["suggest patch", "suggest improvement", "improve ", "fix ", "patch "]):
        target_file = _extract_file_path(request)
        if target_file:
            patch_request = request
            action = _make_action(
                user_request=request,
                intent="suggest_patch",
                title=f"Suggest patch for {target_file}",
                summary="Create a saved patch proposal using the local model. This does not edit files.",
                execution_mode=DIRECT_FUNCTION,
                risk_level="low",
                function_name="suggest_patch",
                function_args={"target_file": target_file, "request": patch_request},
                explanation="Patch suggestions create proposal JSON and a diff only. Applying still requires approval.",
            )
        else:
            action = _make_action(
                user_request=request,
                intent="suggest_patch_missing_file",
                title="Patch suggestion needs a file path",
                summary="I understood this as a patch/improvement request, but no target file was found.",
                execution_mode=BLOCKED,
                risk_level="low",
                blocked_reason="No target file path found. Try: suggest improvement for conscious_agent/memory.py ...",
            )
    # Independent experiment review: selection and invocation of the already-authorized read-only capability.
    elif is_review_confirmation(request):
        pending = pending_review_action() or {}
        pending_id = str(pending.get("id") or "")
        pending_package = str((pending.get("function_args") or {}).get("package_id") or "the proposed package")
        action = _make_action(
            user_request=request,
            intent="experiment_review_confirm",
            title=f"Confirmed review of {pending_package}",
            summary=(f"The review of {pending_package} is saved as action {pending_id} and is waiting to run. "
                     f"Nothing has started yet: open Chat Actions and press Execute to run it."),
            execution_mode=INFO,
            risk_level="low",
            target_action_id=pending_id,
            explanation="Conversation confirms the saved proposal and never runs it. Execution stays on the operator-controlled action surface.",
        )
    elif _is_experiment_review_list_request(lowered):
        from conversational_experiment_review import list_message
        action = _make_action(
            user_request=request,
            intent="experiment_review_list",
            title="Experiment packages I can review",
            summary=list_message(),
            execution_mode=INFO,
            risk_level="low",
            explanation="Reading the installed package listing only. No review runs, and nothing is chosen for you.",
        )
    elif _is_experiment_review_status_request(lowered):
        from conversational_experiment_review import execute_conversational_review_action
        status = execute_conversational_review_action("experiment_review_status", {})
        action = _make_action(
            user_request=request,
            intent="experiment_review_status",
            title="Experiment review status",
            summary=str(status.get("message") or "No review job has been started yet."),
            execution_mode=INFO,
            risk_level="low",
            explanation="Reading the job record only. A review's conclusions stay in its artifact; they are not adopted here.",
        )
    elif _experiment_review_target(request):
        from conversational_experiment_review import propose_message
        package, message = propose_message(_experiment_review_target(request))
        if package is None:
            action = _make_action(
                user_request=request,
                intent="experiment_review_unavailable",
                title="No eligible experiment package",
                summary=message,
                execution_mode=BLOCKED,
                risk_level="low",
                blocked_reason=message,
            )
        else:
            action = _make_action(
                user_request=request,
                intent="experiment_review_start",
                title=f"Review {package['package_id']} independently",
                summary=message,
                execution_mode=DIRECT_FUNCTION,
                risk_level="medium",
                function_name="experiment_review_start",
                function_args={"package_id": package["package_id"]},
                explanation="Confirming runs the frozen read-only reviewer once on this installed package, as a background job. "
                            "The result is a non-authoritative artifact; no source, gold, belief, memory, policy, configuration or release changes.",
            )
    # Read-only / safe commands.
    elif is_supervised_capability_catalog_request(request):
        action = _make_action(
            user_request=request,
            intent="supervised_capabilities",
            title="Current supervised capabilities",
            summary=supervised_capability_summary(),
            execution_mode=INFO,
            risk_level="low",
            explanation="Low-risk allowlisted reads may execute once after the visible reply. Modifications and higher-risk work remain proposals or approval actions. Unrestricted shell access, model management, provider switching, and release promotion are not registered chat capabilities.",
        )
    elif any(phrase in lowered for phrase in ["diagnostic", "system health", "health check", "system check", "is everything working", "how is your system", "how are your systems"]):
        action = _direct_command(request, "run_diagnostics", "Run diagnostics", "Run a diagnostics report.", "python conscious_agent/main.py --diagnostics")
    elif any(phrase in lowered for phrase in ["settings health", "model health", "configuration health", "are your settings okay", "how are your settings", "ollama health"]):
        action = _direct_command(request, "settings_health", "Check settings/model health", "Check configured settings and Ollama model availability.", "python conscious_agent/main.py --settings-health")
    elif any(phrase in lowered for phrase in [
        "attention center", "what needs my attention", "what needs attention", "anything need attention",
        "anything needs attention", "show me what needs attention", "what is waiting for me",
        "what's waiting for me", "catch me up on what needs attention", "operator attention",
    ]):
        action = _direct_command(
            request,
            "attention_center",
            "Show attention center",
            "Show one read-only redacted view of conversation updates, action results, approvals, tasks, projects, and notifications.",
            "python conscious_agent/main.py --attention-center",
        )
    elif any(phrase in lowered for phrase in ["watch check", "run watch", "check watch", "anything wrong", "run a watch"]):
        action = _direct_command(request, "watch_once", "Run watch check", "Run a no-AI watch check and save a watch report.", "python conscious_agent/main.py --watch-once --no-ai-watch")
    elif any(phrase in lowered for phrase in ["approval", "permission", "waiting for review", "waiting for approval"]):
        action = _direct_command(request, "approval_inbox", "Show approval inbox", "Show pending approval requests.", "python conscious_agent/main.py --approval-inbox")
    elif any(phrase in lowered for phrase in ["notification", "alert", "anything to notify", "messages for me"]):
        action = _direct_command(request, "notifications", "Show notifications", "Show unread notifications.", "python conscious_agent/main.py --notifications")
    elif "plan" in lowered or "what next" in lowered or "next step" in lowered or "next session" in lowered:
        action = _direct_command(request, "plan_session", "Plan next session", "Create a no-AI session plan.", "python conscious_agent/main.py --plan-session --no-ai-session")
    elif any(phrase in lowered for phrase in ["maintenance", "maintainence", "maintenance scan", "maintainence scan", "need maintenance", "needs maintenance"]):
        action = _direct_command(request, "maintenance_scan", "Run maintenance scan", "Create a no-AI maintenance scan.", "python conscious_agent/main.py --maintenance-scan --no-ai-maintenance")
    elif "dev loop" in lowered or "autonomous" in lowered or "continue development" in lowered:
        action = _direct_command(request, "dev_loop_dry_run", "Dry-run dev loop", "Run a safe no-AI dev-loop dry run.", "python conscious_agent/main.py --dev-loop --dry-run --no-ai-dev-loop")
    elif "task status" in lowered or "task queue" in lowered or "where are we on the tasks" in lowered or (("show" in lowered or "check" in lowered) and "tasks" in lowered and "next" not in lowered):
        action = _direct_command(request, "task_status", "Show task status", "Show task queue status.", "python conscious_agent/main.py --task-status")
    elif "next task" in lowered or "current task" in lowered:
        action = _direct_command(request, "next_task", "Show next task", "Show the highest-priority ready task.", "python conscious_agent/main.py --next-task")
    elif "latest patch" in lowered or "show patch" in lowered:
        action = _direct_command(request, "show_latest_patch", "Show latest patch", "Show the latest patch proposal.", "python conscious_agent/main.py --show-patch latest")
    elif "latest ids" in lowered or "ids" in lowered:
        action = _direct_command(request, "latest_ids", "Show latest IDs", "Show latest alias targets.", "python conscious_agent/main.py --latest-ids")
    elif "review" in lowered and _extract_file_path(request):
        target_file = _extract_file_path(request)
        action = _direct_command(
            request,
            "review_file",
            f"Review {target_file}",
            f"Run a static code review for {target_file}.",
            f"python conscious_agent/main.py --review-project-file {target_file} --no-ai-review",
        )
    elif any(phrase in lowered for phrase in ["project status", "active project", "where are we on the project", "how is the project"]):
        action = _direct_command(request, "project_status", "Show project status", "Show active project status.", "python conscious_agent/main.py --project-status")
    elif any(phrase in lowered for phrase in ["memory status", "how is your memory", "check your memory", "show memory"]):
        action = _direct_command(request, "memory_status", "Show memory status", "Show memory size and compaction status.", "python conscious_agent/main.py --memory-status")
    elif "dashboard" in lowered:
        action = _make_action(
            user_request=request,
            intent="start_dashboard_manual",
            title="Start dashboard manually",
            summary="The dashboard is a long-running server. Start it manually from the terminal.",
            execution_mode=INFO,
            risk_level="low",
            command="python conscious_agent/main.py --dashboard",
            explanation="Chat-to-action does not start long-running servers. Run the command manually.",
        )
    else:
        action = _make_action(
            user_request=request,
            intent="unknown_request",
            title="No safe action matched",
            summary="I could not map this request to a known safe Eidolon action.",
            execution_mode=BLOCKED,
            risk_level="unknown",
            blocked_reason="Unknown or unsupported chat action request.",
            explanation="Try phrasing it as: run diagnostics, check approvals, plan session, run watch, review conscious_agent/memory.py, or suggest improvement for conscious_agent/memory.py.",
        )

    persistable_intent = action.get("intent") not in {"small_talk", "conversation_only"}
    if dedupe_key:
        action["deduplication_key"] = dedupe_key
    if conversation_session_id:
        action["conversation_session_id"] = str(conversation_session_id or "")[:120]
    if save and persistable_intent and (save_unknown or action.get("intent") != "unknown_request"):
        lock_key = f"dedupe:{dedupe_key}" if dedupe_key else f"action:{action['id']}"
        with _chat_action_storage_lock(lock_key):
            if dedupe_key:
                existing = next((item for item in list_chat_actions(include_closed=True) if item.get("deduplication_key") == dedupe_key), None)
                if existing:
                    return existing
            save_chat_action(action)
            store_memory({
                "type": "chat_action_proposed",
                "content": f"Created chat action {action['id']} for request: {request}. Intent: {action.get('intent')}. Mode: {action.get('execution_mode')}.",
                "source": "chat_action_router",
                "chat_action_id": action["id"],
                "conversation_operation_id": dedupe_key,
                "use_in_conversation": False,
                "intent": action.get("intent"),
                "execution_mode": action.get("execution_mode"),
            }, vectorize=False)
    return action


def _save_dry_run_result(action_id: str, result_data: dict[str, Any]) -> dict[str, Any]:
    with _chat_action_storage_lock(f"action:{action_id}"):
        current = load_chat_action(action_id) or {}
        if not current:
            return {}
        current["updated_at"] = _now()
        current["last_dry_run_result"] = dict(result_data)
        _append_action_event(
            current,
            "dry_run_completed",
            str(current.get("status") or "proposed"),
            "A bounded dry run completed without claiming live execution.",
        )
        save_chat_action(current)
        return current


def _claim_execution_attempt(
    action: dict[str, Any], *, claimant: str = "process", lease_seconds: float | None = None,
) -> dict[str, Any]:
    attempts = [dict(item) for item in action.get("execution_attempts", []) if isinstance(item, dict)]
    attempt_number = max(0, int(action.get("execution_attempt") or 0)) + 1
    previous_attempt_id = str(attempts[-1].get("attempt_id") or "") if attempts else ""
    attempt_id = f"{action.get('id')}:attempt:{attempt_number}"
    scope = _normalize_claimant(claimant)
    claimed_at = _now()
    claimed_epoch = time.time()
    duration = max(5.0, min(_CHAT_ACTION_MAX_CLAIM_LEASE_SECONDS, float(lease_seconds or _CHAT_ACTION_CLAIM_LEASE_SECONDS)))
    claim_token = uuid.uuid4().hex + uuid.uuid4().hex
    claim_owner = {
        "scope": scope,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "claimed_at": claimed_at,
        "claimed_epoch": claimed_epoch,
        "heartbeat_at": claimed_at,
        "lease_expires_at": datetime.fromtimestamp(claimed_epoch + duration).isoformat(timespec="seconds"),
        "lease_expires_epoch": claimed_epoch + duration,
        "lease_seconds": duration,
        "claim_token": claim_token,
        "claim_generation": attempt_number,
        "attempt_id": attempt_id,
        "recovery_after_seconds": duration,
    }
    attempts.append({
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "status": "running",
        "started_at": claimed_at,
        "completed_at": "",
        "retry_of_attempt_id": previous_attempt_id,
        "claimant_scope": scope,
        "claim_generation": attempt_number,
        "claim_token_digest": hashlib.sha256(claim_token.encode("utf-8")).hexdigest(),
        "result": {},
    })
    action["status"] = "running"
    action["execution_started_at"] = attempts[-1]["started_at"]
    action["execution_attempt"] = attempt_number
    action["active_attempt_id"] = attempt_id
    action["execution_attempts"] = attempts
    action["claim_owner"] = claim_owner
    action["result_summary"] = _redacted_result_summary(action, "running", {})
    action["result_summary_status"] = "running"
    _append_action_event(
        action,
        "execution_claimed",
        "running",
        action["result_summary"],
        attempt_number=attempt_number,
        owner_scope=scope,
    )
    _append_action_event(
        action,
        "retry_started" if previous_attempt_id else "attempt_started",
        "running",
        (
            f"Linked retry attempt {attempt_number} started through {_claimant_label(scope)}."
            if previous_attempt_id
            else f"Execution attempt {attempt_number} started through {_claimant_label(scope)}."
        ),
        attempt_number=attempt_number,
        owner_scope=scope,
    )
    action["updated_at"] = _now()
    save_chat_action(action)
    return action


def renew_chat_action_claim(
    action_id: str,
    claim_token: str,
    *,
    claimant: str = "process",
    lease_seconds: float | None = None,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    """Renew only the exact active claim; stale owners cannot extend a newer attempt."""
    token = str(claim_token or "").strip()
    if not token:
        return {"ok": False, "status": "claim_token_required", "redacted": True}
    with _chat_action_storage_lock(f"action:{action_id}"):
        current = load_chat_action(action_id) or {}
        owner = current.get("claim_owner") if isinstance(current.get("claim_owner"), dict) else {}
        owner_token = str(owner.get("claim_token") or "")
        if str(current.get("status") or "") != "running" or not owner_token or not hmac.compare_digest(owner_token, token):
            return {
                "ok": False,
                "status": "stale_claim",
                "action_id": str(current.get("id") or action_id),
                "execution_attempt": max(0, int(current.get("execution_attempt") or 0)),
                "redacted": True,
            }
        scope = _normalize_claimant(claimant)
        if str(owner.get("scope") or "") != scope:
            return {"ok": False, "status": "claimant_mismatch", "action_id": str(current.get("id") or action_id), "redacted": True}
        now = time.time() if now_epoch is None else float(now_epoch)
        duration = max(5.0, min(_CHAT_ACTION_MAX_CLAIM_LEASE_SECONDS, float(lease_seconds or owner.get("lease_seconds") or _CHAT_ACTION_CLAIM_LEASE_SECONDS)))
        owner["heartbeat_at"] = datetime.fromtimestamp(now).isoformat(timespec="seconds")
        owner["lease_expires_at"] = datetime.fromtimestamp(now + duration).isoformat(timespec="seconds")
        owner["lease_expires_epoch"] = now + duration
        owner["lease_seconds"] = duration
        current["claim_owner"] = owner
        current["updated_at"] = _now()
        save_chat_action(current)
        return {
            "ok": True,
            "status": "claim_renewed",
            "action_id": str(current.get("id") or action_id),
            "execution_attempt": max(0, int(current.get("execution_attempt") or 0)),
            "lease_expires_at": str(owner.get("lease_expires_at") or ""),
            "redacted": True,
        }

def _complete_execution_attempt(
    action_id: str,
    *,
    status: str,
    result_data: dict[str, Any],
    extra_updates: dict[str, Any] | None = None,
    expected_claim_token: str = "",
) -> dict[str, Any]:
    with _chat_action_storage_lock(f"action:{action_id}"):
        current = load_chat_action(action_id) or {"id": action_id}
        attempts = [dict(item) for item in current.get("execution_attempts", []) if isinstance(item, dict)]
        active_id = str(current.get("active_attempt_id") or "")
        owner = dict(current.get("claim_owner") or {}) if isinstance(current.get("claim_owner"), dict) else {}
        expected = str(expected_claim_token or "").strip()
        active_token = str(owner.get("claim_token") or "")
        if expected and (not active_token or not hmac.compare_digest(active_token, expected)):
            stale = dict(current)
            stale["stale_completion_ignored"] = True
            stale["claim_conflict"] = True
            stale["redacted"] = True
            return stale
        summary = _redacted_result_summary(current, status, result_data)
        for attempt in reversed(attempts):
            if active_id and str(attempt.get("attempt_id") or "") != active_id:
                continue
            if str(attempt.get("status") or "") == "running":
                attempt["status"] = status
                attempt["completed_at"] = _now()
                attempt["result"] = _redacted_attempt_result(status, result_data, summary)
                break
        current["execution_attempts"] = attempts
        current["active_attempt_id"] = ""
        current["status"] = status
        current["updated_at"] = _now()
        current["result"] = dict(result_data)
        current["result_summary"] = summary
        current["result_summary_status"] = status
        last_owner = {key: value for key, value in owner.items() if key != "claim_token"}
        current["last_claim_owner"] = last_owner
        current["claim_owner"] = {}
        event_type = {
            "executed": "execution_completed",
            "completed": "execution_completed",
            "approval_created": "approval_requested",
            "timed_out": "execution_timed_out",
            "interrupted": "execution_interrupted",
            "cancelled": "action_cancelled",
            "blocked": "action_blocked",
        }.get(str(status), "execution_failed")
        _append_action_event(
            current,
            event_type,
            status,
            summary,
            attempt_number=max(0, int(current.get("execution_attempt") or 0)),
            owner_scope=str(owner.get("scope") or ""),
        )
        if extra_updates:
            current.update(dict(extra_updates))
        save_chat_action(current)
        return current


def _mark_running_action_interrupted(action: dict[str, Any], reason: str) -> dict[str, Any]:
    action_id = str(action.get("id") or "")
    result_data = {
        "ok": False,
        "error": "Execution owner ended before a terminal result was persisted.",
        "interrupted": True,
        "redacted": True,
    }
    return _complete_execution_attempt(
        action_id,
        status="interrupted",
        result_data=result_data,
        extra_updates={"interruption_reason": _redacted_text(reason, 280)},
        expected_claim_token=str((action.get("claim_owner") or {}).get("claim_token") or ""),
    )


def cancel_pending_chat_action(chat_action_id: str) -> ChatActionExecutionResult:
    """Cancel exactly one still-pending governed action; never fake running cancellation."""
    resolved_id = resolve_chat_action_id(chat_action_id)
    if not resolved_id:
        return ChatActionExecutionResult(False, chat_action_id, error="Linked action was not found.", status="not_found")
    with _chat_action_storage_lock(f"action:{resolved_id}"):
        target = load_chat_action(resolved_id)
        if not target:
            return ChatActionExecutionResult(False, chat_action_id, error="Linked action was not found.", status="not_found")
        target_id = str(target.get("id") or resolved_id)
        status = str(target.get("status") or "")
        if status in {"proposed", "approval_required"}:
            result_data = {
                "ok": True,
                "message": "The pending action was cancelled before execution.",
                "redacted": True,
            }
            target["status"] = "cancelled"
            target["cancelled_at"] = _now()
            target["updated_at"] = _now()
            target["result"] = result_data
            target["result_summary"] = _redacted_result_summary(target, "cancelled", result_data)
            target["result_summary_status"] = "cancelled"
            _append_action_event(target, "action_cancelled", "cancelled", target["result_summary"])
            save_chat_action(target)
            return ChatActionExecutionResult(True, target_id, message=result_data["message"], status="cancelled", result=result_data)
        if status == "running":
            return ChatActionExecutionResult(
                False,
                target_id,
                message="The action is already running. This control cannot safely claim that the underlying command was cancelled.",
                status="running",
                result=target.get("result") or {},
                replayed=True,
            )
        return _persisted_execution_replay(target)


def _mark_claimed_action_failed(action_id: str, error: Exception | str, *, claim_token: str = "") -> ChatActionExecutionResult:
    message = f"Action failed safely: {type(error).__name__}" if isinstance(error, Exception) else str(error)
    result_data = {"ok": False, "error": message, "redacted": True}
    _complete_execution_attempt(action_id, status="failed", result_data=result_data, expected_claim_token=claim_token)
    return ChatActionExecutionResult(False, action_id, message=message, status="failed", result=result_data, error=message)


def _persisted_execution_replay(
    action: dict[str, Any],
    *,
    dry_run: bool = False,
    claimant: str = "process",
) -> ChatActionExecutionResult:
    result = action.get("result") if isinstance(action.get("result"), dict) else {}
    status = str(action.get("status") or "")
    ok = status in {"executed", "completed", "approval_created"} or bool(result.get("ok"))
    message = str(action.get("result_summary") or result.get("message") or result.get("error") or action.get("explanation") or f"Action is {status}.")
    owner = action.get("claim_owner") if isinstance(action.get("claim_owner"), dict) else {}
    owner_scope = str(owner.get("scope") or "")
    running_elsewhere = bool(status == "running" and owner_scope and _normalize_claimant(owner_scope) != _normalize_claimant(claimant))
    if status == "running" and owner_scope:
        message = f"This exact action is already running through {_claimant_label(owner_scope)}; no duplicate execution was started."
    return ChatActionExecutionResult(ok, str(action.get("id") or ""), message=message, status=status, result=result, dry_run=dry_run, replayed=True)


def execute_chat_action(
    chat_action_id: str = "latest",
    dry_run: bool = False,
    timeout_seconds: int | None = None,
    *,
    retry: bool = False,
    claimant: str = "process",
) -> ChatActionExecutionResult:
    resolved_id = resolve_chat_action_id(chat_action_id)
    if not resolved_id:
        return ChatActionExecutionResult(False, chat_action_id, error=f"Chat action not found: {chat_action_id}", dry_run=dry_run)

    claim_token = ""
    try:
        with _chat_action_storage_lock(f"action:{resolved_id}"):
            action = load_chat_action(resolved_id)
            if not action:
                return ChatActionExecutionResult(False, chat_action_id, error=f"Chat action not found: {chat_action_id}", dry_run=dry_run)

            action_id = str(action.get("id") or resolved_id)
            mode = action.get("execution_mode")
            status = str(action.get("status") or "")
            if mode not in {DIRECT_COMMAND, DIRECT_FUNCTION, APPROVAL, BLOCKED, INFO, ACTION_RETRY, ACTION_CANCEL}:
                return ChatActionExecutionResult(False, action_id, error=f"Unsupported execution mode: {mode}", status=status, dry_run=dry_run)
            if dry_run and status in {"running", "executed", "completed", "approval_created"}:
                return _persisted_execution_replay(action, dry_run=True, claimant=claimant)
            if not dry_run and status in {"executed", "completed", "approval_created"}:
                return _persisted_execution_replay(action, claimant=claimant)
            if not dry_run and status == "running":
                from conversation_action_portal import running_claim_is_interrupted

                interrupted, reason = running_claim_is_interrupted(
                    action,
                    max_age_seconds=_CHAT_ACTION_INTERRUPTED_CLAIM_SECONDS,
                )
                if interrupted:
                    action = _mark_running_action_interrupted(action, reason)
                    status = "interrupted"
                else:
                    return _persisted_execution_replay(action, claimant=claimant)
            if not dry_run and status in {"failed", "timed_out", "interrupted"}:
                retry_is_allowed = bool(retry and mode == DIRECT_COMMAND and action.get("risk_level") == "low")
                if not retry_is_allowed:
                    return _persisted_execution_replay(action, claimant=claimant)
            if not dry_run and status not in {"proposed", "approval_required", "blocked", "info", "failed", "timed_out", "interrupted"}:
                return ChatActionExecutionResult(False, action_id, error=f"Chat action status is {status}, not executable.", status=status, dry_run=False)
            if not dry_run and mode not in {BLOCKED, INFO}:
                action = _claim_execution_attempt(action, claimant=claimant)
                claim_token = str((action.get("claim_owner") or {}).get("claim_token") or "")
    except TimeoutError:
        current = load_chat_action(resolved_id) or {}
        current_status = str(current.get("status") or "claim_busy")
        return ChatActionExecutionResult(
            False,
            str(current.get("id") or resolved_id),
            message="Action claim ownership is temporarily busy. This process did not start a duplicate execution.",
            status=current_status,
            result=current.get("result") if isinstance(current.get("result"), dict) else {},
            error="Interprocess action claim timed out safely.",
            dry_run=dry_run,
            replayed=True,
        )

    if mode == BLOCKED:
        return ChatActionExecutionResult(False, action_id, error=action.get("blocked_reason") or "This action is blocked.", dry_run=dry_run)

    if mode == INFO:
        return ChatActionExecutionResult(True, action_id, message=action.get("explanation", action.get("summary", "Informational action.")), status="info", result={"command": action.get("command")}, dry_run=dry_run)

    if mode == ACTION_RETRY:
        target_id = str(action.get("target_action_id") or "")
        if dry_run:
            result_data = {
                "ok": True,
                "message": "Dry run passed. The exact linked failed or timed-out low-risk action would be retried once.",
                "target_action_id": target_id,
                "redacted": True,
            }
            current = _save_dry_run_result(action_id, result_data)
            return ChatActionExecutionResult(True, action_id, message=result_data["message"], status=current.get("status", "proposed"), result=result_data, dry_run=True)
        target_result = execute_chat_action(target_id, dry_run=False, timeout_seconds=timeout_seconds, retry=True, claimant=claimant)
        result_data = {
            "ok": bool(target_result.ok),
            "message": str(target_result.message or target_result.error or "Linked retry finished."),
            "target_action_id": target_id,
            "target_status": str(target_result.status or ""),
            "target_replayed": bool(target_result.replayed),
            "redacted": True,
        }
        final_status = "executed" if target_result.ok else ("timed_out" if target_result.status == "timed_out" else "failed")
        current = _complete_execution_attempt(action_id, status=final_status, result_data=result_data, expected_claim_token=claim_token)
        _store_execution_memory(current, result_data)
        return ChatActionExecutionResult(bool(target_result.ok), action_id, message=result_data["message"], status=final_status, result=result_data, error="" if target_result.ok else result_data["message"])

    if mode == ACTION_CANCEL:
        target_id = str(action.get("target_action_id") or "")
        if dry_run:
            result_data = {
                "ok": True,
                "message": "Dry run passed. The exact still-pending linked action would be cancelled before execution.",
                "target_action_id": target_id,
                "redacted": True,
            }
            current = _save_dry_run_result(action_id, result_data)
            return ChatActionExecutionResult(True, action_id, message=result_data["message"], status=current.get("status", "proposed"), result=result_data, dry_run=True)
        target_result = cancel_pending_chat_action(target_id)
        result_data = {
            "ok": bool(target_result.ok),
            "message": str(target_result.message or target_result.error or "Linked cancellation finished."),
            "target_action_id": target_id,
            "target_status": str(target_result.status or ""),
            "redacted": True,
        }
        final_status = "executed" if target_result.ok else "failed"
        current = _complete_execution_attempt(action_id, status=final_status, result_data=result_data, expected_claim_token=claim_token)
        _store_execution_memory(current, result_data)
        return ChatActionExecutionResult(bool(target_result.ok), action_id, message=result_data["message"], status=final_status, result=result_data, error="" if target_result.ok else result_data["message"])

    if mode == DIRECT_COMMAND:
        try:
            result = run_approved_command(
                action.get("command", ""),
                dry_run=dry_run,
                timeout_seconds=timeout_seconds,
            )
        except Exception as error:
            return _mark_claimed_action_failed(action_id, error, claim_token=claim_token) if not dry_run else ChatActionExecutionResult(False, action_id, error=f"Dry run failed safely: {type(error).__name__}", dry_run=True)
        result_data = dict(result.__dict__)
        if dry_run:
            current = _save_dry_run_result(action_id, result_data)
            return ChatActionExecutionResult(bool(result.ok), action_id, message=result.message or result.error, status=current.get("status", "proposed"), result=result_data, dry_run=True)
        final_status = "executed" if result.ok else ("timed_out" if "timed out" in str(result.error or "").lower() else "failed")
        current = _complete_execution_attempt(action_id, status=final_status, result_data=result_data, expected_claim_token=claim_token)
        _store_execution_memory(current, result_data)
        return ChatActionExecutionResult(bool(result.ok), action_id, message=result.message or result.error, status=final_status, result=result_data, dry_run=False)

    if mode == DIRECT_FUNCTION:
        function_name = action.get("function_name")
        args = action.get("function_args", {}) or {}
        if function_name in {"experiment_review_list", "experiment_review_start", "experiment_review_status"}:
            from conversational_experiment_review import execute_conversational_review_action
            try:
                result_data = execute_conversational_review_action(str(function_name), args, dry_run=dry_run)
            except Exception as error:
                return _mark_claimed_action_failed(action_id, error, claim_token=claim_token) if not dry_run else ChatActionExecutionResult(
                    False, action_id, error=f"Dry run failed safely: {type(error).__name__}", dry_run=True)
            if dry_run:
                current = _save_dry_run_result(action_id, result_data)
                return ChatActionExecutionResult(bool(result_data.get("ok")), action_id, message=str(result_data.get("message") or ""),
                                                 status=current.get("status", "proposed"), result=result_data, dry_run=True)
            final_status = "executed" if result_data.get("ok") else "failed"
            current = _complete_execution_attempt(action_id, status=final_status, result_data=result_data, expected_claim_token=claim_token)
            # the result holds a receipt and status only, so the stored memory can carry no review conclusion
            _store_execution_memory(current, result_data)
            return ChatActionExecutionResult(bool(result_data.get("ok")), action_id, message=str(result_data.get("message") or ""),
                                             status=final_status, result=result_data,
                                             error="" if result_data.get("ok") else str(result_data.get("message") or ""))
        if function_name in {
            "research_session_create",
            "research_session_authorize_execute",
            "research_session_cancel",
            "research_session_status",
            "research_history_list",
            "research_sessions_compare",
            "research_report_export",
        }:
            try:
                from conversational_research_actions import execute_conversational_research_action
            except ImportError:
                from conversational_research_actions import execute_conversational_research_action

            try:
                result_data = execute_conversational_research_action(
                    str(function_name),
                    args,
                    event_id=action_id,
                    dry_run=dry_run,
                )
            except Exception as error:
                return _mark_claimed_action_failed(action_id, error, claim_token=claim_token) if not dry_run else ChatActionExecutionResult(False, action_id, error=f"Dry run failed safely: {type(error).__name__}", dry_run=True)
            if dry_run:
                current = _save_dry_run_result(action_id, result_data)
                return ChatActionExecutionResult(bool(result_data.get("ok")), action_id, message=str(result_data.get("message") or "Research dry run finished."), status=current.get("status", "proposed"), result=result_data, dry_run=True)
            final_status = "executed" if result_data.get("ok") else "failed"
            current = _complete_execution_attempt(action_id, status=final_status, result_data=result_data, expected_claim_token=claim_token)
            _store_execution_memory(current, result_data)
            return ChatActionExecutionResult(bool(result_data.get("ok")), action_id, message=str(result_data.get("message") or "Research action finished."), status=final_status, result=result_data, error="" if result_data.get("ok") else str(result_data.get("message") or "Research action failed safely."))
        if function_name == "release_summary":
            from release_self_knowledge import inspect_current_release
            result_data = inspect_current_release().public_result()
            if dry_run:
                result_data = dict(result_data)
                result_data["message"] = "Dry run passed. The allowlisted current-release files would be inspected once without provider contact or mutation."
                current = _save_dry_run_result(action_id, result_data)
                return ChatActionExecutionResult(True, action_id, message=result_data["message"], status=current.get("status", "proposed"), result=result_data, dry_run=True)
            final_status = "executed" if result_data["ok"] else "failed"
            current = _complete_execution_attempt(action_id, status=final_status, result_data=result_data, expected_claim_token=claim_token)
            _store_execution_memory(current, result_data)
            return ChatActionExecutionResult(bool(result_data["ok"]), action_id, message=result_data["message"], status=final_status, result=result_data, error="" if result_data["ok"] else result_data["message"])
        if function_name != "suggest_patch":
            if not dry_run:
                return _mark_claimed_action_failed(action_id, f"Unsupported chat action function: {function_name}", claim_token=claim_token)
            return ChatActionExecutionResult(False, action_id, error=f"Unsupported chat action function: {function_name}", dry_run=True)
        if dry_run:
            result_data = {
                "ok": True,
                "message": "Dry run passed. Patch suggestion would be generated using the local model, but no proposal was created.",
                "target_file": args.get("target_file"),
                "request": args.get("request"),
            }
            current = _save_dry_run_result(action_id, result_data)
            return ChatActionExecutionResult(True, action_id, message=result_data["message"], status=current.get("status", "proposed"), result=result_data, dry_run=True)
        try:
            result = suggest_patch(args.get("target_file", ""), args.get("request", action.get("user_request", "")), use_ai=True)
        except Exception as error:
            return _mark_claimed_action_failed(action_id, error, claim_token=claim_token)
        result_data = dict(result.__dict__)
        final_status = "executed" if result.ok else "failed"
        current = _complete_execution_attempt(action_id, status=final_status, result_data=result_data, expected_claim_token=claim_token)
        _store_execution_memory(current, result_data)
        return ChatActionExecutionResult(bool(result.ok), action_id, message=("Patch proposal created." if result.ok else result.error), status=final_status, result=result_data, dry_run=False)

    if mode == APPROVAL:
        if dry_run:
            result_data = {
                "ok": True,
                "message": "Dry run passed. Executing this chat action would create an approval inbox item, not perform the action directly.",
                "approval_action_type": action.get("approval_action_type"),
                "approval_object_id": action.get("approval_object_id"),
                "approval_command": action.get("approval_command"),
            }
            current = _save_dry_run_result(action_id, result_data)
            return ChatActionExecutionResult(True, action_id, message=result_data["message"], status=current.get("status", "proposed"), result=result_data, dry_run=True)

        try:
            approval = create_approval(
                action_type=action.get("approval_action_type", ""),
                object_id=action.get("approval_object_id", ""),
                command=action.get("approval_command", ""),
                summary=action.get("summary", "Chat action requested approval."),
                risk_level=action.get("risk_level", "medium"),
                source="chat_action_router",
                reason=action.get("explanation", "Plain-English chat action requires approval."),
                metadata={"chat_action_id": action_id, "user_request": action.get("user_request")},
            )
        except Exception as error:
            return _mark_claimed_action_failed(action_id, error, claim_token=claim_token)
        result_data = {"ok": True, "approval_id": approval.get("id"), "status": approval.get("status")}
        current = _complete_execution_attempt(
            action_id,
            status="approval_created",
            result_data=result_data,
            extra_updates={"approval_id": approval.get("id", "")},
            expected_claim_token=claim_token,
        )
        _store_execution_memory(current, result_data)
        return ChatActionExecutionResult(True, action_id, message=f"Approval request created: {approval.get('id')}", status="approval_created", result=result_data, dry_run=False)

    return ChatActionExecutionResult(False, action_id, error=f"Unsupported execution mode: {mode}", dry_run=dry_run)


def _store_execution_memory(action: dict[str, Any], result_data: dict[str, Any]) -> None:
    store_memory({
        "type": "chat_action_executed",
        "content": f"Executed chat action {action.get('id')} with status {action.get('status')}. Intent: {action.get('intent')}. Result: {result_data.get('message') or result_data.get('error') or result_data.get('approval_id') or result_data.get('patch_id') or result_data.get('ok')}",
        "source": "chat_action_router",
        "chat_action_id": action.get("id"),
        "intent": action.get("intent"),
        "status": action.get("status"),
    }, vectorize=False)


def chat_action_text(action: dict[str, Any] | None, full: bool = False) -> str:
    if not action:
        return "Chat action not found."

    lines = [
        f"# Chat Action: {action.get('id')}",
        f"Status: {action.get('status')}",
        f"Created: {action.get('created_at')}",
        f"Updated: {action.get('updated_at')}",
        f"Intent: {action.get('intent')}",
        f"Mode: {action.get('execution_mode')}",
        f"Risk: {action.get('risk_level')}",
        "",
        "## User request",
        action.get("user_request", ""),
        "",
        "## Summary",
        action.get("summary", ""),
    ]

    if action.get("explanation"):
        lines.extend(["", "## Explanation", action.get("explanation", "")])
    if action.get("command"):
        lines.extend(["", "## Command", action.get("command", "")])
    if action.get("function_name"):
        lines.extend(["", "## Function", f"{action.get('function_name')}({json.dumps(action.get('function_args', {}), indent=2)})"])
    if action.get("approval_action_type"):
        lines.extend([
            "",
            "## Approval request to create",
            f"Action type: {action.get('approval_action_type')}",
            f"Object id: {action.get('approval_object_id')}",
            f"Command: {action.get('approval_command')}",
        ])
    if action.get("blocked_reason"):
        lines.extend(["", "## Blocked reason", action.get("blocked_reason", "")])
    if action.get("approval_id"):
        lines.extend(["", "## Created approval", action.get("approval_id", "")])

    result = action.get("last_dry_run_result") or action.get("result")
    if result:
        lines.extend(["", "## Latest result", json.dumps(result, indent=2, default=str)])

    useful = action.get("useful_commands", []) or _chat_action_commands(action)
    if useful:
        lines.extend(["", "## Useful commands"])
        lines.extend(command for command in useful if command)

    if full:
        lines.extend(["", "## Raw chat action", json.dumps(action, indent=2, default=str)])

    return "\n".join(lines)


def print_chat_action(user_request: str) -> None:
    action = propose_chat_action(user_request, save=True)
    print(chat_action_text(action, full=False))
    print()
    if action.get("execution_mode") in {DIRECT_COMMAND, DIRECT_FUNCTION, APPROVAL}:
        print("Next commands:")
        print("  python conscious_agent/main.py --execute-chat-action latest --dry-run")
        print("  python conscious_agent/main.py --execute-chat-action latest")
    elif action.get("command"):
        print("Manual command:")
        print(f"  {action.get('command')}")


def print_execute_chat_action(chat_action_id: str = "latest", dry_run: bool = False) -> None:
    result = execute_chat_action(chat_action_id, dry_run=dry_run, claimant="cli")
    if not result.ok:
        print("Chat action did not complete successfully.")
        print(f"Reason: {result.error or result.message}")
        return
    if dry_run:
        print("Chat action dry run passed.")
    else:
        print("Chat action executed.")
    print(f"Chat action: {result.chat_action_id}")
    print(f"Status: {result.status}")
    if result.message:
        print(f"Message: {result.message}")
    result_data = result.result or {}
    for key in ["approval_id", "patch_id", "target_file", "command", "return_code", "error"]:
        if result_data.get(key) not in {None, ""}:
            print(f"{key.replace('_', ' ').title()}: {result_data.get(key)}")


def print_chat_actions(status: str = "", include_closed: bool = True) -> None:
    actions = list_chat_actions(status=status, include_closed=include_closed)
    if not actions:
        print("No chat actions found.")
        return
    for action in actions:
        print(
            f"{action.get('id')} | status={action.get('status')} | "
            f"intent={action.get('intent')} | mode={action.get('execution_mode')} | risk={action.get('risk_level')}"
        )
        print(f"  Request: {action.get('user_request')}")
        if action.get("command"):
            print(f"  Command: {action.get('command')}")
        if action.get("approval_id"):
            print(f"  Approval: {action.get('approval_id')}")


def print_saved_chat_action(chat_action_id: str = "latest", full: bool = False) -> None:
    action = load_chat_action(chat_action_id)
    if not action:
        print(f"Chat action not found: {chat_action_id}")
        return
    print(chat_action_text(action, full=full))
