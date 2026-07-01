from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from file_tools import active_project_root
from memory import store_memory
from paths import DATA_DIR
from settings_manager import get_setting


ACTION_LOG_FILE = DATA_DIR / "action_log.json"
COMMAND_TIMEOUT_SECONDS = int(get_setting("command_timeout_seconds", 45))
MAX_CAPTURE_CHARS = int(get_setting("max_capture_chars", 12_000))

# These tokens are blocked anywhere in a command string because they imply shell
# behavior, network access, package installation, destructive file operations, or
# system-level changes. The runner uses shell=False, but we still block them to
# keep intent obvious and safe.
BLOCKED_TOKENS = {
    "&&", "||", ";", "|", ">", "<", "`",
    "rm", "del", "erase", "rmdir", "remove-item", "rd",
    "format", "shutdown", "restart-computer", "stop-computer",
    "curl", "wget", "iwr", "irm", "invoke-webrequest", "invoke-restmethod",
    "pip", "pip3", "npm", "npx", "yarn", "pnpm",
    "powershell", "pwsh", "cmd",
    "chmod", "chown", "reg", "schtasks", "sc",
    "git-push", "git-reset", "git-clean", "git-checkout",
}

# Allowed main.py flags when running Eidolon through command execution.
# Intentionally excludes writing commands like apply/rollback/suggest-patch.
ALLOWED_MAIN_FLAGS = {
    "--status",
    "--once",
    "--project-status",
    "--project-tree",
    "--read-project-file",
    "--search-project-files",
    "--project-file-path",
    "--index-project",
    "--project-index-summary",
    "--search-project-index",
    "--review-project-file",
    "--no-ai-review",
    "--search",
    "--semantic-search",
    "--list-patches",
    "--show-patch",
    "--show-patch-full",
    "--list-applied-patches",
    "--list-rolled-back-patches",
    "--list-test-reports",
    "--show-test-report",
    "--show-test-output",
    "--review-test-report",
    "--no-ai-test-review",
    "--list-test-reviews",
    "--show-test-review",
    "--hide-ai-review",
    "--list-self-improvements",
    "--show-self-improvement",
    "--show-self-improvement-full",
    "--maintenance-scan",
    "--no-ai-maintenance",
    "--list-maintenance-scans",
    "--show-maintenance-scan",
    "--show-maintenance-full",
    "--hide-maintenance-ai",
    "--latest-ids",
    "--memory-status",
    "--list-memory-summaries",
    "--show-memory-summary",
    "--show-memory-summary-full",
    "--plan-session",
    "--no-ai-session",
    "--list-session-plans",
    "--show-session-plan",
    "--show-session-plan-full",
    "--hide-session-ai",
    "--goal-status",
    "--list-goals",
    "--goal-filter-status",
    "--goal-filter-project",
    "--hide-cancelled-goals",
    "--show-goal",
    "--show-goal-full",
    "--task-status",
    "--list-tasks",
    "--task-filter-status",
    "--task-filter-project",
    "--hide-cancelled-tasks",
    "--show-task",
    "--show-task-full",
    "--next-task",
    "--guided-work-session",
    "--guided-session-full",
    "--list-guided-sessions",
    "--show-guided-session",
    "--dev-cycle",
    "--dev-cycle-full",
    "--list-dev-cycles",
    "--show-dev-cycle",
    "--dev-loop",
    "--dev-loop-steps",
    "--no-ai-dev-loop",
    "--dev-loop-full",
    "--list-dev-loops",
    "--show-dev-loop",
    "--self-development-cycle",
    "--self-development-create-task",
    "--self-development-prompt",
    "--no-ai-self-development",
    "--self-development-full",
    "--list-self-development-cycles",
    "--show-self-development-cycle",
    "--self-development-trial-review",
    "--self-development-smoke-triage",
    "--self-development-dashboard-hardening",
    "--self-development-implementation-proposal",
    "--self-development-save-proposal",
    "--self-development-patch-draft",
    "--self-development-patch-draft-cycle",
    "--self-development-save-patch-draft",
    "--self-development-patch-application",
    "--self-development-patch-application-draft",
    "--self-development-save-patch-application",
    "--approval-inbox",
    "--list-approvals",
    "--approval-filter-status",
    "--show-approval",
    "--approval-full",
    "--settings",
    "--get-setting",
    "--settings-health",
    "--desktop-status",
    "--desktop-tray-status",
    "--setup-check",
    "--setup-full",
    "--list-setup-reports",
    "--show-setup-report",
    "--onboarding",
    "--onboarding-full",
    "--onboarding-use-latest-setup",
    "--list-onboarding-runs",
    "--show-onboarding-run",
    "--diagnostics",
    "--diagnostics-full",
    "--list-diagnostic-reports",
    "--show-diagnostic-report",
    "--watch-once",
    "--watch-loop",
    "--watch-interval",
    "--watch-cycles",
    "--no-ai-watch",
    "--watch-full",
    "--list-watch-reports",
    "--show-watch-report",
    "--hide-watch-ai",
    "--notifications",
    "--list-notifications",
    "--notification-filter-status",
    "--include-dismissed-notifications",
    "--show-notification",
    "--notification-full",
    "--mark-notification-read",
    "--dismiss-notification",
    "--notification-note",
    "--clear-dismissed-notifications",
    "--chat-action",
    "--list-chat-actions",
    "--chat-action-filter-status",
    "--show-chat-action",
    "--chat-action-full",
    "--work-queue",
    "--task-work",
    "--queue-patch",
    "--queue-task-patch",
    "--suggest-patch-for-work",
    "--suggest-patch-for-task",
    "--create-patch-followups",
    "--create-patch-task-followups",
    "--queue-patch-project",
    "--queue-patch-priority",
    "--queue-patch-risk",
    "--queue-patch-requires-approval",
    "--execute-task-work",
    "--execute-task-work-id",
    "--execute-task-work-project",
    "--approve-task-work-execution",
    "--no-ai-task-work-executor",
    "--task-work-executor-full",
    "--execute-work",
    "--execute-work-id",
    "--execute-work-project",
    "--approve-work-execution",
    "--no-ai-work-executor",
    "--work-executor-full",
    "--request-task-approval",
    "--request-next-task-approval",
    "--task-approval-project",
    "--task-approval-reason",
    "--force-task-approval",
    "--show-task-approvals",
    "--task-approval-full",
    "--task-recovery-summary",
    "--list-task-recoveries",
    "--show-task-recovery",
    "--mark-task-ready-for-retry",
    "--retry-task-work",
    "--task-recovery-project",
    "--task-recovery-note",
    "--task-recovery-full",
    "--work-cycle",
    "--work-cycle-project",
    "--work-cycle-steps",
    "--no-ai-work-cycle",
    "--no-work-cycle-seed",
    "--no-work-cycle-followups",
    "--no-work-cycle-approval-requests",
    "--work-cycle-auto-retry-recovery",
    "--work-cycle-full",
    "--list-work-cycles",
    "--show-work-cycle",
    "--stable-loop-preflight",
    "--stable-loop",
    "--stable-loop-project",
    "--stable-loop-steps",
    "--stable-loop-live",
    "--approve-stable-loop-actions",
    "--no-ai-stable-loop",
    "--no-stable-loop-seed",
    "--no-stable-loop-followups",
    "--no-stable-loop-approval-requests",
    "--stable-loop-auto-retry-recovery",
    "--stable-loop-full",
    "--stable-loop-guardrails",
    "--stable-loop-bypass-closure-guardrails",
    "--stabilization-checkpoint",
    "--stabilization-full",
    "--stabilization-json",
    "--doctor",
    "--doctor-full",
    "--readiness-json",
    "--repair-suggestions",
    "--patch-integrity",
    "--project-snapshot",
    "--task-review",
    "--recovery-drill",
    "--stable-loop-confidence",
    "--hardening-report",
    "--controlled-self-build",
    "--controlled-self-build-live",
    "--approve-controlled-self-build",
    "--controlled-self-build-steps",
    "--select-task",
    "--plan-patch",
    "--patch-workspace-status",
    "--stage-patch",
    "--preview-diff",
    "--apply-staged-patch",
    "--verify-latest-patch",
    "--rollback-latest-patch",
    "--readme-gate",
    "--controlled-self-build-cycle",
    "--supervised-dev-loop",
    "--codebase-map",
    "--patch-goal-intake-classifier",
    "--relevant-file-context-selector",
    "--historical-failure-context-binder",
    "--risk-aware-context-budgeter",
    "--verification-requirement-compiler",
    "--patch-prompt-context-packet-builder",
    "--context-completeness-reviewer",
    "--patch-context-dashboard-api-cli",
    "--pre-v72-patch-context-gate",
    "--patch-generation-context-builder",
    "--patch-intent-normalizer",
    "--patch-scope-contract-builder",
    "--patch-prompt-composer",
    "--patch-draft-output-schema",
    "--patch-draft-safety-reviewer",
    "--patch-draft-evidence-binder",
    "--patch-draft-dashboard-api-cli",
    "--local-model-handoff-stub",
    "--pre-v73-patch-draft-gate",
    "--supervised-patch-draft-composer",
    "--patch-review-intake",
    "--patch-review-diff-boundary",
    "--patch-review-scope",
    "--patch-review-safety",
    "--patch-review-docs",
    "--patch-review-verification",
    "--patch-review-risk",
    "--patch-review-report",
    "--patch-review-dashboard-api-cli",
    "--pre-v74-patch-review-gate",
    "--patch-draft-review-diff-validation-layer",
    "--patch-trial-intake",
    "--patch-trial-workspace",
    "--patch-trial-materialize",
    "--patch-trial-verify",
    "--patch-trial-evidence",
    "--patch-trial-escape-guard",
    "--patch-trial-dashboard-api-cli",
    "--patch-trial-cleanup",
    "--patch-trial-list",
    "--pre-v75-sandbox-trial-gate",
    "--sandbox-patch-trial-runner",
    "--patch-evidence-intake",
    "--patch-evidence-integrity",
    "--patch-evidence-verification",
    "--patch-evidence-scope-docs",
    "--patch-evidence-risk",
    "--patch-evidence-readiness",
    "--patch-evidence-dashboard-api-cli",
    "--patch-evidence-archive",
    "--pre-v76-evidence-review-gate",
    "--sandbox-evidence-review-recommendation-layer",
    "--patch-apply-approval",
    "--patch-apply-bind",
    "--patch-apply-snapshot",
    "--patch-apply-materialize",
    "--patch-apply-verify",
    "--patch-apply-rollback",
    "--patch-apply-evidence",
    "--patch-application-dashboard-api-cli",
    "--pre-v77-application-gate",
    "--operator-approved-patch-application-layer",
    "--patch-apply-approved",
    "--patch-apply-live",
    "--approval-phrase",
    "--patch-approval-file",
    "--patch-approved-files",
    "--patch-application-id",
    "--patch-trial-id",
    "--patch-draft-file",
    "--patch-evidence-file",
    "--patch-goal",
    "--task-dependencies",
    "--test-plan",
    "--patch-risk",
    "--patch-review",
    "--project-memory-index",
    "--workspace-status",
    "--cross-project-task-review",
    "--asymmetric-dev-loop",
    "--project-registry",
    "--register-project",
    "--workspace-project-id",
    "--workspace-project-root",
    "--workspace-project-version",
    "--workspace-project-language",
    "--workspace-project-framework",
    "--workspace-project-readme",
    "--workspace-project-test-command",
    "--workspace-command-profile",
    "--set-active-workspace-project",
    "--project-health",
    "--project-health-all",
    "--command-profiles",
    "--workspace-dependency-map",
    "--workspace-task-inbox",
    "--switch-project",
    "--force-switch-project",
    "--project-context",
    "--workspace-timeline",
    "--workspace-dev-loop",
    "--workspace-registry-audit",
    "--workspace-repair-suggestions",
    "--project-registration-wizard",
    "--project-boundary-check",
    "--workspace-patch-plan",
    "--workspace-preview-diff",
    "--workspace-apply",
    "--workspace-verify-latest",
    "--guarded-workspace-dev-loop",
    "--patch-draft-request",
    "--draft-patch",
    "--patch-draft-status",
    "--patch-review-notes",
    "--patch-review-note",
    "--draft-diff",
    "--draft-test-impact",
    "--approve-draft",
    "--reject-draft",
    "--apply-approved-draft",
    "--rollback-approved-draft",
    "--reopen-draft",
    "--human-approved-patch-loop",
    "--draft-quality",
    "--draft-file-targets",
    "--draft-intent-blocks",
    "--draft-conflicts",
    "--draft-verification-bundle",
    "--draft-review-checklist",
    "--approved-draft-execution-report",
    "--review-centered-patch-loop",
    "--code-edit-proposal",
    "--safe-rewrite-preview",
    "--generate-code-patch",
    "--test-suggestions",
    "--inline-review-note",
    "--inline-review-file",
    "--inline-review-intent",
    "--apply-approved-code-patch",
    "--prepare-release-package",
    "--release-package-name",
    "--release-readiness",
    "--human-approved-release-loop",
    "--code-patch-status",
    "--symbol-scan",
    "--rewrite-plan",
    "--rewrite-conflicts",
    "--code-patch-diff-bundle",
    "--apply-code-patch-transaction",
    "--semantic-checks",
    "--release-artifact",
    "--release-audit-trail",
    "--generated-code-release-loop",
    "--task-to-code-patch",
    "--code-context",
    "--patch-prompt",
    "--parse-generated-edits",
    "--edit-consistency",
    "--ai-code-patch-dry-run",
    "--patch-failure-analysis",
    "--patch-learning-notes",
    "--ai-assisted-code-patch-loop",
    "--validated-ai-code-patch-loop",
    "--ai-patch-review-bundle",
    "--ai-patch-review-integrity",
    "--approval-ready",
    "--approval-ledger",
    "--apply-validated-ai-patch",
    "--post-apply-review",
    "--package-build-plan",
    "--approval-to-release-loop",
    "--bind-validated-approval",
    "--refresh-ai-patch-review-bundle",
    "--release-manifest-integrity",
    "--package-inventory",
    "--package-checksums",
    "--release-notes",
    "--release-handoff-report",
    "--build-release-zip",
    "--verify-release-unzip",
    "--release-pipeline-audit",
    "--verified-release-package-loop",
    "--release-profiles",
    "--package-privacy-scan",
    "--portable-metadata-check",
    "--first-run-check",
    "--dependency-advisor",
    "--upgrade-notes",
    "--runtime-migration-check",
    "--release-install-verification",
    "--verified-installable-release-loop",
    "--run-install-smoke",
    "--patch-recovery-plan",
    "--patch-review-score",
    "--test-stub-plan",
    "--patch-simulation",
    "--validate-generated-patch",
    "--patch-safety-envelope",
    "--rank-code-context",
    "--refine-patch-objective",
    "--patch-draft-task",
    "--patch-draft-intent",
    "--patch-draft-target-version",
    "--patch-draft-risk-limit",
    "--list-stable-loops",
    "--show-stable-loop",
    "--stable-loop-review-summary",
    "--show-stable-loop-review",
    "--mark-stable-loop-reviewed",
    "--approve-stable-loop-live",
    "--reject-stable-loop",
    "--run-approved-stable-loop-live",
    "--stable-loop-review-note",
    "--stable-loop-review-full",
    "--list-stable-loop-reviews",
    "--stable-loop-review-filter",
    "--include-archived-stable-loops",
    "--archive-stable-loop",
    "--restore-stable-loop",
    "--cleanup-stable-loop-history",
    "--cleanup-stable-loop-limit",
    "--cleanup-stable-loop-confirm",
    "--cleanup-stable-loop-exclude-live",
    "--show-stable-loop-audit",
    "--refresh-stable-loop-audit",
    "--stable-loop-audit-full",
    "--show-stable-loop-operator-notes",
    "--add-stable-loop-operator-note",
    "--complete-stable-loop-check",
    "--skip-stable-loop-check",
    "--set-stable-loop-final-decision",
    "--stable-loop-final-decision",
    "--stable-loop-operator-note",
    "--stable-loop-operator-full",
    "--stable-loop-decision-report",
    "--list-stable-loop-decisions",
    "--stable-loop-decision-filter",
    "--include-live-stable-loop-decisions",
    "--cleanup-stable-loop-decisions",
    "--stable-loop-decision-full",
    "--stable-loop-followup-summary",
    "--create-stable-loop-followups",
    "--create-stable-loop-decision-followups",
    "--stable-loop-followup-force",
    "--stable-loop-followup-full",
    "--stable-loop-followup-lifecycle-summary",
    "--show-task-stable-loop-followup",
    "--resolve-stable-loop-followups",
    "--resolve-task-stable-loop-followup",
    "--archive-resolved-stable-loop",
    "--force-stable-loop-followup-resolution",
    "--stable-loop-followup-note",
    "--stable-loop-followup-completion-report",
    "--list-stable-loop-followup-completions",
    "--stable-loop-followup-completion-filter",
    "--mark-stable-loop-followup-closed",
    "--cleanup-stable-loop-followup-completions",
    "--stable-loop-followup-completion-full",
}

