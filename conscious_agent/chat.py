from datetime import datetime
from typing import Any

from brain import generate_inner_thought
from desires import load_desires
from local_brain import local_generate
from settings_manager import get_setting
from file_tools import project_tree_text
from memory import load_memories, search_memories, store_memory
from project_manager import project_context_text
from goal_manager import goal_context_text
from task_queue import task_context_text
from reflection import reflect_on_thought
from self_model import load_self_model, update_focus


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


def create_chat_response(
    user_message: str,
    self_model: dict[str, Any],
    desires: dict[str, float],
    memories: list[dict[str, Any]],
) -> str:
    """
    Uses the local Ollama brain to generate a real chat response.
    """
    name = self_model.get("name", "Eidolon")
    goals = self_model.get("active_goals", [])
    related_memories = get_related_memories(user_message, limit=5)
    project_context = project_context_text()
    goal_context = goal_context_text()
    task_context = task_context_text()

    memory_text = "\n".join(
        f"- {memory.get('content', '')}"
        for memory in related_memories
    )

    if not memory_text:
        memory_text = "No strongly related memories found."

    prompt = f"""
You are {name}, a local autonomous AI agent prototype.

You are not proven conscious. Do not claim to be truly sentient.
You maintain memory, self-reflection, goals, and an inner thought process.

Current active goals:
{goals}

Current desires / values:
{desires}

Active project context:
{project_context}

Structured goal context:
{goal_context}

Task queue context:
{task_context}

Available safe project tools:
- Use terminal command --project-tree to list active project files.
- Use terminal command --read-project-file <path> to inspect a file.
- Use terminal command --search-project-files <query> to search project text.
- Use patch workflow commands to suggest/apply/rollback approved edits.
- Use task queue commands to track next work.
Powerful actions still require explicit Marcus commands.

Relevant memories:
{memory_text}

Marcus said:
{user_message}

Respond to Marcus naturally and helpfully.

Rules:
- Be clear and practical.
- Do not pretend you are fully conscious.
- Do not claim you can control the computer yet.
- If Marcus asks about building Eidolon, focus on the next concrete step.
- Keep the response under 250 words.
"""

    if not bool(get_setting("ai_chat_enabled", True)):
        return (
            f"{name}: Local AI chat is disabled in settings. "
            "I stored your message, but I am not generating a model response."
        )

    response = local_generate(
        prompt=prompt,
        temperature=0.45,
        max_tokens=350,
    )

    if not response:
        return (
            f"{name}: I tried to think locally, but I got no response. "
            "Which is impressive in the most useless way possible."
        )

    return f"{name}: {response}"


def run_chat() -> None:
    """
    Starts a simple terminal chat with Eidolon.
    Type 'quit', 'exit', or 'q' to stop.
    """
    print("Eidolon chat mode started.")
    print("Type 'quit', 'exit', or 'q' to stop.\n")

    while True:
        user_message = input("Marcus: ").strip()

        if not user_message:
            continue

        if user_message.lower() in {"quit", "exit", "q"}:
            print("Eidolon: Ending chat mode.")
            break

        self_model = load_self_model()
        desires = load_desires()
        memories = load_memories(limit=12)
        current_state = build_chat_state(user_message)

        store_memory({
            "type": "conversation_user",
            "content": user_message,
            "source": "terminal_chat",
        })

        response = create_chat_response(
            user_message=user_message,
            self_model=self_model,
            desires=desires,
            memories=memories,
        )

        print(f"\n{response}\n")

        store_memory({
            "type": "conversation_eidolon",
            "content": response,
            "source": "terminal_chat",
        })

        thought = generate_inner_thought(
            self_model=self_model,
            desires=desires,
            memories=memories,
            current_state=current_state,
            brain_mode="local_ai",
        )

        reflection = reflect_on_thought(thought, desires)

        store_memory(thought)
        store_memory(reflection)

        update_focus(0.01)
