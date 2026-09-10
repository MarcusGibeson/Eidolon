from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from code_reviewer import review_project_file
from memory import store_memory
from patch_applier import apply_patch
from patch_suggester import load_patch_proposal, patch_proposal_text, suggest_patch, resolve_patch_id
from paths import DATA_DIR
from test_report_reviewer import review_test_report, test_review_text, load_test_review
from test_runner import run_test_workflow, load_test_report, test_report_text


SELF_IMPROVEMENTS_DIR = DATA_DIR / "self_improvements"
ACTION_LOG_FILE = DATA_DIR / "action_log.json"
MAX_STORED_REVIEW_CHARS = 12_000

DEFAULT_SELF_IMPROVEMENT_TEST_COMMANDS = [
    "python conscious_agent/main.py --status",
    "python conscious_agent/main.py --review-project-file conscious_agent/self_improver.py --no-ai-review",
]


@dataclass
class SelfImprovementResult:
    ok: bool
    run_id: str = ""
    patch_id: str = ""
    test_report_id: str = ""
    test_review_id: str = ""
    recommendation: str = ""
    status: str = ""
    text: str = ""
    error: str = ""
    dry_run: bool = False


def _ensure_storage() -> None:
    SELF_IMPROVEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    ACTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not ACTION_LOG_FILE.exists():
        with ACTION_LOG_FILE.open("w", encoding="utf-8") as file:
            json.dump([], file, indent=2)


def _load_action_log() -> list[dict[str, Any]]:
    _ensure_storage()
    try:
        with ACTION_LOG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _save_action_log(log: list[dict[str, Any]]) -> None:
    _ensure_storage()
    with ACTION_LOG_FILE.open("w", encoding="utf-8") as file:
        json.dump(log, file, indent=2)


def _append_action_log(entry: dict[str, Any]) -> None:
    log = _load_action_log()
    log.append(entry)
    _save_action_log(log)


def _safe_slug(value: str, max_len: int = 60) -> str:
    slug = "".join(char if char.isalnum() or char in {"_", "-"} else "-" for char in value.strip())
    slug = "-".join(part for part in slug.split("-") if part)
    return (slug or "self-improvement")[:max_len]


