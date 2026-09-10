from __future__ import annotations

"""Operator-governed curation for explicit durable entity associations."""

import hashlib
import json
import re
from typing import Any

from conversation_surface_contracts import RelationshipMemoryCurationError
from entity_association_graph import EntityAssociationGraph
from relationship_memory_curation import (
    correct_relationship_memory,
    delete_retracted_relationship_memory,
    list_relationship_memory_curation_records,
    update_relationship_memory,
)


CONTRACT_VERSION = "v1500.5"
ALLOWED_PREDICATES = (
    "uses_provider",
    "belongs_to_project",
    "contains",
    "owned_by",
    "prefers_provider",
    "preferred_over",
)
_DURABLE = re.compile(r"^Entity association: (.{1,120}) \| ([a-z][a-z0-9_]{0,63}) \| (.{1,120})\.$")


def _digest(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(str(part or "") for part in parts).encode("utf-8")).hexdigest()


def _label(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip(" .,!?:;")
    if not text or len(text) > 120 or "|" in text or any(ord(char) < 32 for char in text):
        raise RelationshipMemoryCurationError("Association labels must be plain text of 120 characters or fewer.")
    return text


def _predicate(value: Any) -> str:
    token = " ".join(str(value or "").split()).casefold().replace("-", "_").replace(" ", "_")
    if token not in ALLOWED_PREDICATES:
        raise RelationshipMemoryCurationError("Unsupported entity-association predicate.")
    return token


def _parse_record(record: dict[str, Any]) -> dict[str, Any] | None:
    content = " ".join(str(record.get("content") or "").split())
    match = _DURABLE.fullmatch(content)
    if not match or match.group(2) not in ALLOWED_PREDICATES:
        return None
    record_key = str(record.get("record_key") or "")
    state = str(record.get("state") or "active")
    association_id = "association:" + _digest(record_key, content, state)[:24]
    return {
        "association_id": association_id,
        "record_revision_digest": _digest(record_key, content, state),
        "record_key": record_key,
        "subject": match.group(1),
        "predicate": match.group(2),
        "object": match.group(3),
        "state": state,
        "importance": str(record.get("importance") or "medium"),
        "created_at": str(record.get("created_at") or ""),
        "updated_at": str(record.get("updated_at") or ""),
        "history_count": int(record.get("history_count") or 0),
        "provenance": dict(record.get("provenance") or {}),
        "private_operator_view": True,
        "content_free": False,
        "provider_contacted": False,
        "authority_granted": False,
    }


def list_entity_association_records(*, include_retracted: bool = True) -> list[dict[str, Any]]:
    rows = []
    for record in list_relationship_memory_curation_records(include_retracted=include_retracted):
        parsed = _parse_record(record)
        if parsed:
            rows.append(parsed)
    return rows


def inspect_entity_association(association_id: str) -> dict[str, Any]:
    token = str(association_id or "").strip()
    record = next((row for row in list_entity_association_records() if row["association_id"] == token), None)
    if not record:
        raise RelationshipMemoryCurationError("The selected entity association is stale or no longer exists.")
    return dict(record)


def _structured_content(subject: str, predicate: str, obj: str) -> str:
    clean_subject, relation, clean_object = _label(subject), _predicate(predicate), _label(obj)
    if clean_subject.casefold() == clean_object.casefold():
        raise RelationshipMemoryCurationError("An entity association cannot point an entity to itself.")
    graph = EntityAssociationGraph()
    graph.add_association(clean_subject, relation, clean_object)
    return f"Entity association: {clean_subject} | {relation} | {clean_object}."


def correct_entity_association(
    association_id: str,
    *,
    subject: str,
    predicate: str,
    obj: str,
    importance: str = "",
    source: str = "operator_entity_association_curation_dashboard",
) -> dict[str, Any]:
    current = inspect_entity_association(association_id)
    result = correct_relationship_memory(
        current["record_key"],
        _structured_content(subject, predicate, obj),
        importance=importance,
        source=source,
    )
    refreshed = next(
        (row for row in list_entity_association_records() if row["record_key"] == current["record_key"]),
        None,
    )
    return {
        **result,
        "association": refreshed,
        "stale_revision_rejected": False,
        "provider_contacted": False,
        "authority_granted": False,
    }


def update_entity_association(
    association_id: str,
    action: str,
    *,
    source: str = "operator_entity_association_curation_dashboard",
) -> dict[str, Any]:
    normalized = str(action or "").strip().lower()
    if normalized not in {"retract", "restore"}:
        raise RelationshipMemoryCurationError("Unsupported entity-association action.")
    current = inspect_entity_association(association_id)
    result = update_relationship_memory(
        current["record_key"], normalized,
        source=source,
    )
    refreshed = next(
        (row for row in list_entity_association_records() if row["record_key"] == current["record_key"]),
        None,
    )
    return {
        **result,
        "association": refreshed,
        "stale_revision_rejected": False,
        "provider_contacted": False,
        "authority_granted": False,
    }


def _same(left: Any, right: Any) -> bool:
    return " ".join(str(left or "").split()).casefold() == " ".join(str(right or "").split()).casefold()


def _natural_statement(row: dict[str, Any]) -> str:
    subject, predicate, obj = row["subject"], row["predicate"], row["object"]
    if predicate == "uses_provider":
        return f"{subject} uses {obj}"
    if predicate == "belongs_to_project":
        return f"{subject} belongs to {obj}"
    if predicate == "contains":
        return f"{subject} contains {obj}"
    if predicate == "owned_by" and _same(obj, "the user"):
        return f"you own {subject}"
    if predicate == "prefers_provider" and _same(subject, "the user"):
        return f"your preferred provider is {obj}"
    if predicate == "preferred_over":
        return f"you prefer {subject} over {obj}"
    return f"{subject} {predicate.replace('_', ' ')} {obj}"


def apply_conversational_entity_association_mutation(message: str) -> dict[str, Any]:
    """Apply one explicit conversational correction or reversible retraction."""
    from conversation_entity_associations import conversation_association_mutation_request

    request = conversation_association_mutation_request(message)
    base = {
        "handled": bool(request.recognized),
        "mutated": False,
        "action": request.action,
        "status": "not_requested" if not request.recognized else "unresolved",
        "response": "",
        "provider_contacted": False,
        "authority_granted": False,
        "content_free_receipt": True,
    }
    if not request.recognized:
        return base
    if not request.subject or not request.predicate:
        return {
            **base,
            "status": "ambiguous",
            "response": "I couldn't identify one exact stored association to change. Please name the subject and relationship explicitly.",
        }
    active = [
        row for row in list_entity_association_records(include_retracted=True)
        if row["state"] == "active" and _same(row["subject"], request.subject)
        and row["predicate"] == request.predicate
        and (not request.object or _same(row["object"], request.object))
    ]
    if request.action == "correct":
        active = [
            row for row in list_entity_association_records(include_retracted=True)
            if row["state"] == "active" and _same(row["subject"], request.subject)
            and row["predicate"] == request.predicate
        ]
    if not active:
        return {
            **base,
            "status": "not_found",
            "response": f"I don't have an active stored association for {request.subject} that matches that request.",
        }
    if len(active) != 1:
        return {
            **base,
            "status": "ambiguous",
            "response": "I found more than one matching stored association, so I didn't change any of them. Please be more specific.",
        }
    current = active[0]
    if request.action == "correct":
        if _same(current["object"], request.object):
            return {**base, "status": "already_current", "response": f"I already have it stored that {_natural_statement(current)}."}
        result = correct_entity_association(
            current["association_id"], subject=request.subject, predicate=request.predicate,
            obj=request.object, source="operator_explicit_conversation_association_correction",
        )
        updated = dict(result.get("association") or {})
        return {
            **base,
            "mutated": True,
            "status": "corrected",
            "response": f"I've corrected that. I'll remember that {_natural_statement(updated)}.",
            "association_id_digest": _digest(updated.get("association_id")),
        }
    result = update_entity_association(
        current["association_id"], "retract",
        source="operator_explicit_conversation_association_retraction",
    )
    return {
        **base,
        "mutated": True,
        "status": "retracted",
        "response": f"I've retracted the stored association that {_natural_statement(current)}. You can restore or permanently delete it from the memory inspector.",
        "association_id_digest": _digest((result.get("association") or {}).get("association_id")),
    }


def delete_entity_association(association_id: str, confirmation: str) -> dict[str, Any]:
    current = inspect_entity_association(association_id)
    result = delete_retracted_relationship_memory(
        current["record_key"], confirmation,
        source="operator_entity_association_curation_dashboard",
    )
    return {
        **result,
        "association_id_digest": _digest(association_id),
        "provider_contacted": False,
        "authority_granted": False,
    }


def entity_association_curation_summary() -> dict[str, Any]:
    rows = list_entity_association_records()
    counts = {"active": 0, "disabled": 0, "retracted": 0}
    for row in rows:
        state = row["state"] if row["state"] in counts else "disabled"
        counts[state] += 1
    summary = {
        "contract_version": CONTRACT_VERSION,
        "record_count": len(rows),
        "counts": counts,
        "permanent_deletion_requires_retraction": True,
        "permanent_deletion_confirmation": "DELETE",
        "stale_revision_rejection": True,
        "provider_contacted": False,
        "authority_granted": False,
        "contains_association_content": False,
        "content_free": True,
    }
    summary["summary_digest"] = _digest(json.dumps(summary, sort_keys=True, separators=(",", ":")))[:24]
    return summary


__all__ = [
    "ALLOWED_PREDICATES", "CONTRACT_VERSION", "apply_conversational_entity_association_mutation",
    "correct_entity_association",
    "delete_entity_association", "entity_association_curation_summary",
    "inspect_entity_association", "list_entity_association_records",
    "update_entity_association",
]
