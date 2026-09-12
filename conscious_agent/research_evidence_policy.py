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
from functools import lru_cache
from collections.abc import Mapping
import re
from typing import Any, Callable
from urllib.parse import urlsplit

CONTRACT_VERSION = "v2732.6.0"

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
# The observation code for a page whose publisher presents its own offering and
# discloses no method (see the adapter's _evidence_producer_signal).
SELF_PROMOTING_PUBLISHER = "self_promoting_publisher"

# Roles that carry no authority whatever the claim: a broken URL, a dictionary
# entry, a page whose own path says it is marketing.
ALWAYS_NON_AUTHORITATIVE_ROLES = frozenset({
    "invalid_public_url", "generic_definition", "promotional_summary", "implementation_precedent",
})

# Roles assigned from a URL path - /pricing, /docs, /plans - which say what a page
# is about, not who stands behind it. Treating them as disqualifying refused a
# vendor as a source for its own posted prices, which is the same document-form
# versus publisher-authority confusion that the documentation rules already fixed.
# Whether they carry authority depends on the claim being made.
CLAIM_RELATIVE_EVIDENCE_ROLES = frozenset({
    "first_party_product_claim", "implementation_documentation", "pricing_or_free_tier",
})

NON_AUTHORITATIVE_EVIDENCE_ROLES = ALWAYS_NON_AUTHORITATIVE_ROLES | CLAIM_RELATIVE_EVIDENCE_ROLES

# Roles the policy derives for itself when a citation arrives without one - which
# every live citation does, because the rows handed to the policy carry no role.
# Only the roles that describe what a page *is* are derived: a broken URL, a
# dictionary entry, a page whose own path says it is marketing. The classifier's
# other roles answer "which demand dimension could this support" and would demote
# docs.python.org and MDN if read as authority, so they are not derived here.
DERIVED_DISQUALIFYING_ROLES = frozenset({"invalid_public_url", "generic_definition", "promotional_summary"})

AUTHORITY_KNOWN_AUTHORITATIVE = "known_authoritative"
AUTHORITY_KNOWN_NON_AUTHORITATIVE = "known_non_authoritative"
AUTHORITY_UNCLASSIFIED = "unclassified"

# A documented version is a currency signal in its own right. Reference material
# is pinned to the version it documents, and that is the compatibility question
# a reader actually has; a posted date would not answer it.
_VERSION_SIGNAL = re.compile(
    r"/v?\d+(?:\.\d+){1,2}(?:/|$)|/(?:stable|latest|current)(?:/|$)|[?&](?:version|v)=", re.IGNORECASE
)


@lru_cache(maxsize=4096)
def _derived_role(url: str, kind: str) -> str:
    """A page-nature role from the shared classifier, or "" when it names none."""
    try:
        from research_source_independence import source_evidence_role
    except ImportError:  # measurement must never break the run it observes
        return ""
    role = str(source_evidence_role({"public_url": url, "canonical_url": url, "source_kind": kind})
               .get("evidence_role") or "")
    return role if role in DERIVED_DISQUALIFYING_ROLES else ""


def _citation_role(citation: Mapping[str, Any]) -> str:
    """The role a citation declares, or the page-nature role derived for it.

    The role checks previously read only a supplied field. Live citations never
    supply one, so the promotional-page exclusion passed every unit test - which
    supply roles - and never fired on a real run.
    """
    supplied = str(citation.get("evidence_role") or "")
    if supplied:
        return supplied
    url = str(citation.get("canonical_url") or citation.get("public_url") or "")
    return _derived_role(url, str(citation.get("source_kind") or "unknown").strip().lower())


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


# How a source stands in relation to the specific claim it is cited for.
# Authority is not a property of a publisher alone: Stripe is the primary source
# for Stripe's posted fees and no source at all for whether Stripe is the best
# processor. Both statements can appear on the same page.
CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL = "first_party_operational_fact"
CLAIM_SOURCE_FIRST_PARTY_PROMOTIONAL = "first_party_promotional_claim"
# A first party making a claim that is neither a fact it sets nor a case for
# itself - the Python documentation describing what cancelling a task does. There
# is nothing special about the relationship, so it is evaluated normally. Naming
# it rather than folding it into third-party keeps the counters honest about who
# published what.
CLAIM_SOURCE_FIRST_PARTY_OTHER = "first_party_other_claim"
CLAIM_SOURCE_THIRD_PARTY = "third_party_evaluation"

# Relationships that carry no special standing and are judged on source kind.
EVALUATED_NORMALLY_RELATIONSHIPS = frozenset({CLAIM_SOURCE_FIRST_PARTY_OTHER, CLAIM_SOURCE_THIRD_PARTY})

# Facts an organisation sets rather than argues for: what it charges, what a plan
# contains, what a limit is, what it still supports.
_OPERATIONAL_FACT_CLAIM = re.compile(
    r"\$\s?\d|\b\d+(?:\.\d+)?\s*(?:%|percent|cents?|dollars?)\b|"
    r"\b(?:charge[sd]?|charging|cost[s]?|pric(?:e|es|ed|ing)|fee|fees|rate|rates|"
    r"per\s+transaction|plan|plans|tier|tiers|includ(?:e|es|ed)|"
    r"limit|limits|quota|quotas|threshold|"
    r"support(?:s|ed)?|unsupported|deprecat\w*|end[\s-]of[\s-](?:life|support)|"
    r"availab(?:le|ility)|version|versions|release[sd]?|requires?|specification|specs?)\b",
    re.IGNORECASE,
)

# Claims an organisation is not a source for, about itself.
_EVALUATIVE_CLAIM = re.compile(
    r"\b(?:best|leading|fastest|easiest|simplest|most\s+popular|preferred|top\s+choice|"
    r"industry[\s-]leading|trusted\s+by|loved\s+by|outperform(?:s|ed)?|superior|"
    r"ideal\s+for|recommend(?:ed|s)?|should\s+(?:use|choose|pick)|"
    r"customers?\s+(?:prefer|love|choose|want)|market\s+demands?)\b",
    re.IGNORECASE,
)

