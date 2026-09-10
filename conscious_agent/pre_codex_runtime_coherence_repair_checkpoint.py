from __future__ import annotations

"""Read-only v1253.9.1 pre-Codex runtime coherence repair checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from pre_codex_runtime_coherence_repair import pre_codex_runtime_coherence_contract

CONTRACT_VERSION = "v1253.9.1"
CHECKPOINT_ID = "pre-codex-runtime-coherence-repair"


def build_pre_codex_runtime_coherence_repair_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    del runtime_root
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    contract = pre_codex_runtime_coherence_contract(source_root=root)
    docs = all((root / name).is_file() for name in (
        "archive/docs/legacy_dependencies/validation/Eidolon_v1253_9_1_FINAL_VALIDATION.md",
        "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1253_9_1.md",
        "README.md",
        "README_NEXT_STEPS.md",
    ))
    checks = {
        "repair_contract_passes": contract.get("ok") is True,
        "repair_docs_present": docs,
        "runtime_authority_remains_denied": not any(bool(contract.get(key)) for key in (
            "approval_granted", "tool_execution_authorized", "project_mutation_authorized",
            "provider_contact_authorized", "release_authorized", "independent_authority_granted",
        )),
    }
    return build_read_only_checkpoint_report(
        version="1253.9.1",
        status="pre_codex_runtime_coherence_repair_checkpoint_ready",
        checks=checks,
        source_root=root,
        details={
            "repair_contract_digest": contract.get("contract_digest"),
            "desktop_codex_review_state": "ready_for_postponed_desktop_codex_review",
            "full_segmented_verifier_required": True,
            "fresh_extract_verifier_required": True,
        },
    )


__all__ = ["CONTRACT_VERSION", "CHECKPOINT_ID", "build_pre_codex_runtime_coherence_repair_checkpoint"]
