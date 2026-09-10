from __future__ import annotations

from pathlib import Path

try:
    from checkpoint_registry import build_read_only_checkpoint_report
    from compatibility_registry import validate_compatibility_registry
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report  # type: ignore
    from compatibility_registry import validate_compatibility_registry  # type: ignore


def build_compatibility_registry_migration_checkpoint(*, source_root: str | Path | None = None) -> dict:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    validation = validate_compatibility_registry(source_root=root)
    return build_read_only_checkpoint_report(
        version="1250.5",
        status="compatibility_registry_migration_ready",
        checks={
            "compatibility_registry_passed": validation.get("ok") is True,
            "structured_registry_primary": validation.get("structured_registry_primary") is True,
            "generated_facade_retained": validation.get("generated_facade_retained") is True,
        },
        source_root=root,
        details={"validation_digest": validation.get("validation_digest"), "entry_count": validation.get("entry_count")},
    )


__all__ = ["build_compatibility_registry_migration_checkpoint"]
