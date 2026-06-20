from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from patch_drafting import APPROVAL_STATE, validate_approval_binding
from ai_patch_assistance import (
    AI_PATCH_DIR,
    GENERATED_EDITS,
    TASK_TO_CODE_PATCH,
    CODE_CONTEXT,
    PATCH_PROMPT,
    EDIT_CONSISTENCY,
    AI_PATCH_DRY_RUN,
    build_task_to_code_patch,
    build_code_context,
    build_patch_prompt,
    build_parse_generated_edits,
    build_edit_consistency,
    build_ai_code_patch_dry_run,
    build_patch_failure_analysis,
    build_patch_learning_notes,
)
from code_patch_release import (
    build_apply_code_patch_transaction,
    build_code_patch_diff_bundle,
    build_generated_code_release_loop,
    build_release_artifact,
    build_release_audit_trail,
    build_rewrite_conflicts,
    build_semantic_checks,
)
from release_pipeline import build_release_readiness, build_test_suggestions
from workspace_orchestration import _timeline_event

VALIDATED_AI_PATCH_VERSION = "18.0"
VALIDATED_AI_DIR = AI_PATCH_DIR / "validated"
PATCH_OBJECTIVE_REFINEMENT = VALIDATED_AI_DIR / "patch_objective_refinement.json"
CODE_CONTEXT_RANKING = VALIDATED_AI_DIR / "code_context_ranking.json"
PATCH_SAFETY_ENVELOPE = VALIDATED_AI_DIR / "patch_safety_envelope.json"
GENERATED_PATCH_VALIDATION = VALIDATED_AI_DIR / "generated_patch_validation.json"
PATCH_SIMULATION = VALIDATED_AI_DIR / "patch_simulation.json"
TEST_STUB_PLAN = VALIDATED_AI_DIR / "test_stub_plan.json"
PATCH_REVIEW_SCORE = VALIDATED_AI_DIR / "patch_review_score.json"
PATCH_RECOVERY_PLAN = VALIDATED_AI_DIR / "patch_recovery_plan.json"
VALIDATED_AI_CODE_PATCH_LOOP = VALIDATED_AI_DIR / "validated_ai_code_patch_loop.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    VALIDATED_AI_DIR.mkdir(parents=True, exist_ok=True)


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _read_text(relative_path: str) -> str:
    return _safe_path(relative_path).read_text(encoding="utf-8", errors="replace")


def _file_keyword_score(path: str, text: str, terms: list[str]) -> int:
    haystack = f"{path}\n{text}".lower()
    score = 0
    for term in terms:
        term = term.strip().lower()
        if not term:
            continue
        if term in path.lower():
            score += 5
        if term in haystack:
            score += min(10, haystack.count(term))
    if path.endswith("README_NEXT_STEPS.md"):
        score += 4
    if path.endswith("api_server.py"):
        score += 3
    if path.endswith("dashboard.py"):
        score += 3
    if path.endswith("main.py"):
        score += 3
    return score


