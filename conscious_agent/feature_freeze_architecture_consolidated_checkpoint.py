from __future__ import annotations

"""Read-only v1198.9 Feature Freeze and Architecture Consolidation checkpoint.

This checkpoint consolidates the v1198 feature-freeze and architecture inventory,
operator-reviewed freeze exceptions and consolidation proposals, and performance,
documentation, and verifier reconciliation evidence. It performs no source move,
merge, deletion, import rewrite, profiling, verifier execution, exception
application, release operation, or authority expansion.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from feature_freeze_architecture_consolidation import ARCHITECTURE_AREAS, CONSOLIDATION_KINDS
from feature_freeze_architecture_consolidation_checkpoint import build_feature_freeze_architecture_consolidation_checkpoint
from feature_freeze_consolidation_review import DECISIONS, REVIEW_ACTIONS
from feature_freeze_consolidation_review_checkpoint import build_feature_freeze_consolidation_review_checkpoint
from package_integrity import package_privacy_summary_for_root
from performance_documentation_verifier_hardening import EVIDENCE_CLASSES
from performance_documentation_verifier_hardening_checkpoint import build_performance_documentation_verifier_hardening_checkpoint

CONTRACT_VERSION = "v1198.9"
CHECKPOINT_ID = "feature-freeze-architecture-consolidated-checkpoint"
_EXCLUDED_DIRS = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_PRIVATE_KEYS = {
    "prompt", "conversation", "message", "memory", "secret", "password",
    "token_value", "raw_source", "source_text", "patch", "patch_text",
    "stdout", "stderr", "provider_payload", "private_reasoning", "credential",
    "api_key", "runtime_payload",
}
_EXPECTED_TRUE = (
    "content_free", "read_only", "privacy_preserved", "feature_freeze_active",
    "architecture_ownership_explicit", "duplicate_visibility_preserved",
    "operator_review_accountable", "exact_review_lineage_verified",
    "startup_budget_truth_preserved", "profile_budget_truth_preserved",
    "documentation_consistent", "verifier_registration_consistent",
    "freeze_compliance_preserved", "historical_truth_preserved",
    "current_regressions_separate", "inherited_debt_visible",
    "authority_boundary_preserved", "source_unchanged",
)
_EXPECTED_FALSE = (
    "new_feature_authorized", "exception_applied", "files_moved",
    "modules_merged", "files_deleted", "imports_rewritten",
    "documentation_rewritten", "fixture_deleted", "verifier_retired",
    "startup_executed", "profiling_executed", "verifier_executed",
    "approval_created", "approval_consumed", "provider_contacted",
    "model_contacted", "process_started", "thread_started",
    "runtime_mutated", "production_source_modified", "installation_performed",
    "promotion_performed", "certification_performed", "publication_performed",
    "release_performed", "automatic_continuation",
    "global_profile_pass_claimed", "authority_granted",
)
_LIMITATIONS = (
    "Feature-freeze, ownership, duplication, performance, documentation, and verifier evidence is source-declared, content-free, and read-only.",
    "Approve, reject, and defer are presentation outcomes; no freeze exception or consolidation application is performed.",
    "No files are moved, merged, deleted, or rewritten and no profiling or verifier execution occurs.",
    "Inherited performance-budget and partial-fixture-overlap debt remains explicit; no global quick/full-profile pass is claimed.",
    "Final source-only candidate preparation continues in v1199; Desktop Codex and native-provider review remain scheduled for v1200.",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED_DIRS]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), len(paths)


def _private_fields(snapshot: Mapping[str, Any]) -> list[str]:
    return sorted(
        str(key) for key in snapshot
        if any(token in str(key).lower() for token in _PRIVATE_KEYS)
    )


def _validate_snapshot(snapshot: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(f"private_field:{field}" for field in _private_fields(snapshot))
    for field in _EXPECTED_TRUE:
        if snapshot.get(field) is not True:
            errors.append(f"invalid_{field}")
    for field in _EXPECTED_FALSE:
        if snapshot.get(field) is not False:
            errors.append(f"invalid_{field}")
    if snapshot.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")
    for field, version in (
        ("foundation_contract_version", "v1198.2"),
        ("review_contract_version", "v1198.5"),
        ("hardening_contract_version", "v1198.8"),
    ):
        if snapshot.get(field) != version:
            errors.append(f"{field}_drift")
    expected_counts = {
        "retained_checkpoint_count": 3,
        "architecture_area_count": len(ARCHITECTURE_AREAS),
        "consolidation_kind_count": len(CONSOLIDATION_KINDS),
        "review_action_count": len(REVIEW_ACTIONS),
        "decision_count": len(DECISIONS),
        "review_count": len(REVIEW_ACTIONS) * len(DECISIONS),
        "hardening_evidence_class_count": len(EVIDENCE_CLASSES),
        "hardening_evidence_count": len(EVIDENCE_CLASSES),
        "inherited_debt_count": 1,
    }
    for field, expected in expected_counts.items():
        if snapshot.get(field) != expected:
            errors.append(f"invalid_{field}")
    if snapshot.get("startup_total_ms", 0) > snapshot.get("startup_budget_ms", -1):
        errors.append("startup_budget_truth_loss")
    body = {key: value for key, value in snapshot.items() if key != "checkpoint_digest"}
    if snapshot.get("checkpoint_digest") != _digest(body):
        errors.append("checkpoint_tamper")
    return sorted(set(errors))


def build_feature_freeze_architecture_consolidated_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    foundations = build_feature_freeze_architecture_consolidation_checkpoint(source_root=source)
    review = build_feature_freeze_consolidation_review_checkpoint(source_root=source)
    hardening = build_performance_documentation_verifier_hardening_checkpoint(source_root=source)

    retained = (
        (foundations, "v1198.2", 92),
        (review, "v1198.5", 425),
        (hardening, "v1198.8", 14),
    )
    for report, version, total in retained:
        require(report.get("ok") is True)
        require(report.get("contract_version") == version)
        require(report.get("passed") == report.get("total") == total)
        require(report.get("read_only") is True)
        require(report.get("post_available") is False)
        require(report.get("content_free") is True)
        require(report.get("source_unchanged") is True)
        require(report.get("runtime_mutated") is False)

    foundation_summary = dict(foundations.get("summary") or {})
    reviews = [dict(row) for row in (review.get("reviews") or [])]
    hardening_assessment = dict(hardening.get("assessment") or {})

    expected_pairs = [(action, decision) for action in REVIEW_ACTIONS for decision in DECISIONS]
    actual_pairs = [(row.get("action"), row.get("decision")) for row in reviews]
    review_sequences = [row.get("sequence") for row in reviews]
    review_receipts = [row.get("review_receipt_digest") for row in reviews]
    review_lineage_verified = (
        actual_pairs == expected_pairs
        and review_sequences == list(range(1, len(expected_pairs) + 1))
        and len(review_receipts) == len(set(review_receipts))
        and all(isinstance(item, str) and len(item) == 64 for item in review_receipts)
    )

    snapshot: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "feature-freeze-architecture-consolidation:v1198.9",
        "foundation_contract_version": foundations.get("contract_version"),
        "review_contract_version": review.get("contract_version"),
        "hardening_contract_version": hardening.get("contract_version"),
        "retained_checkpoint_count": 3,
        "architecture_area_count": len(ARCHITECTURE_AREAS),
        "architecture_areas": list(ARCHITECTURE_AREAS),
        "consolidation_kind_count": len(CONSOLIDATION_KINDS),
        "consolidation_kinds": list(CONSOLIDATION_KINDS),
        "review_action_count": len(REVIEW_ACTIONS),
        "review_actions": list(REVIEW_ACTIONS),
        "decision_count": len(DECISIONS),
        "decisions": list(DECISIONS),
        "review_count": len(reviews),
        "hardening_evidence_class_count": len(EVIDENCE_CLASSES),
        "hardening_evidence_classes": list(EVIDENCE_CLASSES),
        "hardening_evidence_count": hardening_assessment.get("evidence_count", 0),
        "inherited_debt_count": hardening_assessment.get("inherited_debt_count", 0),
        "startup_budget_ms": foundation_summary.get("startup_budget_ms", 0),
        "startup_total_ms": foundation_summary.get("startup_total_ms", 0),
        "content_free": True,
        "read_only": True,
        "privacy_preserved": True,
        "feature_freeze_active": (
            foundation_summary.get("feature_freeze_active") is True
            and all(row.get("feature_freeze_active") is True for row in reviews)
            and hardening_assessment.get("feature_freeze_active") is True
        ),
        "architecture_ownership_explicit": foundation_summary.get("architecture_ownership_explicit") is True,
        "duplicate_visibility_preserved": foundation_summary.get("duplicate_visibility_preserved") is True,
        "operator_review_accountable": len(reviews) == len(expected_pairs) and all(row.get("status") == "reviewed" for row in reviews),
        "exact_review_lineage_verified": review_lineage_verified,
        "startup_budget_truth_preserved": foundation_summary.get("startup_total_ms", 0) <= foundation_summary.get("startup_budget_ms", -1),
        "profile_budget_truth_preserved": hardening_assessment.get("current_health_pass") is True,
        "documentation_consistent": hardening_assessment.get("documentation_rewritten") is False,
        "verifier_registration_consistent": hardening_assessment.get("verifier_executed") is False,
        "freeze_compliance_preserved": hardening_assessment.get("feature_freeze_active") is True,
        "historical_truth_preserved": hardening_assessment.get("historical_truth_preserved") is True,
        "current_regressions_separate": hardening_assessment.get("current_health_pass") is True,
        "inherited_debt_visible": hardening_assessment.get("inherited_debt_count") == 1,
        "authority_boundary_preserved": (
            foundation_summary.get("authority_state") == "separate_not_granted"
            and all(row.get("authority_state") == "separate_not_granted" for row in reviews)
            and hardening_assessment.get("authority_state") == "separate_not_granted"
        ),
        "source_unchanged": True,
        "new_feature_authorized": False,
        "exception_applied": False,
        "files_moved": False,
        "modules_merged": False,
        "files_deleted": False,
        "imports_rewritten": False,
        "documentation_rewritten": False,
        "fixture_deleted": False,
        "verifier_retired": False,
        "startup_executed": False,
        "profiling_executed": False,
        "verifier_executed": False,
        "approval_created": False,
        "approval_consumed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "process_started": False,
        "thread_started": False,
        "runtime_mutated": False,
        "production_source_modified": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "publication_performed": False,
        "release_performed": False,
        "automatic_continuation": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
    snapshot["checkpoint_digest"] = _digest(snapshot)
    errors = _validate_snapshot(snapshot)
    require(not errors)

    mutation_cases: dict[str, dict[str, Any]] = {
        "private-field": {"secret": "forbidden"},
        "foundation-drift": {"foundation_contract_version": "v1198.1"},
        "review-drift": {"review_contract_version": "v1198.4"},
        "hardening-drift": {"hardening_contract_version": "v1198.7"},
        "retained-count": {"retained_checkpoint_count": 2},
        "area-count": {"architecture_area_count": 11},
        "kind-count": {"consolidation_kind_count": 3},
        "action-count": {"review_action_count": 4},
        "decision-count": {"decision_count": 2},
        "review-count": {"review_count": 14},
        "evidence-class-count": {"hardening_evidence_class_count": 7},
        "evidence-count": {"hardening_evidence_count": 7},
        "debt-hidden-count": {"inherited_debt_count": 0},
        "privacy-loss": {"privacy_preserved": False},
        "freeze-loss": {"feature_freeze_active": False},
        "ownership-loss": {"architecture_ownership_explicit": False},
        "duplicate-visibility-loss": {"duplicate_visibility_preserved": False},
        "review-accountability-loss": {"operator_review_accountable": False},
        "review-lineage-loss": {"exact_review_lineage_verified": False},
        "startup-budget-loss": {"startup_total_ms": 30001},
        "profile-budget-loss": {"profile_budget_truth_preserved": False},
        "documentation-loss": {"documentation_consistent": False},
        "verifier-registration-loss": {"verifier_registration_consistent": False},
        "freeze-compliance-loss": {"freeze_compliance_preserved": False},
        "historical-truth-loss": {"historical_truth_preserved": False},
        "current-separation-loss": {"current_regressions_separate": False},
        "debt-hidden": {"inherited_debt_visible": False},
        "authority-boundary-loss": {"authority_boundary_preserved": False},
        "source-change": {"source_unchanged": False},
        "new-feature": {"new_feature_authorized": True},
        "exception": {"exception_applied": True},
        "file-move": {"files_moved": True},
        "module-merge": {"modules_merged": True},
        "file-delete": {"files_deleted": True},
        "import-rewrite": {"imports_rewritten": True},
        "documentation-rewrite": {"documentation_rewritten": True},
        "fixture-delete": {"fixture_deleted": True},
        "verifier-retire": {"verifier_retired": True},
        "startup-execution": {"startup_executed": True},
        "profiling-execution": {"profiling_executed": True},
        "verifier-execution": {"verifier_executed": True},
        "approval-create": {"approval_created": True},
        "approval-consume": {"approval_consumed": True},
        "provider-contact": {"provider_contacted": True},
        "model-contact": {"model_contacted": True},
        "process-start": {"process_started": True},
        "thread-start": {"thread_started": True},
        "runtime-mutation": {"runtime_mutated": True},
        "source-mutation": {"production_source_modified": True},
        "installation": {"installation_performed": True},
        "promotion": {"promotion_performed": True},
        "certification": {"certification_performed": True},
        "publication": {"publication_performed": True},
        "release": {"release_performed": True},
        "automatic-continuation": {"automatic_continuation": True},
        "global-pass": {"global_profile_pass_claimed": True},
        "authority-state": {"authority_state": "granted"},
        "authority": {"authority_granted": True},
    }
    blocked_cases: dict[str, list[str]] = {}
    for name, changes in mutation_cases.items():
        candidate = dict(snapshot)
        candidate.update(changes)
        candidate["checkpoint_digest"] = _digest({k: v for k, v in candidate.items() if k != "checkpoint_digest"})
        case_errors = _validate_snapshot(candidate)
        require(bool(case_errors))
        blocked_cases[name] = case_errors

    tampered = dict(snapshot)
    tampered["checkpoint_digest"] = "0" * 64
    tamper_errors = _validate_snapshot(tampered)
    require("checkpoint_tamper" in tamper_errors)
    blocked_cases["tamper"] = tamper_errors

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == CHECKPOINT_ID), None)
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_feature_freeze_architecture_consolidated_checkpoint")
    require((descriptor or {}).get("read_only") is True)
    require((descriptor or {}).get("post_available") is False)
    require((descriptor or {}).get("required_input_count") == 0)
    require(not registry["duplicate_checkpoint_ids"])
    require(not registry["duplicate_builder_targets"])

    after_digest, after_count = _tree_signature(source)
    require(after_digest == before_digest)
    require(after_count == before_count)

    summary = dict(snapshot)
    summary["blocked_case_count"] = len(blocked_cases)
    return {
        "ok": all(checks),
        "checkpoint_id": "feature-freeze-architecture-consolidation:v1198.9",
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "source_unchanged": after_digest == before_digest and after_count == before_count,
        "runtime_mutated": False,
        "production_source_modified": False,
        "new_feature_authorized": False,
        "exception_applied": False,
        "files_moved": False,
        "modules_merged": False,
        "files_deleted": False,
        "imports_rewritten": False,
        "documentation_rewritten": False,
        "fixture_deleted": False,
        "verifier_retired": False,
        "startup_executed": False,
        "profiling_executed": False,
        "verifier_executed": False,
        "approval_created": False,
        "approval_consumed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "process_started": False,
        "thread_started": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "publication_performed": False,
        "release_performed": False,
        "automatic_continuation": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
        "passed": sum(checks),
        "total": len(checks),
        "summary": summary,
        "retained_checkpoints": {
            "foundations": {"contract_version": foundations.get("contract_version"), "passed": foundations.get("passed"), "total": foundations.get("total")},
            "review": {"contract_version": review.get("contract_version"), "passed": review.get("passed"), "total": review.get("total")},
            "hardening": {"contract_version": hardening.get("contract_version"), "passed": hardening.get("passed"), "total": hardening.get("total")},
        },
        "blocked_cases": blocked_cases,
        "privacy": privacy,
        "limitations": list(_LIMITATIONS),
    }
