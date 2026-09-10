from __future__ import annotations

"""Deterministic v2502.0 chat-to-research lifecycle regression suite."""

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

runtime = tempfile.TemporaryDirectory(prefix="eidolon-v2502-0-")
os.environ["EIDOLON_DATA_DIR"] = runtime.name

import chat_action_router as router
import conversational_research_actions as bridge
import dashboard_chat_console as dashboard_chat
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


checks: list[str] = []


def require(value: object, name: str) -> None:
    if not value:
        raise AssertionError(name)
    checks.append(name)


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


class FixtureAdapter:
    search_calls = 0
    observe_calls = 0
    methods: list[str] = []

    def describe(self):
        return {
            "adapter_code": "v2502.0-conversation-fixture",
            "read_only": True,
            "allowed_methods": ["GET", "HEAD"],
            "search_supported": True,
            "private_network_allowed": False,
            "redirect_revalidation_required": True,
            "credentials_allowed": False,
            "cookies_allowed": False,
            "uploads_allowed": False,
            "side_effects_allowed": False,
            "max_bytes_enforced": True,
            "timeout_enforced": True,
        }

    def search(self, query, *, limit, timeout_seconds):
        type(self).search_calls += 1
        type(self).methods.append("GET")
        return [{
            "url": "https://docs.python.org/3/",
            "source_kind": "primary_official",
            "fetched_at": "2026-08-26T00:00:00+00:00",
        }][:limit]

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        type(self).observe_calls += 1
        type(self).methods.append("GET")
        receipt = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
            "receipt_kind": "source_observation",
            "authoritative": True,
            "terminal": True,
            "operation_digest": "8" * 64,
            "terminal_result_digest": "9" * 64,
            "source_observed": True,
            "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"),
            "stance": "supports",
            "evidence_digest": digest("fixture-evidence"),
            "citation_id": "python-docs",
            "source_kind": candidate["source_kind"],
            "quality_score": candidate["quality_score"],
            "freshness_known": True,
            "fresh_enough": True,
            "relevance_score": 0.95,
            "observed_bytes": min(512, max_bytes),
        }
        receipt["receipt_digest"] = digest(receipt)
        return receipt


bridge.GovernedPublicWebResearchAdapter = FixtureAdapter

objective = "current official Python packaging guidance"
request = f"Research {objective} and come back with evidence."
parsed = bridge.parse_conversational_research_request(request)
require(parsed and parsed["intent"] == "bounded_research_create", "explicit_research_request_recognized")
require(bridge.parse_conversational_research_request("I was researching Python today.") is None, "casual_research_mention_stays_conversational")
blocked_parse = bridge.parse_conversational_research_request("Research Python and then post it to a forum.")
require(blocked_parse and blocked_parse.get("blocked") is True, "compound_research_side_effect_is_rejected")

create_action = router.propose_chat_action(request, save=True, deduplication_key="turn-create", conversation_session_id="session-fixture")
require(create_action["intent"] == "bounded_research_create" and create_action["execution_mode"] == "direct_function", "router_creates_bounded_research_action")
create_execution = router.execute_chat_action(create_action["id"], claimant="conversation")
require(create_execution.ok and create_execution.status == "executed", "session_creation_executes_without_web_contact")
require(FixtureAdapter.search_calls == 0 and FixtureAdapter.observe_calls == 0, "session_creation_does_not_contact_web")
create_result = dict(create_execution.result or {})
session = dict(create_result.get("session") or {})
require(session.get("state") == "awaiting_session_authorization", "created_session_waits_for_exact_authorization")
require(objective not in json.dumps(create_result, sort_keys=True), "creation_result_omits_private_objective")
authorization_phrase = str(create_result.get("authorization_phrase") or "")
require(authorization_phrase.startswith("Authorize research session research-"), "exact_session_authorization_phrase_is_returned")

