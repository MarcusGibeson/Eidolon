from __future__ import annotations

from pathlib import Path

try:
    from checkpoint_registry import build_read_only_checkpoint_report
    from cleanup_verification_hardening import validate_cleanup_verification_hardening
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report  # type: ignore
    from cleanup_verification_hardening import validate_cleanup_verification_hardening  # type: ignore


def build_cleanup_verification_hardening_checkpoint(
    *, source_root: str | Path | None = None
) -> dict:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    validation = validate_cleanup_verification_hardening(source_root=root)
    checks = validation.get("checks", {})
    return build_read_only_checkpoint_report(
        version="1250.9",
        status="cleanup_verification_hardening_checkpoint_ready",
        checks={
            "structured_authority_current": checks.get("release_authority_current") is True,
            "complete_segmented_manifest_ready": checks.get("ten_stage_manifest") is True,
            "suite_level_progress_and_isolation_ready": checks.get("suite_level_progress_receipts") is True
            and checks.get("per_suite_runtime_isolation") is True
            and checks.get("per_suite_timeout_bounded") is True,
            "hermetic_process_cleanup_ready": checks.get("temporary_file_output_capture") is True
            and checks.get("residual_process_group_cleanup") is True,
            "checkpoint_and_documentation_current": checks.get("checkpoint_registry_current") is True
            and checks.get("active_documentation_current") is True
            and checks.get("checkpoint_handoff_documents_present") is True,
            "codex_review_gate_ready_without_release_authority": checks.get("codex_review_gate_ready") is True
            and checks.get("review_not_release_authority") is True,
        },
        source_root=root,
        details={
            "validation_digest": validation.get("validation_digest"),
            "stage_count": validation.get("stage_count"),
            "retained_suite_count": validation.get("retained_suite_count"),
            "per_suite_timeout_seconds": validation.get("per_suite_timeout_seconds"),
            "codex_review_state": validation.get("codex_review_state"),
        },
    )


__all__ = ["build_cleanup_verification_hardening_checkpoint"]
