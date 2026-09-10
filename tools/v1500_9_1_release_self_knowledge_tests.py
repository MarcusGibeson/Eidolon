from __future__ import annotations

"""Focused v1500.9.1 receipt-bound release self-knowledge regressions."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)

from active_conversation_facts import resolve_active_conversation_facts
from chat_action_router import propose_chat_action
from conversational_action_portal_v1104 import classify_conversation_action
from conversational_command_integration import build_conversational_command_integration
from natural_conversation_command_distinction import distinguish_natural_conversation_and_command
from release_self_knowledge import inspect_current_release
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


request = (
    "Inspect your local release metadata and README files read-only, then tell me what changed in v1500.9. "
    "Do not guess, and do not modify anything."
)
distinction = distinguish_natural_conversation_and_command(request)
check("grouped release inspection is one objective", distinction["live_action_clause_count"] == 1, distinction)
check("grouped release inspection needs no false clarification", distinction["requires_clarification"] is False, distinction)
integration = build_conversational_command_integration(request)
check("grouped inspection routes as one action", integration["status"] == "action_request_routed", integration)
check("full grouped request is retained for routing", "README files" in integration["routing_text"], integration)
portal = classify_conversation_action(request)
check("portal selects release summary", portal["intent"] == "release_summary", portal)
check("release inspection remains a direct bounded function", portal["execution_mode"] == "direct_function" and portal["blocked"] is False, portal)
action = propose_chat_action(request, save=False)
check("router selects release summary", action["intent"] == "release_summary", action)
check("router uses the bounded release function", action["function_name"] == "release_summary", action)

summary = inspect_current_release()
check("allowlisted release evidence is complete", summary.ok and summary.inspected_file_count == 4, summary)
check("summary names current repair checkpoint", MILESTONE in summary.summary, summary.summary)
check("summary names real conversation repairs", "grounded self-reflection" in summary.summary and "receipt-backed repeated diagnostics" in summary.summary, summary.summary)
check("summary avoids invented generic release claims", all(term not in summary.summary.casefold() for term in ("knowledge base", "natural language processing capabilities", "content filters")), summary.summary)
public = summary.public_result()
check("public result is redacted and provider-free", public["redacted"] and not public["provider_contacted"], public)
check("public result grants no authority or mutation", not public["authority_granted"] and not public["source_modified"], public)
check("public result carries evidence digest", len(public["evidence_digest"]) == 64, public)

direct = resolve_active_conversation_facts("What specifically changed in v1500.9?", ())
check("direct current-release question is grounded", direct.state == "grounded_current_release", direct)
check("direct answer uses authoritative summary", direct.response == summary.summary, direct.response)
follow_up = resolve_active_conversation_facts(
    "What evidence are you using, and what were the actual changes?",
    ({"user_message": "What changed in v1500.9?", "assistant_response": "A prior answer about v1500.9."},),
)
check("release evidence follow-up has distinct grounding", follow_up.state == "grounded_release_evidence", follow_up)
check("release follow-up does not claim missing access", "don't have direct access" not in follow_up.response.casefold(), follow_up.response)
check("release follow-up names all four source classes", all(name in follow_up.response for name in ("release_authority.py", "README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md")), follow_up.response)
check("release follow-up includes evidence digest", summary.evidence_digest in follow_up.response, follow_up.response)
check("release follow-up distinguishes provider text from evidence", "did not use provider-generated claims" in follow_up.response, follow_up.response)

explicit_grounding = resolve_active_conversation_facts(request, ())
check("explicit inspection bypasses immediate answer", explicit_grounding.response == "", explicit_grounding)
check("explicit inspection remains available to governed routing", explicit_grounding.state in {"none", "active_fact_context"}, explicit_grounding)

next_work = resolve_active_conversation_facts("What should we work on next, and why?", ())
check("next-work question is grounded", next_work.state == "grounded_next_bounded_unit", next_work)
check("next-work answer names current supervised initiative unit", NEXT_BOUNDED_UNIT in next_work.response and "supervised-initiative queue" in next_work.response, next_work.response)
check("next-work answer preserves operator authority", "remain your decisions" in next_work.response, next_work.response)

from conversation_quality import should_analyze_chat_action
check("dashboard analysis admits grouped inspection", should_analyze_chat_action(request), request)
dashboard = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
check("dashboard admits only exact release summary function", 'action.get("intent") == "release_summary"' in dashboard and 'action.get("function_name") == "release_summary"' in dashboard)
check("dashboard uses function result as verified output", 'result.get("message") if release_summary_function' in dashboard)

serialized = json.dumps(public, sort_keys=True)
check("receipt exposes no private paths or source filenames", all(term not in serialized for term in (str(ROOT), "README_NEXT_STEPS.md", "release_authority.py")), serialized)

verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
check("v1500.9.1 suite registered exactly once", verifier.count("v1500_9_1_release_self_knowledge_tests.py") == 1)

print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.9.1-release-self-knowledge",
    "provider_contacted": False,
    "runtime_mutated": False,
    "authority_granted": False,
})
if failed:
    raise SystemExit(1)
