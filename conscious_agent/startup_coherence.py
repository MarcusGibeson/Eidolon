from __future__ import annotations

"""Content-safe startup coherence helpers for the conversation-first shell.

The helpers describe the active project from persisted authority, expose bounded
startup phase progress, and compare restart continuity without returning source
paths, conversation text, draft text, prompts, responses, credentials, or
provider payloads. They are read-only and never replay accepted work.
"""

import hashlib
import json
from typing import Any, Iterable

STARTUP_COHERENCE_SCHEMA_VERSION = "1"
MAX_OPTIONAL_RETRY_ATTEMPTS = 3
RETRYABLE_SERVICES: tuple[str, ...] = (
    "active_project",
    "conversation_restoration",
    "conversation_ownership",
    "provider_availability",
)
STARTUP_PHASE_ORDER: tuple[str, ...] = (
    "chat_shell",
    "active_project_restoration",
    "conversation_restoration",
    "conversation_ownership_restoration",
    "provider_availability_restoration",
)


def _text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _source_summary(binding: dict[str, Any]) -> dict[str, Any]:
    capability = binding.get("capability_state") if isinstance(binding.get("capability_state"), dict) else {}
    return {
        "status": _text(binding.get("status") or "unknown", 64),
        "available": bool(binding.get("source_root_accessible")),
        "identity_matches": bool(binding.get("source_identity_matches")),
        "version_matches": not bool(binding.get("version_mismatch")),
        "safe_to_modify": bool(binding.get("safe_to_modify")),
        "conversation_available": bool(
            capability.get("conversation_available", capability.get("ordinary_conversation", True))
        ),
        "inspection_available": bool(
            capability.get("inspection_available", capability.get("source_inspection", False))
        ),
        "development_available": bool(
            capability.get("development_available", capability.get("development", False))
        ),
        "verification_available": bool(
            capability.get("verification_available", capability.get("verification", False))
        ),
    }


def build_active_project_self_description(project: dict[str, Any] | None = None) -> dict[str, Any]:
    """Describe the active project accurately without exposing its source path."""

    try:
        import project_manager
        from release_metadata import WORKING_SOURCE_VERSION
        from version_roles import project_version_roles

        active = dict(project or project_manager.get_active_project() or {})
        if not active:
            return {
                "ok": False,
                "status": "no_active_project",
                "id": "",
                "name": "No active project",
                "description": "No active project is configured. Conversation startup remains available in recovery mode.",
                "language": "",
                "current_milestone": "",
                "next_recommended_arc": "",
                "versions": {
                    "working_source": _text(WORKING_SOURCE_VERSION, 80),
                    "installed": "",
                    "candidate": "",
                    "roles_separate": True,
                },
                "source": _source_summary({}),
                "authority": {
                    "selection": "persisted_project_registry",
                    "working_source": "WORKING_SOURCE_VERSION",
                    "consistent": False,
                },
                "summary": "No active project is configured.",
                "content_free": True,
                "source_path_included": False,
            }

        project_id = _text(active.get("id"), 160)
        binding = project_manager.project_source_binding(project_id)
        source = _source_summary(binding if isinstance(binding, dict) else {})
        roles = project_version_roles(active)
        declared_working = _text(roles.get("working_source_version"), 80)
        authoritative_working = _text(WORKING_SOURCE_VERSION, 80)
        version_consistent = not declared_working or declared_working == authoritative_working
        identity_consistent = bool(source.get("identity_matches"))

        if not source.get("conversation_available"):
            status = "conversation_unavailable"
        elif not source.get("available"):
            status = "source_unavailable"
        elif not identity_consistent:
            status = "source_identity_mismatch"
        elif not version_consistent or not source.get("version_matches"):
            status = "source_version_mismatch"
        else:
            status = "ready"

        name = _text(active.get("name") or "Unknown project", 160)
        description = _text(active.get("description"), 360)
        language = _text(active.get("language"), 80)
        milestone = _text(active.get("current_milestone"), 240)
        next_arc = _text(active.get("next_recommended_arc"), 240)
        conversation_phrase = "Conversation is available" if source.get("conversation_available") else "Conversation is unavailable"
        development_phrase = "source development is available" if source.get("development_available") else "source development is paused"
        truth_phrase = {
            "ready": "project identity and working-source authority agree",
            "source_unavailable": "the configured source is unavailable",
            "source_identity_mismatch": "the configured source identity does not match",
            "source_version_mismatch": "the configured source version does not match working authority",
            "conversation_unavailable": "conversation capability is unavailable",
        }[status]
        summary = f"{name} is the active project. {conversation_phrase}; {development_phrase}; {truth_phrase}."

        return {
            "ok": status != "conversation_unavailable",
            "status": status,
            "id": project_id,
            "name": name,
            "description": description,
            "language": language,
            "current_milestone": milestone,
            "next_recommended_arc": next_arc,
            "versions": {
                "working_source": authoritative_working,
                "declared_working": declared_working,
                "installed": _text(roles.get("installed_version"), 80),
                "candidate": _text(roles.get("candidate_version"), 80),
                "roles_separate": True,
            },
            "source": source,
            "authority": {
                "selection": "persisted_project_registry",
                "working_source": "WORKING_SOURCE_VERSION",
                "consistent": bool(identity_consistent and version_consistent and source.get("version_matches")),
            },
            "summary": summary[:520],
            "content_free": True,
            "source_path_included": False,
        }
    except Exception as error:
        return {
            "ok": False,
            "status": "description_unavailable",
            "id": _text((project or {}).get("id"), 160),
            "name": _text((project or {}).get("name") or "Active project unavailable", 160),
            "description": "Active-project details could not be revalidated during startup.",
            "language": "",
            "current_milestone": "",
            "next_recommended_arc": "",
            "versions": {"working_source": "", "installed": "", "candidate": "", "roles_separate": True},
            "source": _source_summary({}),
            "authority": {
                "selection": "persisted_project_registry",
                "working_source": "WORKING_SOURCE_VERSION",
                "consistent": False,
            },
            "summary": "Active-project details are temporarily unavailable; conversation startup may continue.",
            "error_type": type(error).__name__,
            "content_free": True,
            "source_path_included": False,
        }


