from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from brain import generate_inner_thought
from chat import build_chat_prompt, build_chat_state, create_chat_response
from chat_action_router import propose_chat_action
from desires import load_desires
from memory import load_memories, store_memory
from paths import DATA_DIR
from reflection import reflect_on_thought
from self_model import load_self_model, update_focus
from local_brain import local_generate_stream
from settings_manager import get_setting


DASHBOARD_CHAT_DIR = DATA_DIR / "dashboard_chat"
DASHBOARD_CHAT_README = DASHBOARD_CHAT_DIR / "README.md"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 44) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return (cleaned or "dashboard-chat")[:max_length].strip("-") or "dashboard-chat"


def _ensure_storage() -> None:
    DASHBOARD_CHAT_DIR.mkdir(parents=True, exist_ok=True)
    if not DASHBOARD_CHAT_README.exists():
        DASHBOARD_CHAT_README.write_text(
            "Saved Dashboard Chat Console turns. Each turn contains Marcus's message, Eidolon's response, and any proposed safe action.\n",
            encoding="utf-8",
        )


def _new_turn_id(message: str) -> str:
    return f"dash_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(message, 32)}"


def _turn_path(turn_id: str) -> Path:
    _ensure_storage()
    return DASHBOARD_CHAT_DIR / f"{turn_id}.json"


