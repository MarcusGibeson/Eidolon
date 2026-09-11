from __future__ import annotations

"""One unreadable page must be replaced, and a run must name why it observed nothing.

Four demand runs (2026-09-10 and 2026-09-11) died on a single Reddit thread that
served too little visible text. The draw was always the same shape: the main
demand query contributed nothing, the "site:reddit.com" discussion route
contributed three threads, the first was unreadable and the other two were
skipped as the same host. The one replacement search reused the failed page's
query terms - "site:reddit.com" included - so it could only return Reddit, and
every result was then discarded because Reddit was the host that had just failed.
With nothing observed the run raised source_failure_budget_exhausted, having
spent 1 of 12 allowed failures.

These checks replay that draw. The replacement must leave the failed host's
operator behind, a skipped page must also get its slot refilled, and a run that
observes nothing must say why - keeping the failure budget a real limit.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-9-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import (
    MAX_OBSERVATION_REPLACEMENTS,
    BoundedResearchSessionStore,
    _replacement_search_query,
    _zero_observation_failure_code,
    validate_read_only_adapter,
)
from bounded_research_history import sanitize_report
from conversational_research_actions import _research_report_message
from governed_public_web_research_adapter import PublicWebResearchError
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


OBJECTIVE = "Research creator sponsorship payment delays demand."
# The budget the failing live sessions ran with.
BUDGET = {"max_queries": 20, "max_candidates": 32, "max_observed_pages": 28,
          "max_source_failures": 12, "max_total_bytes": 4194304, "max_elapsed_seconds": 600}
BIAS = "survey study report respondents"
REDDIT = "www.reddit.com"
THREADS = [
    f"https://{REDDIT}/r/Twitch/comments/11bqajt/a_warning_about_streamelements_sponsorships/",
    f"https://{REDDIT}/r/Twitch/comments/17op1hg/sponsorships_my_experience/",
    f"https://{REDDIT}/r/Twitch/comments/oi2yca/streamelements_sponsorship_payment_time/",
]
READABLE = [f"https://survey{index}.example.org/creator-payments-study" for index in range(1, 5)]


# --- the replacement query leaves search operators behind -------------------

terms = "creator sponsorship payment delays demand problem complaints experience discussion site:reddit.com".split()
replacement = _replacement_search_query({"_evidence_terms": terms}, "demand")
require("site:" not in replacement, "a_replacement_query_drops_the_site_operator")
require(replacement.startswith("creator sponsorship payment delays demand"), "a_replacement_query_keeps_the_topic_terms")
require(replacement.endswith(BIAS), "a_replacement_query_keeps_the_dimension_bias")
for operator, label in (("-site:reddit.com", "negated_site"), ("inurl:forum", "inurl"),
                        ("filetype:pdf", "filetype"), ("SITE:Reddit.com", "uppercase_site")):
    require(operator.casefold() not in _replacement_search_query({"_evidence_terms": ["creator", operator]}, "").casefold(),
            f"a_replacement_query_drops_{label}_operators")
require(_replacement_search_query({"_evidence_terms": ["q3", "10:30", "results"]}, "") == "q3 10:30 results study report",
        "ordinary_terms_containing_a_colon_are_kept")


# --- replaying the failing draw ----------------------------------------------


class RedditDrawAdapter:
    """The main query comes back empty and the discussion route returns only Reddit."""

    def __init__(self, *, readable_replacements: bool = True) -> None:
        self.queries: list[str] = []
        self.attempted: list[str] = []
        self.observed: list[str] = []
        self.readable_replacements = readable_replacements

    def describe(self) -> dict[str, object]:
        return {
            "adapter_code": "reddit-draw-fixture", "read_only": True,
            "allowed_methods": ["GET", "HEAD"], "search_supported": True,
            "private_network_allowed": False, "redirect_revalidation_required": True,
            "credentials_allowed": False, "cookies_allowed": False, "uploads_allowed": False,
            "side_effects_allowed": False, "max_bytes_enforced": True, "timeout_enforced": True,
        }

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.queries.append(query)
        if "site:reddit.com" in query:
            # A real engine honours the operator: nothing but Reddit comes back.
            return [{"url": url, "source_kind": "community_experience"} for url in THREADS][:limit]
        if BIAS in query and self.readable_replacements:
            return [{"url": url, "source_kind": "reputable_secondary"} for url in READABLE][:limit]
        return []

    def observe(self, source_candidate, *, plan, max_bytes: int, timeout_seconds: float):
        url = str(source_candidate.get("public_url") or "")
        self.attempted.append(url)
        if REDDIT in url:
            raise PublicWebResearchError("public_web_demand_readable_content_unavailable")
        self.observed.append(url)
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION, "receipt_kind": "source_observation",
            "authoritative": True, "terminal": True, "operation_digest": "8" * 64,
            "terminal_result_digest": "9" * 64, "plan_digest": plan["plan_digest"],
            "source_observed": True, "source_candidate_digest": source_candidate["source_candidate_digest"],
            "claim_code": source_candidate.get("subquestion_id") or "rq1", "stance": "unknown",
            "evidence_digest": hashlib.sha256(url.encode()).hexdigest(),
            "citation_id": f"web-{hashlib.sha256(url.encode()).hexdigest()[:16]}",
            "source_kind": source_candidate["source_kind"], "quality_score": source_candidate["quality_score"],
            "freshness_known": True, "fresh_enough": True, "observed_bytes": min(512, max_bytes),
        }
        row["receipt_digest"] = digest(row)
        return row


def run(adapter, tag: str, *, objective: str = OBJECTIVE, budget: dict | None = None) -> dict:
    store = BoundedResearchSessionStore(RUNTIME)
    created = store.create_session(f"{tag}:create", objective=objective, budget=budget or BUDGET)
    session = created["result"]
    authorized = store.authorize_session(
        f"{tag}:auth", session_id=session["session_id"],
        session_digest=session["session_digest"], public_query_confirmed=True,
    )
    return store.execute_session(
        f"{tag}:exec", session_id=session["session_id"],
        authorization_digest=authorized["result"]["authorization_digest"], adapter=adapter,
    )


adapter = RedditDrawAdapter()
require(validate_read_only_adapter(adapter)["ok"], "reddit_draw_fixture_is_a_read_only_adapter")
result = run(adapter, "v2731-2-9-draw")
session_row = (result.get("result") or {}).get("session", {})
report = (result.get("result") or {}).get("report", {})

require(any("site:reddit.com" in q for q in adapter.queries), "the_replayed_draw_has_the_reddit_discussion_route")
require(adapter.attempted[:1] == THREADS[:1], "the_first_reddit_thread_is_attempted_first")
require(result.get("ok"), "one_unreadable_page_no_longer_ends_the_run")
require(session_row.get("state") == "completed" and not (result.get("result") or {}).get("failure_code"),
        "the_session_completes_without_a_failure_code")

replacements = [q for q in adapter.queries if BIAS in q]
require(replacements, "the_unreadable_page_triggers_a_replacement_search")
require(not any("site:" in q for q in replacements), "no_replacement_search_is_confined_to_the_failed_host")
require(adapter.observed and all("survey" in url for url in adapter.observed),
        "the_replacement_sources_are_the_ones_observed")
require(not any(REDDIT in url for url in adapter.observed), "the_failed_host_is_never_counted_as_observed")

require(int(session_row.get("source_failure_count") or 0) == 1, "an_unreadable_host_still_costs_exactly_one_failure")
require(int(report.get("skipped_unreadable_host_count") or 0) == 2, "both_other_threads_are_skipped_not_fetched")
require(len([url for url in adapter.attempted if REDDIT in url]) == 1, "no_second_request_goes_to_the_failed_host")
require(len(adapter.observed) == len(READABLE),
        "the_skipped_pages_get_their_slots_refilled_too")
require(len(replacements) == 1, "a_skipped_page_draws_on_the_same_replacement_search_without_repeating_it")
require(len(replacements) <= MAX_OBSERVATION_REPLACEMENTS, "replacement_searches_stay_within_their_cap")
require(int(session_row.get("query_count") or 0) <= BUDGET["max_queries"], "replacement_searches_respect_the_query_budget")
receipts = report.get("source_failure_receipts") or []
require(len(receipts) == 1 and receipts[0]["public_url"] == THREADS[0] and receipts[0]["reason"] == "insufficient_readable_text",
        "the_unreadable_thread_is_still_named_on_the_receipt")


# --- a run that observes nothing says why ------------------------------------

blind = RedditDrawAdapter(readable_replacements=False)
failed = run(blind, "v2731-2-9-blind")
failed_report = (failed.get("result") or {}).get("report", {})
require(not failed.get("ok") and failed.get("status") == "bounded_research_failed_safely",
        "a_run_that_reads_nothing_still_fails")
require((failed.get("result") or {}).get("failure_code") == "no_readable_source_observed",
        "a_run_that_found_only_unreadable_sources_says_so")
require((failed.get("result") or {}).get("failure_code") != "source_failure_budget_exhausted",
        "an_unspent_failure_budget_is_not_reported_as_exhausted")
require(int(failed_report.get("source_failure_count") or 0) == 1, "the_unread_run_spent_one_failure_of_twelve")
require(failed_report.get("collection_stop_reason") == "no_readable_source_observed",
        "the_report_stop_reason_names_the_real_cause")
require(sanitize_report(failed_report).get("collection_stop_reason") == "no_readable_source_observed",
        "history_keeps_the_new_stop_reason")
require("no source found could be read" in _research_report_message({}, failed_report),
        "the_chat_message_names_the_real_cause")


class EveryHostUnreadable(RedditDrawAdapter):
    """Each page is on its own host and none can be read, so every attempt fails."""

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.queries.append(query)
        return [{"url": f"https://host{len(self.queries)}-{index}.example.net/thread", "source_kind": "unknown"}
                for index in range(3)][:limit]

    def observe(self, source_candidate, *, plan, max_bytes: int, timeout_seconds: float):
        self.attempted.append(str(source_candidate.get("public_url") or ""))
        raise PublicWebResearchError("public_web_demand_readable_content_unavailable")


exhausting = EveryHostUnreadable()
exhausted = run(exhausting, "v2731-2-9-exhausted", budget={**BUDGET, "max_source_failures": 2})
exhausted_report = (exhausted.get("result") or {}).get("report", {})
require(not exhausted.get("ok"), "a_genuinely_exhausted_budget_still_fails_the_run")
require((exhausted.get("result") or {}).get("failure_code") == "source_failure_budget_exhausted",
        "a_genuinely_exhausted_budget_keeps_its_failure_code")
require(exhausted_report.get("collection_stop_reason") == "source_failure_budget_reached",
        "a_genuinely_exhausted_budget_keeps_its_stop_reason")
require(len(exhausting.attempted) == 2, "no_fetch_starts_after_the_failure_budget_is_spent")

table = {
    (12, 12, 3, 0): "source_failure_budget_exhausted",
    (1, 12, 3, 0): "no_readable_source_observed",
    (1, 12, 0, 1): "search_results_unavailable",
    (0, 12, 0, 0): "no_search_results",
}
for (failures, maximum, candidate_count, search_failures), expected in table.items():
    require(_zero_observation_failure_code(source_failure_count=failures, max_source_failures=maximum,
                                           candidate_count=candidate_count, search_failure_count=search_failures) == expected,
            f"zero_observation_code_{expected}")

print(json.dumps({"suite": "v2731.2.9-unreadable-source-replacement", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
