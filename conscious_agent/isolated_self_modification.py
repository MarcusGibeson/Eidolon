from __future__ import annotations

"""v1265.3-v1265.5 authorized mutation of a clean Eidolon copy only."""

import ast
import difflib
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from ordinary_chat_development_campaign import _proposal_lock
from isolated_self_modification_foundations import (
    CONTRACT_VERSION as FOUNDATION_CONTRACT,
    SELF_MODIFICATION_DENIED_AUTHORITY,
    _digest, _is_link_like, _record_digest, _record_path, _runtime_root, _safe_relative, _write_json,
    check_self_source_freshness, load_self_modification, source_only_manifest,
)

CONTRACT_VERSION = "v1265.5"
MAX_CHANGED_FILES = 32
MAX_CHANGE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_CHANGE_BYTES = 8 * 1024 * 1024


def _provider_request(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "operation_id": record.get("operation_id", ""),
        "objective_code": record.get("objective_code", ""),
        "category": record.get("category", ""),
        "selected_strategy_code": record.get("selected_strategy_code", ""),
        "plan_digest": record.get("plan_digest", ""),
        "source_manifest_digest": record.get("source_manifest_digest", ""),
        "workspace_baseline_manifest_digest": record.get("workspace_baseline_manifest_digest", ""),
        "requested_output": "bounded_structured_source_changes",
        "active_source_mutation_authorized": False,
        "application_authorized": False,
        "release_authorized": False,
    }


def _normalize_changes(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = list(raw.get("changes") or [])
    if not values or len(values) > MAX_CHANGED_FILES:
        raise ValueError("self_modification_change_count_invalid")
    rows: list[dict[str, Any]] = []
    total = 0
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, Mapping):
            raise ValueError("self_modification_change_invalid")
        rel = _safe_relative(str(item.get("path") or ""))
        key = rel.casefold()
        if key in seen:
            raise ValueError("self_modification_duplicate_or_casefold_change")
        seen.add(key)
        action = str(item.get("action") or "modify")
        if action not in {"create", "modify", "delete"}:
            raise ValueError("self_modification_action_invalid")
        content = str(item.get("content") or "") if action != "delete" else ""
        data = content.encode("utf-8")
        if len(data) > MAX_CHANGE_BYTES:
            raise ValueError("self_modification_change_too_large")
        total += len(data)
        if total > MAX_TOTAL_CHANGE_BYTES:
            raise ValueError("self_modification_changes_too_large")
        rows.append({"relative_path": rel, "action": action, "content": content})
    return rows


