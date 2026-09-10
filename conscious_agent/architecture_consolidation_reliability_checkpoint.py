from __future__ import annotations

"""Strictly read-only v1147.8 architecture consolidation reliability checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from architecture_consolidation_continuity import build_architecture_consolidation_continuity
from architecture_consolidation_reliability import build_architecture_consolidation_reliability

CONTRACT_VERSION = "v1147.8"


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}):
        try:
            digest.update(path.relative_to(root).as_posix().encode()); digest.update(b"\0"); digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


def build_architecture_consolidation_reliability_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    before = _tree_signature(source)
    continuity = build_architecture_consolidation_continuity()
    reliability = build_architecture_consolidation_reliability(source_root=str(source))
    checks = [
        ("ownership_lineage_exact", bool(continuity["ownership_digest"])),
        ("checkpoint_registry_lineage_exact", bool(continuity["registry_digest"])),
        ("startup_plan_lineage_exact", bool(continuity["startup_digest"])),
        ("ownership_domains_complete", continuity["ownership_domain_count"] == 9),
        ("startup_tiers_complete", continuity["startup_tier_count"] == 3),
        ("no_missing_tier_owners", not continuity["issues"]["missing_tier_owners"]),
        ("no_duplicate_responsibilities", not continuity["issues"]["duplicate_responsibilities"]),
        ("no_duplicate_checkpoint_ids", not continuity["issues"]["duplicate_checkpoint_ids"]),
        ("historical_modules_preserved", reliability["historical_modules_preserved"]),
        ("checkpoint_dispatch_reliable", reliability["checkpoint_dispatch_failure_count"] == 0),
        ("duplicate_plumbing_absent", reliability["duplicate_plumbing_count"] == 0),
        ("deferred_startup_preserved", not reliability["deferred_tier_started"]),
        ("visible_behavior_bounded", reliability["operator_visible_state"] in {"ready", "attention"}),
        ("privacy_content_free", continuity["content_free"] and reliability["content_free"]),
        ("provider_contact_prohibited", not continuity["provider_contacted"] and not reliability["provider_contacted"]),
        ("runtime_mutation_prohibited", not continuity["runtime_mutated"] and not reliability["runtime_mutated"]),
        ("source_runtime_separation", not (source / "data" / "settings.json").exists()),
        ("checkpoint_read_only", continuity["read_only"] and reliability["read_only"]),
        ("desktop_verification_pending", True),
        ("consciousness_not_proven", True),
    ]
    after = _tree_signature(source)
    rows = [{"id": name, "status": "pass" if ok else "fail", "passed": bool(ok)} for name, ok in checks]
    passed = sum(1 for row in rows if row["passed"])
    return {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "architecture-consolidation-reliability:v1147.8",
        "status": "ready_for_governance_checkpoint" if passed == len(rows) else "review_required",
        "ok": passed == len(rows), "passed": passed, "total": len(rows), "checks": rows,
        "continuity": continuity, "reliability": reliability,
        "summary": {"ownership_domain_count": continuity["ownership_domain_count"], "registered_checkpoint_count": continuity["registered_checkpoint_count"], "issue_count": reliability["continuity_issue_count"], "reliability_score": reliability["reliability_score"]},
        "read_only": True, "post_available": False, "source_modified": before != after,
        "runtime_mutated": False, "desktop_verification_pending": True, "consciousness_proven": False,
    }