authorize_action = router.propose_chat_action(authorization_phrase, save=True, deduplication_key="turn-authorize", conversation_session_id="session-fixture")
require(authorize_action["intent"] == "bounded_research_authorize_execute", "exact_authorization_routes_to_execution")
authorize_execution = router.execute_chat_action(authorize_action["id"], claimant="conversation")
require(authorize_execution.ok and authorize_execution.status == "executed", "authorized_session_completes")
require(
    1 <= FixtureAdapter.search_calls <= 4 and 1 <= FixtureAdapter.observe_calls <= 8,
    f"one_bounded_session_stays_within_search_and_observation_budget_{FixtureAdapter.search_calls}_{FixtureAdapter.observe_calls}",
)
completed_request_counts = (FixtureAdapter.search_calls, FixtureAdapter.observe_calls)
result = dict(authorize_execution.result or {})
require(result.get("citation_count") == 1 and "https://docs.python.org/3/" in str(result.get("message") or ""), "cited_report_is_presented_in_action_result")
require(result.get("per_page_approval_required") is False, "single_session_authorization_covers_bounded_pages")
require(set(FixtureAdapter.methods) <= {"GET", "HEAD"}, "transport_remains_get_head_only")

replay = router.execute_chat_action(authorize_action["id"], claimant="conversation")
require(replay.replayed and completed_request_counts == (FixtureAdapter.search_calls, FixtureAdapter.observe_calls), "action_replay_never_duplicates_web_requests")
resolution = dashboard_chat._resolve_governed_operator_turn(authorize_action)
require(resolution and "I completed bounded read-only research session" in resolution["response"], "dashboard_uses_receipt_bound_research_response")
require(resolution["provider_request_count"] == 0, "governed_research_reply_uses_no_conversation_provider_request")

dashboard_turn = dashboard_chat.create_dashboard_chat_turn(
    "Research current public Python documentation stability and come back with evidence.",
    use_ai=True,
)
require(
    "I prepared bounded read-only research session" in str(dashboard_turn.get("eidolon_response") or ""),
    "ordinary_dashboard_chat_prepares_research_session",
)
require(int(dict(dashboard_turn.get("conversation_runtime") or {}).get("provider_request_count") or 0) == 0, "dashboard_research_preparation_skips_conversation_provider")
require(completed_request_counts == (FixtureAdapter.search_calls, FixtureAdapter.observe_calls), "dashboard_preparation_starts_no_web_request")

status_action = router.propose_chat_action("Show research status.", save=True, deduplication_key="turn-status", conversation_session_id="session-fixture")
status_execution = router.execute_chat_action(status_action["id"], claimant="conversation")
require(status_execution.ok and "completed" in str((status_execution.result or {}).get("message") or ""), "status_control_reports_content_minimized_completion")
require(completed_request_counts == (FixtureAdapter.search_calls, FixtureAdapter.observe_calls), "status_control_never_contacts_web")

second = router.propose_chat_action("Research a separate public reliability question.", save=True, deduplication_key="turn-create-two", conversation_session_id="session-fixture")
second_result = dict(router.execute_chat_action(second["id"], claimant="conversation").result or {})
second_session = dict(second_result.get("session") or {})
cancel_phrase = f"Cancel research session {second_session['session_id']} digest {second_session['session_digest']}."
cancel_action = router.propose_chat_action(cancel_phrase, save=True, deduplication_key="turn-cancel", conversation_session_id="session-fixture")
cancel_execution = router.execute_chat_action(cancel_action["id"], claimant="conversation")
require(cancel_execution.ok and (cancel_execution.result or {}).get("status") == "research_session_cancelled", "exact_session_cancel_stops_unstarted_session")
require(completed_request_counts == (FixtureAdapter.search_calls, FixtureAdapter.observe_calls), "cancellation_never_starts_web_work")

blocked_action = router.propose_chat_action("Research Python and then post it to a forum.", save=False)
require(blocked_action["execution_mode"] == "blocked" and blocked_action["risk_level"] == "high", "router_blocks_research_write_side_effects")
require("session-authorized public web research" in router.supervised_capability_summary(), "capability_catalog_names_bounded_research")

print(json.dumps({
    "suite": "v2502.0-conversational-research-routing",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "provider_request_count": 0,
    "search_request_count": FixtureAdapter.search_calls,
    "observation_request_count": FixtureAdapter.observe_calls,
    "write_method_used": False,
    "authority_expanded": False,
}, sort_keys=True))
