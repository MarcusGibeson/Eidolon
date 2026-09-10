from __future__ import annotations

"""Era 4 memory classification, consolidation and coherent retrieval projection.

This module does not create a second memory store.  It builds a bounded, deterministic
projection over the canonical memory records owned by :mod:`memory`, preserving source
records and provenance while suppressing superseded or weak duplicate alternatives.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1825.9"
MEMORY_CLASSES = (
    "episodic", "semantic", "procedural", "preference", "relationship",
    "project", "correction", "working",
)
MAX_RECORDS = 240
MAX_SELECTED = 96
_PRIVATE_FIELDS = {"private_chain_of_thought", "chain_of_thought", "hidden_reasoning", "provider_payload", "raw_prompt", "raw_provider_response"}
_AUTHORITY_FIELDS = {"approval_granted", "authorized", "execution_permitted", "installation_permitted", "promotion_permitted", "certification_permitted"}
_INACTIVE = {"retracted", "deleted", "rejected", "expired", "blocked"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _text(row: Mapping[str, Any]) -> str:
    return " ".join(str(row.get(k) or "") for k in ("content", "thought", "summary", "title", "name", "description", "value"))[:1800]


def _norm(value: object) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def _time(value: object) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _record_time(row: Mapping[str, Any]) -> datetime | None:
    for key in ("updated_at", "created_at", "timestamp", "occurred_at", "recorded_at"):
        parsed = _time(row.get(key))
        if parsed is not None:
            return parsed
    return None


def classify_memory_record(row: Mapping[str, Any]) -> str:
    explicit = str(row.get("memory_class") or "").strip().lower()
    if explicit in MEMORY_CLASSES:
        return explicit
    kind = " ".join(str(row.get(k) or "").lower() for k in ("type", "category", "source", "kind"))
    if row.get("operator_correction") or row.get("explicit_correction") or row.get("correction_of") or "correction" in kind:
        return "correction"
    if any(token in kind for token in ("preference", "likes", "dislikes", "favorite")) or row.get("preference_key"):
        return "preference"
    if any(token in kind for token in ("relationship", "family", "friend", "partner")) or row.get("relationship_eligible") is True:
        return "relationship"
    if any(token in kind for token in ("project", "release", "codebase", "workspace", "milestone")) or row.get("project_id"):
        return "project"
    if any(token in kind for token in ("procedure", "procedural", "workflow", "how_to", "lesson", "practice")):
        return "procedural"
    if any(token in kind for token in ("working", "temporary", "scratch", "session_state")) or row.get("temporary") is True:
        return "working"
    if any(token in kind for token in ("semantic", "fact", "belief", "knowledge", "concept", "definition")) or row.get("fact_key"):
        return "semantic"
    return "episodic"


def _key(row: Mapping[str, Any], memory_class: str, index: int) -> str:
    for key in ("fact_key", "subject_key", "preference_key", "relationship_key", "entity_key", "project_id", "semantic_subject_key"):
        token = str(row.get(key) or "").strip().casefold()
        if token:
            return f"fact:{key}:{token[:180]}"
    content = _norm(_text(row))
    if content:
        return f"{memory_class}:content:{hashlib.sha256(content.encode()).hexdigest()[:24]}"
    rid = str(row.get("id") or row.get("memory_id") or index)
    return f"{memory_class}:record:{rid[:180]}"


def _record_id(row: Mapping[str, Any], index: int) -> str:
    return str(row.get("id") or row.get("memory_id") or row.get("conversation_turn_id") or f"index:{index}")[:220]


def _provenance(row: Mapping[str, Any]) -> str:
    integ = row.get("provenance_integrity") if isinstance(row.get("provenance_integrity"), Mapping) else {}
    token = str(integ.get("provenance_class") or row.get("provenance_class") or row.get("role") or row.get("source") or "unknown").strip().lower()
    if token in {"user", "operator", "operator_explicit"} or token.startswith("operator_"):
        return "user"
    if token in {"assistant", "eidolon", "generated_turn"}:
        return "assistant"
    if token in {"action_receipt", "execution_receipt", "diagnostic_receipt"}:
        return "action_receipt"
    return token[:80] or "unknown"


def _historical_evidence_eligible(row: Mapping[str, Any]) -> bool | None:
    integrity = row.get("provenance_integrity") if isinstance(row.get("provenance_integrity"), Mapping) else {}
    value = row.get("historical_evidence_eligible")
    if value is None:
        value = integrity.get("historical_evidence_eligible")
    return value if isinstance(value, bool) else None


def _confidence(row: Mapping[str, Any]) -> float:
    value = row.get("confidence", row.get("confidence_score", .5))
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return .5


def _exception(row: Mapping[str, Any]) -> bool:
    return bool(row.get("exception") or row.get("important") or row.get("pinned") or row.get("operator_correction") or row.get("explicit_correction"))


def _polarity(text: str) -> int:
    words = set(_norm(text).split())
    return -1 if words & {"not", "never", "no", "dislike", "hate", "stopped", "quit", "avoid"} else 1


@dataclass(frozen=True)
class MemoryCoherenceDecision:
    record_id: str
    memory_class: str
    group_key: str
    selected: bool
    state: str
    provenance_class: str
    age_days: int | None
    confidence: float
    explicit_exception: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_memory_coherence_projection(message: object, records: object, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    malformed_collection = not isinstance(records, Sequence) or isinstance(records, (str, bytes, bytearray))
    oversized = False
    rows: list[Mapping[str, Any]] = []
    if not malformed_collection:
        oversized = len(records) > MAX_RECORDS
        rows = [row for row in list(records)[:MAX_RECORDS] if isinstance(row, Mapping)]
    query_words = set(_norm(str(message or "")[:4000]).split())
    decisions: list[MemoryCoherenceDecision] = []
    candidates: list[dict[str, Any]] = []
    rejected_private = rejected_authority = inactive = malformed = 0
    nonhistorical = assistant_authored = 0

    for index, row in enumerate(rows):
        status = str(row.get("status") or row.get("curation_state") or "active").strip().lower()
        if status in _INACTIVE or row.get("use_in_conversation") is False:
            inactive += 1
            continue
        if _historical_evidence_eligible(row) is False:
            nonhistorical += 1
            continue
        provenance = _provenance(row)
        if provenance == "assistant":
            assistant_authored += 1
            continue
        if any(key in row for key in _PRIVATE_FIELDS):
            rejected_private += 1
            continue
        if any(key in row and row.get(key) not in {False, None, "", 0} for key in _AUTHORITY_FIELDS):
            rejected_authority += 1
            continue
        text = _text(row)
        if not text and not row.get("id") and not row.get("memory_id"):
            malformed += 1
            continue
        cls = classify_memory_record(row)
        created = _record_time(row)
        age_days = max(0, int((current - created).total_seconds() // 86400)) if created else None
        key = _key(row, cls, index)
        direct = len(query_words & set(_norm(text).split()))
        candidates.append({
            "index": index, "row": dict(row), "record_id": _record_id(row, index), "class": cls,
            "key": key, "time": created, "age_days": age_days, "confidence": _confidence(row),
            "provenance": provenance, "exception": _exception(row), "direct": direct,
            "polarity": _polarity(text), "content_digest": hashlib.sha256(_norm(text).encode()).hexdigest(),
        })

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        groups.setdefault(item["key"], []).append(item)

    selected_indexes: set[int] = set()
    superseded = duplicate = weak_aged = conflict_preserved = 0
    capsules: list[dict[str, Any]] = []
    for key, group in groups.items():
        ordered = sorted(group, key=lambda x: (x["time"] or datetime.min.replace(tzinfo=timezone.utc), x["index"]))
        newest = ordered[-1]
        corrections = [item for item in ordered if item["class"] == "correction" or item["exception"]]
        chosen = corrections[-1] if corrections else newest
        selected_indexes.add(chosen["index"])
        distinct_polarities = {item["polarity"] for item in ordered}
        if len(distinct_polarities) > 1 and not corrections:
            # Without an explicit correction, preserve the newest opposing item as a
            # conflict witness.  An explicit correction instead suppresses superseded
            # alternatives so conversation does not repeat the corrected claim.
            opposing = next((item for item in reversed(ordered) if item["polarity"] != chosen["polarity"]), None)
            if opposing is not None:
                selected_indexes.add(opposing["index"])
                conflict_preserved += 1
        for item in ordered:
            if item["index"] in selected_indexes:
                continue
            if item["content_digest"] == chosen["content_digest"]:
                duplicate += 1
            elif item["age_days"] is not None and item["age_days"] >= 365 and item["confidence"] < .5 and not item["exception"]:
                weak_aged += 1
            else:
                superseded += 1
        capsules.append({
            "group_digest": _digest(key)[:24],
            "memory_class": chosen["class"],
            "member_count": len(ordered),
            "selected_record_digests": [_digest(item["record_id"])[:24] for item in ordered if item["index"] in selected_indexes],
            "provenance_classes": sorted({item["provenance"] for item in ordered}),
            "conflict_preserved": len(distinct_polarities) > 1 and not corrections,
            "contains_explicit_correction": bool(corrections),
            "raw_content_exposed": False,
        })

    selected_items = [item for item in candidates if item["index"] in selected_indexes]
    # Directly relevant unique old memories remain retrievable even when historical.
    selected_items.sort(key=lambda x: (x["direct"], x["exception"], x["time"] or datetime.min.replace(tzinfo=timezone.utc), -x["index"]), reverse=True)
    selected_items = selected_items[:MAX_SELECTED]
    selected_ids = {item["index"] for item in selected_items}
    for item in candidates:
        chosen = item["index"] in selected_ids
        state = "selected"
        if not chosen:
            peers = groups[item["key"]]
            if any(peer["content_digest"] == item["content_digest"] and peer["index"] in selected_indexes for peer in peers):
                state = "duplicate_suppressed"
            elif item["age_days"] is not None and item["age_days"] >= 365 and item["confidence"] < .5 and not item["exception"]:
                state = "weak_aged_suppressed"
            else:
                state = "superseded_suppressed"
        decisions.append(MemoryCoherenceDecision(
            record_id=_digest(item["record_id"])[:24], memory_class=item["class"], group_key=_digest(item["key"])[:24],
            selected=chosen, state=state, provenance_class=item["provenance"], age_days=item["age_days"],
            confidence=round(item["confidence"], 4), explicit_exception=item["exception"],
        ))

    class_counts = {name: sum(1 for item in candidates if item["class"] == name) for name in MEMORY_CLASSES}
    selected_records = [item["row"] for item in selected_items]
    degraded = malformed_collection or oversized or rejected_private or rejected_authority or malformed
    evidence = {
        "contract_version": CONTRACT_VERSION,
        "candidate_count": len(candidates), "selected_count": len(selected_records), "group_count": len(groups),
        "class_counts": class_counts, "duplicate_suppressed_count": duplicate, "superseded_suppressed_count": superseded,
        "weak_aged_suppressed_count": weak_aged, "conflict_exception_preserved_count": conflict_preserved,
        "inactive_suppressed_count": inactive, "private_field_rejected_count": rejected_private,
        "authority_field_rejected_count": rejected_authority, "malformed_count": malformed,
        "nonhistorical_suppressed_count": nonhistorical,
        "assistant_authored_suppressed_count": assistant_authored,
        "malformed_collection": malformed_collection, "oversized_collection": oversized,
        "memory_mutated": False, "second_memory_store_created": False, "provider_contacted": False,
        "contains_memory_text": False, "authority": "none", "integrity": "degraded" if degraded else "valid",
    }
    evidence["evidence_digest"] = _digest(evidence)
    return {
        "ok": not malformed_collection,
        "contract_version": CONTRACT_VERSION,
        "selected_memory_records": selected_records,
        "decisions": [d.to_dict() for d in decisions],
        "capsules": capsules[:MAX_SELECTED],
        "evidence": evidence,
        "authority_boundary": {"can_mutate_memory": False, "can_delete_memory": False, "can_authorize": False, "can_execute": False},
    }


__all__ = ["CONTRACT_VERSION", "MEMORY_CLASSES", "classify_memory_record", "build_memory_coherence_projection"]
