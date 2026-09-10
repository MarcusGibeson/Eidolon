from __future__ import annotations

"""v2533 cognitive observability read model.

Read-only, content-minimized projection over the unified cognitive frame and
mental activity timeline. It exposes operator-facing state transitions and
bounded trends, never hidden reasoning, raw prompts, provider output, tool
arguments, or action authority.
"""

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from mental_activity_timeline_v2511 import EVENT_KINDS, MentalActivityTimeline
from unified_cognitive_state_frame import build_unified_cognitive_state_frame

CONTRACT_VERSION = "v2533.0"
MAX_RECENT = 100


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    base = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return base / "cognition"


def _bounded(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return 0.0


def _frame_summary(frame: Mapping[str, Any]) -> dict[str, Any]:
    home = frame.get("homeostasis") if isinstance(frame.get("homeostasis"), Mapping) else {}
    demands = frame.get("demands") if isinstance(frame.get("demands"), Mapping) else {}
    beliefs = frame.get("beliefs") if isinstance(frame.get("beliefs"), Mapping) else {}
    plans = frame.get("plans") if isinstance(frame.get("plans"), Mapping) else {}
    continuity = frame.get("continuity") if isinstance(frame.get("continuity"), Mapping) else {}
    initiative = frame.get("initiative") if isinstance(frame.get("initiative"), Mapping) else {}
    return {
        "frame_digest": str(frame.get("frame_digest") or ""),
        "observed_at": str(frame.get("observed_at") or frame.get("created_at") or ""),
        "pressure": _bounded(home.get("pressure")),
        "fragmentation": _bounded(home.get("fragmentation")),
        "recovery_margin": _bounded(home.get("recovery_margin")),
        "uncertainty": _bounded(home.get("uncertainty")),
        "active_beliefs": int(beliefs.get("active_count") or 0),
        "belief_conflicts": int(beliefs.get("active_conflict_count") or beliefs.get("contested_count") or 0),
        "active_plans": int(plans.get("active_count") or 0),
        "cognitive_demands": int(demands.get("candidate_count") or 0),
        "active_continuity_subjects": int(continuity.get("active_subject_count") or 0),
        "due_continuity_subjects": int(continuity.get("due_subject_count") or 0),
        "initiative_state": str(initiative.get("state") or initiative.get("mode") or "")[:60],
    }


def build_cognitive_observability_snapshot(
    runtime_root: str | Path | None = None,
    *,
    limit: int = 40,
    kind: str = "",
) -> dict[str, Any]:
    root = _root(runtime_root)
    frame = build_unified_cognitive_state_frame(root, trigger_type="observability", trigger_ref="dashboard")
    timeline = MentalActivityTimeline(root)
    token = str(kind or "").strip().lower()
    if token and token not in EVENT_KINDS:
        raise ValueError("unsupported_event_kind")
    recent = timeline.recent(limit=max(1, min(MAX_RECENT, int(limit or 40))), kind=token)
    events = list(recent.get("events") or [])
    counts = Counter(str(row.get("event_kind") or "") for row in events)
    transitions = Counter(f"{row.get('event_kind')}:{row.get('transition')}" for row in events)
    summaries = [
        {
            "sequence": int(row.get("sequence") or 0),
            "event_kind": str(row.get("event_kind") or "")[:40],
            "transition": str(row.get("transition") or "")[:80],
            "summary": str(row.get("summary") or "")[:180],
            "subject_ref": str(row.get("subject_ref") or "")[:120],
            "outcome_code": str(row.get("outcome_code") or "")[:80],
            "observed_at": str(row.get("observed_at") or "")[:40],
            "timeline_event_digest": str(row.get("timeline_event_digest") or ""),
        }
        for row in events
    ]
    result = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "generated_at": _now(),
        "now": _frame_summary(frame),
        "recent": summaries,
        "recent_count": len(summaries),
        "trends": {
            "event_kind_counts": {name: int(counts.get(name, 0)) for name in sorted(EVENT_KINDS)},
            "top_transitions": [{"transition": name, "count": count} for name, count in transitions.most_common(8)],
        },
        "filters": {"kind": token, "limit": max(1, min(MAX_RECENT, int(limit or 40)))},
        "authority_boundary": {
            "read_only": True,
            "hidden_reasoning_exposed": False,
            "raw_prompt_stored": False,
            "raw_provider_output_stored": False,
            "tool_arguments_stored": False,
            "can_authorize_action": False,
            "can_execute_action": False,
            "can_apply_candidate": False,
        },
    }
    result["snapshot_digest"] = _digest({"now": result["now"], "recent": result["recent"], "trends": result["trends"]})
    from cognitive_observability_signals_v2539 import build_cognitive_observability_signals
    from memory_retrieval_observability_v2576 import load_memory_retrieval_observability
    from memory_retrieval_learning_observability_v2584 import build_memory_retrieval_learning_observability
    result["memory_retrieval"] = load_memory_retrieval_observability(root)
    result["memory_retrieval_learning"] = build_memory_retrieval_learning_observability(root)
    from conversation_context_observability_v2590 import load_conversation_context_observability
    result["conversation_context"] = load_conversation_context_observability(root)
    from response_grounding_learning_observability_v2680 import build_response_grounding_learning_observability
    result["response_grounding_learning"] = build_response_grounding_learning_observability(root)
    from response_grounding_audit_observability_v2686 import load_response_grounding_output_audit_observability
    result["response_grounding_output_audit"] = load_response_grounding_output_audit_observability(root)
    from conversation_target_outcome_history_v2691 import build_conversation_target_learning_profile
    result["conversation_target_learning"] = build_conversation_target_learning_profile(root)
    from conversation_health_v2694 import build_conversation_health
    from conversation_policy_review_v2695 import build_conversation_policy_review_packet
    result["conversation_health"] = build_conversation_health(root)
    result["conversation_policy_review"] = build_conversation_policy_review_packet(result["conversation_health"])
    from conversation_health_history_v2697 import load_conversation_health_history
    from conversation_health_trend_v2698 import build_conversation_health_trend
    result["conversation_health_trend"] = build_conversation_health_trend(load_conversation_health_history(root).get("rows") or [])
    from response_quality_observability_v2705 import build_response_quality_observability
    result["response_quality"] = build_response_quality_observability(root)
    from daily_use_reliability_observability_v2714 import build_daily_use_reliability_observability
    result["daily_use_reliability"] = build_daily_use_reliability_observability(root)
    from combined_trial_campaign_observability_v2727 import build_combined_trial_campaign_observability
    result["combined_trial_campaign"] = build_combined_trial_campaign_observability(root)
    from project_outcome_mind_observability_v2609 import build_project_outcome_mind_observability
    result["project_outcome_learning"] = build_project_outcome_mind_observability(root)
    result["signals"] = build_cognitive_observability_signals(result)
    return deepcopy(result)


__all__ = ["CONTRACT_VERSION", "MAX_RECENT", "build_cognitive_observability_snapshot"]
