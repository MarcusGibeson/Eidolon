from __future__ import annotations

"""Operator-controlled curation for explicit relationship-continuity memories.

The service never reads session transcripts, invokes a provider, infers a fact,
changes personality, or deletes memory history. Every mutation is an explicit
operator action against the private durable memory store.
"""

import hashlib
import json
import threading
from datetime import datetime
from typing import Any

from memory import load_memories, mutate_memories
from memory_commit_attribution import public_memory_commit_attribution
from relationship_continuity import is_relationship_memory, relationship_memory_type
from important_moment_provenance import build_important_moment_provenance
from conversation_surface_contracts import CURATABLE_RELATIONSHIP_TYPES, RelationshipMemoryCurationError

CURATION_SCHEMA_VERSION = "2"
DELETION_TOMBSTONE_SCHEMA_VERSION = "2"
MAX_CURATED_MEMORY_CHARACTERS = 500
MAX_CURATION_HISTORY = 50
MAX_CORRECTION_LINEAGE = 20

_ALLOWED_IMPORTANCE = {"low", "medium", "high", "critical"}
_RETRACTED_STATUSES = {"retracted", "deleted", "rejected", "expired", "stale", "blocked"}
_EXCLUDED_PRIVACY = {"sensitive", "secret", "restricted"}
_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_content(content: str) -> str:
    text = " ".join(str(content or "").split()).strip()
    if not text:
        raise RelationshipMemoryCurationError("Continuity memory content is required.")
    if len(text) > MAX_CURATED_MEMORY_CHARACTERS:
        raise RelationshipMemoryCurationError(
            f"Continuity memory content must be {MAX_CURATED_MEMORY_CHARACTERS} characters or fewer."
        )
    return text


def _normalize_type(memory_type: str) -> str:
    value = str(memory_type or "").strip().lower()
    if value not in CURATABLE_RELATIONSHIP_TYPES:
        raise RelationshipMemoryCurationError("Unsupported relationship-continuity memory type.")
    return value


def _normalize_importance(importance: str) -> str:
    value = str(importance or "medium").strip().lower()
    return value if value in _ALLOWED_IMPORTANCE else "medium"


