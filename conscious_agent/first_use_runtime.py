from __future__ import annotations

"""Fast, bounded first-use restoration for the dashboard shell.

The payload is private runtime state intended for the local browser. Timing
receipts are deliberately content-free and never include paths, messages,
drafts, prompts, responses, provider payloads, credentials, or model output.
"""

import time
from pathlib import Path
from typing import Any, Iterable

try:
    from launch_environment import build_runtime_migration_guidance
except ImportError:
    from launch_environment import build_runtime_migration_guidance

from startup_coherence import (
    build_active_project_self_description,
    build_restart_continuity_snapshot,
    build_startup_progress,
    normalize_retry_attempt,
    normalize_retry_services,
    public_restart_snapshot,
)

FIRST_USE_SCHEMA_VERSION = "2"
CHAT_INTERACTIVE_TARGET_SECONDS = 5.0
COLD_HEALTH_TARGET_SECONDS = 15.0

_PRIVATE_TIMING_KEYS = {
    "path", "content", "draft", "message", "prompt", "response", "payload",
    "secret", "credential", "endpoint", "model", "memory", "conversation",
}


def _phase(name: str, started: float, *, status: str = "ready", required: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "required": bool(required),
        "elapsed_seconds": round(max(0.0, time.perf_counter() - started), 6),
    }


def _safe_session(session: dict[str, Any] | None) -> dict[str, Any]:
    value = session or {}
    return {
        "id": str(value.get("id") or ""),
        "project_id": str(value.get("project_id") or ""),
        "title": str(value.get("title") or "New conversation")[:200],
        "status": str(value.get("status") or ("active" if value else "empty"))[:40],
        "turn_count": max(0, int(value.get("turn_count") or 0)),
        "completed_turn_count": max(0, int(value.get("completed_turn_count") or 0)),
    }


def _safe_session_catalog(project_id: str) -> list[dict[str, Any]]:
    """Return bounded selector metadata without importing the full console renderer."""
    try:
        from conversation_sessions import list_conversation_sessions

        rows = list_conversation_sessions(include_archived=False, project_id=project_id or None)
    except Exception:
        return []
    catalog: list[dict[str, Any]] = []
    for row in rows[:100]:
        if not isinstance(row, dict):
            continue
        catalog.append({
            "id": str(row.get("id") or ""),
            "title": str(row.get("title") or "New conversation")[:72],
            "status": "active",
            "turn_count": max(0, int(row.get("turn_count") or 0)),
            "updated_at": str(row.get("updated_at") or ""),
        })
    return catalog


def _provider_summary() -> dict[str, Any]:
    try:
        from provider_recovery_evidence import load_provider_recovery_evidence, provider_resume_cue

        evidence = load_provider_recovery_evidence()
        cue = provider_resume_cue(evidence)
        state = str(cue.get("state") or "unknown")
        return {
            "status": state,
            "label": str(cue.get("label") or "Provider readiness has not been checked")[:240],
            "recovery_proven": bool(cue.get("recovery_proven")),
            "retry_available": True,
            "source": "persisted_redacted_evidence" if evidence else "not_checked",
            "provider_contacted": False,
        }
    except Exception as error:
        return {
            "status": "unknown",
            "label": "Provider readiness is temporarily unavailable.",
            "recovery_proven": False,
            "retry_available": True,
            "source": "optional_service_failure",
            "error_type": type(error).__name__,
            "provider_contacted": False,
        }


def _launch_mode(value: str) -> str:
    token = str(value or "unspecified").strip().lower()
    allowed = {"unspecified", "cold", "warm", "restart", "refresh", "reopen", "new_tab"}
    return token if token in allowed else "unspecified"


