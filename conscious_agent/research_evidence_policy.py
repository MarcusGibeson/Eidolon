from __future__ import annotations

"""Declarative evidence policy shared by every research objective shape.

Admission rules previously existed only for demand-shaped objectives. A general
research objective was admitted on a title, a summary and one observed citation,
so a single undated forum post could carry a finding, while a demand claim needed
two fresh independent non-promotional survey sources. That is not two
calibrations, it is one gate that exists and one that does not.

A policy is data: named conditions evaluated against a citation, or against a
finding as a whole. The baseline applies to every objective; a stricter policy
composes on top of it rather than restating it. Evaluation reports which named
conditions failed and how often, so a policy can be measured on real corpora
before it is allowed to refuse anything.

This module decides nothing on its own. It has no side effects, contacts no
provider, and its results carry fixed condition codes and counts only - never
claim text, quotes or URLs.
"""

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Callable

CONTRACT_VERSION = "v2731.0.4"

MINIMUM_CLAIM_SOURCE_FIT = 0.5
MINIMUM_INDEPENDENT_PUBLISHERS = 2
SUPPORTING_EVIDENCE_KINDS = frozenset({"customer_experience", "survey_result", "usage_measurement"})
NON_AUTHORITATIVE_EVIDENCE_ROLES = frozenset({
    "invalid_public_url", "generic_definition", "promotional_summary",
    "first_party_product_claim", "implementation_precedent",
    "implementation_documentation", "pricing_or_free_tier",
})


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


# --- citation conditions -----------------------------------------------------
# Each answers one question about a single cited source.

