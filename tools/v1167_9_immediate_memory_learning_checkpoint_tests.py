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
from conscious_agent.immediate_memory_learning_checkpoint import build_immediate_memory_learning_checkpoint


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing")
        return digest.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}):
        try:
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        except OSError:
            continue
    return digest.hexdigest()


checks: list[bool] = []
def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_immediate_memory_learning_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report["contract_version"] == "v1167.9")
    require(report["checkpoint_id"] == "immediate-memory-learning:v1167.9")
    require(report["ok"] and report["passed"] == report["total"] == 66)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["immediate_learning_checkpoint_completed"])
    require(report["correction_retraction_preference_foundations_consolidated"])
    require(report["historical_truth_preserved"])
    require(report["automatic_learning_not_started"])
    require(report["memory_mutation_not_started"])
    require(report["experiential_lesson_conversion_not_started"])
    require(report["autonomous_new_turn_initiation_not_started"])
    require(report["forbidden_report_value_count"] == 0)
    require(report["raw_conversation_exposed"] is False)
    require(report["raw_message_exposed"] is False)
    require(report["changed_value_exposed"] is False)
    require(report["memory_text_exposed"] is False)
    require(report["hidden_reasoning_exposed"] is False)
    require(report["learning_performed"] is False)
    require(report["lesson_created"] is False)
    require(report["memory_corrected"] is False)
    require(report["memory_record_deleted"] is False)
    require(report["memory_record_retracted"] is False)
    require(report["preference_committed"] is False)
    require(report["provider_contacted"] is False)
    require(report["action_executed"] is False)
    require(report["approval_granted"] is False)
    require(report["installation_performed"] is False)
    require(report["promotion_performed"] is False)
    require(report["certification_performed"] is False)
    require(len(report["structural_digest"]) == 64)

    summary = report["summary"]
    require(summary["synthetic_contract_check_count"] == 46)
    require(summary["projection_case_count"] == 15)
    require(summary["handoff_case_count"] == 5)
    require(summary["receipt_case_count"] == 8)
    require(summary["learning_audit_case_count"] == 9)
    require(summary["candidate_maximum_count"] == 24)
    require(summary["prior_receipt_maximum_count"] == 16)
    require(summary["prior_receipt_maximum_bytes"] == 24000)
    require(summary["message_maximum_chars"] == 4000)
    require(summary["learning_prompt_maximum_chars"] == 2800)
    require(summary["authoritative_conversation_path_count"] == 2)
    require(summary["open_limitation_count"] == 6)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)

    synthetic = report["evidence"]["synthetic_contracts"]
    require(synthetic["passed"] == synthetic["total"] == 46)
    require(synthetic["diagnostics_tamper_detected"])
    require(synthetic["audit_tamper_detected"])
    projection = synthetic["projection_summaries"]
    require(projection["correction"]["candidate_type"] == "correction")
    require(projection["preference_change"]["candidate_scope"] == "durable_candidate")
    require(projection["temporary_preference"]["candidate_scope"] == "temporary")
    require(projection["retraction"]["historical_truth_preserved"])
    require(projection["plain_message"]["candidate_present"] is False)
    require(projection["ambiguous_change"]["policy_recovered"])
    require(projection["forged_authority"]["authority_violation_count"] == 1)
    require(projection["private_reasoning"]["private_field_violation_count"] == 1)
    require(projection["verified_cross_turn_resume"]["verified_prior_receipts"] == 1)
    require(projection["conflicting_receipt_recovery"]["policy_recovered"])
    require(all(row["content_free"] and row["authority_preserved"] for row in projection.values()))

    handoffs = synthetic["handoff_summaries"]
    require(handoffs["eligible_after_boundary"]["eligible_for_existing_commit_review"])
    require(not handoffs["before_provider_completion"]["eligible_for_existing_commit_review"])
    require(not handoffs["before_memory_commit"]["eligible_for_existing_commit_review"])
    require(not handoffs["temporary_never_durable"]["eligible_for_existing_commit_review"])
    require(handoffs["retraction_preserves_history"]["historical_truth_preserved"])

    receipts = synthetic["receipt_summaries"]
    require(receipts["verified"]["verified_receipt_count"] == 1)
    require(receipts["replayed"]["replayed_receipt_count"] == 1)
    require(receipts["tampered"]["tampered_receipt_count"] == 1)
    require(receipts["conflicting_types"]["conflicting_receipts"])
    require(receipts["conflicting_resolution"]["conflicting_receipts"])
    require(receipts["malformed_collection"]["malformed_collection"])
    require(receipts["oversized_collection"]["oversized_collection"])
    require(receipts["oversized_bytes"]["oversized_receipt_bytes"])

    audits = synthetic["audit_summaries"]
    require(audits["compliant"]["compliant"])
    require(audits["forged_authority"]["authority_violation_count"] == 1)
    require(audits["private_reasoning"]["private_field_violation_count"] == 1)
    require(audits["recovered_candidate"]["recovered_candidate_violation"])
    require(audits["premature_handoff"]["premature_handoff"])
    require(audits["mutation_violation"]["mutation_violation"])
    require(audits["invalid_diagnostics"]["invalid_diagnostics"])
    require(audits["invalid_handoff"]["invalid_handoff"])
    require(audits["malformed_projection"]["malformed_projection"])

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "immediate-memory-learning-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/immediate-memory-learning-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1167.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/immediate-memory-learning-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(td) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "immediate-memory-learning-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1167.9")
    require(not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "immediate-memory-learning-checkpoint"), None)
require(row is not None and row["builder"] == "build_immediate_memory_learning_checkpoint")
require(registry["checkpoint_count"] >= 194)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("immediate-memory-learning-checkpoint-panel" in dashboard)
require("/api/cognition/immediate-memory-learning-checkpoint" in dashboard)
require("refreshImmediateMemoryLearningCheckpoint" in dashboard)
require("deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
working_version = tuple(map(int, working.groups()))
previous_version = tuple(map(int, previous.groups()))
require(working_version >= (1167, 9) and previous_version < working_version)
require("NEXT_RECOMMENDED_ARC" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("Current working source:" in next_steps)
require("v1200" in next_steps)
require("v1167.9 Immediate Learning" in history)

print(f"v1167.9 immediate memory learning checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
