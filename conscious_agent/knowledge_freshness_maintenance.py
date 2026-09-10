from __future__ import annotations

"""Era 4 freshness-aware, provider-neutral knowledge maintenance.

The module can decide that knowledge needs refresh and describe the evidence contract for
that refresh.  It never browses, contacts providers, rewrites memory, or treats generated
prose as evidence that research occurred.
"""

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1899.9"
FRESHNESS_CLASSES = ("stable", "versioned", "time_sensitive", "local_runtime", "externally_verifiable")
MAX_RECORDS = 160
MAX_EVIDENCE = 24


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _parse(value: object) -> datetime | None:
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


def classify_knowledge_freshness(row: Mapping[str, Any]) -> str:
    explicit = str(row.get("freshness_class") or row.get("knowledge_class") or "").strip().lower()
    if explicit in FRESHNESS_CLASSES:
        return explicit
    text = " ".join(str(row.get(k) or "").lower() for k in ("type", "category", "source", "subject", "title"))
    if row.get("runtime_local") or any(t in text for t in ("local_runtime", "installed_model", "current_config", "local_provider")):
        return "local_runtime"
    if row.get("version") or row.get("versioned") or any(t in text for t in ("version", "release", "api", "library", "dependency")):
        return "versioned"
    if row.get("expires_at") or row.get("time_sensitive") or any(t in text for t in ("price", "weather", "schedule", "current", "today", "news")):
        return "time_sensitive"
    if row.get("external_verification_required") or any(t in text for t in ("web", "external", "research", "citation")):
        return "externally_verifiable"
    return "stable"


def _latest_time(row: Mapping[str, Any]) -> datetime | None:
    for key in ("verified_at", "updated_at", "created_at", "occurred_at", "timestamp"):
        dt = _parse(row.get(key))
        if dt:
            return dt
    return None


def _max_age_days(cls: str) -> int | None:
    return {"stable": 3650, "versioned": 180, "time_sensitive": 7, "local_runtime": 1, "externally_verifiable": 90}.get(cls)


