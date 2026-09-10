from __future__ import annotations

"""Read-only v1193.9 Verifier Ownership and Historical-Debt Consolidation checkpoint.

Consolidates verifier ownership, deterministic profile and budget reconciliation,
and fixture overlap/historical-debt classification. The checkpoint reads source
contracts only. It does not execute suites, delete fixtures, retire verifiers,
rewrite history, mutate runtime state, or grant authority.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from fixture_historical_debt_consolidation_checkpoint import build_fixture_historical_debt_consolidation_checkpoint
from package_integrity import package_privacy_summary_for_root
from verifier_ownership_checkpoint import build_verifier_ownership_checkpoint
from verifier_profile_reconciliation_checkpoint import build_verifier_profile_reconciliation_checkpoint

CONTRACT_VERSION = "v1193.9"
_CHECKPOINT_ID = "verifier-ownership-historical-debt:v1193.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_PRIVATE_KEYS = {
    "prompt", "conversation", "memory", "secret", "raw_source", "patch",
    "stdout", "stderr", "provider_payload", "private_reasoning", "content", "text",
}
_LIMITATIONS = (
    "Ownership, profile, fixture, and cleanup declarations remain source-declared and read-only.",
    "The checkpoint does not execute focused, quick, or full verification profiles.",
    "No fixture is deleted, no verifier is retired, and historical evidence is not rewritten.",
    "Inherited performance-budget and partial-overlap debt remains explicit and unresolved.",
    "Desktop Codex and native-provider review remain scheduled for v1200.",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
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


def _validate_public_snapshot(snapshot: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    lower = {str(key).lower() for key in snapshot}
    if lower & _PRIVATE_KEYS:
        errors.append("private_field")
    if snapshot.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")
    for field in (
        "fixture_deleted", "verifier_retired", "suite_execution_invoked",
        "runtime_mutated", "production_source_modified", "global_profile_pass_claimed",
    ):
        if snapshot.get(field) is not False:
            errors.append(f"invalid_{field}")
    if snapshot.get("historical_truth_preserved") is not True:
        errors.append("historical_truth_loss")
    if snapshot.get("current_regressions_separate") is not True:
        errors.append("current_debt_boundary_loss")
    if snapshot.get("profile_membership_deterministic") is not True:
        errors.append("profile_membership_drift")
    if snapshot.get("cleanup_ownership_assigned") is not True:
        errors.append("cleanup_ownership_missing")
    if snapshot.get("checkpoint_digest") != _digest({k: v for k, v in snapshot.items() if k != "checkpoint_digest"}):
        errors.append("checkpoint_tamper")
    return sorted(set(errors))


def build_verifier_historical_debt_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    ownership = build_verifier_ownership_checkpoint(source_root=source)
    profiles = build_verifier_profile_reconciliation_checkpoint(source_root=source)
    fixtures = build_fixture_historical_debt_consolidation_checkpoint(source_root=source)
    retained = ((ownership, "v1193.2"), (profiles, "v1193.5"), (fixtures, "v1193.8"))
    for report, version in retained:
        for key, expected in (
            ("ok", True), ("contract_version", version), ("read_only", True),
            ("content_free", True), ("source_unchanged", True),
            ("runtime_mutated", False), ("fixture_deleted", False),
            ("verifier_retired", False), ("global_profile_pass_claimed", False),
            ("execution_invoked", False), ("authority_granted", False),
        ):
            require(report.get(key) == expected)
        require(report.get("passed") == report.get("total"))

    ownership_summary = dict(ownership.get("summary") or {})
    focused = dict((profiles.get("summaries") or {}).get("focused") or {})
    quick = dict((profiles.get("summaries") or {}).get("quick") or {})
    full = dict((profiles.get("summaries") or {}).get("full") or {})
    fixture_summary = dict(fixtures.get("summary") or {})

    snapshot: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "ownership_record_count": ownership_summary.get("record_count", 0),
        "owner_count": ownership_summary.get("owner_count", 0),
        "current_regression_count": ownership_summary.get("current_regression_count", 0),
        "retained_checkpoint_count": ownership_summary.get("retained_checkpoint_count", 0),
        "historical_debt_count": ownership_summary.get("historical_debt_count", 0),
        "duplicate_fixture_group_count": ownership_summary.get("duplicate_fixture_group_count", 0),
        "profile_count": 3,
        "focused_current_pass": focused.get("current_regressions_passed") is True,
        "focused_global_pass": focused.get("global_profile_pass") is True,
        "quick_current_pass": quick.get("current_regressions_passed") is True,
        "quick_global_pass": quick.get("global_profile_pass") is True,
        "full_current_pass": full.get("current_regressions_passed") is True,
        "full_global_pass": full.get("global_profile_pass") is True,
        "inherited_nonpass_count": max(int(quick.get("inherited_nonpass_count", 0)), int(full.get("inherited_nonpass_count", 0))),
        "fixture_record_count": fixture_summary.get("record_count", 0),
        "fixture_group_count": fixture_summary.get("fixture_group_count", 0),
        "alias_count": fixture_summary.get("alias_count", 0),
        "deferred_count": fixture_summary.get("deferred_count", 0),
        "cleanup_owner_count": fixture_summary.get("cleanup_owner_count", 0),
        "historical_truth_preserved": fixture_summary.get("historical_truth_preserved") is True,
        "current_regressions_separate": ownership_summary.get("debt_separated") is True and quick.get("historical_debt_separate") is True,
        "profile_membership_deterministic": all((profiles.get("summaries") or {}).get(name, {}).get("status") == "reconciled" for name in ("focused", "quick", "full")),
        "cleanup_ownership_assigned": int(fixture_summary.get("cleanup_owner_count", 0)) > 0,
        "fixture_deleted": False,
        "verifier_retired": False,
        "suite_execution_invoked": False,
        "runtime_mutated": False,
        "production_source_modified": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
    }
    snapshot["checkpoint_digest"] = _digest(snapshot)
    validation_errors = _validate_public_snapshot(snapshot)
    require(not validation_errors)

    expected_values = {
        "ownership_record_count": 6,
        "owner_count": 5,
        "current_regression_count": 1,
        "retained_checkpoint_count": 3,
        "historical_debt_count": 2,
        "profile_count": 3,
        "focused_current_pass": True,
        "focused_global_pass": True,
        "quick_current_pass": True,
        "quick_global_pass": False,
        "full_current_pass": True,
        "full_global_pass": False,
        "inherited_nonpass_count": 1,
        "fixture_record_count": 4,
        "fixture_group_count": 3,
        "alias_count": 1,
        "deferred_count": 1,
        "cleanup_owner_count": 2,
        "historical_truth_preserved": True,
        "current_regressions_separate": True,
        "profile_membership_deterministic": True,
        "cleanup_ownership_assigned": True,
    }
    for key, expected in expected_values.items():
        require(snapshot.get(key) == expected)

    blocked_cases: dict[str, list[str]] = {}
    mutations = {
        "private-field": ("prompt", "private"),
        "authority": ("authority_state", "granted"),
        "fixture-delete": ("fixture_deleted", True),
        "verifier-retire": ("verifier_retired", True),
        "suite-execution": ("suite_execution_invoked", True),
        "runtime-mutation": ("runtime_mutated", True),
        "source-mutation": ("production_source_modified", True),
        "global-pass-claim": ("global_profile_pass_claimed", True),
        "truth-loss": ("historical_truth_preserved", False),
        "boundary-loss": ("current_regressions_separate", False),
        "membership-drift": ("profile_membership_deterministic", False),
        "cleanup-owner-loss": ("cleanup_ownership_assigned", False),
        "tamper": ("owner_count", 999),
    }
    for name, (field, value) in mutations.items():
        candidate = dict(snapshot)
        candidate[field] = value
        if name != "tamper":
            candidate.pop("checkpoint_digest", None)
            candidate["checkpoint_digest"] = _digest(candidate)
        errors = _validate_public_snapshot(candidate)
        blocked_cases[name] = errors
        require(bool(errors))
        require(candidate.get("suite_execution_invoked") is not True or "invalid_suite_execution_invoked" in errors)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "verifier-historical-debt-checkpoint"),
        None,
    )
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("contract_version") == CONTRACT_VERSION)
    require((checkpoint_row or {}).get("builder") == "build_verifier_historical_debt_checkpoint")
    require((checkpoint_row or {}).get("read_only") is True)
    require((checkpoint_row or {}).get("post_available") is False)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    require(int(privacy.get("forbidden_entry_count", 0)) == 0)
    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)

    return {
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "summary": snapshot,
        "retained_checkpoints": {
            "v1193.2": {"passed": ownership.get("passed"), "total": ownership.get("total")},
            "v1193.5": {"passed": profiles.get("passed"), "total": profiles.get("total")},
            "v1193.8": {"passed": fixtures.get("passed"), "total": fixtures.get("total")},
        },
        "blocked_cases": blocked_cases,
        "validation_errors": validation_errors,
        "limitations": list(_LIMITATIONS),
        "source_unchanged": before_digest == after_digest,
        "source_file_count": before_count,
        "runtime_mutated": False,
        "production_source_modified": False,
        "fixture_deleted": False,
        "verifier_retired": False,
        "global_profile_pass_claimed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "execution_invoked": False,
        "approval_consumed": False,
        "authority_granted": False,
    }
