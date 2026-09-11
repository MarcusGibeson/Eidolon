from __future__ import annotations

"""A vendor's own explainer is not independent customer evidence.

Once the summary-prompt fix removed the wording mismatches that had been
refusing it, the demand objective ("creator sponsorship payment delays") was
admitted as a model-assessed inference on two publishers: a Campaign trade-press
article and spark.money. Spark sells stablecoin payment rails; the cited page is
an explainer on why creator payouts are slow that presents Spark as the fix and
discloses no method. It counted as third-party customer evidence because
first-partyness is decided against the objective, and the objective never names
Spark.

Publisher identity is not evidence independence. The adapter now records, as a
fixed code, whether a page presents its own publisher as the provider of
something and whether it discloses a method. For demand evidence:

  - the report-only policy fails evidence_producer_independent for such a page,
    unless it is the first party stating its own operational facts;
  - the live demand gate sets it aside, like a stale source, so it neither
    refuses a finding whose other citations qualify nor counts toward the two
    independent publishers;
  - selection still offers it to synthesis: it is context, just not support.

Measured before it was written, through the adapter's own parser, on the pages
the stored demand runs had observed plus independent controls: it caught Spark,
all three CreaSeed pages and Stripe's pricing page (first party, so still valid
for Stripe's own fees), and fired on none of Campaign, MediaBrief, two LinkedIn
posts, Wikipedia, PMC, the Python docs, discuss.python.org or SciTechDaily. A
looser first draft fired on "Stripe support", "Python Help" and "with
MediaBrief, <name>"; matching verb positions only fixed all three. It cannot see
a vendor that never names itself as the provider - hashtagpaid, nowfluence and
contentcreatorsaccountant among the corpus pages - and this suite pins that limit
rather than hiding it.

The two-publisher threshold and every other demand rule are unchanged.
"""

import hashlib
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-6-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import governed_public_web_research_adapter as adapter_module
from bounded_autonomous_web_research import (
    BoundedResearchSessionStore,
    _evaluate_evidence_policy,
    _select_citable_evidence,
)
from bounded_research_history import sanitize_report
from bounded_research_reasoning import extract_claim_evidence
from research_claim_assessment import assess_source_claims, model_assessed_conclusion
from research_evidence_policy import CONTEXT_PRESERVING_CONDITIONS, DEMAND_EVIDENCE_POLICY
from research_source_classification import classify_source_kind
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION, _validated_native_receipt


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def page(title: str, *paragraphs: str) -> str:
    body = "".join(f"<p>{text}</p>" for text in paragraphs)
    return f"<html><head><title>{title}</title></head><body><article>{body}</article></body></html>"


def signal(url: str, html: str) -> str:
    """The code the adapter records, computed from exactly the text it reads."""
    parser = adapter_module._VisibleTextParser()
    parser.feed(html)
    parser.close()
    return adapter_module._evidence_producer_signal(url, adapter_module._clean(" ".join(parser.parts), 500_000))


# Pages shaped like the corpus pages, in paraphrase.
SPARK_URL = "https://www.spark.money/research/creator-economy-payments"
SPARK_LINES = ("Creators on the largest platforms commonly wait thirty to forty-five days for a payout.",
               "Cross-border transfers can cost creators several percent of their earnings in fees.",
               "Spark, a Bitcoin layer two network, supports instant dollar stablecoin payouts with no minimum.")
SPARK_PAGE = page("Creator Economy Payments: Why Payouts Are Slow | Spark", *SPARK_LINES)
SPARK_SURVEY_PAGE = page("Creator Economy Payments | Spark", *SPARK_LINES,
                         "We surveyed 1,200 creators in March 2026 about how long their last payout took.")
CAMPAIGN_URL = "https://www.campaignlive.com/article/new-campaign-report-reveals-why-creators-arent-getting-paid-time/1930824"
CAMPAIGN_PAGE = page("Why creators still are not paid on time | Campaign US",
                     "Late payment is often the norm rather than the exception for creators.",
                     "Most creators have been paid late at least once, according to payment platforms such as "
                     "Tipalti and Lumanu.")
