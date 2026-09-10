from __future__ import annotations

"""Era 4 temporal, event and identity coherence projection.

The projection is provider-free and non-authorizing.  It relies on explicit entity ids,
alias declarations, timestamps and intervals rather than merging people/projects merely
because their labels look similar.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1850.9"
MAX_RECORDS = 240
TIME_FIELDS = ("occurred_at", "event_at", "timestamp", "created_at", "updated_at", "date")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _parse(value: object) -> tuple[datetime | None, bool]:
    token = str(value or "").strip()
    if not token:
        return None, True
    uncertain = token.endswith("?") or token.lower().startswith(("about ", "around ", "circa "))
    token = token.rstrip("?")
    for prefix in ("about ", "around ", "circa "):
        if token.lower().startswith(prefix):
            token = token[len(prefix):]
    try:
        dt = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return None, True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc), uncertain


def _entity_id(row: Mapping[str, Any]) -> str:
    return str(row.get("canonical_entity_id") or row.get("entity_id") or row.get("person_id") or row.get("project_id") or "").strip()[:180]


def _aliases(row: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    raw = row.get("aliases")
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        values.extend(str(v).strip() for v in raw if str(v).strip())
    for key in ("alias", "name", "display_name", "nickname"):
        if str(row.get(key) or "").strip():
            values.append(str(row.get(key)).strip())
    return list(dict.fromkeys(v[:180] for v in values))[:16]


def _event_time(row: Mapping[str, Any]) -> tuple[datetime | None, bool, str]:
    for field in TIME_FIELDS:
        dt, uncertain = _parse(row.get(field))
        if dt is not None:
            return dt, uncertain or bool(row.get("date_uncertain")), field
    return None, True, ""


def _interval(row: Mapping[str, Any]) -> tuple[datetime | None, datetime | None, bool]:
    start_raw = row.get("start_at") or row.get("starts_at") or row.get("start_date")
    end_raw = row.get("end_at") or row.get("ends_at") or row.get("end_date") or row.get("deadline")
    start, su = _parse(start_raw)
    end, eu = _parse(end_raw)
    uncertain = bool((su if start_raw else False) or (eu if end_raw else False) or row.get("date_uncertain"))
    if start is None and end is None:
        point, pu, _ = _event_time(row)
        if point is not None:
            start = end = point
            uncertain = uncertain or pu
    elif start is not None and end is None:
        end = start
        uncertain = True
    elif end is not None and start is None:
        start = end
        uncertain = True
    return start, end, uncertain


def temporal_relation(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    ls, le, lu = _interval(left)
    rs, re, ru = _interval(right)
    if ls is None or le is None or rs is None or re is None or lu or ru:
        return "uncertain"
    if le < rs:
        return "before"
    if re < ls:
        return "after"
    if ls == rs and le == re:
        return "same_interval"
    return "overlaps"


@dataclass(frozen=True)
class TimelineEvent:
    event_digest: str
    entity_digest: str
    occurred_at: str
    end_at: str
    uncertain: bool
    recurrence: str
    role: str
    source_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_temporal_identity_projection(records: object, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    malformed_collection = not isinstance(records, Sequence) or isinstance(records, (str, bytes, bytearray))
    rows = [] if malformed_collection else [r for r in list(records)[:MAX_RECORDS] if isinstance(r, Mapping)]
    entities: dict[str, dict[str, Any]] = {}
    alias_index: dict[str, set[str]] = {}
    timeline: list[TimelineEvent] = []
    uncertain_dates = 0
    recurrence_count = 0
    role_changes: dict[str, list[str]] = {}

    for index, row in enumerate(rows):
        entity_id = _entity_id(row)
        aliases = _aliases(row)
        # Names without explicit identity are not enough to merge identities.
        if entity_id:
            ent = entities.setdefault(entity_id, {"aliases": set(), "roles": [], "record_digests": []})
            ent["aliases"].update(a.casefold() for a in aliases)
            ent["record_digests"].append(_digest(str(row.get("id") or row.get("memory_id") or index))[:24])
            role = str(row.get("role") or row.get("relationship_role") or row.get("project_role") or "").strip().lower()
            if role and (not ent["roles"] or ent["roles"][-1] != role):
                ent["roles"].append(role[:120])
                role_changes.setdefault(entity_id, []).append(role[:120])
            for alias in aliases:
                alias_index.setdefault(alias.casefold(), set()).add(entity_id)
        start, end, uncertain = _interval(row)
        if start is not None:
            recurrence = str(row.get("recurrence") or row.get("recurrence_rule") or "none").strip().lower()[:120]
            if recurrence not in {"", "none"}:
                recurrence_count += 1
            if uncertain:
                uncertain_dates += 1
            timeline.append(TimelineEvent(
                event_digest=_digest({"record": str(row.get("id") or index), "start": start.isoformat(), "end": end.isoformat() if end else ""})[:24],
                entity_digest=_digest(entity_id)[:24] if entity_id else "",
                occurred_at=start.isoformat(), end_at=(end or start).isoformat(), uncertain=uncertain,
                recurrence=recurrence or "none", role=str(row.get("event_role") or row.get("type") or "event")[:120],
                source_digest=_digest(str(row.get("source") or row.get("provenance_class") or "unknown"))[:24],
            ))

    ambiguous_aliases = {alias: ids for alias, ids in alias_index.items() if len(ids) > 1}
    entity_rows = []
    for entity_id, row in entities.items():
        entity_rows.append({
            "entity_digest": _digest(entity_id)[:24],
            "alias_digests": sorted(_digest(a)[:24] for a in row["aliases"]),
            "role_history": list(row["roles"]),
            "record_count": len(row["record_digests"]),
            "identity_merged_by_explicit_id": True,
            "raw_identity_exposed": False,
        })
    timeline.sort(key=lambda e: (e.occurred_at, e.event_digest))
    now_iso = current.isoformat()
    overdue_deadlines = 0
    anniversaries = 0
    for row in rows:
        deadline, _ = _parse(row.get("deadline"))
        if deadline and deadline < current:
            overdue_deadlines += 1
        if row.get("anniversary") or str(row.get("event_type") or "").lower() == "anniversary":
            anniversaries += 1
    evidence = {
        "contract_version": CONTRACT_VERSION,
        "record_count": len(rows), "entity_count": len(entities), "timeline_event_count": len(timeline),
        "ambiguous_alias_count": len(ambiguous_aliases), "uncertain_date_count": uncertain_dates,
        "recurring_event_count": recurrence_count, "role_change_count": sum(max(0, len(v)-1) for v in role_changes.values()),
        "overdue_deadline_count": overdue_deadlines, "anniversary_count": anniversaries,
        "names_without_identity_not_merged": True, "provider_contacted": False, "memory_mutated": False,
        "identity_mutated": False, "authority": "none", "contains_private_text": False,
        "evaluated_at": now_iso,
    }
    evidence["evidence_digest"] = _digest(evidence)
    return {
        "ok": not malformed_collection,
        "contract_version": CONTRACT_VERSION,
        "entities": entity_rows,
        "timeline": [row.to_dict() for row in timeline],
        "ambiguous_alias_digests": sorted(_digest(alias)[:24] for alias in ambiguous_aliases),
        "evidence": evidence,
        "authority_boundary": {"can_merge_identity": False, "can_mutate_memory": False, "can_schedule": False, "can_authorize": False, "can_execute": False},
    }


def resolve_identity_alias(alias: str, records: object) -> dict[str, Any]:
    token = str(alias or "").strip().casefold()
    if not token:
        return {"status": "invalid_alias", "resolved": False, "ambiguous": False, "entity_digest": ""}
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes, bytearray)):
        return {"status": "invalid_records", "resolved": False, "ambiguous": False, "entity_digest": ""}
    ids = set()
    for row in records:
        if not isinstance(row, Mapping):
            continue
        if token in {a.casefold() for a in _aliases(row)} and _entity_id(row):
            ids.add(_entity_id(row))
    if len(ids) == 1:
        return {"status": "resolved", "resolved": True, "ambiguous": False, "entity_digest": _digest(next(iter(ids)))[:24]}
    if len(ids) > 1:
        return {"status": "ambiguous_alias", "resolved": False, "ambiguous": True, "entity_digest": ""}
    return {"status": "unknown_alias", "resolved": False, "ambiguous": False, "entity_digest": ""}


__all__ = ["CONTRACT_VERSION", "build_temporal_identity_projection", "resolve_identity_alias", "temporal_relation"]
