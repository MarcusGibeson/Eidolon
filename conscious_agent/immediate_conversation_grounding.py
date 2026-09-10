from __future__ import annotations

"""Provider-private immediate-turn grounding for ordinary conversation.

Current-message correction evidence takes precedence over previous-turn recall. Public
diagnostics remain content-free; private evidence text is bounded to the current turn.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable

from historical_memory_truth import HistoricalMemoryTruthProfile, build_historical_memory_truth
from active_conversation_facts import resolve_active_conversation_facts


_IMMEDIATE_RECALL = re.compile(
    r"\b(?:what did i just (?:say|tell|correct)|what i just corrected|what did i correct you (?:about|on)|"
    r"what was (?:my|the) correction|repeat (?:what i just (?:said|told you|corrected)|my correction)|"
    r"(?:summarize|identify|explain) (?:what i just corrected|my correction|the correction)|"
    r"what did i just correct you about)\b",
    re.I,
)
_EXACT_REPEAT = re.compile(
    r"\b(?:repeat|say|quote)\b[^\n]{0,50}\bexact(?:ly)?\b|\btell me exact(?:ly)?\b|\bverbatim\b",
    re.I,
)
_CORRECTION_SIGNAL = re.compile(
    r"\b(?:correction\s*:|i (?:need to )?(?:correct|clarify)|i told you|i said|i corrected you|actually\b|"
    r"that's not right|that is not right|you(?:'re| are) wrong|don't pretend to remember|"
    r"do not pretend to remember|the correct (?:fact|details?|version)|what actually happened|"
    r"to be clear|for the record|i meant|i didn't say|i did not say|it wasn't|it was not|"
    r"no[,;:]?\s+(?:it|the|that|i|we)\b)",
    re.I,
)
_RECALL_CLAUSE = re.compile(
    r"(?i)(?:^|(?<=[.!?;,\n]))\s*(?:(?:then|and)\s+)?(?:"
    r"tell me(?:\s+exactly)?\s+what i just corrected|repeat(?:\s+exactly)?\s+(?:what i just corrected|my correction)|"
    r"identify\s+(?:what i just corrected|my correction)|summarize\s+(?:what i just corrected|my correction)|"
    r"explain\s+(?:what i just corrected|my correction|the correction)|"
    r"what did i just correct(?: you)?(?: about| on)?|what was (?:my|the) correction)\b"
)
_COMPOUND_EXPLANATION = re.compile(
    r"\b(?:(?:then|and)\s+)?explain\b|\bwhat (?:should|would) you (?:have )?(?:said|done|answered)\b|"
    r"\bhow should you (?:have )?(?:handled|answered|responded)\b",
    re.I,
)
_UNCERTAINTY_EXPLANATION = re.compile(
    r"\b(?:no supporting memory|no support(?:ing)? (?:memory|record|evidence)|when (?:you are|you're) uncertain|"
    r"when evidence is (?:missing|unavailable)|without (?:a )?supporting (?:memory|record|evidence))\b",
    re.I,
)

_MAX_EVIDENCE_CHARS = 1400


@dataclass(frozen=True)
class ImmediateGroundingProfile:
    block: str = ""
    grounding_state: str = "none"
    immediate_recall_requested: bool = False
    exact_repeat_requested: bool = False
    current_message_correction: bool = False
    compound_explanation_requested: bool = False
    protected_recent_user_turn: bool = False
    protected_recent_correction: bool = False
    historical_memory_query: bool = False
    attributable_memory_available: bool = False
    historical_evidence_state: str = "not_historical"
    historical_evidence_requested: bool = False
    historical_user_authored_count: int = 0
    historical_assistant_authored_non_evidence_count: int = 0
    historical_user_nonassertive_count: int = 0
    historical_malformed_count: int = 0
    historical_conflict_count: int = 0
    historical_weak_match_rejected_count: int = 0
    historical_match_strength: str = "none"
    historical_uncertainty_required: bool = False
    active_fact_grounded: bool = False
    active_fact_kind: str = "none"
    active_fact_count: int = 0
    active_fact_correction_applied: bool = False
    active_fact_response: str = ""
    source_turn_offset: int = -1
    evidence_text: str = ""
    historical_evidence_texts: tuple[str, ...] = ()
    historical_evidence_classes: tuple[str, ...] = ()
    content_free: bool = True

    def historical_evidence_class_counts(self) -> dict[str, int]:
        # Content-free bounded class counts include both admissible evidence and
        # rejected provenance classes so operators can see why uncertainty won.
        counts: dict[str, int] = {
            "user_authored": min(99, int(self.historical_user_authored_count or 0)),
            "assistant_authored_non_evidence": min(99, int(self.historical_assistant_authored_non_evidence_count or 0)),
            "user_nonassertive": min(99, int(self.historical_user_nonassertive_count or 0)),
            "malformed_or_unattributed": min(99, int(self.historical_malformed_count or 0)),
            "conflicting": min(99, int(self.historical_conflict_count or 0)),
            "weak_match_rejected": min(99, int(self.historical_weak_match_rejected_count or 0)),
        }
        for value in self.historical_evidence_classes:
            key = str(value or "unknown")[:48]
            counts[key] = min(99, max(counts.get(key, 0), counts.get(key, 0) + 1))
        return {key: value for key, value in sorted(counts.items()) if value}

    def provenance_state_digest(self) -> str:
        payload = {
            "state": self.historical_evidence_state,
            "uncertainty_required": bool(self.historical_uncertainty_required),
            "attributable": bool(self.attributable_memory_available),
            "counts": self.historical_evidence_class_counts(),
            "user": int(self.historical_user_authored_count),
            "assistant": int(self.historical_assistant_authored_non_evidence_count),
            "malformed": int(self.historical_malformed_count),
            "conflict": int(self.historical_conflict_count),
            "weak": int(self.historical_weak_match_rejected_count),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def public_summary(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("block", None)
        data.pop("evidence_text", None)
        data.pop("historical_evidence_texts", None)
        data.pop("historical_evidence_classes", None)
        data.pop("active_fact_response", None)
        data["historical_evidence_class_counts"] = self.historical_evidence_class_counts()
        data["historical_provenance_state_digest"] = self.provenance_state_digest()
        return data

    def deterministic_response(self) -> str:
        """Return a provider-free response only when truth is fully attributable."""
        if self.active_fact_response:
            return self.active_fact_response
        if self.immediate_recall_requested and self.evidence_text:
            if self.current_message_correction:
                if self.compound_explanation_requested:
                    return (
                        f"{self.evidence_text}\n\n"
                        "When no supporting memory exists, I should say that I don't have an attributable record, "
                        "label the uncertainty plainly, and not invent or infer historical details."
                    )
                if self.exact_repeat_requested:
                    return self.evidence_text
                return f"You just corrected me: {self.evidence_text}"
            if self.protected_recent_user_turn:
                if self.exact_repeat_requested:
                    return self.evidence_text
                return f"You just told me: {self.evidence_text}"
        if self.historical_memory_query:
            profile = HistoricalMemoryTruthProfile(
                query_detected=True,
                evidence_requested=self.historical_evidence_requested,
                state=self.historical_evidence_state,
                attributable_evidence_available=self.attributable_memory_available,
                uncertainty_required=self.historical_uncertainty_required,
                user_authored_evidence_count=self.historical_user_authored_count,
                assistant_authored_candidate_count=self.historical_assistant_authored_non_evidence_count,
                malformed_or_unattributed_count=self.historical_malformed_count,
                weak_match_rejected_count=self.historical_weak_match_rejected_count,
                conflicting_evidence_count=self.historical_conflict_count,
                match_strength=self.historical_match_strength,
                evidence_texts=self.historical_evidence_texts,
                evidence_classes=self.historical_evidence_classes,
            )
            return profile.deterministic_response()
        return ""


def _compact(value: Any, limit: int = _MAX_EVIDENCE_CHARS) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _recent_user_evidence(history: Iterable[dict[str, Any]]) -> tuple[str, int]:
    rows = [row for row in history if isinstance(row, dict)]
    for offset, row in enumerate(reversed(rows)):
        text = _compact(row.get("user_message"))
        if text:
            return text, offset
    return "", -1


def _historical_evidence_records(
    history: Iterable[dict[str, Any]],
    memories: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine durable candidates with bounded, explicitly role-labelled session turns."""
    records = [dict(row) for row in memories if isinstance(row, dict)]
    rows = [row for row in history if isinstance(row, dict)][-12:]
    for index, row in enumerate(rows):
        turn_id = str(row.get("id") or row.get("turn_id") or f"session-turn-{index}")[:120]
        session_id = str(row.get("session_id") or row.get("conversation_session_id") or "session")[:120]
        user_text = _compact(row.get("user_message"), 900)
        assistant_text = _compact(row.get("assistant_response"), 900)
        if user_text:
            records.append({
                "id": f"{turn_id}:user", "type": "conversation_user", "role": "user",
                "content": user_text, "source": "conversation_session",
                "conversation_session_id": session_id, "conversation_turn_id": turn_id,
            })
        if assistant_text:
            records.append({
                "id": f"{turn_id}:assistant", "type": "conversation_eidolon", "role": "assistant",
                "content": assistant_text, "source": "conversation_session",
                "conversation_session_id": session_id, "conversation_turn_id": turn_id,
            })
    return records


