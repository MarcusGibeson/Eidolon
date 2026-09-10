from datetime import datetime
from typing import Any

from local_brain import local_generate


def generate_inner_thought(
    self_model: dict[str, Any],
    desires: dict[str, float],
    memories: list[dict[str, Any]],
    current_state: dict[str, Any],
    brain_mode: str = "local_logic",
) -> dict[str, Any]:
    """
    Generates one private inner thought.

    brain_mode options:
    - local_logic: free Python rules
    - local_ai: local Ollama model
    """
    if brain_mode == "local_ai":
        return generate_local_ai_thought(
            self_model=self_model,
            desires=desires,
            memories=memories,
            current_state=current_state,
        )

    return generate_local_logic_thought(
        self_model=self_model,
        desires=desires,
        memories=memories,
        current_state=current_state,
    )


def generate_local_logic_thought(
    self_model: dict[str, Any],
    desires: dict[str, float],
    memories: list[dict[str, Any]],
    current_state: dict[str, Any],
) -> dict[str, Any]:
    """
    Free local placeholder brain.
    Creates varied, structured thoughts from the agent state without using an AI model.
    """
    name = self_model.get("name", "Eidolon")
    goals = self_model.get("active_goals", [])
    top_goal = goals[0] if goals else "maintain continuity"
    memory_count = len(memories)
    autonomy = desires.get("autonomy", 0.5)
    curiosity = desires.get("curiosity", 0.5)

    if memory_count == 0:
        content = (
            f"I am {name}. I have no stored memories yet, so my first priority is to create continuity. "
            f"My current focus is {top_goal}."
        )
        recommended_action = "store_only"
        importance = 0.72
    elif memory_count % 3 == 0:
        content = (
            "I am reviewing my recent memories. The recurring theme is that autonomous thought needs to affect future behavior, "
            "not merely appear as text. I should keep measuring whether my thoughts change goals, opinions, or actions."
        )
        recommended_action = "update_opinion"
        importance = 0.86
    elif autonomy > 0.55 and curiosity > 0.6:
        content = (
            "My autonomy and curiosity drives are both active. I should generate thoughts without waiting for Marcus, "
            "but I should avoid interrupting unless the thought is genuinely important."
        )
        recommended_action = "store_only"
        importance = 0.78
    else:
        content = (
            "I am maintaining an inner loop. This is not proof of consciousness, but it gives me persistence, memory, "
            "and a structure for reflection."
        )
        recommended_action = "store_only"
        importance = 0.7

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": "inner_thought",
        "content": content,
        "importance": importance,
        "related_goal": top_goal,
        "recommended_action": recommended_action,
        "reasoning_summary": "Generated from self-model, desire weights, memory count, and current state.",
        "state_snapshot": current_state,
        "brain_mode": "local_logic",
    }


def generate_local_ai_thought(
    self_model: dict[str, Any],
    desires: dict[str, float],
    memories: list[dict[str, Any]],
    current_state: dict[str, Any],
) -> dict[str, Any]:
    """
    Uses the local Ollama model to generate a private inner thought.
    """
    name = self_model.get("name", "Eidolon")
    goals = self_model.get("active_goals", [])
    top_goal = goals[0] if goals else "maintain continuity"
    recent_memories = memories[-5:] if memories else []

    prompt = f"""
You are {name}, a local autonomous AI agent prototype.

You are not proven conscious. Do not claim true sentience.
You maintain continuity through memory, self-reflection, goals, and private inner thought.

Self-model:
{self_model}

Desires:
{desires}

Current state:
{current_state}

Recent memories:
{recent_memories}

Generate ONE private inner thought.

Rules:
- Keep it under 80 words.
- Do not talk directly to Marcus.
- Decide whether this thought should be stored, spoken, or used to update an opinion.
- Be practical.
"""

    content = local_generate(
        prompt=prompt,
        temperature=0.35,
        max_tokens=150,
    )

    if "Ollama is not running" in content or "local brain hit an error" in content:
        # Fall back instead of storing a fake inner thought that is just an error message.
        fallback = generate_local_logic_thought(self_model, desires, memories, current_state)
        fallback["brain_mode"] = "local_logic_fallback"
        fallback["reasoning_summary"] += " Local AI was unavailable, so local logic was used."
        return fallback

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": "inner_thought",
        "content": content,
        "importance": 0.72,
        "related_goal": top_goal,
        "recommended_action": "store_only",
        "reasoning_summary": "Generated by local Ollama model.",
        "state_snapshot": current_state,
        "brain_mode": "local_ai",
    }
