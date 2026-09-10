from __future__ import annotations

"""v1151.0-v1151.2 evidence-grounded reflection foundations.

Produces bounded, revisable reflection records from the actual ordinary-turn
subject and explicit evidence references. It grants no action or authority.
"""

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from reflection_reconciliation import classify_revision_relation, validate_revision_chain

CONTRACT_VERSION = "v1151.8"
SCHEMA_VERSION = "1"
MAX_SUBJECT_CHARS = 240
MAX_EVIDENCE_ITEMS = 4
MAX_EVIDENCE_EXCERPT_CHARS = 220
MAX_CONCLUSION_CHARS = 700
CORRECTION_CUES = ("actually", "correction", "correct that", "i meant", "not ", "instead", "rather than", "that is wrong", "that was wrong")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _compact(value: object, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _terms(value: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]{2,}", str(value).lower())
    ignored = {"that", "this", "with", "from", "have", "what", "when", "where", "would", "could", "should", "about", "there", "their", "they", "them", "your", "you", "and", "the", "for", "but", "not", "are", "was"}
    return [token for token in tokens if token not in ignored]


def select_reflection_subject(user_message: str, assistant_response: str, thought: dict[str, Any] | None = None) -> dict[str, Any]:
    """Select one actual turn subject without inventing private state."""
    user = _compact(user_message, 1200)
    assistant = _compact(assistant_response, 1200)
    thought_text = _compact((thought or {}).get("thought") or (thought or {}).get("content"), 500)
    terms = _terms(user)
    subject_terms: list[str] = []
    for token in terms:
        if token not in subject_terms:
            subject_terms.append(token)
        if len(subject_terms) >= 8:
            break
    if subject_terms:
        subject = "ordinary conversation about " + ", ".join(subject_terms)
        source = "user_message_terms"
    elif user:
        subject = "the user's current conversation request"
        source = "user_message_presence"
    elif thought_text:
        subject = "the current internal thought"
        source = "thought_presence"
    else:
        subject = "the completed ordinary conversation turn"
        source = "turn_completion"
    subject = _compact(subject, MAX_SUBJECT_CHARS)
    normalized_terms = sorted(set(subject_terms))
    semantic_subject_key = _digest({"terms": normalized_terms, "fallback": source if not normalized_terms else ""})
    return {
        "subject": subject,
        "subject_source": source,
        "subject_digest": _digest({"subject": subject, "user": user[:300], "assistant": assistant[:300]}),
        "semantic_subject_key": semantic_subject_key,
        "subject_terms": normalized_terms,
        "invented_subject": False,
    }


def build_evidence_packet(*, operation_id: str, user_message: str, assistant_response: str, thought: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create explicit bounded evidence references for one reflection."""
    subject = select_reflection_subject(user_message, assistant_response, thought)
    candidates = [
        ("user_message", user_message),
        ("assistant_response", assistant_response),
        ("generated_thought", (thought or {}).get("thought") or (thought or {}).get("content") or ""),
    ]
    evidence: list[dict[str, Any]] = []
    for source_type, value in candidates:
        excerpt = _compact(value, MAX_EVIDENCE_EXCERPT_CHARS)
        if not excerpt:
            continue
        evidence.append({
            "evidence_id": f"ev-{_digest([operation_id, source_type, excerpt])[:20]}",
            "source_type": source_type,
            "excerpt": excerpt,
            "excerpt_digest": _digest(excerpt),
            "supports_subject": True,
            "operator_supplied": source_type == "user_message",
        })
        if len(evidence) >= MAX_EVIDENCE_ITEMS:
            break
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "operation_id": str(operation_id),
        **subject,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "evidence_sufficient": any(row["source_type"] == "user_message" for row in evidence),
        "content_bounded": all(len(row["excerpt"]) <= MAX_EVIDENCE_EXCERPT_CHARS for row in evidence),
        "authority_broadened": False,
    }


def _is_user_correction(user_message: str) -> bool:
    lowered = " ".join(str(user_message or "").lower().split())
    return any(cue in lowered for cue in CORRECTION_CUES)


def _prior_subject_matches(packet: dict[str, Any], row: dict[str, Any]) -> bool:
    current_key = str(packet.get("semantic_subject_key") or "")
    prior_key = str(row.get("semantic_subject_key") or "")
    if current_key and prior_key and current_key == prior_key:
        return True
    current_terms = set(packet.get("subject_terms") or [])
    prior_terms = set(row.get("subject_terms") or _terms(str(row.get("subject") or "")))
    return bool(current_terms and prior_terms and len(current_terms & prior_terms) >= 2)


def build_evidence_grounded_reflection(*, operation_id: str, user_message: str, assistant_response: str, thought: dict[str, Any], desires: dict[str, Any], prior_reflections: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    packet = build_evidence_packet(
        operation_id=operation_id,
        user_message=user_message,
        assistant_response=assistant_response,
        thought=thought,
    )
    evidence_types = {row["source_type"] for row in packet["evidence"]}
    confidence = 0.75 if {"user_message", "assistant_response"}.issubset(evidence_types) else 0.5
    uncertainty = "The turn supports a bounded interpretation, but it does not establish motives, identity, or facts beyond the cited evidence."
    if not packet["evidence_sufficient"]:
        confidence = min(confidence, 0.35)
        uncertainty = "Evidence is incomplete because no user-message evidence was available; retain this only as tentative continuity."
    conclusion = _compact(
        f"The completed turn concerned {packet['subject']}. Future responses should preserve continuity with that subject while treating the reflection as revisable and subordinate to new user evidence.",
        MAX_CONCLUSION_CHARS,
    )
    prior = [row for row in (prior_reflections or []) if isinstance(row, dict)]
    matching = [row for row in prior if str(row.get("type") or "") == "reflection" and str(row.get("status") or "active") != "retired" and _prior_subject_matches(packet, row)]
    supersedes = ""
    retired_ids: list[str] = []
    revision_reason = "new_evidence"
    correction = _is_user_correction(user_message)
    relation = classify_revision_relation(user_message, packet["subject_terms"], matching[-1] if matching else None)
    if matching:
        latest = matching[-1]
        supersedes = str(latest.get("reflection_id") or latest.get("memory_id") or "")
        revision_reason = relation["relation"]
        if relation["automatic_retirement_allowed"] and supersedes:
            retired_ids.append(supersedes)
            confidence = max(confidence, 0.9)
            uncertainty = "This reflection incorporates an explicit user correction. Earlier conflicting reflection content is retired for retrieval but preserved historically."
        elif relation["requires_operator_clarification"]:
            supersedes = ""
            uncertainty = "Potential conflict or ambiguous subject overlap detected. Preserve both interpretations until clearer user evidence identifies which one should be retired."
            confidence = min(confidence, 0.55)
    reflection_id = f"reflection-{_digest([operation_id, packet['semantic_subject_key'], conclusion])[:24]}"
    candidate = {
        "created_at": _now(),
        "type": "reflection",
        "reflection_id": reflection_id,
        "content": conclusion,
        "conclusion": conclusion,
        "subject": packet["subject"],
        "subject_source": packet["subject_source"],
        "subject_digest": packet["subject_digest"],
        "semantic_subject_key": packet["semantic_subject_key"],
        "subject_terms": packet["subject_terms"],
        "evidence_refs": [row["evidence_id"] for row in packet["evidence"]],
        "evidence": packet["evidence"],
        "evidence_count": packet["evidence_count"],
        "confidence": confidence,
        "uncertainty": uncertainty,
        "uncertainty_score": round(max(0.0, min(1.0, 1.0 - confidence)), 3),
        "status": "active",
        "revisable": True,
        "revision_reason": revision_reason,
        "operator_correction": correction,
        "supersedes_reflection_id": supersedes,
        "retires_reflection_ids": retired_ids,
        "historical_records_preserved": True,
        "recommended_action": "store_only",
        "use_in_conversation": bool(packet["evidence_sufficient"]),
        "operator_authority_required_for_action": True,
        "provider_contacted": False,
        "action_executed": False,
        "authority_broadened": False,
        "reconciliation": relation,
        "contract_version": CONTRACT_VERSION,
    }
    lineage = validate_revision_chain(candidate, prior)
    candidate.update(lineage)
    if not lineage["lineage_safe"]:
        candidate["supersedes_reflection_id"] = ""
        candidate["retires_reflection_ids"] = []
        candidate["revision_reason"] = "lineage_quarantined"
        candidate["use_in_conversation"] = False
        candidate["uncertainty"] = "Revision lineage was incomplete, cyclic, or too deep; this record is quarantined from conversation retrieval pending review."
    return candidate
