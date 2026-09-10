from __future__ import annotations

"""Read-only v1082.9 daily-use stability checkpoint.

The checkpoint summarizes the local conversation contracts established throughout
v1082 without running generation, replaying requests, changing providers, managing
models, mutating settings, or certifying a release. It is operational state, not a
substitute for the isolated core/full verification reports. A rare case of a status
page declining to appoint itself supreme authority.
"""

from typing import Any, Mapping

from conversation_lifecycle_recovery import lifecycle_recovery_plan
from conversation_offline_durability import offline_session_durability_state
from conversation_sessions import conversation_session_catalog_page
from conversation_turn_presentation import build_turn_presentation
from provider_recovery_evidence import provider_resume_cue
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

DAILY_USE_STABILITY_SCHEMA_VERSION = "1"


def _area(name: str, state: str, detail: str, *, operator_action: str = "none") -> dict[str, Any]:
    return {
        "name": name,
        "state": state,
        "detail": detail,
        "operator_action": operator_action,
    }


def build_daily_use_stability_checkpoint(session_id: str = "") -> dict[str, Any]:
    """Return a bounded content-free summary of the v1082 daily-use contracts."""
    offline = offline_session_durability_state(session_id)
    catalog = conversation_session_catalog_page("", include_archived=True, offset=0, limit=1)
    provider = provider_resume_cue()
    visible_recovery = lifecycle_recovery_plan(
        "focus-recovery",
        hidden=False,
        online=True,
        owns_control=False,
    )
    hidden_recovery = lifecycle_recovery_plan(
        "tab-update",
        hidden=True,
        online=True,
        owns_control=False,
    )
    accepted_state = build_turn_presentation(
        {
            "operation_id": "content-free-checkpoint-operation",
            "accepted_at": "persisted",
            "public_state": "uncertain",
        }
    )
    unaccepted_state = build_turn_presentation(None, non_acceptance={"non_acceptance_proven": True})

    session_state = "ready" if offline.get("session_available") else "ready_without_active_session"
    provider_state = str(provider.get("state") or "unknown")
    generation_state = "ready" if provider.get("generation_available") else provider_state
    areas = [
        _area("session_continuity", session_state, "Local session selection and restoration remain provider-independent."),
        _area("draft_continuity", "ready", "Draft revisions preserve divergent tab edits and require explicit conflict resolution."),
        _area("reading_continuity", "ready", "Turn anchors, unread boundaries, and bounded transcript windows restore without transcript duplication."),
        _area("search_archive", "ready", "Search and archive pages use one lock-consistent catalog revision."),
        _area("browser_navigation", "ready", "Back, Forward, reload, and pageshow restore content-free organizer state."),
        _area("lifecycle_recovery", "ready", "Visible tabs reconcile persisted state; hidden tabs do not start foreground recovery."),
        _area("turn_exactly_once", accepted_state.get("state", "unknown"), "Accepted requests reconcile by persisted operation identity and are never converted into resend eligibility."),
        _area("explicit_resend", unaccepted_state.get("state", "unknown"), "Resend remains operator initiated and requires persisted proof that the original submission was not accepted."),
        _area("action_claim_ownership", "ready", "Cross-process action claims use bounded leases and reject stale-owner completion."),
        _area(
            "provider_generation",
            generation_state,
            str(provider.get("detail") or "Run a bounded readiness check before treating generation as recovered."),
            operator_action="check_configured_provider" if not provider.get("generation_available") else "none",
        ),
    ]
    return {
        "type": "daily_use_stability_checkpoint",
        "schema_version": DAILY_USE_STABILITY_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "checkpoint_status": "runtime_contracts_ready",
        "release_certified": False,
        "verification_required": True,
        "session_id": str(offline.get("session_id") or ""),
        "session_available": bool(offline.get("session_available")),
        "active_session_count": int(offline.get("active_session_count") or 0),
        "archived_session_count": int(offline.get("archived_session_count") or 0),
        "catalog_revision": str(catalog.get("catalog_revision") or ""),
        "catalog_snapshot_consistent": bool(catalog.get("snapshot_consistent")),
        "draft_revision": int(offline.get("draft_revision") or 0),
        "unread_turn_count": int(offline.get("unread_turn_count") or 0),
        "provider_state": provider_state,
        "provider_checked_at": provider.get("checked_at"),
        "provider_recovery_proven": bool(provider.get("recovery_proven")),
        "visible_recovery_reconciles": bool(visible_recovery.get("reconcile_session")),
        "hidden_recovery_reconciles": bool(hidden_recovery.get("reconcile_session")),
        "areas": areas,
        "boundaries": {
            "automatic_generation_retry": False,
            "automatic_resend": False,
            "provider_request_replay": False,
            "provider_switching": False,
            "model_management": False,
            "settings_mutation": False,
            "synthetic_assistant_response": False,
            "unrestricted_shell_execution": False,
            "approval_or_release_authority_changed": False,
            "installation_or_promotion": False,
        },
        "read_only": True,
        "redacted": True,
        "content_free": True,
    }


def daily_use_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "message", "messages", "user_message", "assistant_response", "transcript",
        "prompt", "prompts", "response", "responses", "draft_content", "content",
        "provider_payload", "credentials", "raw_response", "raw_output", "command_output",
        "receipt", "receipts", "model_inventory", "acceptance_key", "claim_token",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