def build_patch_objective_refinement(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v17.1: sharpen the task-to-code objective before generated patch validation."""
    objective = _read_json(TASK_TO_CODE_PATCH, {})
    if not isinstance(objective, dict) or not objective.get("task_summary"):
        objective = build_task_to_code_patch(project_id=project_id, save=False)
    expected_files = list(dict.fromkeys(objective.get("expected_files") or ["README_NEXT_STEPS.md"]))
    task_summary = str(objective.get("task_summary") or "Improve AI-assisted generated patch review.")
    target_behavior = str(objective.get("target_behavior") or "Generate a validated, reviewable AI-assisted patch artifact.")
    surfaces = []
    for path in expected_files:
        if path.endswith("main.py"):
            surfaces.append("CLI")
        if path.endswith("api_server.py"):
            surfaces.append("API")
        if path.endswith("dashboard.py"):
            surfaces.append("dashboard")
        if path.endswith("README_NEXT_STEPS.md"):
            surfaces.append("documentation")
    if not surfaces:
        surfaces.append("code")
    rows = [
        {"name": "objective", "status": "pass" if task_summary else "blocked", "message": task_summary},
        {"name": "allowed-files", "status": "pass" if expected_files else "blocked", "message": f"{len(expected_files)} allowed file(s)."},
        {"name": "surfaces", "status": "pass", "message": ", ".join(sorted(set(surfaces)))},
    ]
    status = _status_from(rows)
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "task_summary": task_summary,
        "specific_behavior_change": target_behavior,
        "affected_surfaces": sorted(set(surfaces)),
        "allowed_files": expected_files,
        "blocked_files": [
            ".git/",
            ".venv/",
            "data/workspaces/projects.json unless registry work is explicit",
            "conscious_agent/command_runner.py unless safety/command policy work is explicit",
        ],
        "success_criteria": [
            "generated edits parse into expected-text rewrites",
            "validation is pass or warn with no blockers",
            "simulation produces no source writes",
            "README impact is explicit",
            "semantic checks remain pass/warn only",
        ],
        "failure_criteria": [
            "file outside project boundary",
            "missing expected_old_text",
            "expected_old_text not present in current file",
            "GET endpoint mutation introduced",
            "dry-run overwrites real apply pointer",
            "approval artifact mismatch",
        ],
        "readme_impact": "README_NEXT_STEPS.md must document v17.1-v18.0 changes.",
        "test_expectations": ["py_compile", "dashboard import", "semantic-checks", "doctor", "stabilization-checkpoint", "smoke_check"],
        "rows": rows,
        "message": "Patch objective refined into explicit surfaces, success/failure criteria, and safety limits.",
    }
    if save:
        _write_json(PATCH_OBJECTIVE_REFINEMENT, report)
    else:
        report["preview_only"] = True
    return report


def build_code_context_ranking(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v17.2: rank focused code context by relevance before prompt construction."""
    refinement = _read_json(PATCH_OBJECTIVE_REFINEMENT, {})
    if not isinstance(refinement, dict) or not refinement.get("allowed_files"):
        refinement = build_patch_objective_refinement(project_id=project_id, save=False)
    context = _read_json(CODE_CONTEXT, {})
    if not isinstance(context, dict) or not context.get("contexts"):
        context = build_code_context(project_id=project_id, save=False)
    terms = []
    terms.extend(str(refinement.get("task_summary", "")).replace("-", " ").split())
    terms.extend(str(refinement.get("specific_behavior_change", "")).replace("-", " ").split())
    terms.extend(str(surface) for surface in refinement.get("affected_surfaces", []) or [])
    ranked: list[dict[str, Any]] = []
    for item in context.get("contexts", []) or []:
        path = str(item.get("path", ""))
        snippet_text = "\n".join(str(snippet.get("snippet", {}).get("text", "")) for snippet in item.get("snippets", []) or [])
        score = _file_keyword_score(path, snippet_text, terms)
        risk = "high" if path.endswith(("command_runner.py", "api_server.py")) else "medium" if path.endswith("dashboard.py") else "low"
        ranked.append({
            "path": path,
            "score": score,
            "risk": risk,
            "symbol_count": len(item.get("symbols", []) or []),
            "snippet_count": len(item.get("snippets", []) or []),
            "reasons": [
                "matches task/surface keywords" if score else "included by target-file selection",
                f"risk={risk}",
            ],
        })
    ranked.sort(key=lambda row: (-int(row.get("score", 0)), str(row.get("path", ""))))
    rows = [{"path": row["path"], "status": "pass", "message": f"score={row['score']} risk={row['risk']}"} for row in ranked]
    if not ranked:
        rows.append({"name": "context", "status": "blocked", "message": "No focused context is available to rank."})
    status = _status_from(rows)
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "objective_id": refinement.get("task_summary"),
        "ranked_context": ranked,
        "top_context_paths": [row.get("path") for row in ranked[:8]],
        "rows": rows,
        "message": "Code context ranked for generated patch prompt focus.",
    }
    if save:
        _write_json(CODE_CONTEXT_RANKING, report)
    else:
        report["preview_only"] = True
    return report