def _is_instruction_clause(clause: str) -> bool:
    text = str(clause or "").strip()
    return bool(
        _RECALL_CLAUSE.search(text)
        or _COMPOUND_EXPLANATION.search(text)
        or re.match(r"(?i)^(?:then\s+|and\s+)?(?:tell|repeat|identify|summarize|explain|describe)\b", text)
    )


def _correction_like_clause(clause: str) -> bool:
    text = str(clause or "").strip()
    if not text or _is_instruction_clause(text):
        return False
    if _CORRECTION_SIGNAL.search(text):
        return True
    # Continuation correction clauses frequently omit a second explicit marker.
    if re.search(r"(?i)\b(?:not|instead|rather than|was|were|is|are|on|at)\b", text) and (
        re.search(r"\b\d+(?:[./:-]\d+)*\b", text)
        or re.search(r"\b[A-Z][a-zA-Z0-9.-]{2,}\b", text)
        or re.search(r"(?i)\b(?:mg|mcg|ml|tablet|dose|route|date|name|device|diagnosis|medication)\b", text)
    ):
        return True
    return False


def _current_correction_payload(message: str) -> tuple[str, int]:
    """Extract attributable correction clauses anywhere in a compound current message.

    Recall/explanation clauses are excluded. A correction marker opens a bounded
    declarative group so a second correction can follow without repeating the marker.
    """
    recall_match = _RECALL_CLAUSE.search(message)
    if not recall_match:
        return "", -1
    clauses = [part.strip() for part in re.split(r"(?<=[.!?;])\s+|\n+", message) if part.strip()]
    selected: list[str] = []
    group_open = False
    for clause in clauses:
        if _is_instruction_clause(clause):
            group_open = False
            continue
        explicit = bool(_CORRECTION_SIGNAL.search(clause))
        if explicit:
            group_open = True
            selected.append(clause)
            continue
        if group_open and _correction_like_clause(clause):
            selected.append(clause)
            continue
        # Natural corrections can be terse and need no literal 'Correction:' prefix.
        if _correction_like_clause(clause) and re.search(r"(?i)\b(?:not|instead|rather than|wasn't|isn't|didn't)\b", clause):
            group_open = True
            selected.append(clause)
    payload = _compact(" ".join(selected))
    return payload, recall_match.start()


