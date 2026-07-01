from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from approval_manager import create_approval
from command_runner import run_approved_command, validate_command
from memory import store_memory
from patch_suggester import suggest_patch
from paths import DATA_DIR


CHAT_ACTIONS_DIR = DATA_DIR / "chat_actions"
CHAT_ACTIONS_README = CHAT_ACTIONS_DIR / "README.md"

DIRECT_COMMAND = "direct_command"
DIRECT_FUNCTION = "direct_function"
APPROVAL = "approval"
BLOCKED = "blocked"
INFO = "info"

SMALL_TALK_ONLY_PATTERNS = (
    r"^(hi|hello|hey|yo|howdy)[!. ]*$",
    r"^(good morning|good afternoon|good evening|good night)[!. ]*$",
    r"^(thanks|thank you|cool|nice|awesome|sweet)[!. ]*$",
)


def _is_small_talk_only(request: str) -> bool:
    lowered = request.strip().lower()
    if not lowered:
        return False
    return any(re.fullmatch(pattern, lowered) for pattern in SMALL_TALK_ONLY_PATTERNS)


def _quote_cli_value(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

SELF_DEVELOPMENT_REQUEST_MARKERS = (
    "self development cycle",
    "self-development cycle",
    "begin self development",
    "begin work on a self development cycle",
    "begin work on a self-development cycle",
    "controlled self-development loop",
    "what should you improve next",
    "plan your own next development step",
    "identify what needs to be improved next",
    "improve yourself next",
    "own next development step",
    "start improving yourself",
    "figure out what you should work on next",
    "begin your own development loop",
    "review your project and make a task",
    "look at your failed actions and plan the next fix",
    "failed actions and plan",
)





def _is_self_development_patch_application_approval_request(request: str) -> bool:
    return bool(re.fullmatch(r"Approve applying self-development patch draft [A-Za-z0-9_.:-]+", request.strip()))

def _self_development_patch_application_command(request: str) -> str:
    safe_phrase = request.strip().replace('"', '\"')
    return f'python conscious_agent/main.py --self-development-patch-application "{safe_phrase}" --self-development-full'

def _is_self_development_patch_draft_approval_request(request: str) -> bool:
    return bool(re.fullmatch(r"Approve drafting a patch proposal for self-development task [A-Za-z0-9_.:-]+", request.strip()))

def _self_development_patch_draft_command(request: str) -> str:
    safe_phrase = request.strip().replace('"', '\"')
    return f'python conscious_agent/main.py --self-development-patch-draft "{safe_phrase}" --self-development-full'

def _is_self_development_cycle_request(lowered: str) -> bool:
    compact = lowered.replace("-", " ")
    if any(marker in lowered or marker.replace("-", " ") in compact for marker in SELF_DEVELOPMENT_REQUEST_MARKERS):
        return True
    if "self" in compact and "development" in compact and any(term in compact for term in ["cycle", "loop", "next", "plan", "improve"]):
        return True
    if "own project" in compact and any(term in compact for term in ["inspect", "improve", "next development", "development step"]):
        return True
    return False


@dataclass
class ChatActionExecutionResult:
    ok: bool
    chat_action_id: str
    message: str = ""
    status: str = ""
    result: dict[str, Any] | None = None
    error: str = ""
    dry_run: bool = False


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 56) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return (cleaned or "chat-action")[:max_length].strip("-") or "chat-action"


def _ensure_storage() -> None:
    CHAT_ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not CHAT_ACTIONS_README.exists():
        CHAT_ACTIONS_README.write_text(
            "Saved chat-to-action proposals. These translate plain-English requests into safe commands, patch suggestions, or approval requests.\n",
            encoding="utf-8",
        )


def _new_chat_action_id(intent: str) -> str:
    return f"chat_action_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(intent, 36)}"


def _chat_action_path(chat_action_id: str) -> Path:
    _ensure_storage()
    return CHAT_ACTIONS_DIR / f"{chat_action_id}.json"