def build_patch_safety_envelope(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v17.3: wrap generated-patch prompts in hard safety rules."""
    refinement = _read_json(PATCH_OBJECTIVE_REFINEMENT, {}) or build_patch_objective_refinement(project_id=project_id, save=False)
    ranking = _read_json(CODE_CONTEXT_RANKING, {}) or build_code_context_ranking(project_id=project_id, save=False)
    prompt = _read_json(PATCH_PROMPT, {})
    if not isinstance(prompt, dict) or not prompt.get("prompt"):
        prompt = build_patch_prompt(project_id=project_id, save=False)
    allowed_files = list(dict.fromkeys(refinement.get("allowed_files") or prompt.get("prompt", {}).get("allowed_files") or []))
    hard_rules = [
        "Return valid JSON only using the generated edit schema.",
        "Only modify allowed_files.",
        "Never rewrite a full file unless full_file_rewrite_allowed is true.",
        "Every edit must include expected_old_text and replacement_text.",
        "Every edit must include README impact and test impact.",
        "Do not touch guardrails, command runners, rollback code, or workspace registry files unless explicitly allowed.",
        "GET endpoints must stay read-only; mutating/live work must be POST-only with confirmation.",
        "Dry-runs must never overwrite real apply, approval, or rollback pointers.",
        "Approval must bind to the exact draft/diff/test/quality/checklist bundle.",
    ]
    rows = [
        {"name": "allowed-files", "status": "pass" if allowed_files else "blocked", "message": f"{len(allowed_files)} allowed file(s)."},
        {"name": "ranked-context", "status": "pass" if ranking.get("ranked_context") else "warn", "message": f"{len(ranking.get('ranked_context', []) or [])} ranked context item(s)."},
        {"name": "hard-rules", "status": "pass", "message": f"{len(hard_rules)} safety rules active."},
    ]
    status = _status_from(rows)
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "allowed_files": allowed_files,
        "blocked_files": refinement.get("blocked_files", []),
        "top_context_paths": ranking.get("top_context_paths", []),
        "hard_rules": hard_rules,
        "output_schema": prompt.get("prompt", {}).get("output_schema", {}),
        "rows": rows,
        "message": "Prompt safety envelope built for bounded AI-generated code edits.",
    }
    if save:
        _write_json(PATCH_SAFETY_ENVELOPE, report)
    else:
        report["preview_only"] = True
    return report


def build_generated_patch_validation(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v17.4: validate generated edit objects before rewrite planning/apply."""
    envelope = _read_json(PATCH_SAFETY_ENVELOPE, {})
    if not isinstance(envelope, dict) or not envelope.get("allowed_files"):
        envelope = build_patch_safety_envelope(project_id=project_id, save=False)
    parsed = _read_json(GENERATED_EDITS, {})
    if not isinstance(parsed, dict) or not parsed.get("rows"):
        parsed = build_parse_generated_edits(project_id=project_id, save=False)
    consistency = _read_json(EDIT_CONSISTENCY, {})
    if not isinstance(consistency, dict) or not consistency.get("rows"):
        consistency = build_edit_consistency(project_id=project_id, save=False)
    allowed = set(envelope.get("allowed_files") or [])
    rows: list[dict[str, Any]] = []
    edits = parsed.get("edits", []) or []
    rejected = parsed.get("rejected", []) or []
    if not edits:
        rows.append({"name": "edits", "status": "blocked", "message": "No accepted generated edits are available."})
    for edit in edits:
        path = str(edit.get("file", ""))
        reasons: list[str] = []
        if allowed and path not in allowed:
            reasons.append("file not allowed by safety envelope")
        try:
            current = _read_text(path)
            expected = str(edit.get("expected_old_text", ""))
            if not expected:
                reasons.append("expected_old_text is missing")
            elif expected not in current:
                reasons.append("expected_old_text not present in current file")
        except Exception as error:
            reasons.append(f"file read/boundary failed: {error}")
        if path != "README_NEXT_STEPS.md" and not edit.get("tests"):
            reasons.append("test impact missing")
        if path != "README_NEXT_STEPS.md" and not edit.get("readme_impact"):
            reasons.append("README impact missing")
        if any(fragment in path for fragment in ["command_runner.py", "controlled_build_cycle.py"]):
            reason = str(edit.get("reason", "")).lower()
            if not any(word in reason for word in ["safety", "guard", "approval", "rollback"]):
                reasons.append("guardrail/recovery file edit lacks explicit safety intent")
        rows.append({
            "edit_id": edit.get("edit_id"),
            "file": path,
            "status": "blocked" if reasons else "pass",
            "message": "; ".join(reasons) if reasons else "Generated edit passed validation.",
            "reasons": reasons,
        })
    if rejected:
        rows.append({"name": "parser-rejections", "status": "blocked", "message": f"{len(rejected)} rejected edit(s) remain."})
    if consistency.get("status") == "blocked":
        rows.append({"name": "consistency", "status": "blocked", "message": "Edit consistency check is blocked."})
    elif consistency.get("status") == "warn":
        rows.append({"name": "consistency", "status": "warn", "message": "Edit consistency check has warnings."})
    status = _status_from(rows)
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "validated_edits": [row for row in rows if row.get("edit_id") and row.get("status") == "pass"],
        "rejected_count": len(rejected),
        "rows": rows,
        "message": "Generated patch validation completed." if status != "blocked" else "Generated patch validation found blockers.",
    }
    if save:
        _write_json(GENERATED_PATCH_VALIDATION, report)
    else:
        report["preview_only"] = True
    return report