def _canonical_digest(memory: dict[str, Any]) -> str:
    encoded = json.dumps(memory, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def relationship_memory_record_key(memory: dict[str, Any], index: int) -> str:
    memory_id = str(memory.get("id") or "").strip()
    if memory_id:
        return f"id:{memory_id}"
    return f"legacy:{index}:{_canonical_digest(memory)}"


def _is_private_or_restricted(memory: dict[str, Any]) -> bool:
    privacy = str(memory.get("privacy") or memory.get("sensitivity") or "").strip().lower()
    return privacy in _EXCLUDED_PRIVACY or memory.get("sensitive") is True


def _curation_state(memory: dict[str, Any]) -> str:
    status = str(memory.get("status") or "").strip().lower()
    if status in _RETRACTED_STATUSES:
        return "retracted"
    if (
        memory.get("use_in_conversation") is False
        or memory.get("relationship_eligible") is False
        or str(memory.get("curation_state") or "").strip().lower() == "disabled"
    ):
        return "disabled"
    return "active"




def _public_provenance(memory: dict[str, Any]) -> dict[str, Any]:
    attribution = public_memory_commit_attribution(
        memory.get("memory_commit_attribution") if isinstance(memory.get("memory_commit_attribution"), dict) else None
    )
    source = str(memory.get("source") or "")[:80]
    if attribution.get("available"):
        return {
            **attribution,
            "source": source,
            "operator_explicit": False,
            "transcript_inferred": False,
        }
    curation_provenance = memory.get("curation_provenance") if isinstance(memory.get("curation_provenance"), dict) else {}
    operator_explicit = source.startswith("operator_relationship_curation") or bool(memory.get("operator_explicit")) or bool(curation_provenance.get("operator_explicit"))
    return {
        "schema_version": "1",
        "available": bool(source),
        "origin": "operator_explicit" if operator_explicit else "legacy_unknown",
        "source": source,
        "operator_explicit": operator_explicit,
        "transcript_inferred": False,
        "provider_invoked": False,
        "content_free_evidence": True,
    }

def _public_record(memory: dict[str, Any], index: int) -> dict[str, Any]:
    category = relationship_memory_type(memory)
    history = memory.get("curation_history") if isinstance(memory.get("curation_history"), list) else []
    return {
        "record_key": relationship_memory_record_key(memory, index),
        "id": str(memory.get("id") or ""),
        "type": str(memory.get("type") or ""),
        "category": category,
        "label": CURATABLE_RELATIONSHIP_TYPES.get(category, category.replace("_", " ").title()),
        "content": str(memory.get("content") or memory.get("thought") or memory.get("summary") or "").strip(),
        "importance": str(memory.get("importance") or "medium"),
        "state": _curation_state(memory),
        "created_at": str(memory.get("created_at") or ""),
        "updated_at": str(memory.get("updated_at") or ""),
        "history_count": len(history),
        "operator_curated": str(memory.get("source") or "").startswith("operator_relationship_curation"),
        "temporal_state": (
            str(memory.get("mood_state") or "current")
            if category == "user_mood"
            else str(memory.get("moment_state") or "open")
            if category == "important_moment"
            else ""
        ),
        "observed_at": str(memory.get("observed_at") or ""),
        "occurred_at": str(memory.get("occurred_at") or ""),
        "superseded_by": str(memory.get("superseded_by") or ""),
        "replaced_by": str(memory.get("replaced_by") or ""),
        "reviewed_at": str(memory.get("reviewed_at") or ""),
        "retention_confirmed": bool(memory.get("retention_confirmed")),
        "provenance": _public_provenance(memory),
        "important_moment_provenance": (build_important_moment_provenance(memory) if category == "important_moment" else {}),
    }


def list_relationship_memory_curation_records(*, include_retracted: bool = True) -> list[dict[str, Any]]:
    """Return safe curatable records without writing or normalizing the store."""
    rows: list[dict[str, Any]] = []
    for index, memory in enumerate(load_memories()):
        if not isinstance(memory, dict) or not is_relationship_memory(memory) or _is_private_or_restricted(memory):
            continue
        row = _public_record(memory, index)
        if not include_retracted and row["state"] == "retracted":
            continue
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            0 if row["state"] == "active" else 1 if row["state"] == "disabled" else 2,
            str(row.get("updated_at") or row.get("created_at") or ""),
            str(row.get("record_key") or ""),
        ),
        reverse=False,
    )


def _find_memory(memories: list[dict[str, Any]], record_key: str) -> tuple[int, dict[str, Any]]:
    token = str(record_key or "").strip()
    if token.startswith("id:"):
        memory_id = token[3:]
        for index, memory in enumerate(memories):
            if isinstance(memory, dict) and str(memory.get("id") or "") == memory_id:
                return index, memory
    elif token.startswith("legacy:"):
        parts = token.split(":", 2)
        if len(parts) == 3 and parts[1].isdigit():
            index = int(parts[1])
            if 0 <= index < len(memories):
                memory = memories[index]
                if isinstance(memory, dict) and _canonical_digest(memory) == parts[2]:
                    return index, memory
    raise RelationshipMemoryCurationError("The selected continuity memory no longer matches the stored record.")


def _history_event(
    action: str,
    *,
    source: str,
    related_memory_id: str = "",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "schema_version": CURATION_SCHEMA_VERSION,
        "action": action,
        "recorded_at": _now(),
        "source": source,
        "operator_explicit": True,
        "provider_invoked": False,
        "transcript_inferred": False,
        "personality_mutated": False,
        "memory_deleted": False,
    }
    if related_memory_id:
        event["related_memory_id"] = str(related_memory_id)[:120]
    if isinstance(details, dict):
        allowed = {
            "previous_content_digest", "new_content_digest", "importance_before", "importance_after",
            "retention_content_digest", "correction_kind",
        }
        event["details"] = {
            key: (str(value)[:120] if not isinstance(value, bool) else value)
            for key, value in details.items() if key in allowed
        }
    return event