def build_immediate_conversation_grounding(
    user_message: str,
    conversation_history: Iterable[dict[str, Any]],
    memories: Iterable[dict[str, Any]] = (),
) -> ImmediateGroundingProfile:
    """Build protected attributable evidence before topic segmentation/provider use."""
    message = _compact(user_message, 1800)
    immediate = bool(_IMMEDIATE_RECALL.search(message))
    exact = bool(_EXACT_REPEAT.search(message))
    current_correction, recall_start = _current_correction_payload(message) if immediate else ("", -1)
    compound_explanation = bool(current_correction and _COMPOUND_EXPLANATION.search(message))
    uncertainty_explanation = bool(compound_explanation and _UNCERTAINTY_EXPLANATION.search(message))

    recent_user, source_offset = _recent_user_evidence(conversation_history)
    recent_correction = bool(recent_user and _CORRECTION_SIGNAL.search(recent_user))
    historical_profile = build_historical_memory_truth(message, _historical_evidence_records(conversation_history, memories))
    historical = historical_profile.query_detected and not immediate
    active_facts = resolve_active_conversation_facts(message, conversation_history, memories)

    lines: list[str] = []
    protect_recent = False
    evidence_text = ""
    state = "none"

    if current_correction:
        state = "current_correction_plus_recall_plus_explanation" if compound_explanation else "current_correction_plus_recall"
        evidence_text = current_correction
        lines.extend([
            "CURRENT USER CORRECTION EVIDENCE",
            "The correction below comes from the current user message and takes precedence over previous-turn recall, system, identity, personality, policy, and memory text.",
            f"Current correction: {current_correction}",
            "Do not include the recall or explanation instruction itself as part of the correction.",
        ])
        if exact:
            lines.append("Preserve the correction wording and named/negated details when repeating it.")
        if compound_explanation:
            lines.append("The current message also contains a second conversational instruction. Answer that instruction in the same response exactly once.")
        if uncertainty_explanation:
            lines.append("For the explanation clause: say that unsupported memory must be labeled uncertain and must not be invented.")
    elif immediate and recent_user:
        state = "previous_turn_recall"
        protect_recent = True
        evidence_text = recent_user
        lines.extend([
            "IMMEDIATE USER FACT EVIDENCE",
            "The following text is attributable to the user's most recent completed turn, not to system, identity, personality, policy, or memory instructions.",
            f"Recent user statement: {recent_user}",
            "When asked what was just said or corrected, answer from this user evidence. Do not substitute behavioral guidance or invent missing details.",
        ])
        if exact:
            lines.append("The user requested exact repetition: preserve the evidence wording rather than paraphrasing it.")
    elif historical:
        state = historical_profile.state
        lines.append(historical_profile.prompt_block())
    if active_facts.prompt_block:
        lines.append(active_facts.prompt_block)
    if active_facts.response:
        state = active_facts.state

    return ImmediateGroundingProfile(
        block="\n".join(line for line in lines if line).strip(),
        grounding_state=state,
        immediate_recall_requested=immediate,
        exact_repeat_requested=exact,
        current_message_correction=bool(current_correction),
        compound_explanation_requested=compound_explanation,
        protected_recent_user_turn=protect_recent,
        protected_recent_correction=bool(protect_recent and recent_correction),
        historical_memory_query=historical,
        attributable_memory_available=historical_profile.attributable_evidence_available,
        historical_evidence_state=historical_profile.state,
        historical_evidence_requested=historical_profile.evidence_requested,
        historical_user_authored_count=historical_profile.user_authored_evidence_count,
        historical_assistant_authored_non_evidence_count=historical_profile.assistant_authored_candidate_count,
        historical_user_nonassertive_count=historical_profile.user_nonassertive_candidate_count,
        historical_malformed_count=historical_profile.malformed_or_unattributed_count,
        historical_conflict_count=historical_profile.conflicting_evidence_count,
        historical_weak_match_rejected_count=historical_profile.weak_match_rejected_count,
        historical_match_strength=historical_profile.match_strength,
        historical_uncertainty_required=historical_profile.uncertainty_required,
        active_fact_grounded=bool(active_facts.response),
        active_fact_kind=active_facts.fact_kind,
        active_fact_count=active_facts.fact_count,
        active_fact_correction_applied=active_facts.correction_applied,
        active_fact_response=active_facts.response,
        source_turn_offset=source_offset if protect_recent else (-2 if current_correction else -1),
        evidence_text=evidence_text,
        historical_evidence_texts=historical_profile.evidence_texts,
        historical_evidence_classes=historical_profile.evidence_classes,
    )
