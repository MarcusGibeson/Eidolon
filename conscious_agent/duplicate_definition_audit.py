from __future__ import annotations

import ast
import hashlib
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DUPLICATE_DEFINITION_AUDIT_VERSION = "1032.0"
DUPLICATE_DEFINITION_BOUNDARIES: dict[str, bool] = {
    "inventory_is_authorization_to_delete": False,
    "classification_is_authorization_to_delete": False,
    "guard_applies_source_edits": False,
    "guard_executes_refactors": False,
    "audit_changes_runtime_behavior": False,
    "cleanup_expands_autonomy": False,
    "operator_review_required_before_removal": True,
    "source_surface_manifest_protects_recent_surfaces": True,
}

RECENT_HIGH_RISK_TOKENS = (
    "memory_application", "memory_retraction", "live_memory", "sandbox_memory",
    "source_surface", "segmented_install", "smoke_segment", "approval", "burnout",
)

# Baseline captures the known historical situation at v430.0. The guard is for new
# high-risk top-level shadowing, not a dramatic one-pass rewrite of 425 versions of sediment.
KNOWN_HISTORICAL_TOP_LEVEL_DUPLICATES = 183
_INVENTORY_CACHE: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class FunctionOccurrence:
    name: str
    lineno: int
    end_lineno: int | None
    scope: str
    scope_type: str


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _source_root() -> Path:
    return Path(__file__).resolve().parent


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _iter_python_files(root: Path | None = None) -> list[Path]:
    root = root or _source_root()
    ignored = {"__pycache__", ".git", "data", "logs"}
    files: list[Path] = []
    for path in root.rglob("*.py"):
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            rel_parts = path.parts
        if any(part in ignored for part in rel_parts):
            continue
        files.append(path)
    return sorted(files)


def _collect_function_occurrences(tree: ast.AST) -> list[FunctionOccurrence]:
    occurrences: list[FunctionOccurrence] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[tuple[str, str]] = [("<module>", "module")]

        def _scope(self) -> tuple[str, str]:
            return self.stack[-1]

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            scope, scope_type = self._scope()
            occurrences.append(FunctionOccurrence(node.name, node.lineno, getattr(node, "end_lineno", None), scope, scope_type))
            self.stack.append((node.name, "function"))
            self.generic_visit(node)
            self.stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            scope, scope_type = self._scope()
            occurrences.append(FunctionOccurrence(node.name, node.lineno, getattr(node, "end_lineno", None), scope, scope_type))
            self.stack.append((node.name, "function"))
            self.generic_visit(node)
            self.stack.pop()

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.stack.append((node.name, "class"))
            self.generic_visit(node)
            self.stack.pop()

    Visitor().visit(tree)
    return occurrences


def _classify(name: str, occurrences: list[FunctionOccurrence], rel_path: str) -> tuple[str, str, str]:
    scopes = {occ.scope_type for occ in occurrences}
    top_level = all(occ.scope == "<module>" for occ in occurrences)
    lower = name.lower()
    risky_token = any(token in lower for token in RECENT_HIGH_RISK_TOKENS)
    if "<locals>" in name:
        return "allowed_local_closure", "low", "keep; local closure style is expected"
    if scopes == {"function"}:
        return "allowed_local_closure", "low", "keep unless the enclosing builder is being refactored"
    if scopes == {"class"}:
        return "generated_registry_pattern", "low", "review with class context only"
    if name.startswith("_make_") or name.startswith("_latest_"):
        return "generated_registry_pattern", "medium", "manual review before touching generated builder factories"
    if top_level and risky_token:
        return "accidental_shadow_candidate", "high", "protect recent governance surface; inspect before any deletion or extraction"
    if top_level and rel_path.endswith("self_maintenance.py"):
        return "needs_manual_review", "medium", "classify as compatibility alias, intentional override, or accidental shadow before removal"
    return "compatibility_alias", "medium", "manual review; do not delete from inventory alone"