MEDIABRIEF_URL = "https://mediabrief.com/exclusive-decoding-the-influencer-marketing-payment-problem/"
MEDIABRIEF_PAGE = page("Leaders decode the influencer payment problem | Mediabrief.com",
                       "In an interaction with MediaBrief, the co-founder of a creator agency said brand payments "
                       "routinely slip past sixty days.")
FORUM_URL = "https://discuss.python.org/"
FORUM_PAGE = page("Discussions on Python.org", "Python Help: general help and discussion about Python.",
                  "Ideas: discussion of possible new features for Python.")
STRIPE_URL = "https://stripe.com/pricing"
STRIPE_PAGE = page("Pricing and fees | Stripe", "2.9% plus 30 cents per successful domestic card charge.",
                   "Stripe handles pricing for your users in their local currency.")
HASHTAG_URL = "https://hashtagpaid.com/banknotes/creator-first-is-an-industry-buzzword-but-creators-are-still-chasing-down-payments"
HASHTAG_PAGE = page("Creators are still chasing down payments",
                    "Brands call themselves creator-first while creators wait months to be paid.")

# --- the detector, on the text the adapter actually reads -----------------------

require(signal(SPARK_URL, SPARK_PAGE) == "self_promoting_publisher", "a_vendor_presenting_its_own_offering_is_marked")
require(signal(SPARK_URL, SPARK_SURVEY_PAGE) == "self_promoting_publisher_with_methodology",
        "a_vendor_that_discloses_a_method_is_marked_separately")
require(signal(SPARK_URL, page("Payouts | Spark", *SPARK_LINES, "Published March 2026.",
                               "According to industry estimates, creators lose several percent to fees."))
        == "self_promoting_publisher", "a_byline_or_an_attribution_is_not_a_disclosed_method")
require(signal(CAMPAIGN_URL, CAMPAIGN_PAGE) == "none", "trade_press_naming_other_vendors_is_not_self_promotion")
require(signal(MEDIABRIEF_URL, MEDIABRIEF_PAGE) == "none", "interview_framing_naming_the_publisher_is_not_an_offer")
require(signal(FORUM_URL, FORUM_PAGE) == "none", "a_forum_category_name_is_not_an_offer")
require(signal(STRIPE_URL, page("Help | Stripe", "Contact Stripe support with billing questions.")) == "none",
        "a_support_noun_is_not_an_offer")
require(signal(STRIPE_URL, STRIPE_PAGE) == "self_promoting_publisher",
        "a_vendor_pricing_page_is_marked_as_presenting_its_own_offering")
require(signal(HASHTAG_URL, HASHTAG_PAGE) == "none", "known_limit_a_vendor_that_never_names_itself_is_not_detected")
require(signal("https://hbr.org/2026/creators", page("HBR", "HBR helps managers.")) == "none",
        "a_publisher_name_too_short_to_be_distinctive_is_not_matched")

# --- the real observation step records it, as a code inside a signed receipt ---


class FixtureFetchAdapter(adapter_module.GovernedPublicWebResearchAdapter):
    """The real adapter with the network replaced by fixture pages."""

    pages: dict[str, str] = {SPARK_URL: SPARK_PAGE, CAMPAIGN_URL: CAMPAIGN_PAGE}

    def _fetch(self, url: str, *, max_bytes: int, timeout_seconds: float) -> dict:
        body = self.pages[url].encode("utf-8")
        return {"public_url": url, "body": body, "content_type": "text/html",
                "content_digest": hashlib.sha256(body).hexdigest(), "observed_bytes": len(body), "redirect_count": 0}


PLAN = {"plan_digest": "a" * 64, "freshness_policy": "current",
        "subquestions": [{"subquestion_id": "rq1", "evidence_dimension": "demand"}]}


def observed(url: str, candidate_digest: str) -> dict:
    return FixtureFetchAdapter().observe(
        {"public_url": url, "source_candidate_digest": candidate_digest, "subquestion_id": "rq1",
         "_evidence_terms": ["creator", "payout", "payment"], "evidence_dimension": "demand", "source_kind": "unknown"},
        plan=PLAN, max_bytes=65_536, timeout_seconds=10)


