from __future__ import annotations

"""v1254.6-v1254.8 reliability and operator-handoff inspection.

The execution engine owns mutation only inside disposable workspaces.  This
module is intentionally read-only: it validates persisted lineage, restart
state, source freshness, attempt/review integrity, and the permanent denial of
selected-project application authority.  Recovery execution remains owned by
the exact authorization path in :mod:`isolated_coding_execution`.
"""

import time
from pathlib import Path
from typing import Any, Mapping

from isolated_coding_execution import (
    _attempt_path,
    _execution_path,
    _review_path,
    _strict_workspace_integrity,
    _valid,
    load_isolated_coding_execution,
    load_isolated_coding_review,
    public_isolated_coding_execution,
    public_isolated_coding_review,
)
from isolated_coding_execution_foundations import (
    AUTHORITY_STATE,
    check_coding_source_freshness,
    load_coding_project_inspection,
    load_coding_work_plan,
    load_coding_work_request,
)
from ordinary_chat_development_campaign import _digest, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1254.8"


def inspect_isolated_coding_execution_health(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
    plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    workspace_record = _read_json(_store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json")
    review = load_isolated_coding_review(request_id, runtime_root=runtime_root)

    errors: list[str] = []
    if not request:
        errors.append("request_missing_or_invalid")
    if not inspection:
        errors.append("inspection_missing_or_invalid")
    if not plan:
        errors.append("plan_missing_or_invalid")
    if not execution:
        errors.append("execution_missing_or_invalid")

    workspace_present = False
    workspace_integrity = "workspace_not_materialized"
    if workspace_record:
        raw = str(workspace_record.get("workspace_path") or "")
        if raw:
            try:
                root = Path(raw).resolve(strict=True)
                workspace_present = root.is_dir()
                ok, workspace_integrity = _strict_workspace_integrity(root)
                if not ok:
                    errors.append(workspace_integrity)
            except OSError:
                workspace_integrity = "workspace_unavailable"
                errors.append(workspace_integrity)
        elif workspace_record.get("workspace_cleaned"):
            workspace_integrity = "workspace_cleaned"

    phase = str(execution.get("phase") or "")
    lease_expired = bool(phase == "running" and float(execution.get("lease_expires_unix") or 0.0) <= time.time())
    lease_active = bool(phase == "running" and not lease_expired)
    if phase == "running" and not str(execution.get("lease_token") or ""):
        errors.append("running_execution_lease_missing")

    attempt_count = int(execution.get("attempt_count") or 0)
    result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
    if phase == "sealed":
        attempt_count = int(result.get("attempt_count") or attempt_count)
    attempt_valid_count = 0
    for number in range(1, attempt_count + 1):
        attempt = _read_json(_attempt_path(request_id, number, runtime_root))
        if attempt and _valid(attempt, "attempt_record_digest"):
            attempt_valid_count += 1
        else:
            errors.append(f"attempt_{number}_missing_or_invalid")

    review_valid = bool(review)
    if phase == "sealed" and result.get("reviewable_diff_available") and not review_valid:
        errors.append("review_missing_or_invalid")

    freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root) if request and inspection else {"ok": False, "status": "source_freshness_unavailable"}
    if execution and phase == "running":
        # A consumed, exact authorization may temporarily grant only the bounded
        # execution/provider/test authorities needed by this disposable run.
        # Application/install/release/permanent/independent authority must remain
        # denied even while recovering a running lease.
        transient_keys = {"implementation_execution_authorized", "command_execution_authorized", "provider_contact_authorized", "test_execution_authorized"}
        authority_denied = all(
            execution.get(key) is expected
            for key, expected in AUTHORITY_STATE.items()
            if key not in transient_keys
        )
    else:
        authority_denied = all(execution.get(key) is expected for key, expected in AUTHORITY_STATE.items()) if execution else True
    if execution and not authority_denied:
        errors.append("authority_boundary_invalid")
    application_denied = all(
        not bool((result or execution).get(key))
        for key in (
            "source_application_authorized", "installation_authorized", "release_authorized",
            "permanent_approval_granted", "independent_authority_granted",
        )
    )
    if not application_denied:
        errors.append("application_authority_boundary_invalid")

    if phase == "sealed":
        recovery_disposition = "terminal_review_available"
    elif lease_active:
        recovery_disposition = "execution_in_progress_do_not_duplicate"
    elif lease_expired:
        recovery_disposition = "same_exact_authorization_may_recover"
    elif phase == "prepared":
        recovery_disposition = "exact_execution_authorization_required"
    else:
        recovery_disposition = "manual_review_required"

    row = {
        "ok": not errors,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "isolated_coding_execution_healthy" if not errors else "isolated_coding_execution_health_blocked",
        "request_id": request_id,
        "phase": phase,
        "execution_status": str(execution.get("status") or ""),
        "attempt_count": attempt_count,
        "attempt_valid_count": attempt_valid_count,
        "review_valid": review_valid,
        "workspace_present": workspace_present,
        "workspace_integrity": workspace_integrity,
        "source_fresh": bool(freshness.get("ok")),
        "source_freshness_status": str(freshness.get("status") or ""),
        "lease_active": lease_active,
        "lease_expired": lease_expired,
        "recovery_disposition": recovery_disposition,
        "authority_denied": authority_denied,
        "application_authority_denied": application_denied,
        "errors": errors,
        "selected_project_modified": False,
        "source_modified": False,
        "provider_contacted_by_inspection": False,
        "tests_executed_by_inspection": False,
        "recovery_executed_by_inspection": False,
        "read_only": True,
    }
    row["health_digest"] = _digest(row)
    return row


def build_isolated_coding_operator_handoff(request_id: str, *, runtime_root=None, include_diff: bool = True) -> dict[str, Any]:
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    review = load_isolated_coding_review(request_id, runtime_root=runtime_root)
    health = inspect_isolated_coding_execution_health(request_id, runtime_root=runtime_root)
    if not execution:
        return {
            "ok": False,
            "status": "isolated_coding_operator_handoff_unavailable",
            "request_id": request_id,
            "reason": "execution_missing_or_invalid",
            "selected_project_modified": False,
            "source_application_authorized": False,
            "release_authorized": False,
        }
    public_execution = public_isolated_coding_execution(execution)
    public_review = public_isolated_coding_review(review, include_diff=include_diff) if review else {}
    result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
    limitations = [
        "The candidate exists only in the disposable workspace; the selected project has not been modified.",
        "Application, installation, release, permanent approval, and independent authority remain denied.",
        "Dependency installation and unrestricted shell execution are not part of v1254.",
    ]
    if not health.get("source_fresh"):
        limitations.append("The selected-project source snapshot is stale; do not apply this candidate without re-inspection and conflict handling.")
    if not public_execution.get("test_passed"):
        limitations.append("Bounded verification is not passing; the result is reviewable evidence, not a successful candidate.")
    row = {
        "ok": bool(result.get("ok")) and bool(review) and bool(health.get("application_authority_denied")),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "isolated_coding_operator_handoff_ready" if review else "isolated_coding_operator_handoff_incomplete",
        "request_id": request_id,
        "execution": public_execution,
        "review": public_review,
        "health": {
            "status": health.get("status"),
            "source_fresh": health.get("source_fresh"),
            "workspace_integrity": health.get("workspace_integrity"),
            "recovery_disposition": health.get("recovery_disposition"),
            "health_digest": health.get("health_digest"),
        },
        "limitations": limitations,
        "operator_decision_required": True,
        "next_authority_stage": "v1255-controlled-application-and-rollback",
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "installation_authorized": False,
        "release_authorized": False,
        "permanent_approval_granted": False,
        "independent_authority_granted": False,
    }
    row["handoff_digest"] = _digest(row)
    return row


__all__ = [
    "CONTRACT_VERSION",
    "inspect_isolated_coding_execution_health",
    "build_isolated_coding_operator_handoff",
]
