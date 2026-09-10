from __future__ import annotations

"""v2504.0 unified cognitive-state projection.

Builds one bounded, privacy-safe frame over existing cognitive subsystems. The
frame is a projection only: it does not contact providers, select attention,
create intentions, authorize actions, mutate source, or modify the underlying
subsystem stores.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from belief_revision import build_belief_revision_inspection
from cognitive_continuity import build_cognitive_continuity_inspection
from cognitive_demand_records import build_cognitive_demand_inspection
from cognitive_homeostasis_signals import build_cognitive_homeostasis_signal_inspection
from initiative_arbitration import build_initiative_arbitration_inspection
from prospective_planning import build_prospective_planning_inspection

CONTRACT_VERSION = "v2504.0"
FRAME_SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _bounded(value: Any, default: float = 0.0) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return round(default, 4)


def _recent(rows: Any, limit: int = 8) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return [deepcopy(row) for row in rows[-limit:] if isinstance(row, Mapping)]


def _summarize_homeostasis(value: Mapping[str, Any]) -> dict[str, Any]:
    recent = _recent(value.get("recent_signals"))
    if not recent:
        return {"signal_count": int(value.get("signal_count") or 0), "pressure": 0.0, "fragmentation": 0.0, "recovery_margin": 1.0, "uncertainty": 0.0, "state_counts": deepcopy(value.get("state_counts") or {})}
    row = recent[-1]
    return {
        "signal_count": int(value.get("signal_count") or 0),
        "pressure": _bounded(row.get("load_pressure")),
        "fragmentation": _bounded(row.get("fragmentation")),
        "recovery_margin": _bounded(row.get("recovery_margin"), 1.0),
        "uncertainty": _bounded(row.get("uncertainty")),
        "state_counts": deepcopy(value.get("state_counts") or {}),
    }


def _summarize_demands(value: Mapping[str, Any]) -> dict[str, Any]:
    rows = _recent(value.get("recent_records"), 12)
    candidates = [row for row in rows if row.get("state") == "candidate"]
    candidates.sort(key=lambda row: (_bounded(row.get("urgency")) + _bounded(row.get("importance")) + _bounded(row.get("deadline_pressure")) - _bounded(row.get("cognitive_cost"))), reverse=True)
    return {
        "record_count": int(value.get("record_count") or 0),
        "candidate_count": int(value.get("candidate_count") or 0),
        "top_candidates": [{
            "demand_id": _clean(row.get("demand_id"), 220),
            "origin_type": _clean(row.get("origin_type"), 80),
            "urgency": _bounded(row.get("urgency")),
            "importance": _bounded(row.get("importance")),
            "cost": _bounded(row.get("cognitive_cost")),
            "deadline_pressure": _bounded(row.get("deadline_pressure")),
        } for row in candidates[:5]],
    }


def _summarize_beliefs(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "active_count": int(value.get("active_belief_count") or 0),
        "contested_count": int(value.get("contested_belief_count") or 0),
        "active_conflict_count": int(value.get("active_conflict_count") or 0),
        "recent_commitment_review_count": len(_recent(value.get("recent_commitment_reviews"))),
    }


def _summarize_plans(value: Mapping[str, Any]) -> dict[str, Any]:
    plans = _recent(value.get("active_plans"), 8)
    return {
        "active_count": int(value.get("active_plan_count") or 0),
        "historical_count": int(value.get("historical_plan_count") or 0),
        "proposal_count": int(value.get("proposal_count") or 0),
        "active_plan_ids": [_clean(row.get("plan_id") or row.get("id"), 180) for row in plans if _clean(row.get("plan_id") or row.get("id"), 180)],
    }


def _summarize_continuity(value: Mapping[str, Any]) -> dict[str, Any]:
    subjects = _recent(value.get("subjects"), 10)
    return {
        "mode": _clean(value.get("mode"), 40) or "unknown",
        "active_subject_count": int(value.get("active_subject_count") or 0),
        "due_subject_count": int(value.get("due_subject_count") or 0),
        "subject_refs": [_clean(row.get("subject_id") or row.get("id"), 180) for row in subjects if _clean(row.get("subject_id") or row.get("id"), 180)],
        "recent_consolidation_count": len(_recent(value.get("recent_consolidations"))),
    }


def build_unified_cognitive_state_frame(runtime_root: str | Path | None = None, *, trigger_type: str = "inspection", trigger_ref: str = "") -> dict[str, Any]:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else None
    homeostasis = build_cognitive_homeostasis_signal_inspection(root)
    demands = build_cognitive_demand_inspection(root)
    initiative = build_initiative_arbitration_inspection(root)
    beliefs = build_belief_revision_inspection(root)
    plans = build_prospective_planning_inspection(root)
    continuity = build_cognitive_continuity_inspection(root)

    source_revisions = {
        "homeostasis": int(homeostasis.get("revision") or 0),
        "demands": int(demands.get("revision") or 0),
        "initiative": int(initiative.get("revision") or 0),
        "beliefs": _clean(beliefs.get("updated_at"), 64),
        "plans": int(plans.get("revision") or 0),
        "continuity": _clean(continuity.get("updated_at"), 64),
    }
    projection = {
        "trigger": {"type": _clean(trigger_type, 80), "ref_digest": hashlib.sha256(_clean(trigger_ref, 1000).encode("utf-8")).hexdigest() if trigger_ref else ""},
        "homeostasis": _summarize_homeostasis(homeostasis),
        "demands": _summarize_demands(demands),
        "beliefs": _summarize_beliefs(beliefs),
        "planning": _summarize_plans(plans),
        "continuity": _summarize_continuity(continuity),
        "initiative": {
            "selection_count": int(initiative.get("selection_count") or 0),
            "deliberate_silence_count": int(initiative.get("deliberate_silence_count") or 0),
            "quiet": bool((initiative.get("controls") or {}).get("quiet")),
            "paused": bool((initiative.get("controls") or {}).get("paused")),
            "sleeping": bool((initiative.get("controls") or {}).get("sleeping")),
        },
    }
    frame_id = f"cognitive-frame-{_digest({'projection': projection, 'source_revisions': source_revisions})[:24]}"
    return {
        "ok": True,
        "schema_version": FRAME_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "frame_id": frame_id,
        "created_at": _now(),
        "source_revisions": source_revisions,
        "projection": projection,
        "frame_digest": _digest(projection),
        "read_only": True,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "message_sent": False,
        "external_action_executed": False,
        "source_mutated": False,
        "authority_broadened": False,
        "hidden_reasoning_exposed": False,
        "raw_messages_exposed": False,
    }
