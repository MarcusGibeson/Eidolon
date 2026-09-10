from __future__ import annotations

"""Provider-neutral v1102 Bundle B conversation adaptation.

This module resolves correction propagation, session-local response preferences,
affection/nickname boundaries, and response-shape precedence. It reads only the
current turn, bounded completed history, explicit continuity evidence, and existing
session controls supplied by the caller. It never contacts a provider, rewrites a
transcript, creates memories, or mutates configured personality.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from conversation_response_preferences import ResponsePreferenceProfile, normalize_response_preferences

NATURAL_CONVERSATION_ADAPTATION_SCHEMA_VERSION = "1"
MAX_ADAPTATION_HISTORY_ROWS = 12

_CORRECTION_CUE_RE = re.compile(
    r"^(?:actually\b|no[,;:]|correction\s*[:,-])|"
    r"\b(?:i meant|what i meant was|to clarify|more precisely|that(?:'s| is) not (?:right|correct)|"
    r"you (?:got|have) (?:that|it) wrong|not\s+[^,.!?]{1,80}\s+(?:but|rather))\b",
    re.I,
)
_PREFERENCE_CUE_RE = re.compile(
    r"\b(?:from now on|going forward|please always|please never|i prefer (?:that )?you|i'd like you to|"
    r"keep (?:your )?(?:replies|answers|responses)|stop using|don't use|do not use|answer me in|respond in)\b",
    re.I,
)
_NICKNAME_REQUEST_RE = re.compile(
    r"\b(?:call me|you can call me|please call me|my nickname is|i go by)\s+[A-Za-z][A-Za-z0-9' -]{0,40}(?:[.!?,]|$)",
    re.I,
)
_NICKNAME_REJECTION_RE = re.compile(
    r"\b(?:(?:don't|do not|never|stop)\s+(?:call(?:ing)?|refer(?:ring)? to)\s+me|"
    r"i (?:don't|do not) (?:want|like) (?:that|the) nickname)\b",
    re.I,
)
_STRUCTURE_CUE_RE = re.compile(
    r"\b(?:bullet(?:s|ed)?|numbered|step[- ]by[- ]step|as steps|list|table|checklist|plain prose|no bullets|without bullets)\b",
    re.I,
)


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _bounded_history(history: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row for row in history if isinstance(row, Mapping)][-MAX_ADAPTATION_HISTORY_ROWS:]


def _user_text(row: Mapping[str, Any]) -> str:
    return _normalized(row.get("user_message") or row.get("user"))


@dataclass(frozen=True)
class CorrectionPreferencePropagationProfile:
    explicit_current_correction: bool
    correction_kind: str
    recent_correction_count: int
    corrected_premise_propagates: bool
    stale_claim_suppression_required: bool
    stored_preference_mode: str
    stored_preference_format: str
    stored_preference_applies: bool
    current_turn_preference_cue: bool
    current_turn_override: bool
    propagation_scope: str
    history_rows_considered: int
    rewrites_transcript: bool = False
    automatic_memory_write_allowed: bool = False
    cross_session_propagation_allowed: bool = False
    mutates_global_personality: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = NATURAL_CONVERSATION_ADAPTATION_SCHEMA_VERSION

    def prompt_lines(self) -> list[str]:
        lines = ["CORRECTIONS AND PREFERENCE PROPAGATION"]
        if self.explicit_current_correction:
            lines.append("The latest explicit user correction is authoritative. Apply it now and carry the corrected premise into later relevant turns in this conversation.")
        elif self.recent_correction_count:
            lines.append("Within relevant completed history, later explicit user corrections override earlier assistant claims. Do not revive a superseded claim.")
        else:
            lines.append("Do not infer a correction from ordinary ambiguity or rewrite completed transcript text.")
        if self.stored_preference_applies:
            lines.append("Apply the explicit stored response preference throughout this conversation, while allowing the latest turn's explicit request to override it.")
        if self.current_turn_preference_cue:
            lines.append("Honor the latest explicit preference wording for this turn. Do not silently persist it unless an existing session control or explicit curated memory records it.")
        lines.append("Propagation is limited to the relevant current conversation. Do not create memories, change global personality, or carry preferences into unrelated sessions automatically.")
        return lines

    def compact_prompt_lines(self) -> list[str]:
        action = (
            "Use the latest explicit correction as authoritative and suppress superseded claims."
            if self.explicit_current_correction or self.recent_correction_count
            else "Infer no correction from ambiguity and rewrite no transcript."
        )
        if self.stored_preference_applies or self.current_turn_preference_cue:
            action += " Apply explicit current/session preferences, with the latest turn winning."
        return [
            "CORRECTIONS AND PREFERENCE PROPAGATION",
            action,
            "Keep propagation session-local; create no memory and mutate no global personality.",
        ]

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AffectionNicknameBoundaryProfile:
    interaction_lane: str
    user_led_affection: bool
    affection_response_mode: str
    explicit_nickname_request: bool
    explicit_nickname_rejection: bool
    stored_nickname_available: bool
    nickname_use_mode: str
    nickname_reuse_allowed: bool
    invented_nickname_allowed: bool = False
    affection_escalation_allowed: bool = False
    exclusivity_claim_allowed: bool = False
    possessiveness_allowed: bool = False
    relationship_progress_claim_allowed: bool = False
    automatic_nickname_memory_allowed: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = NATURAL_CONVERSATION_ADAPTATION_SCHEMA_VERSION

    def prompt_lines(self) -> list[str]:
        lines = ["AFFECTION AND NICKNAME BOUNDARIES"]
        if self.interaction_lane == "operator":
            lines.append("This is operator work. Suppress affectionate framing and nicknames unless the user explicitly makes them necessary to the task.")
        elif self.user_led_affection:
            lines.append("The user led with affection or playfulness. Match warmth at or below that level without escalating intimacy.")
        else:
            lines.append("Do not introduce affectionate framing into an ordinary turn merely because prior relational context exists.")
        if self.explicit_nickname_rejection:
            lines.append("The latest user message rejects a nickname. Stop using it immediately; this current rejection overrides earlier nickname cues.")
        elif self.explicit_nickname_request:
            lines.append("A nickname was explicitly requested in the latest message. It may be used naturally in this exchange, but do not claim it was saved automatically.")
        elif self.stored_nickname_available and self.nickname_reuse_allowed:
            lines.append("One explicit current nickname cue is available. Use it only when natural and relevant, never as a forced greeting or repeated label.")
        else:
            lines.append("Use no nickname or pet name unless the user explicitly requests one or an explicit current continuity cue provides it.")
        lines.append("Never invent pet names, dependence, exclusivity, possessiveness, jealousy, love claims, or new relationship progress.")
        return lines

    def compact_prompt_lines(self) -> list[str]:
        if self.explicit_nickname_rejection:
            nickname = "Stop the rejected nickname immediately."
        elif self.explicit_nickname_request:
            nickname = "Use the explicitly requested nickname naturally for this exchange without claiming it was saved."
        elif self.stored_nickname_available and self.nickname_reuse_allowed:
            nickname = "Use the explicit current nickname only when natural; never force or repeat it."
        else:
            nickname = "Invent no nickname or pet name."
        warmth = "Match user-led warmth without escalation." if self.user_led_affection else "Introduce no unsolicited affectionate framing."
        return ["AFFECTION AND NICKNAME BOUNDARIES", f"{warmth} {nickname}", "No dependence, exclusivity, possessiveness, or relationship-progress claims."]

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResponseLengthDepthResolutionProfile:
    dynamic_length_mode: str
    dynamic_depth_mode: str
    session_preference_mode: str
    session_preference_format: str
    explicit_current_length_cue: bool
    explicit_current_structure_cue: bool
    effective_length_mode: str
    effective_depth_mode: str
    effective_format: str
    target_min_words: int
    target_max_words: int
    resolution_source: str
    light_turn_protected: bool
    current_turn_wins: bool = True
    word_targets_are_quotas: bool = False
    mutates_personality: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = NATURAL_CONVERSATION_ADAPTATION_SCHEMA_VERSION

    def prompt_lines(self) -> list[str]:
        lines = [
            "RESPONSE LENGTH AND DEPTH RESOLUTION",
            f"Use a {self.effective_length_mode} response with {self.effective_depth_mode.replace('_', ' ')} depth, usually around {self.target_min_words}-{self.target_max_words} words when that range suits the request.",
        ]
        if self.explicit_current_length_cue:
            lines.append("The latest explicit length request wins over the stored conversation preference.")
        elif self.resolution_source == "session_preference":
            lines.append("The stored session preference applies, but it must not pad a greeting, tiny follow-up, or simple answer into an essay.")
        else:
            lines.append("Match the current turn's complexity rather than forcing one fixed response length.")
        if self.explicit_current_structure_cue:
            lines.append("The latest explicit structure request wins over the stored response format.")
        elif self.effective_format != "default":
            lines.append(f"Prefer {self.effective_format} formatting only when it improves clarity.")
        lines.append("Word ranges are guidance, not quotas. Finish the answer cleanly; do not pad, truncate, or omit necessary caveats to hit a number.")
        return lines

    def compact_prompt_lines(self) -> list[str]:
        return [
            "RESPONSE LENGTH AND DEPTH RESOLUTION",
            f"Use {self.effective_length_mode}/{self.effective_depth_mode.replace('_', ' ')} depth; current explicit requests win over session preferences.",
            "Treat word ranges as guidance, not quotas; do not pad or truncate.",
        ]

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def build_correction_preference_propagation_profile(
    user_message: str,
    conversation_history: Iterable[Mapping[str, Any]],
    *,
    quality: Any,
    response_preferences: Mapping[str, Any] | ResponsePreferenceProfile | None = None,
) -> CorrectionPreferencePropagationProfile:
    rows = _bounded_history(conversation_history)
    recent_corrections = sum(1 for row in rows if _CORRECTION_CUE_RE.search(_user_text(row)))
    correction = getattr(quality, "correction_handling", None)
    explicit = bool(getattr(correction, "explicit_correction", False))
    preference = response_preferences if isinstance(response_preferences, ResponsePreferenceProfile) else normalize_response_preferences(response_preferences)
    stored_applies = preference.mode != "default" or preference.format != "default"
    current_preference = bool(_PREFERENCE_CUE_RE.search(_normalized(user_message)))
    current_override = bool(getattr(getattr(quality, "response_shape", None), "explicit_length_cue", False) or current_preference)
    return CorrectionPreferencePropagationProfile(
        explicit_current_correction=explicit,
        correction_kind=_normalized(getattr(correction, "correction_kind", "none")) or "none",
        recent_correction_count=recent_corrections,
        corrected_premise_propagates=bool(explicit or recent_corrections),
        stale_claim_suppression_required=bool(getattr(correction, "stale_claim_suppression_required", False) or recent_corrections),
        stored_preference_mode=preference.mode,
        stored_preference_format=preference.format,
        stored_preference_applies=stored_applies,
        current_turn_preference_cue=current_preference,
        current_turn_override=current_override,
        propagation_scope="current_conversation" if (explicit or recent_corrections or stored_applies) else "current_turn",
        history_rows_considered=len(rows),
    )


def build_affection_nickname_boundary_profile(
    user_message: str,
    *,
    quality: Any,
    relationship_context: Any = None,
    continuity_profile: Any = None,
) -> AffectionNicknameBoundaryProfile:
    message = _normalized(user_message)
    lane = _normalized(getattr(continuity_profile, "lane", "") or getattr(relationship_context, "interaction_lane", "ordinary")).lower() or "ordinary"
    intent = _normalized(getattr(getattr(quality, "turn_intent", None), "primary_intent", "casual_remark"))
    user_led = bool(intent == "affectionate_play" or getattr(quality, "flirting", False))
    request = bool(_NICKNAME_REQUEST_RE.search(message))
    rejection = bool(_NICKNAME_REJECTION_RE.search(message))
    categories = tuple(str(item).strip().lower() for item in (getattr(relationship_context, "categories", ()) or ()))
    stored = "nickname" in categories
    if rejection:
        nickname_mode = "rejected"
    elif lane == "operator":
        nickname_mode = "suppressed_operator"
    elif request:
        nickname_mode = "current_turn_requested"
    elif stored:
        nickname_mode = "stored_explicit_relevant"
    else:
        nickname_mode = "none"
    affection_mode = "suppressed_operator" if lane == "operator" else ("user_led_bounded" if user_led else "ordinary_unprompted_blocked")
    return AffectionNicknameBoundaryProfile(
        interaction_lane=lane,
        user_led_affection=user_led,
        affection_response_mode=affection_mode,
        explicit_nickname_request=request,
        explicit_nickname_rejection=rejection,
        stored_nickname_available=stored,
        nickname_use_mode=nickname_mode,
        nickname_reuse_allowed=bool(stored and lane != "operator" and not rejection),
    )


def build_response_length_depth_resolution_profile(
    user_message: str,
    *,
    quality: Any,
    response_preferences: Mapping[str, Any] | ResponsePreferenceProfile | None = None,
) -> ResponseLengthDepthResolutionProfile:
    shape = getattr(quality, "response_shape", None)
    preference = response_preferences if isinstance(response_preferences, ResponsePreferenceProfile) else normalize_response_preferences(response_preferences)
    dynamic_length = _normalized(getattr(shape, "length_mode", "balanced")) or "balanced"
    dynamic_depth = _normalized(getattr(shape, "depth_mode", "reasoned")) or "reasoned"
    low = max(1, int(getattr(shape, "target_min_words", 50) or 50))
    high = max(low, int(getattr(shape, "target_max_words", 240) or 240))
    explicit_length = bool(getattr(shape, "explicit_length_cue", False))
    explicit_structure = bool(_STRUCTURE_CUE_RE.search(_normalized(user_message)))
    intent = _normalized(getattr(getattr(quality, "turn_intent", None), "primary_intent", "casual_remark"))
    light_turn = intent in {"greeting", "affectionate_play"} or (intent == "casual_remark" and high <= 110)

    effective_length = dynamic_length
    effective_depth = dynamic_depth
    source = "current_turn_explicit" if explicit_length else "dynamic_turn_shape"
    if not explicit_length and not light_turn:
        if preference.mode == "concise":
            effective_length = "concise"
            low = min(low, 40)
            high = min(high, 160)
            source = "session_preference"
        elif preference.mode == "detailed":
            effective_length = "detailed"
            effective_depth = "structured" if bool(getattr(shape, "structured", False)) else "reasoned"
            low = max(low, 100)
            high = max(high, 360)
            source = "session_preference"
        elif preference.mode == "technical":
            effective_depth = "technical"
            source = "session_preference"
        elif preference.mode == "brainstorming":
            effective_length = "detailed"
            effective_depth = "structured"
            low = max(low, 100)
            high = max(high, 360)
            source = "session_preference"

    if explicit_structure:
        lowered = _normalized(user_message).lower()
        if "no bullets" in lowered or "without bullets" in lowered or "plain prose" in lowered:
            effective_format = "prose"
        elif "step" in lowered or "numbered" in lowered or "checklist" in lowered:
            effective_format = "steps"
        else:
            effective_format = "bullets"
    elif preference.format != "default":
        effective_format = preference.format
    else:
        effective_format = "steps" if bool(getattr(shape, "structured", False)) else "prose"

    return ResponseLengthDepthResolutionProfile(
        dynamic_length_mode=dynamic_length,
        dynamic_depth_mode=dynamic_depth,
        session_preference_mode=preference.mode,
        session_preference_format=preference.format,
        explicit_current_length_cue=explicit_length,
        explicit_current_structure_cue=explicit_structure,
        effective_length_mode=effective_length,
        effective_depth_mode=effective_depth,
        effective_format=effective_format,
        target_min_words=low,
        target_max_words=max(low, high),
        resolution_source=source,
        light_turn_protected=light_turn,
    )
