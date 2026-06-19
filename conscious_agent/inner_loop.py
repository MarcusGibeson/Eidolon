import time
from typing import Any

from actions import perform_action
from brain import generate_inner_thought
from desires import load_desires
from memory import load_memories, store_memory
from planner import choose_action
from project_manager import get_active_project
from goal_manager import list_goals
from task_queue import list_tasks
from reflection import reflect_on_thought
from safety import is_action_allowed
from self_model import load_self_model, update_focus


def run_cycle(verbose: bool = True) -> dict[str, Any]:
    self_model = load_self_model()
    desires = load_desires()
    memories = load_memories(limit=12)
    current_state = dict(self_model.get("current_state", {}))
    active_project = get_active_project()
    if active_project:
        current_state["active_project"] = {
            "name": active_project.get("name"),
            "language": active_project.get("language"),
            "next_steps": active_project.get("next_steps", [])[:3],
            "known_issues": active_project.get("known_issues", [])[:3],
        }

    open_goals = [goal for goal in list_goals(include_cancelled=False) if goal.get("status") in {"planned", "active", "blocked", "paused"}]
    current_state["structured_goals"] = [
        {
            "id": goal.get("id"),
            "title": goal.get("title"),
            "status": goal.get("status"),
            "priority": goal.get("priority"),
            "next_actions": goal.get("next_actions", [])[:2],
        }
        for goal in open_goals[:5]
    ]

    open_tasks = [task for task in list_tasks(include_cancelled=False) if task.get("status") in {"planned", "active", "blocked", "paused"}]
    current_state["task_queue"] = [
        {
            "id": task.get("id"),
            "title": task.get("title"),
            "status": task.get("status"),
            "priority": task.get("priority"),
            "command": task.get("command"),
            "next_actions": task.get("next_actions", [])[:2],
        }
        for task in open_tasks[:5]
    ]

    thought = generate_inner_thought(self_model, desires, memories, current_state)
    reflection = reflect_on_thought(thought, desires)
    action = choose_action(thought, reflection)

    if not is_action_allowed(action):
        action = {"name": "store_only", "reason": "Blocked by safety policy."}

    result = perform_action(action, thought)

    store_memory(thought)
    store_memory(reflection)
    store_memory({
        "type": "action_result",
        "content": f"Action {action['name']} completed with result: {result['result']}",
        "action": action,
        "result": result
    })

    update_focus(0.005)

    if verbose:
        print(f"\n[INNER THOUGHT]\n{thought['content']}")
        print(f"\n[REFLECTION]\n{reflection['content']}")
        print(f"\n[ACTION]\n{action['name']} - {action['reason']}")

    return {"thought": thought, "reflection": reflection, "action": action, "result": result}


def run_loop(delay_seconds: int = 10) -> None:
    print("Eidolon inner loop running. Press Ctrl+C to stop.")
    while True:
        run_cycle(verbose=True)
        time.sleep(delay_seconds)
