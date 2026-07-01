from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from file_tools import read_project_file
from local_brain import local_generate
from settings_manager import get_setting
from memory import store_memory
from paths import DATA_DIR
from project_indexer import search_project_index
from project_manager import get_active_project


PATCHES_DIR = DATA_DIR / "patches"
MAX_PATCH_INPUT_CHARS = 22_000
PROPOSED_START = "<<<EIDOLON_PROPOSED_FILE>>>"
PROPOSED_END = "<<<END_EIDOLON_PROPOSED_FILE>>>"
NO_PATCH_MARKER = "<<<EIDOLON_NO_PATCH>>>"


@dataclass
class PatchSuggestionResult:
    ok: bool
    patch_id: str = ""
    target_file: str = ""
    text: str = ""
    error: str = ""


def _safe_console_print(value: str = "") -> None:
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode(encoding, errors="replace"))
        sys.stdout.flush()


def _ensure_patches_dir() -> None:
    PATCHES_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(value: str, max_len: int = 36) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    if not slug:
        return "patch"
    return slug[:max_len]


def _new_patch_id(relative_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"patch_{timestamp}_{_slugify(relative_path)}"


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def _extract_proposed_content(raw_output: str) -> tuple[bool, str, str]:
    """
    Returns (ok, proposed_content, error).
    The local model is asked to return a complete replacement file between explicit markers.
    """
    if not raw_output.strip():
        return False, "", "The local model returned an empty response."

    if raw_output.strip().startswith(NO_PATCH_MARKER) or NO_PATCH_MARKER in raw_output:
        reason = raw_output.replace(NO_PATCH_MARKER, "").strip()
        return False, "", reason or "The local model decided no safe patch could be proposed."

    start_index = raw_output.find(PROPOSED_START)
    end_index = raw_output.find(PROPOSED_END)

    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return False, "", (
            "The local model did not return a parseable patch. "
            "Expected the proposed full file between Eidolon patch markers."
        )

    proposed = raw_output[start_index + len(PROPOSED_START):end_index]

    # Preserve meaningful file content while removing marker-adjacent blank lines.
    proposed = proposed.strip("\n")

    return True, proposed, ""


def _make_unified_diff(original: str, proposed: str, relative_path: str) -> str:
    original_lines = original.splitlines(keepends=True)
    proposed_lines = proposed.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        proposed_lines,
        fromfile=f"a/{relative_path}",
        tofile=f"b/{relative_path}",
        lineterm="",
    )

    return "\n".join(diff)


