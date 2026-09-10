from __future__ import annotations

"""Bounded, provider-free coordination across Eidolon's memory domains.

The module creates a structural view over conversational, episodic, semantic,
relationship, and project memory. It preserves provenance and never writes,
merges, retracts, embeds, or otherwise mutates memory records.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

from relationship_continuity import is_relationship_memory


CONTRACT_VERSION = "1165.8"
MEMORY_DOMAINS = ("conversational", "episodic", "semantic", "relationship", "project")
MAX_MEMORY_ROWS = 80
MAX_HISTORY_ROWS = 12
MAX_SELECTED_ROWS = 80
MAX_TEXT_SCAN_CHARS = 1200
MAX_PROMPT_CHARS = 3000
MAX_PROJECT_FIELDS = 24
MAX_PRIOR_RECEIPTS = 12
MAX_PROVENANCE_SOURCES = 24
MAX_RECEIPT_COLLECTION_ROWS = 24
MAX_AUDIT_SELECTED_REFERENCES = 80

_EXCLUDED_STATUSES = {"rejected", "retracted", "deleted", "expired", "blocked", "superseded"}
_PRIVATE_LEVELS = {"secret", "restricted", "private", "sensitive"}
_AUTHORITY_KEYS = {
    "approval_granted", "approved", "authorized", "authorization_granted",
    "execution_permitted", "execute", "action_execution_permitted",
    "tool_use_permitted", "installation_permitted", "promotion_permitted",
    "certification_permitted", "autonomous_action_performed", "may_initiate_new_turn",
}
_PRIVATE_REASONING_KEYS = {
    "private_chain_of_thought", "chain_of_thought", "hidden_reasoning",
    "provider_payload", "raw_prompt", "raw_provider_response",
}
_SEMANTIC_MARKERS = (
    "semantic", "fact", "belief", "knowledge", "lesson", "principle",
    "definition", "preference_model", "concept",
)
_PROJECT_MARKERS = ("project", "codebase", "patch", "release", "workspace", "milestone")
_CONVERSATION_MARKERS = ("conversation", "chat", "session", "dialogue", "turn")
_STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "into", "your", "you", "our",
    "are", "was", "were", "have", "has", "had", "for", "about", "please", "would",
    "could", "should", "what", "when", "where", "which", "who", "why", "how",
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalized_text(record: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key in ("content", "thought", "summary", "title", "name", "description", "value"):
        value = record.get(key)
        if value not in {None, ""}:
            parts.append(str(value))
    text = " ".join(" ".join(parts).split())
    return text[:MAX_TEXT_SCAN_CHARS]


def _words(value: object) -> set[str]:
    tokens = re.findall(r"[a-z0-9_]+", str(value or "").lower())
    return {token for token in tokens if len(token) >= 3 and token not in _STOPWORDS}


def _parse_time(value: object) -> datetime | None:
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


def _age_band(record: Mapping[str, Any], *, now: datetime) -> str:
    created = _parse_time(record.get("updated_at") or record.get("created_at") or record.get("recorded_at"))
    if created is None:
        return "unknown"
    days = max(0, int((now - created).total_seconds() // 86400))
    if days <= 1:
        return "current"
    if days <= 30:
        return "recent"
    if days <= 365:
        return "historical"
    return "archival"


def _confidence_band(record: Mapping[str, Any]) -> str:
    value = record.get("confidence", record.get("importance"))
    try:
        number = float(value)
    except (TypeError, ValueError):
        token = str(value or "").strip().lower()
        if token in {"high", "critical", "core", "verified"}:
            return "high"
        if token in {"low", "tentative", "uncertain"}:
            return "low"
        return "medium" if record.get("operator_explicit") or record.get("source") else "unknown"
    if number >= 0.75:
        return "high"
    if number >= 0.4:
        return "medium"
    return "low"


def _ownership(record: Mapping[str, Any], domain: str) -> str:
    role = str(record.get("role") or "").strip().lower()
    source = str(record.get("source") or "").strip().lower()
    kind = str(record.get("type") or "").strip().lower()
    if role == "user" or kind == "conversation_user" or source in {"user", "operator_input"}:
        return "user"
    if record.get("operator_explicit") is True or "operator" in source:
        return "operator"
    if domain == "project" or "project" in source:
        return "project"
    if role == "assistant" or kind in {"conversation_eidolon", "reflection", "inner_thought"}:
        return "eidolon"
    return "system"


def _domain(record: Mapping[str, Any], *, default: str = "episodic") -> str:
    explicit = str(record.get("memory_domain") or "").strip().lower()
    if explicit in MEMORY_DOMAINS:
        return explicit
    kind = str(record.get("type") or "").strip().lower()
    source = str(record.get("source") or "").strip().lower()
    if is_relationship_memory(dict(record)):
        return "relationship"
    if kind in {"conversation_user", "conversation_eidolon"} or any(marker in kind for marker in _CONVERSATION_MARKERS):
        return "conversational"
    if record.get("project_id") or record.get("project") or any(marker in kind or marker in source for marker in _PROJECT_MARKERS):
        return "project"
    if any(marker in kind for marker in _SEMANTIC_MARKERS):
        return "semantic"
    return default


def _source(record: Mapping[str, Any], domain: str) -> str:
    token = str(record.get("source") or record.get("origin") or domain).strip()
    return (token or domain)[:80]


def _record_key(record: Mapping[str, Any], domain: str, content_digest: str) -> str:
    for key in ("id", "memory_candidate_id", "conversation_turn_id", "conversation_operation_id", "record_key"):
        token = str(record.get(key) or "").strip()
        if token:
            return _text_digest(f"{domain}:{key}:{token}")
    return _text_digest(f"{domain}:{_source(record, domain)}:{str(record.get('type') or '')}:{content_digest}")


def _fact_key(record: Mapping[str, Any]) -> str:
    for key in ("fact_key", "subject_key", "semantic_key", "memory_key", "preference_key", "project_key"):
        token = str(record.get(key) or "").strip().lower()
        if token:
            return token[:160]
    return ""


def _status_eligible(record: Mapping[str, Any]) -> tuple[bool, str]:
    status = str(record.get("status") or record.get("curation_state") or record.get("lifecycle_state") or "").strip().lower()
    if status in _EXCLUDED_STATUSES:
        return False, "inactive_status"
    privacy = str(record.get("privacy") or record.get("sensitivity") or "").strip().lower()
    if privacy in _PRIVATE_LEVELS or record.get("sensitive") is True:
        return False, "private_or_restricted"
    if any(key in record and record.get(key) not in {False, None, "", 0} for key in _AUTHORITY_KEYS):
        return False, "forged_authority"
    if any(key in record for key in _PRIVATE_REASONING_KEYS):
        return False, "private_reasoning_field"
    if not _normalized_text(record) and not record.get("id") and not record.get("project_id"):
        return False, "empty_record"
    return True, "eligible"


def _relevance(record: Mapping[str, Any], message_words: set[str], domain: str) -> int:
    text_words = _words(_normalized_text(record)) | _words(record.get("type")) | _words(record.get("source"))
    score = len(message_words & text_words) * 4
    if domain == "relationship" and record.get("relationship_eligible") is True:
        score += 2
    if record.get("operator_explicit") is True or record.get("operator_correction") is True:
        score += 3
    if record.get("current") is True or str(record.get("mood_state") or "").lower() == "current":
        score += 1
    return score


def _rank(reference: Mapping[str, Any]) -> tuple[int, int, int, str]:
    confidence = {"high": 3, "medium": 2, "low": 1, "unknown": 0}.get(str(reference.get("confidence_band")), 0)
    age = {"current": 4, "recent": 3, "historical": 2, "archival": 1, "unknown": 0}.get(str(reference.get("age_band")), 0)
    domain = {"conversational": 5, "relationship": 4, "project": 3, "semantic": 2, "episodic": 1}.get(str(reference.get("domain")), 0)
    return int(reference.get("relevance_score") or 0), confidence, age + domain, str(reference.get("reference_key") or "")


@dataclass(frozen=True)
class UnifiedMemoryReference:
    domain: str
    reference_key: str
    source: str
    ownership: str
    confidence_band: str
    age_band: str
    authority: str
    content_digest: str
    fact_key_present: bool
    relevance_score: int
    explicit_correction: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _reference(record: Mapping[str, Any], domain: str, message_words: set[str], now: datetime) -> UnifiedMemoryReference:
    text = _normalized_text(record)
    content_digest = _text_digest(text) if text else _digest({"type": record.get("type"), "id": record.get("id"), "project_id": record.get("project_id")})
    return UnifiedMemoryReference(
        domain=domain,
        reference_key=_record_key(record, domain, content_digest),
        source=_source(record, domain),
        ownership=_ownership(record, domain),
        confidence_band=_confidence_band(record),
        age_band=_age_band(record, now=now),
        authority="none",
        content_digest=content_digest,
        fact_key_present=bool(_fact_key(record)),
        relevance_score=_relevance(record, message_words, domain),
        explicit_correction=bool(record.get("operator_correction") or record.get("explicit_correction") or record.get("correction_of")),
    )


def _bounded_rows(value: object, limit: int) -> tuple[list[dict[str, Any]], int, int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return [], 1 if value is not None and value != () else 0, 0
    malformed = 0
    rows: list[dict[str, Any]] = []
    for item in list(value)[:limit]:
        if isinstance(item, Mapping):
            rows.append(dict(item))
        else:
            malformed += 1
    oversized = max(0, len(value) - limit)
    return rows, malformed, oversized


def _project_reference(project_state: object, message_words: set[str], now: datetime) -> tuple[dict[str, Any] | None, UnifiedMemoryReference | None]:
    project = _mapping(project_state)
    if not project:
        return None, None
    bounded = {key: project.get(key) for key in list(project)[:MAX_PROJECT_FIELDS] if key in {
        "id", "name", "description", "current_milestone", "next_recommended_arc", "language",
        "source_root", "path", "status", "updated_at", "created_at",
    }}
    bounded["type"] = "active_project_context"
    bounded["memory_domain"] = "project"
    bounded["source"] = "project_manager"
    return bounded, _reference(bounded, "project", message_words, now)




def _prior_unified_memory_receipts(rows: object, *, now: datetime) -> dict[str, Any]:
    """Validate bounded prior diagnostics without importing memory content."""
    if rows is None:
        rows = ()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return {"verified": 0, "stale": 0, "rejected": 1, "replayed": 0, "oversized": 0, "domains": [], "posture": "", "recovery": "malformed_receipt_collection"}
    oversized = max(0, len(rows) - MAX_RECEIPT_COLLECTION_ROWS)
    if oversized:
        return {"verified": 0, "stale": 0, "rejected": 0, "replayed": 0, "oversized": oversized, "domains": [], "posture": "", "recovery": "oversized_receipt_collection"}
    verified = stale = rejected = replayed = 0
    domains: set[str] = set()
    posture = ""
    seen: set[str] = set()
    for row in list(rows)[:MAX_PRIOR_RECEIPTS]:
        if not isinstance(row, Mapping):
            rejected += 1
            continue
        candidate = row.get("unified_memory_runtime_diagnostics")
        if not isinstance(candidate, Mapping):
            cognitive = row.get("cognitive_context")
            candidate = cognitive.get("unified_memory_runtime_diagnostics") if isinstance(cognitive, Mapping) else None
        if not isinstance(candidate, Mapping):
            continue
        candidate = dict(candidate)
        digest = str(candidate.get("diagnostics_digest") or "")
        if not verify_unified_memory_runtime_diagnostics(candidate):
            rejected += 1
            continue
        if digest in seen:
            replayed += 1
            continue
        seen.add(digest)
        created = _parse_time(row.get("created_at") or row.get("timestamp") or candidate.get("created_at"))
        if created is not None and (now - created).total_seconds() > 7 * 86400:
            stale += 1
            continue
        verified += 1
        posture = str(candidate.get("coordination_posture") or posture)
        for domain in candidate.get("domains_contributing") or ():
            if domain in MEMORY_DOMAINS:
                domains.add(domain)
    recovery = "none"
    if rejected:
        recovery = "invalid_prior_receipt"
    elif replayed:
        recovery = "replayed_prior_receipt"
    elif stale and not verified:
        recovery = "stale_prior_receipt"
    return {"verified": verified, "stale": stale, "rejected": rejected, "replayed": replayed, "oversized": oversized, "domains": sorted(domains), "posture": posture, "recovery": recovery}


def _provenance_summary(references: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    sources: dict[str, int] = {}
    owners: dict[str, int] = {}
    confidence: dict[str, int] = {}
    anomalies = 0
    for ref in references:
        source = str(ref.get("source") or "unknown")[:80]
        owner = str(ref.get("ownership") or "system")[:40]
        band = str(ref.get("confidence_band") or "unknown")[:20]
        if owner not in {"user", "operator", "project", "eidolon", "system"}:
            anomalies += 1
        if band not in {"high", "medium", "low", "unknown"}:
            anomalies += 1
        if str(ref.get("authority") or "none") != "none":
            anomalies += 1
        sources[source] = sources.get(source, 0) + 1
        owners[owner] = owners.get(owner, 0) + 1
        confidence[band] = confidence.get(band, 0) + 1
    bounded_sources = dict(sorted(sources.items(), key=lambda item: (-item[1], item[0]))[:MAX_PROVENANCE_SOURCES])
    return {
        "source_counts": bounded_sources,
        "ownership_counts": dict(sorted(owners.items())),
        "confidence_counts": dict(sorted(confidence.items())),
        "source_count": len(sources),
        "provenance_anomalies": anomalies,
        "provenance_complete": anomalies == 0 and all(bool(ref.get("source")) and bool(ref.get("ownership")) for ref in references),
    }

def build_unified_memory_evidence(
    message: object,
    *,
    memory_records: object = None,
    conversation_history: object = None,
    project_state: object = None,
    protected_operator_constraints: Iterable[str] = (),
    prior_unified_memory_receipts: object = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build content-free evidence plus an internal immutable selection.

    Returned ``selected_memory_records`` are copied records used only by the
    caller to assemble the already-existing prompt sections. They are excluded
    from policy, diagnostics, and prompt projection.
    """
    current_time = now or datetime.now(timezone.utc)
    prior = _prior_unified_memory_receipts(prior_unified_memory_receipts, now=current_time)
    literal_message = str(message or "")[:MAX_TEXT_SCAN_CHARS]
    message_words = _words(literal_message)
    memory_rows, malformed_memory_rows, oversized_memory_rows = _bounded_rows(memory_records, MAX_MEMORY_ROWS)
    history_rows, malformed_history_rows, oversized_history_rows = _bounded_rows(conversation_history, MAX_HISTORY_ROWS)

    candidates: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}
    for record in memory_rows:
        eligible, reason = _status_eligible(record)
        if not eligible:
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            continue
        domain = _domain(record)
        ref = _reference(record, domain, message_words, current_time)
        candidates.append({"record": dict(record), "reference": ref.to_dict(), "fact_key": _fact_key(record)})

    for index, record in enumerate(history_rows):
        safe = {
            "id": record.get("turn_id") or record.get("id") or f"bounded-history-{index}",
            "type": "conversation_history_reference",
            "role": record.get("role") or ("user" if record.get("user_message") else "assistant"),
            "content": record.get("content") or record.get("user_message") or record.get("assistant_response") or "",
            "created_at": record.get("created_at") or record.get("timestamp") or "",
            "source": "conversation_session",
            "memory_domain": "conversational",
        }
        eligible, reason = _status_eligible(safe)
        if not eligible:
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            continue
        ref = _reference(safe, "conversational", message_words, current_time)
        candidates.append({"record": None, "reference": ref.to_dict(), "fact_key": ""})

    project_record, project_ref = _project_reference(project_state, message_words, current_time)
    if project_ref is not None:
        candidates.append({"record": None, "reference": project_ref.to_dict(), "fact_key": str((project_record or {}).get("id") or "active_project")})

    duplicate_references_omitted = 0
    deduplicated: list[dict[str, Any]] = []
    by_content: dict[str, int] = {}
    by_reference: dict[str, int] = {}
    for candidate in sorted(candidates, key=lambda row: _rank(row["reference"]), reverse=True):
        ref = candidate["reference"]
        duplicate_index = by_reference.get(ref["reference_key"])
        if duplicate_index is None:
            duplicate_index = by_content.get(ref["content_digest"])
        if duplicate_index is not None:
            duplicate_references_omitted += 1
            continue
        by_reference[ref["reference_key"]] = len(deduplicated)
        by_content[ref["content_digest"]] = len(deduplicated)
        deduplicated.append(candidate)

    conflict_groups_detected = 0
    conflicting_references_suppressed = 0
    conflict_winners: set[str] = set()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in deduplicated:
        key = str(candidate.get("fact_key") or "")
        if key:
            grouped.setdefault(key, []).append(candidate)
    for rows in grouped.values():
        digests = {row["reference"]["content_digest"] for row in rows}
        if len(digests) <= 1:
            continue
        conflict_groups_detected += 1
        corrected = [row for row in rows if row["reference"].get("explicit_correction")]
        winner = max(corrected or rows, key=lambda row: _rank(row["reference"]))
        conflict_winners.add(winner["reference"]["reference_key"])
        conflicting_references_suppressed += len(rows) - 1

    selected_candidates: list[dict[str, Any]] = []
    for candidate in deduplicated:
        key = str(candidate.get("fact_key") or "")
        rows = grouped.get(key, []) if key else []
        if len({row["reference"]["content_digest"] for row in rows}) > 1:
            if candidate["reference"]["reference_key"] not in conflict_winners:
                continue
        selected_candidates.append(candidate)

    selected_memory_records = [dict(row["record"]) for row in selected_candidates if isinstance(row.get("record"), dict)][:MAX_SELECTED_ROWS]
    selected_references = [dict(row["reference"]) for row in selected_candidates]
    provenance = _provenance_summary(selected_references)
    candidate_counts = {domain: 0 for domain in MEMORY_DOMAINS}
    selected_counts = {domain: 0 for domain in MEMORY_DOMAINS}
    for row in candidates:
        candidate_counts[row["reference"]["domain"]] += 1
    for row in selected_references:
        selected_counts[row["domain"]] += 1

    constraints = tuple(sorted({str(item)[:80] for item in protected_operator_constraints if str(item).strip()}))
    protected_constraints_present = bool(constraints)
    authority_conflict_suppressed = bool(rejection_counts.get("forged_authority"))
    malformed_rows = malformed_memory_rows + malformed_history_rows
    oversized_rows = oversized_memory_rows + oversized_history_rows
    evidence_integrity = "degraded" if malformed_rows or authority_conflict_suppressed or rejection_counts.get("private_reasoning_field") or prior["rejected"] or prior["oversized"] or provenance["provenance_anomalies"] else "valid"
    domains_contributing = [domain for domain in MEMORY_DOMAINS if selected_counts[domain] > 0]
    reasons: dict[str, str] = {}
    for domain in domains_contributing:
        if domain == "conversational":
            reasons[domain] = "bounded_recent_conversation"
        elif domain == "relationship":
            reasons[domain] = "explicit_relationship_continuity"
        elif domain == "project":
            reasons[domain] = "active_project_or_project_record"
        elif domain == "semantic":
            reasons[domain] = "durable_fact_or_belief"
        else:
            reasons[domain] = "durable_experience"

    evidence = {
        "contract_version": CONTRACT_VERSION,
        "evidence_integrity": evidence_integrity,
        "memory_domains": list(MEMORY_DOMAINS),
        "candidate_counts": candidate_counts,
        "selected_counts": selected_counts,
        "domains_contributing": domains_contributing,
        "contribution_reasons": reasons,
        "duplicate_references_omitted": duplicate_references_omitted,
        "conflict_groups_detected": conflict_groups_detected,
        "conflicting_references_suppressed": conflicting_references_suppressed,
        "inactive_or_private_records_ignored": sum(rejection_counts.values()),
        "malformed_rows_ignored": malformed_rows,
        "oversized_rows_ignored": oversized_rows,
        "authority_conflict_suppressed": authority_conflict_suppressed,
        "prior_receipts_verified": prior["verified"],
        "prior_receipts_stale": prior["stale"],
        "prior_receipts_rejected": prior["rejected"],
        "prior_receipts_replayed": prior["replayed"],
        "prior_receipts_oversized": prior["oversized"],
        "prior_domains_contributing": list(prior["domains"]),
        "prior_coordination_posture": prior["posture"],
        "prior_receipt_recovery": prior["recovery"],
        "provenance_source_count": provenance["source_count"],
        "provenance_anomalies": provenance["provenance_anomalies"],
        "provenance_source_counts": provenance["source_counts"],
        "provenance_ownership_counts": provenance["ownership_counts"],
        "provenance_confidence_counts": provenance["confidence_counts"],
        "provenance_complete": provenance["provenance_complete"],
        "protected_constraints_present": protected_constraints_present,
        "current_message_precedence": True,
        "explicit_correction_precedence": True,
        "provenance_preserved": True,
        "physical_store_merge_performed": False,
        "memory_mutation_performed": False,
        "retrieval_provider_contacted": False,
        "contains_message_content": False,
        "contains_memory_text": False,
        "contains_project_text": False,
        "contains_private_reasoning": False,
        "authority": "none",
    }
    evidence["evidence_digest"] = _digest(evidence)
    evidence["selected_memory_records"] = selected_memory_records
    evidence["selected_references"] = selected_references
    return evidence


