from __future__ import annotations

from pathlib import Path

try:
    from checkpoint_registry import build_read_only_checkpoint_report
    from release_metadata_consolidation import validate_release_metadata_consolidation
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report  # type: ignore
    from release_metadata_consolidation import validate_release_metadata_consolidation  # type: ignore


def build_release_metadata_consolidation_checkpoint(*, source_root: str | Path | None = None) -> dict:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    validation = validate_release_metadata_consolidation(source_root=root)
    return build_read_only_checkpoint_report(
        version="1250.3",
        status="release_metadata_consolidation_ready",
        checks={
            "metadata_validation_passed": validation.get("ok") is True,
            "single_active_authority": validation.get("active_authority_count") == 1,
            "generated_facade": validation.get("generated_facade") is True,
        },
        source_root=root,
        details={"metadata_validation_digest": validation.get("validation_digest")},
    )


__all__ = ["build_release_metadata_consolidation_checkpoint"]
