"""v2731.10.1 - a decided proposal must not suppress the next request for the same thing.

Regression for the live dead end of 2026-09-18: a review of G-EVID1 was proposed, confirmed and run. Every later
"Review G-EVID1 independently." then matched the finished action by deduplication key and returned it, so no new
proposal was ever created. The reply named an action id while nothing was waiting, and the confirmation that followed
answered "Nothing waiting matches that name" - an unbreakable loop from the chat window.

    python tools/v2731_10_1_proposal_lifecycle_tests.py
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="proposal-lifecycle-") as tmp:
        import os

        os.environ["EIDOLON_DATA_DIR"] = tmp
        for module in [m for m in list(sys.modules) if m in ("chat_action_router", "experiment_review")]:
            del sys.modules[module]
        import chat_action_router as r
        import conversational_experiment_review as review_adapter

        r.CHAT_ACTIONS_DIR = Path(tmp) / "chat_actions"
        r.CHAT_ACTIONS_DIR.mkdir(parents=True, exist_ok=True)

        KEY = "experiment-review:q-cap-demo"
        MANIFEST = "a" * 64
        review_adapter.find_package = lambda name, root=None: ({"package_id": "Q-CAP-DEMO", "manifest_sha256": MANIFEST}
                                                               if name == "Q-CAP-DEMO" else None)

        def action(status: str, ident: str) -> dict:
            row = {"id": ident, "function_name": "experiment_review_start", "status": status,
                    "deduplication_key": KEY, "created": "2026-09-18T00:00:00Z",
                    "created_at": r._now(),
                    "function_args": {"package_id": "Q-CAP-DEMO", "manifest_sha256": MANIFEST}}
            if status == "proposed":
                r._ensure_confirmation_contract(row)
            return row

        # --- 1. only open statuses are dedupe candidates -------------------------------------------------------
        require(r._OPEN_ACTION_STATUSES == frozenset({"proposed", "approval_required"}),
                "only_undecided_proposals_are_dedupe_candidates")
        for decided in ("executed", "cancelled", "failed", "completed", "running"):
            require(decided not in r._OPEN_ACTION_STATUSES,
                    f"a_decided_action_is_not_a_dedupe_candidate:{decided}")

        # --- 2. an open proposal still collapses a repeat ask --------------------------------------------------
        r.save_chat_action(action("proposed", "act_open"))
        rows = [x for x in r.list_chat_actions(include_closed=False)
                if x.get("deduplication_key") == KEY and str(x.get("status") or "") in r._OPEN_ACTION_STATUSES]
        require(len(rows) == 1 and rows[0]["id"] == "act_open",
                "an_open_proposal_is_found_so_asking_twice_does_not_stack_two")

        # --- 3. once decided, it no longer matches, so a new proposal can be made -------------------------------
        for status in ("executed", "cancelled"):
            done = r.load_chat_action("act_open") or action("proposed", "act_open")
            done["status"] = status
            r.save_chat_action(done)
            rows = [x for x in r.list_chat_actions(include_closed=True)
                    if x.get("deduplication_key") == KEY and str(x.get("status") or "") in r._OPEN_ACTION_STATUSES]
            require(not rows, f"a_{status}_action_no_longer_blocks_a_new_proposal")

        # --- 4. the exact live sequence cannot recur -----------------------------------------------------------
        r.save_chat_action(action("executed", "act_done"))
        waiting = [x for x in r.pending_confirmable_actions() if r._action_target_name(x) == "Q-CAP-DEMO"]
        require(not waiting, "a_finished_review_leaves_nothing_waiting")
        candidates = [x for x in r.list_chat_actions(include_closed=True)
                      if x.get("deduplication_key") == KEY and str(x.get("status") or "") in r._OPEN_ACTION_STATUSES]
        require(not candidates,
                "and_it_no_longer_answers_the_dedupe_lookup_so_the_next_ask_creates_a_fresh_proposal")

        r.save_chat_action(action("proposed", "act_second"))
        waiting = [x for x in r.pending_confirmable_actions() if r._action_target_name(x) == "Q-CAP-DEMO"]
        require(len(waiting) == 1 and waiting[0]["id"] == "act_second",
                "the_fresh_proposal_is_the_one_a_confirmation_resolves_against")
        require(bool(r.waiting_proposal_for("Q-CAP-DEMO")),
                "confirm_by_name_now_finds_the_new_proposal")

        # --- 5. the source no longer deduplicates against history anywhere -------------------------------------
        source = (ROOT / "conscious_agent" / "chat_action_router.py").read_text(encoding="utf-8")
        require('include_closed=True) if item.get("deduplication_key")' not in source,
                "no_dedupe_lookup_matches_closed_actions_any_more")
        require(source.count("_OPEN_ACTION_STATUSES") >= 6,
                "every_dedupe_lookup_filters_on_open_status")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2731.10.1-proposal-lifecycle", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
