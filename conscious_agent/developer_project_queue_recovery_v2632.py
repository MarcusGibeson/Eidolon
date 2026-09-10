from __future__ import annotations
"""v2632 restart-safe validation/recovery for persisted developer queue state."""
from pathlib import Path
from typing import Any, Mapping
import hashlib, json, os

CONTRACT_VERSION = "v2632.0"

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def _root(runtime_root=None) -> Path:
    if runtime_root is not None: return Path(runtime_root).expanduser().resolve()
    return (Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "development")

def _load(path: Path) -> tuple[dict[str, Any], str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return (value if isinstance(value, dict) else {}, "ok" if isinstance(value, dict) else "invalid_type")
    except FileNotFoundError: return {}, "missing"
    except (OSError, ValueError, TypeError): return {}, "invalid_json"

def recover_project_queue_state(*, runtime_root=None) -> dict[str, Any]:
    root = _root(runtime_root)
    queue, qs = _load(root / "developer_project_queue.json")
    readiness, rs = _load(root / "developer_project_queue_readiness.json")
    history, hs = _load(root / "developer_project_queue_history.json")
    statuses = {"queue": qs, "readiness": rs, "history": hs}
    coherent = all(v == "ok" for v in statuses.values())
    queue_digest = str(queue.get("queue_digest") or "")[:64]
    stale_ready = bool(coherent and readiness.get("queue_digest") and str(readiness.get("queue_digest")) != queue_digest)
    out = {
        "ok": coherent and not stale_ready, "contract_version": CONTRACT_VERSION,
        "load_status": statuses, "queue": queue if coherent else {}, "readiness": readiness if coherent else {},
        "history": history if coherent else {}, "queue_digest": queue_digest,
        "stale_readiness": stale_ready, "operator_review_required": (not coherent) or stale_ready,
        "automatic_repair_permitted": False, "automatic_project_start_permitted": False,
        "queue_mutation_permitted": False, "authority_granted": False,
    }
    out["recovery_digest"] = _digest({k:v for k,v in out.items() if k not in {"queue","readiness","history"}})
    return out

__all__ = ["CONTRACT_VERSION", "recover_project_queue_state"]
