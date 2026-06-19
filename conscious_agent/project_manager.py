from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR
from memory import load_json, save_json, store_memory


PROJECTS_FILE = DATA_DIR / "projects.json"


DEFAULT_PROJECTS = {
    "active_project": "Eidolon",
    "projects": [
        {
            "name": "Eidolon",
            "path": str(Path.cwd()),
            "description": "A local autonomous AI agent prototype with memory, inner thoughts, reflection, local AI, semantic search, and project awareness.",
            "language": "Python",
            "status": "active",
            "goals": [
                "Build persistent identity and memory",
                "Add semantic memory search",
                "Add project awareness",
                "Add safe read-only file tools",
                "Eventually support approved code edits and command execution"
            ],
            "known_issues": [
                "No file-reading tools yet",
                "No safe approved write/patch system yet",
                "No command execution yet",
                "Local model quality depends on the Ollama model installed"
            ],
            "next_steps": [
                "Test project awareness commands",
                "Add read-only project file tools",
                "Build a project indexer"
            ],
            "notes": [
                "Powerful actions should remain permission-gated and logged."
            ],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_worked_on": datetime.now().isoformat(timespec="seconds")
        }
    ]
}


def load_projects_data() -> dict[str, Any]:
    data = load_json(PROJECTS_FILE, DEFAULT_PROJECTS)
    if not isinstance(data, dict):
        data = DEFAULT_PROJECTS.copy()
    data.setdefault("active_project", "Eidolon")
    data.setdefault("projects", [])
    if not data["projects"]:
        data["projects"] = DEFAULT_PROJECTS["projects"]
    return data


def save_projects_data(data: dict[str, Any]) -> None:
    save_json(PROJECTS_FILE, data)


def list_projects() -> list[dict[str, Any]]:
    return load_projects_data().get("projects", [])


def get_project(name: str) -> dict[str, Any] | None:
    name_lower = name.lower().strip()
    for project in list_projects():
        if project.get("name", "").lower() == name_lower:
            return project
    return None


def get_active_project() -> dict[str, Any] | None:
    data = load_projects_data()
    active_name = data.get("active_project", "")
    return get_project(active_name)


def set_active_project(name: str) -> bool:
    data = load_projects_data()
    project = get_project(name)
    if not project:
        return False

    data["active_project"] = project["name"]
    project["last_worked_on"] = datetime.now().isoformat(timespec="seconds")
    save_projects_data(data)

    store_memory({
        "type": "project_event",
        "content": f"Active project changed to {project['name']}.",
        "source": "project_manager",
        "project": project["name"]
    })
    return True


def add_project(
    name: str,
    path: str = "",
    description: str = "",
    language: str = "Unknown"
) -> dict[str, Any]:
    data = load_projects_data()
    existing = get_project(name)
    if existing:
        return existing

    project = {
        "name": name,
        "path": path,
        "description": description,
        "language": language,
        "status": "active",
        "goals": [],
        "known_issues": [],
        "next_steps": [],
        "notes": [],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "last_worked_on": datetime.now().isoformat(timespec="seconds")
    }

    data["projects"].append(project)
    data["active_project"] = name
    save_projects_data(data)

    store_memory({
        "type": "project_event",
        "content": f"Project added and set active: {name}.",
        "source": "project_manager",
        "project": name
    })
    return project


def add_project_item(project_name: str, item_type: str, content: str) -> bool:
    """
    Adds a goal, known issue, next step, or note to a project.
    item_type must be: goals, known_issues, next_steps, or notes.
    """
    if item_type not in {"goals", "known_issues", "next_steps", "notes"}:
        return False

    data = load_projects_data()
    for project in data.get("projects", []):
        if project.get("name", "").lower() == project_name.lower().strip():
            project.setdefault(item_type, [])
            project[item_type].append(content)
            project["last_worked_on"] = datetime.now().isoformat(timespec="seconds")
            save_projects_data(data)

            store_memory({
                "type": "project_event",
                "content": f"Added {item_type[:-1].replace('_', ' ')} to {project['name']}: {content}",
                "source": "project_manager",
                "project": project["name"]
            })
            return True

    return False


def project_context_text(limit_items: int = 5) -> str:
    project = get_active_project()
    if not project:
        return "No active project is configured."

    def lines(label: str, values: list[str]) -> str:
        if not values:
            return f"{label}: none"
        clipped = values[:limit_items]
        joined = "\n".join(f"- {value}" for value in clipped)
        return f"{label}:\n{joined}"

    return "\n".join([
        f"Active project: {project.get('name', 'Unknown')}",
        f"Path: {project.get('path', '')}",
        f"Language: {project.get('language', 'Unknown')}",
        f"Description: {project.get('description', '')}",
        lines("Goals", project.get("goals", [])),
        lines("Known issues", project.get("known_issues", [])),
        lines("Next steps", project.get("next_steps", [])),
        lines("Notes", project.get("notes", [])),
    ])


def print_project_status() -> None:
    data = load_projects_data()
    active = data.get("active_project", "None")
    print(f"Active project: {active}")
    print("Projects:")
    for project in data.get("projects", []):
        marker = "*" if project.get("name") == active else "-"
        print(f"{marker} {project.get('name', 'Unknown')} [{project.get('language', 'Unknown')}] {project.get('status', '')}")
        print(f"  Path: {project.get('path', '')}")
        if project.get("description"):
            print(f"  Description: {project.get('description')}")
        if project.get("next_steps"):
            print("  Next steps:")
            for step in project.get("next_steps", [])[:5]:
                print(f"    - {step}")
