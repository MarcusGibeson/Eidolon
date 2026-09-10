from __future__ import annotations

"""The legacy dashboard-chat import must stay idempotent while the directory is live.

The chat surface still writes a turn file into data/dashboard_chat on every
exchange, so the directory the import treats as a frozen archive keeps changing.
Deriving the archive session's identity from a digest of that directory forked a
fresh copy of the whole transcript on every new turn, rewrote every turn under
the global session lock, and left hundreds of duplicate sessions behind. Every
conversation request queued on that lock, so chat stopped responding at all.

These checks cover the identity staying stable, only new turns being appended,
and an unchanged directory being skipped without re-reading every file.
"""

import json
import os
from pathlib import Path
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2730-9-6-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import conversation_sessions as sessions


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


LEGACY_TURN_COUNT = 25
sessions.LEGACY_DASHBOARD_CHAT_DIR.mkdir(parents=True, exist_ok=True)


def write_legacy_turn(index: int) -> None:
    turn_id = f"dash_chat_2026060{index // 10}_{index:06d}_msg"
    (sessions.LEGACY_DASHBOARD_CHAT_DIR / f"{turn_id}.json").write_text(
        json.dumps({
            "id": turn_id,
            "type": "dashboard_chat_turn",
            "created_at": f"2026-06-0{1 + index // 50}T10:{index % 60:02d}:00",
            "user_message": f"message {index}",
            "eidolon_response": f"response {index}",
            "use_ai": True,
        }),
        encoding="utf-8",
    )


def archive_sessions() -> list[str]:
    return sorted(path.name for path in sessions.CONVERSATION_SESSIONS_DIR.glob("conversation_session_*.json"))


for turn_index in range(LEGACY_TURN_COUNT):
    write_legacy_turn(turn_index)

first = sessions.migrate_legacy_dashboard_chat_turns()
require(first["imported_turn_count"] == LEGACY_TURN_COUNT, "first_import_takes_every_legacy_turn")
require(len(archive_sessions()) == 1, "first_import_creates_one_archive_session")
archive_id = str(first["session_id"])

second = sessions.migrate_legacy_dashboard_chat_turns()
require(second["status"] == "current", "unchanged_directory_reports_current")
require(second["imported_turn_count"] == 0, "unchanged_directory_imports_nothing")
require(second["session_id"] == archive_id, "unchanged_directory_keeps_the_same_archive")
require(len(archive_sessions()) == 1, "unchanged_directory_creates_no_second_archive")

# The live chat surface keeps writing here. This is the case that forked a whole
# new archive session per turn and rewrote the entire transcript under the lock.
write_legacy_turn(LEGACY_TURN_COUNT)
third = sessions.migrate_legacy_dashboard_chat_turns()
require(third["imported_turn_count"] == 1, "a_new_live_turn_imports_only_itself")
require(third["session_id"] == archive_id, "a_new_live_turn_does_not_fork_the_archive")
require(len(archive_sessions()) == 1, "a_new_live_turn_creates_no_duplicate_session")

archived = sessions.load_conversation_session(archive_id, include_turns=True)
require(int(archived["turn_count"]) == LEGACY_TURN_COUNT + 1, "archive_holds_every_turn_exactly_once")
turn_ids = [str(turn.get("id")) for turn in archived["turns"]]
require(len(turn_ids) == len(set(turn_ids)), "archive_contains_no_duplicated_turn")

# A fresh process has no in-memory signature and must still skip the rescan.
sessions._LEGACY_IMPORT_SIGNATURE_SEEN = ""
started = time.monotonic()
fourth = sessions.migrate_legacy_dashboard_chat_turns()
elapsed = time.monotonic() - started
require(fourth["status"] == "current", "a_fresh_process_reuses_the_persisted_marker")
require(fourth["imported_turn_count"] == 0, "a_fresh_process_reimports_nothing")
require(len(archive_sessions()) == 1, "a_fresh_process_creates_no_duplicate_session")
require(elapsed < 1.0, "an_unchanged_directory_is_skipped_without_rereading_every_file")

# A corrupt marker must not take the conversation surface down with it.
sessions._atomic_write(sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE, {
    "type": "legacy_dashboard_chat_import",
    "schema_version": "1",
    "session_id": "not-a-valid-session-id",
    "source_signature": "stale",
    "source_turn_count": 0,
})
sessions._LEGACY_IMPORT_SIGNATURE_SEEN = ""
recovered = sessions.migrate_legacy_dashboard_chat_turns()
require(recovered.get("status") in {"imported", "reconciled", "current"}, "a_corrupt_marker_does_not_raise")

print(json.dumps({"suite": "v2730.9.6-legacy-dashboard-chat-import", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
