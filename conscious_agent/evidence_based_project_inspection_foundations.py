from __future__ import annotations

"""v1261.0-v1261.2 evidence-based project inspection foundations.

The inspector reuses v1254 project containment and adapter primitives, but raises
its read-only inventory budget so a complete source project can be characterized.
It records only relative source metadata and minimized structural signals.  Raw
source text, operator feedback, provider payloads, conversations, memories, logs,
and private runtime data are never copied into the assessment.
"""

import ast
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from isolated_coding_execution_foundations import (
    AUTHORITY_STATE,
    _file_digest,
    _is_link_like,
    _is_private_or_excluded,
    _is_relevant_source,
    _path_digest,
    _project_type,
    _resolve_project_root,
    _validate_portable_relative,
    _within,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1261.2"
CLAIM_CLASSES = ("observed", "inferred", "assumed", "unknown")
EVIDENCE_KINDS = (
    "source_inventory", "architecture", "tests", "documentation", "configuration",
    "runtime_health", "operator_feedback", "known_limitation", "development_session",
    "environment", "privacy_boundary",
)
MAX_FILES = 5000
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_TEXT_BYTES_PER_FILE = 64 * 1024
MAX_TEXT_SCAN_BYTES = 8 * 1024 * 1024
MAX_PYTHON_PARSE_BYTES = 8 * 1024 * 1024
MAX_PUBLIC_COMPONENTS = 96
MAX_NOTABLE_FILES = 128
MAX_CLAIMS = 256
MAINTENANCE_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b", re.I)
LIMITATION_RE = re.compile(r"\b(known limitation|not implemented|unsupported|desktop review required|todo|fixme)\b", re.I)
TEST_NAME_RE = re.compile(r"(^|/)(test_[^/]+|[^/]+_test)\.(py|js|ts|tsx|jsx|java|cs|rs|go|php)$", re.I)
DOC_NAMES = {"readme.md", "readme.txt", "contributing.md", "changelog.md", "architecture.md", "design.md"}
CONFIG_NAMES = {
    "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "pytest.ini", "package.json",
    "pom.xml", "build.gradle", "build.gradle.kts", "cargo.toml", "go.mod", "composer.json",
    "makefile", "dockerfile", "tsconfig.json", ".editorconfig",
}

DENIED_AUTHORITY = {
    **AUTHORITY_STATE,
    "diagnostic_execution_authorized": False,
    "repair_authorized": False,
    "backlog_creation_authorized": False,
    "priority_selection_authorized": False,
    "self_modification_authorized": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _claim(claim_class: str, code: str, *, confidence: str, evidence_ids: Iterable[str] = (), basis: str = "") -> dict[str, Any]:
    if claim_class not in CLAIM_CLASSES:
        raise ValueError("invalid_claim_class")
    row = {
        "claim_class": claim_class,
        "claim_code": str(code),
        "confidence": str(confidence),
        "evidence_ids": sorted(set(str(x) for x in evidence_ids if x))[:16],
        "basis_code": str(basis),
    }
    row["claim_id"] = f"claim_{_digest(row)[:24]}"
    return row


def _evidence(kind: str, code: str, facts: Mapping[str, Any]) -> dict[str, Any]:
    if kind not in EVIDENCE_KINDS:
        raise ValueError("invalid_evidence_kind")
    clean: dict[str, Any] = {}
    for key, value in sorted(facts.items()):
        if isinstance(value, (bool, int, float)) or value is None:
            clean[str(key)] = value
        elif isinstance(value, str):
            clean[str(key)] = value[:256]
        elif isinstance(value, (list, tuple)):
            clean[str(key)] = [str(x)[:128] for x in value[:32]]
    row = {"kind": kind, "evidence_code": str(code), "facts": clean, "content_minimized": True}
    row["evidence_id"] = f"ev_{_digest(row)[:24]}"
    row["evidence_digest"] = _digest(row)
    return row


def _bounded_inventory(root: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    files: list[dict[str, Any]] = []
    total = 0
    private_count = link_count = irrelevant_count = 0
    stack = [root]
    while stack:
        current = stack.pop()
        if not _within(root, current):
            raise ValueError("project_containment_violation")
        try:
            entries = sorted(os.scandir(current), key=lambda e: e.name.casefold())
        except OSError as exc:
            raise ValueError(f"project_scan_failed:{type(exc).__name__}") from exc
        dirs: list[Path] = []
        for entry in entries:
            path = Path(entry.path)
            try:
                relative = PurePosixPath(path.relative_to(root).as_posix())
            except ValueError as exc:
                raise ValueError("project_containment_violation") from exc
            _validate_portable_relative(relative)
            if _is_private_or_excluded(relative):
                private_count += 1
                continue
            if _is_link_like(path) or not _within(root, path):
                link_count += 1
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    dirs.append(path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    irrelevant_count += 1
                    continue
            except OSError:
                link_count += 1
                continue
            if not _is_relevant_source(relative):
                irrelevant_count += 1
                continue
            size = int(path.stat().st_size)
            total += size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("inspection_total_byte_budget_exceeded")
            rel = relative.as_posix()
            files.append({
                "relative_path": rel,
                "relative_path_digest": _path_digest(rel),
                "content_digest": _file_digest(path),
                "size_bytes": size,
                "suffix": relative.suffix.casefold(),
            })
            if len(files) > MAX_FILES:
                raise ValueError("inspection_file_count_budget_exceeded")
        stack.extend(reversed(dirs))
    files.sort(key=lambda row: str(row["relative_path"]).casefold())
    folded = [str(row["relative_path"]).casefold() for row in files]
    if len(folded) != len(set(folded)):
        raise ValueError("project_casefold_path_collision")
    return files, {
        "file_count": len(files), "total_bytes": total,
        "private_or_excluded_count": private_count,
        "link_or_boundary_rejection_count": link_count,
        "irrelevant_count": irrelevant_count,
    }


def _manifest_digest(files: Sequence[Mapping[str, Any]]) -> str:
    return _digest([
        {"path_digest": row.get("relative_path_digest", ""), "content_digest": row.get("content_digest", ""), "size_bytes": int(row.get("size_bytes") or 0)}
        for row in files
    ])


def _structural_signals(root: Path, files: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    suffixes: Counter[str] = Counter()
    components: Counter[str] = Counter()
    test_files: list[str] = []
    docs: list[str] = []
    configs: list[str] = []
    python_parse_failures = 0
    python_parse_skipped = 0
    maintenance_markers = 0
    limitation_markers = 0
    scan_bytes = 0
    for row in files:
        rel = str(row.get("relative_path") or "")
        pure = PurePosixPath(rel)
        suffix = str(row.get("suffix") or "")
        suffixes[suffix or "[none]"] += 1
        components[pure.parts[0] if len(pure.parts) > 1 else "[root]"] += 1
        name = pure.name.casefold()
        if TEST_NAME_RE.search(rel) or any(part.casefold() in {"test", "tests", "spec", "specs"} for part in pure.parts):
            test_files.append(rel)
        if name in DOC_NAMES or any(part.casefold() == "docs" for part in pure.parts):
            docs.append(rel)
        if name in CONFIG_NAMES:
            configs.append(rel)
        if scan_bytes >= MAX_TEXT_SCAN_BYTES or suffix not in {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".js", ".ts", ".html", ".css"}:
            continue
        try:
            path = root / rel
            raw = path.read_bytes()[:MAX_TEXT_BYTES_PER_FILE]
            scan_bytes += len(raw)
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        maintenance_markers += len(MAINTENANCE_RE.findall(text))
        limitation_markers += len(LIMITATION_RE.findall(text))
        if suffix == ".py":
            # Never parse a truncated Python prefix: a valid large module can end
            # mid-expression at the text-scan budget and masquerade as a syntax
            # failure. Parse the complete bounded source file or record a skip.
            try:
                size_bytes = int(row.get("size_bytes") or 0)
                if size_bytes > MAX_PYTHON_PARSE_BYTES:
                    python_parse_skipped += 1
                else:
                    parse_text = path.read_text(encoding="utf-8")
                    ast.parse(parse_text, filename=rel)
            except (OSError, UnicodeDecodeError):
                python_parse_skipped += 1
            except (SyntaxError, ValueError):
                python_parse_failures += 1
    notable = sorted(set(test_files + docs + configs), key=str.casefold)[:MAX_NOTABLE_FILES]
    return {
        "suffix_counts": dict(sorted(suffixes.items())),
        "components": [{"component": key, "file_count": count} for key, count in components.most_common(MAX_PUBLIC_COMPONENTS)],
        "test_file_count": len(set(test_files)),
        "documentation_file_count": len(set(docs)),
        "configuration_file_count": len(set(configs)),
        "python_parse_failure_count": python_parse_failures,
        "python_parse_skipped_count": python_parse_skipped,
        "maintenance_marker_count": maintenance_markers,
        "limitation_marker_count": limitation_markers,
        "text_scan_bytes": scan_bytes,
        "notable_files": notable,
    }


def inspect_project_evidence(source_root: str | Path) -> dict[str, Any]:
    """Build a deterministic, read-only project evidence snapshot."""
    root = _resolve_project_root(source_root)
    files, stats = _bounded_inventory(root)
    project = _project_type(files)
    signals = _structural_signals(root, files)
    manifest = _manifest_digest(files)
    evidence: list[dict[str, Any]] = []
    evidence.append(_evidence("source_inventory", "bounded_source_inventory", {
        "file_count": stats["file_count"], "total_bytes": stats["total_bytes"],
        "private_or_excluded_count": stats["private_or_excluded_count"],
        "link_or_boundary_rejection_count": stats["link_or_boundary_rejection_count"],
        "source_manifest_digest": manifest,
    }))
    evidence.append(_evidence("architecture", "project_adapter_detection", {
        "project_type": project.get("project_type", ""), "adapter_id": project.get("adapter_id", ""),
        "adapter_state": project.get("adapter_state", ""), "component_count": len(signals["components"]),
    }))
    evidence.append(_evidence("tests", "test_surface_inventory", {"test_file_count": signals["test_file_count"]}))
    evidence.append(_evidence("documentation", "documentation_inventory", {"documentation_file_count": signals["documentation_file_count"]}))
    evidence.append(_evidence("configuration", "configuration_inventory", {"configuration_file_count": signals["configuration_file_count"]}))
    evidence.append(_evidence("privacy_boundary", "inspection_exclusion_summary", {
        "private_or_excluded_count": stats["private_or_excluded_count"], "link_or_boundary_rejection_count": stats["link_or_boundary_rejection_count"],
        "raw_private_content_read": False,
    }))
    if signals["maintenance_marker_count"] or signals["limitation_marker_count"]:
        evidence.append(_evidence("known_limitation", "source_maintenance_signal_summary", {
            "maintenance_marker_count": signals["maintenance_marker_count"], "limitation_marker_count": signals["limitation_marker_count"]
        }))
    ev = {row["evidence_code"]: row for row in evidence}
    claims: list[dict[str, Any]] = [
        _claim("observed", "source_inventory_observed", confidence="high", evidence_ids=[ev["bounded_source_inventory"]["evidence_id"]], basis="sealed_source_manifest"),
        _claim("observed", "project_type_observed", confidence="high" if project.get("adapter_id") else "medium", evidence_ids=[ev["project_adapter_detection"]["evidence_id"]], basis="adapter_and_suffix_evidence"),
        _claim("observed", "test_surface_observed", confidence="high", evidence_ids=[ev["test_surface_inventory"]["evidence_id"]], basis="bounded_filename_inventory"),
        _claim("observed", "documentation_surface_observed", confidence="high", evidence_ids=[ev["documentation_inventory"]["evidence_id"]], basis="bounded_filename_inventory"),
        _claim("inferred", "architecture_component_boundaries_inferred", confidence="medium", evidence_ids=[ev["project_adapter_detection"]["evidence_id"]], basis="top_level_source_distribution"),
        _claim("assumed", "inspected_snapshot_represents_requested_project", confidence="medium", evidence_ids=[ev["bounded_source_inventory"]["evidence_id"]], basis="caller_supplied_explicit_root"),
        _claim("unknown", "runtime_health_unknown", confidence="none", basis="runtime_evidence_not_supplied"),
        _claim("unknown", "operator_feedback_unknown", confidence="none", basis="operator_feedback_not_supplied"),
        _claim("unknown", "executed_test_outcome_unknown", confidence="none", evidence_ids=[ev["test_surface_inventory"]["evidence_id"]], basis="tests_not_executed_by_inspection"),
        _claim("unknown", "development_session_history_unknown", confidence="none", basis="session_evidence_not_supplied"),
    ]
    if signals["python_parse_failure_count"]:
        claims.append(_claim("observed", "python_parse_failure_observed", confidence="high", evidence_ids=[ev["bounded_source_inventory"]["evidence_id"]], basis="bounded_ast_parse"))
    if signals["maintenance_marker_count"] or signals["limitation_marker_count"]:
        claims.append(_claim("observed", "maintenance_or_limitation_signals_observed", confidence="medium", evidence_ids=[ev["source_maintenance_signal_summary"]["evidence_id"]], basis="bounded_marker_scan_without_raw_text"))
    report = {
        "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "status": "evidence_based_project_inspection_ready", "inspection_mode": "read_only_evidence_snapshot",
        "target_path_digest": hashlib.sha256(str(root).encode()).hexdigest(),
        "source_manifest_digest": manifest, "project_type": project.get("project_type", ""), "adapter_id": project.get("adapter_id", ""),
        "adapter_state": project.get("adapter_state", ""), "marker_codes": list(project.get("marker_codes") or []),
        **stats, **signals,
        "evidence": evidence, "claims": claims[:MAX_CLAIMS],
        "claim_class_counts": {kind: sum(1 for row in claims if row["claim_class"] == kind) for kind in CLAIM_CLASSES},
        "raw_source_content_stored": False, "raw_operator_feedback_stored": False, "raw_runtime_payload_stored": False,
        "private_runtime_discovery_performed": False, "content_minimized": True, "read_only": True,
        "development_proposal_created": False, "backlog_item_created": False,
        **DENIED_AUTHORITY,
    }
    report["inspection_digest"] = _digest(report)
    return report


def public_project_evidence_inspection(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(report.get("ok")), "status": str(report.get("status") or ""),
        "project_type": str(report.get("project_type") or ""), "adapter_id": str(report.get("adapter_id") or ""),
        "source_manifest_digest": str(report.get("source_manifest_digest") or ""),
        "file_count": int(report.get("file_count") or 0), "total_bytes": int(report.get("total_bytes") or 0),
        "test_file_count": int(report.get("test_file_count") or 0), "documentation_file_count": int(report.get("documentation_file_count") or 0),
        "configuration_file_count": int(report.get("configuration_file_count") or 0),
        "component_count": len(report.get("components") or []), "claim_class_counts": dict(report.get("claim_class_counts") or {}),
        "evidence_count": len(report.get("evidence") or []), "inspection_digest": str(report.get("inspection_digest") or ""),
        "raw_paths_exposed": False, "raw_source_content_exposed": False, "private_runtime_content_exposed": False,
        "content_minimized": True, "read_only": True, **DENIED_AUTHORITY,
    }


__all__ = [
    "SCHEMA_VERSION", "CONTRACT_VERSION", "CLAIM_CLASSES", "EVIDENCE_KINDS", "DENIED_AUTHORITY",
    "inspect_project_evidence", "public_project_evidence_inspection",
]
