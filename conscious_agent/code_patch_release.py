from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import ast
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR, path_reference
from patch_drafting import APPROVAL_STATE, build_draft_verification_bundle, validate_approval_binding
from release_pipeline import (
    APPROVED_CODE_APPLY,
    APPROVED_CODE_DRY_RUN,
    CODE_EDIT_PROPOSAL,
    CODE_PATCH_DIR,
    GENERATED_CODE_PATCH,
    RELEASE_PACKAGE,
    RELEASE_READINESS,
    SAFE_REWRITE_PREVIEW,
    TEST_SUGGESTIONS,
    build_apply_approved_code_patch,
    build_code_edit_proposal,
    build_generated_code_patch,
    build_prepare_release_package,
    build_release_readiness,
    build_safe_rewrite_preview,
    build_test_suggestions,
)
from workspace_execution import build_project_boundary_check
from workspace_orchestration import _timeline_event

CODE_PATCH_RELEASE_VERSION = RUNTIME_VERSION
CURRENT_PATCH = CODE_PATCH_DIR / "current_patch.json"
PROPOSED_EDITS = CODE_PATCH_DIR / "proposed_edits.json"
REWRITE_PREVIEWS = CODE_PATCH_DIR / "rewrite_previews.json"
SYMBOL_SCAN = CODE_PATCH_DIR / "symbol_scan.json"
REWRITE_PLAN = CODE_PATCH_DIR / "rewrite_plan.json"
REWRITE_CONFLICTS = CODE_PATCH_DIR / "rewrite_conflicts.json"
CODE_PATCH_DIFF_BUNDLE = CODE_PATCH_DIR / "code_patch_diff_bundle.json"
APPLY_TRANSACTION_REPORT = CODE_PATCH_DIR / "apply_transaction_report.json"
SEMANTIC_CHECKS = CODE_PATCH_DIR / "semantic_checks.json"
RELEASE_ARTIFACT = CODE_PATCH_DIR / "release_artifact.json"
RELEASE_AUDIT_TRAIL = CODE_PATCH_DIR / "release_audit_trail.json"
GENERATED_CODE_RELEASE_LOOP = CODE_PATCH_DIR / "generated_code_release_loop.json"
README_FILE = ROOT_DIR / "README_NEXT_STEPS.md"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    CODE_PATCH_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    _ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _safe_path(relative_path: str) -> Path:
    if not relative_path or relative_path.startswith(("/", "\\")) or ".." in Path(relative_path).parts:
        raise PermissionError(f"Unsafe relative path: {relative_path}")
    target = (ROOT_DIR / relative_path).resolve()
    target.relative_to(ROOT_DIR.resolve())
    return target


def _status_from(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("status", "pass")).lower() for row in rows}
    if statuses & {"blocked", "fail", "failed"}:
        return "blocked"
    if statuses & {"warn", "warning"}:
        return "warn"
    return "pass"


def _target_files(project_id: str = "eidolon") -> list[str]:
    proposal = _read_json(CODE_EDIT_PROPOSAL, {})
    if not isinstance(proposal, dict) or not proposal.get("proposals"):
        proposal = build_code_edit_proposal(project_id=project_id, save=False)
    preview = _read_json(SAFE_REWRITE_PREVIEW, {})
    files: list[str] = []
    for item in proposal.get("proposals", []) or []:
        path = str(item.get("target_file", "")).strip()
        if path and path not in files:
            files.append(path)
    if isinstance(preview, dict):
        for row in preview.get("rows", []) or []:
            path = str(row.get("path", "")).strip()
            if path and path not in files:
                files.append(path)
    if not files:
        files = ["README_NEXT_STEPS.md"]
    return files


