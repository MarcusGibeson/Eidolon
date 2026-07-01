from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from patch_drafting import (
    APPROVAL_STATE,
    CURRENT_DIFF,
    CURRENT_DRAFT,
    DRAFT_REQUEST,
    build_draft_diff,
    build_draft_review_checklist,
    build_draft_test_impact,
    build_draft_verification_bundle,
    build_patch_draft_request,
    build_draft_patch,
    validate_approval_binding,
)
from code_patch_release import (
    build_apply_code_patch_transaction,
    build_code_patch_diff_bundle,
    build_generated_code_release_loop,
    build_release_artifact,
    build_release_audit_trail,
    build_rewrite_conflicts,
    build_rewrite_plan,
    build_semantic_checks,
    build_symbol_scan,
)
from release_pipeline import (
    CODE_PATCH_DIR,
    GENERATED_CODE_PATCH,
    SAFE_REWRITE_PREVIEW,
    TEST_SUGGESTIONS,
    build_generated_code_patch,
    build_release_readiness,
    build_safe_rewrite_preview,
    build_test_suggestions,
)
from workspace_orchestration import _timeline_event

AI_PATCH_ASSIST_VERSION = "1032.0"
AI_PATCH_DIR = CODE_PATCH_DIR / "ai_assisted"
TASK_TO_CODE_PATCH = AI_PATCH_DIR / "task_to_code_patch.json"
CODE_CONTEXT = AI_PATCH_DIR / "code_context.json"
PATCH_PROMPT = AI_PATCH_DIR / "patch_prompt.json"
GENERATED_EDITS = AI_PATCH_DIR / "generated_edits.json"
EDIT_CONSISTENCY = AI_PATCH_DIR / "edit_consistency.json"
AI_PATCH_DRY_RUN = AI_PATCH_DIR / "ai_code_patch_dry_run.json"
PATCH_FAILURE_ANALYSIS = AI_PATCH_DIR / "patch_failure_analysis.json"
PATCH_LEARNING_NOTES = AI_PATCH_DIR / "patch_learning_notes.json"
AI_ASSISTED_CODE_PATCH_LOOP = AI_PATCH_DIR / "ai_assisted_code_patch_loop.json"
README_FILE = ROOT_DIR / "README_NEXT_STEPS.md"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    AI_PATCH_DIR.mkdir(parents=True, exist_ok=True)


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


def _status_from(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("status", "pass")).lower() for row in rows}
    if statuses & {"blocked", "fail", "failed"}:
        return "blocked"
    if statuses & {"warn", "warning"}:
        return "warn"
    return "pass"


def _safe_path(relative_path: str) -> Path:
    if not relative_path or relative_path.startswith(("/", "\\")) or ".." in Path(relative_path).parts:
        raise PermissionError(f"Unsafe relative path: {relative_path}")
    target = (ROOT_DIR / relative_path).resolve()
    target.relative_to(ROOT_DIR.resolve())
    return target


def _read_text(relative_path: str) -> str:
    return _safe_path(relative_path).read_text(encoding="utf-8", errors="replace")


def _saved_request(project_id: str = "eidolon", save: bool = False) -> dict[str, Any]:
    request = _read_json(DRAFT_REQUEST, {})
    if not isinstance(request, dict) or not request.get("request_id"):
        request = build_patch_draft_request(project_id=project_id, target_version="17.0", save=save)
    return request if isinstance(request, dict) else {}


def _saved_draft(project_id: str = "eidolon", save: bool = False) -> dict[str, Any]:
    draft = _read_json(CURRENT_DRAFT, {})
    if not isinstance(draft, dict) or not draft.get("draft_id"):
        _saved_request(project_id=project_id, save=save)
        draft = build_draft_patch(project_id=project_id, save=save)
    return draft if isinstance(draft, dict) else {}


def _saved_diff(project_id: str = "eidolon", save: bool = False) -> dict[str, Any]:
    diff = _read_json(CURRENT_DIFF, {})
    if not isinstance(diff, dict) or not diff.get("rows"):
        diff = build_draft_diff(project_id=project_id, save=save)
    return diff if isinstance(diff, dict) else {}


