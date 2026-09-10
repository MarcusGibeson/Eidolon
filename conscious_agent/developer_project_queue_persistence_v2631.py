from __future__ import annotations
"""v2631 crash-safe runtime persistence for developer project queue artifacts."""
from pathlib import Path
from typing import Any, Mapping
import hashlib, json, os, tempfile

CONTRACT_VERSION = "v2631.0"
FILES = {
    "queue": "developer_project_queue.json",
    "readiness": "developer_project_queue_readiness.json",
    "history": "developer_project_queue_history.json",
}

def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def _root(runtime_root=None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    base = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return base / "development"

def _atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(dict(value), handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        try: os.unlink(name)
        except FileNotFoundError: pass

def persist_project_queue_state(*, queue: Mapping[str, Any], readiness: Mapping[str, Any], history: Mapping[str, Any], runtime_root=None) -> dict[str, Any]:
    root = _root(runtime_root)
    artifacts = {"queue": dict(queue), "readiness": dict(readiness), "history": dict(history)}
    for key, value in artifacts.items():
        _atomic(root / FILES[key], value)
    receipt = {
        "ok": True, "contract_version": CONTRACT_VERSION,
        "queue_digest": str(queue.get("queue_digest") or _digest(queue))[:64],
        "readiness_digest": str(readiness.get("readiness_digest") or _digest(readiness))[:64],
        "history_digest": str(history.get("history_digest") or _digest(history))[:64],
        "artifact_count": 3, "runtime_only": True, "source_mutated": False,
        "campaign_started": False, "automatic_project_start_permitted": False,
        "authority_granted": False,
    }
    receipt["persistence_digest"] = _digest(receipt)
    _atomic(root / "developer_project_queue_persistence_receipt.json", receipt)
    return receipt

__all__ = ["CONTRACT_VERSION", "persist_project_queue_state"]
