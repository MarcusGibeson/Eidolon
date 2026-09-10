from __future__ import annotations

from pathlib import Path

try:
    from checkpoint_registry import build_read_only_checkpoint_report
    from self_maintenance_decomposition import validate_self_maintenance_decomposition
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report  # type: ignore
    from self_maintenance_decomposition import validate_self_maintenance_decomposition  # type: ignore


def build_self_maintenance_decomposition_checkpoint(*, source_root: str | Path | None = None) -> dict:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    validation = validate_self_maintenance_decomposition(source_root=root)
    return build_read_only_checkpoint_report(
        version="1250.6",
        status="self_maintenance_decomposition_ready",
        checks={
            "decomposition_validation_passed": validation.get("ok") is True,
            "signature_primitives_extracted": validation.get("checks", {}).get("moved_definitions_present_in_child") is True,
            "historical_import_surface_preserved": validation.get("checks", {}).get("parent_surface_preserved") is True,
        },
        source_root=root,
        details={
            "validation_digest": validation.get("validation_digest"),
            "parent_line_count": validation.get("parent_line_count"),
            "extracted_line_count": validation.get("extracted_line_count"),
        },
    )


__all__ = ["build_self_maintenance_decomposition_checkpoint"]