def _new_run_id(relative_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"selfimp_{timestamp}_{_safe_slug(relative_path)}"


def _run_path(run_id: str) -> Path:
    return SELF_IMPROVEMENTS_DIR / f"{run_id}.json"


def save_self_improvement_run(run: dict[str, Any]) -> None:
    _ensure_storage()
    with _run_path(run["id"]).open("w", encoding="utf-8") as file:
        json.dump(run, file, indent=2)



def resolve_self_improvement_run_id(run_id: str) -> str:
    """Resolves latest/last into the newest self-improvement run id."""
    token = (run_id or "").strip()
    if token.lower() not in {"latest", "last"}:
        return token

    runs = list_self_improvement_runs()
    if not runs:
        return ""

    return runs[0].get("id", "")


def latest_self_improvement_patch_id() -> str:
    """Returns the patch id from the newest self-improvement run."""
    runs = list_self_improvement_runs()
    if not runs:
        return ""
    return runs[0].get("patch_id", "") or ""


def load_self_improvement_run(run_id: str) -> dict[str, Any] | None:
    resolved_id = resolve_self_improvement_run_id(run_id)
    if not resolved_id:
        return None

    path = _run_path(resolved_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_self_improvement_runs() -> list[dict[str, Any]]:
    _ensure_storage()
    runs: list[dict[str, Any]] = []
    for path in sorted(SELF_IMPROVEMENTS_DIR.glob("*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            runs.append(data)
    return runs


def _find_run_by_patch_id(patch_id: str) -> dict[str, Any] | None:
    for run in list_self_improvement_runs():
        if run.get("patch_id") == patch_id:
            return run
    return None


def _clip(text: str, limit: int = MAX_STORED_REVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[TRUNCATED: stored review exceeded {limit} characters]"


def start_self_improvement(relative_path: str, request: str, use_ai_review: bool = False) -> SelfImprovementResult:
    """
    Starts a supervised self-improvement run.

    This step is advisory only:
    - Review the target file.
    - Ask the local model to propose a patch.
    - Save a self-improvement run record.
    - Do not apply anything.
    """
    run_id = _new_run_id(relative_path)
    created_at = datetime.now().isoformat(timespec="seconds")

    review = review_project_file(relative_path, use_ai=use_ai_review)
    if not review.ok:
        return SelfImprovementResult(ok=False, run_id=run_id, error=review.error, status="review_failed")

    patch = suggest_patch(relative_path, request, use_ai=True)
    if not patch.ok:
        run = {
            "id": run_id,
            "status": "patch_failed",
            "created_at": created_at,
            "target_file": relative_path,
            "request": request,
            "review_text": _clip(review.text),
            "patch_error": patch.error,
            "patch_id": "",
        }
        save_self_improvement_run(run)
        return SelfImprovementResult(ok=False, run_id=run_id, error=patch.error, status="patch_failed")

    run = {
        "id": run_id,
        "status": "patch_proposed",
        "created_at": created_at,
        "target_file": patch.target_file,
        "request": request,
        "review_ai_used": use_ai_review,
        "review_text": _clip(review.text),
        "patch_id": patch.patch_id,
        "patch_status": "proposed",
        "test_report_id": "",
        "test_review_id": "",
        "recommendation": "review_patch_before_applying",
    }
    save_self_improvement_run(run)

    _append_action_log({
        "timestamp": created_at,
        "action": "self_improvement_started",
        "run_id": run_id,
        "patch_id": patch.patch_id,
        "target_file": patch.target_file,
        "status": "patch_proposed",
    })

    store_memory({
        "type": "self_improvement_event",
        "content": (
            f"Started supervised self-improvement run {run_id} for '{patch.target_file}'. "
            f"Patch proposed: {patch.patch_id}. Request: {request}"
        ),
        "source": "self_improver",
        "run_id": run_id,
        "patch_id": patch.patch_id,
        "file": patch.target_file,
    })

    text = self_improvement_run_text(run, include_review=False)
    proposal = load_patch_proposal(patch.patch_id)
    if proposal:
        text += "\n\n" + patch_proposal_text(proposal, include_full_content=False)

    return SelfImprovementResult(
        ok=True,
        run_id=run_id,
        patch_id=patch.patch_id,
        status="patch_proposed",
        recommendation="review_patch_before_applying",
        text=text,
    )


def apply_self_improvement_patch(
    patch_id: str,
    commands: list[str] | None = None,
    use_ai_review: bool = True,
    dry_run: bool = False,
) -> SelfImprovementResult:
    """
    Applies a proposed self-improvement patch, then runs tests and reviews the report.

    This is still supervised because Marcus must explicitly run this command with a patch id.
    """
    requested_patch_id = patch_id
    if (patch_id or "").strip().lower() in {"latest", "last"}:
        patch_id = latest_self_improvement_patch_id() or resolve_patch_id(patch_id, status="proposed") or patch_id
    else:
        patch_id = resolve_patch_id(patch_id, status="proposed") or patch_id

    proposal = load_patch_proposal(patch_id)
    if not proposal:
        return SelfImprovementResult(ok=False, patch_id=patch_id, error=f"Patch not found: {requested_patch_id}")

    run = _find_run_by_patch_id(patch_id) or {
        "id": _new_run_id(proposal.get("target_file", "manual-patch")),
        "status": "manual_patch_reference",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "target_file": proposal.get("target_file", ""),
        "request": proposal.get("request", ""),
        "patch_id": patch_id,
    }

    apply_result = apply_patch(patch_id, dry_run=dry_run)
    run["last_apply_dry_run"] = dry_run
    run["last_apply_ok"] = apply_result.ok
    run["last_apply_error"] = apply_result.error
    run["last_apply_message"] = apply_result.message

    if not apply_result.ok:
        run["status"] = "apply_failed"
        save_self_improvement_run(run)
        return SelfImprovementResult(
            ok=False,
            run_id=run.get("id", ""),
            patch_id=patch_id,
            error=apply_result.error,
            status="apply_failed",
            dry_run=dry_run,
        )

    if dry_run:
        run["status"] = "apply_dry_run_passed"
        run["recommendation"] = "apply_patch_when_ready"
        save_self_improvement_run(run)
        return SelfImprovementResult(
            ok=True,
            run_id=run.get("id", ""),
            patch_id=patch_id,
            status="apply_dry_run_passed",
            recommendation="apply_patch_when_ready",
            text=self_improvement_run_text(run, include_review=False),
            dry_run=True,
        )

    test_commands = [command.strip() for command in (commands or []) if command and command.strip()]
    if not test_commands:
        test_commands = DEFAULT_SELF_IMPROVEMENT_TEST_COMMANDS.copy()

    test_result = run_test_workflow(patch_id=patch_id, commands=test_commands, dry_run=False)
    if not test_result.report_id:
        run["status"] = "test_workflow_failed"
        run["test_error"] = test_result.error
        save_self_improvement_run(run)
        return SelfImprovementResult(
            ok=False,
            run_id=run.get("id", ""),
            patch_id=patch_id,
            error=test_result.error,
            status="test_workflow_failed",
        )

    review_result = review_test_report(test_result.report_id, use_ai=use_ai_review)
    if not review_result.ok:
        run["status"] = "test_review_failed"
        run["test_report_id"] = test_result.report_id
        run["test_review_error"] = review_result.error
        save_self_improvement_run(run)
        return SelfImprovementResult(
            ok=False,
            run_id=run.get("id", ""),
            patch_id=patch_id,
            test_report_id=test_result.report_id,
            error=review_result.error,
            status="test_review_failed",
        )

    run["status"] = "tested_and_reviewed"
    run["patch_status"] = "applied"
    run["applied_at"] = datetime.now().isoformat(timespec="seconds")
    run["test_report_id"] = test_result.report_id
    run["test_review_id"] = review_result.review_id
    run["recommendation"] = review_result.recommendation
    run["test_commands"] = test_commands
    save_self_improvement_run(run)

    _append_action_log({
        "timestamp": run["applied_at"],
        "action": "self_improvement_applied_and_reviewed",
        "run_id": run.get("id"),
        "patch_id": patch_id,
        "test_report_id": test_result.report_id,
        "test_review_id": review_result.review_id,
        "recommendation": review_result.recommendation,
    })

    store_memory({
        "type": "self_improvement_event",
        "content": (
            f"Applied and tested self-improvement patch {patch_id}. "
            f"Report: {test_result.report_id}. Review: {review_result.review_id}. "
            f"Recommendation: {review_result.recommendation}."
        ),
        "source": "self_improver",
        "run_id": run.get("id"),
        "patch_id": patch_id,
        "test_report_id": test_result.report_id,
        "test_review_id": review_result.review_id,
        "recommendation": review_result.recommendation,
    })

    return SelfImprovementResult(
        ok=True,
        run_id=run.get("id", ""),
        patch_id=patch_id,
        test_report_id=test_result.report_id,
        test_review_id=review_result.review_id,
        recommendation=review_result.recommendation,
        status="tested_and_reviewed",
        text=self_improvement_run_text(run, include_review=False),
    )


def self_improvement_run_text(run: dict[str, Any], include_review: bool = False) -> str:
    lines = [
        f"# Self-Improvement Run: {run.get('id')}",
        "",
        f"Status: {run.get('status')}",
        f"Created: {run.get('created_at')}",
        f"Target file: {run.get('target_file')}",
        f"Patch id: {run.get('patch_id') or '[none]'}",
        f"Patch status: {run.get('patch_status') or '[unknown]'}",
        f"Test report: {run.get('test_report_id') or '[none]'}",
        f"Test review: {run.get('test_review_id') or '[none]'}",
        f"Recommendation: {run.get('recommendation') or '[none]'}",
        "",
        "## Request",
        run.get("request", ""),
    ]

    if run.get("patch_error"):
        lines.extend(["", "## Patch error", run.get("patch_error", "")])

    if run.get("last_apply_error"):
        lines.extend(["", "## Last apply error", run.get("last_apply_error", "")])

    if run.get("test_commands"):
        lines.extend(["", "## Test commands"])
        lines.extend(f"- {command}" for command in run.get("test_commands", []))

    if include_review and run.get("review_text"):
        lines.extend(["", "## Initial code review", run.get("review_text", "")])

    if include_review and run.get("test_review_id"):
        review = load_test_review(run.get("test_review_id", ""))
        if review:
            lines.extend(["", "## Saved test review", test_review_text(review, include_ai=True)])

    if include_review and run.get("test_report_id"):
        report = load_test_report(run.get("test_report_id", ""))
        if report:
            lines.extend(["", "## Saved test report", test_report_text(report, include_output=False)])

    return "\n".join(lines).strip()


def print_self_improvement(relative_path: str, request: str, use_ai_review: bool = False) -> None:
    result = start_self_improvement(relative_path, request, use_ai_review=use_ai_review)
    if not result.ok:
        print("Self-improvement proposal failed.")
        print(f"Run id: {result.run_id}")
        print(f"Reason: {result.error}")
        return
    print(result.text)
    print()
    print("Next supervised step:")
    print("  python conscious_agent/main.py --show-self-improvement latest")
    print("  python conscious_agent/main.py --show-patch latest")
    print("  python conscious_agent/main.py --self-improve-apply latest --dry-run")
    print()
    print(f"Concrete ids, if needed: run={result.run_id} patch={result.patch_id}")


def print_self_improvement_apply(
    patch_id: str,
    commands: list[str] | None = None,
    use_ai_review: bool = True,
    dry_run: bool = False,
) -> None:
    result = apply_self_improvement_patch(
        patch_id=patch_id,
        commands=commands,
        use_ai_review=use_ai_review,
        dry_run=dry_run,
    )

    if not result.ok:
        print("Self-improvement apply workflow failed.")
        if result.run_id:
            print(f"Run id: {result.run_id}")
        print(f"Patch id: {patch_id}")
        print(f"Status: {result.status}")
        print(f"Reason: {result.error}")
        return

    print(result.text)
    print()
    if result.dry_run:
        print("Dry run passed. No files were changed.")
        print("Apply when ready: python conscious_agent/main.py --self-improve-apply latest")
        return

    print("Self-improvement patch applied, tested, and reviewed.")
    print(f"Test report: {result.test_report_id}")
    print(f"Test review: {result.test_review_id}")
    print(f"Recommendation: {result.recommendation}")
    if result.recommendation == "rollback_patch":
        print("Suggested rollback: python conscious_agent/main.py --rollback-patch latest --dry-run")


def print_self_improvement_runs() -> None:
    runs = list_self_improvement_runs()
    if not runs:
        print("No self-improvement runs found.")
        return

    for run in runs:
        print(
            f"{run.get('id')} | "
            f"status={run.get('status')} | "
            f"patch={run.get('patch_id') or '[none]'} | "
            f"target={run.get('target_file')}"
        )
        print(f"  Recommendation: {run.get('recommendation') or '[none]'}")
        print(f"  Request: {run.get('request')}")


def print_self_improvement_run(run_id: str, include_review: bool = False) -> None:
    run = load_self_improvement_run(run_id)
    if not run:
        print(f"Self-improvement run not found: {run_id}")
        return
    print(self_improvement_run_text(run, include_review=include_review))
