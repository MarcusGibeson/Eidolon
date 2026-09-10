from __future__ import annotations

"""Read-only inventory of Eidolon's version metadata debt.

The project historically copied the current release into many modules because
smoke checks used local constants as evidence. This report separates the active
runtime authority from imports, compatibility constants, historical evidence,
fixtures/generated reports, and documentation. It never rewrites files.
"""

import ast
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable

from release_metadata import RUNTIME_VERSION
from version_roles import build_version_role_contract

VERSION_METADATA_INVENTORY_VERSION = RUNTIME_VERSION
INVENTORY_ID = "pre-v1078.9-version-metadata-centralization-inventory-v1"

ACTIVE_RUNTIME_MARKERS: dict[str, str] = {
    "conscious_agent/dashboard_dispatcher_branch_backfill.py": "DASHBOARD_DISPATCHER_BRANCH_BACKFILL_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_THREE_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v3.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_THREE_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep_v2.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V2_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep_v3.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V3_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v2.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v3.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_helper_consolidation.py": "DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_VERSION",
    "conscious_agent/install_release_segment_runner_timeout_decomposition.py": "INSTALL_RELEASE_SEGMENT_RUNNER_TIMEOUT_DECOMPOSITION_VERSION",
    "conscious_agent/manifest_fixture_receipt_consolidation.py": "MANIFEST_FIXTURE_RECEIPT_CONSOLIDATION_VERSION",
    "conscious_agent/review_surface_shared.py": "REVIEW_SURFACE_SHARED_VERSION",
    "conscious_agent/sandbox_backend_adapter.py": "SANDBOX_BACKEND_ADAPTER_VERSION",
    "conscious_agent/self_maintenance.py": "SELF_MAINTENANCE_VERSION",
    "conscious_agent/dashboard.py": "DASHBOARD_VERSION",
    "conscious_agent/api_server.py": "API_VERSION",
    "conscious_agent/release_packaging.py": "RELEASE_PACKAGING_VERSION",
    "conscious_agent/release_pipeline.py": "RELEASE_PIPELINE_VERSION",
    "conscious_agent/code_patch_release.py": "CODE_PATCH_RELEASE_VERSION",
    "conscious_agent/approval_release_workflow.py": "APPROVAL_RELEASE_VERSION",
    "conscious_agent/autonomy_phase_zero_readiness_harness.py": "AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION",
    "conscious_agent/release_installation.py": "RELEASE_INSTALLATION_VERSION",
    "conscious_agent/workspace_orchestration.py": "WORKSPACE_ORCHESTRATION_VERSION",
    "conscious_agent/runtime_registry.py": "RUNTIME_REGISTRY_VERSION",
    "conscious_agent/governance_reports.py": "GOVERNANCE_REPORTS_VERSION",
    "conscious_agent/package_integrity.py": "PACKAGE_INTEGRITY_VERSION",
    "conscious_agent/version_state.py": "VERSION_STATE_VERSION",
    "conscious_agent/surface_parity.py": "SURFACE_PARITY_VERSION",
    "conscious_agent/verification_planning.py": "VERIFICATION_PLANNING_VERSION",
    "conscious_agent/identity_expression.py": "IDENTITY_EXPRESSION_VERSION",
    "conscious_agent/self_maintenance_refactor_registry.py": "SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION",
    "conscious_agent/minimal_live_change_replay.py": "MINIMAL_LIVE_CHANGE_REPLAY_VERSION",
    "conscious_agent/current_state_integrity_staleness_hardening.py": "CURRENT_STATE_INTEGRITY_STALENESS_HARDENING_VERSION",
    "conscious_agent/current_version_staleness_audit.py": "CURRENT_VERSION_STALENESS_AUDIT_VERSION",
    "conscious_agent/registry_navigation_smoke_consolidation.py": "MODULE_VERSION",
    "conscious_agent/operational_readiness.py": "OPERATIONAL_READINESS_VERSION",
    "conscious_agent/desktop_setup_helper.py": "SETUP_VERSION",
    "conscious_agent/desktop_onboarding_wizard.py": "ONBOARDING_VERSION",
    "conscious_agent/dashboard_route_registry.py": "DASHBOARD_ROUTE_REGISTRY_VERSION",
    "conscious_agent/dashboard_renderer_metadata.py": "DASHBOARD_RENDERER_METADATA_VERSION",
    "conscious_agent/source_surface_manifest.py": "SOURCE_SURFACE_MANIFEST_VERSION",
    "conscious_agent/api_server_dispatch_shared.py": "API_SERVER_DISPATCH_SHARED_VERSION",
    "conscious_agent/smoke_check_shared.py": "SMOKE_CHECK_SHARED_VERSION",
    "conscious_agent/smoke_segment_registry.py": "SMOKE_SEGMENT_REGISTRY_VERSION",
    "tools/smoke_registry_check_rows.py": "SMOKE_REGISTRY_CHECK_ROWS_VERSION",
    "tools/smoke_registry_metadata.py": "SMOKE_REGISTRY_METADATA_VERSION",
    "tools/smoke_result_formatting.py": "SMOKE_RESULT_FORMATTING_VERSION",
}
BASE_ACTIVE_RUNTIME_MARKERS = dict(ACTIVE_RUNTIME_MARKERS)


