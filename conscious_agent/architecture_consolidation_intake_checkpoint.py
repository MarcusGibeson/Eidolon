from __future__ import annotations

"""Strictly read-only v1147.2 architecture consolidation intake checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from architecture_ownership_manifest import build_architecture_ownership_manifest
from checkpoint_registry import inspect_checkpoint_registry

CONTRACT_VERSION = "v1147.2"


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}):
        try:
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


def build_architecture_consolidation_intake_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    before = _tree_signature(source)
    ownership = build_architecture_ownership_manifest()
    registry = inspect_checkpoint_registry()
    startup_tiers = {row["startup_tier"] for row in ownership["domains"]}
    checks = [
        ("exact_ownership_domains", ownership["domain_count"] == 9 and not ownership["duplicate_domain_owners"]),
        ("single_structural_owner_per_domain", ownership["unique_owner_count"] == ownership["domain_count"]),
        ("responsibility_and_startup_tier_visible", all(row["responsibilities"] and row["startup_tier"] for row in ownership["domains"])),
        ("startup_tiers_bounded", startup_tiers <= {"core", "conversation_critical", "deferred"}),
        ("checkpoint_registry_consolidated", registry["checkpoint_count"] == 2 and not registry["duplicate_checkpoint_ids"]),
        ("checkpoint_registry_read_only", registry["read_only"] and all(row["read_only"] and not row["post_available"] for row in registry["checkpoints"])),
        ("historical_checkpoint_modules_preserved", all((source / (row["module"].replace(".", "/") + ".py")).exists() for row in registry["checkpoints"])),
        ("no_runtime_or_source_mutation_authority", not any(ownership["authority_boundary"].values())),
        ("content_free_structural_records", ownership["content_free"] and registry["content_free"]),
        ("source_runtime_separation", not (source / "data" / "settings.json").exists()),
        ("desktop_verification_pending", True),
        ("consciousness_not_proven", True),
    ]
    after = _tree_signature(source)
    rows = [{"id": name, "status": "pass" if ok else "fail", "passed": bool(ok)} for name, ok in checks]
    passed = sum(1 for row in rows if row["passed"])
    return {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "architecture-consolidation-intake:v1147.2",
        "status": "ready_for_bundle_b" if passed == len(rows) else "review_required",
        "ok": passed == len(rows),
        "passed": passed,
        "total": len(rows),
        "checks": rows,
        "ownership_manifest": ownership,
        "checkpoint_registry": registry,
        "summary": {"ownership_domain_count": ownership["domain_count"], "checkpoint_count": registry["checkpoint_count"], "startup_tier_count": len(startup_tiers)},
        "read_only": True,
        "post_available": False,
        "source_modified": before != after,
        "runtime_mutated": False,
        "desktop_verification_pending": True,
        "consciousness_proven": False,
    }
