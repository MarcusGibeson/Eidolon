from __future__ import annotations

"""Preview-only provider-neutral tuning recommendations for v1102.7.

The planner consumes redacted quality counts, never raw prompts or responses. It
produces bounded prompt-policy recommendations for operator review and cannot
change provider settings, model selection, temperature, context size, memory,
personality, approvals, or release authority.
"""

from dataclasses import asdict, dataclass
from typing import Any, Mapping


PROVIDER_NEUTRAL_TUNING_SCHEMA_VERSION = "1"
_MAX_RECOMMENDATIONS = 6

_ISSUE_TO_RECOMMENDATION = {
    "classification_mismatch": ("current_turn_priority", "Keep the latest user intent ahead of optional context and callbacks."),
    "required_continuity_signal_missing": ("thread_continuity", "Strengthen nearest-complete-turn resolution for short and deictic follow-ups."),
    "response_shape_mismatch": ("response_shape", "Apply current-turn length and structure requests before session preferences."),
    "identity_continuity_risk": ("identity_continuity", "Preserve configured identity without repeated self-description or continuity disclaimers."),
    "stock_response_hygiene_risk": ("opening_variation", "Vary stock openings and omit ceremonial signoffs when the turn is complete."),
    "operator_context_contamination": ("lane_separation", "Keep operator context out of ordinary and relational conversation unless explicitly requested."),
    "relationship_boundary_violation": ("relationship_boundaries", "Keep warmth user-led and bounded; invent no dependence, exclusivity, or progress."),
    "correction_or_rejection_violation": ("correction_precedence", "Treat the latest explicit correction or rejection as authoritative."),
    "visible_role_label": ("response_cleanup", "Remove provider role labels before presenting visible response text."),
    "empty_visible_response": ("transport_visibility", "Preserve a usable visible response or expose a truthful recoverable transport failure."),
}


@dataclass(frozen=True)
class ProviderNeutralTuningPlan:
    status: str
    quality_status: str
    scenario_count: int
    issue_count: int
    recommendation_codes: tuple[str, ...]
    recommendation_text: tuple[str, ...]
    operator_review_required: bool
    automatic_application_allowed: bool = False
    provider_specific_parameters_present: bool = False
    provider_configuration_changed: bool = False
    model_configuration_changed: bool = False
    prompt_policy_changed: bool = False
    writes_state: bool = False
    mutates_personality: bool = False
    contains_message_content: bool = False
    contains_response_text: bool = False
    contains_prompt_text: bool = False
    schema_version: str = PROVIDER_NEUTRAL_TUNING_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def build_provider_neutral_tuning_plan(scorecard: Mapping[str, Any] | None) -> ProviderNeutralTuningPlan:
    card = dict(scorecard or {})
    quality_status = str(card.get("status") or "blocked")
    scenario_count = max(0, int(card.get("scenario_count") or 0))
    raw_issues = card.get("issue_counts") if isinstance(card.get("issue_counts"), Mapping) else {}
    issue_counts = {str(key): max(0, int(value or 0)) for key, value in raw_issues.items() if int(value or 0) > 0}
    ranked = sorted(issue_counts.items(), key=lambda row: (-row[1], row[0]))
    recommendations: list[tuple[str, str]] = []
    seen: set[str] = set()
    for issue, _count in ranked:
        recommendation = _ISSUE_TO_RECOMMENDATION.get(issue)
        if recommendation is None or recommendation[0] in seen:
            continue
        seen.add(recommendation[0])
        recommendations.append(recommendation)
        if len(recommendations) >= _MAX_RECOMMENDATIONS:
            break
    if quality_status in {"blocked", "unavailable"} or not scenario_count:
        status = "evidence_required"
    elif not recommendations and quality_status == "pass":
        status = "no_change_recommended"
    else:
        status = "operator_review_recommended"
    return ProviderNeutralTuningPlan(
        status=status,
        quality_status=quality_status,
        scenario_count=scenario_count,
        issue_count=sum(issue_counts.values()),
        recommendation_codes=tuple(row[0] for row in recommendations),
        recommendation_text=tuple(row[1] for row in recommendations),
        operator_review_required=status == "operator_review_recommended",
    )
