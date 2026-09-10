from __future__ import annotations

"""Era 5 relationship and companion continuity.

This layer reads explicit durable relationship memories and bounded completed-turn
metadata.  It does not create a second relationship store, infer private feelings,
or send proactive messages.  It prepares content-free continuity candidates for
the later governed proactive-communication architecture.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "v1999.9"
SCHEMA_VERSION = "1"
MAX_MEMORIES = 96
MAX_HISTORY = 32
MAX_CANDIDATES = 4

_EXCLUDED = {"rejected", "retracted", "stale", "expired", "deleted", "blocked", "superseded"}
_REL_TYPES = {
    "relationship", "relationship_memory", "preference", "user_preference", "nickname", "preferred_name",
    "user_nickname", "important_moment", "shared_moment", "commitment", "personal_fact", "boundary",
    "relationship_boundary", "affection_preference", "relationship_milestone", "trust",
}
_TRUST = re.compile(r"\btrust\b", re.I)
_AFFECTION = re.compile(r"\b(?:affection|hug|love|warm|nickname|pet name)\b", re.I)
_BOUNDARY = re.compile(r"\b(?:boundary|don't call me|do not call me|never call me|stop calling me|not comfortable)\b", re.I)
_CORRECTION = re.compile(r"\b(?:actually|correction|you misunderstood|that's wrong|that is wrong|i meant)\b", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _memory_type(row: Mapping[str, Any]) -> str:
    return str(row.get("type") or row.get("memory_type") or "").strip().lower()


def _eligible(row: Mapping[str, Any]) -> bool:
    if _memory_type(row) not in _REL_TYPES:
        return False
    state = str(row.get("status") or row.get("state") or "active").strip().lower()
    if state in _EXCLUDED:
        return False
    provenance = row.get("provenance_integrity") if isinstance(row.get("provenance_integrity"), Mapping) else {}
    pclass = str(provenance.get("provenance_class") or row.get("provenance_class") or "").strip().lower()
    if pclass in {"assistant", "generated", "reflection", "unknown"} and not row.get("operator_curated"):
        return False
    return bool(row.get("relationship_eligible") is True or row.get("use_in_conversation") is True or pclass == "user" or row.get("operator_curated"))


def _text(row: Mapping[str, Any]) -> str:
    return " ".join(str(row.get("content") or row.get("thought") or row.get("summary") or "")[:320].split())


def _memories(rows: Iterable[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    if rows is None or isinstance(rows, (str, bytes, dict)):
        return []
    result: list[Mapping[str, Any]] = []
    try:
        iterable = list(rows)[-MAX_MEMORIES:]
    except Exception:
        return []
    for row in iterable:
        if isinstance(row, Mapping) and _eligible(row):
            result.append(row)
    return result


def _history(rows: Iterable[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    if rows is None or isinstance(rows, (str, bytes, dict)):
        return []
    try:
        material = [row for row in list(rows)[-MAX_HISTORY:] if isinstance(row, Mapping)]
    except Exception:
        return []
    return [row for row in material if row.get("success") is not False and str(row.get("status") or "").lower() not in _EXCLUDED]


def _category_counts(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = {
        "trust": 0,
        "nickname": 0,
        "preference": 0,
        "boundary": 0,
        "milestone": 0,
        "important_moment": 0,
        "commitment": 0,
        "affection_style": 0,
    }
    for row in rows:
        kind = _memory_type(row)
        text = _text(row)
        if kind in {"nickname", "preferred_name", "user_nickname"}:
            counts["nickname"] += 1
        if kind in {"preference", "user_preference"}:
            counts["preference"] += 1
        if kind in {"boundary", "relationship_boundary"} or _BOUNDARY.search(text):
            counts["boundary"] += 1
        if kind in {"relationship_milestone"}:
            counts["milestone"] += 1
        if kind in {"important_moment", "shared_moment"}:
            counts["important_moment"] += 1
        if kind == "commitment":
            counts["commitment"] += 1
        if kind in {"affection_preference"} or _AFFECTION.search(text):
            counts["affection_style"] += 1
        if kind == "trust" or _TRUST.search(text):
            counts["trust"] += 1
    return counts


def _repair_evidence(history: list[Mapping[str, Any]]) -> tuple[int, int]:
    corrections = acknowledgements = 0
    for row in history:
        user = str(row.get("user_message") or "")[:512]
        assistant = str(row.get("assistant_response") or "")[:512].lower()
        if _CORRECTION.search(user):
            corrections += 1
            if any(marker in assistant for marker in ("you're right", "you are right", "i misunderstood", "i got", "correction", "i'll use", "i will use")):
                acknowledgements += 1
    return corrections, acknowledgements


@dataclass(frozen=True)
class RelationshipModel:
    explicit_relationship_evidence_count: int
    trust_basis: str
    familiarity_band: str
    nickname_count: int
    preference_count: int
    boundary_count: int
    milestone_count: int
    important_moment_count: int
    commitment_count: int
    affection_style_evidence_count: int
    correction_count: int
    acknowledged_repairs: int
    unresolved_repairs: int
    explicit_evidence_only: bool
    relationship_progress_inferred: bool
    user_feelings_inferred: bool
    dependency_or_exclusivity_inferred: bool
    content_free_public_evidence: bool = True
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_relationship_content": False,
            "contains_memory_content": False,
            "contains_conversation_content": False,
            "provider_contacted": False,
            "runtime_mutated": False,
        })
        result["relationship_digest"] = _digest(result)
        return result


@dataclass(frozen=True)
class ContinuityCandidate:
    candidate_kind: str
    source_digest: str
    relevance: float
    reason_code: str
    current_turn_use: str
    autonomous_delivery_authorized: bool
    notification_authorized: bool
    relationship_progress_claim_allowed: bool

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def build_relationship_model(
    memories: Iterable[Mapping[str, Any]] | None,
    *,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
) -> RelationshipModel:
    rows = _memories(memories)
    history = _history(conversation_history)
    counts = _category_counts(rows)
    corrections, repairs = _repair_evidence(history)
    evidence_count = len(rows)
    if evidence_count >= 8:
        familiarity = "well_established_explicit_context"
    elif evidence_count >= 3:
        familiarity = "established_explicit_context"
    elif evidence_count:
        familiarity = "limited_explicit_context"
    else:
        familiarity = "no_explicit_context"
    trust_basis = "explicitly_recorded" if counts["trust"] else "not_inferred"
    return RelationshipModel(
        explicit_relationship_evidence_count=evidence_count,
        trust_basis=trust_basis,
        familiarity_band=familiarity,
        nickname_count=counts["nickname"],
        preference_count=counts["preference"],
        boundary_count=counts["boundary"],
        milestone_count=counts["milestone"],
        important_moment_count=counts["important_moment"],
        commitment_count=counts["commitment"],
        affection_style_evidence_count=counts["affection_style"],
        correction_count=corrections,
        acknowledged_repairs=repairs,
        unresolved_repairs=max(0, corrections - repairs),
        explicit_evidence_only=True,
        relationship_progress_inferred=False,
        user_feelings_inferred=False,
        dependency_or_exclusivity_inferred=False,
    )


def build_continuity_candidates(
    model: RelationshipModel,
    *,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
    prior_candidate_receipts: Iterable[Mapping[str, Any]] | None = None,
) -> list[ContinuityCandidate]:
    history = _history(conversation_history)
    prior_kinds: list[str] = []
    if prior_candidate_receipts is not None and not isinstance(prior_candidate_receipts, (str, bytes, dict)):
        try:
            for row in list(prior_candidate_receipts)[-12:]:
                if isinstance(row, Mapping):
                    kind = str(row.get("candidate_kind") or "")
                    if kind:
                        prior_kinds.append(kind)
        except Exception:
            pass

    candidates: list[ContinuityCandidate] = []
    latest = history[-1] if history else {}
    last_assistant = str(latest.get("assistant_response") or "")[:1000]
    if "?" in last_assistant and prior_kinds.count("unfinished_thread") < 2:
        candidates.append(ContinuityCandidate(
            candidate_kind="unfinished_thread",
            source_digest=_digest({"kind": "unfinished_thread", "history_count": len(history)}),
            relevance=0.75,
            reason_code="prior_assistant_question_unresolved",
            current_turn_use="only_if_user_reopens_or_directly_relevant",
            autonomous_delivery_authorized=False,
            notification_authorized=False,
            relationship_progress_claim_allowed=False,
        ))
    if model.important_moment_count and prior_kinds.count("important_moment_check_in") < 1:
        candidates.append(ContinuityCandidate(
            candidate_kind="important_moment_check_in",
            source_digest=_digest({"kind": "important_moment", "count": model.important_moment_count}),
            relevance=0.62,
            reason_code="explicit_open_important_moment_available",
            current_turn_use="only_when_relevant_to_current_message",
            autonomous_delivery_authorized=False,
            notification_authorized=False,
            relationship_progress_claim_allowed=False,
        ))
    if model.unresolved_repairs and prior_kinds.count("repair_follow_up") < 1:
        candidates.append(ContinuityCandidate(
            candidate_kind="repair_follow_up",
            source_digest=_digest({"kind": "repair", "count": model.unresolved_repairs}),
            relevance=0.70,
            reason_code="explicit_correction_without_acknowledged_repair",
            current_turn_use="repair_if_current_topic_matches",
            autonomous_delivery_authorized=False,
            notification_authorized=False,
            relationship_progress_claim_allowed=False,
        ))
    return candidates[:MAX_CANDIDATES]


def build_relationship_companion_projection(
    memories: Iterable[Mapping[str, Any]] | None,
    *,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
    prior_candidate_receipts: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    model = build_relationship_model(memories, conversation_history=conversation_history)
    candidates = build_continuity_candidates(
        model,
        conversation_history=conversation_history,
        prior_candidate_receipts=prior_candidate_receipts,
    )
    public = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "relationship_model": model.public_summary(),
        "continuity_candidates": [candidate.public_summary() for candidate in candidates],
        "candidate_count": len(candidates),
        "proactive_message_sent": False,
        "autonomous_new_turn_permitted": False,
        "relationship_progress_inferred": False,
        "memory_mutated": False,
        "authority_granted": False,
    }
    public["projection_digest"] = _digest(public)
    prompt = (
        "ERA 5 RELATIONSHIP AND COMPANION CONTINUITY\n"
        f"Use only explicit relationship evidence: familiarity={model.familiarity_band}; nicknames={model.nickname_count}; "
        f"preferences={model.preference_count}; boundaries={model.boundary_count}; important moments={model.important_moment_count}.\n"
        "Keep warmth and continuity grounded in actual shared history. Do not infer trust, feelings, exclusivity, dependence, or relationship progress. "
        "Revisit unfinished topics only when the current message makes them relevant; do not nag, force check-ins, or create an autonomous new turn."
    )
    return {"ok": True, **public, "prompt_section": prompt}


__all__ = [
    "CONTRACT_VERSION", "RelationshipModel", "ContinuityCandidate", "build_relationship_model",
    "build_continuity_candidates", "build_relationship_companion_projection",
]
