from __future__ import annotations
"""v2625 advisory health/readiness signals for the developer project queue."""
from typing import Any, Mapping
import hashlib, json

CONTRACT_VERSION = "v2625.0"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def build_project_queue_health(queue: Mapping[str, Any], readiness: Mapping[str, Any], history: Mapping[str, Any] | None = None) -> dict[str, Any]:
    entries = [e for e in queue.get("entries") or [] if isinstance(e, Mapping)]
    projects = [p for p in readiness.get("projects") or [] if isinstance(p, Mapping)]
    selected = [e for e in entries if str(e.get("status") or "") == "selected"]
    blocked_selected = [p for p in projects if str(p.get("status") or "") == "selected" and (p.get("missing_dependencies") or int(p.get("blocker_count") or 0) > 0)]
    ready_ids = [str(x)[:120] for x in readiness.get("ready_project_ids") or []]
    concerns = []
    if selected and not ready_ids:
        concerns.append("selected_work_not_ready")
    if blocked_selected:
        concerns.append("selected_work_blocked")
    if len(ready_ids) > 1:
        concerns.append("multiple_ready_projects_require_operator_choice")
    deferred = sum(1 for e in entries if str(e.get("status") or "") == "deferred")
    if entries and deferred == len(entries):
        concerns.append("all_projects_deferred")
    state = "attention" if concerns else ("ready_for_operator_review" if ready_ids else "quiet")
    out = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "state": state,
        "entry_count": len(entries),
        "selected_count": len(selected),
        "ready_count": len(ready_ids),
        "blocked_selected_count": len(blocked_selected),
        "concerns": concerns[:12],
        "next_ready_project_id": str(readiness.get("next_ready_project_id") or "")[:120],
        "history_digest": str((history or {}).get("history_digest") or "")[:64],
        "health_is_advisory": True,
        "automatic_project_start_permitted": False,
        "automatic_priority_change_permitted": False,
        "queue_mutation_permitted": False,
        "authority_granted": False,
    }
    out["health_digest"] = _digest(out)
    return out


__all__ = ["CONTRACT_VERSION", "build_project_queue_health"]