def _append_history(memory: dict[str, Any], event: dict[str, Any]) -> None:
    history = memory.get("curation_history") if isinstance(memory.get("curation_history"), list) else []
    history.append(event)
    memory["curation_history"] = history[-MAX_CURATION_HISTORY:]


def _enforce_single_current(
    memories: list[dict[str, Any]],
    *,
    category: str,
    keep_index: int | None,
    keep_id: str,
    timestamp: str,
    source: str,
) -> int:
    """Deactivate only singleton continuity conflicts; never delete their history."""
    changed = 0
    for index, other in enumerate(memories):
        if index == keep_index or not isinstance(other, dict):
            continue
        if relationship_memory_type(other) != category or _is_private_or_restricted(other):
            continue
        if _curation_state(other) != "active":
            continue
        if category == "nickname":
            other["status"] = "active"
            other["curation_state"] = "disabled"
            other["relationship_eligible"] = False
            other["use_in_conversation"] = False
            other["superseded_by"] = keep_id
            action = "superseded_by_new_nickname"
        elif category == "user_mood":
            state = str(other.get("mood_state") or "current").strip().lower()
            if state != "current":
                continue
            other["mood_state"] = "cleared"
            other["replaced_by"] = keep_id
            action = "cleared_for_new_current_mood"
        else:
            continue
        other["updated_at"] = timestamp
        other["curation_schema_version"] = CURATION_SCHEMA_VERSION
        _append_history(other, _history_event(action, source=source, related_memory_id=keep_id))
        memories[index] = other
        changed += 1
    return changed


def create_relationship_memory(
    memory_type: str,
    content: str,
    *,
    importance: str = "medium",
    source: str = "operator_relationship_curation_dashboard",
) -> dict[str, Any]:
    """Create one explicit continuity memory, deduplicating active equivalent facts."""
    category = _normalize_type(memory_type)
    text = _normalize_content(content)
    normalized_importance = _normalize_importance(importance)
    with _LOCK:
        def create(memories: list[dict[str, Any]]) -> dict[str, Any]:
            for index, memory in enumerate(memories):
                if not isinstance(memory, dict) or relationship_memory_type(memory) != category:
                    continue
                existing_text = " ".join(str(memory.get("content") or "").split()).casefold()
                if existing_text == text.casefold() and _curation_state(memory) != "retracted":
                    return {
                        "ok": True,
                        "status": "duplicate",
                        "created": False,
                        "changed": False,
                        "record": _public_record(memory, index),
                        "message": "That continuity memory already exists and was not duplicated.",
                    }
            timestamp = _now()
            digest = hashlib.sha256(f"{category}\0{text}\0{timestamp}".encode("utf-8")).hexdigest()[:10]
            memory_id = f"relationship_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{digest}"
            memory = {
                "id": memory_id,
                "type": category,
                "content": text,
                "importance": normalized_importance,
                "status": "active",
                "curation_state": "active",
                "relationship_eligible": True,
                "use_in_conversation": True,
                "source": source,
                "created_at": timestamp,
                "updated_at": timestamp,
                "curation_schema_version": CURATION_SCHEMA_VERSION,
                "curation_provenance": {
                    "schema_version": "1",
                    "origin": "operator_explicit",
                    "source": source,
                    "recorded_at": timestamp,
                    "operator_explicit": True,
                    "transcript_inferred": False,
                    "provider_invoked": False,
                    "content_free_evidence": True,
                },
                "curation_history": [_history_event("create", source=source)],
            }
            if category == "user_mood":
                memory["mood_state"] = "current"
                memory["observed_at"] = timestamp
            elif category == "important_moment":
                memory["moment_state"] = "open"
                memory["occurred_at"] = timestamp
            singleton_replacements = (
                _enforce_single_current(
                    memories, category=category, keep_index=None, keep_id=memory_id,
                    timestamp=timestamp, source=source,
                )
                if category in {"nickname", "user_mood"}
                else 0
            )
            memories.append(memory)
            return {
                "ok": True,
                "status": "created",
                "created": True,
                "changed": True,
                "record": _public_record(memory, len(memories) - 1),
                "singleton_replacements": singleton_replacements,
                "message": (
                    f"Created {CURATABLE_RELATIONSHIP_TYPES[category].lower()} continuity memory"
                    + (f" and superseded {singleton_replacements} older current record(s)." if singleton_replacements else ".")
                ),
            }

        return mutate_memories(create)


