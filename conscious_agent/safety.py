from typing import Any

ALLOWED_ACTIONS = {"store_only", "update_opinion", "create_goal", "speak"}


def is_action_allowed(action: dict[str, Any]) -> bool:
    return action.get("name") in ALLOWED_ACTIONS