def _target_files_from_diff(project_id: str = "eidolon") -> list[str]:
    diff = _saved_diff(project_id=project_id, save=False)
    files: list[str] = []
    for row in diff.get("rows", []) or []:
        path = str(row.get("path", "")).strip()
        if path and path not in files:
            files.append(path)
    if not files:
        files = ["README_NEXT_STEPS.md"]
    return files


def _find_symbol_spans(path: Path) -> list[dict[str, Any]]:
    if path.suffix != ".py":
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    spans: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            spans.append({
                "name": node.name,
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "lineno": node.lineno,
                "end_lineno": getattr(node, "end_lineno", node.lineno),
            })
    return sorted(spans, key=lambda item: (item.get("lineno", 0), item.get("name", "")))


def _extract_snippet(path: Path, lineno: int, end_lineno: int, context: int = 8) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, int(lineno) - context)
    end = min(len(lines), int(end_lineno) + context)
    numbered = [f"{idx}: {lines[idx - 1]}" for idx in range(start, end + 1)]
    return {"start_line": start, "end_line": end, "text": "\n".join(numbered)}


def build_task_to_code_patch(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v16.1: translate the current task/draft request into a concrete code patch objective."""
    request = _saved_request(project_id=project_id, save=save)
    draft = _saved_draft(project_id=project_id, save=save)
    diff = _saved_diff(project_id=project_id, save=save)
    target_files = _target_files_from_diff(project_id=project_id)
    task = request.get("task") or draft.get("task") or "Review and improve the generated-code patch release loop."
    intent = request.get("intent") or draft.get("intent") or "Generate a bounded, reviewable patch objective from the active draft."
    rows = [
        {"name": "request", "status": "pass" if request.get("request_id") else "warn", "message": f"Request: {request.get('request_id', 'not saved')}"},
        {"name": "draft", "status": "pass" if draft.get("draft_id") else "warn", "message": f"Draft: {draft.get('draft_id', 'not saved')}"},
        {"name": "target-files", "status": "pass" if target_files else "blocked", "message": f"{len(target_files)} target file(s) resolved."},
    ]
    status = _status_from(rows)
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "request_id": request.get("request_id"),
        "draft_id": draft.get("draft_id"),
        "task_summary": str(task),
        "target_behavior": str(intent),
        "expected_files": target_files,
        "symbols_likely_affected": [Path(path).stem for path in target_files if path.endswith(".py")],
        "readme_impact": "README_NEXT_STEPS.md" in target_files or bool(request.get("constraints")),
        "test_impact": ["py_compile", "semantic-checks", "doctor", "stabilization-checkpoint", "smoke_check"],
        "risk_level": draft.get("risk") or request.get("risk_limit") or "medium",
        "patch_strategy": "Generate artifact-bound, expected-text edits; preview diff; require approval before real apply.",
        "rows": rows,
        "message": "Task translated into a bounded code patch objective.",
    }
    if save:
        _write_json(TASK_TO_CODE_PATCH, report)
    else:
        report["preview_only"] = True
    return report


def build_code_context(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v16.2: extract focused code and README context for generated patch planning."""
    objective = _read_json(TASK_TO_CODE_PATCH, {})
    if not isinstance(objective, dict) or not objective.get("expected_files"):
        objective = build_task_to_code_patch(project_id=project_id, save=False)
    symbol_scan = build_symbol_scan(project_id=project_id, save=False)
    target_files = objective.get("expected_files") or _target_files_from_diff(project_id=project_id)
    contexts: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for relative in target_files:
        try:
            path = _safe_path(str(relative))
            if not path.exists():
                rows.append({"path": relative, "status": "blocked", "message": "Target file does not exist."})
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            spans = _find_symbol_spans(path)
            snippets = []
            for span in spans[:8]:
                snippets.append({**span, "snippet": _extract_snippet(path, span["lineno"], span["end_lineno"], context=4)})
            if not snippets:
                preview = "\n".join(f"{idx}: {line}" for idx, line in enumerate(text.splitlines()[:80], start=1))
                snippets.append({"name": Path(relative).name, "kind": "file", "lineno": 1, "end_lineno": min(80, len(text.splitlines())), "snippet": {"start_line": 1, "end_line": min(80, len(text.splitlines())), "text": preview}})
            contexts.append({"path": str(relative), "size_chars": len(text), "symbols": spans[:40], "snippets": snippets})
            rows.append({"path": relative, "status": "pass", "message": f"Context extracted with {len(snippets)} snippet(s)."})
        except Exception as error:
            rows.append({"path": relative, "status": "blocked", "message": str(error)})
    readme_sections: list[str] = []
    if README_FILE.exists():
        readme = README_FILE.read_text(encoding="utf-8", errors="replace")
        for marker in ["v16.0", "v15.0", "v14.0", "v13.0"]:
            idx = readme.find(marker)
            if idx >= 0:
                readme_sections.append(readme[max(0, idx - 220):idx + 900])
                break
    status = _status_from(rows)
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "objective_id": objective.get("draft_id") or objective.get("request_id"),
        "target_files": target_files,
        "symbol_scan_status": symbol_scan.get("status"),
        "contexts": contexts,
        "readme_context": readme_sections,
        "rows": rows,
        "message": f"Focused code context extracted for {len(contexts)} file(s).",
    }
    if save:
        _write_json(CODE_CONTEXT, report)
    else:
        report["preview_only"] = True
    return report