def inspect_knowledge_freshness(records: object, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    malformed_collection = not isinstance(records, Sequence) or isinstance(records, (str, bytes, bytearray))
    rows = [] if malformed_collection else [r for r in list(records)[:MAX_RECORDS] if isinstance(r, Mapping)]
    candidates = []
    counts = {name: 0 for name in FRESHNESS_CLASSES}
    stale_count = unknown_time_count = 0
    for index, row in enumerate(rows):
        cls = classify_knowledge_freshness(row)
        counts[cls] += 1
        checked = _latest_time(row)
        max_age = _max_age_days(cls)
        age_days = None if checked is None else max(0, int((current - checked).total_seconds() // 86400))
        stale = bool(max_age is not None and age_days is not None and age_days > max_age)
        unknown = checked is None
        if stale:
            stale_count += 1
        if unknown:
            unknown_time_count += 1
        if stale or (unknown and cls != "stable"):
            candidates.append({
                "knowledge_digest": _digest(str(row.get("id") or row.get("fact_key") or index))[:24],
                "freshness_class": cls,
                "age_days": age_days,
                "max_age_days": max_age,
                "reason": "stale_by_policy" if stale else "verification_time_unknown",
                "refresh_requires_private_runtime": cls == "local_runtime",
                "refresh_requires_external_evidence": cls in {"versioned", "time_sensitive", "externally_verifiable"},
                "raw_content_exposed": False,
            })
    result = {
        "contract_version": CONTRACT_VERSION,
        "record_count": len(rows), "class_counts": counts, "refresh_candidate_count": len(candidates),
        "stale_count": stale_count, "unknown_verification_time_count": unknown_time_count,
        "refresh_candidates": candidates,
        "provider_contacted": False, "external_browsing_performed": False, "memory_mutated": False,
        "refresh_claimed_complete": False, "authority": "none", "contains_private_content": False,
    }
    result["inspection_digest"] = _digest(result)
    return result


def build_refresh_proposal(candidate: Mapping[str, Any], *, question_code: str = "verify_current_truth") -> dict[str, Any]:
    cls = str(candidate.get("freshness_class") or "").strip().lower()
    if cls not in FRESHNESS_CLASSES:
        raise ValueError("recognized freshness class required")
    requirements = []
    if cls == "local_runtime":
        requirements.append("operator_authorized_local_runtime_evidence")
    elif cls in {"versioned", "time_sensitive", "externally_verifiable"}:
        requirements.extend(["current_external_source", "publication_or_observation_time", "source_quality_class"])
    else:
        requirements.append("attributable_source_if_refresh_requested")
    proposal = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": "knowledge-refresh-" + _digest((candidate.get("knowledge_digest"), cls, question_code))[:24],
        "knowledge_digest": str(candidate.get("knowledge_digest") or "")[:64],
        "freshness_class": cls,
        "question_code": re.sub(r"[^a-z0-9_]+", "_", str(question_code or "verify_current_truth").lower())[:80],
        "required_evidence": requirements,
        "operator_review_required_for_private_runtime": cls == "local_runtime",
        "provider_neutral": True,
        "browse_authorized": False,
        "provider_contact_authorized": False,
        "memory_mutation_authorized": False,
        "refresh_completed": False,
        "generated_prose_is_evidence": False,
    }
    proposal["proposal_digest"] = _digest(proposal)
    return proposal


def assess_refresh_evidence(proposal: Mapping[str, Any], evidence_rows: object, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    malformed = not isinstance(evidence_rows, Sequence) or isinstance(evidence_rows, (str, bytes, bytearray))
    rows = [] if malformed else list(evidence_rows)[:MAX_EVIDENCE]
    accepted = []
    rejected_private = rejected_quality = rejected_generated = 0
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            rejected_quality += 1
            continue
        if row.get("private") is True or str(row.get("privacy") or "").lower() in {"private", "secret", "restricted"}:
            rejected_private += 1
            continue
        source_type = str(row.get("source_type") or row.get("provenance_class") or "").strip().lower()
        if source_type in {"assistant", "generated", "model_output", "eidolon"}:
            rejected_generated += 1
            continue
        quality = str(row.get("source_quality") or "unknown").strip().lower()
        if quality not in {"primary", "authoritative", "official", "high", "operator_observation"}:
            rejected_quality += 1
            continue
        observed = _parse(row.get("observed_at") or row.get("published_at") or row.get("retrieved_at"))
        if observed is None:
            rejected_quality += 1
            continue
        accepted.append({
            "evidence_digest": _digest(str(row.get("id") or row.get("url") or index))[:24],
            "source_type": source_type or "external_source",
            "source_quality": quality,
            "observed_at": observed.isoformat(),
            "age_days": max(0, int((current - observed).total_seconds() // 86400)),
            "citation_digest": _digest(str(row.get("citation") or row.get("url") or row.get("reference") or index))[:24],
            "raw_content_exposed": False,
        })
    cls = str(proposal.get("freshness_class") or "")
    max_age = _max_age_days(cls)
    current_rows = [r for r in accepted if max_age is None or r["age_days"] <= max_age]
    sufficient = bool(current_rows)
    result = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal.get("proposal_id") or ""),
        "accepted_evidence_count": len(accepted), "current_evidence_count": len(current_rows),
        "rejected_private_count": rejected_private, "rejected_quality_count": rejected_quality,
        "rejected_generated_count": rejected_generated, "sufficient_for_review": sufficient,
        "citation_records": current_rows,
        "refresh_completed": False,
        "safe_next_state": "review_current_evidence" if sufficient else "retain_stale_or_unknown_state",
        "provider_contacted": False, "external_browsing_performed": False,
        "private_public_evidence_separated": True, "memory_mutated": False,
        "generated_prose_is_evidence": False,
    }
    result["assessment_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION", "FRESHNESS_CLASSES", "classify_knowledge_freshness", "inspect_knowledge_freshness",
    "build_refresh_proposal", "assess_refresh_evidence",
]
