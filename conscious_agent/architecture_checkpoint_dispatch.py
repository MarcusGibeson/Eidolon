from __future__ import annotations

"""v1150.2 coherent registry-backed read-only checkpoint dispatch."""

import hashlib
import inspect
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from checkpoint_registry import checkpoint_descriptors, inspect_checkpoint_registry, resolve_checkpoint_builder, resolve_checkpoint_descriptor

CONTRACT_VERSION = "v1150.2"
_IGNORED_PARTS = {"__pycache__", ".git", ".venv", "venv", ".pytest_cache"}
_IGNORED_SUFFIXES = {".pyc", ".pyo"}
_SUPPORTED_REQUIRED_INPUTS = {"bootstrap"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: str | Path | None) -> str:
    if root is None:
        return _digest([])
    base = Path(root).expanduser().resolve()
    rows: list[tuple[str, str]] = []
    if not base.exists():
        return _digest(rows)
    for path in sorted(base.rglob("*")):
        if any(part in _IGNORED_PARTS for part in path.parts):
            continue
        relative = path.relative_to(base).as_posix()
        if path.is_dir():
            rows.append((relative + "/", "directory"))
            continue
        if not path.is_file() or path.suffix in _IGNORED_SUFFIXES:
            continue
        try:
            rows.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
        except OSError as error:
            rows.append((relative, f"unreadable:{type(error).__name__}"))
    return _digest(rows)


