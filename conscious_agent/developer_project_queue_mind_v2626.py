from __future__ import annotations
"""v2626 read-only Mind projection for developer project queue state."""
from pathlib import Path
from typing import Any, Mapping
import json, os

try:
    from developer_project_queue_observability_v2622 import build_project_queue_observability
    from developer_project_queue_health_v2625 import build_project_queue_health
except ImportError:
    from developer_project_queue_observability_v2622 import build_project_queue_observability
    from developer_project_queue_health_v2625 import build_project_queue_health

CONTRACT_VERSION = "v2626.0"


def _root(runtime_root=None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    return (Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "development")


def _load(path: Path, default: Mapping[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else dict(default)
    except (OSError, ValueError, TypeError):
        return dict(default)


def build_developer_project_queue_mind_observability(runtime_root=None) -> dict[str, Any]:
    root = _root(runtime_root)
    queue = _load(root / "developer_project_queue.json", {"entries": [], "queue_digest": "", "queue_persisted": False})
    readiness = _load(root / "developer_project_queue_readiness.json", {"projects": [], "ready_project_ids": [], "next_ready_project_id": ""})
    history = _load(root / "developer_project_queue_history.json", {"transitions": [], "history_digest": ""})
    obs = build_project_queue_observability(queue, readiness)
    health = build_project_queue_health(queue, readiness, history)
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "state": "no_queue" if not obs.get("entry_count") else health.get("state", "quiet"),
        "entry_count": int(obs.get("entry_count") or 0),
        "selected_count": int((obs.get("status_counts") or {}).get("selected") or 0),
        "deferred_count": int((obs.get("status_counts") or {}).get("deferred") or 0),
        "blocked_count": int((obs.get("status_counts") or {}).get("blocked") or 0),
        "review_count": int((obs.get("status_counts") or {}).get("review") or 0),
        "ready_count": int(obs.get("ready_count") or 0),
        "next_ready_project_id": str(obs.get("next_ready_project_id") or "")[:120],
        "concerns": list(health.get("concerns") or [])[:8],
        "content_minimized": True,
        "project_content_stored": False,
        "automatic_project_start_permitted": False,
        "automatic_priority_change_permitted": False,
        "queue_mutation_permitted": False,
        "authority_granted": False,
    }


__all__ = ["CONTRACT_VERSION", "build_developer_project_queue_mind_observability"]
