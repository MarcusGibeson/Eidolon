from __future__ import annotations

"""v1144.1 governed, content-free multi-day continuity soak campaign candidates.

Candidates describe a bounded operator-reviewable campaign. They do not launch
it, create schedules, inject outages, restart processes, interrupt workloads,
or contact providers.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable

from continuity_soak_eligibility import ContinuitySoakEligibilityStore, SOAK_SCENARIOS
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1144.1"
SCHEMA_VERSION = "1"
ACTIONS = {"prepare", "defer", "require_operator_review", "no_action"}
STATES = {
    "planned",
    "deferred",
    "awaiting_eligibility",
    "awaiting_prerequisite",
    "requires_operator_review",
    "suppressed",
    "expired",
    "superseded",
    "retracted",
    "retired",
}
AUTHORITY_KEYS = (
    "can_launch_campaign",
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[:limit]


def _digest(*parts: Any) -> str:
    return hashlib.sha256(
        "\x1f".join(_clean(part, 4000) for part in parts).encode("utf-8")
    ).hexdigest()


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
        "candidates": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {key: False for key in AUTHORITY_KEYS},
    }


class ContinuitySoakCampaignCandidateStore:
    def __init__(
        self,
        runtime_root: Path | str | None = None,
        *,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else _root()
        self.path = self.runtime_root / "continuity_soak_campaign_candidates.json"
        self.clock = clock or _now
        self.eligibility = ContinuitySoakEligibilityStore(self.runtime_root)

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
        eligibility_id: str,
        campaign_action: str,
        campaign_group_id: str,
        observation_profile_id: str,
        recovery_profile_id: str,
        scenario_sequence: list[str],
        planned_sleep_cycles: int,
        planned_restart_count: int,
        planned_interruption_count: int,
        planned_provider_outage_count: int,
        max_provider_outage_minutes: int,
        stale_work_threshold_minutes: int,
        operator_review_required: bool = True,
        prerequisite_ids: list[str] | None = None,
        validity_window_id: str = "",
        contradiction_ids: list[str] | None = None,
        retraction_ids: list[str] | None = None,
        supersession_ids: list[str] | None = None,
        retirement_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        campaign_action = _clean(campaign_action, 80)
        campaign_group_id = _clean(campaign_group_id)
        observation_profile_id = _clean(observation_profile_id)
        recovery_profile_id = _clean(recovery_profile_id)
        if (
            not event_id
            or campaign_action not in ACTIONS
            or not campaign_group_id
            or not observation_profile_id
            or not recovery_profile_id
        ):
            raise ValueError("bounded event, action, group, observation, and recovery profiles required")

        eligibility = next(
            (
                row
                for row in self.eligibility.snapshot().get("records", [])
                if row.get("eligibility_id") == eligibility_id
            ),
            None,
        )
        if not eligibility:
            raise ValueError("exact v1144.0 eligibility required")

        scenarios = [_clean(value, 80) for value in scenario_sequence if _clean(value, 80)]
        if set(scenarios) - SOAK_SCENARIOS:
            raise ValueError("unrecognized continuity soak scenario")
        counts = {
            "planned_sleep_cycles": max(0, int(planned_sleep_cycles)),
            "planned_restart_count": max(0, int(planned_restart_count)),
            "planned_interruption_count": max(0, int(planned_interruption_count)),
            "planned_provider_outage_count": max(0, int(planned_provider_outage_count)),
            "max_provider_outage_minutes": max(0, int(max_provider_outage_minutes)),
            "stale_work_threshold_minutes": max(0, int(stale_work_threshold_minutes)),
        }
        prerequisites = sorted({_clean(value) for value in prerequisite_ids or [] if _clean(value)})
        contradictions = sorted({_clean(value) for value in contradiction_ids or [] if _clean(value)})
        retractions = sorted({_clean(value) for value in retraction_ids or [] if _clean(value)})
        supersessions = sorted({_clean(value) for value in supersession_ids or [] if _clean(value)})
        retirements = sorted({_clean(value) for value in retirement_ids or [] if _clean(value)})

        state = "planned"
        reason = "bounded_campaign_candidate"
        if retirements:
            state, reason = "retired", "retirement_lineage"
        elif retractions:
            state, reason = "retracted", "retraction_lineage"
        elif supersessions:
            state, reason = "superseded", "supersession_lineage"
        elif contradictions:
            state, reason = "suppressed", "contradictory_lineage"
        elif eligibility.get("state") != "eligible":
            state, reason = "awaiting_eligibility", "eligible_v1144_0_record_required"
        elif scenarios != eligibility.get("scenario_ids"):
            state, reason = "suppressed", "exact_scenario_manifest_required"
        elif any(value <= 0 for value in counts.values()):
            state, reason = "suppressed", "positive_bounded_injection_and_recovery_limits_required"
        elif prerequisites:
            state, reason = "awaiting_prerequisite", "prerequisites_unresolved"
        elif campaign_action in {"defer", "no_action"}:
            state, reason = "deferred", "deliberate_non_launch"
        elif operator_review_required or campaign_action == "require_operator_review":
            state, reason = "requires_operator_review", "explicit_operator_confirmation_required"

        structural_digest = _digest(
            eligibility_id,
            campaign_action,
            campaign_group_id,
            observation_profile_id,
            recovery_profile_id,
            *scenarios,
            *counts.values(),
            operator_review_required,
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
                    for row in persisted["candidates"]
                    if row.get("structural_digest") == structural_digest
                    and row.get("state")
                    in {
                        "planned",
                        "deferred",
                        "awaiting_eligibility",
                        "awaiting_prerequisite",
                        "requires_operator_review",
                    }
                ),
                None,
            )
            if duplicate:
                result = {
                    "status": "duplicate_suppressed",
                    "campaign_id": duplicate["campaign_id"],
                    "state": "suppressed",
                }
            else:
                now = self.clock()
                campaign_id = f"continuity-soak-campaign-{structural_digest[:24]}"
                row = {
                    "campaign_id": campaign_id,
                    "eligibility_id": eligibility_id,
                    "soak_scope_id": eligibility.get("soak_scope_id"),
                    "baseline_checkpoint_digest": eligibility.get("baseline_checkpoint_digest"),
                    "runtime_profile_digest": eligibility.get("runtime_profile_digest"),
                    "provider_profile_digest": eligibility.get("provider_profile_digest"),
                    "workload_eligibility_ids": eligibility.get("workload_eligibility_ids", []),
                    "workload_kinds": eligibility.get("workload_kinds", []),
                    "duration_days": eligibility.get("duration_days"),
                    "observation_interval_minutes": eligibility.get("observation_interval_minutes"),
                    "minimum_observation_count": eligibility.get("minimum_observation_count"),
                    "aggregate_budget": eligibility.get("aggregate_budget", {}),
                    "campaign_action": campaign_action,
                    "campaign_group_id": campaign_group_id,
                    "observation_profile_id": observation_profile_id,
                    "recovery_profile_id": recovery_profile_id,
                    "scenario_sequence": scenarios,
                    **counts,
                    "operator_review_required": bool(operator_review_required),
                    "operator_confirmation_recorded": False,
                    "launch_authorized": False,
                    "launch_token_issued": False,
                    "soak_started": False,
                    "fault_injection_started": False,
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
                persisted["candidates"].append(row)
                result = {
                    "status": "campaign_candidate_recorded",
                    "campaign_id": campaign_id,
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
        for row in state["candidates"]:
            counts[row.get("state")] = counts.get(row.get("state"), 0) + 1
        keys = (
            "campaign_id",
            "eligibility_id",
            "soak_scope_id",
            "baseline_checkpoint_digest",
            "runtime_profile_digest",
            "provider_profile_digest",
            "workload_eligibility_ids",
            "workload_kinds",
            "duration_days",
            "observation_interval_minutes",
            "minimum_observation_count",
            "aggregate_budget",
            "campaign_action",
            "campaign_group_id",
            "observation_profile_id",
            "recovery_profile_id",
            "scenario_sequence",
            "planned_sleep_cycles",
            "planned_restart_count",
            "planned_interruption_count",
            "planned_provider_outage_count",
            "max_provider_outage_minutes",
            "stale_work_threshold_minutes",
            "operator_review_required",
            "operator_confirmation_recorded",
            "launch_authorized",
            "launch_token_issued",
            "soak_started",
            "fault_injection_started",
            "state",
            "state_reason",
            "structural_digest",
        )
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "record_count": len(state["candidates"]),
            "state_counts": counts,
            "recent_records": [
                {key: row.get(key) for key in keys} for row in state["candidates"][-32:]
            ],
            "recognized_actions": sorted(ACTIONS),
            "recognized_scenarios": sorted(SOAK_SCENARIOS),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "raw_content_exposed": False,
            "workload_payload_exposed": False,
            "provider_payload_exposed": False,
            "hidden_reasoning_exposed": False,
            "operator_confirmation_recorded": False,
            "launch_authorized": False,
            "launch_token_issued": False,
            "soak_started": False,
            "fault_injection_started": False,
        }


def build_continuity_soak_campaign_candidate_inspection(
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    return ContinuitySoakCampaignCandidateStore(runtime_root).inspection_summary()