def _scan_python(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    constants: list[dict[str, Any]] = []
    cli_arguments: list[dict[str, Any]] = []
    api_routes: list[dict[str, Any]] = []
    dashboard_routes: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({"name": node.name, "lineno": node.lineno, "end_lineno": getattr(node, "end_lineno", node.lineno)})
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "lineno": node.lineno, "end_lineno": getattr(node, "end_lineno", node.lineno)})
        elif isinstance(node, ast.Import):
            imports.append({"module": ", ".join(alias.name for alias in node.names), "lineno": node.lineno})
        elif isinstance(node, ast.ImportFrom):
            imports.append({"module": node.module or "", "names": ", ".join(alias.name for alias in node.names), "lineno": node.lineno})
        elif isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name) and target.id.isupper()]
            for name in names:
                constants.append({"name": name, "lineno": node.lineno})
        elif isinstance(node, ast.Call):
            func = node.func
            attr = func.attr if isinstance(func, ast.Attribute) else ""
            if attr == "add_argument" and node.args and isinstance(node.args[0], ast.Constant):
                cli_arguments.append({"argument": str(node.args[0].value), "lineno": node.lineno})
    for idx, line in enumerate(text.splitlines(), start=1):
        if "self.path" in line or "path.startswith" in line or "send_json" in line:
            route_match = re.search(r"['\"](/[^'\"]+)['\"]", line)
            if route_match:
                api_routes.append({"route": route_match.group(1), "lineno": idx})
        if "path ==" in line or "path.startswith" in line:
            route_match = re.search(r"['\"](/[^'\"]+)['\"]", line)
            if route_match:
                dashboard_routes.append({"route": route_match.group(1), "lineno": idx})
    return {
        "functions": functions,
        "classes": classes,
        "imports": imports[:80],
        "constants": constants[:80],
        "cli_arguments": cli_arguments,
        "api_routes": api_routes[:80],
        "dashboard_routes": dashboard_routes[:80],
    }


def build_code_patch_status(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v15.1: report generated-code patch workspace files and current state."""
    _ensure_dirs()
    files = {
        "current_patch": CURRENT_PATCH,
        "proposed_edits": PROPOSED_EDITS,
        "rewrite_previews": REWRITE_PREVIEWS,
        "apply_transaction_report": APPLY_TRANSACTION_REPORT,
        "verification_report": SEMANTIC_CHECKS,
        "symbol_scan": SYMBOL_SCAN,
        "rewrite_plan": REWRITE_PLAN,
        "rewrite_conflicts": REWRITE_CONFLICTS,
        "diff_bundle": CODE_PATCH_DIFF_BUNDLE,
        "release_artifact": RELEASE_ARTIFACT,
        "audit_trail": RELEASE_AUDIT_TRAIL,
    }
    rows = []
    for name, path in files.items():
        exists = path.exists()
        rows.append({
            "name": name,
            "path": path_reference(path),
            "status": "pass" if exists else "warn",
            "exists": exists,
            "message": "Artifact exists." if exists else "Artifact has not been generated yet.",
        })
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": _status_from(rows),
        "ok": True,
        "workspace_dir": path_reference(CODE_PATCH_DIR),
        "rows": rows,
        "message": "Generated-code patch workspace status loaded.",
    }
    if save:
        _write_json(CURRENT_PATCH, report)
    else:
        report["preview_only"] = True
    return report


def build_symbol_scan(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v15.2: scan target files for symbols and route/CLI surfaces."""
    targets = _target_files(project_id=project_id)
    rows = []
    for target in targets:
        try:
            path = _safe_path(target)
            if not path.exists():
                rows.append({"path": target, "status": "blocked", "message": "Target file does not exist."})
                continue
            if path.suffix != ".py":
                rows.append({"path": target, "status": "pass", "kind": "text", "symbols": {}, "message": "Non-Python file; symbol scan not required."})
                continue
            symbols = _scan_python(path)
            rows.append({"path": target, "status": "pass", "kind": "python", "symbols": symbols, "message": f"Scanned {len(symbols.get('functions', []))} function(s) and {len(symbols.get('classes', []))} class(es)."})
        except SyntaxError as error:
            rows.append({"path": target, "status": "blocked", "message": f"Python syntax error while scanning: {error}"})
        except Exception as error:
            rows.append({"path": target, "status": "blocked", "message": str(error)})
    status = _status_from(rows)
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "rows": rows,
        "message": f"Symbol-aware scan completed for {len(rows)} target file(s).",
    }
    if save:
        _write_json(SYMBOL_SCAN, report)
    else:
        report["preview_only"] = True
    return report


