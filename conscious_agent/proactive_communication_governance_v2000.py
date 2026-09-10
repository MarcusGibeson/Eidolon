from __future__ import annotations

"""Era 6 proactive-communication policy over the retained v1104 queue.

The retained :class:`ProactiveCommunicationStore` remains the sole message queue
and exactly-once delivery owner.  This layer adds explicit relevance/confidence,
relationship-context, quiet/cooldown and interruption judgment, plus batching
inspection.  It never bypasses the retained queue's delivery claim contract.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from proactive_communication import ProactiveCommunicationStore

CONTRACT_VERSION = "v2075.9"
ACTIONS = ("speak", "wait", "summarize", "remind", "ask")

_DENIED = {
    "delivery_claimed": False,
    "message_delivered": False,
    "provider_contacted": False,
    "action_authorized": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _bounded(value: Any, default: float = 0.0) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return round(default, 4)


def evaluate_communication_candidate(
    candidate: Mapping[str, Any], *, store_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Choose speak/wait/summarize/remind/ask without sending anything."""
    urgency = _bounded(candidate.get("urgency"))
    relevance = _bounded(candidate.get("relevance"))
    confidence = _bounded(candidate.get("confidence"))
    relationship_relevance = _bounded(candidate.get("relationship_relevance"))
    operator_priority = _bounded(candidate.get("operator_priority"))
    ignored_count = max(0, min(20, int(candidate.get("ignored_count") or 0)))
    needs_question = bool(candidate.get("needs_question"))
    completion_summary = bool(candidate.get("completion_summary"))
    reminder_due = bool(candidate.get("reminder_due"))
    snapshot = dict(store_snapshot or {})
    prefs = snapshot.get("preferences") if isinstance(snapshot.get("preferences"), Mapping) else {}
    queued = int(snapshot.get("queued_count") or 0)
    unread = int(snapshot.get("unread_count") or 0)

    blockers: list[str] = []
    if prefs and prefs.get("initiative_enabled") is False:
        blockers.append("initiative_disabled")
    if prefs and prefs.get("quiet_indefinite") is True:
        blockers.append("explicit_quiet")
    if unread > 0:
        blockers.append("prior_message_unread")
    if queued > 0:
        blockers.append("prior_message_queued")
    if ignored_count >= 2 and urgency < 0.9:
        blockers.append("ignored_cue_cooldown")
    if confidence < 0.45 and not needs_question:
        blockers.append("confidence_too_low_for_assertion")
    if relevance < 0.5 and operator_priority < 0.8:
        blockers.append("low_relevance")

    if blockers:
        action = "wait"
    elif reminder_due and max(urgency, operator_priority) >= 0.65:
        action = "remind"
    elif completion_summary and relevance >= 0.6:
        action = "summarize"
    elif needs_question and confidence < 0.75 and relevance >= 0.65:
        action = "ask"
    elif max(urgency, operator_priority) >= 0.75 and relevance >= 0.6:
        action = "speak"
    elif relationship_relevance >= 0.75 and relevance >= 0.7 and confidence >= 0.65:
        action = "speak"
    else:
        action = "wait"
        blockers.append("interruption_value_below_threshold")

    result = {
        "ok": True,
        "status": "communication_policy_evaluated",
        "contract_version": CONTRACT_VERSION,
        "action": action,
        "factors": {
            "urgency": urgency,
            "relevance": relevance,
            "confidence": confidence,
            "relationship_relevance": relationship_relevance,
            "operator_priority": operator_priority,
            "ignored_count": ignored_count,
        },
        "blocker_codes": blockers,
        "silence_is_valid_outcome": True,
        "candidate_content_retained": False,
        **_DENIED,
    }
    result["policy_digest"] = _digest(result)
    return result


def govern_proactive_cycle(
    cycle_result: Mapping[str, Any], *, candidate: Mapping[str, Any], runtime_root: str | Path | None = None,
    tone: str = "thoughtful", relationship_context_refs: Iterable[str] = (), continuation_of: str = "",
    now_epoch: float | None = None,
) -> dict[str, Any]:
    """Evaluate policy, then delegate queueing to the retained exactly-once store.

    No delivery is claimed here.  If policy selects wait, the retained store is
    not mutated.  If policy permits communication, the cycle receipt is copied
    with the retained store's existing ``consider_communication`` signal.
    """
    store = ProactiveCommunicationStore(runtime_root)
    summary = store.inspection_summary()
    policy = evaluate_communication_candidate(candidate, store_snapshot=summary)
    if policy["action"] == "wait":
        return {"ok": True, "status": "proactive_silence_selected", "policy": policy, "queue_mutated": False, **_DENIED}
    receipt = cycle_result.get("receipt") if isinstance(cycle_result.get("receipt"), Mapping) else cycle_result
    if not isinstance(receipt, Mapping):
        return {"ok": False, "status": "cognitive_cycle_receipt_required", "policy": policy, **_DENIED}
    merged = dict(receipt)
    merged["communication_decision"] = "consider_communication"
    merged["communication_reason"] = f"era6_{policy['action']}_policy"
    merged["salience"] = max(float(merged.get("salience") or 0.0), float(policy["factors"]["relevance"]), float(policy["factors"]["urgency"]))
    result = store.consider_cycle(
        {"receipt": merged}, tone=tone, relationship_context_refs=relationship_context_refs,
        continuation_of=continuation_of, now_epoch=now_epoch,
    )
    return {
        "ok": bool(result.get("ok")),
        "status": str(result.get("status") or "proactive_queue_result"),
        "policy": policy,
        "queue_mutated": result.get("status") == "proactive_message_queued",
        "message": result.get("message") if isinstance(result.get("message"), Mapping) else None,
        "idempotent": bool(result.get("idempotent")),
        **_DENIED,
    }


def batch_queued_messages(*, runtime_root: str | Path | None = None, limit: int = 20) -> dict[str, Any]:
    """Return content-minimized review batches from the retained queue."""
    store = ProactiveCommunicationStore(runtime_root)
    rows = store.queued_messages(limit=max(1, min(50, int(limit))))
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = str(row.get("thread_id") or row.get("motivation_id") or row.get("message_id") or "unthreaded")
        groups.setdefault(key, []).append(row)
    batches = []
    for key, items in sorted(groups.items()):
        batches.append({
            "batch_id": f"pb_{_digest(key)[:20]}",
            "thread_digest": _digest(key),
            "message_ids": [str(item.get("message_id") or "") for item in items],
            "message_count": len(items),
            "states": sorted({str(item.get("state") or "") for item in items}),
            "review_required_before_external_delivery": True,
        })
    result = {
        "ok": True,
        "status": "proactive_queue_batched",
        "batch_count": len(batches),
        "batches": batches,
        "raw_message_body_exposed": False,
        "delivery_authorized": False,
        **_DENIED,
    }
    result["batch_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "ACTIONS", "evaluate_communication_candidate", "govern_proactive_cycle", "batch_queued_messages"]
