from __future__ import annotations

"""Rendering a transcript must read the action catalogue once, not once per turn.

Each rendered turn resolved its governed action separately, and every resolution
re-read and re-parsed every file in the chat-actions directory. A 120-turn window
against 121 action files meant roughly 14,500 reads for one snapshot. Each call
also took the persistent index lock and deep-copied the projection, so concurrent
snapshot requests stacked up behind one another and the dashboard's thread count
climbed until it stopped responding.

Reading the catalogue once per render is the whole fix, so the count is what
these checks pin.
"""

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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-3-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import chat_action_router
import dashboard_chat_console


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


CATALOGUE = [
    {"id": f"chat_action_{index:04d}", "deduplication_key": f"turn-{index}", "status": "executed",
     "intent": "bounded_research_create", "created_at": "2026-09-10T00:00:00", "result": {}}
    for index in range(40)
]

calls = {"console": 0, "router": 0}


def counting_list_chat_actions(status: str = "", include_closed: bool = True):
    calls["console"] += 1
    return [dict(row) for row in CATALOGUE]


def router_list_chat_actions(status: str = "", include_closed: bool = True):
    calls["router"] += 1
    return [dict(row) for row in CATALOGUE]


dashboard_chat_console.list_chat_actions = counting_list_chat_actions
chat_action_router.list_chat_actions = router_list_chat_actions


def turns(count: int) -> list[dict]:
    return [
        {"id": f"turn-{index}", "created_at": "2026-09-10T09:00:00+00:00",
         "user_message": f"question {index}", "assistant_response": f"answer {index}",
         "completion_state": "completed", "success": True}
        for index in range(count)
    ]


def render(count: int) -> int:
    calls["console"] = 0
    dashboard_chat_console._render_session_transcript("session-1", turns(count))
    return calls["console"]


one = render(1)
require(one <= 1, f"a_single_turn_reads_the_catalogue_at_most_once (saw {one})")

many = render(120)
require(many <= 1, f"a_120_turn_transcript_reads_the_catalogue_once (saw {many})")
require(many == one, "catalogue_reads_do_not_grow_with_turn_count")

empty = render(0)
require(empty == 0, "an_empty_transcript_reads_the_catalogue_not_at_all")

# The lookup must still find the action for its turn.
index = dashboard_chat_console._actions_by_deduplication_key()
require(index.get("turn-7", {}).get("id") == "chat_action_0007",
        "a_turn_still_resolves_to_its_own_action")
require(len(index) == len(CATALOGUE), "every_catalogue_entry_is_indexed")

portal = dashboard_chat_console._current_action_portal_for_turn(
    {"id": "turn-3"}, actions_by_key=index)
require(portal, "a_turn_with_an_action_still_renders_a_portal")
require(dashboard_chat_console._current_action_portal_for_turn(
    {"id": "turn-unknown"}, actions_by_key=index) in (None, {}),
    "a_turn_without_an_action_renders_none")

# Falling back without a prebuilt index must still work for standalone callers.
calls["console"] = 0
standalone = dashboard_chat_console._current_action_portal_for_turn({"id": "turn-5"})
require(standalone, "a_standalone_lookup_still_resolves_without_a_prebuilt_index")
require(calls["console"] == 1, "a_standalone_lookup_reads_the_catalogue_once")

# --- resolving a concrete id must not load the catalogue at all ---------------

calls["router"] = 0
require(chat_action_router.resolve_chat_action_id("chat_action_0002") == "chat_action_0002",
        "a_concrete_action_id_resolves_to_itself")
require(calls["router"] == 0, "a_concrete_action_id_does_not_read_the_catalogue")

calls["router"] = 0
resolved = chat_action_router.resolve_chat_action_id("latest")
require(resolved == "chat_action_0000", "an_alias_still_resolves_against_the_catalogue")
require(calls["router"] == 1, "an_alias_reads_the_catalogue_once")

calls["router"] = 0
chat_action_router.resolve_chat_action_id("latest-executed")
require(calls["router"] == 1, "a_status_alias_still_reads_the_catalogue")

calls["router"] = 0
chat_action_router.resolve_chat_action_id("")
require(calls["router"] == 0, "an_empty_identifier_reads_nothing")

print(json.dumps({"suite": "v2731.0.3-transcript-action-lookup", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
