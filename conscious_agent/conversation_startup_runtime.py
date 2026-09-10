from __future__ import annotations

"""Thread-safe, provider-free initialization for conversation dashboard surfaces.

The startup coordinator loads only the modules needed to display, select, and
coordinate private conversation sessions. It never calls a model provider,
replays accepted turns, mutates provider configuration, or touches release and
administrative services.
"""

import importlib
import sys
import threading
import time
from typing import Any, Iterable

CORE_CONVERSATION_MODULES: tuple[str, ...] = (
    "conversation_sessions",
    "conversation_navigation",
    "conversation_tab_coordination",
    "dashboard_chat_console",
)

OPTIONAL_CONVERSATION_MODULES: tuple[str, ...] = (
    "conversation_offline_degradation",
    "conversation_offline_durability",
)

PROVIDER_SENTINELS: tuple[str, ...] = (
    "local_model",
    "conversation_runtime",
    "brain",
    "chat",
)

ADMINISTRATIVE_SENTINELS: tuple[str, ...] = (
    "release_installation",
    "release_packaging",
    "controlled_build_cycle",
    "workspace_execution",
    "patch_drafting",
    "conversation_daily_evaluation",
)

STALE_INITIALIZATION_SECONDS = 8.0
_WAIT_SLICE_SECONDS = 0.05

_LOCK = threading.RLock()
_CONDITION = threading.Condition(_LOCK)
_STATE: dict[str, Any] = {
    "status": "uninitialized",
    "generation": 0,
    "attempts": 0,
    "recoveries": 0,
    "stale_takeovers": 0,
    "active_owner_wait_timeouts": 0,
    "owner_thread_id": None,
    "owner_token": "",
    "started_monotonic": 0.0,
    "completed_monotonic": 0.0,
    "loaded_modules": [],
    "optional_failures": [],
    "last_error_type": "",
    "last_error_module": "",
    "last_recovery_reason": "",
}


def _thread_is_alive(thread_id: int | None) -> bool:
    if thread_id is None:
        return False
    return any(thread.ident == thread_id and thread.is_alive() for thread in threading.enumerate())


def _safe_module_names(values: Iterable[str]) -> tuple[str, ...]:
    names: list[str] = []
    for raw in values:
        name = str(raw or "").strip()
        if not name or name in names:
            continue
        if not name.replace("_", "").replace(".", "").isalnum():
            raise ValueError(f"Invalid conversation startup module name: {name!r}")
        names.append(name)
    return tuple(names)


def conversation_startup_status() -> dict[str, Any]:
    with _LOCK:
        status = str(_STATE["status"])
        age = 0.0
        if status == "initializing":
            age = max(0.0, time.monotonic() - float(_STATE["started_monotonic"] or 0.0))
        loaded = sorted(name for name in CORE_CONVERSATION_MODULES if name in sys.modules)
        missing = sorted(name for name in CORE_CONVERSATION_MODULES if name not in sys.modules)
        if status == "failed":
            message = "Conversation startup failed safely. A later request may retry without replaying an accepted turn."
        elif status == "degraded":
            message = "Conversation is available; one or more optional local services remain unavailable."
        elif status == "initializing":
            message = "Conversation surfaces are initializing without contacting a provider."
        elif status == "ready":
            message = "Conversation surfaces are ready."
        else:
            message = "Conversation surfaces have not been initialized yet."
        return {
            "ok": status in {"uninitialized", "ready", "degraded"},
            "status": status,
            "generation": int(_STATE["generation"]),
            "attempts": int(_STATE["attempts"]),
            "recoveries": int(_STATE["recoveries"]),
            "stale_takeovers": int(_STATE["stale_takeovers"]),
            "active_owner_wait_timeouts": int(_STATE["active_owner_wait_timeouts"]),
            "initialization_age_seconds": round(age, 6),
            "loaded_core_modules": loaded,
            "missing_core_modules": missing,
            "optional_failures": [dict(item) for item in _STATE["optional_failures"]],
            "last_error_type": str(_STATE["last_error_type"] or ""),
            "last_error_module": str(_STATE["last_error_module"] or ""),
            "last_recovery_reason": str(_STATE["last_recovery_reason"] or ""),
            "retry_available": status == "failed",
            "initialization_owner_active": _thread_is_alive(_STATE.get("owner_thread_id")) if status == "initializing" else False,
            "message": message,
            "provider_modules_loaded": {name: name in sys.modules for name in PROVIDER_SENTINELS},
            "administrative_modules_loaded": {name: name in sys.modules for name in ADMINISTRATIVE_SENTINELS},
            "provider_contacted": False,
            "accepted_turn_replayed": False,
            "runtime_mutation_performed": False,
        }