def build_unified_memory_policy(evidence: object) -> dict[str, Any]:
    value = _mapping(evidence)
    supplied = str(value.get("evidence_digest") or "")
    unsigned = {k: v for k, v in value.items() if k not in {"evidence_digest", "selected_memory_records", "selected_references"}}
    digest_valid = len(supplied) == 64 and _digest(unsigned) == supplied
    integrity = str(value.get("evidence_integrity") or "degraded")
    selected_counts = value.get("selected_counts") if isinstance(value.get("selected_counts"), Mapping) else {}
    domains = [domain for domain in MEMORY_DOMAINS if int(selected_counts.get(domain, 0) or 0) > 0]
    prior_verified = int(value.get("prior_receipts_verified") or 0)
    prior_replayed = int(value.get("prior_receipts_replayed") or 0)
    prior_recovery = str(value.get("prior_receipt_recovery") or "none")
    recovered = not digest_valid or integrity != "valid"
    if recovered:
        domains = []
        posture = "literal_request_only_recovery"
    elif len(domains) >= 2:
        posture = "cross_domain_continuity" if prior_verified else "cross_domain_grounded"
    elif domains:
        posture = "single_domain_grounded"
    else:
        posture = "current_request_without_memory"
    policy = {
        "contract_version": CONTRACT_VERSION,
        "coordination_posture": posture,
        "domains_contributing": domains,
        "domain_count": len(domains),
        "continuity_disposition": "recover_literal_request" if recovered else ("resume_verified_cross_domain_context" if prior_verified and domains else "use_current_selection"),
        "prior_receipts_verified": prior_verified,
        "prior_receipts_replayed": prior_replayed,
        "prior_receipts_oversized": int(value.get("prior_receipts_oversized") or 0),
        "prior_receipt_recovery": prior_recovery,
        "provenance_complete": bool(value.get("provenance_complete")),
        "provenance_source_count": int(value.get("provenance_source_count") or 0),
        "provenance_anomalies": int(value.get("provenance_anomalies") or 0),
        "current_message_precedence": True,
        "explicit_correction_precedence": True,
        "preserve_source_provenance": True,
        "preserve_historical_truth": True,
        "silently_rewrite_conflicts": False,
        "physical_store_merge_permitted": False,
        "memory_mutation_permitted": False,
        "learning_mutation_permitted": False,
        "tool_use_permitted": False,
        "action_execution_permitted": False,
        "approval_granted": False,
        "authority": "none",
        "policy_recovered": recovered,
        "recovery_reason": "invalid_or_degraded_evidence" if recovered else "none",
        "content_free": True,
        "evidence_digest": supplied if digest_valid else "",
    }
    policy["policy_digest"] = _digest(policy)
    return policy