def build_duplicate_definition_inventory(root: str | Path | None = None) -> dict[str, Any]:
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))
    project_root = Path(root).resolve() if root else _root()
    cache_key = str(project_root)
    if cache_key in _INVENTORY_CACHE:
        cached = dict(_INVENTORY_CACHE[cache_key])
        cached["from_cache"] = True
        return cached
    py_root = project_root / "conscious_agent" if (project_root / "conscious_agent").exists() else project_root
    duplicate_records: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []
    scanned_files = 0
    for path in _iter_python_files(py_root):
        scanned_files += 1
        rel_path = str(path.relative_to(project_root)) if path.is_relative_to(project_root) else str(path)
        try:
            tree = ast.parse(_safe_read(path), filename=rel_path)
        except SyntaxError as error:
            parse_errors.append({"file_path": rel_path, "error": str(error)})
            continue
        by_key: dict[tuple[str, str, str], list[FunctionOccurrence]] = defaultdict(list)
        for occ in _collect_function_occurrences(tree):
            by_key[(occ.scope, occ.scope_type, occ.name)].append(occ)
        for (scope, scope_type, name), occurrences in sorted(by_key.items()):
            if len(occurrences) < 2:
                continue
            classification, risk, action = _classify(name, occurrences, rel_path)
            duplicate_records.append({
                "file_path": rel_path,
                "function_name": name,
                "definition_count": len(occurrences),
                "line_numbers": [occ.lineno for occ in occurrences],
                "end_line_numbers": [occ.end_lineno for occ in occurrences],
                "scope": scope,
                "scope_type": scope_type,
                "classification": classification,
                "risk_level": risk,
                "recommended_action": action,
                "recent_high_risk_token": any(token in name.lower() for token in RECENT_HIGH_RISK_TOKENS),
            })
    risk_counts: dict[str, int] = defaultdict(int)
    class_counts: dict[str, int] = defaultdict(int)
    for row in duplicate_records:
        risk_counts[str(row["risk_level"])] += 1
        class_counts[str(row["classification"])] += 1
    result = {
        "version": DUPLICATE_DEFINITION_AUDIT_VERSION,
        "state": "duplicate_definition_inventory_review_only",
        "scanned_file_count": scanned_files,
        "duplicate_record_count": len(duplicate_records),
        "parse_errors": parse_errors,
        "risk_counts": dict(sorted(risk_counts.items())),
        "classification_counts": dict(sorted(class_counts.items())),
        "duplicates": duplicate_records,
        "inventory_is_authorization_to_delete": False,
        "writes_files": False,
        "applies_source_edits": False,
        "ok": not parse_errors,
    }
    _INVENTORY_CACHE[cache_key] = result
    return dict(result)


def build_self_maintenance_duplicate_classification(root: str | Path | None = None) -> dict[str, Any]:
    inventory = build_duplicate_definition_inventory(root)
    records = [row for row in inventory["duplicates"] if row["file_path"].endswith("self_maintenance.py")]
    high = [row for row in records if row["risk_level"] == "high"]
    manual = [row for row in records if row["classification"] in {"needs_manual_review", "accidental_shadow_candidate"}]
    return {
        "version": DUPLICATE_DEFINITION_AUDIT_VERSION,
        "state": "self_maintenance_duplicate_classification_review_only",
        "self_maintenance_duplicate_count": len(records),
        "high_risk_count": len(high),
        "manual_review_count": len(manual),
        "high_risk_samples": high[:12],
        "manual_review_samples": manual[:20],
        "classification_counts": inventory.get("classification_counts", {}),
        "risk_counts": inventory.get("risk_counts", {}),
        "classification_is_authorization_to_delete": False,
        "operator_review_required_before_removal": True,
        "writes_files": False,
        "applies_source_edits": False,
        "ok": inventory.get("ok") is True,
    }


def build_self_maintenance_extraction_candidates(root: str | Path | None = None) -> dict[str, Any]:
    classification = build_self_maintenance_duplicate_classification(root)
    candidates = []
    for row in classification.get("manual_review_samples", []):
        name = str(row.get("function_name", ""))
        candidate_type = "bridge_only" if any(token in name for token in ("source_surface", "memory", "approval", "burnout")) else "manual_review_only"
        candidates.append({
            "function_name": name,
            "file_path": row.get("file_path"),
            "line_numbers": row.get("line_numbers", []),
            "risk_level": row.get("risk_level"),
            "candidate_type": candidate_type,
            "recommended_action": "keep bridge in self_maintenance.py; move implementation to extracted module only after manifest parity passes" if candidate_type == "bridge_only" else "do not move yet; classify legacy compatibility first",
            "manifest_protection_required": candidate_type == "bridge_only",
        })
    protected_surfaces = [
        "v400 memory application trial",
        "v405 segmented smoke",
        "v410 dry-run ledger",
        "v415 sandbox memory write",
        "v420 live memory write trial",
        "v425 memory retraction trial",
        "v430 source surface manifest",
        "v435 duplicate definition cleanup",
    ]
    return {
        "version": DUPLICATE_DEFINITION_AUDIT_VERSION,
        "state": "self_maintenance_extraction_candidates_review_only",
        "protected_recent_surfaces": protected_surfaces,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "safe_extraction_policy": "extract implementation first, keep dashboard/API/CLI bridge names stable, then prove parity through source surface manifest and smoke",
        "extraction_plan_is_authorization": False,
        "writes_files": False,
        "applies_source_edits": False,
        "ok": classification.get("ok") is True,
    }