spark_receipt, campaign_receipt = observed(SPARK_URL, "b" * 64), observed(CAMPAIGN_URL, "c" * 64)
require(spark_receipt.get("evidence_producer_signal") == "self_promoting_publisher",
        "the_real_observation_step_records_the_signal")
require(campaign_receipt.get("evidence_producer_signal") == "none", "and_records_none_for_an_independent_page")
require(_validated_native_receipt(spark_receipt, "source_observation") is not None,
        "the_signed_receipt_still_validates_with_the_signal_in_it")
require("stablecoin" not in json.dumps(spark_receipt), "the_receipt_carries_a_code_never_page_text")

extraction = extract_claim_evidence(plan_digest=PLAN["plan_digest"], observations=[spark_receipt, campaign_receipt],
                                    citation_context={})
carried = {row.get("citation_id"): row.get("evidence_producer_signal") for row in extraction.get("evidence") or []}
require(carried.get(spark_receipt["citation_id"]) == "self_promoting_publisher"
        and carried.get(campaign_receipt["citation_id"]) == "none",
        "evidence_extraction_carries_the_signal_forward")

# --- the report-only policy, through the wrapper the research run uses ---------

DEMAND = "Research creator sponsorship payment delays demand."
CLAIM = "Creators report sponsorship payments arriving weeks after the agreed date."


def live_row(cid: str, url: str, producer: str = "none") -> dict:
    host = url.split("/")[2]
    return {"citation_id": cid, "public_url": url, "host": host, "source_kind": classify_source_kind(url),
            "freshness": "fresh", "quality_score": 0.5, "relevance_score": 1.0, "source_digest": "",
            "candidate_digest": "", "evidence_dimension": "demand", "stance": "unknown",
            "evidence_producer_signal": producer, "source_identity_digest": "", "canonical_page_digest": "",
            "publisher_digest": hashlib.sha256(host.removeprefix("www.").encode()).hexdigest(),
            "explicit_origin_digest": "", "attribution_digest": "", "content_similarity_digest": "",
            "content_similarity_confidence": ""}


def evaluate(rows: list[dict], *, objective: str = DEMAND, claim: str = CLAIM) -> dict:
    finding = {"title": "Payment delays", "summary": claim, "citation_ids": [row["citation_id"] for row in rows],
               "uncertainties": ["Bounded evidence."]}
    payload = {"findings": [finding], "source_assessments": [
        {"citation_id": row["citation_id"], "claim": claim, "passage_index": 1, "assessment": "supports",
         "evidence_kind": "customer_experience", "dimension": "demand"} for row in rows]}
    documents = [{"citation_id": row["citation_id"],
                  "excerpt": f"Account {index}: creators describe sponsorship payments arriving weeks after the agreed date."}
                 for index, row in enumerate(rows, 1)]
    summary = assess_source_claims(payload, documents=documents, citations=rows, required_dimension="demand")
    require(summary.get("grounded_assessment_count") == len(rows), "every_assessment_was_really_grounded")
    CHECKS.pop()
    result = _evaluate_evidence_policy(payload={"findings": [finding]}, citations=rows, assessment_summary=summary,
                                       currency_requirement="demand_current", objective=objective)
    require(result.get("policy_code") == "demand", "the_wrapper_returned_a_real_demand_evaluation")
    CHECKS.pop()
    return result


campaign = live_row("web-campaign", CAMPAIGN_URL)
spark = live_row("web-spark", SPARK_URL, "self_promoting_publisher")

regression = evaluate([campaign, spark])
require((regression["citation_condition_failures"] or {}).get("evidence_producer_independent") == 1,
        "the_vendor_page_fails_evidence_producer_independent")
require(regression["independent_publisher_count"] == 1 and "independent_publishers" in regression["finding_condition_failures"],
        "so_the_finding_no_longer_has_two_independent_publishers")
require(regression["would_admit"] is False, "the_spark_regression_is_not_admitted")
require(regression["producer_signal_judged_count"] == 2 and regression["self_promoting_publisher_count"] == 1,
        "the_receipt_says_both_sources_were_judged_and_one_was_a_self_promoting_publisher")

