from __future__ import annotations

"""Era 4 explicit revisable belief/world-model adapter.

This layer reuses the existing :class:`BeliefRevisionStore` as the durable belief owner.
It adds source/provenance/freshness assessment and deterministic candidate construction;
it does not create a second belief ledger or turn belief state into action authority.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from belief_revision import BeliefRevisionStore
    from json_storage import AtomicJsonWriteError
    from metadata_mutation_coordination import MetadataMutationBusy
except ImportError:
    from belief_revision import BeliefRevisionStore
    from json_storage import AtomicJsonWriteError
    from metadata_mutation_coordination import MetadataMutationBusy

CONTRACT_VERSION = "v1875.9"
MAX_EVIDENCE = 32
ASSISTANT_CLASSES = {"assistant", "eidolon", "generated_turn", "assistant_authored"}
USER_CLASSES = {"user", "operator", "operator_explicit", "user_authored"}
RECEIPT_CLASSES = {"action_receipt", "execution_receipt", "diagnostic_receipt"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _parse_time(value: object) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        dt = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _source_class(row: Mapping[str, Any]) -> str:
    integ = row.get("provenance_integrity") if isinstance(row.get("provenance_integrity"), Mapping) else {}
    token = str(integ.get("provenance_class") or row.get("provenance_class") or row.get("role") or row.get("source_type") or row.get("source") or "unknown").strip().lower()
    if token.startswith("operator_"):
        return "user"
    if token in USER_CLASSES:
        return "user"
    if token in ASSISTANT_CLASSES:
        return "assistant"
    if token in RECEIPT_CLASSES:
        return "action_receipt"
    if token in {"external_source", "document", "web", "research"}:
        return "external_source"
    return token[:80] or "unknown"


def _freshness(row: Mapping[str, Any], now: datetime) -> tuple[str, float]:
    dt = None
    for key in ("updated_at", "created_at", "occurred_at", "timestamp", "recorded_at"):
        dt = _parse_time(row.get(key))
        if dt:
            break
    if not dt:
        return "unknown", .45
    days = max(0.0, (now - dt).total_seconds() / 86400.0)
    if days <= 7:
        return "current", 1.0
    if days <= 90:
        return "recent", .85
    if days <= 365:
        return "historical", .65
    return "archival", .4


def assess_belief_evidence(proposition: str, evidence_rows: object, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    malformed_collection = not isinstance(evidence_rows, Sequence) or isinstance(evidence_rows, (str, bytes, bytearray))
    rows = [] if malformed_collection else list(evidence_rows)[:MAX_EVIDENCE]
    support = contradiction = contextual = 0.0
    counted = rejected_assistant = rejected_unattributed = stale = 0
    sources: set[str] = set()
    contradiction_sources: set[str] = set()
    details = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            rejected_unattributed += 1
            continue
        source_class = _source_class(row)
        if source_class == "assistant":
            rejected_assistant += 1
            continue
        if source_class not in {"user", "action_receipt", "external_source"}:
            rejected_unattributed += 1
            continue
        stance = str(row.get("stance") or "supports").strip().lower()
        if stance not in {"supports", "contradicts", "contextualizes"}:
            rejected_unattributed += 1
            continue
        freshness_band, freshness_weight = _freshness(row, current)
        if freshness_band in {"historical", "archival", "unknown"}:
            stale += 1
        try:
            confidence = max(0.0, min(1.0, float(row.get("confidence", row.get("reliability", .7)))))
        except (TypeError, ValueError):
            confidence = .5
        weight = confidence * freshness_weight
        counted += 1
        sources.add(source_class)
        if stance == "supports":
            support += weight
        elif stance == "contradicts":
            contradiction += weight
            contradiction_sources.add(source_class)
        else:
            contextual += weight
        details.append({
            "evidence_digest": _digest(str(row.get("id") or row.get("evidence_ref") or index))[:24],
            "source_class": source_class,
            "stance": stance,
            "freshness": freshness_band,
            "weight": round(weight, 4),
            "raw_content_exposed": False,
        })
    total = support + contradiction
    confidence = .5 if total == 0 else max(0.0, min(1.0, .5 + .5 * ((support - contradiction) / max(1.0, total))))
    if support > 0 and contradiction > 0:
        state = "contested"
    elif contradiction > support and contradiction >= .5:
        state = "suspend"
    elif support >= .5:
        state = "supported"
    else:
        state = "uncertain"
    result = {
        "contract_version": CONTRACT_VERSION,
        "proposition_digest": _digest(proposition)[:24],
        "counted_evidence": counted,
        "independent_source_classes": sorted(sources),
        "support_weight": round(support, 4),
        "contradiction_weight": round(contradiction, 4),
        "context_weight": round(contextual, 4),
        "confidence": round(confidence, 4),
        "state": state,
        "stale_evidence_count": stale,
        "assistant_authored_rejected_count": rejected_assistant,
        "unattributed_rejected_count": rejected_unattributed,
        "source_disagreement": support > 0 and contradiction > 0,
        "evidence": details,
        "provider_contacted": False,
        "action_authority_changed": False,
        "belief_store_duplicated": False,
        "raw_evidence_text_exposed": False,
    }
    result["assessment_digest"] = _digest(result)
    return result


def integrate_reviewed_belief(
    event_id: str,
    *,
    proposition: str,
    subject_key: str,
    evidence_rows: object,
    runtime_root: str | Path | None = None,
    scope_project_id: str = "",
) -> dict[str, Any]:
    """Integrate an assessed proposition into the existing durable belief owner.

    This is an internal epistemic-state mutation only.  Evidence text is represented to
    the durable owner by stable references/digests.  Assistant-authored rows never count.
    """
    proposition = " ".join(str(proposition or "").split())[:600]
    subject_key = " ".join(str(subject_key or "").split())[:128]
    event_id = " ".join(str(event_id or "").split())[:160]
    if not proposition or not subject_key or not event_id:
        raise ValueError("event_id, proposition, and subject_key are required")
    assessment = assess_belief_evidence(proposition, evidence_rows)
    if assessment["counted_evidence"] == 0:
        return {"ok": False, "status": "insufficient_attributable_evidence", "assessment": assessment, "action_authority_changed": False}
    store = BeliefRevisionStore(runtime_root)
    candidate_id = f"era4-belief-{_digest((subject_key, proposition, assessment['assessment_digest']))[:28]}"
    refs = [row["evidence_digest"] for row in assessment["evidence"] if row["stance"] == "supports"][:4]
    candidate = {
        "belief_candidate_id": candidate_id,
        "proposition": proposition,
        "semantic_subject_key": subject_key,
        "origin_reflection_id": f"era4:{assessment['assessment_digest']}",
        "evidence_refs": refs or [assessment["assessment_digest"]],
        "confidence": assessment["confidence"],
        "revision_basis": "evidence_assessment",
    }
    try:
        integrated = store.integrate_candidate(event_id, candidate=candidate)
        belief_id = str((integrated.get("result") or {}).get("belief_id") or "")
        # Apply contradictions as evidence to the same existing belief owner.
        for idx, row in enumerate(assessment["evidence"]):
            if not belief_id or row["stance"] == "supports":
                continue
            store.add_evidence(
                f"{event_id}:evidence:{idx}", belief_id=belief_id, stance=row["stance"],
                weight=min(1.0, row["weight"]), reliability=1.0,
                evidence_ref=row["evidence_digest"], source_type=row["source_class"],
            )
    except (MetadataMutationBusy, AtomicJsonWriteError) as error:
        return {
            "ok": False,
            "status": (
                "belief_store_busy_retry_safe"
                if isinstance(error, MetadataMutationBusy)
                else "belief_store_write_retry_safe"
                if bool(error.safe_retry) and not bool(error.uncertain_result)
                else "belief_store_write_result_uncertain"
            ),
            "retryable": bool(getattr(error, "safe_retry", False)),
            "uncertain_result": bool(getattr(error, "uncertain_result", False)),
            "assessment": assessment,
            "action_authority_changed": False,
            "provider_contacted": False,
        }
    snapshot = store.inspection_summary(item_limit=32)
    target = next((b for b in snapshot.get("beliefs", []) if b.get("belief_id") == belief_id), None)
    return {
        "ok": True,
        "status": "belief_integrated_into_existing_revision_store",
        "belief_id": belief_id,
        "assessment": assessment,
        "belief_projection": target or {},
        "existing_belief_owner": "belief_revision.BeliefRevisionStore",
        "second_belief_store_created": False,
        "action_authority_changed": False,
        "provider_contacted": False,
    }


__all__ = ["CONTRACT_VERSION", "assess_belief_evidence", "integrate_reviewed_belief"]