# Host labels that name a surface rather than the organisation publishing it.
_HOST_SURFACE_LABELS = frozenset({
    "www", "docs", "doc", "documentation", "developer", "developers", "devcenter",
    "learn", "support", "help", "api", "blog", "news", "reference", "manual",
    "com", "org", "net", "edu", "gov", "int", "mil", "co", "io", "dev", "app", "cloud",
})


def first_party_source(citation: Mapping[str, Any], terms: tuple[str, ...]) -> bool:
    """The organisation the objective is asking about is the one publishing this.

    Structural rather than enumerated: the objective already names its subject, and
    a publisher whose own domain carries that name is the first party for it.
    "Stripe payment processing fee structure" makes stripe.com first-party, and
    leaves an aggregator writing about Stripe exactly as third-party as it is.
    """
    if not terms:
        return False
    host = (urlsplit(_citation_url(citation)).hostname or "").lower().strip(".")
    if not host:
        return False
    labels = {
        _stem(label) for label in host.split(".")
        if len(label) >= _TERM_MIN_LENGTH and label not in _HOST_SURFACE_LABELS
    }
    # An acronym term never names the publisher. Short labels are mostly suffixes
    # and topic subdomains, so "EU AI Act" would otherwise make every .ai and .eu
    # site, and ai.google, the first party - and first-party standing grants
    # authority. Missing a real first party such as ibm.com is the old behaviour.
    return bool(labels & {term for term in terms if len(term) >= _TERM_MIN_LENGTH})


def claim_source_relationship(
    citation: Mapping[str, Any],
    finding: Mapping[str, Any] | None = None,
    terms: tuple[str, ...] = (),
) -> str:
    """Classify this source's standing for this particular claim."""
    if not first_party_source(citation, terms):
        return CLAIM_SOURCE_THIRD_PARTY
    text = _finding_text(finding or {})
    if _EVALUATIVE_CLAIM.search(text):
        return CLAIM_SOURCE_FIRST_PARTY_PROMOTIONAL
    if _OPERATIONAL_FACT_CLAIM.search(text):
        return CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL
    # Neither a fact it sets nor a case for itself. Downgrading here would have
    # made python.org promotional for a claim about Python's own behaviour, so
    # the ambiguous case changes nothing and is judged on source kind.
    return CLAIM_SOURCE_FIRST_PARTY_OTHER


def source_authority_state(citation: Mapping[str, Any], relationship: str = CLAIM_SOURCE_THIRD_PARTY) -> str:
    """Three-valued authority: assessed and sound, assessed and not, or unassessed."""
    role = _citation_role(citation)
    if role in ALWAYS_NON_AUTHORITATIVE_ROLES:
        return AUTHORITY_KNOWN_NON_AUTHORITATIVE
    if relationship == CLAIM_SOURCE_FIRST_PARTY_PROMOTIONAL:
        return AUTHORITY_KNOWN_NON_AUTHORITATIVE
    if relationship == CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL:
        # The organisation is the record of the fact, whatever a host-shape
        # classifier made of its domain: ubuntu.com is unclassified as a host and
        # authoritative about which Ubuntu releases it still supports.
        return AUTHORITY_KNOWN_AUTHORITATIVE
    if role in CLAIM_RELATIVE_EVIDENCE_ROLES:
        return AUTHORITY_KNOWN_NON_AUTHORITATIVE
    kind = str(citation.get("source_kind") or "unknown").strip().lower()
    return AUTHORITY_UNCLASSIFIED if kind in {"", "unknown"} else AUTHORITY_KNOWN_AUTHORITATIVE


def version_signal_present(citation: Mapping[str, Any]) -> bool:
    """The source is pinned to a documented version."""
    url = str(citation.get("canonical_url") or citation.get("public_url") or "")
    return bool(url) and bool(_VERSION_SIGNAL.search(url))


# A URL pinned to a specific minor version documents that version and nothing
# later. The rolling forms - a bare major version, /stable/, /latest/, or no
# version at all - are the page the publisher keeps current.
_PINNED_MINOR_VERSION = re.compile(r"/v?\d+\.\d+(?:\.\d+)?(?:/|$)")
_ROLLING_VERSION = re.compile(r"/(?:stable|latest|current)(?:/|$)", re.IGNORECASE)


def _citation_url(citation: Mapping[str, Any]) -> str:
    return str(citation.get("canonical_url") or citation.get("public_url") or "")


def authoritative_living_documentation(citation: Mapping[str, Any]) -> bool:
    """Reference material its own publisher maintains, which is a currency signal.

    MDN and Microsoft Learn carry neither a version in the URL nor a publication
    date, and asking them for either rejected the most authoritative answer
    available while a mirror of the same documentation carried the finding. What
    makes a living document current is that the publisher maintains it - so this
    requires primary authority, not merely a documentation-shaped path. A mirror
    is documentation-shaped and maintains nothing.

    Widening the version pattern instead would have been the wrong repair: it
    would admit any URL with a number in it and still miss the undated living
    documentation that prompted the problem.
    """
    if source_authority_tier(citation) != TIER_PRIMARY:
        return False
    url = _citation_url(citation)
    if not url:
        return False
    try:
        from research_source_classification import REFERENCE_DOCUMENTATION_FORM, document_form
    except ImportError:  # measurement must never break the run it observes
        return False
    if document_form(url) != REFERENCE_DOCUMENTATION_FORM:
        return False
    return bool(_ROLLING_VERSION.search(url)) or not _PINNED_MINOR_VERSION.search(url)


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


