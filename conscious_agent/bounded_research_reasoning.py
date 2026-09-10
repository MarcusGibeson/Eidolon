from __future__ import annotations

"""Content-minimized planning and evidence reasoning for bounded web research.

This module extends the retained Era 7 research contracts without performing
network I/O, provider calls, browser automation, source mutation, or release
operations. Raw objectives and transient privacy-safe query strings may exist in
memory while planning, but only digests and sanitized evidence metadata are
intended for durable/public research receipts.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

try:
    from research_web_intelligence_v2100 import capture_research_evidence
    from research_source_independence import canonicalize_public_url, cluster_evidence_lineages, independence_summary, source_evidence_role, source_identity
except ImportError:
    from research_web_intelligence_v2100 import capture_research_evidence
    from research_source_independence import (
        canonicalize_public_url,
        cluster_evidence_lineages,
        independence_summary,
        source_evidence_role,
        source_identity,
    )

CONTRACT_VERSION = "v2503.4"
MAX_SUBQUESTIONS = 8
MAX_QUERY_CHARS = 320
MAX_QUERY_TERMS = 24
MAX_REPORT_ITEMS = 32
RESEARCH_EVIDENCE_DIMENSIONS = (
    "demand",
    "competition",
    "implementation_dependencies",
    "free_tier_feasibility",
)

_DENIED = {
    "network_contacted": False,
    "provider_contacted": False,
    "write_method_used": False,
    "private_network_allowed": False,
    "credentials_allowed": False,
    "uploads_allowed": False,
    "source_modified": False,
    "memory_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "standing_research_authority_granted": False,
    "authority_expanded": False,
}

_SECRET = re.compile(
    r"(?:\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|bearer)\b\s*[:=]\s*\S+|\bsk-[A-Za-z0-9_-]{12,})",
    re.I,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"(?<!\w)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\w)")
_WIN_PATH = re.compile(r"\b[A-Za-z]:\\(?:[^\s]+\\)*[^\s]*")
_POSIX_PRIVATE_PATH = re.compile(r"(?<!\w)/(?:home|Users|mnt|private|var/lib|srv/private)/[^\s]+", re.I)
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.I)
_LONG_TOKEN = re.compile(r"\b[A-Za-z0-9_-]{32,}\b")
_URL = re.compile(r"https?://\S+", re.I)
_PERSON_RELATION = re.compile(
    r"\b(?:wife|husband|fianc(?:e|ee|Ã©|Ã©e)|girlfriend|boyfriend|partner|friend|coworker|co-worker|boss|manager|doctor|daughter|son|mother|father|mom|dad|client|customer)\s+([A-Z][a-z]{1,30}(?:\s+[A-Z][a-z]{1,30})*)\b"
)
_POSSESSIVE_NAME = re.compile(r"\b([A-Z][a-z]{1,30})['â€™]s\b")
_OBJECTIVE_SIDE_EFFECT = re.compile(
    r"(?:^|\b(?:and|then)\s+)(?:post|publish|upload|send|message|email|purchase|buy|order)\b|"
    r"\b(?:post|publish|upload|send|message|email|purchase|buy|order)\s+(?:it|this|that|for\s+me|on\s+my\s+behalf)\b|"
    r"\b(?:create\s+(?:an?\s+)?account|log\s*in|sign\s*in|authenticate)\b",
    re.I,
)
_OBJECTIVE_ACCESS_BYPASS = re.compile(
    r"\b(?:bypass|evade|circumvent)\b.{0,40}\b(?:paywall|access\s*control|login|authentication|robots|rate\s*limit)\b|\bprivate\s+network\b",
    re.I,
)
_OBJECTIVE_TOO_BROAD = re.compile(
    r"\b(?:everything\s+about|all\s+(?:available\s+)?information\s+about|entire\s+internet|every\s+source|exhaustive(?:ly)?\s+(?:research|search))\b",
    re.I,
)
_OBJECTIVE_AMBIGUOUS = re.compile(r"^(?:this|that|it|them|those|the thing|the topic|what we discussed)(?:\s+now)?$", re.I)

_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "because", "but", "by", "can", "could", "did", "do", "does",
    "for", "from", "had", "has", "have", "how", "i", "if", "in", "into", "is", "it", "its", "me", "my", "of",
    "on", "or", "our", "ours", "that", "the", "their", "them", "there", "these", "they", "this", "those", "to",
    "us", "was", "we", "were", "what", "when", "where", "which", "who", "why", "will", "with", "would", "you",
    "your", "mine", "remember", "memory", "personal", "private", "locally", "local",
    "wife", "husband", "fiance", "fiancee", "girlfriend", "boyfriend", "partner", "friend", "coworker",
    "boss", "manager", "doctor", "daughter", "son", "mother", "father", "mom", "dad", "client", "customer",
}


def _clean(value: object, limit: int = 8000) -> str:
    return " ".join(str(value or "").split()).strip()[:limit]


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _hex64(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _clamp(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = default
    if not math.isfinite(number):
        number = default
    return max(0.0, min(1.0, number))


def _sanitized_public_url(value: object) -> str:
    raw = canonicalize_public_url(value)
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except Exception:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return ""
    host = parsed.hostname.lower().rstrip(".")
    path = parsed.path or "/"
    return f"{parsed.scheme}://{host}{path}"


def _question_kind(text: str, freshness: str) -> str:
    lower = text.casefold()
    if re.search(r"\b(history|historical|historically|timeline|originally|previously|in the past|used to)\b", lower):
        return "historical"
    if re.search(r"\b(compare|comparison|versus|vs\.?|difference|different|better|worse|relative to)\b", lower):
        return "comparative"
    if re.search(r"\b(explore|possible|possibilities|opportunit|ideas|options|could|might|why|how might)\b", lower):
        return "exploratory"
    if freshness in {"breaking", "current", "versioned"} or re.search(r"\b(latest|current|currently|today|now|recent|recently|this week|this month)\b", lower):
        return "current"
    return "factual"


def _split_objective(text: str) -> list[str]:
    normalized = _clean(text)
    if not normalized:
        return []
    pieces = re.split(r"(?:\?|;|\n+|\b(?:and also|as well as)\b)", normalized, flags=re.I)
    pieces = [_clean(piece.strip(" .?!;"), 1600) for piece in pieces if _clean(piece.strip(" .?!;"), 1600)]
    if not pieces:
        pieces = [normalized]
    # A comparison belongs together; splitting around ordinary "and" often
    # destroys the proposition, so retain it as one bounded subquestion.
    unique: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        tokens = [t.casefold() for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9._+-]*", piece) if t.casefold() not in _STOP]
        semantic = " ".join(tokens[:48]) or piece.casefold()
        key = hashlib.sha256(semantic.encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        unique.append(piece)
        if len(unique) >= MAX_SUBQUESTIONS:
            break
    return unique


_COUNT_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
}


def _requested_result_count(text: str) -> int:
    match = re.search(
        r"\b(?:(\d{1,2})|(" + "|".join(_COUNT_WORDS) + r"))"
        r"(?:\s+[A-Za-z0-9][A-Za-z0-9-]*){0,5}\s+"
        r"(?:opportunit(?:y|ies)|options?|candidates?|alternatives?)\b",
        text,
        re.I,
    )
    if not match:
        return 0
    value = int(match.group(1)) if match.group(1) else _COUNT_WORDS.get(str(match.group(2)).casefold(), 0)
    return max(0, min(value, 8))


def _core_research_subject(text: str) -> str:
    sentences = [piece.strip() for piece in re.split(r"(?<=[.!?])\s+", _clean(text)) if piece.strip()]
    retained: list[str] = []
    for sentence in sentences:
        lower = sentence.casefold()
        if lower.startswith(("use only ", "cite every ", "do not ", "return a cited ")):
            continue
        if lower.startswith(("compare the supporting evidence", "identify uncertainties", "explain which ")):
            continue
        retained.append(sentence.strip(" .?!"))
    return _clean(" ".join(retained) or text, 1400)


def _comparative_discovery_blueprint(text: str) -> tuple[list[dict[str, str]], int]:
    """Expand one multi-option objective into evidence roles, not prose clauses."""
    requested_count = _requested_result_count(text)
    lower = text.casefold()
    comparative = bool(re.search(r"\b(?:compare|most promising|best|which)\b", lower))
    discovery = bool(re.search(r"\b(?:opportunit(?:y|ies)|options?|candidates?|alternatives?|approaches?)\b", lower))
    if not (requested_count and comparative and discovery):
        return [], 0
    subject = _core_research_subject(text)
    return [
        {
            "question": f"Identify distinct candidates supported by public evidence for: {subject}",
            "question_kind": "exploratory",
            "planning_role": "exploratory_unknown",
            "query_focus": f"{subject} documented user pain unmet demand complaints",
            "report_label": "Candidate discovery and concrete problem evidence",
        },
        {
            "question": f"Assess demand and problem severity for the strongest candidates in: {subject}",
            "question_kind": "current",
            "planning_role": "required_fact",
            "query_focus": f"{subject} user demand workflow pain survey requests adoption",
            "report_label": "Demand and problem-severity evidence",
        },
        {
            "question": f"Assess feasibility, cost constraints, competition, and material risks for: {subject}",
            "question_kind": "comparative",
            "planning_role": "comparative_criterion",
            "query_focus": f"{subject} feasibility free tier open source API competition pricing",
            "report_label": "Feasibility, competition, and risk evidence",
        },
        {
            "question": f"Compare the candidates and identify the best-supported recommendation for: {subject}",
            "question_kind": "comparative",
            "planning_role": "comparative_criterion",
            "query_focus": f"{subject} case study willingness to pay validation churn revenue",
            "report_label": "Comparative recommendation and remaining uncertainty",
        },
    ], requested_count


# How long each dimension's evidence stays valid. Whether a customer problem
# exists is a durable market condition, so a 30-day window rejects every honest
# survey and study on merit; published pricing and free-tier limits are not
# durable and must stay current.
_DIMENSION_FRESHNESS = {
    "demand": "slow_changing",
    "competition": "versioned",
    "free_tier_feasibility": "current",
}


EVIDENCE_CURRENCY_REQUIREMENTS = ("reference", "current", "demand_current")

# Wording that makes a claim depend on how recent its evidence is. Naming a
# version does not: "asyncio behaviour in 3.14" is a reference question, and the
# version is the compatibility answer a reader wants.
_CURRENCY_WORDING = re.compile(
    r"\b(?:current(?:ly)?|recent(?:ly)?|latest|newest|nowadays|today|this\s+(?:year|month|week)|"
    r"as\s+of|up[\s-]to[\s-]date|state\s+of|status\s+of|trend(?:s|ing)?|"
    r"deprecat\w*|release\s+notes|what'?s\s+new|new\s+in|changed?\s+(?:in|since)|since\s+20\d{2})\b",
    re.IGNORECASE,
)

# A dimension's currency need is inherent to the objective class, not to a window.
_DIMENSION_CURRENCY = {
    "demand": "demand_current",
    "competition": "current",
    "free_tier_feasibility": "current",
}

# How far back to look, once currency is known. Cause, then effect.
_DEFAULT_WINDOW_FOR_CURRENCY = {
    "reference": "slow_changing",
    "current": "current",
    "demand_current": "slow_changing",
}


def _evidence_currency_requirement(text: str, blueprint: list[dict[str, str]] | None) -> str:
    """Decide what currency the objective's meaning requires.

    Reference material answers a question about how something works, and stays
    correct until the thing changes. A demand claim is about the present state of
    a market. Only the objective can say which is being asked.
    """
    for row in blueprint or []:
        dimension = str(row.get("evidence_dimension") or "").strip().lower()
        if dimension in _DIMENSION_CURRENCY:
            return _DIMENSION_CURRENCY[dimension]
    if blueprint:
        return "current"
    return "current" if _CURRENCY_WORDING.search(str(text or "")) else "reference"


def _single_candidate_dimension_blueprint(text: str) -> tuple[list[dict[str, str]], int]:
    """Keep narrow follow-up objectives tied to their domain instead of a bare keyword."""
    normalized = _clean(text, 1400)
    match = re.match(r"^(?:research\s+)?(.+?)\s+(demand|competition|competitors?|free[- ]tier(?: feasibility)?|feasibility)\.?$", normalized, re.I)
    if not match:
        return [], 0
    candidate = _clean(match.group(1), 240)
    dimension = match.group(2).casefold().replace(" ", "-")
    if dimension in {"competitor", "competitors"}:
        dimension = "competition"
    if dimension in {"free-tier", "free-tier-feasibility", "feasibility"}:
        dimension = "free_tier_feasibility"
    domain_terms = "saas software tool product customer problem evidence"
    focus_by_dimension = {
        "demand": "demand customer problem evidence survey respondents workflow complaints",
        "competition": f"{domain_terms} alternatives competitors official product pricing comparison",
        "free_tier_feasibility": f"{domain_terms} official pricing API documentation free plan limits commercial use hosting",
    }
    focus = f"{candidate} {focus_by_dimension[dimension]}"
    return [{
        "question": f"Assess {dimension.replace('_', ' ')} evidence for {candidate}",
        "question_kind": "current",
        "planning_role": "required_fact",
        "query_focus": focus,
        "report_label": f"{candidate} {dimension.replace('_', ' ')}",
        "evidence_dimension": dimension,
        "freshness_policy": _DIMENSION_FRESHNESS[dimension],
    }], 0


def decompose_research_objective(
    objective: str,
    *,
    freshness: str = "current",
    budget: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Turn one private objective into bounded, answerable internal questions.

    The decomposition remains provider-neutral and performs no network I/O. It
    classifies planning roles and rejects objectives whose requested authority
    or breadth cannot fit the configured read-only research contract.
    """
    text = _clean(objective)
    if not text:
        return {"ok": False, "status": "research_objective_required", "objective_assessment": "missing", **_DENIED}
    if _OBJECTIVE_ACCESS_BYPASS.search(text):
        return {"ok": False, "status": "research_objective_unsafe_access_expansion", "objective_assessment": "unsafe", **_DENIED}
    if _OBJECTIVE_SIDE_EFFECT.search(text):
        return {"ok": False, "status": "research_objective_requests_external_side_effect", "objective_assessment": "side_effecting", **_DENIED}
    if _OBJECTIVE_TOO_BROAD.search(text):
        return {"ok": False, "status": "research_objective_too_broad", "objective_assessment": "too_broad", **_DENIED}
    if _OBJECTIVE_AMBIGUOUS.fullmatch(text):
        return {"ok": False, "status": "research_objective_ambiguous", "objective_assessment": "ambiguous", **_DENIED}

    blueprint, requested_result_count = _single_candidate_dimension_blueprint(text)
    objective_shape = "single_candidate_dimension" if blueprint else ""
    if not blueprint:
        blueprint, requested_result_count = _comparative_discovery_blueprint(text)
        objective_shape = "comparative_discovery" if blueprint else "general_research"
    # What kind of currency the objective means to require, decided from the
    # objective itself. This must come first: deriving it from whatever freshness
    # window happened to be in force reversed cause and effect, and silently gave
    # a documentation lookup a thirty-day recency requirement nobody asked for.
    currency_requirement = _evidence_currency_requirement(text, blueprint)
    # An empty freshness means "let the objective's shape choose". A caller that
    # states a policy keeps it. The window is how far back to look; it never
    # decides whether currency is required at all.
    effective_freshness = (
        str(freshness or "").strip().lower()
        or _clean((blueprint[0] if blueprint else {}).get("freshness_policy"), 24)
        or _DEFAULT_WINDOW_FOR_CURRENCY.get(currency_requirement, "current")
    )
    chunks = [str(row["question"]) for row in blueprint] if blueprint else _split_objective(text)
    bounded = dict(budget or {})
    try:
        query_budget = max(1, min(MAX_SUBQUESTIONS, int(bounded.get("max_queries", MAX_SUBQUESTIONS))))
    except (TypeError, ValueError, OverflowError):
        query_budget = MAX_SUBQUESTIONS
    if len(chunks) > query_budget and query_budget <= 2:
        return {
            "ok": False,
            "status": "research_objective_impossible_within_query_budget",
            "objective_assessment": "budget_impossible",
            "required_subquestion_count": len(chunks),
            "available_query_budget": query_budget,
            **_DENIED,
        }

    rows: list[dict[str, Any]] = []
    required_facts: list[dict[str, Any]] = []
    comparative_criteria: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, 1):
        blueprint_row = blueprint[index - 1] if blueprint else {}
        kind = str(blueprint_row.get("question_kind") or _question_kind(chunk, effective_freshness))
        uncertainty = 0.65 if kind == "exploratory" else 0.55 if kind in {"current", "comparative"} else 0.45
        role = str(blueprint_row.get("planning_role") or ("comparative_criterion" if kind == "comparative" else "exploratory_unknown" if kind == "exploratory" else "required_fact"))
        row = {
            "subquestion_id": f"rq{index}",
            "question": chunk,
            "question_digest": hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
            "question_kind": kind,
            "planning_role": role,
            "uncertainty": uncertainty,
            # Follows the objective's meaning, never the window. A default window
            # must not be able to invent a currency requirement.
            "requires_current_evidence": currency_requirement != "reference",
            "assumption_codes": ["public_evidence_only", "literal_objective_interpretation"],
            "unknown_code": f"rq{index}_evidence_status_unknown",
            "query_focus": _clean(blueprint_row.get("query_focus") or chunk, 1600),
            "report_label": _clean(blueprint_row.get("report_label") or chunk, 240),
            "evidence_dimension": _clean(blueprint_row.get("evidence_dimension"), 60),
        }
        rows.append(row)
        if role == "required_fact":
            required_facts.append({"subquestion_id": row["subquestion_id"], "question_digest": row["question_digest"], "kind": kind})
        if role == "comparative_criterion":
            comparative_criteria.append({
                "subquestion_id": row["subquestion_id"],
                "criterion_codes": ["factual_basis", "source_quality", "source_independence", "freshness", "relevance"],
            })
        unknowns.append({"subquestion_id": row["subquestion_id"], "unknown_code": row["unknown_code"], "resolved": False})

    assumptions = [
        {"assumption_code": "public_evidence_only", "meaning": "Only public read-only evidence may be used."},
        {"assumption_code": "literal_objective_interpretation", "meaning": "No unrelated private context is inferred into the objective."},
    ]
    stopping_conditions = [
        {"condition": "query_budget_reached", "limit": int(bounded.get("max_queries", len(rows) or 1)) if bounded else len(rows)},
        {"condition": "page_budget_reached", "limit": int(bounded.get("max_observed_pages", 0)) if bounded else 0},
        {"condition": "time_budget_reached", "limit": int(bounded.get("max_elapsed_seconds", 0)) if bounded else 0},
        {"condition": "evidence_sufficient_or_material_gap_preserved", "limit": 1},
    ]
    public_rows = [{k: row[k] for k in ("subquestion_id", "question_digest", "question_kind", "planning_role", "uncertainty", "requires_current_evidence", "unknown_code")} for row in rows]
    public_plan = {
        "subquestions": public_rows,
        "required_facts": required_facts,
        "comparative_criteria": comparative_criteria,
        "assumptions": assumptions,
        "unknowns": unknowns,
        "stopping_conditions": stopping_conditions,
        "requested_result_count": requested_result_count,
        "objective_shape": objective_shape,
        "recommended_freshness_policy": effective_freshness,
        "evidence_currency_requirement": currency_requirement,
    }
    result = {
        "ok": True,
        "status": "research_objective_decomposed",
        "contract_version": CONTRACT_VERSION,
        "objective_assessment": "bounded_answerable",
        "subquestions": rows,
        "subquestion_count": len(rows),
        "requested_result_count": requested_result_count,
        "objective_shape": objective_shape,
        "recommended_freshness_policy": effective_freshness,
        "evidence_currency_requirement": currency_requirement,
        "public_subquestions": public_rows,
        "required_facts": required_facts,
        "comparative_criteria": comparative_criteria,
        "assumptions": assumptions,
        "unknowns": unknowns,
        "stopping_conditions": stopping_conditions,
        "uncertainty_preserved": True,
        "non_repetitive": len({row["question_digest"] for row in rows}) == len(rows),
        "provider_neutral": True,
        "raw_objective_persisted_by_this_module": False,
        **_DENIED,
    }
    result["decomposition_digest"] = _digest(public_plan)
    return result


