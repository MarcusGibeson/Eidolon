from __future__ import annotations

"""Source metadata must be read from the document, not left as an inadmissible placeholder.

The search adapter cannot supply a publication date or a source kind, so every
candidate arrives as freshness-unknown and kind-unknown. Both placeholders are
treated downstream as inadmissible: unknown freshness cannot satisfy a
current-evidence claim, and an unknown kind supports no evidence dimension at
all. A trial could therefore never admit evidence, however good the source.

These checks cover reading that metadata off the fetched document, and choosing
the source-age window from the objective's shape rather than a fixed 30 days.
None of it loosens an evidence gate: undeclared metadata stays unknown, and a
promotional page stays unable to establish demand.
"""

import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timedelta, timezone


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2730-9-5-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_research_reasoning import decompose_research_objective
from governed_public_web_research_adapter import _VisibleTextParser, _declared_source_kind
from research_source_independence import source_evidence_role
from research_web_intelligence_v2100 import (
    assess_source_candidate,
    derive_source_freshness,
    evaluate_claim_support,
    plan_research,
)


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


NOW = datetime.now(timezone.utc)
RECENT = (NOW - timedelta(days=5)).date().isoformat()
OLD = (NOW - timedelta(days=500)).date().isoformat()
ANCIENT = (NOW - timedelta(days=1050)).date().isoformat()


def parse(html: str) -> _VisibleTextParser:
    parser = _VisibleTextParser()
    parser.feed(html)
    return parser


def ld_page(payload: str) -> str:
    return (
        f'<html><head><script type="application/ld+json">{payload}</script></head>'
        "<body><p>Creators report chasing payments for months on end.</p></body></html>"
    )


# --- freshness is derived from a declared date, and only from one -----------

require(derive_source_freshness(published_at=RECENT)["fresh_enough"] is True, "recent_declared_date_is_fresh")
require(derive_source_freshness(published_at=OLD)["freshness_known"] is True, "old_declared_date_is_known")
require(derive_source_freshness(published_at=OLD)["fresh_enough"] is False, "old_declared_date_is_not_fresh")
require(derive_source_freshness(published_at="")["freshness_known"] is False, "absent_date_stays_unknown")
require(derive_source_freshness(published_at="not a date")["freshness_known"] is False, "unparseable_date_stays_unknown")
require(derive_source_freshness(published_at="")["fresh_enough"] is False, "unknown_freshness_is_never_fresh")
require(
    derive_source_freshness(published_at=OLD, freshness_policy="slow_changing")["fresh_enough"] is True,
    "slower_policy_admits_an_older_declared_date",
)
require(
    derive_source_freshness(published_at=ANCIENT, freshness_policy="slow_changing")["fresh_enough"] is False,
    "slower_policy_still_rejects_genuinely_outdated_evidence",
)

# An undated candidate must not inherit "published now" from its fetch time.
recent_candidate = assess_source_candidate(url="https://example.com/a", published_at=RECENT, freshness_policy="current")
old_candidate = assess_source_candidate(url="https://example.com/a", published_at=OLD, freshness_policy="current")
undated_candidate = assess_source_candidate(url="https://example.com/a", freshness_policy="current")
require(recent_candidate["fresh_enough"] is True and recent_candidate["age_days"] == 5, "candidate_age_is_measured_from_publication")
require(old_candidate["freshness_known"] is True and old_candidate["fresh_enough"] is False, "old_candidate_is_known_but_not_fresh")
require(undated_candidate["freshness_known"] is False, "undated_candidate_is_not_silently_current")

# --- the fetched document is where the date actually comes from ------------

meta_page = (
    f'<html><head><meta property="article:published_time" content="{RECENT}"></head>'
    "<body><p>Creators report chasing payments.</p></body></html>"
)
require(parse(meta_page).publication_dates == [RECENT], "meta_published_time_is_extracted")
require(parse("<html><body><p>No date anywhere.</p></body></html>").publication_dates == [], "page_without_a_date_declares_none")
require(RECENT in parse(ld_page('{"@type":"NewsArticle","datePublished":"%s"}' % RECENT)).publication_dates, "json_ld_date_published_is_extracted")


def support_state(known: bool, fresh: bool) -> str:
    rows = [
        {
            "claim_code": "rq1", "citation_id": f"web-{index}", "stance": "supports",
            "quality_score": 0.82, "relevance_score": 1.0, "source_observed": True,
            "freshness_known": known, "fresh_enough": fresh, "source_kind": "reputable_secondary",
        }
        for index in range(2)
    ]
    return str(evaluate_claim_support({"evidence": rows}, "rq1", current_claim=True)["support_state"])


require(support_state(False, False) == "insufficient_current_evidence", "undated_evidence_cannot_satisfy_a_current_claim")
require(support_state(True, True) == "supported", "dated_recent_evidence_can_satisfy_a_current_claim")

