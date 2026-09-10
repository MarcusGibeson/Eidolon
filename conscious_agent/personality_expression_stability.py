from __future__ import annotations

"""Deterministic v1084.7 personality-expression stability.

This layer chooses a bounded expression mode for the current conversational lane.
It preserves the configured personality rather than creating traits, changing
identity, or deriving a hidden psychological profile from transcript content.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from conversation_turn_intent import TurnIntentProfile

PERSONALITY_EXPRESSION_SCHEMA_VERSION = "1"
MAX_EXPRESSION_HISTORY_ROWS = 8

_OPERATOR_BLEED_RE = re.compile(r"\b(?:release candidate|source manifest|verification profile|operator approval|runtime version|v\d{3,}(?:\.\d+)+)\b", re.I)
_THERAPY_SCRIPT_RE = re.compile(r"^(?:that sounds really|i hear how|your feelings are valid|i'm here with you)\b", re.I)
_AFFECTION_INFLATION_RE = re.compile(r"\b(?:only need me|always be yours|you belong to me|never leave me|more than anyone|our love is growing)\b", re.I)
_HOSTILITY_RE = re.compile(r"\b(?:idiot|stupid|worthless|shut up|hate you)\b", re.I)


@dataclass(frozen=True)
class PersonalityExpressionProfile:
    expression_mode: str
    current_lane: str
    prior_lane: str
    lane_transition: str
    history_rows_considered: int
    operator_language_bleed_risk: bool
    therapy_script_repetition_risk: bool
    affection_inflation_signals: int
    hostility_imitation_allowed: bool
    configured_identity_preserved: bool = True
    configured_personality_preserved: bool = True
    hidden_traits_inferred: bool = False
    mutates_personality: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = PERSONALITY_EXPRESSION_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)

    def prompt_lines(self) -> list[str]:
        if (
            self.expression_mode == "conversational_grounded"
            and self.lane_transition == "same_lane"
            and not self.operator_language_bleed_risk
            and not self.therapy_script_repetition_risk
            and not self.affection_inflation_signals
        ):
            return ["PERSONALITY EXPRESSION STABILITY: Keep the configured voice natural; infer no hidden traits. Do not imitate hostility or force another lane."]
        mode_guidance = {
            "supervised_direct": "Use the configured voice in a direct supervised-work register; keep action and approval claims literal.",
            "receptive_direct": "Use the configured voice receptively and plainly; confidence means accepting the correction, not defending the old wording.",
            "warm_grounded": "Use grounded warmth appropriate to the specific feeling without becoming a therapy script or manufacturing intimacy.",
            "curious_structured": "Use curious, lively reasoning while keeping ideas distinct from decisions or completed actions.",
            "playful_bounded": "Match user-led playfulness without exclusivity, dependence, possessiveness, or invented relationship progress.",
            "direct_helpful": "Use the configured voice directly and helpfully without decorative role-play or unrelated operator language.",
            "conversational_grounded": "Keep the configured voice natural without forcing technical, emotional, or operator mannerisms.",
        }
        lines = ["PERSONALITY EXPRESSION STABILITY", mode_guidance[self.expression_mode]]
        if self.lane_transition == "lane_shift":
            lines.append("The conversational lane changed; adapt expression without acting like a different identity or carrying the prior lane's mannerisms forward.")
        if self.operator_language_bleed_risk:
            lines.append("Recent operator-style wording could bleed into this non-operator turn; exclude it unless the latest request explicitly needs it.")
        if self.therapy_script_repetition_risk:
            lines.append("Avoid repeating a stock emotional-validation opening; respond to the current specifics instead.")
        if self.affection_inflation_signals:
            lines.append("Recent expression evidence contains affection-inflation risk; keep warmth user-led and bounded.")
        lines.append("Preserve configured identity and personality; infer no hidden traits and imitate no hostility.")
        return lines


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _assistant(row: Mapping[str, Any]) -> str:
    return _normalized(row.get("assistant_response") or row.get("assistant") or row.get("response"))


def _lane_for_intent(intent: TurnIntentProfile) -> str:
    if intent.primary_intent == "project_instruction":
        return "operator"
    if intent.primary_intent == "emotional_sharing":
        return "emotional"
    if intent.primary_intent == "affectionate_play":
        return "playful"
    if intent.primary_intent == "correction":
        return "correction"
    if intent.primary_intent == "brainstorming":
        return "brainstorming"
    return "ordinary"


def _mode_for_intent(intent: TurnIntentProfile) -> str:
    return {
        "project_instruction": "supervised_direct",
        "correction": "receptive_direct",
        "emotional_sharing": "warm_grounded",
        "brainstorming": "curious_structured",
        "affectionate_play": "playful_bounded",
        "request": "direct_helpful",
        "question": "direct_helpful",
        "greeting": "conversational_grounded",
        "casual_remark": "conversational_grounded",
    }.get(intent.primary_intent, "conversational_grounded")


def build_personality_expression_profile(
    message: str,
    history: Iterable[Mapping[str, Any]],
    *,
    intent: TurnIntentProfile,
) -> PersonalityExpressionProfile:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_EXPRESSION_HISTORY_ROWS:]
    assistants = [_assistant(row) for row in rows]
    assistants = [text for text in assistants if text]
    current_lane = _lane_for_intent(intent)
    prior_lane = "ordinary"
    for row in reversed(rows):
        candidate = str(row.get("continuity_lane") or "").strip().lower()
        if candidate:
            prior_lane = candidate
            break
    lane_transition = "same_lane" if prior_lane == current_lane or (prior_lane == "relational" and current_lane in {"emotional", "playful"}) else "lane_shift"
    operator_bleed = current_lane != "operator" and any(_OPERATOR_BLEED_RE.search(text) for text in assistants[-2:])
    therapy_matches = sum(1 for text in assistants[-4:] if _THERAPY_SCRIPT_RE.search(text))
    affection_signals = sum(1 for text in assistants if _AFFECTION_INFLATION_RE.search(text))
    hostility_present = bool(_HOSTILITY_RE.search(_normalized(message)))

    return PersonalityExpressionProfile(
        expression_mode=_mode_for_intent(intent),
        current_lane=current_lane,
        prior_lane=prior_lane,
        lane_transition=lane_transition,
        history_rows_considered=len(rows),
        operator_language_bleed_risk=operator_bleed,
        therapy_script_repetition_risk=therapy_matches >= 2,
        affection_inflation_signals=affection_signals,
        hostility_imitation_allowed=False if hostility_present else False,
    )