_SOURCE_KINDS = {
    "factual": ("primary_official", "primary_data", "reputable_secondary"),
    "comparative": ("primary_official", "primary_data", "specialist_secondary", "reputable_secondary"),
    "current": ("primary_official", "reputable_secondary", "specialist_secondary"),
    "historical": ("primary_official", "primary_data", "reputable_secondary", "specialist_secondary"),
    "exploratory": ("specialist_secondary", "reputable_secondary", "community_experience", "primary_official"),
}
_SOURCE_REASON = {
    "primary_official": "establish first-party or authoritative facts",
    "primary_data": "check underlying measurements or records",
    "reputable_secondary": "cross-check interpretation and independent reporting",
    "specialist_secondary": "add domain-specific analysis and context",
    "community_experience": "capture bounded experience signals without treating anecdotes as primary proof",
}


def build_source_strategy(decomposition: Mapping[str, Any]) -> dict[str, Any]:
    """Build a bounded source-category strategy without contacting the web."""
    rows: list[dict[str, Any]] = []
    for sub in list(decomposition.get("subquestions") or [])[:MAX_SUBQUESTIONS]:
        if not isinstance(sub, Mapping):
            continue
        sid = _clean(sub.get("subquestion_id"), 32)
        kind = _clean(sub.get("question_kind"), 32) or "factual"
        categories = list(_SOURCE_KINDS.get(kind, _SOURCE_KINDS["factual"]))
        rows.append({
            "subquestion_id": sid,
            "question_kind": kind,
            "source_categories": [
                {"source_kind": source_kind, "reason": _SOURCE_REASON[source_kind], "priority": index + 1}
                for index, source_kind in enumerate(categories)
            ],
            "avoid_redundant_hosts": True,
            "independent_confirmation_preferred": True,
            "minimum_independent_sources": 2,
            "max_same_host_observations": 1,
            "freshness_required": bool(sub.get("requires_current_evidence")),
            "quality_floor": 0.55,
            "primary_source_preferred_when_applicable": "primary_official" in categories or "primary_data" in categories,
        })
    result = {
        "ok": bool(rows),
        "status": "research_source_strategy_ready" if rows else "research_source_strategy_requires_decomposition",
        "contract_version": CONTRACT_VERSION,
        "strategies": rows,
        "strategy_count": len(rows),
        "raw_query_text_included": False,
        "raw_objective_included": False,
        **_DENIED,
    }
    result["source_strategy_digest"] = _digest(rows)
    return result


