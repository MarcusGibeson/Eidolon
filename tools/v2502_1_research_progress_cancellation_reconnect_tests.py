from __future__ import annotations

"""Deterministic v2502.1 research progress, cancellation, and reconnect tests."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

runtime = tempfile.TemporaryDirectory(prefix="eidolon-v2502-1-")
os.environ["EIDOLON_DATA_DIR"] = runtime.name

import chat_action_router as router
import conversational_research_actions as bridge
import dashboard_chat_console as dashboard
from bounded_autonomous_web_research import BoundedResearchSessionStore
from conversation_operations import create_operation_marker, finalize_operation_marker, new_conversation_operation_id
from conversation_sessions import create_conversation_session
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


class DelayedAdapter:
    search_calls = 0
    observe_calls = 0
    observe_started = threading.Event()
    release_observation = threading.Event()

    def describe(self):
        return {
            "adapter_code": "v2502.1-delayed-fixture",
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
        return [
            {"url": f"https://example.com/evidence-{index}", "source_kind": "primary_official", "fetched_at": "2026-08-27T00:00:00+00:00"}
            for index in range(1, min(3, limit) + 1)
        ]

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        type(self).observe_calls += 1
        type(self).observe_started.set()
        if not type(self).release_observation.wait(8):
            raise RuntimeError("fixture_observation_release_timeout")
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
            "evidence_digest": digest("delayed-fixture-evidence"),
            "citation_id": "delayed-source",
            "source_kind": candidate["source_kind"],
            "quality_score": candidate["quality_score"],
            "freshness_known": True,
            "fresh_enough": True,
            "relevance_score": 0.95,
            "observed_bytes": min(512, max_bytes),
        }
        receipt["receipt_digest"] = digest(receipt)
        return receipt


bridge.GovernedPublicWebResearchAdapter = DelayedAdapter

create = bridge.execute_conversational_research_action(
    "research_session_create",
    {"objective": "compare current public evidence for a deterministic fixture"},
    event_id="v2502.1:create",
)
require(create.get("ok") is True, "bounded_session_created")
session = dict(create.get("session") or {})
session_id = str(session.get("session_id") or "")
session_digest = str(session.get("session_digest") or "")

conversation = create_conversation_session("v2502.1 reconnect fixture", source="fixture")
operation_id = new_conversation_operation_id()
create_operation_marker(operation_id, conversation["id"], acceptance_key="v2502-1-progress-acceptance")
action = router.propose_chat_action(
    f"Authorize research session {session_id} digest {session_digest}.",
    save=True,
    deduplication_key=operation_id,
    conversation_session_id=conversation["id"],
)
job = dashboard._DashboardOperationJob(operation_id, conversation["id"], operation_id)
dashboard._DASHBOARD_OPERATION_JOBS[operation_id] = job

execution_holder: dict[str, object] = {}


def run_execution() -> None:
    execution_holder["result"] = router.execute_chat_action(action["id"], claimant="conversation")


thread = threading.Thread(target=run_execution, daemon=True)
thread.start()
require(DelayedAdapter.observe_started.wait(8), "research_reaches_observation_stage")

first_portal = dashboard._action_portal_for_operation(operation_id) or {}
progress = dict(first_portal.get("research_progress") or {})
require(first_portal.get("status") == "running", "running_action_portal_is_visible")
require(progress.get("state") == "running" and progress.get("progress_stage") == "observing", "live_stage_is_projected")
require(0 < int(progress.get("progress_percent") or 0) < 100, "live_percent_is_bounded_and_nonterminal")
require(int(progress.get("query_count") or 0) >= 1 and int(progress.get("candidate_count") or 0) >= 1, "live_request_counts_are_projected")

reconnected = BoundedResearchSessionStore(runtime.name).inspect_session(session_id, session_digest=session_digest)
require(reconnected.get("ok") is True and dict(reconnected.get("session") or {}).get("state") == "running", "new_store_instance_rehydrates_same_running_session")
request_counts_before_status = (DelayedAdapter.search_calls, DelayedAdapter.observe_calls)
operation_status = dashboard.dashboard_chat_operation_status(operation_id=operation_id)
require(dict(operation_status.get("action_portal") or {}).get("research_progress", {}).get("session_id") == session_id, "operation_poll_returns_same_research_session")
require(request_counts_before_status == (DelayedAdapter.search_calls, DelayedAdapter.observe_calls), "progress_poll_starts_no_external_request")

cancelled = dashboard.cancel_dashboard_chat_operation(operation_id, project_id=str(conversation.get("project_id") or "eidolon"))
require(cancelled.get("ok") is True and cancelled.get("status") == "cancellation_requested", "dashboard_cancel_targets_running_operation")
research_cancel = dict(cancelled.get("research_cancellation") or {})
require(research_cancel.get("ok") is True and research_cancel.get("status") == "research_session_cancelled", "dashboard_cancel_targets_exact_research_session")
require(job.cancel_event.is_set(), "conversation_cancel_event_is_set")

duplicate_cancel = dashboard.cancel_dashboard_chat_operation(operation_id, project_id=str(conversation.get("project_id") or "eidolon"))
require(duplicate_cancel.get("duplicate_request") is True, "repeated_operation_cancel_is_idempotent")
require(dict(duplicate_cancel.get("research_cancellation") or {}).get("ok") is True, "repeated_research_cancel_replays_same_receipt")

DelayedAdapter.release_observation.set()
thread.join(10)
require(not thread.is_alive(), "cancelled_execution_reaches_terminal_state")
execution = execution_holder.get("result")
require(getattr(execution, "ok", False) is True, "cancelled_research_finishes_without_runtime_crash")
require(str(getattr(execution, "result", {}).get("status") or "") == "bounded_research_cancelled", "research_execution_records_cancelled_outcome")
require("cancelled bounded research session" in str(getattr(execution, "result", {}).get("message") or ""), "cancelled_session_is_not_presented_as_completed_report")
require(DelayedAdapter.observe_calls == 1, "no_new_page_request_starts_after_cancellation")

job.finish()
finalize_operation_marker(operation_id, completion_state="cancelled", success=False, failure_category="cancelled")
final_status = dashboard.dashboard_chat_operation_status(operation_id=operation_id)
final_progress = dict(final_status.get("action_portal", {}).get("research_progress") or {})
require(final_progress.get("state") == "cancelled" and int(final_progress.get("progress_percent") or 0) == 100, "refresh_rehydrates_terminal_cancelled_progress")

serialized = json.dumps(final_status.get("action_portal") or {}, sort_keys=True)
require("deterministic fixture" not in serialized and "compare current" not in serialized, "portal_exposes_no_objective_or_query_text")
require("raw_page_content" not in serialized and "credentials" not in serialized, "portal_exposes_no_raw_content_or_credentials")

source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
styles = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
require("data-research-progress" in source and "renderResearchProgress" in source, "dashboard_has_live_research_progress_renderer")
require("chat-research-progress progress" in styles, "research_progress_has_stable_accessible_meter_styling")
require("never replays external requests" in source, "restart_recovery_copy_states_fail_closed_policy")

rendered = dashboard.render_realtime_chat_panel(None)
scripts = re.findall(r"<script[^>]*>(.*?)</script>", rendered, flags=re.S | re.I)
node = shutil.which("node")
require(bool(scripts) and bool(node), "rendered_dashboard_script_and_node_are_available")
with tempfile.TemporaryDirectory(prefix="eidolon-v2502-1-js-") as js_root:
    for index, script in enumerate(scripts):
        script_path = Path(js_root) / f"dashboard-{index}.js"
        script_path.write_text(script, encoding="utf-8")
        checked = subprocess.run([str(node), "--check", str(script_path)], capture_output=True, text=True, timeout=30)
        require(checked.returncode == 0, f"rendered_dashboard_javascript_{index}_is_valid")


class FailingSourceAdapter(DelayedAdapter):
    search_calls = 0
    observe_calls = 0

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        type(self).observe_calls += 1
        raise RuntimeError("fixture_source_unavailable")


failure_store = BoundedResearchSessionStore(runtime.name)
failure_created = failure_store.create_session(
    "v2502.1:failure:create",
    objective="measure a public source failure count",
    budget={"max_queries": 1, "max_candidates": 1, "max_observed_pages": 1, "max_total_bytes": 4096, "max_elapsed_seconds": 20},
)
failure_ref = dict(failure_created.get("result") or {})
failure_authorized = failure_store.authorize_session(
    "v2502.1:failure:authorize",
    session_id=failure_ref["session_id"],
    session_digest=failure_ref["session_digest"],
    public_query_confirmed=True,
)
failure_execution = failure_store.execute_session(
    "v2502.1:failure:execute",
    session_id=failure_ref["session_id"],
    authorization_digest=str(dict(failure_authorized.get("result") or {}).get("authorization_digest") or ""),
    adapter=FailingSourceAdapter(),
)
failure_session = dict(dict(failure_execution.get("result") or {}).get("session") or {})
require(int(failure_session.get("source_failure_count") or 0) == 1, "source_failure_count_updates_during_and_after_execution")


class NoReplayAdapter(DelayedAdapter):
    search_calls = 0
    observe_calls = 0

    def search(self, query, *, limit, timeout_seconds):
        type(self).search_calls += 1
        return []


restart_store = BoundedResearchSessionStore(runtime.name)
restart_created = restart_store.create_session(
    "v2502.1:restart:create",
    objective="prove interrupted external research is never replayed",
    budget={"max_queries": 1, "max_candidates": 1, "max_observed_pages": 1, "max_total_bytes": 4096, "max_elapsed_seconds": 20},
)
restart_ref = dict(restart_created.get("result") or {})
restart_authorized = restart_store.authorize_session(
    "v2502.1:restart:authorize",
    session_id=restart_ref["session_id"],
    session_digest=restart_ref["session_digest"],
    public_query_confirmed=True,
)
state = json.loads(restart_store.path.read_text(encoding="utf-8"))
private_restart = next(row for row in state["sessions"] if row["session_id"] == restart_ref["session_id"])
private_restart["state"] = "running"
private_restart["execution_owner_pid"] = 2147483000
restart_store.path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
restart_execution = restart_store.execute_session(
    "v2502.1:restart:execute",
    session_id=restart_ref["session_id"],
    authorization_digest=str(dict(restart_authorized.get("result") or {}).get("authorization_digest") or ""),
    adapter=NoReplayAdapter(),
)
require(restart_execution.get("status") == "bounded_research_interrupted_failed_closed", "dead_owner_fails_closed_after_restart")
require(NoReplayAdapter.search_calls == 0 and NoReplayAdapter.observe_calls == 0, "interrupted_session_replays_no_external_request")

dashboard._DASHBOARD_OPERATION_JOBS.pop(operation_id, None)

print(json.dumps({
    "suite": "v2502.1-research-progress-cancellation-reconnect",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "search_request_count": DelayedAdapter.search_calls,
    "observation_request_count": DelayedAdapter.observe_calls,
    "duplicate_external_request_count": 0,
    "raw_content_exposed": False,
    "authority_expanded": False,
}, sort_keys=True))