# --- the source-age window follows the objective's shape -------------------


def recommended_policy(objective: str, freshness: str = "") -> str:
    decomposition = decompose_research_objective(objective, freshness=freshness, budget={"max_queries": 20})
    if not decomposition.get("ok"):
        raise AssertionError(f"objective_did_not_decompose:{decomposition.get('status')}")
    return str(decomposition["recommended_freshness_policy"])


demand = decompose_research_objective("Research Brand Deal Tracking for Content Creators demand.", freshness="", budget={"max_queries": 20})
require(demand["recommended_freshness_policy"] == "slow_changing", "demand_objective_uses_a_durable_window")
require(recommended_policy("Research Foo Bar competition.") == "versioned", "competition_objective_uses_a_versioned_window")
require(recommended_policy("Research Foo Bar free tier feasibility.") == "current", "free_tier_objective_stays_current")
# Superseded deliberately. This asserted that an unshaped objective inherits a
# 30-day window, which turned out to be the defect itself: the default window went
# on to create a semantic currency requirement, so a documentation lookup was asked
# for evidence from the last month. An objective whose wording asks for nothing
# current now gets a reference window. See v2731_0_4 for the invariant.
require(recommended_policy("Research whether creators track sponsorship payments manually") == "slow_changing",
        "an_objective_asking_for_nothing_current_gets_a_reference_window")
require(recommended_policy("Research Foo Bar demand.", freshness="breaking") == "breaking", "explicit_caller_policy_is_preserved")

# Widening the window must not drop the requirement that currency is evidenced.
demand_subquestion = demand["subquestions"][0]
require(demand_subquestion["requires_current_evidence"] is True, "durable_window_still_requires_current_evidence")
require(plan_research("x demand", freshness="slow_changing")["max_source_age_days"] == 730, "durable_window_is_730_days")
require(plan_research("x demand", freshness="current")["max_source_age_days"] == 30, "current_window_is_30_days")

# --- a source kind is read from what the document declares about itself ----

for payload, expected in (
    ('{"@type":"ScholarlyArticle"}', "primary_data"),
    ('{"@type":"Dataset"}', "primary_data"),
    ('{"@type":"NewsArticle"}', "reputable_secondary"),
    ('{"@type":"DiscussionForumPosting"}', "community_experience"),
):
    require(_declared_source_kind(parse(ld_page(payload)).declared_types) == expected, f"declared_type_maps_to_kind_{expected}")

# A vendor blog declaring itself an article is exactly the case this must not promote.
WEAK_TYPES = ('{"@type":"Article"}', '{"@type":"BlogPosting"}', '{"@type":"WebPage"}', '{"@type":"Product"}')
require(
    all(_declared_source_kind(parse(ld_page(weak)).declared_types) == "" for weak in WEAK_TYPES),
    "weak_declared_types_are_not_promoted",
)

graph = parse(ld_page('{"@context":"https://schema.org","@graph":[{"@type":"WebSite"},{"@type":"NewsArticle","datePublished":"%s"}]}' % RECENT))
require(_declared_source_kind(graph.declared_types) == "reputable_secondary", "json_ld_graph_nesting_is_traversed")
require(RECENT in graph.publication_dates, "json_ld_graph_date_published_is_extracted")
og_page = parse('<html><head><meta property="og:type" content="DiscussionForumPosting"></head><body><p>x</p></body></html>')
require(_declared_source_kind(og_page.declared_types) == "community_experience", "open_graph_type_is_read")

malformed = parse(ld_page("{not valid json"))
require(malformed.declared_types == [], "malformed_json_ld_declares_no_type")
require("Creators report chasing payments" in " ".join(malformed.parts), "malformed_json_ld_does_not_lose_visible_text")

# --- the consequence, and the gate that must survive it --------------------

SURVEY = "https://www.gigapay.com/blog/survey-shows-87-of-creators-are-not-happy-with-how-they-are-paid"
VENDOR = "https://papercliphq.com/blog/how-to-manage-brand-deals-content-creator"


def supports_demand(url: str, kind: str) -> bool:
    return "demand" in (source_evidence_role({"public_url": url, "source_kind": kind}).get("supportable_dimensions") or [])


require(not supports_demand(SURVEY, "unknown"), "unknown_kind_supports_no_dimension")
require(supports_demand(SURVEY, "reputable_secondary"), "a_read_kind_lets_a_survey_support_demand")
require(supports_demand(SURVEY, "community_experience"), "community_experience_can_support_demand")
require(not supports_demand(VENDOR, "reputable_secondary"), "promotional_source_cannot_establish_demand")
require(not supports_demand(VENDOR, "unknown"), "promotional_source_stays_blocked_when_unknown")

print(json.dumps({"suite": "v2730.9.5-research-source-metadata", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