def _audited_runtime_markers(root: Path) -> dict[str, str]:
    """Read the audited marker mapping without importing the audit module.

    Importing that large historical validator merely to obtain one literal dict
    made package import and cold inventory timing depend on unrelated module
    initialization.  Static extraction is deterministic and side-effect free.
    """
    audit_path = root / "conscious_agent" / "current_version_staleness_audit.py"
    try:
        tree = ast.parse(audit_path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError):
        return {}
    for node in tree.body:
        target_name: str | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value = node.value
        if target_name != "CURRENT_SURFACE_VERSION_MARKERS" or value is None:
            continue
        try:
            payload = ast.literal_eval(value)
        except (ValueError, TypeError):
            return {}
        if isinstance(payload, dict):
            return {str(key): str(marker) for key, marker in payload.items() if isinstance(key, str) and isinstance(marker, str)}
    return {}



HISTORICAL_PATH_TOKENS = (
    "archive", "historical", "checkpoint", "trial", "prep", "backfill",
    "decomposition", "v1073", "release_history", "legacy",
)
FIXTURE_REPORT_PATH_TOKENS = (
    "fixture", "generated", "receipt", "report", "review_packet", "preview",
)


def _assignment_rows(path: Path, text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    rows: list[dict[str, Any]] = []
    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        if value is None:
            continue
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            literal = value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None
            alias = value.id if isinstance(value, ast.Name) else None
            if literal and literal.replace(".", "").isdigit():
                rows.append({"name": target.id, "value": literal, "kind": "literal", "line": node.lineno})
            elif alias == "RUNTIME_VERSION":
                rows.append({"name": target.id, "value": RUNTIME_VERSION, "kind": "runtime_import", "line": node.lineno})
    return rows


def _category(rel: str, row: dict[str, Any], text: str, active_runtime_markers: dict[str, str]) -> str:
    lowered = rel.lower()
    if rel == "conscious_agent/release_metadata.py" and row["name"] == "WORKING_SOURCE_VERSION":
        return "runtime_authority"
    if row["kind"] == "runtime_import":
        return "active_runtime_import"
    if active_runtime_markers.get(rel) == row["name"]:
        return "active_runtime_literal_remaining"
    if any(token in lowered for token in FIXTURE_REPORT_PATH_TOKENS):
        return "fixture_or_generated_report"
    if any(token in lowered for token in HISTORICAL_PATH_TOKENS):
        return "historical_evidence"
    if "EXPECTED_CURRENT_VERSION" in text or "CURRENT_VERSION" in text:
        return "compatibility_check_constant"
    return "compatibility_constant"


RELEASE_OWNED_SOURCE_ROOTS: tuple[str, ...] = ("conscious_agent", "tools")
RELEASE_OWNED_ROOT_FILES: tuple[str, ...] = ("eidolon.py", "release_metadata.py")
EXCLUDED_SOURCE_DIR_NAMES = frozenset({
    ".git", ".venv", "venv", "env", "__pycache__", "sandbox",
    "retired_evidence_quarantine", "quarantine", "runtime", "logs", "data",
    "build", "dist", "node_modules", "trial_workspaces", "copied_workspaces",
})


def _release_owned_python_files(root: Path) -> list[Path]:
    """Return release-owned Python files with one scandir pass per directory.

    ``Path.rglob`` performs several redundant metadata calls on Windows.  The
    inventory only needs regular, non-followed source files, so an explicit
    scandir walk is both safer around indirection and substantially cheaper on
    cold long-path extractions.
    """
    paths: list[Path] = []

    def visit(directory: Path) -> None:
        try:
            entries = list(os.scandir(directory))
        except OSError:
            return
        for entry in entries:
            if entry.name in EXCLUDED_SOURCE_DIR_NAMES:
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    visit(Path(entry.path))
                elif entry.name.endswith(".py") and entry.is_file(follow_symlinks=False):
                    paths.append(Path(entry.path))
            except OSError:
                continue

    for rel_root in RELEASE_OWNED_SOURCE_ROOTS:
        directory = root / rel_root
        if directory.is_dir():
            visit(directory)
    for name in RELEASE_OWNED_ROOT_FILES:
        path = root / name
        if path.is_file():
            paths.append(path)
    return sorted(set(paths), key=lambda item: item.relative_to(root).as_posix())


_VERSION_ASSIGNMENT_HINT = re.compile(
    rb"(?m)^[ \t]*[A-Za-z_][A-Za-z0-9_]*(?:[ \t]*:[^=\n]+)?[ \t]*=[ \t]*(?:RUNTIME_VERSION\b|[\"\'][0-9]+(?:\.[0-9]+)+[\"\'])"
)
_TOP_LEVEL_VERSION_ASSIGNMENT = re.compile(
    rb"(?m)^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:[ \t]*:[^=\n]+)?[ \t]*=[ \t]*(?:(?P<runtime>RUNTIME_VERSION)\b|(?P<quote>[\"\'])(?P<literal>[0-9]+(?:\.[0-9]+)*)(?P=quote))"
)


def _fast_assignment_rows(raw: bytes) -> list[dict[str, Any]]:
    """Extract the simple top-level constants used by the version inventory."""
    rows: list[dict[str, Any]] = []
    for match in _TOP_LEVEL_VERSION_ASSIGNMENT.finditer(raw):
        name = match.group("name").decode("ascii")
        literal = match.group("literal")
        rows.append({
            "name": name,
            "value": RUNTIME_VERSION if match.group("runtime") else literal.decode("ascii"),
            "kind": "runtime_import" if match.group("runtime") else "literal",
            "line": raw.count(b"\n", 0, match.start()) + 1,
        })
    return rows


def build_version_metadata_inventory(
    root_dir: str | Path | None = None,
    *,
    use_text_prefilter: bool = True,
) -> dict[str, Any]:
    started = time.perf_counter()
    root = Path(root_dir or Path(__file__).resolve().parents[1]).resolve()
    source_paths = _release_owned_python_files(root)
    active_runtime_markers = dict(BASE_ACTIVE_RUNTIME_MARKERS)
    active_runtime_markers.update(_audited_runtime_markers(root))
    active_runtime_marker_files = frozenset(active_runtime_markers)

    assignment_rows: list[dict[str, Any]] = []
    scope_digest = hashlib.sha256()
    parsed_file_count = 0
    prefilter_skipped_count = 0
    source_bytes_read = 0
    for path in source_paths:
        rel = path.relative_to(root).as_posix()
        try:
            raw = path.read_bytes()
        except OSError:
            raw = b""
        source_bytes_read += len(raw)
        scope_digest.update(rel.encode("utf-8"))
        scope_digest.update(b"\0")
        scope_digest.update(hashlib.sha256(raw).digest())
        if use_text_prefilter and not _VERSION_ASSIGNMENT_HINT.search(raw):
            prefilter_skipped_count += 1
            continue
        text = raw.decode("utf-8", errors="ignore")
        rows = _fast_assignment_rows(raw)
        expected_marker = active_runtime_markers.get(rel)
        # Audited active markers must never disappear because a source uses an
        # unusual formatting form. Fall back to AST only for that file or when
        # the prefilter found a candidate but the fast scanner found nothing.
        if (expected_marker and not any(row["name"] == expected_marker for row in rows)) or not rows:
            parsed_file_count += 1
            rows = _assignment_rows(path, text)
        for row in rows:
            assignment_rows.append({
                "path": rel,
                **row,
                "category": _category(rel, row, text, active_runtime_markers),
            })

    category_counts: dict[str, int] = {}
    for row in assignment_rows:
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1

    active_remaining = [row for row in assignment_rows if row["category"] == "active_runtime_literal_remaining"]
    compatibility_inventory = sorted({row["path"] for row in assignment_rows if row["category"] in {
        "compatibility_check_constant", "compatibility_constant", "historical_evidence", "fixture_or_generated_report"
    }})

    documentation_occurrences: list[dict[str, Any]] = []
    for name in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"):
        path = root / name
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            documentation_occurrences.append({"path": name, "runtime_version_occurrences": text.count(RUNTIME_VERSION)})

    authority_ok = category_counts.get("runtime_authority", 0) == 1
    active_imports_ok = len(active_remaining) == 0 and category_counts.get("active_runtime_import", 0) >= 25
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "version": RUNTIME_VERSION,
        "inventory_id": INVENTORY_ID,
        "status": "pass" if authority_ok and active_imports_ok else "blocked",
        "ok": authority_ok and active_imports_ok,
        "scan_scope": {
            "source_roots": list(RELEASE_OWNED_SOURCE_ROOTS),
            "root_files": list(RELEASE_OWNED_ROOT_FILES),
            "excluded_directory_names": sorted(EXCLUDED_SOURCE_DIR_NAMES),
            "runtime_data_scanned": False,
            "sandbox_evidence_scanned": False,
            "quarantine_scanned": False,
            "virtual_environments_scanned": False,
            "copied_workspaces_scanned": False,
        },
        "scanned_source_file_count": len(source_paths),
        "scanned_source_scope_sha256": scope_digest.hexdigest(),
        "source_bytes_read": source_bytes_read,
        "text_prefilter_enabled": use_text_prefilter,
        "ast_parsed_source_file_count": parsed_file_count,
        "fast_scanned_source_file_count": len(source_paths) - prefilter_skipped_count,
        "prefilter_skipped_source_file_count": prefilter_skipped_count,
        "elapsed_ms": elapsed_ms,
        "python_assignment_count": len(assignment_rows),
        "python_file_count": len({row["path"] for row in assignment_rows}),
        "category_counts": category_counts,
        "runtime_authority": "conscious_agent/release_metadata.py:WORKING_SOURCE_VERSION",
        "version_roles": build_version_role_contract(root),
        "installed_version_claimed": False,
        "candidate_version_claimed_as_installed": False,
        "active_runtime_marker_file_count": len(active_runtime_marker_files),
        "active_runtime_literal_remaining": active_remaining,
        "remaining_compatibility_file_count": len(compatibility_inventory),
        "remaining_compatibility_files": compatibility_inventory,
        "documentation_occurrences": documentation_occurrences,
        "data_json_occurrences": [],
        "historical_values_preserved": True,
        "mechanical_full_tree_rewrite_performed": False,
        "deterministic_release_owned_scope": True,
        "recommended_followup": "Migrate compatibility constants only when their owning proof gate is redesigned to distinguish origin version from last-verified release.",
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Inventory active, compatibility, historical, fixture, and documentation version metadata.")
    parser.add_argument("--root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_version_metadata_inventory(args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Version metadata inventory: {report['status']}")
        print(f"Python assignments: {report['python_assignment_count']} across {report['python_file_count']} files")
        for category, count in sorted(report["category_counts"].items()):
            print(f"- {category}: {count}")
        print(f"Remaining compatibility files: {report['remaining_compatibility_file_count']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