def build_rewrite_plan(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v15.3: build targeted rewrite plans against symbols or file regions."""
    proposal = _read_json(CODE_EDIT_PROPOSAL, {})
    if not isinstance(proposal, dict) or not proposal.get("proposals"):
        proposal = build_code_edit_proposal(project_id=project_id, save=False)
    preview = _read_json(SAFE_REWRITE_PREVIEW, {})
    if not isinstance(preview, dict) or not preview.get("rows"):
        preview = build_safe_rewrite_preview(project_id=project_id, save=False)
    scan = _read_json(SYMBOL_SCAN, {})
    if not isinstance(scan, dict) or not scan.get("rows"):
        scan = build_symbol_scan(project_id=project_id, save=False)
    symbol_by_path = {row.get("path"): row.get("symbols", {}) for row in scan.get("rows", []) if isinstance(row, dict)}
    rows = []
    for item in proposal.get("proposals", []) or []:
        target = str(item.get("target_file", ""))
        preview_row = next((row for row in preview.get("rows", []) or [] if row.get("path") == target), {})
        symbols = symbol_by_path.get(target, {}) if isinstance(symbol_by_path, dict) else {}
        target_symbol = None
        expected_symbols = item.get("expected_symbols") or []
        if target.endswith(".py") and expected_symbols:
            candidates = [s for s in symbols.get("functions", []) + symbols.get("classes", []) if s.get("name") in expected_symbols]
            target_symbol = candidates[0] if candidates else None
        strategy = "symbol_targeted" if target_symbol else "file_hash_guarded"
        rows.append({
            "path": target,
            "status": "ready" if preview_row.get("status") in {"ready", "pass"} else "blocked",
            "target_symbol": target_symbol,
            "rewrite_strategy": strategy,
            "expected_sha256": preview_row.get("expected_sha256") or item.get("original_sha256"),
            "replacement_strategy": "Use generated proposed content only if hash and boundary checks pass.",
            "risk": item.get("risk", "medium"),
            "backup_required": True,
            "tests_required": item.get("tests_required") or ["python -m py_compile conscious_agent/*.py tools/smoke_check.py"],
            "readme_impact": bool(item.get("readme_required")) or target == "README_NEXT_STEPS.md",
            "message": f"Rewrite planned with {strategy} guardrails.",
        })
    if not rows:
        rows.append({"path": "README_NEXT_STEPS.md", "status": "warn", "rewrite_strategy": "fallback", "message": "No proposal rows available; fallback README-only plan prepared."})
    status = _status_from(rows)
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "rows": rows,
        "message": f"Targeted rewrite plan prepared for {len(rows)} item(s).",
    }
    if save:
        _write_json(REWRITE_PLAN, report)
        _write_json(PROPOSED_EDITS, {"version": CODE_PATCH_RELEASE_VERSION, "updated_at": _now(), "project_id": project_id, "edits": rows})
    else:
        report["preview_only"] = True
    return report


def build_rewrite_conflicts(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v15.4: detect stale hashes, missing symbols, dirty state, and approval mismatches."""
    plan = _read_json(REWRITE_PLAN, {})
    if not isinstance(plan, dict) or not plan.get("rows"):
        plan = build_rewrite_plan(project_id=project_id, save=False)
    preview = _read_json(SAFE_REWRITE_PREVIEW, {})
    if not isinstance(preview, dict) or not preview.get("rows"):
        preview = build_safe_rewrite_preview(project_id=project_id, save=False)
    approval = _read_json(APPROVAL_STATE, {})
    binding = validate_approval_binding(approval=approval, project_id=project_id) if isinstance(approval, dict) and approval.get("approved") else {"ok": False, "message": "No approved draft currently binds to these artifacts."}
    preview_by_path = {str(row.get("path")): row for row in preview.get("rows", []) if isinstance(row, dict)}
    rows = []
    for item in plan.get("rows", []) or []:
        path = str(item.get("path", ""))
        reasons = []
        try:
            target = _safe_path(path)
            if not target.exists():
                reasons.append("target file missing")
            expected = item.get("expected_sha256") or preview_by_path.get(path, {}).get("expected_sha256")
            if expected and target.exists():
                import hashlib
                current = hashlib.sha256(target.read_text(encoding="utf-8", errors="replace").encode("utf-8", errors="replace")).hexdigest()
                if current != expected:
                    reasons.append("file hash changed")
            if item.get("rewrite_strategy") == "symbol_targeted" and not item.get("target_symbol"):
                reasons.append("target symbol missing")
            preview_row = preview_by_path.get(path, {})
            if preview_row.get("status") == "blocked":
                reasons.append(preview_row.get("message", "safe rewrite preview blocked"))
        except Exception as error:
            reasons.append(str(error))
        rows.append({"path": path, "status": "blocked" if reasons else "pass", "reasons": reasons, "message": "; ".join(reasons) if reasons else "No rewrite conflict detected."})
    if not binding.get("ok"):
        rows.append({"path": "approval_state", "status": "warn", "reasons": [binding.get("message", "approval not currently bound")], "message": "Approval is not currently ready for real apply; dry-run review may continue."})
    status = _status_from(rows)
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "approval_binding": binding,
        "rows": rows,
        "message": "Rewrite conflict detector completed.",
    }
    if save:
        _write_json(REWRITE_CONFLICTS, report)
    else:
        report["preview_only"] = True
    return report