control = evaluate([campaign, live_row("web-spark", SPARK_URL, "none")])
require(control["would_admit"] is True, "the_same_pair_without_the_signal_is_admitted_as_it_was_live")
with_method = evaluate([campaign, live_row("web-spark", SPARK_URL, "self_promoting_publisher_with_methodology")])
require(with_method["would_admit"] is True, "a_vendor_that_discloses_its_method_can_still_count")
unjudged = evaluate([campaign, live_row("web-spark", SPARK_URL, "")])
require(unjudged["producer_signal_judged_count"] == 1, "a_source_without_a_signal_is_reported_as_unjudged")

# A vendor is still the record of its own prices, even while presenting itself.
stripe = live_row("web-stripe", STRIPE_URL, "self_promoting_publisher")
fees = evaluate([stripe, campaign], objective="Research Stripe payment fee demand.",
                claim="Stripe charges 2.9% plus 30 cents per successful card transaction.")
require("first_party_operational_fact" in fees["claim_source_relationships"],
        "stripe_is_first_party_for_its_own_fees")
require("evidence_producer_independent" not in (fees["citation_condition_failures"] or {}),
        "a_first_party_operational_fact_is_not_refused_for_self_promotion")
third_party_stripe = evaluate([stripe, campaign])
require((third_party_stripe["citation_condition_failures"] or {}).get("evidence_producer_independent") == 1,
        "the_same_page_is_not_independent_customer_evidence_about_someone_elses_market")

# --- selection keeps it as context -----------------------------------------------

require(CONTEXT_PRESERVING_CONDITIONS <= set(DEMAND_EVIDENCE_POLICY.citation_conditions),
        "the_demand_policy_carries_the_condition")
selection = _select_citable_evidence(citations=[campaign, spark], currency_requirement="demand_current", objective=DEMAND)
require("web-spark" in (selection.get("citable_ids") or []), "selection_still_offers_the_vendor_page_as_context")
require(selection.get("context_conditions_deferred") == ["evidence_producer_independent"],
        "and_says_the_condition_was_left_to_the_verdict")
require("evidence_producer_independent" not in (selection.get("withheld_condition_counts") or {}),
        "nothing_was_withheld_for_it")

# --- the live demand gate sets it aside rather than counting it -----------------

GATE_DIGEST = hashlib.sha256(CLAIM.encode()).hexdigest()


def gate_row(cid: str, host: str, producer: str = "none") -> dict:
    return {"citation_id": cid, "public_url": f"https://{host}/creator-payments", "host": host,
            "source_kind": "reputable_secondary", "freshness": "fresh", "stance": "unknown",
            "relevance_score": 1.0, "quality_score": 0.82, "evidence_producer_signal": producer,
            "publisher_digest": hashlib.sha256(host.encode()).hexdigest()}


def gate(rows: list[dict]) -> dict:
    ids = [row["citation_id"] for row in rows]
    assessments = [{"citation_id": cid, "claim_digest": GATE_DIGEST, "assessed_dimension": "demand",
                    "model_assessment": "supports", "model_evidence_kind": "customer_experience",
                    "passage_digest": hashlib.sha256(cid.encode()).hexdigest(), "textual_provenance_verified": True}
                   for cid in ids]
    payload = {"findings": [{"title": "Payment delays", "summary": CLAIM, "citation_ids": ids,
                             "uncertainties": ["Bounded evidence."]}]}
    return model_assessed_conclusion(payload, assessment_summary={"assessments": assessments,
                                                                  "rejected_assessment_counts": {}},
                                     citations=rows, dimension="demand")


pair = gate([gate_row("web-1", "campaignlive.com"), gate_row("web-2", "spark.money", "self_promoting_publisher")])
require(pair.get("ok") is False and pair.get("denial_reason") == "insufficient_distinct_publishers",
        "the_gate_refuses_the_spark_pair_for_want_of_a_second_independent_publisher")
require(gate([gate_row("web-1", "campaignlive.com"), gate_row("web-2", "spark.money")]).get("ok") is True,
        "without_the_signal_the_gate_admits_the_same_pair_as_it_did_live")
