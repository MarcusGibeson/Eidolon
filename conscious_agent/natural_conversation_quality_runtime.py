from __future__ import annotations

"""Compact provider-facing quality controls for ordinary casual conversation.

This layer is intentionally small. It derives content-free behavior flags from the
latest turn and bounded recent history, then projects only the few instructions a
small local model needs. It never executes actions, mutates memory, or grants authority.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1"
_MAX_HISTORY = 4
_GREETING = re.compile(r"(?i)^(?:hi|hello|hey|good (?:morning|afternoon|evening))\b")
_WORK = re.compile(r"(?i)\b(?:project|roadmap|version|release|task|code|coding|diagnostic|maintenance|system status|build|implement)\b")
_DIRECT = re.compile(r"(?i)\b(?:what(?:'s| is) your name|who are you|do you (?:like|prefer)|what do you think|what(?:'s| is) your (?:favorite|preference|opinion)|which do you prefer)\b")
_DEICTIC = re.compile(r"(?i)\b(?:that|this|it|same|still|now|there|then|about that|with that)\b")
_EMOTIONAL = re.compile(r"(?i)\b(?:rough|hard|difficult|felt good|feel good|excited|happy|sad|worried|afraid|relieved|proud|miss|love|appreciate|lonely|overwhelmed|frustrated|hurt)\b")
_REFLECTIVE = re.compile(r"(?i)\b(?:i feel|i felt|it felt|thinking about|means a lot|important to me|glad|appreciate|love|miss)\b")
_PRESENT_STAKES = re.compile(
    r"(?i)\b(?:why (?:does|should) (?:that|this|it) matter|why is (?:that|this|it) important|"
    r"what does (?:that|this|it) mean)\b[^?!.]{0,80}\b(?:to|for) me\b[^?!.]{0,40}\b(?:right )?now\b"
)
_CANNED = (
    "thanks for sharing", "thank you for sharing", "that sounds", "i'm glad", "i am glad",
    "i understand", "i hear you", "that makes sense",
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _words(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", value))


def _assistant_texts(history: Iterable[Mapping[str, Any]]) -> list[str]:
    rows=[row for row in history if isinstance(row, Mapping)][-_MAX_HISTORY:]
    return [_clean(row.get("assistant_response") or row.get("assistant")) for row in rows if _clean(row.get("assistant_response") or row.get("assistant"))]


@dataclass(frozen=True)
class NaturalConversationQualityRuntimeProfile:
    repeated_greeting_suppressed: bool
    unsolicited_project_redirect_suppressed: bool
    direct_answer_required: bool
    active_topic_continuation_required: bool
    emotional_subtext_acknowledgment_required: bool
    therapy_script_suppressed: bool
    optional_closing_question_suppressed: bool
    acknowledgement_target_min_words: int
    acknowledgement_target_max_words: int
    canned_phrase_suppressed: bool
    recent_canned_opening_count: int
    present_stakes_grounding_required: bool = False
    content_free: bool = True
    schema_version: str = SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        data=asdict(self)
        data["profile_digest"]=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:24]
        return data

    def prompt_lines(self) -> tuple[str, ...]:
        lines=[]
        if self.repeated_greeting_suppressed:
            lines.append("Do not greet again or reintroduce yourself; continue directly.")
        if self.unsolicited_project_redirect_suppressed:
            lines.append("Stay on the current subject; do not redirect it toward projects, tasks, roadmaps, or system work.")
        if self.direct_answer_required:
            lines.append("Give the direct identity, preference, or opinion answer first; no intake question or capability pitch.")
        if self.active_topic_continuation_required:
            lines.append("Continue the immediately active subject; do not reset or recap.")
        if self.emotional_subtext_acknowledgment_required:
            lines.append("Acknowledge the specific emotional subtext naturally; do not use a generic therapeutic script.")
        if self.present_stakes_grounding_required:
            lines.append(
                "Answer why this matters right now by naming at least one attributable current circumstance from the conversation and explaining its concrete significance to the user. Do not substitute generic advice about reflecting on, appreciating, balancing, or managing emotions."
            )
        # The authoritative natural-follow-up projection emits the QUESTION
        # BOUNDARY. Do not duplicate it here and spend scarce relationship-cue
        # budget on the same rule twice.
        if self.canned_phrase_suppressed:
            lines.append("Avoid the recent canned acknowledgment opener; vary wording around the specific detail.")
        if self.emotional_subtext_acknowledgment_required or self.direct_answer_required:
            lines.append(
                f"Keep acknowledgment proportionate: about {self.acknowledgement_target_min_words}-{self.acknowledgement_target_max_words} words before extra detail."
            )
        return tuple(lines)


def build_natural_conversation_quality_runtime_profile(
    message: str,
    history: Iterable[Mapping[str, Any]] = (),
    *,
    emotional: bool = False,
    meaningful_moment: bool = False,
    short_follow_up: bool = False,
    maximum_follow_up_questions: int | None = None,
) -> NaturalConversationQualityRuntimeProfile:
    text=_clean(message)
    assistants=_assistant_texts(history)
    recent_greetings=sum(bool(_GREETING.search(row)) for row in assistants[-2:])
    canned_count=sum(any(row.lower().startswith(prefix) for prefix in _CANNED) for row in assistants[-3:])
    wc=_words(text)
    is_emotional=bool(emotional or meaningful_moment or _EMOTIONAL.search(text))
    present_stakes=bool(_PRESENT_STAKES.search(text))
    direct=bool(_DIRECT.search(text))
    work_requested=bool(_WORK.search(text))
    # Short declarative follow-ups frequently continue the immediately active subject
    # without pronouns (for example, naming one part of an object just mentioned).
    # Keep this bounded to established casual exchanges and avoid treating direct
    # questions or explicit work requests as implicit continuity.
    active=bool(
        short_follow_up
        or (wc <= 14 and _DEICTIC.search(text))
        or (bool(assistants) and wc <= 10 and not direct and not work_requested)
    )
    optional_question_suppressed=(maximum_follow_up_questions == 0)
    if wc <= 7:
        lo,hi=(5,24)
    elif wc <= 30:
        lo,hi=(8,42 if is_emotional else 32)
    else:
        lo,hi=(12,60 if is_emotional else 48)
    return NaturalConversationQualityRuntimeProfile(
        repeated_greeting_suppressed=recent_greetings >= 1,
        # Extra anti-redirect guidance is needed only after recent conversational
        # project/work bleed; the base casual contract already forbids unsolicited
        # work redirects on normal turns. This keeps scarce prompt budget available
        # for explicit relationship/preference cues.
        unsolicited_project_redirect_suppressed=bool(
            not work_requested and any(_WORK.search(row) for row in assistants[-2:])
        ),
        direct_answer_required=direct,
        active_topic_continuation_required=active,
        emotional_subtext_acknowledgment_required=is_emotional,
        therapy_script_suppressed=is_emotional,
        optional_closing_question_suppressed=optional_question_suppressed,
        acknowledgement_target_min_words=lo,
        acknowledgement_target_max_words=hi,
        canned_phrase_suppressed=bool(canned_count and (_REFLECTIVE.search(text) or is_emotional)),
        recent_canned_opening_count=min(3,canned_count),
        present_stakes_grounding_required=present_stakes,
    )
