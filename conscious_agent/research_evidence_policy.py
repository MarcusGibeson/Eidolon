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

Corroboration is authority-sensitive rather than universal. A blanket "two
sources always" rule would make the official asyncio documentation insufficient
to describe asyncio, which is bureaucracy, not rigour. A blanket "one source
always" rule let an unclassified blog establish what enforcement actions the EU
has not taken. So how many independent publishers a finding needs is decided by
the strongest source actually supporting it and by how much a wrong answer
costs: a claim about pricing, causation, enforcement, market behaviour, or the
absence of something needs corroboration whatever the objective was called.

Admissibility is separate from answering. A finding whose own text says the
sources do not specify the thing that was asked is not a weakly supported answer;
it is not an answer. Claim/source fit measures whether the citations are about
the finding, which that finding passes, so relevance to the objective has to be
its own condition.

This module decides nothing on its own. It has no side effects, contacts no
provider, and its results carry fixed condition codes and counts only - never
claim text, quotes or URLs.
"""

from dataclasses import dataclass
from collections.abc import Mapping
import re
from typing import Any, Callable

CONTRACT_VERSION = "v2731.0.7"

MINIMUM_CLAIM_SOURCE_FIT = 0.5
MINIMUM_INDEPENDENT_PUBLISHERS = 2
# How near an objective's own term must sit to a "the sources do not say"
# admission before that admission is read as being about the question asked.
# Asymmetric because the two positions are not equivalent: what a concession is
# about usually follows it ("do not specify the causes") at some distance, while
# a subject sits immediately before it ("the causes are unspecified"). Reaching
# as far backwards as forwards would sweep in the clause that did answer.
OBJECTIVE_TERM_PROXIMITY = 72
OBJECTIVE_TERM_LOOKBEHIND = 24
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


# How far a single source can carry a claim on its own. Ordered weakest first so
# the strongest supporting source decides what the finding still needs.
TIER_NONE = "none"
TIER_NON_AUTHORITATIVE = "non_authoritative"
TIER_UNCLASSIFIED = "unclassified"
TIER_COMMUNITY = "community"
TIER_SPECIALIST = "specialist"
TIER_PRIMARY = "primary"

AUTHORITY_TIER_ORDER = (
    TIER_NONE, TIER_NON_AUTHORITATIVE, TIER_UNCLASSIFIED, TIER_COMMUNITY, TIER_SPECIALIST, TIER_PRIMARY,
)

_TIER_FOR_SOURCE_KIND = {
    "primary_official": TIER_PRIMARY,
    "primary_data": TIER_PRIMARY,
    "specialist_secondary": TIER_SPECIALIST,
    "reputable_secondary": TIER_SPECIALIST,
    "community_experience": TIER_COMMUNITY,
}

# A source that can stand alone for an ordinary descriptive claim.
SELF_SUFFICIENT_TIERS = frozenset({TIER_PRIMARY, TIER_SPECIALIST})


def source_authority_tier(citation: Mapping[str, Any]) -> str:
    """How much weight one source can carry by itself."""
    if str(citation.get("evidence_role") or "") in NON_AUTHORITATIVE_EVIDENCE_ROLES:
        return TIER_NON_AUTHORITATIVE
    kind = str(citation.get("source_kind") or "unknown").strip().lower()
    return _TIER_FOR_SOURCE_KIND.get(kind, TIER_UNCLASSIFIED)


def strongest_tier(citations: list[Mapping[str, Any]]) -> str:
    """The best support the finding actually has, not the average."""
    best = TIER_NONE
    for citation in citations:
        tier = source_authority_tier(citation)
        if AUTHORITY_TIER_ORDER.index(tier) > AUTHORITY_TIER_ORDER.index(best):
            best = tier
    return best


# Claim shapes where a single uncorroborated source is not good enough, because
# being wrong is expensive and the error is not self-announcing. Deliberately
# narrow: a connective like "because" is not a causal assertion, and matching it
# would make every finding higher-risk and collapse the tiering back into a
# universal two-source rule.
_CLAIM_RISK_PATTERNS: dict[str, re.Pattern[str]] = {
    "pricing_claim": re.compile(
        r"\$\s?\d|\b\d+(?:\.\d+)?\s*(?:%|percent|cents?|dollars?)\b|"
        r"\b(?:pric(?:e|es|ed|ing)|cost(?:s|ed)?|fee|fees|surcharge|per\s+transaction|"
        r"subscription|free\s+tier|paid\s+plan|billing)\b",
        re.IGNORECASE,
    ),
    "enforcement_claim": re.compile(
        r"\b(?:fine|fines|fined|penalt(?:y|ies)|sanction(?:s|ed)?|enforce(?:d|s|ment)|"
        r"lawsuit|prosecut\w*|indict\w*|injunction|settlement|ruled|ruling|"
        r"violation|non[- ]?compliance|regulator[sy]?)\b",
        re.IGNORECASE,
    ),
    "market_claim": re.compile(
        r"\b(?:market\s+(?:share|size)|revenue|adoption\s+rate|growth\s+rate|"
        r"user\s+base|customer\s+base|demand\s+for|willingness\s+to\s+pay|churn)\b",
        re.IGNORECASE,
    ),
    "causal_claim": re.compile(
        r"\b(?:cause[sd]?|causing|caused\s+by|triggered\s+by|led\s+to|resulted\s+(?:in|from)|"
        r"driven\s+by|attributable\s+to|responsible\s+for|reason\s+(?:for|why)|"
        r"consequence\s+of|as\s+a\s+result\s+of)\b",
        re.IGNORECASE,
    ),
    "negative_claim": re.compile(
        r"\bno\s+(?:confirmed|known|reported|recorded|public|documented|evidence|instances?|cases?|records?)\b|"
        r"\bthere\s+(?:is|are|were|was)\s+no\b|\bnone\s+(?:have|has|were|was)\b|"
        r"\b(?:has|have|had)\s+not\s+(?:yet\s+)?been\s+(?:issued|imposed|announced|published|confirmed|reported|brought)\b|"
        r"\bnever\s+been\b|\bno\s+longer\b",
        re.IGNORECASE,
    ),
    "availability_claim": re.compile(
        r"\bdeprecat\w*|\bend[\s-]of[\s-](?:life|support)\b|\bdiscontinued\b|\bsunset(?:ting)?\b|"
        r"\bgenerally\s+available\b|\bno\s+longer\s+(?:available|supported|maintained)\b|"
        r"\bunsupported\b|\bsupported\s+(?:until|through)\b",
        re.IGNORECASE,
    ),
}


# A finding reaches this module in two shapes. The synthesis payload carries the
# claim as "title" plus "summary"; a report row carries it as "finding" or, for a
# recommendation, "conclusion". Reading only one shape leaves the claim-risk and
# relevance conditions evaluating an empty string, which they pass silently.
_FINDING_TEXT_KEYS = ("title", "summary", "finding", "claim", "conclusion", "statement", "text")


def _finding_text(finding: Mapping[str, Any]) -> str:
    parts = [str(finding.get(key) or "").strip() for key in _FINDING_TEXT_KEYS]
    return " ".join(dict.fromkeys(part for part in parts if part))


def claim_risk_flags(finding: Mapping[str, Any]) -> tuple[str, ...]:
    """Which higher-risk claim shapes this finding makes. Fixed codes only."""
    text = _finding_text(finding)
    if not text:
        return ()
    return tuple(sorted(code for code, pattern in _CLAIM_RISK_PATTERNS.items() if pattern.search(text)))


# Objectives whose currency requirement already makes every claim under them
# time-sensitive, so corroboration is required regardless of claim shape.
HIGHER_RISK_POLICY_CODES = frozenset({"current", "demand"})


def required_publisher_count(tier: str, risk_flags: tuple[str, ...], policy_code: str) -> int:
    """How many independent publishers this finding needs, given its best source."""
    if risk_flags or policy_code in HIGHER_RISK_POLICY_CODES:
        return MINIMUM_INDEPENDENT_PUBLISHERS
    return 1 if tier in SELF_SUFFICIENT_TIERS else MINIMUM_INDEPENDENT_PUBLISHERS


# A finding conceding that the sources do not answer the question. Distinct from
# declared uncertainty, which qualifies an answer that was nonetheless given.
_NON_ANSWER = re.compile(
    r"(?:do(?:es)?\s+not|did\s+not|cannot|can(?:no|')t|could\s+not|fail(?:s|ed)?\s+to|without)\s+"
    r"(?:\w+\s+){0,2}"
    r"(?:specify|specifying|state|stating|say|explain|explaining|indicate|address|identify|"
    r"establish|determine|mention|describe|confirm|quantify|clarify|attribute)"
    r"|\bno\s+(?:information|details?|explanation|indication|basis|specifics?)\b"
    r"|\b(?:unclear|unspecified|not\s+specified|not\s+stated|not\s+established|left\s+open)\b",
    re.IGNORECASE,
)

_TERM = re.compile(r"[a-z0-9]{4,}", re.IGNORECASE)
_TERM_STOPWORDS = frozenset({
    "research", "about", "what", "which", "when", "where", "does", "into", "with", "from",
    "that", "this", "their", "there", "have", "been", "will", "would", "could", "should",
    "current", "currently", "recent", "latest", "state", "status", "using", "used", "make",
    "made", "more", "most", "than", "then", "some", "such", "also", "over", "under", "between",
    "information", "evidence", "source", "sources", "page", "pages", "find", "list", "give",
})


def _stem(token: str) -> str:
    """Crude plural trim so "causes" and "cause" are the same term.

    Only the plural "s" comes off. Trimming "es" as a unit would map "causes" to
    "caus" while leaving "cause" alone, which is worse than not stemming at all.
    """
    lowered = token.lower()
    if len(lowered) > 4 and lowered.endswith("ies"):
        return lowered[:-3] + "y"
    if len(lowered) > 4 and lowered.endswith("s") and not lowered.endswith("ss"):
        return lowered[:-1]
    return lowered


def objective_terms(text: str, limit: int = 24) -> tuple[str, ...]:
    """Substantive terms from the objective, for judging whether it was answered."""
    seen: list[str] = []
    for token in _TERM.findall(str(text or "")):
        if token.lower() in _TERM_STOPWORDS:
            continue
        stem = _stem(token)
        if stem not in seen:
            seen.append(stem)
        if len(seen) >= limit:
            break
    return tuple(seen)


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
#
# Each takes the finding, its admissible citations, and a context carrying what
# the objective asked and which policy is in force. Conditions that need neither
# ignore the third argument.

def _publisher_count(admissible: list[Mapping[str, Any]]) -> int:
    publishers = {str(row.get("publisher_digest") or "") for row in admissible}
    publishers.discard("")
    return len(publishers)


def _citation_present(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]], context: Mapping[str, Any]) -> bool:
    return bool(admissible)


def _uncertainty_declared_where_warranted(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]], context: Mapping[str, Any]) -> bool:
    """A thinly supported finding must say what it does not establish."""
    if len(admissible) >= UNCERTAINTY_WARRANTED_BELOW_CITATIONS:
        return True
    values = finding.get("uncertainties")
    return isinstance(values, list) and any(str(item or "").strip() for item in values)


def _independent_publishers(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]], context: Mapping[str, Any]) -> bool:
    return _publisher_count(admissible) >= MINIMUM_INDEPENDENT_PUBLISHERS


def _corroboration_satisfied(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]], context: Mapping[str, Any]) -> bool:
    """Enough independent publishers for what this claim is and what backs it.

    One authoritative primary source settles an ordinary reference question. One
    unclassified aggregator does not settle what a company charges.
    """
    if not admissible:
        return False
    required = required_publisher_count(
        strongest_tier(admissible),
        tuple(context.get("claim_risk_flags") or ()),
        str(context.get("policy_code") or ""),
    )
    return _publisher_count(admissible) >= required


def _answers_objective(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]], context: Mapping[str, Any]) -> bool:
    """The finding resolves the question, rather than reporting that it could not.

    Only fires when the concession lands on a term the objective actually asked
    about: "sources do not give a release date" is fatal to a question about
    release dates and irrelevant to a question about behaviour.
    """
    terms = tuple(context.get("objective_terms") or ())
    text = _finding_text(finding)
    if not terms or not text:
        return True  # nothing to judge against; see objective_terms_supplied
    for match in _NON_ANSWER.finditer(text):
        window = text[max(0, match.start() - OBJECTIVE_TERM_LOOKBEHIND): match.end() + OBJECTIVE_TERM_PROXIMITY]
        stems = {_stem(token) for token in _TERM.findall(window)}
        if stems & set(terms):
            return False
    return True


FINDING_CONDITIONS: dict[str, Callable[[Mapping[str, Any], list[Mapping[str, Any]], Mapping[str, Any]], bool]] = {
    "citation_present": _citation_present,
    "uncertainty_declared_where_warranted": _uncertainty_declared_where_warranted,
    "answers_objective": _answers_objective,
    "corroboration_satisfied": _corroboration_satisfied,
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


# Who published this, is it about the claim, does the finding answer the question
# asked, is it corroborated as far as its own sources and risk require, and does
# it admit its limits.
BASELINE_EVIDENCE_POLICY = EvidencePolicy(
    policy_code="baseline",
    citation_conditions=("source_authority_assessed", "source_not_promotional", "claim_source_fit"),
    finding_conditions=(
        "citation_present", "answers_objective", "corroboration_satisfied",
        "uncertainty_declared_where_warranted",
    ),
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


POLICY_FOR_CURRENCY_REQUIREMENT = {
    "reference": REFERENCE_EVIDENCE_POLICY,
    "current": CURRENT_EVIDENCE_POLICY,
    "demand_current": DEMAND_EVIDENCE_POLICY,
}


def policy_for_objective(currency_requirement: str = "") -> EvidencePolicy:
    """Select a policy from what the objective means, not from a freshness window.

    Deriving the policy from the window in force reversed cause and effect: a
    default window silently created a currency requirement, and a documentation
    lookup was asked for evidence from the last thirty days.
    """
    return POLICY_FOR_CURRENCY_REQUIREMENT.get(
        str(currency_requirement or "").strip().lower(), BASELINE_EVIDENCE_POLICY
    )


def evaluate_policy(
    policy: EvidencePolicy,
    *,
    finding: Mapping[str, Any] | None,
    citations: list[Mapping[str, Any]] | None,
    assessments_by_citation: Mapping[str, Mapping[str, Any]] | None = None,
    objective: str = "",
) -> dict[str, Any]:
    """Report which named conditions a finding and its citations fail.

    Returns counts and fixed condition codes only. Nothing here refuses anything;
    a caller decides what to do with the result.
    """
    row = dict(finding or {})
    rows = [dict(item) for item in (citations or []) if isinstance(item, Mapping)]
    assessments = dict(assessments_by_citation or {})

    try:
        from research_source_classification import classification_reason, document_form
    except ImportError:  # measurement must never break the run it observes
        classification_reason = document_form = None

    citation_failures: dict[str, int] = {}
    authority_states: dict[str, int] = {}
    authority_tiers: dict[str, int] = {}
    url_classification_reasons: dict[str, int] = {}
    document_forms: dict[str, int] = {}
    version_signals = 0
    admissible: list[Mapping[str, Any]] = []
    for citation in rows:
        state = source_authority_state(citation)
        authority_states[state] = authority_states.get(state, 0) + 1
        tier = source_authority_tier(citation)
        authority_tiers[tier] = authority_tiers.get(tier, 0) + 1
        if classification_reason is not None:
            url = str(citation.get("canonical_url") or citation.get("public_url") or "")
            # Which rule family decided this source, so "still unclassified" can be
            # read as novel sources or as a classifier blind spot rather than a
            # number with no explanation attached.
            reason = classification_reason(url)
            url_classification_reasons[reason] = url_classification_reasons.get(reason, 0) + 1
            form = document_form(url) or "none"
            document_forms[form] = document_forms.get(form, 0) + 1
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

    terms = objective_terms(objective)
    risk_flags = claim_risk_flags(row)
    supporting_tier = strongest_tier(admissible)
    context = {
        "policy_code": policy.policy_code,
        "claim_risk_flags": risk_flags,
        "objective_terms": terms,
    }
    finding_failures = [
        name for name in policy.finding_conditions
        if name in FINDING_CONDITIONS and not FINDING_CONDITIONS[name](row, admissible, context)
    ]

    return {
        "contract_version": CONTRACT_VERSION,
        "policy_code": policy.policy_code,
        "evaluated_citation_count": len(rows),
        "admissible_citation_count": len(admissible),
        "citation_condition_failures": dict(sorted(citation_failures.items())),
        "finding_condition_failures": sorted(finding_failures),
        "authority_states": dict(sorted(authority_states.items())),
        "authority_tiers": dict(sorted(authority_tiers.items())),
        "url_classification_reasons": dict(sorted(url_classification_reasons.items())),
        "document_forms": dict(sorted(document_forms.items())),
        "version_signal_count": version_signals,
        "claim_risk_flags": list(risk_flags),
        "supporting_authority_tier": supporting_tier,
        "independent_publisher_count": _publisher_count(admissible),
        "required_publisher_count": required_publisher_count(supporting_tier, risk_flags, policy.policy_code),
        # Whether the relevance check had an objective to judge against, so a
        # clean answers_objective cannot be mistaken for a check that ran.
        "objective_terms_supplied": bool(terms),
        "would_admit": not finding_failures and bool(admissible),
        "enforced": False,
    }


__all__ = [
    "CONTRACT_VERSION",
    "AUTHORITY_KNOWN_AUTHORITATIVE", "AUTHORITY_KNOWN_NON_AUTHORITATIVE", "AUTHORITY_UNCLASSIFIED",
    "BASELINE_EVIDENCE_POLICY", "REFERENCE_EVIDENCE_POLICY", "CURRENT_EVIDENCE_POLICY", "DEMAND_EVIDENCE_POLICY",
    "CURRENCY_LAYER", "POLICIES", "EvidencePolicy",
    "CITATION_CONDITIONS", "FINDING_CONDITIONS",
    "evaluate_policy", "policy_for_objective", "POLICY_FOR_CURRENCY_REQUIREMENT",
    "source_authority_state", "version_signal_present",
    "AUTHORITY_TIER_ORDER", "SELF_SUFFICIENT_TIERS", "HIGHER_RISK_POLICY_CODES",
    "TIER_NONE", "TIER_NON_AUTHORITATIVE", "TIER_UNCLASSIFIED",
    "TIER_COMMUNITY", "TIER_SPECIALIST", "TIER_PRIMARY",
    "source_authority_tier", "strongest_tier", "claim_risk_flags",
    "required_publisher_count", "objective_terms",
]