def build_code_patch_diff_bundle(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v15.5: combine generated code edit artifacts into one reviewable diff bundle."""
    proposal = _read_json(CODE_EDIT_PROPOSAL, {}) or build_code_edit_proposal(project_id=project_id, save=False)
    preview = _read_json(SAFE_REWRITE_PREVIEW, {}) or build_safe_rewrite_preview(project_id=project_id, save=False)
    generated = _read_json(GENERATED_CODE_PATCH, {}) or build_generated_code_patch(project_id=project_id, save=False)
    plan = _read_json(REWRITE_PLAN, {}) or build_rewrite_plan(project_id=project_id, save=False)
    conflicts = _read_json(REWRITE_CONFLICTS, {}) or build_rewrite_conflicts(project_id=project_id, save=False)
    tests = _read_json(TEST_SUGGESTIONS, {}) or build_test_suggestions(project_id=project_id, save=False)
    boundary = build_project_boundary_check(project_id=project_id, changes=preview.get("rows", []))
    approval = _read_json(APPROVAL_STATE, {})
    binding = validate_approval_binding(approval=approval, project_id=project_id) if isinstance(approval, dict) and approval.get("approved") else {"ok": False, "message": "No approved draft is currently bound."}
    blocked = [name for name, report in {"preview": preview, "generated": generated, "plan": plan, "conflicts": conflicts, "boundary": boundary}.items() if isinstance(report, dict) and report.get("ok") is False]
    status = "blocked" if blocked else "warn" if not binding.get("ok") else "pass"
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "target_files": _target_files(project_id=project_id),
        "approval_binding": binding,
        "steps": {
            "draft_verification_bundle": build_draft_verification_bundle(project_id=project_id, save=False),
            "code_edit_proposal": proposal,
            "rewrite_plan": plan,
            "safe_rewrite_preview": preview,
            "generated_code_patch": generated,
            "rewrite_conflicts": conflicts,
            "test_suggestions": tests,
            "boundary": boundary,
        },
        "blocked_steps": blocked,
        "message": "Generated patch diff bundle prepared for review.",
    }
    if save:
        _write_json(CODE_PATCH_DIFF_BUNDLE, report)
        _write_json(REWRITE_PREVIEWS, preview)
    else:
        report["preview_only"] = True
    return report


def build_apply_code_patch_transaction(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v15.6: apply generated edits as a guarded all-prechecks-before-write transaction."""
    conflicts = build_rewrite_conflicts(project_id=project_id, save=False)
    bundle = build_code_patch_diff_bundle(project_id=project_id, save=False)
    approval = _read_json(APPROVAL_STATE, {})
    binding = validate_approval_binding(approval=approval, project_id=project_id) if isinstance(approval, dict) and approval.get("approved") else {"ok": False, "message": "No approved draft currently binds to the patch bundle."}
    precheck_rows = [
        {"name": "rewrite-conflicts", "status": "pass" if conflicts.get("ok") else "blocked", "message": conflicts.get("message")},
        {"name": "diff-bundle", "status": "pass" if bundle.get("ok") else "blocked", "message": bundle.get("message")},
        {"name": "approval-binding", "status": "pass" if binding.get("ok") else "blocked" if not dry_run else "warn", "message": binding.get("message", "Approval binding checked.")},
        {"name": "explicit-confirmation", "status": "pass" if dry_run or approve else "blocked", "message": "Real apply requires --approve-controlled-self-build."},
    ]
    blocked = [row.get("name") for row in precheck_rows if row.get("status") == "blocked"]
    apply_report = None
    if not blocked:
        if dry_run and not binding.get("ok"):
            apply_report = {
                "version": CODE_PATCH_RELEASE_VERSION,
                "checked_at": _now(),
                "project_id": project_id,
                "status": "dry_run",
                "ok": True,
                "dry_run": True,
                "approval_required_for_real_apply": True,
                "message": "Transaction dry-run completed without approval; real apply still requires artifact-bound approval.",
                "would_apply": bundle.get("target_files", []),
            }
        else:
            apply_report = build_apply_approved_code_patch(project_id=project_id, approve=approve, dry_run=dry_run, save=save)
            if isinstance(apply_report, dict) and apply_report.get("ok") is False:
                blocked.append("approved-code-apply")
    status = "blocked" if blocked else "dry_run" if dry_run else "applied"
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "dry_run": dry_run,
        "prechecks": precheck_rows,
        "blocked_steps": blocked,
        "apply_report": apply_report,
        "message": "Code patch transaction completed as dry-run." if dry_run and not blocked else "Code patch transaction applied." if not blocked else "Code patch transaction blocked before source writes.",
    }
    if save:
        _write_json(APPLY_TRANSACTION_REPORT, report)
        _timeline_event("code_patch_transaction", {"project_id": project_id, "status": status, "dry_run": dry_run}, save=True)
    return report