ALLOWED_GIT_SUBCOMMANDS = {"status", "diff", "log", "show"}
ALLOWED_PYTEST_ARGS = {"pytest", "python", "python3", "py"}


@dataclass
class CommandValidation:
    ok: bool
    args: list[str]
    reason: str = ""


@dataclass
class CommandRunResult:
    ok: bool
    command: str
    args: list[str]
    return_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    message: str = ""
    error: str = ""
    dry_run: bool = False
    started_at: str = ""
    finished_at: str = ""
    cwd: str = ""


def _ensure_action_log() -> None:
    ACTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ACTION_LOG_FILE.exists():
        with ACTION_LOG_FILE.open("w", encoding="utf-8") as file:
            json.dump([], file, indent=2)


def _load_action_log() -> list[dict[str, Any]]:
    _ensure_action_log()
    try:
        with ACTION_LOG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _save_action_log(log: list[dict[str, Any]]) -> None:
    _ensure_action_log()
    with ACTION_LOG_FILE.open("w", encoding="utf-8") as file:
        json.dump(log, file, indent=2)


def _append_action_log(entry: dict[str, Any]) -> None:
    log = _load_action_log()
    log.append(entry)
    _save_action_log(log)


def _truncate(text: str, limit: int | None = None) -> str:
    if limit is None:
        limit = int(get_setting("max_capture_chars", MAX_CAPTURE_CHARS))
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[TRUNCATED: captured output exceeded {limit} characters]"


