from typing import Any

from opinions import nudge_opinion


def perform_action(action: dict[str, Any], thought: dict[str, Any]) -> dict[str, Any]:
    name = action.get("name", "store_only")

    if name == "update_opinion":
        updated = nudge_opinion(
            "machine consciousness",
            "Autonomous thoughts should matter by changing future behavior, not merely being logged.",
            0.01
        )
        return {"action": name, "result": "opinion_updated", "opinion": updated}

    if name == "speak":
        return {"action": name, "result": "would_speak", "message": thought.get("content", "")}

    return {"action": name, "result": "stored_without_external_action"}
