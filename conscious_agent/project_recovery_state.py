from __future__ import annotations

"""One content-free read-only project recovery view for dashboard use.

The state is assembled from existing project, session, switching, coordination, and
root-recovery stores. It never persists a second authority record and never returns
conversation text, draft text, source paths, preview tokens, backup paths, provider
payloads, or credentials.
"""

from datetime import datetime, timezone
from typing import Any

PROJECT_RECOVERY_STATE_SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_project(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(project.get("id") or ""),
        "name": str(project.get("name") or "Unknown project")[:160],
        "installed_version": str(project.get("installed_version") or "")[:80],
        "working_version": str(project.get("working_version") or project.get("version") or "")[:80],
        "candidate_version": str(project.get("candidate_version") or "")[:80],
        "current_milestone": str(project.get("current_milestone") or "")[:240],
    }


def _source_summary(binding: dict[str, Any]) -> dict[str, Any]:
    capability = binding.get("capability_state") if isinstance(binding.get("capability_state"), dict) else {}
    return {
        "status": str(binding.get("status") or "unknown")[:64],
        "available": bool(binding.get("source_root_accessible")),
        "identity_matches": bool(binding.get("source_identity_matches")),
        "version_matches": not bool(binding.get("version_mismatch")),
        "safe_to_modify": bool(binding.get("safe_to_modify")),
        "conversation_available": bool(capability.get("conversation_available", True)),
        "inspection_available": bool(capability.get("inspection_available", False)),
        "development_available": bool(capability.get("development_available", False)),
        "verification_available": bool(capability.get("verification_available", False)),
    }


def _pending_correction(project_id: str) -> dict[str, Any]:
    try:
        import project_root_recovery
        if hasattr(project_root_recovery, "pending_project_root_correction"):
            value = project_root_recovery.pending_project_root_correction(project_id)
            if isinstance(value, dict):
                return {
                    "pending": bool(value.get("pending")),
                    "status": str(value.get("status") or "none")[:64],
                    "project_id": str(value.get("project_id") or project_id),
                    "valid": bool(value.get("valid")),
                    "expires_at": str(value.get("expires_at") or ""),
                    "identity_evidence_matches": bool(value.get("identity_evidence_matches")),
                    "switch_revision_matches": bool(value.get("switch_revision_matches")),
                }
    except Exception:
        pass
    return {
        "pending": False,
        "status": "none",
        "project_id": project_id,
        "valid": False,
        "expires_at": "",
        "identity_evidence_matches": False,
        "switch_revision_matches": False,
    }


def build_project_recovery_state(
    project_id: str = "",
    *,
    tab_id: str = "",
    expected_switch_revision: int | None = None,
    restart_restored: bool = False,
    interrupted_switch: bool = False,
    include_conversation_details: bool = True,
) -> dict[str, Any]:
    import project_manager
    import project_switching_continuity as switching

    active = project_manager.get_active_project() or {}
    selected_id = str(project_id or active.get("id") or "eidolon").strip().lower() or "eidolon"
    selected = project_manager.get_project(selected_id) or active
    selected_id = str(selected.get("id") or selected_id)
    binding = project_manager.project_source_binding(selected_id)
    switch = switching.project_switch_snapshot(project_id=selected_id)
    conversation = switching.project_conversation_continuity(selected_id) if include_conversation_details else {}
    correction = _pending_correction(selected_id)

    coordination: dict[str, Any] = {}
    try:
        from conversation_tab_coordination import coordination_snapshot
        coordination = coordination_snapshot(tab_id=tab_id) if tab_id else coordination_snapshot()
    except Exception:
        coordination = {}

    current_revision = max(0, int(switch.get("revision") or 0))
    stale_tab = expected_switch_revision is not None and int(expected_switch_revision) != current_revision
    switch_pending = str(switch.get("last_switch_status") or "") == "pending"
    source_available = bool(binding.get("ok"))

    if stale_tab:
        status = "stale_tab"
    elif interrupted_switch:
        status = "interrupted_switch"
    elif switch_pending:
        status = "switch_pending"
    elif correction.get("pending"):
        status = "correction_pending"
    elif not source_available:
        status = "source_unavailable"
    elif restart_restored:
        status = "restart_restored"
    else:
        status = "healthy"

    messages = {
        "healthy": "The active project and its local conversation state are ready.",
        "source_unavailable": "Conversation remains available, but source inspection and development are paused until the project root is recovered.",
        "correction_pending": "A source-root correction is waiting for current operator review.",
        "switch_pending": "A confirmed project switch is being reconciled from persisted state.",
        "stale_tab": "This tab has an older project revision and must refresh before changing project state.",
        "interrupted_switch": "An interrupted project switch was reconciled from persisted state without replay.",
        "restart_restored": "The project, conversation, draft, and navigation state were restored after restart.",
    }
    return {
        "ok": True,
        "type": "project_recovery_state",
        "schema_version": PROJECT_RECOVERY_STATE_SCHEMA_VERSION,
        "status": status,
        "message": messages[status],
        "project": _safe_project(selected),
        "source": _source_summary(binding),
        "switch": {
            "revision": current_revision,
            "active_project_id": str(switch.get("active_project_id") or selected_id),
            "previous_project_id": str(switch.get("previous_project_id") or ""),
            "status": str(switch.get("last_switch_status") or "idle")[:64],
            "pending": switch_pending,
            "stale_tab": stale_tab,
        },
        "conversation": {
            "active_session_id": str(conversation.get("active_session_id") or ""),
            "session_count": max(0, int(conversation.get("session_count") or 0)),
            "draft_revision": max(0, int(conversation.get("draft_revision") or 0)),
            "has_draft": bool(conversation.get("has_draft")),
            "unfinished_session_count": max(0, int(conversation.get("unfinished_session_count") or 0)),
            "running_operation_count": max(0, int(conversation.get("running_operation_count") or 0)),
            "uncertain_operation_count": max(0, int(conversation.get("uncertain_operation_count") or 0)),
        },
        "root_correction": correction,
        "coordination": {
            "revision": max(0, int(coordination.get("revision") or 0)),
            "selected_project_id": str(coordination.get("selected_project_id") or ""),
            "selected_session_id": str(coordination.get("selected_session_id") or ""),
            "owner_present": bool(coordination.get("owner_present")),
            "is_owner": bool(coordination.get("is_owner")),
        },
        "controls": {
            "conversation_enabled": bool(_source_summary(binding)["conversation_available"]),
            "project_mutations_enabled": not stale_tab and not switch_pending,
            "refresh_required": stale_tab,
            "root_correction_confirmation_required": bool(correction.get("pending")),
            "keyboard_accessible": True,
            "narrow_layout_safe": True,
        },
        "restart_restored": bool(restart_restored),
        "accepted_turn_replayed": False,
        "switch_replayed": False,
        "root_correction_replayed": False,
        "provider_contacted": False,
        "captured_at": _now(),
        "content_free": True,
        "local_private": True,
    }


