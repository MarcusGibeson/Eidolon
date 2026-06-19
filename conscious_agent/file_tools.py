from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paths import ROOT_DIR
from project_manager import get_active_project
from memory import store_memory


IGNORED_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", "venv", ".venv", "env", ".env", "dist", "build",
    "target", "bin", "obj", ".gradle", ".godot", "chroma"
}

TEXT_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".html", ".css", ".js", ".ts", ".java", ".kt", ".cs", ".php", ".gd",
    ".xml", ".csv", ".sql", ".sh", ".bat", ".ps1", ".env.example"
}

MAX_READ_BYTES = 80_000
MAX_SEARCH_FILE_BYTES = 150_000


@dataclass
class FileReadResult:
    ok: bool
    path: str
    content: str = ""
    error: str = ""


def active_project_root() -> Path:
    """
    Returns the active project's root path. If no path is configured, default to Eidolon's root.
    """
    project = get_active_project()
    configured_path = (project or {}).get("path", "") if project else ""

    if configured_path:
        root = Path(configured_path).expanduser()
        if not root.is_absolute():
            root = (ROOT_DIR / root).resolve()
    else:
        root = ROOT_DIR.resolve()

    return root.resolve()


def safe_project_path(relative_path: str | Path = "") -> Path:
    """
    Resolves a path and prevents access outside the active project folder.
    """
    root = active_project_root()
    requested = Path(relative_path)

    if requested.is_absolute():
        resolved = requested.resolve()
    else:
        resolved = (root / requested).resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"Blocked path outside active project: {resolved}") from exc

    return resolved


def is_probably_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True

    try:
        sample = path.read_bytes()[:2048]
    except OSError:
        return False

    if b"\x00" in sample:
        return False

    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def list_project_files(
    relative_path: str = "",
    max_files: int = 200,
    include_dirs: bool = True,
) -> list[dict[str, Any]]:
    """
    Lists files under the active project folder. Read-only.
    """
    root = active_project_root()
    start = safe_project_path(relative_path)

    if not start.exists():
        return [{"type": "error", "path": str(start), "message": "Path does not exist."}]

    if start.is_file():
        return [{
            "type": "file",
            "path": str(start.relative_to(root)),
            "size_bytes": start.stat().st_size,
        }]

    items: list[dict[str, Any]] = []

    for path in sorted(start.rglob("*")):
        rel = path.relative_to(root)
        if should_ignore(rel):
            continue

        if path.is_dir():
            if include_dirs:
                items.append({"type": "dir", "path": str(rel)})
        else:
            items.append({
                "type": "file",
                "path": str(rel),
                "size_bytes": path.stat().st_size,
                "text_like": is_probably_text_file(path),
            })

        if len(items) >= max_files:
            items.append({
                "type": "notice",
                "path": "",
                "message": f"Stopped at {max_files} items. Narrow the path for more."
            })
            break

    store_memory({
        "type": "file_tool_event",
        "content": f"Listed project files under '{relative_path or '.'}'.",
        "source": "file_tools",
        "project_root": str(root),
    })

    return items


def read_project_file(relative_path: str, max_bytes: int = MAX_READ_BYTES) -> FileReadResult:
    """
    Reads a text-like file from the active project folder. Read-only.
    """
    root = active_project_root()

    try:
        path = safe_project_path(relative_path)
    except PermissionError as error:
        return FileReadResult(ok=False, path=relative_path, error=str(error))

    if not path.exists():
        return FileReadResult(ok=False, path=relative_path, error="File does not exist.")

    if not path.is_file():
        return FileReadResult(ok=False, path=relative_path, error="Path is not a file.")

    if not is_probably_text_file(path):
        return FileReadResult(ok=False, path=relative_path, error="Refusing to read binary or unknown non-text file.")

    try:
        raw = path.read_bytes()[:max_bytes]
        content = raw.decode("utf-8", errors="replace")
    except OSError as error:
        return FileReadResult(ok=False, path=relative_path, error=str(error))

    if path.stat().st_size > max_bytes:
        content += f"\n\n[TRUNCATED: file is larger than {max_bytes} bytes]"

    rel_path = str(path.relative_to(root))
    store_memory({
        "type": "file_tool_event",
        "content": f"Read project file '{rel_path}'.",
        "source": "file_tools",
        "project_root": str(root),
    })

    return FileReadResult(ok=True, path=rel_path, content=content)


def search_project_files(
    query: str,
    relative_path: str = "",
    max_matches: int = 50,
) -> list[dict[str, Any]]:
    """
    Searches text-like project files for an exact text query. Read-only.
    """
    query_lower = query.lower().strip()
    if not query_lower:
        return []

    root = active_project_root()
    start = safe_project_path(relative_path)
    matches: list[dict[str, Any]] = []

    files = [start] if start.is_file() else sorted(start.rglob("*"))

    for path in files:
        if len(matches) >= max_matches:
            break
        if not path.is_file():
            continue

        rel = path.relative_to(root)
        if should_ignore(rel):
            continue

        try:
            if path.stat().st_size > MAX_SEARCH_FILE_BYTES:
                continue
        except OSError:
            continue

        if not is_probably_text_file(path):
            continue

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if query_lower in line.lower():
                matches.append({
                    "path": str(rel),
                    "line": line_number,
                    "preview": line.strip()[:240],
                })
                if len(matches) >= max_matches:
                    break

    store_memory({
        "type": "file_tool_event",
        "content": f"Searched project files for '{query}'. Found {len(matches)} matches.",
        "source": "file_tools",
        "project_root": str(root),
    })

    return matches


def project_tree_text(relative_path: str = "", max_files: int = 120) -> str:
    items = list_project_files(relative_path=relative_path, max_files=max_files, include_dirs=True)
    if not items:
        return "No files found."

    lines = []
    for item in items:
        item_type = item.get("type")
        path = item.get("path", "")
        if item_type == "dir":
            lines.append(f"[D] {path}")
        elif item_type == "file":
            lines.append(f"[F] {path} ({item.get('size_bytes', 0)} bytes)")
        elif item_type == "notice":
            lines.append(f"[!] {item.get('message')}")
        elif item_type == "error":
            lines.append(f"[ERROR] {item.get('message')}")
    return "\n".join(lines)