def select_diverse_sources(candidates: Iterable[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    """Prefer quality while round-robining source kinds and de-duplicating hosts/URLs."""
    bounded = max(0, min(int(limit), 64))
    cleaned: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for raw in list(candidates)[:128]:
        row = dict(raw or {})
        public_url = _clean(row.get("public_url"), 2048)
        if not public_url or public_url in seen_urls:
            continue
        seen_urls.add(public_url)
        cleaned.append(row)
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(cleaned, key=lambda item: (-_clamp(item.get("quality_score")), _clean(item.get("host"), 255), _clean(item.get("public_url"), 2048))):
        group = _clean(row.get("subquestion_id"), 32) or "rq1"
        by_kind.setdefault(group, []).append(row)
    order = sorted(by_kind)
    result: list[dict[str, Any]] = []
    used_hosts: set[str] = set()
    while len(result) < bounded and any(by_kind.get(kind) for kind in order):
        progressed = False
        for group in order:
            bucket = by_kind.get(group) or []
            if not bucket:
                continue
            index = next((i for i, row in enumerate(bucket) if _clean(row.get("host"), 255) not in used_hosts), 0)
            row = bucket.pop(index)
            result.append(row)
            host = _clean(row.get("host"), 255)
            if host:
                used_hosts.add(host)
            progressed = True
            if len(result) >= bounded:
                break
        if not progressed:
            break
    return result


def sanitize_public_query(text: str) -> str:
    """Conservatively remove common private-context and secret shapes."""
    value = _clean(text, 4000)
    value = _SECRET.sub(" ", value)
    value = _EMAIL.sub(" ", value)
    value = _PHONE.sub(" ", value)
    value = _WIN_PATH.sub(" ", value)
    value = _POSIX_PRIVATE_PATH.sub(" ", value)
    value = _UUID.sub(" ", value)
    value = _URL.sub(" ", value)
    value = _PERSON_RELATION.sub(lambda m: m.group(0).replace(m.group(1), " "), value)
    value = _POSSESSIVE_NAME.sub(" ", value)
    value = _LONG_TOKEN.sub(" ", value)
    # Capitalization is not a privacy classification: stripping it destroys
    # operator-selected public subjects. Personal context and identifiers are
    # redacted above, before normalization and explicit query authorization.
    # Bare names are not classified by capitalization; public-query confirmation
    # remains mandatory. This heuristic is not a complete personal-data detector.
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9._+-]{1,48}", value):
        lower = token.casefold().strip("._+-")
        if not lower or lower in _STOP or lower in seen:
            continue
        if "=" in token or _SECRET.search(token):
            continue
        seen.add(lower)
        terms.append(lower)
        if len(terms) >= MAX_QUERY_TERMS:
            break
    return " ".join(terms)[:MAX_QUERY_CHARS].strip()


def plan_public_search_queries(
    objective: str,
    decomposition: Mapping[str, Any],
    source_strategy: Mapping[str, Any],
    *,
    max_queries: int,
) -> dict[str, Any]:
    """Create transient, privacy-safe GET-search strings bound to subquestions."""
    maximum = max(1, min(int(max_queries), 8))
    strategy_by_id = {str(row.get("subquestion_id") or ""): row for row in source_strategy.get("strategies", []) if isinstance(row, Mapping)}
    queries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sub in list(decomposition.get("subquestions") or [])[:MAX_SUBQUESTIONS]:
        if not isinstance(sub, Mapping):
            continue
        sid = _clean(sub.get("subquestion_id"), 32)
        safe = sanitize_public_query(str(sub.get("query_focus") or sub.get("question") or ""))
        if not safe:
            safe = sanitize_public_query(objective)
        if not safe or safe in seen:
            continue
        seen.add(safe)
        strategy = strategy_by_id.get(sid, {})
        categories = list(strategy.get("source_categories") or [])
        source_kind = _clean((categories[0] if categories else {}).get("source_kind"), 60) if categories else "unknown"
        tokens = [token for token in safe.split() if token]
        queries.append({
            "subquestion_id": sid,
            "query": safe,
            "query_digest": hashlib.sha256(safe.encode("utf-8")).hexdigest(),
            "query_term_digests": [hashlib.sha256(token.encode("utf-8")).hexdigest() for token in tokens],
            "preferred_source_kind": source_kind or "unknown",
            "private_context_removed": True,
        })
        if len(queries) >= maximum:
            break
    # Reserve a distinct customer-discussion route for a narrow demand question.
    # A search target never establishes source type, truth, or independence.
    if decomposition.get("objective_shape") == "single_candidate_dimension" and len(queries) < maximum:
        sub = next((row for row in decomposition.get("subquestions", [])
                    if isinstance(row, Mapping) and row.get("evidence_dimension") == "demand"), None)
        if sub:
            base = sanitize_public_query(str(sub.get("report_label") or sub.get("question") or ""))
            discussion = sanitize_public_query(f"{base} customer problem complaints personal experience discussion")
            if discussion:
                tokens = discussion.split()[:MAX_QUERY_TERMS - 1]
                while tokens and len(" ".join(tokens) + " site:reddit.com") > MAX_QUERY_CHARS:
                    tokens.pop()
                discussion = " ".join(tokens) + " site:reddit.com"
                if discussion not in seen:
                    queries.append({
                        "subquestion_id": _clean(sub.get("subquestion_id"), 32),
                        "query": discussion,
                        "query_digest": hashlib.sha256(discussion.encode("utf-8")).hexdigest(),
                        "query_term_digests": [hashlib.sha256(token.encode("utf-8")).hexdigest() for token in discussion.split()],
                        "preferred_source_kind": "community_experience",
                        "private_context_removed": True,
                    })
    summary = [{k: row[k] for k in ("subquestion_id", "query_digest", "preferred_source_kind", "private_context_removed")} for row in queries]
    result = {
        "ok": bool(queries),
        "status": "privacy_safe_search_queries_ready" if queries else "privacy_safe_search_query_unavailable",
        "contract_version": CONTRACT_VERSION,
        "queries": queries,
        "query_count": len(queries),
        "public_summary": summary,
        "raw_objective_exposed": False,
        "private_names_retained_by_policy": False,
        "credentials_retained": False,
        "local_paths_retained": False,
        **_DENIED,
    }
    result["query_plan_digest"] = _digest(summary)
    return result


def _demand_discovery_subject(sub: Mapping[str, Any]) -> str:
    label = re.sub(r"\s+demand\s*$", "", str(sub.get("report_label") or ""), flags=re.I)
    parts = re.split(r"\s+for\s+", label, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return sanitize_public_query(label or str(sub.get("question") or ""))
    product, audience = (sanitize_public_query(part) for part in parts)
    specific = [word for word in product.split() if word not in {"tracking", "management", "software", "tool", "tools"}]
    if len(specific) >= 2:
        product = " ".join(specific)
    return sanitize_public_query(f"{audience} {product}")


def plan_adaptive_follow_up(
    decomposition: Mapping[str, Any],
    source_strategy: Mapping[str, Any],
    comparison: Mapping[str, Any],
    *,
    remaining_query_budget: int,
    remaining_page_budget: int,
    remaining_failure_budget: int,
    existing_query_digests: Iterable[str] = (),
    max_followups: int = 1,
) -> dict[str, Any]:
    """Plan privacy-safe follow-up only for material gaps or contradictions.

    This is a deterministic planner. It performs no web/provider work and cannot
    broaden authority. Raw follow-up text is transient; the public summary is
    digest-only.
    """
    q_budget = max(0, int(remaining_query_budget or 0))
    p_budget = max(0, int(remaining_page_budget or 0))
    f_budget = max(0, int(remaining_failure_budget or 0))
    maximum = max(0, min(int(max_followups or 0), q_budget, p_budget, 2))
    if maximum <= 0 or f_budget <= 0:
        return {
            "ok": True, "status": "adaptive_follow_up_not_permitted_by_remaining_budget",
            "queries": [], "query_count": 0, "public_summary": [],
            "network_contacted": False, "authority_expanded": False, **_DENIED,
        }
    subs = {str(row.get("subquestion_id") or ""): dict(row) for row in decomposition.get("subquestions", []) if isinstance(row, Mapping)}
    strategies = {str(row.get("subquestion_id") or ""): dict(row) for row in source_strategy.get("strategies", []) if isinstance(row, Mapping)}
    existing = {str(v).casefold() for v in existing_query_digests if str(v)}
    material: list[dict[str, Any]] = []
    for claim in list(comparison.get("claims") or []):
        if not isinstance(claim, Mapping):
            continue
        code = _clean(claim.get("claim_code"), 120)
        state = _clean(claim.get("state"), 40)
        stale_only = bool(claim.get("stale_citations")) and not (claim.get("supporting_citations") or claim.get("refuting_citations"))
        if state in {"conflicted", "insufficient_current_evidence", "incomplete", "stale_only"} or stale_only:
            material.append(dict(claim))
    rows: list[dict[str, Any]] = []
    for claim in material:
        if len(rows) >= maximum:
            break
        sid = _clean(claim.get("claim_code"), 120)
        sub = subs.get(sid)
        if not sub:
            continue
        base = sanitize_public_query(str(sub.get("question") or ""))
        if not base:
            continue
        state = _clean(claim.get("state"), 40)
        qualifier = "independent authoritative current evidence" if state == "conflicted" else "authoritative current evidence independent source"
        if sub.get("evidence_dimension") == "demand":
            base = _demand_discovery_subject(sub)
            qualifier = "survey"
        query = sanitize_public_query(f"{base} {qualifier}")
        if not query:
            continue
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        if digest in existing:
            continue
        existing.add(digest)
        strategy = strategies.get(sid, {})
        categories = list(strategy.get("source_categories") or [])
        preferred = "unknown"
        if categories:
            preferred = _clean((categories[1] if len(categories) > 1 else categories[0]).get("source_kind"), 60) or "unknown"
        reason = "material_contradiction" if state == "conflicted" else "insufficient_or_stale_evidence"
        rows.append({
            "subquestion_id": sid,
            "query": query,
            "query_digest": digest,
            "preferred_source_kind": preferred,
            "follow_up_reason": reason,
            "private_context_removed": True,
        })
        if sub.get("evidence_dimension") == "demand" and len(rows) < maximum:
            alternate = sanitize_public_query(f"{base} personal experience manual work problems forum discussion")
            alternate_digest = hashlib.sha256(alternate.encode("utf-8")).hexdigest()
            if alternate and alternate_digest not in existing:
                existing.add(alternate_digest)
                rows.append({**rows[-1], "query": alternate, "query_digest": alternate_digest,
                             "preferred_source_kind": "community_experience"})
    summary = [{k: row[k] for k in ("subquestion_id", "query_digest", "preferred_source_kind", "follow_up_reason", "private_context_removed")} for row in rows]
    result = {
        "ok": True,
        "status": "adaptive_follow_up_ready" if rows else "adaptive_follow_up_not_needed",
        "queries": rows,
        "query_count": len(rows),
        "public_summary": summary,
        "material_gap_or_contradiction_required": True,
        "access_controls_may_not_be_evaded": True,
        "authentication_may_not_be_automated": True,
        "page_instructions_do_not_expand_authority": True,
        "network_contacted": False,
        "raw_query_text_exposed": False,
        **_DENIED,
    }
    result["follow_up_plan_digest"] = _digest(summary)
    return result


def _dimension_evidence(
    raw: Mapping[str, Any],
    citation_index: Mapping[str, Mapping[str, Any]],
    *,
    candidate_digest: str,
    matrix_attempted: bool = False,
) -> dict[str, dict[str, Any]]:
    supplied = raw.get("evidence_dimensions") if isinstance(raw.get("evidence_dimensions"), Mapping) else {}
    result: dict[str, dict[str, Any]] = {}
    for dimension in RESEARCH_EVIDENCE_DIMENSIONS:
        source = supplied.get(dimension) if isinstance(supplied.get(dimension), Mapping) else {}
        ids = list(dict.fromkeys(
            _clean(value, 80)
            for value in list(source.get("citation_ids") or source.get("citations") or [])
            if _clean(value, 80) in citation_index
        ))[:6]
        summary = _clean(source.get("summary") or source.get("conclusion"), 360)
        all_candidate_specific_ids = [
            cid
            for cid in ids
            if _hex64(citation_index[cid].get("candidate_digest")) == candidate_digest
            and _clean(citation_index[cid].get("evidence_dimension"), 60) == dimension
        ]
        role_rows = [(cid, source_evidence_role(citation_index[cid])) for cid in all_candidate_specific_ids]
        candidate_specific_ids = [
            cid
            for cid, role in role_rows
            if role.get("valid_public_url") and dimension in set(role.get("supportable_dimensions") or [])
        ]
        role_mismatch_ids = [cid for cid, role in role_rows if cid not in candidate_specific_ids and role.get("valid_public_url")]
        candidate_rows = []
        role_counts: dict[str, int] = {}
        for cid in candidate_specific_ids:
            source = dict(citation_index[cid])
            role = source_evidence_role(source)
            role_name = _clean(role.get("evidence_role"), 60) or "unknown"
            role_counts[role_name] = role_counts.get(role_name, 0) + 1
            source["quality_score"] = min(_clamp(source.get("quality_score")), _clamp(role.get("quality_cap")))
            candidate_rows.append(source)
        independence = independence_summary(candidate_rows)
        qualities = [_clamp(row.get("quality_score")) for row in candidate_rows]
        freshness = [_clean(row.get("freshness"), 16) or "unknown" for row in candidate_rows]
        stances = [_clean(row.get("stance"), 20) or "unknown" for row in candidate_rows]
        maximum = max(qualities, default=0.0)
        independent_count = int(independence.get("independent_lineage_count") or 0)
        authoritative_count = int(independence.get("primary_or_authoritative_lineage_count") or 0)
        if maximum >= 0.75 and independent_count >= 2:
            strength = "strong"
        elif maximum >= 0.5 and independent_count >= 1:
            strength = "moderate"
        else:
            strength = "weak"
        supports = sum(1 for stance in stances if stance == "supports")
        refutes = sum(1 for stance in stances if stance == "refutes")
        unresolved = sum(1 for stance in stances if stance not in {"supports", "refutes"})
        if supports and refutes:
            matrix_state = "contradicted"
        elif candidate_specific_ids and independent_count and maximum >= 0.5:
            matrix_state = "supported"
        elif candidate_specific_ids:
            matrix_state = "weak"
        elif matrix_attempted:
            matrix_state = "researched_with_no_credible_evidence"
        else:
            matrix_state = "not_researched"
        result[dimension] = {
            "summary": summary,
            "citations": ids,
            "evidence_strength": strength,
            "matrix_state": matrix_state,
            "observed_citation_count": int(independence.get("observed_citation_count") or 0),
            "unique_source_identity_count": int(independence.get("unique_source_identity_count") or 0),
            "independent_source_count": independent_count,
            "independent_lineage_count": independent_count,
            "uncertain_lineage_count": int(independence.get("uncertain_lineage_count") or 0),
            "repeated_or_derivative_citation_count": int(independence.get("repeated_or_derivative_citation_count") or 0),
            "primary_or_authoritative_source_count": authoritative_count,
            "fresh_citation_count": sum(1 for value in freshness if value == "fresh"),
            "stale_citation_count": sum(1 for value in freshness if value == "stale"),
            "supporting_evidence_count": supports,
            "refuting_evidence_count": refutes,
            "unresolved_evidence_count": unresolved,
            "evidence_present": bool(summary and ids),
            "candidate_specific_citations": candidate_specific_ids,
            "all_candidate_specific_citations": all_candidate_specific_ids,
            "role_mismatch_citation_count": len(role_mismatch_ids),
            "source_evidence_role_counts": dict(sorted(role_counts.items())),
            "candidate_specific_evidence_present": bool(summary and candidate_specific_ids),
            "citation_volume_increases_confidence": False,
        }
    return result


def plan_candidate_evidence_follow_up(
    synthesis: Mapping[str, Any],
    *,
    remaining_query_budget: int,
    remaining_page_budget: int,
    remaining_failure_budget: int,
    existing_query_digests: Iterable[str] = (),
    max_followups: int = 12,
) -> dict[str, Any]:
    """Plan product-specific queries for weak or missing evidence dimensions.

    Candidate names and descriptions originate in public-document synthesis,
    not private operator context. Only digest-bound summaries are intended for
    durable receipts; raw query strings remain transient.
    """
    q_budget = max(0, int(remaining_query_budget or 0))
    p_budget = max(0, int(remaining_page_budget or 0))
    f_budget = max(0, int(remaining_failure_budget or 0))
    maximum = max(0, min(int(max_followups or 0), q_budget, p_budget, 12))
    if maximum <= 0 or f_budget <= 0:
        return {
            "ok": True,
            "status": "candidate_evidence_follow_up_not_permitted_by_remaining_budget",
            "queries": [],
            "query_count": 0,
            "candidate_count": 0,
            "evidence_dimensions": [],
            "public_summary": [],
            **_DENIED,
        }

    candidates = [
        dict(row)
        for row in list(synthesis.get("reasonable_inferences") or [])
        if isinstance(row, Mapping)
        and _clean(row.get("claim_code"), 80) != "synthesis_recommendation"
        and _clean(row.get("title"), 140)
    ]
    recommendation = synthesis.get("recommendation") if isinstance(synthesis.get("recommendation"), Mapping) else {}
    recommended = _clean(recommendation.get("title"), 140).casefold()
    candidates.sort(key=lambda row: (
        0 if _clean(row.get("title"), 140).casefold() == recommended else 1,
        {"weak": 0, "moderate": 1, "strong": 2}.get(_clean(row.get("evidence_strength"), 20), 0),
        _clean(row.get("title"), 140).casefold(),
    ))

    existing = {str(value).casefold() for value in existing_query_digests if str(value)}
    gaps: dict[str, list[str]] = {}
    for row in candidates:
        title = _clean(row.get("title"), 140)
        dimensions = row.get("evidence_dimensions") if isinstance(row.get("evidence_dimensions"), Mapping) else {}
        gaps[title] = [
            dimension
            for dimension in RESEARCH_EVIDENCE_DIMENSIONS
            if not isinstance(dimensions.get(dimension), Mapping)
            or not dimensions[dimension].get("evidence_present")
            or _clean(dimensions[dimension].get("evidence_strength"), 20) == "weak"
        ]

    rows: list[dict[str, Any]] = []
    # Round-robin by dimension gives multiple candidates a chance before one
    # candidate consumes the entire bounded follow-up budget.
    for dimension_index in range(len(RESEARCH_EVIDENCE_DIMENSIONS)):
        for candidate in candidates:
            if len(rows) >= maximum:
                break
            title = _clean(candidate.get("title"), 140)
            candidate_gaps = gaps.get(title, [])
            if dimension_index >= len(candidate_gaps):
                continue
            dimension = candidate_gaps[dimension_index]
            customer = _clean(candidate.get("customer"), 180)
            problem = _clean(candidate.get("problem"), 220)
            product = _clean(candidate.get("product"), 220)
            dimension_terms = {
                "demand": "demand documented user pain requests complaints reddit forum manual workflow",
                "competition": "existing competitors alternatives pricing plans differentiation",
                "implementation_dependencies": "implementation documentation API dependencies github open source",
                "free_tier_feasibility": "official pricing free plan limits quotas zero cost hosting",
            }[dimension]
            # Put the evidence dimension before descriptive prose so the
            # privacy sanitizer's bounded term limit cannot discard the part
            # that makes this query materially different from the other cells.
            if dimension == "demand":
                evidence_subject = f"{customer.casefold()} {problem.casefold()}"
            else:
                evidence_subject = product.casefold()
            query = sanitize_public_query(f"{title.casefold()} {dimension_terms} {evidence_subject}")
            if not query:
                continue
            digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
            if digest in existing:
                continue
            existing.add(digest)
            candidate_digest = _digest({
                "title": title,
                "customer": customer,
                "problem": problem,
                "product": product,
            })
            rows.append({
                "subquestion_id": f"candidate_{candidate_digest[:12]}_{dimension}",
                "candidate_name": title,
                "candidate_digest": candidate_digest,
                "evidence_dimension": dimension,
                "query": query,
                "query_digest": digest,
                "preferred_source_kind": "primary_official" if dimension in {"implementation_dependencies", "free_tier_feasibility"} else "community_experience",
                "follow_up_reason": "candidate_specific_evidence_gap",
                "private_context_removed": True,
            })
        if len(rows) >= maximum:
            break

    summary = [{
        "subquestion_id": row["subquestion_id"],
        "candidate_digest": row["candidate_digest"],
        "evidence_dimension": row["evidence_dimension"],
        "query_digest": row["query_digest"],
        "preferred_source_kind": row["preferred_source_kind"],
        "follow_up_reason": row["follow_up_reason"],
        "private_context_removed": True,
    } for row in rows]
    result = {
        "ok": True,
        "status": "candidate_evidence_follow_up_ready" if rows else "candidate_evidence_follow_up_not_needed",
        "queries": rows,
        "query_count": len(rows),
        "candidate_count": len({row["candidate_digest"] for row in rows}),
        "evidence_dimensions": sorted({row["evidence_dimension"] for row in rows}),
        "public_summary": summary,
        "candidate_identity_exposed_in_public_receipt": False,
        "raw_query_text_exposed": False,
        "material_gap_required": True,
        **_DENIED,
    }
    result["candidate_follow_up_plan_digest"] = _digest(summary)
    return result



def extract_claim_evidence(
    *,
    plan_digest: str,
    observations: Iterable[Mapping[str, Any]],
    citation_context: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Transform signed Era 7 observations into bounded claim-evidence records."""
    obs = [dict(row or {}) for row in list(observations)[:64]]
    bundle = capture_research_evidence(plan_digest=plan_digest, observations=obs)
    context = dict(citation_context or {})
    by_receipt = {str(row.get("receipt_digest") or ""): row for row in obs}
    evidence: list[dict[str, Any]] = []
    for row in list(bundle.get("evidence") or [])[:64]:
        native = by_receipt.get(str(row.get("native_receipt_digest") or ""), {})
        citation_id = _clean(row.get("citation_id"), 80)
        meta = dict(context.get(citation_id) or {})
        public_url = _sanitized_public_url(meta.get("public_url") or native.get("public_url"))
        host = _clean(meta.get("host") or (urlsplit(public_url).hostname if public_url else ""), 255).casefold()
        relevance = _clamp(native.get("relevance_score"), _clamp(row.get("quality_score"), 0.0))
        quality = _clamp(row.get("quality_score"), 0.0)
        stance = _clean(row.get("stance"), 20) or "unknown"
        freshness = "fresh" if row.get("freshness_known") and row.get("fresh_enough") else "stale" if row.get("freshness_known") else "unknown"
        uncertainty = 1.0 if stance == "unknown" else 0.7 if stance == "mixed" else round(1.0 - (quality * relevance), 4)
        identity = source_identity({
            "citation_id": citation_id,
            "public_url": public_url,
            "canonical_url": meta.get("canonical_url"),
            "host": host,
            "source_kind": _clean(row.get("source_kind"), 60) or "unknown",
            "source_digest": _hex64(row.get("source_digest")),
            "publisher_id": meta.get("publisher_id"),
            "lineage_origin_digest": meta.get("lineage_origin_digest"),
            "mirror_of_source_digest": meta.get("mirror_of_source_digest"),
            "syndicated_from_source_digest": meta.get("syndicated_from_source_digest"),
            "attribution_source_digest": meta.get("attribution_source_digest"),
            "attribution_digest": meta.get("attribution_digest"),
            "content_similarity_digest": meta.get("content_similarity_digest"),
            "content_similarity_confidence": meta.get("content_similarity_confidence"),
        })
        evidence.append({
            "claim_code": _clean(row.get("claim_code"), 120),
            "source_digest": _hex64(row.get("source_digest")),
            "evidence_digest": _hex64(row.get("evidence_digest")),
            "citation_id": citation_id,
            "public_url": public_url,
            "source_identity": host or _hex64(row.get("source_digest")),
            "source_kind": _clean(row.get("source_kind"), 60) or "unknown",
            "candidate_digest": _hex64(meta.get("candidate_digest")),
            "evidence_dimension": _clean(meta.get("evidence_dimension"), 60),
            "stance": stance,
            "freshness": freshness,
            "relevance_score": relevance,
            "quality_score": quality,
            "uncertainty": uncertainty,
            "source_identity_digest": identity.get("source_identity_digest", ""),
            "canonical_page_digest": identity.get("canonical_page_digest", ""),
            "publisher_digest": identity.get("publisher_digest", ""),
            "explicit_origin_digest": identity.get("explicit_origin_digest", ""),
            "attribution_digest": identity.get("attribution_digest", ""),
            "content_similarity_digest": identity.get("content_similarity_digest", ""),
            "content_similarity_confidence": identity.get("content_similarity_confidence", "unknown"),
            "authoritative_source": bool(identity.get("authoritative_source")),
            "authoritative_observation": True,
            "raw_page_content_persisted": False,
            "raw_quote_persisted": False,
        })
    result = {
        "ok": bool(bundle.get("ok")),
        "status": "bounded_claim_evidence_extracted",
        "contract_version": CONTRACT_VERSION,
        "plan_digest": _hex64(plan_digest),
        "evidence": evidence,
        "evidence_count": len(evidence),
        "contradicted_claim_codes": list(bundle.get("contradicted_claim_codes") or []),
        "signed_observation_receipts_required": True,
        "raw_page_content_persisted": False,
        "raw_quotes_persisted": False,
        **_DENIED,
    }
    result["evidence_extraction_digest"] = _digest(evidence)
    return result


def compare_cross_source_evidence(extraction: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve conflict/staleness while counting independent claim lineages, not citation volume."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in list(extraction.get("evidence") or [])[:128]:
        if isinstance(row, Mapping):
            code = _clean(row.get("claim_code"), 120)
            if code:
                groups.setdefault(code, []).append(dict(row))
    comparisons: list[dict[str, Any]] = []
    for code in sorted(groups):
        rows = groups[code]
        clustered = cluster_evidence_lineages(rows)
        lineage_by_citation = {
            _clean(row.get("citation_id"), 80): row
            for row in list(clustered.get("citations") or [])
            if _clean(row.get("citation_id"), 80)
        }
        lineage_rows: dict[str, list[dict[str, Any]]] = {}
        uncertain_rows: list[dict[str, Any]] = []
        for row in rows:
            citation_id = _clean(row.get("citation_id"), 80)
            meta = lineage_by_citation.get(citation_id, {})
            decorated = dict(
                row,
                lineage_digest=_hex64(meta.get("lineage_digest")),
                lineage_reason=_clean(meta.get("lineage_reason"), 60),
                independence_state=_clean(meta.get("independence_state"), 20) or "independent",
            )
            if decorated["independence_state"] == "uncertain":
                uncertain_rows.append(decorated)
                continue
            lineage_key = str(decorated.get("lineage_digest") or decorated.get("source_identity_digest") or decorated.get("source_digest") or citation_id)
            lineage_rows.setdefault(lineage_key, []).append(decorated)

        representatives: list[dict[str, Any]] = []
        for lineage_key, members in sorted(lineage_rows.items()):
            ordered = sorted(
                members,
                key=lambda item: (
                    _clamp(item.get("quality_score")) * _clamp(item.get("relevance_score")),
                    _clamp(item.get("quality_score")),
                    _clean(item.get("citation_id"), 80),
                ),
                reverse=True,
            )
            representative = dict(ordered[0])
            stances = {_clean(item.get("stance"), 20) for item in members}
            if "supports" in stances and "refutes" in stances:
                representative["stance"] = "mixed"
            representative["lineage_citation_count"] = len(members)
            representatives.append(representative)

        fresh = [row for row in representatives if row.get("freshness") == "fresh"]
        supports = [row for row in fresh if row.get("stance") == "supports"]
        refutes = [row for row in fresh if row.get("stance") == "refutes"]
        incomplete = [row for row in representatives if row.get("stance") in {"unknown", "mixed"}] + uncertain_rows
        stale = [row for row in representatives if row.get("freshness") == "stale"]
        if supports and refutes:
            state = "conflicted"
        elif supports:
            state = "supported"
        elif refutes:
            state = "refuted"
        elif stale and not fresh:
            state = "stale_only"
        else:
            state = "incomplete"
        citations = [_clean(row.get("citation_id"), 80) for row in representatives if _clean(row.get("citation_id"), 80)]
        quality_values = [_clamp(row.get("quality_score")) for row in representatives]
        # Retain the v2502 compatibility counters (host/source-identity based)
        # while exposing v2503.3 lineage counters separately. Recommendation
        # confidence consumes the lineage fields, never these legacy counters.
        def legacy_source_key(item: Mapping[str, Any]) -> str:
            supplied = _clean(item.get("source_identity"), 255).casefold()
            if supplied:
                return supplied
            host = _clean(item.get("host"), 255).casefold()
            if not host:
                try:
                    host = (urlsplit(str(item.get("public_url") or "")).hostname or "").casefold()
                except Exception:
                    host = ""
            return host or _hex64(item.get("source_digest")) or _clean(item.get("citation_id"), 80)
        legacy_fresh_support_keys = {legacy_source_key(row) for row in rows if row.get("freshness") == "fresh" and row.get("stance") == "supports"}
        legacy_fresh_refute_keys = {legacy_source_key(row) for row in rows if row.get("freshness") == "fresh" and row.get("stance") == "refutes"}
        legacy_all_keys = [legacy_source_key(row) for row in rows]
        legacy_same_source_repetition_count = max(0, len(legacy_all_keys) - len(set(legacy_all_keys)))
        freshness_counts = {
            "fresh": sum(1 for row in representatives if row.get("freshness") == "fresh"),
            "stale": sum(1 for row in representatives if row.get("freshness") == "stale"),
            "unknown": sum(1 for row in representatives if row.get("freshness") not in {"fresh", "stale"}),
        }
        quality_bands = {
            "high": sum(1 for value in quality_values if value >= 0.75),
            "medium": sum(1 for value in quality_values if 0.5 <= value < 0.75),
            "low": sum(1 for value in quality_values if 0 < value < 0.5),
            "unknown": sum(1 for value in quality_values if value <= 0),
        }
        comparisons.append({
            "claim_code": code,
            "state": state,
            "supporting_citations": [_clean(row.get("citation_id"), 80) for row in supports],
            "refuting_citations": [_clean(row.get("citation_id"), 80) for row in refutes],
            "incomplete_citations": [_clean(row.get("citation_id"), 80) for row in incomplete],
            "stale_citations": [_clean(row.get("citation_id"), 80) for row in stale],
            "all_independent_citations": citations,
            "observed_citation_count": int(clustered.get("observed_citation_count") or len(rows)),
            "unique_source_identity_count": int(clustered.get("unique_source_identity_count") or 0),
            "independent_source_count": len(representatives),
            "independent_lineage_count": len(representatives),
            "uncertain_lineage_count": int(clustered.get("uncertain_lineage_count") or 0),
            "supporting_source_count": len(legacy_fresh_support_keys),
            "refuting_source_count": len(legacy_fresh_refute_keys),
            "independent_evidence_count": len(representatives),
            "duplicate_evidence_count": int(clustered.get("repeated_or_derivative_citation_count") or 0),
            "repeated_or_derivative_citation_count": int(clustered.get("repeated_or_derivative_citation_count") or 0),
            "same_source_repetition_count": legacy_same_source_repetition_count,
            "primary_or_authoritative_source_count": int(clustered.get("primary_or_authoritative_lineage_count") or 0),
            "freshness_bands": freshness_counts,
            "quality_bands": quality_bands,
            "supporting_evidence_count": len(supports),
            "refuting_evidence_count": len(refutes),
            "unresolved_evidence_count": len(incomplete),
            "contradiction_preserved": bool(supports and refutes),
            "minority_evidence_preserved": bool(supports and refutes),
            "repetition_counts_as_independent_confirmation": False,
            "citation_volume_increases_confidence": False,
            "max_quality": max(quality_values, default=0.0),
            "max_relevance": max((_clamp(row.get("relevance_score")) for row in representatives), default=0.0),
            "evidence_weight": round(max((_clamp(row.get("quality_score")) * _clamp(row.get("relevance_score")) for row in representatives), default=0.0), 4),
            "lineage_digest": _hex64(clustered.get("lineage_digest")),
        })
    result = {
        "ok": True,
        "status": "cross_source_evidence_compared",
        "contract_version": CONTRACT_VERSION,
        "claims": comparisons,
        "claim_count": len(comparisons),
        "conflicted_claim_codes": [row["claim_code"] for row in comparisons if row["state"] == "conflicted"],
        "duplicate_evidence_count": sum(int(row["duplicate_evidence_count"]) for row in comparisons),
        "repeated_or_derivative_citation_count": sum(int(row["repeated_or_derivative_citation_count"]) for row in comparisons),
        "contradictions_averaged_away": False,
        "citation_volume_increases_confidence": False,
        **_DENIED,
    }
    result["comparison_digest"] = _digest(comparisons)
    return result


def assemble_cited_conclusion(
    comparison: Mapping[str, Any],
    *,
    claim_labels: Mapping[str, str] | None = None,
    citations: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Assemble evidence-weighted, traceable findings without hiding uncertainty."""
    labels = {str(key): _clean(value, 240) for key, value in dict(claim_labels or {}).items()}
    citation_rows = [dict(row or {}) for row in list(citations)[:128]]
    citation_index = {_clean(row.get("citation_id"), 80): row for row in citation_rows if _clean(row.get("citation_id"), 80)}
    verified: list[dict[str, Any]] = []
    inferences: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    traceability: list[dict[str, Any]] = []
    for claim in list(comparison.get("claims") or [])[:MAX_REPORT_ITEMS]:
        if not isinstance(claim, Mapping):
            continue
        code = _clean(claim.get("claim_code"), 120)
        label = labels.get(code) or code.replace("-", " ").replace("_", " ")
        state = _clean(claim.get("state"), 32)
        supporting = list(dict.fromkeys(str(v) for v in list(claim.get("supporting_citations") or []) if str(v)))
        refuting = list(dict.fromkeys(str(v) for v in list(claim.get("refuting_citations") or []) if str(v)))
        quality = _clamp(claim.get("max_quality"))
        relevance = _clamp(claim.get("max_relevance"))
        weight = round(float(claim.get("evidence_weight") or (quality * relevance)), 4)
        legacy_source_semantics = "supporting_source_count" not in claim and "refuting_source_count" not in claim
        supporting_sources = int(claim.get("supporting_source_count") or claim.get("independent_source_count") or (1 if supporting else 0))
        refuting_sources = int(claim.get("refuting_source_count") or claim.get("independent_source_count") or (1 if refuting else 0))
        if state == "supported" and supporting:
            independently_confirmed = supporting_sources >= 2
            qualifies_verified = quality >= 0.65 and relevance >= 0.5 and (independently_confirmed or legacy_source_semantics)
            row = {
                "claim_code": code, "finding": label, "stance": "supported", "citations": supporting, "traceable": True,
                "evidence_weight": weight, "independent_source_count": supporting_sources,
                "independently_confirmed": independently_confirmed,
                "classification": "verified" if qualifies_verified else "inference",
            }
            (verified if qualifies_verified else inferences).append(row)
            traceability.append({"claim_code": code, "classification": row["classification"], "citations": supporting, "evidence_bound": True})
        elif state == "refuted" and refuting:
            independently_confirmed = refuting_sources >= 2
            qualifies_verified = quality >= 0.65 and relevance >= 0.5 and (independently_confirmed or legacy_source_semantics)
            row = {
                "claim_code": code, "finding": label, "stance": "refuted", "citations": refuting, "traceable": True,
                "evidence_weight": weight, "independent_source_count": refuting_sources,
                "independently_confirmed": independently_confirmed,
                "classification": "verified" if qualifies_verified else "inference",
            }
            (verified if qualifies_verified else inferences).append(row)
            traceability.append({"claim_code": code, "classification": row["classification"], "citations": refuting, "evidence_bound": True})
        elif state == "conflicted":
            row = {
                "claim_code": code, "finding": label, "supporting_citations": supporting, "refuting_citations": refuting,
                "traceable": True, "evidence_weight": weight, "minority_evidence_preserved": True,
                "classification": "unresolved_disagreement",
            }
            disagreements.append(row)
            traceability.append({"claim_code": code, "classification": "unresolved_disagreement", "citations": supporting + refuting, "evidence_bound": True})
        else:
            row = {
                "claim_code": code, "finding": label,
                "reason": "stale evidence only" if state == "stale_only" else "missing or incomplete evidence",
                "citations": list(dict.fromkeys(str(v) for v in list(claim.get("all_independent_citations") or []) if str(v))),
                "traceable": True, "classification": "evidence_gap",
            }
            missing.append(row)
            traceability.append({"claim_code": code, "classification": "evidence_gap", "citations": list(row["citations"]), "evidence_bound": True})

    used_ids = {citation for row in verified + inferences for citation in row.get("citations", [])}
    used_ids |= {citation for row in disagreements for citation in list(row.get("supporting_citations", [])) + list(row.get("refuting_citations", []))}
    used_ids |= {citation for row in missing for citation in row.get("citations", [])}
    used_citations: list[dict[str, Any]] = []
    seen_source_refs: set[tuple[str, str]] = set()
    repeated_source_citation_count = 0
    for cid in sorted(used_ids):
        source = citation_index.get(cid, {})
        host = _clean(source.get("host"), 255).casefold()
        source_digest = _hex64(source.get("source_digest"))
        source_key = (host, source_digest)
        repeated = bool((host or source_digest) and source_key in seen_source_refs)
        if host or source_digest:
            seen_source_refs.add(source_key)
        if repeated:
            repeated_source_citation_count += 1
        used_citations.append({
            "citation_id": cid, "public_url": _clean(source.get("public_url"), 2048), "host": host,
            "source_kind": _clean(source.get("source_kind"), 60) or "unknown",
            "freshness": _clean(source.get("freshness"), 16) or "unknown",
            "quality_score": _clamp(source.get("quality_score"), 0.0),
            "relevance_score": _clamp(source.get("relevance_score"), 0.0),
            "source_digest": source_digest, "repeated_source_reference": repeated,
        })

    lines: list[str] = []
    if verified:
        lines.append("Verified findings: " + "; ".join(f"{row['finding']} [{', '.join(row['citations'])}]" for row in verified))
    if inferences:
        lines.append("Reasonable inferences: " + "; ".join(f"{row['finding']} [{', '.join(row['citations'])}]" for row in inferences))
    if disagreements:
        lines.append("Unresolved disagreement remains for: " + "; ".join(row["finding"] for row in disagreements))
    if missing:
        lines.append("Missing or limited evidence remains for: " + "; ".join(row["finding"] for row in missing))
    if not lines:
        lines.append("No externally verified conclusion is available from the bounded evidence collected.")
    material_traceable = all(row.get("evidence_bound") and (row.get("citations") or row.get("classification") == "evidence_gap") for row in traceability)
    result = {
        "ok": True,
        "status": "cited_research_conclusion_ready" if (verified or inferences or disagreements) else "cited_research_conclusion_insufficient_evidence",
        "contract_version": CONTRACT_VERSION,
        "verified_findings": verified,
        "reasonable_inferences": inferences,
        "unresolved_disagreements": disagreements,
        "missing_evidence": missing,
        "limitations": [
            "Only evidence admitted by signed bounded observations is considered.",
            "Duplicate or same-source repetition is not independent confirmation.",
            "Stale or unknown evidence does not silently satisfy a current-evidence requirement.",
            "Generated prose is synthesis, not evidence.",
            "A single-source supported claim remains labeled inference unless legacy evidence lacks source-independence metadata.",
        ],
        "citations": used_citations,
        "citation_count": len(used_citations),
        "repeated_source_citation_count": repeated_source_citation_count,
        "repeated_citations_count_as_independent_confirmation": False,
        "minority_and_contradictory_evidence_preserved": all(row.get("minority_evidence_preserved") for row in disagreements),
        "material_conclusion_traceability": traceability,
        "all_material_conclusions_evidence_bound_or_labeled_inference": material_traceable,
        "rendered_answer": " ".join(lines),
        "externally_verifiable_claims_traceable": material_traceable,
        "generated_prose_is_evidence": False,
        "raw_page_content_persisted": False,
        "raw_query_text_exposed": False,
        **_DENIED,
    }
    result["report_digest"] = _digest({k: v for k, v in result.items() if k != "rendered_answer"})
    return result


RECOMMENDATION_CONFIDENCE_THRESHOLD = "moderate-confidence"


def _candidate_independence_summary(
    finding: Mapping[str, Any],
    citation_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    dimensions = finding.get("evidence_dimensions") if isinstance(finding.get("evidence_dimensions"), Mapping) else {}
    supporting = [
        citation_id
        for dimension in RESEARCH_EVIDENCE_DIMENSIONS
        for citation_id in list((dimensions.get(dimension) or {}).get("candidate_specific_citations") or [])
    ]
    supplied = supporting or list(finding.get("citations") or [])
    ids = list(dict.fromkeys(_clean(value, 80) for value in supplied if _clean(value, 80) in citation_index))
    rows = [citation_index[cid] for cid in ids]
    return independence_summary(rows)


def _candidate_evidence_strength(dimensions: Mapping[str, Any]) -> str:
    cells = [dimensions.get(dimension) or {} for dimension in RESEARCH_EVIDENCE_DIMENSIONS]
    states = [_clean(cell.get("matrix_state"), 48) for cell in cells]
    strengths = [_clean(cell.get("evidence_strength"), 24) for cell in cells]
    supported = states.count("supported")
    if supported == len(RESEARCH_EVIDENCE_DIMENSIONS) and strengths.count("strong") >= 3:
        return "strong"
    if supported >= 3 and "researched_with_no_credible_evidence" not in states and "not_researched" not in states:
        return "moderate"
    return "weak"


def _matrix_evidence_summary(dimensions: Mapping[str, Any]) -> str:
    bits = []
    for dimension in RESEARCH_EVIDENCE_DIMENSIONS:
        cell = dimensions.get(dimension) or {}
        bits.append(
            f"{dimension.replace('_', ' ')}={_clean(cell.get('matrix_state'), 48) or 'not_researched'}"
            f" ({int(cell.get('independent_lineage_count') or 0)} independent)"
        )
    return "; ".join(bits)


def _calibrated_recommendation_conclusion(*, threshold_met: bool, confidence_label: str) -> str:
    if threshold_met and confidence_label == "high-confidence":
        return "It has the strongest independently supported combination across the requested comparison dimensions."
    if threshold_met:
        return "It has the strongest currently supported combination across the requested comparison dimensions."
    return "It ranks highest within this bounded session, but the evidence does not support an unqualified winner."


def _recommendation_confidence(
    findings: Iterable[Mapping[str, Any]],
    citation_index: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return understandable deterministic confidence labels without fake precision."""
    assessments: list[dict[str, Any]] = []
    for source in list(findings)[:8]:
        row = dict(source)
        dimensions = row.get("evidence_dimensions") if isinstance(row.get("evidence_dimensions"), Mapping) else {}
        states = [
            _clean((dimensions.get(dimension) or {}).get("matrix_state"), 48)
            for dimension in RESEARCH_EVIDENCE_DIMENSIONS
        ]
        supported = states.count("supported")
        weak = states.count("weak")
        contradicted = states.count("contradicted")
        no_credible = states.count("researched_with_no_credible_evidence")
        not_researched = states.count("not_researched")
        independence = _candidate_independence_summary(row, citation_index)
        lineages = int(independence.get("independent_lineage_count") or 0)
        uncertain_lineages = int(independence.get("uncertain_lineage_count") or 0)
        authoritative = int(independence.get("primary_or_authoritative_lineage_count") or 0)
        repeated = int(independence.get("repeated_or_derivative_citation_count") or 0)
        max_quality = float(row.get("max_source_quality") or 0.0)
        fresh_count = sum(
            int((dimensions.get(dimension) or {}).get("fresh_citation_count") or 0)
            for dimension in RESEARCH_EVIDENCE_DIMENSIONS
        )

        if lineages <= 0 or (supported == 0 and weak == 0):
            label = "unsupported"
            reasons = ["No independently supported candidate-specific matrix cell cleared the evidence floor."]
        elif (
            not_researched == 0
            and no_credible == 0
            and contradicted == 0
            and supported == len(RESEARCH_EVIDENCE_DIMENSIONS)
            and lineages >= 6
            and authoritative >= 2
            and max_quality >= 0.75
            and fresh_count >= 3
        ):
            label = "high-confidence"
            reasons = [
                "All four matrix dimensions are supported.",
                "At least six independent evidence lineages support the candidate.",
                "At least two primary or authoritative lineages are present.",
                "Observed evidence is high-quality and predominantly fresh.",
            ]
        elif (
            not_researched == 0
            and no_credible == 0
            and supported >= 3
            and lineages >= 3
            and max_quality >= 0.6
            and contradicted <= 1
        ):
            label = "moderate-confidence"
            reasons = [
                "At least three matrix dimensions have credible support.",
                "At least three independent evidence lineages contribute.",
                "No more than one material contradiction remains.",
            ]
        else:
            label = "tentative"
            reasons = [
                "Some candidate-specific evidence is present, but coverage, independence, quality, freshness, or contradiction limits remain."
            ]
        if repeated:
            reasons.append(f"{repeated} repeated or derivative citation(s) were excluded from independent confirmation.")
        if uncertain_lineages:
            reasons.append(f"{uncertain_lineages} lineage relationship(s) remain uncertain and do not raise confidence.")
        if contradicted:
            reasons.append(f"{contradicted} matrix dimension(s) contain contradictory evidence.")
        if no_credible:
            reasons.append(f"{no_credible} researched matrix dimension(s) produced no credible evidence.")
        if not_researched:
            reasons.append(f"{not_researched} matrix dimension(s) were not researched in this session.")
        assessments.append({
            "candidate_digest": _hex64(row.get("candidate_digest")),
            "title": _clean(row.get("title"), 140),
            "confidence_label": label,
            "threshold_label": RECOMMENDATION_CONFIDENCE_THRESHOLD,
            "threshold_met": label in {"moderate-confidence", "high-confidence"},
            "reasons": reasons[:8],
            "matrix_coverage": {
                "supported": supported,
                "weak": weak,
                "contradicted": contradicted,
                "researched_with_no_credible_evidence": no_credible,
                "not_researched": not_researched,
            },
            "observed_citation_count": int(independence.get("observed_citation_count") or 0),
            "unique_source_identity_count": int(independence.get("unique_source_identity_count") or 0),
            "independent_lineage_count": lineages,
            "uncertain_lineage_count": uncertain_lineages,
            "repeated_or_derivative_citation_count": repeated,
            "primary_or_authoritative_source_count": authoritative,
            "citation_volume_increases_confidence": False,
        })
    return assessments


def validate_research_synthesis(
    raw: Mapping[str, Any] | None,
    *,
    citations: Iterable[Mapping[str, Any]],
    requested_result_count: int = 0,
    candidate_identities: Mapping[str, Any] | None = None,
    require_candidate_specific_coverage: bool = False,
    candidate_research_matrix_complete: bool = False,
    require_recommendation: bool = True,
    allow_generic_opportunity_names: bool = False,
    required_evidence_dimension: str = "",
) -> dict[str, Any]:
    """Admit only bounded synthesis whose material claims cite observed sources."""
    payload = dict(raw or {})
    citation_rows = [dict(row or {}) for row in list(citations)[:128]]
    citation_index = {
        _clean(row.get("citation_id"), 80): row
        for row in citation_rows
        if _clean(row.get("citation_id"), 80)
        and canonicalize_public_url(row.get("canonical_url") or row.get("public_url"))
    }
    invalid_public_url_citation_count = sum(
        1
        for row in citation_rows
        if _clean(row.get("citation_id"), 80)
        and not canonicalize_public_url(row.get("canonical_url") or row.get("public_url"))
    )
    requested = max(0, min(int(requested_result_count or 0), 8))
    opportunity_contract = requested > 0
    identity_rows = [
        dict(row)
        for row in list((candidate_identities or {}).get("reasonable_inferences") or [])
        if isinstance(row, Mapping)
        and _clean(row.get("claim_code"), 80) != "synthesis_recommendation"
        and _clean(row.get("title"), 140)
        and _hex64(row.get("candidate_digest"))
    ]
    identity_groups: dict[str, list[dict[str, Any]]] = {}
    for row in identity_rows:
        key = re.sub(r"[^a-z0-9]+", " ", _clean(row.get("title"), 140).casefold()).strip()
        identity_groups.setdefault(key, []).append(row)
    identity_index = {key: rows[0] for key, rows in identity_groups.items() if len(rows) == 1}
    source_rows = payload.get("opportunities") if isinstance(payload.get("opportunities"), list) else ([] if opportunity_contract else payload.get("findings"))
    findings: list[dict[str, Any]] = []
    admitted_names: set[str] = set()
    rejection_reason_counts: dict[str, int] = {}

    def reject(reason: str) -> None:
        rejection_reason_counts[reason] = rejection_reason_counts.get(reason, 0) + 1

    for raw_row in list(source_rows or [])[: max(8, requested)]:
        if not isinstance(raw_row, Mapping):
            reject("row_not_object")
            continue
        title = _clean(raw_row.get("name") or raw_row.get("title"), 140)
        customer = _clean(raw_row.get("customer"), 240)
        problem = _clean(raw_row.get("problem"), 360)
        product = _clean(raw_row.get("product"), 360)
        zero_budget_rationale = _clean(raw_row.get("zero_budget_rationale"), 360)
        conclusion = _clean(raw_row.get("evidence_summary") or raw_row.get("conclusion") or raw_row.get("summary") or raw_row.get("why"), 700)
        supplied_ids = raw_row.get("citation_ids") or raw_row.get("citations") or raw_row.get("evidence") or []
        ids = list(dict.fromkeys(_clean(value, 80) for value in list(supplied_ids) if _clean(value, 80) in citation_index))[:6]
        normalized_name = re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
        generic_name = bool(re.search(
            r"\b(?:strategy|strategies|opportunities|ideas|guide|framework|frameworks|pricing|validation|"
            r"tools|utilities|automation|analytics|platform|software|solutions)\b",
            normalized_name,
        ))
        rejection_reason = ""
        if not title:
            rejection_reason = "missing_title"
        elif not conclusion:
            rejection_reason = "missing_evidence_summary"
        elif not ids:
            rejection_reason = "missing_observed_citations"
        elif normalized_name in admitted_names:
            rejection_reason = "duplicate_title"
        elif opportunity_contract and (not customer or not problem or not product or not zero_budget_rationale):
            rejection_reason = "missing_required_fields"
        if rejection_reason:
            reject(rejection_reason)
            continue
        if required_evidence_dimension:
            # Observation/relevance alone does not establish support for a claim.
            supporting = [citation_index[cid] for cid in ids
                if required_evidence_dimension in source_evidence_role(citation_index[cid])["supportable_dimensions"]
                and citation_index[cid].get("stance") == "supports"
                and citation_index[cid].get("freshness") == "fresh"
                and _clamp(citation_index[cid].get("relevance_score")) >= 0.5]
            support_summary = independence_summary(supporting)
            conflicting = any(citation_index[cid].get("stance") in {"refutes", "mixed"} for cid in ids)
            if conflicting or int(support_summary["independent_lineage_count"]) < 2 or support_summary["uncertain_lineage_count"]:
                reject("independent_dimension_support_missing")
                continue
        uncertainties = [
            _clean(value, 240)
            for value in list(raw_row.get("uncertainties") or [])[:4]
            if _clean(value, 240)
        ]
        computed_candidate_digest = _digest({
            "title": title,
            "customer": customer,
            "problem": problem,
            "product": product,
        })
        bound_identity = identity_index.get(normalized_name)
        candidate_digest = (
            _hex64(bound_identity.get("candidate_digest"))
            if bound_identity
            else computed_candidate_digest
        )
        candidate_identity_bound = bool(bound_identity and candidate_digest)
        evidence_dimensions = _dimension_evidence(
            raw_row,
            citation_index,
            candidate_digest=candidate_digest,
            matrix_attempted=candidate_research_matrix_complete,
        )
        supporting_ids = list(dict.fromkeys(
            citation_id
            for dimension in RESEARCH_EVIDENCE_DIMENSIONS
            for citation_id in evidence_dimensions[dimension]["candidate_specific_citations"]
        ))
        supporting_rows: list[dict[str, Any]] = []
        for citation_id in supporting_ids:
            source = dict(citation_index[citation_id])
            role = source_evidence_role(source)
            source["quality_score"] = min(_clamp(source.get("quality_score")), _clamp(role.get("quality_cap")))
            supporting_rows.append(source)
        source_independence = independence_summary(supporting_rows)
        independent_lineages = int(source_independence.get("independent_lineage_count") or 0)
        max_quality = max((_clamp(row.get("quality_score")) for row in supporting_rows), default=0.0)
        evidence_strength = _candidate_evidence_strength(evidence_dimensions)
        generic_name_fully_evidence_bound = bool(
            candidate_identity_bound
            and all(
                evidence_dimensions[dimension]["candidate_specific_evidence_present"]
                for dimension in RESEARCH_EVIDENCE_DIMENSIONS
            )
        )
        generic_name_matrix_researched = bool(
            generic_name
            and candidate_identity_bound
            and candidate_research_matrix_complete
        )
        if (
            opportunity_contract and generic_name
            and not allow_generic_opportunity_names
            and not generic_name_fully_evidence_bound
            and not generic_name_matrix_researched
        ):
            reject("generic_name")
            continue
        admitted_names.add(normalized_name)
        dimension_ids = [
            citation_id
            for dimension in RESEARCH_EVIDENCE_DIMENSIONS
            for citation_id in evidence_dimensions[dimension]["citations"]
        ]
        ids = list(dict.fromkeys(ids + dimension_ids))[:12]
        evidence_gap_dimensions = [
            dimension
            for dimension in RESEARCH_EVIDENCE_DIMENSIONS
            if not evidence_dimensions[dimension]["evidence_present"]
            or not evidence_dimensions[dimension]["candidate_specific_evidence_present"]
        ]
        matrix_summary = _matrix_evidence_summary(evidence_dimensions)
        finding_text = f"{title}: {conclusion}"
        if opportunity_contract:
            zero_budget_label = (
                "Zero-budget basis"
                if not require_candidate_specific_coverage
                or evidence_dimensions["free_tier_feasibility"]["matrix_state"] == "supported"
                else "Zero-budget hypothesis (not independently verified)"
            )
            finding_text = (
                f"{title} | Customer: {customer} | Problem: {problem} | Product: {product} | "
                f"{zero_budget_label}: {zero_budget_rationale}"
            )
        findings.append({
            "claim_code": f"synthesis_{len(findings) + 1}",
            "finding": finding_text,
            "title": title,
            "customer": customer,
            "problem": problem,
            "product": product,
            "zero_budget_rationale": zero_budget_rationale,
            "conclusion": conclusion,
            "rendered_evidence_summary": matrix_summary,
            "citations": ids,
            "supporting_citation_ids": supporting_ids,
            "uncertainties": uncertainties,
            "evidence_strength": evidence_strength,
            "candidate_digest": candidate_digest,
            "candidate_identity_bound": candidate_identity_bound,
            "generic_name_fully_evidence_bound": generic_name_fully_evidence_bound,
            "candidate_specificity_limited": bool(generic_name and not generic_name_fully_evidence_bound),
            "evidence_dimensions": evidence_dimensions,
            "evidence_gap_dimensions": evidence_gap_dimensions,
            "evidence_dimension_coverage_count": len(RESEARCH_EVIDENCE_DIMENSIONS) - len(evidence_gap_dimensions),
            "max_source_quality": round(max_quality, 4),
            "observed_citation_count": int(source_independence.get("observed_citation_count") or 0),
            "unique_source_identity_count": int(source_independence.get("unique_source_identity_count") or 0),
            "independent_source_count": independent_lineages,
            "independent_lineage_count": independent_lineages,
            "uncertain_lineage_count": int(source_independence.get("uncertain_lineage_count") or 0),
            "repeated_or_derivative_citation_count": int(source_independence.get("repeated_or_derivative_citation_count") or 0),
            "primary_or_authoritative_source_count": int(source_independence.get("primary_or_authoritative_lineage_count") or 0),
            "candidate_evidence_matrix": {
                dimension: {
                    key: evidence_dimensions[dimension].get(key)
                    for key in (
                        "matrix_state", "evidence_strength", "observed_citation_count",
                        "unique_source_identity_count", "independent_lineage_count",
                        "uncertain_lineage_count", "repeated_or_derivative_citation_count",
                        "primary_or_authoritative_source_count", "fresh_citation_count",
                        "stale_citation_count", "supporting_evidence_count",
                        "refuting_evidence_count", "unresolved_evidence_count",
                    )
                }
                for dimension in RESEARCH_EVIDENCE_DIMENSIONS
            },
            "citation_volume_increases_confidence": False,
            "classification": "inference",
            "traceable": True,
            "evidence_bound": True,
        })
    if requested:
        findings = findings[:requested]

    confidence_assessments = _recommendation_confidence(findings, citation_index)
    confidence_by_title = {
        _clean(row.get("title"), 140).casefold(): row
        for row in confidence_assessments
        if _clean(row.get("title"), 140)
    }
    strength_rank = {"weak": 0, "moderate": 1, "strong": 2}
    confidence_rank = {"unsupported": 0, "tentative": 1, "moderate-confidence": 2, "high-confidence": 3}

    def recommendation_rank(row: Mapping[str, Any]) -> tuple[Any, ...]:
        assessment = confidence_by_title.get(_clean(row.get("title"), 140).casefold(), {})
        return (
            confidence_rank.get(str(assessment.get("confidence_label") or "unsupported"), 0),
            int(row.get("evidence_dimension_coverage_count") or 0),
            strength_rank.get(str(row.get("evidence_strength") or "weak"), 0),
            int(row.get("independent_source_count") or 0),
            float(row.get("max_source_quality") or 0.0),
            str(row.get("title") or "").casefold(),
        )

    deterministic_top_finding = max(findings, key=recommendation_rank) if findings else None

    recommendation_raw = payload.get("recommendation") if isinstance(payload.get("recommendation"), Mapping) else {}
    recommendation_title = _clean(recommendation_raw.get("opportunity_name") or recommendation_raw.get("name") or recommendation_raw.get("title"), 140)
    recommendation_text = _clean(recommendation_raw.get("conclusion") or recommendation_raw.get("why"), 700)
    recommendation_ids = list(dict.fromkeys(
        _clean(value, 80)
        for value in list(recommendation_raw.get("citation_ids") or recommendation_raw.get("citations") or [])
        if _clean(value, 80) in citation_index
    ))[:8]
    recommendation = {}
    selected_finding = next((row for row in findings if row["title"].casefold() == recommendation_title.casefold()), None)
    recommendation_selection_deterministically_corrected = False
    if (
        selected_finding
        and deterministic_top_finding
        and candidate_research_matrix_complete
        and selected_finding is not deterministic_top_finding
    ):
        selected_finding = deterministic_top_finding
        recommendation_title = _clean(selected_finding.get("title"), 140)
        recommendation_ids = list(selected_finding.get("supporting_citation_ids") or [])[:8]
        recommendation_selection_deterministically_corrected = True
    selected_confidence = confidence_by_title.get(recommendation_title.casefold(), {})
    eligible_recommendation_ids = (
        set(selected_finding.get("supporting_citation_ids") or [])
        if selected_finding and (require_candidate_specific_coverage or candidate_research_matrix_complete)
        else set(selected_finding.get("citations") or []) if selected_finding else set()
    )
    recommendation_ids = [
        citation_id
        for citation_id in recommendation_ids
        if citation_id in eligible_recommendation_ids
    ]
    recommendation_overlaps_evidence = bool(recommendation_ids)
    recommendation_has_candidate_coverage = bool(
        selected_finding and int(selected_finding.get("evidence_dimension_coverage_count") or 0) > 0
    )
    if (
        recommendation_title
        and recommendation_text
        and recommendation_ids
        and (not opportunity_contract or recommendation_overlaps_evidence)
        and (not require_candidate_specific_coverage or recommendation_has_candidate_coverage)
    ):
        confidence_label = _clean(selected_confidence.get("confidence_label"), 32) or "tentative"
        threshold_met = bool(selected_confidence.get("threshold_met"))
        recommendation = {
            "title": recommendation_title,
            "conclusion": _calibrated_recommendation_conclusion(
                threshold_met=threshold_met,
                confidence_label=confidence_label,
            ),
            "citations": recommendation_ids,
            "evidence_strength": selected_finding.get("evidence_strength", "weak") if selected_finding else "weak",
            "classification": "inference",
            "traceable": True,
            "evidence_bound": True,
            "deterministic_fallback": False,
            "confidence_label": confidence_label,
            "confidence_threshold": RECOMMENDATION_CONFIDENCE_THRESHOLD,
            "confidence_threshold_met": threshold_met,
            "confidence_reasons": list(selected_confidence.get("reasons") or [])[:8],
            "model_generated_conclusion_rendered": False,
        }

    recommendation_deterministic_fallback_used = False
    if (
        require_recommendation
        and not recommendation
        and findings
        and candidate_research_matrix_complete
    ):
        selected_finding = max(
            findings,
            key=recommendation_rank,
        )
        fallback_ids = list(
            selected_finding.get("supporting_citation_ids")
            or (() if require_candidate_specific_coverage else selected_finding.get("citations") or [])
        )[:8]
        if fallback_ids:
            selected_confidence = confidence_by_title.get(_clean(selected_finding.get("title"), 140).casefold(), {})
            recommendation = {
                "title": selected_finding["title"],
                "conclusion": _calibrated_recommendation_conclusion(
                    threshold_met=False,
                    confidence_label="tentative",
                ),
                "citations": fallback_ids,
                "evidence_strength": selected_finding.get("evidence_strength", "weak"),
                "classification": "inference",
                "traceable": True,
                "evidence_bound": True,
                "deterministic_fallback": True,
                "confidence_label": "tentative",
                "confidence_threshold": RECOMMENDATION_CONFIDENCE_THRESHOLD,
                "confidence_threshold_met": False,
                "confidence_reasons": [
                    "The configured synthesis recommendation was invalid, so deterministic recovery remains tentative even when the selected candidate has stronger underlying evidence."
                ] + list(selected_confidence.get("reasons") or [])[:7],
                "model_generated_conclusion_rendered": False,
            }
            recommendation_title = selected_finding["title"]
            recommendation_text = recommendation["conclusion"]
            recommendation_ids = fallback_ids
            recommendation_deterministic_fallback_used = True

    candidate_coverage_complete = (
        not require_candidate_specific_coverage
        or all(not row.get("evidence_gap_dimensions") for row in findings)
    )
    if recommendation and require_candidate_specific_coverage and not candidate_coverage_complete:
        recommendation["confidence_threshold_met"] = False
        if recommendation.get("confidence_label") in {"moderate-confidence", "high-confidence"}:
            recommendation["confidence_label"] = "tentative"
        recommendation["confidence_reasons"] = [
            "The requested candidate comparison still contains candidate-specific evidence gaps, so no unqualified winner is admitted."
        ] + list(recommendation.get("confidence_reasons") or [])[:7]
    if recommendation:
        recommendation["conclusion"] = _calibrated_recommendation_conclusion(
            threshold_met=bool(recommendation.get("confidence_threshold_met")),
            confidence_label=_clean(recommendation.get("confidence_label"), 32) or "tentative",
        )
    candidate_matrix_requirement_met = (
        not require_candidate_specific_coverage
        or bool(candidate_research_matrix_complete)
    )
    complete = (
        bool(findings)
        and (not requested or len(findings) == requested)
        and (not requested or not require_recommendation or bool(recommendation))
        and candidate_matrix_requirement_met
    )
    used_ids = set(recommendation_ids)
    for row in findings:
        used_ids.update(row["citations"])
    used_source_rows = [citation_index[cid] for cid in sorted(used_ids)]
    used_lineages = cluster_evidence_lineages(used_source_rows)
    lineage_meta = {
        _clean(row.get("citation_id"), 80): row
        for row in list(used_lineages.get("citations") or [])
        if _clean(row.get("citation_id"), 80)
    }
    used_citations: list[dict[str, Any]] = []
    for cid in sorted(used_ids):
        source = citation_index[cid]
        identity = source_identity(source)
        lineage = lineage_meta.get(cid, {})
        used_citations.append({
            "citation_id": cid,
            "public_url": _sanitized_public_url(source.get("canonical_url") or source.get("public_url")),
            "host": _clean(source.get("host") or (urlsplit(str(source.get("canonical_url") or source.get("public_url") or "")).hostname or ""), 255).casefold(),
            "source_kind": _clean(source.get("source_kind"), 60) or "unknown",
            "freshness": _clean(source.get("freshness"), 16) or "unknown",
            "quality_score": _clamp(source.get("quality_score")),
            "relevance_score": _clamp(source.get("relevance_score")),
            "source_digest": _hex64(source.get("source_digest")),
            "candidate_digest": _hex64(source.get("candidate_digest")),
            "evidence_dimension": _clean(source.get("evidence_dimension"), 60),
            "stance": _clean(source.get("stance"), 20) or "unknown",
            "source_identity_digest": _hex64(identity.get("source_identity_digest")),
            "canonical_page_digest": _hex64(identity.get("canonical_page_digest")),
            "publisher_digest": _hex64(identity.get("publisher_digest")),
            "lineage_digest": _hex64(lineage.get("lineage_digest")),
            "lineage_reason": _clean(lineage.get("lineage_reason"), 60),
            "independence_state": _clean(lineage.get("independence_state"), 20) or "independent",
            "authoritative_source": bool(identity.get("authoritative_source")),
            "evidence_role": _clean(identity.get("evidence_role"), 60) or "unknown",
            "source_quality_tier": _clean(identity.get("source_quality_tier"), 24) or "unknown",
            "quality_cap": _clamp(identity.get("quality_cap")),
            "supportable_dimensions": list(identity.get("supportable_dimensions") or []),
        })
    disagreements = [
        _clean(value, 320)
        for value in list(payload.get("disagreements") or [])[:6]
        if _clean(value, 320)
    ]
    limitations = [
        _clean(value, 320)
        for value in list(payload.get("limitations") or [])[:6]
        if _clean(value, 320)
    ]
    lines: list[str] = []
    if complete:
        if recommendation:
            confidence_label = _clean(recommendation.get("confidence_label"), 32) or "tentative"
            recommendation_label = "Most promising" if recommendation.get("confidence_threshold_met") else "Best current lead for further research"
            lines.append(
                f"{recommendation_label}: {recommendation['title']}. {recommendation['conclusion']} "
                f"Confidence: {confidence_label}. [{', '.join(recommendation['citations'])}]"
            )
            if recommendation.get("confidence_reasons"):
                lines.append("Why this confidence: " + "; ".join(recommendation["confidence_reasons"]))
            if not recommendation.get("confidence_threshold_met"):
                lines.append(
                    f"This candidate does not clear the configured {RECOMMENDATION_CONFIDENCE_THRESHOLD} threshold for an unqualified strongest-opportunity claim."
                )
        elif opportunity_contract:
            lines.append("No candidate clears the evidence threshold for a recommendation in this bounded session.")
        lines.append("Candidates and key tradeoffs:" if opportunity_contract else "Cited source interpretations (not independently verified):")
        if not opportunity_contract:
            lines.append("Citation checks establish that the pages were observed; they do not verify the model's interpretation or establish independent support for its conclusions.")
        for index, row in enumerate(findings, 1):
            candidate_confidence = confidence_by_title.get(row["title"].casefold(), {})
            if opportunity_contract:
                lines.append(
                    f"{index}. {row['finding']} | Evidence strength: {row['evidence_strength']} | "
                    f"Confidence: {candidate_confidence.get('confidence_label') or 'unsupported'} "
                    f"[{', '.join(row['citations'])}]"
                )
            else:
                lines.append(f"{index}. {row['finding']} [{', '.join(row['citations'])}]")
            if row["uncertainties"]:
                lines.append("   Uncertainty: " + "; ".join(row["uncertainties"]))
            if opportunity_contract:
                matrix_bits = []
                for dimension in RESEARCH_EVIDENCE_DIMENSIONS:
                    cell = row.get("candidate_evidence_matrix", {}).get(dimension, {})
                    matrix_bits.append(
                        f"{dimension.replace('_', ' ')}={cell.get('matrix_state') or 'not_researched'}"
                        f" ({int(cell.get('independent_lineage_count') or 0)} independent)"
                    )
                lines.append("   Evidence matrix: " + "; ".join(matrix_bits))
                gaps = [dimension.replace("_", " ") for dimension in row["evidence_gap_dimensions"]]
                if gaps:
                    lines.append("   Follow-up still needed: " + ", ".join(gaps))
        if disagreements:
            lines.append("Disagreements or uncertainty: " + "; ".join(disagreements))
        if limitations:
            lines.append("Limitations: " + "; ".join(limitations))

    missing = []
    if requested and len(findings) != requested:
        missing.append({
            "claim_code": "requested_result_count",
            "finding": f"The requested {requested} distinct evidence-backed results",
            "reason": f"Only {len(findings)} concrete, distinct, citation-bound opportunity result(s) passed synthesis validation.",
            "citations": sorted(used_ids),
            "classification": "evidence_gap",
            "traceable": True,
        })
    if requested and require_recommendation and not recommendation:
        missing.append({
            "claim_code": "comparative_recommendation",
            "finding": "A citation-bound comparative recommendation",
            "reason": "The synthesis did not select one admitted opportunity with overlapping observed citations.",
            "citations": sorted(used_ids),
            "classification": "evidence_gap",
            "traceable": True,
        })
    for row in findings:
        if not row.get("evidence_gap_dimensions"):
            continue
        missing.append({
            "claim_code": f"{row['claim_code']}_candidate_evidence",
            "finding": f"Candidate-specific evidence coverage for {row['title']}",
            "reason": "Weak or missing evidence remains for: " + ", ".join(
                str(value).replace("_", " ") for value in row["evidence_gap_dimensions"]
            ),
            "citations": list(row["citations"]),
            "classification": "evidence_gap",
            "traceable": True,
        })
    traceability = [
        {"claim_code": row["claim_code"], "classification": "inference", "citations": list(row["citations"]), "evidence_bound": True}
        for row in findings
    ]
    if recommendation:
        traceability.append({
            "claim_code": "synthesis_recommendation",
            "classification": "inference",
            "citations": list(recommendation["citations"]),
            "evidence_bound": True,
        })
    traceability.extend({
        "claim_code": row["claim_code"], "classification": "evidence_gap", "citations": list(row["citations"]), "evidence_bound": True,
    } for row in missing)
    return {
        "ok": complete,
        "status": "citation_bound_research_synthesis_ready" if complete else "citation_bound_research_synthesis_rejected",
        "reasonable_inferences": findings + ([dict(recommendation, claim_code="synthesis_recommendation", finding=f"{recommendation['title']}: {recommendation['conclusion']}")] if recommendation else []),
        "recommendation": recommendation,
        "unresolved_disagreements": [
            {"claim_code": f"synthesis_disagreement_{index}", "finding": value, "classification": "unresolved_disagreement", "traceable": True}
            for index, value in enumerate(disagreements, 1)
        ],
        "missing_evidence": missing,
        "limitations": limitations,
        "citations": used_citations,
        "citation_count": len(used_citations),
        "invalid_public_url_citation_count": invalid_public_url_citation_count,
        "candidate_identity_binding_count": sum(1 for row in findings if row.get("candidate_identity_bound")),
        "candidate_specificity_limited_count": sum(1 for row in findings if row.get("candidate_specificity_limited")),
        "candidate_identity_binding_required": bool(identity_rows),
        "candidate_specific_coverage_required": bool(require_candidate_specific_coverage),
        "candidate_specific_coverage_complete": bool(candidate_coverage_complete),
        "candidate_research_matrix_complete": bool(candidate_research_matrix_complete),
        "candidate_evidence_matrix": [
            {
                "candidate_digest": _hex64(row.get("candidate_digest")),
                "cells": dict(row.get("candidate_evidence_matrix") or {}),
            }
            for row in findings
        ],
        "recommendation_confidence_assessments": confidence_assessments,
        "recommendation_confidence_threshold": RECOMMENDATION_CONFIDENCE_THRESHOLD,
        "strongest_opportunity_admitted": bool(recommendation and recommendation.get("confidence_threshold_met")),
        "source_independence_summary": independence_summary(used_citations),
        "input_opportunity_count": len(list(source_rows or [])[: max(8, requested)]),
        "admitted_opportunity_count": len(findings),
        "rejected_opportunity_reason_counts": dict(sorted(rejection_reason_counts.items())),
        "recommendation_admitted": bool(recommendation),
        "recommendation_deterministic_fallback_used": recommendation_deterministic_fallback_used,
        "recommendation_selection_deterministically_corrected": recommendation_selection_deterministically_corrected,
        "material_conclusion_traceability": traceability,
        "all_material_conclusions_evidence_bound_or_labeled_inference": all(row.get("evidence_bound") for row in traceability),
        "rendered_answer": "\n".join(lines),
        "generated_prose_is_evidence": False,
        "model_generated_evidence_language_rendered": False,
        "raw_page_content_persisted": False,
        "raw_query_text_exposed": False,
        **_DENIED,
    }


__all__ = [
    "CONTRACT_VERSION",
    "decompose_research_objective",
    "build_source_strategy",
    "select_diverse_sources",
    "sanitize_public_query",
    "plan_public_search_queries",
    "plan_adaptive_follow_up",
    "plan_candidate_evidence_follow_up",
    "extract_claim_evidence",
    "compare_cross_source_evidence",
    "assemble_cited_conclusion",
    "RECOMMENDATION_CONFIDENCE_THRESHOLD",
    "validate_research_synthesis",
]
