from __future__ import annotations

"""v1254.3-v1254.5 supervised isolated coding execution.

This module extends the v1254.0-v1254.2 request/inspection/plan/workspace
foundation through one exact, digest-bound implementation authorization.  It
may contact the configured provider, modify only the disposable workspace, run
bounded project-owned verification, make at most two repair attempts, and seal
an operator-review result.  It never applies changes to the selected project.

The implementation intentionally reuses the existing development-campaign
store/locking primitives, structured-generation validation helpers, and the
bounded Python/Node command runners rather than creating another product or an
unrestricted shell surface.
"""

import difflib
import hashlib
import json
import os
import re
import shutil
import time
import uuid
from collections import Counter
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from isolated_coding_execution_foundations import (
    AUTHORITY_STATE,
    _file_digest,
    _is_link_like,
    _is_private_or_excluded,
    _is_relevant_source,
    _manifest_digest,
    _path_digest,
    _resolve_project_root,
    _safe_relative,
    _walk_project,
    _within,
    check_coding_source_freshness,
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    load_coding_project_inspection,
    load_coding_work_plan,
    load_coding_work_request,
    materialize_or_restore_isolated_coding_workspace,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)
from structured_development_generation import _extract as _extract_structured_output
from structured_development_generation import _syntax as _validate_syntax

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1254.5"
MAX_PROVIDER_CONTEXT_BYTES = 30 * 1024
MAX_PROVIDER_FILE_EXCERPT_BYTES = 12 * 1024
MAX_PROVIDER_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_TRANSIENT_REPAIR_CANDIDATE_BYTES = 16 * 1024
MAX_CHANGE_FILES = 32
MAX_CHANGE_FILE_BYTES = 768 * 1024
MAX_CHANGE_TOTAL_BYTES = 4 * 1024 * 1024
MAX_DIFF_BYTES = 512 * 1024
MAX_EXECUTION_ATTEMPTS = 4  # one implementation + at most three bounded repairs
MAX_FOCUSED_TEST_FILES = 8
LEASE_SECONDS = 180.0
CODING_CONTEXT_SIZE = 16_384
CODING_MAX_TOKENS = 4_096
CODING_READ_TIMEOUT_SECONDS = 600.0

EXECUTION_AUTHORITY = {
    **AUTHORITY_STATE,
    "implementation_execution_authorized": True,
    "command_execution_authorized": True,
    "test_execution_authorized": True,
    "provider_contact_authorized": True,
}

_EXECUTE = re.compile(
    r"^(?:i\s+)?authorize\s+isolated\s+coding\s+execution\s+for\s+request\s+"
    r"(?P<request_id>devc_[a-f0-9]{24})\s+execution\s+(?P<execution_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_CANCEL = re.compile(
    r"^(?:i\s+)?cancel\s+isolated\s+coding\s+request\s+(?P<request_id>devc_[a-f0-9]{24})[.!?]*$",
    re.I,
)
_REVIEW = re.compile(
    r"^(?:please\s+)?review\s+isolated\s+coding\s+request\s+(?P<request_id>devc_[a-f0-9]{24})[.!?]*$",
    re.I,
)


def _execution_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "isolated_coding_executions" / f"{request_id}.json"


def _attempt_path(request_id: str, attempt_number: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "isolated_coding_execution_attempts" / request_id / f"attempt-{int(attempt_number)}.json"


def _review_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "isolated_coding_execution_reviews" / f"{request_id}.json"


def _bridge_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "isolated_coding_proposal_bridges" / proposal_id / f"revision-{int(revision)}.json"


def _seal(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _authorization_phrase(request_id: str, execution_digest: str) -> str:
    return f"Authorize isolated coding execution for request {request_id} execution {execution_digest}."


def _authorization_text_matches(actual: str, expected: str) -> bool:
    """Ignore terminal prose punctuation while preserving exact authority tokens."""

    normalize = lambda value: str(value or "").strip().rstrip(".!?").casefold()
    return normalize(actual) == normalize(expected)


def _failure(status: str, *, request_id: str = "", reason: str = "") -> dict[str, Any]:
    row = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "request_id": request_id,
        "reason": reason,
        "operator_review_required": True,
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "installation_authorized": False,
        "release_authorized": False,
        "permanent_approval_granted": False,
        "independent_authority_granted": False,
    }
    row["failure_digest"] = _digest(row)
    return row


def _workspace_root_from_record(record: Mapping[str, Any]) -> Path:
    raw = str(record.get("workspace_path") or "")
    if not raw:
        raise ValueError("isolated_workspace_path_missing")
    root = Path(raw).resolve(strict=True)
    if not root.is_dir() or _is_link_like(root):
        raise ValueError("isolated_workspace_unavailable")
    return root


def _strict_workspace_integrity(root: Path) -> tuple[bool, str]:
    """Reject unexpected links, private/generated material, and case collisions."""
    folded: set[str] = set()
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name.casefold())
        except OSError:
            return False, "workspace_scan_failed"
        for entry in entries:
            path = Path(entry.path)
            try:
                relative = PurePosixPath(path.relative_to(root).as_posix())
            except ValueError:
                return False, "workspace_containment_violation"
            if _is_link_like(path) or not _within(root, path):
                return False, "workspace_link_or_boundary_rejected"
            if _is_private_or_excluded(relative):
                return False, "workspace_private_or_generated_material_detected"
            key = relative.as_posix().casefold()
            if key in folded:
                return False, "workspace_casefold_path_collision"
            folded.add(key)
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                elif not entry.is_file(follow_symlinks=False):
                    return False, "workspace_special_file_rejected"
            except OSError:
                return False, "workspace_entry_unreadable"
    return True, "workspace_integrity_ready"


def _baseline_workspace_valid(record: Mapping[str, Any]) -> bool:
    try:
        root = _workspace_root_from_record(record)
        integrity_ok, _ = _strict_workspace_integrity(root)
        if not integrity_ok:
            return False
        files, stats = _walk_project(root)
        if int(stats.get("private_or_excluded_count") or 0) or int(stats.get("link_or_boundary_rejection_count") or 0):
            return False
    except (OSError, ValueError):
        return False
    expected = list(record.get("files") or [])
    normalized = [
        {
            "relative_path": str(row.get("relative_path") or ""),
            "relative_path_digest": str(row.get("relative_path_digest") or ""),
            "content_digest": str(row.get("content_digest") or ""),
            "size_bytes": int(row.get("size_bytes") or 0),
        }
        for row in expected
    ]
    actual = [
        {
            "relative_path": str(row.get("relative_path") or ""),
            "relative_path_digest": str(row.get("relative_path_digest") or ""),
            "content_digest": str(row.get("content_digest") or ""),
            "size_bytes": int(row.get("size_bytes") or 0),
        }
        for row in files
    ]
    return actual == normalized and _manifest_digest(actual) == str(record.get("workspace_manifest_digest") or "")