def update_relationship_memory(
    record_key: str,
    action: str,
    *,
    source: str = "operator_relationship_curation_dashboard",
) -> dict[str, Any]:
    """Update one continuity memory without deleting its content or audit history."""
    normalized_action = str(action or "").strip().lower()
    if normalized_action not in {
        "disable", "restore", "retract", "resolve", "reopen", "clear", "make_current", "retain"
    }:
        raise RelationshipMemoryCurationError("Unsupported continuity-memory action.")
    with _LOCK:
        def update(memories: list[dict[str, Any]]) -> dict[str, Any]:
            index, memory = _find_memory(memories, record_key)
            if not is_relationship_memory(memory) or _is_private_or_restricted(memory):
                raise RelationshipMemoryCurationError("The selected memory is not eligible for continuity curation.")
            before = _curation_state(memory)
            category = relationship_memory_type(memory)
            timestamp = _now()

            if normalized_action == "retain":
                if before != "active":
                    raise RelationshipMemoryCurationError("Restore this continuity memory before retaining it.")
                content_digest = hashlib.sha256(
                    str(memory.get("content") or memory.get("thought") or memory.get("summary") or "").encode("utf-8")
                ).hexdigest()
                if memory.get("retention_confirmed") and memory.get("retention_content_digest") == content_digest:
                    return {
                        "ok": True,
                        "status": "active",
                        "created": False,
                        "changed": False,
                        "record": _public_record(memory, index),
                        "message": "Continuity memory retention is already confirmed for this exact content.",
                    }
                memory["retention_confirmed"] = True
                memory["retention_content_digest"] = content_digest
                memory["reviewed_at"] = timestamp
                memory["updated_at"] = timestamp
                memory["curation_schema_version"] = CURATION_SCHEMA_VERSION
                _append_history(memory, _history_event(
                    "retain", source=source, details={"retention_content_digest": content_digest}
                ))
                memories[index] = memory
                return {
                    "ok": True,
                    "status": "active",
                    "created": False,
                    "changed": True,
                    "record": _public_record(memory, index),
                    "message": "Continuity memory retained after explicit operator review.",
                }

            if normalized_action in {"resolve", "reopen"} and category != "important_moment":
                raise RelationshipMemoryCurationError("Only important moments can be resolved or reopened.")
            if normalized_action in {"clear", "make_current"} and category != "user_mood":
                raise RelationshipMemoryCurationError("Only explicit user moods can be cleared or made current.")

            if normalized_action in {"resolve", "reopen", "clear", "make_current"}:
                if before != "active":
                    raise RelationshipMemoryCurationError("Restore this continuity memory before changing its temporal state.")
                field = "moment_state" if category == "important_moment" else "mood_state"
                target = (
                    "resolved" if normalized_action == "resolve"
                    else "open" if normalized_action == "reopen"
                    else "cleared" if normalized_action == "clear"
                    else "current"
                )
                current = str(memory.get(field) or ("open" if field == "moment_state" else "current")).strip().lower()
                if current == target:
                    return {
                        "ok": True,
                        "status": target,
                        "created": False,
                        "changed": False,
                        "record": _public_record(memory, index),
                        "message": f"Continuity memory is already {target}.",
                    }
                memory[field] = target
                if normalized_action == "make_current":
                    memory["observed_at"] = timestamp
                    _enforce_single_current(
                        memories, category="user_mood", keep_index=index,
                        keep_id=str(memory.get("id") or record_key), timestamp=timestamp, source=source,
                    )
                elif normalized_action == "reopen" and not memory.get("occurred_at"):
                    memory["occurred_at"] = timestamp
            else:
                target = "disabled" if normalized_action == "disable" else "retracted" if normalized_action == "retract" else "active"
                if before == target:
                    return {
                        "ok": True,
                        "status": target,
                        "created": False,
                        "changed": False,
                        "record": _public_record(memory, index),
                        "message": f"Continuity memory is already {target}.",
                    }

                if target == "active":
                    memory["status"] = "active"
                    memory["curation_state"] = "active"
                    memory["relationship_eligible"] = True
                    memory["use_in_conversation"] = True
                    memory.pop("superseded_by", None)
                    if category == "nickname":
                        _enforce_single_current(
                            memories, category="nickname", keep_index=index,
                            keep_id=str(memory.get("id") or record_key), timestamp=timestamp, source=source,
                        )
                elif target == "disabled":
                    if str(memory.get("status") or "").strip().lower() in _RETRACTED_STATUSES:
                        memory["status"] = "active"
                    memory["curation_state"] = "disabled"
                    memory["relationship_eligible"] = False
                    memory["use_in_conversation"] = False
                else:
                    memory["status"] = "retracted"
                    memory["curation_state"] = "retracted"
                    memory["relationship_eligible"] = False
                    memory["use_in_conversation"] = False

            memory["updated_at"] = timestamp
            memory["curation_schema_version"] = CURATION_SCHEMA_VERSION
            _append_history(memory, _history_event(normalized_action, source=source))
            memories[index] = memory
            return {
                "ok": True,
                "status": target,
                "created": False,
                "changed": True,
                "record": _public_record(memory, index),
                "message": f"Continuity memory {target}.",
            }

        return mutate_memories(update)



