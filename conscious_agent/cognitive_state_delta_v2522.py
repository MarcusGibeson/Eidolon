from __future__ import annotations

"""v2522 bounded structural delta between unified cognitive frames."""

import hashlib, json
from typing import Any, Mapping

CONTRACT_VERSION = "v2522.0"


def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _num(m: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    try: return float(m.get(key, default) or default)
    except (TypeError, ValueError): return default


def compare_cognitive_frames(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(current, Mapping) or not current.get("ok") or not current.get("frame_digest"):
        raise ValueError("valid current frame required")
    p0 = (previous or {}).get("projection") if isinstance((previous or {}).get("projection"), Mapping) else {}
    p1 = current.get("projection") if isinstance(current.get("projection"), Mapping) else {}
    metrics = {
        "pressure": ("homeostasis", "pressure"),
        "uncertainty": ("homeostasis", "uncertainty"),
        "fragmentation": ("homeostasis", "fragmentation"),
        "recovery_margin": ("homeostasis", "recovery_margin"),
        "demand_count": ("demands", "candidate_count"),
        "belief_conflicts": ("beliefs", "active_conflict_count"),
        "contested_beliefs": ("beliefs", "contested_count"),
        "active_plans": ("planning", "active_count"),
        "due_subjects": ("continuity", "due_subject_count"),
    }
    deltas = {}
    meaningful = []
    for name, (section, key) in metrics.items():
        a = p0.get(section) if isinstance(p0.get(section), Mapping) else {}
        b = p1.get(section) if isinstance(p1.get(section), Mapping) else {}
        old, new = _num(a, key), _num(b, key)
        delta = round(new - old, 4)
        deltas[name] = {"previous": round(old,4), "current": round(new,4), "delta": delta}
        threshold = 0.12 if name in {"pressure","uncertainty","fragmentation","recovery_margin"} else 1.0
        if abs(delta) >= threshold:
            meaningful.append(name)
    direction = "stable"
    if meaningful:
        direction = "changed"
    row = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "previous_frame_digest": str((previous or {}).get("frame_digest") or "")[:64],
        "current_frame_digest": str(current.get("frame_digest") or "")[:64],
        "deltas": deltas,
        "meaningful_changes": sorted(meaningful),
        "change_state": direction,
        "raw_content_stored": False,
        "provider_contacted": False,
        "hidden_reasoning_exposed": False,
        "authority_broadened": False,
    }
    row["delta_digest"] = _digest(row)
    return row

__all__ = ["CONTRACT_VERSION", "compare_cognitive_frames"]