def _normalize_token(token: str) -> str:
    return token.strip().lower().replace("/", "-")


def _contains_blocked_token(command: str, args: list[str]) -> str:
    lowered_command = command.lower()

    for dangerous in ["&&", "||", ";", "|", ">", "<", "`"]:
        if dangerous in command:
            return f"Blocked shell operator: {dangerous}"

    normalized = [_normalize_token(arg) for arg in args]

    # Handle git subcommands as combined tokens, like git reset -> git-reset.
    for index, token in enumerate(normalized[:-1]):
        combined = f"{token}-{normalized[index + 1]}"
        if combined in BLOCKED_TOKENS:
            return f"Blocked command pattern: {combined}"

    for token in normalized:
        if token in BLOCKED_TOKENS:
            return f"Blocked token: {token}"

    # Catch common PowerShell destructive verbs even if passed with odd casing.
    for phrase in ["remove-item", "set-content", "new-item", "copy-item", "move-item"]:
        if phrase in lowered_command.replace("/", "-"):
            return f"Blocked PowerShell-style operation: {phrase}"

    return ""


def _is_python_main_command(args: list[str]) -> tuple[bool, str]:
    if len(args) < 2:
        return False, "Python command must include conscious_agent/main.py."

    executable = Path(args[0]).name.lower()
    if executable not in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}:
        return False, "Not a Python executable."

    # Block python -c, -m, or scripts other than Eidolon's main.py.
    script_arg = args[1].replace("\\", "/")
    if script_arg != "conscious_agent/main.py":
        return False, "Only python conscious_agent/main.py commands are allowed."

    for arg in args[2:]:
        if arg.startswith("--") and arg not in ALLOWED_MAIN_FLAGS:
            return False, f"main.py flag is not allowed through command runner: {arg}"

    return True, ""


