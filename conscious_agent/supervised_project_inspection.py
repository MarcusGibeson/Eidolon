from __future__ import annotations

"""Bounded, read-only project inspection and deficiency identification foundations.

The caller supplies an explicit source root and optional relative scope. This module
reads source metadata and bounded text only; it never writes source, discovers a
private project registry, drafts patches, grants authority, or invokes tools.
"""

import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1180.2"
MAX_FILES = 512
MAX_FILE_BYTES = 512_000
MAX_TOTAL_BYTES = 8_000_000
MAX_PUBLIC_FILES = 128
MAX_CANDIDATES = 64
MAX_REPORT_BYTES = 131_072
ALLOWED_SUFFIXES = frozenset({".py", ".md", ".json", ".toml", ".yaml", ".yml", ".txt", ".html", ".css", ".js", ".ts"})
BLOCKED_PARTS = frozenset({"data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "chroma"})
MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b", re.I)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _safe_relative(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return ""
    parts = tuple(part for part in text.split("/") if part not in {"", "."})
    if not parts or ".." in parts or any(part in BLOCKED_PARTS for part in parts):
        return ""
    return "/".join(parts)


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _candidate(*, category: str, severity: str, path: str, evidence: dict[str, Any], confidence: str = "high") -> dict[str, Any]:
    public_evidence = {key: evidence[key] for key in sorted(evidence)}
    evidence_digest = _digest({"category": category, "path": path, "evidence": public_evidence})
    return {
        "candidate_id": f"def-{evidence_digest[:20]}",
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "path": path,
        "evidence": public_evidence,
        "evidence_digest": evidence_digest,
        "operator_review_required": True,
        "specification_created": False,
        "patch_created": False,
        "source_modified": False,
    }


def inspect_project_source(
    source_root: str | Path,
    *,
    scope: Iterable[str] = (),
    max_files: int = MAX_FILES,
    max_total_bytes: int = MAX_TOTAL_BYTES,
) -> dict[str, Any]:
    """Inspect an explicit source tree and return a bounded, content-free report."""
    root = Path(source_root).expanduser().resolve()
    max_files = max(1, min(int(max_files), MAX_FILES))
    max_total_bytes = max(1, min(int(max_total_bytes), MAX_TOTAL_BYTES))
    requested = list(scope)
    safe_scope = [_safe_relative(item) for item in requested]
    rejected_scope_count = sum(1 for item in safe_scope if not item)
    safe_scope = sorted(set(item for item in safe_scope if item))

    base = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "inspection_mode": "read_only_static",
        "source_root_digest": _digest(str(root)),
        "requested_scope_count": len(requested),
        "accepted_scope": safe_scope,
        "rejected_scope_count": rejected_scope_count,
        "source_modified": False,
        "specification_created": False,
        "patch_created": False,
        "approval_created": False,
        "execution_invoked": False,
        "provider_contacted": False,
        "project_registry_discovered": False,
        "raw_source_exposed": False,
        "content_free": True,
    }
    if not root.is_dir():
        result = {**base, "inspection_status": "blocked", "block_reason": "source_root_unavailable", "file_count": 0, "files": [], "deficiency_candidates": []}
        result["inspection_digest"] = _digest(result)
        return result

    starts: list[Path] = []
    if requested:
        for rel in safe_scope:
            candidate = root / rel
            if _inside(root, candidate) and candidate.exists():
                starts.append(candidate)
            else:
                rejected_scope_count += 1
    else:
        starts = [root]

    paths: set[Path] = set()
    for start in starts:
        if start.is_file():
            paths.add(start)
        elif start.is_dir():
            for path in start.rglob("*"):
                if path.is_file() and _inside(root, path):
                    paths.add(path)
    files: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    total_bytes = 0
    truncated = False
    suffixes: Counter[str] = Counter()

    for path in sorted(paths, key=lambda p: p.relative_to(root).as_posix().lower()):
        rel = path.relative_to(root).as_posix()
        parts = Path(rel).parts
        if any(part in BLOCKED_PARTS for part in parts) or path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            candidates.append(_candidate(category="unreadable_file", severity="medium", path=rel, evidence={"read_failed": True}))
            continue
        if len(files) >= max_files or total_bytes + min(size, MAX_FILE_BYTES) > max_total_bytes:
            truncated = True
            break
        suffixes[path.suffix.lower() or "[none]"] += 1
        text = ""
        raw = b""
        read_bytes = min(size, MAX_FILE_BYTES)
        try:
            raw = path.read_bytes()[:MAX_FILE_BYTES]
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            candidates.append(_candidate(category="unreadable_text", severity="low", path=rel, evidence={"size_bytes": size}))
        line_count = text.count("\n") + (1 if text else 0)
        marker_count = len(MARKER_RE.findall(text)) if text else 0
        syntax_ok: bool | None = None
        if path.suffix.lower() == ".py" and text:
            try:
                ast.parse(text, filename=rel)
                syntax_ok = True
            except SyntaxError as exc:
                syntax_ok = False
                candidates.append(_candidate(category="python_syntax_error", severity="high", path=rel, evidence={"line": int(exc.lineno or 0), "offset": int(exc.offset or 0)}))
        if size > MAX_FILE_BYTES:
            candidates.append(_candidate(category="oversized_file", severity="medium", path=rel, evidence={"size_bytes": size, "inspection_bytes": MAX_FILE_BYTES}, confidence="medium"))
        if line_count > 1200:
            candidates.append(_candidate(category="large_module", severity="low", path=rel, evidence={"line_count": line_count}, confidence="medium"))
        if marker_count:
            candidates.append(_candidate(category="maintenance_marker", severity="low", path=rel, evidence={"marker_count": marker_count}, confidence="medium"))
        file_digest = hashlib.sha256(path.read_bytes()).hexdigest() if size <= MAX_FILE_BYTES else _digest({"path": rel, "size": size, "prefix": hashlib.sha256(raw).hexdigest()})
        files.append({"path": rel, "suffix": path.suffix.lower(), "size_bytes": size, "line_count": line_count, "syntax_ok": syntax_ok, "file_digest": file_digest})
        total_bytes += read_bytes

    files_public = files[:MAX_PUBLIC_FILES]
    candidates = sorted(candidates, key=lambda row: (row["severity"], row["category"], row["path"]))[:MAX_CANDIDATES]
    status = "review_required" if candidates or rejected_scope_count else "clear"
    result = {
        **base,
        "rejected_scope_count": rejected_scope_count,
        "inspection_status": status,
        "file_count": len(files),
        "public_file_count": len(files_public),
        "total_inspected_bytes": total_bytes,
        "input_truncated": truncated,
        "suffix_counts": dict(sorted(suffixes.items())),
        "files": files_public,
        "deficiency_candidate_count": len(candidates),
        "deficiency_candidates": candidates,
        "operator_review_required": bool(candidates),
        "implementation_allowed": False,
    }
    result["scope_digest"] = _digest({"root": result["source_root_digest"], "scope": safe_scope, "files": [row["file_digest"] for row in files]})
    result["inspection_digest"] = _digest(result)
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    if len(encoded) > MAX_REPORT_BYTES:
        raise ValueError("Project inspection report exceeded bounded size")
    return result


def project_inspection_prompt(report: dict[str, Any]) -> str:
    return (
        "Bounded supervised project inspection:\n"
        f"- Status: {report.get('inspection_status')}.\n"
        f"- Inspected files: {int(report.get('file_count') or 0)}.\n"
        f"- Deficiency candidates requiring review: {int(report.get('deficiency_candidate_count') or 0)}.\n"
        "- Treat findings as candidates, not proven defects. Do not claim a patch, approval, execution, or source change."
    )
