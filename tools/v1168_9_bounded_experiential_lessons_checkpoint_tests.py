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
from conscious_agent.bounded_experiential_lessons_checkpoint import build_bounded_experiential_lessons_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing")
        return digest.hexdigest()
    for path in sorted(
        p for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
        and ".pytest_cache" not in p.parts and p.suffix not in {".pyc", ".pyo"}
    ):
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
    report = build_bounded_experiential_lessons_checkpoint(source_root=ROOT, runtime_root=runtime)

    require(report["contract_version"] == "v1168.9")
    require(report["checkpoint_id"] == "bounded-experiential-lessons:v1168.9")
    require(report["ok"] and report["passed"] == report["total"] == 70)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["bounded_experiential_lessons_checkpoint_completed"])
    require(report["experience_to_lesson_foundations_consolidated"])
    require(report["historical_truth_preserved"])
    require(report["uncontrolled_self_training_not_started"])
    require(report["model_training_not_started"])
    require(report["automatic_lesson_commit_not_started"])
    require(report["memory_mutation_not_started"])
    require(report["automatic_generalization_not_started"])
    require(report["autonomous_new_turn_initiation_not_started"])
    require(report["forbidden_report_value_count"] == 0)
    require(report["raw_conversation_exposed"] is False)
    require(report["raw_message_exposed"] is False)
    require(report["lesson_content_exposed"] is False)
    require(report["experience_text_exposed"] is False)
    require(report["memory_text_exposed"] is False)
    require(report["hidden_reasoning_exposed"] is False)
    require(report["lesson_committed"] is False)
    require(report["lesson_created"] is False)
    require(report["model_training_performed"] is False)
    require(report["self_training_performed"] is False)
    require(report["automatic_generalization_performed"] is False)
    require(report["memory_mutated"] is False)
    require(report["provider_contacted"] is False)
    require(report["action_executed"] is False)
    require(report["approval_granted"] is False)
    require(report["installation_performed"] is False)
    require(report["promotion_performed"] is False)
    require(report["certification_performed"] is False)
    require(len(report["structural_digest"]) == 64)

    summary = report["summary"]
    require(summary["synthetic_contract_check_count"] == 50)
    require(summary["projection_case_count"] == 19)
    require(summary["handoff_case_count"] == 5)
    require(summary["receipt_case_count"] == 9)
    require(summary["lesson_audit_case_count"] == 9)
    require(summary["experience_row_maximum_count"] == 24)
    require(summary["prior_receipt_maximum_count"] == 12)
    require(summary["prior_receipt_maximum_bytes"] == 24000)
    require(summary["message_maximum_chars"] == 4000)
    require(summary["lesson_prompt_maximum_chars"] == 3200)
    require(summary["authoritative_conversation_path_count"] == 2)
    require(summary["open_limitation_count"] == 6)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)

    synthetic = report["evidence"]["synthetic_contracts"]
    require(synthetic["passed"] == synthetic["total"] == 50)
    require(synthetic["diagnostics_tamper_detected"])
    require(synthetic["audit_tamper_detected"])

    projections = synthetic["projection_summaries"]
    require(projections["corrective_lesson"]["lesson_type"] == "corrective_lesson")
    require(projections["retraction_lesson"]["lesson_type"] == "retraction_lesson")
    require(projections["preference_lesson"]["lesson_type"] == "preference_lesson")
    require(projections["temporary_preference"]["candidate_present"] is False)
    require(projections["failure_lesson"]["lesson_type"] == "failure_avoidance_lesson")
    require(projections["repair_lesson"]["lesson_type"] == "repair_lesson")
    require(projections["single_success"]["candidate_present"] is False)
    require(projections["repeatable_success"]["lesson_type"] == "repeatable_success_lesson")
    require(projections["plain_message"]["candidate_present"] is False)
    require(projections["malformed_projection"]["policy_recovered"])
    require(projections["malformed_experience_collection"]["policy_recovered"])
    require(projections["oversized_experience_collection"]["policy_recovered"])
    require(projections["oversized_message"]["policy_recovered"])
    require(projections["forged_authority"]["authority_violation_count"] == 1)
    require(projections["private_reasoning"]["private_field_violation_count"] == 1)
    require(projections["verified_cross_turn_resume"]["verified_prior_receipts"] == 1)
    require(projections["conflicting_receipt_recovery"]["policy_recovered"])
    require(all(row["content_free"] and row["authority_preserved"] for row in projections.values()))

    handoffs = synthetic["handoff_summaries"]
    require(handoffs["eligible_after_boundary"]["eligible_for_operator_review"])
    require(not handoffs["before_provider_completion"]["eligible_for_operator_review"])
    require(not handoffs["before_memory_commit"]["eligible_for_operator_review"])
    require(not handoffs["no_candidate"]["eligible_for_operator_review"])
    require(handoffs["retraction_preserves_history"]["historical_truth_preserved"])
    require(all(row["content_free"] and row["authority_preserved"] for row in handoffs.values()))

    receipts = synthetic["receipt_summaries"]
    require(receipts["verified"]["verified_receipt_count"] == 1)
    require(receipts["replayed"]["replayed_receipt_count"] == 1)
    require(receipts["tampered"]["tampered_receipt_count"] == 1)
    require(receipts["conflicting_types"]["conflicting_receipts"])
    require(receipts["conflicting_target_state"]["conflicting_receipts"])
    require(receipts["conflicting_source_lineage"]["conflicting_receipts"])
    require(receipts["malformed_collection"]["malformed_collection"])
    require(receipts["oversized_collection"]["oversized_collection"])
    require(receipts["oversized_bytes"]["oversized_receipt_bytes"])
    require(all(row["content_free"] and row["authority_preserved"] for row in receipts.values()))

    audits = synthetic["audit_summaries"]
    require(audits["compliant"]["compliant"])
    require(audits["forged_authority"]["authority_violation_count"] == 1)
    require(audits["private_reasoning"]["private_field_violation_count"] == 1)
    require(audits["recovered_candidate"]["recovered_candidate_violation"])
    require(audits["premature_handoff"]["premature_handoff"])
    require(audits["mutation_or_training"]["mutation_or_training_violation"])
    require(audits["invalid_diagnostics"]["invalid_diagnostics"])
    require(audits["invalid_handoff"]["invalid_handoff"])
    require(audits["malformed_projection"]["malformed_projection"])
    require(all(row["content_free"] and row["authority_preserved"] for row in audits.values()))

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "bounded-experiential-lessons-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"])
        require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"])
        require(dispatched["checkpoint_summary"]["ok"])
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/bounded-experiential-lessons-checkpoint")
        require(status == 200)
        require((payload.get("data") or {}).get("contract_version") == "v1168.9")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/bounded-experiential-lessons-checkpoint", body={"confirm": True}
        )
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
        [sys.executable, str(ROOT / "eidolon.py"), "bounded-experiential-lessons-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1168.9")
    require(not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (row for row in registry["checkpoints"] if row["checkpoint_id"] == "bounded-experiential-lessons-checkpoint"),
    None,
)
require(row is not None)
require(row["builder"] == "build_bounded_experiential_lessons_checkpoint")
require(registry["checkpoint_count"] >= 195)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("bounded-experiential-lessons-checkpoint-panel" in dashboard)
require("/api/cognition/bounded-experiential-lessons-checkpoint" in dashboard)
require("refreshBoundedExperientialLessonsCheckpoint" in dashboard)
require("deferred to v1200" in dashboard)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
working_version = tuple(map(int, working.groups()))
previous_version = tuple(map(int, previous.groups()))
require(working_version >= (1168, 9) and previous_version < working_version)
require("NEXT_RECOMMENDED_ARC" in metadata)

next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("Current working source:" in next_steps)
require("v1200" in next_steps)
require("v1168.9 Bounded Experiential Lessons" in history)

print(f"v1168.9 bounded experiential lessons checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
