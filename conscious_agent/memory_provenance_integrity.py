from __future__ import annotations

"""Content-free provenance integrity boundary for durable memory ingestion.

The boundary classifies provenance without converting unknown or assistant-authored
material into user history. Malformed claimed provenance is retained for audit but
quarantined from historical-evidence use. It grants no authority and exposes no
memory text through its public diagnostics.
"""

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Iterable, Mapping

from memory_commit_attribution import MemoryCommitAttributionError, validate_memory_commit_attribution

PROVENANCE_SCHEMA_VERSION = "1"
PROVENANCE_USER = "user"
PROVENANCE_ASSISTANT = "assistant"
PROVENANCE_ACTION_RECEIPT = "action_receipt"
PROVENANCE_IMPORTED = "imported"
PROVENANCE_UNKNOWN = "unknown"
PROVENANCE_CLASSES = (
    PROVENANCE_USER, PROVENANCE_ASSISTANT, PROVENANCE_ACTION_RECEIPT,
    PROVENANCE_IMPORTED, PROVENANCE_UNKNOWN,
)


def _text(record: Mapping[str, Any]) -> str:
    return " ".join(str(record.get("content") or record.get("thought") or record.get("summary") or record.get("text") or "").split())


def _digest(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _record_id(record: Mapping[str, Any]) -> str:
    return str(record.get("id") or record.get("memory_id") or record.get("conversation_turn_id") or record.get("receipt_id") or "").strip()


@dataclass(frozen=True)
class MemoryProvenanceProfile:
    provenance_class: str
    provenance_valid: bool
    historical_evidence_eligible: bool
    quarantined: bool
    reason: str
    record_identifier_present: bool
    attribution_digest_valid: bool
    imported: bool = False
    content_free: bool = True
    schema_version: str = PROVENANCE_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def classify_memory_provenance(record: Mapping[str, Any]) -> MemoryProvenanceProfile:
    row = dict(record or {})
    content = _text(row)
    attribution = row.get("memory_commit_attribution") if isinstance(row.get("memory_commit_attribution"), Mapping) else None
    if attribution is not None:
        try:
            validated = validate_memory_commit_attribution(attribution)
            role = str(validated.get("role") or "")
            digest_ok = str(validated.get("content_digest") or "") == _digest(content)
            ids_ok = bool(_record_id(row)) and all(str(validated.get(key) or "").strip() for key in (
                "memory_candidate_id", "conversation_operation_id", "conversation_session_id", "conversation_turn_id",
            ))
            if not digest_ok or not ids_ok:
                return MemoryProvenanceProfile(
                    provenance_class=role if role in {PROVENANCE_USER, PROVENANCE_ASSISTANT} else PROVENANCE_UNKNOWN,
                    provenance_valid=False, historical_evidence_eligible=False, quarantined=True,
                    reason="attribution_digest_or_identifier_invalid", record_identifier_present=bool(_record_id(row)),
                    attribution_digest_valid=digest_ok,
                )
            return MemoryProvenanceProfile(
                provenance_class=PROVENANCE_USER if role == "user" else PROVENANCE_ASSISTANT,
                provenance_valid=True, historical_evidence_eligible=(role == "user"), quarantined=False,
                reason="validated_conversation_attribution", record_identifier_present=True,
                attribution_digest_valid=True,
            )
        except MemoryCommitAttributionError:
            return MemoryProvenanceProfile(
                provenance_class=PROVENANCE_UNKNOWN, provenance_valid=False,
                historical_evidence_eligible=False, quarantined=True,
                reason="malformed_memory_commit_attribution", record_identifier_present=bool(_record_id(row)),
                attribution_digest_valid=False,
            )

    kind = str(row.get("type") or "").strip().lower()
    role = str(row.get("role") or "").strip().lower()
    source = str(row.get("source") or row.get("origin") or "").strip().lower()
    provenance = row.get("provenance") if isinstance(row.get("provenance"), Mapping) else {}
    origin = str(provenance.get("origin") or "").strip().lower()
    rid = _record_id(row)

    if source.startswith("import") or origin in {"imported", "external_import", "migration_import"}:
        valid = bool(rid and source)
        return MemoryProvenanceProfile(
            provenance_class=PROVENANCE_IMPORTED, provenance_valid=valid,
            historical_evidence_eligible=False, quarantined=not valid,
            reason="attributed_import" if valid else "malformed_import_provenance",
            record_identifier_present=bool(rid), attribution_digest_valid=False, imported=True,
        )
    if kind in {"action_receipt", "execution_receipt", "diagnostic_receipt"}:
        valid = bool(rid and source)
        return MemoryProvenanceProfile(
            provenance_class=PROVENANCE_ACTION_RECEIPT, provenance_valid=valid,
            historical_evidence_eligible=valid, quarantined=not valid,
            reason="attributed_action_receipt" if valid else "malformed_action_receipt_provenance",
            record_identifier_present=bool(rid), attribution_digest_valid=False,
        )
    if kind == "conversation_user" or role == "user" or origin in {"user", "operator_input", "operator_explicit", "operator_reviewed_exact_content"} or bool(row.get("operator_explicit")) or source.startswith("operator_"):
        valid = bool(rid and content and (source or origin or row.get("conversation_session_id")))
        return MemoryProvenanceProfile(
            provenance_class=PROVENANCE_USER, provenance_valid=valid,
            historical_evidence_eligible=valid, quarantined=not valid,
            reason="legacy_user_attribution" if valid else "malformed_user_provenance",
            record_identifier_present=bool(rid), attribution_digest_valid=False,
        )
    if kind == "conversation_eidolon" or role == "assistant" or origin in {"assistant", "eidolon", "generated_turn"}:
        valid = bool(rid and content and (source or origin or row.get("conversation_session_id")))
        return MemoryProvenanceProfile(
            provenance_class=PROVENANCE_ASSISTANT, provenance_valid=valid,
            historical_evidence_eligible=False, quarantined=not valid,
            reason="legacy_assistant_attribution" if valid else "malformed_assistant_provenance",
            record_identifier_present=bool(rid), attribution_digest_valid=False,
        )
    return MemoryProvenanceProfile(
        provenance_class=PROVENANCE_UNKNOWN, provenance_valid=False,
        historical_evidence_eligible=False, quarantined=False,
        reason="nonhistorical_or_unknown_provenance", record_identifier_present=bool(rid),
        attribution_digest_valid=False,
    )


def prepare_memory_for_ingestion(record: Mapping[str, Any], *, existing_records: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    row = dict(record or {})
    profile = classify_memory_provenance(row)
    row["provenance_integrity"] = profile.public_summary()
    row["historical_evidence_eligible"] = bool(profile.historical_evidence_eligible)
    if profile.quarantined:
        row["provenance_quarantined"] = True
        row["historical_evidence_eligible"] = False

    # A user-authored correction carries deterministic supersession lineage forward
    # without rewriting prior transcript/memory content.
    fact_key = str(row.get("fact_key") or row.get("fact_identity") or row.get("correction_group_id") or "").strip()
    is_correction = bool(row.get("operator_correction") or row.get("is_correction") or row.get("correction_lineage"))
    if profile.provenance_class == PROVENANCE_USER and profile.provenance_valid and fact_key and is_correction:
        superseded_ids: list[str] = []
        superseded_digests: list[str] = list(row.get("superseded_content_digests") or ())
        for existing in existing_records:
            if not isinstance(existing, Mapping):
                continue
            existing_key = str(existing.get("fact_key") or existing.get("fact_identity") or existing.get("correction_group_id") or "").strip()
            if existing_key != fact_key:
                continue
            eid = _record_id(existing)
            etext = _text(existing)
            if eid and eid not in superseded_ids:
                superseded_ids.append(eid)
            if etext:
                digest = _digest(etext)
                if digest not in superseded_digests:
                    superseded_digests.append(digest)
        if superseded_ids or superseded_digests:
            row["supersession_lineage"] = {
                "schema_version": PROVENANCE_SCHEMA_VERSION,
                "fact_key_digest": _digest(fact_key),
                "superseded_record_ids": superseded_ids[-16:],
                "superseded_record_count": len(superseded_ids),
                "content_free": True,
            }
            row["superseded_content_digests"] = superseded_digests[-32:]
    return row


def bounded_fact_conflicts(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in records:
        if not isinstance(row, Mapping):
            continue
        profile = classify_memory_provenance(row)
        if not profile.provenance_valid or profile.quarantined:
            continue
        key = str(row.get("fact_key") or row.get("fact_identity") or row.get("correction_group_id") or "").strip()
        if key:
            groups.setdefault(key, []).append(row)
    conflicts: list[dict[str, Any]] = []
    for key, rows in groups.items():
        digests = {_digest(_text(row)) for row in rows if _text(row)}
        if len(digests) < 2:
            continue
        conflicts.append({
            "fact_key_digest": _digest(key),
            "record_count": min(99, len(rows)),
            "distinct_content_digest_count": min(99, len(digests)),
            "provenance_classes": sorted({classify_memory_provenance(row).provenance_class for row in rows}),
            "content_free": True,
        })
    return conflicts


def public_provenance_explanation(record: Mapping[str, Any]) -> dict[str, Any]:
    profile = classify_memory_provenance(record)
    reason_text = {
        "malformed_memory_commit_attribution": "Claimed conversation provenance failed validation and was quarantined.",
        "attribution_digest_or_identifier_invalid": "Attribution did not bind to the stored record identity/content digest.",
        "malformed_import_provenance": "Imported memory lacked the required attributable record boundary.",
        "malformed_user_provenance": "User provenance was incomplete, so the record cannot support historical claims.",
        "malformed_assistant_provenance": "Assistant provenance was incomplete and cannot become user-experience evidence.",
        "legacy_assistant_attribution": "Assistant-authored material is not evidence that the user experienced an event.",
        "nonhistorical_or_unknown_provenance": "No attributable historical provenance is available for this record.",
    }.get(profile.reason, "Provenance is bounded and does not broaden historical authority.")
    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "provenance_class": profile.provenance_class,
        "provenance_valid": profile.provenance_valid,
        "historical_evidence_eligible": profile.historical_evidence_eligible,
        "quarantined": profile.quarantined,
        "reason_code": profile.reason,
        "operator_explanation": reason_text,
        "content_free": True,
    }
