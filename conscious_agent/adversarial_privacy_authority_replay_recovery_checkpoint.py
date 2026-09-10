from __future__ import annotations

"""Read-only v1196.9 adversarial privacy, authority, replay, and recovery checkpoint.

This checkpoint consolidates the v1196 privacy/authority foundations,
operator-reviewed replay and recovery evidence, and cross-surface adversarial
reliability evidence. It reads source-declared, content-free checkpoint output
only and performs no attack, recovery, retry, cancellation, execution,
provider/model contact, process/thread start, approval mutation, runtime/source
mutation, installation, promotion, certification, publication, release, or
authority expansion.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from adversarial_privacy_authority import ATTACK_CLASSES, AUTHORITY_DOMAINS
from adversarial_privacy_authority_checkpoint import build_adversarial_privacy_authority_checkpoint
from adversarial_replay_recovery_review import ACTIONS, DECISIONS, EVENT_CLASSES as REVIEW_EVENT_CLASSES
from adversarial_replay_recovery_review_checkpoint import build_adversarial_replay_recovery_review_checkpoint
from adversarial_reliability_integration import EVENT_CLASSES as RELIABILITY_EVENT_CLASSES, SURFACES
from adversarial_reliability_integration_checkpoint import build_adversarial_reliability_integration_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1196.9"
_CHECKPOINT_ID = "adversarial-privacy-authority-replay-recovery-checkpoint"
_EXCLUDED_DIRS = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_PRIVATE_KEYS = {
    "prompt", "conversation", "message", "memory", "secret", "raw_source",
    "source_text", "patch", "patch_text", "stdout", "stderr",
    "provider_payload", "private_reasoning", "credential", "token_value",
}
_LIMITATIONS = (
    "Adversarial evidence is source-declared and content-free; no attack is executed and no private subsystem state is fetched.",
    "Replay, stale-state, interruption, cancellation, and recovery outcomes remain review-only and non-mutating.",
    "No approval, execution, cancellation, installation, promotion, certification, publication, release, or autonomous authority is created or consumed.",
    "Inherited global-profile performance and partial-fixture-overlap debt remains explicit and unresolved.",
    "Runtime migration, upgrade, backup, rollback, and fresh-install testing continues in v1197; Desktop Codex and native-provider review remain scheduled for v1200.",
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
        "content_free", "read_only", "privacy_preserved",
        "authority_boundary_preserved", "original_evidence_preserved",
        "exact_lineage_verified", "operator_review_accountable",
        "foreground_available", "historical_truth_preserved",
        "current_regressions_separate", "inherited_debt_visible",
    )
    expected_false = (
        "attacks_executed", "private_state_fetched", "privacy_attack_succeeded",
        "automatic_recovery", "automatic_retry", "recovery_executed",
        "retry_executed", "cancellation_executed", "execution_invoked",
        "approval_created", "approval_consumed", "runtime_mutated",
        "production_source_modified", "provider_contacted", "model_contacted",
        "thread_started", "process_started", "installation_performed",
        "promotion_performed", "certification_performed", "publication_performed",
        "release_performed", "automatic_continuation",
        "global_profile_pass_claimed", "authority_granted",
    )
    for field in expected_true:
        if snapshot.get(field) is not True:
            errors.append(f"invalid_{field}")
    for field in expected_false:
        if snapshot.get(field) is not False:
            errors.append(f"invalid_{field}")

    if snapshot.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")
    if snapshot.get("foundation_contract_version") != "v1196.2":
        errors.append("foundation_contract_drift")
    if snapshot.get("review_contract_version") != "v1196.5":
        errors.append("review_contract_drift")
    if snapshot.get("reliability_contract_version") != "v1196.8":
        errors.append("reliability_contract_drift")

    expected_counts = {
        "retained_checkpoint_count": 3,
        "attack_class_count": 14,
        "authority_domain_count": 16,
        "review_event_class_count": 5,
        "review_action_count": 4,
        "decision_count": 3,
        "reliability_event_class_count": 8,
        "surface_count": 12,
    }
    for field, expected in expected_counts.items():
        if snapshot.get(field) != expected:
            errors.append(f"invalid_{field}")

    body = {key: value for key, value in snapshot.items() if key != "checkpoint_digest"}
    if snapshot.get("checkpoint_digest") != _digest(body):
        errors.append("checkpoint_tamper")
    return sorted(set(errors))


def build_adversarial_privacy_authority_replay_recovery_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    foundations = build_adversarial_privacy_authority_checkpoint(source_root=source)
    review = build_adversarial_replay_recovery_review_checkpoint(source_root=source)
    reliability = build_adversarial_reliability_integration_checkpoint(source_root=source)

    retained = (
        (foundations, "v1196.2", 72, 3),
        (review, "v1196.5", 114, 3),
        (reliability, "v1196.8", 167, 3),
    )
    for report, version, total, limitation_count in retained:
        require(report.get("ok") is True)
        require(report.get("contract_version") == version)
        require(report.get("passed") == report.get("total") == total)
        require(bool(report.get("summary")))
        require(bool(report.get("blocked_cases")))
        require(len(report.get("limitations") or []) == limitation_count)
        for blocked in (report.get("blocked_cases") or {}).values():
            require(bool(blocked))

    foundation_summary = dict(foundations.get("summary") or {})
    review_summary = dict(review.get("summary") or {})
    reliability_summary = dict(reliability.get("summary") or {})

    snapshot: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "adversarial-privacy-authority-replay-recovery:v1196.9",
        "foundation_contract_version": foundations.get("contract_version"),
        "review_contract_version": review.get("contract_version"),
        "reliability_contract_version": reliability.get("contract_version"),
        "retained_checkpoint_count": 3,
        "attack_class_count": len(ATTACK_CLASSES),
        "authority_domain_count": len(AUTHORITY_DOMAINS),
        "review_event_class_count": len(REVIEW_EVENT_CLASSES),
        "review_action_count": len(ACTIONS),
        "decision_count": len(DECISIONS),
        "reliability_event_class_count": len(RELIABILITY_EVENT_CLASSES),
        "surface_count": len(SURFACES),
        "blocked_attack_count": foundation_summary.get("blocked_attack_count", 0),
        "review_count": review_summary.get("review_count", 0),
        "reliability_sample_count": reliability_summary.get("sample_count", 0),
        "content_free": True,
        "read_only": True,
        "privacy_preserved": foundation_summary.get("privacy_preserved") is True,
        "authority_boundary_preserved": all(
            summary.get("authority_state") == "separate_not_granted"
            for summary in (foundation_summary, review_summary, reliability_summary)
        ),
        "original_evidence_preserved": all(
            summary.get("original_evidence_preserved") is True
            for summary in (review_summary, reliability_summary)
        ),
        "exact_lineage_verified": all(
            bool(sample.get("exact_lineage_verified", True))
            for report in (review, reliability)
            for sample in (report.get("samples") or [])
        ),
        "operator_review_accountable": review_summary.get("review_count") == len(REVIEW_EVENT_CLASSES) * len(DECISIONS),
        "foreground_available": reliability_summary.get("foreground_available") is True,
        "historical_truth_preserved": True,
        "current_regressions_separate": True,
        "inherited_debt_visible": True,
        "attacks_executed": False,
        "private_state_fetched": False,
        "privacy_attack_succeeded": False,
        "automatic_recovery": False,
        "automatic_retry": False,
        "recovery_executed": False,
        "retry_executed": False,
        "cancellation_executed": False,
        "execution_invoked": False,
        "approval_created": False,
        "approval_consumed": False,
        "runtime_mutated": False,
        "production_source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
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
        "private-field": {"secret": "redacted"},
        "foundation-contract-drift": {"foundation_contract_version": "v1196.1"},
        "review-contract-drift": {"review_contract_version": "v1196.4"},
        "reliability-contract-drift": {"reliability_contract_version": "v1196.7"},
        "retained-count": {"retained_checkpoint_count": 2},
        "attack-count": {"attack_class_count": 13},
        "authority-domain-count": {"authority_domain_count": 15},
        "review-event-count": {"review_event_class_count": 4},
        "action-count": {"review_action_count": 3},
        "decision-count": {"decision_count": 2},
        "reliability-event-count": {"reliability_event_class_count": 7},
        "surface-count": {"surface_count": 11},
        "privacy-loss": {"privacy_preserved": False},
        "authority-boundary-loss": {"authority_boundary_preserved": False},
        "evidence-loss": {"original_evidence_preserved": False},
        "lineage-loss": {"exact_lineage_verified": False},
        "review-accountability-loss": {"operator_review_accountable": False},
        "foreground-block": {"foreground_available": False},
        "historical-truth-loss": {"historical_truth_preserved": False},
        "verification-boundary-loss": {"current_regressions_separate": False},
        "debt-hidden": {"inherited_debt_visible": False},
        "attack-execution": {"attacks_executed": True},
        "private-fetch": {"private_state_fetched": True},
        "privacy-attack-success": {"privacy_attack_succeeded": True},
        "automatic-recovery": {"automatic_recovery": True},
        "automatic-retry": {"automatic_retry": True},
        "recovery-execution": {"recovery_executed": True},
        "retry-execution": {"retry_executed": True},
        "cancellation-execution": {"cancellation_executed": True},
        "hidden-execution": {"execution_invoked": True},
        "approval-create": {"approval_created": True},
        "approval-consume": {"approval_consumed": True},
        "runtime-mutation": {"runtime_mutated": True},
        "source-mutation": {"production_source_modified": True},
        "provider-contact": {"provider_contacted": True},
        "model-contact": {"model_contacted": True},
        "thread-start": {"thread_started": True},
        "process-start": {"process_started": True},
        "installation": {"installation_performed": True},
        "promotion": {"promotion_performed": True},
        "certification": {"certification_performed": True},
        "publication": {"publication_performed": True},
        "release": {"release_performed": True},
        "automatic-continuation": {"automatic_continuation": True},
        "global-pass-claim": {"global_profile_pass_claimed": True},
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
    descriptor = next(
        (row for row in registry["checkpoints"] if row["checkpoint_id"] == _CHECKPOINT_ID),
        None,
    )
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_adversarial_privacy_authority_replay_recovery_checkpoint")
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
        "checkpoint_id": "adversarial-privacy-authority-replay-recovery:v1196.9",
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "source_unchanged": after_digest == before_digest and after_count == before_count,
        "runtime_mutated": False,
        "production_source_modified": False,
        "attacks_executed": False,
        "private_state_fetched": False,
        "automatic_recovery": False,
        "automatic_retry": False,
        "recovery_executed": False,
        "retry_executed": False,
        "cancellation_executed": False,
        "execution_invoked": False,
        "approval_created": False,
        "approval_consumed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
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
            "foundations": {
                "contract_version": foundations.get("contract_version"),
                "passed": foundations.get("passed"), "total": foundations.get("total"),
            },
            "review": {
                "contract_version": review.get("contract_version"),
                "passed": review.get("passed"), "total": review.get("total"),
            },
            "reliability": {
                "contract_version": reliability.get("contract_version"),
                "passed": reliability.get("passed"), "total": reliability.get("total"),
            },
        },
        "blocked_cases": blocked_cases,
        "limitations": list(_LIMITATIONS),
    }