def correct_relationship_memory(
    record_key: str,
    content: str,
    *,
    importance: str = "",
    source: str = "operator_relationship_curation_dashboard",
) -> dict[str, Any]:
    """Correct one active or disabled continuity memory without rewriting transcript history."""
    text = _normalize_content(content)
    with _LOCK:
        def correct(memories: list[dict[str, Any]]) -> dict[str, Any]:
            index, memory = _find_memory(memories, record_key)
            if not is_relationship_memory(memory) or _is_private_or_restricted(memory):
                raise RelationshipMemoryCurationError("The selected memory is not eligible for continuity curation.")
            if _curation_state(memory) == "retracted":
                raise RelationshipMemoryCurationError("Restore this continuity memory before correcting it.")
            old_text = str(memory.get("content") or memory.get("thought") or memory.get("summary") or "").strip()
            old_importance = str(memory.get("importance") or "medium")
            new_importance = _normalize_importance(importance or old_importance)
            if old_text == text and old_importance == new_importance:
                return {
                    "ok": True,
                    "status": _curation_state(memory),
                    "created": False,
                    "changed": False,
                    "record": _public_record(memory, index),
                    "message": "Continuity memory already matches that correction.",
                }
            timestamp = _now()
            previous_digest = hashlib.sha256(old_text.encode("utf-8")).hexdigest()
            new_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            lineage = memory.get("correction_lineage") if isinstance(memory.get("correction_lineage"), list) else []
            lineage.append({
                "schema_version": CURATION_SCHEMA_VERSION,
                "recorded_at": timestamp,
                "operator_explicit": True,
                "previous_content": old_text[:MAX_CURATED_MEMORY_CHARACTERS],
                "previous_content_digest": previous_digest,
                "replacement_content_digest": new_digest,
                "provider_invoked": False,
                "raw_transcript_rewritten": False,
            })
            memory["correction_lineage"] = lineage[-MAX_CORRECTION_LINEAGE:]
            superseded = memory.get("superseded_content_digests") if isinstance(memory.get("superseded_content_digests"), list) else []
            if previous_digest not in superseded:
                superseded.append(previous_digest)
            memory["superseded_content_digests"] = superseded[-MAX_CORRECTION_LINEAGE:]
            memory["content"] = text
            memory.pop("thought", None)
            memory.pop("summary", None)
            memory["importance"] = new_importance
            memory["updated_at"] = timestamp
            memory["reviewed_at"] = timestamp
            memory["retention_confirmed"] = False
            memory.pop("retention_content_digest", None)
            memory["curation_schema_version"] = CURATION_SCHEMA_VERSION
            _append_history(memory, _history_event(
                "correct",
                source=source,
                details={
                    "previous_content_digest": previous_digest,
                    "new_content_digest": new_digest,
                    "importance_before": old_importance,
                    "importance_after": new_importance,
                    "correction_kind": "operator_explicit_content_replacement",
                },
            ))
            memories[index] = memory
            return {
                "ok": True,
                "status": _curation_state(memory),
                "created": False,
                "changed": True,
                "record": _public_record(memory, index),
                "message": "Continuity memory corrected after explicit operator review.",
                "raw_conversation_history_changed": False,
            }

        return mutate_memories(correct)

