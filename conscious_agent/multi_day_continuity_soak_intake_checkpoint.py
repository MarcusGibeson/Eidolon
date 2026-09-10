from __future__ import annotations

"""Strictly read-only v1144.2 Multi-Day Continuity Soak Intake checkpoint."""

import hashlib
import os
from pathlib import Path

from continuity_soak_campaign_candidates import ACTIONS, build_continuity_soak_campaign_candidate_inspection
from continuity_soak_eligibility import MAX_DURATION_DAYS, MAX_OBSERVATION_INTERVAL_MINUTES, MIN_DURATION_DAYS, MIN_OBSERVATION_INTERVAL_MINUTES, SOAK_SCENARIOS, build_continuity_soak_eligibility_inspection
from workload_budget_eligibility import WORKLOAD_KINDS

CONTRACT_VERSION = "v1144.2"


def _root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(
            candidate
            for candidate in root.rglob("*")
            if candidate.is_file()
            and candidate.suffix not in {".pyc", ".pyo"}
            and "__pycache__" not in candidate.parts
        ):
            stat = path.stat()
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
    return digest.hexdigest()


def build_multi_day_continuity_soak_intake_checkpoint(
    runtime_root: Path | str | None = None,
    *,
    source_root: Path | str | None = None,
) -> dict[str, object]:
    runtime = Path(runtime_root).resolve() if runtime_root else _root()
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    eligibility = build_continuity_soak_eligibility_inspection(runtime)
    campaigns = build_continuity_soak_campaign_candidate_inspection(runtime)
    eligibility_rows = eligibility.get("recent_records", [])
    campaign_rows = campaigns.get("recent_records", [])

    checks = [
        ("eligibility_contract", eligibility.get("contract_version") == "v1144.0"),
        ("campaign_contract", campaigns.get("contract_version") == "v1144.1"),
        ("complete_scenario_taxonomy", set(eligibility.get("recognized_scenarios", [])) == SOAK_SCENARIOS),
        ("complete_workload_taxonomy", set(eligibility.get("recognized_workload_kinds", [])) == WORKLOAD_KINDS),
        (
            "bounded_multi_day_duration",
            eligibility.get("duration_bounds_days") == [MIN_DURATION_DAYS, MAX_DURATION_DAYS]
            and all(
                MIN_DURATION_DAYS <= int(row.get("duration_days") or 0) <= MAX_DURATION_DAYS
                for row in eligibility_rows
                if row.get("state") == "eligible"
            ),
        ),
        (
            "bounded_observation_interval",
            eligibility.get("observation_interval_bounds_minutes")
            == [MIN_OBSERVATION_INTERVAL_MINUTES, MAX_OBSERVATION_INTERVAL_MINUTES]
            and all(
                MIN_OBSERVATION_INTERVAL_MINUTES
                <= int(row.get("observation_interval_minutes") or 0)
                <= MAX_OBSERVATION_INTERVAL_MINUTES
                for row in eligibility_rows
                if row.get("state") == "eligible"
            ),
        ),
        (
            "exact_profile_binding",
            all(
                row.get("baseline_checkpoint_digest")
                and row.get("runtime_profile_digest")
                and row.get("provider_profile_digest")
                for row in eligibility_rows + campaign_rows
            ),
        ),
        (
            "exact_workload_lineage",
            all(
                row.get("workload_eligibility_ids")
                and set(row.get("workload_kinds") or []) == WORKLOAD_KINDS
                for row in eligibility_rows + campaign_rows
                if row.get("state") in {"eligible", "requires_operator_review", "planned"}
            ),
        ),
        (
            "exact_campaign_lineage",
            all(row.get("eligibility_id") and row.get("soak_scope_id") for row in campaign_rows),
        ),
        (
            "exact_scenario_manifest",
            all(
                row.get("scenario_sequence") == sorted(SOAK_SCENARIOS)
                for row in campaign_rows
                if row.get("state") in {"requires_operator_review", "planned"}
            ),
        ),
        (
            "bounded_injection_and_recovery_profiles",
            all(
                all(
                    int(row.get(key) or 0) > 0
                    for key in (
                        "planned_sleep_cycles",
                        "planned_restart_count",
                        "planned_interruption_count",
                        "planned_provider_outage_count",
                        "max_provider_outage_minutes",
                        "stale_work_threshold_minutes",
                    )
                )
                for row in campaign_rows
                if row.get("state") in {"requires_operator_review", "planned"}
            ),
        ),
        ("recognized_campaign_actions", all(row.get("campaign_action") in ACTIONS for row in campaign_rows)),
        (
            "operator_confirmation_required",
            all(row.get("operator_review_required") for row in campaign_rows if row.get("state") == "requires_operator_review"),
        ),
        (
            "no_launch_authority",
            not campaigns.get("operator_confirmation_recorded")
            and not campaigns.get("launch_authorized")
            and not campaigns.get("launch_token_issued")
            and all(
                not row.get("operator_confirmation_recorded")
                and not row.get("launch_authorized")
                and not row.get("launch_token_issued")
                for row in campaign_rows
            ),
        ),
        (
            "no_soak_or_fault_execution",
            not eligibility.get("soak_started")
            and not eligibility.get("fault_injection_started")
            and not campaigns.get("soak_started")
            and not campaigns.get("fault_injection_started")
            and all(not row.get("soak_started") and not row.get("fault_injection_started") for row in eligibility_rows + campaign_rows),
        ),
        ("lifecycle_visibility", all(row.get("state") and row.get("state_reason") for row in eligibility_rows + campaign_rows)),
        (
            "privacy",
            not eligibility.get("raw_content_exposed")
            and not eligibility.get("workload_payload_exposed")
            and not eligibility.get("provider_payload_exposed")
            and not eligibility.get("hidden_reasoning_exposed")
            and not campaigns.get("raw_content_exposed")
            and not campaigns.get("workload_payload_exposed")
            and not campaigns.get("provider_payload_exposed")
            and not campaigns.get("hidden_reasoning_exposed"),
        ),
        (
            "authority_separation",
            not any(eligibility.get("authority_boundary", {}).values())
            and not any(campaigns.get("authority_boundary", {}).values()),
        ),
        ("source_runtime_separation", runtime != source),
        ("desktop_verification_pending", True),
    ]

    passed = sum(bool(value) for _, value in checks)
    return {
        "ok": passed == len(checks),
        "status": "ready_for_desktop_verification" if passed == len(checks) else "review_required",
        "contract_version": CONTRACT_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": [
            {"id": identifier, "status": "pass" if value else "fail"}
            for identifier, value in checks
        ],
        "eligibility": eligibility,
        "campaigns": campaigns,
        "summary": {
            "eligibility_record_count": int(eligibility.get("record_count") or 0),
            "campaign_candidate_count": int(campaigns.get("record_count") or 0),
            "recognized_scenario_count": len(SOAK_SCENARIOS),
            "recognized_workload_count": len(WORKLOAD_KINDS),
        },
        "runtime_mutated": runtime_before != _tree_signature(runtime),
        "source_modified": source_before != _tree_signature(source),
        "raw_content_exposed": False,
        "workload_payload_exposed": False,
        "provider_payload_exposed": False,
        "hidden_reasoning_exposed": False,
        "campaign_started": False,
        "fault_injection_started": False,
        "provider_contacted": False,
        "process_restarted": False,
        "work_interrupted": False,
        "work_resumed": False,
        "message_sent": False,
        "source_mutated": False,
        "approval_created": False,
        "authorization_created": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "eligibility_created_by_checkpoint": False,
        "campaign_created_by_checkpoint": False,
        "consciousness_proven": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
