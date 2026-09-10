from __future__ import annotations

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
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2503-6-runtime-")

import dashboard_chat_console as console


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


LONG_REPORT = (
    "I completed bounded read-only research session research-fixture.\n\n"
    + "Evidence-backed candidate comparison with citations and explicit uncertainty. " * 90
    + "\n\nNo external side effects occurred."
)


class FixtureExecution:
    def __init__(self, action_id: str) -> None:
        self.ok = True
        self.status = "executed"
        self.message = "Action completed."
        self.error = ""
        self.chat_action_id = action_id
        self.result = {"message": LONG_REPORT}
        self.replayed = False


research_action = {
    "id": "chat-action-long-research",
    "intent": "bounded_research_authorize_execute",
    "execution_mode": "direct_function",
    "function_name": "research_session_authorize_execute",
    "risk_level": "low",
    "status": "executed",
}
release_action = {
    "id": "chat-action-long-release",
    "intent": "release_summary",
    "execution_mode": "direct_function",
    "function_name": "release_summary",
    "risk_level": "low",
    "status": "executed",
}

console.execute_chat_action = lambda action_id, **_: FixtureExecution(action_id)
console.load_chat_action = lambda action_id: research_action if action_id == research_action["id"] else release_action
console._live_action_portal = lambda action: {}
console.build_action_portal_state = lambda *args, **kwargs: {}
console.build_execution_truth_receipt = lambda action: {
    "completion_state": "completed",
    "succeeded": True,
}
console.validate_execution_truth_receipt = lambda receipt, action=None: (True, {"ok": True})
console.public_execution_receipt = lambda receipt: dict(receipt)
console.render_receipt_bound_action_response = lambda *args, **kwargs: "receipt-bound action response"

research_execution = console._execute_explicit_safe_chat_action(dict(research_action)) or {}
require(len(LONG_REPORT) > 2_400, "fixture_exceeds_legacy_governed_output_limit")
require(research_execution.get("output") == LONG_REPORT, "long_research_output_is_not_cut_at_legacy_limit")
require(not research_execution.get("output_truncated"), "bounded_research_output_reports_complete_delivery")

release_execution = console._execute_explicit_safe_chat_action(dict(release_action)) or {}
require(len(str(release_execution.get("output") or "")) == console.MAX_GOVERNED_ACTION_OUTPUT_CHARS, "ordinary_governed_output_remains_compact")
require(release_execution.get("output_truncated"), "ordinary_oversized_output_retains_explicit_truncation_receipt")

resolution = console._resolve_governed_operator_turn(dict(research_action)) or {}
require(resolution.get("response") == LONG_REPORT, "receipt_bound_research_resolution_retains_full_report")

captured: dict[str, object] = {}


def capture_turn(session_id: str, **kwargs):
    captured.update(kwargs)
    return {"session_id": session_id, **kwargs}


console.append_conversation_turn = capture_turn
console._record_governed_operator_session_turn(
    "conversation-fixture",
    "turn-fixture",
    "Authorize exact research session.",
    resolution,
    streaming=True,
    source="v2503.6-fixture",
)
require(captured.get("assistant_response") == LONG_REPORT, "conversation_persistence_receives_full_research_report")

dashboard_source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
require("reply.textContent = turn.assistant_response || '';" in dashboard_source, "rehydration_renders_the_persisted_response_without_slicing")
require("queueReplyText(visibleText);" in dashboard_source, "streaming_queues_the_complete_delta_without_slicing")
require("reply.textContent += pendingReplyText;" in dashboard_source, "streaming_flushes_the_complete_queued_delta_without_slicing")

print(json.dumps({
    "suite": "v2503.6-long-research-response-delivery",
    "ok": True,
    "passed": len(CHECKS),
    "checks": CHECKS,
    "provider_request_count": 0,
    "network_request_count": 0,
    "authority_expanded": False,
}))
