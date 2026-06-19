from __future__ import annotations

import ast
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from file_tools import active_project_root, safe_project_path, is_probably_text_file, should_ignore
from memory import store_memory
from paths import DATA_DIR
from project_manager import get_active_project, add_project_item


INDEX_FILE = DATA_DIR / "project_index.json"

INDEXABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".kt", ".cs", ".php", ".html", ".css",
    ".gd", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".xml", ".sql"
}

MAX_INDEX_FILE_BYTES = 200_000
DEFAULT_MAX_FILES = 400


def load_project_index() -> dict[str, Any]:
    if not INDEX_FILE.exists() or INDEX_FILE.stat().st_size == 0:
        return {"indexed_at": None, "active_project": None, "project_path": "", "files": []}

    try:
        with INDEX_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {"indexed_at": None, "active_project": None, "project_path": "", "files": []}

    if not isinstance(data, dict):
        return {"indexed_at": None, "active_project": None, "project_path": "", "files": []}

    data.setdefault("files", [])
    return data


def save_project_index(index: dict[str, Any]) -> None:
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_FILE.open("w", encoding="utf-8") as file:
        json.dump(index, file, indent=2)


def is_indexable_file(path: Path) -> bool:
    if path.suffix.lower() in INDEXABLE_EXTENSIONS:
        return True
    return is_probably_text_file(path)


def summarize_python_file(content: str) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "classes": [],
        "functions": [],
        "imports": [],
        "parse_error": None,
        "line_count": len(content.splitlines()),
    }

    try:
        tree = ast.parse(content)
    except SyntaxError as error:
        summary["parse_error"] = str(error)
        return summary

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            summary["classes"].append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            summary["functions"].append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                summary["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                summary["imports"].append(module)

    summary["classes"] = sorted(set(summary["classes"]))
    summary["functions"] = sorted(set(summary["functions"]))
    summary["imports"] = sorted(set(summary["imports"]))
    return summary


def summarize_generic_file(content: str) -> dict[str, Any]:
    lines = content.splitlines()
    non_empty = [line.strip() for line in lines if line.strip()]
    return {
        "line_count": len(lines),
        "non_empty_line_count": len(non_empty),
        "preview": "\n".join(non_empty[:10]),
    }


def index_project(relative_path: str = "", max_files: int = DEFAULT_MAX_FILES) -> dict[str, Any]:
    active_project = get_active_project()
    if not active_project:
        return {"success": False, "message": "No active project found.", "files_indexed": 0}

    root = active_project_root()
    if not root.exists():
        return {"success": False, "message": f"Active project path does not exist: {root}", "files_indexed": 0}

    try:
        start = safe_project_path(relative_path)
    except PermissionError as error:
        return {"success": False, "message": str(error), "files_indexed": 0}

    if not start.exists():
        return {"success": False, "message": f"Path does not exist: {relative_path or '.'}", "files_indexed": 0}

    candidate_paths = [start] if start.is_file() else sorted(start.rglob("*"))
    indexed_files: list[dict[str, Any]] = []

    for path in candidate_paths:
        if len(indexed_files) >= max_files:
            break
        if not path.is_file():
            continue

        rel = path.relative_to(root)
        if should_ignore(rel):
            continue
        if not is_indexable_file(path):
            continue
        if path.stat().st_size > MAX_INDEX_FILE_BYTES:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        summary = summarize_python_file(content) if path.suffix.lower() == ".py" else summarize_generic_file(content)

        indexed_files.append({
            "path": str(rel).replace("\\", "/"),
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            "summary": summary,
        })

    index = {
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
        "active_project": active_project.get("name", "Unknown"),
        "project_path": str(root),
        "relative_path": relative_path,
        "max_files": max_files,
        "files": indexed_files,
    }
    save_project_index(index)

    store_memory({
        "type": "project_index_event",
        "content": f"Indexed {len(indexed_files)} files for project {active_project.get('name', 'Unknown')}.",
        "source": "project_indexer",
        "project": active_project.get("name", "Unknown"),
    })

    # Mark the milestone in project notes without failing if the project metadata is unavailable.
    try:
        add_project_item(active_project.get("name", ""), "notes", f"Project indexed at {index['indexed_at']} with {len(indexed_files)} files.")
    except Exception:
        pass

    return {
        "success": True,
        "message": "Project index created.",
        "files_indexed": len(indexed_files),
        "index_file": str(INDEX_FILE),
    }


def project_index_summary_text() -> str:
    index = load_project_index()
    files = index.get("files", [])
    lines = [
        f"Indexed at: {index.get('indexed_at')}",
        f"Active project: {index.get('active_project')}",
        f"Project path: {index.get('project_path')}",
        f"Files indexed: {len(files)}",
    ]

    by_extension: dict[str, int] = {}
    for file in files:
        ext = file.get("extension") or "[none]"
        by_extension[ext] = by_extension.get(ext, 0) + 1

    lines.append("\nFiles by extension:")
    if by_extension:
        for ext, count in sorted(by_extension.items()):
            lines.append(f"  {ext}: {count}")
    else:
        lines.append("  none")

    lines.append("\nPython structure:")
    printed_any = False
    for file in files:
        if file.get("extension") != ".py":
            continue
        summary = file.get("summary", {})
        classes = summary.get("classes", [])
        functions = summary.get("functions", [])
        parse_error = summary.get("parse_error")
        if not classes and not functions and not parse_error:
            continue
        printed_any = True
        lines.append(f"\n{file.get('path')}")
        if classes:
            lines.append(f"  Classes: {', '.join(classes)}")
        if functions:
            lines.append(f"  Functions: {', '.join(functions)}")
        if parse_error:
            lines.append(f"  Parse error: {parse_error}")

    if not printed_any:
        lines.append("  No Python structure found.")

    return "\n".join(lines)


def print_project_index_summary() -> None:
    print(project_index_summary_text())


def search_project_index(query: str) -> list[dict[str, Any]]:
    query_lower = query.lower().strip()
    if not query_lower:
        return []

    index = load_project_index()
    matches: list[dict[str, Any]] = []

    for file in index.get("files", []):
        searchable = json.dumps({
            "path": file.get("path", ""),
            "extension": file.get("extension", ""),
            "summary": file.get("summary", {}),
        }).lower()
        if query_lower in searchable:
            matches.append(file)

    return matches


def project_index_search_text(query: str) -> str:
    matches = search_project_index(query)
    if not matches:
        return "No index matches found. Run --index-project first if the index is empty."

    lines = []
    for file in matches:
        lines.append(f"\n{file.get('path')}")
        lines.append(f"  Extension: {file.get('extension')}")
        lines.append(f"  Size: {file.get('size_bytes')} bytes")
        summary = file.get("summary", {})
        if file.get("extension") == ".py":
            if summary.get("classes"):
                lines.append(f"  Classes: {', '.join(summary.get('classes', []))}")
            if summary.get("functions"):
                lines.append(f"  Functions: {', '.join(summary.get('functions', []))}")
            if summary.get("imports"):
                lines.append(f"  Imports: {', '.join(summary.get('imports', [])[:12])}")
            if summary.get("parse_error"):
                lines.append(f"  Parse error: {summary.get('parse_error')}")
        else:
            preview = summary.get("preview")
            if preview:
                lines.append("  Preview:")
                lines.extend(f"    {line}" for line in preview.splitlines())

    return "\n".join(lines).lstrip()


def print_project_index_search(query: str) -> None:
    print(project_index_search_text(query))
