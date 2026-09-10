from __future__ import annotations

"""A page cannot make itself authoritative by saying so.

After the finding-level evaluation fix, four of the thirteen sources cited across
the seven-domain corpus had their authority set by the page's own markup rather
than by any structural rule. The adapter mapped a self-declared schema.org type
to a source kind whenever the URL rules left a page unclassified:

    axis-intelligence.com   declares "Dataset"      -> primary_data, quality 0.95
    scitechdaily.com        declares "NewsArticle"  -> reputable_secondary

The science finding was admitted on scitechdaily alone because of that
promotion. The current-event refusal survived the other one only because its
negative enforcement claim needs two publishers whatever the tier; an ordinary
claim from the same page would have stood on its own word.

That is the document-form versus publisher-authority confusion a third time,
after documentation mirrors and path-named /pricing roles. A declared type now
names the page's form and grants nothing. The same holds for a "/dataset" path.

Nothing about the evidence policy's conditions changes. These checks pin where
authority is allowed to come from.
"""

import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-1-2-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import governed_public_web_research_adapter as adapter
from bounded_autonomous_web_research import _inferred_source_kind
from research_evidence_policy import (
    CURRENT_EVIDENCE_POLICY,
    REFERENCE_EVIDENCE_POLICY,
    TIER_UNCLASSIFIED,
    evaluate_policy,
    source_authority_tier,
)
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def parse(html: str) -> adapter._VisibleTextParser:
    parser = adapter._VisibleTextParser()
    parser.feed(html)
    parser.close()
    return parser


def ld(types: str) -> str:
    return (f'<html><head><script type="application/ld+json">{{"@graph":[{types}]}}</script></head>'
            "<body><p>Body.</p></body></html>")


# --- the pages from the corpus, as they actually declare themselves ----------

# axis-intelligence.com's real JSON-LD declared all of these; "dataset" was the
# one that made it primary data.
axis = parse(ld('{"@type":"Article"},{"@type":"Dataset"},{"@type":"Person"},{"@type":"WebPage"},'
                '{"@type":"Organization"},{"@type":"NewsMediaOrganization"}'))
require(adapter._declared_document_form(axis.declared_types) == "news_article"
        or adapter._declared_document_form(axis.declared_types) == "dataset",
        "a_self_declared_dataset_is_still_read_as_a_form")
scitech = parse(ld('{"@type":"Person"},{"@type":"WebSite"},{"@type":"WebPage"},{"@type":"NewsArticle"}'))
require(adapter._declared_document_form(scitech.declared_types) == "news_article",
        "a_self_declared_news_article_is_read_as_a_form")

# --- a declared type grants no authority -------------------------------------

require(not hasattr(adapter, "_DECLARED_TYPE_SOURCE_KINDS"), "there_is_no_declared_type_to_authority_table")
require(not hasattr(adapter, "_declared_source_kind"), "there_is_no_declared_type_to_authority_function")
forms = set(adapter._DECLARED_TYPE_DOCUMENT_FORMS.values())
KINDS = {"primary_official", "primary_data", "reputable_secondary", "specialist_secondary", "community_experience"}
require(not forms & KINDS, "a_declared_form_is_never_a_source_kind")

# The observation path must not consult the declared type when setting the kind.
# A source-level guard, because the promotion lived in four lines that are easy to
# restore by accident and would silently re-open the hole.
observe_source = Path(adapter.__file__).read_text(encoding="utf-8")
require("source_kind = declared" not in observe_source and "declared_kind" not in observe_source,
        "the_observation_path_never_sets_a_kind_from_a_declaration")

# --- a path grants no authority either ---------------------------------------

for url in ("https://axis-intelligence.com/dataset/eu-ai-act",
            "https://blog.example.com/data/creator-payments",
            "https://vendor.example.net/datasets/market-size"):
    require(_inferred_source_kind(url, "unknown") == "unknown", "a_data_path_does_not_make_a_host_primary")
    CHECKS.pop()
CHECKS.append("no_data_path_makes_an_unknown_host_primary")

# Genuine data publishers are still recognised - by their host, not their path.
for url, expected in (("https://data.census.gov/table", "primary_official"),
                      ("https://cs.example.edu/research/dataset", "primary_data"),
                      ("https://zenodo.org/records/123", "primary_data"),
                      ("https://www.g2.com/products/stripe/reviews", "specialist_secondary")):
    require(_inferred_source_kind(url, "unknown") == expected, "a_structural_host_rule_still_classifies")
    CHECKS.pop()
CHECKS.append("structural_host_rules_still_classify_real_publishers")

# A kind supplied by an earlier structural stage is still respected.
require(_inferred_source_kind("https://blog.example.com/a", "reputable_secondary") == "reputable_secondary",
        "an_already_classified_kind_is_kept")

# --- the corpus consequences --------------------------------------------------

def cite(cid: str, url: str, *, freshness="fresh") -> dict:
    return {"citation_id": cid, "public_url": url, "canonical_url": url,
            "source_kind": classify_source_kind(url), "evidence_role": "independent_analysis",
            "freshness": freshness, "freshness_known": True, "fresh_enough": True,
            "relevance_score": 1.0, "publisher_digest": f"pub-{url.split('/')[2]}"}


def finding(summary: str, ids=("web-1",)) -> dict:
    return {"title": "T", "summary": summary, "citation_ids": list(ids), "uncertainties": ["Bounded evidence."]}


scitech_row = cite("web-1", "https://scitechdaily.com/researchers-discover-mrna-vaccines-leave-lasting-mark-on-the-immune-system/")
require(source_authority_tier(scitech_row) == TIER_UNCLASSIFIED,
        "a_popular_science_site_is_unclassified_without_its_self_declaration")
science = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                          finding=finding("mRNA vaccines produce spike-specific antibodies and T cells."),
                          citations=[scitech_row],
                          objective="Research how mRNA vaccines produce an immune response")
require(not science["would_admit"], "a_lone_unclassified_science_article_cannot_carry_a_finding")
require("corroboration_satisfied" in science["finding_condition_failures"],
        "and_it_fails_for_want_of_corroboration_not_authority")

axis_row = cite("web-1", "https://axis-intelligence.com/eu-ai-act-compliance-tracker/")
require(source_authority_tier(axis_row) == TIER_UNCLASSIFIED,
        "a_compliance_blog_is_unclassified_without_its_self_declaration")
ordinary = evaluate_policy(CURRENT_EVIDENCE_POLICY,
                           finding=finding("The EU AI Act entered into force in August 2024."),
                           citations=[axis_row],
                           objective="Research the current state of EU AI Act enforcement")
require(ordinary["required_publisher_count"] == 2,
        "an_ordinary_claim_from_that_blog_now_needs_corroboration")
require(not ordinary["would_admit"], "so_it_no_longer_stands_on_its_own_word")

# A real scholarly source is still authoritative, because its host says so.
pmc_row = cite("web-1", "https://pmc.ncbi.nlm.nih.gov/articles/PMC8404899/")
require(source_authority_tier(pmc_row) == "primary", "a_pmc_article_is_primary_by_its_host")
pmc = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                      finding=finding("mRNA vaccines produce spike-specific antibodies and T cells."),
                      citations=[pmc_row],
                      objective="Research how mRNA vaccines produce an immune response")
require(pmc["would_admit"], "a_dated_pmc_article_settles_a_reference_science_question")

print(json.dumps({"suite": "v2731.1.2-declared-type-authority", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