def _apply_transactionally(workspace: Path, changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    staged = Path(tempfile.mkdtemp(prefix="selfmod-stage-", dir=str(workspace.parent)))
    try:
        shutil.copytree(workspace, staged / "Eidolon", dirs_exist_ok=True)
        target_root = staged / "Eidolon"
        review: list[dict[str, Any]] = []
        for change in changes:
            rel = change["relative_path"]
            target = target_root / rel
            if _is_link_like(target.parent) or (target.exists() and _is_link_like(target)):
                raise ValueError("self_modification_link_boundary_rejected")
            before = ""
            before_text = ""
            if target.exists():
                if not target.is_file():
                    raise ValueError("self_modification_target_not_regular_file")
                before = hashlib.sha256(target.read_bytes()).hexdigest()
                try: before_text = target.read_text(encoding="utf-8")
                except UnicodeError: before_text = ""
            action = change["action"]
            if action == "create" and target.exists():
                raise ValueError("self_modification_create_target_exists")
            if action in {"modify", "delete"} and not target.exists():
                raise ValueError("self_modification_target_missing")
            if action == "delete":
                target.unlink()
                after = ""
                after_text = ""
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(change["content"], encoding="utf-8")
                after = hashlib.sha256(target.read_bytes()).hexdigest()
                after_text = change["content"]
                if target.suffix.casefold() == ".py":
                    try: ast.parse(after_text, filename=rel)
                    except SyntaxError as exc: raise ValueError("self_modification_python_syntax_invalid") from exc
            delta = list(difflib.unified_diff(before_text.splitlines(), after_text.splitlines(), lineterm=""))
            review.append({
                "relative_path": rel, "action": action, "before_digest": before, "after_digest": after,
                "added_line_count": sum(1 for line in delta if line.startswith("+") and not line.startswith("+++")),
                "removed_line_count": sum(1 for line in delta if line.startswith("-") and not line.startswith("---")),
                "content_exposed": False,
            })
        # Replace only the disposable workspace, never the active source.
        backup = workspace.parent / "Eidolon.pre-transaction"
        if backup.exists(): shutil.rmtree(backup)
        os.replace(workspace, backup)
        try:
            os.replace(target_root, workspace)
        except Exception:
            os.replace(backup, workspace)
            raise
        shutil.rmtree(backup, ignore_errors=True)
        return review
    finally:
        shutil.rmtree(staged, ignore_errors=True)


def execute_isolated_self_modification(
    operation_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    authorization_phrase: str,
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    with _proposal_lock("devc_" + operation_id.split("_", 1)[1], runtime):
        path = _record_path(operation_id, runtime)
        record = load_self_modification(operation_id, runtime_root=runtime)
        if not record:
            raise ValueError("self_modification_record_missing")
        if record.get("phase") == "sealed":
            return {**record, "operation_status": "restored", "provider_called_this_invocation": False}
        if record.get("phase") != "prepared":
            raise ValueError("self_modification_phase_invalid")
        if str(authorization_phrase or "") != str(record.get("authorization_phrase") or ""):
            return {"ok": False, "status": "isolated_self_modification_exact_authorization_required", "operation_id": operation_id, "provider_contacted": False, "active_source_modified": False, **SELF_MODIFICATION_DENIED_AUTHORITY}
        freshness = check_self_source_freshness(operation_id, source_root, runtime_root=runtime)
        if not freshness.get("ok"):
            return {"ok": False, "status": "stale_self_source_detected", "operation_id": operation_id, "provider_contacted": False, "active_source_modified": False, **SELF_MODIFICATION_DENIED_AUTHORITY}
        workspace = Path(str(record.get("workspace_path") or "")).resolve(strict=True)
        current_workspace = source_only_manifest(workspace)
        if current_workspace["source_manifest_digest"] != record.get("workspace_baseline_manifest_digest"):
            return {"ok": False, "status": "isolated_self_workspace_changed_before_authorization", "operation_id": operation_id, "provider_contacted": False, "active_source_modified": False, **SELF_MODIFICATION_DENIED_AUTHORITY}
        active_before = source_only_manifest(source_root)["source_manifest_digest"]
        running = dict(record); running.update({"phase": "running", "status": "isolated_self_modification_running", "provider_contacted": False})
        running["record_digest"] = _record_digest(running); _write_json(path, running)
        try:
            response = provider(_provider_request(record))
            changes = _normalize_changes(response)
            review = _apply_transactionally(workspace, changes)
        except Exception as exc:
            failed = dict(record); failed.update({"phase": "blocked", "status": "isolated_self_modification_blocked", "blocker_code": str(exc)[:160], "provider_contacted": True, "active_source_modified": False, "isolated_workspace_modified": False})
            failed["record_digest"] = _record_digest(failed); _write_json(path, failed)
            return {**failed, "provider_called_this_invocation": True}
        active_after = source_only_manifest(source_root)["source_manifest_digest"]
        if active_after != active_before or active_after != record.get("source_manifest_digest"):
            raise RuntimeError("active_source_changed_during_isolated_self_modification")
        candidate = source_only_manifest(workspace)
        result = {
            "changed_files": review, "changed_file_count": len(review),
            "candidate_manifest_digest": candidate["source_manifest_digest"], "candidate_file_count": candidate["file_count"],
            "baseline_manifest_digest": record.get("workspace_baseline_manifest_digest", ""),
            "candidate_diff_digest": _digest(review), "structural_python_validation": "passed",
            "tests_executed": False, "content_minimized": True,
        }
        sealed = dict(record)
        sealed.update({
            "contract_version": CONTRACT_VERSION, "phase": "sealed", "status": "isolated_self_modification_candidate_ready",
            "provider_contacted": True, "isolated_workspace_modified": True, "active_source_modified": False,
            "candidate_review_available": True, "authorization_consumed": True, "result": result, "result_digest": _digest(result),
            "source_application_authorized": False, "installation_authorized": False, "release_authorized": False, "self_update_authorized": False,
        })
        sealed["record_digest"] = _record_digest(sealed); _write_json(path, sealed)
        return {**sealed, "operation_status": "completed", "provider_called_this_invocation": True}


def public_self_modification_result(record: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(record.get("result") or {})
    return {
        "ok": record.get("ok") is True and record.get("phase") == "sealed",
        "status": record.get("status", ""), "operation_id": record.get("operation_id", ""),
        "plan_digest": record.get("plan_digest", ""), "source_manifest_digest": record.get("source_manifest_digest", ""),
        "candidate_manifest_digest": result.get("candidate_manifest_digest", ""), "changed_files": result.get("changed_files", []),
        "changed_file_count": result.get("changed_file_count", 0), "candidate_diff_digest": result.get("candidate_diff_digest", ""),
        "operator_review_required": True, "active_source_modified": False, "tests_executed": False,
        "application_authorized": False, "self_update_authorized": False, "release_authorized": False, "content_minimized": True,
    }


__all__ = ["CONTRACT_VERSION", "execute_isolated_self_modification", "public_self_modification_result"]
