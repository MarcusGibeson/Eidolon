from __future__ import annotations

"""Read-only, bounded deliberation over unresolved durable belief conflicts.

This module does not resolve conflicts, contact providers, or authorize actions.
It exposes a small data-only projection for ordinary conversation generation.
"""

from pathlib import Path
from typing import Any, Mapping

try:
    from belief_revision import BeliefRevisionStore
except ImportError:
    from belief_revision import BeliefRevisionStore

CONTRACT_VERSION = "v1152.8"
MAX_CONFLICTS = 2
MAX_OPTIONS = 3
MAX_PROPOSITION_CHARS = 260


def _clean(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _terms(value: str) -> set[str]:
    return {token for token in "".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split() if len(token) >= 3}


def _bounded(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(max(0.0, min(1.0, number)), 4)


def build_belief_deliberation(
    user_message: str,
    *,
    runtime_root: str | Path | None = None,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a content-bounded, non-mutating view of relevant active conflicts."""
    snapshot = dict(state) if isinstance(state, Mapping) else BeliefRevisionStore(runtime_root).snapshot()
    beliefs = {str(row.get("belief_id") or ""): row for row in (snapshot.get("beliefs") or []) if isinstance(row, Mapping)}
    message_terms = _terms(user_message)
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    quarantined = 0
    for conflict in snapshot.get("conflict_sets") or []:
        if not isinstance(conflict, Mapping) or str(conflict.get("status") or "") != "active":
            continue
        conflict_id = _clean(conflict.get("conflict_id"), 120)
        ids = [_clean(value, 120) for value in (conflict.get("belief_ids") or []) if _clean(value, 120)]
        options = []
        for belief_id in ids:
            belief = beliefs.get(belief_id)
            if not isinstance(belief, Mapping):
                continue
            if str(belief.get("lifecycle_state") or "") not in {"active", "contested"}:
                continue
            proposition = _clean(belief.get("proposition"), MAX_PROPOSITION_CHARS)
            if not proposition:
                continue
            options.append({
                "belief_id": belief_id,
                "proposition": proposition,
                "confidence": _bounded(belief.get("confidence"), 0.5),
                "uncertainty": _bounded(belief.get("uncertainty"), 1.0),
                "evidence_count": sum(1 for row in (belief.get("evidence") or []) if isinstance(row, Mapping) and row.get("active")),
            })
        if len(options) < 2:
            quarantined += 1
            continue
        options.sort(key=lambda row: (-row["confidence"], row["uncertainty"], row["belief_id"]))
        overlap = len(message_terms & set().union(*(_terms(row["proposition"]) for row in options))) if message_terms else 0
        margin = round(options[0]["confidence"] - options[1]["confidence"], 4)
        recommendation = "seek_more_evidence" if margin < 0.35 else "mention_provisional_leader_with_uncertainty"
        candidates.append((overlap, conflict_id, {
            "conflict_id": conflict_id,
            "reason_code": _clean(conflict.get("reason_code"), 100),
            "options": options[:MAX_OPTIONS],
            "confidence_margin": margin,
            "recommendation": recommendation,
            "resolution_permitted": False,
            "action_authority": False,
        }))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = [item[2] for item in candidates[:MAX_CONFLICTS] if item[0] > 0 or not message_terms]
    return {
        "contract_version": CONTRACT_VERSION,
        "type": "belief_deliberation",
        "conflict_count": len(selected),
        "conflicts": selected,
        "quarantined_conflict_count": quarantined,
        "read_only": True,
        "provider_contacted": False,
        "resolution_permitted": False,
        "recommended_action": "store_only",
        "operator_authority_required_for_action": True,
        "authority_broadened": False,
    }
