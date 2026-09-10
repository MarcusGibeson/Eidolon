from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import chat_action_router as router
from command_runner import CommandRunResult


def _wait_for(path: Path, description: str, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while not path.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for {description}.")
        time.sleep(0.02)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--ready", required=True)
    parser.add_argument("--go", required=True)
    parser.add_argument("--entered", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--invocations", required=True)
    args = parser.parse_args()

    runtime_root = Path(args.runtime_root)
    ready_path = Path(args.ready)
    go_path = Path(args.go)
    entered_path = Path(args.entered)
    release_path = Path(args.release)
    invocations_path = Path(args.invocations)

    router.CHAT_ACTIONS_DIR = runtime_root / "chat_actions"
    router.CHAT_ACTIONS_README = router.CHAT_ACTIONS_DIR / "README.md"
    router.store_memory = lambda *_args, **_kwargs: None

    def fake_run(command: str, dry_run: bool = False, timeout_seconds: int | None = None) -> CommandRunResult:
        with invocations_path.open("a", encoding="utf-8") as file:
            file.write(f"{args.worker_name}\n")
            file.flush()
        entered_path.write_text("entered", encoding="utf-8")
        _wait_for(release_path, "execution release")
        return CommandRunResult(
            True,
            command,
            ["python"],
            return_code=0,
            message="Diagnostics completed.",
        )

    router.run_approved_command = fake_run
    ready_path.write_text("ready", encoding="utf-8")
    _wait_for(go_path, "claim start")
    result = router.execute_chat_action(args.action_id, timeout_seconds=180)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