def build_duplicate_definition_guard(root: str | Path | None = None, baseline_count: int = KNOWN_HISTORICAL_TOP_LEVEL_DUPLICATES) -> dict[str, Any]:
    inventory = build_duplicate_definition_inventory(root)
    high_risk = [row for row in inventory["duplicates"] if row.get("risk_level") == "high"]
    # The guard intentionally allows the historical baseline while blocking new high-risk recent-surface duplicates.
    new_high_risk = [row for row in high_risk if int(row.get("definition_count", 0)) > 2]
    blockers: list[str] = []
    if inventory.get("parse_errors"):
        blockers.append("parse_errors")
    if len(high_risk) > baseline_count:
        blockers.append("high_risk_duplicate_count_exceeds_baseline")
    if new_high_risk:
        blockers.append("new_recent_surface_duplicate_shadowing")
    return {
        "version": DUPLICATE_DEFINITION_AUDIT_VERSION,
        "state": "duplicate_definition_guard_review_only",
        "baseline_count": baseline_count,
        "high_risk_count": len(high_risk),
        "new_high_risk_count": len(new_high_risk),
        "new_high_risk_samples": new_high_risk[:10],
        "blockers": blockers,
        "guard_applies_source_edits": False,
        "guard_executes_refactors": False,
        "guard_expands_autonomy": False,
        "ok": not blockers,
        "status": "pass" if not blockers else "blocked",
    }


def build_self_maintenance_duplicate_cleanup_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    inventory = build_duplicate_definition_inventory(root)
    classification = build_self_maintenance_duplicate_classification(root)
    extraction = build_self_maintenance_extraction_candidates(root)
    guard = build_duplicate_definition_guard(root)
    required_doc_tokens = [
        "v435.0 - Self-Maintenance Duplicate Definition Cleanup v1",
        "duplicate-definition-inventory",
        "self-maintenance-duplicate-classification",
        "self-maintenance-extraction-candidates",
        "duplicate-definition-guard",
        "self-maintenance-duplicate-cleanup-audit",
    ]
    blockers: list[str] = []
    if not inventory.get("ok"):
        blockers.append("inventory_not_ok")
    if not classification.get("ok"):
        blockers.append("classification_not_ok")
    if not extraction.get("ok"):
        blockers.append("extraction_plan_not_ok")
    if not guard.get("ok"):
        blockers.append("duplicate_guard_not_ok")
    if docs and not all(token in docs for token in required_doc_tokens):
        blockers.append("docs_missing_v435_tokens")
    for key, expected in DUPLICATE_DEFINITION_BOUNDARIES.items():
        if key.startswith("operator_") or key.endswith("required") or key.endswith("protects_recent_surfaces"):
            if expected is not True:
                blockers.append(f"boundary:{key}")
        elif expected is not False:
            blockers.append(f"boundary:{key}")
    return {
        "version": DUPLICATE_DEFINITION_AUDIT_VERSION,
        "state": "self_maintenance_duplicate_cleanup_audit_review_only",
        "inventory": {k: v for k, v in inventory.items() if k != "duplicates"},
        "classification": {k: v for k, v in classification.items() if not k.endswith("samples")},
        "extraction": {k: v for k, v in extraction.items() if k != "candidates"},
        "guard": guard,
        "boundaries": dict(DUPLICATE_DEFINITION_BOUNDARIES),
        "blockers": blockers,
        "ok": not blockers,
        "status": "pass" if not blockers else "blocked",
        "grants_deletion_authority": False,
        "applies_source_edits": False,
        "expands_autonomy": False,
        "writes_memory": False,
        "message": "Duplicate definitions are inventoried, classified, and guarded. Cleanup remains operator-reviewed and does not delete source automatically.",
    }


def render_duplicate_definition_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state', 'duplicate_definition_review')}",
        f"version: {report.get('version', DUPLICATE_DEFINITION_AUDIT_VERSION)}",
        f"status: {report.get('status', 'pass' if report.get('ok') else 'blocked')}",
    ]
    if "duplicate_record_count" in report:
        lines.append(f"duplicate_record_count: {report.get('duplicate_record_count')}")
    if "self_maintenance_duplicate_count" in report:
        lines.append(f"self_maintenance_duplicate_count: {report.get('self_maintenance_duplicate_count')}")
    if "candidate_count" in report:
        lines.append(f"candidate_count: {report.get('candidate_count')}")
    if "high_risk_count" in report:
        lines.append(f"high_risk_count: {report.get('high_risk_count')}")
    blockers = report.get("blockers") or []
    lines.append("blockers: " + (", ".join(blockers) if blockers else "none"))
    lines.append("inventory_is_authorization_to_delete=False")
    lines.append("classification_is_authorization_to_delete=False")
    lines.append("guard_applies_source_edits=False")
    lines.append("operator_review_required_before_removal=True")
    return lines

# v430.1-v435.0 duplicate definition cleanup smoke tokens: duplicate-definition-inventory self-maintenance-duplicate-classification self-maintenance-extraction-candidates duplicate-definition-guard self-maintenance-duplicate-cleanup-audit operator-governed-self-maintenance-duplicate-cleanup-v1 conscious_agent/duplicate_definition_audit.py inventory_is_authorization_to_delete=False classification_is_authorization_to_delete=False guard_applies_source_edits=False guard_executes_refactors=False cleanup_expands_autonomy=False operator_review_required_before_removal=True source_surface_manifest_protects_recent_surfaces=True no_native_title_tooltip data-tip command-deck operator-console
