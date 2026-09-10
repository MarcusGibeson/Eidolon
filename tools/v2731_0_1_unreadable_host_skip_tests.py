from __future__ import annotations

"""One unreadable host must cost one failure, not one per page it appears on.

A consent-gated or JavaScript-rendered domain yields no readable text for any of
its pages. The candidate list is built before observation, so several pages from
such a domain sit in the queue together and each spends its own failure to learn
the same fact. A live run died exactly this way: three Reddit pages, three
failures, no page observed, and the session terminated with an exhausted failure
budget while the query budget was almost untouched.

Skipping later pages from a host that has already refused keeps the budget for
sources that might actually be readable.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-1-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import BoundedResearchSessionStore, validate_read_only_adapter
from governed_public_web_research_adapter import PublicWebResearchError
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


OBJECTIVE = "Research Widget Payment Tracker demand."
BUDGET = {"max_queries": 20, "max_candidates": 32, "max_observed_pages": 28,
          "max_source_failures": 12, "max_total_bytes": 4194304, "max_elapsed_seconds": 600}

GATED_HOST = "gated.example.com"
READABLE_HOST = "survey.example.org"


class GatedHostAdapter:
    """One domain serves a consent gate on every page; another is readable."""

    def __init__(self) -> None:
        self.attempted: list[str] = []
        self.observed: list[str] = []
        self.searches = 0

    def describe(self) -> dict[str, object]:
        return {
            "adapter_code": "gated-host-fixture", "read_only": True,
            "allowed_methods": ["GET", "HEAD"], "search_supported": True,
            "private_network_allowed": False, "redirect_revalidation_required": True,
            "credentials_allowed": False, "cookies_allowed": False, "uploads_allowed": False,
            "side_effects_allowed": False, "max_bytes_enforced": True, "timeout_enforced": True,
        }

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.searches += 1
        if "survey study report respondents" in query:
            return [{"url": f"https://{READABLE_HOST}/study-{self.searches}", "source_kind": "reputable_secondary"}][:limit]
        # The planned queries return several pages from the same gated domain.
        return [
            {"url": f"https://{GATED_HOST}/thread-{self.searches}-a", "source_kind": "community_experience"},
            {"url": f"https://{GATED_HOST}/thread-{self.searches}-b", "source_kind": "community_experience"},
            {"url": f"https://{GATED_HOST}/thread-{self.searches}-c", "source_kind": "community_experience"},
        ][:limit]

    def observe(self, source_candidate, *, plan, max_bytes: int, timeout_seconds: float):
        url = str(source_candidate.get("public_url") or "")
        self.attempted.append(url)
        if GATED_HOST in url:
            # The real adapter raises this typed error, and its .code is what the
            # failure digest is built from. A bare RuntimeError would digest as
            # "RuntimeError" and quietly not match the code under test.
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


adapter = GatedHostAdapter()
require(validate_read_only_adapter(adapter)["ok"], "gated_host_fixture_is_a_read_only_adapter")

store = BoundedResearchSessionStore(RUNTIME)
created = store.create_session("v2731-0-1:create", objective=OBJECTIVE, budget=BUDGET)
session = created["result"]
authorized = store.authorize_session(
    "v2731-0-1:auth", session_id=session["session_id"],
    session_digest=session["session_digest"], public_query_confirmed=True,
)
result = store.execute_session(
    "v2731-0-1:exec", session_id=session["session_id"],
    authorization_digest=authorized["result"]["authorization_digest"], adapter=adapter,
)

gated_attempts = [url for url in adapter.attempted if GATED_HOST in url]
require(gated_attempts, "the_gated_host_was_attempted_at_least_once")
require(len(gated_attempts) == 1, f"a_gated_host_is_attempted_only_once (saw {len(gated_attempts)})")

report = result["result"]["report"] if result.get("ok") else (result.get("result") or {}).get("report", {})
session_row = (result.get("result") or {}).get("session", {})
require(int(session_row.get("source_failure_count") or 0) == 1,
        "an_unreadable_domain_costs_exactly_one_failure")
require(int(report.get("skipped_unreadable_host_count") or 0) >= 1,
        "skipped_pages_from_that_host_are_counted")
require(adapter.observed, "the_readable_replacement_was_still_reached")
require(all(READABLE_HOST in url for url in adapter.observed),
        "only_readable_sources_were_observed")
require(result.get("ok"), "the_session_survives_a_wholly_gated_domain")

# --- the run that observes nothing is the one most in need of diagnostics -----


class WhollyGatedAdapter(GatedHostAdapter):
    """Nothing is readable, so the session ends without observing a single page."""

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.searches += 1
        return [
            {"url": f"https://{GATED_HOST}/thread-{self.searches}-a", "source_kind": "community_experience"},
            {"url": f"https://{GATED_HOST}/thread-{self.searches}-b", "source_kind": "community_experience"},
            {"url": f"https://{GATED_HOST}/thread-{self.searches}-c", "source_kind": "community_experience"},
        ][:limit]


blind = WhollyGatedAdapter()
created = store.create_session("v2731-0-1b:create", objective="Research Gadget Invoice Tracker demand.", budget=BUDGET)
session = created["result"]
authorized = store.authorize_session(
    "v2731-0-1b:auth", session_id=session["session_id"],
    session_digest=session["session_digest"], public_query_confirmed=True,
)
failed = store.execute_session(
    "v2731-0-1b:exec", session_id=session["session_id"],
    authorization_digest=authorized["result"]["authorization_digest"], adapter=blind,
)

require(not failed.get("ok"), "a_wholly_unreadable_corpus_fails_rather_than_reporting_success")
failure_report = (failed.get("result") or {}).get("report", {})
require(failure_report, "a_failed_run_still_produces_a_report")
require("skipped_unreadable_host_count" in failure_report,
        "the_failure_report_carries_the_skip_count")
require(int(failure_report.get("skipped_unreadable_host_count") or 0) >= 1,
        "skips_are_visible_on_the_run_that_observed_nothing")
require(int(failure_report.get("source_failure_count") or 0) == 1,
        "a_wholly_gated_domain_still_costs_only_one_failure")
require(int(failure_report.get("readable_content_failure_count") or 0) >= 1,
        "the_failure_report_names_unreadable_content_as_the_cause")
require(int(failure_report.get("observed_page_count") or 0) == 0,
        "the_failure_report_records_that_nothing_was_observed")
require(int(failure_report.get("candidate_count") or 0) >= 1,
        "the_failure_report_records_how_many_candidates_were_found")

print(json.dumps({"suite": "v2731.0.1-unreadable-host-skip", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