def build_first_use_bootstrap(
    *,
    tab_id: str = "",
    retry_services: Iterable[str] | str | None = None,
    retry_attempt: int = 0,
    launch_mode: str = "unspecified",
) -> dict[str, Any]:
    """Restore the minimum coherent chat state without loading administration.

    Optional failures are reported independently so the shell remains usable.
    Retry metadata is bounded and read-only. This function never sends a provider
    request, replays a turn, or creates a conversation.
    """

    normalized_retry_services = normalize_retry_services(retry_services)
    normalized_retry_attempt = normalize_retry_attempt(retry_attempt)
    normalized_launch_mode = _launch_mode(launch_mode)
    overall_started = time.perf_counter()
    phases: list[dict[str, Any]] = []
    optional_failures: list[dict[str, str]] = []

    project_description: dict[str, Any]
    phase_started = time.perf_counter()
    project_description = build_active_project_self_description()
    project_truth_status = str(project_description.get("status") or "description_unavailable")
    project_id = str(project_description.get("id") or "")
    if project_truth_status in {"no_active_project", "description_unavailable", "conversation_unavailable"}:
        optional_failures.append({
            "service": "active_project",
            "error_type": str(project_description.get("error_type") or project_truth_status),
        })
        phases.append(_phase("active_project_restoration", phase_started, status="degraded", required=False))
    else:
        phases.append(_phase(
            "active_project_restoration",
            phase_started,
            status="ready" if project_truth_status == "ready" else "degraded",
            required=False,
        ))
    # Preserve the established active/unavailable compatibility state while
    # exposing the more precise truth classification separately.
    project_description["truth_status"] = project_truth_status
    project_description["status"] = "active" if project_id else "unavailable"

    session: dict[str, Any] | None = None
    draft: dict[str, Any] = {
        "content": "", "content_digest": "", "revision": 0, "updated_at": "", "cleared_at": "",
    }
    presentation: dict[str, Any] = {
        "follow_latest": True, "scroll_from_bottom_px": 0, "view_anchor_turn_id": "",
        "view_anchor_offset_px": 0, "last_seen_turn_id": "", "last_seen_turn_count": 0,
        "unread_turn_count": 0, "composer_intentionally_empty": True, "updated_at": "",
    }
    phase_started = time.perf_counter()
    try:
        from conversation_sessions import get_active_conversation_session, load_conversation_draft
        from conversation_navigation import load_conversation_presentation_state

        session = get_active_conversation_session(create_if_missing=False)
        session_id = str((session or {}).get("id") or "")
        session_project_id = str((session or {}).get("project_id") or "")
        if session_id and project_id and session_project_id and session_project_id != project_id:
            optional_failures.append({"service": "conversation_restoration", "error_type": "ProjectSessionMismatch"})
            session = None
            session_id = ""
            phases.append(_phase("conversation_restoration", phase_started, status="degraded", required=False))
        else:
            if session_id:
                draft = load_conversation_draft(session_id)
                presentation = load_conversation_presentation_state(session_id)
            phases.append(_phase("conversation_restoration", phase_started, required=False))
    except Exception as error:
        optional_failures.append({"service": "conversation_restoration", "error_type": type(error).__name__})
        phases.append(_phase("conversation_restoration", phase_started, status="degraded", required=False))

    coordination: dict[str, Any] = {
        "status": "not_registered",
        "revision": 0,
        "selected_project_id": project_id,
        "selected_session_id": str((session or {}).get("id") or ""),
        "owner_present": False,
        "is_owner": False,
    }
    phase_started = time.perf_counter()
    try:
        from conversation_tab_coordination import coordination_snapshot

        coordination = coordination_snapshot(tab_id=tab_id) if tab_id else coordination_snapshot()
        selected_project_id = str(coordination.get("selected_project_id") or "")
        if selected_project_id and project_id and selected_project_id != project_id:
            optional_failures.append({"service": "conversation_ownership", "error_type": "ProjectCoordinationMismatch"})
            phases.append(_phase("conversation_ownership_restoration", phase_started, status="degraded", required=False))
        else:
            phases.append(_phase("conversation_ownership_restoration", phase_started, required=False))
    except Exception as error:
        optional_failures.append({"service": "conversation_ownership", "error_type": type(error).__name__})
        phases.append(_phase("conversation_ownership_restoration", phase_started, status="degraded", required=False))

    phase_started = time.perf_counter()
    provider = _provider_summary()
    provider_state = str(provider.get("status") or "unknown")
    provider_phase_status = "ready" if provider_state not in {"unknown", "unavailable", "temporarily_unavailable"} else "pending"
    if provider.get("source") == "optional_service_failure":
        optional_failures.append({"service": "provider_availability", "error_type": str(provider.get("error_type") or "Unavailable")})
        provider_phase_status = "degraded"
    phases.append(_phase(
        "provider_availability_restoration",
        phase_started,
        status=provider_phase_status,
        required=False,
    ))

    elapsed = round(time.perf_counter() - overall_started, 6)
    result: dict[str, Any] = {
        "ok": True,
        "status": "degraded" if optional_failures else "ready",
        "schema_version": FIRST_USE_SCHEMA_VERSION,
        "chat_interactive": True,
        "chat_interactive_target_seconds": CHAT_INTERACTIVE_TARGET_SECONDS,
        "active_project": project_description,
        "runtime_guidance": build_runtime_migration_guidance(
            Path(__file__).resolve().parents[1],
            include_paths=False,
            inspect_runtime_inventory=False,
        ),
        "selected_session": _safe_session(session),
        "session_catalog": _safe_session_catalog(project_id),
        "draft": {
            "content": str(draft.get("content") or ""),
            "content_digest": str(draft.get("content_digest") or ""),
            "revision": max(0, int(draft.get("revision") or 0)),
            "updated_at": str(draft.get("updated_at") or ""),
            "cleared_at": str(draft.get("cleared_at") or ""),
        },
        "presentation": {
            "follow_latest": bool(presentation.get("follow_latest", True)),
            "scroll_from_bottom_px": max(0, int(presentation.get("scroll_from_bottom_px") or 0)),
            "view_anchor_turn_id": str(presentation.get("view_anchor_turn_id") or ""),
            "view_anchor_offset_px": int(presentation.get("view_anchor_offset_px") or 0),
            "last_seen_turn_id": str(presentation.get("last_seen_turn_id") or ""),
            "last_seen_turn_count": max(0, int(presentation.get("last_seen_turn_count") or 0)),
            "unread_turn_count": max(0, int(presentation.get("unread_turn_count") or 0)),
            "composer_intentionally_empty": bool(presentation.get("composer_intentionally_empty", True)),
            "updated_at": str(presentation.get("updated_at") or ""),
        },
        "coordination": coordination,
        "provider": provider,
        "optional_failures": optional_failures,
        "recovery": {
            "chat_remains_usable": True,
            "optional_retry_services": [row["service"] for row in optional_failures],
            "retry_attempt": normalized_retry_attempt,
            "retry_requested_services": list(normalized_retry_services),
            "retry_is_automatic": False,
            "accepted_message_replayed": False,
            "provider_request_repeated": False,
            "false_ready_state": False,
        },
        "timing": {
            "total_seconds": elapsed,
            "phases": phases,
            "content_free": True,
            "private_values_included": False,
        },
        "administrative_services_loaded": False,
        "provider_contacted": False,
        "runtime_mutation_performed": False,
        "accepted_turn_replayed": False,
    }
    result["progress"] = build_startup_progress(
        phases,
        optional_failures,
        provider,
        retry_services=normalized_retry_services,
        retry_attempt=normalized_retry_attempt,
    )
    restart_snapshot = build_restart_continuity_snapshot(result, launch_mode=normalized_launch_mode)
    result["restart"] = public_restart_snapshot(restart_snapshot)
    from first_use_checkpoint import build_first_use_coherence_checkpoint
    result["checkpoint"] = build_first_use_coherence_checkpoint(result)
    from natural_conversation_checkpoint import build_natural_conversation_checkpoint
    result["natural_conversation_checkpoint"] = build_natural_conversation_checkpoint()
    from messaging_reliability_checkpoint import build_messaging_reliability_checkpoint
    result["messaging_reliability_checkpoint"] = build_messaging_reliability_checkpoint()
    return result