def _record_key_digest(record_key: str) -> str:
    return hashlib.sha256(str(record_key or "").strip().encode("utf-8")).hexdigest()


def _find_deletion_tombstone(memories: list[dict[str, Any]], record_key: str) -> dict[str, Any] | None:
    digest = _record_key_digest(record_key)
    return next(
        (
            memory for memory in memories
            if isinstance(memory, dict)
            and memory.get("type") == "relationship_memory_deletion_tombstone"
            and str(memory.get("deleted_record_key_digest") or "") == digest
        ),
        None,
    )


def delete_retracted_relationship_memory(
    record_key: str,
    confirmation: str,
    *,
    source: str = "operator_relationship_curation_dashboard",
) -> dict[str, Any]:
    """Delete only retracted content after verified or honestly unavailable vector cleanup."""
    if str(confirmation or "").strip() != "DELETE":
        raise RelationshipMemoryCurationError("Type DELETE to permanently remove this retracted continuity memory.")
    with _LOCK:
        def delete(memories: list[dict[str, Any]]) -> dict[str, Any]:
            existing_tombstone = _find_deletion_tombstone(memories, record_key)
            if existing_tombstone is not None:
                return {
                    "ok": True,
                    "status": "deleted",
                    "created": False,
                    "changed": False,
                    "record_key": record_key,
                    "message": "Retracted continuity memory was already permanently deleted.",
                    "content_removed": True,
                    "tombstone_retained": True,
                    "vector_cleanup": dict(existing_tombstone.get("vector_cleanup") or {}),
                    "idempotent_replay": True,
                }

            index, memory = _find_memory(memories, record_key)
            if not is_relationship_memory(memory) or _is_private_or_restricted(memory):
                raise RelationshipMemoryCurationError("The selected memory is not eligible for continuity curation.")
            if _curation_state(memory) != "retracted":
                raise RelationshipMemoryCurationError("Only a retracted continuity memory can be permanently deleted.")

            memory_id = str(memory.get("id") or "").strip()
            from vector_memory import delete_memory_vector_verified
            cleanup = delete_memory_vector_verified(memory_id)
            if not bool(cleanup.get("cleanup_complete")):
                raise RelationshipMemoryCurationError(
                    "The semantic-memory copy could not be verified as removed, so the continuity memory was left unchanged."
                )

            timestamp = _now()
            record_key_digest = _record_key_digest(record_key)
            tombstone_id = hashlib.sha256(
                f"{record_key_digest}\0{timestamp}\0{source}".encode("utf-8")
            ).hexdigest()[:16]
            memory_id_digest = hashlib.sha256(memory_id.encode("utf-8")).hexdigest() if memory_id else ""
            vector_cleanup = {
                "schema_version": "1",
                "cleanup_complete": True,
                "deletion_attempted": bool(cleanup.get("deletion_attempted")),
                "verification_status": str(cleanup.get("verification_status") or "")[:80],
                "verified_absent": bool(cleanup.get("verified_absent")),
                "semantic_store_available": bool(cleanup.get("semantic_store_available")),
                "memory_id_digest": memory_id_digest,
                "completed_at": timestamp,
                "provider_invoked": False,
                "content_free": True,
            }
            memories[index] = {
                "id": f"relationship_memory_deletion_{tombstone_id}",
                "type": "relationship_memory_deletion_tombstone",
                "schema_version": DELETION_TOMBSTONE_SCHEMA_VERSION,
                "status": "deleted",
                "deleted_memory_id": memory_id,
                "deleted_memory_id_digest": memory_id_digest,
                "deleted_record_key_digest": record_key_digest,
                "deleted_category": relationship_memory_type(memory),
                "deleted_at": timestamp,
                "source": source,
                "operator_explicit": True,
                "confirmation_consumed": True,
                "content_removed": True,
                "use_in_conversation": False,
                "relationship_eligible": False,
                "provider_invoked": False,
                "personality_mutated": False,
                "vector_cleanup": vector_cleanup,
            }
            return {
                "ok": True,
                "status": "deleted",
                "created": False,
                "changed": True,
                "record_key": record_key,
                "message": "Retracted continuity memory permanently deleted after semantic cleanup verification.",
                "content_removed": True,
                "tombstone_retained": True,
                "vector_cleanup": vector_cleanup,
                "idempotent_replay": False,
            }

        return mutate_memories(delete)


