from __future__ import annotations
"""v2622 content-minimized observability for the developer project queue."""
from typing import Any, Mapping
import hashlib, json

CONTRACT_VERSION = "v2622.0"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def build_project_queue_observability(queue: Mapping[str, Any], readiness: Mapping[str, Any] | None = None) -> dict[str, Any]:
    entries = [e for e in (queue.get("entries") or []) if isinstance(e, Mapping)]
    readiness = readiness if isinstance(readiness, Mapping) else {}
    status_counts = {name: 0 for name in ("selected", "deferred", "blocked", "review")}
    blocker_count = 0
    dependency_count = 0
    for entry in entries:
        status = str(entry.get("status") or "review")
        if status in status_counts:
            status_counts[status] += 1
        blocker_count += len(entry.get("blockers") or [])
        dependency_count += len(entry.get("depends_on") or [])
    ready_ids = [str(x)[:120] for x in readiness.get("ready_project_ids") or []][:32]
    out = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "queue_digest": str(queue.get("queue_digest") or "")[:64],
        "entry_count": len(entries),
        "status_counts": status_counts,
        "ready_count": len(ready_ids),
        "ready_project_ids": ready_ids,
        "next_ready_project_id": str(readiness.get("next_ready_project_id") or "")[:120],
        "blocker_count": blocker_count,
        "dependency_count": dependency_count,
        "queue_persisted": bool(queue.get("queue_persisted")),
        "content_minimized": True,
        "project_content_stored": False,
        "automatic_project_start_permitted": False,
        "queue_mutation_permitted": False,
        "authority_granted": False,
    }
    out["observability_digest"] = _digest(out)
    return out


__all__ = ["CONTRACT_VERSION", "build_project_queue_observability"]
