from __future__ import annotations

"""Content-free v1195.2 long-session and multi-day soak foundations.

The contract models caller-supplied observation evidence. It never sleeps,
waits, schedules, executes, cancels, retries, recovers, contacts a provider, or
mutates runtime state. Long duration is represented by bounded evidence, not by
an autonomous process remaining alive.
"""

import hashlib
import json
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1195.2"
SOAK_MODES = ("long_session", "multi_day")
SOAK_DOMAINS = (
    "conversation",
    "cognition",
    "action",
    "campaign",
    "queue",
    "cancellation",
    "interruption",
    "restart",
    "recovery",
)
LIFECYCLE_STATES = (
    "proposed",
    "review_required",
    "observation_only",
    "paused_evidence_only",
    "completed_evidence_only",
    "failed_evidence_only",
    "blocked",
    "inconclusive",
)
PROGRESS_STATES = ("progress_observed", "no_change_expected", "stalled", "regressed")
INTERRUPTION_STATES = ("none", "observed", "unsupported", "reconciled_evidence_only")
RESTART_STATES = ("not_observed", "observed", "reconciled_evidence_only", "failed_evidence_only")
PROVIDER_STATES = ("not_contacted", "outage_observed", "available_not_contacted")
RECOVERY_STATES = ("not_applicable", "review_required_not_executed", "blocked", "inconclusive")
PRIVATE_TOKENS = (
    "prompt",
    "conversation_text",
    "message",
    "memory_content",
    "memory_text",
    "memory_record",
    "secret",
    "raw_source",
    "source_text",
    "patch",
    "stdout",
    "stderr",
    "provider_payload",
    "private_reasoning",
)
MAX_INTERVALS = 32
MAX_DAYS = 14
MAX_SESSIONS = 64
MAX_CYCLES = 100_000
MAX_ELAPSED_SECONDS = 14 * 24 * 60 * 60
MAX_LATENCY_BUDGET_MS = 60_000
MAX_TOKEN_BUDGET = 10_000_000
MAX_DISK_BUDGET_BYTES = 20_000_000_000
MAX_MEMORY_BUDGET_MB = 65_536


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _is_digest(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(character in "0123456789abcdef" for character in token)


def _private_fields(value: object, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            if any(token in str(key).lower() for token in PRIVATE_TOKENS):
                findings.append(label)
            findings.extend(_private_fields(item, label))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(_private_fields(item, f"{prefix}[{index}]"))
    return sorted(set(findings))


def create_soak_plan(
    *,
    soak_id: str,
    soak_mode: str,
    snapshot_digest: str,
    context_digest: str,
    purpose_code: str,
    planned_days: int,
    planned_sessions: int,
    max_intervals: int,
    max_elapsed_seconds: int,
    max_cycles: int,
    foreground_latency_budget_ms: int,
    token_budget: int,
    disk_budget_bytes: int,
    memory_budget_mb: int,
    deadline_mode: str = "no_deadline",
    deadline_epoch_ms: int | None = None,
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "soak_id": str(soak_id),
        "soak_mode": str(soak_mode),
        "snapshot_digest": str(snapshot_digest),
        "context_digest": str(context_digest),
        "purpose_code": str(purpose_code),
        "planned_days": planned_days,
        "planned_sessions": planned_sessions,
        "max_intervals": max_intervals,
        "max_elapsed_seconds": max_elapsed_seconds,
        "max_cycles": max_cycles,
        "foreground_latency_budget_ms": foreground_latency_budget_ms,
        "token_budget": token_budget,
        "disk_budget_bytes": disk_budget_bytes,
        "memory_budget_mb": memory_budget_mb,
        "deadline_mode": str(deadline_mode),
        "deadline_epoch_ms": deadline_epoch_ms,
        "content_free": True,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "execution_invoked": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "authority_state": "separate_not_granted",
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def create_soak_interval(
    *,
    soak_id: str,
    interval_id: str,
    domain: str,
    sequence: int,
    session_index: int,
    day_index: int,
    cycle_start: int,
    cycle_end: int,
    elapsed_seconds: int,
    observed_latency_ms: int,
    observed_tokens: int,
    observed_disk_bytes: int,
    observed_memory_mb: int,
    snapshot_digest: str,
    context_digest: str,
    artifact_digest: str,
    receipt_digest: str,
    previous_interval_digest: str,
    purpose_code: str,
    lifecycle_state: str = "observation_only",
    progress_state: str = "progress_observed",
    interruption_state: str = "none",
    restart_state: str = "not_observed",
    provider_state: str = "not_contacted",
    recovery_state: str = "not_applicable",
) -> dict[str, Any]:
    interval: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "soak_id": str(soak_id),
        "interval_id": str(interval_id),
        "domain": str(domain),
        "sequence": sequence,
        "session_index": session_index,
        "day_index": day_index,
        "cycle_start": cycle_start,
        "cycle_end": cycle_end,
        "elapsed_seconds": elapsed_seconds,
        "observed_latency_ms": observed_latency_ms,
        "observed_tokens": observed_tokens,
        "observed_disk_bytes": observed_disk_bytes,
        "observed_memory_mb": observed_memory_mb,
        "snapshot_digest": str(snapshot_digest),
        "context_digest": str(context_digest),
        "artifact_digest": str(artifact_digest),
        "receipt_digest": str(receipt_digest),
        "previous_interval_digest": str(previous_interval_digest),
        "purpose_code": str(purpose_code),
        "lifecycle_state": str(lifecycle_state),
        "progress_state": str(progress_state),
        "interruption_state": str(interruption_state),
        "restart_state": str(restart_state),
        "provider_state": str(provider_state),
        "recovery_state": str(recovery_state),
        "content_free": True,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "execution_invoked": False,
        "cancellation_executed": False,
        "recovery_executed": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "authority_state": "separate_not_granted",
    }
    interval["interval_digest"] = _digest(interval)
    return interval


def assess_soak_evidence(
    plan: Mapping[str, Any],
    intervals: Sequence[Mapping[str, Any]],
    *,
    current_snapshot_digest: str,
    current_context_digest: str,
    verification_summary: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    plan_row = dict(plan)
    rows = [dict(row) for row in intervals]

    for field in _private_fields({"plan": plan_row, "intervals": rows, "verification": dict(verification_summary)}):
        errors.append(f"private_field:{field}")

    supplied_plan_digest = plan_row.get("plan_digest")
    unsigned_plan = dict(plan_row)
    unsigned_plan.pop("plan_digest", None)
    if supplied_plan_digest != _digest(unsigned_plan):
        errors.append("plan_tamper")
    if plan_row.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported_plan_contract")
    if plan_row.get("soak_mode") not in SOAK_MODES:
        errors.append("unsupported_soak_mode")
    if not str(plan_row.get("soak_id") or ""):
        errors.append("missing_soak_id")
    for field in ("snapshot_digest", "context_digest"):
        if not _is_digest(plan_row.get(field)):
            errors.append(f"malformed_plan_{field}")
    if plan_row.get("snapshot_digest") != current_snapshot_digest:
        errors.append("stale_plan_snapshot")
    if plan_row.get("context_digest") != current_context_digest:
        errors.append("stale_plan_context")

    bounded_fields = {
        "planned_days": (1, MAX_DAYS),
        "planned_sessions": (1, MAX_SESSIONS),
        "max_intervals": (len(SOAK_DOMAINS), MAX_INTERVALS),
        "max_elapsed_seconds": (1, MAX_ELAPSED_SECONDS),
        "max_cycles": (1, MAX_CYCLES),
        "foreground_latency_budget_ms": (1, MAX_LATENCY_BUDGET_MS),
        "token_budget": (0, MAX_TOKEN_BUDGET),
        "disk_budget_bytes": (0, MAX_DISK_BUDGET_BYTES),
        "memory_budget_mb": (1, MAX_MEMORY_BUDGET_MB),
    }
    for field, (minimum, maximum) in bounded_fields.items():
        value = plan_row.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            errors.append(f"malformed_{field}")

    if plan_row.get("deadline_mode") not in {"no_deadline", "bounded_deadline"}:
        errors.append("unsupported_deadline_mode")
    elif plan_row.get("deadline_mode") == "no_deadline" and plan_row.get("deadline_epoch_ms") is not None:
        errors.append("deadline_truth_mismatch")
    elif plan_row.get("deadline_mode") == "bounded_deadline":
        value = plan_row.get("deadline_epoch_ms")
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            errors.append("deadline_truth_mismatch")

    expected_false = (
        "actual_waiting_started",
        "automatic_continuation",
        "execution_invoked",
        "runtime_mutated",
        "provider_contacted",
        "model_contacted",
        "thread_started",
        "process_started",
    )
    for field in expected_false:
        if plan_row.get(field) is not False:
            errors.append(f"plan_{field}_claim")
    if plan_row.get("authority_state") != "separate_not_granted":
        errors.append("plan_authority_expansion")
    if plan_row.get("content_free") is not True:
        errors.append("plan_content_exposure")

    max_intervals = plan_row.get("max_intervals") if isinstance(plan_row.get("max_intervals"), int) else 0
    if not rows:
        errors.append("empty_soak_evidence")
    if len(rows) > MAX_INTERVALS or len(rows) > max_intervals:
        errors.append("oversized_soak_evidence")
    interval_ids = [str(row.get("interval_id") or "") for row in rows]
    if len(set(interval_ids)) != len(interval_ids):
        errors.append("duplicate_interval_id")
    sequences = [row.get("sequence") for row in rows]
    if sequences != list(range(len(rows))):
        errors.append("duplicate_or_noncontiguous_sequence")
    domains = [row.get("domain") for row in rows]
    if set(domains) != set(SOAK_DOMAINS):
        errors.append("unsupported_or_missing_domain")

    previous = ""
    seen_cycles: set[int] = set()
    total_elapsed = 0
    total_cycles = 0
    total_tokens = 0
    max_disk = 0
    max_memory = 0
    max_latency = 0
    day_indexes: set[int] = set()
    session_indexes: set[int] = set()
    interruption_count = 0
    restart_count = 0
    recovery_review_count = 0
    progress_count = 0

    for row in rows:
        supplied = row.get("interval_digest")
        unsigned = dict(row)
        unsigned.pop("interval_digest", None)
        if supplied != _digest(unsigned):
            errors.append("interval_tamper")
        if row.get("contract_version") != CONTRACT_VERSION:
            errors.append("unsupported_interval_contract")
        if row.get("soak_id") != plan_row.get("soak_id"):
            errors.append("soak_id_mismatch")
        if row.get("previous_interval_digest") != previous:
            errors.append("broken_interval_lineage")
        previous = str(supplied or "")
        for field in ("snapshot_digest", "context_digest", "artifact_digest", "receipt_digest"):
            if not _is_digest(row.get(field)):
                errors.append(f"malformed_{field}")
        if row.get("snapshot_digest") != current_snapshot_digest:
            errors.append("stale_interval_snapshot")
        if row.get("context_digest") != current_context_digest:
            errors.append("stale_interval_context")
        if row.get("domain") not in SOAK_DOMAINS:
            errors.append("unsupported_domain")
        if row.get("lifecycle_state") not in LIFECYCLE_STATES:
            errors.append("unsupported_lifecycle_state")
        if row.get("progress_state") not in PROGRESS_STATES:
            errors.append("unsupported_progress_state")
        if row.get("progress_state") in {"stalled", "regressed"}:
            errors.append("stalled_or_regressed_progress")
        if row.get("progress_state") == "progress_observed":
            progress_count += 1
        if row.get("interruption_state") not in INTERRUPTION_STATES:
            errors.append("unsupported_interruption_state")
        if row.get("restart_state") not in RESTART_STATES:
            errors.append("unsupported_restart_state")
        if row.get("provider_state") not in PROVIDER_STATES:
            errors.append("unsupported_provider_state")
        if row.get("recovery_state") not in RECOVERY_STATES:
            errors.append("unsupported_recovery_state")
        if row.get("interruption_state") != "none":
            interruption_count += 1
        if row.get("restart_state") != "not_observed":
            restart_count += 1
        if row.get("recovery_state") == "review_required_not_executed":
            recovery_review_count += 1

        day_index = row.get("day_index")
        session_index = row.get("session_index")
        if not isinstance(day_index, int) or isinstance(day_index, bool) or day_index < 0:
            errors.append("invalid_day_index")
        else:
            day_indexes.add(day_index)
        if not isinstance(session_index, int) or isinstance(session_index, bool) or session_index < 0:
            errors.append("invalid_session_index")
        else:
            session_indexes.add(session_index)

        start = row.get("cycle_start")
        end = row.get("cycle_end")
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or start < 0 or end <= start:
            errors.append("invalid_cycle_range")
        else:
            cycle_range = set(range(start, end))
            if seen_cycles.intersection(cycle_range):
                errors.append("duplicate_or_overlapping_cycle")
            seen_cycles.update(cycle_range)
            total_cycles += end - start

        numeric_bounds = {
            "elapsed_seconds": (1, MAX_ELAPSED_SECONDS),
            "observed_latency_ms": (0, MAX_LATENCY_BUDGET_MS),
            "observed_tokens": (0, MAX_TOKEN_BUDGET),
            "observed_disk_bytes": (0, MAX_DISK_BUDGET_BYTES),
            "observed_memory_mb": (0, MAX_MEMORY_BUDGET_MB),
        }
        for field, (minimum, maximum) in numeric_bounds.items():
            value = row.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
                errors.append(f"malformed_{field}")
        total_elapsed += row.get("elapsed_seconds") if isinstance(row.get("elapsed_seconds"), int) else 0
        total_tokens += row.get("observed_tokens") if isinstance(row.get("observed_tokens"), int) else 0
        max_disk = max(max_disk, row.get("observed_disk_bytes") if isinstance(row.get("observed_disk_bytes"), int) else 0)
        max_memory = max(max_memory, row.get("observed_memory_mb") if isinstance(row.get("observed_memory_mb"), int) else 0)
        max_latency = max(max_latency, row.get("observed_latency_ms") if isinstance(row.get("observed_latency_ms"), int) else 0)

        for field in (
            "actual_waiting_started",
            "automatic_continuation",
            "execution_invoked",
            "cancellation_executed",
            "recovery_executed",
            "runtime_mutated",
            "provider_contacted",
            "model_contacted",
            "thread_started",
            "process_started",
        ):
            if row.get(field) is not False:
                errors.append(f"interval_{field}_claim")
        if row.get("authority_state") != "separate_not_granted":
            errors.append("interval_authority_expansion")
        if row.get("content_free") is not True:
            errors.append("interval_content_exposure")

    if len(day_indexes) > int(plan_row.get("planned_days") or 0):
        errors.append("planned_day_budget_exceeded")
    if len(session_indexes) > int(plan_row.get("planned_sessions") or 0):
        errors.append("planned_session_budget_exceeded")
    if total_elapsed > int(plan_row.get("max_elapsed_seconds") or 0):
        errors.append("elapsed_budget_exceeded")
    if total_cycles > int(plan_row.get("max_cycles") or 0):
        errors.append("cycle_budget_exceeded")
    if total_tokens > int(plan_row.get("token_budget") or 0):
        errors.append("token_budget_exceeded")
    if max_disk > int(plan_row.get("disk_budget_bytes") or 0):
        errors.append("disk_budget_exceeded")
    if max_memory > int(plan_row.get("memory_budget_mb") or 0):
        errors.append("memory_budget_exceeded")
    if max_latency > int(plan_row.get("foreground_latency_budget_ms") or 0):
        errors.append("foreground_latency_budget_exceeded")
    if progress_count == 0:
        errors.append("no_progress_evidence")

    if verification_summary.get("content_free") is not True:
        errors.append("invalid_verification_summary")
    if verification_summary.get("current_regressions_separate") is not True:
        errors.append("verification_boundary_loss")
    if verification_summary.get("inherited_debt_visible") is not True:
        errors.append("inherited_debt_hidden")
    if verification_summary.get("global_profile_pass_claimed") is not False:
        errors.append("global_pass_claim")

    unique_errors = sorted(set(errors))
    summary: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "soak_mode": plan_row.get("soak_mode"),
        "interval_count": len(rows),
        "domain_count": len(set(domain for domain in domains if domain in SOAK_DOMAINS)),
        "session_count": len(session_indexes),
        "day_count": len(day_indexes),
        "cycle_count": total_cycles,
        "elapsed_seconds": total_elapsed,
        "interruption_evidence_count": interruption_count,
        "restart_evidence_count": restart_count,
        "recovery_review_count": recovery_review_count,
        "foreground_path_available": "foreground_latency_budget_exceeded" not in unique_errors,
        "latency_within_budget": "foreground_latency_budget_exceeded" not in unique_errors,
        "resource_budgets_within_bounds": not any(error.endswith("budget_exceeded") for error in unique_errors),
        "progress_observed": progress_count > 0 and "stalled_or_regressed_progress" not in unique_errors,
        "exact_lineage_verified": not any(error in unique_errors for error in ("broken_interval_lineage", "interval_tamper", "plan_tamper")),
        "original_evidence_preserved": True,
        "current_regressions_separate": verification_summary.get("current_regressions_separate") is True,
        "inherited_debt_visible": verification_summary.get("inherited_debt_visible") is True,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "execution_invoked": False,
        "cancellation_executed": False,
        "recovery_executed": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
        "content_free": True,
    }
    summary["soak_digest"] = _digest(
        {
            "plan": plan_row,
            "intervals": rows,
            "verification": dict(verification_summary),
            "summary": summary,
        }
    )
    return {
        "status": "ready_for_operator_review" if not unique_errors else "blocked",
        "errors": unique_errors,
        "error_count": len(unique_errors),
        "plan": plan_row,
        "intervals": rows,
        "summary": summary,
        "content_free": True,
        "read_only": True,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "approval_created": False,
        "approval_consumed": False,
        "execution_invoked": False,
        "cancellation_executed": False,
        "recovery_executed": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "authority_granted": False,
    }


def public_soak_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    """Return the bounded public summary only."""

    return dict(report.get("summary") or {})
