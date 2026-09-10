from __future__ import annotations

"""v1276.9 read-only Architecture Boundary Extraction checkpoint."""

from pathlib import Path
from typing import Any

from architecture_boundary_foundations import AUTHORITY_FLAGS, build_architecture_boundary_inventory
from architecture_boundary_integration import build_architecture_boundary_integration_report
from architecture_boundary_reliability import CONTRACT_VERSION as RELIABILITY_CONTRACT_VERSION
from checkpoint_registry import build_read_only_checkpoint_report

CONTRACT_VERSION = "v1276.9"


def build_architecture_boundary_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    foundations = build_architecture_boundary_inventory(root)
    integration = build_architecture_boundary_integration_report(root)
    reliability = {"ok": RELIABILITY_CONTRACT_VERSION == "v1276.8", "contract_version": RELIABILITY_CONTRACT_VERSION}
    report = build_read_only_checkpoint_report(
        version="1276.9",
        status="architecture_boundary_extraction_checkpoint_ready",
        checks={
            "evidence_backed_boundaries": foundations.get("ok") is True,
            "behavior_and_surface_preserved": integration.get("ok") is True,
            "restart_import_reliability": reliability.get("ok") is True,
            "three_target_modules_reduced": foundations.get("boundary_count") == 3,
            "authority_ownership_preserved": integration.get("parent_dispatch_ownership_preserved") is True,
        },
        source_root=root,
        details={
            "foundations_digest": foundations.get("inventory_digest"),
            "integration_digest": integration.get("integration_digest"),
            "reliability_contract_version": reliability.get("contract_version"),
            "reliability_suite": "tools/v1276_6_8_architecture_boundary_reliability_tests.py",
            "next_bounded_unit": "v1277 Development Observability",
            "v1277_started": False,
            "checkpoint_executes_provider": False,
            "checkpoint_executes_commands": False,
            "checkpoint_executes_tests": False,
            "checkpoint_executes_install": False,
            "checkpoint_executes_update": False,
            "checkpoint_mutates_source": False,
            "aesthetic_refactor_authorized": False,
            **AUTHORITY_FLAGS,
        },
    )
    return report


__all__ = ["CONTRACT_VERSION", "build_architecture_boundary_checkpoint"]
