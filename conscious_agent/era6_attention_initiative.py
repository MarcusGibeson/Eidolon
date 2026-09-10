from __future__ import annotations

"""Integrated Era 6 attention, initiative, and background-cognition boundary.

Composes retained attention/proactive systems with new salience/focus,
background-ticket scheduling, proactive-policy, and resource cooperation.
Portable Browser code prepares and explains work only; it never creates a
native scheduler, launches work, contacts providers, or sends proactive output.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from attention_center import build_attention_center
from attention_salience_focus_v2000 import (
    choose_focus,
    public_focus_state,
    read_focus_state,
    score_salience_candidates,
)
from background_cognition_scheduler_v2000 import read_scheduler_state, scheduler_tick
from proactive_communication import ProactiveCommunicationStore
from proactive_communication_governance_v2000 import batch_queued_messages
from resource_cooperative_governance_v2000 import (
    apply_cooperative_suspension, assess_resource_pressure, public_resource_state, read_resource_state,
)

CONTRACT_VERSION = "v2099.9"

_DENIED = {
    "background_work_executed": False,
    "message_sent": False,
    "provider_contacted": False,
    "process_started": False,
    "tool_executed": False,
    "source_modified": False,
    "memory_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _attention_candidates(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    severity = {"critical": 1.0, "error": 0.88, "warning": 0.62, "info": 0.28}
    kind_importance = {"approval": 0.95, "conversation": 0.80, "provider": 0.78, "task": 0.68, "action": 0.74, "notification": 0.55, "project": 0.48}
    rows: list[dict[str, Any]] = []
    for item in report.get("items", []) if isinstance(report.get("items"), list) else []:
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("id") or "")[:160]
        if not item_id:
            continue
        kind = str(item.get("kind") or "unknown").lower()
        sev = severity.get(str(item.get("severity") or "info").lower(), 0.28)
        requires = bool(item.get("requires_operator"))
        evidence_digest = _digest({
            "id": item_id,
            "kind": kind,
            "status": str(item.get("status") or ""),
            "severity": str(item.get("severity") or ""),
            "created_at": str(item.get("created_at") or ""),
            "related_id": str(item.get("related_id") or ""),
        })
        rows.append({
            "candidate_id": f"attention:{kind}:{_digest(item_id)[:20]}",
            "evidence_digest": evidence_digest,
            "provenance": f"attention_center_{kind}",
            "urgency": max(sev, 0.86 if requires else 0.0),
            "importance": max(kind_importance.get(kind, 0.45), 0.82 if requires else 0.0),
            "novelty": 0.55,
            "emotional_relevance": 0.65 if kind == "conversation" else 0.20,
            "risk": max(sev, 0.75 if kind in {"approval", "provider", "action"} else 0.0),
            "deadline_pressure": 0.40 if kind in {"approval", "task"} else 0.15,
            "operator_priority": 1.0 if requires else 0.35,
            "freshness": 1.0,
            "uncertainty": 0.15 if kind in {"provider", "conversation"} else 0.05,
        })
    return rows


def build_era6_attention_snapshot(
    *, runtime_root: str | Path | None = None, conversation_updates=None,
) -> dict[str, Any]:
    report = build_attention_center(conversation_updates=conversation_updates)
    candidates = _attention_candidates(report)
    salience = score_salience_candidates(candidates, runtime_root=runtime_root)
    focus = public_focus_state(read_focus_state(runtime_root=runtime_root))
    scheduler = read_scheduler_state(runtime_root=runtime_root)
    resource = public_resource_state(read_resource_state(runtime_root=runtime_root))
    proactive = ProactiveCommunicationStore(runtime_root).inspection_summary(message_limit=6, decision_limit=6)
    result = {
        "ok": True,
        "status": "era6_attention_snapshot",
        "contract_version": CONTRACT_VERSION,
        "attention_item_count": len(candidates),
        "salience": salience,
        "focus": focus,
        "scheduler": {
            "enabled": bool(scheduler.get("enabled")),
            "job_count": len(scheduler.get("jobs") or {}),
            "ticket_count": len(scheduler.get("tickets") or []),
            "quiet_start_hour": scheduler.get("quiet_start_hour"),
            "quiet_end_hour": scheduler.get("quiet_end_hour"),
        },
        "proactive": {
            "queued_count": int(proactive.get("queued_count") or 0),
            "unread_count": int(proactive.get("unread_count") or 0),
            "initiative_enabled": bool((proactive.get("preferences") or {}).get("initiative_enabled", True)),
            "quiet_indefinite": bool((proactive.get("preferences") or {}).get("quiet_indefinite", False)),
        },
        "resource": resource,
        "raw_attention_content_exposed": False,
        "private_runtime_content_exposed": False,
        **_DENIED,
    }
    result["snapshot_digest"] = _digest(result)
    return result


def prepare_era6_background_cycle(
    *, cycle_id: str, runtime_root: str | Path | None = None, conversation_updates=None,
    foreground_busy: bool = False, provider_available: bool = True, resource_pressure: str = "normal",
    resource_measurements: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select focus and prepare scheduler tickets, but execute nothing."""
    token = str(cycle_id or "").strip()
    if not token:
        return {"ok": False, "status": "cycle_id_required", **_DENIED}
    report = build_attention_center(conversation_updates=conversation_updates)
    candidates = _attention_candidates(report)
    focus = choose_focus(candidates, event_id=f"{token}:focus", runtime_root=runtime_root)
    resource_assessment = None
    effective_pressure = str(resource_pressure or "normal")
    if isinstance(resource_measurements, Mapping):
        resource_assessment = assess_resource_pressure(resource_measurements, runtime_root=runtime_root)
        mode = str(resource_assessment.get("mode") or "permit")
        effective_pressure = {"permit": "normal", "degrade": "elevated", "suspend": "critical"}.get(mode, "critical")
    tick = scheduler_tick(
        tick_id=f"{token}:scheduler", runtime_root=runtime_root,
        foreground_busy=foreground_busy, provider_available=provider_available,
        resource_pressure=effective_pressure,
    )
    ticket_ids = [str(row.get("ticket_id") or "") for row in tick.get("tickets", []) if isinstance(row, Mapping)]
    resource_application = None
    if resource_assessment is not None:
        resource_application = apply_cooperative_suspension(
            ticket_ids, assessment=resource_assessment, event_id=f"{token}:resource", runtime_root=runtime_root
        )
    result = {
        "ok": bool(focus.get("ok")) and bool(tick.get("ok")),
        "status": "era6_background_cycle_prepared",
        "focus_status": focus.get("status"),
        "focus": focus.get("state"),
        "scheduler_status": tick.get("status"),
        "tickets_prepared": int(tick.get("tickets_prepared") or 0),
        "ticket_ids": ticket_ids,
        "suppression_reasons": list(tick.get("suppression_reasons") or []),
        "resource_mode": str((resource_assessment or {}).get("mode") or "caller_supplied"),
        "resource_assessment_digest": str((resource_assessment or {}).get("assessment_digest") or ""),
        "resource_state_status": str((resource_application or {}).get("status") or "not_applied"),
        "operator_decision_required_for_external_effects": True,
        **_DENIED,
    }
    result["cycle_digest"] = _digest(result)
    return result


