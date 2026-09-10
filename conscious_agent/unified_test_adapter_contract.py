from __future__ import annotations

"""Unified contract, selection, and bounded dispatch for test adapters.

Registry and selection APIs remain inspection-only.  v1209.3-v1209.5 adds an
explicit execution request and a thin dispatcher which calls the existing
browser, Node/JavaScript, or Python implementation only after a separately
authorized, digest-bound request.  v1209.6-v1209.8 hardens request validation,
specialized-evidence reconciliation, and deterministic retry/recovery evidence.
Specialized execution and evidence remain the authority; this module installs
nothing and contains no test logic.
"""

from dataclasses import dataclass
import importlib
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _digest

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1209.8"

READINESS_STATES = frozenset({"selection_ready", "unavailable", "configuration_error"})
SELECTION_STATUSES = frozenset({
    "test_adapter_selected",
    "test_adapter_unsupported",
    "test_adapter_unavailable",
    "test_adapter_ambiguous",
    "test_adapter_configuration_error",
})

AUTHORITY_FLAGS = {
    "authority_granted": False,
    "execution_authorized": False,
    "install_authorized": False,
    "repair_authorized": False,
    "apply_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
}

EXECUTION_AUTHORITY_FLAGS = {
    **AUTHORITY_FLAGS,
    "execution_authorized": True,
}

_ADAPTER_RESULT_FIELDS = {
    "browser_runtime": ("browser_runtime_test_digest", "browser_executed"),
    "node_javascript": ("node_javascript_test_digest", "node_executed"),
    "python": ("python_test_adapter_digest", "python_executed"),
}

EXECUTION_BOUNDARIES = {
    "description_only": True,
    "tests_executed": False,
    "providers_contacted": False,
    "network_allowed": False,
    "dependencies_installed": False,
    "projects_modified": False,
    "runtime_records_written": False,
    "runtime_records_external_when_executed": True,
    "specialized_executor_preserved": True,
}


@dataclass(frozen=True)
class TestAdapterSpec:
    adapter_id: str
    display_name: str
    implementation_module: str
    execution_entrypoint: str
    public_evidence_entrypoint: str
    supported_project_kinds: tuple[str, ...]
    dependencies: tuple[tuple[str, bool], ...]
    runtime_boundary: str
    readiness_state: str = "selection_ready"
    readiness_reason: str = "contract_registered_runtime_check_deferred"

    def public_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "adapter_identity": {
                "adapter_id": self.adapter_id,
                "display_name": self.display_name,
                "implementation_module": self.implementation_module,
                "execution_entrypoint": self.execution_entrypoint,
                "public_evidence_entrypoint": self.public_evidence_entrypoint,
            },
            "supported_project_kinds": sorted(self.supported_project_kinds),
            "readiness": {
                "state": self.readiness_state,
                "reason": self.readiness_reason,
                "runtime_checked": False,
                "optional_dependencies_imported": False,
            },
            "dependencies": [
                {
                    "dependency_id": dependency_id,
                    "required": required,
                    "availability": "deferred_until_authorized_execution",
                    "installation_attempted": False,
                }
                for dependency_id, required in self.dependencies
            ],
            "execution_boundaries": {
                **EXECUTION_BOUNDARIES,
                "runtime_boundary": self.runtime_boundary,
            },
            "selected_tests": {
                "state": "not_selected",
                "count": 0,
                "selection_digest": None,
                "test_contents_included": False,
            },
            "outcome": {
                "state": "not_executed",
                "passed": None,
                "evidence_digest": None,
                "private_output_included": False,
            },
            "cleanup": {
                "state": "not_required",
                "cleanup_confirmed": None,
                "runtime_artifacts_packaged": False,
            },
            "authority": dict(AUTHORITY_FLAGS),
            "privacy": {
                "private_paths_included": False,
                "test_contents_included": False,
                "prompts_included": False,
                "output_included": False,
                "credentials_included": False,
                "runtime_data_included": False,
            },
        }
        record["adapter_contract_digest"] = _digest(record)
        return record


