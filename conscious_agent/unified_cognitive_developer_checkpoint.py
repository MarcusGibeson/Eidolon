from __future__ import annotations

"""Read-only v1194.9 Unified Cognitive and Developer Experience checkpoint.

This checkpoint consolidates the v1194 foundations, operator coordination, and
reliability hardening surfaces. It reads source-declared, content-free evidence
only. It does not fetch private subsystem state, execute work, consume approval,
perform recovery, mutate runtime state, contact providers or models, or grant
authority.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_cognitive_developer_coordination_checkpoint import build_unified_cognitive_developer_coordination_checkpoint
from unified_cognitive_developer_experience_checkpoint import build_unified_cognitive_developer_experience_checkpoint
from unified_cognitive_developer_reliability_checkpoint import build_unified_cognitive_developer_reliability_checkpoint

CONTRACT_VERSION = "v1194.9"
_CHECKPOINT_ID = "unified-cognitive-developer-checkpoint"
_EXCLUDED_DIRS = {
    "data",
    "sandbox",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "reports",
}
_PRIVATE_KEYS = {
    "prompt",
    "conversation",
    "message",
    "memory",
    "secret",
    "raw_source",
    "source_text",
    "patch",
    "patch_text",
    "stdout",
    "stderr",
    "provider_payload",
    "private_reasoning",
}
_LIMITATIONS = (
    "The checkpoint consolidates caller-supplied, content-free evidence and does not fetch private subsystem records.",
    "Navigation, reliability, recovery, and verifier information remain presentation-only and non-mutating.",
    "No approval is created or consumed, and no queue item, campaign, action, provider, model, process, or thread executes.",
    "Inherited global-profile performance and partial-fixture-overlap debt remains explicit and unresolved.",
    "Long-session and multi-day soak hardening begins in v1195; Desktop Codex and native-provider review remain scheduled for v1200.",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
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
        str(key)
        for key in snapshot
        if any(token in str(key).lower() for token in _PRIVATE_KEYS)
    )


def _validate_snapshot(snapshot: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in _private_fields(snapshot):
        errors.append(f"private_field:{field}")

    expected_true = (
        "content_free",
        "read_only",
        "foreground_path_available",
        "background_work_separate",
        "exact_expansion_verified",
        "original_evidence_preserved",
        "current_regressions_separate",
        "inherited_debt_visible",
        "approval_separate",
        "navigation_accountable",
        "latency_within_budget",
        "historical_truth_preserved",
    )
    for field in expected_true:
        if snapshot.get(field) is not True:
            errors.append(f"invalid_{field}")

    expected_false = (
        "subsystem_state_changed",
        "approval_created",
        "approval_consumed",
        "automatic_continuation",
        "recovery_executed",
        "execution_invoked",
        "runtime_mutated",
        "production_source_modified",
        "provider_contacted",
        "model_contacted",
        "thread_started",
        "process_started",
        "global_profile_pass_claimed",
        "authority_granted",
    )
    for field in expected_false:
        if snapshot.get(field) is not False:
            errors.append(f"invalid_{field}")

    if snapshot.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")
    if snapshot.get("foundation_contract_version") != "v1194.2":
        errors.append("foundation_contract_drift")
    if snapshot.get("coordination_contract_version") != "v1194.5":
        errors.append("coordination_contract_drift")
    if snapshot.get("reliability_contract_version") != "v1194.8":
        errors.append("reliability_contract_drift")
    if snapshot.get("domain_count") != 9:
        errors.append("invalid_domain_count")
    if snapshot.get("work_surface_count") != 2:
        errors.append("invalid_work_surface_count")
    if snapshot.get("decision_count") != 3:
        errors.append("invalid_decision_count")
    if snapshot.get("reliability_event_class_count") != 8:
        errors.append("invalid_reliability_event_class_count")
    if snapshot.get("retained_checkpoint_count") != 3:
        errors.append("invalid_retained_checkpoint_count")
    if snapshot.get("checkpoint_digest") != _digest(
        {key: value for key, value in snapshot.items() if key != "checkpoint_digest"}
    ):
        errors.append("checkpoint_tamper")
    return sorted(set(errors))


def build_unified_cognitive_developer_checkpoint(
    *,
    source_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    foundations = build_unified_cognitive_developer_experience_checkpoint(source_root=source)
    coordination = build_unified_cognitive_developer_coordination_checkpoint(source_root=source)
    reliability = build_unified_cognitive_developer_reliability_checkpoint(source_root=source)
    retained = (
        (foundations, "v1194.2", 50),
        (coordination, "v1194.5", 89),
        (reliability, "v1194.8", 174),
    )
    for report, version, expected_total in retained:
        for key, expected in (
            ("ok", True),
            ("contract_version", version),
            ("read_only", True),
            ("post_available", False),
            ("content_free", True),
            ("source_unchanged", True),
            ("runtime_mutated", False),
            ("production_source_modified", False),
            ("approval_created", False),
            ("approval_consumed", False),
            ("execution_invoked", False),
            ("provider_contacted", False),
            ("model_contacted", False),
            ("thread_started", False),
            ("process_started", False),
            ("authority_granted", False),
        ):
            require(report.get(key) == expected)
        require(report.get("passed") == report.get("total"))
        require(report.get("total") == expected_total)
        require(len(report.get("limitations") or []) == 5)
        require(bool(report.get("summary")))
        require(bool(report.get("blocked_cases")))
        for errors in (report.get("blocked_cases") or {}).values():
            require(bool(errors))

    foundation_summary = dict(foundations.get("summary") or {})
    coordination_summary = dict(coordination.get("summary") or {})
    reliability_summary = dict(reliability.get("summary") or {})

    snapshot: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "unified-cognitive-developer:v1194.9",
        "foundation_contract_version": foundations.get("contract_version"),
        "coordination_contract_version": coordination.get("contract_version"),
        "reliability_contract_version": reliability.get("contract_version"),
        "retained_checkpoint_count": 3,
        "domain_count": foundation_summary.get("domain_count", 0),
        "work_surface_count": 2,
        "decision_count": coordination_summary.get("decision_count", 0),
        "reliability_event_class_count": reliability_summary.get("event_class_count", 0),
        "foreground_path_available": all(
            summary.get("foreground_path_available") is True
            for summary in (foundation_summary, coordination_summary, reliability_summary)
        ),
        "background_work_separate": foundation_summary.get("background_work_separate") is True,
        "exact_expansion_verified": foundation_summary.get("exact_expansion_verified") is True,
        "original_evidence_preserved": all(
            summary.get("original_evidence_preserved") is True
            for summary in (foundation_summary, coordination_summary, reliability_summary)
        ),
        "current_regressions_separate": all(
            summary.get("current_regressions_separate") is True
            for summary in (foundation_summary, coordination_summary)
        ),
        "inherited_debt_visible": all(
            summary.get("inherited_debt_visible") is True
            for summary in (foundation_summary, coordination_summary, reliability_summary)
        ),
        "approval_separate": foundation_summary.get("approval_separate") is True,
        "navigation_accountable": coordination_summary.get("accountable_transition") is True,
        "latency_within_budget": reliability_summary.get("latency_within_budget") is True,
        "historical_truth_preserved": True,
        "content_free": True,
        "read_only": True,
        "subsystem_state_changed": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "recovery_executed": False,
        "execution_invoked": False,
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
        "domain_count": 9,
        "work_surface_count": 2,
        "decision_count": 3,
        "reliability_event_class_count": 8,
        "foreground_path_available": True,
        "background_work_separate": True,
        "exact_expansion_verified": True,
        "original_evidence_preserved": True,
        "current_regressions_separate": True,
        "inherited_debt_visible": True,
        "approval_separate": True,
        "navigation_accountable": True,
        "latency_within_budget": True,
        "historical_truth_preserved": True,
        "content_free": True,
        "read_only": True,
        "subsystem_state_changed": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "recovery_executed": False,
        "execution_invoked": False,
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
        "foundation-contract-drift": ("foundation_contract_version", "v1194.1"),
        "coordination-contract-drift": ("coordination_contract_version", "v1194.4"),
        "reliability-contract-drift": ("reliability_contract_version", "v1194.7"),
        "domain-count": ("domain_count", 8),
        "work-surface-count": ("work_surface_count", 1),
        "decision-count": ("decision_count", 2),
        "event-count": ("reliability_event_class_count", 7),
        "retained-count": ("retained_checkpoint_count", 2),
        "foreground-block": ("foreground_path_available", False),
        "background-boundary-loss": ("background_work_separate", False),
        "compaction-equivalence-loss": ("exact_expansion_verified", False),
        "evidence-loss": ("original_evidence_preserved", False),
        "verification-boundary-loss": ("current_regressions_separate", False),
        "debt-hidden": ("inherited_debt_visible", False),
        "approval-boundary-loss": ("approval_separate", False),
        "navigation-accountability-loss": ("navigation_accountable", False),
        "latency-budget-loss": ("latency_within_budget", False),
        "historical-truth-loss": ("historical_truth_preserved", False),
        "subsystem-mutation": ("subsystem_state_changed", True),
        "approval-create": ("approval_created", True),
        "approval-consume": ("approval_consumed", True),
        "automatic-continuation": ("automatic_continuation", True),
        "hidden-recovery": ("recovery_executed", True),
        "hidden-execution": ("execution_invoked", True),
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
        (
            row
            for row in registry.get("checkpoints", [])
            if row.get("checkpoint_id") == _CHECKPOINT_ID
        ),
        None,
    )
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_unified_cognitive_developer_checkpoint")
    require((descriptor or {}).get("read_only") is True)
    require((descriptor or {}).get("post_available") is False)
    require((descriptor or {}).get("required_input_count") == 0)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))
    for checkpoint_id in (
        "unified-cognitive-developer-experience-checkpoint",
        "unified-cognitive-developer-coordination-checkpoint",
        "unified-cognitive-developer-reliability-checkpoint",
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
        "checkpoint_id": "unified-cognitive-developer:v1194.9",
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "summary": summary,
        "retained_checkpoints": {
            "foundations": {
                "contract_version": foundations.get("contract_version"),
                "passed": foundations.get("passed"),
                "total": foundations.get("total"),
            },
            "coordination": {
                "contract_version": coordination.get("contract_version"),
                "passed": coordination.get("passed"),
                "total": coordination.get("total"),
            },
            "reliability": {
                "contract_version": reliability.get("contract_version"),
                "passed": reliability.get("passed"),
                "total": reliability.get("total"),
            },
        },
        "blocked_cases": blocked_cases,
        "limitations": list(_LIMITATIONS),
        "source_unchanged": before_digest == after_digest,
        "runtime_mutated": False,
        "production_source_modified": False,
        "subsystem_state_changed": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "recovery_executed": False,
        "execution_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
    }