def source_authority_tier(citation: Mapping[str, Any], relationship: str = CLAIM_SOURCE_THIRD_PARTY) -> str:
    """How much weight one source can carry by itself, for this claim."""
    state = source_authority_state(citation, relationship)
    if state == AUTHORITY_KNOWN_NON_AUTHORITATIVE:
        return TIER_NON_AUTHORITATIVE
    if relationship == CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL:
        # An organisation is the primary record of the facts it sets, whatever a
        # host-shape classifier made of its domain.
        return TIER_PRIMARY
    kind = str(citation.get("source_kind") or "unknown").strip().lower()
    return _TIER_FOR_SOURCE_KIND.get(kind, TIER_UNCLASSIFIED)


def strongest_tier(citations: list[Mapping[str, Any]], relationships: list[str] | None = None) -> str:
    """The best support the finding actually has, not the average."""
    codes = list(relationships or [])
    best = TIER_NONE
    for index, citation in enumerate(citations):
        relationship = codes[index] if index < len(codes) else CLAIM_SOURCE_THIRD_PARTY
        tier = source_authority_tier(citation, relationship)
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


# Risk shapes that a first party settles by definition, because it is the entity
# that sets the fact. Corroborating a posted price against a blog does not make
# the price more true. Every other shape - a negative claim, a causal claim, an
# enforcement or market claim - still needs a second publisher even from a first
# party, and especially then: a vendor reporting no enforcement action against
# itself is exactly when corroboration matters.
FIRST_PARTY_SETTLED_RISK_FLAGS = frozenset({"pricing_claim", "availability_claim"})


def required_publisher_count(
    tier: str,
    risk_flags: tuple[str, ...],
    policy_code: str,
    first_party_operational: bool = False,
) -> int:
    """How many independent publishers this finding needs, given its best source."""
    if first_party_operational and set(risk_flags) <= FIRST_PARTY_SETTLED_RISK_FLAGS:
        return 1
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

_TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_TERM_MIN_LENGTH = 4
# Length alone kept "the" and "how" out, and every acronym with them: "how GPS
# works" had no term for GPS and "TCP and UDP" none for either protocol, so a
# correct answer about them looked off-topic. Length cannot tell GPS from "how";
# the writer's casing can. A shorter word is a term when it is written in
# capitals ("EU", "TCP") or mixes letters with digits ("S3", "5G").
_ACRONYM_MIN_LENGTH = 2
# "APIs", "GPUs": the acronym with a plural "s", the same term as "API".
_ACRONYM_PLURAL = re.compile(r"[A-Z0-9]{2,}s")
# The grammar of a question, also when capitalised for emphasis ("NOT"). IT, US,
# WHO and CAN are left out on purpose: each is a subject someone researches.
_SHORT_FUNCTION_WORDS = frozenset({
    "an", "and", "are", "as", "at", "be", "but", "by", "did", "do", "for", "had", "has", "he", "her",
    "his", "how", "if", "in", "is", "its", "me", "my", "no", "not", "of", "on", "or", "our", "she",
    "so", "the", "to", "too", "up", "was", "we", "why", "yes", "yet", "you",
})
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


def _term(token: str, case_informative: bool) -> str:
    """The term a token stands for, or "" when it is not one.

    Capitals say nothing in text that has no lower case at all, so there a short
    word counts only by carrying a digit.
    """
    if _ACRONYM_PLURAL.fullmatch(token):
        token = token[:-1]
    lowered = token.lower()
    if len(token) >= _TERM_MIN_LENGTH:
        return "" if lowered in _TERM_STOPWORDS else _stem(token)
    if len(token) < _ACRONYM_MIN_LENGTH or lowered in _SHORT_FUNCTION_WORDS:
        return ""
    if not any(ch.isalpha() for ch in token):
        return ""  # a bare number: "3" in "Python 3" names nothing on its own
    if any(ch.isdigit() for ch in token) or (case_informative and token.isupper()):
        return lowered
    return ""


def _terms_in(text: str, case_informative: bool | None = None) -> list[str]:
    """The terms a text contains, in order.

    Whether capitals carry information is a property of the whole text, so a
    caller reading a slice of one passes the answer for the whole.
    """
    if case_informative is None:
        case_informative = any(ch.islower() for ch in text)
    return [term for term in (_term(token, case_informative) for token in _TOKEN.findall(text)) if term]


def objective_terms(text: str, limit: int = 24) -> tuple[str, ...]:
    """Substantive terms from the objective, for judging whether it was answered."""
    seen: list[str] = []
    for term in _terms_in(str(text or "")):
        if term not in seen:
            seen.append(term)
        if len(seen) >= limit:
            break
    return tuple(seen)


# --- citation conditions -----------------------------------------------------

def _relationship(context: Mapping[str, Any]) -> str:
    """This citation's standing for the claim under evaluation."""
    return str((context or {}).get("relationship") or CLAIM_SOURCE_THIRD_PARTY)


def _source_authority_assessed(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                               context: Mapping[str, Any]) -> bool:
    """Nothing assessed this source as carrying no authority.

    An unclassified host passes: not having classified it is a gap in our
    metadata, not a finding about the source.
    """
    return source_authority_state(citation, _relationship(context)) != AUTHORITY_KNOWN_NON_AUTHORITATIVE


def _source_authority_known(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                            context: Mapping[str, Any]) -> bool:
    """The source was positively classified. Stricter than the baseline asks."""
    return source_authority_state(citation, _relationship(context)) == AUTHORITY_KNOWN_AUTHORITATIVE


def _source_not_promotional(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                            context: Mapping[str, Any]) -> bool:
    """The source is not making a case for itself on this claim."""
    if _citation_role(citation) in ALWAYS_NON_AUTHORITATIVE_ROLES:
        return False
    return _relationship(context) != CLAIM_SOURCE_FIRST_PARTY_PROMOTIONAL