_DEFAULT_ADAPTERS = (
    TestAdapterSpec(
        adapter_id="browser_runtime",
        display_name="Browser Runtime Test Adapter",
        implementation_module="browser_runtime_test_adapter",
        execution_entrypoint="run_or_resume_browser_runtime_test",
        public_evidence_entrypoint="public_browser_runtime_test",
        supported_project_kinds=(
            "empty_project",
            "javascript_or_web_project",
            "new_small_web_project",
            "static_web_project",
        ),
        dependencies=(("python_playwright", True), ("chromium_runtime", True)),
        runtime_boundary="loopback_browser_process_guard_not_os_container",
    ),
    TestAdapterSpec(
        adapter_id="node_javascript",
        display_name="Node and JavaScript Test Adapter",
        implementation_module="node_javascript_test_adapter",
        execution_entrypoint="run_or_resume_node_javascript_tests",
        public_evidence_entrypoint="public_node_javascript_test_result",
        supported_project_kinds=(
            "javascript_or_web_project",
            "javascript_tool_project",
            "new_javascript_tool_project",
            "new_small_web_project",
            "static_web_project",
        ),
        dependencies=(("node_runtime", True),),
        runtime_boundary="language_runtime_policy_not_os_container",
    ),
    TestAdapterSpec(
        adapter_id="python",
        display_name="Python Test Adapter",
        implementation_module="python_test_adapter",
        execution_entrypoint="run_or_resume_python_tests",
        public_evidence_entrypoint="public_python_test_result",
        supported_project_kinds=("new_python_cli_project", "python_cli_project", "python_project"),
        dependencies=(("python_runtime", True), ("pytest", False)),
        runtime_boundary="language_runtime_policy_not_os_container",
    ),
)

# Concrete kinds retain deterministic product routing.  The intentionally broad
# javascript_or_web_project kind is resolved by an explicit adapter request or
# returned as ambiguous rather than guessed.
PROJECT_ADAPTER_POLICY = {
    "empty_project": "browser_runtime",
    "new_small_web_project": "browser_runtime",
    "static_web_project": "browser_runtime",
    "javascript_tool_project": "node_javascript",
    "new_javascript_tool_project": "node_javascript",
    "new_python_cli_project": "python",
    "python_cli_project": "python",
    "python_project": "python",
}


def _adapter_id(row: Mapping[str, Any]) -> str:
    return str((row.get("adapter_identity") or {}).get("adapter_id") or "").strip()


def _validate_adapter_records(rows: Iterable[Mapping[str, Any]]) -> tuple[bool, str | None]:
    seen_ids: set[str] = set()
    for row in rows:
        adapter_id = _adapter_id(row)
        identity = row.get("adapter_identity")
        kinds = row.get("supported_project_kinds")
        readiness = row.get("readiness")
        if not isinstance(identity, Mapping) or not adapter_id:
            return False, "adapter_identity_missing"
        if adapter_id in seen_ids:
            return False, "duplicate_adapter_identity"
        if not all(str(identity.get(key) or "").strip() for key in (
            "display_name", "implementation_module", "execution_entrypoint", "public_evidence_entrypoint"
        )):
            return False, "adapter_identity_incomplete"
        if not isinstance(kinds, list) or not kinds or any(not str(kind or "").strip() for kind in kinds):
            return False, "supported_project_kinds_invalid"
        if len(set(kinds)) != len(kinds):
            return False, "duplicate_supported_project_kind"
        if not isinstance(readiness, Mapping) or readiness.get("state") not in READINESS_STATES:
            return False, "readiness_state_invalid"
        for field in ("dependencies", "execution_boundaries", "selected_tests", "outcome", "cleanup", "authority", "privacy"):
            if field not in row:
                return False, f"{field}_missing"
        if any(bool((row.get("authority") or {}).get(flag)) for flag in AUTHORITY_FLAGS):
            return False, "authority_flag_true"
        supplied_digest = str(row.get("adapter_contract_digest") or "")
        expected_digest = _digest({key: value for key, value in row.items() if key != "adapter_contract_digest"})
        if not supplied_digest or supplied_digest != expected_digest:
            return False, "adapter_contract_digest_invalid"
        seen_ids.add(adapter_id)
    if not seen_ids:
        return False, "adapter_registry_empty"
    return True, None


