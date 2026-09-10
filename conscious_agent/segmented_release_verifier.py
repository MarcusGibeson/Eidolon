from __future__ import annotations

"""Segmented, resumable broad verification for v1250.1.

The legacy broad verifier remains available for compatibility.  This module
provides the cleanup-arc replacement entry point: ten independently runnable
stages, exact stage/input digests, bounded execution, partial receipts after
every transition, and stale-receipt rejection.  No passing receipt authorizes
installation, promotion, certification, release, or independent action.
"""

import hashlib
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from hermetic_verification_runtime import AUTHORITY_FLAGS, atomic_write_json, build_hermetic_environment, copy_clean_source_snapshot, run_bounded_command, scan_forbidden_runtime_entries, source_signature, validate_external_path
except ImportError:  # direct tool execution compatibility
    from hermetic_verification_runtime import (  # type: ignore
        AUTHORITY_FLAGS,
        atomic_write_json,
        build_hermetic_environment,
        copy_clean_source_snapshot,
        run_bounded_command,
        scan_forbidden_runtime_entries,
        source_signature,
        validate_external_path,
    )

CONTRACT_VERSION = "v1250.1"
DEFAULT_STAGE_TIMEOUT_SECONDS = 900
DEFAULT_SUITE_TIMEOUT_SECONDS = 240
SUITE_TIMEOUT_OVERRIDES = {
    # This retained scale benchmark intentionally writes 20,000 action files,
    # 1,000 sessions, and 20,000 memories. Windows filesystem scanning makes
    # its measured clean-snapshot runtime materially longer than other suites.
    "tools/v1252_9_persistent_state_performance_checkpoint_tests.py": 600,
}
PRIVATE_RECEIPT_KEYS = {
    "stdout",
    "stderr",
    "prompt",
    "conversation",
    "memory",
    "secret",
    "provider_payload",
    "private_reasoning",
    "raw_source",
    "content",
    "text",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _is_digest(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(char in "0123456789abcdef" for char in token.lower())


@dataclass(frozen=True)
class VerificationStage:
    stage_id: str
    label: str
    suites: tuple[str, ...]
    input_globs: tuple[str, ...]
    budget_seconds: int
    owner: str

    def as_dict(self) -> dict[str, Any]:
        row = {
            "stage_id": self.stage_id,
            "label": self.label,
            "suites": list(self.suites),
            "input_globs": list(self.input_globs),
            "budget_seconds": self.budget_seconds,
            "owner": self.owner,
            "authority_state": "verification_only_no_release_authority",
        }
        row["stage_manifest_digest"] = _digest(row)
        return row


DEFAULT_STAGES: tuple[VerificationStage, ...] = (
    VerificationStage(
        "source-privacy",
        "Source-only packaging and privacy",
        (
            "tools/v1247_9_privacy_security_secret_management_audit_checkpoint_tests.py",
            "tools/v1249_9_feature_freeze_final_hardening_checkpoint_tests.py",
        ),
        (
            "conscious_agent/privacy_security_secret_management_audit*.py",
            "conscious_agent/feature_freeze_final_hardening*.py",
            "conscious_agent/release_metadata.py",
            "README*.md",
            "tools/v1247_*.py",
            "tools/v1249_*.py",
        ),
        900,
        "privacy",
    ),
    VerificationStage(
        "authority-approval",
        "Authority, approval, and adversarial boundaries",
        (
            "tools/v1239_9_adversarial_execution_cognitive_boundary_checkpoint_tests.py",
            "tools/v1240_9_integrated_developer_beta_checkpoint_tests.py",
        ),
        (
            "conscious_agent/*approval*.py",
            "conscious_agent/*authority*.py",
            "conscious_agent/adversarial_execution_cognitive_boundary*.py",
            "conscious_agent/integrated_developer_beta*.py",
            "tools/v1239_*.py",
            "tools/v1240_*.py",
        ),
        900,
        "release",
    ),
    VerificationStage(
        "conversation-command",
        "Conversation and command distinction",
        (
            "tools/v1206_0_2_natural_conversation_command_distinction_tests.py",
            "tools/v1248_9_integrated_mind_conversation_development_benchmark_checkpoint_tests.py",
            "tools/v1251_0_2_response_time_prompt_efficiency_tests.py",
            "tools/v1251_3_5_action_startup_provider_efficiency_tests.py",
            "tools/v1252_0_2_conversation_indexing_tests.py",
            "tools/v1253_0_2_critical_path_work_efficiency_tests.py",
        ),
        (
            "conscious_agent/*conversation*.py",
            "conscious_agent/*command*.py",
            "conscious_agent/ordinary_chat_development_campaign.py",
            "conscious_agent/general_small_project_implementation*.py",
            "conscious_agent/integrated_mind_conversation_development_benchmark*.py",
            "tools/v1206_0_2*.py",
            "tools/v1248_*.py",
            "conscious_agent/response_time_runtime.py",
            "conscious_agent/response_time_efficiency.py",
            "conscious_agent/chat_launcher.py",
            "tools/v1251_0_2_*.py",
            "tools/v1251_3_5_*.py",
            "conscious_agent/session_metadata_index.py",
            "conscious_agent/bounded_cross_session_retrieval.py",
            "conscious_agent/persistent_session_summaries.py",
            "conscious_agent/persistent_state_index.py",
            "tools/v1252_0_2_*.py",
            "conscious_agent/critical_path_runtime.py",
            "conscious_agent/goal_planning_bundle.py",
            "conscious_agent/bounded_internal_maintenance.py",
            "conscious_agent/work_coalescing.py",
            "tools/v1253_0_2_*.py",
        ),
        900,
        "conversation",
    ),
    VerificationStage(
        "development-lifecycle",
        "Build, test, diagnosis, and repair lifecycle",
        (
            "tools/v1215_9_conversational_supervised_repair_execution_checkpoint_tests.py",
            "tools/v1216_9_operator_repair_result_review_checkpoint_tests.py",
        ),
        (
            "conscious_agent/*build_test*.py",
            "conscious_agent/*diagnosis*.py",
            "conscious_agent/*repair*.py",
            "tools/v1210_*.py",
            "tools/v1213_*.py",
            "tools/v1214_*.py",
            "tools/v1215_*.py",
            "tools/v1216_*.py",
        ),
        900,
        "campaign",
    ),
    VerificationStage(
        "apply-rollback",
        "Transactional apply and rollback",
        (
            "tools/v1219_9_supervised_repaired_candidate_rollback_checkpoint_tests.py",
            "tools/v1220_9_operator_repaired_candidate_rollback_result_review_checkpoint_tests.py",
        ),
        (
            "conscious_agent/*apply*.py",
            "conscious_agent/*rollback*.py",
            "tools/v1217_*.py",
            "tools/v1218_*.py",
            "tools/v1219_*.py",
            "tools/v1220_*.py",
        ),
        900,
        "runtime",
    ),
    VerificationStage(
        "queue-execution-recovery",
        "Queue, execution, intervention, and recovery",
        (
            "tools/v1228_9_execution_session_pause_resume_cancel_recovery_checkpoint_tests.py",
            "tools/v1230_9_mindful_execution_alpha_integration_benchmark_checkpoint_tests.py",
        ),
        (
            "conscious_agent/*work_queue*.py",
            "conscious_agent/*execution_session*.py",
            "conscious_agent/*recovery*.py",
            "conscious_agent/mindful_execution_alpha*.py",
            "tools/v1223_*.py",
            "tools/v1226_*.py",
            "tools/v1227_*.py",
            "tools/v1228_*.py",
            "tools/v1230_*.py",
        ),
        900,
        "runtime",
    ),
    VerificationStage(
        "cognition-lessons",
        "Cognition and revisable development lessons",
        (
            "tools/v1229_9_execution_outcome_reflection_learning_integration_checkpoint_tests.py",
            "tools/v1235_9_evidence_backed_development_outcome_lessons_checkpoint_tests.py",
            "tools/v1252_3_5_memory_storage_indexing_tests.py",
        ),
        (
            "conscious_agent/*reflection*.py",
            "conscious_agent/*lesson*.py",
            "conscious_agent/*learning*.py",
            "tools/v1229_*.py",
            "tools/v1235_*.py",
            "conscious_agent/append_memory_journal.py",
            "conscious_agent/indexed_memory_retrieval.py",
            "conscious_agent/memory_compaction_recovery.py",
            "conscious_agent/persistent_state_index.py",
            "tools/v1252_3_5_*.py",
        ),
        900,
        "cognition",
    ),
    VerificationStage(
        "provider-project-governance",
        "Provider governance and cross-session project understanding",
        (
            "tools/v1243_9_provider_fallback_model_governance_checkpoint_tests.py",
            "tools/v1245_9_cross_session_project_understanding_checkpoint_tests.py",
            "tools/v1252_6_8_action_cache_migration_tests.py",
        ),
        (
            "conscious_agent/*provider*.py",
            "conscious_agent/*project_understanding*.py",
            "conscious_agent/cross_session*.py",
            "tools/v1243_*.py",
            "tools/v1245_*.py",
            "conscious_agent/indexed_chat_action_ledger.py",
            "conscious_agent/persistent_state_projection_cache.py",
            "conscious_agent/persistent_state_scaling_migration.py",
            "conscious_agent/persistent_state_index.py",
            "tools/v1252_6_8_*.py",
        ),
        900,
        "platform",
    ),
    VerificationStage(
        "dashboard-interface",
        "Operator dashboard and public interface stability",
        (
            "tools/v1241_9_unified_operator_dashboard_checkpoint_tests.py",
            "tools/v1246_9_initiative_proposal_pacing_checkpoint_tests.py",
            "tools/v1250_7_dashboard_shell_decomposition_tests.py",
            "tools/v1250_8_api_catalog_http_runtime_decomposition_tests.py",
            "tools/v1251_6_8_dashboard_response_time_tests.py",
            "tools/v1253_3_5_import_dependency_efficiency_tests.py",
            "tools/v1253_6_8_performance_governance_tests.py",
        ),
        (
            "conscious_agent/dashboard*.py",
            "conscious_agent/api_server.py",
            "conscious_agent/api_catalog.py",
            "conscious_agent/api_http_runtime.py",
            "conscious_agent/api_surface_runtime_decomposition*.py",
            "conscious_agent/unified_operator_dashboard*.py",
            "conscious_agent/initiative_proposal_pacing*.py",
            "eidolon.py",
            "tools/v1241_*.py",
            "tools/v1246_*.py",
            "tools/v1250_[78]_*.py",
            "conscious_agent/dashboard_performance.py",
            "conscious_agent/runtime_projection_cache.py",
            "conscious_agent/static/dashboard.*",
            "tools/v1251_6_8_*.py",
            "conscious_agent/dashboard_fast_status.py",
            "conscious_agent/self_maintenance_attention_primitives.py",
            "conscious_agent/performance_budgets.py",
            "conscious_agent/performance_regression.py",
            "conscious_agent/runtime_efficiency_benchmark.py",
            "conscious_agent/runtime_efficiency_beta.py",
            "tools/v1253_3_5_*.py",
            "tools/v1253_6_8_*.py",
        ),
        900,
        "platform",
    ),
    VerificationStage(
        "retained-checkpoints",
        "Representative retained checkpoint compatibility",
        (
            "tools/v1209_9_general_test_adapter_consolidation_checkpoint_tests.py",
            "tools/v1240_9_integrated_developer_beta_checkpoint_tests.py",
            "tools/v1248_9_integrated_mind_conversation_development_benchmark_checkpoint_tests.py",
            "tools/v1249_9_feature_freeze_final_hardening_checkpoint_tests.py",
            "tools/v1250_3_release_metadata_consolidation_tests.py",
            "tools/v1250_4_checkpoint_registry_consolidation_tests.py",
            "tools/v1250_5_compatibility_registry_migration_tests.py",
            "tools/v1250_6_self_maintenance_signature_primitive_decomposition_tests.py",
            "tools/v1250_7_dashboard_shell_decomposition_tests.py",
            "tools/v1250_8_api_catalog_http_runtime_decomposition_tests.py",
            "tools/v1250_9_cleanup_verification_hardening_checkpoint_tests.py",
            "tools/v1251_9_response_time_runtime_efficiency_checkpoint_tests.py",
            "tools/v1252_9_persistent_state_performance_checkpoint_tests.py",
            "tools/v1253_9_runtime_efficiency_beta_checkpoint_tests.py",
            "tools/v1253_9_1_pre_codex_runtime_coherence_repair_tests.py",
            "tools/v1253_9_2_windows_runtime_coherence_repair_tests.py",
        ),
        (
            "conscious_agent/checkpoint_registry.py",
            "conscious_agent/*registry*checkpoint.py",
            "conscious_agent/release_metadata.py",
            "conscious_agent/release_metadata_consolidation.py",
            "conscious_agent/compatibility_registry.py",
            "conscious_agent/release_authority.py",
            "conscious_agent/release_signature_primitives.py",
            "conscious_agent/self_maintenance_decomposition*.py",
            "conscious_agent/dashboard_layout.py",
            "conscious_agent/dashboard_shell_decomposition*.py",
            "conscious_agent/api_catalog.py",
            "conscious_agent/api_http_runtime.py",
            "conscious_agent/api_surface_runtime_decomposition*.py",
            "docs/compatibility/*.json",
            "docs/release/*.json",
            "README*.md",
            "tools/release_verify.py",
            "tools/v1209_9*.py",
            "tools/v1240_9*.py",
            "tools/v1248_9*.py",
            "tools/v1249_9*.py",
            "tools/v1250_[3456789]_*.py",
            "conscious_agent/response_time_runtime_efficiency_checkpoint.py",
            "tools/v1251_9_*.py",
            "conscious_agent/persistent_state_performance.py",
            "conscious_agent/persistent_state_performance_checkpoint.py",
            "conscious_agent/persistent_state_index.py",
            "tools/v1252_9_*.py",
            "conscious_agent/runtime_efficiency_beta.py",
            "conscious_agent/runtime_efficiency_beta_checkpoint.py",
            "conscious_agent/performance_budgets.py",
            "conscious_agent/performance_regression.py",
            "conscious_agent/runtime_efficiency_benchmark.py",
            "tools/v1253_9_*.py",
            "conscious_agent/pre_codex_runtime_coherence_repair*.py",
            "conscious_agent/performance_baseline.py",
            "conscious_agent/runtime_contention_benchmark.py",
            "conscious_agent/bounded_internal_maintenance.py",
            "conscious_agent/chat_launcher.py",
            "conscious_agent/response_time_runtime.py",
        ),
        1800,
        "release",
    ),
)


def validate_stage_definitions(stages: Sequence[VerificationStage], *, source_root: str | Path | None = None) -> list[str]:
    errors: list[str] = []
    if not stages:
        errors.append("empty_stage_manifest")
    ids = [stage.stage_id for stage in stages]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_stage_id")
    root = Path(source_root).resolve() if source_root is not None else None
    for stage in stages:
        if not stage.stage_id or not all(char.islower() or char.isdigit() or char == "-" for char in stage.stage_id):
            errors.append("invalid_stage_id")
        if not stage.suites:
            errors.append("stage_without_suites")
        if not stage.input_globs:
            errors.append("stage_without_input_globs")
        if not 1 <= int(stage.budget_seconds) <= 3600:
            errors.append("invalid_stage_budget")
        for suite in stage.suites:
            path = Path(suite)
            if path.is_absolute() or ".." in path.parts or not suite.startswith("tools/"):
                errors.append("invalid_suite_path")
            elif root is not None and not (root / path).is_file():
                errors.append("missing_suite")
        row = stage.as_dict()
        if not _is_digest(row.get("stage_manifest_digest")):
            errors.append("invalid_stage_digest")
        if {key.lower() for key in row} & PRIVATE_RECEIPT_KEYS:
            errors.append("private_stage_field")
    return sorted(set(errors))


def _matching_input_files(source: Path, patterns: Sequence[str]) -> list[Path]:
    files: dict[str, Path] = {}
    for pattern in patterns:
        for path in source.glob(pattern):
            if path.is_file():
                files[path.relative_to(source).as_posix()] = path
    return [files[name] for name in sorted(files)]


def stage_input_digest(stage: VerificationStage, *, source_root: str | Path) -> dict[str, Any]:
    source = Path(source_root).resolve()
    rows = []
    for path in _matching_input_files(source, stage.input_globs):
        data = path.read_bytes()
        rows.append(
            {
                "relative_path": path.relative_to(source).as_posix(),
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    result = {
        "stage_id": stage.stage_id,
        "input_file_count": len(rows),
        "input_digest": _digest(rows),
        "stage_manifest_digest": stage.as_dict()["stage_manifest_digest"],
    }
    result["stage_state_digest"] = _digest(result)
    return result


def build_segmented_verifier_manifest(
    *,
    source_root: str | Path | None = None,
    stages: Sequence[VerificationStage] = DEFAULT_STAGES,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    errors = validate_stage_definitions(stages, source_root=source)
    rows = []
    for index, stage in enumerate(stages, 1):
        row = stage.as_dict()
        row["ordinal"] = index
        row.update(stage_input_digest(stage, source_root=source))
        rows.append(row)
    manifest = {
        "ok": not errors,
        "status": "segmented_verifier_manifest_ready" if not errors else "segmented_verifier_manifest_blocked",
        "contract_version": CONTRACT_VERSION,
        "stage_count": len(rows),
        "stages": rows,
        "errors": errors,
        "independently_runnable": True,
        "partial_receipts_supported": True,
        "suite_level_progress_receipts": True,
        "per_suite_runtime_isolation": True,
        "per_suite_timeout_seconds": DEFAULT_SUITE_TIMEOUT_SECONDS,
        "exact_resume_supported": True,
        "stale_receipt_rejected": True,
        "bounded_stage_budgets": True,
        "clean_external_snapshot_default": True,
        "repository_size_thresholds_used": False,
        "read_only_manifest": True,
        **AUTHORITY_FLAGS,
    }
    manifest["manifest_digest"] = _digest(manifest)
    return manifest


def _load_receipt(value: str | Path | Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    path = Path(value)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("resume_receipt_must_be_object")
    return dict(data)


def _prior_stage_map(receipt: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if not receipt:
        return {}
    rows = receipt.get("stage_receipts") or []
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("stage_id")): dict(row)
        for row in rows
        if isinstance(row, Mapping) and row.get("stage_id")
    }


def _stage_receipt_reusable(prior: Mapping[str, Any] | None, state: Mapping[str, Any]) -> bool:
    if not prior:
        return False
    return (
        prior.get("status") in {"passed", "reused_pass"}
        and prior.get("input_digest") == state.get("input_digest")
        and prior.get("stage_manifest_digest") == state.get("stage_manifest_digest")
        and prior.get("stage_state_digest") == state.get("stage_state_digest")
    )


def _receipt_has_private_fields(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in PRIVATE_RECEIPT_KEYS:
                return True
            if _receipt_has_private_fields(item):
                return True
    elif isinstance(value, list):
        return any(_receipt_has_private_fields(item) for item in value)
    return False


def run_segmented_verification(
    *,
    source_root: str | Path | None = None,
    stage_ids: Sequence[str] | None = None,
    receipt_path: str | Path | None = None,
    resume_receipt: str | Path | Mapping[str, Any] | None = None,
    stages: Sequence[VerificationStage] = DEFAULT_STAGES,
    stop_on_failure: bool = True,
    snapshot: bool = True,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    manifest = build_segmented_verifier_manifest(source_root=source, stages=stages)
    requested = list(stage_ids or [stage.stage_id for stage in stages])
    stage_by_id = {stage.stage_id: stage for stage in stages}
    unknown = sorted(set(requested) - set(stage_by_id))
    duplicate_request = len(requested) != len(set(requested))
    if not manifest["ok"] or unknown or duplicate_request:
        return {
            "ok": False,
            "status": "segmented_verification_request_blocked",
            "contract_version": CONTRACT_VERSION,
            "unknown_stage_ids": unknown,
            "duplicate_stage_request": duplicate_request,
            "manifest_errors": manifest.get("errors", []),
            "stage_receipts": [],
            "release_authorized": False,
            **AUTHORITY_FLAGS,
        }
    if receipt_path is not None and not validate_external_path(receipt_path, source_root=source)["ok"]:
        return {
            "ok": False,
            "status": "receipt_path_inside_source_blocked",
            "contract_version": CONTRACT_VERSION,
            "stage_receipts": [],
            "release_authorized": False,
            **AUTHORITY_FLAGS,
        }

    prior_receipt = _load_receipt(resume_receipt)
    if prior_receipt and _receipt_has_private_fields(prior_receipt):
        return {
            "ok": False,
            "status": "private_resume_receipt_blocked",
            "contract_version": CONTRACT_VERSION,
            "stage_receipts": [],
            "release_authorized": False,
            **AUTHORITY_FLAGS,
        }
    prior_stages = _prior_stage_map(prior_receipt)
    source_before = source_signature(source)
    session_started = _utc_now()
    monotonic_started = time.monotonic()
    stage_receipts: list[dict[str, Any]] = []
    runtime_cleanup_ok = False
    snapshot_receipt: Mapping[str, Any] | None = None
    runtime_root_digest = ""

    def current_session(
        status: str,
        *,
        resumable_next_stage: str | None = None,
        active_stage_id: str | None = None,
        active_suite_path: str | None = None,
        active_suite_index: int | None = None,
        active_suite_count: int | None = None,
        active_suite_completed_count: int | None = None,
        active_phase: str | None = None,
    ) -> dict[str, Any]:
        source_after = source_signature(source)
        complete = len(stage_receipts) == len(requested) and all(
            row.get("status") in {"passed", "reused_pass"} for row in stage_receipts
        )
        result = {
            "ok": complete and source_after.get("tree_digest") == source_before.get("tree_digest"),
            "status": status,
            "contract_version": CONTRACT_VERSION,
            "manifest_digest": manifest.get("manifest_digest"),
            "requested_stage_ids": requested,
            "requested_stage_count": len(requested),
            "stage_receipts": stage_receipts,
            "completed_stage_count": sum(row.get("status") in {"passed", "reused_pass"} for row in stage_receipts),
            "executed_stage_count": sum(row.get("status") == "passed" for row in stage_receipts),
            "reused_stage_count": sum(row.get("status") == "reused_pass" for row in stage_receipts),
            "failed_stage_count": sum(row.get("status") not in {"passed", "reused_pass"} for row in stage_receipts),
            "resumable_next_stage": resumable_next_stage,
            "partial_receipt": not complete,
            "session_started_at": session_started,
            "session_completed_at": _utc_now(),
            "elapsed_seconds": round(time.monotonic() - monotonic_started, 6),
            "source_signature_before": source_before,
            "source_signature_after": source_after,
            "source_unchanged": source_after.get("tree_digest") == source_before.get("tree_digest"),
            "snapshot_enabled": snapshot,
            "snapshot_receipt": dict(snapshot_receipt) if isinstance(snapshot_receipt, Mapping) else None,
            "runtime_root_digest": runtime_root_digest,
            "runtime_cleanup_ok": runtime_cleanup_ok,
            "partial_receipts_supported": True,
            "suite_level_progress_receipts": True,
            "per_suite_runtime_isolation": True,
            "per_suite_timeout_seconds": DEFAULT_SUITE_TIMEOUT_SECONDS,
            "active_stage_id": active_stage_id,
            "active_suite_path": active_suite_path,
            "active_suite_path_digest": hashlib.sha256(active_suite_path.encode("utf-8")).hexdigest() if active_suite_path else None,
            "active_suite_index": active_suite_index,
            "active_suite_count": active_suite_count,
            "active_suite_completed_count": active_suite_completed_count,
            "active_phase": active_phase,
            "exact_resume_supported": True,
            "release_authorized": False,
            **AUTHORITY_FLAGS,
        }
        result["session_receipt_digest"] = _digest(result)
        return result

    with tempfile.TemporaryDirectory(prefix="eidolon-v1250-segmented-") as runtime_text:
        runtime = Path(runtime_text).resolve()
        runtime_root_digest = hashlib.sha256(str(runtime).encode("utf-8")).hexdigest()
        execution_root = runtime / "source-snapshot" if snapshot else source
        if snapshot:
            snapshot_receipt = copy_clean_source_snapshot(source_root=source, snapshot_root=execution_root)
        runtime_data = runtime / "runtime"

        for position, stage_id in enumerate(requested):
            stage = stage_by_id[stage_id]
            state = stage_input_digest(stage, source_root=source)
            prior = prior_stages.get(stage_id)
            if _stage_receipt_reusable(prior, state):
                row = {
                    "stage_id": stage_id,
                    "label": stage.label,
                    "ordinal": position + 1,
                    "status": "reused_pass",
                    "ok": True,
                    "input_digest": state["input_digest"],
                    "stage_manifest_digest": state["stage_manifest_digest"],
                    "stage_state_digest": state["stage_state_digest"],
                    "suite_count": len(stage.suites),
                    "suite_receipts": [],
                    "elapsed_seconds": 0.0,
                    "prior_stage_receipt_digest": prior.get("stage_receipt_digest"),
                    "reused_without_execution": True,
                    **AUTHORITY_FLAGS,
                }
                row["stage_receipt_digest"] = _digest(row)
                stage_receipts.append(row)
            else:
                stage_started = time.monotonic()
                suite_receipts: list[dict[str, Any]] = []
                stage_status = "passed"
                for suite_index, suite in enumerate(stage.suites, 1):
                    elapsed = time.monotonic() - stage_started
                    remaining = max(0.0, stage.budget_seconds - elapsed)
                    if remaining <= 0:
                        stage_status = "stage_budget_exhausted"
                        break
                    suite_timeout = min(
                        remaining,
                        float(SUITE_TIMEOUT_OVERRIDES.get(suite, DEFAULT_SUITE_TIMEOUT_SECONDS)),
                    )
                    # Keep Windows subprocess workspaces below MAX_PATH even
                    # when a fixture creates several additional nested roots.
                    suite_runtime = runtime_data / f"s{position + 1:02d}-{suite_index:02d}"
                    env = build_hermetic_environment(runtime_root=suite_runtime, source_root=source)
                    if suite == "tools/v1252_9_persistent_state_performance_checkpoint_tests.py":
                        env["EIDOLON_V1252_BENCHMARK_PROFILE"] = "medium"
                    env["PYTHONPATH"] = os.pathsep.join(
                        [str(execution_root), str(execution_root / "conscious_agent"), str(execution_root / "tools")]
                    )
                    if receipt_path is not None:
                        progress = current_session(
                            "segmented_verification_running",
                            resumable_next_stage=stage_id,
                            active_stage_id=stage_id,
                            active_suite_path=suite,
                            active_suite_index=suite_index,
                            active_suite_count=len(stage.suites),
                            active_suite_completed_count=len(suite_receipts),
                            active_phase="suite_running",
                        )
                        atomic_write_json(receipt_path, progress, source_root=source)
                    command = [sys.executable, suite]
                    command_result = run_bounded_command(
                        command,
                        cwd=execution_root,
                        env=env,
                        timeout_seconds=suite_timeout,
                    )
                    suite_row = {
                        "suite_path": suite,
                        "suite_path_digest": hashlib.sha256(suite.encode("utf-8")).hexdigest(),
                        "suite_index": suite_index,
                        "suite_timeout_seconds": suite_timeout,
                        "runtime_isolated": True,
                        **command_result.as_dict(),
                    }
                    suite_receipts.append(suite_row)
                    if receipt_path is not None:
                        progress = current_session(
                            "segmented_verification_running" if command_result.ok else "segmented_verification_blocked",
                            resumable_next_stage=stage_id,
                            active_stage_id=stage_id,
                            active_suite_path=suite,
                            active_suite_index=suite_index,
                            active_suite_count=len(stage.suites),
                            active_suite_completed_count=len(suite_receipts),
                            active_phase="suite_completed",
                        )
                        atomic_write_json(receipt_path, progress, source_root=source)
                    if not command_result.ok:
                        stage_status = command_result.status
                        break
                debris = scan_forbidden_runtime_entries(execution_root)
                if not debris["ok"] and stage_status == "passed":
                    stage_status = "runtime_debris_detected"
                row = {
                    "stage_id": stage_id,
                    "label": stage.label,
                    "ordinal": position + 1,
                    "status": stage_status,
                    "ok": stage_status == "passed",
                    "input_digest": state["input_digest"],
                    "stage_manifest_digest": state["stage_manifest_digest"],
                    "stage_state_digest": state["stage_state_digest"],
                    "suite_count": len(stage.suites),
                    "completed_suite_count": len(suite_receipts),
                    "suite_receipts": suite_receipts,
                    "elapsed_seconds": round(time.monotonic() - stage_started, 6),
                    "budget_seconds": stage.budget_seconds,
                    "suite_timeout_cap_seconds": DEFAULT_SUITE_TIMEOUT_SECONDS,
                    "per_suite_runtime_isolation": True,
                    "runtime_debris_scan": debris,
                    "reused_without_execution": False,
                    **AUTHORITY_FLAGS,
                }
                row["stage_receipt_digest"] = _digest(row)
                stage_receipts.append(row)

            next_stage = requested[position + 1] if position + 1 < len(requested) else None
            partial = current_session(
                "segmented_verification_running"
                if stage_receipts[-1]["ok"] and next_stage
                else (
                    "segmented_verification_complete"
                    if stage_receipts[-1]["ok"] and not next_stage
                    else "segmented_verification_blocked"
                ),
                resumable_next_stage=next_stage if stage_receipts[-1]["ok"] else stage_id,
            )
            if receipt_path is not None:
                atomic_write_json(receipt_path, partial, source_root=source)
            if not stage_receipts[-1]["ok"] and stop_on_failure:
                break

    runtime_cleanup_ok = not Path(runtime_text).exists()
    failed = next((row for row in stage_receipts if not row.get("ok")), None)
    if failed:
        resumable = str(failed.get("stage_id"))
        status = "segmented_verification_blocked"
    elif len(stage_receipts) < len(requested):
        resumable = requested[len(stage_receipts)]
        status = "segmented_verification_partial"
    else:
        resumable = None
        status = "segmented_verification_complete"
    final = current_session(status, resumable_next_stage=resumable)
    if receipt_path is not None:
        final["receipt_write"] = atomic_write_json(receipt_path, final, source_root=source)
    return final


__all__ = [
    "CONTRACT_VERSION",
    "VerificationStage",
    "DEFAULT_SUITE_TIMEOUT_SECONDS",
    "SUITE_TIMEOUT_OVERRIDES",
    "DEFAULT_STAGES",
    "validate_stage_definitions",
    "stage_input_digest",
    "build_segmented_verifier_manifest",
    "run_segmented_verification",
]
