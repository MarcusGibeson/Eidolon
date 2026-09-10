from __future__ import annotations

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
from conscious_agent.evidence_grounded_reflection import build_evidence_grounded_reflection
from conscious_agent.reflection_alpha_checkpoint import build_reflection_alpha_checkpoint
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
    runtime.mkdir(parents=True)
    base = build_evidence_grounded_reflection(
        operation_id="checkpoint-base",
        user_message="We are reviewing the greenhouse temperature schedule for Tuesday.",
        assistant_response="The greenhouse schedule currently uses Tuesday.",
        thought={"thought": "Preserve the current greenhouse schedule."},
        desires={},
        prior_reflections=[],
    )
    correction = build_evidence_grounded_reflection(
        operation_id="checkpoint-correction",
        user_message="Actually, the greenhouse temperature schedule should use Thursday instead.",
        assistant_response="The corrected greenhouse schedule uses Thursday.",
        thought={"thought": "Prefer the explicit user correction."},
        desires={},
        prior_reflections=[base],
    )
    (runtime / "memories.json").write_text(json.dumps([base, correction]), encoding="utf-8")
    (runtime / "private-canary.txt").write_text("PRIVATE REFLECTION CHECKPOINT CANARY", encoding="utf-8")
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_reflection_alpha_checkpoint(runtime, source_root=ROOT)

    require(report["contract_version"] == "v1151.9")
    require(report["checkpoint_id"] == "reflection-alpha:v1151.9")
    require(report["ok"] and report["status"] == "reflection_alpha_candidate")
    require(report["passed"] == report["total"] == 24)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["summary"]["synthetic_contract_check_count"] == 13)
    require(report["summary"]["registered_checkpoint_count"] >= 178)
    require(report["summary"]["runtime_reflection_count"] == 2)
    require(report["summary"]["runtime_operator_correction_count"] == 1)
    require(report["summary"]["runtime_supersession_count"] == 1)
    require(report["summary"]["runtime_quarantined_count"] == 0)
    require(report["summary"]["maximum_evidence_items"] == 4)
    require(report["summary"]["maximum_evidence_excerpt_chars"] == 220)
    require(report["summary"]["maximum_revision_depth"] == 12)
    require(report["summary"]["privacy_forbidden_entry_count"] == 0)
    require(report["summary"]["privacy_content_finding_count"] == 0)
    require(len(report["remaining_limitations"]) == 5)
    require(report["read_only"] and not report["post_available"] and report["content_free"])
    require(report["authority_preserved"] and report["operator_promotion_required"])
    require(report["desktop_verification_pending"] and report["native_provider_certification_pending"])
    require(not report["consciousness_proven"] and not report["sentience_proven"] and not report["personhood_proven"])
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "plan_created", "approval_created",
        "authorization_created", "installation_performed", "upgrade_performed",
        "rollback_performed", "packaging_performed", "promotion_performed",
        "certification_performed",
    )))
    serialized = json.dumps(report, sort_keys=True)
    require("PRIVATE REFLECTION CHECKPOINT CANARY" not in serialized)
    require("greenhouse" not in serialized.lower() and "thursday" not in serialized.lower())
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "prompt_exposed",
        "reflection_text_exposed", "memory_text_exposed", "evidence_text_exposed",
        "provider_payload_exposed", "hidden_reasoning_exposed",
    )))
    require(report["evidence"]["runtime_reflection_health"]["all_content_omitted"])
    require(report["evidence"]["runtime_reflection_health"]["all_bounds_respected"])
    require(report["evidence"]["runtime_reflection_health"]["all_governance_boundaries_preserved"])
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "reflection-alpha-checkpoint",
            source_root=ROOT,
            runtime_root=runtime,
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/reflection-alpha-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1151.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/reflection-alpha-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    empty = build_reflection_alpha_checkpoint(runtime, source_root=ROOT)
    require(empty["ok"] and empty["summary"]["runtime_reflection_count"] == 0)
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "reflection-alpha-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=240,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1151.9")
    require(not (Path(td) / "runtime").exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "reflection-alpha-checkpoint"), None)
require(row is not None and row["builder"] == "build_reflection_alpha_checkpoint")
require(registry["checkpoint_count"] >= 178)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as td:
    reasoning_runtime = Path(td) / "runtime"
    reasoning_runtime.mkdir(parents=True)
    reasoning = build_reasoning_alpha_checkpoint(reasoning_runtime, source_root=ROOT)
    require(reasoning["ok"] and reasoning["passed"] == reasoning["total"] == 22)

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "reflection-alpha-checkpoint-panel" in dashboard
    and "/api/cognition/reflection-alpha-checkpoint" in dashboard
    and "refreshReflectionAlphaCheckpoint" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) >= (1151, 9) and tuple(map(int, previous.groups())) >= (1151, 8))
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1151.9 Reflection Alpha Read-Only Checkpoint" in history)
require("v1151.6-v1151.8 Reflection Reliability and Adversarial Reconciliation" in history)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
require(any(token in next_steps for token in ("v1152.0-v1152.2 Belief Revision and Uncertainty Foundations", "v1153.0-v1153.2 Multi-Step Deliberation Foundations", "v1154.0-v1154.2 Deliberation Outcome and Decision-Boundary Foundations", "v1155.0-v1155.2", "v1156.0-v1156.2")))
require((ROOT / "tools" / "v1151_9_full_registry_validation.py").exists())

print(json.dumps({"passed": passed, "total": 48, "suite": "v1151.9"}))
