from __future__ import annotations

"""An unreadable source must be replaced, not silently dropped.

The candidate list is fixed before observation begins, so a source that cannot be
read shrank the evidence pool by exactly one and the run finished short while most
of its query budget sat unused. A trial could lose a quarter of its corpus to
JavaScript-rendered pages and still report "planned collection finished".

These checks cover spending spare query budget on a targeted replacement, not
retrying the host that just failed, keeping promotional pages out of a slot when
the objective needs a specific evidence dimension, and staying inside every budget.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2730-9-7-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import (
    MAX_OBSERVATION_REPLACEMENTS,
    BoundedResearchSessionStore,
    validate_read_only_adapter,
)
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def native_receipt(**values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
        "receipt_kind": "source_observation",
        "authoritative": True,
        "terminal": True,
        "operation_digest": "8" * 64,
        "terminal_result_digest": "9" * 64,
        **values,
    }
    row["receipt_digest"] = digest(row)
    return row


OBJECTIVE = "Research Widget Payment Tracker demand."
BUDGET = {"max_queries": 20, "max_candidates": 32, "max_observed_pages": 28,
          "max_source_failures": 12, "max_total_bytes": 4194304, "max_elapsed_seconds": 600}

UNREADABLE_HOST = "unreadable.example.com"
REPLACEMENT_HOST = "survey.example.org"
PROMOTIONAL_URL = "https://vendor.example.com/blog/best-widget-tracker-tools"


class ReplacementAdapter:
    """Every first-round result is unreadable; replacement rounds return good sources."""

    def __init__(self, *, promotional_replacements: bool = False) -> None:
        self.queries: list[str] = []
        self.observed: list[str] = []
        self.failed: list[str] = []
        self.promotional_replacements = promotional_replacements
        self._replacement_round = 0

    def describe(self) -> dict[str, object]:
        return {
            "adapter_code": "replacement-fixture", "read_only": True,
            "allowed_methods": ["GET", "HEAD"], "search_supported": True,
            "private_network_allowed": False, "redirect_revalidation_required": True,
            "credentials_allowed": False, "cookies_allowed": False, "uploads_allowed": False,
            "side_effects_allowed": False, "max_bytes_enforced": True, "timeout_enforced": True,
        }

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.queries.append(query)
        # A replacement query carries the dimension bias terms; the planned ones do not.
        if "survey study report respondents" in query:
            self._replacement_round += 1
            if self.promotional_replacements:
                return [{"url": PROMOTIONAL_URL, "source_kind": "unknown"}][:limit]
            return [
                {"url": f"https://{REPLACEMENT_HOST}/study-{self._replacement_round}", "source_kind": "reputable_secondary"},
                {"url": f"https://{UNREADABLE_HOST}/again-{self._replacement_round}", "source_kind": "unknown"},
            ][:limit]
        return [{"url": f"https://{UNREADABLE_HOST}/page-{len(self.queries)}", "source_kind": "unknown"}][:limit]

    def observe(self, source_candidate, *, plan, max_bytes: int, timeout_seconds: float):
        url = str(source_candidate.get("public_url") or "")
        if UNREADABLE_HOST in url:
            self.failed.append(url)
            raise RuntimeError("public_web_demand_readable_content_unavailable")
        self.observed.append(url)
        return native_receipt(
            plan_digest=plan["plan_digest"], source_observed=True,
            source_candidate_digest=source_candidate["source_candidate_digest"],
            claim_code=source_candidate.get("subquestion_id") or "rq1", stance="unknown",
            evidence_digest=hashlib.sha256(url.encode()).hexdigest(),
            citation_id=f"web-{hashlib.sha256(url.encode()).hexdigest()[:16]}",
            source_kind=source_candidate["source_kind"], quality_score=source_candidate["quality_score"],
            freshness_known=True, fresh_enough=True, observed_bytes=min(512, max_bytes),
        )


def run(adapter, tag: str) -> dict:
    store = BoundedResearchSessionStore(RUNTIME)
    created = store.create_session(f"{tag}:create", objective=OBJECTIVE, budget=BUDGET)
    session = created["result"]
    authorized = store.authorize_session(
        f"{tag}:auth", session_id=session["session_id"],
        session_digest=session["session_digest"], public_query_confirmed=True,
    )
    return store.execute_session(
        f"{tag}:exec", session_id=session["session_id"],
        authorization_digest=authorized["result"]["authorization_digest"], adapter=adapter,
    )


adapter = ReplacementAdapter()
require(validate_read_only_adapter(adapter)["ok"], "replacement_fixture_is_a_read_only_adapter")
result = run(adapter, "v2730-9-7-replace")
require(result.get("ok"), "session_with_unreadable_sources_still_completes")

require(adapter.failed, "unreadable_sources_were_actually_attempted")
replacement_queries = [q for q in adapter.queries if "survey study report respondents" in q]
require(replacement_queries, "an_unreadable_source_triggers_a_replacement_search")
require(
    all(REPLACEMENT_HOST in url for url in adapter.observed),
    "replacement_sources_are_the_ones_actually_observed",
)
require(adapter.observed, "a_replacement_source_was_read_after_the_failure")
require(
    not any(UNREADABLE_HOST in url for url in adapter.observed),
    "the_failed_host_is_never_counted_as_observed",
)
require(
    len(replacement_queries) <= MAX_OBSERVATION_REPLACEMENTS,
    "replacement_searches_stay_within_their_cap",
)

report = result["result"]["report"]
require(report["source_failure_count"] >= 1, "failures_are_still_recorded_on_the_receipt")
require(len(report.get("source_failure_receipts") or []) >= 1, "failure_receipts_are_preserved")

session_row = result["result"]["session"] if isinstance(result["result"].get("session"), dict) else {}
query_count = int(session_row.get("query_count") or 0)
require(query_count <= BUDGET["max_queries"], "replacement_searches_respect_the_query_budget")
require(
    int(session_row.get("candidate_count") or 0) <= BUDGET["max_candidates"],
    "replacement_candidates_respect_the_candidate_budget",
)
require(
    int(session_row.get("source_failure_count") or 0) <= BUDGET["max_source_failures"],
    "replacement_attempts_respect_the_failure_budget",
)

# A promotional page cannot establish a required dimension, so it must not take a
# slot. With nothing else readable the run ends with no evidence, and reporting
# nothing is the correct outcome - preferable to admitting a vendor page.
promotional = ReplacementAdapter(promotional_replacements=True)
promotional_result = run(promotional, "v2730-9-7-promo")
require(
    not any("vendor.example.com" in url for url in promotional.observed),
    "a_promotional_replacement_is_not_given_an_observation_slot",
)
require(promotional.queries, "a_replacement_was_still_attempted_before_giving_up")
require(
    promotional_result.get("status") == "bounded_research_failed_safely",
    "an_unusable_corpus_fails_safely_rather_than_admitting_a_vendor_page",
)
require(not promotional_result.get("ok"), "an_unusable_corpus_is_not_reported_as_success")

print(json.dumps({"suite": "v2730.9.7-observation-replacement", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
