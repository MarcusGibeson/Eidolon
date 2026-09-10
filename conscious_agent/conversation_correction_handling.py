from __future__ import annotations

"""Deterministic v1084.6 conversational correction handling.

The profile reacts only to explicit correction intent already established by the
turn-intent classifier. It does not infer corrections from ordinary ambiguity,
rewrite transcripts, mutate memories, or contact a provider.
"""

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from conversation_turn_intent import TurnIntentProfile

CORRECTION_HANDLING_SCHEMA_VERSION = "1"
MAX_CORRECTION_HISTORY_ROWS = 6

_CLARIFICATION_RE = re.compile(r"\b(?:i meant|what i meant was|to clarify|more precisely)\b", re.I)
_REPLACEMENT_RE = re.compile(r"\bnot\s+[^,.!?]{1,80}\b(?:but|rather)\b", re.I)
_REJECTION_RE = re.compile(
    r"^(?:no[,;:]\s+|correction\s*[:,-]\s*)|\b(?:that(?:'s| is) not (?:right|correct)|you (?:got|have) (?:that|it) wrong)\b",
    re.I,
)
_UPDATE_RE = re.compile(r"^actually[,;:]?\s+", re.I)
_ACK_RE = re.compile(
    r"\b(?:thanks for (?:the )?correction|thank you for correcting|you(?:'re| are) right|my mistake|got it[,;:]? corrected)\b",
    re.I,
)


@dataclass(frozen=True)
class CorrectionHandlingProfile:
    explicit_correction: bool
    correction_kind: str
    target_scope: str
    target_turn_offset: int | None
    acknowledge_once: bool
    stale_claim_suppression_required: bool
    defensive_repetition_allowed: bool
    repeated_acknowledgment_risk: bool
    correction_evidence_digest: str
    history_rows_considered: int
    ambiguous_correction_inferred: bool = False
    rewrites_transcript: bool = False
    mutates_memory: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = CORRECTION_HANDLING_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)

    def prompt_lines(self) -> list[str]:
        if not self.explicit_correction:
            return []
        lines = [
            "CONVERSATIONAL CORRECTION HANDLING",
            "Acknowledge the explicit correction briefly once, adopt the corrected premise immediately, and continue without arguing or over-apologizing.",
        ]
        if self.stale_claim_suppression_required:
            lines.append("Do not repeat, defend, or quietly reuse the corrected assistant claim in this reply.")
        if self.repeated_acknowledgment_risk:
            lines.append("A recent correction acknowledgment already exists; avoid another ceremonial apology and focus on the corrected substance.")
        lines.append("Do not rewrite prior transcript text or infer a broader correction than the user explicitly supplied.")
        return lines


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _assistant_text(row: Mapping[str, Any]) -> str:
    return _normalized(row.get("assistant_response") or row.get("assistant") or row.get("response"))


def _kind(message: str) -> str:
    if _REPLACEMENT_RE.search(message):
        return "explicit_replacement"
    if _CLARIFICATION_RE.search(message):
        return "clarification"
    if _REJECTION_RE.search(message):
        return "stale_claim_rejection"
    if _UPDATE_RE.search(message):
        return "factual_update"
    return "explicit_correction"


def build_correction_handling_profile(
    message: str,
    history: Iterable[Mapping[str, Any]],
    *,
    intent: TurnIntentProfile,
) -> CorrectionHandlingProfile:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_CORRECTION_HISTORY_ROWS:]
    explicit = bool(intent.explicit_correction)
    if not explicit:
        return CorrectionHandlingProfile(
            explicit_correction=False,
            correction_kind="none",
            target_scope="none",
            target_turn_offset=None,
            acknowledge_once=False,
            stale_claim_suppression_required=False,
            defensive_repetition_allowed=False,
            repeated_acknowledgment_risk=False,
            correction_evidence_digest="",
            history_rows_considered=len(rows),
        )

    latest_assistant_offset: int | None = None
    for offset, row in enumerate(reversed(rows)):
        if _assistant_text(row):
            latest_assistant_offset = offset
            break
    target_scope = "latest_assistant_claim" if latest_assistant_offset is not None else "current_conversation_premise"
    correction_kind = _kind(_normalized(message))
    recent_ack = any(_ACK_RE.search(_assistant_text(row)) for row in rows[-2:] if _assistant_text(row))
    material = f"{correction_kind}\n{target_scope}\n{latest_assistant_offset}\n{_normalized(message).casefold()}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

    return CorrectionHandlingProfile(
        explicit_correction=True,
        correction_kind=correction_kind,
        target_scope=target_scope,
        target_turn_offset=latest_assistant_offset,
        acknowledge_once=True,
        stale_claim_suppression_required=latest_assistant_offset is not None,
        defensive_repetition_allowed=False,
        repeated_acknowledgment_risk=recent_ack,
        correction_evidence_digest=digest,
        history_rows_considered=len(rows),
    )
