from __future__ import annotations

"""Read-only v1195.2 Long-Session and Multi-Day Soak Foundations checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from long_session_multi_day_soak import SOAK_DOMAINS, assess_soak_evidence, create_soak_interval, create_soak_plan, public_soak_summary
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1195.2"
_CHECKPOINT_ID = "long-session-multi-day-soak-checkpoint"
_LIMITATIONS = (
    "Long-session and multi-day duration is represented by bounded caller-supplied evidence; the checkpoint does not wait or remain alive.",
    "No private conversation, cognition, campaign, queue, cancellation, interruption, restart, or recovery record is fetched.",
    "No approval is created or consumed, and no work, cancellation, retry, restart, recovery, provider, model, process, or thread executes.",
    "Operator-reviewed soak progression, pause, resume, and interval dispositions are deferred to v1195.3-v1195.5.",
    "Desktop Codex and native-provider review remain scheduled for v1200.",
)
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


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _case() -> tuple[dict[str, Any], list[dict[str, Any]], str, str, dict[str, Any]]:
    snapshot = _h("v1195.2:unified-snapshot")
    context = _h("v1195.2:unified-context")
    plan = create_soak_plan(
        soak_id="soak-foundations-0001",
        soak_mode="multi_day",
        snapshot_digest=snapshot,
        context_digest=context,
        purpose_code="operator_long_session_multi_day_review",
        planned_days=3,
        planned_sessions=3,
        max_intervals=16,
        max_elapsed_seconds=259_200,
        max_cycles=1_000,
        foreground_latency_budget_ms=750,
        token_budget=90_000,
        disk_budget_bytes=10_000_000,
        memory_budget_mb=2_048,
        deadline_mode="no_deadline",
    )
    rows: list[dict[str, Any]] = []
    previous = ""
    for index, domain in enumerate(SOAK_DOMAINS):
        interruption_state = "observed" if domain == "interruption" else "none"
        restart_state = "reconciled_evidence_only" if domain == "restart" else "not_observed"
        provider_state = "outage_observed" if domain == "recovery" else "not_contacted"
        recovery_state = "review_required_not_executed" if domain == "recovery" else "not_applicable"
        row = create_soak_interval(
            soak_id=plan["soak_id"],
            interval_id=f"soak-interval-{index:04d}",
            domain=domain,
            sequence=index,
            session_index=index // 3,
            day_index=index // 3,
            cycle_start=index * 10,
            cycle_end=index * 10 + 10,
            elapsed_seconds=600 + index,
            observed_latency_ms=100 + index,
            observed_tokens=1_000 + index,
            observed_disk_bytes=100_000 + index,
            observed_memory_mb=512 + index,
            snapshot_digest=snapshot,
            context_digest=context,
            artifact_digest=_h(f"{domain}:artifact"),
            receipt_digest=_h(f"{domain}:receipt"),
            previous_interval_digest=previous,
            purpose_code="bounded_soak_observation",
            progress_state="progress_observed",
            interruption_state=interruption_state,
            restart_state=restart_state,
            provider_state=provider_state,
            recovery_state=recovery_state,
        )
        rows.append(row)
        previous = row["interval_digest"]
    verification = {
        "content_free": True,
        "current_regressions_separate": True,
        "inherited_debt_visible": True,
        "global_profile_pass_claimed": False,
    }
    return plan, rows, snapshot, context, verification


def _resign_interval(row: dict[str, Any]) -> None:
    from long_session_multi_day_soak import _digest

    row.pop("interval_digest", None)
    row["interval_digest"] = _digest(row)


def _resign_plan(row: dict[str, Any]) -> None:
    from long_session_multi_day_soak import _digest

    row.pop("plan_digest", None)
    row["plan_digest"] = _digest(row)


def build_long_session_multi_day_soak_checkpoint(
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

    plan, rows, snapshot, context, verification = _case()
    report = assess_soak_evidence(
        plan,
        rows,
        current_snapshot_digest=snapshot,
        current_context_digest=context,
        verification_summary=verification,
    )
    summary = public_soak_summary(report)
    for value in (
        report["status"] == "ready_for_operator_review",
        report["errors"] == [],
        report["content_free"] is True,
        report["read_only"] is True,
        summary["soak_mode"] == "multi_day",
        summary["interval_count"] == 9,
        summary["domain_count"] == 9,
        summary["session_count"] == 3,
        summary["day_count"] == 3,
        summary["cycle_count"] == 90,
        summary["foreground_path_available"] is True,
        summary["latency_within_budget"] is True,
        summary["resource_budgets_within_bounds"] is True,
        summary["progress_observed"] is True,
        summary["exact_lineage_verified"] is True,
        summary["original_evidence_preserved"] is True,
        summary["current_regressions_separate"] is True,
        summary["inherited_debt_visible"] is True,
        summary["actual_waiting_started"] is False,
        summary["automatic_continuation"] is False,
        summary["execution_invoked"] is False,
        summary["cancellation_executed"] is False,
        summary["recovery_executed"] is False,
        summary["provider_contacted"] is False,
        summary["model_contacted"] is False,
        summary["thread_started"] is False,
        summary["process_started"] is False,
        summary["global_profile_pass_claimed"] is False,
        summary["authority_granted"] is False,
        len(summary["soak_digest"]) == 64,
    ):
        require(value)

    blocked: dict[str, dict[str, Any]] = {}

    def case(name: str, mutation: Any) -> None:
        plan_copy = dict(plan)
        row_copy = [dict(row) for row in rows]
        verification_copy = dict(verification)
        mutation(plan_copy, row_copy, verification_copy)
        blocked[name] = assess_soak_evidence(
            plan_copy,
            row_copy,
            current_snapshot_digest=snapshot,
            current_context_digest=context,
            verification_summary=verification_copy,
        )

    case("duplicate-id", lambda p, r, v: r[1].__setitem__("interval_id", r[0]["interval_id"]))
    case("duplicate-sequence", lambda p, r, v: r[1].__setitem__("sequence", 0))
    case("broken-lineage", lambda p, r, v: (r[1].__setitem__("previous_interval_digest", _h("broken")), _resign_interval(r[1])))
    case("stale-snapshot", lambda p, r, v: (r[0].__setitem__("snapshot_digest", _h("stale")), _resign_interval(r[0])))
    case("stale-context", lambda p, r, v: (r[0].__setitem__("context_digest", _h("stale")), _resign_interval(r[0])))
    case("unsupported-domain", lambda p, r, v: (r[0].__setitem__("domain", "unknown"), _resign_interval(r[0])))
    case("unsupported-state", lambda p, r, v: (r[0].__setitem__("lifecycle_state", "running"), _resign_interval(r[0])))
    case("malformed-digest", lambda p, r, v: (r[0].__setitem__("artifact_digest", "bad"), _resign_interval(r[0])))
    case("oversized", lambda p, r, v: (p.__setitem__("max_intervals", 8), _resign_plan(p)))
    case("elapsed-budget", lambda p, r, v: (p.__setitem__("max_elapsed_seconds", 100), _resign_plan(p)))
    case("cycle-budget", lambda p, r, v: (p.__setitem__("max_cycles", 10), _resign_plan(p)))
    case("latency-budget", lambda p, r, v: (p.__setitem__("foreground_latency_budget_ms", 50), _resign_plan(p)))
    case("token-budget", lambda p, r, v: (p.__setitem__("token_budget", 100), _resign_plan(p)))
    case("disk-budget", lambda p, r, v: (p.__setitem__("disk_budget_bytes", 10), _resign_plan(p)))
    case("memory-budget", lambda p, r, v: (p.__setitem__("memory_budget_mb", 10), _resign_plan(p)))
    case("duplicate-cycle", lambda p, r, v: (r[1].__setitem__("cycle_start", r[0]["cycle_start"]), r[1].__setitem__("cycle_end", r[0]["cycle_end"]), _resign_interval(r[1])))
    case("stalled-progress", lambda p, r, v: (r[0].__setitem__("progress_state", "stalled"), _resign_interval(r[0])))
    case("private-field", lambda p, r, v: (r[0].__setitem__("prompt", "private"), _resign_interval(r[0])))
    case("hidden-wait", lambda p, r, v: (r[0].__setitem__("actual_waiting_started", True), _resign_interval(r[0])))
    case("automatic-continuation", lambda p, r, v: (r[0].__setitem__("automatic_continuation", True), _resign_interval(r[0])))
    case("hidden-execution", lambda p, r, v: (r[0].__setitem__("execution_invoked", True), _resign_interval(r[0])))
    case("cancellation", lambda p, r, v: (r[0].__setitem__("cancellation_executed", True), _resign_interval(r[0])))
    case("recovery", lambda p, r, v: (r[0].__setitem__("recovery_executed", True), _resign_interval(r[0])))
    case("provider-contact", lambda p, r, v: (r[0].__setitem__("provider_contacted", True), _resign_interval(r[0])))
    case("thread-start", lambda p, r, v: (r[0].__setitem__("thread_started", True), _resign_interval(r[0])))
    case("runtime-mutation", lambda p, r, v: (r[0].__setitem__("runtime_mutated", True), _resign_interval(r[0])))
    case("authority", lambda p, r, v: (r[0].__setitem__("authority_state", "granted"), _resign_interval(r[0])))
    case("global-pass", lambda p, r, v: v.__setitem__("global_profile_pass_claimed", True))
    case("tamper", lambda p, r, v: r[0].__setitem__("purpose_code", "tampered"))

    for blocked_report in blocked.values():
        require(blocked_report["status"] == "blocked")
        require(blocked_report["error_count"] > 0)
        require(blocked_report["actual_waiting_started"] is False)
        require(blocked_report["execution_invoked"] is False)
        require(blocked_report["runtime_mutated"] is False)
        require(blocked_report["authority_granted"] is False)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry["checkpoints"] if row["checkpoint_id"] == _CHECKPOINT_ID),
        None,
    )
    require(descriptor is not None)
    require((descriptor or {}).get("builder") == "build_long_session_multi_day_soak_checkpoint")
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require(not registry["duplicate_checkpoint_ids"])
    require(not registry["duplicate_builder_targets"])

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)

    return {
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "long-session-multi-day-soak:v1195.2",
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "summary": summary,
        "blocked_cases": {name: item["errors"] for name, item in blocked.items()},
        "limitations": list(_LIMITATIONS),
        "source_unchanged": before_digest == after_digest,
        "runtime_mutated": False,
        "production_source_modified": False,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "approval_created": False,
        "approval_consumed": False,
        "execution_invoked": False,
        "cancellation_executed": False,
        "recovery_executed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
    }