def process_era6_attention_control(text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").split())
    low = raw.lower()
    exact = {
        "inspect attention and initiative": "snapshot",
        "show attention and initiative": "snapshot",
        "show background cognition status": "snapshot",
        "inspect background cognition status": "snapshot",
        "show proactive communication queue": "proactive",
        "inspect proactive communication queue": "proactive",
        "show resource budgets": "resource",
        "inspect resource budgets": "resource",
    }
    mode = exact.get(low.rstrip(".!?"))
    if mode is None:
        # Fail closed on compound attempts that start with a recognized read-only control.
        if any(low.startswith(prefix) for prefix in exact):
            return {"active": True, "ok": False, "status": "era6_read_only_scope_expansion_rejected", **_DENIED}
        return {"active": False}
    if mode == "proactive":
        data = batch_queued_messages(runtime_root=runtime_root)
        return {"active": True, **data}
    if mode == "resource":
        state = public_resource_state(read_resource_state(runtime_root=runtime_root))
        return {"active": True, "ok": True, "status": "era6_resource_budgets_inspected", "resource": state, **_DENIED}
    return {"active": True, **build_era6_attention_snapshot(runtime_root=runtime_root)}


__all__ = [
    "CONTRACT_VERSION", "build_era6_attention_snapshot", "prepare_era6_background_cycle",
    "process_era6_attention_control",
]
