from __future__ import annotations

"""Exact four-turn v1500.9.2 acceptance contract."""

import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)

runtime = tempfile.TemporaryDirectory(prefix="eidolon-v1500-9-2-")
os.environ["EIDOLON_DATA_DIR"] = runtime.name

from active_conversation_facts import resolve_active_conversation_facts
from chat_action_router import propose_chat_action
from conversation_quality import should_analyze_chat_action
from dashboard_chat_console import _resolve_governed_operator_turn
from release_authority import MILESTONE, NEXT_BOUNDED_UNIT

passed = failed = 0


def check(name: str, condition: bool, details: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, details)


first_message = "What specifically changed in v1500.9?"
first = resolve_active_conversation_facts(first_message, ())
check("turn one is grounded release knowledge", first.state == "grounded_current_release", first)
check("turn one names concrete v1500.9 repairs", "family and project-association recall" in first.response, first.response)

history = ({"user_message": first_message, "assistant_response": first.response},)
second = resolve_active_conversation_facts("What evidence are you using for that answer?", history)
check("turn two is evidence explanation", second.state == "grounded_release_evidence", second)
check("turn two names evidence sources", "release_authority.py" in second.response and "README_RELEASE_HISTORY.md" in second.response, second.response)
check("turn two includes sha256 evidence", "SHA-256 evidence digest" in second.response, second.response)
check("turn two does not merely repeat turn one", second.response != first.response, second.response)

third_message = (
    "Inspect your local release metadata and README files read-only, then tell me what changed in v1500.9. "
    "Do not guess, and do not modify anything."
)
third_grounding = resolve_active_conversation_facts(third_message, history)
check("turn three is not swallowed by immediate grounding", third_grounding.response == "", third_grounding)
check("turn three is recognized as governed work", should_analyze_chat_action(third_message), third_message)
action = propose_chat_action(
    third_message,
    save=True,
    deduplication_key="v1500-9-2-exact-acceptance",
    conversation_session_id="acceptance-session",
)
check("turn three creates one release-summary action", action["intent"] == "release_summary" and action["function_name"] == "release_summary", action)
resolution = _resolve_governed_operator_turn(action) or {}
execution = resolution.get("execution") or {}
check("turn three executes exactly once", execution.get("ok") is True and execution.get("replayed") is False, execution)
check("turn three has a valid completed receipt", resolution.get("receipt_valid") is True and (resolution.get("receipt") or {}).get("completion_state") == "completed", resolution)
check("turn three contacts no provider", resolution.get("provider_request_count") == 0, resolution)
check("turn three response names its action", str(action["id"]) in str(resolution.get("response") or ""), resolution.get("response"))
check("turn three response contains verified release result", MILESTONE in str(resolution.get("response") or ""), resolution.get("response"))

fourth = resolve_active_conversation_facts("What should we work on next, and why?", history)
check("turn four is grounded roadmap guidance", fourth.state == "grounded_next_bounded_unit", fourth)
check("turn four names current objective and rationale", NEXT_BOUNDED_UNIT in fourth.response and "review, pace, and reconcile" in fourth.response, fourth.response)
check("turn four keeps final authority with operator", "remain your decisions" in fourth.response, fourth.response)

runtime.cleanup()
print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.9.2-conversation-evidence-boundary",
    "provider_contacted": False,
    "source_modified": False,
    "authority_granted": False,
})
if failed:
    raise SystemExit(1)
