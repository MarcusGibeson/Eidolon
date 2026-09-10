from __future__ import annotations

"""Strictly read-only v1209.9 General Test Adapter checkpoint.

The checkpoint evaluates the public unified contract with synthetic,
content-free adapter evidence.  It does not invoke a specialized executor,
probe a runtime, read project/runtime records, or grant execution authority.
"""

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_test_adapter_contract import PROJECT_ADAPTER_POLICY, adapter_for_id, list_test_adapters, prepare_test_adapter_execution, registry_digest, run_or_resume_selected_test_adapter, select_test_adapter, validate_registry

CONTRACT_VERSION = "v1209.9"
RETAINED_CONTRACT_VERSION = "v1209.8"
_CHECKPOINT_ID = "general-test-adapter-consolidation-checkpoint"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_LIMITATIONS = (
    "Registry readiness is descriptive until a separately authorized specialized execution performs runtime checks.",
    "The checkpoint uses synthetic content-free dispatch evidence and does not execute browser, Node, or Python project tests.",
    "Language-runtime guards remain policy boundaries rather than OS containers.",
    "Test failures remain review evidence and do not authorize diagnosis, repair, apply, installation, or release.",
    "Optional dependency and native-runtime verification remain separately attributable to the executing environment.",
)


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
            content = path.read_bytes()
        except OSError:
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest(), len(paths)


def _synthetic_loader(adapter_id: str) -> tuple[Callable[..., dict[str, Any]], Callable[[Mapping[str, Any]], dict[str, Any]]]:
    digest_field, executed_field, marker = {
        "browser_runtime": ("browser_runtime_test_digest", "browser_executed", "b"),
        "node_javascript": ("node_javascript_test_digest", "node_executed", "d"),
        "python": ("python_test_adapter_digest", "python_executed", "e"),
    }[adapter_id]

    def execute(proposal_id: str, **kwargs: Any) -> dict[str, Any]:
        del proposal_id, kwargs
        return {
            "ok": True,
            "status": f"{adapter_id}_synthetic_passed",
            "passed": True,
            executed_field: True,
            digest_field: marker * 64,
            "test_file_count": 2,
            "test_selection_digest": "f" * 64,
            "cleanup_confirmed": True,
            "operation_status": "synthetic_checkpoint_evidence",
            "approval_receipt_digest": "c" * 64,
        }

    return execute, lambda record: dict(record)


def _request(project_kind: str, **extra: Any) -> dict[str, Any]:
    return prepare_test_adapter_execution(
        project_kind,
        proposal_id="content-free-checkpoint-proposal",
        expected_revision=1,
        expected_revision_digest="a" * 64,
        expected_workspace_digest="b" * 64,
        approval_receipt_digest="c" * 64,
        execution_authorized=True,
        **extra,
    )