def _risk_level(relative_path: str, request: str, diff_text: str) -> str:
    lowered = f"{relative_path}\n{request}\n{diff_text}".lower()

    high_risk_terms = [
        "delete", "remove safety", "disable safety", "token", "password", "secret",
        "api_key", "subprocess", "os.system", "shell=true", "eval(", "exec(",
        "write", "unlink", "rmtree", "chmod", "admin", "registry",
    ]
    medium_files = [
        "safety.py", "actions.py", "file_tools.py", "patch_suggester.py", "main.py",
        "local_brain.py", "memory.py",
    ]

    if any(term in lowered for term in high_risk_terms):
        return "high"

    if any(relative_path.endswith(name) for name in medium_files):
        return "medium"

    changed_lines = [line for line in diff_text.splitlines() if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
    if len(changed_lines) > 80:
        return "medium"

    return "low"


def _project_index_context(relative_path: str) -> str:
    matches = search_project_index(relative_path)
    if not matches:
        return "No matching project index entry found. Run --index-project to refresh the index."

    chosen = matches[0]
    for match in matches:
        if match.get("path") == relative_path:
            chosen = match
            break

    return json.dumps(chosen, indent=2)[:4_000]


def _build_patch_prompt(relative_path: str, request: str, original: str) -> str:
    active_project = get_active_project() or {}
    index_context = _project_index_context(relative_path)
    clipped_original = original[:MAX_PATCH_INPUT_CHARS]

    return f"""
You are Eidolon, a local AI programming assistant for Marcus.

You are in PATCH SUGGESTION MODE.
You are READ-ONLY. You are not allowed to claim you edited files.
Your job is to propose a safe full-file replacement for the target file.

Active project:
{active_project}

Target file:
{relative_path}

Project index context:
{index_context}

Marcus's requested change:
{request}

Original file content, possibly truncated:
```text
{clipped_original}
```

Rules:
- Return ONLY a complete replacement file between the exact markers below.
- Do not include explanations outside the markers.
- Preserve existing behavior unless the requested change requires changing it.
- Keep changes minimal and safe.
- Do not add destructive file operations.
- Do not add command execution.
- Do not add external network calls.
- Do not remove safety checks.
- If the file is too incomplete/truncated or you cannot safely propose a patch, return:
{NO_PATCH_MARKER} <short reason>

Required output format:
{PROPOSED_START}
<full replacement file content here>
{PROPOSED_END}
""".strip()


def _proposal_path(patch_id: str) -> Path:
    return PATCHES_DIR / f"{patch_id}.json"


def save_patch_proposal(proposal: dict[str, Any]) -> None:
    _ensure_patches_dir()
    with _proposal_path(proposal["id"]).open("w", encoding="utf-8") as file:
        json.dump(proposal, file, indent=2)



def resolve_patch_id(patch_id: str, status: str | None = None) -> str:
    """
    Resolves convenience aliases like latest, latest-proposed, latest-applied,
    and latest-rolled-back into a concrete patch id.
    """
    token = (patch_id or "").strip()
    lowered = token.lower()

    alias_status = {
        "latest-proposed": "proposed",
        "last-proposed": "proposed",
        "latest-applied": "applied",
        "last-applied": "applied",
        "latest-rolled-back": "rolled_back",
        "last-rolled-back": "rolled_back",
        "latest-rollback": "rolled_back",
        "last-rollback": "rolled_back",
    }

    if lowered in alias_status:
        status = alias_status[lowered]
    elif lowered not in {"latest", "last"}:
        return token

    proposals = list_patch_proposals()
    if status:
        proposals = [proposal for proposal in proposals if proposal.get("status") == status]

    if not proposals:
        return ""

    return proposals[0].get("id", "")


def load_patch_proposal(patch_id: str) -> dict[str, Any] | None:
    resolved_id = resolve_patch_id(patch_id)
    if not resolved_id:
        return None

    path = _proposal_path(resolved_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_patch_proposals() -> list[dict[str, Any]]:
    _ensure_patches_dir()
    proposals: list[dict[str, Any]] = []

    for path in sorted(PATCHES_DIR.glob("*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(data, dict):
            proposals.append(data)

    return proposals


def suggest_patch(relative_path: str, request: str, use_ai: bool = True) -> PatchSuggestionResult:
    read = read_project_file(relative_path)
    if not read.ok:
        return PatchSuggestionResult(ok=False, target_file=relative_path, error=read.error)

    if not use_ai:
        return PatchSuggestionResult(
            ok=False,
            target_file=read.path,
            error="Patch suggestion currently requires the local AI model. Use code review mode for static-only feedback.",
        )

    original = read.content
    prompt = _build_patch_prompt(read.path, request, original)
    raw_output = local_generate(
        prompt=prompt,
        temperature=0.15,
        max_tokens=2600,
    )

    if raw_output.startswith("I tried to use my local brain") or raw_output.startswith("My local brain"):
        return PatchSuggestionResult(ok=False, target_file=read.path, error=raw_output)

    ok, proposed, parse_error = _extract_proposed_content(raw_output)
    if not ok:
        return PatchSuggestionResult(ok=False, target_file=read.path, error=parse_error)

    if proposed.strip() == original.strip():
        return PatchSuggestionResult(
            ok=False,
            target_file=read.path,
            error="The proposed file is effectively identical to the original. No patch saved.",
        )

    diff_text = _make_unified_diff(original, proposed, read.path)
    patch_id = _new_patch_id(read.path)
    risk = _risk_level(read.path, request, diff_text)

    proposal = {
        "id": patch_id,
        "status": "proposed",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "target_file": read.path,
        "request": request,
        "summary": "Local AI generated a full-file replacement proposal. Review the diff before applying in a future version.",
        "risk_level": risk,
        "model": get_setting("local_model", "qwen2.5:7b"),
        "original_sha256": _sha256(original),
        "proposed_sha256": _sha256(proposed),
        "original_content": original,
        "proposed_content": proposed,
        "unified_diff": diff_text,
    }

    save_patch_proposal(proposal)

    store_memory({
        "type": "patch_suggestion_event",
        "content": f"Created patch proposal {patch_id} for '{read.path}' with risk level {risk}. Request: {request}",
        "source": "patch_suggester",
        "file": read.path,
        "patch_id": patch_id,
        "risk_level": risk,
    })

    return PatchSuggestionResult(
        ok=True,
        patch_id=patch_id,
        target_file=read.path,
        text=patch_proposal_text(proposal, include_full_content=False),
    )


def patch_proposal_text(proposal: dict[str, Any], include_full_content: bool = False) -> str:
    lines = [
        f"# Patch Proposal: {proposal.get('id')}",
        "",
        f"Status: {proposal.get('status')}",
        f"Created: {proposal.get('created_at')}",
        f"Target file: {proposal.get('target_file')}",
        f"Risk level: {proposal.get('risk_level')}",
        f"Request: {proposal.get('request')}",
        "",
        "## Summary",
        proposal.get("summary", ""),
        "",
        "## Unified diff",
        "```diff",
        proposal.get("unified_diff", ""),
        "```",
    ]

    if include_full_content:
        lines.extend([
            "",
            "## Proposed full file content",
            "```text",
            proposal.get("proposed_content", ""),
            "```",
        ])

    return "\n".join(lines).strip()


def print_patch_suggestion(relative_path: str, request: str, use_ai: bool = True) -> None:
    result = suggest_patch(relative_path=relative_path, request=request, use_ai=use_ai)
    if not result.ok:
        print(f"Could not create patch suggestion for {result.target_file or relative_path}: {result.error}")
        return
    _safe_console_print(result.text)
    print()
    print(f"Saved patch proposal: {result.patch_id}")
    print("This did not edit any files. Review only. The goblin still has no hands.")
    print()
    print("Shortcut commands:")
    print("  python conscious_agent/main.py --show-patch latest")
    print("  python conscious_agent/main.py --apply-patch latest --dry-run")


def print_patch_list() -> None:
    proposals = list_patch_proposals()
    if not proposals:
        print("No patch proposals found.")
        return

    for proposal in proposals:
        print(
            f"{proposal.get('id')} | {proposal.get('status')} | "
            f"risk={proposal.get('risk_level')} | {proposal.get('target_file')} | "
            f"{proposal.get('created_at')}"
        )
        print(f"  Request: {proposal.get('request')}")


def print_patch_proposal(patch_id: str, include_full_content: bool = False) -> None:
    proposal = load_patch_proposal(patch_id)
    if not proposal:
        print(f"Patch proposal not found: {patch_id}")
        return
    _safe_console_print(patch_proposal_text(proposal, include_full_content=include_full_content))
