from datetime import datetime
from typing import Any

from local_model import LocalModelConfig
from conversation_context import build_conversation_prompt
from conversation_runtime import cancel_conversation_operation, run_conversation_turn, stream_conversation_turn
from conversation_recovery import retry_failed_conversation_turn
from conversation_sessions import (
    archive_conversation_session,
    create_conversation_session,
    get_active_conversation_session,
    list_conversation_sessions,
    rename_conversation_session,
    restore_conversation_session,
    search_conversation_sessions,
    select_conversation_session,
)
from file_tools import project_tree_text
from memory import search_memories
from project_manager import project_context_text
from goal_manager import goal_context_text
from task_queue import task_context_text


def build_chat_state(user_message: str) -> dict[str, Any]:
    """
    Builds the state Eidolon sees during a chat message.
    """
    return {
        "mode": "chat",
        "user_message": True,
        "latest_user_message": user_message,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def get_related_memories(user_message: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Uses semantic memory first, then falls back to keyword memory.
    """
    try:
        from vector_memory import search_memory_vectors
        related = search_memory_vectors(user_message, limit=limit)
        if related:
            return related
    except Exception as error:
        print(f"Semantic memory unavailable, using keyword search: {error}")

    return search_memories(user_message, limit=limit)


def build_chat_prompt(
    user_message: str,
    self_model: dict[str, Any],
    desires: dict[str, float],
    memories: list[dict[str, Any]],
) -> str:
    """Builds the shared local-model prompt for terminal, dashboard, and streaming chat."""
    config = LocalModelConfig.from_settings()
    related_memories = get_related_memories(user_message, limit=8)
    combined = [*memories, *related_memories]
    packet = build_conversation_prompt(
        user_message=user_message,
        self_model=self_model,
        desires=desires,
        memories=combined,
        project_context=project_context_text(include_version_roles=False),
        goal_context=goal_context_text(),
        task_context=task_context_text(),
        context_size=config.context_size,
        max_tokens=config.generation.max_tokens,
    )
    return packet.prompt


def create_chat_response(
    user_message: str,
    self_model: dict[str, Any],
    desires: dict[str, float],
    memories: list[dict[str, Any]],
) -> str:
    """Compatibility wrapper over the authoritative non-stream conversation runtime."""
    _ = (self_model, desires, memories)
    result = run_conversation_turn(user_message, source="terminal_chat_compatibility", use_ai=True)
    return result.display_message

def run_chat() -> None:
    """
    Starts a simple terminal chat with Eidolon.
    Type 'quit', 'exit', or 'q' to stop.
    """
    active_session = get_active_conversation_session(create_if_missing=True) or {}
    print("Eidolon chat mode started.")
    print("Commands: /new [title], /sessions, /find <text>, /use <session-id>, /rename <title>, /archive, /restore <session-id>, /retry <turn-id>, /current, quit")
    print(f"Active conversation: {active_session.get('title', 'New conversation')} ({active_session.get('id', '')})\n")

    while True:
        user_message = input("Marcus: ").strip()

        if not user_message:
            continue

        if user_message.lower() in {"quit", "exit", "q"}:
            print("Eidolon: Ending chat mode.")
            break
        if user_message.lower().startswith("/new"):
            title = user_message[4:].strip()
            active_session = create_conversation_session(title, source="terminal_chat")
            print(f"Eidolon: New conversation selected: {active_session.get('title')} ({active_session.get('id')})\n")
            continue
        if user_message.lower() == "/sessions":
            sessions = list_conversation_sessions()
            for session in sessions:
                marker = "*" if session.get("id") == active_session.get("id") else " "
                print(f"{marker} {session.get('id')} | {session.get('title')} | {session.get('turn_count', 0)} turns")
            print()
            continue
        if user_message.lower().startswith("/find "):
            matches = search_conversation_sessions(user_message[6:].strip(), include_archived=True)
            for session in matches:
                print(f"  {session.get('id')} | {session.get('status')} | {session.get('title')} | {session.get('match_snippet','')}")
            print()
            continue
        if user_message.lower().startswith("/use "):
            try:
                active_session = select_conversation_session(user_message[5:].strip())
                print(f"Eidolon: Conversation resumed: {active_session.get('title')}\n")
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue
        if user_message.lower() == "/current":
            active_session = get_active_conversation_session(create_if_missing=True) or {}
            print(f"Eidolon: Active conversation: {active_session.get('title')} ({active_session.get('id')})\n")
            continue
        if user_message.lower().startswith("/rename "):
            try:
                active_session = rename_conversation_session(
                    str(active_session.get("id") or ""),
                    user_message[8:].strip(),
                )
                print(f"Eidolon: Conversation renamed: {active_session.get('title')}\n")
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue
        if user_message.lower() == "/archive":
            try:
                archived = archive_conversation_session(str(active_session.get("id") or ""))
                print(f"Eidolon: Conversation archived: {archived.get('title')}\n")
                active_session = get_active_conversation_session(create_if_missing=True) or {}
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue
        if user_message.lower().startswith("/restore "):
            try:
                restored = restore_conversation_session(user_message[9:].strip())
                print(f"Eidolon: Conversation restored: {restored.get('title')}\n")
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue
        if user_message.lower().startswith("/retry "):
            try:
                result = retry_failed_conversation_turn(
                    str(active_session.get("id") or ""),
                    user_message[7:].strip(),
                    use_ai=True,
                    source="terminal_chat_recovery",
                )
                print(f"\n{result.display_message}\n")
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue

        operation_id = ""
        final_result: dict[str, Any] | None = None
        stream = stream_conversation_turn(user_message, source="terminal_chat", use_ai=True, session_id=str(active_session.get("id") or ""))
        print()
        try:
            for event in stream:
                event_type = event.get("event")
                if event_type == "meta":
                    operation_id = str(event.get("operation_id") or "")
                elif event_type == "delta":
                    print(str(event.get("text") or ""), end="", flush=True)
                elif event_type == "replace":
                    print(f"\n{event.get('text', '')}", end="", flush=True)
                elif event_type == "error":
                    print(f"\n[{event.get('failure_category', 'conversation_error')}] {event.get('message', '')}", end="", flush=True)
                elif event_type == "done":
                    final_result = event.get("result") if isinstance(event.get("result"), dict) else None
        except KeyboardInterrupt:
            if operation_id:
                cancel_conversation_operation(operation_id)
            stream.close()
            print("\nEidolon: Conversation cancelled. Partial output was not committed to memory.")
            continue
        print("\n")

        if not final_result or not final_result.get("success"):
            continue
        # v1253.9.1: post-turn cognition is owned by conversation_runtime.
        # The legacy terminal compatibility path must not perform a second
        # synchronous local-model reflection after the visible reply.
