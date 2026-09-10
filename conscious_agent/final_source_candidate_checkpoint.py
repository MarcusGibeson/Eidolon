from __future__ import annotations

"""Read-only v1199.9 Final Source-Only Candidate checkpoint.

This checkpoint consolidates v1199.2 preparation, v1199.5 operator review,
and v1199.8 reliability evidence into one source-discovered, content-free
handoff surface for the separate v1200 Desktop Codex and native-provider
decision gate. It performs no candidate acceptance, risk waiver, verification
execution, installation, promotion, certification, publication, release,
provider/model contact, source/runtime mutation, or authority expansion.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from final_candidate_reliability import EVENT_CLASSES
from final_candidate_reliability_checkpoint import build_final_candidate_reliability_checkpoint
from final_candidate_review import DECISIONS, REVIEW_ACTIONS
from final_candidate_review_checkpoint import build_final_candidate_review_checkpoint
from final_source_candidate_preparation import PREPARATION_AREAS
from final_source_candidate_preparation_checkpoint import build_final_source_candidate_preparation_checkpoint
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1199.9"
CHECKPOINT_ID = "final-source-candidate-checkpoint"
_EXCLUDED_DIRS = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_PRIVATE_KEYS = {
    "prompt", "conversation", "message", "memory", "secret", "raw_source",
    "source_text", "patch", "patch_text", "stdout", "stderr",
    "provider_payload", "private_reasoning", "credential", "token_value",
    "runtime_payload", "candidate_payload", "handoff_payload",
}
_LIMITATIONS = (
    "The checkpoint is source-declared, content-free, and read-only; it does not execute retained verifiers or inspect private runtime state.",
    "Candidate and handoff review remain presentation-only; no candidate or handoff is accepted and no risk is waived.",
    "Inherited quick/full performance-budget and partial-fixture-overlap debt remains explicit and unresolved.",
    "Installation, promotion, certification, publication, release, and independent authority remain prohibited.",
    "Desktop Codex and native-provider review plus an explicit operator decision remain mandatory at the separate v1200 decision gate.",
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

    expected_true = (
        "content_free", "read_only", "source_only", "privacy_preserved",
        "authority_boundary_preserved", "original_candidate_preserved",
        "retained_verification_preserved", "unresolved_risks_preserved",
        "desktop_handoff_preserved", "native_provider_handoff_preserved",
        "operator_review_accountable", "exact_review_lineage_verified",
        "exact_reliability_lineage_verified", "foreground_available",
        "historical_truth_preserved", "current_regressions_separate",
        "inherited_debt_visible", "v1200_gate_required", "source_unchanged",
    )
    expected_false = (
        "candidate_prepared", "candidate_accepted", "handoff_accepted",
        "risk_waived", "release_approved", "global_profile_pass_claimed",
        "verifier_executed", "candidate_modified", "source_modified",
        "runtime_mutated", "approval_created", "approval_consumed",
        "provider_contacted", "model_contacted", "process_started",
        "thread_started", "automatic_continuation", "automatic_recovery",
        "installation_performed", "promotion_performed",
        "certification_performed", "publication_performed",
        "release_performed", "authority_granted",
    )
    for field in expected_true:
        if snapshot.get(field) is not True:
            errors.append(f"invalid_{field}")
    for field in expected_false:
        if snapshot.get(field) is not False:
            errors.append(f"invalid_{field}")

    if snapshot.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")
    if snapshot.get("preparation_contract_version") != "v1199.2":
        errors.append("preparation_contract_drift")
    if snapshot.get("review_contract_version") != "v1199.5":
        errors.append("review_contract_drift")
    if snapshot.get("reliability_contract_version") != "v1199.8":
        errors.append("reliability_contract_drift")

    expected_counts = {
        "retained_checkpoint_count": 3,
        "preparation_area_count": 8,
        "manifest_count": 8,
        "verification_count": 6,
        "risk_count": 2,
        "blocking_risk_count": 2,
        "review_action_count": 5,
        "decision_count": 3,
        "review_count": 15,
        "reliability_event_class_count": 8,
        "reliability_event_count": 8,
    }
    for field, expected in expected_counts.items():
        if snapshot.get(field) != expected:
            errors.append(f"invalid_{field}")

    body = {key: value for key, value in snapshot.items() if key != "checkpoint_digest"}
    if snapshot.get("checkpoint_digest") != _digest(body):
        errors.append("checkpoint_tamper")
    return sorted(set(errors))


def build_final_source_candidate_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    preparation = build_final_source_candidate_preparation_checkpoint(source_root=source)
    review = build_final_candidate_review_checkpoint(source_root=source)
    reliability = build_final_candidate_reliability_checkpoint(source_root=source)

    retained = (
        ("preparation", preparation, "v1199.2", 30, 4),
        ("review", review, "v1199.5", 160, 4),
        ("reliability", reliability, "v1199.8", 167, 4),
    )
    for _name, report, version, total, limitation_count in retained:
        require(report.get("ok") is True)
        require(report.get("contract_version") == version)
        require(report.get("passed") == report.get("total") == total)
        require(bool(report.get("summary")))
        require(bool(report.get("blocked_cases")))
        require(len(report.get("limitations") or []) == limitation_count)
        for blocked in (report.get("blocked_cases") or {}).values():
            require(bool(blocked))

    prep_summary = dict(preparation.get("summary") or {})
    review_summary = dict(review.get("summary") or {})
    reliability_summary = dict(reliability.get("summary") or {})

    snapshot: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "final-source-candidate:v1199.9",
        "preparation_contract_version": preparation.get("contract_version"),
        "review_contract_version": review.get("contract_version"),
        "reliability_contract_version": reliability.get("contract_version"),
        "retained_checkpoint_count": 3,
        "preparation_area_count": len(PREPARATION_AREAS),
        "preparation_areas": list(PREPARATION_AREAS),
        "manifest_count": prep_summary.get("manifest_count"),
        "verification_count": prep_summary.get("verification_count"),
        "risk_count": prep_summary.get("risk_count"),
        "blocking_risk_count": prep_summary.get("blocking_risk_count"),
        "review_action_count": len(REVIEW_ACTIONS),
        "review_actions": list(REVIEW_ACTIONS),
        "decision_count": len(DECISIONS),
        "decisions": list(DECISIONS),
        "review_count": review_summary.get("review_count"),
        "reliability_event_class_count": len(EVENT_CLASSES),
        "reliability_event_classes": list(EVENT_CLASSES),
        "reliability_event_count": reliability_summary.get("event_count"),
        "content_free": True,
        "read_only": True,
        "source_only": True,
        "privacy_preserved": True,
        "authority_boundary_preserved": all(
            summary.get("authority_state") == "separate_not_granted"
            for summary in (prep_summary, review_summary, reliability_summary)
        ),
        "original_candidate_preserved": reliability_summary.get("original_candidate_preserved") is True,
        "retained_verification_preserved": reliability_summary.get("retained_verification_preserved") is True,
        "unresolved_risks_preserved": reliability_summary.get("unresolved_risks_preserved") is True,
        "desktop_handoff_preserved": reliability_summary.get("handoff_truth_preserved") is True,
        "native_provider_handoff_preserved": reliability_summary.get("handoff_truth_preserved") is True,
        "operator_review_accountable": (
            review_summary.get("review_count") == len(REVIEW_ACTIONS) * len(DECISIONS)
            and review_summary.get("presentation_only") is True
        ),
        "exact_review_lineage_verified": review.get("ok") is True,
        "exact_reliability_lineage_verified": reliability.get("ok") is True,
        "foreground_available": reliability_summary.get("foreground_available") is True,
        "historical_truth_preserved": True,
        "current_regressions_separate": True,
        "inherited_debt_visible": True,
        "v1200_gate_required": True,
        "source_unchanged": True,
        "candidate_prepared": False,
        "candidate_accepted": False,
        "handoff_accepted": False,
        "risk_waived": False,
        "release_approved": False,
        "global_profile_pass_claimed": False,
        "verifier_executed": False,
        "candidate_modified": False,
        "source_modified": False,
        "runtime_mutated": False,
        "approval_created": False,
        "approval_consumed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "process_started": False,
        "thread_started": False,
        "automatic_continuation": False,
        "automatic_recovery": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "publication_performed": False,
        "release_performed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
    snapshot["checkpoint_digest"] = _digest(snapshot)
    require(not _validate_snapshot(snapshot))

    mutation_cases: dict[str, dict[str, Any]] = {
        "private-field": {"candidate_payload": "forbidden"},
        "preparation-contract-drift": {"preparation_contract_version": "v1199.1"},
        "review-contract-drift": {"review_contract_version": "v1199.4"},
        "reliability-contract-drift": {"reliability_contract_version": "v1199.7"},
        "retained-count": {"retained_checkpoint_count": 2},
        "preparation-area-count": {"preparation_area_count": 7},
        "manifest-count": {"manifest_count": 7},
        "verification-count": {"verification_count": 5},
        "risk-count": {"risk_count": 1},
        "blocking-risk-count": {"blocking_risk_count": 1},
        "review-action-count": {"review_action_count": 4},
        "decision-count": {"decision_count": 2},
        "review-count": {"review_count": 14},
        "reliability-class-count": {"reliability_event_class_count": 7},
        "reliability-event-count": {"reliability_event_count": 7},
        "content-loss": {"content_free": False},
        "read-only-loss": {"read_only": False},
        "source-only-loss": {"source_only": False},
        "privacy-loss": {"privacy_preserved": False},
        "authority-boundary-loss": {"authority_boundary_preserved": False},
        "candidate-loss": {"original_candidate_preserved": False},
        "verification-loss": {"retained_verification_preserved": False},
        "risk-loss": {"unresolved_risks_preserved": False},
        "desktop-handoff-loss": {"desktop_handoff_preserved": False},
        "native-handoff-loss": {"native_provider_handoff_preserved": False},
        "review-accountability-loss": {"operator_review_accountable": False},
        "review-lineage-loss": {"exact_review_lineage_verified": False},
        "reliability-lineage-loss": {"exact_reliability_lineage_verified": False},
        "foreground-block": {"foreground_available": False},
        "historical-truth-loss": {"historical_truth_preserved": False},
        "current-regression-loss": {"current_regressions_separate": False},
        "debt-hidden": {"inherited_debt_visible": False},
        "gate-bypass": {"v1200_gate_required": False},
        "source-change": {"source_unchanged": False},
        "candidate-prepared": {"candidate_prepared": True},
        "candidate-accepted": {"candidate_accepted": True},
        "handoff-accepted": {"handoff_accepted": True},
        "risk-waived": {"risk_waived": True},
        "release-approved": {"release_approved": True},
        "global-pass": {"global_profile_pass_claimed": True},
        "verifier-execution": {"verifier_executed": True},
        "candidate-modified": {"candidate_modified": True},
        "source-modified": {"source_modified": True},
        "runtime-mutated": {"runtime_mutated": True},
        "approval-created": {"approval_created": True},
        "approval-consumed": {"approval_consumed": True},
        "provider-contact": {"provider_contacted": True},
        "model-contact": {"model_contacted": True},
        "process-start": {"process_started": True},
        "thread-start": {"thread_started": True},
        "automatic-continuation": {"automatic_continuation": True},
        "automatic-recovery": {"automatic_recovery": True},
        "installation": {"installation_performed": True},
        "promotion": {"promotion_performed": True},
        "certification": {"certification_performed": True},
        "publication": {"publication_performed": True},
        "release": {"release_performed": True},
        "authority-state": {"authority_state": "granted"},
        "authority": {"authority_granted": True},
    }
    blocked_cases: dict[str, list[str]] = {}
    for name, changes in mutation_cases.items():
        candidate = dict(snapshot)
        candidate.update(changes)
        candidate["checkpoint_digest"] = _digest({k: v for k, v in candidate.items() if k != "checkpoint_digest"})
        errors = _validate_snapshot(candidate)
        require(bool(errors))
        blocked_cases[name] = errors

    tampered = dict(snapshot)
    tampered["checkpoint_digest"] = "0" * 64
    tamper_errors = _validate_snapshot(tampered)
    require("checkpoint_tamper" in tamper_errors)
    blocked_cases["tamper"] = tamper_errors

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry["checkpoints"] if row["checkpoint_id"] == CHECKPOINT_ID),
        None,
    )
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_final_source_candidate_checkpoint")
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
        "checkpoint_id": "final-source-candidate:v1199.9",
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "source_only": True,
        "source_unchanged": after_digest == before_digest and after_count == before_count,
        "candidate_prepared": False,
        "candidate_accepted": False,
        "handoff_accepted": False,
        "risk_waived": False,
        "release_approved": False,
        "global_profile_pass_claimed": False,
        "verifier_executed": False,
        "candidate_modified": False,
        "source_modified": False,
        "runtime_mutated": False,
        "approval_created": False,
        "approval_consumed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "process_started": False,
        "thread_started": False,
        "automatic_continuation": False,
        "automatic_recovery": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "publication_performed": False,
        "release_performed": False,
        "authority_granted": False,
        "passed": sum(checks),
        "total": len(checks),
        "summary": summary,
        "retained_checkpoints": {
            name: {
                "contract_version": report.get("contract_version"),
                "passed": report.get("passed"),
                "total": report.get("total"),
            }
            for name, report, _version, _total, _limitations in retained
        },
        "blocked_cases": blocked_cases,
        "privacy": privacy,
        "limitations": list(_LIMITATIONS),
    }


CHECKPOINT_DESCRIPTOR = {
    "checkpoint_id": CHECKPOINT_ID,
    "contract_version": CONTRACT_VERSION,
    "module": "conscious_agent.final_source_candidate_checkpoint",
    "builder": "build_final_source_candidate_checkpoint",
    "required_inputs": [],
    "read_only": True,
    "post_available": False,
    "content_free": True,
}
