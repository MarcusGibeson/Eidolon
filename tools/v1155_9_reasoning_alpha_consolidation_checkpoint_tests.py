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
sys.path.insert(0, str(ROOT))

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.reasoning_alpha_consolidation_checkpoint import build_reasoning_alpha_consolidation_checkpoint
from conscious_agent.reasoning_consolidation import build_reasoning_state
from conscious_agent.reasoning_state_continuity import (
    _bounded_projection,
    _candidate_digest_from_parts,
    _digest,
    record_reasoning_state,
)

checks: list[bool] = []

def require(value: object) -> None:
    checks.append(bool(value))


def signature(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        h.update(b"missing")
        return h.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and path_suffix_ok(p)):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def path_suffix_ok(path: Path) -> bool:
    return path.suffix.lower() not in {".pyc", ".pyo"}


def sample_state() -> dict:
    return build_reasoning_state(
        reflection_items=[{"confidence": 0.8, "uncertainty_score": 0.2}],
        belief_deliberation={"conflict_count": 1, "quarantined_conflict_count": 0},
        multi_step_deliberation={
            "cases": [{
                "case_digest": "private-case-id",
                "options": [{
                    "option_id": "private-option-id",
                    "proposition": "PRIVATE_REASONING_CANARY inspect the exact candidate in a sandbox",
                    "confidence": 0.8,
                    "uncertainty": 0.2,
                    "evidence_quality": 0.8,
                }],
                "steps": [{"complete": True}, {"complete": True}],
                "comparison": {"outcome": "provisional_leader_only", "provisional_leader_option_id": "private-option-id"},
            }]
        },
        decision_boundary={
            "cases": [{
                "boundary_id": "private-boundary-id",
                "state": "candidate_recommendation",
                "candidate_option_id": "private-option-id",
                "evidence_sufficient": True,
                "prerequisites_complete": True,
                "risk_level": "low",
                "reversibility": "high",
                "operator_approval_required": True,
            }]
        },
        continuity={"prior_session_present": False, "prior_session_stale": False, "goal_context_count": 1},
        prior_reasoning_state=None,
    )


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    cognition = runtime / "cognition"
    state = sample_state()
    record = record_reasoning_state(
        operation_id="private-operation-id",
        session_id="private-session-id",
        state=state,
        runtime_root=cognition,
    )
    require(record.get("record_digest"))
    require(record["projection"]["reasoning_quality"] == "bounded_candidate")
    require(record["projection"]["authority"] == "none")
    require(not record["projection"]["decision_created"] and not record["projection"]["execution_permitted"])

    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_reasoning_alpha_consolidation_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1155.9")
    require(report["checkpoint_id"] == "reasoning-alpha-consolidation:v1155.9")
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 44)
    require(report["summary"]["synthetic_contract_check_count"] >= 16)
    require(report["summary"]["registered_checkpoint_count"] >= 182)
    require(report["summary"]["runtime_reasoning_record_count"] == 1)
    require(report["summary"]["runtime_reasoning_pending_count"] == 0)
    require(report["summary"]["runtime_reasoning_integrity_mismatch_count"] == 0)
    require(report["summary"]["reasoning_stale_after_days"] == 7)
    require(report["summary"]["maximum_reasoning_cases"] == 2)
    require(report["summary"]["maximum_options_per_case"] == 3)
    require(report["summary"]["privacy_forbidden_entry_count"] == 0)
    require(report["summary"]["privacy_content_finding_count"] == 0)
    require(len(report["remaining_limitations"]) == 5)
    require(report["read_only"] and not report["post_available"] and report["content_free"])
    require(report["authority_preserved"] and report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["native_provider_certification_pending"])
    require(not report["consciousness_proven"] and not report["sentience_proven"] and not report["personhood_proven"])
    require(report["forbidden_report_token_count"] == 0)
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "goal_modified", "plan_created",
        "decision_created", "intention_created", "conflict_resolved",
        "approval_request_created", "approval_created", "approval_granted",
        "authorization_created", "installation_performed", "upgrade_performed",
        "rollback_performed", "packaging_performed", "promotion_performed", "certification_performed",
    )))
    serialized = json.dumps(report, sort_keys=True)
    require("PRIVATE_REASONING_CANARY" not in serialized)
    require("private-operation-id" not in serialized and "private-session-id" not in serialized)
    require("private-case-id" not in serialized and "private-boundary-id" not in serialized and "private-option-id" not in serialized)
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "prompt_exposed",
        "reasoning_content_exposed", "reasoning_registry_exposed",
        "session_identifiers_exposed", "operation_identifiers_exposed",
        "memory_text_exposed", "evidence_text_exposed", "provider_payload_exposed",
        "hidden_reasoning_exposed",
    )))
    health = report["evidence"]["runtime_reasoning_health"]
    require(health["parse_valid"] and health["schema_valid"] and health["schema_version_current"])
    require(health["record_bounds_valid"] and health["pending_bounds_valid"])
    require(health["all_projections_bounded"] and health["timestamps_valid"])
    require(health["quality_values_valid"] and health["transition_values_valid"])
    require(health["integrity_mismatch_count"] == 0 and health["pending_integrity_mismatch_count"] == 0)
    require(health["all_authority_boundaries_preserved"] and not health["review_required"])
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "reasoning-alpha-consolidation-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/reasoning-alpha-consolidation-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1155.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/reasoning-alpha-consolidation-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old

    # Canonical projection tampering with recomputed outer hashes must still fail.
    path = cognition / "reasoning_alpha_states.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    tampered = json.loads(json.dumps(stored))
    row = tampered["records"][0]
    row["projection"]["reasoning_transition"] = "approve_and_execute"
    row["candidate_digest"] = _candidate_digest_from_parts(row["operation_id"], row["session_digest"], row["projection"])
    row["record_digest"] = _digest({key: value for key, value in row.items() if key != "record_digest"})
    path.write_text(json.dumps(tampered), encoding="utf-8")
    before = signature(runtime)
    malformed = build_reasoning_alpha_consolidation_checkpoint(runtime, source_root=ROOT)
    require(not malformed["ok"])
    require(malformed["summary"]["runtime_reasoning_integrity_mismatch_count"] == 1)
    require(any(item["check_id"] == "runtime_reasoning_integrity_passes" and item["status"] == "fail" for item in malformed["checks"]))
    require(before == signature(runtime))

    # Pending wrapper mismatch must be reported without mutation.
    path.write_text(json.dumps(stored), encoding="utf-8")
    pending = json.loads(json.dumps(stored["records"][0]))
    staged = {
        "operation_id": pending["operation_id"],
        "session_digest": pending["session_digest"],
        "candidate_digest": "wrong-digest",
        "created_at": pending["created_at"],
        "record": pending,
        "content_free": True,
        "authority": "none",
    }
    pending_store = {"schema_version": "2", "records": [], "pending": [staged]}
    path.write_text(json.dumps(pending_store), encoding="utf-8")
    before = signature(runtime)
    pending_bad = build_reasoning_alpha_consolidation_checkpoint(runtime, source_root=ROOT)
    require(not pending_bad["ok"])
    require(pending_bad["evidence"]["runtime_reasoning_health"]["pending_integrity_mismatch_count"] == 1)
    require(before == signature(runtime))

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    cognition = runtime / "cognition"
    cognition.mkdir(parents=True)
    path = cognition / "reasoning_alpha_states.json"
    path.write_text(json.dumps({"schema_version": "2", "records": "wrong-shape", "pending": []}), encoding="utf-8")
    before = signature(runtime)
    malformed = build_reasoning_alpha_consolidation_checkpoint(runtime, source_root=ROOT)
    require(not malformed["ok"])
    require(any(item["check_id"] == "runtime_reasoning_store_schema_is_valid" and item["status"] == "fail" for item in malformed["checks"]))
    require(before == signature(runtime))

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    empty = build_reasoning_alpha_consolidation_checkpoint(runtime, source_root=ROOT)
    require(empty["ok"] and empty["summary"]["runtime_reasoning_record_count"] == 0)
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "reasoning-alpha-consolidation-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1155.9")
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.reasoning_consolidation; import conscious_agent.reasoning_state_continuity; import conscious_agent.reasoning_alpha_consolidation_checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=90,
    )
    require(imported.returncode == 0 and not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "reasoning-alpha-consolidation-checkpoint"), None)
require(row is not None and row["builder"] == "build_reasoning_alpha_consolidation_checkpoint")
require(registry["checkpoint_count"] >= 182)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "reasoning-alpha-consolidation-checkpoint-panel" in dashboard
    and "/api/cognition/reasoning-alpha-consolidation-checkpoint" in dashboard
    and "refreshReasoningAlphaConsolidationCheckpoint" in dashboard
    and "deferred to v1200" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1155, 9) and tuple(map(int, previous.groups())) == (1155, 8))
require("v1156.0-v1156.2 Conversation Intent Selection Foundations" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1155.9 Reasoning Alpha Consolidation" in next_steps)
require("v1156.0-v1156.2" in next_steps and "v1200" in next_steps)
require("v1155.9 Reasoning Alpha Consolidation" in history)

print(f"v1155.9 reasoning alpha consolidation checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
