import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.reasoning_alpha_checkpoint import build_reasoning_alpha_checkpoint

passed = 0


def require(value):
    global passed
    if not value:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    cognition = runtime / "cognition"
    cognition.mkdir(parents=True)
    (cognition / "ordinary_conversation_turns.json").write_text(
        json.dumps({
            "turns": [
                {
                    "operation_id": "conversation_test",
                    "completion_state": "completed",
                    "user_content_stored": False,
                    "assistant_content_stored": False,
                    "authority_broadened": False,
                    "action_executed": False,
                }
            ]
        }),
        encoding="utf-8",
    )
    (runtime / "private-canary.txt").write_text("PRIVATE CHECKPOINT CANARY", encoding="utf-8")
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_reasoning_alpha_checkpoint(runtime, source_root=ROOT)

    require(report["contract_version"] == "v1150.9")
    require(report["checkpoint_id"] == "reasoning-alpha:v1150.9")
    require(report["ok"] and report["status"] == "reasoning_alpha_candidate")
    require(report["passed"] == report["total"] == 22)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["summary"]["resolved_integration_finding_count"] == 3)
    require(report["summary"]["registered_checkpoint_count"] >= 177)
    require(report["summary"]["ordinary_turn_count"] == 1)
    require(report["summary"]["prompt_character_budget"] == 1800)
    require(report["summary"]["cognitive_item_budget"] == 6)
    require(report["summary"]["privacy_forbidden_entry_count"] == 0)
    require(report["summary"]["privacy_content_finding_count"] == 0)
    require(len(report["remaining_limitations"]) == 4)
    require(report["read_only"] and not report["post_available"] and report["content_free"])
    require(report["authority_preserved"])
    require(report["desktop_verification_pending"] and report["native_provider_certification_pending"])
    require(report["operator_promotion_required"])
    require(not report["consciousness_proven"] and not report["sentience_proven"] and not report["personhood_proven"])
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "plan_created", "approval_created",
        "authorization_created", "installation_performed", "upgrade_performed",
        "rollback_performed", "packaging_performed", "promotion_performed",
        "certification_performed",
    )))
    serialized = json.dumps(report, sort_keys=True)
    require("PRIVATE CHECKPOINT CANARY" not in serialized)
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "prompt_exposed",
        "reflection_text_exposed", "memory_text_exposed", "provider_payload_exposed",
        "hidden_reasoning_exposed",
    )))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "reasoning-alpha-checkpoint",
            source_root=ROOT,
            runtime_root=runtime,
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"])
        daily = dispatch_registered_checkpoint(
            "conversation-daily-evaluation-checkpoint",
            source_root=ROOT,
            runtime_root=runtime,
        )
        require(daily["read_only"] and not daily["source_modified"] and not daily["runtime_mutated"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/reasoning-alpha-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1150.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/reasoning-alpha-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old

with tempfile.TemporaryDirectory() as td:
    import_runtime = Path(td) / "import-runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(import_runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.local_brain"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(imported.returncode == 0 and not (import_runtime / "settings.json").exists())

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "reasoning-alpha-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1150.9")

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "reasoning-alpha-checkpoint"), None)
require(row is not None and row["builder"] == "build_reasoning_alpha_checkpoint")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "reasoning-alpha-checkpoint-panel" in dashboard
    and "/api/cognition/reasoning-alpha-checkpoint" in dashboard
    and "refreshReasoningAlphaCheckpoint" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) >= (1150, 9) and tuple(map(int, previous.groups())) >= (1150, 8))
require("v1150.9 Reasoning Alpha Read-Only Checkpoint" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
require("v1151.2 Evidence-Grounded Reflection Foundations" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))

print(json.dumps({"passed": passed, "total": 36, "suite": "v1150.9"}))