require(gate([gate_row("web-1", "campaignlive.com"),
              gate_row("web-2", "spark.money", "self_promoting_publisher_with_methodology")]).get("ok") is True,
        "the_gate_counts_a_vendor_that_discloses_its_method")

three = gate([gate_row("web-1", "campaignlive.com"), gate_row("web-2", "mediabrief.com"),
              gate_row("web-3", "spark.money", "self_promoting_publisher")])
require(three.get("ok") is True, "two_independent_publishers_still_admit_with_a_vendor_page_cited_beside_them")
inference = three["reasonable_inferences"][0]
require(inference.get("set_aside_vendor_citations") == ["web-3"], "the_vendor_page_is_recorded_as_set_aside")
require("web-3" not in inference.get("citations", []), "and_is_not_counted_as_support")
require(any("vendor presenting its own offering" in text for text in three.get("limitations", [])),
        "the_reader_is_told_a_vendor_page_was_set_aside")

# --- end to end: the Spark regression through the real research run ---------------

BUDGET = {"max_queries": 3, "max_candidates": 8, "max_observed_pages": 5, "max_total_bytes": 65_536,
          "max_elapsed_seconds": 120, "max_source_failures": 3}
EXCERPTS = {CAMPAIGN_URL: "Trade reporting describes creators waiting weeks after the agreed date for sponsorship payments.",
            SPARK_URL: "Creators describe sponsorship payments that routinely arrive weeks after the agreed date."}


class DemandRegressionAdapter:
    """Campaign and Spark, as the stored demand run observed them."""

    def __init__(self, spark_signal: str) -> None:
        self.spark_signal = spark_signal
        self.search_calls = 0
        self.urls: dict[str, str] = {}
        self.offered_ids: list[str] = []

    def describe(self) -> dict[str, object]:
        return {"adapter_code": "v2731.2.6-evidence-producer-fixture", "read_only": True,
                "allowed_methods": ["GET", "HEAD"], "search_supported": True,
                "private_network_allowed": False, "redirect_revalidation_required": True,
                "credentials_allowed": False, "cookies_allowed": False, "uploads_allowed": False,
                "side_effects_allowed": False, "max_bytes_enforced": True, "timeout_enforced": True}

    def search(self, query: str, *, limit: int, timeout_seconds: float) -> list[dict[str, object]]:
        self.search_calls += 1
        if self.search_calls > 1:
            return []
        return [{"url": url, "source_kind": "unknown", "fetched_at": "2026-09-10T00:00:00+00:00"}
                for url in (CAMPAIGN_URL, SPARK_URL)][:limit]

    def observe(self, candidate: dict[str, object], *, plan: dict[str, object], max_bytes: int,
                timeout_seconds: float) -> dict[str, object]:
        url = str(candidate.get("public_url") or candidate.get("url") or "")
        cid = "web-" + hashlib.sha256(url.encode()).hexdigest()[:16]
        self.urls[cid] = url
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION, "receipt_kind": "source_observation",
            "authoritative": True, "terminal": True,
            "operation_digest": digest({"operation": cid}), "terminal_result_digest": digest({"terminal": cid}),
            "source_observed": True, "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"), "stance": "unknown",
            "evidence_digest": digest({"evidence": cid}), "citation_id": cid,
            "source_kind": candidate.get("source_kind", "unknown"), "quality_score": 0.5,
            "freshness_known": True, "fresh_enough": True, "relevance_score": 0.85,
            "observed_bytes": min(512, max_bytes), "public_url": url,
            "evidence_producer_signal": self.spark_signal if url == SPARK_URL else "none",
        }
        row["receipt_digest"] = digest(row)
        return row

    def synthesize(self, *, decomposition, citations, **kwargs) -> dict[str, object]:
        rows = [dict(row) for row in citations]
        self.offered_ids = [str(row["citation_id"]) for row in rows]
        by_url = {self.urls[cid]: cid for cid in self.offered_ids}
        # The model cites the trade article; completion adds the grounded vendor
        # page, exactly as the live run went from one citation to two.
        finding = {"title": "Payment delays", "summary": CLAIM, "citation_ids": [by_url[CAMPAIGN_URL]],
                   "uncertainties": ["Accounts describe delays; how common they are is not measured."]}
        assessed = {"findings": [finding], "source_assessments": [
            {"citation_id": cid, "claim": CLAIM, "passage_index": 1, "assessment": "supports",
             "evidence_kind": "customer_experience", "dimension": "demand"} for cid in self.offered_ids]}
        summary = assess_source_claims(assessed, documents=[{"citation_id": cid, "excerpt": EXCERPTS[self.urls[cid]]}
                                                            for cid in self.offered_ids],
                                       citations=rows, required_dimension="demand")
        return {"ok": True, "status": "research_synthesis_ready",
                "payload": {"findings": [finding], "limitations": ["Fixture evidence only."]},
                "source_assessment_summary": summary, "provider_contacted": False, "provider_request_count": 0}


