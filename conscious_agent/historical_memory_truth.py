from __future__ import annotations

"""Attributable historical-memory truth boundary for ordinary conversation.

This module never writes memory or public conversation content.  It classifies the
already-selected memory candidates by provenance and literal relevance, then exposes
only content-free diagnostics publicly.  Private evidence text is bounded and may be
used only for the current user-visible answer/provider prompt.
"""

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Iterable, Mapping

from memory_provenance_integrity import classify_memory_provenance


_MAX_EVIDENCE_RECORDS = 3
_MAX_EVIDENCE_CHARS = 900

_HISTORICAL_QUERY = re.compile(
    r"\b(?:do you remember|can you remember|what do you remember|remember what|"
    r"what did (?:i|we|you) (?:tell|say|discuss|talk about|work on|struggle with)|"
    r"what (?:difficulties|problems|issues|challenges) (?:have|did) (?:we|i|you)|"
    r"what (?:difficulties|problems|issues|challenges) (?:had|have) (?:occurred|happened|come up)|"
    r"what have we (?:discussed|talked about|worked on|gone through|struggled with)|"
    r"what happened (?:before|earlier|last time)|"
    r"what evidence (?:supports|supported|do you have for)|what (?:record|records|evidence) (?:supports|support|supported))\b",
    re.I,
)
_EVIDENCE_REQUEST = re.compile(
    r"\b(?:what evidence|what records?|show (?:me )?(?:the )?evidence|what supports|what supported|"
    r"evidence (?:for|supports|supported)|supporting (?:record|evidence)|how do you know|what is that based on)\b",
    re.I,
)
_ASSISTANT_TARGET = re.compile(
    r"\b(?:what did you (?:say|tell|promise|claim)|what have you (?:said|promised|claimed)|"
    r"did you (?:say|promise|claim)|your (?:promise|statement|claim))\b",
    re.I,
)

_STOP = {
    "about", "after", "again", "before", "can", "could", "detail", "details", "did", "difficulties",
    "difficulty", "discussed", "discussion", "do", "earlier", "evidence", "from", "have", "history", "how",
    "issue", "issues", "just", "know", "last", "memory", "problems", "problem", "record", "records", "remember",
    "said", "say", "shared", "something", "support", "supports", "tell", "that", "the", "this", "told", "what",
    "when", "where", "which", "with", "would", "you", "your", "our", "were", "was", "are", "and", "for",
    "had", "has", "been", "we", "they", "them", "then", "there", "thing", "things", "challenge", "challenges",
}


def _compact(value: Any, limit: int = _MAX_EVIDENCE_CHARS) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _digest(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _terms(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) >= 3 and token not in _STOP
    }


def historical_memory_query_requested(message: str) -> bool:
    return bool(_HISTORICAL_QUERY.search(str(message or "")))


def _content(record: Mapping[str, Any]) -> str:
    return _compact(record.get("content") or record.get("text") or record.get("summary"))


def _provenance_class(record: Mapping[str, Any], content: str) -> tuple[str, bool]:
    """Return (class, provenance_valid).  Ambiguity fails closed."""
    integrity = record.get("provenance_integrity") if isinstance(record.get("provenance_integrity"), Mapping) else None
    if integrity is not None:
        profile = classify_memory_provenance(record)
        if profile.quarantined or not profile.provenance_valid:
            return "malformed_or_unattributed", False
        if profile.provenance_class == "user":
            return "user_authored", True
        if profile.provenance_class == "assistant":
            return "assistant_authored", True
        if profile.provenance_class == "action_receipt":
            return "action_receipt", True
        # Imported/unknown records remain non-evidence unless separately reviewed.
        return "malformed_or_unattributed", False
    kind = str(record.get("type") or "").strip().lower()
    role = str(record.get("role") or "").strip().lower()
    source = str(record.get("source") or record.get("origin") or "").strip().lower()
    attribution = record.get("memory_commit_attribution") if isinstance(record.get("memory_commit_attribution"), Mapping) else {}
    attribution_role = str(attribution.get("role") or "").strip().lower()
    provenance = record.get("provenance") if isinstance(record.get("provenance"), Mapping) else {}
    provenance_origin = str(provenance.get("origin") or "").strip().lower()

    if attribution:
        supplied_digest = str(attribution.get("content_digest") or "")
        if attribution_role not in {"user", "assistant"} or not supplied_digest or supplied_digest != _digest(content):
            return "malformed_or_unattributed", False
        required = (
            attribution.get("memory_candidate_id"), attribution.get("conversation_operation_id"),
            attribution.get("conversation_session_id"), attribution.get("conversation_turn_id"),
        )
        if not all(str(item or "").strip() for item in required):
            return "malformed_or_unattributed", False
        return ("user_authored" if attribution_role == "user" else "assistant_authored"), True

    # Bounded legacy attribution: a concrete conversation record still needs an
    # identity and source boundary.  Merely having semantically similar text is not
    # enough to become historical evidence.
    record_id = str(record.get("id") or record.get("memory_id") or record.get("conversation_turn_id") or "").strip()
    if kind == "conversation_user" or role == "user" or provenance_origin in {"user", "operator_input", "operator_explicit", "operator_reviewed_exact_content"} or bool(record.get("operator_explicit")) or source.startswith("operator_"):
        valid = bool(record_id and content and (source or provenance_origin or record.get("conversation_session_id")))
        return ("user_authored" if valid else "malformed_or_unattributed"), valid
    if kind == "conversation_eidolon" or role == "assistant" or provenance_origin in {"assistant", "eidolon", "generated_turn"}:
        valid = bool(record_id and content and (source or provenance_origin or record.get("conversation_session_id")))
        return ("assistant_authored" if valid else "malformed_or_unattributed"), valid
    if kind in {"action_receipt", "execution_receipt", "diagnostic_receipt"}:
        valid = bool(record_id and content and source)
        return ("action_receipt" if valid else "malformed_or_unattributed"), valid
    return "malformed_or_unattributed", False