def list_test_adapters(records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Return deterministic public descriptions without probing or executing."""
    rows = [dict(row) for row in records] if records is not None else [spec.public_record() for spec in _DEFAULT_ADAPTERS]
    valid, error = _validate_adapter_records(rows)
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "test_adapter_registry_ready" if valid else "test_adapter_configuration_error",
        "configuration_error": error,
        "adapter_count": len(rows),
        "adapters": rows,
        "supported_project_kinds": sorted({str(kind) for row in rows for kind in (row.get("supported_project_kinds") or [])}),
        "inspection_only": True,
        "tests_executed": False,
        "providers_contacted": False,
        "dependencies_installed": False,
        "projects_modified": False,
        "runtime_records_written": False,
        "authority": dict(AUTHORITY_FLAGS),
    }
    result["registry_digest"] = _digest(result)
    return result


def registry_digest() -> str:
    return str(list_test_adapters()["registry_digest"])


def adapter_for_id(adapter_id: str, registry: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    source = registry or list_test_adapters()
    target = str(adapter_id or "").strip()
    return next((dict(row) for row in source.get("adapters") or [] if _adapter_id(row) == target), None)


def _selection_result(status: str, project_kind: str, **details: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "project_kind": project_kind,
        "selected_adapter_id": None,
        "candidate_adapter_ids": [],
        "selection_only": True,
        "tests_executed": False,
        "projects_modified": False,
        "runtime_records_written": False,
        "authority": dict(AUTHORITY_FLAGS),
        **details,
    }
    result["selection_digest"] = _digest(result)
    return result


def select_test_adapter(
    project_kind: str,
    *,
    requested_adapter_id: str | None = None,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select contract metadata only; never invoke an adapter executor."""
    kind = str(project_kind or "").strip()
    source = dict(registry or list_test_adapters())
    if not kind:
        return _selection_result("test_adapter_configuration_error", kind, reason="project_kind_missing")
    records_valid, records_error = _validate_adapter_records(source.get("adapters") or [])
    if source.get("status") != "test_adapter_registry_ready" or not records_valid:
        return _selection_result(
            "test_adapter_configuration_error", kind,
            reason=str(source.get("configuration_error") or records_error or "registry_invalid"),
        )

    candidates = sorted(
        (dict(row) for row in source.get("adapters") or [] if kind in (row.get("supported_project_kinds") or [])),
        key=_adapter_id,
    )
    candidate_ids = [_adapter_id(row) for row in candidates]
    requested = str(requested_adapter_id or "").strip()
    selected: dict[str, Any] | None = None
    if requested:
        known = adapter_for_id(requested, source)
        if known is None:
            return _selection_result(
                "test_adapter_configuration_error", kind,
                candidate_adapter_ids=candidate_ids, reason="requested_adapter_unknown",
            )
        if kind not in (known.get("supported_project_kinds") or []):
            return _selection_result(
                "test_adapter_configuration_error", kind,
                candidate_adapter_ids=candidate_ids, reason="requested_adapter_project_kind_mismatch",
            )
        selected = known
    else:
        preferred_id = PROJECT_ADAPTER_POLICY.get(kind)
        if preferred_id:
            selected = next((row for row in candidates if _adapter_id(row) == preferred_id), None)
            if selected is None:
                return _selection_result(
                    "test_adapter_configuration_error", kind,
                    candidate_adapter_ids=candidate_ids, reason="project_policy_adapter_missing",
                )
        elif not candidates:
            return _selection_result("test_adapter_unsupported", kind, reason="unsupported_project_kind")
        elif len(candidates) > 1:
            return _selection_result(
                "test_adapter_ambiguous", kind,
                candidate_adapter_ids=candidate_ids, reason="explicit_adapter_required",
            )
        else:
            selected = candidates[0]

    readiness = str((selected.get("readiness") or {}).get("state") or "")
    if readiness == "unavailable":
        return _selection_result(
            "test_adapter_unavailable", kind,
            candidate_adapter_ids=candidate_ids, reason=str((selected.get("readiness") or {}).get("reason") or "adapter_unavailable"),
        )
    if readiness != "selection_ready":
        return _selection_result(
            "test_adapter_configuration_error", kind,
            candidate_adapter_ids=candidate_ids, reason="adapter_readiness_configuration_error",
        )
    return _selection_result(
        "test_adapter_selected", kind,
        selected_adapter_id=_adapter_id(selected), candidate_adapter_ids=candidate_ids,
        adapter_contract_digest=selected.get("adapter_contract_digest"),
        execution_requires_separate_authorization=True,
    )


def validate_registry(registry: Mapping[str, Any] | None = None) -> bool:
    source = registry or list_test_adapters()
    valid, _ = _validate_adapter_records(source.get("adapters") or [])
    return bool(valid and source.get("status") == "test_adapter_registry_ready")


def _bound_text(value: Any, reason: str) -> tuple[str, str | None]:
    text = str(value or "").strip()
    return text, None if text else reason


def _is_sha256_digest(value: Any) -> bool:
    text = value if isinstance(value, str) else ""
    return len(text) == 64 and all(character in "0123456789abcdefABCDEF" for character in text)


def prepare_test_adapter_execution(
    project_kind: str,
    *,
    proposal_id: str,
    expected_revision: int,
    expected_revision_digest: str,
    expected_workspace_digest: str,
    approval_receipt_digest: str,
    expected_preview_digest: str | None = None,
    requested_adapter_id: str | None = None,
    execution_authorized: bool = False,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Prepare a content-free, approval-bound request without executing tests."""
    selection = select_test_adapter(
        project_kind, requested_adapter_id=requested_adapter_id, registry=registry,
    )
    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "test_adapter_execution_request_invalid",
        "reason": None,
        "project_kind": str(project_kind or "").strip(),
        "proposal_id": str(proposal_id or "").strip(),
        "expected_revision": expected_revision,
        "expected_revision_digest": str(expected_revision_digest or "").strip(),
        "expected_workspace_digest": str(expected_workspace_digest or "").strip(),
        "approval_receipt_digest": str(approval_receipt_digest or "").strip(),
        "expected_preview_digest": str(expected_preview_digest or "").strip() or None,
        "selected_adapter_id": selection.get("selected_adapter_id"),
        "selection_digest": selection.get("selection_digest"),
        "adapter_contract_digest": selection.get("adapter_contract_digest"),
        "execution_requested": True,
        "tests_executed": False,
        "runtime_records_written": False,
        "authority": dict(EXECUTION_AUTHORITY_FLAGS if execution_authorized else AUTHORITY_FLAGS),
        "privacy": {
            "private_paths_included": False,
            "test_contents_included": False,
            "prompts_included": False,
            "output_included": False,
            "credentials_included": False,
            "runtime_data_included": False,
        },
    }
    reason: str | None = None
    if selection.get("status") != "test_adapter_selected":
        base["status"] = str(selection.get("status") or "test_adapter_configuration_error")
        reason = str(selection.get("reason") or "adapter_not_selected")
    elif execution_authorized is not True:
        base["status"] = "test_adapter_execution_approval_required"
        reason = "separate_execution_authorization_required"
    else:
        for value, missing_reason, invalid_reason in (
            (proposal_id, "proposal_id_missing", None),
            (expected_revision_digest, "expected_revision_digest_missing", "expected_revision_digest_invalid"),
            (expected_workspace_digest, "expected_workspace_digest_missing", "expected_workspace_digest_invalid"),
            (approval_receipt_digest, "approval_receipt_digest_missing", "approval_receipt_digest_invalid"),
        ):
            bounded, reason = _bound_text(value, missing_reason)
            if reason is None and invalid_reason and not _is_sha256_digest(bounded):
                reason = invalid_reason
            if reason:
                break
        if reason is None and (not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 1):
            reason = "expected_revision_invalid"
        if reason is None and selection.get("selected_adapter_id") == "browser_runtime" and not base["expected_preview_digest"]:
            reason = "expected_preview_digest_missing"
        if reason is None and base["expected_preview_digest"] and not _is_sha256_digest(base["expected_preview_digest"]):
            reason = "expected_preview_digest_invalid"
        if reason is None:
            base["status"] = "test_adapter_execution_prepared"
    base["reason"] = reason
    base["execution_request_digest"] = _digest(base)
    return base


def _request_valid(request: Mapping[str, Any]) -> bool:
    if not isinstance(request, Mapping):
        return False
    supplied = str(request.get("execution_request_digest") or "")
    expected = _digest({key: value for key, value in request.items() if key != "execution_request_digest"})
    authority = request.get("authority") or {}
    if not isinstance(authority, Mapping):
        return False
    return bool(
        supplied and supplied == expected
        and request.get("status") == "test_adapter_execution_prepared"
        and authority.get("execution_authorized") is True
        and all(authority.get(flag) is False for flag in AUTHORITY_FLAGS if flag != "execution_authorized")
    )


def _load_specialized_adapter(adapter_id: str):
    spec = next(spec for spec in _DEFAULT_ADAPTERS if spec.adapter_id == adapter_id)
    module = importlib.import_module(spec.implementation_module)
    return getattr(module, spec.execution_entrypoint), getattr(module, spec.public_evidence_entrypoint)


def _retry_disposition(status: str, details: Mapping[str, Any]) -> str:
    if status == "test_adapter_execution_completed":
        return "not_needed"
    if status == "test_adapter_execution_rejected":
        return "same_request_may_resume"
    if status == "test_adapter_execution_internal_error":
        return "same_request_may_resume"
    if status == "test_adapter_cleanup_incomplete":
        return "cleanup_review_required"
    if status in {"test_adapter_configuration_error", "test_adapter_evidence_invalid"}:
        return "blocked_by_configuration"
    return "new_review_required"


def _failure_class(status: str, details: Mapping[str, Any]) -> str | None:
    if status == "test_adapter_execution_completed":
        outcome = details.get("outcome") or {}
        return "test_failure" if outcome.get("state") == "failed" else None
    return {
        "test_adapter_execution_request_invalid": "request_invalid",
        "test_adapter_configuration_error": "configuration_error",
        "test_adapter_execution_internal_error": "specialized_adapter_exception",
        "test_adapter_authority_boundary_violation": "authority_boundary_violation",
        "test_adapter_approval_binding_mismatch": "approval_binding_mismatch",
        "test_adapter_evidence_invalid": "specialized_evidence_invalid",
        "test_adapter_execution_rejected": "specialized_adapter_rejected",
        "test_adapter_cleanup_incomplete": "cleanup_incomplete",
    }.get(status, "unclassified")


def _dispatch_result(status: str, request: Mapping[str, Any], **details: Any) -> dict[str, Any]:
    runtime_root_supplied = bool(details.pop("_runtime_root_supplied", False))
    executable_override_supplied = bool(details.pop("_executable_override_supplied", False))
    request_digest = request.get("execution_request_digest")
    attempt_binding = {
        "contract_version": CONTRACT_VERSION,
        "execution_request_digest": request_digest,
        "selected_adapter_id": request.get("selected_adapter_id"),
    }
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "project_kind": str(request.get("project_kind") or ""),
        "proposal_id": str(request.get("proposal_id") or ""),
        "expected_revision": request.get("expected_revision"),
        "selected_adapter_id": request.get("selected_adapter_id"),
        "execution_request_digest": request_digest,
        "dispatch_attempt_digest": _digest(attempt_binding),
        "tests_executed": False,
        "runtime_records_external": True,
        "specialized_executor_preserved": True,
        "selected_tests": {"state": "not_reported", "count": None, "selection_digest": None, "test_contents_included": False},
        "outcome": {"state": "not_executed", "passed": None, "specialized_status": None, "evidence_digest": None, "private_output_included": False},
        "cleanup": {"state": "not_required", "cleanup_confirmed": None, "runtime_artifacts_packaged": False},
        "authority": dict(EXECUTION_AUTHORITY_FLAGS),
        "privacy": {
            "private_paths_included": False, "test_contents_included": False, "prompts_included": False,
            "output_included": False, "credentials_included": False, "runtime_data_included": False,
        },
        **details,
    }
    result["reliability"] = {
        "failure_class": _failure_class(status, details),
        "retry_disposition": _retry_disposition(status, details),
        "same_request_digest_required": True,
        "specialized_resume_authoritative": True,
        "runtime_root_supplied": runtime_root_supplied,
        "executable_override_supplied": executable_override_supplied,
        "path_values_exposed": False,
    }
    result["unified_test_adapter_digest"] = _digest(result)
    return result


def _privacy_projection_safe(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    sensitive_tokens = ("private", "raw_output", "raw_browser_output", "prompt", "credential", "executable_path")
    for key, item in value.items():
        lowered = str(key).lower()
        if any(token in lowered for token in sensitive_tokens) and item not in (False, None, "", 0, [], {}):
            return False
        if isinstance(item, Mapping) and not _privacy_projection_safe(item):
            return False
        if isinstance(item, (list, tuple)):
            for member in item:
                if isinstance(member, Mapping) and not _privacy_projection_safe(member):
                    return False
    return True


def _public_evidence_valid(adapter_id: str, public: Any) -> bool:
    if not isinstance(public, Mapping) or not _privacy_projection_safe(public):
        return False
    if not isinstance(public.get("ok"), bool) or not str(public.get("status") or "").strip():
        return False
    digest_field, executed_field = _ADAPTER_RESULT_FIELDS[adapter_id]
    executed = public.get(executed_field)
    passed = public.get("passed")
    if executed is not None and not isinstance(executed, bool):
        return False
    if passed is not None and not isinstance(passed, bool):
        return False
    if passed is True and executed is not True:
        return False
    if executed is True and not _is_sha256_digest(public.get(digest_field)):
        return False
    if public.get("test_selection_digest") is not None and not _is_sha256_digest(public.get("test_selection_digest")):
        return False
    if public.get("approval_receipt_digest") is not None and not _is_sha256_digest(public.get("approval_receipt_digest")):
        return False
    if public.get("cleanup_confirmed") is not None and not isinstance(public.get("cleanup_confirmed"), bool):
        return False
    return True


def run_or_resume_selected_test_adapter(
    request: Mapping[str, Any], *, runtime_root=None, executable: str | None = None,
    adapter_loader=None,
) -> dict[str, Any]:
    """Delegate one valid request to its unchanged specialized executor."""
    if not isinstance(request, Mapping):
        request = {}
    if not _request_valid(request):
        return _dispatch_result("test_adapter_execution_request_invalid", request, reason="request_digest_or_authority_invalid")
    adapter_id = str(request.get("selected_adapter_id") or "")
    if adapter_id not in _ADAPTER_RESULT_FIELDS:
        return _dispatch_result("test_adapter_configuration_error", request, reason="selected_adapter_unknown")
    try:
        executor, projector = (adapter_loader or _load_specialized_adapter)(adapter_id)
        kwargs: dict[str, Any] = {
            "expected_revision": int(request["expected_revision"]),
            "expected_revision_digest": str(request["expected_revision_digest"]),
            "expected_workspace_digest": str(request["expected_workspace_digest"]),
            "runtime_root": runtime_root,
        }
        if adapter_id == "browser_runtime":
            kwargs["expected_preview_digest"] = str(request["expected_preview_digest"])
            if executable is not None:
                kwargs["chromium_executable"] = executable
        elif adapter_id == "node_javascript" and executable is not None:
            kwargs["node_executable"] = executable
        elif adapter_id == "python" and executable is not None:
            kwargs["python_executable"] = executable
        specialized = executor(str(request["proposal_id"]), **kwargs)
        if not isinstance(specialized, Mapping):
            return _dispatch_result("test_adapter_evidence_invalid", request, reason="specialized_result_not_mapping")
        public = projector(specialized)
    except Exception:
        return _dispatch_result("test_adapter_execution_internal_error", request, reason="specialized_adapter_exception")

    if not _public_evidence_valid(adapter_id, public):
        return _dispatch_result("test_adapter_evidence_invalid", request, reason="specialized_public_evidence_invalid")

    digest_field, executed_field = _ADAPTER_RESULT_FIELDS[adapter_id]
    forbidden_true = any(bool(public.get(flag)) for flag in (
        "authority_granted", "repair_authorized", "apply_authorized", "rollback_authorized", "release_authorized",
        "selected_project_modified", "source_modified", "implementation_applied", "network_allowed", "dependencies_installed",
        "private_path_exposed", "private_content_exposed", "raw_output_exposed", "raw_browser_output_exposed",
    ))
    if forbidden_true:
        return _dispatch_result("test_adapter_authority_boundary_violation", request, reason="specialized_public_evidence_boundary_violation")
    public_approval_digest = public.get("approval_receipt_digest")
    if public_approval_digest is not None and public_approval_digest != request.get("approval_receipt_digest"):
        return _dispatch_result("test_adapter_approval_binding_mismatch", request, reason="specialized_approval_receipt_mismatch")
    executed = bool(public.get(executed_field))
    passed = public.get("passed") if isinstance(public.get("passed"), bool) else None
    evidence_digest = public.get(digest_field)
    test_count = public.get("test_file_count")
    selection_digest = public.get("test_selection_digest")
    cleanup_confirmed = public.get("cleanup_confirmed")
    if passed is True:
        outcome_state = "passed"
    elif executed or passed is False:
        outcome_state = "failed"
    else:
        outcome_state = "not_executed"
    if cleanup_confirmed is False:
        status = "test_adapter_cleanup_incomplete"
    else:
        status = "test_adapter_execution_completed" if public.get("ok") is True else "test_adapter_execution_rejected"
    return _dispatch_result(
        status, request,
        _runtime_root_supplied=runtime_root is not None,
        _executable_override_supplied=executable is not None,
        tests_executed=executed,
        operation_status=specialized.get("operation_status"),
        selected_tests={
            "state": "reported" if selection_digest or test_count is not None else "adapter_managed",
            "count": test_count, "selection_digest": selection_digest, "test_contents_included": False,
        },
        outcome={
            "state": outcome_state, "passed": passed, "specialized_status": public.get("status"),
            "evidence_digest": evidence_digest, "private_output_included": False,
        },
        cleanup={
            "state": "confirmed" if cleanup_confirmed is True else ("failed" if cleanup_confirmed is False else "not_reported"),
            "cleanup_confirmed": cleanup_confirmed, "runtime_artifacts_packaged": False,
        },
        public_specialized_evidence=public,
    )
