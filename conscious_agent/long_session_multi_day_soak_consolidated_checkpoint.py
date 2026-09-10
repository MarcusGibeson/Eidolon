from __future__ import annotations

"""Read-only v1195.9 Long-Session and Multi-Day Soak checkpoint.

This checkpoint consolidates the v1195 soak foundations, operator-reviewed
progression, and adversarial reliability surfaces. It consumes only
source-declared, content-free evidence and performs no waiting, continuation,
pause, resume, cancellation, recovery, execution, provider/model contact,
process/thread start, runtime mutation, or authority expansion.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from long_session_multi_day_soak import SOAK_DOMAINS, SOAK_MODES
from long_session_multi_day_soak_checkpoint import build_long_session_multi_day_soak_checkpoint
from operator_reviewed_soak_progression import ACTIONS, DECISIONS
from operator_reviewed_soak_progression_checkpoint import build_operator_reviewed_soak_progression_checkpoint
from package_integrity import package_privacy_summary_for_root
from soak_reliability_adversarial import EVENTS
from soak_reliability_adversarial_checkpoint import build_soak_reliability_adversarial_checkpoint

CONTRACT_VERSION = "v1195.9"
_CHECKPOINT_ID = "long-session-multi-day-soak-consolidated-checkpoint"
_EXCLUDED_DIRS = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_PRIVATE_KEYS = {
    "prompt", "conversation", "message", "memory", "secret", "raw_source",
    "source_text", "patch", "patch_text", "stdout", "stderr",
    "provider_payload", "private_reasoning",
}
_LIMITATIONS = (
    "Long-session and multi-day duration remains bounded caller-supplied evidence; the checkpoint does not wait or remain alive.",
    "Progression, pause, resume, cancellation, restart, and recovery remain presentation-only and non-mutating.",
    "No private conversation, cognition, campaign, queue, cancellation, interruption, restart, or recovery record is fetched.",
    "Inherited global-profile performance and partial-fixture-overlap debt remains explicit and unresolved.",
    "Adversarial privacy and authority hardening continues in v1196; Desktop Codex and native-provider review remain scheduled for v1200.",
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
        "content_free", "read_only", "foreground_path_available",
        "latency_within_budget", "resource_budgets_within_bounds",
        "progress_observed", "exact_lineage_verified",
        "original_evidence_preserved", "current_regressions_separate",
        "inherited_debt_visible", "operator_review_accountable",
        "multi_session_lineage_verified", "historical_truth_preserved",
    )
    for field in expected_true:
        if snapshot.get(field) is not True:
            errors.append(f"invalid_{field}")

    expected_false = (
        "actual_waiting_started", "automatic_continuation", "progression_started",
        "pause_executed", "resume_executed", "cancellation_executed",
        "automatic_recovery", "automatic_retry", "recovery_executed",
        "execution_invoked", "approval_created", "approval_consumed",
        "runtime_mutated", "production_source_modified", "provider_contacted",
        "model_contacted", "thread_started", "process_started",
        "global_profile_pass_claimed", "authority_granted",
    )
    for field in expected_false:
        if snapshot.get(field) is not False:
            errors.append(f"invalid_{field}")

    if snapshot.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")
    if snapshot.get("foundation_contract_version") != "v1195.2":
        errors.append("foundation_contract_drift")
    if snapshot.get("progression_contract_version") != "v1195.5":
        errors.append("progression_contract_drift")
    if snapshot.get("reliability_contract_version") != "v1195.8":
        errors.append("reliability_contract_drift")
    expected_counts = {
        "retained_checkpoint_count": 3,
        "soak_mode_count": 2,
        "domain_count": 9,
        "decision_count": 3,
        "progression_action_count": 9,
        "reliability_event_class_count": 8,
        "terminal_disposition_count": 4,
    }
    for field, expected in expected_counts.items():
        if snapshot.get(field) != expected:
            errors.append(f"invalid_{field}")
    if snapshot.get("checkpoint_digest") != _digest(
        {key: value for key, value in snapshot.items() if key != "checkpoint_digest"}
    ):
        errors.append("checkpoint_tamper")
    return sorted(set(errors))


def build_long_session_multi_day_soak_consolidated_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    foundations = build_long_session_multi_day_soak_checkpoint(source_root=source)
    progression = build_operator_reviewed_soak_progression_checkpoint(source_root=source)
    reliability = build_soak_reliability_adversarial_checkpoint(source_root=source)

    retained = (
        (foundations, "v1195.2", 212, 5),
        (progression, "v1195.5", 340, 5),
        (reliability, "v1195.8", 133, 2),
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
    progression_summary = dict(progression.get("summary") or {})
    reliability_summary = dict(reliability.get("summary") or {})

    snapshot: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "long-session-multi-day-soak:v1195.9",
        "foundation_contract_version": foundations.get("contract_version"),
        "progression_contract_version": progression.get("contract_version"),
        "reliability_contract_version": reliability.get("contract_version"),
        "retained_checkpoint_count": 3,
        "soak_mode_count": len(SOAK_MODES),
        "domain_count": len(SOAK_DOMAINS),
        "decision_count": len(DECISIONS),
        "progression_action_count": len(ACTIONS),
        "reliability_event_class_count": len(EVENTS),
        "terminal_disposition_count": progression_summary.get("terminal_disposition_count", 0),
        "interval_count": foundation_summary.get("interval_count", 0),
        "session_count": foundation_summary.get("session_count", 0),
        "day_count": foundation_summary.get("day_count", 0),
        "cycle_count": foundation_summary.get("cycle_count", 0),
        "transition_count": progression_summary.get("transition_count", 0),
        "reliability_ready_count": reliability_summary.get("ready_count", 0),
        "foreground_path_available": all(
            summary.get("foreground_path_available") is True
            for summary in (foundation_summary, progression_summary, reliability_summary)
        ),
        "latency_within_budget": foundation_summary.get("latency_within_budget") is True,
        "resource_budgets_within_bounds": foundation_summary.get("resource_budgets_within_bounds") is True,
        "progress_observed": foundation_summary.get("progress_observed") is True,
        "exact_lineage_verified": all(
            summary.get("exact_lineage_verified") is True
            for summary in (foundation_summary, progression_summary)
        ),
        "original_evidence_preserved": all(
            summary.get("original_evidence_preserved") is True
            for summary in (foundation_summary, progression_summary, reliability_summary)
        ),
        "current_regressions_separate": all(
            summary.get("current_regressions_separate") is True
            for summary in (foundation_summary, progression_summary)
        ),
        "inherited_debt_visible": all(
            summary.get("inherited_debt_visible") is True
            for summary in (foundation_summary, progression_summary)
        ),
        "operator_review_accountable": progression_summary.get("accountable_transition_presented") is True,
        "multi_session_lineage_verified": progression_summary.get("multi_session_lineage_verified") is True,
        "historical_truth_preserved": True,
        "content_free": True,
        "read_only": True,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "progression_started": False,
        "pause_executed": False,
        "resume_executed": False,
        "cancellation_executed": False,
        "automatic_recovery": False,
        "automatic_retry": False,
        "recovery_executed": False,
        "execution_invoked": False,
        "approval_created": False,
        "approval_consumed": False,
        "runtime_mutated": False,
        "production_source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
    snapshot["checkpoint_digest"] = _digest(snapshot)
    validation_errors = _validate_snapshot(snapshot)
    require(not validation_errors)

    expected_values = {
        "retained_checkpoint_count": 3,
        "soak_mode_count": 2,
        "domain_count": 9,
        "decision_count": 3,
        "progression_action_count": 9,
        "reliability_event_class_count": 8,
        "terminal_disposition_count": 4,
        "interval_count": 9,
        "session_count": 3,
        "day_count": 3,
        "cycle_count": 90,
        "transition_count": 9,
        "reliability_ready_count": 8,
        "foreground_path_available": True,
        "latency_within_budget": True,
        "resource_budgets_within_bounds": True,
        "progress_observed": True,
        "exact_lineage_verified": True,
        "original_evidence_preserved": True,
        "current_regressions_separate": True,
        "inherited_debt_visible": True,
        "operator_review_accountable": True,
        "multi_session_lineage_verified": True,
        "historical_truth_preserved": True,
        "content_free": True,
        "read_only": True,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "progression_started": False,
        "pause_executed": False,
        "resume_executed": False,
        "cancellation_executed": False,
        "automatic_recovery": False,
        "automatic_retry": False,
        "recovery_executed": False,
        "execution_invoked": False,
        "approval_created": False,
        "approval_consumed": False,
        "runtime_mutated": False,
        "production_source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
    for key, expected in expected_values.items():
        require(snapshot.get(key) == expected)
    require(len(str(snapshot.get("checkpoint_digest") or "")) == 64)

    blocked_cases: dict[str, list[str]] = {}
    mutations: dict[str, tuple[str, Any]] = {
        "private-field": ("prompt", "private"),
        "foundation-contract-drift": ("foundation_contract_version", "v1195.1"),
        "progression-contract-drift": ("progression_contract_version", "v1195.4"),
        "reliability-contract-drift": ("reliability_contract_version", "v1195.7"),
        "retained-count": ("retained_checkpoint_count", 2),
        "mode-count": ("soak_mode_count", 1),
        "domain-count": ("domain_count", 8),
        "decision-count": ("decision_count", 2),
        "action-count": ("progression_action_count", 8),
        "event-count": ("reliability_event_class_count", 7),
        "terminal-count": ("terminal_disposition_count", 3),
        "foreground-block": ("foreground_path_available", False),
        "latency-budget-loss": ("latency_within_budget", False),
        "resource-budget-loss": ("resource_budgets_within_bounds", False),
        "progress-loss": ("progress_observed", False),
        "lineage-loss": ("exact_lineage_verified", False),
        "evidence-loss": ("original_evidence_preserved", False),
        "verification-boundary-loss": ("current_regressions_separate", False),
        "debt-hidden": ("inherited_debt_visible", False),
        "review-accountability-loss": ("operator_review_accountable", False),
        "multi-session-lineage-loss": ("multi_session_lineage_verified", False),
        "historical-truth-loss": ("historical_truth_preserved", False),
        "actual-wait": ("actual_waiting_started", True),
        "automatic-continuation": ("automatic_continuation", True),
        "progression-start": ("progression_started", True),
        "pause-execution": ("pause_executed", True),
        "resume-execution": ("resume_executed", True),
        "cancellation-execution": ("cancellation_executed", True),
        "automatic-recovery": ("automatic_recovery", True),
        "automatic-retry": ("automatic_retry", True),
        "hidden-recovery": ("recovery_executed", True),
        "hidden-execution": ("execution_invoked", True),
        "approval-create": ("approval_created", True),
        "approval-consume": ("approval_consumed", True),
        "runtime-mutation": ("runtime_mutated", True),
        "source-mutation": ("production_source_modified", True),
        "provider-contact": ("provider_contacted", True),
        "model-contact": ("model_contacted", True),
        "thread-start": ("thread_started", True),
        "process-start": ("process_started", True),
        "global-pass-claim": ("global_profile_pass_claimed", True),
        "authority-state": ("authority_state", "granted"),
        "authority": ("authority_granted", True),
    }
    for name, (field, value) in mutations.items():
        altered = dict(snapshot)
        altered[field] = value
        altered.pop("checkpoint_digest", None)
        altered["checkpoint_digest"] = _digest(altered)
        blocked_cases[name] = _validate_snapshot(altered)
        require(bool(blocked_cases[name]))
    tampered = dict(snapshot)
    tampered["domain_count"] = 8
    blocked_cases["tamper"] = _validate_snapshot(tampered)
    require("checkpoint_tamper" in blocked_cases["tamper"])

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == _CHECKPOINT_ID),
        None,
    )
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_long_session_multi_day_soak_consolidated_checkpoint")
    require((descriptor or {}).get("read_only") is True)
    require((descriptor or {}).get("post_available") is False)
    require((descriptor or {}).get("required_input_count") == 0)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))
    for checkpoint_id in (
        "long-session-multi-day-soak-checkpoint",
        "operator-reviewed-soak-progression-checkpoint",
        "soak-reliability-adversarial-checkpoint",
        _CHECKPOINT_ID,
    ):
        require(any(row.get("checkpoint_id") == checkpoint_id for row in registry.get("checkpoints", [])))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    require(privacy.get("forbidden_runtime_entry_count", 0) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)

    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)

    summary = dict(snapshot)
    summary["blocked_case_count"] = len(blocked_cases)
    return {
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "long-session-multi-day-soak:v1195.9",
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "summary": summary,
        "retained_checkpoints": {
            "foundations": {"contract_version": foundations.get("contract_version"), "passed": foundations.get("passed"), "total": foundations.get("total")},
            "progression": {"contract_version": progression.get("contract_version"), "passed": progression.get("passed"), "total": progression.get("total")},
            "reliability": {"contract_version": reliability.get("contract_version"), "passed": reliability.get("passed"), "total": reliability.get("total")},
        },
        "blocked_cases": blocked_cases,
        "limitations": list(_LIMITATIONS),
        "source_unchanged": before_digest == after_digest,
        "runtime_mutated": False,
        "production_source_modified": False,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "progression_started": False,
        "pause_executed": False,
        "resume_executed": False,
        "approval_created": False,
        "approval_consumed": False,
        "cancellation_executed": False,
        "automatic_recovery": False,
        "automatic_retry": False,
        "recovery_executed": False,
        "execution_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
    }
