from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from file_tools import read_project_file
from local_brain import local_generate
from memory import store_memory
from project_indexer import search_project_index
from project_manager import get_active_project


MAX_REVIEW_CHARS = 18_000


@dataclass
class ReviewResult:
    ok: bool
    path: str
    text: str
    error: str = ""


def _line_count(content: str) -> int:
    return len(content.splitlines())


def _python_static_review(path: str, content: str) -> list[str]:
    """
    Lightweight read-only Python review. This is intentionally conservative.
    It flags things worth inspecting, not guaranteed bugs.
    """
    issues: list[str] = []
    lines = content.splitlines()

    try:
        tree = ast.parse(content)
    except SyntaxError as error:
        return [f"Syntax error: {error}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if len(node.body) > 80:
                issues.append(f"Function '{node.name}' is long ({len(node.body)} top-level statements). Consider splitting it.")
            if not ast.get_docstring(node) and not node.name.startswith("_"):
                issues.append(f"Function '{node.name}' has no docstring. Not fatal, but important public helpers may need one.")

        elif isinstance(node, ast.ClassDef):
            if not ast.get_docstring(node):
                issues.append(f"Class '{node.name}' has no docstring.")

        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append("Bare except found. Catch a specific exception unless there is a very good reason.")
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                issues.append("Exception handler silently passes. This can hide failures.")

        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "eval":
                issues.append("Use of eval() found. This is risky unless input is tightly controlled.")
            if isinstance(func, ast.Name) and func.id == "exec":
                issues.append("Use of exec() found. This is risky unless input is tightly controlled.")

    for number, line in enumerate(lines, start=1):
        lowered = line.lower()
        stripped = line.strip()
        if "todo" in lowered or "fixme" in lowered:
            issues.append(f"Line {number}: TODO/FIXME found: {stripped[:160]}")
        if len(line) > 140:
            issues.append(f"Line {number}: very long line ({len(line)} chars).")
        if "password" in lowered and "=" in line:
            issues.append(f"Line {number}: possible hardcoded password-like value. Inspect manually.")
        if "api_key" in lowered and "=" in line:
            issues.append(f"Line {number}: possible hardcoded API key-like value. Inspect manually.")
        if "secret" in lowered and "=" in line:
            issues.append(f"Line {number}: possible hardcoded secret-like value. Inspect manually.")

    # Deduplicate while preserving order.
    deduped: list[str] = []
    seen: set[str] = set()
    for issue in issues:
        if issue not in seen:
            deduped.append(issue)
            seen.add(issue)

    return deduped[:40]


def _generic_static_review(path: str, content: str) -> list[str]:
    issues: list[str] = []
    lines = content.splitlines()

    for number, line in enumerate(lines, start=1):
        lowered = line.lower()
        stripped = line.strip()
        if "todo" in lowered or "fixme" in lowered:
            issues.append(f"Line {number}: TODO/FIXME found: {stripped[:160]}")
        if len(line) > 180:
            issues.append(f"Line {number}: very long line ({len(line)} chars).")
        if any(term in lowered for term in ["password", "api_key", "secret", "token"]):
            if "=" in line or ":" in line:
                issues.append(f"Line {number}: possible sensitive value. Inspect manually: {stripped[:160]}")

    return issues[:40]


def static_review(path: str, content: str) -> list[str]:
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        return _python_static_review(path, content)
    return _generic_static_review(path, content)


def _project_index_context(relative_path: str) -> str:
    matches = search_project_index(relative_path)
    if not matches:
        return "No matching project index entry found. Run --index-project to refresh the index."

    # Prefer exact path match if available.
    chosen = matches[0]
    for match in matches:
        if match.get("path") == relative_path:
            chosen = match
            break

    summary = chosen.get("summary", {})
    return f"Index entry for {chosen.get('path')}:\n{summary}"


def _ai_review(relative_path: str, content: str, static_issues: list[str]) -> str:
    active_project = get_active_project() or {}
    clipped_content = content[:MAX_REVIEW_CHARS]

    prompt = f"""
You are Eidolon, a local AI programming assistant reviewing code for Marcus.

You are doing READ-ONLY review. Do not claim you edited files. Do not tell Marcus to blindly trust you.

Active project:
{active_project}

File path:
{relative_path}

Static findings:
{static_issues if static_issues else 'No static findings.'}

File content, possibly truncated:
```text
{clipped_content}
```

Write a practical code review with these sections:
1. What this file appears to do
2. Important functions/classes/components
3. Likely issues or risks
4. Suggested improvements
5. Safest next step

Keep it under 700 words.
"""
    return local_generate(prompt=prompt, temperature=0.25, max_tokens=900)


def review_project_file(relative_path: str, use_ai: bool = True) -> ReviewResult:
    read = read_project_file(relative_path)
    if not read.ok:
        return ReviewResult(ok=False, path=relative_path, text="", error=read.error)

    content = read.content
    static_issues = static_review(read.path, content)
    index_context = _project_index_context(read.path)

    lines: list[str] = [
        f"# Code Review: {read.path}",
        "",
        "## Basic facts",
        f"- Lines: {_line_count(content)}",
        f"- Characters reviewed: {min(len(content), MAX_REVIEW_CHARS)} of {len(content)}",
        "",
        "## Project index context",
        index_context,
        "",
        "## Static review findings",
    ]

    if static_issues:
        lines.extend(f"- {issue}" for issue in static_issues)
    else:
        lines.append("- No obvious static issues found by the lightweight checker.")

    if use_ai:
        lines.extend([
            "",
            "## Local AI review",
            _ai_review(read.path, content, static_issues),
        ])
    else:
        lines.extend([
            "",
            "## Local AI review",
            "Skipped. Run without --no-ai-review to use the local Ollama model.",
        ])

    review_text = "\n".join(lines).strip()

    store_memory({
        "type": "code_review_event",
        "content": f"Reviewed project file '{read.path}' using {'static + local AI' if use_ai else 'static only'} review.",
        "source": "code_reviewer",
        "file": read.path,
    })

    return ReviewResult(ok=True, path=read.path, text=review_text)


def print_code_review(relative_path: str, use_ai: bool = True) -> None:
    result = review_project_file(relative_path, use_ai=use_ai)
    if not result.ok:
        print(f"Could not review {relative_path}: {result.error}")
        return
    print(result.text)
