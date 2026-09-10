from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import chat_action_router as router


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--claimant", default="cli")
    args = parser.parse_args()

    runtime_root = Path(args.runtime_root)
    router.CHAT_ACTIONS_DIR = runtime_root / "chat_actions"
    router.CHAT_ACTIONS_README = router.CHAT_ACTIONS_DIR / "README.md"
    router.store_memory = lambda *_args, **_kwargs: None

    with router._chat_action_storage_lock(f"action:{args.action_id}"):
        action = router.load_chat_action(args.action_id)
        if not action:
            raise SystemExit("action not found")
        claimed = router._claim_execution_attempt(action, claimant=args.claimant)
    print(json.dumps({
        "action_id": claimed.get("id"),
        "status": claimed.get("status"),
        "attempt": claimed.get("execution_attempt"),
        "claimant": (claimed.get("claim_owner") or {}).get("scope"),
    }, sort_keys=True))
    # Exiting without completion intentionally simulates a dashboard or CLI process
    # ending after its durable claim but before terminal evidence is written.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