def build_content_free_timing_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    """Return only safe phase timing and readiness classifications."""

    timing = payload.get("timing") if isinstance(payload.get("timing"), dict) else {}
    rows = timing.get("phases") if isinstance(timing.get("phases"), list) else []
    phases = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        phases.append({
            "name": str(row.get("name") or "")[:80],
            "status": str(row.get("status") or "unknown")[:24],
            "required": bool(row.get("required")),
            "elapsed_seconds": round(max(0.0, float(row.get("elapsed_seconds") or 0.0)), 6),
        })
    progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
    restart = payload.get("restart") if isinstance(payload.get("restart"), dict) else {}
    return {
        "type": "first_use_startup_timing",
        "schema_version": FIRST_USE_SCHEMA_VERSION,
        "status": str(payload.get("status") or "unknown")[:24],
        "chat_interactive": bool(payload.get("chat_interactive")),
        "total_seconds": round(max(0.0, float(timing.get("total_seconds") or 0.0)), 6),
        "phases": phases,
        "completed_phase_count": max(0, int(progress.get("completed_phase_count") or 0)),
        "total_phase_count": max(0, int(progress.get("total_phase_count") or 0)),
        "retry_attempt": max(0, int((progress.get("retry") or {}).get("attempt") or 0)),
        "optional_failure_count": len(payload.get("optional_failures") or []),
        "provider_state": str((payload.get("provider") or {}).get("status") or "unknown")[:40],
        "restart_launch_mode": str(restart.get("launch_mode") or "unspecified")[:40],
        "continuity_digest": str(restart.get("continuity_digest") or "")[:64],
        "provider_contacted": bool(payload.get("provider_contacted")),
        "accepted_turn_replayed": bool(payload.get("accepted_turn_replayed")),
        "runtime_mutation_performed": bool(payload.get("runtime_mutation_performed")),
        "content_free": True,
        "private_values_included": False,
    }


def timing_receipt_contains_private_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered not in {"content_free", "private_values_included"} and any(
                token in lowered for token in _PRIVATE_TIMING_KEYS
            ):
                return True
            if timing_receipt_contains_private_fields(item):
                return True
    elif isinstance(value, list):
        return any(timing_receipt_contains_private_fields(item) for item in value)
    return False