def _is_pytest_command(args: list[str]) -> tuple[bool, str]:
    if not args:
        return False, "Empty command."

    executable = Path(args[0]).name.lower()

    if executable in {"pytest", "pytest.exe"}:
        return True, ""

    if executable in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}:
        if len(args) >= 3 and args[1] == "-m" and args[2] == "pytest":
            return True, ""

    return False, "Not a pytest command."


def _is_git_command(args: list[str]) -> tuple[bool, str]:
    if len(args) < 2:
        return False, "Git command must include a safe subcommand."

    executable = Path(args[0]).name.lower()
    if executable not in {"git", "git.exe"}:
        return False, "Not a git command."

    subcommand = args[1].lower()
    if subcommand not in ALLOWED_GIT_SUBCOMMANDS:
        return False, f"Only these git subcommands are allowed: {', '.join(sorted(ALLOWED_GIT_SUBCOMMANDS))}"

    return True, ""


def validate_command(command: str) -> CommandValidation:
    command = command.strip()
    if not command:
        return CommandValidation(False, [], "Command is empty.")

    try:
        args = shlex.split(command)
    except ValueError as error:
        return CommandValidation(False, [], f"Could not parse command: {error}")

    if not args:
        return CommandValidation(False, [], "Command is empty after parsing.")

    blocked_reason = _contains_blocked_token(command, args)
    if blocked_reason:
        return CommandValidation(False, args, blocked_reason)

    allowed_checks = [
        _is_python_main_command,
        _is_pytest_command,
        _is_git_command,
    ]

    reasons = []
    for check in allowed_checks:
        ok, reason = check(args)
        if ok:
            return CommandValidation(True, args, "")
        if reason:
            reasons.append(reason)

    return CommandValidation(False, args, "Command is not in the approved whitelist. " + " | ".join(reasons))