def build_patch_simulation(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v17.5: simulate generated edits without touching source files."""
    validation = _read_json(GENERATED_PATCH_VALIDATION, {})
    if not isinstance(validation, dict) or not validation.get("rows"):
        validation = build_generated_patch_validation(project_id=project_id, save=False)
    parsed = _read_json(GENERATED_EDITS, {})
    if not isinstance(parsed, dict) or not parsed.get("edits"):
        parsed = build_parse_generated_edits(project_id=project_id, save=False)
    rows: list[dict[str, Any]] = []
    changed_files: list[dict[str, Any]] = []
    for edit in parsed.get("edits", []) or []:
        path = str(edit.get("file", ""))
        expected = str(edit.get("expected_old_text", ""))
        replacement = str(edit.get("replacement_text", ""))
        reasons: list[str] = []
        try:
            current = _read_text(path)
            before_hash = _sha256_text(current)
            if not expected or expected not in current:
                reasons.append("expected_old_text not found; simulated replacement skipped")
                after_text = current
            else:
                after_text = current.replace(expected, replacement, 1)
            after_hash = _sha256_text(after_text)
            changed = before_hash != after_hash
            changed_files.append({
                "file": path,
                "would_change": changed,
                "before_sha256": before_hash,
                "after_sha256": after_hash,
                "backup_required": changed,
                "rollback_plan": "copy backup after verifying applied_sha256" if changed else "not applicable for no-op",
            })
        except Exception as error:
            reasons.append(str(error))
            changed = False
        rows.append({
            "edit_id": edit.get("edit_id"),
            "file": path,
            "status": "blocked" if reasons else "pass",
            "message": "; ".join(reasons) if reasons else ("Replacement simulated." if changed else "No-op simulated."),
        })
    if validation.get("status") == "blocked":
        rows.append({"name": "validation", "status": "blocked", "message": "Simulation is blocked because generated patch validation failed."})
    if not parsed.get("edits"):
        rows.append({"name": "edits", "status": "blocked", "message": "No parsed edits available to simulate."})
    status = _status_from(rows)
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "dry_run": True,
        "source_writes": False,
        "changed_files": changed_files,
        "test_commands_that_would_run": ["python -m py_compile conscious_agent/*.py tools/smoke_check.py", "python conscious_agent/main.py --semantic-checks", "python tools/smoke_check.py"],
        "semantic_checks_that_would_trigger": ["GET read-only", "POST confirmation", "dry-run pointer separation", "approval artifact binding", "rollback stale-pointer guard"],
        "release_readiness_effect": "preview only; readiness remains informational until real apply occurs",
        "rows": rows,
        "message": "Patch simulation completed without source writes." if status != "blocked" else "Patch simulation found blockers.",
    }
    if save:
        _write_json(PATCH_SIMULATION, report)
    else:
        report["preview_only"] = True
    return report


def build_test_stub_plan(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v17.6: propose smoke/test stub additions for generated patch classes."""
    parsed = _read_json(GENERATED_EDITS, {})
    if not isinstance(parsed, dict) or not parsed.get("rows"):
        parsed = build_parse_generated_edits(project_id=project_id, save=False)
    files = [str(edit.get("file", "")) for edit in parsed.get("edits", []) or []]
    suggestions = [
        {"kind": "compile", "status": "pass", "command": "python -m py_compile conscious_agent/*.py tools/smoke_check.py", "reason": "basic syntax/import coverage"},
        {"kind": "smoke", "status": "pass", "command": "python tools/smoke_check.py", "reason": "core regression coverage"},
        {"kind": "semantic", "status": "pass", "command": "python conscious_agent/main.py --semantic-checks", "reason": "approval, rollback, dry-run, and GET/POST safety markers"},
    ]
    if any(path.endswith("api_server.py") for path in files):
        suggestions.append({"kind": "api", "status": "pass", "command": "GET endpoints preview-only; POST endpoints require confirmation for live writes", "reason": "API safety regression"})
    if any(path.endswith("dashboard.py") for path in files):
        suggestions.append({"kind": "dashboard", "status": "pass", "command": "PYTHONPATH=conscious_agent python -c \"import dashboard; print(dashboard.DASHBOARD_VERSION)\"", "reason": "dashboard import regression"})
    if any(path.endswith("main.py") for path in files):
        suggestions.append({"kind": "cli", "status": "pass", "command": "python conscious_agent/main.py --validated-ai-code-patch-loop", "reason": "CLI surface regression"})
    rows = [{"name": item["kind"], "status": item["status"], "message": f"{item['command']} - {item['reason']}"} for item in suggestions]
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": _status_from(rows),
        "ok": True,
        "target_files": files,
        "suggestions": suggestions,
        "rows": rows,
        "message": "Generated patch test stub plan created.",
    }
    if save:
        _write_json(TEST_STUB_PLAN, report)
    else:
        report["preview_only"] = True
    return report