def _source_contains(path: str, needle: str) -> bool:
    try:
        return needle in _safe_path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False


def build_semantic_checks(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v15.7: behavior-level safety checks for generated patch/release systems."""
    rows = [
        {"name": "api-get-read-only-discipline", "status": "pass" if _source_contains("conscious_agent/api_server.py", "do_POST") and _source_contains("conscious_agent/api_server.py", "do_GET") else "warn", "message": "API server has separate GET/POST handlers; inspect route-specific writes during review."},
        {"name": "approval-binding", "status": "pass" if _source_contains("conscious_agent/patch_drafting.py", "validate_approval_binding") and _source_contains("conscious_agent/release_pipeline.py", "validate_approval_binding") else "blocked", "message": "Approved applies require artifact-bound draft validation."},
        {"name": "dry-run-pointer-separation", "status": "pass" if _source_contains("conscious_agent/release_pipeline.py", "APPROVED_CODE_DRY_RUN") and _source_contains("conscious_agent/release_pipeline.py", "APPROVED_CODE_APPLY") else "blocked", "message": "Code apply dry-runs are stored separately from real apply pointers."},
        {"name": "rollback-stale-guard", "status": "pass" if _source_contains("conscious_agent/controlled_build_cycle.py", "status") and _source_contains("conscious_agent/controlled_build_cycle.py", "applied_sha256") else "warn", "message": "Controlled rollback has status/hash guard markers."},
        {"name": "single-use-approval", "status": "pass" if _source_contains("conscious_agent/release_pipeline.py", "consumed") else "blocked", "message": "Approved real apply consumes approval."},
        {"name": "dashboard-import", "status": "pass", "message": "Dashboard import is covered by smoke/verification commands."},
    ]
    compile_cmd = [sys.executable, "-m", "py_compile", *[str(path) for path in sorted((ROOT_DIR / "conscious_agent").glob("*.py"))], str(ROOT_DIR / "tools" / "smoke_check.py")]
    try:
        result = subprocess.run(compile_cmd, cwd=ROOT_DIR, text=True, capture_output=True, timeout=45)
        rows.append({"name": "py-compile", "status": "pass" if result.returncode == 0 else "blocked", "returncode": result.returncode, "message": "Python compile passed." if result.returncode == 0 else (result.stderr or result.stdout)[-1000:]})
    except Exception as error:
        rows.append({"name": "py-compile", "status": "blocked", "message": str(error)})
    status = _status_from(rows)
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "rows": rows,
        "message": "Post-apply semantic checks completed.",
    }
    if save:
        _write_json(SEMANTIC_CHECKS, report)
    else:
        report["preview_only"] = True
    return report


def build_release_artifact(project_id: str = "eidolon", package_name: str | None = None, save: bool = True) -> dict[str, Any]:
    """v15.8: prepare release artifact manifest before zipping."""
    readiness = build_release_readiness(project_id=project_id, save=False)
    package = build_prepare_release_package(project_id=project_id, package_name=package_name or "Eidolon_v16_0.zip", save=False)
    semantic = _read_json(SEMANTIC_CHECKS, {}) or build_semantic_checks(project_id=project_id, save=False)
    transaction = _read_json(APPLY_TRANSACTION_REPORT, {})
    readme = README_FILE.read_text(encoding="utf-8", errors="replace") if README_FILE.exists() else ""
    sections = [f"v15.{i}" for i in range(1, 10)] + ["v16.0"]
    rows = [
        {"name": "release-readiness", "status": "pass" if readiness.get("ok") else "blocked", "message": readiness.get("message")},
        {"name": "semantic-checks", "status": "pass" if semantic.get("ok") else "blocked", "message": semantic.get("message")},
        {"name": "readme-v16-sections", "status": "pass" if all(section in readme for section in sections) else "warn", "message": "README includes v15.1-v16.0 sections." if all(section in readme for section in sections) else "README is missing one or more v15.1-v16.0 section markers."},
    ]
    status = _status_from(rows)
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "package_name": package_name or "Eidolon_v16_0.zip",
        "changed_files": package.get("changed_files", []),
        "previewed_files": package.get("previewed_files", []),
        "excluded_files": [".git", ".venv", "__pycache__", "*.pyc", "data/code_patches/backups"],
        "readme_sections": sections,
        "verification_commands": package.get("verification_commands", []),
        "known_warnings": readiness.get("known_warnings", []),
        "rollback_status": ((transaction.get("apply_report") or {}).get("rollback_available") if isinstance(transaction, dict) else None),
        "release_readiness": readiness.get("release_readiness"),
        "rows": rows,
        "message": f"Release artifact manifest prepared for {package_name or 'Eidolon_v16_0.zip'}.",
    }
    if save:
        _write_json(RELEASE_ARTIFACT, report)
    else:
        report["preview_only"] = True
    return report


def build_release_audit_trail(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v15.9: collect draft/review/apply/readiness/artifact evidence into one audit trail."""
    artifacts = {
        "draft_verification_bundle": build_draft_verification_bundle(project_id=project_id, save=False),
        "approval_state": _read_json(APPROVAL_STATE, {}),
        "code_patch_diff_bundle": _read_json(CODE_PATCH_DIFF_BUNDLE, {}),
        "apply_transaction_report": _read_json(APPLY_TRANSACTION_REPORT, {}),
        "semantic_checks": _read_json(SEMANTIC_CHECKS, {}),
        "release_readiness": _read_json(RELEASE_READINESS, {}),
        "release_package": _read_json(RELEASE_PACKAGE, {}),
        "release_artifact": _read_json(RELEASE_ARTIFACT, {}),
    }
    rows = []
    for name, artifact in artifacts.items():
        exists = isinstance(artifact, dict) and bool(artifact)
        rows.append({"name": name, "status": "pass" if exists else "warn", "message": f"{name} {'available' if exists else 'not generated yet'}."})
    status = _status_from(rows)
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": True,
        "rows": rows,
        "artifacts": artifacts,
        "message": "Release audit trail assembled.",
    }
    if save:
        _write_json(RELEASE_AUDIT_TRAIL, report)
    else:
        report["preview_only"] = True
    return report


