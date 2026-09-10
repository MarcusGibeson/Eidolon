from __future__ import annotations

from pathlib import Path

try:
    from checkpoint_registry import build_read_only_checkpoint_report, checkpoint_registry_manifest
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report, checkpoint_registry_manifest  # type: ignore


def build_checkpoint_registry_consolidation_checkpoint(*, source_root: str | Path | None = None) -> dict:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    manifest = checkpoint_registry_manifest(source_root=root)
    return build_read_only_checkpoint_report(
        version="1250.4",
        status="checkpoint_registry_consolidation_ready",
        checks={
            "registry_manifest_passed": manifest.get("ok") is True,
            "all_checkpoint_tests_resolve": not manifest.get("errors"),
            "single_registry_authority": manifest.get("single_registry_authority") is True,
            "legacy_descriptor_surface_preserved": int(manifest.get("legacy_descriptor_count") or 0) >= 300,
        },
        source_root=root,
        details={
            "registry_digest": manifest.get("registry_digest"),
            "record_count": manifest.get("record_count"),
            "legacy_descriptor_count": manifest.get("legacy_descriptor_count"),
        },
    )


__all__ = ["build_checkpoint_registry_consolidation_checkpoint"]
