from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.deliberation_continuity import inspect_deliberation_continuity
from conscious_agent.multi_step_deliberation_alpha_checkpoint import build_multi_step_deliberation_alpha_checkpoint

passed = 0


def require(value: object) -> None:
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
    canary = "PRIVATE MULTI STEP DELIBERATION CHECKPOINT CANARY"
    continuity = {
        "schema_version": 1,
        "contract_version": "v1153.8",
        "sessions": [
            {
                "continuity_id": "private-continuity-id",
                "operation_id": "private-operation-id",
                "session_id": "private-session-id",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "case_count": 1,
                "cases": [
                    {
                        "case_digest": "private-case-digest",
                        "step_count": 4,
                        "completed_step_count": 4,
                        "outcome": "requires_more_evidence",
                        "resolution_permitted": False,
                        "decision_created": False,
                    }
                ],
                "goal_context": [
                    {
                        "goal_id": "private-goal-id",
                        "title": canary,
                        "status": "active",
                        "priority": "high",
                        "blocker_count": 1,
                        "next_action_count": 2,
                        "authority": "context_only",
                    }
                ],
                "goal_context_count": 1,
                "malformed_goal_store_count": 0,
                "user_content_stored": False,
                "belief_content_stored": False,
                "resolution_permitted": False,
                "decision_created": False,
                "action_executed": False,
                "operator_authority_required_for_action": True,
            },
            {
                "continuity_id": "stale-id",
                "operation_id": "stale-operation",
                "session_id": "private-session-id",
                "recorded_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
                "case_count": 0,
                "cases": [],
                "goal_context": [],
                "goal_context_count": 0,
                "user_content_stored": False,
                "belief_content_stored": False,
                "resolution_permitted": False,
                "decision_created": False,
                "action_executed": False,
                "operator_authority_required_for_action": True,
            },
        ],
        "pending": [
            {
                "pending_id": "private-pending-id",
                "operation_id": "private-pending-operation",
                "session_id": "private-session-id",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "content_stored": False,
            }
        ],
    }
    (cognition / "deliberation_continuity.json").write_text(json.dumps(continuity), encoding="utf-8")
    (runtime / "goals.json").write_text(json.dumps({"goals": [{"id": "g1", "title": canary, "description": canary, "status": "active", "priority": "high", "blockers": [], "next_actions": []}]}), encoding="utf-8")
    (runtime / "private-canary.txt").write_text(canary, encoding="utf-8")

    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_multi_step_deliberation_alpha_checkpoint(runtime, source_root=ROOT)

    require(report["contract_version"] == "v1153.9")
    require(report["checkpoint_id"] == "multi-step-deliberation-alpha:v1153.9")
    require(report["ok"] and report["status"] == "multi_step_deliberation_alpha_candidate")
    require(report["passed"] == report["total"] == 39)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["summary"]["synthetic_contract_check_count"] == 16)
    require(report["summary"]["registered_checkpoint_count"] >= 180)
    require(report["summary"]["runtime_session_count"] == 2)
    require(report["summary"]["runtime_pending_count"] == 1)
    require(report["summary"]["runtime_stale_session_count"] == 1)
    require(report["summary"]["runtime_case_count"] == 1)
    require(report["summary"]["runtime_completed_step_count"] == 4)
    require(report["summary"]["runtime_goal_context_count"] == 1)
    require(report["summary"]["maximum_cases"] == 2)
    require(report["summary"]["maximum_options_per_case"] == 3)
    require(report["summary"]["maximum_steps_per_case"] == 4)
    require(report["summary"]["maximum_proposition_chars"] == 260)
    require(report["summary"]["continuity_stale_after_days"] == 7)
    require(report["summary"]["privacy_forbidden_entry_count"] == 0)
    require(report["summary"]["privacy_content_finding_count"] == 0)
    require(len(report["remaining_limitations"]) == 5)
    require(report["read_only"] and not report["post_available"] and report["content_free"])
    require(report["authority_preserved"] and report["operator_promotion_required"])
    require(report["desktop_verification_pending"] and report["native_provider_certification_pending"])
    require(not report["consciousness_proven"] and not report["sentience_proven"] and not report["personhood_proven"])
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "goal_modified", "plan_created",
        "decision_created", "conflict_resolved", "approval_created", "authorization_created",
        "installation_performed", "upgrade_performed", "rollback_performed",
        "packaging_performed", "promotion_performed", "certification_performed",
    )))
    serialized = json.dumps(report, sort_keys=True)
    require(canary not in serialized)
    require("private-operation-id" not in serialized and "private-session-id" not in serialized)
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "prompt_exposed",
        "belief_text_exposed", "goal_text_exposed", "deliberation_text_exposed",
        "session_identifiers_exposed", "operation_identifiers_exposed", "memory_text_exposed",
        "evidence_text_exposed", "provider_payload_exposed", "hidden_reasoning_exposed",
    )))
    health = report["evidence"]["runtime_deliberation_health"]
    require(health["continuity_parse_valid"] and health["goal_store_parse_valid"])
    require(health["continuity_schema_valid"] and health["goal_store_schema_valid"])
    require(health["session_bounds_valid"] and health["pending_bounds_valid"])
    require(health["case_bounds_valid"] and health["goal_context_bounds_valid"])
    require(health["prerequisite_progress_valid"] and health["outcomes_valid"])
    require(health["pending_content_free"] and health["all_continuity_content_free"])
    require(health["all_authority_boundaries_preserved"])
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))

    diagnostics = inspect_deliberation_continuity(cognition)
    diagnostics_text = json.dumps(diagnostics, sort_keys=True)
    require(canary not in diagnostics_text and "private-operation-id" not in diagnostics_text)
    require(diagnostics["raw_continuity_exposed"] is False and diagnostics["raw_goal_context_exposed"] is False)
    require(all(set(row).issubset({"record_digest", "case_count", "completed_step_count", "goal_context_count", "stale", "content_free", "authority_preserved"}) for row in diagnostics["recent"]))

    malformed_rows = dict(continuity)
    malformed_rows["sessions"] = [{
        "operation_id": "private-malformed-operation",
        "session_id": "private-malformed-session",
        "recorded_at": "not-a-date",
        "case_count": "not-a-number",
        "cases": [{"completed_step_count": "also-not-a-number"}],
        "goal_context_count": "wrong",
        "user_content_stored": False,
        "belief_content_stored": False,
        "resolution_permitted": False,
        "decision_created": False,
        "action_executed": False,
    }]
    (cognition / "deliberation_continuity.json").write_text(json.dumps(malformed_rows), encoding="utf-8")
    malformed_diagnostics = inspect_deliberation_continuity(cognition)
    require(malformed_diagnostics["malformed_record_count"] == 1 and malformed_diagnostics["recent"][0]["stale"] is True)
    (cognition / "deliberation_continuity.json").write_text(json.dumps(continuity), encoding="utf-8")

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "multi-step-deliberation-alpha-checkpoint",
            source_root=ROOT,
            runtime_root=runtime,
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/multi-step-deliberation-alpha-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1153.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/multi-step-deliberation-alpha-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    (runtime / "cognition").mkdir(parents=True)
    (runtime / "cognition" / "deliberation_continuity.json").write_text(json.dumps({"sessions": "wrong-shape", "pending": []}), encoding="utf-8")
    before = signature(runtime)
    malformed = build_multi_step_deliberation_alpha_checkpoint(runtime, source_root=ROOT)
    require(not malformed["ok"] and malformed["evidence"]["runtime_deliberation_health"]["continuity_schema_valid"] is False)
    require(any(row["check_id"] == "runtime_deliberation_schema_is_valid" and row["status"] == "fail" for row in malformed["checks"]))
    require(before == signature(runtime))

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    empty = build_multi_step_deliberation_alpha_checkpoint(runtime, source_root=ROOT)
    require(empty["ok"] and empty["summary"]["runtime_session_count"] == 0)
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "multi-step-deliberation-alpha-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1153.9")
    require(not (Path(td) / "runtime").exists())

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.multi_step_deliberation; import conscious_agent.deliberation_continuity"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(imported.returncode == 0 and not (Path(td) / "runtime").exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "multi-step-deliberation-alpha-checkpoint"), None)
require(row is not None and row["builder"] == "build_multi_step_deliberation_alpha_checkpoint")
require(registry["checkpoint_count"] >= 180)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as td:
    retained_runtime = Path(td) / "runtime"
    retained_runtime.mkdir(parents=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(retained_runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    retained_code = r"""
import json, os
from pathlib import Path
from conscious_agent.belief_revision_alpha_checkpoint import build_belief_revision_alpha_checkpoint
from conscious_agent.reflection_alpha_checkpoint import build_reflection_alpha_checkpoint
from conscious_agent.reasoning_alpha_checkpoint import build_reasoning_alpha_checkpoint
root = Path(os.environ['EIDOLON_SOURCE_ROOT'])
runtime = Path(os.environ['EIDOLON_DATA_DIR'])
rows = {
 'belief': build_belief_revision_alpha_checkpoint(runtime, source_root=root),
 'reflection': build_reflection_alpha_checkpoint(runtime, source_root=root),
 'reasoning': build_reasoning_alpha_checkpoint(runtime, source_root=root),
}
print(json.dumps({k: {'ok': v['ok'], 'passed': v['passed'], 'total': v['total']} for k,v in rows.items()}))
"""
    env["EIDOLON_SOURCE_ROOT"] = str(ROOT)
    retained = subprocess.run([sys.executable, "-c", retained_code], cwd=ROOT, env=env, text=True, capture_output=True, timeout=420)
    require(retained.returncode == 0)
    retained_rows = json.loads(retained.stdout)
    require(retained_rows["belief"] == {"ok": True, "passed": 34, "total": 34})
    require(retained_rows["reflection"] == {"ok": True, "passed": 24, "total": 24})
    require(retained_rows["reasoning"] == {"ok": True, "passed": 22, "total": 22})

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "multi-step-deliberation-alpha-checkpoint-panel" in dashboard
    and "/api/cognition/multi-step-deliberation-alpha-checkpoint" in dashboard
    and "refreshMultiStepDeliberationAlphaCheckpoint" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
working_version = tuple(map(int, working.groups()))
previous_version = tuple(map(int, previous.groups()))
require(working_version >= (1153, 9) and previous_version >= (1153, 8) and previous_version < working_version)
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1153.9 Multi-Step Deliberation Alpha Read-Only Checkpoint" in history)
require("v1153.6-v1153.8 Multi-Step Deliberation Reliability and Adversarial Testing" in history)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
require(
    "v1154.0-v1154.2 Deliberation Outcome and Decision-Boundary Foundations" in next_steps
    or "v1155.0-v1155.2" in next_steps
    or "v1156.0-v1156.2" in next_steps
)
require((ROOT / "tools" / "v1153_9_full_registry_validation.py").exists())

print(json.dumps({"passed": passed, "total": passed, "suite": "v1153.9"}))