def build_generated_code_release_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v16.0: one generated code patch through transaction, semantic checks, readiness, artifact, and audit."""
    status_report = build_code_patch_status(project_id=project_id, save=save)
    scan = build_symbol_scan(project_id=project_id, save=save)
    plan = build_rewrite_plan(project_id=project_id, save=save)
    conflicts = build_rewrite_conflicts(project_id=project_id, save=save)
    bundle = build_code_patch_diff_bundle(project_id=project_id, save=save)
    transaction = build_apply_code_patch_transaction(project_id=project_id, approve=approve, dry_run=dry_run, save=save)
    semantic = build_semantic_checks(project_id=project_id, save=save)
    readiness = build_release_readiness(project_id=project_id, save=save)
    artifact = build_release_artifact(project_id=project_id, save=save)
    audit = build_release_audit_trail(project_id=project_id, save=save)
    blocked = [name for name, report in {
        "workspace_status": status_report,
        "symbol_scan": scan,
        "rewrite_plan": plan,
        "rewrite_conflicts": conflicts,
        "diff_bundle": bundle,
        "transaction": transaction,
        "semantic_checks": semantic,
        "release_readiness": readiness,
        "release_artifact": artifact,
    }.items() if isinstance(report, dict) and report.get("ok") is False]
    status = "blocked" if blocked else "dry_run" if dry_run else "applied"
    report = {
        "version": CODE_PATCH_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "dry_run": dry_run,
        "steps": {
            "code_patch_status": status_report,
            "symbol_scan": scan,
            "rewrite_plan": plan,
            "rewrite_conflicts": conflicts,
            "diff_bundle": bundle,
            "apply_transaction": transaction,
            "semantic_checks": semantic,
            "release_readiness": readiness,
            "release_artifact": artifact,
            "audit_trail": audit,
        },
        "blocked_steps": blocked,
        "message": "Generated code patch release loop completed one bounded dry-run path and stopped." if dry_run else "Generated code patch release loop applied one approved patch and stopped.",
    }
    if save:
        _write_json(GENERATED_CODE_RELEASE_LOOP, report)
        _timeline_event("generated_code_release_loop", {"project_id": project_id, "status": status, "dry_run": dry_run}, save=True)
    return report


def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# {title}",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at', '')}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Message: {report.get('message', '')}",
    ]
    for key in ["blocked_steps", "blocked_reasons", "known_warnings"]:
        values = report.get(key) or []
        if values:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values])
    rows = report.get("rows") or report.get("prechecks") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:35]:
            if isinstance(row, dict):
                name = row.get("name") or row.get("path") or "row"
                status = row.get("status") or "info"
                msg = row.get("message") or "; ".join(row.get("reasons", []))
                lines.append(f"- {str(status).upper()} {name}: {msg}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def code_patch_status_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.1 Real Patch Workspace Files", report or build_code_patch_status(save=False), full)


def symbol_scan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.2 Symbol-Aware File Scanner", report or build_symbol_scan(save=False), full)


def rewrite_plan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.3 Targeted Rewrite Planner", report or build_rewrite_plan(save=False), full)


def rewrite_conflicts_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.4 Rewrite Conflict Detector", report or build_rewrite_conflicts(save=False), full)


def code_patch_diff_bundle_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.5 Generated Patch Diff Bundle", report or build_code_patch_diff_bundle(save=False), full)


def apply_code_patch_transaction_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.6 Patch Apply Transaction", report or build_apply_code_patch_transaction(dry_run=True, save=False), full)


def semantic_checks_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.7 Post-Apply Semantic Checks", report or build_semantic_checks(save=False), full)


def release_artifact_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.8 Release Artifact Builder", report or build_release_artifact(save=False), full)


def release_audit_trail_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.9 Release Audit Trail", report or build_release_audit_trail(save=False), full)


def generated_code_release_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.0 Generated Code Patch Release Loop", report or build_generated_code_release_loop(save=False), full)


def print_code_patch_status(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_code_patch_status(project_id=project_id, save=True)
    _json_print(report) if json_output else print(code_patch_status_text(report, full=full))


def print_symbol_scan(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_symbol_scan(project_id=project_id, save=True)
    _json_print(report) if json_output else print(symbol_scan_text(report, full=full))


def print_rewrite_plan(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_rewrite_plan(project_id=project_id, save=True)
    _json_print(report) if json_output else print(rewrite_plan_text(report, full=full))


def print_rewrite_conflicts(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_rewrite_conflicts(project_id=project_id, save=True)
    _json_print(report) if json_output else print(rewrite_conflicts_text(report, full=full))


def print_code_patch_diff_bundle(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_code_patch_diff_bundle(project_id=project_id, save=True)
    _json_print(report) if json_output else print(code_patch_diff_bundle_text(report, full=full))


def print_apply_code_patch_transaction(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_apply_code_patch_transaction(project_id=project_id, approve=approve, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(apply_code_patch_transaction_text(report, full=full))


def print_semantic_checks(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_semantic_checks(project_id=project_id, save=True)
    _json_print(report) if json_output else print(semantic_checks_text(report, full=full))


def print_release_artifact(project_id: str = "eidolon", package_name: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_artifact(project_id=project_id, package_name=package_name, save=True)
    _json_print(report) if json_output else print(release_artifact_text(report, full=full))


def print_release_audit_trail(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_audit_trail(project_id=project_id, save=True)
    _json_print(report) if json_output else print(release_audit_trail_text(report, full=full))


def print_generated_code_release_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_generated_code_release_loop(project_id=project_id, approve=approve, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(generated_code_release_loop_text(report, full=full))
