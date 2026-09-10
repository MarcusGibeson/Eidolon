from __future__ import annotations

"""v1144.0 durable, content-free multi-day continuity soak eligibility.

Eligibility is preparatory. It binds a proposed soak to the exact v1143 workload
budget records, bounded scenario coverage, a source checkpoint digest, and
runtime/provider profile digests. It cannot start a soak, inject faults, contact
a provider, restart a process, or mutate cognition/conversation/development
state.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
from typing import Any, Callable

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from workload_budget_eligibility import WorkloadBudgetEligibilityStore, WORKLOAD_KINDS

CONTRACT_VERSION = "v1144.0"
SCHEMA_VERSION = "1"
SOAK_SCENARIOS = {
    "sleep",
    "restart",
    "interruption",
    "provider_outage",
    "stale_work",
    "recovery",
}
MIN_DURATION_DAYS = 2
MAX_DURATION_DAYS = 30
MIN_OBSERVATION_INTERVAL_MINUTES = 5
MAX_OBSERVATION_INTERVAL_MINUTES = 1440
STATES = {
    "eligible",
    "awaiting_baseline",
    "awaiting_profile",
    "awaiting_scenario_coverage",
    "awaiting_workload_lineage",
    "awaiting_prerequisite",
    "suppressed",
    "expired",
    "superseded",
    "retracted",
    "retired",
}
AUTHORITY_KEYS = (
    "can_start_soak",
    "can_schedule",
    "can_inject_fault",
    "can_sleep_process",
    "can_restart_process",
    "can_interrupt_work",
    "can_contact_provider",
    "can_change_provider",
    "can_resume_work",
    "can_send_message",
    "can_modify_source",
    "can_approve",
    "can_authorize",
    "can_install",
    "can_promote",
    "can_certify",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[:limit]


def _digest(*parts: Any) -> str:
    return hashlib.sha256(
        "\x1f".join(_clean(part, 4000) for part in parts).encode("utf-8")
    ).hexdigest()


def _validated_digest(value: Any) -> str:
    token = _clean(value, 64).lower()
    return token if _HEX64.fullmatch(token) else ""


def _root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "records": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {key: False for key in AUTHORITY_KEYS},
    }


class ContinuitySoakEligibilityStore:
    def __init__(
        self,
        runtime_root: Path | str | None = None,
        *,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else _root()
        self.path = self.runtime_root / "continuity_soak_eligibility.json"
        self.clock = clock or _now
        self.workload_eligibility = WorkloadBudgetEligibilityStore(self.runtime_root)

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def register(
        self,
        event_id: str,
        *,
        soak_scope_id: str,
        baseline_checkpoint_digest: str,
        runtime_profile_digest: str,
        provider_profile_digest: str,
        workload_eligibility_ids: list[str],
        scenario_ids: list[str],
        duration_days: int,
        observation_interval_minutes: int,
        prerequisite_ids: list[str] | None = None,
        validity_window_id: str = "",
        contradiction_ids: list[str] | None = None,
        retraction_ids: list[str] | None = None,
        supersession_ids: list[str] | None = None,
        retirement_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        soak_scope_id = _clean(soak_scope_id)
        if not event_id or not soak_scope_id:
            raise ValueError("bounded event and soak scope required")

        baseline_digest = _validated_digest(baseline_checkpoint_digest)
        runtime_digest = _validated_digest(runtime_profile_digest)
        provider_digest = _validated_digest(provider_profile_digest)
        workloads = sorted({_clean(value) for value in workload_eligibility_ids if _clean(value)})
        scenarios = sorted({_clean(value, 80) for value in scenario_ids if _clean(value, 80)})
        unknown_scenarios = sorted(set(scenarios) - SOAK_SCENARIOS)
        if unknown_scenarios:
            raise ValueError("unrecognized continuity soak scenario")

        days = max(0, int(duration_days))
        interval = max(0, int(observation_interval_minutes))
        prerequisites = sorted({_clean(value) for value in prerequisite_ids or [] if _clean(value)})
        contradictions = sorted({_clean(value) for value in contradiction_ids or [] if _clean(value)})
        retractions = sorted({_clean(value) for value in retraction_ids or [] if _clean(value)})
        supersessions = sorted({_clean(value) for value in supersession_ids or [] if _clean(value)})
        retirements = sorted({_clean(value) for value in retirement_ids or [] if _clean(value)})

        workload_rows = {
            row.get("eligibility_id"): row
            for row in self.workload_eligibility.snapshot().get("records", [])
        }
        exact_rows = [workload_rows.get(identifier) for identifier in workloads]
        workload_kinds = {row.get("workload_kind") for row in exact_rows if row}
        exact_workload_lineage = bool(workloads) and all(
            row and row.get("state") == "eligible" for row in exact_rows
        )
        complete_workload_coverage = workload_kinds == WORKLOAD_KINDS

        state = "eligible"
        reason = "bounded_multi_day_soak_profile"
        if retirements:
            state, reason = "retired", "retirement_lineage"
        elif retractions:
            state, reason = "retracted", "retraction_lineage"
        elif supersessions:
            state, reason = "superseded", "supersession_lineage"
        elif contradictions:
            state, reason = "suppressed", "contradictory_lineage"
        elif not baseline_digest:
            state, reason = "awaiting_baseline", "exact_checkpoint_digest_required"
        elif not runtime_digest or not provider_digest:
            state, reason = "awaiting_profile", "runtime_and_provider_profile_digests_required"
        elif set(scenarios) != SOAK_SCENARIOS:
            state, reason = "awaiting_scenario_coverage", "all_continuity_scenarios_required"
        elif not exact_workload_lineage or not complete_workload_coverage:
            state, reason = "awaiting_workload_lineage", "exact_v1143_workload_coverage_required"
        elif not MIN_DURATION_DAYS <= days <= MAX_DURATION_DAYS:
            state, reason = "suppressed", "bounded_multi_day_duration_required"
        elif not MIN_OBSERVATION_INTERVAL_MINUTES <= interval <= MAX_OBSERVATION_INTERVAL_MINUTES:
            state, reason = "suppressed", "bounded_observation_interval_required"
        elif prerequisites:
            state, reason = "awaiting_prerequisite", "prerequisites_unresolved"

        structural_digest = _digest(
            soak_scope_id,
            baseline_digest,
            runtime_digest,
            provider_digest,
            *workloads,
            *scenarios,
            days,
            interval,
            *prerequisites,
            validity_window_id,
            *contradictions,
            *retractions,
            *supersessions,
            *retirements,
        )

        with metadata_mutation_lock(self.path, timeout_seconds=5):
            persisted = self._load()
            prior = next(
                (row for row in persisted["processed_events"] if row.get("event_id") == event_id),
                None,
            )
            if prior:
                return {"ok": True, **deepcopy(prior["result"]), "idempotent": True}

            duplicate = next(
                (
                    row
                    for row in persisted["records"]
                    if row.get("structural_digest") == structural_digest
                    and row.get("state")
                    in {
                        "eligible",
                        "awaiting_baseline",
                        "awaiting_profile",
                        "awaiting_scenario_coverage",
                        "awaiting_workload_lineage",
                        "awaiting_prerequisite",
                    }
                ),
                None,
            )
            if duplicate:
                result = {
                    "status": "duplicate_suppressed",
                    "eligibility_id": duplicate["eligibility_id"],
                    "state": "suppressed",
                }
            else:
                now = self.clock()
                eligibility_id = f"continuity-soak-eligibility-{structural_digest[:24]}"
                total_budgets = {
                    "cpu_budget_ms": sum(int((row or {}).get("cpu_budget_ms") or 0) for row in exact_rows),
                    "memory_budget_mb": sum(int((row or {}).get("memory_budget_mb") or 0) for row in exact_rows),
                    "latency_budget_ms": sum(int((row or {}).get("latency_budget_ms") or 0) for row in exact_rows),
                    "token_budget": sum(int((row or {}).get("token_budget") or 0) for row in exact_rows),
                }
                row = {
                    "eligibility_id": eligibility_id,
                    "soak_scope_id": soak_scope_id,
                    "baseline_checkpoint_digest": baseline_digest,
                    "runtime_profile_digest": runtime_digest,
                    "provider_profile_digest": provider_digest,
                    "workload_eligibility_ids": workloads,
                    "workload_kinds": sorted(workload_kinds),
                    "scenario_ids": scenarios,
                    "duration_days": days,
                    "observation_interval_minutes": interval,
                    "minimum_observation_count": (days * 24 * 60) // interval if interval else 0,
                    "aggregate_budget": total_budgets,
                    "prerequisite_ids": prerequisites,
                    "validity_window_id": _clean(validity_window_id),
                    "contradiction_ids": contradictions,
                    "retraction_ids": retractions,
                    "supersession_ids": supersessions,
                    "retirement_ids": retirements,
                    "state": state,
                    "state_reason": reason,
                    "structural_digest": structural_digest,
                    "content_free": True,
                    "soak_started": False,
                    "fault_injection_started": False,
                    "created_at": now,
                    "history": [
                        {
                            "change": "recorded",
                            "state": state,
                            "occurred_at": now,
                            "content_free": True,
                        }
                    ],
                }
                persisted["records"].append(row)
                result = {
                    "status": "eligibility_recorded",
                    "eligibility_id": eligibility_id,
                    "state": state,
                }

            now = self.clock()
            persisted["processed_events"].append(
                {
                    "event_id": event_id,
                    "event_digest": _digest(event_id),
                    "occurred_at": now,
                    "result": deepcopy(result),
                    "content_free": True,
                }
            )
            persisted["revision"] += 1
            persisted["updated_at"] = now
            write_json_atomic(self.path, persisted, expected_type=dict, sort_keys=True)
            return {"ok": True, **result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        counts: dict[str, int] = {}
        for row in state["records"]:
            counts[row.get("state")] = counts.get(row.get("state"), 0) + 1
        keys = (
            "eligibility_id",
            "soak_scope_id",
            "baseline_checkpoint_digest",
            "runtime_profile_digest",
            "provider_profile_digest",
            "workload_eligibility_ids",
            "workload_kinds",
            "scenario_ids",
            "duration_days",
            "observation_interval_minutes",
            "minimum_observation_count",
            "aggregate_budget",
            "prerequisite_ids",
            "validity_window_id",
            "state",
            "state_reason",
            "structural_digest",
            "soak_started",
            "fault_injection_started",
        )
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "record_count": len(state["records"]),
            "state_counts": counts,
            "recent_records": [
                {key: row.get(key) for key in keys} for row in state["records"][-32:]
            ],
            "recognized_scenarios": sorted(SOAK_SCENARIOS),
            "recognized_workload_kinds": sorted(WORKLOAD_KINDS),
            "duration_bounds_days": [MIN_DURATION_DAYS, MAX_DURATION_DAYS],
            "observation_interval_bounds_minutes": [
                MIN_OBSERVATION_INTERVAL_MINUTES,
                MAX_OBSERVATION_INTERVAL_MINUTES,
            ],
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "raw_content_exposed": False,
            "workload_payload_exposed": False,
            "provider_payload_exposed": False,
            "hidden_reasoning_exposed": False,
            "soak_started": False,
            "fault_injection_started": False,
        }


def build_continuity_soak_eligibility_inspection(
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    return ContinuitySoakEligibilityStore(runtime_root).inspection_summary()
