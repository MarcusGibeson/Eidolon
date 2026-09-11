from __future__ import annotations

"""A page that is not a results page is a failed search, not an empty one.

Four runs (asyncio, mRNA, and two 1929-crash objectives) each issued one query,
got zero candidates and zero failures, and finished in a second or two as
"planned collection finished". A live probe on 2026-09-11 found the search
endpoint returns 30 results for that very query, and 27 even for nonsense
words, so it essentially never answers "nothing matched". The adapter was
reading a 200 response with no result links - a challenge, interstitial or
blank page - as an honest empty result.

These checks cover telling a results page from a non-results page, pausing
before the next search, retrying that one failure once, and ending a run that
found nothing as a failure that says why, instead of as a finished collection.
"""

import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-0-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import BoundedResearchSessionStore, validate_read_only_adapter
from bounded_research_history import sanitize_report
from conversational_research_actions import _research_report_message
from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter, PublicWebResearchError
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


# --- transport fixtures, as in the v2501.1 adapter suite ---------------------


def resolver(host: str, port: int, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


class FakeCookies:
    def clear(self) -> None:
        pass


class FakeRaw:
    class _Connection:
        class _Socket:
            def getpeername(self):
                return ("93.184.216.34", 443)

        sock = _Socket()

    _connection = _Connection()


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.status_code = 200
        self.headers = {"Content-Type": "text/html", "Content-Length": str(len(body))}
        self.raw = FakeRaw()

    def iter_content(self, chunk_size: int):
        yield self.body


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.cookies = FakeCookies()
        self.trust_env = True

    def get(self, url: str, **kwargs):
        return self.response

    def close(self) -> None:
        pass


class FakeFactory:
    def __init__(self, *bodies: bytes) -> None:
        self.bodies = list(bodies)
        self.requests = 0

    def __call__(self) -> FakeSession:
        if not self.bodies:
            raise AssertionError("fixture response exhausted")
        self.requests += 1
        return FakeSession(FakeResponse(self.bodies.pop(0)))


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def adapter_for(*bodies: bytes, clock: FakeClock | None = None) -> GovernedPublicWebResearchAdapter:
    kwargs = {"clock": clock, "sleeper": clock.sleep} if clock else {"sleeper": lambda seconds: None}
    return GovernedPublicWebResearchAdapter(resolver=resolver, session_factory=FakeFactory(*bodies), **kwargs)


def raised_code(adapter: GovernedPublicWebResearchAdapter, query: str = "causes 1929 stock market crash") -> str:
    try:
        adapter.search(query, limit=10, timeout_seconds=5)
    except PublicWebResearchError as error:
        return error.code
    return ""


# The markup the live endpoint served on 2026-09-11, reduced to its structure.
RESULTS_PAGE = b"""<html><body><div class="serp__results"><div id="links" class="results">
<div class="result results_links results_links_deep web-result"><h2 class="result__title">
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.history.com%2Farticles%2F1929-stock-market-crash">One</a></h2></div>
<div class="result results_links results_links_deep web-result"><h2 class="result__title">
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.federalreservehistory.org%2Fessays%2Fstock-market-crash-of-1929">Two</a></h2></div>
</div></div></body></html>"""
NO_RESULTS_PAGE = b"""<html><body><div class="serp__results"><div id="links" class="results">
<div class="no-results">No results.</div></div></div></body></html>"""
BLANK_PAGE = b"<html><head><title></title></head><body></body></html>"
CHALLENGE_PAGE = b"""<html><body><form action="//duckduckgo.com/anomaly.js" method="post">
<div class="anomaly-modal__title">Please confirm you are human</div>
<a href="https://html.duckduckgo.com/html/">Back</a></form></body></html>"""


# --- telling a results page from a page that is not one ----------------------

results = adapter_for(RESULTS_PAGE).search("causes 1929 stock market crash", limit=10, timeout_seconds=5)
require([row["url"] for row in results] == [
    "https://www.history.com/articles/1929-stock-market-crash",
    "https://www.federalreservehistory.org/essays/stock-market-crash-of-1929",
], "a_results_page_still_returns_its_results")
require(adapter_for(NO_RESULTS_PAGE).search("qzxv wmbf", limit=10, timeout_seconds=5) == [],
        "a_genuine_no_results_page_returns_an_empty_list")
require(raised_code(adapter_for(BLANK_PAGE)) == "public_search_results_unavailable",
        "a_blank_200_page_is_a_failed_search_not_an_empty_one")
require(raised_code(adapter_for(CHALLENGE_PAGE)) == "public_search_results_unavailable",
        "a_challenge_page_linking_only_to_the_engine_is_a_failed_search")
bare_links = adapter_for(b"<a class='result__a' href='https://docs.example.com/report'>One</a>")
require(len(bare_links.search("report", limit=5, timeout_seconds=5)) == 1,
        "result_links_without_a_results_section_still_count")

clock = FakeClock()
paced = adapter_for(BLANK_PAGE, RESULTS_PAGE, RESULTS_PAGE, clock=clock)
require(raised_code(paced) == "public_search_results_unavailable", "the_paced_adapter_sees_the_blank_page")
paced.search("causes 1929 stock market crash", limit=10, timeout_seconds=5)
require(clock.sleeps and clock.sleeps[-1] >= paced.search_unavailable_backoff_seconds - 1e-9,
        "the_search_after_a_non_results_page_waits_out_the_backoff")
clock.now += 5.0
before = len(clock.sleeps)
paced.search("causes 1929 stock market crash", limit=10, timeout_seconds=5)
require(len(clock.sleeps) == before, "the_backoff_does_not_outlast_one_good_search")


# --- the coordinator retries once, then ends honestly ------------------------


def native_receipt(source_candidate, plan, url: str, max_bytes: int) -> dict:
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


class ScriptedSearchAdapter:
    """Each search takes the next scripted outcome: a list of URLs or an error code."""

    def __init__(self, *outcomes) -> None:
        self.outcomes = list(outcomes)
        self.queries: list[str] = []
        self.observed: list[str] = []

    def describe(self) -> dict[str, object]:
        return {
            "adapter_code": "scripted-search-fixture", "read_only": True,
            "allowed_methods": ["GET", "HEAD"], "search_supported": True,
            "private_network_allowed": False, "redirect_revalidation_required": True,
            "credentials_allowed": False, "cookies_allowed": False, "uploads_allowed": False,
            "side_effects_allowed": False, "max_bytes_enforced": True, "timeout_enforced": True,
        }

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.queries.append(query)
        outcome = self.outcomes.pop(0) if self.outcomes else []
        if isinstance(outcome, str):
            raise PublicWebResearchError(outcome)
        return [{"url": url, "source_kind": "reputable_secondary"} for url in outcome][:limit]

    def observe(self, source_candidate, *, plan, max_bytes: int, timeout_seconds: float):
        url = str(source_candidate.get("public_url") or "")
        self.observed.append(url)
        return native_receipt(source_candidate, plan, url, max_bytes)


OBJECTIVE = "Research the causes of the 1929 stock market crash"
BUDGET = {"max_queries": 20, "max_candidates": 32, "max_observed_pages": 28,
          "max_source_failures": 12, "max_total_bytes": 4194304, "max_elapsed_seconds": 600}
SOURCES = ["https://www.history.com/articles/1929-stock-market-crash",
           "https://www.federalreservehistory.org/essays/stock-market-crash-of-1929"]


def run(adapter, tag: str, *, budget: dict | None = None) -> dict:
    store = BoundedResearchSessionStore(RUNTIME)
    created = store.create_session(f"{tag}:create", objective=OBJECTIVE, budget=budget or BUDGET)
    session = created["result"]
    authorized = store.authorize_session(
        f"{tag}:auth", session_id=session["session_id"],
        session_digest=session["session_digest"], public_query_confirmed=True,
    )
    return store.execute_session(
        f"{tag}:exec", session_id=session["session_id"],
        authorization_digest=authorized["result"]["authorization_digest"], adapter=adapter,
    )


recovering = ScriptedSearchAdapter("public_search_results_unavailable", SOURCES)
require(validate_read_only_adapter(recovering)["ok"], "scripted_search_fixture_is_a_read_only_adapter")
recovered = run(recovering, "v2731-3-0-retry")
recovered_session = (recovered.get("result") or {}).get("session", {})
require(recovered.get("ok") and recovered_session.get("state") == "completed", "a_run_recovers_when_the_retry_returns_results")
require(len(recovering.queries) >= 2 and recovering.queries[0] == recovering.queries[1],
        "the_retry_asks_the_same_query_again")
require(recovering.observed, "the_retried_search_leads_to_observed_sources")
require(int(recovered_session.get("source_failure_count") or 0) == 1, "the_failed_attempt_is_counted_as_a_failure")
require(int(recovered_session.get("query_count") or 0) == len(recovering.queries),
        "every_search_attempt_is_counted_as_a_query")

unavailable = ScriptedSearchAdapter("public_search_results_unavailable", "public_search_results_unavailable")
blocked = run(unavailable, "v2731-3-0-unavailable")
blocked_report = (blocked.get("result") or {}).get("report", {})
require(not blocked.get("ok") and (blocked.get("result") or {}).get("session", {}).get("state") == "failed",
        "a_search_that_never_returns_a_results_page_fails_the_run")
require((blocked.get("result") or {}).get("failure_code") == "search_results_unavailable",
        "the_failure_says_the_search_returned_no_results_page")
require(blocked_report.get("collection_stop_reason") == "search_results_unavailable",
        "the_report_is_not_a_finished_collection")
require(len(unavailable.queries) == 2, "a_non_results_page_is_retried_exactly_once")
require(sanitize_report(blocked_report).get("collection_stop_reason") == "search_results_unavailable",
        "history_keeps_the_unavailable_stop_reason")
require("did not return a results page" in _research_report_message({}, blocked_report),
        "the_chat_message_says_the_search_returned_no_results_page")

refused = ScriptedSearchAdapter("public_web_transport_failed", "public_web_transport_failed")
transport = run(refused, "v2731-3-0-transport")
require(len(refused.queries) == 1, "other_search_failures_are_not_retried")
require((transport.get("result") or {}).get("failure_code") == "search_results_unavailable",
        "a_failed_search_with_nothing_found_is_a_retrieval_failure")

empty = ScriptedSearchAdapter([])
nothing = run(empty, "v2731-3-0-empty")
nothing_report = (nothing.get("result") or {}).get("report", {})
require(not nothing.get("ok") and (nothing.get("result") or {}).get("session", {}).get("state") == "failed",
        "a_search_with_no_results_fails_rather_than_finishing")
require((nothing.get("result") or {}).get("failure_code") == "no_search_results", "the_empty_search_is_named")
require(nothing_report.get("collection_stop_reason") == "no_search_results",
        "the_empty_search_report_names_its_stop_reason")
require(int(nothing_report.get("source_failure_count") or 0) == 0, "a_genuine_empty_result_costs_no_failure")
require(len(empty.queries) == 1, "a_genuine_empty_result_is_not_retried")
require("the search returned no results" in _research_report_message({}, nothing_report),
        "the_chat_message_says_the_search_returned_no_results")

# The real adapter and the coordinator together: blank page, then results, then
# one document. With three queries or fewer no adaptive follow-up is reserved, so
# the fixture's three responses are exactly what the run needs.
clock = FakeClock()
native = GovernedPublicWebResearchAdapter(
    resolver=resolver, sleeper=clock.sleep,
    session_factory=FakeFactory(BLANK_PAGE, RESULTS_PAGE, b"<html><body>The crash followed a speculative boom.</body></html>"),
)
native_run = run(native, "v2731-3-0-native", budget={"max_queries": 2, "max_candidates": 2, "max_observed_pages": 1})
native_session = (native_run.get("result") or {}).get("session", {})
require(native_run.get("ok") and int(native_session.get("observed_page_count") or 0) == 1,
        "the_real_adapter_recovers_from_a_blank_search_page")
require(any(seconds >= 2.5 for seconds in clock.sleeps), "the_real_adapter_backs_off_before_the_retry")
require(int(native_session.get("query_count") or 0) == 2, "the_retry_stays_inside_the_query_budget")

print(json.dumps({"suite": "v2731.3.0-empty-search-page", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
