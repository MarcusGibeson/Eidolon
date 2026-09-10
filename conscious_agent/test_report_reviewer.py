from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from local_brain import local_generate
from memory import store_memory
from patch_suggester import load_patch_proposal
from paths import DATA_DIR
from test_runner import load_test_report, list_test_reports, test_report_text


TEST_REVIEWS_DIR = DATA_DIR / "test_reviews"
ACTION_LOG_FILE = DATA_DIR / "action_log.json"
MAX_OUTPUT_FOR_REVIEW = 8_000


@dataclass
class TestReviewResult:
    ok: bool
    review_id: str = ""
    recommendation: str = ""
    error: str = ""


def _ensure_storage() -> None:
    TEST_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
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


def _new_review_id(report_id: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_report = "".join(char if char.isalnum() or char in {"_", "-"} else "-" for char in report_id)
    return f"review_{timestamp}_{safe_report[:90]}"


def _review_path(review_id: str) -> Path:
    return TEST_REVIEWS_DIR / f"{review_id}.json"


def save_test_review(review: dict[str, Any]) -> None:
    _ensure_storage()
    with _review_path(review["id"]).open("w", encoding="utf-8") as file:
        json.dump(review, file, indent=2)



def resolve_test_review_id(review_id: str) -> str:
    """Resolves latest/last into the newest saved test review id."""
    token = (review_id or "").strip()
    if token.lower() not in {"latest", "last"}:
        return token

    reviews = list_test_reviews()
    if not reviews:
        return ""

    return reviews[0].get("id", "")


def load_test_review(review_id: str) -> dict[str, Any] | None:
    resolved_id = resolve_test_review_id(review_id)
    if not resolved_id:
        return None

    path = _review_path(resolved_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_test_reviews() -> list[dict[str, Any]]:
    _ensure_storage()
    reviews: list[dict[str, Any]] = []
    for path in sorted(TEST_REVIEWS_DIR.glob("*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            reviews.append(data)
    return reviews


def _latest_report_id() -> str:
    reports = list_test_reports()
    if not reports:
        return ""
    return reports[0].get("id", "")


def _resolve_report(report_id: str) -> tuple[str, dict[str, Any] | None]:
    if report_id.strip().lower() == "latest":
        latest = _latest_report_id()
        if not latest:
            return "", None
        return latest, load_test_report(latest)

    return report_id, load_test_report(report_id)


def _clip(text: str, limit: int = MAX_OUTPUT_FOR_REVIEW) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[TRUNCATED FOR REVIEW: output exceeded {limit} characters]"


def _failed_commands(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [command for command in report.get("commands", []) if not command.get("ok")]


def _output_blob(command: dict[str, Any]) -> str:
    parts = [
        command.get("error", ""),
        command.get("message", ""),
        command.get("stdout", ""),
        command.get("stderr", ""),
    ]
    return "\n".join(part for part in parts if part)


def _detect_risk_signals(command_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patterns = {
        "syntax_error": ["syntaxerror", "invalid syntax"],
        "traceback": ["traceback (most recent call last)"],
        "missing_module": ["modulenotfounderror", "importerror", "no module named"],
        "name_error": ["nameerror"],
        "type_error": ["typeerror"],
        "attribute_error": ["attributeerror"],
        "assertion_failure": ["assertionerror", "failed", "failures"],
        "command_blocked": ["blocked", "not in the approved whitelist", "not allowed"],
        "timeout": ["timed out", "timeout"],
        "file_not_found": ["filenotfounderror", "no such file or directory", "target file no longer exists"],
    }

    signals: list[dict[str, Any]] = []
    for command in command_results:
        blob = _output_blob(command).lower()
        for signal_name, needles in patterns.items():
            if any(needle in blob for needle in needles):
                signals.append({
                    "signal": signal_name,
                    "command": command.get("command"),
                    "return_code": command.get("return_code"),
                })
                break
    return signals


def _patch_target_matches_output(report: dict[str, Any], failed: list[dict[str, Any]]) -> bool:
    patch = report.get("patch", {})
    target_file = (patch.get("target_file") or "").replace("\\", "/")
    if not target_file:
        return False

    target_name = Path(target_file).name.lower()
    target_stem = Path(target_file).stem.lower()

    for command in failed:
        blob = _output_blob(command).lower().replace("\\", "/")
        if target_file.lower() in blob:
            return True
        if target_name and target_name in blob:
            return True
        if target_stem and target_stem in blob:
            return True
    return False


def _heuristic_review(report: dict[str, Any]) -> dict[str, Any]:
    failed = _failed_commands(report)
    signals = _detect_risk_signals(report.get("commands", []))
    patch = report.get("patch", {})
    patch_id = patch.get("patch_id", "")
    patch_status = patch.get("status", "")
    patch_found = bool(patch.get("patch_found"))
    report_status = report.get("status", "")
    dry_run = bool(report.get("dry_run"))

    if dry_run:
        if failed:
            return {
                "recommendation": "fix_test_workflow",
                "summary": "The dry run found one or more commands that are not allowed or not valid. Fix the workflow commands before running real tests.",
                "next_actions": [
                    "Run --list-allowed-commands to see allowed command patterns.",
                    "Update the --test-command values and dry-run the workflow again.",
                ],
                "confidence": 0.86,
                "risk_signals": signals,
            }
        return {
            "recommendation": "run_real_tests",
            "summary": "The dry run passed. The configured commands are allowed, but no real tests were executed yet.",
            "next_actions": [
                "Run the same --run-test-workflow command without --dry-run.",
            ],
            "confidence": 0.9,
            "risk_signals": signals,
        }

    if report_status == "passed" and not failed:
        if patch_found and patch_status == "applied":
            return {
                "recommendation": "keep_patch",
                "summary": "All configured checks passed after the applied patch. Keep the patch for now.",
                "next_actions": [
                    "Run any broader manual tests you care about.",
                    "Re-index the project if the patch changed code structure.",
                ],
                "confidence": 0.82,
                "risk_signals": signals,
            }
        if patch_found and patch_status == "proposed":
            return {
                "recommendation": "safe_to_apply_then_retest",
                "summary": "The checks passed, but the patch is still proposed. Apply it first, then run the workflow again.",
                "next_actions": [
                    f"Run: python conscious_agent/main.py --apply-patch {patch_id} --dry-run",
                    f"Then: python conscious_agent/main.py --apply-patch {patch_id}",
                    f"Then re-run the test workflow for {patch_id}.",
                ],
                "confidence": 0.78,
                "risk_signals": signals,
            }
        return {
            "recommendation": "checks_passed",
            "summary": "All configured checks passed. No patch-specific action is needed.",
            "next_actions": ["Continue development."],
            "confidence": 0.84,
            "risk_signals": signals,
        }

    if failed:
        patch_related = _patch_target_matches_output(report, failed)
        severe_signals = {"syntax_error", "traceback", "missing_module", "name_error", "type_error", "attribute_error"}
        found_severe = any(signal.get("signal") in severe_signals for signal in signals)

        if patch_found and patch_status == "applied" and (patch_related or found_severe):
            return {
                "recommendation": "rollback_patch",
                "summary": "One or more checks failed after an applied patch, and the output looks code-related or patch-related. Roll back unless you can clearly prove the failure is unrelated.",
                "next_actions": [
                    f"Review the failed command output with --show-test-report {report.get('id')} --show-test-output.",
                    f"Dry-run rollback: python conscious_agent/main.py --rollback-patch {patch_id} --dry-run",
                    f"Rollback if the dry run passes: python conscious_agent/main.py --rollback-patch {patch_id}",
                ],
                "confidence": 0.8 if patch_related else 0.66,
                "risk_signals": signals,
            }

        if any(signal.get("signal") == "command_blocked" for signal in signals):
            return {
                "recommendation": "fix_test_workflow",
                "summary": "The workflow failed because at least one command was blocked or not whitelisted. This is likely a workflow configuration issue, not necessarily a code issue.",
                "next_actions": [
                    "Run --list-allowed-commands.",
                    "Replace blocked commands with approved equivalents.",
                    "Run the workflow again with --dry-run first.",
                ],
                "confidence": 0.88,
                "risk_signals": signals,
            }

        return {
            "recommendation": "manual_review",
            "summary": "One or more checks failed. The failure is not clearly patch-related from heuristics alone. Review the full output before deciding whether to keep or rollback.",
            "next_actions": [
                f"Run: python conscious_agent/main.py --show-test-report {report.get('id')} --show-test-output",
                "Review the failing commands and rerun targeted checks.",
            ],
            "confidence": 0.58,
            "risk_signals": signals,
        }

    return {
        "recommendation": "manual_review",
        "summary": "The report did not clearly pass or fail. Review it manually.",
        "next_actions": [f"Run: python conscious_agent/main.py --show-test-report {report.get('id')} --show-test-output"],
        "confidence": 0.5,
        "risk_signals": signals,
    }


def _ai_review(report: dict[str, Any], heuristic: dict[str, Any]) -> str:
    report_text = _clip(test_report_text(report, include_output=True))
    prompt = f"""
You are reviewing an Eidolon test workflow report after a patch/test run.

You are not allowed to execute commands or modify files.
Your job is to summarize the result and recommend one of these actions:
- keep_patch
- rollback_patch
- manual_review
- fix_test_workflow
- run_real_tests
- safe_to_apply_then_retest
- checks_passed

Heuristic review:
{json.dumps(heuristic, indent=2)}

Test report:
{report_text}

Respond in this exact structure:
Summary: <2-4 sentences>
Recommendation: <one of the allowed actions>
Reasons:
- <reason 1>
- <reason 2>
Next steps:
- <step 1>
- <step 2>
""".strip()

    response = local_generate(prompt=prompt, temperature=0.25, max_tokens=550)
    if response.startswith("My local brain hit an error") or response.startswith("I tried to use my local brain"):
        return ""
    return response.strip()


def review_test_report(report_id: str, use_ai: bool = True) -> TestReviewResult:
    resolved_report_id, report = _resolve_report(report_id)
    if not report:
        return TestReviewResult(ok=False, error=f"Test report not found: {report_id}")

    heuristic = _heuristic_review(report)
    ai_text = _ai_review(report, heuristic) if use_ai else ""
    review_id = _new_review_id(resolved_report_id)
    created_at = datetime.now().isoformat(timespec="seconds")

    patch = report.get("patch", {})
    review = {
        "id": review_id,
        "created_at": created_at,
        "test_report_id": resolved_report_id,
        "test_report_status": report.get("status"),
        "patch_id": patch.get("patch_id", ""),
        "patch_status": patch.get("status", ""),
        "target_file": patch.get("target_file", ""),
        "recommendation": heuristic.get("recommendation"),
        "summary": heuristic.get("summary"),
        "confidence": heuristic.get("confidence"),
        "next_actions": heuristic.get("next_actions", []),
        "risk_signals": heuristic.get("risk_signals", []),
        "failed_commands": [
            {
                "command": command.get("command"),
                "return_code": command.get("return_code"),
                "error": command.get("error"),
                "message": command.get("message"),
            }
            for command in _failed_commands(report)
        ],
        "ai_review": ai_text,
        "ai_used": bool(ai_text),
    }

    save_test_review(review)

    _append_action_log({
        "timestamp": created_at,
        "action": "test_report_review",
        "review_id": review_id,
        "test_report_id": resolved_report_id,
        "patch_id": review.get("patch_id", ""),
        "recommendation": review.get("recommendation"),
        "ai_used": review.get("ai_used"),
    })

    store_memory({
        "type": "test_report_review_event",
        "content": (
            f"Reviewed test report {resolved_report_id}. "
            f"Recommendation: {review.get('recommendation')}. Summary: {review.get('summary')}"
        ),
        "source": "test_report_reviewer",
        "review_id": review_id,
        "test_report_id": resolved_report_id,
        "patch_id": review.get("patch_id", ""),
        "recommendation": review.get("recommendation"),
    })

    return TestReviewResult(
        ok=True,
        review_id=review_id,
        recommendation=review.get("recommendation", ""),
    )


def test_review_text(review: dict[str, Any], include_ai: bool = True) -> str:
    lines = [
        f"# Test Review: {review.get('id')}",
        "",
        f"Created: {review.get('created_at')}",
        f"Test report: {review.get('test_report_id')}",
        f"Report status: {review.get('test_report_status')}",
        f"Patch: {review.get('patch_id') or '[none]'}",
        f"Target file: {review.get('target_file') or '[none]'}",
        f"Recommendation: {review.get('recommendation')}",
        f"Confidence: {review.get('confidence')}",
        "",
        "## Summary",
        review.get("summary", ""),
        "",
        "## Risk signals",
    ]

    signals = review.get("risk_signals", [])
    if signals:
        for signal in signals:
            lines.append(f"- {signal.get('signal')} from `{signal.get('command')}`")
    else:
        lines.append("- none detected")

    failed = review.get("failed_commands", [])
    lines.extend(["", "## Failed commands"])
    if failed:
        for command in failed:
            lines.append(f"- {command.get('command')} | return={command.get('return_code')} | {command.get('error') or command.get('message') or ''}")
    else:
        lines.append("- none")

    lines.extend(["", "## Next actions"])
    for action in review.get("next_actions", []):
        lines.append(f"- {action}")

    if include_ai and review.get("ai_review"):
        lines.extend(["", "## Local AI review", review.get("ai_review", "")])

    return "\n".join(lines).strip()


def print_test_review(report_id: str, use_ai: bool = True) -> None:
    result = review_test_report(report_id, use_ai=use_ai)
    if not result.ok:
        print("Test report review failed.")
        print(f"Reason: {result.error}")
        return

    review = load_test_review(result.review_id)
    if not review:
        print(f"Review was created, but could not be loaded: {result.review_id}")
        return

    print(test_review_text(review, include_ai=True))
    print()
    print(f"Saved test review: {result.review_id}")
    print("Shortcut: python conscious_agent/main.py --show-test-review latest")


def print_saved_test_review(review_id: str, include_ai: bool = True) -> None:
    review = load_test_review(review_id)
    if not review:
        print(f"Test review not found: {review_id}")
        return
    print(test_review_text(review, include_ai=include_ai))


def print_test_reviews() -> None:
    reviews = list_test_reviews()
    if not reviews:
        print("No test reviews found.")
        return

    for review in reviews:
        print(
            f"{review.get('id')} | "
            f"recommendation={review.get('recommendation')} | "
            f"report={review.get('test_report_id')} | "
            f"patch={review.get('patch_id') or '[none]'}"
        )
        print(f"  Summary: {review.get('summary')}")
