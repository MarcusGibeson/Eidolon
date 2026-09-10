from __future__ import annotations

"""Deterministic, provider-free relationship-memory conflict evidence and reconciliation."""

import hashlib
import re
from dataclasses import dataclass, asdict
from typing import Any, Iterable

from relationship_continuity import is_relationship_memory, relationship_memory_type

SCHEMA_VERSION = "1"
_SINGLETON = {"nickname", "user_mood"}
_NEGATIONS = {"not", "never", "no", "dislike", "hate", "avoid", "stopped", "quit"}
_STOP = {"the","a","an","is","are","was","were","to","of","and","or","my","i","user","likes","like"}


def _text(memory: dict[str, Any]) -> str:
    return " ".join(str(memory.get("content") or memory.get("thought") or memory.get("summary") or "").split())


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def _tokens(text: str) -> set[str]:
    return {t for t in _norm(text).split() if len(t) > 1 and t not in _STOP}


def _digest(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


def _active(memory: dict[str, Any]) -> bool:
    return str(memory.get("status") or "active").lower() not in {"retracted","deleted","rejected","expired","stale","blocked"} and memory.get("use_in_conversation") is not False


def _key(memory: dict[str, Any], index: int) -> str:
    return f"id:{memory.get('id')}" if memory.get("id") else f"legacy:{index}:{_digest(_text(memory))[:16]}"


def _relation(left: dict[str, Any], right: dict[str, Any]) -> tuple[str, float, str]:
    lt, rt = _text(left), _text(right)
    ln, rn = _norm(lt), _norm(rt)
    category = relationship_memory_type(left)
    if ln and ln == rn:
        return "exact_duplicate", 1.0, "normalized_content_match"
    ltok, rtok = _tokens(lt), _tokens(rt)
    union = ltok | rtok
    overlap = len(ltok & rtok) / len(union) if union else 0.0
    lneg = bool(ltok & _NEGATIONS)
    rneg = bool(rtok & _NEGATIONS)
    core_overlap = len((ltok - _NEGATIONS) & (rtok - _NEGATIONS))
    if category in _SINGLETON:
        return "singleton_conflict", overlap, "multiple_active_singleton_records"
    if core_overlap >= 2 and lneg != rneg:
        return "contradiction", overlap, "shared_subject_with_opposed_polarity"
    if overlap >= 0.72:
        return "near_duplicate", overlap, "high_deterministic_token_overlap"
    if category in {"preference", "personal_fact", "relationship", "commitment"} and overlap >= 0.45:
        return "temporal_supersession", overlap, "same_bounded_fact_cluster_with_newer_record"
    return "none", overlap, "insufficient_deterministic_evidence"


def detect_memory_conflicts(memories: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [(i, m) for i, m in enumerate(memories) if isinstance(m, dict) and is_relationship_memory(m) and _active(m)]
    evidence: list[dict[str, Any]] = []
    for pos, (li, left) in enumerate(rows):
        for ri, right in rows[pos + 1:]:
            if relationship_memory_type(left) != relationship_memory_type(right):
                continue
            kind, score, reason = _relation(left, right)
            if kind == "none":
                continue
            older, newer = (left, right)
            older_i, newer_i = li, ri
            if str(left.get("updated_at") or left.get("created_at") or "") > str(right.get("updated_at") or right.get("created_at") or ""):
                older, newer, older_i, newer_i = right, left, ri, li
            token = hashlib.sha256(f"{_key(older, older_i)}\0{_key(newer, newer_i)}\0{kind}".encode()).hexdigest()[:20]
            evidence.append({
                "schema_version": SCHEMA_VERSION,
                "conflict_id": f"memory_conflict_{token}",
                "kind": kind,
                "category": relationship_memory_type(left),
                "record_keys": [_key(older, older_i), _key(newer, newer_i)],
                "older_record_key": _key(older, older_i),
                "newer_record_key": _key(newer, newer_i),
                "confidence": round(score, 3),
                "reason": reason,
                "content_digests": [_digest(_text(older)), _digest(_text(newer))],
                "content_free_evidence": True,
                "provider_invoked": False,
                "automatic_mutation": False,
                "available_actions": ["keep_both", "mark_superseded", "disable_older", "retract_older"],
            })
    return sorted(evidence, key=lambda row: (row["kind"], row["conflict_id"]))


def apply_reconciliation(memories: list[dict[str, Any]], conflict: dict[str, Any], action: str) -> dict[str, Any]:
    """Apply only an explicit operator-selected action; repeated applications are idempotent."""
    action = str(action or "").strip().lower()
    if action not in set(conflict.get("available_actions") or []):
        raise ValueError("Unsupported explicit reconciliation action.")
    older_key = str(conflict.get("older_record_key") or "")
    target = next((m for i, m in enumerate(memories) if _key(m, i) == older_key), None)
    if target is None:
        raise ValueError("Conflict record no longer matches stored memory.")
    marker = {"schema_version": SCHEMA_VERSION, "conflict_id": conflict["conflict_id"], "action": action, "operator_explicit": True, "provider_invoked": False}
    history = target.setdefault("reconciliation_history", [])
    if marker in history:
        return {"ok": True, "changed": False, "status": action, "idempotent_replay": True}
    if action == "mark_superseded":
        target["superseded_by"] = conflict.get("newer_record_key")
        target["use_in_conversation"] = False
        target["relationship_eligible"] = False
    elif action == "disable_older":
        target["curation_state"] = "disabled"; target["use_in_conversation"] = False; target["relationship_eligible"] = False
    elif action == "retract_older":
        target["status"] = "retracted"; target["curation_state"] = "retracted"; target["use_in_conversation"] = False; target["relationship_eligible"] = False
    history.append(marker)
    return {"ok": True, "changed": True, "status": action, "idempotent_replay": False}
