from __future__ import annotations

"""Unified supervised coordinator for supported small-project kinds.

The coordinator performs grounded planning once, resolves an immutable public
capability descriptor, and delegates to the existing type-specific bounded
implementation path. v1205.6-v1205.8 adds a durable coordinator journal so
concurrent retries, process interruption, stale capability resolution, and
record tampering cannot cause untracked duplicate delegation. It adds no apply,
repair, model, release, or autonomous authority.
"""

import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from grounded_development_planning import create_or_resume_grounded_plan
from javascript_tool_implementation_foundations import (
    public_javascript_tool_checkpoint,
    run_or_resume_javascript_tool_implementation,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)
from python_cli_implementation_foundations import (
    public_python_cli_checkpoint,
    run_or_resume_python_cli_implementation,
)
from small_project_capability_registry import (
    capability_for_project_kind,
    list_small_project_capabilities,
    registry_digest,
    validate_registry,
)
from small_website_implementation_checkpoint import (
    public_small_website_checkpoint,
    run_or_resume_small_website_implementation,
)

SCHEMA_VERSION = "2"
CONTRACT_VERSION = "v1205.8"
COORDINATOR_LEASE_SECONDS = 90.0
COORDINATOR_WAIT_SECONDS = 120.0
COORDINATOR_POLL_SECONDS = 0.025


def _failure(status: str, *, project_kind: str = "", failed_stage: str = "routing") -> dict[str, Any]:
    return {
        "ok": False,
        "status": status,
        "failed_stage": failed_stage,
        "project_kind": project_kind,
        "supported": False,
        "operator_review_required": True,
        "provider_contacted": False,
        "selected_project_modified": False,
        "source_modified": False,
        "implementation_applied": False,
        "dependencies_installed": False,
        "network_allowed": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "private_request_included": False,
        "private_path_included": False,
        "private_content_included": False,
        "raw_provider_output_included": False,
    }


def _normalize_result(result: Mapping[str, Any], *, project_kind: str, capability_id: str) -> dict[str, Any]:
    normalized = dict(result)
    normalized.update({
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "project_kind": project_kind,
        "capability_id": capability_id,
        "capability_registry_digest": registry_digest(),
        "supported": True,
        "coordinator": "general_small_project_implementation",
        "operator_review_required": True,
        "dependencies_installed": False,
        "network_allowed": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "private_request_included": False,
        "private_path_included": False,
        "private_content_included": False,
        "raw_provider_output_included": False,
    })
    normalized["unified_result_digest"] = _digest({k: v for k, v in normalized.items() if k not in {"unified_result_digest", "operation_status"}})
    return normalized


def _coordination_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "general-small-project-coordination" / proposal_id / f"revision-{int(revision)}.json"


def _coordination_digest(record: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in record.items() if k not in {"coordination_digest", "operation_status"}})


def _valid_coordination(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("coordination_digest") or "")
    return bool(supplied) and supplied == _coordination_digest(record)


def _bindings(
    *,
    proposal_id: str,
    revision: int,
    revision_digest: str,
    planning_digest: str,
    project_kind: str,
    capability_id: str,
    capability_registry_digest: str,
) -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "revision": int(revision),
        "revision_digest": str(revision_digest),
        "planning_digest": str(planning_digest),
        "project_kind": str(project_kind),
        "capability_id": str(capability_id),
        "capability_registry_digest": str(capability_registry_digest),
    }