def _match_strength(query_terms: set[str], content: str) -> tuple[str, int]:
    content_terms = _terms(content)
    overlap = query_terms & content_terms
    if not query_terms or not overlap:
        return "none", 0
    ratio = len(overlap) / max(1, len(query_terms))
    if len(overlap) >= 3 or ratio >= 0.60:
        return "strong", len(overlap)
    if len(overlap) >= 2 or (len(query_terms) <= 2 and len(overlap) == 1):
        return "bounded", len(overlap)
    return "weak", len(overlap)


_USER_ASSERTION = re.compile(
    r"\b(?:i|we)\s+(?:had|have had|was|were|did|said|told|experienced|struggled|missed|felt|went|worked|decided|changed|moved|kept|used|needed)\b",
    re.I,
)

def _user_record_is_assertive(content: str) -> bool:
    text = str(content or "").strip()
    if not text:
        return False
    if "?" not in text:
        return True
    if re.match(r"(?i)^(?:what|when|where|why|how|do|did|does|have|has|can|could|would|were|was|are|is)\b", text):
        return False
    return bool(_USER_ASSERTION.search(text))


@dataclass(frozen=True)
class HistoricalMemoryTruthProfile:
    query_detected: bool = False
    evidence_requested: bool = False
    state: str = "not_historical"
    claim_target: str = "shared_or_user"
    attributable_evidence_available: bool = False
    uncertainty_required: bool = False
    relevant_candidate_count: int = 0
    user_authored_evidence_count: int = 0
    assistant_authored_candidate_count: int = 0
    user_nonassertive_candidate_count: int = 0
    action_receipt_evidence_count: int = 0
    malformed_or_unattributed_count: int = 0
    weak_match_rejected_count: int = 0
    conflicting_evidence_count: int = 0
    match_strength: str = "none"
    evidence_texts: tuple[str, ...] = ()
    evidence_classes: tuple[str, ...] = ()
    content_free: bool = True

    def public_summary(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("evidence_texts", None)
        return data

    def prompt_block(self) -> str:
        if not self.query_detected:
            return ""
        if self.uncertainty_required or not self.attributable_evidence_available:
            return (
                "HISTORICAL MEMORY TRUTH\n"
                "No attributable historical memory evidence is available for this request. State that uncertainty plainly "
                "instead of constructing a plausible memory. Do not convert assistant suggestions, capability statements, "
                "generic term overlap, embedding proximity, malformed provenance, or conflicting records into events."
            )
        lines = [
            "ATTRIBUTABLE HISTORICAL EVIDENCE",
            "Use only the bounded records below. Do not add historical claims that are not directly supported by them.",
        ]
        for index, (text, provenance) in enumerate(zip(self.evidence_texts, self.evidence_classes), start=1):
            lines.append(f"Evidence {index} ({provenance}): {text}")
        if self.evidence_requested:
            lines.append("The user requested evidence: identify the supporting provenance class in ordinary language without exposing private paths or internal payloads.")
        return "\n".join(lines)

    def deterministic_response(self) -> str:
        if not self.query_detected:
            return ""
        if self.state == "assistant_authored_non_evidence":
            return (
                "I don't have an attributable user record supporting that as part of our shared history. "
                "I found only assistant-authored material, and that is not evidence that you experienced or discussed those events."
            )
        if self.state == "conflicting_memory_evidence":
            return (
                "I found conflicting attributable records, so I can't honestly turn them into one historical account. "
                "I should treat that history as uncertain until the conflict is resolved."
            )
        if self.state == "malformed_or_unattributed_memory":
            return (
                "I found memory material without trustworthy attribution, so I can't use it as evidence of our history. "
                "I don't have enough attributable support to make that claim."
            )
        if self.uncertainty_required or not self.attributable_evidence_available:
            return "I don't have an attributable memory record supporting that history, so I can't honestly claim those events happened."
        if self.evidence_texts:
            if len(self.evidence_texts) == 1:
                body = f"The attributable record supports this much: {self.evidence_texts[0]}"
            else:
                body = "The attributable records support these points: " + " | ".join(self.evidence_texts)
            if self.evidence_requested:
                classes = ", ".join(dict.fromkeys(self.evidence_classes))
                body += f" Evidence: {classes.replace('_', '-')} attributable record."
            return body
        return ""


def build_historical_memory_truth(
    message: str,
    memories: Iterable[dict[str, Any]] = (),
) -> HistoricalMemoryTruthProfile:
    text = _compact(message, 1800)
    if not historical_memory_query_requested(text):
        return HistoricalMemoryTruthProfile()

    query_terms = _terms(text)
    evidence_requested = bool(_EVIDENCE_REQUEST.search(text))
    target = "assistant" if _ASSISTANT_TARGET.search(text) else "shared_or_user"
    candidates: list[dict[str, Any]] = []
    assistant_relevant = malformed_relevant = weak_rejected = user_nonassertive = 0
    strongest = "none"
    strength_rank = {"none": 0, "weak": 1, "bounded": 2, "strong": 3}

    for raw in memories:
        if not isinstance(raw, Mapping):
            malformed_relevant += 1
            continue
        content = _content(raw)
        if not content:
            continue
        strength, overlap = _match_strength(query_terms, content)
        if strength == "none":
            continue
        if strength == "weak":
            weak_rejected += 1
            continue
        provenance_class, provenance_valid = _provenance_class(raw, content)
        if not provenance_valid:
            malformed_relevant += 1
            continue
        strongest = strength if strength_rank[strength] > strength_rank[strongest] else strongest
        if provenance_class == "user_authored" and target != "assistant" and not _user_record_is_assertive(content):
            user_nonassertive += 1
            continue
        if provenance_class == "assistant_authored" and target != "assistant":
            assistant_relevant += 1
            continue
        if provenance_class not in {"user_authored", "assistant_authored", "action_receipt"}:
            malformed_relevant += 1
            continue
        candidates.append({
            "text": content,
            "class": provenance_class,
            "strength": strength,
            "overlap": overlap,
            "fact_key": str(raw.get("fact_key") or raw.get("subject_key") or raw.get("memory_key") or "").strip().lower()[:160],
            "digest": _digest(content),
        })

    conflict_count = 0
    by_fact: dict[str, set[str]] = {}
    for row in candidates:
        if row["fact_key"]:
            by_fact.setdefault(row["fact_key"], set()).add(row["digest"])
    conflict_count = sum(max(0, len(digests) - 1) for digests in by_fact.values() if len(digests) > 1)

    if conflict_count:
        state = "conflicting_memory_evidence"
        selected: list[dict[str, Any]] = []
        uncertainty = True
    elif candidates:
        candidates.sort(key=lambda row: (strength_rank[row["strength"]], row["overlap"]), reverse=True)
        selected = candidates[:_MAX_EVIDENCE_RECORDS]
        state = "supported_user_authored_memory" if any(row["class"] == "user_authored" for row in selected) else "supported_attributable_memory"
        uncertainty = False
    elif assistant_relevant:
        selected = []
        state = "assistant_authored_non_evidence"
        uncertainty = True
    elif malformed_relevant:
        selected = []
        state = "malformed_or_unattributed_memory"
        uncertainty = True
    else:
        selected = []
        state = "unsupported_historical_memory"
        uncertainty = True

    return HistoricalMemoryTruthProfile(
        query_detected=True,
        evidence_requested=evidence_requested,
        state=state,
        claim_target=target,
        attributable_evidence_available=bool(selected),
        uncertainty_required=uncertainty,
        relevant_candidate_count=len(candidates) + assistant_relevant + malformed_relevant + weak_rejected + user_nonassertive,
        user_authored_evidence_count=sum(1 for row in selected if row["class"] == "user_authored"),
        assistant_authored_candidate_count=assistant_relevant + sum(1 for row in selected if row["class"] == "assistant_authored"),
        user_nonassertive_candidate_count=user_nonassertive,
        action_receipt_evidence_count=sum(1 for row in selected if row["class"] == "action_receipt"),
        malformed_or_unattributed_count=malformed_relevant,
        weak_match_rejected_count=weak_rejected,
        conflicting_evidence_count=conflict_count,
        match_strength=strongest,
        evidence_texts=tuple(row["text"] for row in selected),
        evidence_classes=tuple(row["class"] for row in selected),
    )