def _source_authority_known(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """The source was classified at all. Unknown authority supports no dimension."""
    return str(citation.get("source_kind") or "unknown").strip().lower() != "unknown"


def _source_not_promotional(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """The source is not selling the thing it is cited as evidence about."""
    return str(citation.get("evidence_role") or "") not in NON_AUTHORITATIVE_EVIDENCE_ROLES


def _publication_date_declared(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """The document says when it was published. Recency is a separate question."""
    return bool(citation.get("freshness_known")) or str(citation.get("freshness") or "unknown") != "unknown"


def _claim_source_fit(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """The cited page is actually about the claim, not merely observed."""
    relevance = _number(citation.get("relevance_score"))
    return relevance is not None and relevance >= MINIMUM_CLAIM_SOURCE_FIT


def _freshness_current(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """The declared date is inside the window this objective considers current."""
    return bool(citation.get("fresh_enough")) or str(citation.get("freshness") or "") == "fresh"


def _stance_supports(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """The assessment of this source supports the claim it is cited for."""
    return str((assessment or {}).get("model_assessment") or "") == "supports"


def _evidence_type_admissible(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """The source is the kind of thing that can establish this dimension."""
    return str((assessment or {}).get("model_evidence_kind") or "") in SUPPORTING_EVIDENCE_KINDS


CITATION_CONDITIONS: dict[str, Callable[[Mapping[str, Any], Mapping[str, Any] | None], bool]] = {
    "source_authority_known": _source_authority_known,
    "source_not_promotional": _source_not_promotional,
    "publication_date_declared": _publication_date_declared,
    "claim_source_fit": _claim_source_fit,
    "freshness_current": _freshness_current,
    "stance_supports": _stance_supports,
    "evidence_type_admissible": _evidence_type_admissible,
}


# --- finding conditions ------------------------------------------------------
# Each answers one question about the finding and its admissible citations.

def _citation_present(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]]) -> bool:
    return bool(admissible)


def _uncertainty_declared(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]]) -> bool:
    """A finding states what it does not establish."""
    values = finding.get("uncertainties")
    return isinstance(values, list) and any(str(item or "").strip() for item in values)


def _independent_publishers(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]]) -> bool:
    publishers = {str(row.get("publisher_digest") or "") for row in admissible}
    publishers.discard("")
    return len(publishers) >= MINIMUM_INDEPENDENT_PUBLISHERS


FINDING_CONDITIONS: dict[str, Callable[[Mapping[str, Any], list[Mapping[str, Any]]], bool]] = {
    "citation_present": _citation_present,
    "uncertainty_declared": _uncertainty_declared,
    "independent_publishers": _independent_publishers,
}


@dataclass(frozen=True)
class EvidencePolicy:
    """Named conditions a finding and its citations must satisfy."""

    policy_code: str
    citation_conditions: tuple[str, ...]
    finding_conditions: tuple[str, ...]

    def tightened(self, policy_code: str, *, citation: tuple[str, ...] = (), finding: tuple[str, ...] = ()) -> "EvidencePolicy":
        """Compose a stricter policy on top of this one without restating it."""
        return EvidencePolicy(
            policy_code=policy_code,
            citation_conditions=self.citation_conditions + tuple(c for c in citation if c not in self.citation_conditions),
            finding_conditions=self.finding_conditions + tuple(c for c in finding if c not in self.finding_conditions),
        )


BASELINE_EVIDENCE_POLICY = EvidencePolicy(
    policy_code="baseline",
    citation_conditions=(
        "source_authority_known",
        "source_not_promotional",
        "publication_date_declared",
        "claim_source_fit",
    ),
    finding_conditions=("citation_present", "uncertainty_declared"),
)

DEMAND_EVIDENCE_POLICY = BASELINE_EVIDENCE_POLICY.tightened(
    "demand",
    citation=("freshness_current", "stance_supports", "evidence_type_admissible"),
    finding=("independent_publishers",),
)

POLICIES = {policy.policy_code: policy for policy in (BASELINE_EVIDENCE_POLICY, DEMAND_EVIDENCE_POLICY)}


def policy_for_dimension(dimension: str) -> EvidencePolicy:
    """The baseline applies everywhere; a dimension may tighten it."""
    return DEMAND_EVIDENCE_POLICY if str(dimension or "").strip().lower() == "demand" else BASELINE_EVIDENCE_POLICY


def evaluate_policy(
    policy: EvidencePolicy,
    *,
    finding: Mapping[str, Any] | None,
    citations: list[Mapping[str, Any]] | None,
    assessments_by_citation: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Report which named conditions a finding and its citations fail.

    Returns counts and fixed condition codes only. Nothing here refuses anything;
    a caller decides what to do with the result.
    """
    row = dict(finding or {})
    rows = [dict(item) for item in (citations or []) if isinstance(item, Mapping)]
    assessments = dict(assessments_by_citation or {})

    citation_failures: dict[str, int] = {}
    admissible: list[Mapping[str, Any]] = []
    for citation in rows:
        assessment = assessments.get(str(citation.get("citation_id") or ""))
        failed = [
            name for name in policy.citation_conditions
            if name in CITATION_CONDITIONS and not CITATION_CONDITIONS[name](citation, assessment)
        ]
        for name in failed:
            citation_failures[name] = citation_failures.get(name, 0) + 1
        if not failed:
            admissible.append(citation)

    finding_failures = [
        name for name in policy.finding_conditions
        if name in FINDING_CONDITIONS and not FINDING_CONDITIONS[name](row, admissible)
    ]

    return {
        "contract_version": CONTRACT_VERSION,
        "policy_code": policy.policy_code,
        "evaluated_citation_count": len(rows),
        "admissible_citation_count": len(admissible),
        "citation_condition_failures": dict(sorted(citation_failures.items())),
        "finding_condition_failures": sorted(finding_failures),
        "would_admit": not finding_failures and bool(admissible),
        "enforced": False,
    }


__all__ = [
    "CONTRACT_VERSION",
    "BASELINE_EVIDENCE_POLICY",
    "DEMAND_EVIDENCE_POLICY",
    "POLICIES",
    "EvidencePolicy",
    "CITATION_CONDITIONS",
    "FINDING_CONDITIONS",
    "evaluate_policy",
    "policy_for_dimension",
]