def ensure_conversation_startup(
    required_modules: Iterable[str] = CORE_CONVERSATION_MODULES,
    optional_modules: Iterable[str] = OPTIONAL_CONVERSATION_MODULES,
    *,
    stale_seconds: float = STALE_INITIALIZATION_SECONDS,
) -> dict[str, Any]:
    """Load conversation surfaces once and recover from abandoned initialization.

    Required module failures return a safe failed status. Optional failures leave
    the runtime degraded but usable. A later request may retry a failed startup.
    """

    required = _safe_module_names(required_modules)
    optional = tuple(name for name in _safe_module_names(optional_modules) if name not in required)
    stale_after = max(0.05, float(stale_seconds))
    token = f"{threading.get_ident()}:{time.monotonic_ns()}"
    wait_started = time.monotonic()

    while True:
        with _CONDITION:
            missing = [name for name in required if name not in sys.modules]
            if not missing and _STATE["status"] in {"ready", "degraded"}:
                return conversation_startup_status()

            if _STATE["status"] == "initializing":
                age = max(0.0, time.monotonic() - float(_STATE["started_monotonic"] or 0.0))
                owner_alive = _thread_is_alive(_STATE.get("owner_thread_id"))
                if not owner_alive:
                    _STATE["stale_takeovers"] += 1
                    _STATE["recoveries"] += 1
                    _STATE["last_recovery_reason"] = "stale_initialization_owner"
                    _STATE["status"] = "uninitialized"
                    _STATE["owner_thread_id"] = None
                    _STATE["owner_token"] = ""
                    _CONDITION.notify_all()
                elif time.monotonic() - wait_started >= stale_after:
                    # A live owner may be slow or blocked inside an import. Starting a
                    # second generation would duplicate initialization and can violate
                    # exactly-once startup boundaries. Return a bounded retry-later
                    # state while leaving the active owner untouched.
                    _STATE["active_owner_wait_timeouts"] += 1
                    return conversation_startup_status()
                else:
                    remaining = max(0.01, stale_after - (time.monotonic() - wait_started))
                    _CONDITION.wait(timeout=min(_WAIT_SLICE_SECONDS, remaining))
                    continue

            if _STATE["status"] == "failed":
                _STATE["recoveries"] += 1
                _STATE["last_recovery_reason"] = "retry_after_failure"

            _STATE["status"] = "initializing"
            _STATE["generation"] += 1
            _STATE["attempts"] += 1
            _STATE["owner_thread_id"] = threading.get_ident()
            _STATE["owner_token"] = token
            _STATE["started_monotonic"] = time.monotonic()
            _STATE["completed_monotonic"] = 0.0
            _STATE["optional_failures"] = []
            _STATE["last_error_type"] = ""
            _STATE["last_error_module"] = ""
            break

    loaded: list[str] = []
    optional_failures: list[dict[str, str]] = []
    try:
        for name in required:
            importlib.import_module(name)
            loaded.append(name)
        for name in optional:
            try:
                importlib.import_module(name)
                loaded.append(name)
            except Exception as error:  # optional failure is visible but non-blocking
                optional_failures.append({"module": name, "error_type": type(error).__name__})
    except Exception as error:
        with _CONDITION:
            if _STATE.get("owner_token") == token:
                _STATE["status"] = "failed"
                _STATE["loaded_modules"] = sorted(set(loaded))
                _STATE["last_error_type"] = type(error).__name__
                _STATE["last_error_module"] = str(name or "")
                _STATE["owner_thread_id"] = None
                _STATE["owner_token"] = ""
                _STATE["completed_monotonic"] = time.monotonic()
                _CONDITION.notify_all()
        return conversation_startup_status()

    with _CONDITION:
        if _STATE.get("owner_token") == token:
            _STATE["status"] = "degraded" if optional_failures else "ready"
            _STATE["loaded_modules"] = sorted(set(loaded))
            _STATE["optional_failures"] = optional_failures
            _STATE["last_error_type"] = ""
            _STATE["last_error_module"] = ""
            if optional_failures and not _STATE.get("last_recovery_reason"):
                _STATE["last_recovery_reason"] = "optional_service_degraded"
            _STATE["owner_thread_id"] = None
            _STATE["owner_token"] = ""
            _STATE["completed_monotonic"] = time.monotonic()
            _CONDITION.notify_all()
    return conversation_startup_status()


def _reset_conversation_startup_for_tests() -> None:
    """Reset only in-memory startup coordination; private runtime data is untouched."""
    with _CONDITION:
        _STATE.update(
            {
                "status": "uninitialized",
                "generation": 0,
                "attempts": 0,
                "recoveries": 0,
                "stale_takeovers": 0,
    "active_owner_wait_timeouts": 0,
                "owner_thread_id": None,
                "owner_token": "",
                "started_monotonic": 0.0,
                "completed_monotonic": 0.0,
                "loaded_modules": [],
                "optional_failures": [],
                "last_error_type": "",
                "last_error_module": "",
                "last_recovery_reason": "",
            }
        )
        _CONDITION.notify_all()