def build_patch_review_score(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v17.7: score generated patch review readiness before approval."""
    refinement = _read_json(PATCH_OBJECTIVE_REFINEMENT, {}) or build_patch_objective_refinement(project_id=project_id, save=False)
    ranking = _read_json(CODE_CONTEXT_RANKING, {}) or build_code_context_ranking(project_id=project_id, save=False)
    envelope = _read_json(PATCH_SAFETY_ENVELOPE, {}) or build_patch_safety_envelope(project_id=project_id, save=False)
    validation = _read_json(GENERATED_PATCH_VALIDATION, {}) or build_generated_patch_validation(project_id=project_id, save=False)
    simulation = _read_json(PATCH_SIMULATION, {}) or build_patch_simulation(project_id=project_id, save=False)
    test_plan = _read_json(TEST_STUB_PLAN, {}) or build_test_stub_plan(project_id=project_id, save=False)
    categories = [
        ("objective clarity", 10 if refinement.get("ok") else 0, "refined objective exists"),
        ("context quality", min(10, len(ranking.get("ranked_context", []) or []) * 2), "ranked context available"),
        ("prompt safety", 10 if envelope.get("ok") else 0, "safety envelope active"),
        ("schema validity", 10 if validation.get("status") != "blocked" else 0, "generated edits validate"),
        ("boundary safety", 10 if validation.get("ok") else 0, "files are inside allowed boundary"),
        ("simulation", 10 if simulation.get("status") != "blocked" else 0, "patch simulation completed"),
        ("test coverage", min(10, len(test_plan.get("suggestions", []) or []) * 2), "test stubs planned"),
        ("README coverage", 10 if any("README" in str(row) for row in validation.get("rows", [])) or "README_NEXT_STEPS.md" in str(refinement.get("allowed_files", [])) else 5, "README impact visible"),
        ("rollback safety", 10 if simulation.get("dry_run") and simulation.get("source_writes") is False else 0, "simulation preserves rollback pointers"),
        ("approval safety", 10, "real apply remains approval gated"),
    ]
    total = sum(score for _, score, _ in categories)
    score = max(0, min(100, total))
    rows = [{"name": name, "status": "pass" if points >= 8 else "warn" if points else "blocked", "score": points, "message": reason} for name, points, reason in categories]
    status = "blocked" if score < 50 else "warn" if score < 80 else "pass"
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": score >= 50,
        "score": score,
        "max_score": 100,
        "categories": [{"name": name, "score": points, "reason": reason} for name, points, reason in categories],
        "strengths": [name for name, points, _ in categories if points >= 8],
        "weaknesses": [name for name, points, _ in categories if points < 8],
        "rows": rows,
        "message": f"Patch review score is {score}/100.",
    }
    if save:
        _write_json(PATCH_REVIEW_SCORE, report)
    else:
        report["preview_only"] = True
    return report


def build_patch_recovery_plan(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v17.9: create a safe retry/recovery plan for failed generated patches."""
    failure = build_patch_failure_analysis(project_id=project_id, save=False)
    validation = _read_json(GENERATED_PATCH_VALIDATION, {}) or build_generated_patch_validation(project_id=project_id, save=False)
    simulation = _read_json(PATCH_SIMULATION, {}) or build_patch_simulation(project_id=project_id, save=False)
    rows: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    if validation.get("status") == "blocked":
        actions.append({"action": "regenerate_edits", "status": "warn", "message": "Regenerate edits with stricter expected_old_text and allowed file constraints."})
    if simulation.get("status") == "blocked":
        actions.append({"action": "refresh_context", "status": "warn", "message": "Refresh code context and rerun validation before approval."})
    for row in failure.get("rows", []) or []:
        if row.get("status") in {"warn", "blocked"}:
            actions.append({"action": "add_prompt_constraint", "status": "warn", "message": f"Add future constraint for {row.get('class')}."})
    if not actions:
        actions.append({"action": "proceed_to_review", "status": "pass", "message": "No active blockers found; proceed with human review checklist."})
    rows.extend(actions)
    status = _status_from(rows)
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "failure_classes": [row.get("class") for row in failure.get("rows", []) or []],
        "safe_retry_strategy": actions,
        "files_to_avoid": ["conscious_agent/command_runner.py unless safety intent is explicit", "data/workspaces/projects.json unless registry work is explicit"],
        "tests_to_add": build_test_stub_plan(project_id=project_id, save=False).get("suggestions", []),
        "human_review_required": True,
        "rows": rows,
        "message": "Patch recovery plan created from validation, simulation, and failure analysis artifacts.",
    }
    if save:
        _write_json(PATCH_RECOVERY_PLAN, report)
    else:
        report["preview_only"] = True
    return report