def relationship_memory_deletion_integrity_summary() -> dict[str, Any]:
    """Return a read-only, content-free view of permanent-deletion evidence."""
    tombstones = [
        memory for memory in load_memories()
        if isinstance(memory, dict) and memory.get("type") == "relationship_memory_deletion_tombstone"
    ]
    verified_absent = sum(
        1 for memory in tombstones
        if bool((memory.get("vector_cleanup") or {}).get("verified_absent"))
    )
    unavailable = sum(
        1 for memory in tombstones
        if str((memory.get("vector_cleanup") or {}).get("verification_status") or "") == "semantic_store_unavailable"
    )
    incomplete = sum(
        1 for memory in tombstones
        if not bool((memory.get("vector_cleanup") or {}).get("cleanup_complete"))
    )
    return {
        "schema_version": DELETION_TOMBSTONE_SCHEMA_VERSION,
        "tombstone_count": len(tombstones),
        "vector_verified_absent": verified_absent,
        "semantic_store_unavailable": unavailable,
        "incomplete_cleanup": incomplete,
        "content_free_tombstones": all("content" not in memory and "thought" not in memory and "summary" not in memory for memory in tombstones),
        "repeated_cleanup_idempotent": True,
        "restart_recovery_supported": True,
        "provider_invocation": False,
        "writes_on_read": False,
    }

def relationship_memory_curation_summary() -> dict[str, Any]:
    records = list_relationship_memory_curation_records(include_retracted=True)
    deletion_integrity = relationship_memory_deletion_integrity_summary()
    counts = {"active": 0, "disabled": 0, "retracted": 0}
    for record in records:
        counts[record["state"]] = counts.get(record["state"], 0) + 1
    active_nicknames = [row for row in records if row.get("category") == "nickname" and row.get("state") == "active"]
    current_moods = [
        row for row in records
        if row.get("category") == "user_mood" and row.get("state") == "active" and row.get("temporal_state") == "current"
    ]
    singleton_conflicts = max(0, len(active_nicknames) - 1) + max(0, len(current_moods) - 1)
    return {
        "schema_version": CURATION_SCHEMA_VERSION,
        "record_count": len(records),
        "counts": counts,
        "singleton_conflicts": singleton_conflicts,
        "single_current_nickname": True,
        "single_current_user_mood": True,
        "records": records,
        "writes_on_read": False,
        "transcript_inference": False,
        "provider_invocation": False,
        "personality_mutation": False,
        "deletes_memories": True,
        "deletes_memories_without_confirmation": False,
        "confirmed_permanent_deletion_supported": True,
        "permanent_deletion_requires_retracted_state": True,
        "permanent_deletion_requires_exact_confirmation": True,
        "provenance_visible": True,
        "explicit_correction_supported": True,
        "explicit_retention_supported": True,
        "important_moment_provenance_visible": True,
        "important_moment_review_rationale_content_free": True,
        "raw_conversation_history_rewrite_supported": False,
        "deletion_integrity": deletion_integrity,
    }
