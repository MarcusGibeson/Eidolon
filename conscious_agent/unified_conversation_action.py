from __future__ import annotations

"""v1287.3-v1287.5 unified conversation/action integration.

Builds one response-time projection over the established v1259 conversational
command path, natural-language action routing, supervised development lifecycle,
and operator progress state.  It never performs a routed action itself.
"""

import hashlib
import json
from typing import Any, Mapping, Sequence

from conversational_command_integration import public_conversational_command_integration
from conversational_command_integration_foundations import DENIED_AUTHORITY
from unified_conversation_action_foundations import (
    classify_unified_conversation_action_turn,
    public_unified_conversation_action_turn,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1287.5"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _bounded_codes(rows: Sequence[Any] | None, limit: int = 12) -> list[str]:
    result: list[str] = []
    for value in list(rows or [])[:limit]:
        if isinstance(value, Mapping):
            token = str(value.get("event_code") or value.get("status") or value.get("state") or "").strip()
        else:
            token = str(value or "").strip()
        if token and token not in result:
            result.append(token[:120])
    return result


def _progress_summary(
    *,
    action_projection: Mapping[str, Any] | None,
    development_lifecycle: Mapping[str, Any] | None,
    operator_snapshot: Mapping[str, Any] | None,
) -> dict[str, Any]:
    action = dict(action_projection or {})
    lifecycle = dict(development_lifecycle or {})
    operator = dict(operator_snapshot or {})
    current = dict(operator.get("current") or {})
    progress = dict(operator.get("progress") or {})
    verification = dict(operator.get("verification") or {})
    known = bool(action or lifecycle or operator)
    return {
        "known": known,
        "action_status": str(action.get("status") or action.get("route_kind") or "unknown") if action else "unknown",
        "development_event": str(lifecycle.get("event") or lifecycle.get("status") or "unknown") if lifecycle else "unknown",
        "session_state": str(current.get("session_state") or "unknown") if current else "unknown",
        "campaign_phase": str(current.get("campaign_phase") or current.get("current_phase") or "unknown") if current else "unknown",
        "event_count": int(progress.get("event_count_total") or 0),
        "failure_count": int(progress.get("failure_count_total") or 0),
        "retry_count": int(progress.get("retry_count_total") or 0),
        "tests_executed_observed": bool(verification.get("tests_executed")) if verification else False,
        "verification_pass_observed": bool(verification.get("passed")) if verification else False,
        "recent_progress_codes": _bounded_codes(progress.get("recent_events") if progress else []),
        "unknown_is_not_failure": True,
        "content_minimized": True,
    }


def build_unified_conversation_action_projection(
    user_text: str,
    *,
    conversational_command_integration: Mapping[str, Any] | None = None,
    action_projection: Mapping[str, Any] | None = None,
    development_lifecycle: Mapping[str, Any] | None = None,
    developer_campaign_projection: Mapping[str, Any] | None = None,
    operator_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    turn = classify_unified_conversation_action_turn(user_text)
    integration = dict(conversational_command_integration or {})
    mode = str(turn.get("turn_mode") or "discussion")
    progress = _progress_summary(
        action_projection=action_projection,
        development_lifecycle=development_lifecycle,
        operator_snapshot=operator_snapshot,
    )

    route_status = {
        "companionship": "conversation_ready",
        "discussion": "conversation_ready",
        "question": "question_ready",
        "planning": "planning_discussion_ready",
        "development_request": "supervised_development_route_ready",
        "progress_request": "progress_projection_ready" if progress["known"] else "progress_unknown",
        "correction": str(integration.get("status") or "existing_correction_route_required"),
        "cancellation": str(integration.get("status") or "existing_cancellation_route_required"),
        "authorization_control": str(integration.get("status") or ("exact_control_passthrough" if turn.get("exact_control_shape") else "exact_authorization_required")),
        "ambiguous_action": "clarification_required",
    }[mode]

    technical_execution_state = {
        "state": "not_inferred_from_user_language",
        "authoritative_execution_evidence_present": bool(
            (action_projection or {}).get("authoritative_result_present")
            or (operator_snapshot or {}).get("verification")
            or (development_lifecycle or {}).get("execution_invoked")
        ),
        "provider_contact_observed": bool((development_lifecycle or {}).get("provider_contacted")),
        "execution_invoked_observed": bool((development_lifecycle or {}).get("execution_invoked")),
        "source_modified_observed": bool((development_lifecycle or {}).get("source_modified")),
        "observation_is_not_authorization": True,
    }

    row = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": route_status,
        "turn": public_unified_conversation_action_turn(turn),
        "turn_mode": mode,
        "route_owner": turn.get("route_owner"),
        "response_obligations": list(turn.get("response_obligations") or []),
        "conversational_command_integration": public_conversational_command_integration(integration) if integration else {},
        "action_projection_present": bool(action_projection),
        "development_lifecycle_present": bool(development_lifecycle),
        "developer_campaign_projection_present": bool(developer_campaign_projection),
        "operator_snapshot_present": bool(operator_snapshot),
        "progress": progress,
        "technical_execution": technical_execution_state,
        "foreground_conversation_preserved": True,
        "parallel_conversation_system_created": False,
        "parallel_execution_engine_created": False,
        "generic_authorization_is_exact_authorization": False,
        "correction_cancellation_reuse_existing_contracts": True,
        "raw_turn_text_exposed": False,
        "raw_operator_content_exposed": False,
        "provider_contacted": False,
        "commands_executed": False,
        "project_modified": False,
        **DENIED_AUTHORITY,
    }
    row["projection_digest"] = _digest({k: v for k, v in row.items() if k != "projection_digest"})
    return row


def unified_conversation_action_prompt(projection: Mapping[str, Any]) -> str:
    mode = str(projection.get("turn_mode") or "discussion")
    status = str(projection.get("status") or "unknown")
    obligations = ", ".join(str(x) for x in list(projection.get("response_obligations") or [])[:4])
    progress = dict(projection.get("progress") or {})
    if mode == "progress_request":
        progress_text = (
            f" known={str(bool(progress.get('known'))).lower()}; session={progress.get('session_state','unknown')};"
            f" phase={progress.get('campaign_phase','unknown')}; failures={int(progress.get('failure_count') or 0)}."
        )
    else:
        progress_text = ""
    return (
        "Unified conversation/action contract: "
        f"mode={mode}; status={status}; obligations={obligations or 'respond to the current turn'}.{progress_text} "
        "Use the existing ordinary-chat/action/development route. Do not infer execution or authorization from conversational language. "
        "Generic approval is never an exact authorization."
    )[:900]


def public_unified_conversation_action_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(value or {})
    row["raw_turn_text_exposed"] = False
    row["raw_operator_content_exposed"] = False
    return row


__all__ = [
    "CONTRACT_VERSION",
    "build_unified_conversation_action_projection",
    "public_unified_conversation_action_projection",
    "unified_conversation_action_prompt",
]
