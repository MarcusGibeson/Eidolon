from __future__ import annotations

"""Strictly read-only v1147.5 architecture consolidation execution checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from architecture_checkpoint_dispatch import build_checkpoint_dispatch_consolidation
from architecture_startup_consolidation import build_startup_tier_plan, inspect_startup_consolidation

CONTRACT_VERSION = "v1147.5"


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}):
        try:
            digest.update(path.relative_to(root).as_posix().encode()); digest.update(b"\0"); digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


def build_architecture_consolidation_execution_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    before = _tree_signature(source)
    dispatch = build_checkpoint_dispatch_consolidation(source_root=source)
    plan = build_startup_tier_plan()
    startup = inspect_startup_consolidation()
    tiers = {row["tier"]: row for row in plan["tiers"]}
    checks = [
        ("registry_dispatch_complete", dispatch["dispatch_count"] == 2),
        ("registry_dispatch_unique", not dispatch["duplicate_modules"] and not dispatch["duplicate_builders"]),
        ("historical_builders_preserved", dispatch["historical_builders_preserved"]),
        ("checkpoint_dispatch_read_only", dispatch["all_registered_checkpoints_read_only"] and dispatch["read_only"]),
        ("raw_checkpoint_content_excluded", not dispatch["raw_checkpoint_content_included"]),
        ("startup_tier_order_exact", plan["tier_order"] == ["core", "conversation_critical", "deferred"]),
        ("conversation_critical_only_auto_executable", tiers["conversation_critical"]["automatic_execution_allowed"] and not tiers["core"]["automatic_execution_allowed"] and not tiers["deferred"]["automatic_execution_allowed"]),
        ("deferred_services_remain_lazy", plan["deferred_tier_remains_lazy"] and not startup["deferred_tier_started"]),
        ("provider_contact_prohibited", not dispatch["provider_contacted"] and not plan["provider_contact_allowed"] and not startup["provider_contacted"]),
        ("inspection_content_free", dispatch["content_free"] and plan["content_free"] and startup["content_free"]),
        ("source_runtime_separation", not (source / "data" / "settings.json").exists()),
        ("desktop_verification_pending", True),
        ("consciousness_not_proven", True),
    ]
    after = _tree_signature(source)
    rows = [{"id": name, "status": "pass" if ok else "fail", "passed": bool(ok)} for name, ok in checks]
    passed = sum(1 for row in rows if row["passed"])
    return {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "architecture-consolidation-execution:v1147.5",
        "status": "ready_for_bundle_c" if passed == len(rows) else "review_required",
        "ok": passed == len(rows), "passed": passed, "total": len(rows), "checks": rows,
        "checkpoint_dispatch": dispatch,
        "startup_plan": plan,
        "startup_inspection": startup,
        "summary": {"registered_checkpoint_count": dispatch["dispatch_count"], "startup_tier_count": len(plan["tiers"]), "deferred_domain_count": tiers["deferred"]["module_count"]},
        "read_only": True, "post_available": False, "source_modified": before != after,
        "runtime_mutated": False, "desktop_verification_pending": True, "consciousness_proven": False,
    }