def prepare_isolated_coding_execution(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    """Prepare one exact authorization for the sealed v1254 foundation lineage."""

    with _proposal_lock(request_id, runtime_root):
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
        plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
        workspace = _read_json(_store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json")
        if not request or not inspection or not plan or not workspace:
            return _failure("isolated_coding_execution_foundation_missing", request_id=request_id)
        if request.get("cancelled"):
            return _failure("isolated_coding_execution_cancelled", request_id=request_id)

        binding = {
            "contract_version": CONTRACT_VERSION,
            "request_id": request_id,
            "request_digest": str(request.get("request_digest") or ""),
            "inspection_digest": str(inspection.get("inspection_digest") or ""),
            "plan_digest": str(plan.get("plan_digest") or ""),
            "source_manifest_digest": str(inspection.get("source_manifest_digest") or ""),
            "baseline_workspace_manifest_digest": str(workspace.get("workspace_manifest_digest") or ""),
            "project_type": str(inspection.get("project_type") or ""),
            "adapter_id": str(inspection.get("adapter_id") or ""),
            "maximum_attempts": MAX_EXECUTION_ATTEMPTS,
        }
        execution_digest = _digest(binding)
        path = _execution_path(request_id, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "execution_record_digest"):
                return _failure("isolated_coding_execution_record_invalid", request_id=request_id)
            if str(existing.get("execution_digest") or "") != execution_digest:
                return _failure("isolated_coding_execution_binding_changed", request_id=request_id)
            if existing.get("phase") == "sealed":
                result = dict(existing.get("result") or {})
                if not result or str(existing.get("result_digest") or "") != _digest(result):
                    return _failure("isolated_coding_execution_result_invalid", request_id=request_id)
                return {**existing, "operation_status": "restored"}
            if existing.get("phase") == "running":
                return {**existing, "operation_status": "restored"}
            if existing.get("phase") != "prepared":
                return _failure("isolated_coding_execution_state_invalid", request_id=request_id)
        if not _baseline_workspace_valid(workspace):
            return _failure("isolated_coding_execution_workspace_changed", request_id=request_id)
        freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
        if freshness.get("ok") is not True:
            return _failure(str(freshness.get("status") or "stale_source_detected"), request_id=request_id)
        if existing:
            return {**existing, "operation_status": "restored"}

        record = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "isolated_coding_execution_authorization_required",
            **binding,
            "execution_digest": execution_digest,
            "authorization_phrase": _authorization_phrase(request_id, execution_digest),
            "phase": "prepared",
            "attempt_count": 0,
            "repair_attempt_count": 0,
            "recovery_count": 0,
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "provider_contacted": False,
            "tests_executed": False,
            "reviewable_diff_available": False,
            "operator_review_required": True,
            "execution_authority_consumed": False,
            "selected_project_modified": False,
            "source_modified": False,
            **AUTHORITY_STATE,
        }
        record = _seal(record, "execution_record_digest")
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def _context_paths(plan: Mapping[str, Any], inspection: Mapping[str, Any]) -> list[str]:
    preferred: list[str] = []
    for path in plan.get("context_paths") or []:
        if path not in preferred:
            preferred.append(str(path))
    if preferred:
        return preferred
    for link in plan.get("requirement_file_links") or []:
        for path in link.get("candidate_files") or []:
            if path not in preferred:
                preferred.append(str(path))
    inventory = [str(row.get("relative_path") or "") for row in inspection.get("inventory") or []]
    return preferred or inventory[:8]


_CONTEXT_TERM = re.compile(r"[A-Za-z_][A-Za-z0-9_]{3,}")
_CONTEXT_LITERAL = re.compile(r"(['\"])([^\r\n'\"]{6,80})\1")
_CONTEXT_STOP_TERMS = {
    "assert", "class", "continue", "def", "else", "false", "from", "import",
    "none", "raise", "return", "self", "true", "with",
}


def _context_terms(text: str) -> Counter[str]:
    terms = Counter(
        term.lower()
        for term in _CONTEXT_TERM.findall(text)
        if term.lower() not in _CONTEXT_STOP_TERMS
    )
    # Exact literals shared by a focused test and source are stronger evidence
    # than frequent domain words such as "response" or "context".
    for _quote, literal in _CONTEXT_LITERAL.findall(text):
        if any(character.isalpha() for character in literal) and any(character.isspace() for character in literal):
            terms[f"literal:{literal.lower()}"] += 1_000
    return terms


def _relevant_source_excerpt(content: str, byte_limit: int, reference: Counter[str]) -> tuple[str, int, int]:
    """Return one exact contiguous source window centered on attributable terms."""

    lines = content.splitlines(keepends=True)
    if not lines:
        return "", 0, 0
    scores = [
        sum(reference.get(term, 0) for term in set(_context_terms(line)))
        for line in lines
    ]
    center = max(range(len(lines)), key=lambda index: (scores[index], -index))
    start = center
    end = center + 1
    center_bytes = lines[center].encode("utf-8")
    if len(center_bytes) > byte_limit:
        # A single pathological/minified line must never consume more than the
        # provider context budget. Keep a UTF-8-safe bounded window and mark it
        # explicitly so architecture analysis knows the physical line was larger.
        marker = f"\n[physical line {center + 1} truncated to provider byte budget]\n"
        marker_bytes = marker.encode("utf-8")
        payload_limit = max(0, byte_limit - len(marker_bytes))
        clipped = center_bytes[:payload_limit]
        while clipped:
            try:
                excerpt = clipped.decode("utf-8")
                break
            except UnicodeDecodeError:
                clipped = clipped[:-1]
        else:
            excerpt = ""
        return excerpt + marker, center + 1, center + 1
    size = len(center_bytes)
    while True:
        choices: list[tuple[int, int, str]] = []
        if start > 0:
            choices.append((scores[start - 1], -(center - (start - 1)), "left"))
        if end < len(lines):
            choices.append((scores[end], -(end - center), "right"))
        if not choices:
            break
        side = max(choices)[2]
        candidate = lines[start - 1] if side == "left" else lines[end]
        candidate_size = len(candidate.encode("utf-8"))
        if size + candidate_size > byte_limit:
            # Try the other side before declaring the bounded window full.
            other = "right" if side == "left" else "left"
            if other == "left" and start > 0:
                candidate = lines[start - 1]
            elif other == "right" and end < len(lines):
                candidate = lines[end]
            else:
                break
            candidate_size = len(candidate.encode("utf-8"))
            if size + candidate_size > byte_limit:
                break
            side = other
        if side == "left":
            start -= 1
        else:
            end += 1
        size += candidate_size
    return "".join(lines[start:end]), start + 1, end


def _read_provider_context(root: Path, paths: Sequence[str], *, relevance_text: str = "") -> list[dict[str, Any]]:
    available: list[tuple[str, str, int]] = []
    for relative in paths:
        safe = _safe_relative(relative)
        path = root / safe
        if not _within(root, path) or _is_link_like(path) or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        available.append((safe, content, len(content.encode("utf-8"))))

    rows: list[dict[str, Any]] = []
    total = 0
    reference = _context_terms(relevance_text)
    for _safe, content, _size in available:
        reference.update(_context_terms(content))
    for safe, content, size in available:
        remaining = MAX_PROVIDER_CONTEXT_BYTES - total
        if remaining <= 0:
            break
        if size <= remaining:
            rows.append({"path": safe, "content": content})
            total += size
            continue
        excerpt_limit = min(MAX_PROVIDER_FILE_EXCERPT_BYTES, remaining)
        if excerpt_limit < 512:
            continue
        own_terms = _context_terms(content)
        external_reference = reference.copy()
        external_reference.subtract(own_terms)
        external_reference += Counter()
        excerpt, start_line, end_line = _relevant_source_excerpt(content, excerpt_limit, external_reference)
        excerpt_size = len(excerpt.encode("utf-8"))
        if not excerpt or excerpt_size > remaining:
            continue
        rows.append({
            "path": safe,
            "content": excerpt,
            "excerpt": True,
            "start_line": start_line,
            "end_line": end_line,
        })
        total += excerpt_size
    if not rows:
        raise ValueError("provider_context_empty")
    return rows


def _provider_prompt(
    *,
    request: Mapping[str, Any],
    plan: Mapping[str, Any],
    inspection: Mapping[str, Any],
    root: Path,
    execution_digest: str,
    attempt_number: int,
    previous_outcome: Mapping[str, Any] | None,
) -> str:
    relevance_text = json.dumps({"request": dict(request), "plan": dict(plan)}, sort_keys=True, default=str)
    files = _read_provider_context(
        root,
        _context_paths(plan, inspection),
        relevance_text=relevance_text,
    )
    construction_contract = {}
    try:
        from complete_application_construction_foundations import (
            load_complete_application_construction,
            public_complete_application_construction,
        )
        loaded_construction = load_complete_application_construction(str(request.get("request_id") or ""), runtime_root=None)
        # The ordinary runtime root is not carried by the prompt helper.  The
        # caller may inject the contract below through the request's transient
        # construction_contract_public field when a non-default runtime root is
        # used.  Default-root operation can load it directly.
        if loaded_construction:
            construction_contract = public_complete_application_construction(loaded_construction)
    except Exception:
        construction_contract = {}
    if isinstance(request.get("construction_contract_public"), Mapping):
        construction_contract = dict(request.get("construction_contract_public") or {})

    payload = {
        "task": (
            "Return only one JSON object describing a bounded isolated implementation. "
            "Use exact replacements for existing files and full content only for new files. "
            "Every replacement old block must occur exactly once in the complete target file; include enough "
            "unchanged neighboring lines to make it unique. Repair the general production behavior described by "
            "the requirements; focused tests are verification evidence, not implementation templates. Do not copy "
            "or special-case prose literals that appear only in focused tests. Prefer the smallest unique replacement "
            "that satisfies the acceptance criteria. Preserve exact indentation, "
            "ensure every resulting Python file parses, and do not modify existing tests. "
            "Do not use markdown, commands, unified diffs, ellipses, or unchanged file content. "
            "On a repair attempt, if previous_outcome contains rejected_candidate_json, correct that exact candidate's "
            "syntax or validation defect instead of independently recreating the same edit."
        ),
        "mode": "initial_implementation" if attempt_number == 1 else "repair_failed_isolated_attempt",
        "authority": {
            "request_id": request.get("request_id"),
            "execution_digest": execution_digest,
            "attempt": attempt_number,
            "selected_project_application_authorized": False,
        },
        "request": {
            "objective": request.get("user_objective"),
            "requirements": request.get("requirements"),
            "acceptance_criteria": request.get("acceptance_criteria"),
            "constraints": request.get("constraints"),
            "prohibited_actions": request.get("prohibited_actions"),
            "assumptions": request.get("assumptions"),
            "ambiguities": request.get("ambiguities"),
        },
        "plan": {
            "project_type": plan.get("project_type"),
            "requirement_file_links": plan.get("requirement_file_links"),
            "verification_plan": plan.get("verification_plan"),
        },
        "workspace_files": files,
        "previous_outcome": dict(previous_outcome or {}),
        "response_schema": {
            "edits": [{
                "path": "relative/posix/path",
                "replacements": [{
                    "old": "exact non-empty UTF-8 block occurring exactly once",
                    "new": "complete replacement block; may be empty",
                }],
            }],
            "creates": [{"path": "relative/posix/path", "content": "complete UTF-8 file content"}],
        },
        "application_construction": construction_contract,
        "limits": {
            "max_files": MAX_CHANGE_FILES,
            "max_file_bytes": MAX_CHANGE_FILE_BYTES,
            "max_total_bytes": MAX_CHANGE_TOTAL_BYTES,
            "workspace_only": True,
            "no_shell_commands": True,
            "no_dependency_installation": True,
            "no_network_authority": True,
            "no_selected_project_application": True,
        },
    }
    prompt = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(prompt.encode("utf-8")) > MAX_PROVIDER_RESPONSE_BYTES:
        raise ValueError("provider_prompt_budget_exceeded")
    return prompt


def _syntax_repair_prompt(
    *,
    root: Path,
    request_id: str,
    execution_digest: str,
    attempt_number: int,
    rejected_candidate_json: str,
) -> str:
    """Build a small transient correction prompt for one rejected candidate."""

    payload = {
        "task": (
            "Correct only the Python syntax defect in rejected_candidate_json. Return one replacement JSON object using "
            "the same edits/creates schema and the same bounded paths. Preserve the intended behavior and exact old blocks, "
            "but repair incomplete expressions, quotes, brackets, indentation, or statement structure in new content. "
            "Check that every complete resulting Python file parses. Do not add files, broaden scope, use markdown, explain "
            "the correction, or return a unified diff."
        ),
        "mode": "syntax_repair",
        "authority": {
            "request_id": request_id,
            "execution_digest": execution_digest,
            "attempt": attempt_number,
            "selected_project_application_authorized": False,
        },
        "rejection": {"code": "syntax_invalid", "candidate_is_transient": True},
        "syntax_diagnostics": _syntax_repair_diagnostics(root, rejected_candidate_json),
        "rejected_candidate_json": rejected_candidate_json,
        "response_schema": {
            "edits": [{
                "path": "same relative path",
                "replacements": [{"old": "same exact old block", "new": "syntax-corrected replacement"}],
            }],
            "creates": [{"path": "same relative path", "content": "syntax-corrected complete content"}],
        },
        "limits": {
            "same_paths_only": True,
            "workspace_only": True,
            "no_commands": True,
            "no_dependency_installation": True,
            "no_selected_project_application": True,
        },
    }
    prompt = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(prompt.encode("utf-8")) > MAX_PROVIDER_RESPONSE_BYTES:
        raise ValueError("syntax_repair_prompt_budget_exceeded")
    return prompt


def _syntax_repair_diagnostics(root: Path, rejected_candidate_json: str) -> list[dict[str, Any]]:
    """Locate syntax failures in a transient compact candidate."""

    try:
        candidate = json.loads(rejected_candidate_json)
    except json.JSONDecodeError as exc:
        raise ValueError("syntax_repair_candidate_invalid") from exc
    if not isinstance(candidate, Mapping):
        raise ValueError("syntax_repair_candidate_invalid")

    diagnostics: list[dict[str, Any]] = []
    candidates: list[tuple[str, str]] = []
    edits = candidate.get("edits") or []
    creates = candidate.get("creates") or []
    if not isinstance(edits, list) or not isinstance(creates, list):
        raise ValueError("syntax_repair_candidate_invalid")

    for edit in edits:
        if not isinstance(edit, Mapping):
            continue
        relative = _safe_relative(str(edit.get("path") or ""))
        path = root / relative
        if not _within(root, path) or not path.is_file() or _is_link_like(path):
            raise ValueError("syntax_repair_path_invalid")
        content = path.read_text(encoding="utf-8")
        replacements = edit.get("replacements") or []
        if not isinstance(replacements, list):
            continue
        for replacement in replacements:
            if not isinstance(replacement, Mapping):
                continue
            old = replacement.get("old")
            new = replacement.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                continue
            if content.count(old) != 1:
                continue
            content = content.replace(old, new, 1)
        candidates.append((relative, content))

    for create in creates:
        if not isinstance(create, Mapping):
            continue
        relative = _safe_relative(str(create.get("path") or ""))
        content = create.get("content")
        if isinstance(content, str):
            candidates.append((relative, content))

    for relative, content in candidates:
        if not relative.casefold().endswith(".py"):
            continue
        try:
            compile(content, relative, "exec")
        except SyntaxError as exc:
            lines = content.splitlines()
            line_number = max(1, int(exc.lineno or 1))
            start = max(1, line_number - 2)
            end = min(len(lines), line_number + 2)
            excerpt = "\n".join(f"{index}: {lines[index - 1]}" for index in range(start, end + 1))
            diagnostics.append({
                "path": relative,
                "line": line_number,
                "column": max(0, int(exc.offset or 0)),
                "message": str(exc.msg or "invalid syntax")[:160],
                "candidate_excerpt": excerpt[:2_000],
            })
            if len(diagnostics) >= 4:
                break
    if not diagnostics:
        raise ValueError("syntax_repair_diagnostics_unavailable")
    return diagnostics


def _duplicate_anchor_contexts(root: Path, rejected_candidate_json: str) -> list[dict[str, Any]]:
    """Return bounded source evidence for ambiguous compact replacements."""

    try:
        candidate = json.loads(rejected_candidate_json)
    except json.JSONDecodeError as exc:
        raise ValueError("anchor_repair_candidate_invalid") from exc
    edits = candidate.get("edits") if isinstance(candidate, Mapping) else None
    if not isinstance(edits, list):
        raise ValueError("anchor_repair_candidate_invalid")
    contexts: list[dict[str, Any]] = []
    remaining = MAX_PROVIDER_CONTEXT_BYTES - len(rejected_candidate_json.encode("utf-8"))
    for edit in edits:
        if not isinstance(edit, Mapping):
            continue
        relative = _safe_relative(str(edit.get("path") or ""))
        path = root / relative
        if not _within(root, path) or not path.is_file() or _is_link_like(path):
            raise ValueError("anchor_repair_path_invalid")
        content = path.read_text(encoding="utf-8")
        replacements = edit.get("replacements")
        if not isinstance(replacements, list):
            continue
        for replacement_index, replacement in enumerate(replacements):
            if not isinstance(replacement, Mapping):
                continue
            old = replacement.get("old")
            if not isinstance(old, str) or not old:
                continue
            positions = [match.start() for match in re.finditer(re.escape(old), content)]
            if len(positions) == 1:
                new = replacement.get("new")
                if isinstance(new, str):
                    content = content.replace(old, new, 1)
                continue
            if len(positions) <= 1:
                continue
            occurrences: list[dict[str, Any]] = []
            for occurrence_index, position in enumerate(positions[:8], start=1):
                line_start = content.rfind("\n", 0, max(0, position - 1))
                for _ in range(3):
                    prior = content.rfind("\n", 0, max(0, line_start))
                    if prior < 0:
                        line_start = 0
                        break
                    line_start = prior
                line_end = position + len(old)
                for _ in range(4):
                    following = content.find("\n", line_end + 1)
                    if following < 0:
                        line_end = len(content)
                        break
                    line_end = following
                excerpt = content[line_start:line_end].strip("\n")
                encoded = excerpt.encode("utf-8")
                if not excerpt or len(encoded) > remaining:
                    continue
                remaining -= len(encoded)
                occurrences.append({"occurrence": occurrence_index, "excerpt": excerpt})
            contexts.append({
                "path": relative,
                "replacement_index": replacement_index,
                "old": old,
                "occurrence_count": len(positions),
                "occurrences": occurrences,
            })
    if not contexts:
        raise ValueError("anchor_repair_context_unavailable")
    return contexts


def _missing_anchor_contexts(root: Path, rejected_candidate_json: str) -> list[dict[str, Any]]:
    """Return nearby source evidence for compact replacements whose old block is absent."""

    candidate = _extract_structured_output(rejected_candidate_json)
    edits = candidate.get("edits") if isinstance(candidate, Mapping) else None
    if not isinstance(edits, list):
        raise ValueError("missing_anchor_candidate_invalid")
    contexts: list[dict[str, Any]] = []
    remaining = max(0, MAX_PROVIDER_CONTEXT_BYTES - len(rejected_candidate_json.encode("utf-8")) - 4_096)
    for edit in edits:
        if not isinstance(edit, Mapping):
            continue
        relative = _safe_relative(str(edit.get("path") or ""))
        path = root / relative
        if not _within(root, path) or not path.is_file() or _is_link_like(path):
            raise ValueError("missing_anchor_path_invalid")
        content = path.read_text(encoding="utf-8")
        replacements = edit.get("replacements")
        if not isinstance(replacements, list):
            continue
        for replacement_index, replacement in enumerate(replacements):
            if not isinstance(replacement, Mapping):
                continue
            old = replacement.get("old")
            new = replacement.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                continue
            occurrence_count = content.count(old)
            if occurrence_count == 1:
                content = content.replace(old, new, 1)
                continue
            if occurrence_count > 1:
                continue
            source_lines = content.splitlines(keepends=True)
            old_lines = [line.strip() for line in old.splitlines() if line.strip()]
            if not source_lines or not old_lines:
                continue
            ranked = sorted(
                (
                    max(difflib.SequenceMatcher(None, target, line.strip()).ratio() for target in old_lines),
                    index,
                )
                for index, line in enumerate(source_lines)
                if line.strip()
            )
            excerpts: list[dict[str, Any]] = []
            occupied: list[tuple[int, int]] = []
            for score, center in reversed(ranked):
                if score < 0.2 or len(excerpts) >= 3:
                    break
                radius = max(4, min(12, len(old_lines) + 3))
                start = max(0, center - radius)
                end = min(len(source_lines), center + radius + 1)
                if any(start < prior_end and end > prior_start for prior_start, prior_end in occupied):
                    continue
                excerpt = "".join(source_lines[start:end])
                size = len(excerpt.encode("utf-8"))
                if not excerpt or size > remaining:
                    continue
                remaining -= size
                occupied.append((start, end))
                excerpts.append({
                    "start_line": start + 1,
                    "end_line": end,
                    "similarity": round(score, 4),
                    "content": excerpt,
                })
            if excerpts:
                contexts.append({
                    "path": relative,
                    "replacement_index": replacement_index,
                    "missing_old": old,
                    "nearby_source": excerpts,
                })
    if not contexts:
        raise ValueError("missing_anchor_context_unavailable")
    return contexts


def _missing_anchor_repair_prompt(
    *,
    root: Path,
    request_id: str,
    execution_digest: str,
    attempt_number: int,
    rejected_candidate_json: str,
) -> str:
    """Ask for source-grounded old-anchor corrections without changing implementation intent."""

    payload = {
        "task": (
            "Correct only missing old replacement anchors in rejected_candidate_json. For every missing anchor, copy "
            "one exact non-empty block from its nearby_source so it occurs exactly once after preceding replacements. "
            "Preserve every path, new block, replacement order, and create exactly. Return only the complete edits/creates "
            "JSON object with no prose, markdown, commands, new files, or unrelated changes."
        ),
        "mode": "replacement_missing_anchor_repair",
        "authority": {
            "request_id": request_id,
            "execution_digest": execution_digest,
            "attempt": attempt_number,
            "selected_project_application_authorized": False,
        },
        "rejection": {"code": "compact_replacement_missing", "candidate_is_transient": True},
        "rejected_candidate_json": rejected_candidate_json,
        "missing_anchor_contexts": _missing_anchor_contexts(root, rejected_candidate_json),
        "limits": {
            "old_anchors_only": True,
            "same_paths_only": True,
            "workspace_only": True,
            "no_commands": True,
            "no_dependency_installation": True,
            "no_selected_project_application": True,
        },
    }
    prompt = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(prompt.encode("utf-8")) > MAX_PROVIDER_CONTEXT_BYTES:
        raise ValueError("missing_anchor_repair_prompt_budget_exceeded")
    return prompt


def _restore_missing_anchor_repair_intent(
    rejected_candidate_json: str,
    repair_raw: str,
    *,
    root: Path | None = None,
) -> str:
    """Accept corrected old anchors while retaining all validated implementation intent."""

    rejected = _extract_structured_output(rejected_candidate_json)
    repaired = _extract_structured_output(repair_raw)
    bound = json.loads(json.dumps(rejected, sort_keys=True, ensure_ascii=True)) if isinstance(rejected, Mapping) else None
    rejected_edits = bound.get("edits") if isinstance(bound, Mapping) else None
    repaired_edits = repaired.get("edits") if isinstance(repaired, Mapping) else None
    if not isinstance(rejected_edits, list) or not isinstance(repaired_edits, list):
        raise ValueError("missing_anchor_candidate_invalid")
    if len(rejected_edits) != len(repaired_edits):
        raise ValueError("missing_anchor_scope_changed")
    if repaired.get("creates") != rejected.get("creates"):
        raise ValueError("missing_anchor_scope_changed")
    for rejected_edit, repaired_edit in zip(rejected_edits, repaired_edits):
        if not isinstance(rejected_edit, Mapping) or not isinstance(repaired_edit, Mapping):
            raise ValueError("missing_anchor_candidate_invalid")
        if _safe_relative(str(repaired_edit.get("path") or "")) != _safe_relative(str(rejected_edit.get("path") or "")):
            raise ValueError("missing_anchor_scope_changed")
        content: str | None = None
        if root is not None:
            relative = _safe_relative(str(rejected_edit.get("path") or ""))
            path = root / relative
            if not _within(root, path) or not path.is_file() or _is_link_like(path):
                raise ValueError("missing_anchor_path_invalid")
            content = path.read_text(encoding="utf-8")
        rejected_replacements = rejected_edit.get("replacements")
        repaired_replacements = repaired_edit.get("replacements")
        if not isinstance(rejected_replacements, list) or not isinstance(repaired_replacements, list):
            raise ValueError("missing_anchor_candidate_invalid")
        if len(rejected_replacements) != len(repaired_replacements):
            raise ValueError("missing_anchor_scope_changed")
        for rejected_replacement, repaired_replacement in zip(rejected_replacements, repaired_replacements):
            if not isinstance(rejected_replacement, Mapping) or not isinstance(repaired_replacement, Mapping):
                raise ValueError("missing_anchor_candidate_invalid")
            repaired_old = repaired_replacement.get("old")
            if not isinstance(repaired_old, str) or not repaired_old:
                raise ValueError("missing_anchor_candidate_invalid")
            if repaired_replacement.get("new") != rejected_replacement.get("new"):
                raise ValueError("missing_anchor_intent_changed")
            rejected_old = rejected_replacement.get("old")
            rejected_new = rejected_replacement.get("new")
            if not isinstance(rejected_old, str) or not rejected_old or not isinstance(rejected_new, str):
                raise ValueError("missing_anchor_candidate_invalid")
            if content is None or content.count(rejected_old) == 0:
                rejected_replacement["old"] = repaired_old
                selected_old = repaired_old
            else:
                selected_old = rejected_old
            rejected_replacement.pop("occurrence", None)
            if content is not None and content.count(selected_old) == 1:
                content = content.replace(selected_old, rejected_new, 1)
    return json.dumps(bound, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _anchor_repair_prompt(
    *,
    root: Path,
    request_id: str,
    execution_digest: str,
    attempt_number: int,
    rejected_candidate_json: str,
) -> str:
    """Build a transient prompt that disambiguates duplicate exact anchors."""

    payload = {
        "task": (
            "Correct only duplicate exact replacement anchors in rejected_candidate_json. Preserve every path, create, "
            "and intended new block. For each ambiguous replacement, choose the intended occurrence from "
            "duplicate_anchor_contexts and add its one-based occurrence number to that replacement. The runtime will "
            "expand the selected occurrence deterministically; do not copy or invent neighboring source. Return one "
            "replacement JSON object with no prose, markdown, commands, "
            "new files, scope expansion, or unrelated edits."
        ),
        "mode": "replacement_anchor_repair",
        "authority": {
            "request_id": request_id,
            "execution_digest": execution_digest,
            "attempt": attempt_number,
            "selected_project_application_authorized": False,
        },
        "rejection": {"code": "compact_replacement_not_unique", "candidate_is_transient": True},
        "rejected_candidate_json": rejected_candidate_json,
        "duplicate_anchor_contexts": _duplicate_anchor_contexts(root, rejected_candidate_json),
        "response_schema": {
            "edits": [{
                "path": "same relative path",
                "replacements": [{"old": "same ambiguous old block", "new": "same intended new block", "occurrence": 1}],
            }],
            "creates": [{"path": "same relative path", "content": "unchanged candidate content"}],
        },
        "limits": {
            "same_paths_only": True,
            "workspace_only": True,
            "no_commands": True,
            "no_dependency_installation": True,
            "no_selected_project_application": True,
        },
    }
    prompt = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(prompt.encode("utf-8")) > MAX_PROVIDER_CONTEXT_BYTES:
        raise ValueError("anchor_repair_prompt_budget_exceeded")
    return prompt


def _materialize_anchor_repair_response(root: Path, raw: str) -> str:
    """Turn provider-selected duplicate occurrences into unique exact blocks."""

    data = _extract_structured_output(raw)
    edits = data.get("edits") if isinstance(data, Mapping) else None
    if not isinstance(edits, list):
        raise ValueError("anchor_repair_candidate_invalid")
    materialized = False
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        relative = _safe_relative(str(edit.get("path") or ""))
        path = root / relative
        if not _within(root, path) or not path.is_file() or _is_link_like(path):
            raise ValueError("anchor_repair_path_invalid")
        content = path.read_text(encoding="utf-8")
        replacements = edit.get("replacements")
        if not isinstance(replacements, list):
            continue
        for replacement in replacements:
            if not isinstance(replacement, dict):
                continue
            old = replacement.get("old")
            new = replacement.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                continue
            positions = [match.start() for match in re.finditer(re.escape(old), content)]
            if len(positions) == 1:
                replacement.pop("occurrence", None)
                content = content.replace(old, new, 1)
                continue
            occurrence = replacement.get("occurrence")
            if len(positions) < 2 or not isinstance(occurrence, int) or isinstance(occurrence, bool):
                raise ValueError("anchor_repair_occurrence_required")
            if occurrence < 1 or occurrence > min(len(positions), 8):
                raise ValueError("anchor_repair_occurrence_invalid")
            position = positions[occurrence - 1]
            start = content.rfind("\n", 0, position) + 1
            following = content.find("\n", position + len(old))
            end = len(content) if following < 0 else following + 1
            while content.count(content[start:end]) != 1:
                previous = content.rfind("\n", 0, max(0, start - 1))
                start = 0 if previous < 0 else previous + 1
                following = content.find("\n", end)
                end = len(content) if following < 0 else following + 1
                if start == 0 and end == len(content):
                    break
            expanded_old = content[start:end]
            if not expanded_old or content.count(expanded_old) != 1:
                raise ValueError("anchor_repair_unique_context_unavailable")
            if len(expanded_old.encode("utf-8")) > MAX_PROVIDER_FILE_EXCERPT_BYTES:
                raise ValueError("anchor_repair_unique_context_budget_exceeded")
            prefix = content[start:position]
            suffix = content[position + len(old):end]
            expanded_new = prefix + new + suffix
            replacement["old"] = expanded_old
            replacement["new"] = expanded_new
            replacement.pop("occurrence", None)
            content = content.replace(expanded_old, expanded_new, 1)
            materialized = True
    if not materialized:
        raise ValueError("anchor_repair_occurrence_unavailable")
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _restore_rejected_candidate_anchors(rejected_candidate_json: str, repair_raw: str) -> str:
    """Bind only provider occurrence choices onto the validated rejected candidate."""

    rejected = _extract_structured_output(rejected_candidate_json)
    repaired = _extract_structured_output(repair_raw)
    bound = json.loads(json.dumps(rejected, sort_keys=True, ensure_ascii=True)) if isinstance(rejected, Mapping) else None
    rejected_edits = bound.get("edits") if isinstance(bound, Mapping) else None
    repaired_edits = repaired.get("edits") if isinstance(repaired, Mapping) else None
    if not isinstance(rejected_edits, list) or not isinstance(repaired_edits, list):
        raise ValueError("anchor_repair_candidate_invalid")
    if len(rejected_edits) != len(repaired_edits):
        raise ValueError("anchor_repair_scope_changed")
    for rejected_edit, repaired_edit in zip(rejected_edits, repaired_edits):
        if not isinstance(rejected_edit, Mapping) or not isinstance(repaired_edit, dict):
            raise ValueError("anchor_repair_candidate_invalid")
        rejected_path = _safe_relative(str(rejected_edit.get("path") or ""))
        repaired_path = _safe_relative(str(repaired_edit.get("path") or ""))
        if repaired_path != rejected_path:
            raise ValueError("anchor_repair_scope_changed")
        rejected_replacements = rejected_edit.get("replacements")
        repaired_replacements = repaired_edit.get("replacements")
        if not isinstance(rejected_replacements, list) or not isinstance(repaired_replacements, list):
            raise ValueError("anchor_repair_candidate_invalid")
        if len(rejected_replacements) != len(repaired_replacements):
            raise ValueError("anchor_repair_scope_changed")
        for rejected_replacement, repaired_replacement in zip(rejected_replacements, repaired_replacements):
            if not isinstance(rejected_replacement, Mapping) or not isinstance(repaired_replacement, dict):
                raise ValueError("anchor_repair_candidate_invalid")
            old = rejected_replacement.get("old")
            new = rejected_replacement.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                raise ValueError("anchor_repair_candidate_invalid")
            occurrence = repaired_replacement.get("occurrence")
            if isinstance(occurrence, int) and not isinstance(occurrence, bool):
                rejected_replacement["occurrence"] = occurrence
            else:
                rejected_replacement.pop("occurrence", None)
    return json.dumps(bound, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _anchor_occurrence_selection_prompt(
    *,
    root: Path,
    request_id: str,
    execution_digest: str,
    attempt_number: int,
    rejected_candidate_json: str,
) -> str:
    """Request only the missing duplicate-anchor occurrence choices."""

    contexts = _duplicate_anchor_contexts(root, rejected_candidate_json)
    payload = {
        "task": (
            "Select the intended one-based occurrence for every ambiguous replacement. Return only the selections "
            "JSON object. Do not rewrite code, paths, old blocks, new blocks, or create files."
        ),
        "mode": "replacement_anchor_occurrence_selection",
        "authority": {
            "request_id": request_id,
            "execution_digest": execution_digest,
            "attempt": attempt_number,
            "selected_project_application_authorized": False,
        },
        "duplicate_anchor_contexts": contexts,
        "response_schema": {
            "selections": [{
                "path": "same relative path",
                "replacement_index": 0,
                "occurrence": 1,
            }],
        },
        "limits": {
            "selection_only": True,
            "same_paths_only": True,
            "workspace_only": True,
            "no_commands": True,
            "no_selected_project_application": True,
        },
    }
    prompt = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(prompt.encode("utf-8")) > MAX_PROVIDER_CONTEXT_BYTES:
        raise ValueError("anchor_occurrence_selection_prompt_budget_exceeded")
    return prompt


def _materialize_anchor_occurrence_selection(root: Path, candidate_raw: str, selection_raw: str) -> str:
    """Bind a selection-only response to the transient repair candidate."""

    candidate = _extract_structured_output(candidate_raw)
    selected = _extract_structured_output(selection_raw)
    edits = candidate.get("edits") if isinstance(candidate, Mapping) else None
    selections = selected.get("selections") if isinstance(selected, Mapping) else None
    if not isinstance(edits, list) or not isinstance(selections, list):
        raise ValueError("anchor_occurrence_selection_invalid")
    by_key: dict[tuple[str, int], int] = {}
    for row in selections:
        if not isinstance(row, Mapping):
            raise ValueError("anchor_occurrence_selection_invalid")
        relative = _safe_relative(str(row.get("path") or ""))
        replacement_index = row.get("replacement_index")
        occurrence = row.get("occurrence")
        if (
            not isinstance(replacement_index, int)
            or isinstance(replacement_index, bool)
            or replacement_index < 0
            or not isinstance(occurrence, int)
            or isinstance(occurrence, bool)
        ):
            raise ValueError("anchor_occurrence_selection_invalid")
        key = (relative, replacement_index)
        if key in by_key:
            raise ValueError("anchor_occurrence_selection_duplicate")
        by_key[key] = occurrence
    required: set[tuple[str, int]] = set()
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        relative = _safe_relative(str(edit.get("path") or ""))
        path = root / relative
        if not _within(root, path) or not path.is_file() or _is_link_like(path):
            raise ValueError("anchor_repair_path_invalid")
        content = path.read_text(encoding="utf-8")
        replacements = edit.get("replacements")
        if not isinstance(replacements, list):
            continue
        for replacement_index, replacement in enumerate(replacements):
            if not isinstance(replacement, dict):
                continue
            old = replacement.get("old")
            new = replacement.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                continue
            occurrence_count = content.count(old)
            if occurrence_count == 1:
                content = content.replace(old, new, 1)
                continue
            if occurrence_count < 2:
                continue
            key = (relative, replacement_index)
            required.add(key)
            if key not in by_key:
                raise ValueError("anchor_repair_occurrence_required")
            replacement["occurrence"] = by_key[key]
    if not required or set(by_key) != required:
        raise ValueError("anchor_occurrence_selection_scope_invalid")
    return _materialize_anchor_repair_response(
        root,
        json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
    )


def _configured_coding_generate(prompt: str) -> str:
    """Use the configured provider/model with a coding-sized request envelope."""

    from local_model import LocalModelClient, LocalModelConfig

    configured = LocalModelConfig.from_settings()
    generation = replace(
        configured.generation,
        max_tokens=max(configured.generation.max_tokens, CODING_MAX_TOKENS),
        temperature=min(configured.generation.temperature, 0.2),
    )
    coding_config = replace(
        configured,
        context_size=max(configured.context_size, CODING_CONTEXT_SIZE),
        read_timeout_seconds=max(configured.read_timeout_seconds, CODING_READ_TIMEOUT_SECONDS),
        structured_json=True,
        generation=generation,
    )
    with LocalModelClient(coding_config) as client:
        return client.generate(prompt)


def _safe_generation_rejection_code(error: Exception) -> str:
    value = str(error or "").strip()
    if re.fullmatch(r"[a-z0-9_]{1,80}", value):
        return value
    prefix = value.split(":", 1)[0]
    if re.fullmatch(r"[a-z0-9_]{1,80}", prefix):
        return prefix
    return "structured_output_invalid"


def _generation_repair_guidance(code: str) -> str:
    guidance = {
        "compact_replacement_not_unique": (
            "The prior old block matched more than once. Expand it with exact unchanged neighboring lines until it occurs once."
        ),
        "compact_replacement_missing": "Copy the old block exactly from the supplied source excerpt, including indentation.",
        "syntax_invalid": "Return a smaller replacement and verify the complete resulting Python file parses.",
        "existing_project_test_change_rejected": "Do not edit an existing test; create only the requested new regression fixture.",
        "provider_output_not_json": "Return only the response-schema JSON object with no prose or markdown.",
        "test_fixture_literal_leakage": (
            "Do not special-case text copied from a focused test. Repair the general production condition instead."
        ),
    }
    return guidance.get(str(code or ""), "Correct the prior validation failure while preserving the same bounded scope.")


def _capture_before(root: Path, relative: str, operation: str) -> dict[str, Any]:
    path = root / relative
    if not _within(root, path) or _is_link_like(path):
        raise ValueError("change_path_boundary_rejected")
    exists = path.exists()
    if operation == "create" and exists:
        raise ValueError("create_target_already_exists")
    if operation in {"modify", "delete"} and (not path.is_file() or _is_link_like(path)):
        raise ValueError("change_target_missing_or_link")
    if not exists:
        return {"before_exists": False, "before_content_digest": "", "before_content": ""}
    content = path.read_text(encoding="utf-8")
    return {
        "before_exists": True,
        # Conflict checks compare the actual workspace bytes. Text-mode reads
        # normalize CRLF on Windows, so hashing the decoded text creates false
        # drift even when the file is untouched.
        "before_content_digest": _file_digest(path),
        "before_content": content,
    }


def _is_project_test_path(relative: str) -> bool:
    pure = PurePosixPath(relative)
    name = pure.name.casefold()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith("_tests.py")
        or name.endswith(".test.js")
        or name.endswith(".spec.js")
        or any(part.casefold() in {"test", "tests", "__tests__"} for part in pure.parts[:-1])
    )


def _validated_change_row(
    root: Path,
    *,
    relative: str,
    operation: str,
    content: str,
    before: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    size = len(content.encode("utf-8"))
    if size > MAX_CHANGE_FILE_BYTES:
        raise ValueError("change_content_budget_exceeded")
    captured = dict(before or _capture_before(root, relative, operation))
    if captured.get("before_exists") and _is_project_test_path(relative) and operation in {"modify", "delete"}:
        raise ValueError("existing_project_test_change_rejected")
    syntax = "deleted" if operation == "delete" else _validate_syntax(relative, content)
    return {
        "relative_path": relative,
        "relative_path_digest": _path_digest(relative),
        "operation": operation,
        "content": content,
        "content_digest": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "size_bytes": size,
        "syntax": syntax,
        **captured,
    }


def _validate_compact_changes(data: Mapping[str, Any], *, root: Path) -> list[dict[str, Any]]:
    edits = data.get("edits") or []
    creates = data.get("creates") or []
    if not isinstance(edits, list) or not isinstance(creates, list) or not edits and not creates:
        raise ValueError("compact_change_contract_invalid")
    if len(edits) + len(creates) > MAX_CHANGE_FILES:
        raise ValueError("change_file_count_rejected")
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    total = 0

    for raw_row in edits:
        if not isinstance(raw_row, Mapping):
            raise ValueError("compact_edit_entry_invalid")
        relative = _safe_relative(str(raw_row.get("path") or ""))
        folded = relative.casefold()
        if folded in seen:
            raise ValueError("duplicate_change_path")
        seen.add(folded)
        if not _is_relevant_source(PurePosixPath(relative)):
            raise ValueError("change_path_not_source_relevant")
        before = _capture_before(root, relative, "modify")
        if _is_project_test_path(relative):
            raise ValueError("existing_project_test_change_rejected")
        replacements = raw_row.get("replacements")
        if not isinstance(replacements, list) or not replacements or len(replacements) > 32:
            raise ValueError("compact_replacement_count_rejected")
        content = str(before.get("before_content") or "")
        for replacement in replacements:
            if not isinstance(replacement, Mapping):
                raise ValueError("compact_replacement_invalid")
            old = replacement.get("old")
            new = replacement.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                raise ValueError("compact_replacement_content_invalid")
            occurrence_count = content.count(old)
            if occurrence_count == 0:
                raise ValueError("compact_replacement_missing")
            if occurrence_count > 1:
                raise ValueError("compact_replacement_not_unique")
            content = content.replace(old, new, 1)
        if content == before.get("before_content"):
            raise ValueError("compact_replacement_no_change")
        row = _validated_change_row(root, relative=relative, operation="modify", content=content, before=before)
        total += int(row["size_bytes"])
        if total > MAX_CHANGE_TOTAL_BYTES:
            raise ValueError("change_content_budget_exceeded")
        validated.append(row)

    for raw_row in creates:
        if not isinstance(raw_row, Mapping):
            raise ValueError("compact_create_entry_invalid")
        relative = _safe_relative(str(raw_row.get("path") or ""))
        folded = relative.casefold()
        if folded in seen:
            raise ValueError("duplicate_change_path")
        seen.add(folded)
        if not _is_relevant_source(PurePosixPath(relative)):
            raise ValueError("change_path_not_source_relevant")
        content = raw_row.get("content")
        if not isinstance(content, str) or not content:
            raise ValueError("compact_create_content_invalid")
        row = _validated_change_row(root, relative=relative, operation="create", content=content)
        total += int(row["size_bytes"])
        if total > MAX_CHANGE_TOTAL_BYTES:
            raise ValueError("change_content_budget_exceeded")
        validated.append(row)
    return validated


def _validate_generation(
    raw: str,
    *,
    request_id: str,
    execution_digest: str,
    attempt_number: int,
    root: Path,
    test_paths: Sequence[str] = (),
) -> list[dict[str, Any]]:
    if len(str(raw).encode("utf-8")) > MAX_PROVIDER_RESPONSE_BYTES:
        raise ValueError("provider_output_too_large")
    data = _extract_structured_output(raw)
    # This trusted call site already binds generation to the exact request,
    # digest, and attempt. The model supplies edits, not authority. If it
    # volunteers an authority object, it must still match exactly.
    authority = data.get("authority")
    if authority is not None:
        if not isinstance(authority, Mapping) or (
            authority.get("request_id") != request_id
            or authority.get("execution_digest") != execution_digest
            or int(authority.get("attempt") or 0) != int(attempt_number)
        ):
            raise ValueError("execution_authority_binding_rejected")
    if "edits" in data or "creates" in data:
        validated = _validate_compact_changes(data, root=root)
        _reject_test_fixture_literal_leakage(root, validated, test_paths)
        return validated
    files = data.get("files")
    if not isinstance(files, list) or not files or len(files) > MAX_CHANGE_FILES:
        raise ValueError("change_file_count_rejected")
    seen: set[str] = set()
    total = 0
    validated: list[dict[str, Any]] = []
    for raw_row in files:
        if not isinstance(raw_row, Mapping):
            raise ValueError("change_entry_invalid")
        relative = _safe_relative(str(raw_row.get("path") or ""))
        folded = relative.casefold()
        if folded in seen:
            raise ValueError("duplicate_change_path")
        seen.add(folded)
        pure = PurePosixPath(relative)
        if not _is_relevant_source(pure):
            raise ValueError("change_path_not_source_relevant")
        operation = str(raw_row.get("operation") or "")
        if operation not in {"create", "modify", "delete"}:
            raise ValueError("change_operation_rejected")
        content = raw_row.get("content", "")
        if not isinstance(content, str) or (operation == "delete" and content):
            raise ValueError("change_content_contract_invalid")
        before = _capture_before(root, relative, operation)
        row = _validated_change_row(root, relative=relative, operation=operation, content=content, before=before)
        total += int(row["size_bytes"])
        if total > MAX_CHANGE_TOTAL_BYTES:
            raise ValueError("change_content_budget_exceeded")
        validated.append(row)
    _reject_test_fixture_literal_leakage(root, validated, test_paths)
    return validated


def _python_string_literals(content: str) -> set[str]:
    try:
        import ast
        tree = ast.parse(content)
    except (SyntaxError, ValueError, TypeError):
        return set()
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _reject_test_fixture_literal_leakage(
    root: Path,
    changes: Sequence[Mapping[str, Any]],
    test_paths: Sequence[str],
) -> None:
    test_literals: set[str] = set()
    for value in test_paths:
        try:
            relative = _safe_relative(str(value or ""))
            if not _is_project_test_path(relative):
                continue
            path = root / relative
            if _within(root, path) and path.is_file() and not _is_link_like(path):
                test_literals.update(_python_string_literals(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, ValueError):
            continue
    suspicious = {
        literal
        for literal in test_literals
        if len(literal) >= 20 and len(literal.split()) >= 3
    }
    if not suspicious:
        return
    for row in changes:
        relative = str(row.get("relative_path") or "")
        if not relative.endswith(".py") or _is_project_test_path(relative):
            continue
        before = _python_string_literals(str(row.get("before_content") or ""))
        after = _python_string_literals(str(row.get("content") or ""))
        if (after - before) & suspicious:
            raise ValueError("test_fixture_literal_leakage")


def _preflight_change(root: Path, row: Mapping[str, Any]) -> str:
    relative = _safe_relative(str(row.get("relative_path") or ""))
    operation = str(row.get("operation") or "")
    path = root / relative
    if not _within(root, path) or _is_link_like(path):
        raise ValueError("workspace_change_boundary_rejected")
    expected_before = str(row.get("before_content_digest") or "")
    expected_after = str(row.get("content_digest") or "")
    exists = path.exists()
    current = _file_digest(path) if exists and path.is_file() and not _is_link_like(path) else ""
    if operation == "create":
        if exists and current == expected_after:
            return "already_applied"
        if exists:
            raise ValueError("workspace_create_conflict")
        return "pending"
    if operation == "modify":
        if exists and current == expected_after:
            return "already_applied"
        if not exists or current != expected_before:
            raise ValueError("workspace_modify_conflict")
        return "pending"
    if operation == "delete":
        if not exists:
            return "already_applied"
        if current != expected_before:
            raise ValueError("workspace_delete_conflict")
        return "pending"
    raise ValueError("workspace_change_operation_invalid")


def _apply_one(root: Path, row: Mapping[str, Any]) -> str:
    relative = _safe_relative(str(row.get("relative_path") or ""))
    operation = str(row.get("operation") or "")
    path = root / relative
    state = _preflight_change(root, row)
    if state == "already_applied":
        return state
    expected_after = str(row.get("content_digest") or "")

    if operation == "delete":
        path.unlink()
        return "applied"
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    cursor = parent
    while cursor != root:
        if _is_link_like(cursor) or not _within(root, cursor):
            raise ValueError("workspace_parent_boundary_rejected")
        cursor = cursor.parent
    tmp = path.with_name(path.name + ".eidolon-tmp-" + uuid.uuid4().hex)
    tmp.write_text(str(row.get("content") or ""), encoding="utf-8", newline="")
    os.replace(tmp, path)
    if _file_digest(path) != expected_after:
        raise ValueError("workspace_write_verification_failed")
    return "applied"


def _attempt_record(
    *,
    request_id: str,
    execution_digest: str,
    attempt_number: int,
    prompt_digest: str,
    provider_raw_digest: str,
    changes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "isolated_coding_generation_validated",
        "request_id": request_id,
        "execution_digest": execution_digest,
        "attempt_number": int(attempt_number),
        "prompt_digest": prompt_digest,
        "provider_raw_digest": provider_raw_digest,
        "provider_contacted": True,
        "changes": [dict(change) for change in changes],
        "change_count": len(changes),
        "change_manifest_digest": _digest([
            {key: change.get(key) for key in ("relative_path_digest", "operation", "content_digest", "before_content_digest")}
            for change in changes
        ]),
        "workspace_apply_state": "pending",
        "verification": {},
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "release_authorized": False,
        "independent_authority_granted": False,
    }
    return _seal(row, "attempt_record_digest")


def _load_or_generate_attempt(
    *,
    request: Mapping[str, Any],
    plan: Mapping[str, Any],
    inspection: Mapping[str, Any],
    root: Path,
    execution_digest: str,
    attempt_number: int,
    previous_outcome: Mapping[str, Any] | None,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None,
) -> dict[str, Any]:
    path = _attempt_path(str(request.get("request_id") or ""), attempt_number, runtime_root)
    existing = _read_json(path)
    if existing:
        if not _valid(existing, "attempt_record_digest"):
            return _failure("isolated_coding_attempt_record_invalid", request_id=str(request.get("request_id") or ""))
        if str(existing.get("execution_digest") or "") != execution_digest:
            return _failure("isolated_coding_attempt_binding_changed", request_id=str(request.get("request_id") or ""))
        return {**existing, "operation_status": "restored"}

    if provider_generate is None:
        provider_generate = _configured_coding_generate
    try:
        rejected_candidate_json = str((previous_outcome or {}).get("rejected_candidate_json") or "")
        rejection_code = str((previous_outcome or {}).get("generation_rejection_code") or "")
        if (
            attempt_number > 1
            and rejection_code == "syntax_invalid"
            and rejected_candidate_json
        ):
            prompt = _syntax_repair_prompt(
                root=root,
                request_id=str(request.get("request_id") or ""),
                execution_digest=execution_digest,
                attempt_number=attempt_number,
                rejected_candidate_json=rejected_candidate_json,
            )
        elif attempt_number > 1 and rejection_code == "compact_replacement_missing" and rejected_candidate_json:
            prompt = _missing_anchor_repair_prompt(
                root=root,
                request_id=str(request.get("request_id") or ""),
                execution_digest=execution_digest,
                attempt_number=attempt_number,
                rejected_candidate_json=rejected_candidate_json,
            )
        elif attempt_number > 1 and rejection_code == "compact_replacement_not_unique" and rejected_candidate_json:
            try:
                prompt = _anchor_repair_prompt(
                    root=root,
                    request_id=str(request.get("request_id") or ""),
                    execution_digest=execution_digest,
                    attempt_number=attempt_number,
                    rejected_candidate_json=rejected_candidate_json,
                )
            except ValueError as exc:
                if str(exc) != "anchor_repair_context_unavailable":
                    raise
                prompt = _provider_prompt(
                    request=request,
                    plan=plan,
                    inspection=inspection,
                    root=root,
                    execution_digest=execution_digest,
                    attempt_number=attempt_number,
                    previous_outcome=previous_outcome,
                )
        elif attempt_number > 1 and rejection_code == "anchor_repair_occurrence_required" and rejected_candidate_json:
            prompt = _anchor_occurrence_selection_prompt(
                root=root,
                request_id=str(request.get("request_id") or ""),
                execution_digest=execution_digest,
                attempt_number=attempt_number,
                rejected_candidate_json=rejected_candidate_json,
            )
        else:
            prompt = _provider_prompt(
                request=request,
                plan=plan,
                inspection=inspection,
                root=root,
                execution_digest=execution_digest,
                attempt_number=attempt_number,
                previous_outcome=previous_outcome,
            )
    except ValueError as exc:
        context_code = str(exc) if re.fullmatch(r"[a-z0-9_]{1,80}", str(exc)) else "provider_context_invalid"
        return {
            **_failure(
                "isolated_coding_provider_context_rejected",
                request_id=str(request.get("request_id") or ""),
                reason=context_code,
            ),
            "provider_contacted": False,
            "provider_context_rejection_code": context_code,
        }
    prompt_digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    try:
        raw = provider_generate(prompt)
    except Exception as exc:
        return {
            **_failure(
                "isolated_coding_provider_failed",
                request_id=str(request.get("request_id") or ""),
                reason=_digest({"type": type(exc).__name__}),
            ),
            "provider_contacted": True,
            "provider_failure_class": type(exc).__name__[:80],
        }
    if attempt_number > 1 and rejection_code == "compact_replacement_missing":
        try:
            raw = _restore_missing_anchor_repair_intent(rejected_candidate_json, str(raw), root=root)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            repaired_code = _safe_generation_rejection_code(exc)
            return {
                **_failure(
                    "isolated_coding_generation_rejected",
                    request_id=str(request.get("request_id") or ""),
                    reason=_digest({"rejection_code": repaired_code}),
                ),
                "provider_contacted": True,
                "generation_rejection_code": repaired_code,
            }
    elif attempt_number > 1 and rejection_code == "compact_replacement_not_unique":
        try:
            raw = _restore_rejected_candidate_anchors(rejected_candidate_json, str(raw))
            raw = _materialize_anchor_repair_response(root, str(raw))
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            repaired_code = _safe_generation_rejection_code(exc)
            return {
                **_failure(
                    "isolated_coding_generation_rejected",
                    request_id=str(request.get("request_id") or ""),
                    reason=_digest({"rejection_code": repaired_code}),
                ),
                "provider_contacted": True,
                "generation_rejection_code": repaired_code,
                "transient_repair_candidate": (
                    str(raw)
                    if repaired_code == "anchor_repair_occurrence_required"
                    and len(str(raw).encode("utf-8")) <= MAX_TRANSIENT_REPAIR_CANDIDATE_BYTES
                    else ""
                ),
            }
    elif attempt_number > 1 and rejection_code == "anchor_repair_occurrence_required":
        try:
            raw = _materialize_anchor_occurrence_selection(
                root,
                rejected_candidate_json,
                str(raw),
            )
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            repaired_code = _safe_generation_rejection_code(exc)
            return {
                **_failure(
                    "isolated_coding_generation_rejected",
                    request_id=str(request.get("request_id") or ""),
                    reason=_digest({"rejection_code": repaired_code}),
                ),
                "provider_contacted": True,
                "generation_rejection_code": repaired_code,
            }
    try:
        changes = _validate_generation(
            str(raw),
            request_id=str(request.get("request_id") or ""),
            execution_digest=execution_digest,
            attempt_number=attempt_number,
            root=root,
            test_paths=[
                str(value or "")
                for value in plan.get("verification_plan") or []
                if _is_project_test_path(str(value or ""))
            ],
        )
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        rejection_code = _safe_generation_rejection_code(exc)
        transient_repair_candidate = ""
        if rejection_code in {
            "syntax_invalid",
            "compact_replacement_missing",
            "compact_replacement_not_unique",
        }:
            candidate = str(raw)
            if len(candidate.encode("utf-8")) <= MAX_TRANSIENT_REPAIR_CANDIDATE_BYTES:
                transient_repair_candidate = candidate
        return {
            **_failure(
                "isolated_coding_generation_rejected",
                request_id=str(request.get("request_id") or ""),
                reason=_digest({"rejection_code": rejection_code}),
            ),
            "provider_contacted": True,
            "generation_rejection_code": rejection_code,
            # This value exists only in the in-memory attempt result. It is
            # supplied back to the same provider on the next bounded attempt
            # and is never written to an attempt, execution, or public record.
            "transient_repair_candidate": transient_repair_candidate,
        }
    record = _attempt_record(
        request_id=str(request.get("request_id") or ""),
        execution_digest=execution_digest,
        attempt_number=attempt_number,
        prompt_digest=prompt_digest,
        provider_raw_digest=hashlib.sha256(str(raw).encode("utf-8")).hexdigest(),
        changes=changes,
    )
    _atomic_json(path, record)
    return {**record, "operation_status": "created"}


def _apply_attempt(record: Mapping[str, Any], *, runtime_root=None) -> dict[str, Any]:
    request_id = str(record.get("request_id") or "")
    workspace = _read_json(_store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json")
    if not workspace:
        return _failure("isolated_coding_workspace_record_missing", request_id=request_id)
    try:
        root = _workspace_root_from_record(workspace)
        integrity_ok, integrity_status = _strict_workspace_integrity(root)
        if not integrity_ok:
            raise ValueError(integrity_status)
        changes = list(record.get("changes") or [])
        preflight = [_preflight_change(root, row) for row in changes]
        outcomes = [state if state == "already_applied" else _apply_one(root, row) for state, row in zip(preflight, changes)]
        integrity_ok, integrity_status = _strict_workspace_integrity(root)
        if not integrity_ok:
            raise ValueError(integrity_status)
        files, _ = _walk_project(root)
    except (OSError, UnicodeError, ValueError) as exc:
        return _failure("isolated_coding_workspace_apply_blocked", request_id=request_id, reason=str(exc))
    updated = dict(record)
    updated.update({
        "status": "isolated_coding_workspace_changes_ready",
        "workspace_apply_state": "applied",
        "change_apply_outcomes": outcomes,
        "workspace_manifest_digest_after_apply": _manifest_digest(files),
        "workspace_file_count_after_apply": len(files),
    })
    updated = _seal(updated, "attempt_record_digest")
    _atomic_json(_attempt_path(request_id, int(record.get("attempt_number") or 0), runtime_root), updated)
    return updated


def _verification_private_root(request_id: str, attempt_number: int, runtime_root=None) -> Path:
    root = _store_root(runtime_root) / "isolated_coding_test_private" / request_id / f"attempt-{int(attempt_number)}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run_python_verification(
    root: Path,
    files: Sequence[Mapping[str, Any]],
    *,
    request_id: str,
    attempt_number: int,
    runtime_root=None,
    python_executable: str | None = None,
) -> dict[str, Any]:
    from python_test_adapter import (
        SYNTAX_TIMEOUT_SECONDS,
        TEST_TIMEOUT_SECONDS,
        PYTHON_PROBE_TIMEOUT_SECONDS,
        _capability_contract_ok,
        _minimal_environment,
        _preferred_runner,
        _python_candidates,
        _read_workspace_sources,
        _runner_source,
        _select_python,
    )
    from node_javascript_test_adapter import _run_bounded_command

    rows, failure = _read_workspace_sources(root, {"files": list(files)})
    if rows is None:
        return {"passed": False, "status": str(failure.get("status") or "python_verification_rejected"), "tests_executed": False, "cleanup_confirmed": True}
    py_rows = [row for row in rows if str(row.get("relative_path") or "").endswith(".py")]
    tests = [row for row in py_rows if row.get("is_test")]
    expected_tests = [row for row in py_rows if _is_project_test_path(str(row.get("relative_path") or ""))]
    if expected_tests and len(tests) != len(expected_tests):
        return {
            "passed": False,
            "status": "python_test_classification_mismatch",
            "tests_executed": False,
            "cleanup_confirmed": True,
            "test_file_count": len(tests),
            "expected_test_file_count": len(expected_tests),
        }
    contract_ok, rejected_digest = _capability_contract_ok(py_rows)
    if not contract_ok:
        return {"passed": False, "status": "python_test_capability_contract_rejected", "tests_executed": False, "cleanup_confirmed": True, "rejected_path_digest": rejected_digest}
    private = _verification_private_root(request_id, attempt_number, runtime_root)
    python, source_class, failures, launch_attempts, cleanup = _select_python(_python_candidates(python_executable), cwd=root, private=private)
    if not python:
        return {"passed": False, "status": "python_runtime_unavailable", "tests_executed": False, "cleanup_confirmed": cleanup, "runtime_source_class": "none", "launch_attempt_count": launch_attempts, "launch_failure_digests": failures}
    env = _minimal_environment(python, private)
    command_results: list[dict[str, Any]] = []
    syntax_source = "import ast,pathlib,sys;ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))"
    for row in py_rows:
        command = _run_bounded_command([python, "-I", "-B", "-c", syntax_source, str(row["path"])], cwd=root, env=env, timeout_seconds=SYNTAX_TIMEOUT_SECONDS)
        cleanup = cleanup and bool(command.get("cleanup_confirmed"))
        command_results.append({"phase": "syntax", "path_digest": str(row.get("relative_path_digest") or ""), **command})
        if command.get("passed") is not True:
            return {"passed": False, "status": "python_syntax_failed", "tests_executed": True, "cleanup_confirmed": cleanup, "runtime_source_class": source_class, "command_results": command_results, "test_file_count": len(tests)}
    if not tests:
        return {"passed": True, "status": "python_syntax_verification_passed_no_tests", "tests_executed": True, "cleanup_confirmed": cleanup, "runtime_source_class": source_class, "command_results": command_results, "test_file_count": 0}
    runner = _preferred_runner(rows)
    if runner == "pytest":
        probe = _run_bounded_command([python, "-I", "-B", "-c", "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('pytest') else 1)"], cwd=root, env=env, timeout_seconds=PYTHON_PROBE_TIMEOUT_SECONDS)
        cleanup = cleanup and bool(probe.get("cleanup_confirmed"))
        if probe.get("passed") is not True:
            return {"passed": False, "status": "python_pytest_unavailable", "tests_executed": True, "cleanup_confirmed": cleanup, "runtime_source_class": source_class, "command_results": command_results, "test_file_count": len(tests)}
    selected = [str(row["path"]) for row in tests]
    command = _run_bounded_command([python, "-I", "-B", "-c", _runner_source(runner), str(root), str(private / "temp"), *selected], cwd=root, env=env, timeout_seconds=TEST_TIMEOUT_SECONDS)
    cleanup = cleanup and bool(command.get("cleanup_confirmed"))
    command_results.append({"phase": "tests", "runner": runner, "selection_digest": _digest([str(row.get("relative_path_digest") or "") for row in tests]), **command})
    passed = bool(command.get("passed")) and cleanup
    return {
        "passed": passed,
        "status": "python_tests_passed" if passed else "python_tests_failed",
        "tests_executed": True,
        "cleanup_confirmed": cleanup,
        "runtime_source_class": source_class,
        "runner": runner,
        "command_results": command_results,
        "test_file_count": len(tests),
    }


def _run_node_verification(
    root: Path,
    files: Sequence[Mapping[str, Any]],
    *,
    request_id: str,
    attempt_number: int,
    runtime_root=None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    from node_javascript_test_adapter import (
        NODE_PROBE_TIMEOUT_SECONDS,
        TEST_TIMEOUT_SECONDS,
        _capability_contract_ok,
        _minimal_environment,
        _node_candidates,
        _read_workspace_sources,
        _run_bounded_command,
        _select_node,
    )

    rows, failure = _read_workspace_sources(root, {"files": list(files)})
    if rows is None:
        return {"passed": False, "status": str(failure.get("status") or "node_verification_rejected"), "tests_executed": False, "cleanup_confirmed": True}
    js_rows = [row for row in rows if PurePosixPath(str(row.get("relative_path") or "")).suffix.casefold() in {".js", ".mjs", ".cjs"}]
    contract_ok, rejected_digest = _capability_contract_ok(js_rows)
    if not contract_ok:
        return {"passed": False, "status": "node_test_capability_contract_rejected", "tests_executed": False, "cleanup_confirmed": True, "rejected_path_digest": rejected_digest}
    private = _verification_private_root(request_id, attempt_number, runtime_root)
    node, source_class, failures, launch_attempts, cleanup = _select_node(_node_candidates(node_executable), cwd=root, home=private)
    if not node:
        return {"passed": False, "status": "node_runtime_unavailable", "tests_executed": False, "cleanup_confirmed": cleanup, "runtime_source_class": "none", "launch_attempt_count": launch_attempts, "launch_failure_digests": failures}
    env = _minimal_environment(node, private)
    command_results: list[dict[str, Any]] = []
    for row in js_rows:
        command = _run_bounded_command([node, "--check", str(row["path"])], cwd=root, env=env, timeout_seconds=NODE_PROBE_TIMEOUT_SECONDS)
        cleanup = cleanup and bool(command.get("cleanup_confirmed"))
        command_results.append({"phase": "syntax", "path_digest": str(row.get("relative_path_digest") or ""), **command})
        if command.get("passed") is not True:
            return {"passed": False, "status": "node_syntax_failed", "tests_executed": True, "cleanup_confirmed": cleanup, "runtime_source_class": source_class, "command_results": command_results}
    tests = [row for row in js_rows if row.get("is_test")]
    if not tests:
        return {"passed": True, "status": "node_syntax_verification_passed_no_tests", "tests_executed": True, "cleanup_confirmed": cleanup, "runtime_source_class": source_class, "command_results": command_results, "test_file_count": 0}
    selected = [str(row["path"]) for row in tests]
    command = _run_bounded_command([node, "--test", *selected], cwd=root, env=env, timeout_seconds=TEST_TIMEOUT_SECONDS)
    cleanup = cleanup and bool(command.get("cleanup_confirmed"))
    command_results.append({"phase": "tests", "selection_digest": _digest([str(row.get("relative_path_digest") or "") for row in tests]), **command})
    passed = bool(command.get("passed")) and cleanup
    return {"passed": passed, "status": "node_tests_passed" if passed else "node_tests_failed", "tests_executed": True, "cleanup_confirmed": cleanup, "runtime_source_class": source_class, "command_results": command_results, "test_file_count": len(tests)}


def _run_static_verification(root: Path, files: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked = 0
    try:
        for row in files:
            relative = str(row.get("relative_path") or "")
            suffix = PurePosixPath(relative).suffix.casefold()
            if suffix not in {".html", ".htm", ".js", ".mjs", ".cjs", ".json"}:
                continue
            path = root / _safe_relative(relative)
            content = path.read_text(encoding="utf-8")
            _validate_syntax(relative, content)
            checked += 1
    except (OSError, UnicodeError, ValueError) as exc:
        return {"passed": False, "status": "static_validation_failed", "tests_executed": True, "cleanup_confirmed": True, "reason_digest": _digest({"type": type(exc).__name__, "reason": str(exc)})}
    return {"passed": True, "status": "static_validation_passed", "tests_executed": True, "cleanup_confirmed": True, "validated_file_count": checked}


def _bounded_verification_files(
    files: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    attempt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    by_path = {str(row.get("relative_path") or ""): dict(row) for row in files}
    selected: set[str] = {
        str(row.get("relative_path") or "")
        for row in attempt.get("changes") or []
        if str(row.get("relative_path") or "") in by_path
    }
    verification_plan = [str(value or "") for value in plan.get("verification_plan") or []]
    explicit_tests = 0
    for value in verification_plan:
        relative = str(value or "").replace("\\", "/")
        if relative in by_path and _is_project_test_path(relative):
            selected.add(relative)
            explicit_tests += 1
    if explicit_tests == 0 and any("test" in value.casefold() for value in verification_plan):
        discovered = sorted(
            (path for path in by_path if _is_project_test_path(path)),
            key=str.casefold,
        )[:MAX_FOCUSED_TEST_FILES]
        selected.update(discovered)
    if not selected:
        return [dict(row) for row in files]
    return [by_path[path] for path in sorted(selected, key=str.casefold)]


def run_isolated_coding_verification(
    request_id: str,
    attempt_number: int,
    *,
    runtime_root=None,
    python_executable: str | None = None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
    plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
    workspace = _read_json(_store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json")
    attempt = _read_json(_attempt_path(request_id, attempt_number, runtime_root))
    if not inspection or not plan or not workspace or not attempt:
        return _failure("isolated_coding_verification_lineage_missing", request_id=request_id)
    try:
        root = _workspace_root_from_record(workspace)
        integrity_ok, integrity_status = _strict_workspace_integrity(root)
        if not integrity_ok:
            raise ValueError(integrity_status)
        files, _ = _walk_project(root)
        verification_files = _bounded_verification_files(files, plan, attempt)
    except (OSError, ValueError) as exc:
        return _failure("isolated_coding_verification_workspace_invalid", request_id=request_id, reason=str(exc))
    project_type = str(inspection.get("project_type") or "")
    if project_type == "python_project" or any(str(row.get("relative_path") or "").endswith(".py") for row in verification_files):
        result = _run_python_verification(root, verification_files, request_id=request_id, attempt_number=attempt_number, runtime_root=runtime_root, python_executable=python_executable)
    elif project_type in {"javascript_project", "javascript_web_project"} or any(PurePosixPath(str(row.get("relative_path") or "")).suffix.casefold() in {".js", ".mjs", ".cjs"} for row in verification_files):
        result = _run_node_verification(root, verification_files, request_id=request_id, attempt_number=attempt_number, runtime_root=runtime_root, node_executable=node_executable)
    else:
        result = _run_static_verification(root, verification_files)
    result = dict(result)
    result["verification_scope_file_count"] = len(verification_files)
    result["verification_scope_digest"] = _digest([str(row.get("relative_path_digest") or "") for row in verification_files])
    construction_quality = {}
    if result.get("passed") is True:
        try:
            from complete_application_construction_foundations import load_complete_application_construction
            construction = load_complete_application_construction(request_id, runtime_root=runtime_root)
            if construction:
                from complete_application_construction import evaluate_complete_application_quality, public_complete_application_quality
                quality = evaluate_complete_application_quality(request_id, attempt_number, runtime_root=runtime_root)
                construction_quality = public_complete_application_quality(quality) if quality.get("quality_result_digest") else dict(quality)
                quality_command = {
                    "phase": "construction_quality",
                    "runner": "deterministic_structural_quality",
                    "selection_digest": str(construction.get("construction_contract_digest") or ""),
                    "passed": bool(quality.get("passed")),
                    "exit_class": "success" if quality.get("passed") else "quality_failed",
                    "output_digest": str(quality.get("quality_result_digest") or quality.get("failure_digest") or ""),
                    "output_bytes": 0,
                    "cleanup_confirmed": True,
                    "duration_ms": 0,
                    "quality_failure_codes": list(quality.get("failed_finding_codes") or []),
                }
                result = dict(result)
                result["command_results"] = [*list(result.get("command_results") or []), quality_command]
                result["construction_quality_passed"] = bool(quality.get("passed"))
                result["construction_quality_digest"] = str(quality.get("quality_result_digest") or "")
                result["construction_failed_finding_codes"] = list(quality.get("failed_finding_codes") or [])
                if quality.get("passed") is not True:
                    result["passed"] = False
                    result["status"] = "complete_application_quality_failed"
                else:
                    result["status"] = "complete_application_verification_passed"
        except Exception as exc:
            result = dict(result)
            result["passed"] = False
            result["status"] = "complete_application_quality_internal_error"
            result["construction_quality_error_digest"] = _digest({"type": type(exc).__name__})
    public_commands = []
    for command in result.get("command_results") or []:
        public_commands.append({
            "phase": command.get("phase", ""),
            "runner": command.get("runner", ""),
            "path_digest": command.get("path_digest", ""),
            "selection_digest": command.get("selection_digest", ""),
            "passed": bool(command.get("passed")),
            "exit_class": command.get("exit_class", ""),
            "output_digest": command.get("output_digest", ""),
            "output_bytes": int(command.get("output_bytes") or 0),
            "cleanup_confirmed": bool(command.get("cleanup_confirmed", True)),
            "duration_ms": int(command.get("duration_ms") or 0),
            "quality_failure_codes": list(command.get("quality_failure_codes") or [])[:24],
        })
    public = {
        "ok": True,
        "status": str(result.get("status") or "isolated_coding_verification_completed"),
        "request_id": request_id,
        "attempt_number": int(attempt_number),
        "project_type": project_type,
        "passed": bool(result.get("passed")),
        "tests_executed": bool(result.get("tests_executed")),
        "cleanup_confirmed": bool(result.get("cleanup_confirmed", True)),
        "test_file_count": int(result.get("test_file_count") or 0),
        "validated_file_count": int(result.get("validated_file_count") or 0),
        "runtime_source_class": str(result.get("runtime_source_class") or ""),
        "runner": str(result.get("runner") or ""),
        "command_results": public_commands,
        "construction_quality": construction_quality,
        "construction_quality_passed": bool(result.get("construction_quality_passed")) if construction_quality else None,
        "construction_quality_digest": str(result.get("construction_quality_digest") or ""),
        "construction_failed_finding_codes": list(result.get("construction_failed_finding_codes") or [])[:24],
        "network_allowed": False,
        "dependencies_installed": False,
        "shell_executed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "release_authorized": False,
        "raw_output_exposed": False,
        "private_content_exposed": False,
    }
    public["verification_digest"] = _digest(public)
    return public


def _save_verification(attempt: Mapping[str, Any], verification: Mapping[str, Any], *, runtime_root=None) -> dict[str, Any]:
    updated = dict(attempt)
    updated["verification"] = dict(verification)
    updated["status"] = "isolated_coding_attempt_verified"
    updated = _seal(updated, "attempt_record_digest")
    _atomic_json(_attempt_path(str(attempt.get("request_id") or ""), int(attempt.get("attempt_number") or 0), runtime_root), updated)
    return updated


def _attempt_summary(attempt: Mapping[str, Any]) -> dict[str, Any]:
    verification = dict(attempt.get("verification") or {})
    return {
        "attempt_number": int(attempt.get("attempt_number") or 0),
        "change_count": int(attempt.get("change_count") or 0),
        "change_manifest_digest": str(attempt.get("change_manifest_digest") or ""),
        "verification_status": str(verification.get("status") or ""),
        "verification_digest": str(verification.get("verification_digest") or ""),
        "tests_executed": bool(verification.get("tests_executed")),
        "passed": bool(verification.get("passed")),
        "cleanup_confirmed": bool(verification.get("cleanup_confirmed", True)),
    }


def _build_review(request_id: str, attempts: Sequence[Mapping[str, Any]], *, runtime_root=None) -> dict[str, Any]:
    workspace = _read_json(_store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json")
    if not workspace:
        return _failure("isolated_coding_review_workspace_missing", request_id=request_id)
    root = _workspace_root_from_record(workspace)
    baseline: dict[str, tuple[bool, str]] = {}
    changed_paths: list[str] = []
    for attempt in attempts:
        for row in attempt.get("changes") or []:
            relative = str(row.get("relative_path") or "")
            if relative not in baseline:
                baseline[relative] = (bool(row.get("before_exists")), str(row.get("before_content") or ""))
            if relative not in changed_paths:
                changed_paths.append(relative)
    diff_parts: list[str] = []
    added = modified = deleted = 0
    for relative in sorted(changed_paths, key=str.casefold):
        existed, before = baseline[relative]
        path = root / _safe_relative(relative)
        after_exists = path.is_file() and not _is_link_like(path)
        after = path.read_text(encoding="utf-8") if after_exists else ""
        if existed and not after_exists:
            deleted += 1
        elif not existed and after_exists:
            added += 1
        elif before != after:
            modified += 1
        if before == after and existed == after_exists:
            continue
        before_lines = before.splitlines(keepends=True)
        after_lines = after.splitlines(keepends=True)
        chunk = "".join(difflib.unified_diff(before_lines, after_lines, fromfile=f"a/{relative}" if existed else "/dev/null", tofile=f"b/{relative}" if after_exists else "/dev/null", lineterm="\n"))
        diff_parts.append(chunk)
    full_diff = "\n".join(part for part in diff_parts if part)
    truncated = False
    raw = full_diff.encode("utf-8")
    if len(raw) > MAX_DIFF_BYTES:
        raw = raw[:MAX_DIFF_BYTES]
        full_diff = raw.decode("utf-8", errors="ignore") + "\n[diff truncated by bounded review contract]\n"
        truncated = True
    files, _ = _walk_project(root)
    freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
    review = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "isolated_coding_review_ready" if freshness.get("ok") else "isolated_coding_review_stale_source",
        "request_id": request_id,
        "changed_paths": sorted(changed_paths, key=str.casefold),
        "changed_path_digests": [_path_digest(path) for path in sorted(changed_paths, key=str.casefold)],
        "added_file_count": added,
        "modified_file_count": modified,
        "deleted_file_count": deleted,
        "diff": full_diff,
        "diff_digest": hashlib.sha256(full_diff.encode("utf-8")).hexdigest(),
        "diff_bytes": len(full_diff.encode("utf-8")),
        "diff_truncated": truncated,
        "workspace_manifest_digest": _manifest_digest(files),
        "workspace_file_count": len(files),
        "source_fresh_at_review": bool(freshness.get("ok")),
        "source_freshness_digest": str(freshness.get("freshness_digest") or ""),
        "reviewable_diff_available": bool(full_diff),
        "operator_review_required": True,
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "installation_authorized": False,
        "release_authorized": False,
        "permanent_approval_granted": False,
        "independent_authority_granted": False,
    }
    review = _seal(review, "review_record_digest")
    _atomic_json(_review_path(request_id, runtime_root), review)
    return review


def _capture_isolated_coding_training_evidence(
    *,
    runtime_root,
    capture_authorized: bool,
    request: Mapping[str, Any],
    plan: Mapping[str, Any],
    current_attempt: Mapping[str, Any],
    verification: Mapping[str, Any],
    previous_attempt: Mapping[str, Any] | None = None,
    auto_sanitize: bool = False,
) -> dict[str, Any]:
    """Best-effort opt-in capture; recording failure never changes coding outcome."""
    if capture_authorized is not True:
        return {"ok": False, "status": "training_capture_not_requested"}
    try:
        from model_training.training_capture_adapters import capture_software_attempt
    except ImportError:
        try:
            from model_training.training_capture_adapters import capture_software_attempt
        except ImportError:
            return {"ok": False, "status": "training_capture_adapter_unavailable"}
    try:
        current_output = {
            "changes": list(current_attempt.get("changes") or []),
            "attempt_number": int(current_attempt.get("attempt_number") or 0),
            "change_manifest_digest": str(current_attempt.get("change_manifest_digest") or ""),
        }
        prior_output = None
        if previous_attempt:
            prior_output = {
                "changes": list(previous_attempt.get("changes") or []),
                "attempt_number": int(previous_attempt.get("attempt_number") or 0),
                "change_manifest_digest": str(previous_attempt.get("change_manifest_digest") or ""),
            }
        validation = {
            "passed": bool(verification.get("passed") is True),
            "tests_passed": bool(verification.get("passed") is True),
            "deterministic": True,
            "status": str(verification.get("status") or ""),
            "verification_digest": str(verification.get("verification_digest") or ""),
        }
        # When a verified repair follows a failed attempt, preserve the failed
        # candidate as model_output and the verified candidate as correction.
        model_output = prior_output if prior_output is not None and validation["passed"] else current_output
        corrected_output = current_output if prior_output is not None and validation["passed"] else None
        return capture_software_attempt(
            runtime_root=runtime_root,
            capture_authorized=True,
            prompt_or_context={
                "request": dict(request),
                "plan": dict(plan),
            },
            model_output=model_output,
            corrected_output=corrected_output,
            verification=validation,
            provenance={
                "request_id_digest": _digest(str(request.get("request_id") or "")),
                "execution_digest": str(current_attempt.get("execution_digest") or ""),
                "attempt_record_digest": str(current_attempt.get("attempt_record_digest") or ""),
            },
            auto_sanitize=auto_sanitize,
        )
    except Exception as exc:
        try:
            from model_training.training_capture_runtime import persist_capture_failure
        except ImportError:
            from model_training.training_capture_runtime import persist_capture_failure
        return persist_capture_failure(runtime_root=runtime_root, capability="coding_repair", status="training_capture_failed", failure_class=type(exc).__name__)


def authorize_and_run_isolated_coding_execution(
    request_id: str,
    *,
    expected_execution_digest: str,
    authorization_phrase: str,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    python_executable: str | None = None,
    node_executable: str | None = None,
    capture_training_evidence: bool = False,
) -> dict[str, Any]:
    try:
        from model_training.training_policy import resolve_training_evidence_capture_policy
    except ImportError:
        from model_training.training_policy import resolve_training_evidence_capture_policy
    training_policy = resolve_training_evidence_capture_policy()
    capture_training_evidence = bool(capture_training_evidence or training_policy.coding_repair_enabled)
    prepared = prepare_isolated_coding_execution(request_id, runtime_root=runtime_root)
    if prepared.get("ok") is not True:
        return prepared
    if str(prepared.get("execution_digest") or "") != str(expected_execution_digest or ""):
        return _failure("isolated_coding_execution_stale_authorization", request_id=request_id)
    if not _authorization_text_matches(
        authorization_phrase,
        _authorization_phrase(request_id, expected_execution_digest),
    ):
        return _failure("isolated_coding_execution_exact_authorization_required", request_id=request_id)

    path = _execution_path(request_id, runtime_root)
    lease_token = uuid.uuid4().hex
    recovery_count = 0
    with _proposal_lock(request_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid(current, "execution_record_digest"):
            return _failure("isolated_coding_execution_record_invalid", request_id=request_id)
        if current.get("phase") == "sealed":
            result = dict(current.get("result") or {})
            if result and str(current.get("result_digest") or "") == _digest(result):
                return {**result, "operation_status": "restored"}
            return _failure("isolated_coding_execution_result_invalid", request_id=request_id)
        if current.get("phase") == "running" and float(current.get("lease_expires_unix") or 0.0) > time.time():
            return _failure("isolated_coding_execution_in_progress", request_id=request_id)
        if current.get("phase") not in {"prepared", "running"}:
            return _failure("isolated_coding_execution_state_invalid", request_id=request_id)
        recovery_count = int(current.get("recovery_count") or 0) + int(current.get("phase") == "running")
        running = dict(current)
        running.update({
            "status": "isolated_coding_execution_running",
            "phase": "running",
            "lease_token": lease_token,
            "lease_expires_unix": time.time() + LEASE_SECONDS,
            "recovery_count": recovery_count,
            "execution_authority_consumed": True,
            **EXECUTION_AUTHORITY,
        })
        _atomic_json(path, _seal(running, "execution_record_digest"))

    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
    plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
    workspace = _read_json(_store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json")
    if not request or not inspection or not plan or not workspace:
        result = _failure("isolated_coding_execution_lineage_missing", request_id=request_id)
    else:
        try:
            root = _workspace_root_from_record(workspace)
            attempts: list[dict[str, Any]] = []
            diagnostic_cycles: list[dict[str, Any]] = []
            previous_outcome: dict[str, Any] | None = None
            final_passed = False
            provider_contacted = False
            provider_request_count = 0
            provider_failure_class = ""
            provider_context_rejection_code = ""
            generation_rejection_code = ""
            terminal_status = "isolated_coding_execution_attempts_exhausted"
            for attempt_number in range(1, MAX_EXECUTION_ATTEMPTS + 1):
                latest_request = load_coding_work_request(request_id, runtime_root=runtime_root)
                if latest_request.get("cancelled"):
                    terminal_status = "isolated_coding_execution_cancelled"
                    break
                freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
                if freshness.get("ok") is not True:
                    terminal_status = str(freshness.get("status") or "stale_source_detected")
                    break
                execution_request = dict(request)
                try:
                    from complete_application_construction_foundations import (
                        load_complete_application_construction,
                        public_complete_application_construction,
                    )
                    construction = load_complete_application_construction(request_id, runtime_root=runtime_root)
                    if construction:
                        execution_request["construction_contract_public"] = public_complete_application_construction(construction)
                except Exception:
                    pass
                attempt = _load_or_generate_attempt(
                    request=execution_request,
                    plan=plan,
                    inspection=inspection,
                    root=root,
                    execution_digest=expected_execution_digest,
                    attempt_number=attempt_number,
                    previous_outcome=previous_outcome,
                    runtime_root=runtime_root,
                    provider_generate=provider_generate,
                )
                provider_contacted = provider_contacted or bool(attempt.get("provider_contacted"))
                provider_request_count += int(bool(attempt.get("provider_contacted")))
                provider_failure_class = str(attempt.get("provider_failure_class") or provider_failure_class)
                provider_context_rejection_code = str(
                    attempt.get("provider_context_rejection_code") or provider_context_rejection_code
                )
                generation_rejection_code = str(attempt.get("generation_rejection_code") or generation_rejection_code)
                if not attempt.get("attempt_record_digest"):
                    terminal_status = str(attempt.get("status") or "isolated_coding_generation_failed")
                    rejection_code = str(attempt.get("generation_rejection_code") or "")
                    previous_outcome = {
                        "status": terminal_status,
                        "passed": False,
                        "generation_rejection_code": rejection_code,
                        "repair_guidance": _generation_repair_guidance(rejection_code),
                    }
                    transient_repair_candidate = str(attempt.get("transient_repair_candidate") or "")
                    if transient_repair_candidate:
                        previous_outcome["rejected_candidate_json"] = transient_repair_candidate
                    boundary_rejection = rejection_code in {
                        "existing_project_test_change_rejected", "execution_authority_binding_rejected",
                        "change_path_boundary_rejected", "change_path_not_source_relevant",
                    }
                    if terminal_status == "isolated_coding_generation_rejected" and not boundary_rejection and attempt_number < MAX_EXECUTION_ATTEMPTS:
                        continue
                    break
                latest_request = load_coding_work_request(request_id, runtime_root=runtime_root)
                if latest_request.get("cancelled"):
                    terminal_status = "isolated_coding_execution_cancelled"
                    break
                freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
                if freshness.get("ok") is not True:
                    terminal_status = str(freshness.get("status") or "stale_source_detected")
                    break
                applied = _apply_attempt(attempt, runtime_root=runtime_root)
                if not applied.get("attempt_record_digest"):
                    terminal_status = str(applied.get("status") or "isolated_coding_workspace_apply_blocked")
                    previous_outcome = {"status": terminal_status, "passed": False}
                    break
                verification = dict(applied.get("verification") or {})
                if not verification.get("verification_digest"):
                    verification = run_isolated_coding_verification(
                        request_id,
                        attempt_number,
                        runtime_root=runtime_root,
                        python_executable=python_executable,
                        node_executable=node_executable,
                    )
                    applied = _save_verification(applied, verification, runtime_root=runtime_root)
                previous_training_attempt = attempts[-1] if attempts else None
                attempts.append(applied)
                if capture_training_evidence:
                    capture_receipt = _capture_isolated_coding_training_evidence(
                        runtime_root=runtime_root,
                        capture_authorized=True,
                        request=request,
                        plan=plan,
                        current_attempt=applied,
                        verification=verification,
                        previous_attempt=previous_training_attempt,
                        auto_sanitize=training_policy.auto_sanitize_enabled,
                    )
                    applied["training_capture_status"] = str(capture_receipt.get("status") or "")
                if verification.get("passed") is True:
                    final_passed = True
                    terminal_status = "isolated_coding_execution_completed"
                    break
                # v1257 diagnostic reasoning is deliberately subordinate to
                # this already-consumed isolated-execution authorization.  A
                # failed verification is diagnosed before another provider
                # repair attempt is allowed.  The diagnostic record itself
                # grants no authority and stores no raw test output.
                from diagnostic_repair_reasoning import (
                    provider_repair_context, public_diagnostic_result, run_focused_diagnostics,
                )
                diagnosis = run_focused_diagnostics(
                    request_id,
                    attempt_number,
                    expected_execution_digest=expected_execution_digest,
                    runtime_root=runtime_root,
                    python_executable=python_executable,
                    node_executable=node_executable,
                )
                if diagnosis.get("ok") is not True:
                    terminal_status = str(diagnosis.get("status") or "isolated_coding_diagnostic_failed")
                    previous_outcome = {
                        "status": terminal_status,
                        "passed": False,
                        "verification_digest": verification.get("verification_digest"),
                    }
                    break
                diagnostic_cycles.append(public_diagnostic_result(diagnosis))
                if diagnosis.get("repair_supported") is not True:
                    terminal_status = f"isolated_coding_execution_{str(diagnosis.get('repair_posture') or 'diagnostic_blocked')}"
                    previous_outcome = {
                        "status": terminal_status,
                        "passed": False,
                        "verification_digest": verification.get("verification_digest"),
                        "diagnostic_context": provider_repair_context(diagnosis),
                    }
                    break
                previous_outcome = {
                    "status": verification.get("status"),
                    "passed": False,
                    "verification_digest": verification.get("verification_digest"),
                    "test_file_count": verification.get("test_file_count", 0),
                    "command_outcome_classes": [str(row.get("exit_class") or "") for row in verification.get("command_results") or []],
                    "diagnostic_context": provider_repair_context(diagnosis),
                }
            review = _build_review(request_id, attempts, runtime_root=runtime_root) if attempts else {}
            source_fresh = bool(review.get("source_fresh_at_review")) if review else bool(check_coding_source_freshness(request_id, runtime_root=runtime_root).get("ok"))
            if final_passed and not source_fresh:
                terminal_status = "isolated_coding_execution_stale_source_at_review"
                final_passed = False
            result = {
                "ok": final_passed,
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "status": terminal_status,
                "request_id": request_id,
                "execution_digest": expected_execution_digest,
                "project_type": inspection.get("project_type", ""),
                "attempt_count": len(attempts),
                "repair_attempt_count": max(0, len(attempts) - 1),
                "attempts": [_attempt_summary(row) for row in attempts],
                "diagnostic_cycle_count": len(diagnostic_cycles),
                "diagnostic_cycles": diagnostic_cycles,
                "diagnostic_reasoning_used": bool(diagnostic_cycles),
                "provider_contacted": provider_contacted or bool(attempts),
                "provider_request_count": provider_request_count,
                "provider_failure_class": provider_failure_class,
                "provider_context_rejection_code": provider_context_rejection_code,
                "generation_rejection_code": generation_rejection_code,
                "tests_executed": any(bool((row.get("verification") or {}).get("tests_executed")) for row in attempts),
                "test_passed": final_passed,
                "cleanup_confirmed": all(bool((row.get("verification") or {}).get("cleanup_confirmed", True)) for row in attempts),
                "source_fresh_at_review": source_fresh,
                "review_digest": str(review.get("review_record_digest") or ""),
                "diff_digest": str(review.get("diff_digest") or ""),
                "reviewable_diff_available": bool(review.get("reviewable_diff_available")),
                "changed_file_count": len(review.get("changed_paths") or []),
                "recovery_count": recovery_count,
                "operator_review_required": True,
                "runtime_records_external": True,
                "selected_project_modified": False,
                "source_modified": False,
                "source_application_authorized": False,
                "installation_authorized": False,
                "release_authorized": False,
                "permanent_approval_granted": False,
                "independent_authority_granted": False,
                "execution_authority_consumed": True,
                "raw_provider_output_exposed": False,
                "raw_test_output_exposed": False,
                "private_content_exposed": False,
            }
            result["execution_result_digest"] = _digest(result)
        except Exception as exc:
            result = _failure("isolated_coding_execution_internal_error", request_id=request_id, reason=_digest({"type": type(exc).__name__}))

    with _proposal_lock(request_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid(current, "execution_record_digest") or str(current.get("lease_token") or "") != lease_token:
            return _failure("isolated_coding_execution_lease_lost", request_id=request_id)
        sealed = dict(current)
        sealed.update({
            "status": str(result.get("status") or "isolated_coding_execution_internal_error"),
            "phase": "sealed",
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "attempt_count": int(result.get("attempt_count") or 0),
            "repair_attempt_count": int(result.get("repair_attempt_count") or 0),
            "provider_contacted": bool(result.get("provider_contacted")),
            "tests_executed": bool(result.get("tests_executed")),
            "reviewable_diff_available": bool(result.get("reviewable_diff_available")),
            "result": result,
            "result_digest": _digest(result),
            **AUTHORITY_STATE,
            "execution_authority_consumed": True,
        })
        _atomic_json(path, _seal(sealed, "execution_record_digest"))
    return {**result, "operation_status": "recovered" if recovery_count else "created"}


def load_isolated_coding_execution(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_execution_path(request_id, runtime_root))
    return record if record and _valid(record, "execution_record_digest") else {}


def load_isolated_coding_review(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_review_path(request_id, runtime_root))
    return record if record and _valid(record, "review_record_digest") else {}


def public_isolated_coding_execution(record: Mapping[str, Any]) -> dict[str, Any]:
    result = record.get("result") if isinstance(record.get("result"), Mapping) else record
    return {
        "ok": bool(result.get("ok")),
        "status": str(result.get("status") or record.get("status") or ""),
        "request_id": str(result.get("request_id") or record.get("request_id") or ""),
        "execution_digest": str(result.get("execution_digest") or record.get("execution_digest") or ""),
        "authorization_phrase": str(record.get("authorization_phrase") or "") if record.get("phase") == "prepared" else "",
        "phase": str(record.get("phase") or ("sealed" if result.get("execution_result_digest") else "")),
        "project_type": str(result.get("project_type") or record.get("project_type") or ""),
        "attempt_count": int(result.get("attempt_count") or record.get("attempt_count") or 0),
        "repair_attempt_count": int(result.get("repair_attempt_count") or record.get("repair_attempt_count") or 0),
        "provider_contacted": bool(result.get("provider_contacted") or record.get("provider_contacted")),
        "provider_request_count": int(result.get("provider_request_count") or 0),
        "provider_context_rejection_code": str(result.get("provider_context_rejection_code") or ""),
        "generation_rejection_code": str(result.get("generation_rejection_code") or ""),
        "tests_executed": bool(result.get("tests_executed") or record.get("tests_executed")),
        "test_passed": result.get("test_passed") if isinstance(result.get("test_passed"), bool) else None,
        "cleanup_confirmed": result.get("cleanup_confirmed") if isinstance(result.get("cleanup_confirmed"), bool) else None,
        "source_fresh_at_review": result.get("source_fresh_at_review") if isinstance(result.get("source_fresh_at_review"), bool) else None,
        "reviewable_diff_available": bool(result.get("reviewable_diff_available") or record.get("reviewable_diff_available")),
        "changed_file_count": int(result.get("changed_file_count") or 0),
        "diff_digest": str(result.get("diff_digest") or ""),
        "review_digest": str(result.get("review_digest") or ""),
        "operator_review_required": True,
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "installation_authorized": False,
        "release_authorized": False,
        "permanent_approval_granted": False,
        "independent_authority_granted": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
    }


def public_isolated_coding_review(record: Mapping[str, Any], *, include_diff: bool = False) -> dict[str, Any]:
    row = {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "request_id": str(record.get("request_id") or ""),
        "changed_paths": list(record.get("changed_paths") or []),
        "added_file_count": int(record.get("added_file_count") or 0),
        "modified_file_count": int(record.get("modified_file_count") or 0),
        "deleted_file_count": int(record.get("deleted_file_count") or 0),
        "diff_digest": str(record.get("diff_digest") or ""),
        "diff_bytes": int(record.get("diff_bytes") or 0),
        "diff_truncated": bool(record.get("diff_truncated")),
        "source_fresh_at_review": bool(record.get("source_fresh_at_review")),
        "workspace_manifest_digest": str(record.get("workspace_manifest_digest") or ""),
        "reviewable_diff_available": bool(record.get("reviewable_diff_available")),
        "operator_review_required": True,
        "selected_project_modified": False,
        "source_application_authorized": False,
        "release_authorized": False,
        "private_project_path_exposed": False,
    }
    if include_diff:
        row["diff"] = str(record.get("diff") or "")
    else:
        row["diff_exposed"] = False
    return row


def prepare_isolated_coding_from_approved_proposal(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Bridge the existing ordinary-chat proposal lifecycle into v1254."""

    from ordinary_chat_development_campaign import _proposal_path, _validate

    bridge_path = _bridge_path(proposal_id, expected_revision, runtime_root)
    existing = _read_json(bridge_path)
    if existing:
        if not _valid(existing, "bridge_record_digest"):
            return _failure("isolated_coding_proposal_bridge_invalid", reason="bridge_digest_invalid")
        request_id = str(existing.get("request_id") or "")
        prepared = prepare_isolated_coding_execution(request_id, runtime_root=runtime_root)
        return {**existing, "execution": public_isolated_coding_execution(prepared), "operation_status": "restored"}

    proposal = _read_json(_proposal_path(proposal_id, runtime_root))
    if not proposal or not _validate(proposal):
        return _failure("isolated_coding_proposal_missing_or_invalid")
    if int(proposal.get("revision") or 0) != int(expected_revision) or str(proposal.get("revision_digest") or "") != str(expected_revision_digest or ""):
        return _failure("isolated_coding_proposal_stale")
    if proposal.get("approval_consumed") is not True:
        return _failure("isolated_coding_proposal_approval_required")
    target = dict(proposal.get("target") or {})
    if target.get("mode") != "selected_project" or not str(target.get("private_path") or ""):
        return _failure("isolated_coding_selected_project_required")

    request = create_or_restore_coding_work_request(
        user_objective=str(proposal.get("request") or ""),
        target_project=str(target.get("private_path") or ""),
        requirements=[str(proposal.get("request") or "")],
        acceptance_criteria=["The requested behavior is implemented in the isolated workspace and bounded verification passes."],
        constraints=["Preserve the selected project's existing architecture unless the request requires a bounded change."],
        prohibited_actions=["Do not install dependencies or modify the selected project."],
        expected_artifacts=["Reviewable isolated diff", "Bounded verification evidence", "Source-freshness evidence"],
        verification=["Run project-appropriate bounded syntax/tests", "Verify selected project remains unchanged", "Verify source is fresh before review"],
        runtime_root=runtime_root,
    )
    if request.get("ok") is not True:
        return _failure("isolated_coding_request_bridge_failed")
    inspection = inspect_coding_project(str(request["request_id"]), runtime_root=runtime_root)
    if inspection.get("ok") is not True:
        return _failure("isolated_coding_inspection_bridge_failed", request_id=str(request["request_id"]))
    plan = create_or_restore_coding_work_plan(str(request["request_id"]), runtime_root=runtime_root)
    if plan.get("ok") is not True:
        return _failure(str(plan.get("status") or "isolated_coding_plan_bridge_failed"), request_id=str(request["request_id"]))
    workspace = materialize_or_restore_isolated_coding_workspace(str(request["request_id"]), runtime_root=runtime_root)
    if workspace.get("ok") is not True:
        return _failure(str(workspace.get("status") or "isolated_coding_workspace_bridge_failed"), request_id=str(request["request_id"]))
    construction = {}
    try:
        from complete_application_construction_foundations import prepare_complete_application_construction
        construction = prepare_complete_application_construction(str(request["request_id"]), runtime_root=runtime_root)
        if construction.get("ok") is not True and construction.get("status") != "complete_application_construction_not_required":
            return _failure(str(construction.get("status") or "complete_application_construction_bridge_failed"), request_id=str(request["request_id"]))
        if construction.get("ok") is not True:
            construction = {}
    except Exception:
        construction = {}
    prepared = prepare_isolated_coding_execution(str(request["request_id"]), runtime_root=runtime_root)
    if prepared.get("ok") is not True:
        return prepared
    bridge = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "isolated_coding_proposal_bridged",
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": str(expected_revision_digest),
        "proposal_approval_receipt_digest": str(proposal.get("approval_receipt_digest") or ""),
        "request_id": str(request["request_id"]),
        "request_digest": str(request.get("request_digest") or ""),
        "inspection_digest": str(inspection.get("inspection_digest") or ""),
        "plan_digest": str(plan.get("plan_digest") or ""),
        "execution_digest": str(prepared.get("execution_digest") or ""),
        "complete_application_construction_digest": str(construction.get("construction_contract_digest") or ""),
        "complete_application_construction_active": bool(construction),
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "release_authorized": False,
        "independent_authority_granted": False,
    }
    bridge = _seal(bridge, "bridge_record_digest")
    _atomic_json(bridge_path, bridge)
    return {**bridge, "execution": public_isolated_coding_execution(prepared), "operation_status": "created"}


def process_isolated_coding_execution_control(
    user_text: str,
    *,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    python_executable: str | None = None,
    node_executable: str | None = None,
    capture_training_evidence: bool = False,
) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _EXECUTE.fullmatch(text)
    if match:
        request_id = match.group("request_id").lower()
        result = authorize_and_run_isolated_coding_execution(
            request_id,
            expected_execution_digest=match.group("execution_digest").lower(),
            authorization_phrase=text,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            python_executable=python_executable,
            node_executable=node_executable,
            capture_training_evidence=capture_training_evidence,
        )
        public = public_isolated_coding_execution(result)
        if result.get("status") == "isolated_coding_execution_completed":
            conversation = (
                f"The isolated coding execution for {request_id} completed with bounded verification passing. "
                f"A reviewable diff covering {public.get('changed_file_count', 0)} file(s) is ready. "
                "The selected project was not modified; application of the result still requires a later, separate authority stage."
            )
        else:
            detail_code = str(
                public.get("generation_rejection_code")
                or public.get("provider_context_rejection_code")
                or ""
            )
            detail = f" ({detail_code})" if detail_code else ""
            conversation = (
                f"The isolated coding execution for {request_id} stopped with status {result.get('status', 'blocked')}{detail}. "
                "The selected project was not modified and application authority remains denied."
            )
        return {
            "active": True,
            "event": str(result.get("status") or "isolated_coding_execution_blocked"),
            "isolated_coding_execution": public,
            "conversation_response": conversation,
            "public_digest": _digest(public),
        }
    review_match = _REVIEW.fullmatch(text)
    if review_match:
        request_id = review_match.group("request_id").lower()
        from isolated_coding_execution_reliability import build_isolated_coding_operator_handoff
        handoff = build_isolated_coding_operator_handoff(request_id, runtime_root=runtime_root, include_diff=True)
        response = (
            f"Isolated coding review for {request_id}: {handoff.get('status', 'unavailable')}. "
            "The diff, verification evidence, source-freshness state, and remaining limitations are attached to this review. "
            "No selected-project application or release authority is granted by reviewing it."
        )
        return {
            "active": True,
            "event": str(handoff.get("status") or "isolated_coding_operator_handoff_unavailable"),
            "operator_review": handoff,
            "conversation_response": response,
            "public_digest": str(handoff.get("handoff_digest") or _digest(handoff)),
        }
    cancel = _CANCEL.fullmatch(text)
    if cancel:
        from isolated_coding_execution_foundations import cancel_coding_work_request
        request_id = cancel.group("request_id").lower()
        result = cancel_coding_work_request(request_id, runtime_root=runtime_root)
        return {
            "active": True,
            "event": str(result.get("status") or "isolated_coding_cancel_blocked"),
            "isolated_coding_execution": public_isolated_coding_execution(result),
            "conversation_response": f"Isolated coding request {request_id} was cancelled. Any disposable workspace was cleaned when safe; the selected project was not modified.",
            "public_digest": _digest({"request_id": request_id, "status": result.get("status")}),
        }
    return {"active": False, "event": "inactive"}


__all__ = [
    "CONTRACT_VERSION",
    "MAX_EXECUTION_ATTEMPTS",
    "prepare_isolated_coding_execution",
    "authorize_and_run_isolated_coding_execution",
    "run_isolated_coding_verification",
    "load_isolated_coding_execution",
    "load_isolated_coding_review",
    "public_isolated_coding_execution",
    "public_isolated_coding_review",
    "prepare_isolated_coding_from_approved_proposal",
    "process_isolated_coding_execution_control",
]