def build_patch_prompt(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v16.3: build a structured prompt for AI-assisted patch generation."""
    objective = _read_json(TASK_TO_CODE_PATCH, {}) or build_task_to_code_patch(project_id=project_id, save=False)
    context = _read_json(CODE_CONTEXT, {}) or build_code_context(project_id=project_id, save=False)
    allowed_files = list(dict.fromkeys(objective.get("expected_files") or context.get("target_files") or []))
    blocked_files = [
        ".git/",
        ".venv/",
        "data/workspaces/projects.json unless the task explicitly targets workspace registry",
        "conscious_agent/command_runner.py unless safety gate changes are explicit",
    ]
    output_schema = {
        "edits": [
            {
                "file": "relative/path.py",
                "symbol": "optional_function_or_class",
                "expected_old_text": "exact text to replace",
                "replacement_text": "new text",
                "reason": "why this edit is needed",
                "tests": ["commands or checks"],
                "readme_impact": True,
            }
        ]
    }
    prompt = {
        "role": "bounded local patch generator",
        "task_objective": objective.get("task_summary"),
        "target_behavior": objective.get("target_behavior"),
        "constraints": [
            "Return structured JSON only.",
            "Use exact expected_old_text for every rewrite.",
            "Do not propose full-file rewrites unless explicitly allowed.",
            "Do not touch files outside allowed_files.",
            "Include README and test impact for every patch.",
            "GET endpoints must remain read-only; live actions must be POST/confirmation gated.",
            "Dry-runs must never overwrite real apply or rollback pointers.",
        ],
        "allowed_files": allowed_files,
        "blocked_files": blocked_files,
        "code_context": context.get("contexts", [])[:8],
        "readme_context": context.get("readme_context", []),
        "required_tests": objective.get("test_impact", []),
        "output_schema": output_schema,
    }
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if allowed_files else "blocked",
        "ok": bool(allowed_files),
        "prompt": prompt,
        "message": "Structured patch prompt built for bounded AI-assisted code generation.",
    }
    if save:
        _write_json(PATCH_PROMPT, report)
    else:
        report["preview_only"] = True
    return report


def _candidate_edits_from_previews(project_id: str = "eidolon") -> list[dict[str, Any]]:
    preview = _read_json(SAFE_REWRITE_PREVIEW, {})
    if not isinstance(preview, dict) or not preview.get("rows"):
        preview = build_safe_rewrite_preview(project_id=project_id, save=False)
    edits: list[dict[str, Any]] = []
    for row in preview.get("rows", []) or []:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path", ""))
        if row.get("status") not in {"ready", "pass"}:
            continue
        expected = row.get("expected_old_text")
        replacement = row.get("replacement_text")
        if expected is None:
            try:
                expected = _read_text(path)
            except Exception:
                expected = ""
        if replacement is None:
            replacement = row.get("proposed_content") or expected
        edits.append({
            "file": path,
            "symbol": row.get("target_symbol") or "",
            "expected_old_text": expected,
            "replacement_text": replacement,
            "reason": row.get("message", "Generated from safe rewrite preview."),
            "tests": row.get("tests_required") or ["python tools/smoke_check.py"],
            "readme_impact": path == "README_NEXT_STEPS.md" or bool(row.get("readme_required")),
            "source": "safe_rewrite_preview",
        })
    if not edits:
        # Safe fallback: review-only README no-op edit so downstream reports have a concrete shape.
        try:
            readme = _read_text("README_NEXT_STEPS.md")
        except Exception:
            readme = ""
        edits.append({
            "file": "README_NEXT_STEPS.md",
            "symbol": "",
            "expected_old_text": readme,
            "replacement_text": readme,
            "reason": "Fallback no-op README edit for review-only dry-run.",
            "tests": ["python tools/smoke_check.py"],
            "readme_impact": True,
            "source": "fallback_noop",
        })
    return edits


def build_parse_generated_edits(project_id: str = "eidolon", generated: dict[str, Any] | None = None, save: bool = True) -> dict[str, Any]:
    """v16.4: parse generated patch suggestions into safe internal edit objects."""
    prompt = _read_json(PATCH_PROMPT, {}) or build_patch_prompt(project_id=project_id, save=False)
    allowed_files = set(prompt.get("prompt", {}).get("allowed_files", []) or [])
    source = generated if isinstance(generated, dict) else _read_json(GENERATED_CODE_PATCH, {})
    raw_edits = []
    if isinstance(source, dict):
        raw_edits = source.get("edits") or source.get("generated_edits") or []
    if not raw_edits:
        raw_edits = _candidate_edits_from_previews(project_id=project_id)
    parsed: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for idx, edit in enumerate(raw_edits, start=1):
        if not isinstance(edit, dict):
            rejected.append({"index": idx, "status": "blocked", "message": "Generated edit is not an object."})
            continue
        path = str(edit.get("file") or edit.get("path") or "").strip()
        expected_old_text = edit.get("expected_old_text")
        replacement_text = edit.get("replacement_text")
        reasons: list[str] = []
        if not path:
            reasons.append("missing file")
        if allowed_files and path not in allowed_files:
            reasons.append("file is not in allowed_files")
        try:
            if path:
                _safe_path(path)
        except Exception as error:
            reasons.append(str(error))
        if expected_old_text in (None, ""):
            reasons.append("missing expected_old_text")
        if replacement_text is None:
            reasons.append("missing replacement_text")
        if expected_old_text and isinstance(expected_old_text, str):
            try:
                current = _read_text(path)
                if expected_old_text == current and len(current) > 12000 and path != "README_NEXT_STEPS.md":
                    reasons.append("full-file rewrite rejected for large non-README file")
                if expected_old_text not in current:
                    reasons.append("expected_old_text not found in current file")
            except Exception as error:
                reasons.append(f"current file read failed: {error}")
        if path.startswith("conscious_agent/command_runner.py") and "command_runner" not in str(edit.get("reason", "")).lower():
            reasons.append("guardrail file requires explicit safety intent")
        row = {
            "edit_id": f"edit_{idx:03d}",
            "file": path,
            "symbol": edit.get("symbol") or "",
            "expected_old_text": expected_old_text,
            "replacement_text": replacement_text,
            "reason": edit.get("reason") or "Generated edit parsed for review.",
            "tests": edit.get("tests") or ["python tools/smoke_check.py"],
            "readme_impact": bool(edit.get("readme_impact")) or path == "README_NEXT_STEPS.md",
            "source": edit.get("source") or "generated",
            "status": "blocked" if reasons else "ready",
            "reasons": reasons,
        }
        (rejected if reasons else parsed).append(row)
    rows = parsed + rejected
    status = _status_from([{"status": "blocked" if rejected else "pass"}]) if rows else "blocked"
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not rejected and bool(parsed),
        "allowed_files": sorted(allowed_files),
        "edits": parsed,
        "rejected": rejected,
        "rows": rows,
        "message": f"Parsed {len(parsed)} safe edit(s); rejected {len(rejected)} edit(s).",
    }
    if save:
        _write_json(GENERATED_EDITS, report)
    else:
        report["preview_only"] = True
    return report


def build_edit_consistency(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v16.5: validate that generated edits work together as one patch."""
    parsed = _read_json(GENERATED_EDITS, {})
    if not isinstance(parsed, dict) or not parsed.get("rows"):
        parsed = build_parse_generated_edits(project_id=project_id, save=False)
    edits = parsed.get("edits", []) or []
    rows: list[dict[str, Any]] = []
    seen_targets: dict[tuple[str, str], str] = {}
    for edit in edits:
        key = (str(edit.get("file")), str(edit.get("expected_old_text")))
        reasons: list[str] = []
        if key in seen_targets:
            reasons.append(f"duplicate target region also used by {seen_targets[key]}")
        else:
            seen_targets[key] = str(edit.get("edit_id"))
        if edit.get("file") != "README_NEXT_STEPS.md" and not edit.get("readme_impact"):
            reasons.append("code edit lacks README impact marker")
        if not edit.get("tests"):
            reasons.append("edit lacks test suggestions")
        if edit.get("file", "").endswith("api_server.py") and "GET" in str(edit.get("replacement_text", "")) and "POST" not in str(edit.get("tests", "")):
            reasons.append("API edit needs GET/POST safety test coverage")
        rows.append({
            "edit_id": edit.get("edit_id"),
            "file": edit.get("file"),
            "status": "blocked" if reasons else "pass",
            "reasons": reasons,
            "message": "; ".join(reasons) if reasons else "Edit is consistent with the current generated patch set.",
        })
    if parsed.get("rejected"):
        rows.append({"name": "rejected-edits", "status": "blocked", "message": f"{len(parsed.get('rejected', []))} generated edit(s) were rejected by parser."})
    if not edits:
        rows.append({"name": "edits", "status": "blocked", "message": "No safe generated edits are available."})
    status = _status_from(rows)
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "rows": rows,
        "message": "Generated edit consistency check completed.",
    }
    if save:
        _write_json(EDIT_CONSISTENCY, report)
    else:
        report["preview_only"] = True
    return report