def project_recovery_state_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {
        "content", "draft_content", "conversation_content", "message_text", "prompt", "provider_payload",
        "credential", "secret", "preview_token", "backup_paths", "source_root", "candidate_source_root",
        "current_source_root", "transcript", "memory", "raw_response", "endpoint",
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


def restore_project_recovery_state() -> dict[str, Any]:
    """Revalidate and restore the active project after a fresh dashboard process.

    This reads persisted authority state, reconciles incomplete switching, restores
    project-local conversation selection, and revalidates any private correction
    preview. No accepted action is replayed.
    """
    import project_manager
    import project_switching_continuity as switching

    active = project_manager.get_active_project() or {}
    project_id = str(active.get("id") or "eidolon")
    restored = switching.restore_project_switch_continuity()
    interrupted = bool((restored.get("switching") or {}).get("restart_reconciled"))
    state = build_project_recovery_state(
        project_id,
        restart_restored=True,
        interrupted_switch=interrupted,
    )
    restored_summary = {
        "project_id": project_id,
        "active_session_id": str(restored.get("active_session_id") or ""),
        "draft_revision": max(0, int(restored.get("draft_revision") or 0)),
        "has_draft": bool(restored.get("has_draft")),
        "coordination_revision": max(0, int((restored.get("coordination") or {}).get("revision") or 0)),
    }
    state["restored"] = restored_summary
    # Compatibility aliases for established restart callers. These remain content-free.
    state.update({
        "project_id": restored_summary["project_id"],
        "project_name": str(active.get("name") or ""),
        "active_session_id": restored_summary["active_session_id"],
        "draft_revision": restored_summary["draft_revision"],
        "has_draft": restored_summary["has_draft"],
        # Compatibility aliases remain content-free. Older callers keep their
        # established keys without receiving raw source paths, marker lists,
        # switch keys, or other private recovery internals.
        "source_binding": {
            "ok": bool(state.get("source", {}).get("available") and state.get("source", {}).get("identity_matches")),
            "status": str(state.get("source", {}).get("status") or "unknown"),
            "project_id": restored_summary["project_id"],
            "project_name": str(active.get("name") or ""),
            **dict(state.get("source") or {}),
        },
        "switching": {
            **dict(state.get("switch") or {}),
            "restart_reconciled": interrupted,
            "switch_replayed": False,
            "content_free": True,
            "local_private": True,
        },
        "coordination": restored.get("coordination") or state.get("coordination") or {},
    })
    state["accepted_turn_replayed"] = False
    state["switch_replayed"] = False
    state["root_correction_replayed"] = False
    state["provider_contacted"] = False
    return state
