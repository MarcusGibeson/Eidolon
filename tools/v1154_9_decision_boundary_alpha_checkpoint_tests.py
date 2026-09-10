from __future__ import annotations

from datetime import datetime, timedelta, timezone
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

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.decision_boundary_alpha_checkpoint import build_decision_boundary_alpha_checkpoint
from conscious_agent.decision_review_registry import (
    _digest,
    build_operator_approval_preview,
    inspect_decision_review_registry,
    record_decision_review_candidates,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing")
        return digest.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and path_suffix_ok(p)):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def path_suffix_ok(path: Path) -> bool:
    return path.suffix.lower() not in {".pyc", ".pyo"}


def boundary(proposition: str = "preview the repair in a sandbox", *, risk: str = "low", reversibility: str = "high") -> dict:
    return {
        "cases": [{
            "boundary_id": "private-boundary-id",
            "state": "candidate_recommendation",
            "candidate_option_id": "private-option-id",
            "candidate_proposition": proposition,
            "evidence_sufficient": True,
            "prerequisites_complete": True,
            "risk_level": risk,
            "reversibility": reversibility,
            "operator_approval_required": True,
        }]
    }


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    cognition = runtime / "cognition"
    canary = "PRIVATE-CANDIDATE-CANARY-1154-9"
    record = record_decision_review_candidates(
        operation_id="private-operation-id",
        session_id="private-session-id",
        boundary=boundary(canary + " preview the repair in a sandbox"),
        runtime_root=cognition,
    )
    item = record["review_items"][0]
    preview = build_operator_approval_preview(
        operation_id="private-operation-id",
        review_item_id=item["review_item_id"],
        expected_candidate_digest=item["candidate_digest"],
        runtime_root=cognition,
    )
    require(record["contract_version"] == "v1154.9")
    require(preview["status"] == "ready_for_operator_review")
    require(preview["exact_candidate_bound"] and preview["read_only"])
    require(not any(preview.get(key) for key in (
        "approval_request_created", "approval_created", "approval_granted",
        "decision_created", "execution_permitted", "action_authority", "authority_broadened",
    )))
    mismatch = build_operator_approval_preview(
        operation_id="private-operation-id",
        review_item_id=item["review_item_id"],
        expected_candidate_digest="0" * 64,
        runtime_root=cognition,
    )
    require(mismatch["status"] == "candidate_digest_mismatch")

    registry_path = cognition / "decision_review_registry.json"
    clean_state = json.loads(registry_path.read_text(encoding="utf-8"))

    candidate_tamper = json.loads(json.dumps(clean_state))
    candidate_tamper["records"][0]["review_items"][0]["candidate_proposition"] = "tampered executable content"
    candidate_tamper["records"][0]["record_digest"] = _digest({
        key: value for key, value in candidate_tamper["records"][0].items() if key != "record_digest"
    })
    registry_path.write_text(json.dumps(candidate_tamper), encoding="utf-8")
    tampered_candidate_preview = build_operator_approval_preview(
        operation_id="private-operation-id",
        review_item_id=item["review_item_id"],
        expected_candidate_digest=item["candidate_digest"],
        runtime_root=cognition,
    )
    require(tampered_candidate_preview["status"] == "candidate_integrity_mismatch")
    try:
        record_decision_review_candidates(
            operation_id="private-operation-id",
            session_id="private-session-id",
            boundary=boundary(canary + " preview the repair in a sandbox"),
            runtime_root=cognition,
        )
        existing_tamper_rejected = False
    except ValueError as error:
        existing_tamper_rejected = "integrity mismatch" in str(error)
    require(existing_tamper_rejected)
    tampered_inspection = inspect_decision_review_registry(cognition)
    require(tampered_inspection["candidate_integrity_mismatch_count"] == 1)
    require(tampered_inspection["malformed"] and tampered_inspection["review_required"])

    record_tamper = json.loads(json.dumps(clean_state))
    record_tamper["records"][0]["created_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    registry_path.write_text(json.dumps(record_tamper), encoding="utf-8")
    tampered_record_preview = build_operator_approval_preview(
        operation_id="private-operation-id",
        review_item_id=item["review_item_id"],
        expected_candidate_digest=item["candidate_digest"],
        runtime_root=cognition,
    )
    require(tampered_record_preview["status"] == "record_integrity_mismatch")
    try:
        record_decision_review_candidates(
            operation_id="private-operation-id",
            session_id="private-session-id",
            boundary=boundary(canary + " preview the repair in a sandbox"),
            runtime_root=cognition,
        )
        existing_record_tamper_rejected = False
    except ValueError as error:
        existing_record_tamper_rejected = "integrity mismatch" in str(error)
    require(existing_record_tamper_rejected)
    require(inspect_decision_review_registry(cognition)["record_integrity_mismatch_count"] == 1)

    registry_path.write_text(json.dumps(clean_state), encoding="utf-8")
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_decision_boundary_alpha_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1154.9")
    require(report["checkpoint_id"] == "decision-boundary-alpha:v1154.9")
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 43)
    require(report["summary"]["registered_checkpoint_count"] >= 181)
    require(report["summary"]["runtime_review_record_count"] == 1)
    require(report["summary"]["runtime_review_item_count"] == 1)
    require(report["summary"]["runtime_integrity_mismatch_count"] == 0)
    require(report["summary"]["review_stale_after_days"] == 14)
    require(report["summary"]["privacy_forbidden_entry_count"] == 0)
    require(report["summary"]["privacy_content_finding_count"] == 0)
    require(len(report["remaining_limitations"]) == 5)
    require(report["read_only"] and not report["post_available"] and report["content_free"])
    require(report["authority_preserved"] and report["operator_promotion_required"])
    require(report["desktop_verification_pending"] and report["native_provider_certification_pending"])
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
    require(canary not in serialized)
    require("private-operation-id" not in serialized and "private-session-id" not in serialized)
    require("private-boundary-id" not in serialized and "private-option-id" not in serialized)
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "prompt_exposed",
        "candidate_text_exposed", "review_registry_exposed", "session_identifiers_exposed",
        "operation_identifiers_exposed", "memory_text_exposed", "evidence_text_exposed",
        "provider_payload_exposed", "hidden_reasoning_exposed",
    )))
    health = report["evidence"]["runtime_decision_review_health"]
    require(health["parse_valid"] and health["schema_valid"] and health["schema_version_current"])
    require(health["record_bounds_valid"] and health["pending_bounds_valid"] and health["item_bounds_valid"])
    require(health["record_count_fields_valid"] and health["timestamps_valid"])
    require(health["record_integrity_mismatch_count"] == 0 and health["candidate_integrity_mismatch_count"] == 0)
    require(health["pending_integrity_valid"] and health["all_authority_boundaries_preserved"])
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "decision-boundary-alpha-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/decision-boundary-alpha-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1154.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/decision-boundary-alpha-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    cognition = runtime / "cognition"
    cognition.mkdir(parents=True)
    path = cognition / "decision_review_registry.json"
    path.write_text(json.dumps({"schema_version": "2", "records": "wrong-shape", "pending": []}), encoding="utf-8")
    before = signature(runtime)
    malformed = build_decision_boundary_alpha_checkpoint(runtime, source_root=ROOT)
    require(not malformed["ok"])
    require(any(row["check_id"] == "runtime_review_registry_schema_is_valid" and row["status"] == "fail" for row in malformed["checks"]))
    require(before == signature(runtime))

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    empty = build_decision_boundary_alpha_checkpoint(runtime, source_root=ROOT)
    require(empty["ok"] and empty["summary"]["runtime_review_record_count"] == 0)
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    runtime = Path(td) / "runtime"
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "decision-boundary-alpha-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=420,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1154.9")
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    runtime = Path(td) / "runtime"
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.deliberation_decision_boundary; import conscious_agent.decision_review_registry; import conscious_agent.decision_boundary_alpha_checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=90,
    )
    require(imported.returncode == 0 and not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "decision-boundary-alpha-checkpoint"), None)
require(row is not None and row["builder"] == "build_decision_boundary_alpha_checkpoint")
require(registry["checkpoint_count"] >= 181)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "decision-boundary-alpha-checkpoint-panel" in dashboard
    and "/api/cognition/decision-boundary-alpha-checkpoint" in dashboard
    and "refreshDecisionBoundaryAlphaCheckpoint" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) >= (1154, 9) and tuple(map(int, previous.groups())) >= (1154, 8))
require("v1154.9 Decision-Boundary Alpha" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))

print(f"v1154.9 decision-boundary alpha checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