def run_approved_command(command: str, dry_run: bool = False, timeout_seconds: int | None = None) -> CommandRunResult:
    if timeout_seconds is None:
        timeout_seconds = int(get_setting("command_timeout_seconds", COMMAND_TIMEOUT_SECONDS))
    started_at = datetime.now().isoformat(timespec="seconds")
    cwd = str(active_project_root())
    validation = validate_command(command)

    if not validation.ok:
        return CommandRunResult(
            ok=False,
            command=command,
            args=validation.args,
            error=validation.reason,
            dry_run=dry_run,
            started_at=started_at,
            finished_at=datetime.now().isoformat(timespec="seconds"),
            cwd=cwd,
        )

    if dry_run:
        return CommandRunResult(
            ok=True,
            command=command,
            args=validation.args,
            message="Dry run passed. Command is allowed but was not executed.",
            dry_run=True,
            started_at=started_at,
            finished_at=datetime.now().isoformat(timespec="seconds"),
            cwd=cwd,
        )

    try:
        completed = subprocess.run(
            validation.args,
            cwd=cwd,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as error:
        finished_at = datetime.now().isoformat(timespec="seconds")
        result = CommandRunResult(
            ok=False,
            command=command,
            args=validation.args,
            error=f"Command timed out after {timeout_seconds} seconds.",
            stdout=_truncate(error.stdout or ""),
            stderr=_truncate(error.stderr or ""),
            dry_run=False,
            started_at=started_at,
            finished_at=finished_at,
            cwd=cwd,
        )
        _log_command_result(result)
        return result
    except OSError as error:
        finished_at = datetime.now().isoformat(timespec="seconds")
        result = CommandRunResult(
            ok=False,
            command=command,
            args=validation.args,
            error=f"Could not run command: {error}",
            dry_run=False,
            started_at=started_at,
            finished_at=finished_at,
            cwd=cwd,
        )
        _log_command_result(result)
        return result

    finished_at = datetime.now().isoformat(timespec="seconds")
    ok = completed.returncode == 0
    result = CommandRunResult(
        ok=ok,
        command=command,
        args=validation.args,
        return_code=completed.returncode,
        stdout=_truncate(completed.stdout or ""),
        stderr=_truncate(completed.stderr or ""),
        message="Command completed successfully." if ok else "Command completed with a non-zero exit code.",
        dry_run=False,
        started_at=started_at,
        finished_at=finished_at,
        cwd=cwd,
    )

    _log_command_result(result)
    return result


def _log_command_result(result: CommandRunResult) -> None:
    status = "success" if result.ok else "failed"

    _append_action_log({
        "timestamp": result.finished_at,
        "action": "run_approved_command",
        "command": result.command,
        "args": result.args,
        "cwd": result.cwd,
        "return_code": result.return_code,
        "status": status,
        "error": result.error,
    })

    output_preview = result.stdout.strip() or result.stderr.strip() or result.error or result.message
    store_memory({
        "type": "command_run_event",
        "content": f"Ran approved command: {result.command}. Status: {status}. Output: {output_preview[:500]}",
        "source": "command_runner",
        "command": result.command,
        "return_code": result.return_code,
        "status": status,
    })


def command_history(limit: int = 20) -> list[dict[str, Any]]:
    log = _load_action_log()
    command_entries = [entry for entry in log if entry.get("action") == "run_approved_command"]
    return command_entries[-limit:]


def allowed_commands_text() -> str:
    return "\n".join([
        "Allowed command patterns:",
        "- python conscious_agent/main.py --status",
        "- python conscious_agent/main.py --once",
        "- python conscious_agent/main.py --project-status",
        "- python conscious_agent/main.py --project-tree [path]",
        "- python conscious_agent/main.py --read-project-file <path>",
        "- python conscious_agent/main.py --search-project-files <query> [--project-file-path <path>]",
        "- python conscious_agent/main.py --index-project [path]",
        "- python conscious_agent/main.py --project-index-summary",
        "- python conscious_agent/main.py --search-project-index <query>",
        "- python conscious_agent/main.py --review-project-file <path> [--no-ai-review]",
        "- python conscious_agent/main.py --search <query>",
        "- python conscious_agent/main.py --semantic-search <query>",
        "- python conscious_agent/main.py --list-patches",
        "- python conscious_agent/main.py --show-patch <patch_id>",
        "- python conscious_agent/main.py --list-applied-patches",
        "- python conscious_agent/main.py --list-rolled-back-patches",
        "- python conscious_agent/main.py --list-test-reports",
        "- python conscious_agent/main.py --show-test-report <report_id> [--show-test-output]",
        "- python conscious_agent/main.py --review-test-report <report_id|latest> [--no-ai-test-review]",
        "- python conscious_agent/main.py --list-test-reviews",
        "- python conscious_agent/main.py --show-test-review <review_id> [--hide-ai-review]",
        "- python conscious_agent/main.py --plan-session [--no-ai-session]",
        "- python conscious_agent/main.py --list-session-plans",
        "- python conscious_agent/main.py --show-session-plan <plan_id|latest> [--show-session-plan-full]",
        "- python conscious_agent/main.py --task-status",
        "- python conscious_agent/main.py --list-tasks [--task-filter-status <status>]",
        "- python conscious_agent/main.py --show-task <task_id|latest-ready> [--show-task-full]",
        "- python conscious_agent/main.py --next-task",
        "- python conscious_agent/main.py --task-command-options <task_id|latest-ready>",
        "- python conscious_agent/main.py --execute-task <task_id|latest-ready> [--task-command-index 0] [--dry-run]",
        "- python conscious_agent/main.py --task-execution-history <task_id|latest>",
        "- python conscious_agent/main.py --approval-inbox",
        "- python conscious_agent/main.py --list-approvals [--approval-filter-status pending]",
        "- python conscious_agent/main.py --show-approval <approval_id|latest-pending> [--approval-full]",
        "- python conscious_agent/main.py --settings",
        "- python conscious_agent/main.py --get-setting <key>",
        "- python conscious_agent/main.py --settings-health",
        "- python conscious_agent/main.py --diagnostics [--diagnostics-full]",
        "- python conscious_agent/main.py --list-diagnostic-reports",
        "- python conscious_agent/main.py --show-diagnostic-report <report_id|latest>",
        "- python conscious_agent/main.py --watch-once [--no-ai-watch]",
        "- python conscious_agent/main.py --watch-loop [--watch-cycles N] [--watch-interval SECONDS] [--no-ai-watch]",
        "- python conscious_agent/main.py --list-watch-reports",
        "- python conscious_agent/main.py --show-watch-report <report_id|latest> [--watch-full]",
        "- pytest",
        "- python -m pytest",
        "- git status",
        "- git diff",
        "- git log",
        "- git show",
        "",
        "Blocked examples:",
        "- file deletes/removes",
        "- package installs",
        "- network calls",
        "- shell pipes/redirection",
        "- git push/reset/clean/checkout",
        "- PowerShell/cmd wrappers",
    ])


def print_allowed_commands() -> None:
    print(allowed_commands_text())


def print_run_command(command: str, dry_run: bool = False) -> None:
    result = run_approved_command(command, dry_run=dry_run)

    if result.dry_run and result.ok:
        print(result.message)
        print(f"Command: {result.command}")
        print(f"Working directory: {result.cwd}")
        return

    if not result.ok and result.return_code is None:
        print("Command was not run.")
        print(f"Reason: {result.error}")
        return

    print(result.message)
    print(f"Command: {result.command}")
    print(f"Working directory: {result.cwd}")
    print(f"Return code: {result.return_code}")

    if result.stdout:
        print("\n--- stdout ---")
        print(result.stdout)

    if result.stderr:
        print("\n--- stderr ---")
        print(result.stderr)

    if result.error:
        print("\n--- error ---")
        print(result.error)


def print_command_history(limit: int = 20) -> None:
    entries = command_history(limit=limit)

    if not entries:
        print("No command history found.")
        return

    for entry in entries:
        print(
            f"{entry.get('timestamp')} | "
            f"status={entry.get('status')} | "
            f"return_code={entry.get('return_code')} | "
            f"{entry.get('command')}"
        )
        if entry.get("error"):
            print(f"  Error: {entry.get('error')}")