def _bindings_match(record: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(record.get(key) == value for key, value in expected.items())


def _safe_registry() -> tuple[bool, str]:
    public = list_small_project_capabilities()
    if not validate_registry(public.get("capabilities") or []):
        return False, ""
    supplied = str(public.get("registry_digest") or "")
    recalculated = _digest({k: v for k, v in public.items() if k != "registry_digest"})
    return bool(supplied and supplied == recalculated), supplied


def _wait_for_coordination(path: Path, expected: Mapping[str, Any], deadline: float) -> dict[str, Any] | None:
    while time.monotonic() < deadline:
        try:
            record = _read_json(path)
        except (OSError, ValueError):
            return {"ok": False, "status": "general_coordinator_record_invalid", "failed_stage": "coordination"}
        if not record:
            return None
        if not _valid_coordination(record):
            return {"ok": False, "status": "general_coordinator_record_invalid", "failed_stage": "coordination"}
        if not _bindings_match(record, expected):
            return {"ok": False, "status": "stale_general_coordinator_binding", "failed_stage": "coordination"}
        phase = str(record.get("phase") or "")
        if phase == "sealed":
            result = record.get("result")
            if not isinstance(result, dict) or str(record.get("result_digest") or "") != _digest(result):
                return {"ok": False, "status": "general_coordinator_result_invalid", "failed_stage": "coordination"}
            return {**result, "operation_status": "resumed", "coordination_digest": str(record.get("coordination_digest") or ""), "coordination_recovered": bool(record.get("recovery_count"))}
        if phase == "blocked":
            return _failure(str(record.get("blocked_status") or "general_coordinator_blocked"), project_kind=str(record.get("project_kind") or ""), failed_stage="coordination")
        if phase != "prepared":
            return {"ok": False, "status": "general_coordinator_record_invalid", "failed_stage": "coordination"}
        if float(record.get("lease_expires_unix") or 0.0) <= time.time():
            return None
        time.sleep(COORDINATOR_POLL_SECONDS)
    return {"ok": False, "status": "general_coordinator_in_progress", "failed_stage": "coordination"}


def _delegate(
    capability_id: str,
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    runtime_root,
    provider_generate: Callable[[str], str] | None,
    node_executable: str | None,
    python_executable: str | None,
) -> Mapping[str, Any]:
    if capability_id == "small_website":
        return run_or_resume_small_website_implementation(
            proposal_id,
            expected_revision=expected_revision,
            expected_revision_digest=expected_revision_digest,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            node_executable=node_executable,
        )
    if capability_id == "javascript_tool":
        return run_or_resume_javascript_tool_implementation(
            proposal_id,
            expected_revision=expected_revision,
            expected_revision_digest=expected_revision_digest,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            node_executable=node_executable,
        )
    if capability_id == "python_cli":
        return run_or_resume_python_cli_implementation(
            proposal_id,
            expected_revision=expected_revision,
            expected_revision_digest=expected_revision_digest,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            python_executable=python_executable,
        )
    return _failure("capability_coordinator_unavailable")


def run_or_resume_general_small_project_implementation(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    node_executable: str | None = None,
    python_executable: str | None = None,
) -> dict[str, Any]:
    plan = create_or_resume_grounded_plan(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
    )
    if not plan.get("planning_digest"):
        failure = _failure(str(plan.get("status") or "planning_failed"), failed_stage="planning")
        failure["capability_registry_digest"] = registry_digest()
        return failure

    registry_ok, registry_value = _safe_registry()
    if not registry_ok:
        failure = _failure("small_project_capability_registry_invalid", failed_stage="routing")
        failure["capability_registry_digest"] = registry_value
        return failure

    project_kind = str(plan.get("project_kind") or "")
    capability = capability_for_project_kind(project_kind)
    if capability is None:
        failure = _failure("unsupported_small_project_kind", project_kind=project_kind)
        failure["capability_registry_digest"] = registry_value
        failure["limitation_digest"] = _digest({"project_kind": project_kind, "status": failure["status"]})
        return failure

    expected = _bindings(
        proposal_id=proposal_id,
        revision=expected_revision,
        revision_digest=expected_revision_digest,
        planning_digest=str(plan.get("planning_digest") or ""),
        project_kind=project_kind,
        capability_id=capability.capability_id,
        capability_registry_digest=registry_value,
    )
    path = _coordination_path(proposal_id, expected_revision, runtime_root)
    lease_token = uuid.uuid4().hex
    recovery_count = 0
    while True:
        should_wait = False
        with _proposal_lock(proposal_id, runtime_root):
            existing = _read_json(path)
            if existing:
                if not _valid_coordination(existing):
                    return _failure("general_coordinator_record_invalid", project_kind=project_kind, failed_stage="coordination")
                if not _bindings_match(existing, expected):
                    return _failure("stale_general_coordinator_binding", project_kind=project_kind, failed_stage="coordination")
                phase = str(existing.get("phase") or "")
                if phase == "sealed":
                    result = existing.get("result")
                    if not isinstance(result, dict) or str(existing.get("result_digest") or "") != _digest(result):
                        return _failure("general_coordinator_result_invalid", project_kind=project_kind, failed_stage="coordination")
                    return {**result, "operation_status": "resumed", "coordination_digest": str(existing.get("coordination_digest") or ""), "coordination_recovered": bool(existing.get("recovery_count"))}
                if phase == "blocked":
                    return _failure(str(existing.get("blocked_status") or "general_coordinator_blocked"), project_kind=project_kind, failed_stage="coordination")
                if phase != "prepared":
                    return _failure("general_coordinator_record_invalid", project_kind=project_kind, failed_stage="coordination")
                if float(existing.get("lease_expires_unix") or 0.0) > time.time():
                    should_wait = True
                else:
                    recovery_count = int(existing.get("recovery_count") or 0) + 1
                    prepared = dict(existing)
                    prepared.update({
                        "lease_token": lease_token,
                        "lease_expires_unix": time.time() + COORDINATOR_LEASE_SECONDS,
                        "recovery_count": recovery_count,
                        "attempt_count": int(existing.get("attempt_count") or 1) + 1,
                    })
                    prepared["coordination_digest"] = _coordination_digest(prepared)
                    _atomic_json(path, prepared)
            else:
                prepared = {
                    "schema_version": SCHEMA_VERSION,
                    "contract_version": CONTRACT_VERSION,
                    **expected,
                    "phase": "prepared",
                    "lease_token": lease_token,
                    "lease_expires_unix": time.time() + COORDINATOR_LEASE_SECONDS,
                    "attempt_count": 1,
                    "recovery_count": 0,
                    "provider_contacted": False,
                    "selected_project_modified": False,
                    "source_modified": False,
                    "implementation_applied": False,
                    "repair_authorized": False,
                    "apply_authorized": False,
                    "release_authorized": False,
                    "authority_granted": False,
                }
                prepared["coordination_digest"] = _coordination_digest(prepared)
                _atomic_json(path, prepared)
        if not should_wait:
            break
        waited = _wait_for_coordination(path, expected, time.monotonic() + COORDINATOR_WAIT_SECONDS)
        if waited is not None:
            return waited

    try:
        delegated = _delegate(
            capability.capability_id,
            proposal_id,
            expected_revision=expected_revision,
            expected_revision_digest=expected_revision_digest,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            node_executable=node_executable,
            python_executable=python_executable,
        )
    except Exception as exc:  # private exception text is reduced to a digest-only receipt
        delegated = _failure("general_coordinator_delegate_failed", project_kind=project_kind, failed_stage="implementation")
        delegated["failure_digest"] = _digest({"type": type(exc).__name__, "message": str(exc)[:256]})

    normalized = _normalize_result(delegated, project_kind=project_kind, capability_id=capability.capability_id)
    refreshed_plan = create_or_resume_grounded_plan(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
    )
    refreshed_registry_ok, refreshed_registry = _safe_registry()
    blocked_status = ""
    if str(refreshed_plan.get("planning_digest") or "") != expected["planning_digest"]:
        blocked_status = "general_coordinator_planning_changed"
    elif not refreshed_registry_ok or refreshed_registry != registry_value:
        blocked_status = "general_coordinator_registry_changed"
    else:
        refreshed_capability = capability_for_project_kind(str(refreshed_plan.get("project_kind") or ""))
        if refreshed_capability is None or refreshed_capability.capability_id != capability.capability_id:
            blocked_status = "general_coordinator_capability_changed"

    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid_coordination(current):
            return _failure("general_coordinator_record_invalid", project_kind=project_kind, failed_stage="coordination")
        if not _bindings_match(current, expected):
            return _failure("stale_general_coordinator_binding", project_kind=project_kind, failed_stage="coordination")
        if str(current.get("lease_token") or "") != lease_token:
            return _failure("general_coordinator_lease_lost", project_kind=project_kind, failed_stage="coordination")
        if blocked_status:
            blocked = dict(current)
            blocked.update({"phase": "blocked", "blocked_status": blocked_status, "lease_token": "", "lease_expires_unix": 0.0})
            blocked["coordination_digest"] = _coordination_digest(blocked)
            _atomic_json(path, blocked)
            return _failure(blocked_status, project_kind=project_kind, failed_stage="coordination")
        sealed = dict(current)
        sealed.update({
            "phase": "sealed",
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "result": normalized,
            "result_digest": _digest(normalized),
            "provider_contacted": bool(normalized.get("provider_contacted")),
        })
        sealed["coordination_digest"] = _coordination_digest(sealed)
        _atomic_json(path, sealed)
        return {**normalized, "operation_status": "created" if not recovery_count else "recovered", "coordination_digest": sealed["coordination_digest"], "coordination_recovered": bool(recovery_count)}


def public_general_small_project_result(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    capability_id = str(record.get("capability_id") or "")
    if capability_id == "small_website":
        projected = public_small_website_checkpoint(record)
    elif capability_id == "javascript_tool":
        projected = public_javascript_tool_checkpoint(record)
    elif capability_id == "python_cli":
        projected = public_python_cli_checkpoint(record)
    else:
        projected = {key: record.get(key) for key in ("ok", "status", "failed_stage", "project_kind", "supported", "limitation_digest") if key in record}
    projected.update({
        "contract_version": CONTRACT_VERSION,
        "capability_id": capability_id,
        "project_kind": str(record.get("project_kind") or ""),
        "supported": bool(record.get("supported")),
        "capability_registry_digest": str(record.get("capability_registry_digest") or registry_digest()),
        "unified_result_digest": str(record.get("unified_result_digest") or ""),
        "coordination_digest": str(record.get("coordination_digest") or ""),
        "coordination_recovered": bool(record.get("coordination_recovered")),
        "coordinator": "general_small_project_implementation",
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    })
    return projected


def public_small_project_capabilities() -> dict[str, Any]:
    return list_small_project_capabilities()