def _claim_source_fit(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                      context: Mapping[str, Any]) -> bool:
    relevance = _number(citation.get("relevance_score"))
    return relevance is not None and relevance >= MINIMUM_CLAIM_SOURCE_FIT


def _currency_signal_present(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                             context: Mapping[str, Any]) -> bool:
    """Something establishes when or for what this source applies."""
    dated = bool(citation.get("freshness_known")) or str(citation.get("freshness") or "unknown") != "unknown"
    return dated or version_signal_present(citation) or authoritative_living_documentation(citation)


def _freshness_current(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                       context: Mapping[str, Any]) -> bool:
    """Recent enough for a claim that depends on when it was true.

    Maintained first-party documentation qualifies without a timestamp: its
    currency comes from the publisher keeping it correct, which is a stronger
    guarantee than a date on an article that will never be revised.
    """
    if bool(citation.get("fresh_enough")) or str(citation.get("freshness") or "") == "fresh":
        return True
    return authoritative_living_documentation(citation)


def _stance_supports(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                     context: Mapping[str, Any]) -> bool:
    return str((assessment or {}).get("model_assessment") or "") == "supports"


def _evidence_type_admissible(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                              context: Mapping[str, Any]) -> bool:
    return str((assessment or {}).get("model_evidence_kind") or "") in SUPPORTING_EVIDENCE_KINDS


def _evidence_producer_independent(citation: Mapping[str, Any], assessment: Mapping[str, Any] | None,
                                   context: Mapping[str, Any]) -> bool:
    """The evidence was not produced by a vendor making the case for its own offering.

    Publisher identity is not evidence independence. A vendor's explainer on the
    problem its product solves is third-party to an objective that never names
    the vendor, yet it is the organisation producing - and benefiting from - the
    customer evidence it reports. Without a disclosed method it cannot count as
    independent customer evidence. It stays an observed source that synthesis
    may read for context; it just does not count.

    A vendor stating its own prices or limits is the record of that fact, so the
    first-party operational relationship stays exactly as valid as before.
    """
    if str(citation.get("evidence_producer_signal") or "") != SELF_PROMOTING_PUBLISHER:
        return True  # no signal, or not judged; see producer_signal_judged_count
    return _relationship(context) == CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL


CITATION_CONDITIONS: dict[
    str, Callable[[Mapping[str, Any], Mapping[str, Any] | None, Mapping[str, Any]], bool]
] = {
    "source_authority_assessed": _source_authority_assessed,
    "source_authority_known": _source_authority_known,
    "source_not_promotional": _source_not_promotional,
    "claim_source_fit": _claim_source_fit,
    "currency_signal_present": _currency_signal_present,
    "freshness_current": _freshness_current,
    "stance_supports": _stance_supports,
    "evidence_type_admissible": _evidence_type_admissible,
    "evidence_producer_independent": _evidence_producer_independent,
    "grounded_support": lambda citation, assessment, context: _grounded_support(citation, context),
}


# Conditions that read the synthesis model's own assessment of a source. They
# cannot be evaluated before synthesis runs, so selection leaves them to the
# post-synthesis verdict, exactly as before.
ASSESSMENT_DEPENDENT_CONDITIONS = frozenset({"stance_supports", "evidence_type_admissible", "grounded_support"})

# Conditions selection could evaluate but leaves to the verdict: a source failing
# one is still worth reading as context, it just cannot count as support.
CONTEXT_PRESERVING_CONDITIONS = frozenset({"evidence_producer_independent"})


def _grounded_support(citation: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    """An observed passage from this source was judged to support exactly this claim.

    A citation could count as supporting evidence merely by being authoritative,
    current and relevant-looking. In the seven-domain corpus a history finding
    cited a source the model had itself assessed as "unclear" - as it had all
    eight of its sources - and nothing in the general policy noticed, because the
    stance check existed only for demand.

    When no assessment step ran at all there is nothing to judge against, and the
    receipt says so. When it ran and grounded nothing, that is a result: no source
    supports the claim.
    """
    supporting = context.get("grounded_supporting_ids")
    if supporting is None:
        return True  # not judged; see grounded_support_judged
    return str(citation.get("citation_id") or "") in supporting


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
        strongest_tier(admissible, list(context.get("admissible_relationships") or [])),
        tuple(context.get("claim_risk_flags") or ()),
        str(context.get("policy_code") or ""),
        bool(context.get("first_party_operational")),
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
    case_informative = any(ch.islower() for ch in text)
    for match in _NON_ANSWER.finditer(text):
        window = text[max(0, match.start() - OBJECTIVE_TERM_LOOKBEHIND): match.end() + OBJECTIVE_TERM_PROXIMITY]
        if set(_terms_in(window, case_informative)) & set(terms):
            return False
    return True


# --- answer quality: measurement only ------------------------------------------
#
# answers_objective catches a finding that admits it could not answer. It cannot
# see one that answers something easier than what was asked: "how do mRNA vaccines
# produce an immune response" answered with "mRNA vaccines induce immune
# responses" is on topic, supported, and restates the question. None of fifteen
# stored how-question findings was a complete mechanism.
#
# Whether a finding explains a mechanism is semantic. A deterministic answer-form
# check failed exactly those cases in a 55-case benchmark - it could not tell an
# agent-only answer from a restatement, and lost every acronym subject - so a
# separate model judge supplies the answer level. This module stays
# deterministic: it derives which relation the objective asked for, and maps the
# judge's fixed code onto three measured fields. None of them feeds a condition
# or would_admit.

REQUESTED_RELATIONS = ("mechanism", "explanation", "causes", "comparison", "amount", "state",
                       "configuration", "descriptive")
# Relations whose full answer needs more than naming what was asked for: the
# intermediate steps of a mechanism, or how causes produced an outcome. "What were
# the causes of X" is answered by the causes; "why did X happen" is not.
DEPTH_REQUESTING_RELATIONS = frozenset({"mechanism", "explanation"})
ANSWER_QUALITY_LEVELS = ("off_topic", "topic_only", "partial", "complete")

# First match wins, so the more specific relations come first: "why" before any
# causal word, "how to" and configuration before a bare "how", a fee before "how".
_REQUESTED_RELATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("comparison", re.compile(r"\b(?:differences?|differ|differs|compare|compared|comparison|versus|vs)\b"
                              r"|\bbetween\b.+\band\b", re.IGNORECASE)),
    ("explanation", re.compile(r"\bwhy\b", re.IGNORECASE)),
    ("causes", re.compile(r"\b(?:causes?|caused|reasons?|factors?|origins?)\b|\bled to\b|\bresponsible for\b",
                          re.IGNORECASE)),
    ("configuration", re.compile(r"\bhow to\b|\b(?:configure|configured|configuring|configuration|settings?"
                                 r"|set ?up|install|installation|tuning|tune)\b", re.IGNORECASE)),
    ("amount", re.compile(r"\bhow (?:much|many)\b|\b(?:costs?|price|prices|pricing|fees?|rates?|amount)\b",
                          re.IGNORECASE)),
    ("mechanism", re.compile(r"\bhow\b|\b(?:mechanisms?|works?|working)\b", re.IGNORECASE)),
    ("state", re.compile(r"\b(?:current state|state of|status|latest|currently)\b", re.IGNORECASE)),
)


