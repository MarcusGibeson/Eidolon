from __future__ import annotations

"""Lightweight terminal-chat launcher for v1251.4.

Unlike the legacy main CLI, this entry point imports only conversation modules
needed for the active chat path. Post-turn cognition is owned by ``conversation_runtime``; the launcher never
performs a second hidden provider call after the visible reply.
"""

import sys
from typing import Any

CONTRACT_VERSION = "v1251.4"
RUNTIME_REPAIR_VERSION = "v1253.9.1"



def run_chat() -> None:
    from conversation_sessions import (
        archive_conversation_session, create_conversation_session, get_active_conversation_session,
        list_conversation_sessions, rename_conversation_session, restore_conversation_session,
        search_conversation_sessions, select_conversation_session,
    )

    active_session = get_active_conversation_session(create_if_missing=True) or {}
    try:
        from bounded_internal_maintenance import resume_pending_internal_maintenance
        resume_pending_internal_maintenance()
    except Exception:
        pass
    print("Eidolon chat mode started.")
    print("Commands: /new [title], /sessions, /find <text>, /use <session-id>, /rename <title>, /archive, /restore <session-id>, /retry <turn-id>, /current, quit")
    print(f"Active conversation: {active_session.get('title', 'New conversation')} ({active_session.get('id', '')})\n")
    while True:
        user_message = input("Marcus: ").strip()
        if not user_message:
            continue
        lowered = user_message.lower()
        if lowered in {"quit", "exit", "q"}:
            print("Eidolon: Ending chat mode.")
            break
        if lowered.startswith("/new"):
            active_session = create_conversation_session(user_message[4:].strip(), source="terminal_chat")
            print(f"Eidolon: New conversation selected: {active_session.get('title')} ({active_session.get('id')})\n")
            continue
        if lowered == "/sessions":
            for session in list_conversation_sessions():
                marker = "*" if session.get("id") == active_session.get("id") else " "
                print(f"{marker} {session.get('id')} | {session.get('title')} | {session.get('turn_count', 0)} turns")
            print(); continue
        if lowered.startswith("/find "):
            for session in search_conversation_sessions(user_message[6:].strip(), include_archived=True):
                print(f"  {session.get('id')} | {session.get('status')} | {session.get('title')} | {session.get('match_snippet','')}")
            print(); continue
        if lowered.startswith("/use "):
            try:
                active_session = select_conversation_session(user_message[5:].strip())
                print(f"Eidolon: Conversation resumed: {active_session.get('title')}\n")
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue
        if lowered == "/current":
            active_session = get_active_conversation_session(create_if_missing=True) or {}
            print(f"Eidolon: Active conversation: {active_session.get('title')} ({active_session.get('id')})\n"); continue
        if lowered.startswith("/rename "):
            try:
                active_session = rename_conversation_session(str(active_session.get("id") or ""), user_message[8:].strip())
                print(f"Eidolon: Conversation renamed: {active_session.get('title')}\n")
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue
        if lowered == "/archive":
            try:
                archived = archive_conversation_session(str(active_session.get("id") or ""))
                print(f"Eidolon: Conversation archived: {archived.get('title')}\n")
                active_session = get_active_conversation_session(create_if_missing=True) or {}
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue
        if lowered.startswith("/restore "):
            try:
                restored = restore_conversation_session(user_message[9:].strip())
                print(f"Eidolon: Conversation restored: {restored.get('title')}\n")
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue
        if lowered.startswith("/retry "):
            try:
                from conversation_recovery import retry_failed_conversation_turn
                result = retry_failed_conversation_turn(
                    str(active_session.get("id") or ""), user_message[7:].strip(),
                    use_ai=True, source="terminal_chat_recovery",
                )
                print(f"\n{result.display_message}\n")
            except ValueError as error:
                print(f"Eidolon: {error}\n")
            continue

        from conversation_runtime import cancel_conversation_operation, stream_conversation_turn
        operation_id = ""
        final_result: dict[str, Any] | None = None
        stream = stream_conversation_turn(
            user_message, source="terminal_chat", use_ai=True,
            session_id=str(active_session.get("id") or ""),
        )
        print()
        try:
            for event in stream:
                event_type = event.get("event")
                if event_type == "meta": operation_id = str(event.get("operation_id") or "")
                elif event_type == "delta": print(str(event.get("text") or ""), end="", flush=True)
                elif event_type == "replace": print(f"\n{event.get('text', '')}", end="", flush=True)
                elif event_type == "error": print(f"\n[{event.get('failure_category', 'conversation_error')}] {event.get('message', '')}", end="", flush=True)
                elif event_type == "done": final_result = event.get("result") if isinstance(event.get("result"), dict) else None
        except KeyboardInterrupt:
            if operation_id: cancel_conversation_operation(operation_id)
            stream.close()
            print("\nEidolon: Conversation cancelled. Partial output was not committed to memory.")
            continue
        print("\n")


def main() -> int:
    run_chat()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
