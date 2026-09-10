from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import dashboard_chat_console as console


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--barrier", required=True)
    parser.add_argument("--writer", required=True)
    args = parser.parse_args()

    store = Path(args.store)
    barrier = Path(args.barrier)
    store.mkdir(parents=True, exist_ok=True)
    console.DASHBOARD_CHAT_DIR = store
    console.DASHBOARD_CHAT_README = store / "README.md"

    ready = barrier / f"ready-{args.writer}"
    release = barrier / "release"
    barrier.mkdir(parents=True, exist_ok=True)
    ready.write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 10
    while not release.exists():
        if time.monotonic() >= deadline:
            print(json.dumps({"ok": False, "error": "barrier_timeout"}))
            return 2
        time.sleep(0.01)

    turn = {
        "id": "dash_chat_cross_process_same_turn",
        "type": "dashboard_chat_turn",
        "created_at": "2026-07-19T00:00:00",
        "session_id": "conversation_session_fixture",
        "user_message": "fixture",
        "eidolon_response": f"writer-{args.writer}",
        "writer": args.writer,
    }
    console.save_dashboard_chat_turn(turn)
    print(json.dumps({"ok": True, "writer": args.writer}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
