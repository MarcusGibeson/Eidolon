from __future__ import annotations
"""v2624 bounded structural history for operator-shaped developer queue transitions."""
from typing import Any, Mapping, Sequence
import hashlib, json

CONTRACT_VERSION = "v2624.0"
VALID = {"selected", "deferred", "blocked", "review"}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def build_queue_transition(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> dict[str, Any]:
    previous = previous if isinstance(previous, Mapping) else {}
    pid = str(current.get("project_id") or "")[:120]
    digest = str(current.get("project_digest") or "")[:64]
    before = str(previous.get("status") or "")
    after = str(current.get("status") or "review")
    if after not in VALID:
        after = "review"
    changed = before != after or str(previous.get("project_digest") or "") != digest
    out = {
        "ok": bool(pid and digest),
        "contract_version": CONTRACT_VERSION,
        "project_id": pid,
        "project_digest": digest,
        "from_status": before if before in VALID else "",
        "to_status": after,
        "changed": changed,
        "blocker_count": len(current.get("blockers") or []),
        "dependency_count": len(current.get("depends_on") or []),
        "content_minimized": True,
        "project_content_stored": False,
        "queue_mutated": False,
        "campaign_started": False,
        "authority_granted": False,
    }
    out["transition_digest"] = _digest(out)
    return out


def build_project_queue_history(transitions: Sequence[Mapping[str, Any]], limit: int = 64) -> dict[str, Any]:
    limit = max(1, min(256, int(limit)))
    rows = []
    for row in transitions[-limit:]:
        if not isinstance(row, Mapping) or not row.get("ok"):
            continue
        rows.append({
            "project_id": str(row.get("project_id") or "")[:120],
            "project_digest": str(row.get("project_digest") or "")[:64],
            "from_status": str(row.get("from_status") or "")[:16],
            "to_status": str(row.get("to_status") or "review")[:16],
            "changed": bool(row.get("changed")),
            "blocker_count": int(row.get("blocker_count") or 0),
            "dependency_count": int(row.get("dependency_count") or 0),
            "transition_digest": str(row.get("transition_digest") or "")[:64],
        })
    out = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "transitions": rows,
        "transition_count": len(rows),
        "content_minimized": True,
        "runtime_persistence_required_from_caller": True,
        "queue_mutated": False,
        "authority_granted": False,
    }
    out["history_digest"] = _digest(out)
    return out


__all__ = ["CONTRACT_VERSION", "build_queue_transition", "build_project_queue_history"]