def save_chat_action(action: dict[str, Any]) -> None:
    _ensure_storage()
    with _chat_action_path(action["id"]).open("w", encoding="utf-8") as file:
        json.dump(action, file, indent=2)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_chat_actions(status: str = "", include_closed: bool = True) -> list[dict[str, Any]]:
    _ensure_storage()
    actions: list[dict[str, Any]] = []
    for path in CHAT_ACTIONS_DIR.glob("*.json"):
        data = _load_json_file(path)
        if not data:
            continue
        if status and data.get("status") != status:
            continue
        if not include_closed and data.get("status") not in {"proposed", "approval_required"}:
            continue
        actions.append(data)
    return sorted(actions, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_chat_action_id(chat_action_id: str) -> str:
    token = (chat_action_id or "").strip()
    lowered = token.lower()
    actions = list_chat_actions(include_closed=True)

    if lowered in {"latest", "last"}:
        return actions[0].get("id", "") if actions else ""

    alias_status = {
        "latest-proposed": "proposed",
        "last-proposed": "proposed",
        "latest-executed": "executed",
        "last-executed": "executed",
        "latest-approved": "approval_created",
        "last-approved": "approval_created",
        "latest-approval": "approval_created",
        "last-approval": "approval_created",
        "latest-blocked": "blocked",
        "last-blocked": "blocked",
        "latest-failed": "failed",
        "last-failed": "failed",
    }

    if lowered in alias_status:
        matches = [item for item in actions if item.get("status") == alias_status[lowered]]
        return matches[0].get("id", "") if matches else ""

    if lowered.startswith("latest-"):
        desired_intent = lowered.replace("latest-", "", 1).replace("-", "_")
        matches = [item for item in actions if item.get("intent") == desired_intent]
        return matches[0].get("id", "") if matches else ""

    return token


def load_chat_action(chat_action_id: str) -> dict[str, Any] | None:
    resolved = resolve_chat_action_id(chat_action_id)
    if not resolved:
        return None
    path = _chat_action_path(resolved)
    if path.exists():
        return _load_json_file(path)
    for action in list_chat_actions(include_closed=True):
        if action.get("id") == resolved:
            return action
    return None


def _normalize_request(user_request: str) -> str:
    return re.sub(r"\s+", " ", user_request.strip())


def _looks_like_path(value: str) -> bool:
    return bool(re.search(r"\.(py|json|md|txt|js|ts|java|kt|cs|php|html|css|gd)\b", value, re.IGNORECASE))


def _normalize_project_path(path_text: str) -> str:
    path_text = path_text.strip().strip('"\'`.,')
    path_text = path_text.replace("\\", "/")
    if not path_text:
        return ""
    if "/" not in path_text and _looks_like_path(path_text):
        return f"conscious_agent/{path_text}"
    return path_text


def _extract_file_path(text: str) -> str:
    # Prefer explicit paths first.
    match = re.search(r"([\w./\\-]+\.(?:py|json|md|txt|js|ts|java|kt|cs|php|html|css|gd))", text, re.IGNORECASE)
    if match:
        return _normalize_project_path(match.group(1))
    return ""


def _make_action(
    user_request: str,
    intent: str,
    title: str,
    summary: str,
    execution_mode: str,
    risk_level: str = "low",
    command: str = "",
    function_name: str = "",
    function_args: dict[str, Any] | None = None,
    approval_action_type: str = "",
    approval_object_id: str = "",
    approval_command: str = "",
    blocked_reason: str = "",
    explanation: str = "",
    source: str = "chat_action_router",
) -> dict[str, Any]:
    action = {
        "id": _new_chat_action_id(intent),
        "type": "chat_action",
        "created_at": _now(),
        "updated_at": _now(),
        "status": "proposed" if execution_mode not in {BLOCKED, INFO} else execution_mode,
        "user_request": user_request,
        "intent": intent,
        "title": title,
        "summary": summary,
        "explanation": explanation or summary,
        "execution_mode": execution_mode,
        "risk_level": risk_level,
        "command": command,
        "function_name": function_name,
        "function_args": function_args or {},
        "approval_action_type": approval_action_type,
        "approval_object_id": approval_object_id,
        "approval_command": approval_command,
        "blocked_reason": blocked_reason,
        "source": source,
        "result": {},
        "approval_id": "",
        "useful_commands": [],
    }
    action["useful_commands"] = _chat_action_commands(action)
    return action


def _chat_action_commands(action: dict[str, Any]) -> list[str]:
    action_id = action.get("id", "latest")
    commands = [
        f"python conscious_agent/main.py --show-chat-action {action_id}",
    ]
    if action.get("execution_mode") in {DIRECT_COMMAND, DIRECT_FUNCTION, APPROVAL}:
        commands.extend([
            f"python conscious_agent/main.py --execute-chat-action {action_id} --dry-run",
            f"python conscious_agent/main.py --execute-chat-action {action_id}",
        ])
    return commands


def _direct_command(user_request: str, intent: str, title: str, summary: str, command: str, risk: str = "low") -> dict[str, Any]:
    validation = validate_command(command)
    if not validation.ok:
        return _make_action(
            user_request=user_request,
            intent=intent,
            title=title,
            summary=f"The matched command was blocked by command safety: {validation.reason}",
            execution_mode=BLOCKED,
            risk_level="medium",
            command=command,
            blocked_reason=validation.reason,
        )
    return _make_action(
        user_request=user_request,
        intent=intent,
        title=title,
        summary=summary,
        execution_mode=DIRECT_COMMAND,
        risk_level=risk,
        command=command,
        explanation="This maps to an approved read-only or low-risk command.",
    )


def propose_chat_action(user_request: str, save: bool = True) -> dict[str, Any]:
    request = _normalize_request(user_request)
    lowered = request.lower()

    if not request:
        action = _make_action(
            user_request=user_request,
            intent="empty_request",
            title="Empty request",
            summary="No request was provided.",
            execution_mode=BLOCKED,
            risk_level="low",
            blocked_reason="Empty request.",
        )
        if save:
            save_chat_action(action)
        return action

    if _is_small_talk_only(request):
        action = _make_action(
            user_request=request,
            intent="small_talk",
            title="Conversation only",
            summary="This message is conversational and does not request a project action.",
            execution_mode=INFO,
            risk_level="low",
            explanation="No command, approval, patch, release, memory mutation, or autonomy action is needed for this greeting.",
        )
    # Narrow self-development patch application approval. This prepares a preimage/application receipt only; it does not publish, release, or expand autonomy.
    elif _is_self_development_patch_application_approval_request(request):
        action = _direct_command(
            request,
            "operator_approved_self_development_patch_application_trial",
            "Prepare Self Development patch application trial receipt",
            "Validate the exact patch application approval phrase, capture preimage hashes, enforce the low-risk file allowlist, and stop when no concrete diff exists.",
            _self_development_patch_application_command(request),
            risk="low",
        )
    # Narrow self-development patch draft approval. This prepares a review packet only; it does not apply a patch.
    elif _is_self_development_patch_draft_approval_request(request):
        action = _direct_command(
            request,
            "operator_approved_self_development_patch_draft",
            "Prepare Self Development patch draft packet",
            "Prepare a review-only patch draft packet for the explicitly named low-risk Self Development task; no source edits are applied.",
            _self_development_patch_draft_command(request),
            risk="low",
        )
    # Approval-gated writes.
    elif re.search(r"\b(apply|approve|install)\b.*\bpatch\b", lowered) or re.search(r"\bapply\b.*\blatest\b", lowered):
        action = _make_action(
            user_request=request,
            intent="request_apply_patch",
            title="Request approval to apply latest proposed patch",
            summary="Applying a patch writes to a project file, so this becomes an approval request.",
            execution_mode=APPROVAL,
            risk_level="medium",
            approval_action_type="apply_patch",
            approval_object_id="latest-proposed",
            approval_command="python conscious_agent/main.py --apply-patch latest-proposed",
            explanation="File edits require approval. Executing this chat action creates an approval inbox item; it does not apply the patch directly.",
        )
    elif re.search(r"\b(rollback|undo|revert)\b.*\b(patch|latest|change)\b", lowered):
        action = _make_action(
            user_request=request,
            intent="request_rollback_patch",
            title="Request approval to rollback latest applied patch",
            summary="Rolling back writes to a project file, so this becomes an approval request.",
            execution_mode=APPROVAL,
            risk_level="medium",
            approval_action_type="rollback_patch",
            approval_object_id="latest-applied",
            approval_command="python conscious_agent/main.py --rollback-patch latest-applied",
            explanation="Rollback changes files and requires explicit approval.",
        )
    elif "apply task evaluation" in lowered or "apply evaluation" in lowered:
        action = _make_action(
            user_request=request,
            intent="request_apply_task_evaluation",
            title="Request approval to apply latest task evaluation",
            summary="Applying a task evaluation may change task status, so this becomes an approval request.",
            execution_mode=APPROVAL,
            risk_level="low",
            approval_action_type="apply_task_evaluation",
            approval_object_id="latest",
            approval_command="python conscious_agent/main.py --apply-task-evaluation latest",
            explanation="Task status changes are routed through the approval system from chat actions.",
        )
    elif _is_self_development_cycle_request(lowered):
        action = _direct_command(
            request,
            "self_development_cycle",
            "Begin Self Development Cycle",
            "Run a dedicated proposal-only self-development cycle that inspects, ranks at least three candidates, creates one safe work item, defines verification, and stops before source edits.",
            "python conscious_agent/main.py --self-development-cycle --self-development-create-task --no-ai-self-development --self-development-prompt " + _quote_cli_value(request),
            risk="low",
        )
    elif "compact memory" in lowered or "compress memory" in lowered:
        action = _make_action(
            user_request=request,
            intent="manual_memory_compaction",
            title="Memory compaction requires manual command",
            summary="Memory compaction archives and rewrites memory files. Use the existing dry-run/explicit command flow.",
            execution_mode=BLOCKED,
            risk_level="medium",
            blocked_reason="Chat-to-action does not execute memory compaction yet. Run --compact-memory --dry-run first.",
            explanation="This is blocked from chat actions because it rewrites memory files.",
        )
    # Patch suggestion: safe proposal creation, no file edit.
    elif any(term in lowered for term in ["suggest patch", "suggest improvement", "improve ", "fix ", "patch "]):
        target_file = _extract_file_path(request)
        if target_file:
            patch_request = request
            action = _make_action(
                user_request=request,
                intent="suggest_patch",
                title=f"Suggest patch for {target_file}",
                summary="Create a saved patch proposal using the local model. This does not edit files.",
                execution_mode=DIRECT_FUNCTION,
                risk_level="low",
                function_name="suggest_patch",
                function_args={"target_file": target_file, "request": patch_request},
                explanation="Patch suggestions create proposal JSON and a diff only. Applying still requires approval.",
            )
        else:
            action = _make_action(
                user_request=request,
                intent="suggest_patch_missing_file",
                title="Patch suggestion needs a file path",
                summary="I understood this as a patch/improvement request, but no target file was found.",
                execution_mode=BLOCKED,
                risk_level="low",
                blocked_reason="No target file path found. Try: suggest improvement for conscious_agent/memory.py ...",
            )
    # Read-only / safe commands.
    elif "diagnostic" in lowered or "system health" in lowered or "health check" in lowered:
        action = _direct_command(request, "run_diagnostics", "Run diagnostics", "Run a diagnostics report.", "python conscious_agent/main.py --diagnostics")
    elif "settings health" in lowered or "ollama" in lowered or "model health" in lowered:
        action = _direct_command(request, "settings_health", "Check settings/model health", "Check configured settings and Ollama model availability.", "python conscious_agent/main.py --settings-health")
    elif "watch" in lowered or "needs attention" in lowered or "check attention" in lowered or "anything wrong" in lowered:
        action = _direct_command(request, "watch_once", "Run watch check", "Run a no-AI watch check and save a watch report.", "python conscious_agent/main.py --watch-once --no-ai-watch")
    elif "approval" in lowered or "permission" in lowered:
        action = _direct_command(request, "approval_inbox", "Show approval inbox", "Show pending approval requests.", "python conscious_agent/main.py --approval-inbox")
    elif "notification" in lowered or "alert" in lowered:
        action = _direct_command(request, "notifications", "Show notifications", "Show unread notifications.", "python conscious_agent/main.py --notifications")
    elif "plan" in lowered or "what next" in lowered or "next step" in lowered or "next session" in lowered:
        action = _direct_command(request, "plan_session", "Plan next session", "Create a no-AI session plan.", "python conscious_agent/main.py --plan-session --no-ai-session")
    elif "maintenance" in lowered or "scan" in lowered:
        action = _direct_command(request, "maintenance_scan", "Run maintenance scan", "Create a no-AI maintenance scan.", "python conscious_agent/main.py --maintenance-scan --no-ai-maintenance")
    elif "dev loop" in lowered or "autonomous" in lowered or "continue development" in lowered:
        action = _direct_command(request, "dev_loop_dry_run", "Dry-run dev loop", "Run a safe no-AI dev-loop dry run.", "python conscious_agent/main.py --dev-loop --dry-run --no-ai-dev-loop")
    elif "task status" in lowered or "tasks" in lowered and "next" not in lowered:
        action = _direct_command(request, "task_status", "Show task status", "Show task queue status.", "python conscious_agent/main.py --task-status")
    elif "next task" in lowered or "current task" in lowered:
        action = _direct_command(request, "next_task", "Show next task", "Show the highest-priority ready task.", "python conscious_agent/main.py --next-task")
    elif "latest patch" in lowered or "show patch" in lowered:
        action = _direct_command(request, "show_latest_patch", "Show latest patch", "Show the latest patch proposal.", "python conscious_agent/main.py --show-patch latest")
    elif "latest ids" in lowered or "ids" in lowered:
        action = _direct_command(request, "latest_ids", "Show latest IDs", "Show latest alias targets.", "python conscious_agent/main.py --latest-ids")
    elif "review" in lowered and _extract_file_path(request):
        target_file = _extract_file_path(request)
        action = _direct_command(
            request,
            "review_file",
            f"Review {target_file}",
            f"Run a static code review for {target_file}.",
            f"python conscious_agent/main.py --review-project-file {target_file} --no-ai-review",
        )
    elif "project status" in lowered or "active project" in lowered:
        action = _direct_command(request, "project_status", "Show project status", "Show active project status.", "python conscious_agent/main.py --project-status")
    elif "memory status" in lowered:
        action = _direct_command(request, "memory_status", "Show memory status", "Show memory size and compaction status.", "python conscious_agent/main.py --memory-status")
    elif "dashboard" in lowered:
        action = _make_action(
            user_request=request,
            intent="start_dashboard_manual",
            title="Start dashboard manually",
            summary="The dashboard is a long-running server. Start it manually from the terminal.",
            execution_mode=INFO,
            risk_level="low",
            command="python conscious_agent/main.py --dashboard",
            explanation="Chat-to-action does not start long-running servers. Run the command manually.",
        )
    else:
        action = _make_action(
            user_request=request,
            intent="unknown_request",
            title="No safe action matched",
            summary="I could not map this request to a known safe Eidolon action.",
            execution_mode=BLOCKED,
            risk_level="unknown",
            blocked_reason="Unknown or unsupported chat action request.",
            explanation="Try phrasing it as: run diagnostics, check approvals, plan session, run watch, review conscious_agent/memory.py, or suggest improvement for conscious_agent/memory.py.",
        )

    if save:
        save_chat_action(action)
        store_memory({
            "type": "chat_action_proposed",
            "content": f"Created chat action {action['id']} for request: {request}. Intent: {action.get('intent')}. Mode: {action.get('execution_mode')}.",
            "source": "chat_action_router",
            "chat_action_id": action["id"],
            "intent": action.get("intent"),
            "execution_mode": action.get("execution_mode"),
        })
    return action


def execute_chat_action(chat_action_id: str = "latest", dry_run: bool = False) -> ChatActionExecutionResult:
    action = load_chat_action(chat_action_id)
    if not action:
        return ChatActionExecutionResult(False, chat_action_id, error=f"Chat action not found: {chat_action_id}", dry_run=dry_run)

    action_id = action.get("id", chat_action_id)
    mode = action.get("execution_mode")

    if action.get("status") not in {"proposed", "approval_required", "blocked", "info", "failed"} and not dry_run:
        return ChatActionExecutionResult(False, action_id, error=f"Chat action status is {action.get('status')}, not executable.", dry_run=dry_run)

    if mode == BLOCKED:
        return ChatActionExecutionResult(False, action_id, error=action.get("blocked_reason") or "This action is blocked.", dry_run=dry_run)

    if mode == INFO:
        return ChatActionExecutionResult(True, action_id, message=action.get("explanation", action.get("summary", "Informational action.")), status="info", result={"command": action.get("command")}, dry_run=dry_run)

    if mode == DIRECT_COMMAND:
        result = run_approved_command(action.get("command", ""), dry_run=dry_run)
        result_data = dict(result.__dict__)
        if dry_run:
            action["updated_at"] = _now()
            action["last_dry_run_result"] = result_data
            save_chat_action(action)
            return ChatActionExecutionResult(bool(result.ok), action_id, message=result.message or result.error, status=action.get("status", "proposed"), result=result_data, dry_run=True)
        action["updated_at"] = _now()
        action["status"] = "executed" if result.ok else "failed"
        action["result"] = result_data
        save_chat_action(action)
        _store_execution_memory(action, result_data)
        return ChatActionExecutionResult(bool(result.ok), action_id, message=result.message or result.error, status=action["status"], result=result_data, dry_run=False)

    if mode == DIRECT_FUNCTION:
        function_name = action.get("function_name")
        args = action.get("function_args", {}) or {}
        if function_name != "suggest_patch":
            return ChatActionExecutionResult(False, action_id, error=f"Unsupported chat action function: {function_name}", dry_run=dry_run)
        if dry_run:
            result_data = {
                "ok": True,
                "message": "Dry run passed. Patch suggestion would be generated using the local model, but no proposal was created.",
                "target_file": args.get("target_file"),
                "request": args.get("request"),
            }
            action["updated_at"] = _now()
            action["last_dry_run_result"] = result_data
            save_chat_action(action)
            return ChatActionExecutionResult(True, action_id, message=result_data["message"], status=action.get("status", "proposed"), result=result_data, dry_run=True)
        result = suggest_patch(args.get("target_file", ""), args.get("request", action.get("user_request", "")), use_ai=True)
        result_data = dict(result.__dict__)
        action["updated_at"] = _now()
        action["status"] = "executed" if result.ok else "failed"
        action["result"] = result_data
        save_chat_action(action)
        _store_execution_memory(action, result_data)
        return ChatActionExecutionResult(bool(result.ok), action_id, message=("Patch proposal created." if result.ok else result.error), status=action["status"], result=result_data, dry_run=False)

    if mode == APPROVAL:
        if dry_run:
            result_data = {
                "ok": True,
                "message": "Dry run passed. Executing this chat action would create an approval inbox item, not perform the action directly.",
                "approval_action_type": action.get("approval_action_type"),
                "approval_object_id": action.get("approval_object_id"),
                "approval_command": action.get("approval_command"),
            }
            action["updated_at"] = _now()
            action["last_dry_run_result"] = result_data
            save_chat_action(action)
            return ChatActionExecutionResult(True, action_id, message=result_data["message"], status=action.get("status", "proposed"), result=result_data, dry_run=True)

        approval = create_approval(
            action_type=action.get("approval_action_type", ""),
            object_id=action.get("approval_object_id", ""),
            command=action.get("approval_command", ""),
            summary=action.get("summary", "Chat action requested approval."),
            risk_level=action.get("risk_level", "medium"),
            source="chat_action_router",
            reason=action.get("explanation", "Plain-English chat action requires approval."),
            metadata={"chat_action_id": action_id, "user_request": action.get("user_request")},
        )
        result_data = {"ok": True, "approval_id": approval.get("id"), "status": approval.get("status")}
        action["updated_at"] = _now()
        action["status"] = "approval_created"
        action["approval_id"] = approval.get("id", "")
        action["result"] = result_data
        save_chat_action(action)
        _store_execution_memory(action, result_data)
        return ChatActionExecutionResult(True, action_id, message=f"Approval request created: {approval.get('id')}", status=action["status"], result=result_data, dry_run=False)

    return ChatActionExecutionResult(False, action_id, error=f"Unsupported execution mode: {mode}", dry_run=dry_run)


def _store_execution_memory(action: dict[str, Any], result_data: dict[str, Any]) -> None:
    store_memory({
        "type": "chat_action_executed",
        "content": f"Executed chat action {action.get('id')} with status {action.get('status')}. Intent: {action.get('intent')}. Result: {result_data.get('message') or result_data.get('error') or result_data.get('approval_id') or result_data.get('patch_id') or result_data.get('ok')}",
        "source": "chat_action_router",
        "chat_action_id": action.get("id"),
        "intent": action.get("intent"),
        "status": action.get("status"),
    })


def chat_action_text(action: dict[str, Any] | None, full: bool = False) -> str:
    if not action:
        return "Chat action not found."

    lines = [
        f"# Chat Action: {action.get('id')}",
        f"Status: {action.get('status')}",
        f"Created: {action.get('created_at')}",
        f"Updated: {action.get('updated_at')}",
        f"Intent: {action.get('intent')}",
        f"Mode: {action.get('execution_mode')}",
        f"Risk: {action.get('risk_level')}",
        "",
        "## User request",
        action.get("user_request", ""),
        "",
        "## Summary",
        action.get("summary", ""),
    ]

    if action.get("explanation"):
        lines.extend(["", "## Explanation", action.get("explanation", "")])
    if action.get("command"):
        lines.extend(["", "## Command", action.get("command", "")])
    if action.get("function_name"):
        lines.extend(["", "## Function", f"{action.get('function_name')}({json.dumps(action.get('function_args', {}), indent=2)})"])
    if action.get("approval_action_type"):
        lines.extend([
            "",
            "## Approval request to create",
            f"Action type: {action.get('approval_action_type')}",
            f"Object id: {action.get('approval_object_id')}",
            f"Command: {action.get('approval_command')}",
        ])
    if action.get("blocked_reason"):
        lines.extend(["", "## Blocked reason", action.get("blocked_reason", "")])
    if action.get("approval_id"):
        lines.extend(["", "## Created approval", action.get("approval_id", "")])

    result = action.get("last_dry_run_result") or action.get("result")
    if result:
        lines.extend(["", "## Latest result", json.dumps(result, indent=2, default=str)])

    useful = action.get("useful_commands", []) or _chat_action_commands(action)
    if useful:
        lines.extend(["", "## Useful commands"])
        lines.extend(command for command in useful if command)

    if full:
        lines.extend(["", "## Raw chat action", json.dumps(action, indent=2, default=str)])

    return "\n".join(lines)


def print_chat_action(user_request: str) -> None:
    action = propose_chat_action(user_request, save=True)
    print(chat_action_text(action, full=False))
    print()
    if action.get("execution_mode") in {DIRECT_COMMAND, DIRECT_FUNCTION, APPROVAL}:
        print("Next commands:")
        print("  python conscious_agent/main.py --execute-chat-action latest --dry-run")
        print("  python conscious_agent/main.py --execute-chat-action latest")
    elif action.get("command"):
        print("Manual command:")
        print(f"  {action.get('command')}")


def print_execute_chat_action(chat_action_id: str = "latest", dry_run: bool = False) -> None:
    result = execute_chat_action(chat_action_id, dry_run=dry_run)
    if not result.ok:
        print("Chat action did not complete successfully.")
        print(f"Reason: {result.error or result.message}")
        return
    if dry_run:
        print("Chat action dry run passed.")
    else:
        print("Chat action executed.")
    print(f"Chat action: {result.chat_action_id}")
    print(f"Status: {result.status}")
    if result.message:
        print(f"Message: {result.message}")
    result_data = result.result or {}
    for key in ["approval_id", "patch_id", "target_file", "command", "return_code", "error"]:
        if result_data.get(key) not in {None, ""}:
            print(f"{key.replace('_', ' ').title()}: {result_data.get(key)}")


def print_chat_actions(status: str = "", include_closed: bool = True) -> None:
    actions = list_chat_actions(status=status, include_closed=include_closed)
    if not actions:
        print("No chat actions found.")
        return
    for action in actions:
        print(
            f"{action.get('id')} | status={action.get('status')} | "
            f"intent={action.get('intent')} | mode={action.get('execution_mode')} | risk={action.get('risk_level')}"
        )
        print(f"  Request: {action.get('user_request')}")
        if action.get("command"):
            print(f"  Command: {action.get('command')}")
        if action.get("approval_id"):
            print(f"  Approval: {action.get('approval_id')}")


def print_saved_chat_action(chat_action_id: str = "latest", full: bool = False) -> None:
    action = load_chat_action(chat_action_id)
    if not action:
        print(f"Chat action not found: {chat_action_id}")
        return
    print(chat_action_text(action, full=full))