def run(spark_signal: str, label: str) -> tuple[dict, DemandRegressionAdapter]:
    store = BoundedResearchSessionStore(RUNTIME / label)
    adapter = DemandRegressionAdapter(spark_signal)
    created = store.create_session(f"create-{label}", objective=DEMAND, budget=BUDGET)
    require(created["ok"], f"{label}_session_created")
    session = created["result"]
    authorized = store.authorize_session(f"authorize-{label}", session_id=session["session_id"],
                                         session_digest=session["session_digest"], public_query_confirmed=True)
    require(authorized["ok"], f"{label}_session_authorized")
    executed = store.execute_session(f"execute-{label}", session_id=session["session_id"],
                                     authorization_digest=authorized["result"]["authorization_digest"],
                                     adapter=adapter)
    require(executed["ok"], f"{label}_session_completes")
    return executed["result"]["report"], adapter


report, adapter = run("self_promoting_publisher", "vendor")
spark_cid = next(cid for cid, url in adapter.urls.items() if url == SPARK_URL)
require(spark_cid in adapter.offered_ids, "the_run_offered_the_vendor_page_to_synthesis_as_context")
policy = report.get("evidence_policy_evaluation") or {}
require(policy.get("policy_code") == "demand", "the_run_evaluated_the_demand_policy")
require((policy.get("citation_condition_failures") or {}).get("evidence_producer_independent") == 1,
        "the_run_failed_the_vendor_page_on_evidence_producer_independent")
require(policy.get("would_admit") is False and "independent_publishers" in (policy.get("finding_condition_failures") or []),
        "the_run_no_longer_admits_on_one_independent_publisher")
require(policy.get("producer_signal_judged_count") == 2 and policy.get("self_promoting_publisher_count") == 1,
        "the_signal_reached_the_policy_through_the_live_row_path")
require(report.get("model_assessment_denial_reason") == "insufficient_distinct_publishers",
        "the_live_gate_refused_it_for_want_of_a_second_independent_publisher")
require(report.get("synthesis_status") != "research_model_assessed_inference", "no_inference_was_admitted")
indexed = {row.get("citation_id"): row for row in report.get("citations") or []}
require(indexed.get(spark_cid, {}).get("evidence_producer_signal") == "self_promoting_publisher",
        "the_vendor_page_stays_observable_in_the_report")

persisted = sanitize_report(report)
persisted_index = {row.get("citation_id"): row for row in persisted.get("citations") or []}
require(persisted_index.get(spark_cid, {}).get("evidence_producer_signal") == "self_promoting_publisher",
        "the_signal_survives_persistence_on_the_citation")
require(persisted["evidence_policy_evaluation"]["self_promoting_publisher_count"] == 1,
        "the_count_survives_persistence")
require(persisted["evidence_policy_evaluation"]["source_selection"]["context_conditions_deferred"]
        == ["evidence_producer_independent"], "the_selection_deferral_survives_persistence")

control, _control_adapter = run("none", "control")
control_policy = control.get("evidence_policy_evaluation") or {}
require(control.get("synthesis_status") == "research_model_assessed_inference",
        "without_the_signal_the_run_admits_the_inference_as_the_live_run_did")
require(control_policy.get("would_admit") is True and control_policy.get("independent_publisher_count") == 2,
        "and_the_policy_counts_two_independent_publishers")

print(json.dumps({"suite": "v2731.2.6-evidence-producer-independence", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
