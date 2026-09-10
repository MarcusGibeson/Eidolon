from __future__ import annotations

"""v1181.0-v1181.2 bounded implementation preparation foundations.

Consumes exact v1180.8 structural plans plus a caller-supplied content-free source
baseline and explicit target bindings. It prepares digest-bound implementation
candidates only. It never reads or writes source, creates a patch, runs tests,
invokes a shell/tool/provider/model, or grants approval or authorization.
"""

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1181.2"
MAX_PLANS = 32
MAX_BASELINE_FILES = 512
MAX_PREPARATIONS = 32
MAX_REPORT_BYTES = 131_072
_ALLOWED_SUFFIXES = frozenset({".py", ".md", ".json", ".html", ".css", ".js", ".txt", ".toml", ".yaml", ".yml"})
_BLOCKED_PARTS = frozenset({"data", "sandbox", ".git", "__pycache__", ".venv", "venv", "node_modules", "conversations", "memories"})
_DRIVE = re.compile(r"^[A-Za-z]:")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _text(value: Any, limit: int = 180) -> str:
    return " ".join(str(value or "").split())[:limit]


def _safe_target(value: Any) -> str:
    raw = _text(value, 260).replace("\\", "/")
    if not raw or raw.startswith("/") or _DRIVE.match(raw):
        return ""
    path = PurePosixPath(raw)
    if any(part in {"", ".", ".."} or part.lower() in _BLOCKED_PARTS for part in path.parts):
        return ""
    if path.suffix.lower() not in _ALLOWED_SUFFIXES:
        return ""
    return path.as_posix()


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "preparation_mode": "bounded_content_free",
        "source_read": False,
        "source_modified": False,
        "patch_created": False,
        "patch_applied": False,
        "tests_executed": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "approval_created": False,
        "authorization_created": False,
        "implementation_started": False,
        "project_registry_discovered": False,
        "raw_source_exposed": False,
        "raw_arguments_exposed": False,
        "content_free": True,
        "operator_review_required": True,
    }


def prepare_implementation_candidates(
    planning_bundle: Mapping[str, Any],
    source_baseline: Mapping[str, Any],
    target_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind exact plans to an explicit source baseline without touching source."""
    base = _base()
    planning_digest = _text(planning_bundle.get("planning_bundle_digest"), 64)
    valid_plan_bundle = (
        planning_bundle.get("contract_version") == "v1180.8"
        and planning_bundle.get("content_free") is True
        and planning_bundle.get("source_modified") is False
        and planning_bundle.get("patch_created") is False
        and planning_bundle.get("tests_executed") is False
        and len(planning_digest) == 64
    )
    baseline_digest = _text(source_baseline.get("baseline_digest"), 64)
    files = list(source_baseline.get("files") or [])[:MAX_BASELINE_FILES]
    valid_baseline = source_baseline.get("content_free") is True and len(baseline_digest) == 64
    baseline_by_path: dict[str, str] = {}
    for row in files:
        path = _safe_target(row.get("path"))
        digest = _text(row.get("file_digest"), 64)
        if path and len(digest) == 64 and path not in baseline_by_path:
            baseline_by_path[path] = digest
    if not valid_plan_bundle or not valid_baseline:
        result = {**base, "preparation_status": "blocked", "block_reason": "invalid_input_contract", "preparations": [], "preparation_count": 0}
        result["preparation_bundle_digest"] = _digest(result)
        return result

    preparations: list[dict[str, Any]] = []
    invalid_count = stale_count = duplicate_count = 0
    seen: set[str] = set()
    for plan in list(planning_bundle.get("plans") or [])[:MAX_PLANS]:
        plan_id = _text(plan.get("implementation_plan_id"), 64)
        plan_digest = _text(plan.get("implementation_plan_digest"), 64)
        spec_id = _text(plan.get("specification_id"), 64)
        if not plan_id or len(plan_digest) != 64 or not spec_id or plan.get("patch_allowed") is not False or plan.get("test_execution_allowed") is not False:
            invalid_count += 1
            continue
        if plan_id in seen:
            duplicate_count += 1
            continue
        seen.add(plan_id)
        binding = target_bindings.get(plan_id) if isinstance(target_bindings, Mapping) else None
        if not isinstance(binding, Mapping):
            invalid_count += 1
            continue
        target = _safe_target(binding.get("target_path"))
        expected_digest = _text(binding.get("expected_file_digest"), 64)
        actual_digest = baseline_by_path.get(target, "")
        if not target or len(expected_digest) != 64 or not actual_digest:
            invalid_count += 1
            continue
        if expected_digest != actual_digest:
            stale_count += 1
            continue
        structural = {
            "implementation_plan_id": plan_id,
            "implementation_plan_digest": plan_digest,
            "test_plan_digest": _text(plan.get("test_plan_digest"), 64),
            "specification_id": spec_id,
            "target_path": target,
            "baseline_file_digest": actual_digest,
            "baseline_digest": baseline_digest,
            "change_step_codes": list(plan.get("implementation_step_codes") or [])[:8],
            "precondition_codes": list(plan.get("pre_change_checks") or [])[:8],
            "acceptance_criteria_codes": list(plan.get("acceptance_criteria_codes") or [])[:12],
            "test_plan_codes": list(plan.get("post_change_checks") or [])[:12],
            "rollback_plan_codes": list(plan.get("rollback_plan_codes") or [])[:8],
            "sandbox_required": True,
            "fresh_source_match_required": True,
            "operator_review_required": True,
            "patch_creation_allowed": False,
            "implementation_authorized": False,
            "test_execution_allowed": False,
        }
        structural["preparation_digest"] = _digest({"planning_bundle_digest": planning_digest, **structural})
        structural["preparation_id"] = f"prep-{structural['preparation_digest'][:20]}"
        preparations.append(structural)
        if len(preparations) >= MAX_PREPARATIONS:
            break

    result = {
        **base,
        "preparation_status": "candidate_ready" if preparations else ("stale_source" if stale_count else "no_valid_target"),
        "planning_bundle_digest": planning_digest,
        "baseline_digest": baseline_digest,
        "baseline_file_count": len(baseline_by_path),
        "input_plan_count": min(len(list(planning_bundle.get("plans") or [])), MAX_PLANS),
        "invalid_plan_or_binding_count": invalid_count,
        "stale_binding_count": stale_count,
        "duplicate_plan_count": duplicate_count,
        "preparation_count": len(preparations),
        "preparations": preparations,
        "patch_creation_allowed": False,
        "implementation_allowed": False,
        "test_execution_allowed": False,
    }
    result["preparation_bundle_digest"] = _digest(result)
    if len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()) > MAX_REPORT_BYTES:
        raise ValueError("Implementation preparation report exceeded bounded size")
    return result


def implementation_preparation_prompt(result: Mapping[str, Any]) -> str:
    return (
        "Bounded implementation preparation:\n"
        f"- Preparation candidates: {int(result.get('preparation_count') or 0)}.\n"
        "- These bind reviewed plans to an explicit source baseline; they are not patches or authority.\n"
        "- Do not claim source modification, implementation, test execution, approval, or authorization."
    )
