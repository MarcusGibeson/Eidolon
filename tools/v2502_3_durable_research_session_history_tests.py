from __future__ import annotations

"""Deterministic v2502.3 durable research-session history regression suite."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

runtime = tempfile.TemporaryDirectory(prefix="eidolon-v2502-3-")
os.environ["EIDOLON_DATA_DIR"] = runtime.name

import conversational_research_actions as bridge
import dashboard_chat_console as dashboard
from bounded_autonomous_web_research import BoundedResearchSessionStore
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION

checks: list[str] = []


def require(value: object, name: str) -> None:
    if not value:
        raise AssertionError(name)
    checks.append(name)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class HistoryAdapter:
    search_calls = 0
    observe_calls = 0

    def describe(self):
        return {
            "adapter_code": "v2502.3-history-fixture",
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
        return [{"url": "https://official.example/history", "source_kind": "primary_official", "fetched_at": "2026-08-27T00:00:00+00:00"}][:limit]

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        type(self).observe_calls += 1
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
            "receipt_kind": "source_observation",
            "authoritative": True,
            "terminal": True,
            "operation_digest": digest(["op", type(self).observe_calls]),
            "terminal_result_digest": digest(["result", type(self).observe_calls]),
            "source_observed": True,
            "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"),
            "stance": "supports",
            "evidence_digest": digest(["evidence", candidate.get("subquestion_id")]),
            "citation_id": f"history-{type(self).observe_calls}",
            "source_kind": candidate["source_kind"],
            "quality_score": 0.9,
            "freshness_known": True,
            "fresh_enough": True,
            "relevance_score": 0.9,
            "observed_bytes": min(256, max_bytes),
        }
        row["receipt_digest"] = digest(row)
        return row


class FailingClock:
    """Fail inside execution after the session has entered its running state."""

    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("fixture_execution_failure")
        return 0.0


def complete(store: BoundedResearchSessionStore, key: str, objective: str, adapter=None):
    created = store.create_session(f"{key}:create", objective=objective, budget={"max_queries": 1, "max_candidates": 2, "max_observed_pages": 1, "max_total_bytes": 2048, "max_elapsed_seconds": 20})
    ref = dict(created.get("result") or {})
    authorized = store.authorize_session(f"{key}:authorize", session_id=ref["session_id"], session_digest=ref["session_digest"], public_query_confirmed=True)
    executed = store.execute_session(f"{key}:execute", session_id=ref["session_id"], authorization_digest=str(dict(authorized.get("result") or {}).get("authorization_digest") or ""), adapter=adapter or HistoryAdapter())
    return ref, executed


store = BoundedResearchSessionStore(runtime.name)
completed_ref, completed = complete(store, "v2502.3:completed", "current public history catalog evidence")
require(completed.get("ok") is True, "completed_session_fixture_finishes")

cancel_created = store.create_session("v2502.3:cancel:create", objective="public cancelled history fixture")
cancel_ref = dict(cancel_created.get("result") or {})
cancelled = store.cancel_session("v2502.3:cancel", session_id=cancel_ref["session_id"], session_digest=cancel_ref["session_digest"])
require(cancelled.get("ok") is True, "cancelled_terminal_session_persists")

store.clock = FailingClock()
failed_ref, failed = complete(store, "v2502.3:failed", "public failed history fixture")
store.clock = time.monotonic
require(failed.get("status") == "bounded_research_failed_safely", "failed_terminal_session_persists")

interrupt_created = store.create_session("v2502.3:interrupt:create", objective="public interrupted history fixture")
interrupt_ref = dict(interrupt_created.get("result") or {})
interrupt_auth = store.authorize_session("v2502.3:interrupt:authorize", session_id=interrupt_ref["session_id"], session_digest=interrupt_ref["session_digest"], public_query_confirmed=True)
state = json.loads(store.path.read_text(encoding="utf-8"))
row = next(item for item in state["sessions"] if item["session_id"] == interrupt_ref["session_id"])
row["state"] = "running"
row["execution_owner_pid"] = 2147483000
store.path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
interrupted = store.execute_session("v2502.3:interrupt:execute", session_id=interrupt_ref["session_id"], authorization_digest=str(dict(interrupt_auth.get("result") or {}).get("authorization_digest") or ""), adapter=HistoryAdapter())
require(interrupted.get("status") == "bounded_research_interrupted_failed_closed", "interrupted_session_fails_closed")

calls_before_history = (HistoryAdapter.search_calls, HistoryAdapter.observe_calls)
history = store.history_catalog(limit=64)
require(len(history.get("sessions") or []) == 4, "history_catalog_contains_all_terminal_session_classes")
statuses = {row.get("terminal_status") for row in history.get("sessions") or []}
require(statuses == {"completed", "cancelled", "failed", "interrupted"}, "history_distinguishes_terminal_statuses")
require(all(re.fullmatch(r"[0-9a-f]{64}", str(row.get("history_record_digest") or "")) for row in history.get("sessions") or []), "history_records_are_digest_bound")
require(all(row.get("session_digest") and row.get("plan_digest") for row in history.get("sessions") or []), "history_preserves_exact_session_lineage")
completed_history = next(row for row in history["sessions"] if row.get("session_id") == completed_ref["session_id"])
require(completed_history.get("report_digest") and completed_history.get("evidence_count") == 1, "history_preserves_report_and_evidence_counts")
require(sum(dict(completed_history.get("freshness_bands") or {}).values()) == completed_history.get("citation_count"), "history_preserves_freshness_bands")
require(sum(dict(completed_history.get("quality_bands") or {}).values()) == completed_history.get("citation_count"), "history_preserves_quality_bands")
serialized = json.dumps(history, sort_keys=True)
require("current public history catalog evidence" not in serialized and history.get("query_text_exposed") is False, "history_projection_excludes_objective_and_query_text")
require(calls_before_history == (HistoryAdapter.search_calls, HistoryAdapter.observe_calls), "history_inspection_performs_no_web_request")

repeat = store.history_catalog(limit=64)
require(len(repeat.get("sessions") or []) == len(history.get("sessions") or []), "reconnect_does_not_duplicate_history_records")
replayed = store.execute_session("v2502.3:completed:execute", session_id=completed_ref["session_id"], authorization_digest="0" * 64, adapter=HistoryAdapter())
require(replayed.get("idempotent") is True and len(store.history_catalog().get("sessions") or []) == 4, "duplicate_execution_event_does_not_duplicate_history")

history_action = {
    "id": "history-action",
    "status": "completed",
    "function_name": "research_history_list",
    "result": {"history": history},
}
projection = bridge.conversational_research_history(history_action) or {}
portal = {"research_history": projection}
server_html = dashboard._render_research_history(portal)
require("data-research-history='true'" in server_html and "Research history" in server_html, "dashboard_server_renders_history_surface")
require("current public history catalog evidence" not in server_html, "dashboard_history_surface_is_content_minimized")
progress_html = dashboard._render_research_progress({"research_progress": {"session_id": completed_ref["session_id"], "state": "completed", "progress_stage": "completed", "progress_percent": 100}})
require("data-research-progress='true'" in progress_html, "server_progress_renderer_repaired")

styles = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
require("chat-research-history-list" in styles and "max-width:100%" in styles, "history_surface_has_narrow_width_contract")
require("renderResearchHistory" in source and "data-research-history" in source, "dashboard_has_dynamic_history_renderer")
rendered = dashboard.render_realtime_chat_panel(None)
scripts = re.findall(r"<script[^>]*>(.*?)</script>", rendered, flags=re.S | re.I)
node = shutil.which("node")
require(bool(scripts) and bool(node), "rendered_dashboard_script_and_node_available")
with tempfile.TemporaryDirectory(prefix="eidolon-v2502-3-js-") as js_root:
    for index, script in enumerate(scripts):
        path = Path(js_root) / f"dashboard-{index}.js"
        path.write_text(script, encoding="utf-8")
        checked = subprocess.run([str(node), "--check", str(path)], capture_output=True, text=True, timeout=30)
        require(checked.returncode == 0, f"rendered_dashboard_javascript_{index}_valid")

# Tampering is detected and deliberately not repaired.
raw_state = json.loads(store.path.read_text(encoding="utf-8"))
raw_state["history_records"][0]["evidence_count"] = int(raw_state["history_records"][0].get("evidence_count") or 0) + 7
store.path.write_text(json.dumps(raw_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
tampered = store.history_catalog()
require(any(row.get("integrity_status") == "invalid" for row in tampered.get("sessions") or []), "tampered_history_record_is_detected")
require(tampered.get("silent_repair_performed") is False, "tampered_history_is_not_silently_repaired")
raw_again = json.loads(store.path.read_text(encoding="utf-8"))
require(raw_again["history_records"][0]["evidence_count"] == raw_state["history_records"][0]["evidence_count"], "tampered_history_bytes_remain_unmodified_by_inspection")

print(json.dumps({
    "suite": "v2502.3-durable-research-session-history",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "history_count": 4,
    "history_web_request_count": 0,
    "raw_content_exposed": False,
    "authority_expanded": False,
}, sort_keys=True))