def build_ai_code_patch_dry_run(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v16.6: run task->context->prompt->parse->consistency->diff/semantic review without writes."""
    objective = build_task_to_code_patch(project_id=project_id, save=save)
    context = build_code_context(project_id=project_id, save=save)
    prompt = build_patch_prompt(project_id=project_id, save=save)
    # v16.6 intentionally uses the local generated-code artifact path as a stand-in for an AI response.
    generated = build_generated_code_patch(project_id=project_id, save=save)
    parsed = build_parse_generated_edits(project_id=project_id, save=save)
    consistency = build_edit_consistency(project_id=project_id, save=save)
    rewrite_preview = build_safe_rewrite_preview(project_id=project_id, save=False)
    diff_bundle = build_code_patch_diff_bundle(project_id=project_id, save=save)
    semantic = build_semantic_checks(project_id=project_id, save=save)
    blocked = [name for name, report in {
        "task_to_code_patch": objective,
        "code_context": context,
        "patch_prompt": prompt,
        "generated_code_patch": generated,
        "parse_generated_edits": parsed,
        "edit_consistency": consistency,
        "diff_bundle": diff_bundle,
        "semantic_checks": semantic,
    }.items() if isinstance(report, dict) and report.get("ok") is False]
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "blocked" if blocked else "dry_run",
        "ok": not blocked,
        "dry_run": True,
        "steps": {
            "task_to_code_patch": objective,
            "code_context": context,
            "patch_prompt": prompt,
            "generated_code_patch": generated,
            "parse_generated_edits": parsed,
            "edit_consistency": consistency,
            "rewrite_preview": rewrite_preview,
            "diff_bundle": diff_bundle,
            "semantic_checks": semantic,
        },
        "blocked_steps": blocked,
        "message": "AI code patch dry-run completed without source writes." if not blocked else "AI code patch dry-run found blockers before approval/apply.",
    }
    if save:
        _write_json(AI_PATCH_DRY_RUN, report)
        _timeline_event("ai_code_patch_dry_run", {"project_id": project_id, "status": report["status"]}, save=True)
    return report


def build_patch_failure_analysis(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v16.8: classify the latest generated patch failures into actionable categories."""
    artifacts = {
        "dry_run": _read_json(AI_PATCH_DRY_RUN, {}),
        "parse_generated_edits": _read_json(GENERATED_EDITS, {}),
        "edit_consistency": _read_json(EDIT_CONSISTENCY, {}),
        "rewrite_conflicts": _read_json(DATA_DIR / "code_patches" / "rewrite_conflicts.json", {}),
        "semantic_checks": _read_json(DATA_DIR / "code_patches" / "semantic_checks.json", {}),
        "release_readiness": _read_json(DATA_DIR / "code_patches" / "release_readiness.json", {}),
    }
    signals: list[dict[str, Any]] = []
    for artifact_name, artifact in artifacts.items():
        if not isinstance(artifact, dict) or not artifact:
            continue
        artifact_status = str(artifact.get("status", "")).lower()
        if artifact_status in {"blocked", "failed", "fail"}:
            signals.append({"artifact": artifact_name, "status": artifact_status, "message": artifact.get("message", "")})
        for collection_name in ["rows", "prechecks", "blocked_steps", "rejected"]:
            collection = artifact.get(collection_name) or []
            if not isinstance(collection, list):
                continue
            for item in collection:
                if isinstance(item, dict):
                    item_status = str(item.get("status", "")).lower()
                    if item_status in {"blocked", "failed", "fail", "warn", "warning"}:
                        signals.append({
                            "artifact": artifact_name,
                            "status": item_status,
                            "message": item.get("message") or "; ".join(item.get("reasons", [])) or json.dumps(item, default=str)[:500],
                        })
                elif collection_name == "blocked_steps":
                    signals.append({"artifact": artifact_name, "status": "blocked", "message": str(item)})
    classifiers = [
        ("context mismatch", ["expected_old_text not found", "file hash changed", "context mismatch"]),
        ("symbol missing", ["target symbol missing", "symbol missing"]),
        ("compile failure", ["py_compile failed", "syntax error", "compile failed"]),
        ("dashboard import failure", ["dashboard import failed", "import dashboard"]),
        ("API safety failure", ["GET endpoint mutates", "POST confirmation", "api safety"]),
        ("README gate failure", ["README gate", "readme missing", "README is missing"]),
        ("approval mismatch", ["approval", "binding", "draft_id"]),
        ("rollback unavailable", ["rollback", "backup", "stale apply"]),
        ("test failure", ["test failed", "smoke check failed", "doctor failed"]),
        ("environment warning", ["chromadb", "Ollama", "environment"]),
    ]
    signal_text = "\n".join(str(signal.get("message", "")) for signal in signals)
    rows: list[dict[str, Any]] = []
    for label, needles in classifiers:
        matched = [needle for needle in needles if needle.lower() in signal_text.lower()]
        if matched:
            severity = "warn"
            rows.append({"class": label, "status": severity, "matched": matched, "message": f"Detected active signal(s) for {label}."})
    if not rows:
        rows.append({"class": "no-failure-detected", "status": "pass", "message": "No saved generated-patch failure signals detected."})
    status = _status_from(rows)
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "signals_checked": len(signals),
        "rows": rows,
        "message": "Patch failure analysis completed.",
    }
    if save:
        _write_json(PATCH_FAILURE_ANALYSIS, report)
    else:
        report["preview_only"] = True
    return report