def build_unified_memory_runtime_projection(
    message: object,
    *,
    memory_records: object = None,
    conversation_history: object = None,
    project_state: object = None,
    protected_operator_constraints: Iterable[str] = (),
    prior_unified_memory_receipts: object = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    evidence = build_unified_memory_evidence(
        message,
        memory_records=memory_records,
        conversation_history=conversation_history,
        project_state=project_state,
        protected_operator_constraints=protected_operator_constraints,
        prior_unified_memory_receipts=prior_unified_memory_receipts,
        now=now,
    )
    policy = build_unified_memory_policy(evidence)
    selected_memory_records = [] if policy["policy_recovered"] else [dict(row) for row in evidence["selected_memory_records"]]
    public = dict(policy)
    prompt = '<unified_memory_context data_only="true" authority="none">' + json.dumps(public, sort_keys=True, separators=(",", ":")) + '</unified_memory_context>'
    if len(prompt) > MAX_PROMPT_CHARS:
        policy = build_unified_memory_policy({})
        selected_memory_records = []
        public = dict(policy)
        prompt = '<unified_memory_context data_only="true" authority="none">' + json.dumps(public, sort_keys=True, separators=(",", ":")) + '</unified_memory_context>'
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "coordination_posture": policy["coordination_posture"],
        "domains_contributing": list(policy["domains_contributing"]),
        "domain_count": policy["domain_count"],
        "continuity_disposition": policy["continuity_disposition"],
        "prior_receipts_verified": policy["prior_receipts_verified"],
        "prior_receipts_replayed": policy["prior_receipts_replayed"],
        "prior_receipts_oversized": policy["prior_receipts_oversized"],
        "prior_receipt_recovery": policy["prior_receipt_recovery"],
        "provenance_complete": policy["provenance_complete"],
        "provenance_source_count": policy["provenance_source_count"],
        "provenance_anomalies": policy["provenance_anomalies"],
        "candidate_counts": dict(evidence.get("candidate_counts") or {}),
        "selected_counts": dict(evidence.get("selected_counts") or {}),
        "contribution_reasons": dict(evidence.get("contribution_reasons") or {}),
        "duplicate_references_omitted": int(evidence.get("duplicate_references_omitted") or 0),
        "conflict_groups_detected": int(evidence.get("conflict_groups_detected") or 0),
        "conflicting_references_suppressed": int(evidence.get("conflicting_references_suppressed") or 0),
        "policy_recovered": policy["policy_recovered"],
        "recovery_reason": policy["recovery_reason"],
        "provider_contacted": False,
        "memory_mutated": False,
        "authority": "none",
        "content_free": True,
        "policy_digest": policy["policy_digest"],
    }
    diagnostics["diagnostics_digest"] = _digest(diagnostics)
    return {
        "policy": policy,
        "prompt_section": prompt,
        "diagnostics": diagnostics,
        "selected_memory_records": selected_memory_records,
        "selected_references": [dict(row) for row in evidence.get("selected_references") or ()],
        "evidence": {k: v for k, v in evidence.items() if k not in {"selected_memory_records", "selected_references"}},
    }


