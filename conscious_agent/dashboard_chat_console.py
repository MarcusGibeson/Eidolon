from __future__ import annotations

import hmac
import json
import os
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Iterator

from lazy_imports import install_lazy_callables
from conversation_surface_contracts import ACTION_CANCEL, ACTION_RETRY, CURATABLE_RELATIONSHIP_TYPES
from dashboard_chat_styles import COMPANION_CHAT_STYLES
from chat_time_labels import day_label, time_label

from execution_claim_guard import (
    build_execution_truth_receipt,
    public_execution_receipt,
    render_receipt_bound_action_response,
    validate_execution_truth_receipt,
)
from mixed_intent_action_presentation import present_mixed_intent_action_response

from paths import DATA_DIR
from release_metadata import RUNTIME_UI_CONTRACT, RUNTIME_VERSION_TAG
from supervised_candidate_installation import is_candidate_review_installation_control
from supervised_development_continuation import is_supervised_development_continuation


MAX_GOVERNED_ACTION_OUTPUT_CHARS = 2_400
MAX_RESEARCH_REPORT_OUTPUT_CHARS = 12_000


# Conversation services are resolved only when their surface is used.
_LAZY_ATTENTION_CENTER_EXPORTS = install_lazy_callables(
    globals(),
    'attention_center',
    {
        'build_attention_center': 'build_attention_center',
    },
)

_LAZY_BRAIN_EXPORTS = install_lazy_callables(
    globals(),
    'brain',
    {
        'generate_inner_thought': 'generate_inner_thought',
    },
)

_LAZY_CHAT_EXPORTS = install_lazy_callables(
    globals(),
    'chat',
    {
        'build_chat_state': 'build_chat_state',
    },
)

_LAZY_CHAT_ACTION_ROUTER_EXPORTS = install_lazy_callables(
    globals(),
    'chat_action_router',
    {
        'classify_chat_action_follow_up': 'classify_chat_action_follow_up',
        'execute_chat_action': 'execute_chat_action',
        'list_chat_actions': 'list_chat_actions',
        'load_chat_action': 'load_chat_action',
        'propose_chat_action': 'propose_chat_action',
        'propose_ambiguous_chat_action_follow_up': 'propose_ambiguous_chat_action_follow_up',
        'propose_chat_action_follow_up': 'propose_chat_action_follow_up',
        'resolve_follow_up_target': 'resolve_follow_up_target',
        'select_follow_up_target': 'select_follow_up_target',
    },
)

_LAZY_CONVERSATION_QUALITY_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_quality',
    {
        'should_analyze_chat_action': 'should_analyze_chat_action',
    },
)

_LAZY_CONVERSATION_ACTION_PORTAL_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_action_portal',
    {
        'build_action_portal_state': 'build_action_portal_state',
        'sanitize_action_portal_state': 'sanitize_action_portal_state',
    },
)

_LAZY_DESIRES_EXPORTS = install_lazy_callables(
    globals(),
    'desires',
    {
        'load_desires': 'load_desires',
    },
)

_LAZY_MEMORY_EXPORTS = install_lazy_callables(
    globals(),
    'memory',
    {
        'load_memories': 'load_memories',
        'store_memory_batch': 'store_memory_batch',
    },
)

_LAZY_REFLECTION_EXPORTS = install_lazy_callables(
    globals(),
    'reflection',
    {
        'reflect_on_thought': 'reflect_on_thought',
    },
)

_LAZY_RELATIONSHIP_CONTINUITY_EXPORTS = install_lazy_callables(
    globals(),
    'relationship_continuity',
    {
        'build_relationship_continuity_snapshot': 'build_relationship_continuity_snapshot',
    },
)

_LAZY_PROVIDER_RECOVERY_EVIDENCE_EXPORTS = install_lazy_callables(
    globals(),
    'provider_recovery_evidence',
    {
        'provider_resume_cue': 'provider_resume_cue',
    },
)

_LAZY_RELATIONSHIP_MEMORY_CURATION_EXPORTS = install_lazy_callables(
    globals(),
    'relationship_memory_curation',
    {
        'relationship_memory_curation_summary': 'relationship_memory_curation_summary',
    },
)

_LAZY_ENTITY_ASSOCIATION_CURATION_EXPORTS = install_lazy_callables(
    globals(),
    'entity_association_curation',
    {
        'entity_association_curation_summary': 'entity_association_curation_summary',
        'list_entity_association_records': 'list_entity_association_records',
    },
)

_LAZY_SELF_MODEL_EXPORTS = install_lazy_callables(
    globals(),
    'self_model',
    {
        'load_self_model': 'load_self_model',
    },
)

_LAZY_SETTINGS_MANAGER_EXPORTS = install_lazy_callables(
    globals(),
    'settings_manager',
    {
        'load_settings': 'load_settings',
    },
)

_LAZY_CONVERSATION_RUNTIME_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_runtime',
    {
        'run_conversation_turn': 'run_conversation_turn',
        'stream_conversation_turn': 'stream_conversation_turn',
    },
)

_LAZY_CONVERSATION_EXPERIENCE_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_experience',
    {
        'build_conversation_experience_state': 'build_conversation_experience_state',
        'redacted_turn_diagnostics': 'redacted_turn_diagnostics',
        'turn_experience_state': 'turn_experience_state',
    },
)

_LAZY_CONVERSATION_RECOVERY_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_recovery',
    {
        'recovery_state': 'recovery_state',
        'retry_failed_conversation_turn': 'retry_failed_conversation_turn',
    },
)

_LAZY_CONVERSATION_RECOVERY_CONTRACT_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_recovery_contract',
    {
        'conversation_recovery_contract': 'conversation_recovery_contract',
    },
)

_LAZY_CONVERSATION_TURN_PRESENTATION_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_turn_presentation',
    {
        'build_turn_presentation': 'build_turn_presentation',
    },
)

_LAZY_CONVERSATION_LIFECYCLE_RECOVERY_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_lifecycle_recovery',
    {
        'lifecycle_recovery_plan': 'lifecycle_recovery_plan',
    },
)

_LAZY_CONVERSATION_RESEND_LINEAGE_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_resend_lineage',
    {
        'claim_explicit_resend': 'claim_explicit_resend',
        'finalize_explicit_resend': 'finalize_explicit_resend',
        'find_resend_lineage_by_acceptance_key': 'find_resend_lineage_by_acceptance_key',
        'resend_candidate_for_session': 'resend_candidate_for_session',
    },
)

_LAZY_CONVERSATION_OPERATIONS_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_operations',
    {
        'acknowledge_operation_marker': 'acknowledge_operation_marker',
        'claim_operation_acceptance': 'claim_operation_acceptance',
        'create_operation_marker': 'create_operation_marker',
        'finalize_operation_marker': 'finalize_operation_marker',
        'find_operation_by_acceptance_key': 'find_operation_by_acceptance_key',
        'latest_operation_marker': 'latest_operation_marker',
        'load_operation_acknowledgement': 'load_operation_acknowledgement',
        'load_operation_marker': 'load_operation_marker',
        'mark_operation_client_disconnected': 'mark_operation_client_disconnected',
        'new_client_acceptance_key': 'new_client_acceptance_key',
        'new_conversation_operation_id': 'new_conversation_operation_id',
        'operation_cue_token': 'operation_cue_token',
        'request_operation_cancellation': 'request_operation_cancellation',
    },
)

_LAZY_CONVERSATION_SESSIONS_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_sessions',
    {
        'append_conversation_turn': 'append_conversation_turn',
        'archive_conversation_session': 'archive_conversation_session',
        'clear_conversation_draft': 'clear_conversation_draft',
        'conversation_history_for_prompt': 'conversation_history_for_prompt',
        'build_conversation_session_catalog_page': 'conversation_session_catalog_page',
        'conversation_session_turns': 'conversation_session_turns',
        'conversation_session_turn_window': 'conversation_session_turn_window',
        'get_active_conversation_session': 'get_active_conversation_session',
        'list_conversation_sessions': 'list_conversation_sessions',
        'load_conversation_draft': 'load_conversation_draft',
        'load_conversation_controls': 'load_conversation_controls',
        'rename_conversation_session': 'rename_conversation_session',
        'resolve_conversation_session': 'resolve_conversation_session',
        'restore_conversation_session': 'restore_conversation_session',
        'update_conversation_turn_action': 'update_conversation_turn_action',
    },
)

_LAZY_CONVERSATION_NAVIGATION_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_navigation',
    {
        'load_conversation_presentation_state': 'load_conversation_presentation_state',
    },
)

_LAZY_CONVERSATION_OFFLINE_DURABILITY_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_offline_durability',
    {
        'offline_session_durability_state': 'offline_session_durability_state',
    },
)

_LAZY_CONVERSATION_OFFLINE_DEGRADATION_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_offline_degradation',
    {
        'offline_conversation_degradation_state': 'offline_conversation_degradation_state',
    },
)

_LAZY_CONVERSATION_LONG_SESSION_HARDENING_EXPORTS = install_lazy_callables(
    globals(),
    'conversation_long_session_hardening',
    {
        'build_long_session_hardening_state': 'build_long_session_hardening_state',
    },
)

_LAZY_MESSAGING_RESILIENCE_EXPORTS = install_lazy_callables(
    globals(),
    'messaging_resilience',
    {
        'build_operation_reconciliation': 'build_operation_reconciliation',
    },
)



def _safe(value: Any) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def _provider_settings_href() -> str:
    return "/local-model?return_to=chat#local-model-config-form"


def _provider_readiness_href() -> str:
    return "/local-model?return_to=chat&run_readiness=1#local-model-availability"


@dataclass
class _DashboardOperationJob:
    operation_id: str
    session_id: str
    turn_id: str
    cancel_event: threading.Event = field(default_factory=threading.Event)
    condition: threading.Condition = field(default_factory=threading.Condition)
    events: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False

    def append(self, item: dict[str, Any]) -> None:
        with self.condition:
            self.events.append(dict(item))
            self.condition.notify_all()

    def finish(self) -> None:
        with self.condition:
            self.done = True
            self.condition.notify_all()


_DASHBOARD_OPERATION_LOCK = threading.RLock()
_DASHBOARD_OPERATION_JOBS: dict[str, _DashboardOperationJob] = {}


def _active_dashboard_operation_ids() -> set[str]:
    with _DASHBOARD_OPERATION_LOCK:
        return {operation_id for operation_id, job in _DASHBOARD_OPERATION_JOBS.items() if not job.done}


def _discard_dashboard_operation_job(operation_id: str) -> None:
    with _DASHBOARD_OPERATION_LOCK:
        job = _DASHBOARD_OPERATION_JOBS.get(operation_id)
        if job is None or not job.done:
            return
        job.events.clear()
        _DASHBOARD_OPERATION_JOBS.pop(operation_id, None)


def _session_turn_for_operation(session_id: str, operation_id: str) -> dict[str, Any] | None:
    for turn in conversation_session_turns(session_id):
        if str(turn.get("id") or "") == str(operation_id or ""):
            return dict(turn)
    return None


def _run_dashboard_operation_job(
    job: _DashboardOperationJob,
    *,
    message: str,
    use_ai: bool,
    transient_instruction: str = "",
    transient_instruction_scope: str = "current_turn",
) -> None:
    runtime_result: dict[str, Any] = {}
    try:
        stream_options = {
            "use_ai": use_ai,
            "cancel_event": job.cancel_event,
            "session_id": job.session_id,
            "operation_id": job.operation_id,
            "draft_already_cleared": True,
        }
        if str(transient_instruction or "").strip():
            stream_options["transient_instruction"] = transient_instruction
            stream_options["transient_instruction_scope"] = transient_instruction_scope
        from live_cognitive_activity_v2510 import project_live_activity
        from internal_voice_projection_v2512 import project_activity_internal_voice
        from state_grounded_internal_voice_v2523 import project_activity_internal_voice_beta
        from foreground_cognitive_observability_v2536 import record_foreground_observability_event
        for item in stream_dashboard_chat_turn(message, **stream_options):
            activity = project_live_activity(item, operation_id=job.operation_id)
            if activity:
                job.append(activity)
                try:
                    record_foreground_observability_event(activity, operation_id=job.operation_id)
                except (OSError, ValueError):
                    pass
                legacy_voice = project_activity_internal_voice(activity)
                voice = project_activity_internal_voice_beta(activity) or legacy_voice
                if voice:
                    job.append(voice)
                    try:
                        record_foreground_observability_event(voice, operation_id=job.operation_id)
                    except (OSError, ValueError):
                        pass
            job.append(item)
            if str(item.get("event") or "") == "done":
                turn = item.get("turn") if isinstance(item.get("turn"), dict) else {}
                candidate = turn.get("conversation_runtime") if isinstance(turn.get("conversation_runtime"), dict) else {}
                runtime_result = dict(candidate)
                if not runtime_result and isinstance(item.get("result"), dict):
                    runtime_result = dict(item.get("result") or {})
    except Exception as error:
        runtime_result = {
            "operation_id": job.operation_id,
            "session_id": job.session_id,
            "success": False,
            "completion_state": "failed",
            "failure_category": "dashboard_operation_failure",
            "session_turn_recorded": False,
            "error_type": type(error).__name__,
        }
        job.append({
            "event": "error",
            "operation_id": job.operation_id,
            "failure_category": "dashboard_operation_failure",
            "message": "The accepted conversation operation stopped safely.",
        })
        job.append({"event": "done", "operation_id": job.operation_id, "result": runtime_result})
    finally:
        completion_state = str(runtime_result.get("completion_state") or "uncertain")
        finalize_operation_marker(
            job.operation_id,
            completion_state=completion_state,
            success=bool(runtime_result.get("success")),
            failure_category=str(runtime_result.get("failure_category") or ""),
            final_session_turn_recorded=bool(runtime_result.get("session_turn_recorded")),
        )
        job.finish()
        cleanup = threading.Timer(60.0, _discard_dashboard_operation_job, args=(job.operation_id,))
        cleanup.daemon = True
        cleanup.start()


def start_dashboard_chat_operation(
    user_message: str,
    *,
    use_ai: bool = True,
    session_id: str = "",
    acceptance_key: str = "",
    resend_source_acceptance_key: str = "",
    resend_evidence_token: str = "",
    transient_instruction: str = "",
    transient_instruction_scope: str = "current_turn",
) -> dict[str, Any]:
    """Accept one browser turn once, then run it independently of the viewer socket."""
    message = str(user_message or "").strip()
    if not message:
        raise ValueError("Conversation message cannot be empty.")
    session = resolve_conversation_session(session_id, create_if_missing=True) or {}
    resolved_session_id = str(session.get("id") or "")
    if not resolved_session_id:
        raise ValueError("Conversation session could not be resolved.")
    from project_manager import get_active_project
    from conversation_sessions import _session_project_id
    active_project = get_active_project() or {}
    active_project_id = str(active_project.get("id") or "eidolon")
    session_project_id = _session_project_id(session)
    if session_project_id != active_project_id:
        raise ValueError("Conversation operation belongs to a different active project. Switch back before accepting a new turn there.")
    key = str(acceptance_key or "").strip() or new_client_acceptance_key()
    resend_source = str(resend_source_acceptance_key or "").strip()
    resend_token = str(resend_evidence_token or "").strip()
    resend_lineage = None
    if resend_source or resend_token:
        if not resend_source or not resend_token:
            raise ValueError("Explicit resend lineage requires both the original acceptance identity and its evidence token.")
        resend_lineage = claim_explicit_resend(
            resolved_session_id,
            resend_source,
            key,
            source_evidence_token=resend_token,
        )
        if resend_lineage.get("state") == "accepted" and resend_lineage.get("operation_id"):
            accepted_marker = load_operation_marker(str(resend_lineage.get("operation_id") or ""))
            if accepted_marker:
                return {"operation": accepted_marker, "duplicate_acceptance": True, "resend_lineage": resend_lineage}
    with _DASHBOARD_OPERATION_LOCK:
        existing = find_operation_by_acceptance_key(resolved_session_id, key)
        if existing:
            if resend_source:
                resend_lineage = finalize_explicit_resend(resolved_session_id, resend_source, key, str(existing.get("operation_id") or ""))
            return {"operation": existing, "duplicate_acceptance": True, "resend_lineage": resend_lineage}

        operation_id = new_conversation_operation_id()
        acceptance_claim = claim_operation_acceptance(resolved_session_id, key, operation_id)
        if not acceptance_claim.get("claimed"):
            claimed_operation_id = str(acceptance_claim.get("operation_id") or "")
            marker = None
            for _attempt in range(20):
                marker = load_operation_marker(claimed_operation_id)
                if marker:
                    break
                import time as _time
                _time.sleep(0.01)
            if marker:
                return {"operation": marker, "duplicate_acceptance": True, "resend_lineage": resend_lineage, "acceptance_claim": acceptance_claim}
            raise ValueError("The accepted turn is still being claimed. No duplicate provider request was started.")
        turn_id = _new_turn_id(message)
        marker = create_operation_marker(
            operation_id,
            resolved_session_id,
            streaming=True,
            acceptance_key=key,
        )
        if resend_source:
            resend_lineage = finalize_explicit_resend(resolved_session_id, resend_source, key, operation_id)
        clear_conversation_draft(resolved_session_id, source="dashboard_chat_stream_acceptance")
        job = _DashboardOperationJob(operation_id=operation_id, session_id=resolved_session_id, turn_id=turn_id)
        _DASHBOARD_OPERATION_JOBS[operation_id] = job
    thread = threading.Thread(
        target=_run_dashboard_operation_job,
        kwargs={
            "job": job,
            "message": message,
            "use_ai": bool(use_ai),
            "transient_instruction": str(transient_instruction or ""),
            "transient_instruction_scope": str(transient_instruction_scope or "current_turn"),
        },
        name=f"eidolon-chat-{operation_id[-12:]}",
        daemon=True,
    )
    thread.start()
    return {"operation": marker, "duplicate_acceptance": False, "resend_lineage": resend_lineage, "acceptance_claim": acceptance_claim}


def subscribe_dashboard_chat_operation(operation_id: str, *, start_index: int = 0) -> Iterator[dict[str, Any]]:
    """Yield in-memory live events. Persisted reconciliation never depends on this buffer."""
    with _DASHBOARD_OPERATION_LOCK:
        job = _DASHBOARD_OPERATION_JOBS.get(str(operation_id or ""))
    if job is None:
        marker = load_operation_marker(operation_id)
        if marker:
            yield {"event": "operation", "operation": marker}
            turn = _session_turn_for_operation(str(marker.get("session_id") or ""), str(marker.get("operation_id") or ""))
            yield {"event": "done", "operation_id": operation_id, "operation": marker, "session_turn": turn}
        return
    index = max(0, int(start_index))
    while True:
        keepalive = False
        with job.condition:
            while index >= len(job.events) and not job.done:
                job.condition.wait(timeout=0.75)
                if index >= len(job.events) and not job.done:
                    keepalive = True
                    break
            pending = [dict(item) for item in job.events[index:]]
            index = len(job.events)
            done = job.done and index >= len(job.events)
        if keepalive and not pending:
            yield {"event": "keepalive", "operation_id": job.operation_id}
        for item in pending:
            yield item
        if done:
            return


def detach_dashboard_chat_operation(operation_id: str) -> dict[str, Any] | None:
    """Detach only the viewer; provider cancellation remains an explicit separate action."""
    return mark_operation_client_disconnected(operation_id)


def _chat_action_for_operation(operation_id: str) -> dict[str, Any] | None:
    token = str(operation_id or "").strip()
    if not token:
        return None
    return next(
        (item for item in list_chat_actions(include_closed=True) if str(item.get("deduplication_key") or "") == token),
        None,
    )


def _live_action_portal(action: dict[str, Any] | None) -> dict[str, Any] | None:
    if not action:
        return None
    result = action.get("result") if isinstance(action.get("result"), dict) else None
    portal = build_action_portal_state(action, result)
    if not portal:
        return None
    try:
        from conversational_research_actions import conversational_research_comparison, conversational_research_export, conversational_research_history, conversational_research_progress, conversational_research_review
    except ImportError:
        from conversational_research_actions import conversational_research_comparison, conversational_research_export, conversational_research_history, conversational_research_progress, conversational_research_review
    progress = conversational_research_progress(action)
    review = conversational_research_review(action)
    history = conversational_research_history(action)
    comparison = conversational_research_comparison(action)
    research_export = conversational_research_export(action)
    if progress:
        portal["research_progress"] = progress
        if portal.get("status") == "running":
            portal["message"] = (
                f"Research is {int(progress.get('progress_percent') or 0)}% complete at "
                f"{str(progress.get('progress_stage') or 'starting').replace('_', ' ')}. "
                "Refresh or reconnect will inspect this same session without replaying requests."
            )
    if review:
        portal["research_review"] = review
    if history:
        portal["research_history"] = history
    if comparison:
        portal["research_comparison"] = comparison
    if research_export:
        portal["research_export"] = research_export
    return portal


def cancel_dashboard_chat_operation(operation_id: str, *, project_id: str = "") -> dict[str, Any]:
    token = str(operation_id or "").strip()
    marker = load_operation_marker(token)
    if not marker:
        return {"ok": False, "operation_id": token, "status": "not_found", "message": "Conversation operation was not found."}
    state = str(marker.get("public_state") or "running")
    if state != "running":
        return {
            "ok": False,
            "operation_id": token,
            "status": state,
            "message": "The conversation operation already reached a terminal state.",
        }
    marker_project_id = str(marker.get("project_id") or "eidolon")
    expected_project_id = str(project_id or "").strip().lower()
    if expected_project_id and expected_project_id != marker_project_id:
        return {
            "ok": False,
            "operation_id": token,
            "status": "project_mismatch",
            "project_id": marker_project_id,
            "message": "This operation belongs to a different project and was not cancelled.",
            "operation": marker,
        }
    already_requested = bool(marker.get("cancellation_requested"))
    marker = request_operation_cancellation(token, expected_project_id=expected_project_id) or marker
    if marker.get("cancellation_rejected"):
        return {
            "ok": False,
            "operation_id": token,
            "status": str(marker.get("cancellation_rejection") or "cancellation_rejected"),
            "project_id": marker_project_id,
            "message": "This operation was not cancelled because its project binding did not match.",
            "operation": marker,
        }
    state_after_request = str(marker.get("public_state") or "running")
    if state_after_request != "running":
        return {
            "ok": False,
            "operation_id": token,
            "status": state_after_request,
            "message": "The conversation operation reached a terminal state before cancellation could be applied.",
            "operation": marker,
        }
    governed_action = _chat_action_for_operation(token)
    research_cancellation = None
    if governed_action:
        try:
            from conversational_research_actions import cancel_research_for_conversation_operation
        except ImportError:
            from conversational_research_actions import cancel_research_for_conversation_operation
        research_cancellation = cancel_research_for_conversation_operation(
            governed_action,
            event_id=f"dashboard-operation:{token}:research-cancel",
        )
    with _DASHBOARD_OPERATION_LOCK:
        job = _DASHBOARD_OPERATION_JOBS.get(token)
    if job is not None:
        job.cancel_event.set()
    # The runtime registry closes an active provider client when one is available.
    from conversation_runtime import cancel_conversation_operation
    runtime_result = cancel_conversation_operation(token)
    return {
        "ok": True,
        "operation_id": token,
        "status": "cancellation_requested",
        "duplicate_request": already_requested,
        "runtime_status": str(runtime_result.get("status") or ""),
        "message": (
            "Research cancellation and conversation cancellation were requested for this exact operation."
            if research_cancellation is not None
            else "Conversation cancellation was requested for this exact operation."
        ),
        "research_cancellation": research_cancellation,
        "operation": marker,
        "operation_reconciliation": build_operation_reconciliation(
            marker,
            runtime_active=job is not None and not job.done,
            session_turn_present=False,
            resend_lineage_present=False,
        ),
    }


def _action_portal_for_operation(operation_id: str) -> dict[str, Any] | None:
    return _live_action_portal(_chat_action_for_operation(operation_id))


def dashboard_chat_operation_status(
    *,
    operation_id: str = "",
    session_id: str = "",
    acceptance_key: str = "",
) -> dict[str, Any]:
    try:
        marker = load_operation_marker(operation_id) if operation_id else None
        if marker is None and session_id and acceptance_key:
            marker = find_operation_by_acceptance_key(session_id, acceptance_key)
        if marker is None and session_id:
            marker = latest_operation_marker(session_id)
    except ValueError as error:
        return {"ok": False, "error": str(error), "operation": None, "session_turn": None}
    if marker is None:
        return {"ok": True, "operation": None, "session_turn": None}
    if (
        str(marker.get("public_state") or "running") == "running"
        and str(marker.get("operation_id") or "") not in _active_dashboard_operation_ids()
    ):
        marker = dict(marker)
        marker["public_state"] = "uncertain"
        marker["failure_category"] = "runtime_status_unknown_after_restart"
        marker["completed_at"] = ""
    turn = None
    recovery = None
    if marker.get("final_session_turn_recorded"):
        turn = _session_turn_for_operation(str(marker.get("session_id") or ""), str(marker.get("operation_id") or ""))
        if turn and str(marker.get("public_state") or "") != "running":
            try:
                recovery = recovery_state(str(marker.get("session_id") or ""), str(marker.get("operation_id") or ""))
            except ValueError:
                recovery = None
    resend_lineage = None
    try:
        resend_lineage = find_resend_lineage_by_acceptance_key(
            str(marker.get("session_id") or ""),
            str(marker.get("acceptance_key") or ""),
        )
    except ValueError:
        resend_lineage = None
    reconciliation = build_operation_reconciliation(
        marker,
        runtime_active=str(marker.get("operation_id") or "") in _active_dashboard_operation_ids(),
        session_turn_present=bool(turn),
        resend_lineage_present=bool(resend_lineage),
    )
    return {
        "ok": True,
        "operation": marker,
        "operation_reconciliation": reconciliation,
        "session_turn": turn,
        "recovery": recovery,
        "resend_lineage": resend_lineage,
        "action_portal": _action_portal_for_operation(str(marker.get("operation_id") or "")),
        "session_cue": _operation_cue_from_marker(marker),
        "turn_presentation": build_turn_presentation(marker, turn=turn, recovery=recovery, resend_lineage=resend_lineage),
        "recovery_contract": conversation_recovery_contract(str(marker.get("session_id") or "")),
    }



_SESSION_CUE_PRESENTATIONS: dict[str, tuple[str, str, bool]] = {
    "running": ("still_responding", "Still responding", False),
    "completed": ("reply_ready", "Reply ready", True),
    "failed": ("needs_recovery", "Needs recovery", True),
    "cancelled": ("cancelled", "Cancelled", True),
    "uncertain": ("completion_uncertain", "Completion uncertain", True),
}


def _operation_cue_from_marker(
    marker: dict[str, Any] | None,
    *,
    include_token: bool = False,
    ignore_acknowledgement: bool = False,
) -> dict[str, Any] | None:
    if not isinstance(marker, dict):
        return None
    state = str(marker.get("public_state") or "uncertain").strip().lower()
    presentation = _SESSION_CUE_PRESENTATIONS.get(state)
    if not presentation:
        return None
    if state == "completed" and not (marker.get("client_disconnected") or marker.get("reconciled_late")):
        return None
    operation_id = str(marker.get("operation_id") or "")
    if not operation_id:
        return None
    acknowledgement = load_operation_acknowledgement(operation_id)
    if acknowledgement and state != "running" and not ignore_acknowledgement:
        return None
    kind, label, acknowledgeable = presentation
    cue = {
        "kind": kind,
        "label": label,
        "public_state": state,
        "acknowledgeable": bool(acknowledgeable),
    }
    if include_token:
        cue["acknowledgement_token"] = operation_cue_token(marker, public_state=state)
    return cue


def dashboard_session_operation_cue(session_id: str, *, include_token: bool = False) -> dict[str, Any] | None:
    status = dashboard_chat_operation_status(session_id=session_id)
    marker = status.get("operation") if isinstance(status.get("operation"), dict) else None
    return _operation_cue_from_marker(marker, include_token=include_token)


def acknowledge_dashboard_session_operation_cue(
    session_id: str,
    *,
    acknowledgement_token: str = "",
    operation_id: str = "",
) -> dict[str, Any]:
    """Acknowledge only the latest exact terminal cue; GET/render paths never call this."""
    status = dashboard_chat_operation_status(session_id=session_id)
    marker = status.get("operation") if isinstance(status.get("operation"), dict) else None
    if not marker:
        return {"ok": False, "status": "not_found", "message": "No conversation update is waiting to be acknowledged."}
    marker_operation_id = str(marker.get("operation_id") or "")
    if not str(operation_id or "").strip() and not str(acknowledgement_token or "").strip():
        return {"ok": False, "status": "exact_selector_required", "message": "An exact conversation cue selector is required."}
    if operation_id and str(operation_id).strip() != marker_operation_id:
        return {"ok": False, "status": "stale", "message": "A newer conversation operation is now current."}
    cue = _operation_cue_from_marker(marker, include_token=True, ignore_acknowledgement=True)
    if not cue or not cue.get("acknowledgeable"):
        return {"ok": False, "status": "not_acknowledgeable", "message": "This conversation update is not acknowledgeable."}
    expected = str(cue.get("acknowledgement_token") or "")
    supplied = str(acknowledgement_token or "").strip()
    if supplied and not hmac.compare_digest(supplied, expected):
        return {"ok": False, "status": "stale", "message": "The conversation cue changed before acknowledgement."}
    existing = load_operation_acknowledgement(marker_operation_id)
    if existing:
        return {
            "ok": True,
            "status": "already_acknowledged",
            "changed": False,
            "session_id": str(marker.get("session_id") or ""),
            "session_cue": None,
        }
    record = acknowledge_operation_marker(
        marker_operation_id,
        str(marker.get("session_id") or ""),
        public_state=str(marker.get("public_state") or "uncertain"),
        source="dashboard_chat_session_cue",
    )
    return {
        "ok": True,
        "status": "acknowledged",
        "changed": bool(record.get("changed")),
        "session_id": str(marker.get("session_id") or ""),
        "session_cue": None,
    }


def _render_provider_recovery_resume_cue(cue: dict[str, Any]) -> str:
    visible = bool(cue.get("visible"))
    state = str(cue.get("state") or "unknown")
    hidden = "" if visible else " hidden"
    checked_at = str(cue.get("checked_at") or "Not checked")
    resume_text = "Composition may resume explicitly." if cue.get("can_resume_composition") else "Configured-provider recovery is not yet proven."
    return (
        f"<section class='provider-recovery-resume-cue' id='provider-recovery-resume-cue' data-state='{_safe(state)}'{hidden}>"
        f"<strong id='provider-recovery-resume-label'>{_safe(cue.get('label') or 'Provider readiness')}</strong>"
        f"<span id='provider-recovery-resume-detail'>{_safe(cue.get('detail') or '')}</span>"
        f"<small id='provider-recovery-resume-time'>Last persisted check: {_safe(checked_at)} Â· {_safe(resume_text)} No accepted request is replayed.</small>"
        "<div class='provider-recovery-actions'>"
        "<a class='chat-check-provider' href='/local-model?return_to=chat&run_readiness=1#local-model-availability'>Check configured provider</a>"
        f"<a class='chat-open-provider-settings' href='{_provider_settings_href()}'>Open provider settings</a>"
        "</div></section>"
    )


def _render_conversation_recovery_contract(contract: dict[str, Any]) -> str:
    state = str(contract.get("state") or "ready")
    hidden = " hidden" if state == "ready" else ""
    return (
        f"<section class='chat-recovery-contract' id='chat-recovery-contract' data-state='{_safe(state)}'{hidden}>"
        f"<strong id='chat-recovery-contract-label'>{_safe(contract.get('label') or 'Conversation recovery')}</strong>"
        f"<span id='chat-recovery-contract-detail'>{_safe(contract.get('detail') or '')}</span>"
        "<small>Recovery remains explicit. Accepted requests are never replayed, and deterministic local notices are not model responses.</small>"
        "</section>"
    )


def _render_reentry_cue_row(
    session: dict[str, Any],
    cue: dict[str, Any],
    *,
    active_session_id: str,
) -> str:
    session_id = str(session.get("id") or "")
    title = str(session.get("title") or "New conversation")
    kind = str(cue.get("kind") or "")
    label = str(cue.get("label") or "")
    acknowledgeable = bool(cue.get("acknowledgeable"))
    token = str(cue.get("acknowledgement_token") or "")
    is_active = session_id == active_session_id
    hidden_ack = (
        f"<input type='hidden' name='acknowledgement_token' value='{_safe(token)}'>"
        if acknowledgeable and token else ""
    )
    if is_active and acknowledgeable:
        action = (
            "<form method='post' action='/action' class='inline chat-session-cue-ack-form'>"
            "<input type='hidden' name='action' value='dashboard_chat_operation_cue_acknowledge'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            f"{hidden_ack}<button type='submit'>Mark seen</button></form>"
        )
    elif is_active:
        action = ""
    else:
        open_action = (
            "<form method='post' action='/action' class='inline chat-session-open-form' data-chat-session-open>"
            "<input type='hidden' name='action' value='dashboard_chat_session_select'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            "<button type='submit'>Open</button></form>"
        )
        seen_action = (
            "<form method='post' action='/action' class='inline chat-session-open-seen-form' data-chat-session-open-seen>"
            "<input type='hidden' name='action' value='dashboard_chat_session_select_and_acknowledge'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            f"{hidden_ack}<button type='submit'>Open and mark seen</button></form>"
            if acknowledgeable and token else ""
        )
        action = open_action + seen_action
    return (
        f"<li class='conversation-reentry-cue' data-session-cue-session-id='{_safe(session_id)}' "
        f"data-cue-kind='{_safe(kind)}'><b>{_safe(title)}</b>"
        f"<span class='conversation-reentry-cue-state' data-session-operation-cue>{_safe(label)}</span>{action}</li>"
    )

def _render_turn_diagnostics(turn: dict[str, Any], *, session_id: str = "") -> str:
    diagnostic = redacted_turn_diagnostics(turn)
    evidence = diagnostic.get("evidence") or {}
    evidence_rows = "".join(
        f"<li><code>{_safe(key)}</code>: {_safe(value)}</li>"
        for key, value in sorted(evidence.items())
    ) or "<li>No additional bounded evidence was recorded.</li>"
    status_code = diagnostic.get("status_code")
    return (
        "<details class='chat-turn-diagnostics'>"
        "<summary>Technical details</summary>"
        "<div class='chat-diagnostic-grid'>"
        f"<span>Category: <code>{_safe(diagnostic.get('technical_category'))}</code></span>"
        f"<span>Provider: <b>{_safe(diagnostic.get('provider'))}</b></span>"
        f"<span>Model: <b>{_safe(diagnostic.get('model'))}</b></span>"
        f"<span>Endpoint: <code>{_safe(diagnostic.get('endpoint'))}</code></span>"
        f"<span>HTTP status: <b>{_safe(status_code if status_code is not None else 'not available')}</b></span>"
        f"<span>Transport retryable: <b>{_safe(diagnostic.get('retryable'))}</b></span>"
        f"<span>Acceptance proven: <b>{_safe(recovery_state(str(session_id or turn.get('session_id') or ''), str(turn.get('id') or '')).get('acceptance_proven'))}</b></span>"
        "</div>"
        f"<ul class='chat-diagnostic-evidence'>{evidence_rows}</ul>"
        "<small>Only bounded redacted fields are shown. Prompts, raw responses, credentials, receipts, and stack traces are never displayed.</small>"
        "</details>"
    )


def _render_completed_turn_controls(session_id: str, turn: dict[str, Any]) -> str:
    """Render explicit completed-turn actions without rewriting the source turn."""
    if turn.get("success") is not True or str(turn.get("completion_state") or "") != "completed":
        return ""
    turn_id = str(turn.get("id") or "")
    user_message = str(turn.get("user_message") or "")
    if not turn_id or not user_message.strip():
        return ""
    shared = (
        f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
        f"<input type='hidden' name='turn_id' value='{_safe(turn_id)}'>"
        "<input type='hidden' name='use_ai' value='true'>"
    )
    return (
        f"<details class='chat-completed-turn-controls' data-turn-id='{_safe(turn_id)}'>"
        "<summary>Retry, regenerate, or branch</summary>"
        "<p><small>These are distinct explicit actions. Regenerate preserves the original reply and reuses its user-memory lineage. Resend creates a fresh user turn. Editing creates a new conversation branch and does not send automatically.</small></p>"
        "<div class='inline'>"
        "<form method='post' action='/action' class='inline chat-turn-regenerate-form'>"
        "<input type='hidden' name='action' value='dashboard_chat_turn_regenerate'>"
        f"{shared}<button type='submit' data-tip='Generate a new response in a fresh operation while preserving the original completed turn.'>Regenerate response</button></form>"
        "<form method='post' action='/action' class='inline chat-turn-resend-form'>"
        "<input type='hidden' name='action' value='dashboard_chat_turn_resend'>"
        f"{shared}<button type='submit' data-tip='Send the same user message as a new turn with a fresh acceptance identity.'>Resend as new turn</button></form>"
        "</div>"
        "<details class='chat-turn-branch-editor'><summary>Edit into a new branch</summary>"
        "<form method='post' action='/action' class='chat-turn-branch-form'>"
        "<input type='hidden' name='action' value='dashboard_chat_turn_branch'>"
        f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
        f"<input type='hidden' name='turn_id' value='{_safe(turn_id)}'>"
        "<label><small>Edited user message</small>"
        f"<textarea name='edited_user_message' rows='3' maxlength='20000' required>{_safe(user_message)}</textarea></label>"
        "<label><small>Optional branch title</small><input name='title' maxlength='72' placeholder='Branch of this conversation'></label>"
        "<button type='submit' data-tip='Create a separate private conversation and save this edit as an unsent draft. The original transcript is not changed.'>Create branch draft</button>"
        "</form></details></details>"
    )


def _render_turn_recovery_controls(session_id: str, turn: dict[str, Any]) -> str:
    presentation = turn_experience_state(turn)
    recovery = recovery_state(session_id, str(turn.get("id") or ""))
    controls: list[str] = []
    recovered_turn_id = str(recovery.get("successful_recovery_turn_id") or "")
    attempt_count = int(recovery.get("recovery_attempt_count") or 0)
    latest_state = str(recovery.get("latest_recovery_state") or "none")
    history_note = ""
    if attempt_count:
        history_note = (
            f"<small class='muted chat-recovery-history' data-recovery-attempt-count='{attempt_count}'>"
            f"Linked recovery history: {attempt_count} explicit attempt{'s' if attempt_count != 1 else ''}; latest state {_safe(latest_state)}. Earlier evidence remains preserved.</small>"
        )
    if recovered_turn_id:
        return (
            history_note
            + "<small class='muted chat-recovery-note'>Recovered successfully in a later linked turn. The original failed turn remains excluded from prompt history.</small>"
            + _render_turn_diagnostics(turn, session_id=session_id)
        )
    recovery_token = str(recovery.get("recovery_cue_token") or "")
    if recovery.get("retryable") and presentation.retry_allowed and recovery_token:
        controls.append(
            "<form method='post' action='/action' class='inline chat-recovery-control'>"
            "<input type='hidden' name='action' value='dashboard_chat_turn_retry'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            f"<input type='hidden' name='turn_id' value='{_safe(turn.get('id',''))}'>"
            f"<input type='hidden' name='recovery_token' value='{_safe(recovery_token)}'>"
            "<input type='hidden' name='use_ai' value='true'>"
            "<button type='submit' data-tip='Run one explicit linked recovery for this exact persisted failure state. A stale card is rejected before provider work begins.'>Run explicit linked recovery</button>"
            "</form>"
        )
    controls.append(
        f"<a class='chat-check-provider' href='{_provider_readiness_href()}' "
        "data-tip='Save this conversation draft, then run one bounded readiness check against the configured provider. No message is sent.'>Check configured provider</a>"
    )
    if presentation.settings_allowed:
        controls.append(
            f"<a class='chat-open-provider-settings' href='{_provider_settings_href()}' "
            "data-tip='Save this conversation draft, then open provider settings without changing the selected conversation.'>Open provider settings</a>"
        )
    if presentation.offline_allowed:
        controls.append(
            "<button type='button' class='chat-continue-offline' "
            "data-tip='Turn off local generation for future messages in this browser. This does not retry or duplicate the failed turn.'>Continue without local generation</button>"
        )
    return (
        history_note
        + (f"<div class='chat-recovery-actions' data-turn-id='{_safe(turn.get('id',''))}' data-recovery-token='{_safe(recovery_token)}'>{''.join(controls)}</div>" if controls else "")
        + _render_turn_diagnostics(turn, session_id=session_id)
    )


def _render_relationship_memory_curation_panel() -> str:
    summary = relationship_memory_curation_summary()
    records = [
        record for record in list(summary.get("records") or [])
        if not str(record.get("content") or "").startswith("Entity association: ")
    ]
    type_options = "".join(
        f"<option value='{_safe(memory_type)}'>{_safe(label)}</option>"
        for memory_type, label in CURATABLE_RELATIONSHIP_TYPES.items()
    )
    record_rows: list[str] = []
    for record in records:
        state = str(record.get("state") or "active")
        action_forms: list[str] = []
        actions = []
        if state == "active":
            actions = [("retain", "Retain"), ("disable", "Disable"), ("retract", "Retract")]
            category = str(record.get("category") or "")
            temporal_state = str(record.get("temporal_state") or "")
            if category == "important_moment":
                actions.insert(0, ("reopen", "Reopen") if temporal_state == "resolved" else ("resolve", "Resolve"))
            elif category == "user_mood":
                actions.insert(0, ("make_current", "Make current") if temporal_state == "cleared" else ("clear", "Clear current mood"))
        elif state == "disabled":
            actions = [("restore", "Restore"), ("retract", "Retract")]
        else:
            actions = [("restore", "Restore")]
        for action, label in actions:
            action_forms.append(
                "<form method='post' action='/action' class='inline'>"
                "<input type='hidden' name='action' value='dashboard_relationship_memory_update'>"
                f"<input type='hidden' name='record_key' value='{_safe(record.get('record_key',''))}'>"
                f"<input type='hidden' name='curation_action' value='{_safe(action)}'>"
                f"<button type='submit' data-tip='{_safe(label)} this explicit continuity memory without deleting its history.'>{_safe(label)}</button>"
                "</form>"
            )
        if state != "retracted":
            action_forms.append(
                "<details class='continuity-memory-correction'><summary>Correct</summary>"
                "<form method='post' action='/action' class='continuity-memory-correct'>"
                "<input type='hidden' name='action' value='dashboard_relationship_memory_correct'>"
                f"<input type='hidden' name='record_key' value='{_safe(record.get('record_key',''))}'>"
                f"<textarea name='content' rows='2' maxlength='500' required>{_safe(record.get('content',''))}</textarea>"
                "<label><small>Importance</small><select name='importance'>"
                + "".join(
                    f"<option value='{level}' {'selected' if str(record.get('importance') or 'medium') == level else ''}>{level.title()}</option>"
                    for level in ("low", "medium", "high", "critical")
                )
                + "</select></label>"
                "<button type='submit' data-tip='Replace only this curated memory content after explicit review. Raw conversation history is not rewritten.'>Save correction</button>"
                "</form></details>"
            )
        if state == "retracted":
            action_forms.append(
                "<form method='post' action='/action' class='inline continuity-memory-delete'>"
                "<input type='hidden' name='action' value='dashboard_relationship_memory_delete'>"
                f"<input type='hidden' name='record_key' value='{_safe(record.get('record_key',''))}'>"
                "<input name='confirmation' required pattern='DELETE' autocomplete='off' "
                "placeholder='Type DELETE' aria-label='Type DELETE to confirm permanent deletion'>"
                "<button type='submit' data-tip='Permanently remove this already-retracted memory content. A content-free audit tombstone remains.'>Delete permanently</button>"
                "</form>"
            )
        provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {}
        provenance_origin = str(provenance.get("origin") or "legacy_unknown")
        provenance_bits = [f"origin {_safe(provenance_origin.replace('_', ' '))}"]
        if provenance.get("conversation_session_id"):
            provenance_bits.append(f"session {_safe(provenance.get('conversation_session_id'))}")
        if provenance.get("conversation_turn_id"):
            provenance_bits.append(f"turn {_safe(provenance.get('conversation_turn_id'))}")
        if provenance.get("eligibility_decision"):
            provenance_bits.append(f"eligibility {_safe(provenance.get('eligibility_decision'))}")
        if record.get("retention_confirmed"):
            provenance_bits.append("retention confirmed")
        provenance_html = " Â· ".join(provenance_bits)
        moment_provenance = record.get("important_moment_provenance") if isinstance(record.get("important_moment_provenance"), dict) else {}
        moment_rationale_html = ""
        if moment_provenance:
            moment_rationale_html = (
                "<small class='continuity-memory-moment-rationale'>Why retained: "
                + _safe(moment_provenance.get("rationale", "Review rationale unavailable."))
                + " Â· eligibility " + _safe(str(moment_provenance.get("eligibility_state") or "unknown").replace("_", " "))
                + ". This rationale is content-free and never rewrites raw conversation history.</small>"
            )
        record_rows.append(
            "<li class='continuity-memory-row'>"
            f"<div><b>{_safe(record.get('label','Continuity'))}</b> "
            f"<span class='badge'>{_safe(state)}</span></div>"
            f"<div>{_safe(record.get('content',''))}</div>"
            f"<small>importance {_safe(record.get('importance','medium'))} Â· "
            f"history {_safe(record.get('history_count',0))}"
            + (f" Â· temporal state {_safe(record.get('temporal_state',''))}" if record.get('temporal_state') else "")
            + (" Â· superseded by a newer explicit nickname" if record.get("superseded_by") else "")
            + (" Â· replaced by a newer current mood" if record.get("replaced_by") else "")
            + "</small>"
            f"<small class='continuity-memory-provenance'>Provenance: {provenance_html}. Content-free evidence only; prompts, responses, provider payloads, and receipts are not shown.</small>"
            f"{moment_rationale_html}"
            f"<div class='inline'>{''.join(action_forms)}</div>"
            "</li>"
        )
    records_html = "".join(record_rows) or "<li>No curatable continuity memories are stored yet.</li>"
    counts = {
        state: sum(str(record.get("state") or "active") == state for record in records)
        for state in ("active", "disabled", "retracted")
    }
    singleton_conflicts = int(summary.get("singleton_conflicts") or 0)
    conflict_note = (
        f"<p class='warning'><small>{_safe(singleton_conflicts)} legacy singleton conflict(s) remain; prompt continuity defensively uses only the newest current value.</small></p>"
        if singleton_conflicts else ""
    )
    return (
        "<details class='chat-continuity-curation' id='chat-continuity-curation'>"
        f"<summary>Manage continuity memories: {_safe(counts.get('active', 0))} active, "
        f"{_safe(counts.get('disabled', 0))} disabled, {_safe(counts.get('retracted', 0))} retracted</summary>"
        "<p><small>Only explicit operator-authored facts are added here. Session transcripts are never mined or promoted automatically.</small></p>"
        f"{conflict_note}"
        "<form method='post' action='/action' class='continuity-memory-create'>"
        "<input type='hidden' name='action' value='dashboard_relationship_memory_create'>"
        f"<label><small>Memory type</small><select name='memory_type'>{type_options}</select></label>"
        "<label><small>Explicit fact</small><textarea name='content' rows='2' maxlength='500' placeholder='Add one explicit continuity fact'></textarea></label>"
        "<label><small>Importance</small><select name='importance'>"
        "<option value='low'>Low</option><option value='medium' selected>Medium</option>"
        "<option value='high'>High</option><option value='critical'>Critical</option>"
        "</select></label>"
        "<button type='submit' data-tip='Create one explicit durable continuity memory.'>Add continuity memory</button>"
        "</form>"
        f"<ul class='continuity-memory-list'>{records_html}</ul>"
        "<small>Correct, disable, restore, and retract preserve audit history. Permanent deletion is available only after retraction and exact DELETE confirmation.</small>"
        "</details>"
    )


def _render_entity_association_curation_panel() -> str:
    records = list_entity_association_records(include_retracted=True)
    summary = entity_association_curation_summary()
    predicate_labels = {
        "uses_provider": "uses provider",
        "belongs_to_project": "belongs to project",
        "contains": "contains",
        "owned_by": "owned by",
        "prefers_provider": "prefers provider",
        "preferred_over": "preferred over",
    }
    rows: list[str] = []
    for record in records:
        association_id = str(record.get("association_id") or "")
        state = str(record.get("state") or "active")
        predicate = str(record.get("predicate") or "")
        controls: list[str] = []
        if state != "retracted":
            controls.append(
                "<form method='post' action='/action' class='inline'>"
                "<input type='hidden' name='action' value='dashboard_entity_association_update'>"
                f"<input type='hidden' name='association_id' value='{_safe(association_id)}'>"
                "<input type='hidden' name='curation_action' value='retract'>"
                "<button type='submit' data-tip='Retract this exact association revision while retaining its audit history.'>Retract</button>"
                "</form>"
            )
            predicate_options = "".join(
                f"<option value='{_safe(value)}' {'selected' if value == predicate else ''}>{_safe(label)}</option>"
                for value, label in predicate_labels.items()
            )
            controls.append(
                "<details class='continuity-memory-correction'><summary>Correct</summary>"
                "<form method='post' action='/action' class='continuity-memory-correct'>"
                "<input type='hidden' name='action' value='dashboard_entity_association_correct'>"
                f"<input type='hidden' name='association_id' value='{_safe(association_id)}'>"
                f"<label><small>Subject</small><input name='subject' maxlength='120' required value='{_safe(record.get('subject',''))}'></label>"
                f"<label><small>Relationship</small><select name='predicate'>{predicate_options}</select></label>"
                f"<label><small>Object</small><input name='object' maxlength='120' required value='{_safe(record.get('object',''))}'></label>"
                "<button type='submit' data-tip='Replace only this exact durable association revision.'>Save correction</button>"
                "</form></details>"
            )
        else:
            controls.append(
                "<form method='post' action='/action' class='inline'>"
                "<input type='hidden' name='action' value='dashboard_entity_association_update'>"
                f"<input type='hidden' name='association_id' value='{_safe(association_id)}'>"
                "<input type='hidden' name='curation_action' value='restore'>"
                "<button type='submit' data-tip='Restore this exact retracted association revision.'>Restore</button>"
                "</form>"
            )
            controls.append(
                "<form method='post' action='/action' class='inline continuity-memory-delete'>"
                "<input type='hidden' name='action' value='dashboard_entity_association_delete'>"
                f"<input type='hidden' name='association_id' value='{_safe(association_id)}'>"
                "<input name='confirmation' required pattern='DELETE' autocomplete='off' placeholder='Type DELETE' "
                "aria-label='Type DELETE to confirm permanent association deletion'>"
                "<button type='submit' data-tip='Permanently remove this retracted association after semantic cleanup verification.'>Delete permanently</button>"
                "</form>"
            )
        rows.append(
            "<li class='continuity-memory-row entity-association-row'>"
            f"<div><b>{_safe(record.get('subject',''))}</b> {_safe(predicate_labels.get(predicate, predicate.replace('_',' ')))} "
            f"<b>{_safe(record.get('object',''))}</b> <span class='badge'>{_safe(state)}</span></div>"
            f"<small>revision {_safe(association_id[-12:])} Â· history {_safe(record.get('history_count',0))} Â· "
            "operator-private view Â· provider not contacted</small>"
            f"<div class='inline'>{''.join(controls)}</div>"
            "</li>"
        )
    counts = summary.get("counts") or {}
    body = "".join(rows) or "<li>No durable entity associations are stored yet. Use an explicit remember request in chat to create one.</li>"
    return (
        "<details class='chat-continuity-curation' id='chat-entity-association-curation' open>"
        f"<summary>Manage entity associations Â· {_safe(counts.get('active',0))} active Â· "
        f"{_safe(counts.get('retracted',0))} retracted</summary>"
        "<p><small>Each control is bound to the displayed record revision. Stale forms fail closed. Correction preserves lineage; retraction is reversible; permanent deletion requires retraction and exact DELETE confirmation.</small></p>"
        f"<ul class='continuity-memory-list'>{body}</ul>"
        "</details>"
    )
def _actions_by_deduplication_key() -> dict[str, dict[str, Any]]:
    """Index the action catalogue once, for a whole transcript render.

    Resolving each turn separately re-read and re-parsed every action file, so a
    120-turn window did that work 120 times over. Each call also took the index
    lock and deep-copied the projection, which is what left request threads
    stacked up behind one another.
    """
    index: dict[str, dict[str, Any]] = {}
    for item in list_chat_actions(include_closed=True):
        key = str(item.get("deduplication_key") or "").strip()
        if key and key not in index:
            index[key] = item
    return index


def _current_action_portal_for_turn(
    turn: dict[str, Any], *, actions_by_key: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Resolve current governed action state without mutating history during GET rendering."""
    stored = sanitize_action_portal_state(turn.get("operator_action"))
    action_id = str((stored or {}).get("action_id") or "").strip()
    action = load_chat_action(action_id) if action_id else None
    if action:
        return _live_action_portal(action)
    turn_id = str(turn.get("id") or "").strip()
    if turn_id:
        if actions_by_key is None:
            actions_by_key = _actions_by_deduplication_key()
        action = actions_by_key.get(turn_id)
        if action:
            return _live_action_portal(action)
    return stored


def _render_action_timeline(portal: dict[str, Any], *, restored: bool = False) -> str:
    events = [dict(item) for item in portal.get("activity_timeline", []) if isinstance(item, dict)]
    rows: list[str] = []
    for event in events:
        status = str(event.get("status") or "event")
        attempt = max(0, int(event.get("attempt_number") or 0))
        owner = str(event.get("owner_scope") or "")
        suffix = f" Â· attempt {attempt}" if attempt else ""
        if owner:
            suffix += f" Â· {owner}"
        rows.append(
            f"<li data-action-event-sequence='{_safe(event.get('sequence') or 0)}'>"
            f"<b>{_safe(status)}</b>{_safe(suffix)}: {_safe(event.get('summary') or '')}</li>"
        )
    if restored:
        rows.append("<li data-action-event-restored='true'><b>restored</b>: Rehydrated from persisted redacted evidence without execution.</li>")
    if not rows:
        return ""
    total = max(len(events), int(portal.get("timeline_total") or len(events)))
    pruned = max(0, int(portal.get("timeline_pruned") or 0))
    pruned_text = f"; {pruned} older summarized" if pruned else ""
    return (
        "<details class='chat-action-timeline' data-action-timeline>"
        f"<summary>Activity timeline ({_safe(total)} events{_safe(pruned_text)})</summary>"
        f"<ol>{''.join(rows)}</ol></details>"
    )


def _render_research_progress(portal: dict[str, Any]) -> str:
    progress = portal.get("research_progress") if isinstance(portal.get("research_progress"), dict) else None
    if not progress:
        return ""
    percent = max(0, min(100, int(progress.get("progress_percent") or 0)))
    stage = str(progress.get("progress_stage") or "starting").replace("_", " ")
    counts = (
        f"{int(progress.get('query_count') or 0)} searches Â· "
        f"{int(progress.get('observed_page_count') or 0)} pages Â· "
        f"{int(progress.get('evidence_count') or 0)} evidence items Â· "
        f"{int(progress.get('source_failure_count') or 0)} source failures"
    )
    return (
        "<section class='chat-research-progress' data-research-progress='true' "
        f"data-research-state='{_safe(progress.get('state') or '')}' data-research-revision='{_safe(progress.get('store_revision') or 0)}'>"
        "<div class='chat-research-progress-head'>"
        f"<b data-research-stage='true'>{_safe(stage.title())}</b>"
        f"<span data-research-percent='true'>{_safe(percent)}%</span>"
        "</div>"
        f"<progress max='100' value='{_safe(percent)}' aria-label='Research progress: {_safe(stage)}, {_safe(percent)} percent'></progress>"
        f"<small data-research-counts='true'>{_safe(counts)}</small>"
        "<small data-research-recovery='true'>Refresh reconnects to this exact session. A process restart fails closed and never replays external requests.</small>"
        "</section>"
    )


def _render_research_review(portal: dict[str, Any]) -> str:
    review = portal.get("research_review") if isinstance(portal.get("research_review"), dict) else None
    if not review:
        return ""
    counts = (
        f"{int(review.get('verified_count') or 0)} verified Â· "
        f"{int(review.get('inference_count') or 0)} inferred Â· "
        f"{int(review.get('disagreement_count') or 0)} disputed Â· "
        f"{int(review.get('missing_evidence_count') or 0)} gaps"
    )
    quality = dict(review.get("quality_counts") or {})
    freshness = dict(review.get("freshness_counts") or {})
    quality_text = (
        f"Quality: {int(quality.get('high') or 0)} high, {int(quality.get('medium') or 0)} medium, "
        f"{int(quality.get('low') or 0)} low, {int(quality.get('unknown') or 0)} unknown"
    )
    freshness_text = (
        f"Freshness: {int(freshness.get('fresh') or 0)} fresh, {int(freshness.get('stale') or 0)} stale, "
        f"{int(freshness.get('unknown') or 0)} unknown"
    )
    citations = []
    for row in list(review.get("citations") or [])[:12]:
        if not isinstance(row, dict) or not row.get("public_url"):
            continue
        label = str(row.get("citation_id") or row.get("host") or "Source")
        metadata = " Â· ".join(
            part for part in (
                str(row.get("host") or ""),
                str(row.get("source_kind") or "unknown").replace("_", " "),
                f"{row.get('quality') or 'unknown'} quality",
                f"{row.get('freshness') or 'unknown'} freshness",
            ) if part
        )
        citations.append(
            "<li>"
            f"<a href='{_safe(row.get('public_url') or '')}' target='_blank' rel='noopener noreferrer'>{_safe(label)}</a>"
            f"<small>{_safe(metadata)}</small>"
            "</li>"
        )
    citation_list = "".join(citations) or "<li><small>No reviewable public citation URL was retained.</small></li>"
    confidence_rows = [row for row in list(review.get("recommendation_confidence_assessments") or [])[:8] if isinstance(row, dict)]
    confidence_by_digest = {str(row.get("candidate_digest") or ""): row for row in confidence_rows}
    threshold = str(review.get("recommendation_confidence_threshold") or "moderate-confidence")
    confidence_items = []
    for row in confidence_rows:
        title = str(row.get("title") or row.get("candidate_digest") or "Candidate")
        label = str(row.get("confidence_label") or "unsupported")
        reasons = "; ".join(str(value) for value in list(row.get("reasons") or [])[:3] if str(value).strip())
        confidence_items.append(
            f"<li><b>{_safe(title)}</b>: {_safe(label)}"
            + (f"<small>{_safe(reasons)}</small>" if reasons else "")
            + "</li>"
        )
    confidence_html = (
        "<section class='chat-research-confidence' data-research-confidence='true' aria-label='Recommendation confidence'>"
        f"<strong>Recommendation confidence Â· threshold {_safe(threshold)}</strong>"
        f"<ul>{''.join(confidence_items)}</ul>"
        "</section>"
        if confidence_items else ""
    )
    matrix_rows = []
    dimensions = (
        ("demand", "Demand"), ("competition", "Competition"),
        ("implementation_dependencies", "Dependencies"), ("free_tier_feasibility", "Free-tier"),
    )
    for row in list(review.get("candidate_evidence_matrix") or [])[:8]:
        if not isinstance(row, dict):
            continue
        candidate_digest = str(row.get("candidate_digest") or "")
        assessment = confidence_by_digest.get(candidate_digest, {})
        title = str(assessment.get("title") or (candidate_digest[:12] + "â€¦" if candidate_digest else "Candidate"))
        cells = row.get("cells") if isinstance(row.get("cells"), dict) else {}
        rendered_cells = []
        for key, _label in dimensions:
            cell = cells.get(key) if isinstance(cells.get(key), dict) else {}
            state = str(cell.get("matrix_state") or cell.get("state") or "not_researched").replace("_", " ")
            independent = int(cell.get("independent_lineage_count") or 0)
            rendered_cells.append(f"<td><span>{_safe(state)}</span><small>{_safe(independent)} independent</small></td>")
        matrix_rows.append(f"<tr><th scope='row'>{_safe(title)}</th>{''.join(rendered_cells)}</tr>")
    matrix_html = (
        "<div class='chat-research-matrix-wrap' data-research-matrix='true' tabindex='0' aria-label='Candidate evidence matrix'>"
        "<table class='chat-research-matrix'><caption>Candidate evidence matrix</caption>"
        "<thead><tr><th scope='col'>Candidate</th>"
        + "".join(f"<th scope='col'>{_safe(label)}</th>" for _key, label in dimensions)
        + "</tr></thead><tbody>" + "".join(matrix_rows) + "</tbody></table></div>"
        if matrix_rows else ""
    )
    digest = str(review.get("report_digest") or "")[:12]
    return (
        "<details class='chat-research-review' data-research-review='true'>"
        f"<summary>Review research evidence ({_safe(review.get('citation_count') or 0)} citations)</summary>"
        "<div class='chat-research-review-body'>"
        f"<div class='chat-research-review-counts' data-research-review-counts='true'>{_safe(counts)}</div>"
        f"<small data-research-review-quality='true'>{_safe(quality_text)}</small>"
        f"<small data-research-review-freshness='true'>{_safe(freshness_text)}</small>"
        f"<small data-research-review-cues='true'>Contradictions: {_safe(review.get('disagreement_count') or 0)} Â· Missing evidence: {_safe(review.get('missing_evidence_count') or 0)} Â· Source failures: {_safe(review.get('source_failure_count') or 0)} Â· Independent lineages: {_safe(review.get('independent_lineage_count') or 0)} Â· Repeated/derivative citations: {_safe(review.get('repeated_or_derivative_citation_count') or review.get('repeated_source_citation_count') or 0)}</small>"
        f"{confidence_html}{matrix_html}"
        f"<ol class='chat-research-citations' data-research-citations='true'>{citation_list}</ol>"
        f"<small data-research-review-boundary='true'>Report {_safe(digest)}â€¦ is digest-bound. Generated prose is synthesis, not evidence; raw pages, private objectives, and queries remain private. Opening a citation is your explicit browser action.</small>"
        "</div></details>"
    )
def _render_research_history(portal: dict[str, Any]) -> str:
    history = portal.get("research_history") if isinstance(portal.get("research_history"), dict) else None
    if not history:
        return ""
    rows = []
    for row in list(history.get("sessions") or [])[:20]:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("session_id") or "")
        status = str(row.get("terminal_status") or "unknown")
        integrity = str(row.get("integrity_status") or "unknown")
        evidence = int(row.get("evidence_count") or 0)
        citations = int(row.get("citation_count") or 0)
        completed = str(row.get("completed_at") or "")
        report_digest = str(row.get("report_digest") or "")[:12]
        metadata = f"{status} Â· {evidence} evidence Â· {citations} citations Â· integrity {integrity}"
        confidence_labels = [str(item.get("confidence_label") or "") for item in list(row.get("recommendation_confidence_labels") or [])[:8] if isinstance(item, dict)]
        if confidence_labels:
            metadata += " Â· confidence " + ", ".join(confidence_labels)
        if completed:
            metadata += f" Â· {completed}"
        rows.append(
            "<li class='chat-research-history-item'>"
            f"<code>{_safe(sid)}</code>"
            f"<small>{_safe(metadata)}</small>"
            f"<small>Report digest: {_safe(report_digest or 'none')}â€¦</small>"
            "</li>"
        )
    missing = len(list(history.get("missing_records") or []))
    warning = (
        f"<small class='chat-research-history-warning' data-research-history-warning='true'>Integrity warning: {_safe(missing)} terminal session(s) have missing catalog records. No repair was performed.</small>"
        if missing else ""
    )
    body = "".join(rows) or "<li><small>No terminal research sessions are recorded yet.</small></li>"
    return (
        "<details class='chat-research-history' data-research-history='true'>"
        f"<summary>Research history ({_safe(history.get('history_count') or len(rows))} sessions)</summary>"
        f"<ol class='chat-research-history-list'>{body}</ol>"
        f"{warning}"
        "<small data-research-history-workflow='true'>Use the exact session IDs and digests shown here to compare two completed sessions or explicitly export one completed report as Markdown.</small>"
        "<small data-research-history-boundary='true'>History is digest-bound and content-minimized. Private objectives, search queries, raw pages, credentials, and cookies are not projected here.</small>"
        "</details>"
    )


def _render_research_comparison(portal: dict[str, Any]) -> str:
    comparison = portal.get("research_comparison") if isinstance(portal.get("research_comparison"), dict) else None
    if not comparison:
        return ""
    changed = len(list(comparison.get("changed_claims") or []))
    added = len(list(comparison.get("added_claim_codes") or []))
    removed = len(list(comparison.get("removed_claim_codes") or []))
    stale = len(list(comparison.get("stale_claim_codes") or []))
    conflicts = len(list(comparison.get("contradictory_claim_codes") or []))
    duplicates = len(list(comparison.get("duplicated_claim_codes") or []))
    unsupported = len(list(comparison.get("unsupported_claim_codes") or []))
    confidence_changes = len(list(comparison.get("changed_recommendation_confidence") or []))
    left = str(comparison.get("left_session_id") or "")
    right = str(comparison.get("right_session_id") or "")
    return (
        "<details class='chat-research-comparison' data-research-comparison='true'>"
        f"<summary>Compare research evidence: {_safe(left)} â†” {_safe(right)}</summary>"
        f"<div class='chat-research-comparison-counts'>Changed {_safe(changed)} Â· Added {_safe(added)} Â· Removed {_safe(removed)} Â· Stale {_safe(stale)} Â· Contradictory {_safe(conflicts)} Â· Duplicate {_safe(duplicates)} Â· Unsupported {_safe(unsupported)} Â· Confidence changes {_safe(confidence_changes)}</div>"
        f"<small>Left report {_safe(str(comparison.get('left_report_digest') or '')[:12])}â€¦ Â· Right report {_safe(str(comparison.get('right_report_digest') or '')[:12])}â€¦</small>"
        "<small data-research-comparison-boundary='true'>This is a content-free evidence-structure comparison. It performs no web request, reveals no private objective or raw page, preserves source independence, and declares no automatic winner.</small>"
        "</details>"
    )


def _render_research_export(portal: dict[str, Any]) -> str:
    export = portal.get("research_export") if isinstance(portal.get("research_export"), dict) else None
    if not export:
        return ""
    return (
        "<section class='chat-research-export' data-research-export='true' aria-label='Research report export'>"
        f"<strong>Local Markdown export ready</strong><code>{_safe(export.get('file_name') or '')}</code>"
        f"<small>Report {_safe(str(export.get('report_digest') or '')[:12])}â€¦ Â· Export {_safe(str(export.get('export_digest') or '')[:12])}â€¦ Â· {_safe(export.get('export_byte_count') or 0)} bytes</small>"
        "<small data-research-export-boundary='true'>Explicit local export only. Nothing was uploaded or transmitted; private objectives, raw pages, queries, credentials, provider payloads, stack traces, and private filesystem paths are excluded.</small>"
        "</section>"
    )


def _render_action_portal_card(
    session_id: str, turn: dict[str, Any], *, actions_by_key: dict[str, dict[str, Any]] | None = None,
) -> str:
    portal = _current_action_portal_for_turn(turn, actions_by_key=actions_by_key)
    if not portal:
        return ""
    action_id = str(portal.get("action_id") or "")
    status = str(portal.get("status") or "proposed")
    message = str(portal.get("message") or portal.get("summary") or "")
    retry = ""
    if portal.get("retry_allowed"):
        retry = (
            "<form method='post' action='/action' class='inline' data-chat-action-retry>"
            "<input type='hidden' name='action' value='chat_action_execute'>"
            f"<input type='hidden' name='chat_action_id' value='{_safe(action_id)}'>"
            "<input type='hidden' name='retry' value='true'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            f"<input type='hidden' name='turn_id' value='{_safe(turn.get('id',''))}'>"
            "<button type='submit'>Retry safe action once</button></form>"
        )
    approval = (
        f"<small>Approval: {_safe(portal.get('approval_id'))}</small>"
        if portal.get("approval_id") else ""
    )
    attempt_number = max(0, int(portal.get("execution_attempt") or 0))
    prior_attempts = max(0, int(portal.get("prior_attempt_count") or 0))
    attempt_evidence = ""
    if attempt_number:
        attempt_evidence = (
            f"<small data-action-attempt-evidence='true'>Latest execution attempt: {_safe(attempt_number)}. "
            f"Earlier preserved attempts: {_safe(prior_attempts)}.</small>"
        )
    owner = ""
    if portal.get("status") == "running" and portal.get("claim_owner_label"):
        owner = f"<small data-action-owner='true'>Execution owner: {_safe(portal.get('claim_owner_label'))}.</small>"
    timeline = _render_action_timeline(portal, restored=True)
    research_progress = _render_research_progress(portal)
    research_review = _render_research_review(portal)
    research_history = _render_research_history(portal)
    research_comparison = _render_research_comparison(portal)
    research_export = _render_research_export(portal)
    return (
        f"<section id='chat-inline-action-{_safe(action_id)}' class='chat-action-portal chat-inline-action' data-action-id='{_safe(action_id)}' data-action-status='{_safe(status)}' data-execution-mode='{_safe(portal.get('execution_mode') or 'review')}' data-risk-level='{_safe(portal.get('risk_level') or 'unknown')}'>"
        "<div class='chat-action-portal-head'>"
        f"<span class='badge' data-action-field='status'>{_safe(portal.get('status_label') or status)}</span>"
        f"<span class='badge'>{_safe(portal.get('execution_mode') or 'review')}</span>"
        f"<span class='badge'>risk: {_safe(portal.get('risk_level') or 'unknown')}</span>"
        "</div>"
        f"<b>{_safe(portal.get('title') or 'Supervised action')}</b>"
        f"<p>{_safe(portal.get('summary') or '')}</p>"
        f"<small data-action-execution='true'>{_safe(message)}</small>{approval}{attempt_evidence}{owner}{research_progress}{research_review}{research_history}{research_comparison}{research_export}{timeline}"
        "<div class='chat-action-portal-actions'>"
        f"{retry}<a href='/detail?kind=chat_action&amp;id={_safe(action_id)}'>Action details</a>"
        "</div>"
        "<small data-action-restored='true'>Rehydrated from redacted persisted state. Viewing this card never executes the action again.</small>"
        "</section>"
    )


def _persist_turn_action_portal(
    session_id: str,
    turn_id: str,
    action: dict[str, Any] | None,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    current_action = None
    if isinstance(action, dict) and action.get("id"):
        current_action = load_chat_action(str(action.get("id") or ""))
    governed_action = current_action or action
    governed_execution = (
        governed_action.get("result")
        if isinstance(governed_action, dict) and isinstance(governed_action.get("result"), dict)
        else execution
    )
    portal = build_action_portal_state(governed_action, governed_execution)
    if not portal or not session_id or not turn_id:
        return portal
    try:
        update_conversation_turn_action(session_id, turn_id, portal)
    except (OSError, ValueError):
        pass
    return portal


def _turn_timestamp(turn: dict[str, Any]) -> str:
    stamp = str(turn.get("created_at") or "")
    if not stamp:
        return ""
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return ""
    parsed = parsed.astimezone()
    label = time_label(parsed.hour, parsed.minute)
    return f" <time datetime='{_safe(stamp)}' title='Recorded turn time'>{_safe(label)}</time>"


def _render_session_transcript(session_id: str, turns: list[dict[str, Any]], *, include_empty: bool = True) -> str:
    transcript_parts: list[str] = []
    last_date = None
    actions_by_key = _actions_by_deduplication_key() if turns else {}
    for turn in turns:
        try:
            local_time = datetime.fromisoformat(str(turn.get("created_at") or "").replace("Z", "+00:00")).astimezone()
        except ValueError:
            local_time = None
        if local_time and local_time.date() != last_date:
            last_date = local_time.date()
            transcript_parts.append(f"<div class='chat-date-divider' data-chat-date='{last_date.isoformat()}'>{day_label(last_date.year, last_date.month, last_date.day)}</div>")
        user_text = str(turn.get("user_message") or "").strip()
        assistant_text = str(turn.get("assistant_response") or "").strip()
        state = str(turn.get("completion_state") or "")
        presentation = turn_experience_state(turn)
        if user_text:
            transcript_parts.append(
                f"<article class='chat-turn user-turn' data-session-turn-id='{_safe(turn.get('id',''))}'>"
                f"<small class='chat-speaker'>{_turn_timestamp(turn)} Marcus:</small>"
                f"<div class='chat-bubble user'>{_safe(user_text)}</div>"
                "</article>"
            )
        if turn.get("success") and assistant_text:
            transcript_parts.append(
                f"<article class='chat-turn eidolon-turn' data-session-turn-id='{_safe(turn.get('id',''))}'>"
                f"<small class='chat-speaker'>{_turn_timestamp(turn)} Eidolon:</small>"
                f"<div class='chat-bubble eidolon' data-completion-state='{_safe(state)}'>{_safe(assistant_text)}</div>"
                + (
                    "<small class='chat-turn-state recovered'>Recovered successfully through one explicit linked retry.</small>"
                    if presentation.recovered else ""
                )
                + "</article>"
            )
            action_card = _render_action_portal_card(session_id, turn, actions_by_key=actions_by_key)
            if action_card:
                transcript_parts.append(action_card)
            completed_controls = _render_completed_turn_controls(session_id, turn)
            if completed_controls:
                transcript_parts.append(completed_controls)
        elif not turn.get("success"):
            transcript_parts.append(
                f"<article class='chat-turn eidolon-turn' data-session-turn-id='{_safe(turn.get('id',''))}'>"
                f"<small class='chat-speaker'>{_turn_timestamp(turn)} Eidolon:</small>"
                f"<div class='chat-bubble eidolon failed' data-completion-state='{_safe(state)}'>"
                f"<b>{_safe(presentation.label)}</b><span>{_safe(presentation.detail)}</span></div>"
                "<small class='chat-turn-state'>Not added to memory or future continuity.</small>"
                "</article>"
            )
            transcript_parts.append(_render_turn_recovery_controls(session_id, turn))
            action_card = _render_action_portal_card(session_id, turn, actions_by_key=actions_by_key)
            if action_card:
                transcript_parts.append(action_card)
    if not transcript_parts and include_empty:
        transcript_parts.append(
            "<article class='chat-turn eidolon-turn welcome-turn'>"
            "<small class='chat-speaker'>Eidolon</small>"
            "<div class='chat-bubble eidolon'>Iâ€™m here. Start wherever you left off, or open a new conversation when you want a clean thread.</div>"
            "</article>"
        )
    return "".join(transcript_parts)


def _conversation_continuity_summary() -> dict[str, Any]:
    continuity = build_relationship_continuity_snapshot(
        load_memories(limit=120), load_self_model(), user_message="",
    )
    return continuity.public_summary(include_cues=True)


def dashboard_chat_session_catalog_page(
    *, query: str = "", include_archived: bool = True, offset: int = 0, limit: int = 30,
) -> dict[str, Any]:
    """Return one read-only private catalog page without changing session state.

    Provider/model diagnostics stay in explicit turn disclosures and are not embedded in
    the organizer payload, where they would otherwise become visible page source data.
    """
    page = build_conversation_session_catalog_page(
        query, include_archived=include_archived, offset=offset, limit=limit,
    )
    sanitized = dict(page)
    sanitized["items"] = [
        {key: value for key, value in dict(item).items() if key not in {"last_provider", "last_model"}}
        for item in page.get("items") or []
        if isinstance(item, dict)
    ]
    return sanitized


def dashboard_chat_session_catalog_state(*, include_archived: bool = True) -> list[dict[str, Any]]:
    """Return bounded lifecycle metadata for selectors and in-place controls."""
    page = dashboard_chat_session_catalog_page(
        query="", include_archived=include_archived, offset=0, limit=30,
    )
    rows: list[dict[str, Any]] = []
    for session in page.get("items") or []:
        rows.append({
            "id": str(session.get("id") or ""),
            "title": str(session.get("title") or "New conversation")[:72],
            "display_title": str(session.get("display_title") or session.get("title") or "New conversation")[:120],
            "duplicate_title": bool(session.get("duplicate_title")),
            "status": "archived" if str(session.get("status") or "active") == "archived" else "active",
            "turn_count": max(0, int(session.get("turn_count") or 0)),
            "completed_turn_count": max(0, int(session.get("completed_turn_count") or 0)),
            "created_at": str(session.get("created_at") or ""),
            "updated_at": str(session.get("updated_at") or ""),
            "group_label": str(session.get("group_label") or "Older conversations")[:80],
        })
    return rows


def dashboard_chat_attention_center_payload() -> dict[str, Any]:
    """Return one redacted read-only attention snapshot for the chat console."""
    updates: list[dict[str, Any]] = []
    for session in dashboard_chat_session_catalog_state(include_archived=False):
        session_id = str(session.get("id") or "")
        cue = dashboard_session_operation_cue(session_id) if session_id else None
        contract = conversation_recovery_contract(session_id) if session_id else {}
        if cue:
            kind = str(cue.get("kind") or "conversation_update")
            label = str(cue.get("label") or "Conversation update")
            status = str(cue.get("public_state") or "")
        elif str(contract.get("state") or "ready") != "ready":
            kind = "conversation_recovery"
            label = str(contract.get("label") or "Conversation recovery")
            status = str(contract.get("state") or "attention")
        else:
            continue
        updates.append({
            "session_id": session_id,
            "title": str(session.get("title") or "New conversation")[:120],
            "kind": kind[:80],
            "label": label[:160],
            "status": status[:80],
            "updated_at": str(session.get("updated_at") or ""),
        })
    return build_attention_center(conversation_updates=updates)


def _render_attention_center(report: dict[str, Any]) -> str:
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    rows = []
    for item in report.get("items") or []:
        href = str(item.get("href") or "")
        link = f"<a href='{_safe(href)}'>Open</a>" if href.startswith("/") else ""
        rows.append(
            f"<li class='attention-center-item' data-attention-kind='{_safe(item.get('kind',''))}' "
            f"data-attention-status='{_safe(item.get('status',''))}' data-requires-operator='{'true' if item.get('requires_operator') else 'false'}'>"
            "<div class='attention-center-item-head'>"
            f"<span class='badge'>{_safe(item.get('kind','item'))}</span>"
            f"<span class='badge'>{_safe(item.get('status',''))}</span>"
            f"<b>{_safe(item.get('title','Attention item'))}</b></div>"
            f"<small>{_safe(item.get('summary',''))}</small>{link}</li>"
        )
    list_html = "".join(rows) or "<li class='attention-center-empty'>Nothing currently needs attention.</li>"
    return (
        "<details class='chat-attention-center' id='chat-attention-center'>"
        f"<summary>Attention center Â· <span id='attention-center-total'>{_safe(counts.get('total_attention', 0))}</span> requiring you</summary>"
        "<div class='attention-center-counts' id='attention-center-counts'>"
        f"<span class='badge'>approvals {_safe(counts.get('pending_approvals', 0))}</span>"
        f"<span class='badge'>notifications {_safe(counts.get('unread_notifications', 0))}</span>"
        f"<span class='badge'>tasks {_safe(counts.get('open_tasks', 0))}</span>"
        f"<span class='badge'>conversation updates {_safe(counts.get('conversation_updates', 0))}</span>"
        f"<span class='badge'>provider recovery {_safe(counts.get('provider_recovery', 0))}</span>"
        f"<span class='badge'>action issues {_safe(counts.get('action_attention', 0))}</span>"
        "</div>"
        f"<ul class='attention-center-list' id='attention-center-list'>{list_html}</ul>"
        "<div class='inline'><button type='button' id='attention-center-refresh'>Refresh</button>"
        "<a href='/notifications'>Notifications</a><a href='/approvals'>Approvals</a><a href='/tasks'>Tasks</a></div>"
        "<small id='attention-center-status'>Read-only and redacted. Refreshing does not acknowledge, approve, execute, select, or modify anything.</small>"
        "</details>"
    )


def dashboard_chat_session_window(
    session_id: str, *, before_turn_id: str = "", limit: int = 80,
) -> dict[str, Any]:
    """Return one bounded earlier-history window with canonical rendered markup."""
    window = conversation_session_turn_window(session_id, before_turn_id=before_turn_id, limit=limit)
    return {
        key: value for key, value in window.items() if key != "turns"
    } | {
        "transcript_html": _render_session_transcript(
            session_id, list(window.get("turns") or []), include_empty=False,
        ),
        "receipts_included": False,
    }


def dashboard_chat_session_snapshot(session_id: str) -> dict[str, Any]:
    """Return one bounded full-session view without changing active selection."""
    session = resolve_conversation_session(session_id, create_if_missing=False) or {}
    resolved_session_id = str(session.get("id") or "")
    if not resolved_session_id or session.get("status") == "archived":
        raise ValueError("Conversation session not found or archived.")
    history_window = conversation_session_turn_window(resolved_session_id, limit=80)
    turns = list(history_window.get("turns") or [])
    draft = load_conversation_draft(resolved_session_id)
    presentation = load_conversation_presentation_state(resolved_session_id)
    continuity_summary = _conversation_continuity_summary()
    experience = build_conversation_experience_state(
        active_session=session,
        latest_turn=turns[-1] if turns else None,
        settings=load_settings(),
        continuity_summary=continuity_summary,
    )
    operation_status = dashboard_chat_operation_status(session_id=resolved_session_id)
    return {
        "ok": True,
        "session": {
            "id": resolved_session_id,
            "title": str(session.get("title") or "New conversation"),
            "turn_count": int(session.get("turn_count") or 0),
            "completed_turn_count": int(session.get("completed_turn_count") or 0),
            "status": str(session.get("status") or "active"),
        },
        "draft": draft,
        "presentation": presentation,
        "transcript_html": _render_session_transcript(resolved_session_id, turns),
        "history_window": {key: value for key, value in history_window.items() if key != "turns"},
        "experience": experience.public_dict(),
        "operation_status": operation_status,
        "provider_recovery": provider_resume_cue(),
        "resend_candidate": resend_candidate_for_session(resolved_session_id),
        "recovery_contract": conversation_recovery_contract(resolved_session_id),
        "offline_session": offline_session_durability_state(resolved_session_id),
        "offline_degradation": offline_conversation_degradation_state(resolved_session_id, provider_available=False),
        "conversation_controls": load_conversation_controls(resolved_session_id, include_instruction=False),
        "long_session_hardening": build_long_session_hardening_state(resolved_session_id),
        "lifecycle_recovery": lifecycle_recovery_plan(
            "history-return", hidden=False, online=True, owns_control=False,
            active_operation_id=str((operation_status.get("operation") or {}).get("operation_id") or ""),
        ),
        "project_recovery": __import__("project_recovery_state").build_project_recovery_state(
            include_conversation_details=False,
        ),
    }


def render_realtime_chat_panel(
    latest: dict[str, Any] | None,
    compact: bool = False,
    *,
    session_query: str = "",
    include_archived: bool = False,
    session_offset: int = 0,
) -> str:
    active = get_active_conversation_session(create_if_missing=False) or {}
    active_session_id = str(active.get("id") or "")
    try:
        from project_manager import get_active_project
        active_project = get_active_project() or {}
        active_project_id = str(active_project.get("id") or "eidolon")
        active_project_name = str(active_project.get("name") or "Eidolon")
    except Exception:
        active_project_id = "eidolon"
        active_project_name = "Eidolon"
    active_draft = load_conversation_draft(active_session_id) if active_session_id else {
        "content": "",
        "updated_at": "",
        "cleared_at": "",
    }
    active_presentation = load_conversation_presentation_state(active_session_id) if active_session_id else {
        "follow_latest": True,
        "scroll_from_bottom_px": 0,
        "composer_intentionally_empty": True,
        "updated_at": "",
    }
    operation_status = dashboard_chat_operation_status(session_id=active_session_id) if active_session_id else {"operation": None}
    initial_operation = operation_status.get("operation") if isinstance(operation_status.get("operation"), dict) else None
    if initial_operation:
        operation_state = str(initial_operation.get("public_state") or "")
        needs_reconciliation = (
            operation_state in {"running", "uncertain"}
            or (bool(initial_operation.get("client_disconnected")) and not initial_operation.get("reconciled_at"))
        )
        if not needs_reconciliation:
            initial_operation = None
    initial_operation_json = json.dumps(initial_operation, separators=(",", ":")).replace("</", "<\\/")
    initial_action_portal = operation_status.get("action_portal") if initial_operation else None
    initial_action_portal_json = json.dumps(initial_action_portal, separators=(",", ":")).replace("</", "<\\/")
    initial_presentation_json = json.dumps(active_presentation, separators=(",", ":")).replace("</", "<\\/")
    initial_offline_session = (
        offline_session_durability_state(active_session_id)
        if active_session_id
        else offline_session_durability_state()
    )
    initial_offline_session_json = json.dumps(
        initial_offline_session, separators=(",", ":")
    ).replace("</", "<\\/")
    initial_project_recovery = {
        "ok": True, "status": "checking", "message": "Checking current project state in the background.",
        "project": {"id": active_project_id, "name": active_project_name}, "source": {"status": "checking"},
        "switch": {"revision": 0, "stale_tab": False}, "root_correction": {"pending": False, "status": "none"},
        "controls": {"project_mutations_enabled": True, "refresh_required": False},
        "provider_contacted": False, "content_free": True,
    }
    initial_project_recovery_json = json.dumps(initial_project_recovery, separators=(",", ":")).replace("</", "<\\/")
    project_recovery_panel = (
        "<section class='chat-project-recovery' id='chat-project-recovery' data-status='{}' role='status' aria-live='polite' aria-atomic='true'>"
        "<div><small>Active project</small><b id='chat-project-recovery-name'>{}</b></div>"
        "<div class='chat-project-recovery-summary'><span class='badge' id='chat-project-recovery-source'>source {}</span>"
        "<span class='badge' id='chat-project-recovery-switch'>revision {}</span>"
        "<span class='badge' id='chat-project-recovery-correction'{}>root correction pending</span></div>"
        "<small id='chat-project-recovery-message'>{}</small>"
        "<button type='button' id='chat-project-recovery-refresh' data-tip='Refresh the read-only active-project recovery state. This does not switch projects, contact a provider, or apply a source-root correction.'>Refresh project state</button>"
        "</section>"
    ).format(
        _safe(initial_project_recovery.get("status", "unknown")),
        _safe((initial_project_recovery.get("project") or {}).get("name", "Unknown project")),
        _safe((initial_project_recovery.get("source") or {}).get("status", "unknown")),
        _safe((initial_project_recovery.get("switch") or {}).get("revision", 0)),
        "" if (initial_project_recovery.get("root_correction") or {}).get("pending") else " hidden",
        _safe(initial_project_recovery.get("message", "")),
    )
    metadata_recovery_panel = (
        "<section class='chat-metadata-recovery' id='chat-metadata-recovery' data-status='checking' role='status' aria-live='polite' aria-atomic='true'>"
        "<div><small>Metadata recovery</small><b id='chat-metadata-recovery-status'>checking</b></div>"
        "<div class='chat-metadata-recovery-summary'><span class='badge' id='chat-metadata-recovery-busy'>busy 0</span>"
        "<span class='badge' id='chat-metadata-recovery-pending'>recovery 0</span>"
        "<span class='badge' id='chat-metadata-recovery-review'>review 0</span></div>"
        "<small id='chat-metadata-recovery-message'>Checking private metadata coordination state. Conversation remains available.</small>"
        "<button type='button' id='chat-metadata-recovery-refresh' data-tip='Refresh read-only metadata recovery state. This does not contact a provider, migrate a file, or reveal private metadata.'>Refresh metadata state</button>"
        "</section>"
    )
    process_recovery_panel = (
        "<section class='chat-process-recovery' id='chat-process-recovery' data-status='checking' role='status' aria-live='polite' aria-atomic='false'>"
        "<div><small>Process operations</small><b id='chat-process-recovery-status'>checking</b></div>"
        "<div class='chat-process-recovery-summary'><span class='badge' id='chat-process-recovery-active'>active 0</span>"
        "<span class='badge' id='chat-process-recovery-cancel'>cancellation 0</span>"
        "<span class='badge' id='chat-process-recovery-uncertain'>uncertain 0</span></div>"
        "<small id='chat-process-recovery-message'>Checking restart-safe operation state. Conversation remains available.</small>"
        "<div id='chat-process-recovery-rows' class='chat-process-recovery-rows'></div>"
        "<button type='button' id='chat-process-recovery-refresh' data-tip='Refresh read-only process operation state. This does not start, retry, or replay work.'>Refresh operation state</button>"
        "</section>"
    )
    sessions = dashboard_chat_session_catalog_state(include_archived=False)
    catalog_page = dashboard_chat_session_catalog_page(
        query=session_query, include_archived=include_archived, offset=session_offset, limit=30,
    )
    catalog = list(catalog_page.get("items") or [])
    attention_report = {"counts": {}, "items": []}
    attention_center_html = _render_attention_center(attention_report)
    reentry_panel = (
        "<section class='conversation-reentry-panel' id='conversation-reentry-panel' hidden>"
        "<small>Conversation updates</small><ul class='conversation-reentry-cues' id='conversation-reentry-cues'></ul></section>"
    )
    provider_recovery_html = _render_provider_recovery_resume_cue(provider_resume_cue())
    recovery_contract_html = _render_conversation_recovery_contract(conversation_recovery_contract(active_session_id)) if active_session_id else ""
    offline_session_html = (
        "<section class='chat-offline-session-durability' id='chat-offline-session-durability' data-provider-dependency='none_for_local_surfaces'>"
        "<b id='chat-offline-session-label'>Local conversation continuity ready</b>"
        "<small id='chat-offline-session-detail'>History, drafts, search, archive, and reading position remain local and usable when generation is unavailable.</small>"
        "</section>"
    )
    active_controls = load_conversation_controls(
        active_session_id, include_instruction=True, include_pinned_context=True,
    ) if active_session_id else {"revision": 0, "pinned_context": [], "queued_operator_intent": {"state": "none"}}
    pinned_items = [item for item in active_controls.get("pinned_context", []) if isinstance(item, dict)]
    pinned_rows = "".join(
        "<li class='chat-pinned-context-item' data-pin-id='{}'><span><b>{}</b> Â· {} Â· {}</span>"
        "<small>{}</small><button type='button' data-conversation-control-mutation data-remove-pin='{}'>Remove</button></li>".format(
            _safe(item.get("id", "")),
            _safe(str(item.get("kind") or "note").replace("_", " ").title()),
            _safe(str(item.get("scope") or "current_session").replace("_", " ")),
            _safe("expired" if item.get("expired") else ("active" if item.get("active") else str(item.get("reason") or "inactive"))),
            _safe(item.get("content", "")),
            _safe(item.get("id", "")),
        )
        for item in pinned_items
    ) or "<li class='chat-pinned-context-empty'>No pinned working context for this conversation.</li>"
    queued_intent = active_controls.get("queued_operator_intent") if isinstance(active_controls.get("queued_operator_intent"), dict) else {"state": "none"}
    queued_label = (
        f"{str(queued_intent.get('kind') or 'none').replace('_', ' ')} Â· {str(queued_intent.get('state') or 'none')}"
        if str(queued_intent.get("state") or "none") != "none" else "No queued operator intent"
    )
    working_context_panel = (
        "<details class='chat-working-context-control' id='chat-working-context-control'>"
        f"<summary>Pinned working context Â· <span id='chat-pinned-count'>{len(pinned_items)}</span></summary>"
        f"<ul class='chat-pinned-context-list' id='chat-pinned-context-list'>{pinned_rows}</ul>"
        "<div class='chat-working-context-editor'>"
        "<label><small>Kind</small><select id='chat-pin-kind'><option value='note'>Note</option><option value='goal'>Goal</option><option value='project_constraint'>Project constraint</option><option value='reference_fact'>Reference fact</option></select></label>"
        "<label><small>Scope</small><select id='chat-pin-scope'><option value='current_session'>Current session</option><option value='current_topic'>Current topic</option><option value='until_cleared'>Until cleared</option></select></label>"
        "<label><small>Optional expiry</small><input id='chat-pin-expiry' type='datetime-local'></label>"
        "<label class='chat-pin-content-label'><small>Working context</small><textarea id='chat-pin-content' rows='2' maxlength='1200' placeholder='Pin a bounded note, goal, constraint, or reference fact for this conversation.'></textarea></label>"
        "<div class='inline'><button id='chat-pin-add' type='button' data-conversation-control-mutation>Add pinned context</button><button id='chat-pin-clear' type='button' data-conversation-control-mutation>Clear all pins</button></div>"
        "</div><small>Pins are private, session-local, bounded, optionally expiring, and never grant provider, approval, release, or execution authority.</small></details>"
    )
    offline_intent_panel = (
        "<details class='chat-offline-intent-control' id='chat-offline-intent-control'>"
        f"<summary>Offline intent queue Â· <span id='chat-offline-intent-label'>{_safe(queued_label)}</span></summary>"
        "<div class='chat-offline-intent-editor'><label><small>Intent</small><select id='chat-offline-intent-kind'><option value='send_current_draft'>Send current draft</option><option value='retry_failed_turn'>Retry failed turn</option><option value='regenerate_completed_turn'>Regenerate completed turn</option><option value='resend_user_turn'>Resend user turn</option><option value='open_branch_draft'>Open branch draft</option></select></label>"
        "<label><small>Optional turn id</small><input id='chat-offline-intent-turn' maxlength='160' placeholder='Required for retry, regenerate, or resend'></label>"
        "<div class='inline'><button id='chat-offline-intent-queue' type='button' data-conversation-control-mutation>Queue for review</button><button id='chat-offline-intent-clear' type='button' data-conversation-control-mutation>Clear queued intent</button></div></div>"
        "<small>Queued intent never executes or resends automatically when the provider returns. Review and confirm it explicitly.</small></details>"
    )
    conversation_controls_revision = int(active_controls.get("revision") or 0)
    session_title_map_json = json.dumps(
        {str(session.get("id") or ""): str(session.get("title") or "New conversation") for session in sessions},
        separators=(",", ":"),
    ).replace("</", "<\\/")
    session_turn_limit = 50 if compact else 80
    initial_history_window = conversation_session_turn_window(active_session_id, limit=session_turn_limit) if active_session_id else {"has_older": False, "oldest_turn_id": "", "total_turns": 0, "shown": 0}
    session_turns = list(initial_history_window.get("turns") or [])
    compact_class = " compact" if compact else ""
    session_options = "".join(
        f"<option value='{_safe(session.get('id',''))}' {'selected' if session.get('id') == active_session_id else ''}>"
        f"{_safe(session.get('display_title') or session.get('title') or 'New conversation')} Â· {_safe(session.get('turn_count', 0))} turns</option>"
        for session in sessions
    )
    transcript_html = _render_session_transcript(active_session_id, session_turns)
    continuity_summary = _conversation_continuity_summary()
    cue_items = "".join(
        f"<li><b>{_safe(cue.get('label','Continuity'))}:</b> {_safe(cue.get('text',''))}</li>"
        for cue in continuity_summary.get("cues", [])
    )
    if not cue_items:
        cue_items = "<li>No explicit nickname, preference, relationship, important-moment, or mood memories are stored yet.</li>"
    temporal_summary = continuity_summary.get("mood_moment") or {}
    current_user_mood = temporal_summary.get("user_mood") or {}
    open_moments = list(temporal_summary.get("important_moments") or [])
    current_mood_text = str(current_user_mood.get("text") or "").strip()
    temporal_status = (
        (f"Current user mood recorded Â· {_safe(current_user_mood.get('freshness','current'))}" if current_mood_text else "No current user mood recorded")
        + f" Â· {_safe(len(open_moments))} open important moment{'s' if len(open_moments) != 1 else ''}"
    )
    emotional_guard = continuity_summary.get("emotional_guard") or {}
    emotional_status = (
        "Old moods do not accumulate Â· affection escalation blocked Â· new relationship-progress claims blocked"
        if emotional_guard else "Emotional continuity guard unavailable"
    )
    continuity_panel = (
        "<details class='chat-continuity-panel' id='chat-continuity-panel'>"
        f"<summary>Continuity: {_safe(continuity_summary.get('cue_count', 0))} cues Â· "
        f"Eidolon mood {_safe(continuity_summary.get('mood_label', 'neutral'))}</summary>"
        f"<p><small>{temporal_status}</small></p>"
        f"<p><small>{emotional_status}</small></p>"
        f"<ul>{cue_items}</ul>"
        f"<small>Stable personality guard active Â· singleton conflicts defensively omitted {_safe(continuity_summary.get('singleton_conflicts_omitted', 0))}. Uses explicit durable memories only. Operator-only turns suppress personal cue content. Old moods are not assumed current and resolved moments are omitted. Raw transcripts and runtime receipts are not mined for relationship facts.</small>"
        "</details>"
    )
    curation_panel = _render_entity_association_curation_panel() + _render_relationship_memory_curation_panel()
    latest_latency = (latest or {}).get("latency") or {}
    first_token = _safe(latest_latency.get("first_token_ms", "n/a"))
    total = _safe(latency_total if (latency_total := latest_latency.get("total_ms")) is not None else "n/a")
    experience = build_conversation_experience_state(
        active_session=active,
        latest_turn=session_turns[-1] if session_turns else None,
        settings=load_settings(),
        continuity_summary=continuity_summary,
    )
    public_experience = experience.public_dict()
    catalog_rows: list[str] = []
    previous_group = ""
    for session in catalog:
        session_id = str(session.get("id") or "")
        archived = str(session.get("status") or "active") == "archived"
        group_label = str(session.get("group_label") or "Older conversations")
        if group_label != previous_group:
            catalog_rows.append(f"<li class='conversation-session-group' data-session-group='{_safe(group_label)}'>{_safe(group_label)}</li>")
            previous_group = group_label
        session_action = (
            "<form method='post' action='/action' class='inline' data-chat-session-restore>"
            "<input type='hidden' name='action' value='dashboard_chat_session_restore'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            "<button type='submit'>Restore</button></form>"
            "<form method='post' action='/action' class='inline' data-chat-session-restore-open>"
            "<input type='hidden' name='action' value='dashboard_chat_session_restore_open'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            "<button type='submit'>Restore and open</button></form>"
            if archived else ""
        )
        archive_action = "" if archived else (
            "<form method='post' action='/action' class='inline' data-chat-session-archive>"
            "<input type='hidden' name='action' value='dashboard_chat_session_archive'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            "<button type='submit'>Archive</button></form>"
        )
        catalog_rows.append(
            "<li class='conversation-session-row'>"
            f"<div><b>{_safe(session.get('display_title') or session.get('title') or 'New conversation')}</b> "
            f"<span class='badge'>{'archived' if archived else 'active'}</span> "
            f"<small>{_safe(session.get('turn_count', 0))} turns</small></div>"
            f"<small class='conversation-session-snippet'>{_safe(session.get('match_snippet') or session.get('last_turn_at') or session.get('created_at') or '')}</small>"
            "<div class='inline'>"
            f"{session_action}{archive_action}"
            "<form method='post' action='/action' class='inline' data-chat-session-rename>"
            "<input type='hidden' name='action' value='dashboard_chat_session_rename'>"
            f"<input type='hidden' name='session_id' value='{_safe(session_id)}'>"
            f"<input name='title' maxlength='72' value='{_safe(session.get('title') or '')}' aria-label='Conversation title'>"
            "<button type='submit'>Rename</button></form>"
            "</div></li>"
        )
    catalog_html = "".join(catalog_rows) or "<li>No matching conversations.</li>"
    checked = " checked" if include_archived else ""
    tools_open = " open" if session_query else ""
    catalog_page_json = json.dumps(catalog_page, separators=(",", ":")).replace("</", "<\\/")
    catalog_total = int(catalog_page.get("total") or 0)
    catalog_shown = int(catalog_page.get("shown") or 0)
    catalog_offset = int(catalog_page.get("offset") or 0)
    catalog_end = catalog_offset + catalog_shown
    catalog_summary = f"{catalog_offset + 1 if catalog_shown else 0}-{catalog_end} of {catalog_total}"
    previous_disabled = " disabled" if not catalog_page.get("has_previous") else ""
    next_disabled = " disabled" if not catalog_page.get("has_next") else ""
    return f"""
<div class='realtime-chat-shell{compact_class}' id='realtime-chat-shell' data-chat-mode='streaming-sse' data-chat-version='{_safe(RUNTIME_VERSION_TAG)}-{_safe(RUNTIME_UI_CONTRACT)}'>
  <header class='companion-chat-header'>
    <div>
      <small class='chat-eyebrow'>Conversation with Eidolon</small>
      <h2 id='companion-session-title' data-session-id='{_safe(active_session_id)}'>{_safe(public_experience['session_title'])}</h2>
    </div>
    <div class='companion-status-card' id='companion-status-card' data-state='{_safe(public_experience['state'])}' role='status' aria-live='polite' aria-atomic='true'>
      <span class='companion-status-dot' aria-hidden='true'></span>
      <span><b id='realtime-chat-status'>{_safe(public_experience['label'])}</b><small id='realtime-chat-status-detail'>{_safe(public_experience['detail'])}</small></span>
    </div>
    <span class='chat-mode-pill'>Private local conversation</span>
    <div class='chat-live-activity' id='chat-live-activity' data-active='false' aria-live='polite' aria-label='Live Eidolon activity'>
      <small>Live activity</small><div id='chat-live-activity-lines' class='chat-live-activity-lines'></div>
    </div>
    <div class='chat-tab-coordination' id='chat-tab-coordination' data-owner='false' data-conflict='false' role='status' aria-live='polite'>
      <span id='chat-tab-coordination-text'>Coordinating conversation control across tabsâ€¦</span>
      <button type='button' id='chat-tab-take-control' hidden>Take control</button>
    </div>
  </header>
  <nav class='chat-primary-conversation-bar' aria-label='Conversation navigation'>
    <form method='post' action='/action' class='inline chat-session-switch-form' id='chat-session-switch-form'>
      <input type='hidden' name='action' value='dashboard_chat_session_select'>
      <label><small>Conversation</small><select id='chat-session-selector' name='session_id' data-active-session-id='{_safe(active_session_id)}' aria-label='Choose conversation'>{session_options}</select></label>
      <button type='button' id='chat-session-open-button' aria-label='Open selected conversation'>Open</button>
    </form>
    <form method='post' action='/action' class='inline' id='chat-session-create-form' data-chat-session-create>
      <input type='hidden' name='action' value='dashboard_chat_session_new'>
      <button type='submit' aria-label='Create a new conversation'>New conversation</button>
    </form>
  </nav>
  {reentry_panel}
  {recovery_contract_html}
  <details class='chat-tools-drawer' id='chat-tools-drawer'{tools_open}>
    <summary>More conversation options</summary>
    {project_recovery_panel}
    {metadata_recovery_panel}
    {process_recovery_panel}
    {provider_recovery_html}
    {offline_session_html}
    {attention_center_html}
    {working_context_panel}
    {offline_intent_panel}
    <details class='chat-session-organizer' id='chat-session-organizer' {'open' if session_query else ''}>
      <summary>Find and organize conversations Â· <span id='conversation-catalog-summary'>{_safe(catalog_summary)}</span></summary>
      <form method='get' action='/chat-console' class='inline' id='conversation-catalog-search-form'>
        <input id='conversation-catalog-query' name='q' value='{_safe(session_query)}' placeholder='Search titles and completed conversation text'>
        <label><input id='conversation-catalog-archived' type='checkbox' name='archived' value='true'{checked}> Include archived</label>
        <button type='submit'>Search</button>
        <button type='button' id='conversation-catalog-clear'>Clear</button>
      </form>
      <ul class='conversation-session-list' id='conversation-session-list'>{catalog_html}</ul>
      <div class='conversation-catalog-pager' id='conversation-catalog-pager'>
        <button type='button' id='conversation-catalog-previous' data-offset='{_safe(catalog_page.get("previous_offset", 0))}'{previous_disabled}>Previous</button>
        <button type='button' id='conversation-catalog-next' data-offset='{_safe(catalog_page.get("next_offset", 0))}'{next_disabled}>Next</button>
      </div>
      <small>Archive hides a conversation without deleting private history. Search excludes failed turns and runtime receipts.</small>
    </details>
    {continuity_panel}
    {curation_panel}
  </details>
  <div class='chat-history-window-controls' id='chat-history-window-controls' data-has-older='{'true' if initial_history_window.get('has_older') else 'false'}'>
    <button type='button' id='chat-load-earlier' {' ' if initial_history_window.get('has_older') else 'hidden'} data-before-turn-id='{_safe(initial_history_window.get('oldest_turn_id',''))}'>Load earlier messages</button>
    <small id='chat-history-window-status'>Showing {_safe(initial_history_window.get('shown',0))} of {_safe(initial_history_window.get('total_turns',0))} turns.</small>
  </div>
  <div class='realtime-chat-log' id='realtime-chat-log' data-session-id='{_safe(active_session_id)}' role='log' aria-live='polite' aria-relevant='additions text' aria-atomic='false'>{transcript_html}</div>
  <button class='chat-jump-latest' id='chat-jump-latest' type='button' hidden>Latest messages</button>
  <form id='realtime-chat-form' class='realtime-chat-form' action='/api/dashboard-chat/stream' method='post'>
    <input type='hidden' id='realtime-chat-session-id' name='session_id' value='{_safe(active_session_id)}'>
    <label class='chat-composer-label'><small>Message Eidolon</small><textarea id='realtime-chat-message' name='message' rows='3' enterkeyhint='send' inputmode='text' aria-label='Message Eidolon' aria-describedby='chat-draft-status' autocomplete='off' data-session-id='{_safe(active_session_id)}' data-server-draft-updated-at='{_safe(active_draft.get("updated_at", ""))}' data-server-draft-cleared-at='{_safe(active_draft.get("cleared_at", ""))}' data-server-draft-revision='{_safe(active_draft.get("revision", 0))}' data-server-draft-digest='{_safe(active_draft.get("content_digest", ""))}' placeholder='Write naturally. Enter sends; Shift+Enter adds a new line.'>{_safe(active_draft.get("content", ""))}</textarea></label>
    <section class='chat-draft-conflict' id='chat-draft-conflict' hidden role='alert' aria-live='assertive'>
      <b>Two tabs edited this draft</b>
      <small id='chat-draft-conflict-detail'>Both versions were preserved. Choose which text should become the saved draft.</small>
      <div class='chat-draft-conflict-actions'>
        <button type='button' id='chat-draft-conflict-current' disabled>Keep saved draft</button>
        <button type='button' id='chat-draft-conflict-incoming' disabled>Use this tabâ€™s draft</button>
      </div>
    </section>
    <div class='chat-composer-actions'>
      <small class='chat-draft-status' id='chat-draft-status' data-state='saved' role='status' aria-live='polite' aria-atomic='true'>{'Draft restored' if active_draft.get('content') else 'Drafts save per conversation'}</small>
      <button id='realtime-chat-send' type='submit' aria-label='Send message to Eidolon'>Send</button>
      <button id='realtime-chat-cancel' type='button' disabled aria-label='Cancel the active response' data-tip='Cancel the active conversation operation. Partial output is not committed to memory or future session continuity.'>Cancel</button>
    </div>
    <details class='chat-steering-control' id='chat-steering-control'>
      <summary>Interrupt and redirect</summary>
      <label><small>Replacement direction</small><textarea id='chat-steering-message' rows='2' maxlength='4000' placeholder='Cancel the current response and prepare this as the next unsent message.'></textarea></label>
      <button id='chat-steering-request' type='button' disabled data-tip='Request cancellation for the exact active operation, then place this redirect in the composer without sending it automatically.'>Cancel and prepare redirect</button>
      <small>The accepted request is never edited or replayed. Wait for cancellation, review the prepared draft, then send it explicitly with a fresh acceptance identity.</small>
    </details>
  </form>
  <div class='chat-toggle-line'>
    <label><input id='realtime-chat-use-ai' type='checkbox' checked> Talk with the configured local model</label>
    <span>Provider changes keep this conversation selected.</span>
  </div>
  <details class='chat-diagnostics-drawer' id='chat-diagnostics-drawer'>
    <summary>Generation details</summary>
    <div class='chat-latency-panel'>
      <span>Provider: <b id='chat-provider-detail'>{_safe(public_experience['provider_label'])}</b></span>
      <span>Model: <b id='chat-model-detail'>{_safe(public_experience['model_label'])}</b></span>
      <span>Endpoint: <code id='chat-endpoint-detail'>{_safe(public_experience['endpoint_label'])}</code></span>
      <span>First token: <b id='chat-first-token'>{first_token}</b> ms</span>
      <span>Total saved: <b id='chat-total-time'>{total}</b> ms</span>
      <span>Session turns: <b id='chat-session-turn-count'>{_safe(active.get('turn_count', 0))}</b></span>
      <span>{_safe(public_experience['continuity_label'])}</span>
    </div>
    <div class='inline'><a class='chat-open-provider-settings' href='{_provider_settings_href()}'>Open provider settings</a></div>
    <small>These are bounded local operational details. Runtime receipts, prompts, raw responses, credentials, and stack traces remain private.</small>
  </details>
</div>
<script>
(function() {{
  const sessionTitles = {session_title_map_json};
  const initialCatalogPage = {catalog_page_json};
  const chatShell = document.getElementById('realtime-chat-shell');
  const reentryPanel = document.getElementById('conversation-reentry-panel');
  const reentryList = document.getElementById('conversation-reentry-cues');
  const providerRecoveryCue = document.getElementById('provider-recovery-resume-cue');
  const providerRecoveryLabel = document.getElementById('provider-recovery-resume-label');
  const providerRecoveryDetail = document.getElementById('provider-recovery-resume-detail');
  const providerRecoveryTime = document.getElementById('provider-recovery-resume-time');
  const recoveryContractCue = document.getElementById('chat-recovery-contract');
  const recoveryContractLabel = document.getElementById('chat-recovery-contract-label');
  const recoveryContractDetail = document.getElementById('chat-recovery-contract-detail');
  const offlineSessionCue = document.getElementById('chat-offline-session-durability');
  const offlineSessionLabel = document.getElementById('chat-offline-session-label');
  const offlineSessionDetail = document.getElementById('chat-offline-session-detail');
  const pinContent = document.getElementById('chat-pin-content');
  const pinKind = document.getElementById('chat-pin-kind');
  const pinScope = document.getElementById('chat-pin-scope');
  const pinExpiry = document.getElementById('chat-pin-expiry');
  const pinAddButton = document.getElementById('chat-pin-add');
  const pinClearButton = document.getElementById('chat-pin-clear');
  const pinnedList = document.getElementById('chat-pinned-context-list');
  const offlineIntentKind = document.getElementById('chat-offline-intent-kind');
  const offlineIntentTurn = document.getElementById('chat-offline-intent-turn');
  const offlineIntentQueue = document.getElementById('chat-offline-intent-queue');
  const offlineIntentClear = document.getElementById('chat-offline-intent-clear');
  let conversationControlsRevision = {conversation_controls_revision};
  const form = document.getElementById('realtime-chat-form');
  if (!form || form.dataset.bound === 'true') return;
  form.dataset.bound = 'true';
  const log = document.getElementById('realtime-chat-log');
  const jumpLatestButton = document.getElementById('chat-jump-latest');
  const messageBox = document.getElementById('realtime-chat-message');
  const sessionBox = document.getElementById('realtime-chat-session-id');
  const sendButton = document.getElementById('realtime-chat-send');
  const cancelButton = document.getElementById('realtime-chat-cancel');
  const steeringMessage = document.getElementById('chat-steering-message');
  const steeringButton = document.getElementById('chat-steering-request');
  const useAi = document.getElementById('realtime-chat-use-ai');
  const statusCard = document.getElementById('companion-status-card');
  const status = document.getElementById('realtime-chat-status');
  const statusDetail = document.getElementById('realtime-chat-status-detail');
  const liveActivity = document.getElementById('chat-live-activity');
  const liveActivityLines = document.getElementById('chat-live-activity-lines');
  const providerDetail = document.getElementById('chat-provider-detail');
  const modelDetail = document.getElementById('chat-model-detail');
  const endpointDetail = document.getElementById('chat-endpoint-detail');
  const firstToken = document.getElementById('chat-first-token');
  const totalTime = document.getElementById('chat-total-time');
  const draftStatus = document.getElementById('chat-draft-status');
  const draftConflict = document.getElementById('chat-draft-conflict');
  const draftConflictDetail = document.getElementById('chat-draft-conflict-detail');
  const draftConflictCurrent = document.getElementById('chat-draft-conflict-current');
  const draftConflictIncoming = document.getElementById('chat-draft-conflict-incoming');
  const sessionSwitchForm = document.getElementById('chat-session-switch-form');
  const sessionOpenButton = document.getElementById('chat-session-open-button');
  const sessionCreateForm = document.getElementById('chat-session-create-form');
  const sessionList = document.getElementById('conversation-session-list');
  const catalogSearchForm = document.getElementById('conversation-catalog-search-form');
  const catalogQuery = document.getElementById('conversation-catalog-query');
  const catalogArchived = document.getElementById('conversation-catalog-archived');
  const catalogSummary = document.getElementById('conversation-catalog-summary');
  const catalogPrevious = document.getElementById('conversation-catalog-previous');
  const catalogNext = document.getElementById('conversation-catalog-next');
  const catalogClear = document.getElementById('conversation-catalog-clear');
  const loadEarlierButton = document.getElementById('chat-load-earlier');
  const historyWindowStatus = document.getElementById('chat-history-window-status');
  const toolsDrawer = document.getElementById('chat-tools-drawer');
  const sessionOrganizer = document.getElementById('chat-session-organizer');
  const continuityPanel = document.getElementById('chat-continuity-panel');
  const continuityCuration = document.getElementById('chat-continuity-curation');
  const entityAssociationCuration = document.getElementById('chat-entity-association-curation');
  const diagnosticsDrawer = document.getElementById('chat-diagnostics-drawer');
  const attentionDrawer = document.getElementById('chat-attention-center');
  const attentionTotal = document.getElementById('attention-center-total');
  const attentionCounts = document.getElementById('attention-center-counts');
  const attentionList = document.getElementById('attention-center-list');
  const attentionRefresh = document.getElementById('attention-center-refresh');
  const attentionStatus = document.getElementById('attention-center-status');
  const sessionSelector = document.getElementById('chat-session-selector');
  const sessionTitle = document.getElementById('companion-session-title');
  const sessionTurnCount = document.getElementById('chat-session-turn-count');
  const tabCoordination = document.getElementById('chat-tab-coordination');
  const tabCoordinationText = document.getElementById('chat-tab-coordination-text');
  const tabTakeControl = document.getElementById('chat-tab-take-control');
  const initialOperation = {initial_operation_json};
  const initialActionPortal = {initial_action_portal_json};
  const initialPresentation = {initial_presentation_json};
  const initialOfflineSession = {initial_offline_session_json};
  let activeController = null;
  let composerSubmissionPending = false;
  let attentionRefreshPromise = null;
  let catalogRefreshController = null;
  let catalogRefreshSequence = 0;
  const usabilityStorageKey = 'eidolon.chat.usability.v1';
  const usabilitySurfaceIds = ['chat-tools-drawer','chat-attention-center','chat-session-organizer','chat-continuity-panel','chat-continuity-curation','chat-entity-association-curation','chat-diagnostics-drawer'];
  function readUsabilityState() {{
    let state = null;
    try {{ state = JSON.parse(window.sessionStorage.getItem(usabilityStorageKey) || 'null'); }} catch (_error) {{ state = null; }}
    if (!state || typeof state !== 'object') return {{ open_surfaces:[], catalog_query:'', include_archived:false, catalog_offset:0 }};
    return {{
      open_surfaces: Array.isArray(state.open_surfaces) ? state.open_surfaces.filter(function(value) {{ return usabilitySurfaceIds.includes(String(value)); }}) : [],
      catalog_query: String(state.catalog_query || '').slice(0, 160),
      include_archived: !!state.include_archived,
      catalog_offset: Math.max(0, Math.min(1000000, Number(state.catalog_offset) || 0))
    }};
  }}
  function captureUsabilityState() {{
    return {{
      open_surfaces: usabilitySurfaceIds.filter(function(id) {{ const node = document.getElementById(id); return !!(node && node.open); }}),
      catalog_query: catalogQuery ? String(catalogQuery.value || '').slice(0, 160) : '',
      include_archived: !!(catalogArchived && catalogArchived.checked),
      catalog_offset: Math.max(0, Number((catalogPageState && catalogPageState.offset) || 0) || 0)
    }};
  }}
  function persistUsabilityState() {{
    try {{ window.sessionStorage.setItem(usabilityStorageKey, JSON.stringify(captureUsabilityState())); }} catch (_error) {{}}
  }}
  function restoreUsabilityState() {{
    const state = readUsabilityState();
    if (catalogQuery && !catalogQuery.value && state.catalog_query) catalogQuery.value = state.catalog_query;
    if (catalogArchived && !catalogArchived.checked && state.include_archived) catalogArchived.checked = true;
    state.open_surfaces.forEach(function(id) {{ const node = document.getElementById(id); if (node) node.open = true; }});
    return state;
  }}
  const chatHistorySchema = 'eidolon-chat-history-v1';
  let restoringBrowserHistory = false;
  let initialHistoryRestorationPending = !!(window.history && window.history.state && window.history.state.schema === chatHistorySchema);
  function currentChatHistoryState() {{
    const presentation = capturePresentation(String(sessionBox.value || ''));
    return {{
      schema:chatHistorySchema,
      session_id:String(sessionBox.value || ''),
      catalog_query:catalogQuery ? String(catalogQuery.value || '').slice(0,160) : '',
      include_archived:!!(catalogArchived && catalogArchived.checked),
      catalog_offset:Math.max(0, Number((catalogPageState && catalogPageState.offset) || 0) || 0),
      view_anchor_turn_id:String(presentation.view_anchor_turn_id || ''),
      view_anchor_offset_px:Number(presentation.view_anchor_offset_px) || 0,
      content_free:true
    }};
  }}
  function writeChatHistoryState(mode) {{
    if (restoringBrowserHistory || initialHistoryRestorationPending || !window.history || typeof window.history[mode + 'State'] !== 'function') return;
    const state = currentChatHistoryState();
    const params = new URLSearchParams();
    if (state.catalog_query) params.set('q', state.catalog_query);
    if (state.include_archived) params.set('archived', 'true');
    if (state.catalog_offset) params.set('offset', String(state.catalog_offset));
    if (state.session_id) params.set('session', state.session_id);
    const url = '/chat-console' + (params.toString() ? '?' + params.toString() : '');
    window.history[mode + 'State'](state, '', url);
  }}
  async function restoreChatHistoryState(state, reason) {{
    if (!state || state.schema !== chatHistorySchema) return reconcileActiveSessionSnapshot(reason || 'history-return');
    restoringBrowserHistory = true;
    try {{
      if (catalogQuery) catalogQuery.value = String(state.catalog_query || '');
      if (catalogArchived) catalogArchived.checked = !!state.include_archived;
      await refreshConversationOrganizer(Number(state.catalog_offset || 0));
      if (!sessionIdentityResolved) await reconcileActiveSessionSnapshot(reason || 'history-return');
      const target = String(state.session_id || '');
      if (target && target !== String(sessionBox.value || '')) await switchConversationSession(target, {{ historyRestore:true }});
      const anchor = String(state.view_anchor_turn_id || '');
      if (anchor) {{
        const node = Array.from(log.querySelectorAll('[data-session-turn-id]')).find(function(candidate) {{
          return String(candidate.dataset.sessionTurnId || '') === anchor;
        }});
        if (node) log.scrollTop += Math.round(node.getBoundingClientRect().top - log.getBoundingClientRect().top - Number(state.view_anchor_offset_px || 0));
      }}
    }} finally {{
      restoringBrowserHistory = false;
      initialHistoryRestorationPending = false;
      writeChatHistoryState('replace');
    }}
    return true;
  }}
  let activeOperationId = '';
  let currentDraftKey = '';
  let draftSaveTimer = null;
  let draftSaveSequence = 0;
  let presentationSaveTimer = null;
  let presentationSaveSequence = 0;
  let foregroundTurnSequence = 0;
  const operationPollTimers = new Map();
  const pendingSubmissions = new Map();
  let explicitResendContext = null;
  let activeDraftConflict = null;
  let currentPresentationState = Object.assign({{}}, initialPresentation || {{}});
  let draftClearedOperationId = '';
  let selectedSessionId = sessionBox.value || '';
  let selectionRequestToken = 0;
  let sessionIdentityResolved = false;
  function renderAttentionCenter(payload) {{
    if (!payload || payload.ok === false || !attentionList) return false;
    const counts = payload.counts || {{}};
    if (attentionTotal) attentionTotal.textContent = String(counts.total_attention || 0);
    if (attentionCounts) {{
      attentionCounts.replaceChildren();
      [
        ['approvals', counts.pending_approvals],
        ['notifications', counts.unread_notifications],
        ['tasks', counts.open_tasks],
        ['conversation updates', counts.conversation_updates],
        ['action issues', counts.action_attention]
      ].forEach(function(entry) {{
        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = entry[0] + ' ' + String(entry[1] || 0);
        attentionCounts.appendChild(badge);
      }});
    }}
    attentionList.replaceChildren();
    const items = Array.isArray(payload.items) ? payload.items : [];
    if (!items.length) {{
      const empty = document.createElement('li');
      empty.className = 'attention-center-empty';
      empty.textContent = 'Nothing currently needs attention.';
      attentionList.appendChild(empty);
    }} else {{
      items.forEach(function(item) {{
        const row = document.createElement('li');
        row.className = 'attention-center-item';
        row.dataset.attentionKind = String(item.kind || 'item');
        row.dataset.attentionStatus = String(item.status || '');
        row.dataset.requiresOperator = item.requires_operator ? 'true' : 'false';
        const head = document.createElement('div');
        head.className = 'attention-center-item-head';
        [String(item.kind || 'item'), String(item.status || '')].forEach(function(label) {{
          const badge = document.createElement('span');
          badge.className = 'badge';
          badge.textContent = label;
          head.appendChild(badge);
        }});
        const title = document.createElement('b');
        title.textContent = String(item.title || 'Attention item');
        head.appendChild(title);
        row.appendChild(head);
        const summary = document.createElement('small');
        summary.textContent = String(item.summary || '');
        row.appendChild(summary);
        if (typeof item.href === 'string' && item.href.startsWith('/')) {{
          const link = document.createElement('a');
          link.href = item.href;
          link.textContent = 'Open';
          row.appendChild(link);
        }}
        attentionList.appendChild(row);
      }});
    }}
    if (attentionStatus) attentionStatus.textContent = 'Updated read-only attention snapshot. No state was changed.';
    return true;
  }}
  async function refreshAttentionCenter() {{
    if (!attentionList) return false;
    if (attentionRefreshPromise) return attentionRefreshPromise;
    const request = (async function() {{
      if (attentionRefresh) attentionRefresh.disabled = true;
      attentionList.setAttribute('aria-busy', 'true');
      if (attentionStatus) attentionStatus.textContent = 'Refreshing read-only attention snapshotâ€¦';
      try {{
        const response = await fetch('/api/dashboard-chat/attention-center', {{ method:'GET', cache:'no-store' }});
        const payload = await response.json();
        if (!response.ok || !renderAttentionCenter(payload)) throw new Error(payload.error || 'attention refresh failed');
        return true;
      }} catch (_error) {{
        if (attentionStatus) attentionStatus.textContent = 'Attention snapshot could not be refreshed. No state was changed.';
        return false;
      }} finally {{
        attentionList.removeAttribute('aria-busy');
        if (attentionRefresh) attentionRefresh.disabled = false;
      }}
    }})();
    attentionRefreshPromise = request;
    try {{ return await request; }} finally {{ if (attentionRefreshPromise === request) attentionRefreshPromise = null; }}
  }}
  if (attentionRefresh) attentionRefresh.addEventListener('click', refreshAttentionCenter);
  if (attentionDrawer) attentionDrawer.addEventListener('toggle', function() {{ persistUsabilityState(); if (attentionDrawer.open) refreshAttentionCenter(); }});
  window.setInterval(function() {{ if (attentionDrawer && attentionDrawer.open && !document.hidden) refreshAttentionCenter(); }}, 30000);
  let sessionReentryPromise = null;
  const navigationStorageKey = 'eidolon.chat.navigation.v1';
  function loadNavigationState() {{
    let state = null;
    try {{ state = JSON.parse(window.sessionStorage.getItem(navigationStorageKey) || 'null'); }} catch (_error) {{ state = null; }}
    const validClient = state && typeof state.client_id === 'string' && /^[a-f0-9-]{{36}}$/.test(state.client_id);
    const clientId = validClient ? state.client_id : ((window.crypto && typeof window.crypto.randomUUID === 'function') ? window.crypto.randomUUID() : '00000000-0000-4000-8000-' + Math.random().toString(16).slice(2).padEnd(12, '0').slice(0, 12));
    const generation = state && Number.isFinite(Number(state.generation)) ? Math.max(0, Number(state.generation)) : 0;
    const result = {{ client_id: clientId, generation: generation }};
    try {{ window.sessionStorage.setItem(navigationStorageKey, JSON.stringify(result)); }} catch (_error) {{}}
    return result;
  }}
  const navigationState = loadNavigationState();
  const tabCoordinationStorageKey = 'eidolon.chat.tab-coordination.v1';
  const browserIdentityStorageKey = 'eidolon.chat.browser-identity.v1';
  const coordinationBroadcastKey = 'eidolon.chat.coordination.broadcast.v1';
  const activeProjectId = {json.dumps(active_project_id)};
  const initialProjectRecovery = {initial_project_recovery_json};
  const projectRecoveryPanel = document.getElementById('chat-project-recovery');
  const projectRecoveryName = document.getElementById('chat-project-recovery-name');
  const projectRecoverySource = document.getElementById('chat-project-recovery-source');
  const projectRecoverySwitch = document.getElementById('chat-project-recovery-switch');
  const projectRecoveryCorrection = document.getElementById('chat-project-recovery-correction');
  const projectRecoveryMessage = document.getElementById('chat-project-recovery-message');
  const projectRecoveryRefresh = document.getElementById('chat-project-recovery-refresh');
  let projectRecoveryState = initialProjectRecovery || {{}};
  const metadataRecoveryPanel = document.getElementById('chat-metadata-recovery');
  const metadataRecoveryStatus = document.getElementById('chat-metadata-recovery-status');
  const metadataRecoveryBusy = document.getElementById('chat-metadata-recovery-busy');
  const metadataRecoveryPending = document.getElementById('chat-metadata-recovery-pending');
  const metadataRecoveryReview = document.getElementById('chat-metadata-recovery-review');
  const metadataRecoveryMessage = document.getElementById('chat-metadata-recovery-message');
  const metadataRecoveryRefresh = document.getElementById('chat-metadata-recovery-refresh');
  const processRecoveryPanel = document.getElementById('chat-process-recovery');
  const processRecoveryStatus = document.getElementById('chat-process-recovery-status');
  const processRecoveryActive = document.getElementById('chat-process-recovery-active');
  const processRecoveryCancel = document.getElementById('chat-process-recovery-cancel');
  const processRecoveryUncertain = document.getElementById('chat-process-recovery-uncertain');
  const processRecoveryMessage = document.getElementById('chat-process-recovery-message');
  const processRecoveryRows = document.getElementById('chat-process-recovery-rows');
  const processRecoveryRefresh = document.getElementById('chat-process-recovery-refresh');
  const coordinationInstanceNonce = (window.crypto && typeof window.crypto.randomUUID === 'function') ? window.crypto.randomUUID() : ('instance-' + Date.now() + '-' + Math.random().toString(16).slice(2));
  function randomUuid() {{
    return (window.crypto && typeof window.crypto.randomUUID === 'function')
      ? window.crypto.randomUUID()
      : '00000000-0000-4000-8000-' + Math.random().toString(16).slice(2).padEnd(12, '0').slice(0, 12);
  }}
  function newConversationOperationId() {{
    const now = new Date();
    const pad = function(value) {{ return String(value).padStart(2, '0'); }};
    const stamp = String(now.getUTCFullYear()) + pad(now.getUTCMonth() + 1) + pad(now.getUTCDate())
      + 'T' + pad(now.getUTCHours()) + pad(now.getUTCMinutes()) + pad(now.getUTCSeconds());
    return 'conversation_' + stamp + '_' + randomUuid().replace(/-/g, '').slice(0, 12);
  }}
  function loadBrowserIdentity() {{
    let value = '';
    try {{ value = String(window.localStorage.getItem(browserIdentityStorageKey) || ''); }} catch (_error) {{ value = ''; }}
    if (!/^[a-f0-9-]{{36}}$/.test(value)) value = randomUuid();
    try {{ window.localStorage.setItem(browserIdentityStorageKey, value); }} catch (_error) {{}}
    return value;
  }}
  function loadTabCoordinationIdentity() {{
    let value = null;
    try {{ value = JSON.parse(window.sessionStorage.getItem(tabCoordinationStorageKey) || 'null'); }} catch (_error) {{ value = null; }}
    const result = {{
      tab_id: value && /^[a-f0-9-]{{36}}$/.test(String(value.tab_id || '')) ? String(value.tab_id) : randomUuid(),
      browser_id: loadBrowserIdentity(),
      lease_token: value && /^[a-f0-9]{{32,96}}$/.test(String(value.lease_token || '')) ? String(value.lease_token) : '',
      revision: value && Number.isFinite(Number(value.revision)) ? Math.max(0, Number(value.revision)) : 0
    }};
    try {{ window.sessionStorage.setItem(tabCoordinationStorageKey, JSON.stringify(result)); }} catch (_error) {{}}
    return result;
  }}
  let tabIdentity = loadTabCoordinationIdentity();
  let coordinationState = {{ is_owner:false, owner_present:false, revision:tabIdentity.revision || 0, status:'starting', lease_token:tabIdentity.lease_token || '' }};
  function projectRevisionControls() {{
    return [sessionSelector, sessionOpenButton, document.querySelector('#chat-session-create-form button'), sendButton, cancelButton, steeringButton].filter(Boolean);
  }}
  function applyProjectRecoveryState(payload) {{
    if (!payload || typeof payload !== 'object') return false;
    projectRecoveryState = payload;
    const project = payload.project || {{}};
    const source = payload.source || {{}};
    const switching = payload.switch || {{}};
    const correction = payload.root_correction || {{}};
    const controls = payload.controls || {{}};
    const stale = String(payload.status || '') === 'stale_tab' || !!switching.stale_tab || !!controls.refresh_required;
    if (projectRecoveryPanel) projectRecoveryPanel.dataset.status = String(payload.status || 'unknown');
    if (projectRecoveryName) projectRecoveryName.textContent = String(project.name || 'Unknown project');
    if (projectRecoverySource) projectRecoverySource.textContent = 'source ' + String(source.status || 'unknown').replace(/_/g, ' ');
    if (projectRecoverySwitch) projectRecoverySwitch.textContent = 'revision ' + String(Number(switching.revision || 0));
    if (projectRecoveryCorrection) projectRecoveryCorrection.hidden = !correction.pending;
    if (projectRecoveryMessage) projectRecoveryMessage.textContent = String(payload.message || 'Project recovery state updated.');
    projectRevisionControls().forEach(function(control) {{
      control.dataset.projectRevisionStale = stale ? 'true' : 'false';
      if (stale) control.disabled = true;
    }});
    if (stale) setStatus('attention', 'This tab has an older project revision. Refresh project state before changing conversations or operations.');
    return true;
  }}
  async function refreshProjectRecoveryState() {{
    if (!projectRecoveryRefresh) return false;
    projectRecoveryRefresh.disabled = true;
    try {{
      const query = new URLSearchParams({{ tab_id:String(tabIdentity.tab_id || ''), expected_switch_revision:String((projectRecoveryState.switch || {{}}).revision || 0) }});
      const response = await fetch('/api/project-recovery-state?' + query.toString(), {{ method:'GET', cache:'no-store' }});
      const payload = await response.json();
      if (!response.ok || !applyProjectRecoveryState(payload)) throw new Error(payload.error || 'project recovery refresh failed');
      return true;
    }} catch (_error) {{
      if (projectRecoveryMessage) projectRecoveryMessage.textContent = 'Project recovery state could not be refreshed. No project, conversation, provider, or source-root state changed.';
      return false;
    }} finally {{ projectRecoveryRefresh.disabled = false; }}
  }}
  applyProjectRecoveryState(projectRecoveryState);
  if (projectRecoveryRefresh) projectRecoveryRefresh.addEventListener('click', refreshProjectRecoveryState);
  window.setTimeout(refreshProjectRecoveryState, 0);
  function applyMetadataRecoveryState(payload) {{
    if (!payload || typeof payload !== 'object') return false;
    const summary = payload.summary || {{}};
    const status = String(payload.status || 'uncertain');
    if (metadataRecoveryPanel) metadataRecoveryPanel.dataset.status = status;
    if (metadataRecoveryStatus) metadataRecoveryStatus.textContent = status.replace(/_/g, ' ');
    if (metadataRecoveryBusy) metadataRecoveryBusy.textContent = 'busy ' + String(Number(summary.busy_store_count || 0));
    if (metadataRecoveryPending) metadataRecoveryPending.textContent = 'recovery ' + String(Number(summary.recovery_required_count || 0));
    if (metadataRecoveryReview) metadataRecoveryReview.textContent = 'review ' + String(Number(summary.operator_review_count || 0));
    if (metadataRecoveryMessage) metadataRecoveryMessage.textContent = String(payload.message || 'Metadata recovery state updated.');
    return true;
  }}
  async function refreshMetadataRecoveryState() {{
    if (!metadataRecoveryRefresh) return false;
    metadataRecoveryRefresh.disabled = true;
    try {{
      const response = await fetch('/api/metadata-recovery-state', {{ method:'GET', cache:'no-store' }});
      const payload = await response.json();
      if (!response.ok || !applyMetadataRecoveryState(payload)) throw new Error('metadata recovery refresh failed');
      return true;
    }} catch (_error) {{
      if (metadataRecoveryPanel) metadataRecoveryPanel.dataset.status = 'uncertain';
      if (metadataRecoveryStatus) metadataRecoveryStatus.textContent = 'unavailable';
      if (metadataRecoveryMessage) metadataRecoveryMessage.textContent = 'Metadata recovery state could not be refreshed. Conversation, provider, and project state remain unchanged.';
      return false;
    }} finally {{ metadataRecoveryRefresh.disabled = false; }}
  }}
  if (metadataRecoveryRefresh) metadataRecoveryRefresh.addEventListener('click', refreshMetadataRecoveryState);
  window.setTimeout(refreshMetadataRecoveryState, 0);
  function escapeOperationText(value) {{
    return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {{ return ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[ch]; }});
  }}
  function applyProcessRecoveryState(payload) {{
    if (!payload || typeof payload !== 'object') return false;
    const rows = Array.isArray(payload.rows) ? payload.rows : [];
    const status = String(payload.status || 'uncertain');
    const active = rows.filter(function(row) {{ return !!row.read_only_reattached; }}).length;
    const cancelling = rows.filter(function(row) {{ return String(row.status || '') === 'cancellation_requested'; }}).length;
    const uncertain = rows.filter(function(row) {{ return !!row.uncertain_result || String(row.status || '') === 'uncertain'; }}).length;
    if (processRecoveryPanel) processRecoveryPanel.dataset.status = status;
    if (processRecoveryStatus) processRecoveryStatus.textContent = status.replace(/_/g, ' ');
    if (processRecoveryActive) processRecoveryActive.textContent = 'active ' + String(active);
    if (processRecoveryCancel) processRecoveryCancel.textContent = 'cancellation ' + String(cancelling);
    if (processRecoveryUncertain) processRecoveryUncertain.textContent = 'uncertain ' + String(uncertain);
    if (processRecoveryMessage) processRecoveryMessage.textContent = payload.history_truncated ? 'Recent exact operation state restored. Older terminal history is hidden; work was not replayed.' : (rows.length ? 'Operation visibility restored from exact persisted ownership. Work was not replayed.' : 'No project-bound process operation needs attention.');
    if (processRecoveryRows) processRecoveryRows.innerHTML = rows.map(function(row) {{
      const action = row.force_termination_available ? 'cancel' : 'request';
      const canCancel = !!row.cancellation_available || !!row.force_termination_available;
      const label = action === 'cancel' ? 'Cancel with exact escalation' : 'Request cancellation';
      const button = canCancel ? "<button type='button' class='chat-process-cancel' data-action='" + action + "' data-operation-id='" + escapeOperationText(row.operation_id) + "' data-generation='" + String(Number(row.generation || 0)) + "'>" + label + "</button>" : '';
      return "<div class='chat-process-recovery-row' data-status='" + escapeOperationText(String(row.status || 'unknown')) + "'><span><b>" + escapeOperationText(row.operation_kind || 'operation') + "</b><small>" + escapeOperationText(String(row.status || 'unknown').replace(/_/g, ' ')) + "</small></span>" + button + "</div>";
    }}).join('');
    return true;
  }}
  async function refreshProcessRecoveryState() {{
    if (processRecoveryRefresh) processRecoveryRefresh.disabled = true;
    try {{
      const query = new URLSearchParams({{project_id:String(activeProjectId || ''), session_id:String(selectedSessionId || ''), tab_id:String(tabIdentity.tab_id || ''), tab_revision:String(Number(coordinationState.revision || 0))}});
      const response = await fetch('/api/process-recovery-state?' + query.toString(), {{method:'GET', cache:'no-store'}});
      const payload = await response.json();
      if (!response.ok || !applyProcessRecoveryState(payload)) throw new Error('process recovery refresh failed');
      return true;
    }} catch (_error) {{
      if (processRecoveryPanel) processRecoveryPanel.dataset.status = 'uncertain';
      if (processRecoveryStatus) processRecoveryStatus.textContent = 'unavailable';
      if (processRecoveryMessage) processRecoveryMessage.textContent = 'Process state could not be refreshed. No operation was started, cancelled, retried, or replayed.';
      return false;
    }} finally {{ if (processRecoveryRefresh) processRecoveryRefresh.disabled = false; }}
  }}
  async function cancelProcessOperation(button) {{
    if (!button || button.disabled) return false;
    const action = String(button.dataset.action || 'request');
    button.disabled = true;
    try {{
      const response = await fetch('/api/process-operation/cancel', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{
        action:action, operation_id:String(button.dataset.operationId || ''), generation:Number(button.dataset.generation || 0),
        project_id:String(activeProjectId || ''), session_id:String(selectedSessionId || ''), tab_id:String(tabIdentity.tab_id || ''),
        tab_revision:Number(coordinationState.revision || 0), operator_confirmed:true, force_termination_permitted:action === 'cancel', cooperative_wait_seconds:1.0
      }})}});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.status || 'cancellation rejected');
      await refreshProcessRecoveryState();
      return true;
    }} catch (_error) {{
      if (processRecoveryMessage) processRecoveryMessage.textContent = 'Cancellation was not applied. Refresh exact operation state before trying again.';
      return false;
    }} finally {{ button.disabled = false; }}
  }}
  if (processRecoveryRows) processRecoveryRows.addEventListener('click', function(event) {{ const button = event.target.closest('.chat-process-cancel'); if (button) cancelProcessOperation(button); }});
  if (processRecoveryRefresh) processRecoveryRefresh.addEventListener('click', refreshProcessRecoveryState);
  window.setTimeout(refreshProcessRecoveryState, 0);
  let coordinationHeartbeatTimer = null;
  let coordinationChannel = null;
  let coordinationReconcileTimer = null;
  let lifecycleRecoveryPromise = null;
  let lifecycleRecoveryGeneration = 0;
  function saveTabCoordinationIdentity() {{
    tabIdentity.lease_token = coordinationState.lease_token || '';
    tabIdentity.revision = Number(coordinationState.revision) || 0;
    try {{ window.sessionStorage.setItem(tabCoordinationStorageKey, JSON.stringify(tabIdentity)); }} catch (_error) {{}}
  }}
  function newMutationKey(prefix) {{
    return String(prefix || 'mutation') + '_' + randomUuid();
  }}
  function tabOwnsConversationControl() {{
    return !!coordinationState.is_owner && !!coordinationState.lease_token;
  }}
  function coordinationMutationFields(mutationKey) {{
    return {{
      tab_id: tabIdentity.tab_id,
      lease_token: coordinationState.lease_token || '',
      coordination_revision: Number(coordinationState.revision) || 0,
      project_id: activeProjectId,
      mutation_key: String(mutationKey || newMutationKey('mutation'))
    }};
  }}
  function applyCoordinationState(payload, options) {{
    const value = payload && payload.coordination ? payload.coordination : payload;
    if (!value || value.ok === false) return false;
    const previousRevision = Number(coordinationState.revision) || 0;
    coordinationState = Object.assign({{}}, coordinationState, value);
    if (value.lease_token) coordinationState.lease_token = String(value.lease_token);
    else if (!value.is_owner) coordinationState.lease_token = '';
    tabIdentity.lease_token = coordinationState.lease_token || '';
    tabIdentity.revision = Number(coordinationState.revision) || 0;
    saveTabCoordinationIdentity();
    if (tabCoordination) {{
      tabCoordination.dataset.tabId = tabIdentity.tab_id;
      tabCoordination.dataset.owner = coordinationState.is_owner ? 'true' : 'false';
      const conflict = !coordinationState.is_owner && !!coordinationState.owner_present;
      tabCoordination.dataset.conflict = conflict ? 'true' : 'false';
      if (tabCoordinationText) {{
        tabCoordinationText.textContent = coordinationState.is_owner
          ? 'This tab controls conversation changes.'
          : (coordinationState.owner_present ? 'Another tab controls changes; this tab stays synchronized.' : 'Conversation control is available.');
      }}
      if (tabTakeControl) tabTakeControl.hidden = !!coordinationState.is_owner;
    }}
    setSessionMutationControlsDisabled(!sessionIdentityResolved);
    const remoteRevision = Number(coordinationState.revision) || 0;
    if (options && options.reconcile && remoteRevision > previousRevision && !coordinationState.is_owner) scheduleCoordinationReconcile('tab-update');
    return true;
  }}
  async function withBrowserCoordinationLock(callback) {{
    if (navigator.locks && typeof navigator.locks.request === 'function') {{
      return navigator.locks.request('eidolon-chat-coordination', {{ mode:'exclusive' }}, callback);
    }}
    return callback();
  }}
  async function boundedControlFetch(url, options, timeoutMs) {{
    const controller = new AbortController();
    const timer = window.setTimeout(function() {{ controller.abort(); }}, Math.max(250, Number(timeoutMs) || 5000));
    try {{
      return await fetch(url, Object.assign({{}}, options || {{}}, {{ signal:controller.signal }}));
    }} finally {{
      window.clearTimeout(timer);
    }}
  }}
  function splitSseFrames(rawBuffer, flushFinal) {{
    let source = String(rawBuffer || '');
    const frames = [];
    const delimiter = /\\r\\n\\r\\n|\\n\\n|\\r\\r/;
    while (source) {{
      const match = delimiter.exec(source);
      if (!match) break;
      frames.push(source.slice(0, match.index));
      source = source.slice(match.index + match[0].length);
    }}
    if (flushFinal && source.trim()) {{
      frames.push(source);
      source = '';
    }}
    return {{ frames:frames, remainder:source }};
  }}
  function parseSseFrame(packet) {{
    const lines = String(packet || '').split(/\\r\\n|\\r|\\n/);
    let type = 'message';
    const dataLines = [];
    for (const line of lines) {{
      if (line.startsWith('event:')) type = line.slice(6).trim();
      if (line.startsWith('data:')) {{
        let value = line.slice(5);
        if (value.startsWith(' ')) value = value.slice(1);
        dataLines.push(value);
      }}
    }}
    return {{ type:type, data:dataLines.join('\\n') }};
  }}
  function transportDelay(milliseconds) {{
    return new Promise(function(resolve) {{ window.setTimeout(resolve, Math.max(0, Number(milliseconds) || 0)); }});
  }}
  async function postCoordination(action) {{
    try {{
      const response = await boundedControlFetch('/api/dashboard-chat/coordination', {{
        method:'POST', headers:{{ 'Content-Type':'application/json' }}, cache:'no-store',
        body:JSON.stringify({{
          action:String(action || 'snapshot'), tab_id:tabIdentity.tab_id, browser_id:tabIdentity.browser_id,
          lease_token:coordinationState.lease_token || '', instance_nonce:coordinationInstanceNonce, visible:!document.hidden
        }})
      }}, 5000);
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'coordination_failed');
      if (payload.renew_tab_id) {{
        tabIdentity.tab_id = randomUuid();
        tabIdentity.lease_token = '';
        coordinationState.is_owner = false;
        coordinationState.lease_token = '';
        saveTabCoordinationIdentity();
        return postCoordination('register');
      }}
      applyCoordinationState(payload, {{ reconcile:true }});
      return payload;
    }} catch (_error) {{
      if (tabCoordinationText) tabCoordinationText.textContent = 'Tab coordination is temporarily unavailable; changes remain paused.';
      coordinationState.is_owner = false;
      setSessionMutationControlsDisabled(true);
      return null;
    }}
  }}
  async function activateCurrentBrowserTab() {{
    const registered = await postCoordination('register');
    if (registered && !registered.is_owner && registered.owner_present && !document.hidden) {{
      return postCoordination('activate');
    }}
    return registered;
  }}
  async function recoverConversationLifecycle(reason, options) {{
    const settings = Object.assign({{ allowHidden:false, restoreHistory:false }}, options || {{}});
    if (document.hidden && !settings.allowHidden) return false;
    if (lifecycleRecoveryPromise) return lifecycleRecoveryPromise;
    const generation = ++lifecycleRecoveryGeneration;
    lifecycleRecoveryPromise = (async function() {{
      const activate = tabOwnsConversationControl()
        ? function() {{ return postCoordination('heartbeat'); }}
        : activateCurrentBrowserTab;
      const coordinated = await withBrowserCoordinationLock(activate);
      if (!coordinated || generation !== lifecycleRecoveryGeneration) return false;
      scheduleCoordinationHeartbeat();
      if (settings.restoreHistory && window.history && window.history.state) {{
        await restoreChatHistoryState(window.history.state, String(reason || 'history-return'));
      }} else if (!document.hidden) {{
        await reconcileActiveSessionSnapshot(String(reason || 'history-return'));
      }}
      if (!document.hidden && activeOperationId) pollOperation(activeOperationId, {{ failureCount:0 }});
      return true;
    }})();
    try {{ return await lifecycleRecoveryPromise; }}
    finally {{ lifecycleRecoveryPromise = null; }}
  }}
  async function confirmConversationControl() {{
    if (!tabOwnsConversationControl()) return false;
    const payload = await postCoordination('heartbeat');
    return !!payload && !!payload.is_owner && !!payload.lease_token;
  }}
  function announceCoordination(kind, details) {{
    const packet = Object.assign({{
      type:'eidolon-chat-coordination', kind:String(kind || 'state_changed'), tab_id:tabIdentity.tab_id,
      instance_nonce:coordinationInstanceNonce, revision:Number(coordinationState.revision) || 0, sent_at:Date.now()
    }}, details || {{}});
    if (coordinationChannel) {{ try {{ coordinationChannel.postMessage(packet); }} catch (_error) {{}} }}
    try {{ window.localStorage.setItem(coordinationBroadcastKey, JSON.stringify(packet)); }} catch (_error) {{}}
  }}
  function scheduleCoordinationReconcile(reason) {{
    if (coordinationReconcileTimer) window.clearTimeout(coordinationReconcileTimer);
    coordinationReconcileTimer = window.setTimeout(function() {{
      coordinationReconcileTimer = null;
      reconcileActiveSessionSnapshot(reason || 'tab-update');
    }}, 60);
  }}
  function handleCoordinationPacket(packet) {{
    if (!packet || packet.type !== 'eidolon-chat-coordination') return;
    if (packet.tab_id === tabIdentity.tab_id && packet.instance_nonce && packet.instance_nonce !== coordinationInstanceNonce) {{
      if (coordinationInstanceNonce > String(packet.instance_nonce)) {{
        tabIdentity.tab_id = randomUuid();
        coordinationState.lease_token = '';
        coordinationState.is_owner = false;
        saveTabCoordinationIdentity();
        withBrowserCoordinationLock(function() {{ return postCoordination('register'); }}).then(function() {{ announceCoordination('identity_repaired'); }});
      }} else {{
        announceCoordination('identity_collision_ack', {{ target_nonce:String(packet.instance_nonce) }});
      }}
      return;
    }}
    if (packet.tab_id === tabIdentity.tab_id) return;
    if (Number(packet.revision) > Number(coordinationState.revision || 0)) coordinationState.revision = Number(packet.revision);
    if (packet.kind === 'draft_changed' || packet.kind === 'state_changed' || packet.kind === 'operation_changed' || packet.kind === 'ownership_changed') {{
      postCoordination('snapshot').then(function() {{ scheduleCoordinationReconcile('tab-update'); }});
    }}
  }}
  if ('BroadcastChannel' in window) {{
    try {{
      coordinationChannel = new BroadcastChannel('eidolon-chat-coordination-v1');
      coordinationChannel.addEventListener('message', function(event) {{ handleCoordinationPacket(event.data); }});
    }} catch (_error) {{ coordinationChannel = null; }}
  }}
  window.addEventListener('storage', function(event) {{
    if (event.key !== coordinationBroadcastKey || !event.newValue) return;
    try {{ handleCoordinationPacket(JSON.parse(event.newValue)); }} catch (_error) {{}}
  }});
  function scheduleCoordinationHeartbeat() {{
    if (coordinationHeartbeatTimer) window.clearTimeout(coordinationHeartbeatTimer);
    coordinationHeartbeatTimer = window.setTimeout(async function() {{
      const action = tabOwnsConversationControl() ? 'heartbeat' : 'snapshot';
      const payload = await postCoordination(action);
      if (payload && !payload.owner_present) {{
        await withBrowserCoordinationLock(function() {{ return postCoordination('register'); }});
        announceCoordination('ownership_changed');
      }}
      scheduleCoordinationHeartbeat();
    }}, document.hidden ? 5000 : 2500);
  }}
  function nextSelectionGeneration() {{
    navigationState.generation += 1;
    selectionRequestToken = navigationState.generation;
    try {{ window.sessionStorage.setItem(navigationStorageKey, JSON.stringify(navigationState)); }} catch (_error) {{}}
    return selectionRequestToken;
  }}
  function isCurrentSelection(sessionId, generation) {{
    return selectedSessionId === sessionId && sessionBox.value === sessionId && (generation == null || selectionRequestToken === generation);
  }}
  function sessionIdentityIsConsistent() {{
    const sessionId = String(sessionBox.value || '');
    return sessionIdentityResolved
      && selectedSessionId === sessionId
      && (!sessionTitle || String(sessionTitle.dataset.sessionId || '') === sessionId)
      && (!messageBox || String(messageBox.dataset.sessionId || '') === sessionId)
      && (!log || String(log.dataset.sessionId || '') === sessionId)
      && (!sessionSelector || String(sessionSelector.dataset.activeSessionId || '') === sessionId);
  }}
  function setSessionMutationControlsDisabled(disabled) {{
    const paused = !!disabled || !tabOwnsConversationControl();
    if (chatShell) chatShell.setAttribute('aria-busy', paused ? 'true' : 'false');
    if (sessionSelector) sessionSelector.disabled = paused || !sessionSelector.options.length;
    if (sessionOpenButton) sessionOpenButton.disabled = paused || !sessionSelector || !sessionSelector.value;
    if (sessionCreateForm) {{
      const createButton = sessionCreateForm.querySelector('button');
      if (createButton) createButton.disabled = paused;
    }}
    if (chatShell) {{
      chatShell.querySelectorAll('[data-lifecycle-action], [data-conversation-control-mutation], .conversation-session-row button, .chat-session-cue-ack-form button').forEach(function(control) {{
        control.disabled = paused;
      }});
    }}
    if (messageBox) messageBox.readOnly = paused;
    if (useAi) useAi.disabled = paused;
    sendButton.disabled = paused || !sessionBox.value || !!activeOperationId || !!activeController || composerSubmissionPending;
    cancelButton.disabled = paused || !activeOperationId;
    if (steeringButton) steeringButton.disabled = paused || !activeOperationId || !steeringMessage || !String(steeringMessage.value || '').trim();
  }}
  function bindResolvedSessionIdentity(sessionId) {{
    const identity = String(sessionId || '');
    selectedSessionId = identity;
    sessionBox.value = identity;
    if (sessionTitle) sessionTitle.dataset.sessionId = identity;
    if (messageBox) messageBox.dataset.sessionId = identity;
    if (log) log.dataset.sessionId = identity;
    if (sessionSelector) sessionSelector.dataset.activeSessionId = identity;
  }}
  function markSessionIdentityUnresolved() {{
    sessionIdentityResolved = false;
    setSessionMutationControlsDisabled(true);
  }}
  function settleTerminalControls(operationId) {{
    if (operationId && activeOperationId === operationId) activeOperationId = '';
    setSessionMutationControlsDisabled(!sessionIdentityResolved);
  }}
  function applyEmptySessionSnapshot(payload, generation) {{
    if (generation !== selectionRequestToken) return false;
    markSessionIdentityUnresolved();
    bindResolvedSessionIdentity('');
    if (sessionSelector) {{ sessionSelector.replaceChildren(); sessionSelector.value = ''; }}
    if (sessionTitle) sessionTitle.textContent = 'No conversation selected';
    if (sessionTurnCount) sessionTurnCount.textContent = '0';
    log.innerHTML = "<article class='chat-turn eidolon-turn welcome-turn'><small class='chat-speaker'>Eidolon</small><div class='chat-bubble eidolon'>Create a conversation when you are ready.</div></article>";
    messageBox.value = '';
    currentDraftKey = draftKey('');
    activeOperationId = '';
    rebuildSessionCatalog((payload && payload.catalog) || []);
    bindResolvedSessionIdentity('');
    sessionIdentityResolved = true;
    setSessionMutationControlsDisabled(false);
    setStatus('ready', 'Create a conversation to begin.');
    return true;
  }}
  async function reconcileActiveSessionSnapshot(reason) {{
    if (sessionReentryPromise) return sessionReentryPromise;
    const generation = nextSelectionGeneration();
    markSessionIdentityUnresolved();
    setStatus('switching', reason === 'history-return' ? 'Restoring the active conversation after returning.' : 'Confirming the active conversation before saving or sending.');
    const request = (async function() {{
      try {{
        const response = await boundedControlFetch('/api/dashboard-chat/active-session', {{ cache:'no-store' }}, 8000);
        const payload = await response.json();
        if (!response.ok || !payload.ok) throw new Error(payload.error || 'active_session_reconciliation_failed');
        if (generation !== selectionRequestToken) return false;
        if (payload.empty || !payload.snapshot) return applyEmptySessionSnapshot(payload, generation);
        return applySessionSnapshot(payload.snapshot, generation, Array.isArray(payload.catalog) ? payload.catalog : null);
      }} catch (_error) {{
        if (generation === selectionRequestToken) {{
          markSessionIdentityUnresolved();
          setStatus('attention', 'Conversation identity could not be reconciled yet. Saving and sending remain paused.');
        }}
        return false;
      }}
    }})();
    sessionReentryPromise = request;
    try {{
      return await request;
    }} finally {{
      if (sessionReentryPromise === request) sessionReentryPromise = null;
    }}
  }}
  const stateCopy = {{
    ready: ['Ready', 'Your conversation is saved and ready.'],
    recovered: ['Ready', 'The explicit retry completed once and was saved.'],
    draft_saving: ['Saving draft', 'Your unsent text is being saved to this conversation.'],
    switching: ['Switching conversation', 'Saving this draft before opening the selected conversation.'],
    creating: ['Creating conversation', 'Saving this conversation before creating a new one.'],
    archiving: ['Archiving conversation', 'Preserving the conversation before hiding it from the active list.'],
    restoring: ['Restoring conversation', 'Returning the archived conversation to the active list.'],
    connecting: ['Still responding', 'Eidolon is starting the accepted local response.'],
    thinking: ['Still responding', 'Eidolon is preparing a reply.'],
    responding: ['Still responding', 'The reply is arriving now.'],
    saving: ['Still responding', 'The completed reply is being saved once.'],
    cancelling: ['Cancelling safely', 'Partial output will not enter memory or future continuity.'],
    cancelled: ['Cancelled safely', 'The partial reply was excluded from memory and future continuity.'],
    attention: ['Needs recovery', 'The incomplete turn is visible but excluded from future continuity.'],
    disconnected: ['Completion uncertain', 'No automatic retry or duplicate submission occurred.'],
    offline: ['Offline mode', 'No provider will be contacted.']
  }};
  const failureAliases = {{
    provider_unavailable: 'unavailable_service', provider_disconnect: 'interrupted_stream',
    model_unavailable: 'missing_model', malformed_event: 'malformed_response',
    empty_output: 'empty_response', memory_write_failed: 'memory_write_failure'
  }};
  const failureCopy = {{
    ai_disabled: ['offline', 'Local generation is off', 'The message was recorded without contacting a provider.'],
    unavailable_service: ['offline', 'Eidolon cannot reach the local service', 'Nothing was switched or installed. History, drafts, search, action evidence, settings, and other local tools remain available.'],
    missing_model: ['offline', 'The selected model is unavailable', 'Eidolon did not pull, replace, or switch models. History, drafts, search, action evidence, settings, and other local tools remain available.'],
    invalid_configuration: ['attention', 'Local generation needs attention', 'No provider request or fallback was attempted.'],
    timeout: ['attention', 'Eidolon took too long', 'The turn stopped safely. Retry remains explicit.'],
    interrupted_stream: ['disconnected', 'The reply was interrupted', 'The incomplete reply was excluded from memory and future continuity.'],
    consumer_disconnected: ['disconnected', 'The conversation connection ended', 'No automatic retry or duplicate submission occurred.'],
    cancelled: ['cancelled', 'Cancelled safely', 'The partial reply was excluded from memory and future continuity.'],
    unsupported_streaming: ['attention', 'Streaming is unavailable', 'Nothing was switched automatically.'],
    context_limit: ['attention', 'This conversation is too large for the current model', 'The failed turn was excluded from future continuity.'],
    malformed_response: ['attention', 'The local service returned an unusable reply', 'Raw provider content was not accepted or saved.'],
    empty_response: ['attention', 'No usable reply arrived', 'The provider completed without safe content.'],
    http_failure: ['attention', 'The local request failed', 'No fallback or model switch occurred.'],
    closed_client: ['disconnected', 'The local connection closed', 'The incomplete reply was excluded from future continuity.'],
    memory_write_failure: ['attention', 'The reply could not be saved', 'The turn was not reported as complete.']
  }};
  const retryableFailures = new Set(['cancelled','timeout','unavailable_service','missing_model','invalid_configuration','interrupted_stream','consumer_disconnected','closed_client','unsupported_streaming','context_limit','malformed_response','empty_response','http_failure']);
  const settingsFailures = new Set(['timeout','unavailable_service','missing_model','invalid_configuration','interrupted_stream','consumer_disconnected','closed_client','unsupported_streaming','context_limit','malformed_response','empty_response','http_failure']);
  function setStatus(state, detail) {{
    const copy = stateCopy[state] || stateCopy.attention;
    statusCard.dataset.state = state;
    statusCard.setAttribute('aria-busy', ['draft_saving','switching','creating','archiving','restoring','connecting','thinking','responding','saving','cancelling'].includes(state) ? 'true' : 'false');
    status.textContent = copy[0];
    statusDetail.textContent = detail || copy[1];
  }}
  function resetLiveActivity() {{
    if (!liveActivity || !liveActivityLines) return;
    liveActivityLines.replaceChildren();
    liveActivity.dataset.active = 'true';
  }}
  function appendLiveActivity(payload) {{
    if (!liveActivity || !liveActivityLines) return;
    const summary = String((payload && payload.summary) || '').trim();
    if (!summary) return;
    liveActivity.dataset.active = 'true';
    const line = document.createElement('div');
    line.className = 'chat-live-activity-line';
    line.dataset.kind = String(payload.activity_kind || 'activity');
    const dot = document.createElement('span'); dot.className = 'chat-live-activity-dot'; dot.setAttribute('aria-hidden','true');
    const text = document.createElement('span'); text.textContent = summary;
    line.append(dot,text); liveActivityLines.appendChild(line);
    while (liveActivityLines.children.length > 8) liveActivityLines.firstElementChild.remove();
    liveActivityLines.scrollTop = liveActivityLines.scrollHeight;
  }}
  const companionActionLocks = new Set();
  function beginCompanionAction(key, control) {{
    if (!key || companionActionLocks.has(key)) return false;
    companionActionLocks.add(key);
    if (control) control.disabled = true;
    return true;
  }}
  function endCompanionAction(key, control) {{
    companionActionLocks.delete(key);
    if (control && control.isConnected) control.disabled = false;
  }}
  function focusComposer(options) {{
    if (!messageBox || messageBox.disabled) return;
    const settings = Object.assign({{ force:false, trigger:null }}, options || {{}});
    const active = document.activeElement;
    const eligible = settings.force || active === messageBox || (settings.trigger && active === settings.trigger);
    if (!eligible) return;
    window.requestAnimationFrame(function() {{
      const current = document.activeElement;
      const unchanged = current === active || current === messageBox;
      if (unchanged && messageBox.isConnected && !messageBox.disabled) messageBox.focus();
    }});
  }}
  function closeTemporaryCompanionSurfaces() {{
    let closed = false;
    document.querySelectorAll('.chat-tools-drawer[open],.chat-diagnostics-drawer[open],.chat-session-organizer[open],.chat-attention-center[open],.chat-continuity-panel[open],.chat-continuity-curation[open],.chat-turn-diagnostics[open]').forEach(function(node) {{
      node.removeAttribute('open');
      closed = true;
    }});
    if (closed) persistUsabilityState();
    return closed;
  }}
  function normalizedFailure(category) {{
    const token = String(category || '').toLowerCase();
    return failureAliases[token] || token || 'conversation_runtime_failure';
  }}
  function applyFailurePresentation(category, node, options) {{
    const normalized = normalizedFailure(category);
    const copy = failureCopy[normalized] || ['attention', 'The conversation stopped safely', 'The incomplete turn was excluded from memory and future continuity.'];
    if (!options || options.updateStatus !== false) setStatus(copy[0], copy[2]);
    if (node) {{
      node.dataset.failureCategory = normalized;
      node.classList.add('failed');
      node.textContent = '';
      const label = document.createElement('b');
      label.textContent = copy[1];
      const detail = document.createElement('span');
      detail.textContent = copy[2];
      node.appendChild(label);
      node.appendChild(detail);
    }}
    return normalized;
  }}
  function appendRecoveryActions(result) {{
    if (!result || result.success || !result.operation_id) return;
    const rowId = 'chat-recovery-actions-' + result.operation_id;
    const existingRow = document.getElementById(rowId);
    if (existingRow) existingRow.remove();
    const category = normalizedFailure(result.failure_category || result.completion_state);
    const recovery = result.recovery && typeof result.recovery === 'object' ? result.recovery : {{}};
    const row = document.createElement('div');
    row.id = rowId;
    row.className = 'chat-recovery-actions';
    row.dataset.turnId = result.operation_id;
    row.dataset.recoveryToken = String(recovery.recovery_cue_token || '');
    const attemptCount = Number(recovery.recovery_attempt_count || 0);
    if (attemptCount > 0) {{
      const history = document.createElement('small');
      history.className = 'muted chat-recovery-history';
      history.dataset.recoveryAttemptCount = String(attemptCount);
      history.textContent = 'Linked recovery history: ' + String(attemptCount) + ' explicit attempt' + (attemptCount === 1 ? '' : 's') + '; latest state ' + String(recovery.latest_recovery_state || 'unknown') + '. Earlier evidence remains preserved.';
      row.appendChild(history);
    }}
    if (recovery.successful_recovery_turn_id) {{
      const recovered = document.createElement('small');
      recovered.className = 'muted chat-recovery-note';
      recovered.textContent = 'Recovered successfully in a later linked turn. The original failed turn remains excluded from prompt history.';
      row.appendChild(recovered);
    }} else if (recovery.retryable && recovery.recovery_cue_token) {{
      const retryForm = document.createElement('form');
      retryForm.method = 'post';
      retryForm.action = '/action';
      retryForm.className = 'inline chat-recovery-control';
      [['action','dashboard_chat_turn_retry'],['session_id',result.session_id || sessionBox.value],['turn_id',result.operation_id],['recovery_token',recovery.recovery_cue_token],['use_ai','true']].forEach(function(pair) {{
        const input = document.createElement('input'); input.type = 'hidden'; input.name = pair[0]; input.value = pair[1] || ''; retryForm.appendChild(input);
      }});
      const retry = document.createElement('button'); retry.type = 'submit'; retry.textContent = 'Run explicit linked recovery'; retryForm.appendChild(retry); row.appendChild(retryForm);
    }} else if (retryableFailures.has(category)) {{
      const refresh = document.createElement('button'); refresh.type = 'button'; refresh.className = 'chat-refresh-recovery-state'; refresh.textContent = 'Refresh recovery state'; row.appendChild(refresh);
    }}
    if (settingsFailures.has(category)) {{
      const checkLink = document.createElement('a'); checkLink.className = 'chat-check-provider'; checkLink.href = '/local-model?return_to=chat&run_readiness=1#local-model-availability'; checkLink.textContent = 'Check configured provider'; row.appendChild(checkLink);
      const settingsLink = document.createElement('a'); settingsLink.className = 'chat-open-provider-settings'; settingsLink.href = '/local-model?return_to=chat#local-model-config-form'; settingsLink.textContent = 'Open provider settings'; row.appendChild(settingsLink);
    }}
    if (settingsFailures.has(category) || category === 'ai_disabled') {{
      const offline = document.createElement('button'); offline.type = 'button'; offline.className = 'chat-continue-offline'; offline.textContent = 'Continue without local generation'; row.appendChild(offline);
    }}
    if (row.childNodes.length) log.appendChild(row);
    const error = result.error && result.error.redacted ? result.error : {{}};
    const details = document.createElement('details'); details.className = 'chat-turn-diagnostics';
    const summary = document.createElement('summary'); summary.textContent = 'Technical details'; details.appendChild(summary);
    const lines = [
      ['Category', category], ['Provider', error.provider || result.provider || 'Local provider'],
      ['Model', error.model || result.model || 'Not selected'], ['Endpoint', error.endpoint || 'Not available'],
      ['HTTP status', error.status_code == null ? 'not available' : String(error.status_code)]
    ];
    lines.forEach(function(item) {{ const line = document.createElement('div'); const key = document.createElement('b'); key.textContent = item[0] + ': '; line.appendChild(key); line.appendChild(document.createTextNode(String(item[1]))); details.appendChild(line); }});
    const privacy = document.createElement('small'); privacy.textContent = 'Prompts, raw responses, credentials, receipts, and stack traces remain private.'; details.appendChild(privacy); log.appendChild(details);
    scrollConversation(false);
  }}
  function isFollowingConversation() {{
    return (log.scrollHeight - log.scrollTop - log.clientHeight) < 72;
  }}
  function updateJumpLatestButton() {{
    if (!jumpLatestButton) return;
    const following = isFollowingConversation();
    const unread = following ? 0 : Math.max(0, Number((currentPresentationState && currentPresentationState.unread_turn_count) || 0));
    jumpLatestButton.dataset.unreadCount = String(unread);
    jumpLatestButton.hidden = following;
    jumpLatestButton.setAttribute('aria-label', unread ? 'Jump to latest messages, ' + String(unread) + ' unread turns' : 'Jump to latest messages');
  }}
  function scrollConversation(force) {{
    if (force || isFollowingConversation()) {{
      log.scrollTop = log.scrollHeight;
      if (currentPresentationState) {{
        currentPresentationState.follow_latest = true;
        currentPresentationState.unread_turn_count = 0;
        currentPresentationState.last_seen_turn_count = orderedTurnNodes().length;
      }}
    }}
    updateJumpLatestButton();
  }}
  function bubble(role, text) {{
    const follow = role === 'user' || isFollowingConversation();
    const turn = document.createElement('article');
    turn.className = 'chat-turn ' + role + '-turn';
    const speaker = document.createElement('small');
    speaker.className = 'chat-speaker';
    const speakerName = role === 'user' ? 'Marcus' : 'Eidolon';
    const stamp = document.createElement('time');
    const now = new Date();
    stamp.dateTime = now.toISOString();
    stamp.title = 'Displayed locally; saved history uses recorded turn time';
    const dateKey = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
    const dividers = log.querySelectorAll('.chat-date-divider');
    if (!dividers.length || dividers[dividers.length - 1].dataset.chatDate !== dateKey) {{
      const divider = document.createElement('div');
      divider.className = 'chat-date-divider';
      divider.dataset.chatDate = dateKey;
      const day = now.getDate();
      const suffix = day % 100 >= 10 && day % 100 <= 20 ? 'th' : ({{1:'st',2:'nd',3:'rd'}}[day % 10] || 'th');
      divider.textContent = now.toLocaleString('en-US', {{month:'long'}}) + ' ' + day + suffix + ', ' + now.getFullYear();
      log.appendChild(divider);
    }}
    stamp.textContent = '[' + (now.getHours() % 12 || 12) + ':' + String(now.getMinutes()).padStart(2, '0') + (now.getHours() < 12 ? 'am' : 'pm') + ']';
    speaker.appendChild(stamp);
    speaker.appendChild(document.createTextNode(' ' + speakerName + ':'));
    const node = document.createElement('div');
    node.className = 'chat-bubble ' + role;
    node.textContent = text || '';
    turn.appendChild(speaker);
    turn.appendChild(node);
    log.appendChild(turn);
    if (follow) scrollConversation(true);
    return node;
  }}
  function ensureActionCardActions(card) {{
    let actions = card.querySelector('.chat-action-portal-actions');
    if (!actions) {{
      actions = document.createElement('div');
      actions.className = 'chat-action-portal-actions';
      card.appendChild(actions);
    }}
    return actions;
  }}
  function normalizedActionStatus(value) {{
    const raw = String(value || 'proposed').toLowerCase().trim();
    if (['executed','complete','success','succeeded','info'].includes(raw)) return 'completed';
    if (['approval_required','approval_created','pending_approval'].includes(raw)) return 'awaiting_approval';
    if (['timeout','timedout'].includes(raw)) return 'timed_out';
    if (raw === 'canceled') return 'cancelled';
    return raw || 'proposed';
  }}
  function actionStatusLabel(value) {{
    const normalized = normalizedActionStatus(value).replace(/_/g, ' ').trim();
    return normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : 'Proposed';
  }}
  function renderActionTimeline(card, portal, restored) {{
    if (!card) return;
    const events = Array.isArray(portal && portal.activity_timeline)
      ? portal.activity_timeline
      : (Array.isArray(portal && portal.action_events) ? portal.action_events.slice(-12) : []);
    let details = card.querySelector('[data-action-timeline]');
    if (!events.length && !restored) {{ if (details) details.remove(); return; }}
    if (!details) {{
      details = document.createElement('details'); details.className = 'chat-action-timeline'; details.dataset.actionTimeline = 'true';
      const summary = document.createElement('summary'); details.appendChild(summary);
      const list = document.createElement('ol'); details.appendChild(list);
      card.insertBefore(details, ensureActionCardActions(card));
    }}
    const total = Number((portal && portal.timeline_total) || events.length || 0);
    const pruned = Number((portal && portal.timeline_pruned) || 0);
    details.querySelector('summary').textContent = 'Activity timeline (' + String(total) + ' events' + (pruned ? '; ' + String(pruned) + ' older summarized' : '') + ')';
    const list = details.querySelector('ol'); list.replaceChildren();
    events.forEach(function(event) {{
      const item = document.createElement('li'); item.dataset.actionEventSequence = String(event.sequence || '');
      const label = document.createElement('b'); label.textContent = actionStatusLabel(event.status || event.type || 'event'); item.appendChild(label);
      const attempt = Number(event.attempt_number || 0); const owner = String(event.owner_scope || '');
      const suffix = (attempt ? ' Â· attempt ' + String(attempt) : '') + (owner ? ' Â· ' + owner : '');
      item.appendChild(document.createTextNode(suffix + ': ' + String(event.summary || 'Persisted action event.'))); list.appendChild(item);
    }});
    if (restored) {{
      const item = document.createElement('li'); item.dataset.actionEventRestored = 'true';
      const label = document.createElement('b'); label.textContent = 'Restored'; item.appendChild(label);
      item.appendChild(document.createTextNode(': Rehydrated from persisted redacted evidence without execution.')); list.appendChild(item);
    }}
  }}
  function setActionCardRetry(card, allowed, actionId, sessionId, turnId) {{
    if (!card) return;
    const actions = ensureActionCardActions(card);
    const existing = actions.querySelector('[data-chat-action-retry]');
    if (!allowed) {{
      if (existing) existing.remove();
      return;
    }}
    if (existing) {{
      const button = existing.querySelector('button');
      if (button) button.disabled = false;
      return;
    }}
    const form = document.createElement('form');
    form.method = 'post'; form.action = '/action'; form.className = 'inline'; form.dataset.chatActionRetry = 'true';
    [['action','chat_action_execute'],['chat_action_id',String(actionId || '')],['retry','true'],['session_id',String(sessionId || selectedSessionId || '')],['turn_id',String(turnId || '')]].forEach(function(pair) {{
      const input = document.createElement('input'); input.type = 'hidden'; input.name = pair[0]; input.value = pair[1]; form.appendChild(input);
    }});
    const button = document.createElement('button'); button.type = 'submit'; button.textContent = 'Retry safe action once'; form.appendChild(button); actions.prepend(form);
  }}
  function updateLinkedTargetCard(result) {{
    const targetId = String((result && result.target_action_id) || '');
    if (!targetId) return;
    const card = document.getElementById('chat-inline-action-' + targetId);
    if (!card) return;
    const targetStatus = normalizedActionStatus(result.target_status || (result.ok ? 'completed' : 'failed'));
    card.dataset.actionStatus = targetStatus;
    const badge = card.querySelector('[data-action-field="status"]');
    if (badge) badge.textContent = actionStatusLabel(card.dataset.actionStatus);
    const execution = card.querySelector('[data-action-execution]');
    if (execution) execution.textContent = String(result.message || 'The linked action state changed.');
    const retryAllowed = ['failed','timed_out'].includes(card.dataset.actionStatus)
      && String(card.dataset.executionMode || '') === 'direct_command'
      && String(card.dataset.riskLevel || '') === 'low';
    setActionCardRetry(card, retryAllowed, targetId, selectedSessionId, '');
    card.querySelectorAll('.chat-action-portal-actions form:not([data-chat-action-retry]) button').forEach(function(button) {{ button.disabled = true; }});
  }}
  function appendChatActionCard(action, replyNode) {{
    if (!action || !action.id) return null;
    const cardId = 'chat-inline-action-' + String(action.id);
    let card = document.getElementById(cardId);
    if (card) {{
      card.classList.add('chat-action-portal', 'chat-inline-action');
      card.dataset.actionStatus = normalizedActionStatus(action.status || card.dataset.actionStatus || 'proposed');
      card.dataset.executionMode = String(action.execution_mode || card.dataset.executionMode || 'review');
      card.dataset.riskLevel = String(action.risk_level || card.dataset.riskLevel || 'unknown');
      ensureActionCardActions(card);
      return card;
    }}
    card = document.createElement('section');
    card.id = cardId;
    card.className = 'chat-action-portal chat-inline-action';
    card.dataset.actionId = String(action.id);
    card.dataset.actionStatus = normalizedActionStatus(action.status || 'proposed');
    card.dataset.executionMode = String(action.execution_mode || 'review');
    card.dataset.riskLevel = String(action.risk_level || 'unknown');

    const badges = document.createElement('div');
    badges.className = 'chat-action-portal-head';
    [['status',actionStatusLabel(action.status || 'proposed')],['mode',action.execution_mode || 'review'],['risk','risk: ' + String(action.risk_level || 'unknown')]].forEach(function(item) {{
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.dataset.actionField = item[0];
      badge.textContent = String(item[1]);
      badges.appendChild(badge);
    }});
    card.appendChild(badges);
    const title = document.createElement('b'); title.textContent = String(action.title || 'Supervised action'); card.appendChild(title);
    const summary = document.createElement('p'); summary.textContent = String(action.summary || ''); card.appendChild(summary);
    const execution = document.createElement('small');
    execution.dataset.actionExecution = 'true';
    execution.textContent = action.execution_mode === 'direct_command' && action.risk_level === 'low'
      ? 'This allowlisted read-only action will run once after the reply completes.'
      : action.execution_mode === 'action_retry' && action.risk_level === 'low'
        ? 'This exact failed or timed-out low-risk action will retry once after the reply; earlier attempt evidence remains preserved.'
        : action.execution_mode === 'action_cancel' && action.risk_level === 'low'
          ? 'This exact still-pending action is being held before provider generation starts.'
          : 'This action is prepared for explicit review. Nothing protected runs automatically.';
    card.appendChild(execution);
    renderActionTimeline(card, action, false);

    const actions = ensureActionCardActions(card);
    const actionStatus = String(action.status || 'proposed').toLowerCase();
    if (['proposed','approval_required'].includes(actionStatus) && ['direct_function','approval'].includes(String(action.execution_mode || ''))) {{
      const form = document.createElement('form'); form.method = 'post'; form.action = '/action'; form.className = 'inline';
      [['action','chat_action_execute'],['chat_action_id',String(action.id)]].forEach(function(pair) {{
        const input = document.createElement('input'); input.type = 'hidden'; input.name = pair[0]; input.value = pair[1]; form.appendChild(input);
      }});
      const button = document.createElement('button'); button.type = 'submit'; button.textContent = action.execution_mode === 'approval' ? 'Review approval' : 'Run prepared action'; form.appendChild(button); actions.appendChild(form);
    }}
    const details = document.createElement('a'); details.href = '/detail?kind=chat_action&id=' + encodeURIComponent(String(action.id)); details.textContent = 'Action details'; actions.appendChild(details);
    const anchor = replyNode && replyNode.closest ? replyNode.closest('.chat-turn') : null;
    if (anchor && anchor.parentNode === log) anchor.insertAdjacentElement('afterend', card); else log.appendChild(card);
    scrollConversation(false);
    return card;
  }}
  function renderResearchProgress(card, progress) {{
    if (!card) return;
    let panel = card.querySelector('[data-research-progress]');
    if (!progress || !progress.session_id) {{
      if (panel) panel.remove();
      return;
    }}
    if (!panel) {{
      panel = document.createElement('section');
      panel.className = 'chat-research-progress';
      panel.dataset.researchProgress = 'true';
      const head = document.createElement('div'); head.className = 'chat-research-progress-head';
      const stage = document.createElement('b'); stage.dataset.researchStage = 'true'; head.appendChild(stage);
      const percent = document.createElement('span'); percent.dataset.researchPercent = 'true'; head.appendChild(percent);
      panel.appendChild(head);
      const meter = document.createElement('progress'); meter.max = 100; panel.appendChild(meter);
      const counts = document.createElement('small'); counts.dataset.researchCounts = 'true'; panel.appendChild(counts);
      const recovery = document.createElement('small'); recovery.dataset.researchRecovery = 'true';
      recovery.textContent = 'Refresh reconnects to this exact session. A process restart fails closed and never replays external requests.';
      panel.appendChild(recovery);
      card.insertBefore(panel, ensureActionCardActions(card));
    }}
    const rawPercent = Math.max(0, Math.min(100, Number(progress.progress_percent || 0)));
    const stageText = String(progress.progress_stage || 'starting').replaceAll('_', ' ');
    panel.dataset.researchState = String(progress.state || 'unknown');
    panel.dataset.researchRevision = String(progress.store_revision || 0);
    const stage = panel.querySelector('[data-research-stage]');
    if (stage) stage.textContent = stageText.replace(/\\b\\w/g, function(letter) {{ return letter.toUpperCase(); }});
    const percent = panel.querySelector('[data-research-percent]');
    if (percent) percent.textContent = String(Math.round(rawPercent)) + '%';
    const meter = panel.querySelector('progress');
    if (meter) {{ meter.value = rawPercent; meter.setAttribute('aria-label', 'Research progress: ' + stageText + ', ' + String(Math.round(rawPercent)) + ' percent'); }}
    const counts = panel.querySelector('[data-research-counts]');
    if (counts) counts.textContent = [
      String(Number(progress.query_count || 0)) + ' searches',
      String(Number(progress.observed_page_count || 0)) + ' pages',
      String(Number(progress.evidence_count || 0)) + ' evidence items',
      String(Number(progress.source_failure_count || 0)) + ' source failures'
    ].join(' Â· ');
  }}
  function renderResearchReview(card, review) {{
    if (!card) return;
    let details = card.querySelector('[data-research-review]');
    if (!review || !review.report_digest) {{
      if (details) details.remove();
      return;
    }}
    if (!details) {{
      details = document.createElement('details');
      details.className = 'chat-research-review';
      details.dataset.researchReview = 'true';
      const summary = document.createElement('summary');
      details.appendChild(summary);
      const body = document.createElement('div');
      body.className = 'chat-research-review-body';
      body.dataset.researchReviewBody = 'true';
      details.appendChild(body);
      card.insertBefore(details, ensureActionCardActions(card));
    }}
    const summary = details.querySelector('summary');
    if (summary) summary.textContent = 'Review research evidence (' + String(Number(review.citation_count || 0)) + ' citations)';
    const body = details.querySelector('[data-research-review-body]');
    if (!body) return;
    body.replaceChildren();
    const counts = document.createElement('div');
    counts.className = 'chat-research-review-counts';
    counts.dataset.researchReviewCounts = 'true';
    counts.textContent = [
      String(Number(review.verified_count || 0)) + ' verified',
      String(Number(review.inference_count || 0)) + ' inferred',
      String(Number(review.disagreement_count || 0)) + ' disputed',
      String(Number(review.missing_evidence_count || 0)) + ' gaps'
    ].join(' Â· ');
    body.appendChild(counts);
    const quality = review.quality_counts || {{}};
    const qualityLine = document.createElement('small');
    qualityLine.dataset.researchReviewQuality = 'true';
    qualityLine.textContent = 'Quality: ' + [
      String(Number(quality.high || 0)) + ' high', String(Number(quality.medium || 0)) + ' medium',
      String(Number(quality.low || 0)) + ' low', String(Number(quality.unknown || 0)) + ' unknown'
    ].join(', ');
    body.appendChild(qualityLine);
    const freshness = review.freshness_counts || {{}};
    const freshnessLine = document.createElement('small');
    freshnessLine.dataset.researchReviewFreshness = 'true';
    freshnessLine.textContent = 'Freshness: ' + [
      String(Number(freshness.fresh || 0)) + ' fresh', String(Number(freshness.stale || 0)) + ' stale',
      String(Number(freshness.unknown || 0)) + ' unknown'
    ].join(', ');
    body.appendChild(freshnessLine);
    const cues = document.createElement('small');
    cues.dataset.researchReviewCues = 'true';
    cues.textContent = 'Contradictions: ' + String(Number(review.disagreement_count || 0))
      + ' Â· Missing evidence: ' + String(Number(review.missing_evidence_count || 0))
      + ' Â· Source failures: ' + String(Number(review.source_failure_count || 0))
      + ' Â· Independent lineages: ' + String(Number(review.independent_lineage_count || 0))
      + ' Â· Repeated/derivative citations: ' + String(Number(review.repeated_or_derivative_citation_count || review.repeated_source_citation_count || 0));
    body.appendChild(cues);
    const confidenceRows = Array.isArray(review.recommendation_confidence_assessments) ? review.recommendation_confidence_assessments.slice(0, 8) : [];
    const confidenceByDigest = new Map();
    confidenceRows.forEach(function(row) {{ confidenceByDigest.set(String(row.candidate_digest || ''), row); }});
    if (confidenceRows.length) {{
      const confidence = document.createElement('section'); confidence.className = 'chat-research-confidence'; confidence.dataset.researchConfidence = 'true'; confidence.setAttribute('aria-label','Recommendation confidence');
      const heading = document.createElement('strong'); heading.textContent = 'Recommendation confidence Â· threshold ' + String(review.recommendation_confidence_threshold || 'moderate-confidence'); confidence.appendChild(heading);
      const items = document.createElement('ul');
      confidenceRows.forEach(function(row) {{
        const item = document.createElement('li'); const label = document.createElement('b'); label.textContent = String(row.title || row.candidate_digest || 'Candidate') + ': '; item.appendChild(label); item.appendChild(document.createTextNode(String(row.confidence_label || 'unsupported')));
        const reasons = Array.isArray(row.reasons) ? row.reasons.slice(0,3) : []; if (reasons.length) {{ const note = document.createElement('small'); note.textContent = reasons.join('; '); item.appendChild(note); }}
        items.appendChild(item);
      }});
      confidence.appendChild(items); body.appendChild(confidence);
    }}
    const matrixRows = Array.isArray(review.candidate_evidence_matrix) ? review.candidate_evidence_matrix.slice(0,8) : [];
    if (matrixRows.length) {{
      const dimensions = [['demand','Demand'],['competition','Competition'],['implementation_dependencies','Dependencies'],['free_tier_feasibility','Free-tier']];
      const wrap = document.createElement('div'); wrap.className='chat-research-matrix-wrap'; wrap.dataset.researchMatrix='true'; wrap.tabIndex=0; wrap.setAttribute('aria-label','Candidate evidence matrix');
      const table = document.createElement('table'); table.className='chat-research-matrix'; const caption=document.createElement('caption'); caption.textContent='Candidate evidence matrix'; table.appendChild(caption);
      const head=document.createElement('thead'); const hr=document.createElement('tr'); ['Candidate'].concat(dimensions.map(function(d){{return d[1];}})).forEach(function(text){{const th=document.createElement('th'); th.scope='col'; th.textContent=text; hr.appendChild(th);}}); head.appendChild(hr); table.appendChild(head);
      const tbody=document.createElement('tbody'); matrixRows.forEach(function(row){{ const tr=document.createElement('tr'); const th=document.createElement('th'); th.scope='row'; const assessment=confidenceByDigest.get(String(row.candidate_digest||''))||{{}}; th.textContent=String(assessment.title || (String(row.candidate_digest||'Candidate').slice(0,12)+'â€¦')); tr.appendChild(th); const cells=row.cells||{{}}; dimensions.forEach(function(d){{const cell=cells[d[0]]||{{}}; const td=document.createElement('td'); const state=document.createElement('span'); state.textContent=String(cell.matrix_state||cell.state||'not_researched').replaceAll('_',' '); td.appendChild(state); const count=document.createElement('small'); count.textContent=String(Number(cell.independent_lineage_count||0))+' independent'; td.appendChild(count); tr.appendChild(td);}}); tbody.appendChild(tr); }}); table.appendChild(tbody); wrap.appendChild(table); body.appendChild(wrap);
    }}
    const list = document.createElement('ol');
    list.className = 'chat-research-citations';
    list.dataset.researchCitations = 'true';
    (Array.isArray(review.citations) ? review.citations.slice(0, 12) : []).forEach(function(citation) {{
      let parsed;
      try {{ parsed = new URL(String(citation.public_url || '')); }} catch (_error) {{ return; }}
      if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) return;
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = parsed.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
      link.textContent = String(citation.citation_id || citation.host || 'Source');
      item.appendChild(link);
      const metadata = document.createElement('small');
      metadata.textContent = [
        String(citation.host || parsed.hostname), String(citation.source_kind || 'unknown').replaceAll('_', ' '),
        String(citation.quality || 'unknown') + ' quality', String(citation.freshness || 'unknown') + ' freshness'
      ].join(' Â· ');
      item.appendChild(metadata);
      list.appendChild(item);
    }});
    if (!list.children.length) {{
      const item = document.createElement('li'); const note = document.createElement('small');
      note.textContent = 'No reviewable public citation URL was retained.'; item.appendChild(note); list.appendChild(item);
    }}
    body.appendChild(list);
    const boundary = document.createElement('small');
    boundary.dataset.researchReviewBoundary = 'true';
    boundary.textContent = 'Report ' + String(review.report_digest).slice(0, 12)
      + 'â€¦ is digest-bound. Generated prose is synthesis, not evidence; raw pages, private objectives, and queries remain private. Opening a citation is your explicit browser action.';
    body.appendChild(boundary);
  }}
  function renderResearchHistory(card, history) {{
    if (!card) return;
    let details = card.querySelector('[data-research-history]');
    if (!history || !Array.isArray(history.sessions)) {{
      if (details) details.remove();
      return;
    }}
    if (!details) {{
      details = document.createElement('details');
      details.className = 'chat-research-history';
      details.dataset.researchHistory = 'true';
      const summary = document.createElement('summary'); details.appendChild(summary);
      const list = document.createElement('ol'); list.className = 'chat-research-history-list'; list.dataset.researchHistoryList = 'true'; details.appendChild(list);
      const workflow = document.createElement('small'); workflow.dataset.researchHistoryWorkflow = 'true';
      workflow.textContent = 'Use exact session IDs and digests to compare two completed sessions or explicitly export one completed report as Markdown.'; details.appendChild(workflow);
      const boundary = document.createElement('small'); boundary.dataset.researchHistoryBoundary = 'true';
      boundary.textContent = 'History is digest-bound and content-minimized. Private objectives, search queries, raw pages, credentials, and cookies are not projected here.';
      details.appendChild(boundary);
      card.insertBefore(details, ensureActionCardActions(card));
    }}
    const summary = details.querySelector('summary');
    if (summary) summary.textContent = 'Research history (' + String(Number(history.history_count || history.sessions.length || 0)) + ' sessions)';
    const list = details.querySelector('[data-research-history-list]');
    if (list) {{
      list.replaceChildren();
      history.sessions.slice(0, 20).forEach(function(row) {{
        const item = document.createElement('li'); item.className = 'chat-research-history-item';
        const code = document.createElement('code'); code.textContent = String(row.session_id || 'unknown session'); item.appendChild(code);
        const meta = document.createElement('small');
        const historyConfidence = Array.isArray(row.recommendation_confidence_labels) ? row.recommendation_confidence_labels.slice(0,8).map(function(item) {{ return String(item.confidence_label || 'unsupported'); }}).join(', ') : '';
        meta.textContent = [
          String(row.terminal_status || 'unknown'),
          String(Number(row.evidence_count || 0)) + ' evidence',
          String(Number(row.citation_count || 0)) + ' citations',
          'integrity ' + String(row.integrity_status || 'unknown'),
          historyConfidence ? 'confidence ' + historyConfidence : ''
        ].filter(Boolean).join(' Â· ');
        item.appendChild(meta);
        const digest = document.createElement('small'); digest.textContent = 'Report digest: ' + String(row.report_digest || 'none').slice(0, 12) + 'â€¦'; item.appendChild(digest);
        list.appendChild(item);
      }});
      if (!list.children.length) {{ const item = document.createElement('li'); const note = document.createElement('small'); note.textContent = 'No terminal research sessions are recorded yet.'; item.appendChild(note); list.appendChild(item); }}
    }}
    let warning = details.querySelector('[data-research-history-warning]');
    const missing = Array.isArray(history.missing_records) ? history.missing_records.length : 0;
    if (missing) {{
      if (!warning) {{ warning = document.createElement('small'); warning.className = 'chat-research-history-warning'; warning.dataset.researchHistoryWarning = 'true'; details.insertBefore(warning, details.lastElementChild); }}
      warning.textContent = 'Integrity warning: ' + String(missing) + ' terminal session(s) have missing catalog records. No repair was performed.';
    }} else if (warning) {{ warning.remove(); }}
  }}
  function renderResearchComparison(card, comparison) {{
    if (!card) return;
    let details = card.querySelector('[data-research-comparison]');
    if (!comparison || !comparison.left_session_id || !comparison.right_session_id) {{ if (details) details.remove(); return; }}
    if (!details) {{
      details = document.createElement('details'); details.className = 'chat-research-comparison'; details.dataset.researchComparison = 'true';
      const summary = document.createElement('summary'); details.appendChild(summary);
      const body = document.createElement('div'); body.dataset.researchComparisonBody = 'true'; details.appendChild(body);
      card.insertBefore(details, ensureActionCardActions(card));
    }}
    const summary = details.querySelector('summary');
    if (summary) summary.textContent = 'Compare research evidence: ' + String(comparison.left_session_id) + ' â†” ' + String(comparison.right_session_id);
    const body = details.querySelector('[data-research-comparison-body]'); if (!body) return; body.replaceChildren();
    const counts = document.createElement('div'); counts.className = 'chat-research-comparison-counts';
    counts.textContent = ['Changed ' + String((comparison.changed_claims || []).length), 'Added ' + String((comparison.added_claim_codes || []).length), 'Removed ' + String((comparison.removed_claim_codes || []).length), 'Stale ' + String((comparison.stale_claim_codes || []).length), 'Contradictory ' + String((comparison.contradictory_claim_codes || []).length), 'Duplicate ' + String((comparison.duplicated_claim_codes || []).length), 'Unsupported ' + String((comparison.unsupported_claim_codes || []).length), 'Confidence changes ' + String((comparison.changed_recommendation_confidence || []).length)].join(' Â· '); body.appendChild(counts);
    const digests = document.createElement('small'); digests.textContent = 'Left report ' + String(comparison.left_report_digest || '').slice(0, 12) + 'â€¦ Â· Right report ' + String(comparison.right_report_digest || '').slice(0, 12) + 'â€¦'; body.appendChild(digests);
    const boundary = document.createElement('small'); boundary.dataset.researchComparisonBoundary = 'true'; boundary.textContent = 'Content-free comparison only: no web request, no private objective or raw page, source independence preserved, no automatic winner.'; body.appendChild(boundary);
  }}
  function renderResearchExport(card, receipt) {{
    if (!card) return;
    let panel = card.querySelector('[data-research-export]');
    if (!receipt || !receipt.export_digest) {{ if (panel) panel.remove(); return; }}
    if (!panel) {{ panel = document.createElement('section'); panel.className='chat-research-export'; panel.dataset.researchExport='true'; panel.setAttribute('aria-label','Research report export'); card.insertBefore(panel, ensureActionCardActions(card)); }}
    panel.replaceChildren();
    const title=document.createElement('strong'); title.textContent='Local Markdown export ready'; panel.appendChild(title);
    const name=document.createElement('code'); name.textContent=String(receipt.file_name||''); panel.appendChild(name);
    const meta=document.createElement('small'); meta.textContent='Report '+String(receipt.report_digest||'').slice(0,12)+'â€¦ Â· Export '+String(receipt.export_digest||'').slice(0,12)+'â€¦ Â· '+String(Number(receipt.export_byte_count||0))+' bytes'; panel.appendChild(meta);
    const boundary=document.createElement('small'); boundary.dataset.researchExportBoundary='true'; boundary.textContent='Explicit local export only. Nothing was uploaded or transmitted; private objectives, raw pages, queries, credentials, provider payloads, stack traces, and private filesystem paths are excluded.'; panel.appendChild(boundary);
  }}
  function applyChatActionResult(payload, replyNode) {{
    const action = payload && payload.action ? payload.action : {{}};
    const result = payload && payload.execution ? payload.execution : {{}};
    const card = appendChatActionCard(action, replyNode);
    if (!card) return;
    const status = normalizedActionStatus(result.status || (result.ok ? 'completed' : 'failed'));
    card.dataset.actionStatus = status;
    const statusBadge = card.querySelector('[data-action-field="status"]');
    if (statusBadge) statusBadge.textContent = actionStatusLabel(status);
    const execution = card.querySelector('[data-action-execution]');
    if (execution) execution.textContent = String(result.message || (result.ok ? 'Action completed.' : 'Action failed.'));
    card.querySelectorAll('.chat-action-portal-actions form:not([data-chat-action-retry]) button').forEach(function(button) {{ button.disabled = true; }});
    const article = replyNode && replyNode.closest ? replyNode.closest('[data-session-turn-id]') : null;
    const retryAllowed = ['failed','timed_out'].includes(status)
      && String(action.execution_mode || card.dataset.executionMode || '') === 'direct_command'
      && String(action.risk_level || card.dataset.riskLevel || '') === 'low';
    setActionCardRetry(card, retryAllowed, action.id, selectedSessionId, article ? article.dataset.sessionTurnId : '');
    renderActionTimeline(card, result.portal || action, false);
    renderResearchProgress(card, (result.portal && result.portal.research_progress) || result.research_progress || result.session || null);
    renderResearchReview(card, (result.portal && result.portal.research_review) || result.research_review || null);
    renderResearchHistory(card, (result.portal && result.portal.research_history) || result.research_history || null);
    renderResearchComparison(card, (result.portal && result.portal.research_comparison) || result.research_comparison || null);
    renderResearchExport(card, (result.portal && result.portal.research_export) || result.research_export || null);
    updateLinkedTargetCard(result);
    if (result.output) {{
      let details = card.querySelector('details[data-action-output]');
      if (!details) {{
        details = document.createElement('details'); details.dataset.actionOutput = 'true';
        const summary = document.createElement('summary'); summary.textContent = 'View current-run output'; details.appendChild(summary);
        const output = document.createElement('pre'); output.dataset.actionOutputBody = 'true'; details.appendChild(output); card.appendChild(details);
      }}
      const output = details.querySelector('[data-action-output-body]');
      if (output) output.textContent = String(result.output) + (result.output_truncated ? '\\n[output truncated]' : '');
    }}
    scrollConversation(false);
  }}
  function applyPersistedActionPortal(portal, marker) {{
    if (!portal || !portal.action_id) return null;
    const operationId = marker && marker.operation_id ? String(marker.operation_id) : '';
    const article = operationId ? operationTurnNode(operationId) : null;
    const reply = article ? article.querySelector('.chat-bubble.eidolon') : null;
    const action = {{
      id:String(portal.action_id), status:String(portal.status || 'proposed'),
      execution_mode:String(portal.execution_mode || 'review'), risk_level:String(portal.risk_level || 'unknown'),
      title:String(portal.title || 'Supervised action'), summary:String(portal.summary || '')
    }};
    const card = appendChatActionCard(action, reply);
    if (!card) return null;
    card.dataset.actionStatus = normalizedActionStatus(portal.status || 'proposed');
    card.dataset.executionMode = String(portal.execution_mode || 'review');
    card.dataset.riskLevel = String(portal.risk_level || 'unknown');
    const statusBadge = card.querySelector('[data-action-field="status"]');
    if (statusBadge) statusBadge.textContent = String(portal.status_label || actionStatusLabel(portal.status));
    const modeBadge = card.querySelector('[data-action-field="mode"]');
    if (modeBadge) modeBadge.textContent = String(portal.execution_mode || 'review');
    const riskBadge = card.querySelector('[data-action-field="risk"]');
    if (riskBadge) riskBadge.textContent = 'risk: ' + String(portal.risk_level || 'unknown');
    const execution = card.querySelector('[data-action-execution]');
    if (execution) execution.textContent = String(portal.message || portal.summary || 'Persisted supervised action state.');
    let evidence = card.querySelector('[data-action-attempt-evidence]');
    const attemptNumber = Number(portal.execution_attempt || 0);
    const priorAttempts = Number(portal.prior_attempt_count || 0);
    if (attemptNumber > 0) {{
      if (!evidence) {{ evidence = document.createElement('small'); evidence.dataset.actionAttemptEvidence = 'true'; card.insertBefore(evidence, ensureActionCardActions(card)); }}
      evidence.textContent = 'Latest execution attempt: ' + String(attemptNumber) + '. Earlier preserved attempts: ' + String(priorAttempts) + '.';
    }} else if (evidence) {{
      evidence.remove();
    }}
    const actions = ensureActionCardActions(card);
    actions.querySelectorAll('form:not([data-chat-action-retry]) button').forEach(function(button) {{
      button.disabled = !['proposed','approval_required'].includes(String(portal.status || '').toLowerCase());
    }});
    setActionCardRetry(card, Boolean(portal.retry_allowed), portal.action_id, (marker && marker.session_id) || selectedSessionId || '', operationId);
    renderResearchProgress(card, portal.research_progress || null);
    renderResearchReview(card, portal.research_review || null);
    renderResearchHistory(card, portal.research_history || null);
    renderResearchComparison(card, portal.research_comparison || null);
    renderResearchExport(card, portal.research_export || null);
    renderActionTimeline(card, portal, true);
    let restored = card.querySelector('[data-action-restored]');
    if (!restored) {{
      restored = document.createElement('small'); restored.dataset.actionRestored = 'true';
      restored.textContent = 'Rehydrated from redacted persisted state. Viewing this card never executes the action again.';
      card.appendChild(restored);
    }}
    return card;
  }}
  function sessionCueFromPayload(payload) {{
    if (payload && Object.prototype.hasOwnProperty.call(payload, 'session_cue')) return payload.session_cue;
    const marker = payload && payload.operation ? payload.operation : null;
    if (!marker) return null;
    const state = String(marker.public_state || 'uncertain');
    if (state === 'completed' && !(marker.client_disconnected || marker.reconciled_late)) return null;
    const presentations = {{
      running: ['still_responding', 'Still responding', false],
      completed: ['reply_ready', 'Reply ready', true],
      failed: ['needs_recovery', 'Needs recovery', true],
      cancelled: ['cancelled', 'Cancelled', true],
      uncertain: ['completion_uncertain', 'Completion uncertain', true]
    }};
    const item = presentations[state];
    return item ? {{ kind:item[0], label:item[1], acknowledgeable:item[2] }} : null;
  }}
  function removeSessionCue(sessionId) {{
    if (!reentryList || !sessionId) return;
    reentryList.querySelectorAll('[data-session-cue-session-id]').forEach(function(node) {{
      if (node.dataset.sessionCueSessionId === sessionId) node.remove();
    }});
    if (reentryPanel) reentryPanel.hidden = reentryList.children.length === 0;
  }}
  async function acknowledgeCurrentSessionCue(sessionId, operationId, button, acknowledgementToken) {{
    if (!tabOwnsConversationControl()) {{
      setStatus('attention', 'Another tab controls conversation changes. This update was not marked seen.');
      return false;
    }}
    const acknowledgementLockKey = 'acknowledge:' + String(sessionId || '') + ':' + String(operationId || acknowledgementToken || 'current');
    if (!beginCompanionAction(acknowledgementLockKey, button || null)) return false;
    const acknowledgementMutationKey = newMutationKey('acknowledge');
    try {{
      const response = await fetch('/api/dashboard-chat/operation-acknowledge', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(Object.assign({{ session_id: sessionId, operation_id: operationId || '', acknowledgement_token: acknowledgementToken || '' }}, coordinationMutationFields(acknowledgementMutationKey))),
        cache: 'no-store'
      }});
      const payload = await response.json();
      if (payload.coordination) applyCoordinationState(payload.coordination, {{ reconcile:true }});
      if (!response.ok || !payload.ok) throw new Error(payload.message || 'acknowledgement_failed');
      removeSessionCue(sessionId);
      announceCoordination('operation_changed', {{ session_id:String(sessionId || ''), operation_id:String(operationId || '') }});
      return true;
    }} catch (_error) {{
      if (isCurrentSelection(sessionId)) setStatus('attention', 'The conversation update could not be marked seen. Its state was not changed.');
      return false;
    }} finally {{
      endCompanionAction(acknowledgementLockKey, button || null);
    }}
  }}
  function updateSessionCue(payload) {{
    if (!reentryList) return;
    const marker = payload && payload.operation ? payload.operation : null;
    if (!marker || !marker.session_id) return;
    const sessionId = String(marker.session_id);
    const cue = sessionCueFromPayload(payload);
    removeSessionCue(sessionId);
    if (!cue) return;
    const row = document.createElement('li');
    row.className = 'conversation-reentry-cue';
    row.dataset.sessionCueSessionId = sessionId;
    row.dataset.cueKind = cue.kind || '';
    const title = document.createElement('b');
    title.textContent = sessionTitles[sessionId] || 'Conversation';
    const state = document.createElement('span');
    state.className = 'conversation-reentry-cue-state';
    state.dataset.sessionOperationCue = '';
    state.textContent = cue.label || '';
    row.appendChild(title);
    row.appendChild(state);
    if (isCurrentSelection(sessionId)) {{
      if (cue.acknowledgeable) {{
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = 'Mark seen';
        button.addEventListener('click', function() {{ acknowledgeCurrentSessionCue(sessionId, marker.operation_id, button, ''); }});
        row.appendChild(button);
      }}
    }} else {{
      const open = document.createElement('button');
      open.type = 'button';
      open.textContent = 'Open';
      open.addEventListener('click', function() {{ switchConversationSession(sessionId, {{ control:open }}); }});
      row.appendChild(open);
      if (cue.acknowledgeable) {{
        const openSeen = document.createElement('button');
        openSeen.type = 'button';
        openSeen.textContent = 'Open and mark seen';
        openSeen.addEventListener('click', function() {{ switchConversationSession(sessionId, {{ acknowledgementOperationId: marker.operation_id, control:openSeen }}); }});
        row.appendChild(openSeen);
      }}
    }}
    reentryList.appendChild(row);
    if (reentryPanel) reentryPanel.hidden = false;
  }}
  function operationTurnNode(operationId) {{
    if (!operationId) return false;
    return Array.from(log.querySelectorAll('[data-session-turn-id]')).find(function(node) {{
      return node.dataset.sessionTurnId === operationId;
    }}) || null;
  }}
  function operationTurnExists(operationId) {{
    return !!operationTurnNode(operationId);
  }}
  function markReplyForReconciliation(reply, operationId) {{
    if (!reply || !operationId) return;
    const article = reply.closest('.chat-turn');
    if (article) article.dataset.sessionTurnId = operationId;
    reply.dataset.reconciliationPending = 'true';
  }}
  function appendOperationDetails(marker) {{
    if (!marker || !marker.operation_id) return;
    const detailId = 'chat-operation-details-' + marker.operation_id;
    let details = document.getElementById(detailId);
    if (!details) {{
      details = document.createElement('details');
      details.id = detailId;
      details.className = 'chat-turn-diagnostics chat-operation-diagnostics';
      const summary = document.createElement('summary');
      summary.textContent = 'Reconciliation details';
      details.appendChild(summary);
      log.appendChild(details);
    }}
    while (details.childNodes.length > 1) details.removeChild(details.lastChild);
    const rows = [
      ['Operation', marker.operation_id],
      ['State', marker.public_state || 'unknown'],
      ['Accepted', marker.accepted_at || 'not available'],
      ['Completed', marker.completed_at || 'not confirmed'],
      ['Technical category', marker.failure_category || 'none'],
      ['Cancellation requested', marker.cancellation_requested ? 'yes' : 'no'],
      ['Session turn recorded', marker.final_session_turn_recorded ? 'yes' : 'no']
    ];
    rows.forEach(function(item) {{
      const line = document.createElement('div');
      const key = document.createElement('b');
      key.textContent = item[0] + ': ';
      line.appendChild(key);
      line.appendChild(document.createTextNode(String(item[1])));
      details.appendChild(line);
    }});
    const privacy = document.createElement('small');
    privacy.textContent = 'This marker contains no message text, prompt, generated text, partial tokens, memories, provider payloads, credentials, receipts, or stack traces.';
    details.appendChild(privacy);
  }}
  function appendReconciledTurn(turn, marker, options) {{
    if (!turn || !turn.id) return;
    const existingArticle = operationTurnNode(turn.id);
    if (existingArticle) {{
      const existingReply = existingArticle.querySelector('.chat-bubble.eidolon');
      if (!existingReply) return;
      delete existingReply.dataset.reconciliationPending;
      delete existingReply.dataset.pendingReply;
      if (turn.success && turn.completion_state === 'completed') {{
        existingReply.classList.remove('failed');
        existingReply.textContent = turn.assistant_response || '';
      }} else {{
        applyFailurePresentation(turn.failure_category || turn.completion_state, existingReply, options);
        appendRecoveryActions({{
          operation_id: turn.id,
          session_id: (marker && marker.session_id) || sessionBox.value,
          success: false,
          completion_state: turn.completion_state,
          failure_category: turn.failure_category,
          provider: turn.provider,
          model: turn.model,
          error: turn.diagnostic || {{ redacted: true }},
          recovery: options && options.recovery ? options.recovery : null
        }});
      }}
      return;
    }}
    if (turn.user_message) bubble('user', turn.user_message);
    const reply = bubble('eidolon', '');
    const article = reply.closest('.chat-turn');
    if (article) article.dataset.sessionTurnId = turn.id;
    if (turn.success && turn.completion_state === 'completed') {{
      reply.textContent = turn.assistant_response || '';
    }} else {{
      applyFailurePresentation(turn.failure_category || turn.completion_state, reply, options);
      appendRecoveryActions({{
        operation_id: turn.id,
        session_id: (marker && marker.session_id) || sessionBox.value,
        success: false,
        completion_state: turn.completion_state,
        failure_category: turn.failure_category,
        provider: turn.provider,
        model: turn.model,
        error: turn.diagnostic || {{ redacted: true }},
        recovery: options && options.recovery ? options.recovery : null
      }});
    }}
  }}
  function applyTurnPresentation(presentation) {{
    if (!presentation || !presentation.state) return false;
    const state = String(presentation.state || 'idle');
    const detail = String(presentation.detail || '');
    const statusMap = {{
      accepted_running:'thinking', accepted_cancelling:'cancelling', accepted_completed:'recovered',
      accepted_completed_late:'recovered', accepted_cancelled:'cancelled', accepted_failed:'attention',
      accepted_recovery_available:'attention', accepted_recovered:'recovered', accepted_uncertain:'disconnected',
      proven_unaccepted:'attention', proven_unaccepted_claimed:'attention', acceptance_unknown:'disconnected', idle:'ready'
    }};
    setStatus(statusMap[state] || 'attention', detail || String(presentation.label || 'Conversation status updated.'));
    return true;
  }}
  function applyOperationStatus(payload, options) {{
    if (payload && payload.recovery_contract) applyRecoveryContract(payload.recovery_contract);
    const marker = payload && payload.operation ? payload.operation : null;
    if (!marker || !marker.operation_id) return;
    updateSessionCue(payload);
    const markerSessionId = String(marker.session_id || '');
    if (!isCurrentSelection(markerSessionId)) return;
    appendOperationDetails(marker);
    applyPersistedActionPortal(payload.action_portal, marker);
    const updateStatus = !options || options.updateStatus !== false;
    const state = String(marker.public_state || 'uncertain');
    if (state === 'running') {{
      if (!updateStatus) return;
      activeOperationId = marker.operation_id;
      setSessionMutationControlsDisabled(!sessionIdentityResolved);
      if (tabOwnsConversationControl()) cancelButton.disabled = !!marker.cancellation_requested;
      setStatus(marker.cancellation_requested ? 'cancelling' : 'thinking', marker.cancellation_requested ? 'Cancellation was requested for this exact turn.' : 'Eidolon is still responding. Refreshing will not submit it again.');
      return;
    }}
    if (activeOperationId === marker.operation_id) activeOperationId = '';
    appendReconciledTurn(payload.session_turn, marker, {{ updateStatus:updateStatus, recovery:payload.recovery || null }});
    applyPersistedActionPortal(payload.action_portal, marker);
    if (!updateStatus) return;
    setSessionMutationControlsDisabled(!sessionIdentityResolved);
    if (!applyTurnPresentation(payload.turn_presentation || null)) {{
      if (state === 'completed') {{
        setStatus('recovered', marker.client_disconnected || marker.reconciled_late ? 'The reply completed while you were away and was attached once.' : 'The reply completed and was saved once.');
      }} else if (state === 'cancelled') {{
        setStatus('cancelled', 'Cancelled safely. The partial reply stayed out of memory and future continuity.');
      }} else if (state === 'failed') {{
        const category = payload.session_turn ? (payload.session_turn.failure_category || payload.session_turn.completion_state) : marker.failure_category;
        applyFailurePresentation(category, null);
      }} else {{
        setStatus('disconnected', 'The connection ended before completion could be confirmed. Nothing was resubmitted or silently cancelled.');
      }}
    }}
    focusComposer();
  }}
  async function resolveAcceptanceOutcome(sessionId, acceptanceKey, attempts) {{
    if (!sessionId || !acceptanceKey) return {{ state:'not_found', payload:null }};
    const limit = Math.max(1, Math.min(4, Number(attempts) || 3));
    let reachableNotFound = false;
    for (let attempt = 0; attempt < limit; attempt += 1) {{
      try {{
        const url = '/api/dashboard-chat/operation?session_id=' + encodeURIComponent(sessionId) + '&acceptance_key=' + encodeURIComponent(acceptanceKey);
        const response = await boundedControlFetch(url, {{ cache:'no-store' }}, 3500);
        const payload = await response.json();
        if (response.ok && payload.ok && payload.operation) return {{ state:'accepted', payload:payload }};
        if (response.ok && payload.ok && !payload.operation) reachableNotFound = true;
      }} catch (_error) {{}}
      if (attempt + 1 < limit) await transportDelay(250 * Math.pow(2, attempt));
    }}
    return {{ state:reachableNotFound ? 'not_found' : 'unavailable', payload:null }};
  }}
  async function resolveAcceptanceByKey(sessionId, acceptanceKey) {{
    const outcome = await resolveAcceptanceOutcome(sessionId, acceptanceKey, 3);
    return outcome.state === 'accepted' ? outcome.payload : null;
  }}
  async function persistNonAcceptanceEvidence(sessionId, acceptanceKey, reason) {{
    if (!sessionId || !acceptanceKey) return null;
    try {{
      const response = await boundedControlFetch('/api/dashboard-chat/non-acceptance', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{session_id:sessionId, acceptance_key:acceptanceKey, reason:reason || 'acceptance_internal_failure'}}),
        cache:'no-store'
      }}, 5000);
      const payload = await response.json();
      const evidence = payload && payload.evidence ? payload.evidence : null;
      if (response.ok && payload.ok && evidence && evidence.resend_allowed && evidence.fresh_acceptance_identity_required) return evidence;
    }} catch (_error) {{}}
    return null;
  }}
  function setExplicitResendContext(candidate) {{
    if (!candidate || !candidate.resend_allowed || !candidate.source_acceptance_key || !candidate.source_evidence_token) {{
      explicitResendContext = null;
      return;
    }}
    explicitResendContext = {{
      session_id:String(candidate.session_id || sessionBox.value || ''),
      source_acceptance_key:String(candidate.source_acceptance_key || ''),
      source_evidence_token:String(candidate.source_evidence_token || ''),
      resend_acceptance_key:String(candidate.resend_acceptance_key || ''),
      claim_state:String(candidate.claim_state || 'unclaimed')
    }};
  }}
  function appendExplicitResendPresentation(reply, evidence) {{
    if (!reply || !evidence || !evidence.resend_allowed) return;
    const candidate = {{
      session_id:String(evidence.session_id || sessionBox.value || ''),
      source_acceptance_key:String(evidence.source_acceptance_key || evidence.acceptance_key || ''),
      source_evidence_token:String(evidence.source_evidence_token || evidence.evidence_token || ''),
      resend_acceptance_key:String(evidence.resend_acceptance_key || ''),
      claim_state:String(evidence.claim_state || 'unclaimed'),
      resend_allowed:true
    }};
    setExplicitResendContext(candidate);
    const article = reply.closest('.chat-turn');
    if (!article) return;
    let row = article.querySelector('.chat-explicit-resend-presentation');
    if (!row) {{
      row = document.createElement('div');
      row.className = 'chat-explicit-resend-presentation';
      row.dataset.nonAcceptanceProven = 'true';
      row.dataset.automaticResend = 'false';
      const note = document.createElement('small');
      note.textContent = candidate.resend_acceptance_key
        ? 'The earlier submission was not accepted. An interrupted explicit resend claim is preserved and will resume the same new acceptance identity.'
        : 'Persisted evidence proves the earlier submission was not accepted. Your draft is preserved. Sending it again remains explicit and will create one new acceptance identity.';
      row.appendChild(note);
      const review = document.createElement('button');
      review.type = 'button';
      review.className = 'chat-review-resend-draft';
      review.textContent = 'Review restored draft';
      row.appendChild(review);
      article.appendChild(row);
    }}
  }}
  function applyResendCandidate(candidate) {{
    setExplicitResendContext(candidate || null);
    if (!candidate || !candidate.resend_allowed) return;
    const cue = document.createElement('div');
    cue.className = 'chat-explicit-resend-presentation chat-restored-resend-cue';
    cue.dataset.nonAcceptanceProven = 'true';
    cue.dataset.automaticResend = 'false';
    const note = document.createElement('small');
    note.textContent = candidate.claim_pending
      ? 'A previously interrupted explicit resend is ready to resume with the same acceptance identity. Nothing was submitted automatically.'
      : 'A draft has persisted non-acceptance evidence. Review it and press Send explicitly to create one new acceptance identity.';
    cue.appendChild(note);
    const review = document.createElement('button');
    review.type = 'button';
    review.className = 'chat-review-resend-draft';
    review.textContent = 'Review restored draft';
    cue.appendChild(review);
    log.appendChild(cue);
  }}
  function clearOperationPoll(operationId) {{
    const timer = operationPollTimers.get(operationId);
    if (timer) window.clearTimeout(timer);
    operationPollTimers.delete(operationId);
  }}
  async function pollOperation(operationId, options) {{
    if (!operationId) return;
    clearOperationPoll(operationId);
    const pollOptions = Object.assign({{}}, options || {{}});
    const priorFailures = Math.max(0, Number(pollOptions.failureCount) || 0);
    const updateStatus = pollOptions.uiSequence == null || (
      Number(pollOptions.uiSequence) === foregroundTurnSequence
      && isCurrentSelection(String(pollOptions.sessionId || ''), Number(pollOptions.generation))
    );
    try {{
      const url = '/api/dashboard-chat/operation?operation_id=' + encodeURIComponent(operationId);
      const response = await boundedControlFetch(url, {{ cache:'no-store' }}, 5000);
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error('operation_status_failed');
      applyOperationStatus(payload, {{ updateStatus:updateStatus }});
      if (payload.operation && payload.operation.public_state === 'running') {{
        pollOptions.failureCount = 0;
        operationPollTimers.set(operationId, window.setTimeout(function() {{ pollOperation(operationId, pollOptions); }}, 900));
      }} else {{
        clearOperationPoll(operationId);
      }}
    }} catch (_error) {{
      const markerSessionId = selectedSessionId;
      const nextFailures = priorFailures + 1;
      if (nextFailures >= 18) {{
        clearOperationPoll(operationId);
        if (updateStatus && activeOperationId === operationId && isCurrentSelection(markerSessionId)) {{
          setStatus('attention', 'Operation reconciliation paused after repeated unavailable status checks. Reload or retry status later; no turn was replayed.');
        }}
        return;
      }}
      if (updateStatus && activeOperationId === operationId && isCurrentSelection(markerSessionId)) {{
        setStatus('disconnected', 'The operation status could not be checked yet. No retry or duplicate submission occurred.');
      }}
      pollOptions.failureCount = nextFailures;
      const delay = Math.min(15000, Math.round(900 * Math.pow(1.45, nextFailures)));
      operationPollTimers.set(operationId, window.setTimeout(function() {{ pollOperation(operationId, pollOptions); }}, delay));
    }}
  }}
  function setDraftStatus(state, text) {{
    if (!draftStatus) return;
    draftStatus.dataset.state = state;
    draftStatus.textContent = text;
  }}
  function draftKey(sessionId) {{
    return 'eidolon.chat.draft.v3.' + (sessionId || sessionBox.value || 'new-conversation');
  }}
  function parseDraftTime(value) {{
    const parsed = Date.parse(value || '');
    return Number.isFinite(parsed) ? parsed : 0;
  }}
  function draftEditorId() {{
    return String((tabIdentity && tabIdentity.tab_id) || 'browser-editor');
  }}
  function serverDraftRevision() {{
    return Math.max(0, Number(messageBox.dataset.serverDraftRevision || 0) || 0);
  }}
  function readLocalDraft(key) {{
    try {{
      const raw = window.localStorage.getItem(key);
      if (!raw) return null;
      const saved = JSON.parse(raw);
      if (!saved || typeof saved.text !== 'string') return null;
      return {{
        text: saved.text,
        updated_at: String(saved.updated_at || ''),
        base_revision: Math.max(0, Number(saved.base_revision || 0) || 0),
        content_digest: String(saved.content_digest || '')
      }};
    }} catch (_error) {{ return null; }}
  }}
  function writeLocalDraft(key, text, updatedAt, baseRevision, contentDigest) {{
    try {{
      if (text) window.localStorage.setItem(key, JSON.stringify({{
        text: text,
        updated_at: updatedAt,
        base_revision: Math.max(0, Number(baseRevision || 0) || 0),
        content_digest: String(contentDigest || '')
      }}));
      else window.localStorage.removeItem(key);
    }} catch (_error) {{}}
  }}
  function clearDraftConflictState() {{
    activeDraftConflict = null;
    if (draftConflict) draftConflict.hidden = true;
    if (draftConflictCurrent) draftConflictCurrent.disabled = true;
    if (draftConflictIncoming) draftConflictIncoming.disabled = true;
  }}
  function showDraftConflict(conflict) {{
    if (!conflict || !conflict.conflict_id) return;
    activeDraftConflict = conflict;
    if (draftConflict) draftConflict.hidden = false;
    if (draftConflictCurrent) draftConflictCurrent.disabled = false;
    if (draftConflictIncoming) draftConflictIncoming.disabled = false;
    if (draftConflictDetail) draftConflictDetail.textContent = 'Both versions are preserved at saved revision ' + String(conflict.current_revision || 0) + '. Choose explicitly; nothing was overwritten.';
    setDraftStatus('error', 'Draft conflict preserved');
    setStatus('attention', 'Another tab saved a different draft first. Both versions were preserved and no automatic choice was made.');
  }}
  async function resolveDraftConflict(choice) {{
    if (!activeDraftConflict || !sessionIdentityIsConsistent()) return false;
    if (!tabOwnsConversationControl() || !await confirmConversationControl()) {{
      setStatus('attention', 'Take conversation control before resolving the preserved draft conflict.');
      return false;
    }}
    const targetSessionId = sessionBox.value || '';
    const conflict = activeDraftConflict;
    if (draftConflictCurrent) draftConflictCurrent.disabled = true;
    if (draftConflictIncoming) draftConflictIncoming.disabled = true;
    try {{
      const mutationKey = newMutationKey('draft-conflict-resolve');
      const response = await fetch('/api/dashboard-chat/draft-conflict-resolve', {{
        method:'POST', headers:{{'Content-Type':'application/json'}}, cache:'no-store',
        body:JSON.stringify(Object.assign({{
          session_id:targetSessionId,
          conflict_id:String(conflict.conflict_id || ''),
          choice:String(choice || ''),
          expected_revision:Number(conflict.current_revision || 0),
          editor_id:draftEditorId()
        }}, coordinationMutationFields(mutationKey)))
      }});
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'draft_conflict_resolution_failed');
      if (payload.coordination) applyCoordinationState(payload.coordination);
      messageBox.value = String(payload.content || '');
      messageBox.dataset.serverDraftUpdatedAt = String(payload.updated_at || '');
      messageBox.dataset.serverDraftRevision = String(Number(payload.revision || 0));
      messageBox.dataset.serverDraftDigest = String(payload.content_digest || '');
      writeLocalDraft(draftKey(targetSessionId), messageBox.value || '', String(payload.updated_at || new Date().toISOString()), Number(payload.revision || 0), String(payload.content_digest || ''));
      clearDraftConflictState();
      setDraftStatus('saved', payload.resolution === 'incoming' ? 'This tabâ€™s draft saved' : 'Saved draft kept');
      setStatus('ready', 'The draft conflict was resolved explicitly. No provider request was sent.');
      announceCoordination('draft_changed', {{ session_id:targetSessionId }});
      return true;
    }} catch (_error) {{
      if (draftConflictCurrent) draftConflictCurrent.disabled = false;
      if (draftConflictIncoming) draftConflictIncoming.disabled = false;
      setStatus('attention', 'The draft conflict could not be resolved because the saved draft changed again. Both versions remain preserved.');
      return false;
    }}
  }}
  function presentationKey(sessionId) {{
    return 'eidolon.chat.presentation.v2.' + (sessionId || sessionBox.value || 'new-conversation');
  }}
  function readLocalPresentation(sessionId) {{
    try {{
      const raw = window.localStorage.getItem(presentationKey(sessionId));
      const value = raw ? JSON.parse(raw) : null;
      if (!value || typeof value.follow_latest !== 'boolean') return null;
      return {{
        follow_latest: !!value.follow_latest,
        scroll_from_bottom_px: Math.max(0, Math.min(1000000, Number(value.scroll_from_bottom_px) || 0)),
        view_anchor_turn_id: String(value.view_anchor_turn_id || ''),
        view_anchor_offset_px: Math.max(-1000000, Math.min(1000000, Number(value.view_anchor_offset_px) || 0)),
        last_seen_turn_id: String(value.last_seen_turn_id || ''),
        last_seen_turn_count: Math.max(0, Number(value.last_seen_turn_count) || 0),
        unread_turn_count: Math.max(0, Number(value.unread_turn_count) || 0),
        turn_count: Math.max(0, Number(value.turn_count) || 0),
        composer_intentionally_empty: !!value.composer_intentionally_empty,
        updated_at: String(value.updated_at || '')
      }};
    }} catch (_error) {{ return null; }}
  }}
  function writeLocalPresentation(sessionId, value) {{
    if (!sessionId || !value) return;
    const bounded = {{
      follow_latest: !!value.follow_latest,
      scroll_from_bottom_px: Math.max(0, Math.min(1000000, Number(value.scroll_from_bottom_px) || 0)),
      view_anchor_turn_id: String(value.view_anchor_turn_id || '').slice(0,160),
      view_anchor_offset_px: Math.max(-1000000, Math.min(1000000, Number(value.view_anchor_offset_px) || 0)),
      last_seen_turn_id: String(value.last_seen_turn_id || '').slice(0,160),
      last_seen_turn_count: Math.max(0, Number(value.last_seen_turn_count) || 0),
      unread_turn_count: Math.max(0, Number(value.unread_turn_count) || 0),
      turn_count: Math.max(0, Number(value.turn_count) || 0),
      composer_intentionally_empty: !!value.composer_intentionally_empty,
      updated_at: String(value.updated_at || new Date().toISOString())
    }};
    try {{ window.localStorage.setItem(presentationKey(sessionId), JSON.stringify(bounded)); }} catch (_error) {{}}
  }}
  function orderedTurnNodes() {{
    const result = [];
    const seen = new Set();
    log.querySelectorAll('[data-session-turn-id]').forEach(function(node) {{
      const turnId = String(node.dataset.sessionTurnId || '');
      if (!turnId || seen.has(turnId)) return;
      seen.add(turnId);
      result.push(node);
    }});
    return result;
  }}
  function readingBoundary() {{
    const nodes = orderedTurnNodes();
    const logRect = log.getBoundingClientRect();
    let anchorTurnId = '';
    let anchorOffset = 0;
    let lastSeenTurnId = '';
    let lastSeenTurnCount = 0;
    nodes.forEach(function(node, index) {{
      const rect = node.getBoundingClientRect();
      if (!anchorTurnId && rect.bottom > logRect.top + 1) {{
        anchorTurnId = String(node.dataset.sessionTurnId || '');
        anchorOffset = Math.round(rect.top - logRect.top);
      }}
      if (rect.top < logRect.bottom - 1) {{
        lastSeenTurnId = String(node.dataset.sessionTurnId || '');
        lastSeenTurnCount = index + 1;
      }}
    }});
    return {{
      view_anchor_turn_id: anchorTurnId,
      view_anchor_offset_px: anchorOffset,
      last_seen_turn_id: lastSeenTurnId,
      last_seen_turn_count: lastSeenTurnCount,
      turn_count: nodes.length
    }};
  }}
  function findTurnAnchor(turnId) {{
    if (!turnId) return null;
    const nodes = log.querySelectorAll('[data-session-turn-id]');
    for (const node of nodes) if (String(node.dataset.sessionTurnId || '') === String(turnId)) return node;
    return null;
  }}
  function capturePresentation(sessionId) {{
    const follow = isFollowingConversation();
    const offset = Math.max(0, Math.round(log.scrollHeight - log.scrollTop - log.clientHeight));
    const boundary = readingBoundary();
    if (follow) {{
      boundary.last_seen_turn_count = boundary.turn_count;
      boundary.last_seen_turn_id = boundary.turn_count ? String(orderedTurnNodes().slice(-1)[0].dataset.sessionTurnId || '') : '';
      boundary.view_anchor_turn_id = '';
      boundary.view_anchor_offset_px = 0;
    }}
    const priorUnread = Math.max(0, Number((currentPresentationState && currentPresentationState.unread_turn_count) || 0));
    return {{
      session_id: sessionId || sessionBox.value || '',
      follow_latest: follow,
      scroll_from_bottom_px: follow ? 0 : Math.min(1000000, offset),
      view_anchor_turn_id: boundary.view_anchor_turn_id,
      view_anchor_offset_px: boundary.view_anchor_offset_px,
      last_seen_turn_id: boundary.last_seen_turn_id,
      last_seen_turn_count: boundary.last_seen_turn_count,
      unread_turn_count: follow ? 0 : priorUnread,
      turn_count: boundary.turn_count,
      composer_intentionally_empty: !(messageBox.value || ''),
      updated_at: new Date().toISOString()
    }};
  }}
  async function persistPresentation(options) {{
    if (!sessionIdentityIsConsistent() || !tabOwnsConversationControl()) return null;
    const targetSessionId = options && options.sessionId ? options.sessionId : (sessionBox.value || '');
    if (!targetSessionId) return null;
    const sequence = ++presentationSaveSequence;
    const value = options && options.value ? options.value : capturePresentation(targetSessionId);
    writeLocalPresentation(targetSessionId, value);
    try {{
      const response = await fetch('/api/dashboard-chat/presentation', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(Object.assign({{
          session_id: targetSessionId,
          follow_latest: !!value.follow_latest,
          scroll_from_bottom_px: Number(value.scroll_from_bottom_px) || 0,
          view_anchor_turn_id: String(value.view_anchor_turn_id || ''),
          view_anchor_offset_px: Number(value.view_anchor_offset_px) || 0,
          last_seen_turn_id: String(value.last_seen_turn_id || ''),
          last_seen_turn_count: Number(value.last_seen_turn_count) || 0,
          composer_intentionally_empty: !!value.composer_intentionally_empty,
          client_updated_at: String(value.updated_at || '')
        }}, coordinationMutationFields(newMutationKey('presentation')))),
        cache: 'no-store',
        keepalive: !!(options && options.keepalive)
      }});
      const payload = await response.json();
      if (!response.ok || !payload.ok) {{
        if (payload.coordination) applyCoordinationState(payload.coordination, {{ reconcile:true }});
        throw new Error(payload.error || 'presentation_save_failed');
      }}
      if (payload.coordination) applyCoordinationState(payload.coordination);
      if (sequence === presentationSaveSequence && isCurrentSelection(targetSessionId)) {{
        currentPresentationState = Object.assign({{}}, value, payload, {{ updated_at:String(payload.updated_at || value.updated_at || '') }});
        writeLocalPresentation(targetSessionId, currentPresentationState);
        updateJumpLatestButton();
      }}
      return payload;
    }} catch (_error) {{
      return null;
    }}
  }}
  function schedulePresentationSave() {{
    if (!sessionIdentityIsConsistent()) return;
    const targetSessionId = sessionBox.value || '';
    if (!targetSessionId) return;
    const value = capturePresentation(targetSessionId);
    currentPresentationState = Object.assign({{}}, currentPresentationState || {{}}, value);
    writeLocalPresentation(targetSessionId, value);
    if (presentationSaveTimer) window.clearTimeout(presentationSaveTimer);
    presentationSaveTimer = window.setTimeout(function() {{ persistPresentation({{ sessionId: targetSessionId, value: value }}); }}, 350);
  }}
  function restorePresentation(serverPresentation) {{
    const targetSessionId = sessionBox.value || '';
    const server = serverPresentation || {{ follow_latest:true, scroll_from_bottom_px:0, view_anchor_turn_id:'', view_anchor_offset_px:0, last_seen_turn_id:'', last_seen_turn_count:0, unread_turn_count:0, turn_count:0, composer_intentionally_empty:true, updated_at:'' }};
    const local = readLocalPresentation(targetSessionId);
    const localIsNewer = !!(local && parseDraftTime(local.updated_at) > parseDraftTime(server.updated_at));
    const chosen = localIsNewer ? local : server;
    currentPresentationState = Object.assign({{}}, chosen);
    writeLocalPresentation(targetSessionId, chosen);
    window.requestAnimationFrame(function() {{
      if (!isCurrentSelection(targetSessionId)) return;
      if (chosen.follow_latest !== false) scrollConversation(true);
      else {{
        const anchor = findTurnAnchor(chosen.view_anchor_turn_id);
        if (anchor) {{
          const before = anchor.getBoundingClientRect().top - log.getBoundingClientRect().top;
          log.scrollTop += Math.round(before - (Number(chosen.view_anchor_offset_px) || 0));
        }} else {{
          log.scrollTop = Math.max(0, log.scrollHeight - log.clientHeight - (Number(chosen.scroll_from_bottom_px) || 0));
        }}
      }}
      updateJumpLatestButton();
    }});
    return localIsNewer ? {{ sessionId: targetSessionId, value: local }} : null;
  }}
  async function persistDraft(options) {{
    if (!sessionIdentityIsConsistent() || !tabOwnsConversationControl()) return null;
    const targetSessionId = options && options.sessionId ? options.sessionId : (sessionBox.value || '');
    if (!targetSessionId) return null;
    const sequence = ++draftSaveSequence;
    const key = options && options.key ? options.key : draftKey(targetSessionId);
    const text = options && Object.prototype.hasOwnProperty.call(options, 'text') ? String(options.text || '') : (messageBox.value || '');
    const local = readLocalDraft(key);
    const clientUpdatedAt = options && options.clientUpdatedAt ? String(options.clientUpdatedAt) : (local && local.updated_at ? local.updated_at : new Date().toISOString());
    const baseRevision = options && Object.prototype.hasOwnProperty.call(options, 'baseRevision') ? Number(options.baseRevision || 0) : (local ? Number(local.base_revision || 0) : serverDraftRevision());
    if (isCurrentSelection(targetSessionId)) setDraftStatus('saving', 'Saving draftâ€¦');
    try {{
      const response = await fetch('/api/dashboard-chat/draft', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(Object.assign({{
          session_id: targetSessionId, content: text, client_updated_at: clientUpdatedAt,
          base_revision: Math.max(0, baseRevision || 0), editor_id: draftEditorId()
        }}, coordinationMutationFields(newMutationKey('draft')))),
        cache: 'no-store',
        keepalive: !!(options && options.keepalive)
      }});
      const payload = await response.json();
      if (!response.ok || !payload.ok) {{
        if (payload.coordination) applyCoordinationState(payload.coordination, {{ reconcile:true }});
        throw new Error(payload.error || 'draft_save_failed');
      }}
      if (payload.coordination) applyCoordinationState(payload.coordination);
      announceCoordination('draft_changed', {{ session_id:targetSessionId }});
      if (sequence !== draftSaveSequence || !isCurrentSelection(targetSessionId)) return payload;
      messageBox.dataset.serverDraftUpdatedAt = String(payload.updated_at || clientUpdatedAt);
      messageBox.dataset.serverDraftRevision = String(Number(payload.revision || baseRevision || 0));
      messageBox.dataset.serverDraftDigest = String(payload.content_digest || '');
      if (payload.draft_conflict && payload.conflict) {{
        showDraftConflict(payload.conflict);
        writeLocalDraft(key, text, clientUpdatedAt, baseRevision, local && local.content_digest ? local.content_digest : '');
        return payload;
      }}
      clearDraftConflictState();
      if (payload.stale_update_ignored) {{
        if (!payload.has_draft) writeLocalDraft(key, '', String(payload.updated_at || clientUpdatedAt), Number(payload.revision || 0), String(payload.content_digest || ''));
        setDraftStatus('saved', payload.has_draft ? 'A newer identical draft is already saved' : 'Message accepted; stale draft discarded');
        return payload;
      }}
      writeLocalDraft(key, text, String(payload.updated_at || clientUpdatedAt), Number(payload.revision || 0), String(payload.content_digest || ''));
      setDraftStatus('saved', text ? 'Draft saved' : 'Draft cleared');
      return payload;
    }} catch (_error) {{
      if (sequence === draftSaveSequence && isCurrentSelection(targetSessionId)) setDraftStatus('error', 'Saved in browser; Eidolon will sync when available');
      return null;
    }}
  }}
  function scheduleDraftSave() {{
    if (!sessionIdentityIsConsistent()) return;
    const targetSessionId = sessionBox.value || '';
    currentDraftKey = draftKey(targetSessionId);
    const clientUpdatedAt = new Date().toISOString();
    const baseRevision = serverDraftRevision();
    writeLocalDraft(currentDraftKey, messageBox.value || '', clientUpdatedAt, baseRevision, String(messageBox.dataset.serverDraftDigest || ''));
    setDraftStatus('saving', 'Saving draftâ€¦');
    if (draftSaveTimer) window.clearTimeout(draftSaveTimer);
    draftSaveTimer = window.setTimeout(function() {{ persistDraft({{ sessionId: targetSessionId, key: currentDraftKey, baseRevision:baseRevision }}); }}, 250);
    schedulePresentationSave();
  }}
  function restoreDraft(serverDraft) {{
    const targetSessionId = sessionBox.value || '';
    currentDraftKey = draftKey(targetSessionId);
    const draft = serverDraft || {{ content:messageBox.value || '', updated_at:messageBox.dataset.serverDraftUpdatedAt || '', cleared_at:messageBox.dataset.serverDraftClearedAt || '', revision:serverDraftRevision(), content_digest:messageBox.dataset.serverDraftDigest || '' }};
    const serverText = String(draft.content || '');
    const serverUpdatedAt = String(draft.updated_at || '');
    const serverClearedAt = String(draft.cleared_at || '');
    const serverRevision = Math.max(0, Number(draft.revision || 0) || 0);
    const serverDigest = String(draft.content_digest || '');
    messageBox.dataset.serverDraftUpdatedAt = serverUpdatedAt;
    messageBox.dataset.serverDraftClearedAt = serverClearedAt;
    messageBox.dataset.serverDraftRevision = String(serverRevision);
    messageBox.dataset.serverDraftDigest = serverDigest;
    const serverStamp = Math.max(parseDraftTime(serverUpdatedAt), parseDraftTime(serverClearedAt));
    const local = readLocalDraft(currentDraftKey);
    if (local && parseDraftTime(local.updated_at) > serverStamp) {{
      messageBox.value = local.text;
      setDraftStatus('saving', local.base_revision < serverRevision && local.text !== serverText ? 'Restored divergent browser draft; preserving bothâ€¦' : 'Restored browser draft; syncingâ€¦');
      return {{ sessionId: targetSessionId, key: currentDraftKey, text: local.text, clientUpdatedAt: local.updated_at, baseRevision:local.base_revision }};
    }}
    clearDraftConflictState();
    messageBox.value = serverText;
    writeLocalDraft(currentDraftKey, serverText, serverUpdatedAt || serverClearedAt || new Date().toISOString(), serverRevision, serverDigest);
    setDraftStatus('saved', serverText ? 'Draft restored' : 'Drafts save per conversation');
    return null;
  }}
  async function restoreUnacceptedDraft(unacceptedSessionId, previousKey, submittedMessage, submittedGeneration) {{
    const key = previousKey || draftKey(unacceptedSessionId);
    const local = readLocalDraft(key);
    const currentText = isCurrentSelection(unacceptedSessionId, submittedGeneration) ? String(messageBox.value || '') : '';
    const newerText = currentText && currentText !== submittedMessage
      ? currentText
      : (local && local.text && local.text !== submittedMessage ? String(local.text) : '');
    if (newerText) {{
      const newerStamp = String((local && local.updated_at) || new Date().toISOString());
      writeLocalDraft(key, newerText, newerStamp);
      await persistDraft({{ sessionId:unacceptedSessionId, key:key, text:newerText, clientUpdatedAt:newerStamp }});
      if (isCurrentSelection(unacceptedSessionId, submittedGeneration)) {{
        messageBox.value = newerText;
        setDraftStatus('saved', 'Newer draft preserved');
        setStatus('attention', 'The turn was not accepted. Your newer draft was preserved instead of being overwritten.');
      }}
      return false;
    }}
    const restoreStamp = new Date().toISOString();
    writeLocalDraft(key, submittedMessage, restoreStamp);
    await persistDraft({{ sessionId:unacceptedSessionId, key:key, text:submittedMessage, clientUpdatedAt:restoreStamp }});
    if (isCurrentSelection(unacceptedSessionId, submittedGeneration)) {{
      messageBox.value = submittedMessage;
      setDraftStatus('saved', 'Draft restored');
    }}
    return true;
  }}
  function clearAcceptedDraft(acceptedSessionId, previousKey, acceptedGeneration) {{
    if (draftSaveTimer) window.clearTimeout(draftSaveTimer);
    draftSaveTimer = null;
    draftSaveSequence += 1;
    try {{ window.localStorage.removeItem(previousKey || draftKey(acceptedSessionId)); }} catch (_error) {{}}
    if (!isCurrentSelection(acceptedSessionId, acceptedGeneration)) return;
    messageBox.dataset.serverDraftRevision = String(serverDraftRevision() + 1);
    messageBox.dataset.serverDraftDigest = '';
    const newerText = messageBox.value || '';
    currentDraftKey = draftKey(acceptedSessionId);
    if (newerText) {{
      const newerStamp = new Date().toISOString();
      writeLocalDraft(currentDraftKey, newerText, newerStamp, serverDraftRevision(), '');
      setDraftStatus('saving', 'Message accepted; newer draft preserved');
      draftSaveTimer = window.setTimeout(function() {{ persistDraft({{ sessionId: acceptedSessionId, key: currentDraftKey, text: newerText, clientUpdatedAt: newerStamp, baseRevision:serverDraftRevision() }}); }}, 0);
    }} else {{
      setDraftStatus('saved', 'Message accepted; draft cleared');
    }}
  }}
  function applyProviderRecoveryCue(cue) {{
    if (!providerRecoveryCue) return;
    if (!cue || !cue.visible) {{ providerRecoveryCue.hidden = true; return; }}
    providerRecoveryCue.hidden = false;
    providerRecoveryCue.dataset.state = String(cue.state || 'unknown');
    if (providerRecoveryLabel) providerRecoveryLabel.textContent = String(cue.label || 'Provider readiness');
    if (providerRecoveryDetail) providerRecoveryDetail.textContent = String(cue.detail || '');
    if (providerRecoveryTime) {{
      const resumeText = cue.can_resume_composition ? 'Composition may resume explicitly.' : 'Configured-provider recovery is not yet proven.';
      providerRecoveryTime.textContent = 'Last persisted check: ' + String(cue.checked_at || 'Not checked') + ' Â· ' + resumeText + ' No accepted request is replayed.';
    }}
  }}
  function applyRecoveryContract(contract) {{
    if (!recoveryContractCue) return;
    const state = String((contract && contract.state) || 'ready');
    recoveryContractCue.dataset.state = state;
    recoveryContractCue.hidden = state === 'ready';
    if (recoveryContractLabel) recoveryContractLabel.textContent = String((contract && contract.label) || 'Conversation recovery');
    if (recoveryContractDetail) recoveryContractDetail.textContent = String((contract && contract.detail) || '');
  }}
  function applyOfflineSessionDurability(state) {{
    if (!offlineSessionCue || !state) return;
    const capabilities = state.capabilities || {{}};
    offlineSessionCue.dataset.sessionAvailable = state.session_available ? 'true' : 'false';
    offlineSessionCue.dataset.providerDependency = String(state.provider_dependency || 'none_for_local_surfaces');
    if (offlineSessionLabel) offlineSessionLabel.textContent = state.session_available ? 'Local conversation continuity ready' : 'Local conversation continuity available';
    if (offlineSessionDetail) {{
      const unread = Math.max(0, Number(state.unread_turn_count || 0));
      offlineSessionDetail.textContent = 'History, drafts, search, archive, and reading position remain local without generation.' + (unread ? ' ' + String(unread) + ' turn' + (unread === 1 ? '' : 's') + ' remain unread.' : '') + (capabilities.provider_generation === false ? ' No provider response is fabricated.' : '');
    }}
    try {{
      window.localStorage.setItem('eidolon.chat.offline-continuity.v1', JSON.stringify({{
        session_id:String(state.session_id || ''),
        draft_revision:Math.max(0, Number(state.draft_revision || 0)),
        unread_turn_count:Math.max(0, Number(state.unread_turn_count || 0)),
        saved_at:new Date().toISOString(),
        content_free:true
      }}));
    }} catch (_error) {{}}
  }}
  function applySessionSnapshot(snapshot, generation, catalog) {{
    if (!snapshot || generation !== selectionRequestToken) return false;
    const session = snapshot.session || {{}};
    const targetSessionId = String(session.id || '');
    if (!targetSessionId) return false;
    markSessionIdentityUnresolved();
    bindResolvedSessionIdentity(targetSessionId);
    if (Array.isArray(catalog)) rebuildSessionCatalog(catalog);
    bindResolvedSessionIdentity(targetSessionId);
    if (sessionSelector) sessionSelector.value = targetSessionId;
    if (sessionTitle) sessionTitle.textContent = session.title || 'New conversation';
    if (sessionTurnCount) sessionTurnCount.textContent = String(session.turn_count || 0);
    sessionTitles[targetSessionId] = session.title || 'New conversation';
    log.innerHTML = String(snapshot.transcript_html || '');
    const historyWindow = snapshot.history_window || {{}};
    if (loadEarlierButton) {{
      loadEarlierButton.hidden = !historyWindow.has_older;
      loadEarlierButton.dataset.beforeTurnId = String(historyWindow.oldest_turn_id || '');
    }}
    if (historyWindowStatus) historyWindowStatus.textContent = 'Showing ' + String(historyWindow.shown || 0) + ' of ' + String(historyWindow.total_turns || session.turn_count || 0) + ' turns.';
    applyResendCandidate(snapshot.resend_candidate || null);
    draftClearedOperationId = '';
    const pendingDraftSync = restoreDraft(snapshot.draft || {{}});
    const pendingPresentationSync = restorePresentation(snapshot.presentation || {{}});
    const experience = snapshot.experience || {{}};
    applyProviderRecoveryCue(snapshot.provider_recovery || null);
    applyRecoveryContract(snapshot.recovery_contract || null);
    applyOfflineSessionDurability(snapshot.offline_session || null);
    setStatus(experience.state || 'ready', experience.detail || 'Your conversation is saved and ready.');
    if (providerDetail) providerDetail.textContent = experience.provider_label || 'Local provider';
    if (modelDetail) modelDetail.textContent = experience.model_label || 'Not selected';
    if (endpointDetail) endpointDetail.textContent = experience.endpoint_label || 'Not available';
    activeOperationId = '';
    const operationStatus = snapshot.operation_status || {{}};
    if (operationStatus.operation) {{
      updateSessionCue(operationStatus);
      const operationState = String(operationStatus.operation.public_state || 'uncertain');
      if (operationState === 'running') activeOperationId = String(operationStatus.operation.operation_id || '');
      if (operationState === 'running' || operationState === 'uncertain' || operationStatus.session_cue) applyOperationStatus(operationStatus);
      if (operationState === 'running') pollOperation(operationStatus.operation.operation_id);
    }}
    bindResolvedSessionIdentity(targetSessionId);
    sessionIdentityResolved = true;
    setSessionMutationControlsDisabled(false);
    if (pendingDraftSync) persistDraft(pendingDraftSync);
    if (pendingPresentationSync) persistPresentation(pendingPresentationSync);
    focusComposer();
    return true;
  }}
  async function refreshSessionCue(sessionId) {{
    if (!sessionId) return;
    try {{
      const response = await boundedControlFetch('/api/dashboard-chat/operation?session_id=' + encodeURIComponent(sessionId), {{ cache:'no-store' }}, 5000);
      const payload = await response.json();
      if (response.ok && payload.ok && payload.operation) updateSessionCue(payload);
      else if (response.ok && payload.ok) removeSessionCue(sessionId);
    }} catch (_error) {{}}
  }}
  async function switchConversationSession(targetSessionId, options) {{
    if (!sessionIdentityIsConsistent() || !tabOwnsConversationControl()) return false;
    if (!await confirmConversationControl()) {{
      setStatus('attention', 'Another tab now controls conversation changes. Nothing was switched.');
      return false;
    }}
    const target = String(targetSessionId || '');
    const source = String(sessionBox.value || '');
    const switchControl = options && options.control ? options.control : null;
    const switchLockKey = 'switch:' + target;
    if (!target || !source || !beginCompanionAction(switchLockKey, switchControl)) return false;
    if (target === source) {{
      try {{
        if (options && (options.acknowledgementToken || options.acknowledgementOperationId)) await acknowledgeCurrentSessionCue(target, options.acknowledgementOperationId || '', null, options.acknowledgementToken || '');
        focusComposer({{ trigger:switchControl }});
        return true;
      }} finally {{
        endCompanionAction(switchLockKey, switchControl);
      }}
    }}
    const generation = nextSelectionGeneration();
    const pendingSource = pendingSubmissions.get(source);
    const sourceDraftText = (messageBox.value || '') || (pendingSource && !pendingSource.accepted ? String(pendingSource.message || '') : '');
    const sourceDraftStamp = new Date().toISOString();
    const sourceDraftKey = draftKey(source);
    const sourceDraftRevision = serverDraftRevision();
    writeLocalDraft(sourceDraftKey, sourceDraftText, sourceDraftStamp, sourceDraftRevision, String(messageBox.dataset.serverDraftDigest || ''));
    const sourcePresentation = capturePresentation(source);
    writeLocalPresentation(source, sourcePresentation);
    if (draftSaveTimer) window.clearTimeout(draftSaveTimer);
    if (presentationSaveTimer) window.clearTimeout(presentationSaveTimer);
    draftSaveTimer = null;
    presentationSaveTimer = null;
    draftSaveSequence += 1;
    presentationSaveSequence += 1;
    setStatus('switching');
    const coordinationMutationKey = newMutationKey('switch');
    try {{
      const response = await fetch('/api/dashboard-chat/session-switch', {{
        method: 'POST',
        headers: {{ 'Content-Type':'application/json' }},
        body: JSON.stringify(Object.assign({{
          source_session_id: source,
          target_session_id: target,
          navigation_client_id: navigationState.client_id,
          selection_generation: generation,
          source_draft_content: sourceDraftText,
          source_draft_updated_at: sourceDraftStamp,
          source_draft_base_revision: sourceDraftRevision,
          source_draft_editor_id: draftEditorId(),
          source_follow_latest: !!sourcePresentation.follow_latest,
          source_scroll_from_bottom_px: Number(sourcePresentation.scroll_from_bottom_px) || 0,
          source_composer_intentionally_empty: !!sourcePresentation.composer_intentionally_empty,
          source_presentation_updated_at: sourcePresentation.updated_at,
          source_view_anchor_turn_id: String(sourcePresentation.view_anchor_turn_id || ''),
          source_view_anchor_offset_px: Number(sourcePresentation.view_anchor_offset_px) || 0,
          source_last_seen_turn_id: String(sourcePresentation.last_seen_turn_id || ''),
          source_last_seen_turn_count: Number(sourcePresentation.last_seen_turn_count) || 0,
          source_view_anchor_turn_id: String(sourcePresentation.view_anchor_turn_id || ''),
          source_view_anchor_offset_px: Number(sourcePresentation.view_anchor_offset_px) || 0,
          source_last_seen_turn_id: String(sourcePresentation.last_seen_turn_id || ''),
          source_last_seen_turn_count: Number(sourcePresentation.last_seen_turn_count) || 0
        }}, coordinationMutationFields(coordinationMutationKey))),
        cache: 'no-store'
      }});
      const payload = await response.json();
      if (!response.ok || !payload.ok) {{
        if (payload.coordination) applyCoordinationState(payload.coordination, {{ reconcile:true }});
        throw new Error(payload.error || 'session_switch_failed');
      }}
      if (payload.coordination) applyCoordinationState(payload.coordination);
      announceCoordination('state_changed', {{ session_id:String(payload.selected_session_id || target) }});
      if (generation !== selectionRequestToken) return false;
      if (payload.stale_selection_ignored || !payload.snapshot) return false;
      if (!applySessionSnapshot(payload.snapshot, generation, Array.isArray(payload.catalog) ? payload.catalog : null)) return false;
      await refreshSessionCue(source);
      const operationStatus = payload.snapshot.operation_status || {{}};
      if (operationStatus.operation) updateSessionCue(operationStatus);
      if (!(options && options.historyRestore)) writeChatHistoryState('push');
      if (options && (options.acknowledgementToken || options.acknowledgementOperationId)) {{
        await acknowledgeCurrentSessionCue(target, options.acknowledgementOperationId || '', null, options.acknowledgementToken || '');
      }}
      return true;
    }} catch (_error) {{
      if (generation === selectionRequestToken && isCurrentSelection(source)) {{
        if (sessionSelector) sessionSelector.value = source;
        setStatus('attention', 'The conversation could not be switched safely. Your source draft remains saved in the browser.');
      }}
      return false;
    }} finally {{
      endCompanionAction(switchLockKey, switchControl);
    }}
  }}
  function newLifecycleRequestKey() {{
    if (window.crypto && typeof window.crypto.randomUUID === 'function') return window.crypto.randomUUID();
    return 'lifecycle-' + Date.now() + '-' + Math.random().toString(16).slice(2);
  }}
  let catalogPageState = initialCatalogPage && typeof initialCatalogPage === 'object' ? initialCatalogPage : {{ items:[], offset:0, limit:30, total:0 }};
  function rebuildSessionCatalog(catalog) {{
    if (!Array.isArray(catalog)) return;
    const activeRows = catalog.filter(function(item) {{ return item && item.status !== 'archived'; }});
    if (sessionSelector) {{
      const selected = String(sessionBox.value || '');
      sessionSelector.replaceChildren();
      activeRows.forEach(function(item) {{
        const option = document.createElement('option');
        option.value = String(item.id || '');
        option.textContent = String(item.display_title || item.title || 'New conversation') + ' Â· ' + String(item.turn_count || 0) + ' turns';
        option.selected = option.value === selected;
        sessionSelector.appendChild(option);
        sessionTitles[option.value] = String(item.title || 'New conversation');
      }});
      if (selected && !activeRows.some(function(item) {{ return String(item.id || '') === selected; }})) {{
        const option = document.createElement('option');
        option.value = selected;
        option.textContent = String(sessionTitles[selected] || 'Current conversation');
        option.selected = true;
        sessionSelector.appendChild(option);
      }}
      sessionSelector.value = selected;
      sessionSelector.dataset.activeSessionId = selected;
    }}
    setSessionMutationControlsDisabled(!sessionIdentityResolved);
  }}
  function lifecycleButton(label, action, sessionId) {{
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.dataset.lifecycleAction = action;
    button.dataset.sessionId = sessionId;
    return button;
  }}
  function renderOrganizerCatalogPage(page) {{
    if (!page || !Array.isArray(page.items) || !sessionList) return;
    if (catalogPageState && catalogPageState.catalog_revision && page.catalog_revision && catalogPageState.catalog_revision !== page.catalog_revision) page.catalog_changed = true;
    catalogPageState = page;
    sessionList.replaceChildren();
    if (!page.items.length) {{
      const empty = document.createElement('li');
      empty.textContent = page.query ? 'No matching conversations.' : 'No conversations.';
      sessionList.appendChild(empty);
    }} else {{
      let previousGroup = '';
      page.items.forEach(function(item) {{
        if (!item || !item.id) return;
        const group = String(item.group_label || 'Older conversations');
        if (group !== previousGroup) {{
          const groupRow = document.createElement('li');
          groupRow.className = 'conversation-session-group';
          groupRow.dataset.sessionGroup = group;
          groupRow.textContent = group;
          sessionList.appendChild(groupRow);
          previousGroup = group;
        }}
        const sessionId = String(item.id);
        const archived = item.status === 'archived';
        const row = document.createElement('li');
        row.className = 'conversation-session-row';
        row.dataset.sessionId = sessionId;
        const heading = document.createElement('div');
        const strong = document.createElement('b');
        strong.textContent = String(item.display_title || item.title || 'New conversation');
        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = archived ? 'archived' : 'active';
        const turns = document.createElement('small');
        turns.textContent = String(item.turn_count || 0) + ' turns';
        heading.append(strong, document.createTextNode(' '), badge, document.createTextNode(' '), turns);
        const snippet = document.createElement('small');
        snippet.className = 'conversation-session-snippet';
        snippet.textContent = String(item.match_snippet || item.last_turn_at || item.created_at || '');
        const controls = document.createElement('div');
        controls.className = 'inline';
        if (archived) {{
          controls.append(lifecycleButton('Restore', 'restore', sessionId), lifecycleButton('Restore and open', 'restore_open', sessionId));
        }} else {{
          controls.append(lifecycleButton('Archive', 'archive', sessionId));
        }}
        const renameInput = document.createElement('input');
        renameInput.value = String(item.title || '');
        renameInput.maxLength = 72;
        renameInput.setAttribute('aria-label', 'Conversation title');
        renameInput.dataset.lifecycleRenameInput = sessionId;
        controls.append(renameInput, lifecycleButton('Rename', 'rename', sessionId));
        row.append(heading, snippet, controls);
        sessionList.appendChild(row);
      }});
    }}
    const shown = Number(page.shown) || 0;
    const offset = Number(page.offset) || 0;
    const total = Number(page.total) || 0;
    if (catalogSummary) catalogSummary.textContent = (shown ? String(offset + 1) + '-' + String(offset + shown) : '0-0') + ' of ' + String(total);
    if (catalogPrevious) {{
      catalogPrevious.disabled = !page.has_previous;
      catalogPrevious.dataset.offset = String(Number(page.previous_offset) || 0);
    }}
    if (catalogNext) {{
      catalogNext.disabled = !page.has_next;
      catalogNext.dataset.offset = String(Number(page.next_offset) || offset);
    }}
    setSessionMutationControlsDisabled(!sessionIdentityResolved);
    persistUsabilityState();
    writeChatHistoryState('replace');
  }}
  async function refreshConversationOrganizer(offset) {{
    if (!sessionList) return false;
    const query = catalogQuery ? String(catalogQuery.value || '').trim().slice(0, 160) : '';
    const archived = !!(catalogArchived && catalogArchived.checked);
    const requestedOffset = Math.max(0, Number(offset == null ? catalogPageState.offset : offset) || 0);
    const params = new URLSearchParams({{ q:query, archived:archived ? 'true' : 'false', offset:String(requestedOffset), limit:String(Number(catalogPageState.limit) || 30) }});
    const sequence = ++catalogRefreshSequence;
    if (catalogRefreshController) catalogRefreshController.abort();
    const controller = new AbortController();
    catalogRefreshController = controller;
    sessionList.setAttribute('aria-busy', 'true');
    if (catalogSearchForm) catalogSearchForm.querySelectorAll('button,input').forEach(function(control) {{ control.disabled = true; }});
    try {{
      const response = await fetch('/api/dashboard-chat/session-catalog?' + params.toString(), {{ method:'GET', cache:'no-store', signal:controller.signal }});
      const payload = await response.json();
      if (sequence !== catalogRefreshSequence) return false;
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'catalog_search_failed');
      renderOrganizerCatalogPage(payload);
      if (payload.catalog_changed) setStatus('ready', 'Conversation results were refreshed from the latest archive state.');
      return true;
    }} catch (error) {{
      if (error && error.name === 'AbortError') return false;
      if (sequence === catalogRefreshSequence) setStatus('attention', 'Conversation search could not be refreshed. Existing results were preserved and no conversation state was changed.');
      return false;
    }} finally {{
      if (sequence === catalogRefreshSequence) {{
        sessionList.removeAttribute('aria-busy');
        if (catalogSearchForm) catalogSearchForm.querySelectorAll('button,input').forEach(function(control) {{ control.disabled = false; }});
        if (catalogRefreshController === controller) catalogRefreshController = null;
        persistUsabilityState();
      }}
    }}
  }}
  async function performConversationLifecycle(action, targetSessionId, title, control) {{
    if (!tabOwnsConversationControl() || !await confirmConversationControl()) {{ setStatus('attention', 'Another tab controls conversation changes. Take control when that tab is hidden or closed.'); return false; }}
    const lifecycleLockKey = 'lifecycle:' + String(action || '') + ':' + String(targetSessionId || '') + ':' + String(title || '');
    if (!beginCompanionAction(lifecycleLockKey, control || null)) return false;
    if (!sessionIdentityIsConsistent()) {{ endCompanionAction(lifecycleLockKey, control || null); return false; }}
    const sourceSessionId = String(sessionBox.value || '');
    if (!sourceSessionId && action !== 'create') {{ endCompanionAction(lifecycleLockKey, control || null); return false; }}
    const generation = nextSelectionGeneration();
    const sourceDraftText = sourceSessionId ? (messageBox.value || '') : '';
    const sourceDraftStamp = sourceSessionId ? new Date().toISOString() : '';
    const sourceDraftKey = sourceSessionId ? draftKey(sourceSessionId) : '';
    const sourceDraftRevision = sourceSessionId ? serverDraftRevision() : 0;
    if (sourceSessionId) writeLocalDraft(sourceDraftKey, sourceDraftText, sourceDraftStamp, sourceDraftRevision, String(messageBox.dataset.serverDraftDigest || ''));
    const sourcePresentation = sourceSessionId ? capturePresentation(sourceSessionId) : {{ follow_latest:true, scroll_from_bottom_px:0, composer_intentionally_empty:true, updated_at:'' }};
    if (sourceSessionId) writeLocalPresentation(sourceSessionId, sourcePresentation);
    if (draftSaveTimer) window.clearTimeout(draftSaveTimer);
    if (presentationSaveTimer) window.clearTimeout(presentationSaveTimer);
    draftSaveTimer = null;
    presentationSaveTimer = null;
    draftSaveSequence += 1;
    presentationSaveSequence += 1;
    const coordinationMutationKey = newMutationKey('lifecycle-' + String(action || 'change'));
    if (action === 'create') setStatus('creating');
    else if (action === 'archive') setStatus('archiving');
    else if (action === 'restore' || action === 'restore_open') setStatus('restoring');
    else setStatus('draft_saving', 'Saving conversation state before renaming.');
    try {{
      const response = await fetch('/api/dashboard-chat/session-lifecycle', {{
        method: 'POST',
        headers: {{ 'Content-Type':'application/json' }},
        body: JSON.stringify(Object.assign({{
          action: String(action || ''),
          navigation_client_id: navigationState.client_id,
          lifecycle_generation: generation,
          request_key: coordinationMutationKey,
          source_session_id: sourceSessionId,
          target_session_id: String(targetSessionId || ''),
          title: String(title || ''),
          source_draft_content: sourceDraftText,
          source_draft_updated_at: sourceDraftStamp,
          source_draft_base_revision: sourceDraftRevision,
          source_draft_editor_id: draftEditorId(),
          source_follow_latest: !!sourcePresentation.follow_latest,
          source_scroll_from_bottom_px: Number(sourcePresentation.scroll_from_bottom_px) || 0,
          source_composer_intentionally_empty: !!sourcePresentation.composer_intentionally_empty,
          source_presentation_updated_at: sourcePresentation.updated_at
        }}, coordinationMutationFields(coordinationMutationKey))),
        cache: 'no-store'
      }});
      const payload = await response.json();
      if (!response.ok || !payload.ok) {{
        if (payload.coordination) applyCoordinationState(payload.coordination, {{ reconcile:true }});
        throw new Error(payload.error || 'lifecycle_action_failed');
      }}
      if (payload.coordination) applyCoordinationState(payload.coordination);
      announceCoordination('state_changed', {{ session_id:String(payload.selected_session_id || '') }});
      if (generation !== selectionRequestToken) return false;
      rebuildSessionCatalog(payload.catalog || []);
      if (payload.stale_lifecycle_ignored) return false;
      if (payload.blocked) {{
        setStatus('attention', payload.message || 'This conversation cannot be changed while it is still responding.');
        return false;
      }}
      if (payload.snapshot && !applySessionSnapshot(payload.snapshot, generation, Array.isArray(payload.catalog) ? payload.catalog : null)) return false;
      rebuildSessionCatalog(payload.catalog || []);
      await refreshConversationOrganizer(catalogPageState.offset || 0);
      await refreshSessionCue(sourceSessionId);
      if (targetSessionId) await refreshSessionCue(String(targetSessionId));
      if (action === 'create') setStatus('ready', 'New conversation created.');
      else if (action === 'rename') setStatus('ready', payload.message || 'Conversation renamed.');
      else if (action === 'archive') setStatus('ready', payload.message || 'Conversation archived.');
      else if (action === 'restore_open') setStatus('ready', 'Conversation restored and opened.');
      else setStatus('ready', payload.message || 'Conversation restored.');
      return true;
    }} catch (_error) {{
      if (generation === selectionRequestToken) {{
        setStatus('attention', 'The conversation change could not be completed safely. Your draft remains saved locally.');
      }}
      return false;
    }} finally {{
      endCompanionAction(lifecycleLockKey, control || null);
    }}
  }}
  markSessionIdentityUnresolved();
  restoreDraft({{
    content: messageBox.value || '',
    updated_at: messageBox.dataset.serverDraftUpdatedAt || '',
    cleared_at: messageBox.dataset.serverDraftClearedAt || ''
  }});
  restorePresentation(initialPresentation);
  applyOfflineSessionDurability(initialOfflineSession);
  if (initialOperation && initialOperation.operation_id) {{
    activeOperationId = initialOperation.operation_id;
    applyOperationStatus({{ operation: initialOperation, session_turn: null, action_portal: initialActionPortal }});
    pollOperation(initialOperation.operation_id);
  }}
  setSessionMutationControlsDisabled(true);
  messageBox.addEventListener('input', scheduleDraftSave);
  log.addEventListener('scroll', function() {{ updateJumpLatestButton(); schedulePresentationSave(); }}, {{ passive:true }});
  if (jumpLatestButton) jumpLatestButton.addEventListener('click', function() {{ scrollConversation(true); schedulePresentationSave(); focusComposer({{ force:true }}); }});
  if (draftConflictCurrent) draftConflictCurrent.addEventListener('click', function() {{ resolveDraftConflict('current'); }});
  if (draftConflictIncoming) draftConflictIncoming.addEventListener('click', function() {{ resolveDraftConflict('incoming'); }});
  if (tabTakeControl) {{
    tabTakeControl.addEventListener('click', function() {{
      withBrowserCoordinationLock(function() {{ return postCoordination('acquire'); }}).then(function(payload) {{
        if (payload && payload.is_owner) {{
          announceCoordination('ownership_changed');
          reconcileActiveSessionSnapshot('ownership-transfer');
        }} else if (payload) {{
          setStatus('attention', payload.message || 'Another visible tab is still active.');
        }}
      }});
    }});
  }}
  window.addEventListener('beforeunload', function() {{
    if (!sessionIdentityIsConsistent() || !tabOwnsConversationControl()) return;
    const targetSessionId = sessionBox.value || '';
    if (targetSessionId) {{
      persistDraft({{ sessionId:targetSessionId, key:draftKey(targetSessionId), text:messageBox.value || '', clientUpdatedAt:new Date().toISOString(), baseRevision:serverDraftRevision(), keepalive:true }});
      persistPresentation({{ sessionId:targetSessionId, value:capturePresentation(targetSessionId), keepalive:true }});
    }}
  }});
  window.addEventListener('pagehide', function() {{
    if (!tabOwnsConversationControl()) return;
    const payload = JSON.stringify({{
      action:'release', tab_id:tabIdentity.tab_id, browser_id:tabIdentity.browser_id,
      lease_token:coordinationState.lease_token || '', instance_nonce:coordinationInstanceNonce, visible:false
    }});
    try {{
      if (navigator.sendBeacon) navigator.sendBeacon('/api/dashboard-chat/coordination', new Blob([payload], {{ type:'application/json' }}));
      else fetch('/api/dashboard-chat/coordination', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:payload, keepalive:true }});
    }} catch (_error) {{}}
  }});
  window.addEventListener('popstate', function(event) {{ restoreChatHistoryState(event.state, 'browser-back-forward'); }});
  window.addEventListener('pageshow', function(event) {{
    recoverConversationLifecycle(event.persisted ? 'bfcache-return' : 'history-return', {{ restoreHistory:!!event.persisted }});
  }});
  document.addEventListener('visibilitychange', function() {{
    if (document.hidden) {{
      postCoordination(tabOwnsConversationControl() ? 'heartbeat' : 'snapshot').then(scheduleCoordinationHeartbeat);
      return;
    }}
    recoverConversationLifecycle('sleep-resume');
  }});
  window.addEventListener('online', function() {{ recoverConversationLifecycle('offline-recovery'); }});
  window.addEventListener('focus', function() {{
    if (!document.hidden) recoverConversationLifecycle('focus-recovery');
  }});
  window.addEventListener('offline', function() {{
    setStatus('offline', 'The dashboard is offline. Draft text remains in this browser until coordination returns.');
  }});
  window.setTimeout(function() {{
    announceCoordination('hello');
    withBrowserCoordinationLock(activateCurrentBrowserTab).then(function() {{
      announceCoordination('ownership_changed');
      scheduleCoordinationHeartbeat();
      if (!sessionIdentityResolved) reconcileActiveSessionSnapshot('initial-load');
    }});
  }}, 0);
  let allowNextLineBreak = false;
  let compositionActive = false;
  let keyboardSubmitLatch = false;
  function requestComposerSubmitOnce(event) {{
    if (keyboardSubmitLatch || composerSubmissionPending || sendButton.disabled) {{ if (event) event.preventDefault(); return false; }}
    keyboardSubmitLatch = true; if (event) event.preventDefault();
    Promise.resolve().then(function() {{ keyboardSubmitLatch = false; }});
    form.requestSubmit(); return true;
  }}
  messageBox.addEventListener('compositionstart', function() {{ compositionActive = true; }});
  messageBox.addEventListener('compositionend', function() {{ compositionActive = false; }});
  messageBox.addEventListener('keydown', function(event) {{
    if (event.key !== 'Enter') return;
    if (event.shiftKey) {{
      allowNextLineBreak = true;
      window.setTimeout(function() {{ allowNextLineBreak = false; }}, 0);
      return;
    }}
    if (compositionActive || event.isComposing || event.keyCode === 229) return;
    if (event.repeat) {{ event.preventDefault(); return; }}
    requestComposerSubmitOnce(event);
  }});
  messageBox.addEventListener('beforeinput', function(event) {{
    if (!['insertLineBreak','insertParagraph'].includes(String(event.inputType || ''))) return;
    if (allowNextLineBreak || compositionActive || event.isComposing) {{ allowNextLineBreak = false; return; }}
    requestComposerSubmitOnce(event);
  }});
  document.addEventListener('keydown', function(event) {{
    if (event.key !== 'Escape' || event.defaultPrevented || event.isComposing) return;
    if (closeTemporaryCompanionSurfaces()) {{
      event.preventDefault();
      focusComposer({{ force:true }});
    }}
  }});
  function openSelectedConversation(control) {{
    if (!sessionIdentityIsConsistent()) {{
      setStatus('attention', 'The active conversation is still being reconciled. Nothing was switched.');
      reconcileActiveSessionSnapshot('history-return');
      return false;
    }}
    return switchConversationSession(sessionSelector ? sessionSelector.value : '', {{ control:control || sessionOpenButton }});
  }}
  if (sessionSwitchForm) {{
    sessionSwitchForm.addEventListener('submit', function(event) {{
      event.preventDefault();
      openSelectedConversation(sessionOpenButton);
    }});
  }}
  if (sessionOpenButton) {{
    sessionOpenButton.addEventListener('click', function(event) {{
      event.preventDefault();
      openSelectedConversation(sessionOpenButton);
    }});
  }}
  if (sessionCreateForm) {{
    sessionCreateForm.addEventListener('submit', function(event) {{
      event.preventDefault();
      const titleInput = sessionCreateForm.querySelector("input[name='title']");
      const title = titleInput ? titleInput.value : '';
      const button = sessionCreateForm.querySelector('button');
      performConversationLifecycle('create', '', title, button).then(function(ok) {{
        if (ok && titleInput) titleInput.value = '';
      }});
    }});
  }}
  document.addEventListener('submit', function(event) {{
    const targetForm = event.target;
    if (!targetForm || targetForm === form || targetForm === sessionSwitchForm || targetForm === sessionCreateForm) return;
    const openForm = targetForm.matches && targetForm.matches('[data-chat-session-open]');
    const openSeenForm = targetForm.matches && targetForm.matches('[data-chat-session-open-seen]');
    const acknowledgeForm = targetForm.matches && targetForm.matches('.chat-session-cue-ack-form');
    const renameForm = targetForm.matches && targetForm.matches('[data-chat-session-rename]');
    const archiveForm = targetForm.matches && targetForm.matches('[data-chat-session-archive]');
    const restoreForm = targetForm.matches && targetForm.matches('[data-chat-session-restore]');
    const restoreOpenForm = targetForm.matches && targetForm.matches('[data-chat-session-restore-open]');
    const recoveryForm = targetForm.matches && targetForm.matches('.chat-recovery-control');
    const regenerateForm = targetForm.matches && targetForm.matches('.chat-turn-regenerate-form');
    const resendForm = targetForm.matches && targetForm.matches('.chat-turn-resend-form');
    const branchForm = targetForm.matches && targetForm.matches('.chat-turn-branch-form');
    if (!openForm && !openSeenForm && !acknowledgeForm && !renameForm && !archiveForm && !restoreForm && !restoreOpenForm && !recoveryForm && !regenerateForm && !resendForm && !branchForm) return;
    event.preventDefault();
    if (regenerateForm || resendForm || branchForm) {{
      if (!tabOwnsConversationControl()) {{
        setStatus('attention', 'Another tab controls conversation changes. Nothing was submitted.');
        return;
      }}
      const actionPrefix = branchForm ? 'branch' : (regenerateForm ? 'regenerate' : 'resend');
      const mutationFields = coordinationMutationFields(newMutationKey(actionPrefix));
      Object.keys(mutationFields).forEach(function(name) {{
        let input = targetForm.querySelector("input[name='" + name + "']");
        if (!input) {{ input = document.createElement('input'); input.type = 'hidden'; input.name = name; targetForm.appendChild(input); }}
        input.value = String(mutationFields[name] == null ? '' : mutationFields[name]);
      }});
      const identityName = branchForm ? 'branch_request_id' : 'operation_id';
      let identityInput = targetForm.querySelector("input[name='" + identityName + "']");
      if (!identityInput) {{ identityInput = document.createElement('input'); identityInput.type = 'hidden'; identityInput.name = identityName; targetForm.appendChild(identityInput); }}
      identityInput.value = branchForm ? String(mutationFields.mutation_key) : newConversationOperationId();
      setStatus('connecting', branchForm ? 'Creating an unsent branch draft.' : 'Opening the explicit turn action.');
      targetForm.submit();
      return;
    }}
    if (recoveryForm) {{
      const recoveryButton = targetForm.querySelector('button');
      const turnInput = targetForm.querySelector("input[name='turn_id']");
      const recoveryLockKey = 'recovery:' + String(turnInput ? turnInput.value : 'unknown');
      if (!tabOwnsConversationControl()) {{
        setStatus('attention', 'Another tab controls conversation changes. The failed turn was not retried.');
        return;
      }}
      if (!beginCompanionAction(recoveryLockKey, recoveryButton || null)) return;
      const recoveryFields = coordinationMutationFields(newMutationKey('retry'));
      Object.keys(recoveryFields).forEach(function(name) {{
        let input = targetForm.querySelector("input[name='" + name + "']");
        if (!input) {{ input = document.createElement('input'); input.type = 'hidden'; input.name = name; targetForm.appendChild(input); }}
        input.value = String(recoveryFields[name] == null ? '' : recoveryFields[name]);
      }});
      setStatus('draft_saving', 'Opening the explicit recovery action.');
      targetForm.submit();
      return;
    }}
    const sessionInput = targetForm.querySelector("input[name='session_id']");
    const tokenInput = targetForm.querySelector("input[name='acknowledgement_token']");
    const titleInput = targetForm.querySelector("input[name='title']");
    const targetSessionId = sessionInput ? sessionInput.value : '';
    const acknowledgementToken = tokenInput ? tokenInput.value : '';
    const button = targetForm.querySelector('button');
    if (acknowledgeForm) acknowledgeCurrentSessionCue(targetSessionId, '', button, acknowledgementToken);
    else if (renameForm) performConversationLifecycle('rename', targetSessionId, titleInput ? titleInput.value : '', button);
    else if (archiveForm) performConversationLifecycle('archive', targetSessionId, '', button);
    else if (restoreOpenForm) performConversationLifecycle('restore_open', targetSessionId, '', button);
    else if (restoreForm) performConversationLifecycle('restore', targetSessionId, '', button);
    else switchConversationSession(targetSessionId, openSeenForm ? {{ acknowledgementToken:acknowledgementToken, control:button }} : {{ control:button }});
  }});
  if (catalogSearchForm) {{
    catalogSearchForm.addEventListener('submit', function(event) {{
      event.preventDefault();
      persistUsabilityState();
      refreshConversationOrganizer(0);
    }});
  }}
  if (catalogClear) catalogClear.addEventListener('click', function() {{
    if (catalogQuery) catalogQuery.value = '';
    if (catalogArchived) catalogArchived.checked = false;
    persistUsabilityState();
    refreshConversationOrganizer(0);
    if (catalogQuery) catalogQuery.focus();
  }});
  if (catalogPrevious) catalogPrevious.addEventListener('click', function() {{ refreshConversationOrganizer(Number(catalogPrevious.dataset.offset) || 0); }});
  if (catalogNext) catalogNext.addEventListener('click', function() {{ refreshConversationOrganizer(Number(catalogNext.dataset.offset) || 0); }});
  [toolsDrawer,sessionOrganizer,continuityPanel,continuityCuration,entityAssociationCuration,diagnosticsDrawer].forEach(function(node) {{
    if (node) node.addEventListener('toggle', persistUsabilityState);
  }});
  if (entityAssociationCuration) entityAssociationCuration.addEventListener('submit', function(event) {{
    const form = event.target && event.target.closest ? event.target.closest('form') : null;
    if (!form) return;
    persistUsabilityState();
    setStatus('working', 'Updating the selected stored association. The change is revision-bound and the page may take a moment to refresh.');
    form.querySelectorAll('button').forEach(function(button) {{ button.disabled = true; }});
  }});
  const initialBrowserHistoryState = initialHistoryRestorationPending ? window.history.state : null;
  renderOrganizerCatalogPage(catalogPageState);
  if (initialBrowserHistoryState) restoreChatHistoryState(initialBrowserHistoryState, 'initial-history-restore');
  else writeChatHistoryState('replace');
  const restoredUsabilityState = restoreUsabilityState();
  if (window.location.hash) {{
    const hashTarget = document.querySelector(window.location.hash);
    if (hashTarget) {{
      let ancestor = hashTarget;
      while (ancestor) {{
        if (ancestor.tagName === 'DETAILS') ancestor.open = true;
        ancestor = ancestor.parentElement;
      }}
      window.requestAnimationFrame(function() {{ hashTarget.scrollIntoView({{ block:'start' }}); }});
    }}
  }}
  if ((catalogQuery && String(catalogQuery.value || '').trim() !== String(catalogPageState.query || ''))
      || (catalogArchived && !!catalogArchived.checked !== !!catalogPageState.include_archived)
      || Number(restoredUsabilityState.catalog_offset || 0) !== Number(catalogPageState.offset || 0)) {{
    refreshConversationOrganizer(restoredUsabilityState.catalog_offset || 0);
  }}
  document.addEventListener('click', function(event) {{
    const button = event.target && event.target.closest ? event.target.closest('[data-lifecycle-action]') : null;
    if (!button) return;
    event.preventDefault();
    const action = String(button.dataset.lifecycleAction || '');
    const targetSessionId = String(button.dataset.sessionId || '');
    let title = '';
    if (action === 'rename' && sessionList) {{
      const input = sessionList.querySelector("[data-lifecycle-rename-input='" + targetSessionId + "']");
      title = input ? input.value : '';
    }}
    performConversationLifecycle(action, targetSessionId, title, button);
  }});
  async function loadEarlierConversationHistory() {{
    if (!loadEarlierButton || loadEarlierButton.hidden || !sessionBox.value) return false;
    const before = String(loadEarlierButton.dataset.beforeTurnId || '');
    if (!before) return false;
    loadEarlierButton.disabled = true;
    const priorHeight = log.scrollHeight;
    try {{
      const params = new URLSearchParams({{ session_id:String(sessionBox.value), before_turn_id:before, limit:'80' }});
      const response = await fetch('/api/dashboard-chat/session-window?' + params.toString(), {{ cache:'no-store' }});
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'history_window_failed');
      const holder = document.createElement('div');
      holder.innerHTML = String(payload.transcript_html || '');
      const fragment = document.createDocumentFragment();
      Array.from(holder.childNodes).forEach(function(node) {{ fragment.appendChild(node); }});
      log.insertBefore(fragment, log.firstChild);
      let previousDate = '';
      log.querySelectorAll('.chat-date-divider').forEach(function(divider) {{
        if (divider.dataset.chatDate === previousDate) divider.remove();
        else previousDate = divider.dataset.chatDate;
      }});
      log.scrollTop += Math.max(0, log.scrollHeight - priorHeight);
      loadEarlierButton.hidden = !payload.has_older;
      loadEarlierButton.dataset.beforeTurnId = String(payload.oldest_turn_id || '');
      if (historyWindowStatus) historyWindowStatus.textContent = 'Earlier messages loaded. ' + String(log.querySelectorAll('.chat-turn.user-turn').length) + ' turns are rendered of ' + String(payload.total_turns || 0) + '.';
      schedulePresentationSave();
      return true;
    }} catch (_error) {{
      setStatus('attention', 'Earlier conversation history could not be loaded. Existing messages were preserved.');
      return false;
    }} finally {{ loadEarlierButton.disabled = false; }}
  }}
  if (loadEarlierButton) loadEarlierButton.addEventListener('click', loadEarlierConversationHistory);
  form.addEventListener('submit', async function(event) {{
    event.preventDefault();
    if (!sessionIdentityIsConsistent() || !sessionBox.value || !tabOwnsConversationControl()) {{ setStatus('attention', 'Conversation control is not available in this tab. Nothing was sent.'); return; }}
    if (activeDraftConflict) {{ setStatus('attention', 'Resolve the preserved draft conflict before sending. No text was submitted.'); return; }}
    const message = (messageBox.value || '').trim();
    if (!message) {{ setStatus('attention', 'Write something before sending.'); return; }}
    if (composerSubmissionPending || activeController || activeOperationId) {{ setStatus('connecting', 'The current message is already being accepted or answered. Nothing was submitted twice.'); return; }}
    composerSubmissionPending = true;
    setSessionMutationControlsDisabled(false);
    if (!await confirmConversationControl()) {{
      composerSubmissionPending = false;
      setSessionMutationControlsDisabled(!sessionIdentityResolved);
      setStatus('attention', 'Another tab now controls this conversation. Nothing was sent.');
      return;
    }}
    const turnSessionId = String(sessionBox.value || '');
    const turnGeneration = selectionRequestToken;
    const turnDraftKey = currentDraftKey || draftKey(turnSessionId);
    bubble('user', message);
    const reply = bubble('eidolon', '');
    reply.dataset.pendingReply = 'true';
    reply.textContent = 'Thinking...';
    const turnUiSequence = ++foregroundTurnSequence;
    let pendingReplyText = '';
    let replyFlushHandle = 0;
    function turnIsForeground() {{
      return turnUiSequence === foregroundTurnSequence && isCurrentSelection(turnSessionId, turnGeneration) && reply.isConnected;
    }}
    function flushReplyText() {{
      if (replyFlushHandle) window.cancelAnimationFrame(replyFlushHandle);
      replyFlushHandle = 0;
      if (!pendingReplyText || !reply.isConnected) return;
      reply.textContent += pendingReplyText;
      pendingReplyText = '';
    }}
    function queueReplyText(text) {{
      pendingReplyText += String(text || '');
      if (replyFlushHandle || !pendingReplyText) return;
      replyFlushHandle = window.requestAnimationFrame(function() {{
        replyFlushHandle = 0;
        if (!reply.isConnected) {{ pendingReplyText = ''; return; }}
        const follow = isFollowingConversation();
        reply.textContent += pendingReplyText;
        pendingReplyText = '';
        if (follow) scrollConversation(true);
      }});
    }}
    messageBox.value = '';
    sendButton.disabled = true;
    cancelButton.disabled = false;
    setStatus('connecting');
    const started = performance.now();
    resetLiveActivity();
    const turnController = new AbortController();
    activeController = turnController;
    activeOperationId = '';
    let operationIdForTurn = '';
    let acceptedByRuntime = false;
    draftClearedOperationId = '';
    const resendContextForTurn = explicitResendContext && explicitResendContext.session_id === turnSessionId
      ? Object.assign({{}}, explicitResendContext) : null;
    const acceptanceKey = resendContextForTurn && resendContextForTurn.resend_acceptance_key
      ? resendContextForTurn.resend_acceptance_key
      : ((window.crypto && typeof window.crypto.randomUUID === 'function')
          ? window.crypto.randomUUID()
          : ('chat-' + Date.now() + '-' + Math.random().toString(16).slice(2)));
    if (resendContextForTurn) resendContextForTurn.resend_acceptance_key = acceptanceKey;
    pendingSubmissions.set(turnSessionId, {{ message:message, acceptance_key:acceptanceKey, accepted:false, generation:turnGeneration, resend_context:resendContextForTurn }});
    let streamStartTimedOut = false;
    let terminalEventSeen = false;
    let transportWatchdog = 0;
    let transportRecoveryStarted = false;
    function clearTransportWatchdog() {{
      if (transportWatchdog) window.clearTimeout(transportWatchdog);
      transportWatchdog = 0;
    }}
    function armTransportWatchdog() {{
      clearTransportWatchdog();
      if (terminalEventSeen) return;
      transportWatchdog = window.setTimeout(async function() {{
        if (terminalEventSeen || transportRecoveryStarted) return;
        transportRecoveryStarted = true;
        const foreground = turnIsForeground();
        if (acceptedByRuntime && operationIdForTurn) {{
          markReplyForReconciliation(reply, operationIdForTurn);
          if (foreground) setStatus('disconnected', 'The viewer stream is quiet. Eidolon is checking the accepted operation without replaying it.');
          pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence, sessionId:turnSessionId, generation:turnGeneration }});
          return;
        }}
        const outcome = await resolveAcceptanceOutcome(turnSessionId, acceptanceKey, 2);
        if (outcome.state === 'accepted' && outcome.payload && outcome.payload.operation) {{
          acceptedByRuntime = true;
          operationIdForTurn = String(outcome.payload.operation.operation_id || '');
          if (resendContextForTurn) explicitResendContext = null;
          pendingSubmissions.delete(turnSessionId);
          markReplyForReconciliation(reply, operationIdForTurn);
          if (foreground) {{
            activeOperationId = operationIdForTurn;
            setStatus('disconnected', 'The viewer stream is quiet, but the turn was accepted. Its status is being reconciled without replay.');
          }}
          applyOperationStatus(outcome.payload, {{ updateStatus:foreground }});
          pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence, sessionId:turnSessionId, generation:turnGeneration }});
        }} else if (foreground) {{
          setStatus('disconnected', 'The viewer stream is quiet and acceptance is not yet confirmed. No retry or duplicate submission occurred.');
        }}
      }}, 12000);
    }}
    function noteTransportActivity() {{
      transportRecoveryStarted = false;
      if (!terminalEventSeen) armTransportWatchdog();
    }}
    try {{
      let response;
      try {{
        response = await boundedControlFetch('/api/dashboard-chat/stream', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(Object.assign({{
            message: message, use_ai: !!useAi.checked, session_id: turnSessionId, acceptance_key: acceptanceKey,
            resend_source_acceptance_key: resendContextForTurn ? resendContextForTurn.source_acceptance_key : '',
            resend_evidence_token: resendContextForTurn ? resendContextForTurn.source_evidence_token : ''
          }}, coordinationMutationFields(acceptanceKey))),
          cache: 'no-store',
          signal: turnController.signal
        }}, 12000);
      }} catch (error) {{
        if (error && error.name === 'AbortError') streamStartTimedOut = true;
        throw error;
      }}
      if (!response.ok || !response.body) {{
        const outcome = await resolveAcceptanceOutcome(turnSessionId, acceptanceKey, 3);
        const resolved = outcome.state === 'accepted' ? outcome.payload : null;
        if (resolved && resolved.operation) {{
          acceptedByRuntime = true;
          operationIdForTurn = String(resolved.operation.operation_id || '');
          if (resendContextForTurn) explicitResendContext = null;
          pendingSubmissions.delete(turnSessionId);
          if (turnIsForeground()) activeOperationId = operationIdForTurn;
          markReplyForReconciliation(reply, operationIdForTurn);
          if (operationIdForTurn && draftClearedOperationId !== operationIdForTurn) {{
            clearAcceptedDraft(turnSessionId, turnDraftKey, turnGeneration);
            draftClearedOperationId = operationIdForTurn;
          }}
          if (turnIsForeground()) setStatus('disconnected', 'The turn was accepted, but the initial stream response was uncertain. Nothing was resubmitted.');
          applyOperationStatus(resolved, {{ updateStatus:turnIsForeground() }});
          pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence, sessionId:turnSessionId, generation:turnGeneration }});
          return;
        }}
        pendingSubmissions.delete(turnSessionId);
        const restored = await restoreUnacceptedDraft(turnSessionId, turnDraftKey, message, turnGeneration);
        const evidence = outcome.state === 'not_found'
          ? await persistNonAcceptanceEvidence(turnSessionId, acceptanceKey, 'acceptance_rejected')
          : null;
        if (turnIsForeground()) {{
          reply.textContent = outcome.state === 'not_found'
            ? 'The conversation endpoint did not accept the turn. Your message was not regenerated automatically.'
            : 'The conversation endpoint could not confirm acceptance. Your message was not regenerated automatically.';
          if (evidence) appendExplicitResendPresentation(reply, evidence);
          if (restored) setStatus('attention', outcome.state === 'not_found' ? 'The turn was proven unaccepted. Your draft was restored for explicit review.' : 'Acceptance could not be confirmed. Your draft was restored without enabling resend.');
        }}
        return;
      }}
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let gotFirstToken = false;
      armTransportWatchdog();
      function consume(raw, flushFinal) {{
        const framed = splitSseFrames(buffer + raw, flushFinal);
        buffer = framed.remainder;
        for (const packet of framed.frames) {{
          const parsedFrame = parseSseFrame(packet);
          const type = parsedFrame.type;
          const data = parsedFrame.data;
          noteTransportActivity();
          if (!data) continue;
          let payload = {{}};
          try {{ payload = JSON.parse(data); }} catch (_error) {{ payload = {{ text: data }}; }}
          const turnIsCurrent = isCurrentSelection(turnSessionId, turnGeneration) && reply.isConnected;
          const foreground = turnUiSequence === foregroundTurnSequence && turnIsCurrent;
          if (type === 'accepted') {{
            if (payload.coordination) applyCoordinationState(payload.coordination);
            announceCoordination('operation_changed', {{ session_id:turnSessionId, operation_id:String(payload.operation_id || '') }});
            acceptedByRuntime = true;
            operationIdForTurn = payload.operation_id || operationIdForTurn;
            const pending = pendingSubmissions.get(turnSessionId);
            if (pending) pending.accepted = true;
            pendingSubmissions.delete(turnSessionId);
            if (foreground) activeOperationId = operationIdForTurn || activeOperationId;
            if (operationIdForTurn && draftClearedOperationId !== operationIdForTurn) {{
              clearAcceptedDraft(turnSessionId, turnDraftKey, turnGeneration);
              draftClearedOperationId = operationIdForTurn;
              const article = reply.closest('.chat-turn');
              if (article) article.dataset.sessionTurnId = operationIdForTurn;
            }}
            if (foreground) setStatus('thinking', 'The turn was accepted once. Eidolon is still responding.');
          }} else if (type === 'meta') {{
            acceptedByRuntime = true;
            operationIdForTurn = payload.operation_id || operationIdForTurn;
            const pending = pendingSubmissions.get(turnSessionId);
            if (pending) pending.accepted = true;
            pendingSubmissions.delete(turnSessionId);
            if (foreground) activeOperationId = operationIdForTurn || activeOperationId;
            if (operationIdForTurn && draftClearedOperationId !== operationIdForTurn) {{
              clearAcceptedDraft(turnSessionId, turnDraftKey, turnGeneration);
              draftClearedOperationId = operationIdForTurn;
              const article = reply.closest('.chat-turn');
              if (article) article.dataset.sessionTurnId = operationIdForTurn;
            }}
            if (foreground) {{
              if (payload.provider) providerDetail.textContent = payload.provider;
              if (payload.model) modelDetail.textContent = payload.model;
              setStatus('thinking');
            }}
          }} else if (type === 'delta') {{
            if (!turnIsCurrent) continue;
            const visibleText = String(payload.text || '');
            if (!gotFirstToken && visibleText.trim()) {{
              gotFirstToken = true;
              if (reply.dataset.pendingReply === 'true') reply.textContent = '';
              delete reply.dataset.pendingReply;
              if (foreground) {{
                const clientFirstVisibleMs = Math.round(performance.now() - started);
                firstToken.textContent = String(clientFirstVisibleMs);
                window.__eidolonLastDeliveryTiming = {{
                  intent_to_first_visible_ms:clientFirstVisibleMs,
                  server:payload.timing || null,
                  content_free:true
                }};
                setStatus('responding');
              }}
            }}
            queueReplyText(visibleText);
          }} else if (type === 'conversation_complete') {{
            flushReplyText();
            const result = payload.result || {{}};
            if (foreground) {{
              if (result.success && result.recovery_of) setStatus('recovered');
              else if (result.success) setStatus('ready', 'Reply saved. You can keep talking.');
              else applyFailurePresentation(result.failure_category || result.completion_state, reply);
              settleTerminalControls(operationIdForTurn);
              focusComposer();
            }}
          }} else if (type === 'action') {{
            if (turnIsCurrent) appendChatActionCard(payload.action || {{}}, reply);
          }} else if (type === 'action_result') {{
            if (turnIsCurrent) applyChatActionResult(payload, reply);
            if (foreground) setStatus(payload.execution && payload.execution.ok ? 'ready' : 'attention', payload.execution ? payload.execution.message : 'The action finished.');
          }} else if (type === 'activity') {{
            if (foreground) appendLiveActivity(payload);
          }} else if (type === 'internal_voice') {{
            if (foreground) appendLiveActivity({{summary:String(payload.voice_text || ''), activity_kind:'observation'}});
          }} else if (type === 'status') {{
            if (!foreground) continue;
            const stage = String(payload.stage || '').toLowerCase();
            if (stage === 'action_execution') setStatus('saving', payload.message || 'Running the explicitly requested safe system action.');
            else if (stage === 'action_retry') setStatus('saving', payload.message || 'Retrying the exact linked low-risk action once.');
            else if (stage === 'action_control') setStatus('saving', payload.message || 'Applying the exact pending-action control.');
            else if (stage === 'action_ready') setStatus('ready', payload.message || 'The supervised action is ready for review.');
            else if (stage === 'action_proposal') setStatus('ready', 'Reply saved. Optional action details are finishing in the background.');
            else if (stage.includes('save') || stage.includes('commit')) setStatus('saving');
            else setStatus('thinking', payload.message || 'Eidolon is working on the reply.');
          }} else if (type === 'saved') {{
            if (!foreground) continue;
            if (payload.latency && payload.latency.total_ms) totalTime.textContent = String(payload.latency.total_ms);
            setStatus('ready');
          }} else if (type === 'done') {{
            terminalEventSeen = true;
            clearTransportWatchdog();
            flushReplyText();
            announceCoordination('operation_changed', {{ session_id:turnSessionId, operation_id:String(operationIdForTurn || '') }});
            const result = payload.result || (payload.turn && payload.turn.conversation_runtime) || {{}};
            if (payload.operation) applyOperationStatus(payload, {{ updateStatus:foreground }});
            else if (payload.session_turn && operationIdForTurn) updateSessionCue({{ operation:{{ operation_id:operationIdForTurn, session_id:turnSessionId, public_state:result.success ? 'completed' : (result.completion_state || 'failed') }}, session_turn:payload.session_turn }});
            if (foreground) {{
              if (result.success && result.recovery_of) setStatus('recovered');
              else if (result.success) setStatus('ready');
              else applyFailurePresentation(result.failure_category || result.completion_state, reply);
              appendRecoveryActions(result);
              settleTerminalControls(operationIdForTurn);
            }}
            if (operationIdForTurn) clearOperationPoll(operationIdForTurn);
          }} else if (type === 'replace') {{
            if (!turnIsCurrent || reply.dataset.failureCategory) continue;
            flushReplyText();
            const follow = isFollowingConversation();
            delete reply.dataset.pendingReply;
            reply.textContent = payload.text || '';
            if (follow) scrollConversation(true);
          }} else if (type === 'error') {{
            flushReplyText();
            if (turnIsCurrent) applyFailurePresentation(payload.failure_category, reply, {{ updateStatus:foreground }});
          }}
        }}
      }}
      while (true) {{
        const result = await reader.read();
        if (result.done) break;
        consume(decoder.decode(result.value, {{ stream: true }}));
      }}
      consume(decoder.decode(), true);
      if (!terminalEventSeen) {{
        const foreground = turnIsForeground();
        if (acceptedByRuntime && operationIdForTurn) {{
          pendingSubmissions.delete(turnSessionId);
          markReplyForReconciliation(reply, operationIdForTurn);
          if (foreground) {{
            activeOperationId = operationIdForTurn;
            if (reply.dataset.pendingReply === 'true') {{
              reply.textContent = 'The viewer stream ended before final confirmation. Eidolon is reconciling the accepted turn without replaying it.';
            }}
            setStatus('disconnected', 'The accepted turn ended without a terminal stream event. Its persisted state is being reconciled.');
          }}
          pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence, sessionId:turnSessionId, generation:turnGeneration }});
        }} else {{
          const outcome = await resolveAcceptanceOutcome(turnSessionId, acceptanceKey, 3);
          const resolved = outcome.state === 'accepted' ? outcome.payload : null;
          if (resolved && resolved.operation) {{
            acceptedByRuntime = true;
            operationIdForTurn = String(resolved.operation.operation_id || '');
            if (resendContextForTurn) explicitResendContext = null;
            pendingSubmissions.delete(turnSessionId);
            markReplyForReconciliation(reply, operationIdForTurn);
            if (operationIdForTurn && draftClearedOperationId !== operationIdForTurn) {{
              clearAcceptedDraft(turnSessionId, turnDraftKey, turnGeneration);
              draftClearedOperationId = operationIdForTurn;
            }}
            if (foreground) {{
              activeOperationId = operationIdForTurn;
              setStatus('disconnected', 'The stream ended before confirmation, but the turn was accepted. Nothing was resubmitted.');
            }}
            applyOperationStatus(resolved, {{ updateStatus:foreground }});
            pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence, sessionId:turnSessionId, generation:turnGeneration }});
          }} else {{
            pendingSubmissions.delete(turnSessionId);
            const restored = await restoreUnacceptedDraft(turnSessionId, turnDraftKey, message, turnGeneration);
            const evidence = outcome.state === 'not_found'
              ? (resendContextForTurn || await persistNonAcceptanceEvidence(turnSessionId, acceptanceKey, 'acceptance_validation_failed'))
              : null;
            if (foreground) {{
              reply.textContent = outcome.state === 'not_found'
                ? 'The stream ended before the turn was accepted. Your message was not replayed automatically.'
                : 'The stream ended before acceptance could be confirmed. No resend was enabled.';
              if (evidence) appendExplicitResendPresentation(reply, evidence);
              if (restored) setStatus('attention', outcome.state === 'not_found' ? 'The stream ended before acceptance. Your draft was restored for explicit review.' : 'Acceptance remains uncertain. Your draft was restored without enabling resend.');
            }}
          }}
        }}
      }}
    }} catch (error) {{
      flushReplyText();
      const turnIsCurrent = isCurrentSelection(turnSessionId, turnGeneration) && reply.isConnected;
      const foreground = turnUiSequence === foregroundTurnSequence && turnIsCurrent;
      if (error && error.name === 'AbortError' && !streamStartTimedOut) {{
        if (foreground) {{
          reply.textContent = 'Cancellation was requested. Eidolon will reconcile the exact final state without replaying the turn.';
          setStatus('cancelling', 'Cancellation was requested for this exact operation.');
        }}
        if (operationIdForTurn) pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence, sessionId:turnSessionId, generation:turnGeneration }});
      }} else {{
        if (foreground) {{
          reply.textContent = acceptedByRuntime
            ? 'The viewer connection ended. Eidolon will reconcile the already-accepted operation without resubmitting it.'
            : 'The conversation endpoint did not accept the turn. Your draft was restored.';
        }}
        if (!acceptedByRuntime) {{
          const outcome = await resolveAcceptanceOutcome(turnSessionId, acceptanceKey, 3);
          const resolved = outcome.state === 'accepted' ? outcome.payload : null;
          if (resolved && resolved.operation) {{
            acceptedByRuntime = true;
            operationIdForTurn = resolved.operation.operation_id || '';
            if (resendContextForTurn) explicitResendContext = null;
            pendingSubmissions.delete(turnSessionId);
            if (foreground) activeOperationId = operationIdForTurn;
            markReplyForReconciliation(reply, operationIdForTurn);
            if (operationIdForTurn && draftClearedOperationId !== operationIdForTurn) {{
              clearAcceptedDraft(turnSessionId, turnDraftKey, turnGeneration);
              draftClearedOperationId = operationIdForTurn;
            }}
            if (foreground) setStatus('disconnected', 'The turn was accepted before the viewer connection ended. Nothing was resubmitted.');
            applyOperationStatus(resolved, {{ updateStatus:foreground }});
            pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence, sessionId:turnSessionId, generation:turnGeneration }});
          }} else {{
            pendingSubmissions.delete(turnSessionId);
            const restored = await restoreUnacceptedDraft(turnSessionId, turnDraftKey, message, turnGeneration);
            const evidence = outcome.state === 'not_found'
              ? (resendContextForTurn || await persistNonAcceptanceEvidence(turnSessionId, acceptanceKey, 'acceptance_internal_failure'))
              : null;
            if (foreground) {{
              if (evidence) appendExplicitResendPresentation(reply, evidence);
              if (restored) setStatus('disconnected', outcome.state === 'not_found' ? 'The connection ended before acceptance. Your draft was restored for explicit review.' : 'Acceptance remains uncertain. Your draft was restored without enabling resend.');
            }}
          }}
        }} else {{
          if (foreground) setStatus('disconnected', 'The connection ended before completion could be confirmed. Nothing was resubmitted or silently cancelled.');
          if (operationIdForTurn) pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence, sessionId:turnSessionId, generation:turnGeneration }});
        }}
      }}
    }} finally {{
      clearTransportWatchdog();
      flushReplyText();
      if (activeController === turnController) activeController = null;
      composerSubmissionPending = false;
      if (turnIsForeground()) {{
        setSessionMutationControlsDisabled(!sessionIdentityResolved);
        messageBox.focus();
      }}
    }}
  }});
  log.addEventListener('click', function(event) {{
    const refreshRecovery = event.target && event.target.closest ? event.target.closest('.chat-refresh-recovery-state') : null;
    if (refreshRecovery) {{
      reconcileActiveSessionSnapshot('recovery-state-refresh');
      return;
    }}
    const reviewResend = event.target && event.target.closest ? event.target.closest('.chat-review-resend-draft') : null;
    if (reviewResend) {{
      messageBox.focus();
      setStatus('ready', 'Review the restored draft, then press Send explicitly. Eidolon will create one new acceptance identity, or resume the already-claimed one after an interruption.');
      return;
    }}
    const offline = event.target && event.target.closest ? event.target.closest('.chat-continue-offline') : null;
    if (!offline) return;
    useAi.checked = false;
    setStatus('offline', 'Future messages will be recorded without contacting a provider until you turn local generation back on.');
    messageBox.focus();
  }});
  document.addEventListener('click', async function(event) {{
    const link = event.target && event.target.closest ? event.target.closest('.chat-open-provider-settings') : null;
    if (!link) return;
    event.preventDefault();
    if (!sessionIdentityIsConsistent()) {{
      setStatus('attention', 'The active conversation must be reconciled before opening provider settings. No draft was saved to another session.');
      reconcileActiveSessionSnapshot('history-return');
      return;
    }}
    if (draftSaveTimer) window.clearTimeout(draftSaveTimer);
    if (presentationSaveTimer) window.clearTimeout(presentationSaveTimer);
    const targetSessionId = sessionBox.value || '';
    await persistDraft({{ sessionId:targetSessionId, key:draftKey(targetSessionId), text:messageBox.value || '', clientUpdatedAt:new Date().toISOString(), baseRevision:serverDraftRevision(), keepalive:true }});
    await persistPresentation({{ sessionId:targetSessionId, value:capturePresentation(targetSessionId), keepalive:true }});
    window.location.assign(link.href);
  }});
  async function mutateConversationControls(action, extra) {{
    if (!sessionIdentityIsConsistent() || !tabOwnsConversationControl() || !await confirmConversationControl()) {{
      setStatus('attention', 'Take conversation control before changing session-local working context.');
      return null;
    }}
    const mutationKey = newMutationKey('conversation-controls');
    const payload = Object.assign({{
      session_id:String(sessionBox.value || selectedSessionId || ''),
      action:String(action || ''),
      expected_revision:conversationControlsRevision
    }}, extra || {{}}, coordinationMutationFields(mutationKey));
    const response = await boundedControlFetch('/api/dashboard-chat/conversation-controls', {{
      method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(payload), cache:'no-store'
    }}, 8000);
    const result = await response.json();
    if (result.coordination) applyCoordinationState(result.coordination, {{reconcile:true}});
    if (!response.ok || result.ok === false) throw new Error(result.error || 'conversation_controls_failed');
    conversationControlsRevision = Number(result.revision || conversationControlsRevision);
    return result;
  }}
  if (pinAddButton) pinAddButton.addEventListener('click', async function() {{
    const content = String((pinContent && pinContent.value) || '').trim();
    if (!content) {{ setStatus('attention', 'Write pinned working context before adding it.'); return; }}
    pinAddButton.disabled = true;
    try {{
      const expiresValue = String((pinExpiry && pinExpiry.value) || '').trim();
      await mutateConversationControls('add_pinned_context', {{
        content:content, kind:String((pinKind && pinKind.value) || 'note'), scope:String((pinScope && pinScope.value) || 'current_session'),
        expires_at:expiresValue ? new Date(expiresValue).toISOString() : ''
      }});
      setStatus('ready', 'Pinned working context saved for this conversation.');
      window.location.reload();
    }} catch (_error) {{ setStatus('attention', 'Pinned context could not be saved safely. Nothing else changed.'); }}
    finally {{ pinAddButton.disabled = false; }}
  }});
  if (pinClearButton) pinClearButton.addEventListener('click', async function() {{
    try {{ await mutateConversationControls('clear_pinned_context', {{}}); setStatus('ready', 'Pinned context cleared.'); window.location.reload(); }}
    catch (_error) {{ setStatus('attention', 'Pinned context could not be cleared safely.'); }}
  }});
  if (pinnedList) pinnedList.addEventListener('click', async function(event) {{
    const button = event.target && event.target.closest ? event.target.closest('[data-remove-pin]') : null;
    if (!button) return;
    try {{ await mutateConversationControls('remove_pinned_context', {{item_id:String(button.dataset.removePin || '')}}); setStatus('ready', 'Pinned context removed.'); window.location.reload(); }}
    catch (_error) {{ setStatus('attention', 'The pinned item could not be removed safely.'); }}
  }});
  if (offlineIntentQueue) offlineIntentQueue.addEventListener('click', async function() {{
    try {{
      await mutateConversationControls('queue_offline_intent', {{kind:String((offlineIntentKind && offlineIntentKind.value) || 'send_current_draft'), target_turn_id:String((offlineIntentTurn && offlineIntentTurn.value) || '').trim()}});
      setStatus('offline', 'Operator intent queued for explicit review. It will not execute automatically.');
      window.location.reload();
    }} catch (_error) {{ setStatus('attention', 'The offline intent could not be queued safely. No request was sent.'); }}
  }});
  if (offlineIntentClear) offlineIntentClear.addEventListener('click', async function() {{
    try {{ await mutateConversationControls('clear_offline_intent', {{}}); setStatus('ready', 'Queued operator intent cleared.'); window.location.reload(); }}
    catch (_error) {{ setStatus('attention', 'The queued intent could not be cleared safely.'); }}
  }});
  if (steeringMessage) steeringMessage.addEventListener('input', function() {{ setSessionMutationControlsDisabled(false); }});
  if (steeringButton) steeringButton.addEventListener('click', async function() {{
    const redirect = String((steeringMessage && steeringMessage.value) || '').trim();
    const operationId = String(activeOperationId || '');
    const sessionId = String(sessionBox.value || selectedSessionId || '');
    if (!redirect || !operationId || !sessionId) return;
    steeringButton.disabled = true;
    try {{
      const response = await boundedControlFetch('/api/conversation/steer', {{
        method:'POST', headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{session_id:sessionId, operation_id:operationId, redirect_message:redirect}})
      }}, 8000);
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'steering_request_failed');
      messageBox.value = redirect;
      if (steeringMessage) steeringMessage.value = '';
      scheduleDraftSave();
      setStatus('cancelling', 'Cancellation requested. The redirect is an unsent draft and will require a fresh explicit send.');
    }} catch (error) {{
      setStatus('attention', 'The active response could not be redirected safely. Nothing was resent.');
    }} finally {{
      setSessionMutationControlsDisabled(false);
    }}
  }});
  cancelButton.addEventListener('click', async function() {{
    if (!tabOwnsConversationControl() || !await confirmConversationControl()) {{
      setStatus('attention', 'Another tab controls this turn. No cancellation request was submitted.');
      return;
    }}
    const cancellationLockKey = 'cancel:' + String(activeOperationId || 'none');
    if (!beginCompanionAction(cancellationLockKey, cancelButton)) return;
    cancelButton.disabled = true;
    setStatus('cancelling');
    if (activeOperationId) {{
      const operationToCancel = activeOperationId;
      const cancellationMutationKey = newMutationKey('cancel');
      try {{
        const response = await boundedControlFetch('/api/dashboard-chat/cancel', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(Object.assign({{ operation_id: operationToCancel }}, coordinationMutationFields(cancellationMutationKey))),
          cache: 'no-store'
        }}, 7000);
        const payload = await response.json();
        if (payload.coordination) applyCoordinationState(payload.coordination, {{ reconcile:true }});
        if (!response.ok || payload.ok === false) throw new Error(payload.error || 'cancellation_failed');
        if (payload.status === 'completed') {{
          setStatus('ready', 'The reply completed before cancellation could win.');
        }} else if (payload.status === 'cancellation_requested') {{
          setStatus('cancelling', payload.duplicate_request ? 'Cancellation was already requested for this exact turn.' : 'Cancellation was requested for this exact turn.');
        }}
        announceCoordination('operation_changed', {{ session_id:String(sessionBox.value || ''), operation_id:String(operationToCancel) }});
      }} catch (_error) {{
        setStatus('attention', 'The cancellation request could not be confirmed. No second request was submitted automatically.');
      }}
      pollOperation(operationToCancel);
    }}
    endCompanionAction(cancellationLockKey, cancelButton);
    setSessionMutationControlsDisabled(!sessionIdentityResolved);
    focusComposer();
  }});
}})();
</script>
"""


DASHBOARD_CHAT_DIR = DATA_DIR / "dashboard_chat"
DASHBOARD_CHAT_README = DASHBOARD_CHAT_DIR / "README.md"
_POST_RESPONSE_SIDE_EFFECT_LOCK = threading.RLock()
_DASHBOARD_CHAT_STORAGE_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 44) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return (cleaned or "dashboard-chat")[:max_length].strip("-") or "dashboard-chat"


def _ensure_storage() -> None:
    DASHBOARD_CHAT_DIR.mkdir(parents=True, exist_ok=True)
    if not DASHBOARD_CHAT_README.exists():
        DASHBOARD_CHAT_README.write_text(
            "Saved Dashboard Chat Console turns. Each turn contains Marcus's message, Eidolon's response, and any proposed safe action.\n",
            encoding="utf-8",
        )


def _new_turn_id(message: str) -> str:
    return f"dash_chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{_slug(message, 32)}"


def _turn_path(turn_id: str) -> Path:
    _ensure_storage()
    return DASHBOARD_CHAT_DIR / f"{turn_id}.json"


def save_dashboard_chat_turn(turn: dict[str, Any]) -> None:
    _ensure_storage()
    path = _turn_path(turn["id"])
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
    )
    with _DASHBOARD_CHAT_STORAGE_LOCK:
        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(turn, file, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_dashboard_chat_turns(session_id: str = "") -> list[dict[str, Any]]:
    if not DASHBOARD_CHAT_DIR.exists():
        return []
    turns: list[dict[str, Any]] = []
    for path in DASHBOARD_CHAT_DIR.glob("*.json"):
        data = _load_json_file(path)
        if data and (not session_id or str(data.get("session_id") or "") == str(session_id)):
            turns.append(data)
    return sorted(turns, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_dashboard_chat_turn_id(turn_id: str) -> str:
    token = (turn_id or "").strip()
    lowered = token.lower()
    turns = list_dashboard_chat_turns()
    if lowered in {"latest", "last"}:
        return turns[0].get("id", "") if turns else ""
    return token


def load_dashboard_chat_turn(turn_id: str) -> dict[str, Any] | None:
    resolved = resolve_dashboard_chat_turn_id(turn_id)
    if not resolved:
        return None
    path = _turn_path(resolved)
    if path.exists():
        return _load_json_file(path)
    for turn in list_dashboard_chat_turns():
        if turn.get("id") == resolved:
            return turn
    return None


def _action_history_before_message(session_id: str, message: str) -> list[dict[str, str]]:
    history = conversation_history_for_prompt(session_id, limit=8)
    if history and str(history[-1].get("user_message") or "").strip() == str(message or "").strip():
        return history[:-1]
    return history


def _recent_governed_actions_for_session(session_id: str, *, turn_window: int = 4) -> list[dict[str, Any]]:
    """Return recent distinct session-linked action targets, newest first."""
    turns = conversation_session_turns(session_id)
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for turn in reversed(turns[-max(1, int(turn_window)):]):
        stored = sanitize_action_portal_state(turn.get("operator_action"))
        action_id = str((stored or {}).get("action_id") or "").strip()
        action = load_chat_action(action_id) if action_id else None
        if not action:
            operation_id = str(turn.get("id") or "").strip()
            action = next(
                (item for item in list_chat_actions(include_closed=True) if str(item.get("deduplication_key") or "") == operation_id),
                None,
            )
        target = resolve_follow_up_target(action)
        target_id = str((target or {}).get("id") or "")
        if target and target_id and target_id not in seen:
            seen.add(target_id)
            actions.append(target)
    for item in list_chat_actions(include_closed=True):
        if str(item.get("conversation_session_id") or "") != str(session_id or ""):
            continue
        if str(item.get("status") or "") not in {"proposed", "running", "approval_required"}:
            continue
        target = resolve_follow_up_target(item)
        target_id = str((target or {}).get("id") or "")
        if target and target_id and target_id not in seen:
            seen.add(target_id)
            actions.append(target)
    return actions


def _latest_governed_action_for_session(session_id: str, *, turn_window: int = 4) -> dict[str, Any] | None:
    """Compatibility wrapper for callers that need only the newest session action."""
    actions = _recent_governed_actions_for_session(session_id, turn_window=turn_window)
    return actions[0] if actions else None


def _propose_explicit_chat_action(
    message: str,
    session_id: str,
    *,
    operation_id: str = "",
) -> dict[str, Any] | None:
    if is_candidate_review_installation_control(message) or is_supervised_development_continuation(message):
        return None
    try:
        from conversational_research_actions import parse_conversational_research_request
    except ImportError:
        from conversational_research_actions import parse_conversational_research_request
    if parse_conversational_research_request(message):
        return propose_chat_action(
            message,
            save=True,
            save_unknown=False,
            deduplication_key=operation_id,
            conversation_session_id=session_id,
        )
    history = _action_history_before_message(session_id, message)
    follow_up_kind = classify_chat_action_follow_up(message)
    if follow_up_kind:
        candidates = _recent_governed_actions_for_session(session_id)
        target, resolution = select_follow_up_target(message, candidates)
        if resolution == "ambiguous":
            return propose_ambiguous_chat_action_follow_up(
                message,
                follow_up_kind,
                candidates,
                save=True,
                deduplication_key=operation_id,
                conversation_session_id=session_id,
            )
        follow_up = propose_chat_action_follow_up(
            message,
            target,
            save=True,
            deduplication_key=operation_id,
            conversation_session_id=session_id,
        )
        if follow_up:
            return follow_up
        return None
    if not should_analyze_chat_action(message, history):
        return None
    action = propose_chat_action(
        message,
        save=True,
        save_unknown=False,
        deduplication_key=operation_id,
        conversation_session_id=session_id,
    )
    if action.get("intent") in {"small_talk", "conversation_only"}:
        return None
    if action.get("intent") == "unknown_request":
        return {
            "id": "",
            "status": "unsupported",
            "intent": "unsupported_command",
            "execution_mode": "blocked",
            "risk_level": "unknown",
            "summary": "The request was recognized as operator work but no supported governed capability matched it.",
            "redacted": True,
        }
    return action


def _execute_explicit_safe_chat_action(action: dict[str, Any] | None) -> dict[str, Any] | None:
    """Execute/reconcile one explicitly requested, allowlisted, low-risk action exactly once."""
    if not isinstance(action, dict):
        return None
    allowed_direct_function = bool(
        action.get("execution_mode") == "direct_function"
        and action.get("function_name") in {
            "release_summary",
            "research_session_create",
            "research_session_authorize_execute",
            "research_session_cancel",
            "research_session_status",
            "research_history_list",
            "research_sessions_compare",
            "research_report_export",
        }
    )
    if (
        action.get("execution_mode") not in {"direct_command", ACTION_RETRY, ACTION_CANCEL}
        and not allowed_direct_function
    ) or action.get("risk_level") != "low":
        return None
    if not action.get("id"):
        return None
    execution = execute_chat_action(
        str(action.get("id") or ""),
        dry_run=False,
        timeout_seconds=180,
        claimant="conversation",
    )
    result = execution.result if isinstance(execution.result, dict) else {}
    output = str(
        result.get("message") if allowed_direct_function
        else result.get("stdout") or result.get("stderr") or ""
    ).strip()
    output_limit = (
        MAX_RESEARCH_REPORT_OUTPUT_CHARS
        if str(action.get("intent") or "").startswith("bounded_research_")
        else MAX_GOVERNED_ACTION_OUTPUT_CHARS
    )
    action["status"] = execution.status or action.get("status") or ("executed" if execution.ok else "failed")
    current_action = load_chat_action(str(execution.chat_action_id or action.get("id") or "")) or action
    portal = _live_action_portal(current_action) or build_action_portal_state(current_action, execution.__dict__)
    receipt = build_execution_truth_receipt(current_action)
    receipt_valid, receipt_validation = validate_execution_truth_receipt(receipt, current_action)
    return {
        "ok": bool(execution.ok),
        "action_id": str(execution.chat_action_id or action.get("id") or ""),
        "status": str(execution.status or action.get("status") or ""),
        "message": str(execution.message or execution.error or "Action finished."),
        "output": output[:output_limit],
        "output_truncated": len(output) > output_limit,
        "execution_mode": str(action.get("execution_mode") or "direct_command"),
        "risk_level": "low",
        "target_action_id": str(action.get("target_action_id") or ""),
        "replayed": bool(getattr(execution, "replayed", False)),
        "receipt": public_execution_receipt(receipt),
        "receipt_valid": bool(receipt_valid),
        "receipt_validation": receipt_validation,
        "portal": portal or {},
    }


def _resolve_governed_operator_turn(action: dict[str, Any] | None) -> dict[str, Any] | None:
    """Resolve one recognized operator turn before any conversational provider request."""
    if not isinstance(action, dict):
        return None
    execution = _execute_explicit_safe_chat_action(action)
    current = load_chat_action(str(action.get("id") or "")) if action.get("id") else None
    governed_action = current or action
    receipt = (execution or {}).get("receipt") if isinstance(execution, dict) else build_execution_truth_receipt(governed_action)
    output = str((execution or {}).get("output") or "")
    response = render_receipt_bound_action_response(governed_action, receipt, verified_output=output)
    valid, validation = validate_execution_truth_receipt(receipt, governed_action if governed_action.get("id") else None)
    if (
        valid
        and isinstance(execution, dict)
        and execution.get("ok") is True
        and governed_action.get("intent") == "release_summary"
        and output
    ):
        response = (
            "I completed the requested supervised read-only release inspection, and its receipt verifies success. "
            f"Action ID: {governed_action.get('id')}. {output}"
        )
    elif (
        valid
        and isinstance(execution, dict)
        and execution.get("ok") is True
        and str(governed_action.get("intent") or "").startswith("bounded_research_")
        and output
    ):
        response = output
    portal = (execution or {}).get("portal") if isinstance(execution, dict) else build_action_portal_state(governed_action, governed_action.get("result") if isinstance(governed_action.get("result"), dict) else None)
    resolution = {
        "action": governed_action,
        "execution": execution,
        "receipt": public_execution_receipt(receipt),
        "receipt_valid": bool(valid),
        "receipt_validation": validation,
        "response": response,
        "portal": portal or {},
        "provider_request_count": 0,
        "content_free_evidence": True,
    }
    resolution["outcome"] = _governed_operator_outcome(resolution)
    return resolution


def _governed_operator_outcome(resolution: dict[str, Any]) -> dict[str, Any]:
    """Derive outer turn truth from the validated governed-action receipt."""
    receipt = resolution.get("receipt") if isinstance(resolution.get("receipt"), dict) else {}
    action = resolution.get("action") if isinstance(resolution.get("action"), dict) else {}
    receipt_valid = bool(resolution.get("receipt_valid"))
    action_status = str(action.get("status") or "unsupported").strip().lower()
    completion = str(receipt.get("completion_state") or "").strip().lower() if receipt_valid else ""

    if receipt_valid and completion == "completed" and receipt.get("succeeded") is True:
        return {"success": True, "completion_state": "completed", "failure_category": ""}
    if receipt_valid and completion == "information_only":
        return {"success": True, "completion_state": "information_only", "failure_category": ""}

    state = completion or action_status or "receipt_unavailable"
    if state in {"approval_required", "blocked", "failed", "timed_out", "cancelled", "pending"}:
        completion_state = state
    elif state in {"unsupported", "unsupported_command"}:
        completion_state = "unsupported"
    else:
        completion_state = "receipt_unavailable"
    return {
        "success": False,
        "completion_state": completion_state,
        "failure_category": f"governed_action_{completion_state}",
    }


def _record_governed_operator_session_turn(
    session_id: str,
    operation_id: str,
    message: str,
    resolution: dict[str, Any],
    *,
    streaming: bool,
    source: str,
) -> dict[str, Any]:
    portal = resolution.get("portal") if isinstance(resolution.get("portal"), dict) else {}
    outcome = resolution.get("outcome") if isinstance(resolution.get("outcome"), dict) else _governed_operator_outcome(resolution)
    diagnostic = {
        "redacted": True,
        "operator_routed_before_provider": True,
        "provider_request_count": 0,
        "receipt_present": bool(resolution.get("receipt")),
        "receipt_valid": bool(resolution.get("receipt_valid")),
        "action_status": str(((resolution.get("action") or {}).get("status") if isinstance(resolution.get("action"), dict) else "") or "")[:40],
    }
    return append_conversation_turn(
        session_id,
        turn_id=operation_id,
        user_message=message,
        assistant_response=str(resolution.get("response") or ""),
        completion_state=str(outcome.get("completion_state") or "receipt_unavailable"),
        success=bool(outcome.get("success")),
        provider="",
        model="",
        streaming=streaming,
        source=source,
        diagnostic=diagnostic,
        operator_action=portal,
        continuity_lane="operator",
        relationship_memory_policy="operator_excluded",
    )


def _apply_pre_provider_action_control(action: dict[str, Any] | None) -> dict[str, Any] | None:
    """Apply only a fast pending-action hold before provider generation starts."""
    if not isinstance(action, dict) or action.get("execution_mode") != ACTION_CANCEL:
        return None
    return _execute_explicit_safe_chat_action(action)


def _fallback_response(user_message: str, action: dict[str, Any] | None) -> str:
    if action:
        return (
            "Eidolon: I mapped that to a proposed safe action. "
            f"Intent: {action.get('intent')}. "
            f"Next: inspect the action card and dry-run it before executing."
        )
    return (
        "Eidolon: I saved your message, but I did not generate a local AI response. "
        "The dashboard still created a safe action proposal if the request matched a known workflow."
    )


def create_dashboard_chat_turn(
    user_message: str,
    use_ai: bool = True,
    session_id: str = "",
    *,
    transient_instruction: str = "",
    transient_instruction_scope: str = "current_turn",
) -> dict[str, Any]:
    """
    Creates one dashboard chat turn. Clear supported low-risk operator commands are
    routed through the governed action system before conversational generation;
    ordinary conversation remains provider-driven and action-free.
    """
    message = (user_message or "").strip()
    session = resolve_conversation_session(session_id, create_if_missing=True) or {}
    resolved_session_id = str(session.get("id") or "")
    turn_id = _new_turn_id(message or "empty")
    created_at = _now()

    if not message:
        turn = {
            "id": turn_id,
            "type": "dashboard_chat_turn",
            "created_at": created_at,
            "session_id": resolved_session_id,
            "user_message": "",
            "eidolon_response": "Eidolon: I need an actual message before I can help. Revolutionary, I know.",
            "action_id": "",
            "action": None,
            "error": "Empty message.",
        }
        save_dashboard_chat_turn(turn)
        return turn

    clear_conversation_draft(resolved_session_id, source="dashboard_chat_fallback_acceptance")

    action: dict[str, Any] | None = None
    try:
        action = _propose_explicit_chat_action(message, resolved_session_id, operation_id=turn_id)
    except Exception as error:
        action = {
            "id": "",
            "status": "failed",
            "intent": "action_proposal_failed",
            "summary": f"Could not propose a safe action: {type(error).__name__}",
            "error": type(error).__name__,
        }

    if action:
        governed_started = datetime.now()
        resolution = _resolve_governed_operator_turn(action) or {}
        governed_action = resolution.get("action") if isinstance(resolution.get("action"), dict) else action
        action_execution = resolution.get("execution") if isinstance(resolution.get("execution"), dict) else None
        response = str(resolution.get("response") or "I recognized the operator request, but no governed result is available.")
        response, mixed_intent_presentation = present_mixed_intent_action_response(message, response)
        resolution["response"] = response
        resolution["mixed_intent_presentation"] = mixed_intent_presentation
        outcome = resolution.get("outcome") if isinstance(resolution.get("outcome"), dict) else _governed_operator_outcome(resolution)
        session_turn = _record_governed_operator_session_turn(
            resolved_session_id,
            turn_id,
            message,
            resolution,
            streaming=False,
            source="dashboard_chat_console_governed_action",
        )
        latency = {
            "mode": "governed_action",
            "first_token_ms": int((datetime.now() - governed_started).total_seconds() * 1000),
            "response_complete_ms": int((datetime.now() - governed_started).total_seconds() * 1000),
            "total_ms": int((datetime.now() - governed_started).total_seconds() * 1000),
        }
        runtime_public = {
            "operation_id": turn_id,
            "session_id": resolved_session_id,
            "success": bool(outcome.get("success")),
            "completion_state": str(outcome.get("completion_state") or "receipt_unavailable"),
            "failure_category": str(outcome.get("failure_category") or ""),
            "provider_request_count": 0,
            "session_turn_recorded": True,
            "timings_ms": latency,
            "operator_routed_before_provider": True,
            "execution_receipt": resolution.get("receipt") or {},
        }
        turn = {
            "id": turn_id,
            "type": "dashboard_chat_turn",
            "created_at": created_at,
            "session_id": resolved_session_id,
            "user_message": message,
            "eidolon_response": response,
            "action_id": governed_action.get("id", "") if isinstance(governed_action, dict) else "",
            "action": governed_action,
            "action_execution": action_execution,
            "execution_receipt": resolution.get("receipt") or {},
            "use_ai": use_ai,
            "error": str(outcome.get("failure_category") or ""),
            "latency": latency,
            "completion_state": str(outcome.get("completion_state") or "receipt_unavailable"),
            "conversation_runtime": runtime_public,
            "provider": "",
            "model": "",
        }
        save_dashboard_chat_turn(turn)
        return turn

    pre_provider_action_execution: dict[str, Any] | None = None
    if action and action.get("execution_mode") == ACTION_CANCEL:
        pre_provider_action_execution = _apply_pre_provider_action_control(action)

    runtime_result = run_conversation_turn(
        message,
        source="dashboard_chat_console",
        use_ai=use_ai,
        session_id=resolved_session_id,
        transient_instruction=transient_instruction,
        transient_instruction_scope=transient_instruction_scope,
    )

    action_execution = pre_provider_action_execution or _execute_explicit_safe_chat_action(action)
    _persist_turn_action_portal(resolved_session_id, runtime_result.operation_id, action, action_execution)

    response = runtime_result.display_message or _fallback_response(message, action)
    response_error = "" if runtime_result.success else str(runtime_result.failure_category or "conversation_runtime_failure")


    turn = {
        "id": turn_id,
        "type": "dashboard_chat_turn",
        "created_at": created_at,
        "session_id": resolved_session_id,
        "user_message": message,
        "eidolon_response": response,
        "action_id": action.get("id", "") if action else "",
        "action": action,
        "action_execution": action_execution,
        "use_ai": use_ai,
        "error": response_error,
        "completion_state": runtime_result.completion_state,
        "conversation_runtime": runtime_result.to_dict(include_response=False),
        "provider": runtime_result.provider,
        "model": runtime_result.model,
    }
    save_dashboard_chat_turn(turn)
    return turn



def _save_post_response_side_effects(
    turn_id: str,
    message: str,
    response: str,
    action: dict[str, Any] | None,
) -> str:
    """Run optional reflection bookkeeping once after a committed response."""
    response_error = ""
    marker = str(turn_id or "").strip()
    try:
        with _POST_RESPONSE_SIDE_EFFECT_LOCK:
            existing = [
                memory for memory in load_memories()
                if isinstance(memory, dict)
                and str(memory.get("conversation_side_effect_id") or "") == marker
            ]
            existing_phases = {
                str(memory.get("conversation_side_effect_phase") or memory.get("type") or "").strip().lower()
                for memory in existing
            }
            if {"thought", "reflection"}.issubset(existing_phases):
                return ""
            self_model = load_self_model()
            desires = load_desires()
            memories = load_memories(limit=12)
            current_state = build_chat_state(message)
            current_state["mode"] = "dashboard_chat"
            current_state["chat_action_id"] = action.get("id", "") if action else ""
            thought = generate_inner_thought(
                self_model=self_model,
                desires=desires,
                memories=memories,
                current_state=current_state,
                brain_mode="local_logic",
            )
            reflection = reflect_on_thought(thought, desires)
            pending_items: list[dict[str, Any]] = []
            for phase, item in (("thought", thought), ("reflection", reflection)):
                if isinstance(item, dict):
                    item["conversation_side_effect_id"] = marker
                    item["conversation_operation_id"] = marker
                    item["conversation_side_effect_phase"] = phase
                    item["use_in_conversation"] = False
                    if phase not in existing_phases:
                        pending_items.append(item)
            store_memory_batch(pending_items)
    except Exception as error:
        response_error = response_error or f"Reflection failed: {type(error).__name__}"
    return response_error


def retry_dashboard_chat_turn(
    session_id: str,
    turn_id: str,
    *,
    use_ai: bool = True,
    expected_recovery_cue: str = "",
) -> dict[str, Any]:
    """Retry one failed session turn without duplicating its user memory or actions."""
    recovery_token = str(expected_recovery_cue or "").strip()
    if not recovery_token:
        raise ValueError("This recovery control has no persisted state token. Refresh the conversation before trying again.")
    runtime_result = retry_failed_conversation_turn(
        session_id,
        turn_id,
        use_ai=use_ai,
        source="dashboard_chat_recovery",
        expected_recovery_cue=recovery_token,
    )
    message = ""
    for session_turn in conversation_session_turns(session_id):
        if str(session_turn.get("id") or "") == str(turn_id or ""):
            message = str(session_turn.get("user_message") or "").strip()
            break
    dashboard_turn_id = _new_turn_id(f"retry-{message or turn_id}")
    # A provider retry never proposes or executes the operator action again. The original
    # action remains attached to the original operation and can be reviewed separately.
    action: dict[str, Any] | None = None
    response_error = "" if runtime_result.success else str(runtime_result.failure_category or "conversation_runtime_failure")
    turn = {
        "id": dashboard_turn_id,
        "type": "dashboard_chat_turn",
        "created_at": _now(),
        "session_id": session_id,
        "user_message": message,
        "eidolon_response": runtime_result.display_message,
        "action_id": action.get("id", "") if action else "",
        "action": action,
        "use_ai": use_ai,
        "error": response_error,
        "completion_state": runtime_result.completion_state,
        "conversation_runtime": runtime_result.to_dict(include_response=False),
        "provider": runtime_result.provider,
        "model": runtime_result.model,
        "recovery_of": str(turn_id or ""),
        "recovery_kind": runtime_result.recovery_kind,
    }
    save_dashboard_chat_turn(turn)
    return turn


def stream_dashboard_chat_turn(
    user_message: str,
    use_ai: bool = True,
    cancel_event: threading.Event | None = None,
    session_id: str = "",
    operation_id: str = "",
    draft_already_cleared: bool = False,
    transient_instruction: str = "",
    transient_instruction_scope: str = "current_turn",
):
    """
    Streams a dashboard chat turn as event dictionaries.

    Ordinary conversation streams incrementally. Clear supported low-risk operator
    commands execute only through the governed action system and are summarized from
    a validated receipt before any provider generation. This grants no new authority.
    """
    message = (user_message or "").strip()
    session = resolve_conversation_session(session_id, create_if_missing=True) or {}
    resolved_session_id = str(session.get("id") or "")
    turn_id = _new_turn_id(message or "empty")
    created_at = _now()
    started_at = datetime.now()

    if message and not draft_already_cleared:
        clear_conversation_draft(resolved_session_id, source="dashboard_chat_stream_acceptance")

    if not message:
        turn = {
            "id": turn_id,
            "type": "dashboard_chat_turn",
            "created_at": created_at,
            "session_id": resolved_session_id,
            "user_message": "",
            "eidolon_response": "Eidolon: I need an actual message before I can help. Revolutionary, I know.",
            "action_id": "",
            "action": None,
            "use_ai": use_ai,
            "error": "Empty message.",
            "latency": {"mode": "stream", "error": "empty_message"},
        }
        save_dashboard_chat_turn(turn)
        yield {"event": "delta", "text": turn["eidolon_response"]}
        yield {"event": "done", "turn": turn}
        return

    action: dict[str, Any] | None = None
    try:
        action = _propose_explicit_chat_action(message, resolved_session_id, operation_id=operation_id)
    except Exception as error:
        action = {
            "id": "",
            "status": "failed",
            "intent": "action_proposal_failed",
            "summary": f"Could not propose a safe action: {type(error).__name__}",
            "error": type(error).__name__,
        }
    if action:
        yield {"event": "action", "action": action}
        yield {
            "event": "status",
            "stage": "governed_action",
            "message": "Routing the explicit operator request through the supervised action system before conversational generation.",
        }
        resolution = _resolve_governed_operator_turn(action) or {}
        governed_action = resolution.get("action") if isinstance(resolution.get("action"), dict) else action
        action_execution = resolution.get("execution") if isinstance(resolution.get("execution"), dict) else None
        if action_execution:
            yield {"event": "action_result", "action": governed_action, "execution": action_execution}
        response = str(resolution.get("response") or "I recognized the operator request, but no governed result is available.")
        response, mixed_intent_presentation = present_mixed_intent_action_response(message, response)
        resolution["response"] = response
        resolution["mixed_intent_presentation"] = mixed_intent_presentation
        outcome = resolution.get("outcome") if isinstance(resolution.get("outcome"), dict) else _governed_operator_outcome(resolution)
        governed_operation_id = str(operation_id or turn_id)
        first_visible_at = datetime.now()
        yield {
            "event": "delta",
            "text": response,
            "operation_id": governed_operation_id,
            "trusted_status": True,
            "authoritative_execution_claim": bool(resolution.get("receipt_valid")),
            "timing": {
                "first_visible_token_ms": int((first_visible_at - started_at).total_seconds() * 1000),
                "content_free": True,
            },
        }
        session_turn = _record_governed_operator_session_turn(
            resolved_session_id,
            governed_operation_id,
            message,
            resolution,
            streaming=True,
            source="dashboard_chat_console_stream_governed_action",
        )
        completed_at = datetime.now()
        latency = {
            "mode": "governed_action_stream",
            "first_token_ms": int((first_visible_at - started_at).total_seconds() * 1000),
            "response_complete_ms": int((completed_at - started_at).total_seconds() * 1000),
            "total_ms": int((completed_at - started_at).total_seconds() * 1000),
        }
        runtime_result = {
            "operation_id": governed_operation_id,
            "session_id": resolved_session_id,
            "success": bool(outcome.get("success")),
            "completion_state": str(outcome.get("completion_state") or "receipt_unavailable"),
            "failure_category": str(outcome.get("failure_category") or ""),
            "provider_request_count": 0,
            "session_turn_recorded": True,
            "timings_ms": latency,
            "operator_routed_before_provider": True,
            "execution_receipt": resolution.get("receipt") or {},
        }
        yield {
            "event": "conversation_complete",
            "result": {
                "success": bool(outcome.get("success")),
                "completion_state": str(outcome.get("completion_state") or "receipt_unavailable"),
                "failure_category": str(outcome.get("failure_category") or ""),
                "provider_request_count": 0,
            },
        }
        turn = {
            "id": turn_id,
            "type": "dashboard_chat_turn",
            "created_at": created_at,
            "session_id": resolved_session_id,
            "user_message": message,
            "eidolon_response": response,
            "action_id": governed_action.get("id", "") if isinstance(governed_action, dict) else "",
            "action": governed_action,
            "action_execution": action_execution,
            "execution_receipt": resolution.get("receipt") or {},
            "use_ai": use_ai,
            "error": str(outcome.get("failure_category") or ""),
            "latency": latency,
            "streaming": True,
            "completion_state": str(outcome.get("completion_state") or "receipt_unavailable"),
            "conversation_runtime": runtime_result,
            "provider": "",
            "model": "",
        }
        save_dashboard_chat_turn(turn)
        yield {"event": "saved", "turn_id": turn_id, "latency": latency}
        yield {"event": "done", "turn": turn}
        return

    action_execution: dict[str, Any] | None = None
    if action and action.get("execution_mode") == ACTION_CANCEL:
        yield {"event": "status", "stage": "action_control", "message": "Applying the exact pending-action hold before provider generation."}
        action_execution = _apply_pre_provider_action_control(action)
        if action_execution:
            yield {"event": "action_result", "action": action, "execution": action_execution}

    response_error = ""
    runtime_result: dict[str, Any] | None = None
    for item in stream_conversation_turn(
        message,
        source="dashboard_chat_console_stream",
        use_ai=use_ai,
        cancel_event=cancel_event,
        session_id=resolved_session_id,
        operation_id=operation_id,
        select_session_on_record=False,
        transient_instruction=transient_instruction,
        transient_instruction_scope=transient_instruction_scope,
    ):
        event_name = str(item.get("event") or "message")
        if event_name == "done":
            runtime_result = item.get("result") if isinstance(item.get("result"), dict) else None
            continue
        forwarded = dict(item)
        forwarded["turn_id"] = turn_id
        if event_name == "meta":
            forwarded["created_at"] = created_at
            forwarded["use_ai"] = bool(use_ai)
            forwarded["session_id"] = resolved_session_id
        yield forwarded

    runtime_result = runtime_result or {
        "success": False,
        "completion_state": "failed",
        "display_message": "The conversation runtime ended without a completion result.",
        "failure_category": "missing_runtime_result",
        "timings_ms": {},
    }
    response = str(runtime_result.get("display_message") or runtime_result.get("response") or "").strip()
    response_error = "" if runtime_result.get("success") else str(runtime_result.get("failure_category") or "conversation_runtime_failure")
    finished_response_at = datetime.now()

    yield {
        "event": "conversation_complete",
        "result": {
            key: runtime_result.get(key)
            for key in ("success", "completion_state", "failure_category", "recovery_of", "recovery_kind")
        },
    }

    if action and not action_execution:
        if action.get("execution_mode") == "direct_command" and action.get("risk_level") == "low":
            yield {"event": "status", "stage": "action_execution", "message": "Running the explicitly requested safe system action."}
            action_execution = _execute_explicit_safe_chat_action(action)
            if action_execution:
                yield {"event": "action_result", "action": action, "execution": action_execution}
        elif action.get("execution_mode") == ACTION_RETRY and action.get("risk_level") == "low":
            yield {"event": "status", "stage": "action_retry", "message": "Retrying the exact linked low-risk action once while preserving prior evidence."}
            action_execution = _execute_explicit_safe_chat_action(action)
            if action_execution:
                yield {"event": "action_result", "action": action, "execution": action_execution}
        else:
            yield {"event": "status", "stage": "action_ready", "message": "The supervised action is ready for review."}
    elif not action:
        yield {"event": "status", "stage": "conversation_only", "message": "Conversation complete; no operator action was needed."}

    _persist_turn_action_portal(
        resolved_session_id,
        str(runtime_result.get("operation_id") or ""),
        action,
        action_execution,
    )

    if runtime_result.get("success"):
        side_effect_error = ""
        response_error = response_error or side_effect_error
    completed_at = datetime.now()
    latency = {
        "mode": "stream",
        "first_token_ms": (runtime_result.get("timings_ms") or {}).get("first_token"),
        "response_complete_ms": (runtime_result.get("timings_ms") or {}).get("provider"),
        "total_ms": int((completed_at - started_at).total_seconds() * 1000),
    }
    turn = {
        "id": turn_id,
        "type": "dashboard_chat_turn",
        "created_at": created_at,
        "session_id": resolved_session_id,
        "user_message": message,
        "eidolon_response": response,
        "action_id": action.get("id", "") if action else "",
        "action": action,
        "action_execution": action_execution,
        "use_ai": use_ai,
        "error": response_error,
        "latency": latency,
        "streaming": True,
        "completion_state": runtime_result.get("completion_state"),
        "conversation_runtime": {key: value for key, value in runtime_result.items() if key not in {"response", "display_message", "cognitive_context"}},
        "provider": runtime_result.get("provider"),
        "model": runtime_result.get("model"),
    }
    save_dashboard_chat_turn(turn)
    yield {"event": "saved", "turn_id": turn_id, "latency": latency}
    yield {"event": "done", "turn": turn}

def dashboard_chat_turn_text(turn: dict[str, Any] | None, full: bool = False) -> str:
    if not turn:
        return "Dashboard chat turn not found."

    action = turn.get("action") or {}
    lines = [
        f"# Dashboard Chat Turn: {turn.get('id')}",
        f"Created: {turn.get('created_at')}",
        f"Use AI: {turn.get('use_ai')}",
        "",
        "## Marcus",
        str(turn.get("user_message", "")),
        "",
        "## Eidolon",
        str(turn.get("eidolon_response", "")),
    ]

    if action:
        lines.extend([
            "",
            "## Proposed Action",
            f"Action ID: {turn.get('action_id')}",
            f"Status: {action.get('status')}",
            f"Intent: {action.get('intent')}",
            f"Mode: {action.get('execution_mode')}",
            f"Risk: {action.get('risk_level')}",
            f"Summary: {action.get('summary')}",
            f"Command: {action.get('command') or action.get('approval_command') or '[none]'}",
        ])

    if turn.get("error"):
        lines.extend(["", "## Error", str(turn.get("error"))])

    if full:
        lines.extend(["", "## Raw turn", json.dumps(turn, indent=2, default=str)])

    return "\n".join(lines)