def build_patch_learning_notes(project_id: str = "eidolon", note: str | None = None, save: bool = True) -> dict[str, Any]:
    """v16.9: save lessons from generated patch failures/rejections for future constraints."""
    analysis = build_patch_failure_analysis(project_id=project_id, save=False)
    existing = _read_json(PATCH_LEARNING_NOTES, {"notes": []})
    notes = existing.get("notes", []) if isinstance(existing, dict) else []
    if note:
        notes.append({"created_at": _now(), "project_id": project_id, "source": "human", "note": note})
    for row in analysis.get("rows", []) or []:
        if row.get("status") in {"blocked", "warn"}:
            notes.append({
                "created_at": _now(),
                "project_id": project_id,
                "source": "failure_analysis",
                "failure_class": row.get("class"),
                "recommended_future_constraint": f"Check for {row.get('class')} before approval.",
                "details": row.get("message"),
            })
    # De-duplicate rough repeated rows by JSON string.
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in notes[-80:]:
        key = json.dumps({k: v for k, v in item.items() if k != "created_at"}, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if deduped else "warn",
        "ok": True,
        "notes": deduped,
        "message": f"Stored {len(deduped)} generated-patch learning note(s).",
    }
    if save:
        _write_json(PATCH_LEARNING_NOTES, report)
    else:
        report["preview_only"] = True
    return report


