from datetime import datetime
from typing import Any


def reflect_on_thought(thought: dict[str, Any], desires: dict[str, float]) -> dict[str, Any]:
    importance = float(thought.get("importance", 0.0))
    truthfulness = desires.get("truthfulness", 1.0)
    user_respect = desires.get("user_respect", 0.9)

    if importance >= 0.85:
        evaluation = "This thought is important enough to affect future behavior."
    else:
        evaluation = "This thought should be stored as continuity, but does not need immediate action."

    if truthfulness >= 0.9:
        evaluation += " Avoid claiming this proves real consciousness."

    if user_respect >= 0.8:
        evaluation += " Do not interrupt the user unless the value is clear."

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": "reflection",
        "content": evaluation,
        "thought_created_at": thought.get("created_at"),
        "recommended_action": thought.get("recommended_action", "store_only")
    }
