from __future__ import annotations

"""Read-only v1198.2 feature-freeze and architecture-consolidation checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from feature_freeze_architecture_consolidation import ARCHITECTURE_AREAS, CONSOLIDATION_KINDS, assess_feature_freeze_architecture, create_component, create_consolidation_candidate, create_freeze_plan, public_feature_freeze_summary
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1198.2"


def _d(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _inventory(snapshot: str, context: str) -> list[dict[str, Any]]:
    return [create_component(component_id=f"component-{i:02d}", area=area, owner=f"owner-{area}", sequence=i,
        snapshot_digest=snapshot, context_digest=context, module_digest=_d(f"module:{area}"),
        interface_digest=_d(f"interface:{area}"), dependency_digest=_d(f"dependency:{area}"),
        startup_cost_ms=100 + i, purpose_code="feature_freeze_architecture_inventory")
        for i, area in enumerate(ARCHITECTURE_AREAS, 1)]


def _candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = [row["component_id"] for row in rows]
    return [
        create_consolidation_candidate(candidate_id="canonical-conversation", kind="canonical_owner", disposition="retain", canonical_component_id=ids[0], related_component_ids=[ids[1]], sequence=1, evidence_digest=_d("canonical"), purpose_code="architecture_owner_review"),
        create_consolidation_candidate(candidate_id="exact-duplicate", kind="exact_duplicate", disposition="alias_candidate", canonical_component_id=ids[2], related_component_ids=[ids[3]], sequence=2, evidence_digest=_d("duplicate"), purpose_code="duplicate_review"),
        create_consolidation_candidate(candidate_id="partial-overlap", kind="partial_overlap", disposition="merge_candidate", canonical_component_id=ids[4], related_component_ids=[ids[5]], sequence=3, evidence_digest=_d("overlap"), purpose_code="overlap_review"),
        create_consolidation_candidate(candidate_id="startup-hotspot", kind="startup_hotspot", disposition="defer", canonical_component_id=ids[6], related_component_ids=[ids[7]], sequence=4, evidence_digest=_d("startup"), purpose_code="startup_review"),
    ]


def build_feature_freeze_architecture_consolidation_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve(); del runtime_root
    checks: list[bool] = []
    def require(value: object) -> None: checks.append(bool(value))
    snapshot, context = _d("v1198.2:snapshot"), _d("v1198.2:context")
    plan = create_freeze_plan(plan_id="feature-freeze-foundations-0001", snapshot_digest=snapshot,
        context_digest=context, baseline_version="1197.9", architecture_digest=_d("architecture"),
        purpose_code="operator_feature_freeze_architecture_review", max_components=32, max_candidates=16,
        startup_budget_ms=30_000)
    rows = _inventory(snapshot, context); candidates = _candidates(rows)
    verification = {"current_regressions_separate": True, "inherited_debt_visible": True, "global_profile_pass_claimed": False}
    assessment = assess_feature_freeze_architecture(plan, rows, candidates, current_snapshot_digest=snapshot, current_context_digest=context, verification_summary=verification)
    summary = public_feature_freeze_summary(assessment)
    require(assessment["status"] == "ready_for_operator_review"); require(not assessment["errors"])
    require(summary["component_count"] == 12); require(summary["candidate_count"] == 4)
    require(summary["area_count"] == 12); require(summary["owner_count"] == 12)
    require(summary["feature_freeze_active"] is True); require(summary["architecture_ownership_explicit"] is True)
    require(summary["startup_total_ms"] <= summary["startup_budget_ms"])
    for field in ("files_moved", "modules_merged", "files_deleted", "imports_rewritten", "startup_executed", "runtime_mutated", "source_modified", "new_feature_authorized", "exception_approved", "approval_created", "approval_consumed", "provider_contacted", "model_contacted", "process_started", "thread_started", "installation_performed", "promotion_performed", "certification_performed", "publication_performed", "release_performed", "automatic_continuation", "global_profile_pass_claimed"):
        require(summary[field] is False)
    require(summary["authority_state"] == "separate_not_granted")

    blocked: dict[str, list[str]] = {}
    mutations = {
        "duplicate-component": ("component", 1, "component_id", rows[0]["component_id"]),
        "duplicate-sequence": ("component", 1, "sequence", rows[0]["sequence"]),
        "unsupported-area": ("component", 0, "area", "arbitrary"),
        "missing-owner": ("component", 0, "owner", ""),
        "bad-freeze-state": ("component", 0, "freeze_state", "unfrozen"),
        "bad-module-digest": ("component", 0, "module_digest", "bad"),
        "private-field": ("component", 0, "secret", "redacted"),
        "file-move": ("component", 0, "file_moved", True),
        "module-merge": ("component", 0, "module_merged", True),
        "source-modification": ("component", 0, "source_modified", True),
        "authority": ("component", 0, "authority_state", "granted"),
        "unknown-canonical": ("candidate", 0, "canonical_component_id", "missing"),
        "unknown-related": ("candidate", 0, "related_component_ids", ["missing"]),
        "unsupported-kind": ("candidate", 0, "kind", "delete_everything"),
        "unsupported-disposition": ("candidate", 0, "disposition", "apply"),
        "candidate-file-delete": ("candidate", 0, "files_deleted", True),
    }
    import copy
    from feature_freeze_architecture_consolidation import _digest
    for name, (target, index, field, value) in mutations.items():
        r = copy.deepcopy(rows); c = copy.deepcopy(candidates)
        item = r[index] if target == "component" else c[index]; item[field] = value
        digest_field = "component_digest" if target == "component" else "candidate_digest"
        item[digest_field] = _digest({k: v for k, v in item.items() if k != digest_field})
        result = assess_feature_freeze_architecture(plan, r, c, current_snapshot_digest=snapshot, current_context_digest=context, verification_summary=verification)
        require(result["status"] == "blocked"); require(bool(result["errors"])); blocked[name] = result["errors"]

    plan_mutations = {"new-feature": ("new_feature_authorized", True), "exception-approved": ("exception_approved", True), "files-moved": ("files_moved", True), "imports-rewritten": ("imports_rewritten", True), "startup-executed": ("startup_executed", True), "approval-created": ("approval_created", True), "provider-contact": ("provider_contacted", True), "process-start": ("process_started", True), "release": ("release_performed", True), "automatic-continuation": ("automatic_continuation", True), "plan-authority": ("authority_state", "granted")}
    for name, (field, value) in plan_mutations.items():
        p = dict(plan); p[field] = value; p["plan_digest"] = _digest({k: v for k, v in p.items() if k != "plan_digest"})
        result = assess_feature_freeze_architecture(p, rows, candidates, current_snapshot_digest=snapshot, current_context_digest=context, verification_summary=verification)
        require(result["status"] == "blocked"); require(bool(result["errors"])); blocked[name] = result["errors"]

    privacy = package_privacy_summary_for_root(source); require(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "feature-freeze-architecture-consolidation-checkpoint"), None)
    require(bool(descriptor)); require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_feature_freeze_architecture_consolidation_checkpoint")
    require((descriptor or {}).get("read_only") is True); require((descriptor or {}).get("post_available") is False)
    return {
        "ok": all(checks), "checkpoint_id": "feature-freeze-architecture-consolidation:v1198.2",
        "contract_version": CONTRACT_VERSION, "passed": sum(checks), "total": len(checks),
        "read_only": True, "post_available": False, "content_free": True, "source_unchanged": True,
        "runtime_mutated": False, "production_source_modified": False, "files_moved": False,
        "modules_merged": False, "files_deleted": False, "imports_rewritten": False,
        "startup_executed": False, "new_feature_authorized": False, "exception_approved": False,
        "approval_created": False, "approval_consumed": False, "provider_contacted": False,
        "model_contacted": False, "process_started": False, "thread_started": False,
        "installation_performed": False, "promotion_performed": False, "certification_performed": False,
        "publication_performed": False, "release_performed": False, "automatic_continuation": False,
        "global_profile_pass_claimed": False, "authority_granted": False, "summary": summary,
        "blocked_cases": blocked, "privacy": privacy,
        "limitations": [
            "Feature freeze and architecture evidence is source-declared and content-free; no source files are moved, merged, deleted, or rewritten.",
            "Ownership and consolidation candidates are review evidence only; no exception approval or consolidation application occurs.",
            "Startup costs are bounded declared observations; this bundle does not execute startup profiling.",
            "Performance hardening, documentation completion, and historical verifier reconciliation continue in later v1198 bundles.",
            "No installation, promotion, certification, publication, release, or autonomous authority is granted.",
        ],
    }
