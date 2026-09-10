from __future__ import annotations

"""Read-only validation for the v1250.9 cleanup and verification checkpoint.

The contract verifies the cleanup arc's structured authority, segmented broad
verifier, hermetic process runtime, checkpoint registry, generated metadata,
and public documentation. It does not execute suites, contact providers,
install, promote, certify, release, mutate projects, or grant authority.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from checkpoint_registry import checkpoint_registry_manifest, lookup_checkpoint
    from hermetic_verification_runtime import hermetic_runtime_contract
    from release_authority import CODEX_REVIEW_STATE, PREVIOUS_WORKING_SOURCE_VERSION, WORKING_SOURCE_VERSION, validate_release_authority
    from release_metadata_consolidation import validate_release_metadata_consolidation
    from segmented_release_verifier import DEFAULT_SUITE_TIMEOUT_SECONDS, build_segmented_verifier_manifest
except ImportError:
    from checkpoint_registry import checkpoint_registry_manifest, lookup_checkpoint  # type: ignore
    from hermetic_verification_runtime import hermetic_runtime_contract  # type: ignore
    from release_authority import (  # type: ignore
        CODEX_REVIEW_STATE,
        PREVIOUS_WORKING_SOURCE_VERSION,
        WORKING_SOURCE_VERSION,
        validate_release_authority,
    )
    from release_metadata_consolidation import validate_release_metadata_consolidation  # type: ignore
    from segmented_release_verifier import DEFAULT_SUITE_TIMEOUT_SECONDS, build_segmented_verifier_manifest  # type: ignore

CONTRACT_VERSION = "v1250.9"
EXPECTED_STAGE_IDS = (
    "source-privacy",
    "authority-approval",
    "conversation-command",
    "development-lifecycle",
    "apply-rollback",
    "queue-execution-recovery",
    "cognition-lessons",
    "provider-project-governance",
    "dashboard-interface",
    "retained-checkpoints",
)
AUTHORITY_FLAGS = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def validate_cleanup_verification_hardening(
    *, source_root: str | Path | None = None
) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    authority = validate_release_authority(source_root=root)
    manifest = build_segmented_verifier_manifest(source_root=root)
    registry = checkpoint_registry_manifest(source_root=root)
    runtime = hermetic_runtime_contract()
    metadata = validate_release_metadata_consolidation(source_root=root)
    stage_rows = {row["stage_id"]: row for row in manifest.get("stages", [])}
    conversation = stage_rows.get("conversation-command", {})
    retained = stage_rows.get("retained-checkpoints", {})
    conversation_suites = tuple(conversation.get("suites") or ())
    retained_suites = tuple(retained.get("suites") or ())
    docs = {
        name: (root / name).read_text(encoding="utf-8")
        for name in (
            "README.md",
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
        )
        if (root / name).is_file()
    }
    visible = {
        name: text.split('<details id="retained-pre-v1250-compatibility">', 1)[0]
        for name, text in docs.items()
    }
    checkpoint = lookup_checkpoint("1250.9")
    checks = {
        "release_authority_current": authority.get("ok") is True
        and bool(WORKING_SOURCE_VERSION)
        and bool(PREVIOUS_WORKING_SOURCE_VERSION),
        "codex_review_gate_ready": isinstance(CODEX_REVIEW_STATE, str)
        and bool(CODEX_REVIEW_STATE.strip()),
        "ten_stage_manifest": manifest.get("stage_count") == 10
        and tuple(row.get("stage_id") for row in manifest.get("stages", [])) == EXPECTED_STAGE_IDS,
        "suite_level_progress_receipts": manifest.get("suite_level_progress_receipts") is True,
        "per_suite_runtime_isolation": manifest.get("per_suite_runtime_isolation") is True,
        "per_suite_timeout_bounded": manifest.get("per_suite_timeout_seconds") == DEFAULT_SUITE_TIMEOUT_SECONDS
        and 180 <= DEFAULT_SUITE_TIMEOUT_SECONDS <= 300,
        "conversation_stage_semantic": "tools/v1206_0_2_natural_conversation_command_distinction_tests.py" in conversation_suites
        and "tools/v1206_9_browser_runtime_test_adapter_checkpoint_tests.py" not in conversation_suites,
        "checkpoint_self_in_retained_stage": "tools/v1250_9_cleanup_verification_hardening_checkpoint_tests.py" in retained_suites,
        "temporary_file_output_capture": runtime.get("temporary_file_output_capture") is True,
        "residual_process_group_cleanup": runtime.get("residual_process_group_cleanup") is True,
        "snapshot_external_to_source": runtime.get("clean_external_snapshot_required") is True,
        "metadata_generated_exactly": metadata.get("ok") is True
        and metadata.get("working_source_version") == WORKING_SOURCE_VERSION,
        "checkpoint_registry_current": registry.get("ok") is True
        and registry.get("working_source_version") == WORKING_SOURCE_VERSION
        and checkpoint is not None,
        "active_documentation_current": len(visible) == 4
        and all(f"v{WORKING_SOURCE_VERSION}" in text for text in visible.values()),
        "checkpoint_handoff_documents_present": (root / "archive/docs/legacy_dependencies/validation/Eidolon_v1250_9_CHECKPOINT_VALIDATION.md").is_file()
        and (root / "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1250_9.md").is_file(),
        "review_not_release_authority": all(value is False for value in AUTHORITY_FLAGS.values()),
    }
    passed = sum(bool(value) for value in checks.values())
    result: dict[str, Any] = {
        "ok": passed == len(checks),
        "status": "cleanup_verification_hardening_ready" if passed == len(checks) else "cleanup_verification_hardening_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "stage_count": manifest.get("stage_count"),
        "stage_ids": [row.get("stage_id") for row in manifest.get("stages", [])],
        "retained_suite_count": len(retained_suites),
        "per_suite_timeout_seconds": DEFAULT_SUITE_TIMEOUT_SECONDS,
        "codex_review_state": CODEX_REVIEW_STATE,
        "read_only": True,
        "content_free": True,
        "verification_executed": False,
        **AUTHORITY_FLAGS,
    }
    result["validation_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION",
    "EXPECTED_STAGE_IDS",
    "AUTHORITY_FLAGS",
    "validate_cleanup_verification_hardening",
]
