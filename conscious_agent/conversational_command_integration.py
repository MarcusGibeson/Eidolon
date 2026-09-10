from __future__ import annotations

"""v1259.3-v1259.5 ordinary-conversation command integration.

The integration maps v1259 speech acts onto the *existing* development proposal
lifecycle.  It may resolve one unambiguous pending development proposal for an
explicit correction or cancellation.  It never converts generic authorization
("go ahead") into approval/execution authority and it never creates a second
execution engine.
"""

import hashlib
from typing import Any, Iterable, Mapping

from conversational_command_integration_foundations import (
    DENIED_AUTHORITY,
    classify_conversational_command_turn,
    public_conversational_command_turn,
)
from ordinary_chat_development_campaign import (
    _digest,
    cancel_development_campaign_proposal,
    list_development_campaign_proposals,
    load_development_campaign_proposal,
    public_development_campaign_proposal,
    revise_development_campaign_proposal,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1259.5"
_PENDING_STATES = frozenset({"awaiting_approval", "unsupported_request"})


def _session_digest(session_id: str) -> str:
    clean = str(session_id or "").strip()
    return hashlib.sha256(clean.encode("utf-8")).hexdigest() if clean else ""


def _pending_targets(*, session_id: str = "", runtime_root=None) -> list[dict[str, Any]]:
    listed = list_development_campaign_proposals(runtime_root=runtime_root, public=False, limit=50)
    wanted_session = str(session_id or "").strip()
    rows: list[dict[str, Any]] = []
    for row in listed.get("proposals") or []:
        if str(row.get("lifecycle_state") or "") not in _PENDING_STATES:
            continue
        if row.get("approval_consumed"):
            continue
        if wanted_session and str(row.get("session_id") or "") != wanted_session:
            continue
        rows.append({
            "proposal_id": str(row.get("proposal_id") or ""),
            "revision": int(row.get("revision") or 0),
            "revision_digest": str(row.get("revision_digest") or ""),
            "session_digest": str(row.get("session_digest") or ""),
            "request_digest": str(row.get("request_digest") or ""),
            "lifecycle_state": str(row.get("lifecycle_state") or ""),
        })
    return rows


def build_conversational_command_integration(
    user_text: str,
    *,
    action_projection: Mapping[str, Any] | None = None,
    conversation_history: Iterable[Mapping[str, Any]] = (),
    session_id: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    classification = classify_conversational_command_turn(user_text)
    kind = str(classification.get("primary_act") or "discussion")
    targets: list[dict[str, Any]] = []
    status = "conversation_only"
    routing_text = ""
    conversation_text = str(classification.get("conversation_text") or "").strip()
    canonical_control_text = ""
    correction_text = ""
    target = {}
    target_status = "not_required"

    if kind == "action_request" and classification.get("requires_clarification"):
        status = "ambiguous_action_blocked"
        target_status = "clarification_required"
    elif kind == "action_request":
        status = "action_request_routed"
        routing_text = str(classification.get("action_text") or "").strip()
    elif kind == "authorization":
        if classification.get("exact_control_shape"):
            status = "exact_authorization_passthrough"
            routing_text = str(user_text or "").strip()
        else:
            status = "generic_authorization_blocked"
            target_status = "exact_control_required"
    elif kind == "correction" and not classification.get("development_correction_shape"):
        status = "conversation_only"
        target_status = "not_a_development_control"
    elif kind in {"correction", "cancellation"}:
        if classification.get("exact_control_shape"):
            status = "exact_terminal_control_passthrough"
            routing_text = str(user_text or "").strip()
        else:
            targets = _pending_targets(session_id=session_id, runtime_root=runtime_root)
            if len(targets) == 1:
                target = targets[0]
                target_status = "unique_pending_development_proposal"
                if kind == "cancellation":
                    status = "cancellation_target_resolved"
                    canonical_control_text = (
                        f"Cancel development proposal {target['proposal_id']} revision {target['revision']}."
                    )
                else:
                    status = "correction_target_resolved"
                    correction_text = " ".join(str(user_text or "").replace("\x00", " ").split())[:12000]
            else:
                status = f"{kind}_target_ambiguous"
                target_status = "no_pending_target" if not targets else "multiple_pending_targets"
    elif kind == "ambiguous_action":
        status = "ambiguous_action_blocked"
        target_status = "clarification_required"

    projection = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "classification": public_conversational_command_turn(classification),
        "primary_act": kind,
        "routing_text": routing_text,
        "conversation_text": conversation_text,
        "canonical_control_text": canonical_control_text,
        "correction_text": correction_text,
        "target_status": target_status,
        "target_candidate_count": len(targets),
        "target": target,
        "session_digest": _session_digest(session_id),
        "action_projection_digest": str((action_projection or {}).get("projection_digest") or ""),
        "conversation_history_count_bounded": min(sum(1 for _ in conversation_history), 8),
        "raw_conversation_history_stored": False,
        "provider_contacted": False,
        "commands_executed": False,
        "project_modified": False,
        **DENIED_AUTHORITY,
    }
    projection["integration_digest"] = _digest({
        k: v for k, v in projection.items()
        if k not in {"routing_text", "canonical_control_text", "correction_text", "integration_digest"}
    })
    return projection


def public_conversational_command_integration(value: Mapping[str, Any]) -> dict[str, Any]:
    hidden = {"routing_text", "conversation_text", "canonical_control_text", "correction_text", "target"}
    row = {k: v for k, v in dict(value or {}).items() if k not in hidden}
    target = dict(value.get("target") or {})
    if target:
        row["target"] = {
            "proposal_id": target.get("proposal_id", ""),
            "revision": int(target.get("revision") or 0),
            "revision_digest": target.get("revision_digest", ""),
            "request_digest": target.get("request_digest", ""),
            "lifecycle_state": target.get("lifecycle_state", ""),
        }
    row.update({
        "raw_turn_text_exposed": False,
        "conversation_clause_exposed": False,
        "raw_correction_text_exposed": False,
        "raw_control_phrase_exposed": False,
        "private_path_exposed": False,
        "content_minimized": True,
    })
    return row


def _blocked_response(projection: Mapping[str, Any]) -> str:
    status = str(projection.get("status") or "")
    if status == "generic_authorization_blocked":
        return (
            "I understood that as authorization-shaped language, but it does not match an exact existing authorization. "
            "Nothing was approved or executed. Use the exact authorization phrase attached to the reviewed proposal or operation."
        )
    if status == "correction_target_ambiguous":
        return "I understood that as a correction, but there is not exactly one pending development proposal in this conversation to revise. Nothing changed."
    if status == "cancellation_target_ambiguous":
        return "I understood that as a cancellation, but there is not exactly one pending development proposal in this conversation to cancel. Nothing changed."
    if status == "ambiguous_action_blocked":
        return "I found more than one live action in that turn. Name the one action you want handled first; nothing was executed or approved."
    return ""


def process_conversational_development_control(
    user_text: str,
    *,
    session_id: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    """Apply only v1259-safe proposal correction/cancellation consequences.

    Exact existing controls are deliberately passed through to their original
    owners later in ``ordinary_chat_development_campaign``.
    """
    projection = build_conversational_command_integration(
        user_text, session_id=session_id, runtime_root=runtime_root
    )
    status = str(projection.get("status") or "")
    if status in {"conversation_only", "action_request_routed", "exact_authorization_passthrough", "exact_terminal_control_passthrough"}:
        return {"active": False, "event": "inactive", "v1259": public_conversational_command_integration(projection)}
    if status in {"generic_authorization_blocked", "correction_target_ambiguous", "cancellation_target_ambiguous", "ambiguous_action_blocked"}:
        row = {
            "active": True,
            "event": status,
            "conversation_response": _blocked_response(projection),
            "v1259": public_conversational_command_integration(projection),
            "provider_contacted": False,
            "commands_executed": False,
            "source_modified": False,
            **DENIED_AUTHORITY,
        }
        row["public_digest"] = _digest({k: v for k, v in row.items() if k != "conversation_response"})
        return row

    target = dict(projection.get("target") or {})
    proposal_id = str(target.get("proposal_id") or "")
    revision = int(target.get("revision") or 0)
    revision_digest = str(target.get("revision_digest") or "")
    if status == "cancellation_target_resolved":
        outcome = cancel_development_campaign_proposal(
            proposal_id, revision=revision, revision_digest=revision_digest, runtime_root=runtime_root
        )
        ok = outcome.get("status") in {"cancelled", "already_cancelled"}
        row = {
            "active": True,
            "event": "conversational_cancellation_applied" if ok else "conversational_cancellation_blocked",
            **outcome,
            "conversation_response": (
                f"Development proposal {proposal_id} revision {revision} is cancelled. No implementation was started by this cancellation."
                if ok else "That cancellation no longer matches the current pending proposal state, so nothing changed."
            ),
            "v1259": public_conversational_command_integration(projection),
            "provider_contacted": False,
            "commands_executed": False,
            "source_modified": False,
            **DENIED_AUTHORITY,
        }
        row["public_digest"] = _digest({k: v for k, v in row.items() if k != "conversation_response"})
        return row

    if status == "correction_target_resolved":
        current = load_development_campaign_proposal(proposal_id, runtime_root=runtime_root)
        if current.get("status") in {"not_found", "tampered"}:
            return {
                "active": True,
                "event": "conversational_correction_blocked",
                "conversation_response": "The pending development proposal could not be validated, so the correction was not applied.",
                "v1259": public_conversational_command_integration(projection),
                **DENIED_AUTHORITY,
            }
        correction = str(projection.get("correction_text") or "").strip()
        marker = f"Operator correction: {correction}"
        original = str(current.get("request") or "").strip()
        if original.endswith(marker):
            revised = current
            deduplicated = True
        else:
            revised = revise_development_campaign_proposal(
                proposal_id,
                expected_revision=revision,
                request=f"{original} {marker}".strip(),
                runtime_root=runtime_root,
            )
            deduplicated = False
            if revised.get("status") == "stale_save_rejected":
                latest = load_development_campaign_proposal(proposal_id, runtime_root=runtime_root)
                if str(latest.get("request") or "").strip().endswith(marker):
                    revised = latest
                    deduplicated = True
        ok = bool(revised.get("proposal_digest")) and revised.get("status") not in {"stale_save_rejected", "tampered", "not_found"}
        public = public_development_campaign_proposal(revised) if ok else {}
        new_revision = int(revised.get("revision") or revision)
        row = {
            "active": True,
            "event": "conversational_correction_applied" if ok else "conversational_correction_blocked",
            "proposal": public,
            "proposal_id": proposal_id,
            "revision": new_revision,
            "deduplicated": deduplicated,
            "conversation_response": (
                f"I revised development proposal {proposal_id} to revision {new_revision}. The previous revision is stale; review and approve the new exact revision before any implementation."
                if ok else "The correction no longer matches the current pending proposal revision, so nothing changed."
            ),
            "v1259": public_conversational_command_integration(projection),
            "provider_contacted": False,
            "commands_executed": False,
            "source_modified": False,
            **DENIED_AUTHORITY,
        }
        row["public_digest"] = _digest({k: v for k, v in row.items() if k != "conversation_response"})
        return row

    return {"active": False, "event": "inactive", "v1259": public_conversational_command_integration(projection)}


__all__ = [
    "CONTRACT_VERSION",
    "build_conversational_command_integration",
    "process_conversational_development_control",
    "public_conversational_command_integration",
]