def save_dashboard_chat_turn(turn: dict[str, Any]) -> None:
    _ensure_storage()
    with _turn_path(turn["id"]).open("w", encoding="utf-8") as file:
        json.dump(turn, file, indent=2)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_dashboard_chat_turns() -> list[dict[str, Any]]:
    _ensure_storage()
    turns: list[dict[str, Any]] = []
    for path in DASHBOARD_CHAT_DIR.glob("*.json"):
        data = _load_json_file(path)
        if data:
            turns.append(data)
    return sorted(turns, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_dashboard_chat_turn_id(turn_id: str) -> str:
    token = (turn_id or "").strip()
    lowered = token.lower()
    turns = list_dashboard_chat_turns()
    if lowered in {"latest", "last"}:
        return turns[0].get("id", "") if turns else ""
    return token


def load_dashboard_chat_turn(turn_id: str) -> dict[str, Any] | None:
    resolved = resolve_dashboard_chat_turn_id(turn_id)
    if not resolved:
        return None
    path = _turn_path(resolved)
    if path.exists():
        return _load_json_file(path)
    for turn in list_dashboard_chat_turns():
        if turn.get("id") == resolved:
            return turn
    return None


def _fallback_response(user_message: str, action: dict[str, Any] | None) -> str:
    if action:
        return (
            "Eidolon: I mapped that to a proposed safe action. "
            f"Intent: {action.get('intent')}. "
            f"Next: inspect the action card and dry-run it before executing."
        )
    return (
        "Eidolon: I saved your message, but I did not generate a local AI response. "
        "The dashboard still created a safe action proposal if the request matched a known workflow."
    )


def create_dashboard_chat_turn(user_message: str, use_ai: bool = True) -> dict[str, Any]:
    """
    Creates a dashboard chat turn with:
    - saved user message
    - conversational response
    - chat-to-action proposal
    - lightweight reflection memory

    This does not execute actions. The dashboard presents action controls separately.
    """
    message = (user_message or "").strip()
    turn_id = _new_turn_id(message or "empty")
    created_at = _now()

    if not message:
        turn = {
            "id": turn_id,
            "type": "dashboard_chat_turn",
            "created_at": created_at,
            "user_message": "",
            "eidolon_response": "Eidolon: I need an actual message before I can help. Revolutionary, I know.",
            "action_id": "",
            "action": None,
            "error": "Empty message.",
        }
        save_dashboard_chat_turn(turn)
        return turn

    store_memory({
        "type": "conversation_user",
        "content": message,
        "source": "dashboard_chat_console",
        "dashboard_chat_turn_id": turn_id,
    })

    action: dict[str, Any] | None = None
    try:
        action = propose_chat_action(message, save=True)
    except Exception as error:
        action = {
            "id": "",
            "status": "failed",
            "intent": "action_proposal_failed",
            "summary": f"Could not propose a safe action: {error}",
            "error": str(error),
        }

    response = ""
    response_error = ""
    if use_ai:
        try:
            self_model = load_self_model()
            desires = load_desires()
            memories = load_memories(limit=12)
            response = create_chat_response(message, self_model, desires, memories)
        except Exception as error:
            response_error = str(error)
            response = _fallback_response(message, action)
    else:
        response = _fallback_response(message, action)

    store_memory({
        "type": "conversation_eidolon",
        "content": response,
        "source": "dashboard_chat_console",
        "dashboard_chat_turn_id": turn_id,
        "chat_action_id": action.get("id", "") if action else "",
    })

    try:
        self_model = load_self_model()
        desires = load_desires()
        memories = load_memories(limit=12)
        current_state = build_chat_state(message)
        current_state["mode"] = "dashboard_chat"
        current_state["chat_action_id"] = action.get("id", "") if action else ""
        thought = generate_inner_thought(
            self_model=self_model,
            desires=desires,
            memories=memories,
            current_state=current_state,
            brain_mode="local_logic",
        )
        reflection = reflect_on_thought(thought, desires)
        store_memory(thought)
        store_memory(reflection)
        update_focus(0.01)
    except Exception as error:
        response_error = response_error or f"Reflection failed: {error}"

    turn = {
        "id": turn_id,
        "type": "dashboard_chat_turn",
        "created_at": created_at,
        "user_message": message,
        "eidolon_response": response,
        "action_id": action.get("id", "") if action else "",
        "action": action,
        "use_ai": use_ai,
        "error": response_error,
    }
    save_dashboard_chat_turn(turn)
    return turn



def _save_post_response_side_effects(
    turn_id: str,
    message: str,
    response: str,
    action: dict[str, Any] | None,
) -> str:
    """Runs slower memory/reflection bookkeeping after the visible answer exists."""
    response_error = ""
    try:
        store_memory({
            "type": "conversation_eidolon",
            "content": response,
            "source": "dashboard_chat_console",
            "dashboard_chat_turn_id": turn_id,
            "chat_action_id": action.get("id", "") if action else "",
        })
    except Exception as error:
        response_error = f"Response memory save failed: {error}"

    try:
        self_model = load_self_model()
        desires = load_desires()
        memories = load_memories(limit=12)
        current_state = build_chat_state(message)
        current_state["mode"] = "dashboard_chat"
        current_state["chat_action_id"] = action.get("id", "") if action else ""
        thought = generate_inner_thought(
            self_model=self_model,
            desires=desires,
            memories=memories,
            current_state=current_state,
            brain_mode="local_logic",
        )
        reflection = reflect_on_thought(thought, desires)
        store_memory(thought)
        store_memory(reflection)
        update_focus(0.01)
    except Exception as error:
        response_error = response_error or f"Reflection failed: {error}"
    return response_error


def _build_streaming_response(message: str, use_ai: bool) -> tuple[str, list[str]]:
    """Returns a response prefix and generator chunks as a concrete list fallback for simple callers."""
    if not use_ai:
        return "", [_fallback_response(message, None)]
    if not bool(get_setting("ai_chat_enabled", True)):
        name = load_self_model().get("name", "Eidolon")
        return "", [f"{name}: Local AI chat is disabled in settings. I saved your message, but I am not generating a model response."]
    self_model = load_self_model()
    desires = load_desires()
    memories = load_memories(limit=12)
    prompt = build_chat_prompt(message, self_model, desires, memories)
    return f"{self_model.get('name', 'Eidolon')}: ", list(local_generate_stream(prompt=prompt, temperature=0.45, max_tokens=350))


def stream_dashboard_chat_turn(user_message: str, use_ai: bool = True):
    """
    Streams a dashboard chat turn as event dictionaries.

    The visible response is emitted before slower action/reflection bookkeeping so the
    dashboard feels like a conversation instead of a court filing process with buttons.
    This still does not execute actions or grant autonomy.
    """
    message = (user_message or "").strip()
    turn_id = _new_turn_id(message or "empty")
    created_at = _now()
    started_at = datetime.now()

    yield {"event": "meta", "turn_id": turn_id, "created_at": created_at, "use_ai": bool(use_ai)}

    if not message:
        turn = {
            "id": turn_id,
            "type": "dashboard_chat_turn",
            "created_at": created_at,
            "user_message": "",
            "eidolon_response": "Eidolon: I need an actual message before I can help. Revolutionary, I know.",
            "action_id": "",
            "action": None,
            "use_ai": use_ai,
            "error": "Empty message.",
            "latency": {"mode": "stream", "error": "empty_message"},
        }
        save_dashboard_chat_turn(turn)
        yield {"event": "delta", "text": turn["eidolon_response"]}
        yield {"event": "done", "turn": turn}
        return

    try:
        store_memory({
            "type": "conversation_user",
            "content": message,
            "source": "dashboard_chat_console_stream",
            "dashboard_chat_turn_id": turn_id,
        })
        yield {"event": "status", "stage": "user_saved", "message": "User message saved."}
    except Exception as error:
        yield {"event": "status", "stage": "user_memory_failed", "message": str(error)}

    response_error = ""
    response_parts: list[str] = []
    first_token_at: datetime | None = None

    if use_ai and bool(get_setting("ai_chat_enabled", True)):
        try:
            self_model = load_self_model()
            desires = load_desires()
            memories = load_memories(limit=12)
            prompt = build_chat_prompt(message, self_model, desires, memories)
            prefix = f"{self_model.get('name', 'Eidolon')}: "
            response_parts.append(prefix)
            yield {"event": "delta", "text": prefix}
            for chunk in local_generate_stream(prompt=prompt, temperature=0.45, max_tokens=350):
                if first_token_at is None:
                    first_token_at = datetime.now()
                    yield {
                        "event": "status",
                        "stage": "first_token",
                        "latency_ms": int((first_token_at - started_at).total_seconds() * 1000),
                    }
                response_parts.append(chunk)
                yield {"event": "delta", "text": chunk}
        except Exception as error:
            response_error = str(error)
            fallback = _fallback_response(message, None)
            response_parts = [fallback]
            yield {"event": "delta", "text": fallback}
    else:
        fallback = _fallback_response(message, None)
        response_parts = [fallback]
        yield {"event": "delta", "text": fallback}

    response = "".join(response_parts).strip()
    finished_response_at = datetime.now()
    yield {
        "event": "response_complete",
        "latency_ms": int((finished_response_at - started_at).total_seconds() * 1000),
    }

    action: dict[str, Any] | None = None
    try:
        yield {"event": "status", "stage": "action_proposal", "message": "Preparing safe action card."}
        action = propose_chat_action(message, save=True)
        if action.get("intent") != "small_talk":
            yield {"event": "action", "action": action}
        else:
            yield {"event": "status", "stage": "conversation_only", "message": "No project action was needed for this message."}
    except Exception as error:
        action = {
            "id": "",
            "status": "failed",
            "intent": "action_proposal_failed",
            "summary": f"Could not propose a safe action: {error}",
            "error": str(error),
        }
        yield {"event": "action", "action": action}

    side_effect_error = _save_post_response_side_effects(turn_id, message, response, action)
    response_error = response_error or side_effect_error
    completed_at = datetime.now()
    latency = {
        "mode": "stream",
        "first_token_ms": int((first_token_at - started_at).total_seconds() * 1000) if first_token_at else None,
        "response_complete_ms": int((finished_response_at - started_at).total_seconds() * 1000),
        "total_ms": int((completed_at - started_at).total_seconds() * 1000),
    }
    turn = {
        "id": turn_id,
        "type": "dashboard_chat_turn",
        "created_at": created_at,
        "user_message": message,
        "eidolon_response": response,
        "action_id": action.get("id", "") if action else "",
        "action": action,
        "use_ai": use_ai,
        "error": response_error,
        "latency": latency,
        "streaming": True,
    }
    save_dashboard_chat_turn(turn)
    yield {"event": "saved", "turn_id": turn_id, "latency": latency}
    yield {"event": "done", "turn": turn}

def dashboard_chat_turn_text(turn: dict[str, Any] | None, full: bool = False) -> str:
    if not turn:
        return "Dashboard chat turn not found."

    action = turn.get("action") or {}
    lines = [
        f"# Dashboard Chat Turn: {turn.get('id')}",
        f"Created: {turn.get('created_at')}",
        f"Use AI: {turn.get('use_ai')}",
        "",
        "## Marcus",
        str(turn.get("user_message", "")),
        "",
        "## Eidolon",
        str(turn.get("eidolon_response", "")),
    ]

    if action:
        lines.extend([
            "",
            "## Proposed Action",
            f"Action ID: {turn.get('action_id')}",
            f"Status: {action.get('status')}",
            f"Intent: {action.get('intent')}",
            f"Mode: {action.get('execution_mode')}",
            f"Risk: {action.get('risk_level')}",
            f"Summary: {action.get('summary')}",
            f"Command: {action.get('command') or action.get('approval_command') or '[none]'}",
        ])

    if turn.get("error"):
        lines.extend(["", "## Error", str(turn.get("error"))])

    if full:
        lines.extend(["", "## Raw turn", json.dumps(turn, indent=2, default=str)])

    return "\n".join(lines)
