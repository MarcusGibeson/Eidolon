from __future__ import annotations

"""Execution-session authorization and bounded launch.

v1226 converts one accepted, current v1225 prepared execution session into one
single-use launch authorization and, only after the exact digest-bound operator
phrase, one active bounded execution-session record. Launch creates an external
runtime namespace and consumes the launch authorization exactly once. It does
not contact a provider, execute a command, run a test, materialize project
files, modify a project, write cognition, or grant any downstream step
authority.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from supervised_work_dispatch_execution_session_preparation import (
    _review_path as _prepared_review_path,
    _valid as _valid_v1225,
    inspect_prepared_development_execution_session,
    load_prepared_development_execution_session,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1226.8"
MAX_LAUNCH_AUTHORIZATIONS = 100
MAX_BOUNDED_EXECUTION_SESSIONS = 100

AUTHORITY_FLAGS = {
    "execution_session_launch_authorized": False,
    "execution_session_launched": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "background_execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "old_authority_reusable": False,
}

_PREPARE_AUTH = re.compile(
    r"^prepare bounded launch authorization for prepared development execution session "
    r"(?P<session>session_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_AUTHORIZE_LAUNCH = re.compile(
    r"^authorize bounded launch for prepared development execution session "
    r"(?P<session>session_[a-f0-9]{24}) digest (?P<session_digest>[a-f0-9]{64}) "
    r"authorization (?P<authorization>launch_auth_[a-f0-9]{24}) digest "
    r"(?P<authorization_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW = re.compile(r"^show bounded development execution sessions[.!?]*$", re.I)
_INSPECT = re.compile(
    r"^show bounded development execution session (?P<launch>launch_[a-f0-9]{24})[.!?]*$",
    re.I,
)


def _authorization_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "bounded_execution_session_launch_authorizations"


def _authorization_path(authorization_id: str, runtime_root=None) -> Path:
    return _authorization_root(runtime_root) / f"{authorization_id}.json"


def _authorization_consumption_path(authorization_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "bounded_execution_session_launch_authorization_consumptions" / f"{authorization_id}.json"


def _launch_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "bounded_development_execution_sessions"


def _launch_path(launch_id: str, runtime_root=None) -> Path:
    return _launch_root(runtime_root) / f"{launch_id}.json"


def _launch_snapshot_path(launch_id: str, generation: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "bounded_development_execution_session_snapshots" / launch_id / f"generation-{generation:06d}.json"


def _runtime_namespace_path(launch_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "bounded_development_execution_session_runtime" / launch_id


@contextmanager
def _lock(runtime_root=None):
    path = _store_root(runtime_root) / "locks" / "execution-session-authorization-bounded-launch.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for bounded-launch lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "single_use_launch_authorization_required": True,
        "prepared_session_review_preserved_as_authority_source": True,
        "bounded_launch_is_not_step_execution_authority": True,
        "fresh_step_authorization_required": True,
        "goal_alignment_review_required": True,
        "uncertainty_review_required": True,
        "outcome_reflection_required": True,
        "runtime_records_external": True,
        "operator_control_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_created": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_name_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        "cognition_written": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["execution_session_bounded_launch_result_digest"] = _digest(row)
    return row


def _load_accepted_prepared_session(session_id: str, expected_session_digest: str, runtime_root=None) -> tuple[dict[str, Any], dict[str, Any]]:
    session = inspect_prepared_development_execution_session(session_id, runtime_root=runtime_root)
    if session.get("ok") is not True:
        raise ValueError(str(session.get("reason") or "prepared_session_missing_or_stale"))
    if str(session.get("session_digest") or "") != str(expected_session_digest or ""):
        raise ValueError("stale_prepared_session_digest")
    review = _read_json(_prepared_review_path(str(session.get("session_id") or ""), runtime_root))
    if not review or not _valid_v1225(review, "prepared_execution_session_review_record_digest"):
        raise ValueError("accepted_prepared_session_review_required")
    if str(review.get("decision") or "") != "accept" or review.get("launch_readiness_established") is not True:
        raise ValueError("prepared_session_not_accepted")
    if review.get("execution_session_launch_authorized") is not False:
        raise ValueError("prepared_session_review_authority_boundary_invalid")
    requirements = dict(session.get("requirements") or {})
    required = (
        "fresh_isolated_workspace_required",
        "provider_plan_review_required",
        "test_plan_review_required",
        "risk_review_required",
        "rollback_plan_review_required",
        "execution_budget_review_required",
        "goal_alignment_review_required",
        "uncertainty_review_required",
        "outcome_reflection_required",
        "fresh_launch_authorization_required",
    )
    if not all(requirements.get(key) is True for key in required):
        raise ValueError("prepared_session_requirements_incomplete")
    return session, review


def _validate_authorization(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "bounded_launch_authorization_record_digest"):
        return False
    expected = _digest({
        "authorization_id": str(record.get("authorization_id") or ""),
        "source_session_id": str(record.get("source_session_id") or ""),
        "source_session_digest": str(record.get("source_session_digest") or ""),
        "source_prepared_review_digest": str(record.get("source_prepared_review_digest") or ""),
        "queue_item_id": str(record.get("queue_item_id") or ""),
        "project_reference": str(record.get("project_reference") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
    })
    return (
        str(record.get("authorization_digest") or "") == expected
        and str(record.get("authorization_id") or "").startswith("launch_auth_")
        and bool(record.get("source_session_id"))
        and record.get("authorization_consumed") is False
    )


def _validate_consumption(record: Mapping[str, Any]) -> bool:
    return (
        _valid(record, "bounded_launch_authorization_consumption_record_digest")
        and str(record.get("authorization_id") or "").startswith("launch_auth_")
        and str(record.get("launch_id") or "").startswith("launch_")
        and record.get("authorization_consumed") is True
    )


def _validate_launch(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "bounded_execution_session_launch_record_digest"):
        return False
    expected = _digest({
        "launch_id": str(record.get("launch_id") or ""),
        "generation": int(record.get("generation") or 0),
        "authorization_id": str(record.get("authorization_id") or ""),
        "authorization_digest": str(record.get("authorization_digest") or ""),
        "source_session_id": str(record.get("source_session_id") or ""),
        "source_session_digest": str(record.get("source_session_digest") or ""),
        "queue_item_id": str(record.get("queue_item_id") or ""),
        "project_reference": str(record.get("project_reference") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
        "launch_bounds_digest": str(record.get("launch_bounds_digest") or ""),
    })
    return (
        str(record.get("launch_digest") or "") == expected
        and str(record.get("launch_id") or "").startswith("launch_")
        and record.get("execution_session_launched") is True
        and record.get("execution_session_launch_authorized") is True
        and record.get("provider_execution_authorized") is False
        and record.get("command_execution_authorized") is False
        and record.get("project_mutation_authorized") is False
    )


def _authorization_rows(runtime_root=None) -> list[dict[str, Any]]:
    root = _authorization_root(runtime_root)
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("launch_auth_*.json"))[: MAX_LAUNCH_AUTHORIZATIONS + 1]:
        row = _read_json(path)
        if not row or not _validate_authorization(row) or path.stem != row.get("authorization_id"):
            raise ValueError("launch_authorization_tampered_or_malformed")
        rows.append(row)
    if len(rows) > MAX_LAUNCH_AUTHORIZATIONS:
        raise ValueError("launch_authorization_limit_exceeded")
    return rows


def _launch_rows(runtime_root=None) -> list[dict[str, Any]]:
    root = _launch_root(runtime_root)
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("launch_*.json"))[: MAX_BOUNDED_EXECUTION_SESSIONS + 1]:
        row = _read_json(path)
        if not row or not _validate_launch(row) or path.stem != row.get("launch_id"):
            raise ValueError("bounded_launch_tampered_or_malformed")
        rows.append(row)
    if len(rows) > MAX_BOUNDED_EXECUTION_SESSIONS:
        raise ValueError("bounded_launch_limit_exceeded")
    return rows


def prepare_bounded_launch_authorization(
    session_id: str,
    *,
    expected_session_digest: str,
    exact_phrase: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            session, review = _load_accepted_prepared_session(session_id, expected_session_digest, runtime_root)
            seed = _digest({
                "source_session_id": str(session.get("session_id") or ""),
                "source_session_digest": str(session.get("session_digest") or ""),
                "source_prepared_review_digest": str(review.get("prepared_execution_session_review_record_digest") or ""),
            })
            authorization_id = "launch_auth_" + seed[:24]
            path = _authorization_path(authorization_id, runtime_root)
            existing = _read_json(path)
            if existing:
                if not _validate_authorization(existing):
                    raise ValueError("launch_authorization_tampered_or_malformed")
                return {**existing, "operation_status": "resumed"}
            authorization_digest = _digest({
                "authorization_id": authorization_id,
                "source_session_id": str(session.get("session_id") or ""),
                "source_session_digest": str(session.get("session_digest") or ""),
                "source_prepared_review_digest": str(review.get("prepared_execution_session_review_record_digest") or ""),
                "queue_item_id": str(session.get("queue_item_id") or ""),
                "project_reference": str(session.get("project_reference") or ""),
                "proposal_id": str(session.get("proposal_id") or ""),
            })
            row = {
                "ok": True,
                "status": "bounded_execution_session_launch_authorization_ready",
                "authorization_id": authorization_id,
                "authorization_digest": authorization_digest,
                "source_session_id": str(session.get("session_id") or ""),
                "source_session_digest": str(session.get("session_digest") or ""),
                "source_prepared_review_digest": str(review.get("prepared_execution_session_review_record_digest") or ""),
                "source_schedule_digest": str(session.get("source_schedule_digest") or ""),
                "source_queue_digest": str(session.get("source_queue_digest") or ""),
                "queue_item_id": str(session.get("queue_item_id") or ""),
                "project_reference": str(session.get("project_reference") or ""),
                "proposal_id": str(session.get("proposal_id") or ""),
                "priority_rank": int(session.get("priority_rank") or 0),
                "priority_level": str(session.get("priority_level") or "normal"),
                "dependency_item_ids": list(session.get("dependency_item_ids") or []),
                "requirements_digest": str(session.get("requirements_digest") or ""),
                "authorization_consumed": False,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                "authorize_phrase": (
                    f"Authorize bounded launch for prepared development execution session "
                    f"{session.get('session_id')} digest {session.get('session_digest')} authorization "
                    f"{authorization_id} digest {authorization_digest}."
                ),
                **_base(),
            }
            row = _sealed(row, "bounded_launch_authorization_record_digest")
            _atomic_json(path, row)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("bounded_execution_session_launch_authorization_blocked", str(exc))


def load_bounded_launch_authorization(authorization_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_authorization_path(str(authorization_id or "").lower(), runtime_root))
    return row if row and _validate_authorization(row) else {}


def inspect_bounded_launch_authorization(authorization_id: str, *, runtime_root=None) -> dict[str, Any]:
    try:
        row = load_bounded_launch_authorization(authorization_id, runtime_root=runtime_root)
        if not row:
            raise ValueError("launch_authorization_missing_or_invalid")
        _load_accepted_prepared_session(
            str(row.get("source_session_id") or ""),
            str(row.get("source_session_digest") or ""),
            runtime_root,
        )
        consumption = _read_json(_authorization_consumption_path(str(row.get("authorization_id") or ""), runtime_root))
        if consumption:
            if not _validate_consumption(consumption):
                raise ValueError("launch_authorization_consumption_tampered")
            return {**row, "authorization_consumed": True, "launch_id": str(consumption.get("launch_id") or "")}
        return row
    except (OSError, ValueError) as exc:
        return _failure("bounded_execution_session_launch_authorization_expired", str(exc))


def _launch_bounds(session: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "one_project_reference": str(session.get("project_reference") or ""),
        "one_queue_item_id": str(session.get("queue_item_id") or ""),
        "one_proposal_id": str(session.get("proposal_id") or ""),
        "single_active_session_for_project": True,
        "fresh_isolated_workspace_required_before_step_execution": True,
        "provider_plan_review_required_before_provider_call": True,
        "test_plan_review_required_before_test_execution": True,
        "risk_review_required_before_step_execution": True,
        "rollback_plan_review_required_before_project_mutation": True,
        "execution_budget_review_required_before_step_execution": True,
        "goal_alignment_review_required": True,
        "uncertainty_review_required": True,
        "outcome_reflection_required": True,
        "fresh_step_authorization_required": True,
    }


def launch_bounded_development_execution_session(
    authorization_id: str,
    *,
    expected_authorization_digest: str,
    expected_session_id: str,
    expected_session_digest: str,
    exact_phrase: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            authorization = load_bounded_launch_authorization(authorization_id, runtime_root=runtime_root)
            if not authorization:
                raise ValueError("launch_authorization_missing_or_invalid")
            if str(authorization.get("authorization_digest") or "") != str(expected_authorization_digest or ""):
                raise ValueError("stale_launch_authorization_digest")
            if str(authorization.get("source_session_id") or "") != str(expected_session_id or ""):
                raise ValueError("launch_session_id_mismatch")
            if str(authorization.get("source_session_digest") or "") != str(expected_session_digest or ""):
                raise ValueError("launch_session_digest_mismatch")
            session, review = _load_accepted_prepared_session(
                expected_session_id, expected_session_digest, runtime_root
            )
            if str(review.get("prepared_execution_session_review_record_digest") or "") != str(
                authorization.get("source_prepared_review_digest") or ""
            ):
                raise ValueError("stale_prepared_session_review")

            consumption_path = _authorization_consumption_path(authorization_id, runtime_root)
            existing_consumption = _read_json(consumption_path)
            launch_id = "launch_" + _digest({
                "authorization_id": authorization_id,
                "authorization_digest": expected_authorization_digest,
                "source_session_id": expected_session_id,
                "source_session_digest": expected_session_digest,
            })[:24]
            if existing_consumption:
                if not _validate_consumption(existing_consumption):
                    raise ValueError("launch_authorization_consumption_tampered")
                if str(existing_consumption.get("launch_id") or "") != launch_id:
                    raise ValueError("launch_authorization_consumption_conflict")
                existing_launch = _read_json(_launch_path(launch_id, runtime_root))
                if not existing_launch or not _validate_launch(existing_launch):
                    raise ValueError("consumed_authorization_launch_missing_or_invalid")
                return {**existing_launch, "operation_status": "replayed"}

            for other in _launch_rows(runtime_root):
                effective_state = str(other.get("session_state") or "")
                try:
                    from execution_session_pause_resume_cancel_recovery import get_effective_execution_session_state
                    effective_state = get_effective_execution_session_state(
                        str(other.get("launch_id") or ""), runtime_root=runtime_root
                    )
                except Exception:
                    pass
                if (
                    str(other.get("project_reference") or "") == str(session.get("project_reference") or "")
                    and str(other.get("launch_id") or "") != launch_id
                    and effective_state in {
                        "active", "launching", "paused", "pause_pending_safe_boundary", "recovery_required"
                    }
                ):
                    raise ValueError("conflicting_active_execution_session_for_project")

            bounds = _launch_bounds(session)
            bounds_digest = _digest(bounds)
            generation = 1
            launch_digest = _digest({
                "launch_id": launch_id,
                "generation": generation,
                "authorization_id": authorization_id,
                "authorization_digest": expected_authorization_digest,
                "source_session_id": expected_session_id,
                "source_session_digest": expected_session_digest,
                "queue_item_id": str(session.get("queue_item_id") or ""),
                "project_reference": str(session.get("project_reference") or ""),
                "proposal_id": str(session.get("proposal_id") or ""),
                "launch_bounds_digest": bounds_digest,
            })
            namespace = _runtime_namespace_path(launch_id, runtime_root)
            namespace.mkdir(parents=True, exist_ok=False)
            namespace_record = {
                "launch_id": launch_id,
                "launch_digest": launch_digest,
                "content_free": True,
                "project_files_materialized": False,
                "provider_contacted": False,
                "commands_executed": False,
                "tests_executed": False,
            }
            _atomic_json(namespace / "session.json", namespace_record)

            row = {
                "ok": True,
                "status": "bounded_development_execution_session_launched",
                "launch_id": launch_id,
                "launch_digest": launch_digest,
                "generation": generation,
                "session_state": "active",
                "authorization_id": authorization_id,
                "authorization_digest": expected_authorization_digest,
                "authorization_consumed": True,
                "source_session_id": expected_session_id,
                "source_session_digest": expected_session_digest,
                "source_prepared_review_digest": str(review.get("prepared_execution_session_review_record_digest") or ""),
                "source_schedule_digest": str(session.get("source_schedule_digest") or ""),
                "source_queue_digest": str(session.get("source_queue_digest") or ""),
                "queue_item_id": str(session.get("queue_item_id") or ""),
                "project_reference": str(session.get("project_reference") or ""),
                "proposal_id": str(session.get("proposal_id") or ""),
                "priority_rank": int(session.get("priority_rank") or 0),
                "priority_level": str(session.get("priority_level") or "normal"),
                "dependency_item_ids": list(session.get("dependency_item_ids") or []),
                "launch_bounds": bounds,
                "launch_bounds_digest": bounds_digest,
                "session_runtime_namespace_created": True,
                "project_workspace_materialized": False,
                "mindful_launch_gate_passed": True,
                "goal_alignment_review_required": True,
                "uncertainty_review_required": True,
                "outcome_reflection_required": True,
                "fresh_step_authorization_required": True,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                **_base(),
                "execution_session_launch_authorized": True,
                "execution_session_launched": True,
            }
            row = _sealed(row, "bounded_execution_session_launch_record_digest")
            consumption = {
                "ok": True,
                "status": "bounded_launch_authorization_consumed",
                "authorization_id": authorization_id,
                "authorization_digest": expected_authorization_digest,
                "launch_id": launch_id,
                "launch_digest": launch_digest,
                "source_session_id": expected_session_id,
                "source_session_digest": expected_session_digest,
                "authorization_consumed": True,
                "consumption_count": 1,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                "old_authority_reusable": False,
                "content_free": True,
            }
            consumption = _sealed(consumption, "bounded_launch_authorization_consumption_record_digest")
            _atomic_json(_launch_snapshot_path(launch_id, generation, runtime_root), row)
            _atomic_json(_launch_path(launch_id, runtime_root), row)
            _atomic_json(consumption_path, consumption)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("bounded_development_execution_session_launch_blocked", str(exc))


def load_bounded_development_execution_session(launch_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_launch_path(str(launch_id or "").lower(), runtime_root))
    return row if row and _validate_launch(row) else {}


def inspect_bounded_development_execution_session(launch_id: str, *, runtime_root=None) -> dict[str, Any]:
    try:
        row = load_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
        if not row:
            raise ValueError("bounded_execution_session_missing_or_invalid")
        authorization = load_bounded_launch_authorization(str(row.get("authorization_id") or ""), runtime_root=runtime_root)
        if not authorization:
            raise ValueError("source_launch_authorization_missing_or_invalid")
        consumption = _read_json(_authorization_consumption_path(str(row.get("authorization_id") or ""), runtime_root))
        if not consumption or not _validate_consumption(consumption):
            raise ValueError("launch_authorization_consumption_missing_or_invalid")
        if str(consumption.get("launch_id") or "") != str(row.get("launch_id") or ""):
            raise ValueError("launch_consumption_binding_invalid")
        _load_accepted_prepared_session(
            str(row.get("source_session_id") or ""),
            str(row.get("source_session_digest") or ""),
            runtime_root,
        )
        namespace_record = _read_json(_runtime_namespace_path(str(row.get("launch_id") or ""), runtime_root) / "session.json")
        if not namespace_record or str(namespace_record.get("launch_digest") or "") != str(row.get("launch_digest") or ""):
            raise ValueError("bounded_session_runtime_namespace_invalid")
        return row
    except (OSError, ValueError) as exc:
        return _failure("bounded_development_execution_session_expired", str(exc))


def _public_authorization(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("ok") is not True:
        return {key: record.get(key) for key in ("ok", "status", "reason") if key in record} | _base()
    allowed = {
        "ok", "status", "authorization_id", "authorization_digest", "source_session_id",
        "source_session_digest", "source_schedule_digest", "source_queue_digest", "queue_item_id",
        "project_reference", "proposal_id", "priority_rank", "priority_level", "dependency_item_ids",
        "requirements_digest", "authorization_consumed", "authorize_phrase", "operation_status",
    }
    row = {key: record.get(key) for key in allowed if key in record}
    row.update(_base())
    row["public_bounded_launch_authorization_digest"] = _digest(row)
    return row


def _public_launch(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("ok") is not True:
        return {key: record.get(key) for key in ("ok", "status", "reason") if key in record} | _base()
    allowed = {
        "ok", "status", "launch_id", "launch_digest", "generation", "session_state",
        "authorization_id", "authorization_digest", "authorization_consumed", "source_session_id",
        "source_session_digest", "source_schedule_digest", "source_queue_digest", "queue_item_id",
        "project_reference", "proposal_id", "priority_rank", "priority_level", "dependency_item_ids",
        "launch_bounds", "launch_bounds_digest", "session_runtime_namespace_created",
        "project_workspace_materialized", "mindful_launch_gate_passed", "goal_alignment_review_required",
        "uncertainty_review_required", "outcome_reflection_required", "fresh_step_authorization_required",
        "execution_session_launch_authorized", "execution_session_launched", "operation_status",
    }
    row = {key: record.get(key) for key in allowed if key in record}
    row.update(_base())
    if record.get("execution_session_launch_authorized") is True:
        row["execution_session_launch_authorized"] = True
    if record.get("execution_session_launched") is True:
        row["execution_session_launched"] = True
    row["public_bounded_execution_session_digest"] = _digest(row)
    return row


def public_bounded_development_execution_sessions(*, runtime_root=None) -> dict[str, Any]:
    try:
        sessions = [_public_launch(row) for row in _launch_rows(runtime_root)]
        result = {
            "ok": True,
            "status": "bounded_development_execution_session_list_ready",
            "session_count": len(sessions),
            "sessions": sessions,
            **_base(),
        }
        result["public_bounded_execution_session_list_digest"] = _digest(result)
        return result
    except (OSError, ValueError) as exc:
        return _failure("bounded_development_execution_session_list_blocked", str(exc))


def bounded_launch_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if record.get("ok") is not True:
        return f"Bounded execution-session launch was blocked: {record.get('reason', status or 'invalid evidence')}."
    if status == "bounded_execution_session_launch_authorization_ready":
        return (
            f"Launch authorization {record.get('authorization_id')} is ready for prepared session "
            f"{record.get('source_session_id')}. Reply with the exact authorization phrase to launch it once. "
            "No provider, command, test, workspace, or project action has occurred."
        )
    if status == "bounded_development_execution_session_launched":
        return (
            f"Bounded execution session {record.get('launch_id')} is active for queue item {record.get('queue_item_id')}. "
            "The launch authorization was consumed exactly once. No provider, command, test, project workspace, "
            "or project change was authorized by launch."
        )
    if status == "bounded_development_execution_session_list_ready":
        return f"There are {record.get('session_count', 0)} bounded development execution sessions."
    return f"The bounded execution-session control recorded: {status}."


def process_execution_session_authorization_bounded_launch_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    prepare = _PREPARE_AUTH.fullmatch(text)
    launch = _AUTHORIZE_LAUNCH.fullmatch(text)
    inspect = _INSPECT.fullmatch(text)
    if prepare:
        result = _public_authorization(prepare_bounded_launch_authorization(
            prepare.group("session").lower(),
            expected_session_digest=prepare.group("digest").lower(),
            exact_phrase=text,
            runtime_root=runtime_root,
        ))
    elif launch:
        result = _public_launch(launch_bounded_development_execution_session(
            launch.group("authorization").lower(),
            expected_authorization_digest=launch.group("authorization_digest").lower(),
            expected_session_id=launch.group("session").lower(),
            expected_session_digest=launch.group("session_digest").lower(),
            exact_phrase=text,
            runtime_root=runtime_root,
        ))
    elif _SHOW.fullmatch(text):
        result = public_bounded_development_execution_sessions(runtime_root=runtime_root)
    elif inspect:
        result = _public_launch(inspect_bounded_development_execution_session(
            inspect.group("launch").lower(), runtime_root=runtime_root
        ))
    else:
        return {"active": False, "event": "inactive"}
    return {
        "active": True,
        "event": str(result.get("status") or "bounded_development_execution_session_launch_blocked"),
        "execution_session_bounded_launch": result,
        "conversation_response": bounded_launch_response(result),
    }