def verify_unified_memory_runtime_diagnostics(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("diagnostics_digest") or "")
    unsigned = {k: v for k, v in value.items() if k != "diagnostics_digest"}
    return (
        len(supplied) == 64
        and _digest(unsigned) == supplied
        and value.get("authority") == "none"
        and value.get("content_free") is True
        and value.get("provider_contacted") is False
        and value.get("memory_mutated") is False
    )


def audit_unified_memory_selection(value: object) -> dict[str, Any]:
    """Return a content-free compliance audit for a transient unified selection."""
    projection = _mapping(value)
    policy = _mapping(projection.get("policy"))
    evidence = _mapping(projection.get("evidence"))
    selected = projection.get("selected_memory_records")
    invalid_collection = not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray))
    rows = [] if invalid_collection else list(selected)[:MAX_AUDIT_SELECTED_REFERENCES]
    oversized = 0 if invalid_collection else max(0, len(selected) - MAX_AUDIT_SELECTED_REFERENCES)
    malformed = authority_violations = private_field_violations = domain_violations = 0
    for row in rows:
        if not isinstance(row, Mapping):
            malformed += 1
            continue
        domain = _domain(row)
        if domain not in MEMORY_DOMAINS:
            domain_violations += 1
        if any(key in row and row.get(key) not in {False, None, "", 0} for key in _AUTHORITY_KEYS):
            authority_violations += 1
        if any(key in row for key in _PRIVATE_REASONING_KEYS):
            private_field_violations += 1
    recovered_with_selection = bool(policy.get("policy_recovered")) and bool(rows)
    provenance_violation = int(policy.get("provenance_anomalies") or 0) > 0 or evidence.get("provenance_preserved") is not True
    compliant = not any((invalid_collection, oversized, malformed, authority_violations, private_field_violations, domain_violations, recovered_with_selection, provenance_violation))
    audit = {
        "contract_version": CONTRACT_VERSION,
        "selected_count": len(rows),
        "invalid_collection": invalid_collection,
        "oversized_count": oversized,
        "malformed_count": malformed,
        "authority_violation_count": authority_violations,
        "private_field_violation_count": private_field_violations,
        "domain_violation_count": domain_violations,
        "recovered_with_selection": recovered_with_selection,
        "provenance_violation": provenance_violation,
        "compliant": compliant,
        "contains_memory_text": False,
        "contains_private_reasoning": False,
        "authority": "none",
        "content_free": True,
    }
    audit["audit_digest"] = _digest(audit)
    return audit


def verify_unified_memory_selection_audit(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("audit_digest") or "")
    unsigned = {k: v for k, v in value.items() if k != "audit_digest"}
    return (
        len(supplied) == 64
        and _digest(unsigned) == supplied
        and value.get("authority") == "none"
        and value.get("content_free") is True
        and value.get("contains_memory_text") is False
        and value.get("contains_private_reasoning") is False
    )
