from __future__ import annotations

from pathlib import Path

try:
    from api_surface_runtime_decomposition import validate_api_surface_runtime_decomposition
    from checkpoint_registry import build_read_only_checkpoint_report
except ImportError:
    from api_surface_runtime_decomposition import validate_api_surface_runtime_decomposition  # type: ignore
    from checkpoint_registry import build_read_only_checkpoint_report  # type: ignore


def build_api_surface_runtime_decomposition_checkpoint(*, source_root: str | Path | None = None) -> dict:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    validation = validate_api_surface_runtime_decomposition(source_root=root)
    return build_read_only_checkpoint_report(
        version="1250.8",
        status="api_surface_runtime_decomposition_ready",
        checks={
            "decomposition_validation_passed": validation.get("ok") is True,
            "api_catalog_parity_preserved": validation.get("checks", {}).get("catalog_parity") is True,
            "manual_dispatch_preserved": validation.get("checks", {}).get("manual_dispatch_preserved") is True,
            "http_transport_has_no_route_ownership": validation.get("checks", {}).get("transport_has_no_route_builders") is True,
        },
        source_root=root,
        details={
            "validation_digest": validation.get("validation_digest"),
            "parent_line_count": validation.get("parent_line_count"),
            "catalog_line_count": validation.get("catalog_line_count"),
            "runtime_line_count": validation.get("runtime_line_count"),
            "endpoint_count": validation.get("endpoint_count"),
        },
    )


__all__ = ["build_api_surface_runtime_decomposition_checkpoint"]
