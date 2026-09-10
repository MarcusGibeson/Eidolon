from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

import settings_manager
from model_training.training_capture_adapters import capture_research_synthesis, capture_software_attempt
from model_training.training_capture_runtime import finalize_capture_result
from model_training.training_export import approve_training_record
from model_training.training_operator import (
    build_training_evidence_status,
    create_governed_dataset,
    create_governed_eval_corpus,
    list_training_artifacts,
    run_configured_local_benchmark,
)
from model_training.training_policy import resolve_training_evidence_capture_policy, update_training_evidence_capture_policy
from model_training.training_preferences import build_preference_pair
from model_training.training_record import load_training_record

checks: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    checks.append(label)


with tempfile.TemporaryDirectory(prefix="eid-training-operatorization-") as directory:
    runtime = Path(directory)
    original_settings_file = settings_manager.SETTINGS_FILE
    settings_manager.SETTINGS_FILE = runtime / "settings.json"
    try:
        settings_manager.SETTINGS_FILE.write_text(json.dumps({"local_model_provider": "ollama", "local_model": "qwen2.5:7b"}), encoding="utf-8")
        migrated = settings_manager.load_settings()
        persisted = json.loads(settings_manager.SETTINGS_FILE.read_text(encoding="utf-8"))
        require(migrated["training_capture_coding_repair_enabled"] is True, "existing_install_migrates_coding_capture_on")
        require(migrated["training_capture_research_enabled"] is True, "existing_install_migrates_research_capture_on")
        require(migrated["training_auto_sanitize_enabled"] is True, "existing_install_migrates_auto_sanitize_on")
        require(migrated["training_capture_conversation_enabled"] is False, "existing_install_migrates_conversation_capture_off")
        require("training_capture_coding_repair_enabled" in persisted, "migration_is_durable")
        policy = resolve_training_evidence_capture_policy()
        require(policy.coding_repair_enabled and policy.research_enabled and policy.auto_sanitize_enabled, "policy_resolves_safe_defaults")
        require(not policy.auto_approve_enabled and not policy.model_training_authorized and not policy.model_promotion_authorized, "policy_preserves_authority_boundaries")

        coding = capture_software_attempt(
            runtime_root=runtime, capture_authorized=True,
            prompt_or_context={"objective": "repair synthetic target"},
            model_output={"edit": "broken"}, corrected_output={"edit": "verified"},
            verification={"passed": True, "deterministic": True, "status": "verified"}, auto_sanitize=True,
        )
        require(coding["ok"] is True and coding["sanitization_ok"] is True, "verified_coding_capture_auto_sanitizes")
        record_id = coding["record"]["record_id"]
        sanitized = load_training_record(record_id, runtime_root=runtime, stage="sanitized")
        require(bool(sanitized) and sanitized["approved_for_training"] is False, "coding_capture_is_not_auto_approved")
        require(build_preference_pair(sanitized)["ok"] is True, "verified_repair_creates_preference_pair")

        research = capture_research_synthesis(
            runtime_root=runtime, capture_authorized=True,
            research_context={"objective": "synthetic public research"},
            model_output={"finding": "supported"}, validation={"passed": True, "deterministic": True, "status": "verified"},
            auto_sanitize=True,
        )
        require(research["ok"] is True and research["sanitization_ok"] is True, "verified_research_capture_auto_sanitizes")
        research_id = research["record"]["record_id"]
        require(load_training_record(research_id, runtime_root=runtime, stage="sanitized")["approved_for_training"] is False, "research_capture_is_not_auto_approved")

        update_training_evidence_capture_policy({
            "training_capture_coding_repair_enabled": False,
            "training_capture_research_enabled": False,
        })
        disabled = resolve_training_evidence_capture_policy()
        require(not disabled.coding_repair_enabled and not disabled.research_enabled, "operator_can_disable_capture_durably")

        failure = finalize_capture_result(
            {"ok": True, "status": "training_record_created", "record": {"record_id": "trn_missing"}},
            runtime_root=runtime, capability="research", auto_sanitize=True,
        )
        require(failure["ok"] is True and failure["sanitization_ok"] is False, "capture_failure_preserves_underlying_success")
        require(bool(failure.get("capture_failure", {}).get("runtime_path")), "capture_failure_receipt_is_visible")

        for rid in (record_id, research_id):
            approved = approve_training_record(rid, runtime_root=runtime, operator_approved=True)
            require(approved["ok"] is True, f"explicit_approval_succeeds_{rid}")
        dataset = create_governed_dataset(runtime_root=runtime, dataset_version="operator-test-v1", operator_authorized=True)
        require(dataset["ok"] is True and dataset["manifest"]["record_count"] == 2, "operator_dataset_builds_from_approved_store")
        require(bool(dataset["provenance"].get("certificate_digest")), "dataset_provenance_is_materialized")
        restored = create_governed_dataset(runtime_root=runtime, dataset_version="operator-test-v1", operator_authorized=True)
        require(restored["ok"] is True, "identical_dataset_retry_is_idempotent")

        cases = [
            {"case_id": "case-1", "capability": "research", "prompt": "Return evidence.", "checks": ["nonempty"]},
            {"case_id": "case-2", "capability": "coding", "prompt": "Return a patch.", "checks": ["nonempty"]},
        ]
        corpus = create_governed_eval_corpus(runtime_root=runtime, corpus_version="eval-v1", cases=cases, operator_authorized=True)
        require(corpus["ok"] is True and corpus["corpus"]["case_count"] == 2, "operator_can_freeze_eval_corpus")
        require(create_governed_eval_corpus(runtime_root=runtime, corpus_version="eval-v1", cases=cases, operator_authorized=True)["ok"] is True, "eval_retry_is_idempotent")
        conflict = create_governed_eval_corpus(runtime_root=runtime, corpus_version="eval-v1", cases=cases[:1], operator_authorized=True)
        require(conflict["ok"] is False and conflict["status"] == "evaluation_corpus_version_conflict", "eval_conflicting_overwrite_fails_closed")

        import local_model
        original_client = local_model.LocalModelClient
        class FakeClient:
            def __init__(self, _config): pass
            def generate(self, prompt: str) -> str: return "verified " + prompt
            def close(self) -> None: pass
        local_model.LocalModelClient = FakeClient
        try:
            benchmark = run_configured_local_benchmark(
                runtime_root=runtime, corpus_version="eval-v1", provider="ollama",
                model="qwen2.5:7b", operator_authorized=True,
            )
        finally:
            local_model.LocalModelClient = original_client
        require(benchmark["ok"] is True and benchmark["provider_request_count"] == 2, "configured_local_benchmark_executes_all_cases")
        require(benchmark["provider_contacted"] is True and benchmark["raw_model_outputs_stored"] is False, "benchmark_accounting_and_privacy_are_truthful")
        require(benchmark["model_registered"] is False and benchmark["model_promotion_authorized"] is False, "benchmark_does_not_register_or_promote_model")

        status = build_training_evidence_status(runtime_root=runtime)
        require(status["counts"]["raw"] == 2 and status["counts"]["sanitized"] == 2 and status["counts"]["approved"] == 2, "status_reports_stage_counts")
        require(status["counts"]["preference_pairs"] == 1 and status["counts"]["capture_failures"] >= 1, "status_reports_preferences_and_failures")
        require(status["latest_dataset_version"] == "operator-test-v1" and status["provenance_status"] == "verified", "status_reports_dataset_and_provenance")
        require(status["readiness"]["approved_target"] == 5000 and status["readiness"]["frozen_eval_target"] == 500, "status_reports_readiness_thresholds")
        require(status["readiness"]["ready"] is False, "status_does_not_overstate_readiness")
        require(status["hard_boundaries"]["training_authorized"] is False and status["hard_boundaries"]["model_promotion_authorized"] is False, "status_shows_hard_boundaries")
        require(list_training_artifacts(runtime_root=runtime, kind="benchmarks")["count"] == 1, "benchmark_status_lists_sealed_result")
        import paths
        original_data_dir = paths.DATA_DIR
        paths.DATA_DIR = runtime
        try:
            require(build_training_evidence_status()["counts"]["approved"] == 2, "operator_status_resolves_canonical_runtime_root")
        finally:
            paths.DATA_DIR = original_data_dir
    finally:
        settings_manager.SETTINGS_FILE = original_settings_file

dashboard_source = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
cli_source = (ROOT / "tools" / "eidolon_training_dataset.py").read_text(encoding="utf-8")
coding_source = (ROOT / "conscious_agent" / "isolated_coding_execution.py").read_text(encoding="utf-8")
research_source = (ROOT / "conscious_agent" / "bounded_autonomous_web_research.py").read_text(encoding="utf-8")
require("/api/training-evidence/status" in dashboard_source and "Training Evidence Capture" in dashboard_source, "dashboard_exposes_status_and_controls")
require(all(command in cli_source for command in ["list-raw", "list-sanitized", "list-approved", "build-manifest", "list-eval-corpora", "benchmark-status"]), "cli_exposes_operator_inspection_workflows")
require("resolve_training_evidence_capture_policy" in coding_source and "resolve_training_evidence_capture_policy" in research_source, "ordinary_workflows_resolve_operator_policy")

print(json.dumps({"ok": True, "suite": "v2503.4.39-training-operatorization-acceptance", "passed": len(checks), "failed": 0, "checks": checks}, indent=2))