def requested_relation(objective: str) -> str:
    """Which relation the objective asks a finding to supply, as a fixed code."""
    text = re.sub(r"^\s*research\s+", "", str(objective or ""), flags=re.IGNORECASE)
    if not text.strip():
        return ""
    for code, pattern in _REQUESTED_RELATION_PATTERNS:
        if pattern.search(text):
            return code
    return "descriptive"


def answer_quality_codes(level: str | None, relation: str) -> dict[str, Any]:
    """Map a judged answer level onto the three measured answer-quality fields.

    Unjudged stays visibly unjudged - empty codes and answer_quality_judged False -
    never a quiet pass or a quiet fail.
    """
    level = str(level or "").strip().lower()
    if level not in ANSWER_QUALITY_LEVELS or relation not in REQUESTED_RELATIONS:
        return {"answer_quality_judged": False, "answer_quality_level": "", "answers_topic": "",
                "answers_requested_relation": "", "answers_requested_depth": ""}
    depth_requested = relation in DEPTH_REQUESTING_RELATIONS
    if level in ("off_topic", "topic_only"):
        answers_relation = "not_satisfied"
    elif level == "complete" or depth_requested:
        # For a mechanism or an explanation, "partial" names the agent or the causes:
        # the relation is answered, the depth is not.
        answers_relation = "satisfied"
    else:
        answers_relation = "partial"
    if not depth_requested:
        depth = "not_requested"
    else:
        depth = "satisfied" if level == "complete" else "not_satisfied"
    return {"answer_quality_judged": True, "answer_quality_level": level,
            "answers_topic": "no" if level == "off_topic" else "yes",
            "answers_requested_relation": answers_relation, "answers_requested_depth": depth}


def _grounded_refutation(finding: Mapping[str, Any], admissible: list[Mapping[str, Any]], context: Mapping[str, Any]) -> bool:
    """No observed passage was judged to refute exactly this claim.

    A current-event finding was admitted on four grounded supporters while a fifth
    source was grounded as refuting the same exact claim - and nothing in the
    general policy looked, because grounded_support only asks whether the cited
    sources support the claim, and completion only adds supporters.

    Listed as a failure, this reads "failed on a grounded refutation". It blocks
    an uncontested verdict; it does not declare the claim false. Supported and
    refuted at once is a disputed finding, and the report surfaces it as an
    unresolved disagreement rather than hiding the contradicting source.
    """
    refuting = context.get("grounded_refuting_ids")
    if refuting is None:
        return True  # not judged; see grounded_support_judged
    return not refuting


FINDING_CONDITIONS: dict[str, Callable[[Mapping[str, Any], list[Mapping[str, Any]], Mapping[str, Any]], bool]] = {
    "citation_present": _citation_present,
    "uncertainty_declared_where_warranted": _uncertainty_declared_where_warranted,
    "answers_objective": _answers_objective,
    "corroboration_satisfied": _corroboration_satisfied,
    "independent_publishers": _independent_publishers,
    "grounded_refutation": _grounded_refutation,
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
    citation_conditions=("source_authority_assessed", "source_not_promotional", "claim_source_fit",
                         "grounded_support"),
    finding_conditions=(
        "citation_present", "answers_objective", "corroboration_satisfied",
        "uncertainty_declared_where_warranted", "grounded_refutation",
    ),
)

# Applied only where a claim depends on when or for what a source applies.
CURRENCY_LAYER: tuple[str, ...] = ("currency_signal_present",)

# Reference material is pinned to a version rather than a publication date.
REFERENCE_EVIDENCE_POLICY = BASELINE_EVIDENCE_POLICY.tightened("reference", citation=CURRENCY_LAYER)

CURRENT_EVIDENCE_POLICY = BASELINE_EVIDENCE_POLICY.tightened("current", citation=CURRENCY_LAYER + ("freshness_current",))

