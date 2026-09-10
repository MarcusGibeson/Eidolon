from __future__ import annotations

"""v1085.2 deterministic recency/salience balancing.

The balancer prevents a stream of recent trivial records from excluding an older
operator-curated or high-importance relevant record. It never invents relevance,
mutates records, or calls generation/embedding providers.
"""

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from context_relevance_ranking import RankedContextCandidate

CONTEXT_SALIENCE_SCHEMA_VERSION = "1"
SALIENCE_RESERVATION_WINDOW = 3


@dataclass(frozen=True)
class SalienceBalanceEvidence:
    candidate_count: int
    salient_candidate_count: int
    relevant_salient_candidate_count: int
    reservations_applied: int
    recent_trivial_demotions: int
    reservation_window: int = SALIENCE_RESERVATION_WINDOW
    read_only: bool = True
    provider_invoked: bool = False
    writes_state: bool = False
    schema_version: str = CONTEXT_SALIENCE_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result["type"] = "recency_salience_balance"
        result["content_free"] = True
        return result


def _eligible_salient(evidence: RankedContextCandidate) -> bool:
    return bool(
        evidence.salient
        and evidence.status_score > 0
        and (
            evidence.lexical_score > 0
            or evidence.relationship_relevant
        )
    )


def _recent_trivial(evidence: RankedContextCandidate) -> bool:
    return bool(
        evidence.recency_score >= 3
        and evidence.lexical_score == 0
        and evidence.importance_score == 0
        and evidence.operator_curation_score == 0
        and not evidence.relationship_relevant
    )


def balance_ranked_context(
    ranked: Sequence[tuple[Mapping[str, Any], RankedContextCandidate]],
) -> tuple[list[tuple[Mapping[str, Any], RankedContextCandidate]], SalienceBalanceEvidence]:
    ordered = list(ranked)
    eligible = [index for index, (_record, evidence) in enumerate(ordered) if _eligible_salient(evidence)]
    reservations = 0
    demotions = 0
    if eligible and not any(index < SALIENCE_RESERVATION_WINDOW for index in eligible):
        selected_index = eligible[0]
        selected = ordered.pop(selected_index)
        insertion = min(1, len(ordered))
        displaced = ordered[insertion] if insertion < len(ordered) else None
        ordered.insert(insertion, selected)
        reservations = 1
        if displaced is not None and _recent_trivial(displaced[1]):
            demotions = 1
    evidence = SalienceBalanceEvidence(
        candidate_count=len(ordered),
        salient_candidate_count=sum(1 for _record, row in ordered if row.salient),
        relevant_salient_candidate_count=sum(1 for _record, row in ordered if _eligible_salient(row)),
        reservations_applied=reservations,
        recent_trivial_demotions=demotions,
    )
    return ordered, evidence
