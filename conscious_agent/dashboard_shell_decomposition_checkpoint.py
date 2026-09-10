from __future__ import annotations

from pathlib import Path

try:
    from checkpoint_registry import build_read_only_checkpoint_report
    from dashboard_shell_decomposition import validate_dashboard_shell_decomposition
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report  # type: ignore
    from dashboard_shell_decomposition import validate_dashboard_shell_decomposition  # type: ignore


def build_dashboard_shell_decomposition_checkpoint(*, source_root: str | Path | None = None) -> dict:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    validation = validate_dashboard_shell_decomposition(source_root=root)
    return build_read_only_checkpoint_report(
        version="1250.7",
        status="dashboard_shell_decomposition_ready",
        checks={
            "decomposition_validation_passed": validation.get("ok") is True,
            "layout_parity_preserved": validation.get("checks", {}).get("deterministic_layout_parity") is True,
            "manual_dashboard_surface_preserved": validation.get("checks", {}).get("manual_dashboard_surface_preserved") is True,
        },
        source_root=root,
        details={
            "validation_digest": validation.get("validation_digest"),
            "parent_line_count": validation.get("parent_line_count"),
            "extracted_line_count": validation.get("extracted_line_count"),
        },
    )


__all__ = ["build_dashboard_shell_decomposition_checkpoint"]