def build_general_test_adapter_consolidation_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic checkpoint without touching runtime or project state."""

    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    runtime_path = Path(runtime_root).expanduser() if runtime_root is not None else None
    runtime_existed_before = runtime_path.exists() if runtime_path is not None else False
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    first_registry = list_test_adapters()
    second_registry = list_test_adapters()
    require(first_registry == second_registry)
    require(first_registry.get("contract_version") == RETAINED_CONTRACT_VERSION)
    require(first_registry.get("status") == "test_adapter_registry_ready")
    require(first_registry.get("adapter_count") == 3)
    require(validate_registry(first_registry))
    require(registry_digest() == first_registry.get("registry_digest"))
    require(first_registry.get("inspection_only") is True)
    require(first_registry.get("tests_executed") is False)
    require(first_registry.get("runtime_records_written") is False)
    require(first_registry.get("projects_modified") is False)
    require(all(value is False for value in (first_registry.get("authority") or {}).values()))

    adapter_ids = tuple(sorted(
        str((row.get("adapter_identity") or {}).get("adapter_id") or "")
        for row in first_registry.get("adapters") or []
    ))
    require(adapter_ids == ("browser_runtime", "node_javascript", "python"))
    require(all(adapter_for_id(adapter_id, first_registry) is not None for adapter_id in adapter_ids))

    selected: dict[str, str] = {}
    for project_kind, expected_adapter in sorted(PROJECT_ADAPTER_POLICY.items()):
        selection = select_test_adapter(project_kind, registry=first_registry)
        selected[project_kind] = str(selection.get("selected_adapter_id") or "")
        require(selection.get("status") == "test_adapter_selected")
        require(selection.get("selected_adapter_id") == expected_adapter)
        require(selection.get("execution_requires_separate_authorization") is True)
        require(selection.get("selection_only") is True)
        require(selection.get("tests_executed") is False)
        require(all(value is False for value in (selection.get("authority") or {}).values()))

    ambiguous = select_test_adapter("javascript_or_web_project", registry=first_registry)
    unsupported = select_test_adapter("rust_project", registry=first_registry)
    explicit_browser = select_test_adapter(
        "javascript_or_web_project", requested_adapter_id="browser_runtime", registry=first_registry,
    )
    explicit_node = select_test_adapter(
        "javascript_or_web_project", requested_adapter_id="node_javascript", registry=first_registry,
    )
    require(ambiguous.get("status") == "test_adapter_ambiguous")
    require(unsupported.get("status") == "test_adapter_unsupported")
    require(explicit_browser.get("selected_adapter_id") == "browser_runtime")
    require(explicit_node.get("selected_adapter_id") == "node_javascript")

    unavailable_registry = copy.deepcopy(first_registry)
    python_row = next(
        row for row in unavailable_registry["adapters"]
        if (row.get("adapter_identity") or {}).get("adapter_id") == "python"
    )
    python_row["readiness"] = {
        "state": "unavailable", "reason": "runtime_unavailable",
        "runtime_checked": False, "optional_dependencies_imported": False,
    }
    python_row["adapter_contract_digest"] = _digest({
        key: value for key, value in python_row.items() if key != "adapter_contract_digest"
    })
    unavailable = select_test_adapter("python_project", registry=unavailable_registry)
    invalid_registry = list_test_adapters([first_registry["adapters"][0], first_registry["adapters"][0]])
    configuration_error = select_test_adapter("static_web_project", registry=invalid_registry)
    require(unavailable.get("status") == "test_adapter_unavailable")
    require(configuration_error.get("status") == "test_adapter_configuration_error")

    unapproved = prepare_test_adapter_execution(
        "python_project", proposal_id="content-free-checkpoint-proposal", expected_revision=1,
        expected_revision_digest="a" * 64, expected_workspace_digest="b" * 64,
        approval_receipt_digest="c" * 64, execution_authorized=False,
    )
    require(unapproved.get("status") == "test_adapter_execution_approval_required")
    require(unapproved.get("tests_executed") is False)

    dispatch_results: dict[str, dict[str, Any]] = {}
    for project_kind, adapter_id, extra in (
        ("new_small_web_project", "browser_runtime", {"expected_preview_digest": "d" * 64}),
        ("javascript_tool_project", "node_javascript", {}),
        ("python_project", "python", {}),
    ):
        request = _request(project_kind, **extra)
        result = run_or_resume_selected_test_adapter(request, adapter_loader=_synthetic_loader)
        dispatch_results[adapter_id] = result
        require(request.get("status") == "test_adapter_execution_prepared")
        require(result.get("status") == "test_adapter_execution_completed")
        require(result.get("selected_adapter_id") == adapter_id)
        require((result.get("outcome") or {}).get("state") == "passed")
        require((result.get("cleanup") or {}).get("state") == "confirmed")
        require((result.get("reliability") or {}).get("retry_disposition") == "not_needed")
        require(result.get("runtime_records_external") is True)
        require(result.get("specialized_executor_preserved") is True)
        authority = result.get("authority") or {}
        require(authority.get("execution_authorized") is True)
        require(all(authority.get(flag) is False for flag in (
            "authority_granted", "install_authorized", "repair_authorized", "apply_authorized",
            "promotion_authorized", "release_authorized", "model_management_authorized",
        )))
        require(all(value is False for value in (result.get("privacy") or {}).values()))

    python_request = _request("python_project")

    def run_case(evidence: Mapping[str, Any] | None = None, *, raises: bool = False) -> dict[str, Any]:
        def loader(adapter_id: str):
            del adapter_id
            def execute(proposal_id: str, **kwargs: Any):
                del proposal_id, kwargs
                if raises:
                    raise RuntimeError("private path and provider output")
                return dict(evidence or {})
            return execute, lambda row: dict(row)
        return run_or_resume_selected_test_adapter(python_request, adapter_loader=loader)

    failure = run_case({
        "ok": True, "status": "python_test_adapter_failed", "passed": False,
        "python_executed": True, "python_test_adapter_digest": "1" * 64,
        "cleanup_confirmed": True, "approval_receipt_digest": "c" * 64,
    })
    unavailable_execution = run_case({"ok": False, "status": "python_runtime_unavailable"})
    cleanup_failure = run_case({
        "ok": True, "status": "python_test_adapter_passed", "passed": True,
        "python_executed": True, "python_test_adapter_digest": "2" * 64,
        "cleanup_confirmed": False, "approval_receipt_digest": "c" * 64,
    })
    invalid_evidence = run_case({
        "ok": True, "status": "python_test_adapter_passed", "passed": True,
        "python_executed": True, "python_test_adapter_digest": "short",
    })
    authority_violation = run_case({
        "ok": True, "status": "python_test_adapter_passed", "passed": True,
        "python_executed": True, "python_test_adapter_digest": "3" * 64,
        "selected_project_modified": True,
    })
    approval_mismatch = run_case({
        "ok": True, "status": "python_test_adapter_passed", "passed": True,
        "python_executed": True, "python_test_adapter_digest": "4" * 64,
        "approval_receipt_digest": "9" * 64,
    })
    internal_error = run_case(raises=True)
    statuses = {
        "test_failure": failure.get("status"),
        "unavailable_execution": unavailable_execution.get("status"),
        "cleanup_failure": cleanup_failure.get("status"),
        "invalid_evidence": invalid_evidence.get("status"),
        "authority_violation": authority_violation.get("status"),
        "approval_mismatch": approval_mismatch.get("status"),
        "internal_error": internal_error.get("status"),
    }
    require(statuses == {
        "test_failure": "test_adapter_execution_completed",
        "unavailable_execution": "test_adapter_execution_rejected",
        "cleanup_failure": "test_adapter_cleanup_incomplete",
        "invalid_evidence": "test_adapter_evidence_invalid",
        "authority_violation": "test_adapter_authority_boundary_violation",
        "approval_mismatch": "test_adapter_approval_binding_mismatch",
        "internal_error": "test_adapter_execution_internal_error",
    })
    require((failure.get("reliability") or {}).get("failure_class") == "test_failure")
    require((unavailable_execution.get("reliability") or {}).get("retry_disposition") == "same_request_may_resume")
    require((cleanup_failure.get("reliability") or {}).get("retry_disposition") == "cleanup_review_required")
    require("private path" not in json.dumps(statuses, sort_keys=True))

    checkpoint_registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in checkpoint_registry.get("checkpoints", []) if row.get("checkpoint_id") == _CHECKPOINT_ID),
        None,
    )
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_general_test_adapter_consolidation_checkpoint")
    require((descriptor or {}).get("read_only") is True)
    require((descriptor or {}).get("post_available") is False)
    require((descriptor or {}).get("required_input_count") == 0)
    require(not checkpoint_registry.get("duplicate_checkpoint_ids"))
    require(not checkpoint_registry.get("duplicate_builder_targets"))
    require(checkpoint_registry.get("runtime_data_read") is False)
    require(checkpoint_registry.get("provider_contacted") is False)

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)
    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)
    runtime_exists_after = runtime_path.exists() if runtime_path is not None else False
    require(runtime_exists_after == runtime_existed_before)

    report: dict[str, Any] = {
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "contract_version": CONTRACT_VERSION,
        "retained_contract_version": RETAINED_CONTRACT_VERSION,
        "checkpoint_id": f"general-test-adapter-consolidation:{CONTRACT_VERSION}",
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "synthetic_contract_evaluation": True,
        "specialized_executor_invoked": False,
        "project_tests_executed": False,
        "runtime_probed": False,
        "runtime_data_read": False,
        "runtime_mutated": False,
        "runtime_records_written": False,
        "source_modified": False,
        "project_modified": False,
        "provider_contacted": False,
        "dependencies_installed": False,
        "automatic_diagnosis": False,
        "automatic_repair": False,
        "approval_created": False,
        "approval_consumed": False,
        "apply_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
        "source_signature_before": before_digest,
        "source_signature_after": after_digest,
        "source_file_count": before_count,
        "summary": {
            "adapter_count": len(adapter_ids),
            "adapter_ids": list(adapter_ids),
            "concrete_project_kind_count": len(selected),
            "concrete_project_routing": selected,
            "explicit_state_count": 5,
            "synthetic_dispatch_count": len(dispatch_results),
            "dispatch_error_class_count": len(statuses),
            "registry_deterministic": first_registry == second_registry,
            "selection_non_executing": True,
            "execution_separately_authorized": True,
            "specialized_executor_preserved": True,
            "runtime_records_external": True,
            "privacy_preserved": True,
            "authority_preserved": True,
            "checkpoint_registry_discovered": descriptor is not None,
        },
        "limitations": list(_LIMITATIONS),
    }
    report["structural_digest"] = _digest(report)
    return report
