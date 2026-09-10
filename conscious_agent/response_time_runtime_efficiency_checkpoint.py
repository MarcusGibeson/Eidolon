from __future__ import annotations

"""Read-only v1251.9 Response-Time and Runtime Efficiency Alpha checkpoint."""

import hashlib
import json
from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from response_time_efficiency import response_time_contract

CONTRACT_VERSION = "v1251.9"
CHECKPOINT_ID = "response-time-runtime-efficiency-alpha-checkpoint"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def build_response_time_runtime_efficiency_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    del runtime_root
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    contract = response_time_contract(source_root=root)
    docs = all((root / name).is_file() for name in (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1251_0_2.md", "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1251_3_5.md", "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1251_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1251_9_FINAL_VALIDATION.md", "docs/release/v1251_response_time_budgets.json",
    ))
    checks = {
        "integrated_contract_passes": contract.get("ok") is True,
        "all_nine_precheckpoint_units_present": len(contract.get("versions") or []) == 9,
        "ordinary_projection_bounded": int(contract.get("ordinary_projection_estimated_tokens") or 9999) <= 800,
        "social_projection_bounded": int(contract.get("social_projection_estimated_tokens") or 9999) <= 600,
        "authority_remains_denied": not any(bool(contract.get(k)) for k in ("approval_granted","tool_execution_authorized","project_mutation_authorized","provider_contact_authorized","release_authorized","independent_authority_granted")),
        "checkpoint_docs_present": docs,
    }
    details = {
        "response_time_contract_digest": contract.get("contract_digest"),
        "ordinary_projection_estimated_tokens": contract.get("ordinary_projection_estimated_tokens"),
        "social_projection_estimated_tokens": contract.get("social_projection_estimated_tokens"),
        "native_desktop_performance_review_deferred_to_v1253_9": True,
    }
    report = build_read_only_checkpoint_report(
        version="1251.9", status="response_time_runtime_efficiency_alpha_checkpoint_ready",
        checks=checks, source_root=root, details=details,
    )
    return report


__all__ = ["CONTRACT_VERSION", "CHECKPOINT_ID", "build_response_time_runtime_efficiency_checkpoint"]