def normalize_retry_services(values: Iterable[str] | str | None) -> tuple[str, ...]:
    if values is None:
        return ()
    raw_values = values.split(",") if isinstance(values, str) else list(values)
    normalized: list[str] = []
    for raw in raw_values:
        name = _text(raw, 80).lower()
        if not name or name in normalized:
            continue
        if name not in RETRYABLE_SERVICES:
            raise ValueError(f"Unsupported startup retry service: {name}")
        normalized.append(name)
    return tuple(normalized)


def normalize_retry_attempt(value: Any) -> int:
    try:
        attempt = int(value or 0)
    except (TypeError, ValueError) as error:
        raise ValueError("Startup retry attempt must be an integer.") from error
    if attempt < 0 or attempt > MAX_OPTIONAL_RETRY_ATTEMPTS:
        raise ValueError(f"Startup retry attempt must be between 0 and {MAX_OPTIONAL_RETRY_ATTEMPTS}.")
    return attempt


def build_startup_progress(
    phases: list[dict[str, Any]],
    optional_failures: list[dict[str, Any]],
    provider: dict[str, Any],
    *,
    retry_services: Iterable[str] = (),
    retry_attempt: int = 0,
) -> dict[str, Any]:
    phase_by_name = {
        _text(row.get("name"), 80): row
        for row in phases
        if isinstance(row, dict) and _text(row.get("name"), 80)
    }
    failures = {
        _text(row.get("service"), 80): _text(row.get("error_type") or "Unavailable", 80)
        for row in optional_failures
        if isinstance(row, dict)
    }
    retry_scope = normalize_retry_services(retry_services)
    rows: list[dict[str, Any]] = []
    labels = {
        "chat_shell": "Chat input",
        "active_project_restoration": "Active project",
        "conversation_restoration": "Conversation and draft",
        "conversation_ownership_restoration": "Tab ownership",
        "provider_availability_restoration": "Provider availability",
    }
    service_for_phase = {
        "active_project_restoration": "active_project",
        "conversation_restoration": "conversation_restoration",
        "conversation_ownership_restoration": "conversation_ownership",
        "provider_availability_restoration": "provider_availability",
    }
    for name in STARTUP_PHASE_ORDER:
        if name == "chat_shell":
            status = "ready"
            required = True
            elapsed = 0.0
        else:
            phase = phase_by_name.get(name, {})
            status = _text(phase.get("status") or "pending", 24)
            required = bool(phase.get("required"))
            elapsed = round(max(0.0, float(phase.get("elapsed_seconds") or 0.0)), 6)
        service = service_for_phase.get(name, "")
        if service == "provider_availability" and provider.get("status") in {"unknown", "unavailable", "temporarily_unavailable"}:
            status = "pending" if provider.get("status") == "unknown" else "degraded"
        failed = service in failures
        if failed:
            status = "degraded"
        rows.append({
            "name": name,
            "label": labels[name],
            "status": status,
            "required": required,
            "elapsed_seconds": elapsed,
            "retry_service": service if failed else "",
            "retry_available": bool(failed and retry_attempt < MAX_OPTIONAL_RETRY_ATTEMPTS),
            "error_type": failures.get(service, ""),
        })
    completed = sum(1 for row in rows if row["status"] in {"ready", "degraded"})
    return {
        "schema_version": STARTUP_COHERENCE_SCHEMA_VERSION,
        "status": "degraded" if failures else "ready",
        "completed_phase_count": completed,
        "total_phase_count": len(rows),
        "phases": rows,
        "retry": {
            "attempt": retry_attempt,
            "maximum_attempts": MAX_OPTIONAL_RETRY_ATTEMPTS,
            "requested_services": list(retry_scope),
            "remaining_attempts": max(0, MAX_OPTIONAL_RETRY_ATTEMPTS - retry_attempt),
            "automatic_retry": False,
            "accepted_message_replayed": False,
            "provider_request_repeated": False,
        },
        "content_free": True,
    }