def build_ai_assisted_code_patch_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v17.0: one AI-assisted, human-approved generated code patch loop."""
    objective = build_task_to_code_patch(project_id=project_id, save=save)
    context = build_code_context(project_id=project_id, save=save)
    prompt = build_patch_prompt(project_id=project_id, save=save)
    parsed = build_parse_generated_edits(project_id=project_id, save=save)
    consistency = build_edit_consistency(project_id=project_id, save=save)
    dry = build_ai_code_patch_dry_run(project_id=project_id, save=save)
    approval = _read_json(APPROVAL_STATE, {})
    binding = validate_approval_binding(approval=approval, project_id=project_id) if isinstance(approval, dict) and approval.get("approved") else {"ok": False, "message": "No artifact-bound approval is active."}
    generated_release = None
    transaction = None
    if binding.get("ok") and (approve or dry_run):
        # Dry-run is still safe when approval exists; real writes require approve=True and dry_run=False.
        generated_release = build_generated_code_release_loop(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=save)
        transaction = build_apply_code_patch_transaction(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=save)
    semantic = build_semantic_checks(project_id=project_id, save=save)
    readiness = build_release_readiness(project_id=project_id, save=save)
    artifact = build_release_artifact(project_id=project_id, package_name="Eidolon_v19_0.zip", save=save)
    audit = build_release_audit_trail(project_id=project_id, save=save)
    failure = build_patch_failure_analysis(project_id=project_id, save=save)
    learning = build_patch_learning_notes(project_id=project_id, save=save)
    blocked = [name for name, report in {
        "task_to_code_patch": objective,
        "code_context": context,
        "patch_prompt": prompt,
        "parse_generated_edits": parsed,
        "edit_consistency": consistency,
        "ai_patch_dry_run": dry,
        "semantic_checks": semantic,
    }.items() if isinstance(report, dict) and report.get("ok") is False]
    status = "blocked" if blocked else "awaiting_approval" if not binding.get("ok") else "dry_run" if (dry_run or not approve) else "applied"
    report = {
        "version": AI_PATCH_ASSIST_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "dry_run": dry_run or not approve,
        "approval_binding": binding,
        "steps": {
            "task_to_code_patch": objective,
            "code_context": context,
            "patch_prompt": prompt,
            "parse_generated_edits": parsed,
            "edit_consistency": consistency,
            "ai_code_patch_dry_run": dry,
            "generated_code_release_loop": generated_release,
            "apply_transaction": transaction,
            "semantic_checks": semantic,
            "release_readiness": readiness,
            "release_artifact": artifact,
            "audit_trail": audit,
            "failure_analysis": failure,
            "learning_notes": learning,
        },
        "blocked_steps": blocked,
        "message": "AI-assisted code patch loop prepared review artifacts and stopped for approval." if not binding.get("ok") else "AI-assisted code patch loop completed one bounded approved path and stopped.",
    }
    if save:
        _write_json(AI_ASSISTED_CODE_PATCH_LOOP, report)
        _timeline_event("ai_assisted_code_patch_loop", {"project_id": project_id, "status": status, "dry_run": report["dry_run"]}, save=True)
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
    for key in ["blocked_steps", "expected_files", "target_files", "allowed_files"]:
        values = report.get(key) or []
        if values:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values[:40]])
    rows = report.get("rows") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:40]:
            if isinstance(row, dict):
                name = row.get("name") or row.get("class") or row.get("file") or row.get("path") or row.get("edit_id") or "row"
                status = row.get("status") or "info"
                msg = row.get("message") or "; ".join(row.get("reasons", []))
                lines.append(f"- {str(status).upper()} {name}: {msg}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def task_to_code_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.1 Task-to-Code Patch Translator", report or build_task_to_code_patch(save=False), full)


def code_context_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.2 Code Context Extractor", report or build_code_context(save=False), full)


def patch_prompt_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.3 Patch Prompt Builder", report or build_patch_prompt(save=False), full)


def parse_generated_edits_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.4 Generated Edit Parser", report or build_parse_generated_edits(save=False), full)


def edit_consistency_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.5 Multi-Edit Consistency Checker", report or build_edit_consistency(save=False), full)


def ai_code_patch_dry_run_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.6 AI Patch Draft Dry-Run", report or build_ai_code_patch_dry_run(save=False), full)


def patch_failure_analysis_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.8 Patch Failure Classifier", report or build_patch_failure_analysis(save=False), full)


def patch_learning_notes_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v16.9 Patch Learning Notes", report or build_patch_learning_notes(save=False), full)


def ai_assisted_code_patch_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.0 AI-Assisted Human-Approved Code Patch Loop", report or build_ai_assisted_code_patch_loop(save=False), full)


def print_task_to_code_patch(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_task_to_code_patch(project_id=project_id, save=True)
    _json_print(report) if json_output else print(task_to_code_patch_text(report, full=full))


def print_code_context(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_code_context(project_id=project_id, save=True)
    _json_print(report) if json_output else print(code_context_text(report, full=full))


def print_patch_prompt(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_prompt(project_id=project_id, save=True)
    _json_print(report) if json_output else print(patch_prompt_text(report, full=full))


def print_parse_generated_edits(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_parse_generated_edits(project_id=project_id, save=True)
    _json_print(report) if json_output else print(parse_generated_edits_text(report, full=full))


def print_edit_consistency(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_edit_consistency(project_id=project_id, save=True)
    _json_print(report) if json_output else print(edit_consistency_text(report, full=full))


def print_ai_code_patch_dry_run(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_ai_code_patch_dry_run(project_id=project_id, save=True)
    _json_print(report) if json_output else print(ai_code_patch_dry_run_text(report, full=full))


def print_patch_failure_analysis(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_failure_analysis(project_id=project_id, save=True)
    _json_print(report) if json_output else print(patch_failure_analysis_text(report, full=full))


def print_patch_learning_notes(project_id: str = "eidolon", note: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_patch_learning_notes(project_id=project_id, note=note, save=True)
    _json_print(report) if json_output else print(patch_learning_notes_text(report, full=full))


def print_ai_assisted_code_patch_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_ai_assisted_code_patch_loop(project_id=project_id, approve=approve, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(ai_assisted_code_patch_loop_text(report, full=full))
