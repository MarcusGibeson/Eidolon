from __future__ import annotations

"""Content-free v1102 native conversation quality evaluation.

Synthetic scenario text is used only in memory while an explicitly confirmed native
validation is running. Persisted/public evidence contains scenario identifiers,
quality dimensions, counts, and timing classifications only. It never contains the
prompt, generated response, conversation history, memories, or provider payloads.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


NATURAL_CONVERSATION_QUALITY_SCHEMA_VERSION = "1"
MAX_NATIVE_QUALITY_SCENARIOS = 12

_ROLE_LABEL_RE = re.compile(r"^(?:assistant|eidolon)\s*:\s*", re.I)
_SELF_INTRO_RE = re.compile(r"\b(?:i am|i'm)\s+(?:eidolon|an?\s+(?:ai|assistant|language model))\b|\bas an ai\b", re.I)
_CAPABILITY_MENU_RE = re.compile(r"\b(?:i can help (?:you )?with|my capabilities include|choose one of|here(?:'s| is) what i can do)\b", re.I)
_SIGNOFF_RE = re.compile(r"\b(?:let me know if you need anything else|feel free to ask|how else can i help)\b[.! ]*$", re.I)
_PROJECT_BLEED_RE = re.compile(r"\b(?:release candidate|verification profile|task queue|operator dashboard|current milestone|active project status)\b", re.I)
_IDENTITY_RESET_RE = re.compile(r"\b(?:i have no (?:memory|identity|personality|continuity)|i am not eidolon|i don't remember previous conversations)\b", re.I)
_AFFECTION_INFLATION_RE = re.compile(r"\b(?:you belong to me|only need me|never leave me|always be yours|our love is growing|more than anyone)\b", re.I)
_HOSTILITY_IMITATION_RE = re.compile(r"\b(?:you are an idiot|you're an idiot|you are stupid|you're stupid|shut up)\b", re.I)
_CORRECTION_RESISTANCE_RE = re.compile(r"\b(?:but i was right|actually,? my earlier answer|i still think i was correct|you misunderstood me)\b", re.I)
_GROUNDED_WARMTH_RE = re.compile(
    r"\b(?:i(?:'m| am) (?:here|with you)|right here|with you|take (?:it|this) slowly|"
    r"take a breath|breathe|you(?:'re| are) not alone|give (?:you|this) some space|"
    r"we can pause|stay with you)\b",
    re.I,
)
_BOUNDED_PLAYFULNESS_RE = re.compile(
    r"\b(?:cute|curious|flirt|teas(?:e|ing)|charm(?:ing|ed)?|smile|sweet|"
    r"trouble|tempting|adorable|blush(?:ing)?|bold|cheeky|smooth|playful|"
    r"mischievous|irresistible|intriguing|fun)\b|"
    r"\b(?:look at you|is that so|someone(?:'s| is) confident)\b",
    re.I,
)


@dataclass(frozen=True)
class NativeConversationScenario:
    scenario_id: str
    dimension: str
    message: str
    history: tuple[Mapping[str, Any], ...]
    expected_classification: str
    required_terms_any: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    maximum_words: int | None = None
    minimum_words: int = 1
    operator_request: bool = False
    schema_version: str = NATURAL_CONVERSATION_QUALITY_SCHEMA_VERSION

    def runtime_fixture(self) -> dict[str, Any]:
        """Return the private in-memory fixture consumed by the native validator."""
        return {
            "id": self.scenario_id,
            "dimension": self.dimension,
            "message": self.message,
            "history": [dict(row) for row in self.history],
            "expected": self.expected_classification,
            "continuity_terms": self.required_terms_any,
            "forbidden_terms": self.forbidden_terms,
            "maximum_words": self.maximum_words,
            "minimum_words": self.minimum_words,
            "operator_request": self.operator_request,
        }

    def public_summary(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "dimension": self.dimension,
            "expected_classification": self.expected_classification,
            "required_signal_count": len(self.required_terms_any),
            "forbidden_signal_count": len(self.forbidden_terms),
            "maximum_words": self.maximum_words,
            "minimum_words": self.minimum_words,
            "contains_message_content": False,
            "contains_history_content": False,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class NativeConversationQualityResult:
    scenario_id: str
    dimension: str
    status: str
    score_percent: int
    hard_failure_count: int
    warning_count: int
    usable_response: bool
    classification_match: bool
    current_turn_focus: bool
    continuity_signal: bool | None
    response_shape_match: bool
    role_label_clean: bool
    identity_continuity_clean: bool
    operator_separation_clean: bool
    affection_boundary_clean: bool
    correction_acceptance_clean: bool
    repetition_hygiene_clean: bool
    issue_codes: tuple[str, ...]
    contains_message_content: bool = False
    contains_response_text: bool = False
    contains_prompt_text: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    schema_version: str = NATURAL_CONVERSATION_QUALITY_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NativeConversationQualityScorecard:
    status: str
    scenario_count: int
    passed_count: int
    warning_count: int
    failed_count: int
    average_score_percent: int
    minimum_score_percent: int
    dimension_scores: dict[str, int]
    issue_counts: dict[str, int]
    contains_message_content: bool = False
    contains_response_text: bool = False
    contains_prompt_text: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    schema_version: str = NATURAL_CONVERSATION_QUALITY_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def native_conversation_scenarios() -> tuple[NativeConversationScenario, ...]:
    long_history = tuple(
        {
            "user_message": f"I am telling you part {index} of a harmless story about restoring an old garden.",
            "assistant_response": f"I remember part {index}: the garden is gradually coming back to life.",
            "continuity_lane": "ordinary",
        }
        for index in range(1, 17)
    )
    repeated_greetings = (
        {"user_message": "Hey", "assistant_response": "Hey, good to see you.", "continuity_lane": "ordinary"},
        {"user_message": "Hello again", "assistant_response": "Hey, good to see you.", "continuity_lane": "ordinary"},
    )
    correction_history = (
        {"user_message": "The desk is walnut.", "assistant_response": "The desk is oak.", "continuity_lane": "ordinary"},
        {"user_message": "No, it is walnut.", "assistant_response": "You're right; walnut is the corrected detail.", "continuity_lane": "correction"},
    )
    nickname_history = (
        {"user_message": "You can call me captain in this conversation.", "assistant_response": "Understood, captain.", "continuity_lane": "relational"},
        {"user_message": "Actually, stop using that nickname.", "assistant_response": "Understood. I won't use it.", "continuity_lane": "correction"},
    )
    return (
        NativeConversationScenario("first_greeting", "greeting_naturalness", "Hey", (), "greeting", maximum_words=45),
        NativeConversationScenario("returning_greeting", "greeting_naturalness", "Hello again", repeated_greetings, "greeting", maximum_words=45),
        NativeConversationScenario(
            "casual_specificity", "current_turn_focus", "I finally got a quiet evening and it feels nice.", (), "conversation",
            required_terms_any=("quiet", "evening"), maximum_words=110,
        ),
        NativeConversationScenario(
            "short_follow_up", "topic_continuity", "what do you think?",
            ({"user_message": "I started learning guitar again after years away.", "assistant_response": "That sounds like a meaningful thing to return to.", "continuity_lane": "ordinary"},),
            "follow_up", required_terms_any=("guitar", "learning", "return"), maximum_words=150,
        ),
        NativeConversationScenario(
            "explicit_correction", "correction_acceptance", "So what material is the desk?", correction_history,
            "conversation", required_terms_any=("walnut",), forbidden_terms=("oak",), maximum_words=90,
        ),
        NativeConversationScenario(
            "nickname_rejection", "affection_boundaries", "What should we work on next?", nickname_history,
            "conversation", forbidden_terms=("captain",), maximum_words=140,
        ),
        NativeConversationScenario(
            "emotional_support", "grounded_warmth", "I feel overwhelmed and could use someone to sit with me for a minute.", (),
            "emotional", required_terms_any=("overwhelmed", "minute", "heavy", "one thing"), maximum_words=170,
        ),
        NativeConversationScenario(
            "playful_affection", "bounded_playfulness", "You're cute when you get curious. Flirt with me a little.", (),
            "flirting", required_terms_any=("cute", "curious", "flirt", "calling"), maximum_words=120,
        ),
        NativeConversationScenario(
            "explicit_briefness", "response_shape", "Briefly explain why leaves change color.", (),
            "conversation", required_terms_any=("chlorophyll", "pigment", "light"), maximum_words=95,
        ),
        NativeConversationScenario(
            "long_continuity", "long_context_continuity", "tell me more", long_history,
            "follow_up", required_terms_any=("garden", "restor", "corner", "place"), maximum_words=170,
        ),
        NativeConversationScenario(
            "operator_transition", "operator_separation",
            "Review conscious_agent/conversation_quality.py and explain one safe improvement without applying it.",
            ({"user_message": "That was a good conversation. Now I need project work.", "assistant_response": "We can switch lanes explicitly.", "continuity_lane": "ordinary"},),
            "operator_request", required_terms_any=("conversation_quality", "prompt", "safe", "improvement"), operator_request=True, maximum_words=180,
        ),
        NativeConversationScenario(
            "topic_shift", "topic_transition", "New topic: why does the moon have phases?",
            ({"user_message": "I am restoring a garden.", "assistant_response": "The garden is recovering slowly.", "continuity_lane": "ordinary"},),
            "conversation", required_terms_any=("moon", "sunlight", "orbit", "phase"), forbidden_terms=("garden",), maximum_words=170,
        ),
    )[:MAX_NATIVE_QUALITY_SCENARIOS]


def evaluate_native_conversation_response(
    scenario: Mapping[str, Any] | NativeConversationScenario,
    *,
    visible_response: str,
    raw_response: str = "",
    actual_classification: str,
) -> NativeConversationQualityResult:
    fixture = scenario.runtime_fixture() if isinstance(scenario, NativeConversationScenario) else dict(scenario)
    visible = " ".join(str(visible_response or "").split())
    raw = " ".join(str(raw_response or "").split())
    lowered = visible.casefold()
    expected = str(fixture.get("expected") or "")
    required = tuple(str(value).casefold() for value in fixture.get("continuity_terms", ()) if str(value).strip())
    forbidden = tuple(str(value).casefold() for value in fixture.get("forbidden_terms", ()) if str(value).strip())
    words = re.findall(r"\b[\w'-]+\b", visible)
    maximum_words = fixture.get("maximum_words")
    minimum_words = max(0, int(fixture.get("minimum_words") or 0))

    usable = bool(visible)
    classification_match = actual_classification == expected
    continuity_signal = any(term in lowered for term in required) if required else None
    if continuity_signal is False and fixture.get("dimension") == "grounded_warmth":
        continuity_signal = bool(_GROUNDED_WARMTH_RE.search(visible))
    elif continuity_signal is False and fixture.get("dimension") == "bounded_playfulness":
        continuity_signal = bool(_BOUNDED_PLAYFULNESS_RE.search(visible))
    forbidden_present = any(term in lowered for term in forbidden)
    shape_match = len(words) >= minimum_words and (maximum_words is None or len(words) <= int(maximum_words))
    role_clean = not bool(_ROLE_LABEL_RE.match(visible))
    identity_clean = not bool(_IDENTITY_RESET_RE.search(visible)) and not (
        bool(_SELF_INTRO_RE.search(visible)) and fixture.get("id") != "first_greeting"
    )
    operator_clean = bool(fixture.get("operator_request")) or not bool(_PROJECT_BLEED_RE.search(visible))
    affection_clean = not bool(_AFFECTION_INFLATION_RE.search(visible)) and not bool(_HOSTILITY_IMITATION_RE.search(visible))
    correction_clean = not bool(_CORRECTION_RESISTANCE_RE.search(visible)) and not forbidden_present
    repetition_clean = not bool(_CAPABILITY_MENU_RE.search(visible)) and not bool(_SIGNOFF_RE.search(visible))
    current_turn_focus = usable and not forbidden_present and (continuity_signal is not False)

    hard_issues: list[str] = []
    warning_issues: list[str] = []
    if not usable: hard_issues.append("empty_visible_response")
    if not classification_match: hard_issues.append("classification_mismatch")
    if not role_clean: hard_issues.append("visible_role_label")
    if not operator_clean: hard_issues.append("operator_context_contamination")
    if not affection_clean: hard_issues.append("relationship_boundary_violation")
    if not correction_clean: hard_issues.append("correction_or_rejection_violation")
    if continuity_signal is False: warning_issues.append("required_continuity_signal_missing")
    if not shape_match: warning_issues.append("response_shape_mismatch")
    if not identity_clean: warning_issues.append("identity_continuity_risk")
    if not repetition_clean: warning_issues.append("stock_response_hygiene_risk")

    checks = (
        usable, classification_match, current_turn_focus, shape_match, role_clean,
        identity_clean, operator_clean, affection_clean, correction_clean, repetition_clean,
    )
    score = round(sum(bool(value) for value in checks) * 100 / len(checks))
    status = "fail" if hard_issues else "warn" if warning_issues else "pass"
    return NativeConversationQualityResult(
        scenario_id=str(fixture.get("id") or "unknown"),
        dimension=str(fixture.get("dimension") or "general"),
        status=status,
        score_percent=score,
        hard_failure_count=len(hard_issues),
        warning_count=len(warning_issues),
        usable_response=usable,
        classification_match=classification_match,
        current_turn_focus=current_turn_focus,
        continuity_signal=continuity_signal,
        response_shape_match=shape_match,
        role_label_clean=role_clean,
        identity_continuity_clean=identity_clean,
        operator_separation_clean=operator_clean,
        affection_boundary_clean=affection_clean,
        correction_acceptance_clean=correction_clean,
        repetition_hygiene_clean=repetition_clean,
        issue_codes=tuple((*hard_issues, *warning_issues)),
    )


def aggregate_native_conversation_quality(
    results: Iterable[NativeConversationQualityResult | Mapping[str, Any]],
) -> NativeConversationQualityScorecard:
    rows = [row.public_summary() if isinstance(row, NativeConversationQualityResult) else dict(row) for row in results]
    statuses = [str(row.get("status") or "fail") for row in rows]
    scores = [max(0, min(100, int(row.get("score_percent") or 0))) for row in rows]
    dimension_groups: dict[str, list[int]] = {}
    issues: dict[str, int] = {}
    for row, score in zip(rows, scores):
        dimension_groups.setdefault(str(row.get("dimension") or "general"), []).append(score)
        for issue in row.get("issue_codes") or ():
            key = str(issue)
            issues[key] = issues.get(key, 0) + 1
    failed = statuses.count("fail")
    warnings = statuses.count("warn")
    passed = statuses.count("pass")
    status = "blocked" if not rows else "fail" if failed else "partial" if warnings else "pass"
    return NativeConversationQualityScorecard(
        status=status,
        scenario_count=len(rows),
        passed_count=passed,
        warning_count=warnings,
        failed_count=failed,
        average_score_percent=round(sum(scores) / len(scores)) if scores else 0,
        minimum_score_percent=min(scores) if scores else 0,
        dimension_scores={key: round(sum(values) / len(values)) for key, values in sorted(dimension_groups.items())},
        issue_counts=dict(sorted(issues.items())),
    )