def build_validated_ai_code_patch_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v18.0: generate, validate, simulate, score, and package an AI-assisted patch for approval/apply."""
    refinement = build_patch_objective_refinement(project_id=project_id, save=save)
    ranking = build_code_context_ranking(project_id=project_id, save=save)
    envelope = build_patch_safety_envelope(project_id=project_id, save=save)
    prompt = build_patch_prompt(project_id=project_id, save=save)
    parsed = build_parse_generated_edits(project_id=project_id, save=save)
    consistency = build_edit_consistency(project_id=project_id, save=save)
    validation = build_generated_patch_validation(project_id=project_id, save=save)
    simulation = build_patch_simulation(project_id=project_id, save=save)
    test_stub = build_test_stub_plan(project_id=project_id, save=save)
    review_score = build_patch_review_score(project_id=project_id, save=save)
    diff_bundle = build_code_patch_diff_bundle(project_id=project_id, save=save)
    semantic = build_semantic_checks(project_id=project_id, save=save)
    recovery = build_patch_recovery_plan(project_id=project_id, save=save)
    approval = _read_json(APPROVAL_STATE, {})
    binding = validate_approval_binding(approval=approval, project_id=project_id) if isinstance(approval, dict) and approval.get("approved") else {"ok": False, "message": "No artifact-bound approval is active."}
    generated_release = None
    transaction = None
    readiness = build_release_readiness(project_id=project_id, save=save)
    artifact = build_release_artifact(project_id=project_id, package_name="Eidolon_v18_0.zip", save=save)
    audit = build_release_audit_trail(project_id=project_id, save=save)
    learning = None
    blocked = [name for name, report in {
        "objective_refinement": refinement,
        "context_ranking": ranking,
        "safety_envelope": envelope,
        "parse_generated_edits": parsed,
        "edit_consistency": consistency,
        "generated_patch_validation": validation,
        "patch_simulation": simulation,
        "semantic_checks": semantic,
    }.items() if isinstance(report, dict) and report.get("ok") is False]
    validated_manifest_binding = {"ok": False, "message": "Validated patch approval manifest is required for real apply paths."}
    if binding.get("ok") and not blocked:
        if approve and not dry_run:
            try:
                from approval_release_workflow import _approval_manifest_binding  # local import avoids a module cycle
                validated_manifest_binding = _approval_manifest_binding(project_id=project_id)
            except Exception as error:
                validated_manifest_binding = {"ok": False, "message": str(error)}
            if not validated_manifest_binding.get("ok"):
                blocked.append("validated-patch-approval-manifest")
        if not blocked:
            generated_release = build_generated_code_release_loop(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=save)
            transaction = build_apply_code_patch_transaction(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=save)
            readiness = build_release_readiness(project_id=project_id, save=save)
            artifact = build_release_artifact(project_id=project_id, package_name="Eidolon_v18_0.zip", save=save)
            audit = build_release_audit_trail(project_id=project_id, save=save)
            learning = build_patch_learning_notes(project_id=project_id, save=save)
        else:
            learning = build_patch_learning_notes(project_id=project_id, save=save)
    else:
        learning = build_patch_learning_notes(project_id=project_id, save=save)
    status = "blocked" if blocked else "awaiting_approval" if not binding.get("ok") else "dry_run" if (dry_run or not approve) else "applied"
    report = {
        "version": VALIDATED_AI_PATCH_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "dry_run": dry_run or not approve,
        "approval_binding": binding,
        "validated_patch_manifest_binding": validated_manifest_binding,
        "review_ready": not blocked and review_score.get("score", 0) >= 50,
        "steps": {
            "objective_refinement": refinement,
            "context_ranking": ranking,
            "safety_envelope": envelope,
            "patch_prompt": prompt,
            "parse_generated_edits": parsed,
            "edit_consistency": consistency,
            "generated_patch_validation": validation,
            "patch_simulation": simulation,
            "test_stub_plan": test_stub,
            "patch_review_score": review_score,
            "diff_bundle": diff_bundle,
            "semantic_checks": semantic,
            "recovery_plan": recovery,
            "generated_code_release_loop": generated_release,
            "apply_transaction": transaction,
            "release_readiness": readiness,
            "release_artifact": artifact,
            "audit_trail": audit,
            "learning_notes": learning,
        },
        "blocked_steps": blocked,
        "message": "Validated AI code patch loop prepared review artifacts and stopped for approval." if not binding.get("ok") else "Validated AI code patch loop completed one bounded approved path and stopped.",
    }
    if save:
        _write_json(VALIDATED_AI_CODE_PATCH_LOOP, report)
        _timeline_event("validated_ai_code_patch_loop", {"project_id": project_id, "status": status, "dry_run": report["dry_run"]}, save=True)
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
    if "score" in report:
        lines.append(f"Score: {report.get('score')}/{report.get('max_score', 100)}")
    for key in ["blocked_steps", "allowed_files", "top_context_paths", "affected_surfaces", "failure_classes"]:
        values = report.get(key) or []
        if values:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values[:60]])
    rows = report.get("rows") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:60]:
            if isinstance(row, dict):
                name = row.get("name") or row.get("class") or row.get("file") or row.get("path") or row.get("edit_id") or row.get("action") or "row"
                status = row.get("status") or "info"
                msg = row.get("message") or "; ".join(row.get("reasons", []))
                lines.append(f"- {str(status).upper()} {name}: {msg}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def patch_objective_refinement_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.1 Patch Objective Refinement", report or build_patch_objective_refinement(save=False), full)


def code_context_ranking_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.2 Code Context Ranking", report or build_code_context_ranking(save=False), full)


def patch_safety_envelope_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.3 Prompt Safety Envelope", report or build_patch_safety_envelope(save=False), full)


def generated_patch_validation_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.4 Generated Patch Validator", report or build_generated_patch_validation(save=False), full)


def patch_simulation_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.5 Patch Simulation Runner", report or build_patch_simulation(save=False), full)


def test_stub_plan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.6 Test Stub Planner", report or build_test_stub_plan(save=False), full)


def patch_review_score_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.7 Patch Review Scoring", report or build_patch_review_score(save=False), full)


def patch_recovery_plan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v17.9 Patch Failure Recovery Plan", report or build_patch_recovery_plan(save=False), full)


def validated_ai_code_patch_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v18.0 Validated AI Code Patch Loop", report or build_validated_ai_code_patch_loop(save=False), full)


def print_patch_objective_refinement(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_objective_refinement(project_id=project_id, save=True)
    _json_print(report) if json_output else print(patch_objective_refinement_text(report, full=full))


def print_code_context_ranking(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_code_context_ranking(project_id=project_id, save=True)
    _json_print(report) if json_output else print(code_context_ranking_text(report, full=full))


def print_patch_safety_envelope(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_safety_envelope(project_id=project_id, save=True)
    _json_print(report) if json_output else print(patch_safety_envelope_text(report, full=full))


def print_generated_patch_validation(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_generated_patch_validation(project_id=project_id, save=True)
    _json_print(report) if json_output else print(generated_patch_validation_text(report, full=full))


def print_patch_simulation(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_simulation(project_id=project_id, save=True)
    _json_print(report) if json_output else print(patch_simulation_text(report, full=full))


def print_test_stub_plan(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_test_stub_plan(project_id=project_id, save=True)
    _json_print(report) if json_output else print(test_stub_plan_text(report, full=full))


def print_patch_review_score(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_review_score(project_id=project_id, save=True)
    _json_print(report) if json_output else print(patch_review_score_text(report, full=full))


def print_patch_recovery_plan(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_recovery_plan(project_id=project_id, save=True)
    _json_print(report) if json_output else print(patch_recovery_plan_text(report, full=full))


def print_validated_ai_code_patch_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_validated_ai_code_patch_loop(project_id=project_id, approve=approve, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(validated_ai_code_patch_loop_text(report, full=full))