def _continuity_projection(payload: dict[str, Any]) -> dict[str, Any]:
    project = payload.get("active_project") if isinstance(payload.get("active_project"), dict) else {}
    session = payload.get("selected_session") if isinstance(payload.get("selected_session"), dict) else {}
    draft = payload.get("draft") if isinstance(payload.get("draft"), dict) else {}
    presentation = payload.get("presentation") if isinstance(payload.get("presentation"), dict) else {}
    coordination = payload.get("coordination") if isinstance(payload.get("coordination"), dict) else {}
    provider = payload.get("provider") if isinstance(payload.get("provider"), dict) else {}
    return {
        "project_id": _text(project.get("id"), 160),
        "project_status": _text(project.get("status"), 64),
        "session_id": _text(session.get("id"), 200),
        "session_status": _text(session.get("status"), 64),
        "turn_count": max(0, int(session.get("turn_count") or 0)),
        "draft_digest": _text(draft.get("content_digest"), 128),
        "draft_revision": max(0, int(draft.get("revision") or 0)),
        "follow_latest": bool(presentation.get("follow_latest", True)),
        "scroll_from_bottom_px": max(0, int(presentation.get("scroll_from_bottom_px") or 0)),
        "view_anchor_turn_id": _text(presentation.get("view_anchor_turn_id"), 200),
        "view_anchor_offset_px": int(presentation.get("view_anchor_offset_px") or 0),
        "coordination_revision": max(0, int(coordination.get("revision") or 0)),
        "selected_session_id": _text(coordination.get("selected_session_id"), 200),
        "owner_present": bool(coordination.get("owner_present")),
        "is_owner": bool(coordination.get("is_owner")),
        "provider_status": _text(provider.get("status") or "unknown", 64),
        "provider_recovery_proven": bool(provider.get("recovery_proven")),
    }


def build_restart_continuity_snapshot(payload: dict[str, Any], *, launch_mode: str = "unspecified") -> dict[str, Any]:
    projection = _continuity_projection(payload)
    stable_projection = {
        key: value
        for key, value in projection.items()
        if key not in {"coordination_revision", "owner_present", "is_owner", "provider_status", "provider_recovery_proven"}
    }
    encoded = json.dumps(stable_projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": STARTUP_COHERENCE_SCHEMA_VERSION,
        "launch_mode": _text(launch_mode or "unspecified", 40),
        "continuity_digest": hashlib.sha256(encoded).hexdigest(),
        "project_present": bool(projection["project_id"]),
        "session_present": bool(projection["session_id"]),
        "draft_present": bool(projection["draft_digest"] or projection["draft_revision"]),
        "presentation_restored": bool(
            projection["follow_latest"] is False
            or projection["scroll_from_bottom_px"]
            or projection["view_anchor_turn_id"]
            or projection["view_anchor_offset_px"]
        ),
        "ownership_restored": bool(projection["owner_present"] or projection["is_owner"]),
        "provider_state": projection["provider_status"],
        "provider_recovery_proven": projection["provider_recovery_proven"],
        "accepted_message_replayed": False,
        "provider_request_repeated": False,
        "runtime_mutation_performed": False,
        "content_free": True,
        "private_values_included": False,
        "_projection": projection,
    }


def compare_restart_continuity(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_projection = left.get("_projection") if isinstance(left.get("_projection"), dict) else {}
    right_projection = right.get("_projection") if isinstance(right.get("_projection"), dict) else {}
    fields = (
        "project_id",
        "project_status",
        "session_id",
        "session_status",
        "turn_count",
        "draft_digest",
        "draft_revision",
        "follow_latest",
        "scroll_from_bottom_px",
        "view_anchor_turn_id",
        "view_anchor_offset_px",
        "selected_session_id",
    )
    checks = {field: left_projection.get(field) == right_projection.get(field) for field in fields}
    # Lease ownership can legitimately change between tabs or processes. Its state
    # must remain explicit, but it is not required for continuity parity.
    ownership_explicit = all(key in right_projection for key in ("owner_present", "is_owner", "coordination_revision"))
    provider_truthful = bool(right_projection.get("provider_status"))
    parity = all(checks.values()) and ownership_explicit and provider_truthful
    return {
        "ok": parity,
        "status": "parity" if parity else "drift_detected",
        "checks": checks,
        "ownership_state_explicit": ownership_explicit,
        "provider_state_explicit": provider_truthful,
        "provider_change_allowed": True,
        "accepted_message_replayed": False,
        "provider_request_repeated": False,
        "runtime_mutation_performed": False,
        "content_free": True,
        "private_values_included": False,
    }


def public_restart_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Remove the local comparison projection before returning a payload."""

    return {key: value for key, value in snapshot.items() if key != "_projection"}
