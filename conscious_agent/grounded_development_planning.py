from __future__ import annotations

"""Grounded, read-only planning for an exactly approved development proposal.

v1200.4-v1200.6 inspects a bounded project snapshot and persists a revision-bound
specification, file plan, risk assessment, and test plan. It never contacts a
provider, creates implementation files, executes commands, mutates the selected
project, or grants source/release authority.
"""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from selected_project_change_planning import parse_change_directives

from ordinary_chat_development_campaign import (
    _atomic_json, _digest, _event, _proposal_lock, _proposal_path, _read_json,
    _seal, _store_root, _validate,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1205.8"
MAX_FILES = 200
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024
ALLOWED_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json", ".py", ".md", ".txt"}
ALLOWED_NAMES = {"package.json", "pyproject.toml", "requirements.txt", "setup.cfg", "pytest.ini"}
IGNORED_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "coverage"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _planning_path(proposal_id: str, revision: int, runtime_root: str | Path | None = None) -> Path:
    return _store_root(runtime_root) / "planning" / proposal_id / f"revision-{int(revision)}.json"


def _safe_root(raw: str) -> Path:
    if not raw:
        raise ValueError("selected_project_path_missing")
    root = Path(raw).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("selected_project_not_directory")
    if root.is_symlink():
        raise ValueError("selected_project_symlink_rejected")
    return root


def _inventory(root: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    total = 0
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not (Path(current) / d).is_symlink())
        for name in sorted(files):
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if name not in ALLOWED_NAMES and path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            size = path.stat().st_size
            if size > MAX_FILE_BYTES:
                raise ValueError(f"oversized_input:{relative}")
            total += size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("project_input_budget_exceeded")
            rows.append({
                "relative_path": relative,
                "relative_path_digest": hashlib.sha256(relative.encode()).hexdigest(),
                "size_bytes": size,
                "content_digest": hashlib.sha256(path.read_bytes()).hexdigest(),
                "suffix": path.suffix.lower(),
            })
            if len(rows) > MAX_FILES:
                raise ValueError("project_file_count_exceeded")
    return rows, total


def _project_kind(files: list[Mapping[str, Any]], isolated: bool, request: str = "") -> str:
    if isolated:
        lowered = request.casefold()
        python_markers = ("python", "python3", "python cli", "py cli")
        javascript_markers = ("node", "javascript", "command-line", "command line", "cli", "utility", "tool")
        web_markers = ("webpage", "web page", "website", "browser", "html", "frontend", "front-end")
        if any(marker in lowered for marker in python_markers) and not any(marker in lowered for marker in web_markers):
            return "new_python_cli_project"
        if any(marker in lowered for marker in javascript_markers) and not any(marker in lowered for marker in web_markers):
            return "new_javascript_tool_project"
        return "new_small_web_project"
    names = {str(row.get("relative_path") or "").lower() for row in files}
    suffixes = {str(row.get("suffix") or "") for row in files}
    has_web = ".html" in suffixes or ".css" in suffixes
    has_javascript = "package.json" in names or bool({".js", ".mjs", ".cjs"} & suffixes)
    has_python = "pyproject.toml" in names or "requirements.txt" in names or ".py" in suffixes
    if has_web: return "javascript_or_web_project" if has_javascript else "static_web_project"
    if has_javascript: return "javascript_tool_project"
    if has_python: return "python_project"
    if not files:
        return "empty_project"
    return "unsupported_project_type"


def _planned_files(request: str, kind: str, existing: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    explicit = parse_change_directives(request, existing)
    if explicit: return explicit
    names = {str(row.get("relative_path") or "") for row in existing}
    lower = request.casefold()
    if kind in {"new_small_web_project", "static_web_project", "javascript_or_web_project", "empty_project"}:
        candidates = ["index.html", "styles.css", "app.js"]
        if "test" in lower or kind == "javascript_or_web_project":
            candidates.append("tests/app.test.js")
    elif kind in {"new_javascript_tool_project", "javascript_tool_project"}:
        candidates = ["package.json", "cli.js", "lib/tool.js", "tests/tool.test.js"]
    elif kind == "new_python_cli_project":
        candidates = ["main.py", "tool.py", "tests/test_tool.py", "README.md"]
    elif kind == "python_project":
        candidates = ["main.py", "tests/test_main.py"]
    else:
        candidates = []
    return [{
        "relative_path": name,
        "relative_path_digest": hashlib.sha256(name.encode()).hexdigest(),
        "operation": "modify" if name in names else "create",
        "authority": "future_isolated_workspace_only",
    } for name in candidates]


def _test_plan(kind: str) -> list[dict[str, str]]:
    if kind in {"new_small_web_project", "static_web_project", "empty_project"}:
        return [
            {"adapter": "browser", "purpose": "Render the page and verify the primary interaction."},
            {"adapter": "javascript", "purpose": "Validate deterministic client-side behavior without network access."},
        ]
    if kind == "javascript_or_web_project":
        return [
            {"adapter": "node", "purpose": "Run the project-owned JavaScript test entry point when allowlisted later."},
            {"adapter": "browser", "purpose": "Verify the requested user flow in an isolated browser workspace."},
        ]
    if kind in {"new_javascript_tool_project", "javascript_tool_project"}:
        return [
            {"adapter": "javascript_syntax", "purpose": "Validate every generated JavaScript module with Node syntax checking."},
            {"adapter": "node_cli_smoke", "purpose": "Run the generated CLI with --help under a bounded, network-free process contract."},
        ]
    if kind == "new_python_cli_project":
        return [
            {"adapter": "python_syntax", "purpose": "Compile every generated Python module without writing bytecode."},
            {"adapter": "python_cli_smoke", "purpose": "Run the generated CLI with --help under a bounded, network-free process contract."},
        ]
    if kind == "python_project":
        return [{"adapter": "python", "purpose": "Run focused project tests in the isolated workspace."}]
    return []


def _seal_plan(plan: dict[str, Any]) -> dict[str, Any]:
    plan["planning_digest"] = _digest({k: v for k, v in plan.items() if k != "planning_digest"})
    return plan


def _valid_plan(plan: Mapping[str, Any]) -> bool:
    supplied = str(plan.get("planning_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in plan.items() if k != "planning_digest"}))


def create_or_resume_grounded_plan(
    proposal_id: str, *, expected_revision: int, expected_revision_digest: str,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        proposal_path = _proposal_path(proposal_id, runtime_root)
        proposal = _read_json(proposal_path)
        if not proposal or not _validate(proposal):
            return {"ok": False, "status": "proposal_missing_or_tampered"}
        if int(proposal.get("revision") or 0) != int(expected_revision) or proposal.get("revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if proposal.get("lifecycle_state") not in {"approved_pending_grounded_specification", "grounded_plan_ready"}:
            return {"ok": False, "status": "approval_required", "lifecycle_state": proposal.get("lifecycle_state")}
        if not proposal.get("approval_consumed") or int(proposal.get("approval_consumption_count") or 0) != 1:
            return {"ok": False, "status": "valid_consumed_approval_required"}

        path = _planning_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid_plan(existing) or existing.get("proposal_revision_digest") != expected_revision_digest:
                return {"ok": False, "status": "planning_record_invalid"}
            result = dict(existing)
            result["operation_status"] = "resumed"
            return result

        target = dict(proposal.get("target") or {})
        isolated = target.get("mode") == "isolated_workspace"
        try:
            root = None if isolated else _safe_root(str(target.get("private_path") or ""))
            files, total = ([], 0) if isolated else _inventory(root)
            kind = _project_kind(files, isolated, str(proposal.get("request") or ""))
            if kind == "unsupported_project_type":
                status = "unsupported_project_type"
            else:
                status = "grounded_plan_ready"
        except (OSError, ValueError) as exc:
            return {"ok": False, "status": "inspection_rejected", "reason": str(exc)}

        try:
            planned = _planned_files(str(proposal.get("request") or ""), kind, files)
        except ValueError as exc:
            return {"ok": False, "status": "change_plan_rejected", "reason": str(exc)}
        tests = _test_plan(kind)
        inventory_digest = _digest([{k: row[k] for k in ("relative_path_digest", "size_bytes", "content_digest")} for row in files])
        project_snapshot_digest = _digest({
            "target_digest": target.get("target_digest"), "inventory_digest": inventory_digest,
            "file_count": len(files), "total_bytes": total, "project_kind": kind,
        })
        created = _now()
        plan: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "request_digest": proposal.get("request_digest"),
            "target_digest": target.get("target_digest"),
            "approval_receipt_digest": proposal.get("approval_receipt_digest"),
            "planning_status": status,
            "project_kind": kind,
            "project_snapshot_digest": project_snapshot_digest,
            "inventory": files,
            "inventory_digest": inventory_digest,
            "inspected_file_count": len(files),
            "inspected_total_bytes": total,
            "specification": {
                "objective": str(proposal.get("request") or ""),
                "scope": "A bounded small-project implementation in an isolated external workspace.",
                "acceptance": ["Requested primary behavior is present.", "Focused tests pass.", "Selected project remains unmodified during planning."],
                "non_goals": ["No provider generation in this bundle.", "No command execution or implementation mutation.", "No Eidolon source or release authority."],
            },
            "file_plan": planned,
            "risk_assessment": {
                "level": "high" if kind == "unsupported_project_type" else ("low" if isolated or len(files) < 25 else "medium"),
                "reasons": ["Project snapshot is digest-bound.", "Future changes must remain inside an isolated workspace.", "Stale snapshots require replanning."],
            },
            "test_plan": tests,
            "created_at": created,
            "provider_contacted": False,
            "model_contacted": False,
            "implementation_started": False,
            "workspace_created": False,
            "command_executed": False,
            "selected_project_modified": False,
            "source_modified": False,
            "release_authorized": False,
            "authority_granted": False,
        }
        _seal_plan(plan)
        _atomic_json(path, plan)
        proposal["lifecycle_state"] = status
        proposal["grounded_plan_digest"] = plan["planning_digest"]
        proposal["project_snapshot_digest"] = project_snapshot_digest
        proposal["planned_next_step"] = (
            "Review the grounded specification, file plan, risk assessment, and test plan. Provider-generated structured output remains deferred to v1200.7-v1200.9."
            if status == "grounded_plan_ready" else "Narrow the request or select a supported web, JavaScript, or Python project."
        )
        proposal["updated_at"] = created
        _seal(proposal)
        _atomic_json(proposal_path, proposal)
        _event(proposal, "grounded_plan_created", runtime_root=runtime_root, details={
            "planning_digest": plan["planning_digest"], "project_snapshot_digest": project_snapshot_digest,
            "planning_status": status, "inspected_file_count": len(files),
        })
        _seal(proposal)
        _atomic_json(proposal_path, proposal)
        result = dict(plan)
        result["operation_status"] = "created"
        return result


def load_grounded_plan(proposal_id: str, revision: int, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    plan = _read_json(_planning_path(proposal_id, revision, runtime_root))
    return plan if plan and _valid_plan(plan) else {}


def public_grounded_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": plan.get("schema_version", SCHEMA_VERSION),
        "contract_version": plan.get("contract_version", CONTRACT_VERSION),
        "proposal_id": plan.get("proposal_id", ""),
        "proposal_revision": int(plan.get("proposal_revision") or 0),
        "proposal_revision_digest": plan.get("proposal_revision_digest", ""),
        "request_digest": plan.get("request_digest", ""),
        "target_digest": plan.get("target_digest", ""),
        "approval_receipt_digest": plan.get("approval_receipt_digest", ""),
        "planning_status": plan.get("planning_status", ""),
        "project_kind": plan.get("project_kind", ""),
        "project_snapshot_digest": plan.get("project_snapshot_digest", ""),
        "inventory_digest": plan.get("inventory_digest", ""),
        "inspected_file_count": int(plan.get("inspected_file_count") or 0),
        "inspected_total_bytes": int(plan.get("inspected_total_bytes") or 0),
        "planned_file_count": len(plan.get("file_plan") or []),
        "planned_file_digests": [row.get("relative_path_digest", "") for row in plan.get("file_plan") or []],
        "planned_operations": [row.get("operation", "") for row in plan.get("file_plan") or []],
        "risk_level": (plan.get("risk_assessment") or {}).get("level", "unknown"),
        "test_adapters": [row.get("adapter", "") for row in plan.get("test_plan") or []],
        "planning_digest": plan.get("planning_digest", ""),
        "content_free_public_projection": True,
        "private_request_included": False,
        "private_path_included": False,
        "source_content_included": False,
        "provider_contacted": False,
        "implementation_started": False,
        "command_executed": False,
        "selected_project_modified": False,
        "authority_granted": False,
    }
