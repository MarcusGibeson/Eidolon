from __future__ import annotations

"""Declarative evidence policy shared by every research objective shape.

Admission rules previously existed only for demand-shaped objectives. A general
research objective was admitted on a title, a summary and one observed citation,
so a single undated forum post could carry a finding, while a demand claim needed
two fresh independent non-promotional survey sources. That is not two
calibrations, it is one gate that exists and one that does not.

A policy is data: named conditions evaluated against a citation, or against a
finding as a whole. A universal baseline asks who published this, whether it is
about the claim, and whether the finding admits what it does not establish.
Currency is a separate layer, applied only where a claim actually depends on it,
because stable reference documentation is not suspicious for lacking a
publication timestamp. Demand tightens further.

Authority is three-valued. Treating an unclassified host as though it had been
assessed and found wanting conflates "we have not classified this" with "this
carries no authority", which are not the same claim.

This module decides nothing on its own. It has no side effects, contacts no
provider, and its results carry fixed condition codes and counts only - never
claim text, quotes or URLs.
"""

from dataclasses import dataclass
from collections.abc import Mapping
import re
from typing import Any, Callable

CONTRACT_VERSION = "v2731.0.5"

MINIMUM_CLAIM_SOURCE_FIT = 0.5
MINIMUM_INDEPENDENT_PUBLISHERS = 2
UNCERTAINTY_WARRANTED_BELOW_CITATIONS = 2
SUPPORTING_EVIDENCE_KINDS = frozenset({"customer_experience", "survey_result", "usage_measurement"})
NON_AUTHORITATIVE_EVIDENCE_ROLES = frozenset({
    "invalid_public_url", "generic_definition", "promotional_summary",
    "first_party_product_claim", "implementation_precedent",
    "implementation_documentation", "pricing_or_free_tier",
})

AUTHORITY_KNOWN_AUTHORITATIVE = "known_authoritative"
AUTHORITY_KNOWN_NON_AUTHORITATIVE = "known_non_authoritative"
AUTHORITY_UNCLASSIFIED = "unclassified"

# A documented version is a currency signal in its own right. Reference material
# is pinned to the version it documents, and that is the compatibility question
# a reader actually has; a posted date would not answer it.
_VERSION_SIGNAL = re.compile(
    r"/v?\d+(?:\.\d+){1,2}(?:/|$)|/(?:stable|latest|current)(?:/|$)|[?&](?:version|v)=", re.IGNORECASE
)


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def source_authority_state(citation: Mapping[str, Any]) -> str:
    """Three-valued authority: assessed and sound, assessed and not, or unassessed."""
    if str(citation.get("evidence_role") or "") in NON_AUTHORITATIVE_EVIDENCE_ROLES:
        return AUTHORITY_KNOWN_NON_AUTHORITATIVE
    kind = str(citation.get("source_kind") or "unknown").strip().lower()
    return AUTHORITY_UNCLASSIFIED if kind in {"", "unknown"} else AUTHORITY_KNOWN_AUTHORITATIVE


def version_signal_present(citation: Mapping[str, Any]) -> bool:
    """The source is pinned to a documented version."""
    url = str(citation.get("canonical_url") or citation.get("public_url") or "")
    return bool(url) and bool(_VERSION_SIGNAL.search(url))


# --- citation conditions -----------------------------------------------------