DEMAND_EVIDENCE_POLICY = BASELINE_EVIDENCE_POLICY.tightened(
    "demand",
    citation=CURRENCY_LAYER + ("freshness_current", "stance_supports", "evidence_type_admissible",
                               "evidence_producer_independent"),
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


def _finding_citation_ids(finding: Mapping[str, Any]) -> tuple[list[str], bool]:
    """The citations the finding itself rests on, and whether it declared any.

    The synthesis payload names them "citation_ids"; a report row names them
    "citations". Both are lists of citation id strings.
    """
    for key in ("citation_ids", "citations"):
        value = finding.get(key)
        if isinstance(value, list):
            ids = [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]
            return list(dict.fromkeys(ids)), True
    return [], False


def _verdict(
    policy: EvidencePolicy,
    finding: Mapping[str, Any],
    evaluated: list[tuple[Mapping[str, Any], str, list[str]]],
    base_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the finding conditions to one set of already-evaluated citations."""
    admissible = [citation for citation, _relationship, failed in evaluated if not failed]
    relationships = [relationship for _citation, relationship, failed in evaluated if not failed]
    failures: dict[str, int] = {}
    for _citation, _relationship, failed in evaluated:
        for name in failed:
            failures[name] = failures.get(name, 0) + 1
    tier = strongest_tier(admissible, relationships)
    first_party_operational = CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL in relationships
    context = {
        **base_context,
        "first_party_operational": first_party_operational,
        "admissible_relationships": relationships,
    }
    finding_failures = [
        name for name in policy.finding_conditions
        if name in FINDING_CONDITIONS and not FINDING_CONDITIONS[name](finding, admissible, context)
    ]
    return {
        "evaluated_citation_count": len(evaluated),
        "admissible_citation_count": len(admissible),
        "citation_condition_failures": dict(sorted(failures.items())),
        "finding_condition_failures": sorted(finding_failures),
        "supporting_authority_tier": tier,
        "independent_publisher_count": _publisher_count(admissible),
        "required_publisher_count": required_publisher_count(
            tier, tuple(base_context.get("claim_risk_flags") or ()), policy.policy_code, first_party_operational),
        "would_admit": not finding_failures and bool(admissible),
        "_admissible_ids": [str(citation.get("citation_id") or "") for citation in admissible],
    }


def evaluate_policy(
    policy: EvidencePolicy,
    *,
    finding: Mapping[str, Any] | None,
    citations: list[Mapping[str, Any]] | None,
    assessments_by_citation: Mapping[str, Mapping[str, Any]] | None = None,
    objective: str = "",
    currency_reason: str = "",
    freshness_window: str = "",
    assessments: list[Mapping[str, Any]] | None = None,
    answer_quality_level: str | None = None,
) -> dict[str, Any]:
    """Report which named conditions a finding and its own citations fail.

    The verdict is about the finding, so it is taken over the citations the
    finding names - not over everything the run observed. Judging the pool let a
    finding that cited one unclassified blog borrow admission from seven other
    publishers it never used, and let a finding citing an aggregator borrow the
    vendor's own price list. The pool is still measured, separately, as the
    admissible evidence that was available: the gap between the two is the signal
    that good evidence existed and synthesis did not use it.

    Returns counts and fixed condition codes only. Nothing here refuses anything;
    a caller decides what to do with the result.
    """
    row = dict(finding or {})
    rows = [dict(item) for item in (citations or []) if isinstance(item, Mapping)]
    assessments_by_id = dict(assessments_by_citation or {})

    try:
        from research_source_classification import classification_reason, document_form
    except ImportError:  # measurement must never break the run it observes
        classification_reason = document_form = None

    # Coverage diagnostics describe every observed source: they measure the
    # classifier, not the finding, and stay comparable with earlier receipts.
    authority_states: dict[str, int] = {}
    authority_tiers: dict[str, int] = {}
    url_classification_reasons: dict[str, int] = {}
    document_forms: dict[str, int] = {}
    version_signals = 0
    living_documentation = 0
    relationships: dict[str, int] = {}
    producer_signal_judged = self_promoting_publishers = 0
    # Decided before the loop: every condition that asks about authority needs the
    # objective's own terms to know whether a source is the first party for it.
    terms = objective_terms(objective)
    relation_requested = requested_relation(objective)
    risk_flags = claim_risk_flags(row)
    # Which citations the model grounded as supporting exactly this finding's
    # claim. None means no assessment step ran; an empty set means it ran and
    # grounded nothing, which is itself a result.
    grounded_ids: set[str] | None = None
    refuting_ids: set[str] | None = None
    claim_matched = claim_mismatched = 0
    exact_digest_matches = normalized_exact_matches = different_claim_matches = 0
    if isinstance(assessments, list):
        from research_claim_assessment import (
            digest_of_claim, digest_of_normalized_claim, grounded_refuting_citation_ids,
            grounded_supporting_citation_ids,
        )
        grounded_ids = set(grounded_supporting_citation_ids(assessments, row.get("summary")))
        refuting_ids = set(grounded_refuting_citation_ids(assessments, row.get("summary")))
        finding_digest = digest_of_claim(row.get("summary"))
        finding_normalized = digest_of_normalized_claim(row.get("summary"))
        for item in assessments:
            if isinstance(item, Mapping):
                if item.get("claim_digest") == finding_digest:
                    claim_matched += 1
                    exact_digest_matches += 1
                    continue
                claim_mismatched += 1
                # Measurement only: admission above still requires the exact digest.
                normalized = item.get("normalized_claim_digest")
                if normalized == finding_normalized:
                    normalized_exact_matches += 1
                elif normalized:
                    different_claim_matches += 1
    base_context = {
        "policy_code": policy.policy_code,
        "claim_risk_flags": risk_flags,
        "objective_terms": terms,
        "grounded_supporting_ids": grounded_ids,
        "grounded_refuting_ids": refuting_ids,
    }
    evaluated: list[tuple[Mapping[str, Any], str, list[str]]] = []
    for citation in rows:
        # Standing is per claim, not per publisher, so it is decided here and
        # carried into every condition that asks about authority.
        relationship = claim_source_relationship(citation, row, terms)
        relationships[relationship] = relationships.get(relationship, 0) + 1
        citation_context = {**base_context, "relationship": relationship}
        state = source_authority_state(citation, relationship)
        authority_states[state] = authority_states.get(state, 0) + 1
        tier = source_authority_tier(citation, relationship)
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
        if authoritative_living_documentation(citation):
            living_documentation += 1
        producer_signal = str(citation.get("evidence_producer_signal") or "")
        if producer_signal:
            producer_signal_judged += 1
            self_promoting_publishers += producer_signal == SELF_PROMOTING_PUBLISHER
        assessment = assessments_by_id.get(str(citation.get("citation_id") or ""))
        failed = [
            name for name in policy.citation_conditions
            if name in CITATION_CONDITIONS and not CITATION_CONDITIONS[name](citation, assessment, citation_context)
        ]
        evaluated.append((citation, relationship, failed))

    cited_ids, ids_declared = _finding_citation_ids(row)
    by_id = {str(citation.get("citation_id") or ""): (citation, relationship, failed)
             for citation, relationship, failed in evaluated}
    cited = [by_id[cid] for cid in cited_ids if cid in by_id]
    finding_verdict = _verdict(policy, row, cited, base_context)
    available = _verdict(policy, row, evaluated, base_context)
    cited_admissible = set(finding_verdict.pop("_admissible_ids"))
    uncited_admissible = [cid for cid in available.pop("_admissible_ids") if cid not in cited_admissible]

    return {
        "contract_version": CONTRACT_VERSION,
        "policy_code": policy.policy_code,
        # Why currency was required and how far back retrieval looked. Both are
        # fixed vocabularies, and without them a freshness rejection cannot be
        # read as "the source was old" or as "the window was wrong".
        "currency_reason": str(currency_reason or ""),
        "freshness_window": str(freshness_window or ""),
        # The verdict: this finding, judged on the citations it names.
        **finding_verdict,
        "cited_citation_ids_supplied": ids_declared,
        # Named but never observed, so they could not be judged at all.
        "unobserved_cited_citation_count": len([cid for cid in cited_ids if cid not in by_id]),
        # What the run had in hand. Admissible here and not cited above is the
        # "good evidence existed, synthesis ignored it" case.
        "available_admissible_evidence": {
            "observed_citation_count": available["evaluated_citation_count"],
            "admissible_citation_count": available["admissible_citation_count"],
            "independent_publisher_count": available["independent_publisher_count"],
            "supporting_authority_tier": available["supporting_authority_tier"],
            "citation_condition_failures": available["citation_condition_failures"],
            "would_admit": available["would_admit"],
        },
        "uncited_admissible_citation_count": len(uncited_admissible),
        "admissible_evidence_not_cited": bool(available["would_admit"] and not finding_verdict["would_admit"]),
        "authority_states": dict(sorted(authority_states.items())),
        "authority_tiers": dict(sorted(authority_tiers.items())),
        "url_classification_reasons": dict(sorted(url_classification_reasons.items())),
        "document_forms": dict(sorted(document_forms.items())),
        "version_signal_count": version_signals,
        "living_documentation_count": living_documentation,
        "claim_risk_flags": list(risk_flags),
        "claim_source_relationships": dict(sorted(relationships.items())),
        # Whether the relevance check had an objective to judge against, so a
        # clean answers_objective cannot be mistaken for a check that ran.
        "objective_terms_supplied": bool(terms),
        # Whether grounded support could be judged, and the counts that separate a
        # model that paraphrased the claim from one that found nothing supportive.
        "grounded_support_judged": grounded_ids is not None,
        "grounded_supporting_citation_count": len(grounded_ids or ()),
        "grounded_refuting_citation_count": len(refuting_ids or ()),
        "claim_matched_assessment_count": claim_matched,
        "claim_mismatched_assessment_count": claim_mismatched,
        # Of the assessments made for other wording: which matched once case,
        # whitespace and trailing punctuation are ignored, and which stated a
        # different proposition. Admission is not changed by either.
        "exact_digest_matches": exact_digest_matches,
        "normalized_exact_matches": normalized_exact_matches,
        "different_claim_matches": different_claim_matches,
        # How many observed sources carried a producer signal at all, so a clean
        # evidence_producer_independent cannot be mistaken for a check that ran;
        # and how many were a vendor presenting its own offering without a method.
        "producer_signal_judged_count": producer_signal_judged,
        "self_promoting_publisher_count": self_promoting_publishers,
        # Which relation the objective asked for, and what the separate answer judge
        # said the finding supplied. Measurement only: no condition above reads them.
        "requested_relation": relation_requested,
        **answer_quality_codes(answer_quality_level, relation_requested),
        "enforced": False,
    }


# The keys of an evaluate_policy result that describe the run rather than one
# finding: the policy, how the observed pool was classified, the objective's
# requested relation and the judged answer level. A multi-finding report states
# them once beside the per-finding verdicts. Every other key - including
# authority states and the available evidence, which depend on the finding's
# claim-source relationship - is judged on one finding and its own citations.
RUN_LEVEL_EVALUATION_KEYS = frozenset({
    "contract_version", "policy_code", "currency_reason", "freshness_window",
    "url_classification_reasons", "document_forms", "version_signal_count", "living_documentation_count",
    "objective_terms_supplied", "producer_signal_judged_count", "self_promoting_publisher_count",
    "requested_relation", "answer_quality_judged", "answer_quality_level", "answers_topic",
    "answers_requested_relation", "answers_requested_depth", "enforced",
})

SELECTION_ADMISSIBLE_ONLY = "admissible_only"
SELECTION_NO_ADMISSIBLE_EVIDENCE = "no_admissible_evidence"

_TIER_RANK = {tier: index for index, tier in enumerate(AUTHORITY_TIER_ORDER)}


def select_citable_evidence(
    policy: EvidencePolicy,
    *,
    citations: list[Mapping[str, Any]] | None,
    objective: str = "",
) -> dict[str, Any]:
    """Which observed sources synthesis may cite, decided by this policy.

    Synthesis used to receive every observed source in hash order with nothing
    to say which the policy would admit, so it cited a documentation mirror while
    the official docs sat in the same pool, a fee aggregator beside the vendor's
    own price list, and one blog beside five admissible publishers. Selection
    does not define a second notion of a good source: it runs this policy's own
    source conditions and offers synthesis the sources that pass.

    Before synthesis there is no finding, so the objective stands in as the
    provisional claim: it names the subject a first party is judged against and
    the kind of fact being sought. Conditions that read the model's assessment of
    a source cannot run yet and stay with the post-synthesis verdict.

    When nothing is admissible, every observed source is offered as before and the
    verdict refuses the finding afterwards. Selection never makes a source
    admissible; it only stops synthesis citing one that is not while an
    admissible one is in hand.
    """
    rows = [dict(item) for item in (citations or []) if isinstance(item, Mapping)]
    terms = objective_terms(objective)
    provisional = {"summary": str(objective or "")}
    base_context = {"policy_code": policy.policy_code, "claim_risk_flags": (), "objective_terms": terms}
    conditions = [name for name in policy.citation_conditions
                  if name in CITATION_CONDITIONS and name not in ASSESSMENT_DEPENDENT_CONDITIONS
                  and name not in CONTEXT_PRESERVING_CONDITIONS]
    admissible: list[tuple[int, float, str]] = []
    withheld: dict[str, int] = {}
    offered_tiers: dict[str, int] = {}
    for row in rows:
        cid = str(row.get("citation_id") or "")
        if not cid:
            continue
        relationship = claim_source_relationship(row, provisional, terms)
        context = {**base_context, "relationship": relationship}
        failed = [name for name in conditions if not CITATION_CONDITIONS[name](row, None, context)]
        if failed:
            for name in failed:
                withheld[name] = withheld.get(name, 0) + 1
            continue
        tier = source_authority_tier(row, relationship)
        relevance = _number(row.get("relevance_score")) or 0.0
        admissible.append((_TIER_RANK.get(tier, 0), relevance, cid))
        offered_tiers[tier] = offered_tiers.get(tier, 0) + 1
    # Strongest authority first, then the most relevant, so a source's share of a
    # fixed excerpt budget is not spent on weaker evidence ahead of it.
    admissible.sort(key=lambda item: (-item[0], -item[1], item[2]))
    all_ids = [str(row.get("citation_id") or "") for row in rows if str(row.get("citation_id") or "")]
    if admissible:
        mode, citable = SELECTION_ADMISSIBLE_ONLY, [cid for _rank, _relevance, cid in admissible]
    else:
        mode, citable = SELECTION_NO_ADMISSIBLE_EVIDENCE, all_ids
    return {
        "policy_code": policy.policy_code,
        "selection_mode": mode,
        "citable_ids": citable,
        "observed_citation_count": len(all_ids),
        "offered_citation_count": len(citable),
        "withheld_citation_count": len(all_ids) - len(citable),
        "withheld_condition_counts": dict(sorted(withheld.items())) if admissible else {},
        "offered_authority_tiers": dict(sorted(offered_tiers.items())),
        "assessment_conditions_deferred": sorted(ASSESSMENT_DEPENDENT_CONDITIONS & set(policy.citation_conditions)),
        "context_conditions_deferred": sorted(CONTEXT_PRESERVING_CONDITIONS & set(policy.citation_conditions)),
    }


__all__ = [
    "CONTRACT_VERSION",
    "AUTHORITY_KNOWN_AUTHORITATIVE", "AUTHORITY_KNOWN_NON_AUTHORITATIVE", "AUTHORITY_UNCLASSIFIED",
    "BASELINE_EVIDENCE_POLICY", "REFERENCE_EVIDENCE_POLICY", "CURRENT_EVIDENCE_POLICY", "DEMAND_EVIDENCE_POLICY",
    "CURRENCY_LAYER", "POLICIES", "EvidencePolicy",
    "CITATION_CONDITIONS", "FINDING_CONDITIONS",
    "evaluate_policy", "policy_for_objective", "POLICY_FOR_CURRENCY_REQUIREMENT",
    "source_authority_state", "version_signal_present", "authoritative_living_documentation",
    "ALWAYS_NON_AUTHORITATIVE_ROLES", "CLAIM_RELATIVE_EVIDENCE_ROLES",
    "CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL", "CLAIM_SOURCE_FIRST_PARTY_PROMOTIONAL",
    "CLAIM_SOURCE_FIRST_PARTY_OTHER", "CLAIM_SOURCE_THIRD_PARTY",
    "EVALUATED_NORMALLY_RELATIONSHIPS", "FIRST_PARTY_SETTLED_RISK_FLAGS",
    "claim_source_relationship", "first_party_source",
    "ASSESSMENT_DEPENDENT_CONDITIONS", "CONTEXT_PRESERVING_CONDITIONS", "DERIVED_DISQUALIFYING_ROLES",
    "SELF_PROMOTING_PUBLISHER",
    "REQUESTED_RELATIONS", "DEPTH_REQUESTING_RELATIONS", "ANSWER_QUALITY_LEVELS",
    "requested_relation", "answer_quality_codes",
    "SELECTION_ADMISSIBLE_ONLY", "SELECTION_NO_ADMISSIBLE_EVIDENCE", "select_citable_evidence",
    "RUN_LEVEL_EVALUATION_KEYS",
    "AUTHORITY_TIER_ORDER", "SELF_SUFFICIENT_TIERS", "HIGHER_RISK_POLICY_CODES",
    "TIER_NONE", "TIER_NON_AUTHORITATIVE", "TIER_UNCLASSIFIED",
    "TIER_COMMUNITY", "TIER_SPECIALIST", "TIER_PRIMARY",
    "source_authority_tier", "strongest_tier", "claim_risk_flags",
    "required_publisher_count", "objective_terms",
]