def _invoke_read_only(
    builder: object,
    *,
    source_root: str | Path,
    runtime_root: str | Path,
    checkpoint_inputs: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not callable(builder):
        raise TypeError("checkpoint builder is not callable")
    source = Path(source_root).expanduser().resolve()
    runtime = Path(runtime_root).expanduser().resolve()
    supplied = dict(checkpoint_inputs or {})
    parameters = inspect.signature(builder).parameters
    kwargs: dict[str, Any] = {}
    required_unknown: list[str] = []
    for name, parameter in parameters.items():
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if name == "source_root":
            kwargs[name] = source
        elif name in {"runtime_root", "data_dir", "root"}:
            kwargs[name] = runtime
        elif name in supplied:
            kwargs[name] = supplied[name]
        elif parameter.default is inspect.Parameter.empty:
            required_unknown.append(name)
    if required_unknown:
        return {}, {
            "invocation_supported": set(required_unknown).issubset(_SUPPORTED_REQUIRED_INPUTS),
            "invocation_completed": False,
            "required_parameters": required_unknown,
            "error_type": "checkpoint_inputs_required",
        }
    result = builder(**kwargs)
    if not isinstance(result, dict):
        raise TypeError("checkpoint builder returned a non-mapping result")
    return result, {
        "invocation_supported": True,
        "invocation_completed": True,
        "required_parameters": [],
        "error_type": "",
    }


def _runtime_selection(runtime_root: str | Path | None) -> tuple[Path, bool]:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve(), False
    configured = str(os.environ.get("EIDOLON_DATA_DIR") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve(), False
    return Path(tempfile.mkdtemp(prefix="eidolon-checkpoint-runtime-")).resolve(), True


def dispatch_registered_checkpoint(
    checkpoint_id: str,
    *,
    source_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
    checkpoint_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    runtime, runtime_isolated = _runtime_selection(runtime_root)
    runtime.mkdir(parents=True, exist_ok=True)
    descriptor = resolve_checkpoint_descriptor(checkpoint_id, source_root=source)
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    previous_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    error_type = ""
    report: dict[str, Any] = {}
    invocation: dict[str, Any] = {
        "invocation_supported": False,
        "invocation_completed": False,
        "required_parameters": [],
        "error_type": "",
    }
    try:
        os.environ["EIDOLON_DATA_DIR"] = str(runtime)
        builder = resolve_checkpoint_builder(checkpoint_id, source_root=source)
        report, invocation = _invoke_read_only(
            builder,
            source_root=source,
            runtime_root=runtime,
            checkpoint_inputs=checkpoint_inputs,
        )
    except Exception as caught:  # normalized evidence only; no exception text or private paths
        error_type = type(caught).__name__
    finally:
        if previous_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = previous_data_dir
    source_after = _tree_signature(source)
    runtime_after = _tree_signature(runtime)
    source_modified = source_before != source_after
    runtime_mutated = runtime_before != runtime_after
    reported_ok = bool(report.get("ok")) if report else False
    normalized_status = str(report.get("status") or ("ready" if reported_ok else "review_required")) if report else "invocation_error"
    if invocation.get("error_type") == "checkpoint_inputs_required":
        normalized_status = "checkpoint_inputs_required"
    elif not invocation.get("invocation_completed"):
        normalized_status = "invocation_error"
    if source_modified or runtime_mutated:
        normalized_status = "read_only_contract_violated"
    reported_read_only = bool(report.get("read_only", not report.get("runtime_mutation_performed", False))) if report else True
    effective_read_only = bool(reported_read_only and not source_modified and not runtime_mutated)
    summary = {
        "checkpoint_id": descriptor["checkpoint_id"],
        "requested_checkpoint_id": str(checkpoint_id),
        "resolved_from_alias": str(descriptor.get("resolved_from_alias") or ""),
        "registered_contract_version": descriptor["contract_version"],
        "reported_contract_version": str(report.get("contract_version") or report.get("schema_version") or ""),
        "status": normalized_status,
        "ok": bool(reported_ok and not source_modified and not runtime_mutated and invocation.get("invocation_completed")),
        "passed": int(report.get("passed") or 0) if report else 0,
        "total": int(report.get("total") or 0) if report else 0,
        "reported_read_only": reported_read_only,
        "read_only": effective_read_only,
        "post_available": bool(report.get("post_available", False)) if report else False,
        "invocation_supported": bool(invocation.get("invocation_supported")),
        "invocation_completed": bool(invocation.get("invocation_completed")),
        "required_checkpoint_inputs": list(invocation.get("required_parameters") or []),
        "error_type": error_type or str(invocation.get("error_type") or ""),
        "source_modified": source_modified,
        "runtime_mutated": runtime_mutated,
        "runtime_isolated": runtime_isolated,
        "content_free": True,
    }
    summary["structural_digest"] = _digest(summary)
    result = {
        "contract_version": CONTRACT_VERSION,
        "dispatch_id": f"architecture-checkpoint-dispatch:{descriptor['checkpoint_id']}",
        "descriptor": descriptor,
        "checkpoint_summary": summary,
        "raw_checkpoint_included": False,
        "provider_contacted": False,
        "source_modified": source_modified,
        "runtime_mutated": runtime_mutated,
        "read_only": not source_modified and not runtime_mutated,
        "post_available": False,
        "content_free": True,
        "structural_digest": _digest({"descriptor": descriptor, "summary": summary}),
    }
    if runtime_isolated:
        shutil.rmtree(runtime, ignore_errors=True)
    return result


def build_checkpoint_dispatch_consolidation(
    *,
    source_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
    invoke_checkpoint_ids: Iterable[str] = (),
    checkpoint_inputs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    registry = inspect_checkpoint_registry(source_root=source)
    requested = tuple(dict.fromkeys(str(item).strip() for item in invoke_checkpoint_ids if str(item).strip()))
    if not requested:
        requested = ("conversation-cognition-unification", "understandable-cognitive-controls")
    inputs = checkpoint_inputs or {}
    dispatches = [
        dispatch_registered_checkpoint(
            item,
            source_root=source,
            runtime_root=runtime_root,
            checkpoint_inputs=inputs.get(item),
        )
        for item in requested
    ]
    descriptors = checkpoint_descriptors(source_root=source)
    dispatched_modules = [row["descriptor"]["module"] for row in dispatches]
    dispatched_builders = [row["descriptor"]["builder"] for row in dispatches]
    return {
        "contract_version": CONTRACT_VERSION,
        "consolidation_id": "architecture-checkpoint-dispatch:v1150.2",
        "registry": {
            "checkpoint_count": registry["checkpoint_count"],
            "checkpoint_module_count": registry["checkpoint_module_count"],
            "duplicate_checkpoint_ids": registry["duplicate_checkpoint_ids"],
            "duplicate_builder_targets": registry["duplicate_builder_targets"],
            "all_compatibility_targets_available": registry["all_compatibility_targets_available"],
            "required_input_names": registry["required_input_names"],
            "all_required_inputs_dispatch_supported": registry["all_required_inputs_dispatch_supported"],
            "structural_digest": registry["structural_digest"],
        },
        "descriptor_count": len(descriptors),
        "requested_dispatch_count": len(requested),
        "dispatch_count": len(dispatches),
        "dispatches": dispatches,
        "duplicate_modules": sorted({item for item in dispatched_modules if dispatched_modules.count(item) > 1}),
        "duplicate_builders": sorted({item for item in dispatched_builders if dispatched_builders.count(item) > 1}),
        "all_requested_checkpoints_read_only": all(row["read_only"] for row in dispatches),
        "all_requested_checkpoints_invocation_supported": all(row["checkpoint_summary"]["invocation_supported"] for row in dispatches),
        "all_requested_checkpoints_completed": all(row["checkpoint_summary"]["invocation_completed"] for row in dispatches),
        "all_registered_checkpoints_read_only": all(
            row["checkpoint_summary"]["read_only"] and not row["checkpoint_summary"]["post_available"]
            for row in dispatches
        ),
        "historical_builders_preserved": registry["all_compatibility_targets_available"],
        "historical_aliases_preserved": registry["all_compatibility_targets_available"],
        "raw_checkpoint_content_included": False,
        "provider_contacted": False,
        "source_modified": any(row["source_modified"] for row in dispatches),
        "runtime_mutated": any(row["runtime_mutated"] for row in dispatches),
        "read_only": all(row["read_only"] for row in dispatches),
        "content_free": True,
        "structural_digest": _digest({"registry": registry["structural_digest"], "dispatches": dispatches}),
    }