def _source_authority_assessed(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """Nothing assessed this source as carrying no authority.

    An unclassified host passes: not having classified it is a gap in our
    metadata, not a finding about the source.
    """
    return source_authority_state(citation) != AUTHORITY_KNOWN_NON_AUTHORITATIVE


def _source_authority_known(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """The source was positively classified. Stricter than the baseline asks."""
    return source_authority_state(citation) == AUTHORITY_KNOWN_AUTHORITATIVE


def _source_not_promotional(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    return str(citation.get("evidence_role") or "") not in NON_AUTHORITATIVE_EVIDENCE_ROLES


def _claim_source_fit(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    relevance = _number(citation.get("relevance_score"))
    return relevance is not None and relevance >= MINIMUM_CLAIM_SOURCE_FIT


def _currency_signal_present(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    """Something establishes when or for what this source applies."""
    dated = bool(citation.get("freshness_known")) or str(citation.get("freshness") or "unknown") != "unknown"
    return dated or version_signal_present(citation)


def _freshness_current(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    return bool(citation.get("fresh_enough")) or str(citation.get("freshness") or "") == "fresh"


def _stance_supports(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    return str((assessment or {}).get("model_assessment") or "") == "supports"


def _evidence_type_admissible(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None) -> bool:
    return str((assessment or {}).get("model_evidence_kind") or "") in SUPPORTING_EVIDENCE_KINDS


CITATION_CONDITIONS: dict[str, Callable[[Mapping[str, Any], Mapping[str, Any] | None], bool]] = {
    "source_authority_assessed": _source_authority_assessed,
    "source_authority_known": _source_authority_known,
    "source_not_promotional": _source_not_promotional,
    "claim_source_fit": _claim_source_fit,
    "currency_signal_present": _currency_signal_present,
    "freshness_current": _freshness_current,
    "stance_supports": _stance_supports,
    "evidence_type_admissible": _evidence_type_admissible,
}


# --- finding conditions ------------------------------------------------------

def _citation_present(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]]) -> bool:
    return bool(admissible)


def _uncertainty_declared_where_warranted(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]]) -> bool:
    """A thinly supported finding must say what it does not establish."""
    if len(admissible) >= UNCERTAINTY_WARRANTED_BELOW_CITATIONS:
        return True
    values = finding.get("uncertainties")
    return isinstance(values, list) and any(str(item or "").strip() for item in values)


def _independent_publishers(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]]) -> bool:
    publishers = {str(row.get("publisher_digest") or "") for row in admissible}
    publishers.discard("")
    return len(publishers) >= MINIMUM_INDEPENDENT_PUBLISHERS


FINDING_CONDITIONS: dict[str, Callable[[Mapping[str, Any], list[Mapping[str, Any]]], bool]] = {
    "citation_present": _citation_present,
    "uncertainty_declared_where_warranted": _uncertainty_declared_where_warranted,
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


# Who published this, is it about the claim, and does the finding admit its limits.
BASELINE_EVIDENCE_POLICY = EvidencePolicy(
    policy_code="baseline",
    citation_conditions=("source_authority_assessed", "source_not_promotional", "claim_source_fit"),
    finding_conditions=("citation_present", "uncertainty_declared_where_warranted"),
)

# Applied only where a claim depends on when or for what a source applies.
CURRENCY_LAYER: tuple[str, ...] = ("currency_signal_present",)

# Reference material is pinned to a version rather than a publication date.
REFERENCE_EVIDENCE_POLICY = BASELINE_EVIDENCE_POLICY.tightened("reference", citation=CURRENCY_LAYER)

CURRENT_EVIDENCE_POLICY = BASELINE_EVIDENCE_POLICY.tightened("current", citation=CURRENCY_LAYER + ("freshness_current",))

DEMAND_EVIDENCE_POLICY = BASELINE_EVIDENCE_POLICY.tightened(
    "demand",
    citation=CURRENCY_LAYER + ("freshness_current", "stance_supports", "evidence_type_admissible"),
    finding=("independent_publishers",),
)

POLICIES = {
    policy.policy_code: policy
    for policy in (BASELINE_EVIDENCE_POLICY, REFERENCE_EVIDENCE_POLICY, CURRENT_EVIDENCE_POLICY, DEMAND_EVIDENCE_POLICY)
}


def policy_for_objective(
    dimension: str = "", *, requires_current_evidence: bool = False, reference_material: bool = False,
) -> EvidencePolicy:
    """The baseline applies everywhere; currency and dimension tighten it."""
    if str(dimension or "").strip().lower() == "demand":
        return DEMAND_EVIDENCE_POLICY
    if reference_material:
        return REFERENCE_EVIDENCE_POLICY
    if requires_current_evidence:
        return CURRENT_EVIDENCE_POLICY
    return BASELINE_EVIDENCE_POLICY


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
    authority_states: dict[str, int] = {}
    version_signals = 0
    admissible: list[Mapping[str, Any]] = []
    for citation in rows:
        state = source_authority_state(citation)
        authority_states[state] = authority_states.get(state, 0) + 1
        if version_signal_present(citation):
            version_signals += 1
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
        "authority_states": dict(sorted(authority_states.items())),
        "version_signal_count": version_signals,
        "would_admit": not finding_failures and bool(admissible),
        "enforced": False,
    }


__all__ = [
    "CONTRACT_VERSION",
    "AUTHORITY_KNOWN_AUTHORITATIVE", "AUTHORITY_KNOWN_NON_AUTHORITATIVE", "AUTHORITY_UNCLASSIFIED",
    "BASELINE_EVIDENCE_POLICY", "REFERENCE_EVIDENCE_POLICY", "CURRENT_EVIDENCE_POLICY", "DEMAND_EVIDENCE_POLICY",
    "CURRENCY_LAYER", "POLICIES", "EvidencePolicy",
    "CITATION_CONDITIONS", "FINDING_CONDITIONS",
    "evaluate_policy", "policy_for_objective", "source_authority_state", "version_signal_present",
]
