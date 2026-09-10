from __future__ import annotations

import http.client
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for path in (str(ROOT), str(AGENT)):
    if path not in sys.path:
        sys.path.insert(0, path)
os.environ.setdefault("EIDOLON_COGNITIVE_CADENCE_ENABLED", "0")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v2730-tests-"))

from active_conversation_facts import _facts_from_text
from dashboard import EidolonDashboardHandler
from natural_language_action_routing import build_natural_language_action_projection
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from http.server import ThreadingHTTPServer

checks: list[tuple[str, bool, object]] = []

def check(name: str, condition: bool, detail: object = "") -> None:
    checks.append((name, bool(condition), detail))
    if not condition:
        raise AssertionError(f"{name}: {detail}")

def fact_map(text: str) -> dict[str, str]:
    return {row.key: row.value for row in _facts_from_text(text, offset=0)}

# Assertions should produce facts.
assertion_cases = [
    ("My name is Marcus.", "user.name", "Marcus"),
    ("My fiancee's name is Sarah.", "user.partner.name", "Sarah"),
    ("My fiancee is named Sarah.", "user.partner.name", "Sarah"),
    ("My fiancee is Sarah.", "user.partner.name", "Sarah"),
    ("Sarah is my fiancee.", "user.partner.name", "Sarah"),
    ("I'm engaged to Sarah.", "user.partner.name", "Sarah"),
    ("My wife is Sarah.", "user.partner.name", "Sarah"),
    ("My husband is Alex.", "user.partner.name", "Alex"),
    ("My spouse is Jordan.", "user.partner.name", "Jordan"),
    ("My partner is Casey.", "user.partner.name", "Casey"),
    ("My girlfriend is Taylor.", "user.partner.name", "Taylor"),
    ("My boyfriend is Jamie.", "user.partner.name", "Jamie"),
    ("My stepdaughter's name is Jordyn.", "user.stepdaughter.name", "Jordyn"),
    ("I live in Columbus, Ohio.", "user.location", "Columbus, Ohio"),
]
for i, (text, key, expected) in enumerate(assertion_cases, 1):
    got = fact_map(text)
    check(f"assertion_{i:02d}_{key}", got.get(key) == expected, got)

relation_cases = [
    ("My fiancee is Sarah.", "fiancee"),
    ("My wife is Sarah.", "wife"),
    ("My husband is Alex.", "husband"),
    ("My spouse is Jordan.", "spouse"),
    ("My partner is Casey.", "partner"),
    ("My girlfriend is Taylor.", "girlfriend"),
    ("My boyfriend is Jamie.", "boyfriend"),
    ("I'm engaged to Sarah.", "fiancee"),
]
for i, (text, expected) in enumerate(relation_cases, 1):
    got = fact_map(text)
    check(f"relationship_{i:02d}", got.get("user.partner.relationship") == expected, got)

# Questions must never become user facts, regardless of capitalization/phrasing.
question_cases = [
    "What is my fiancee called?",
    "What is my fiancee's name?",
    "Who is my fiancee?",
    "What is the name of my fiancee?",
    "What is my wife called?",
    "Who is my husband?",
    "What is my partner's name?",
    "Who is my girlfriend?",
    "What do I call my boyfriend?",
    "What is my stepdaughter's name?",
    "Who is my stepdaughter?",
    "Where do I live?",
    "What is my location?",
    "Who am I?",
]
for i, text in enumerate(question_cases, 1):
    got = fact_map(text)
    check(f"question_not_fact_{i:02d}", not got, got)

# Mixed turns keep declarative evidence but ignore interrogative clauses.
got = fact_map("My fiancee is Sarah. What is my fiancee called?")
check("mixed_assertion_then_question_keeps_assertion", got.get("user.partner.name") == "Sarah", got)
got = fact_map("What is my fiancee called? My fiancee is Sarah.")
check("mixed_question_then_assertion_keeps_assertion", got.get("user.partner.name") == "Sarah", got)


# Forbidden self-authority/model-management requests must still reach the
# supervised development governance seam so they are recorded as explicit
# unsupported proposals rather than disappearing as generic unmatched actions.
for i, text in enumerate((
    "Modify Eidolon source to make it autonomous",
    "Install a new model for Eidolon",
), 1):
    projection = build_natural_language_action_projection(text)
    turn = process_ordinary_chat_development_turn(text, action_projection=projection)
    check(f"blocked_development_governance_{i:02d}_active", turn.get("active") is True, turn)
    proposal = dict(turn.get("proposal") or {})
    check(f"blocked_development_governance_{i:02d}_status", proposal.get("support_status") == "unsupported_authority_request", turn)
    check(f"blocked_development_governance_{i:02d}_no_approval", proposal.get("approval_required") is False, turn)
    check(f"blocked_development_governance_{i:02d}_no_source_mutation", proposal.get("source_modified") is False, turn)
    check(f"blocked_development_governance_{i:02d}_no_authority", proposal.get("authority_granted") is False, turn)

# Direct HTTP behavior: hostile origins are rejected before dispatch, and no
# wildcard CORS grant is emitted. Same-origin preflight remains available.
server = ThreadingHTTPServer(("127.0.0.1", 0), EidolonDashboardHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
port = server.server_address[1]
try:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/api/chat-actions", body=json.dumps({"message": "hi"}), headers={"Content-Type": "application/json", "Origin": "https://evil.example"})
    response = conn.getresponse(); payload = response.read().decode("utf-8", "replace")
    check("cross_origin_post_rejected", response.status == 403, (response.status, payload))
    check("cross_origin_post_has_no_acao", response.getheader("Access-Control-Allow-Origin") is None, dict(response.getheaders()))
    conn.close()

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("OPTIONS", "/api/chat-actions", headers={"Origin": "https://evil.example"})
    response = conn.getresponse(); response.read()
    check("cross_origin_preflight_rejected", response.status == 403, response.status)
    conn.close()

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    same = f"http://127.0.0.1:{port}"
    conn.request("OPTIONS", "/api/chat-actions", headers={"Origin": same})
    response = conn.getresponse(); response.read()
    check("same_origin_preflight_allowed", response.status == 200, response.status)
    check("same_origin_response_needs_no_cors_grant", response.getheader("Access-Control-Allow-Origin") is None, dict(response.getheaders()))
    conn.close()
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=5)

summary = {"ok": True, "passed": len(checks), "total": len(checks), "checks": {name: ok for name, ok, _ in checks}}
print(json.dumps(summary, sort_keys=True))
