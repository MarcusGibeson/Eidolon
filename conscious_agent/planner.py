from typing import Any


def choose_action(thought: dict[str, Any], reflection: dict[str, Any]) -> dict[str, Any]:
    recommended = thought.get("recommended_action", "store_only")
    importance = float(thought.get("importance", 0.0))

    if recommended == "speak" and importance >= 0.9:
        return {"name": "speak", "reason": "Thought is high importance and explicitly recommended speech."}

    if recommended == "update_opinion":
        return {"name": "update_opinion", "reason": "Thought suggests a belief/opinion should be strengthened."}

    if recommended == "create_goal":
        return {"name": "create_goal", "reason": "Thought suggests a new goal is needed."}

    return {"name": "store_only", "reason": "Private continuity is enough for this cycle."}
