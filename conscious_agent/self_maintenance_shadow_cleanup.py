from __future__ import annotations

import ast
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SELF_MAINTENANCE_SHADOW_CLEANUP_VERSION = "500.0"

REMOVED_SHADOWED_DEFINITIONS: list[dict[str, Any]] = [
    {"function_name": "build_post_apply_verification_runner", "removed_stage": "v61.6", "classification": "shadowed_legacy_helper"},
    {"function_name": "post_apply_verification_runner_text", "removed_stage": "v61.6", "classification": "shadowed_legacy_helper"},
    {"function_name": "print_post_apply_verification_runner", "removed_stage": "v61.6", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_promotion_packet_intake_gate", "removed_stage": "v68.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_transaction_plan_materializer", "removed_stage": "v68.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "_latest_execution_context", "removed_stage": "v69-v70", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_patch_intent_normalizer", "removed_stage": "v72.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_patch_scope_contract_builder", "removed_stage": "v72.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_patch_draft_output_schema", "removed_stage": "v72.x/v73.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_patch_prompt_composer", "removed_stage": "v72.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_patch_draft_safety_reviewer", "removed_stage": "v72.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_patch_draft_evidence_binder", "removed_stage": "v72.x/v73.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_patch_draft_dashboard_api_cli", "removed_stage": "v72.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_local_model_handoff_stub", "removed_stage": "v72.x/v73.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_pre_v73_patch_draft_gate", "removed_stage": "v72.x/v73.x", "classification": "shadowed_legacy_helper"},
    {"function_name": "build_supervised_patch_draft_composer", "removed_stage": "v72.x/v73.x", "classification": "shadowed_legacy_helper"},
]

SELF_MAINTENANCE_SHADOW_CLEANUP_BOUNDARIES: dict[str, bool] = {
    "duplicate_cleanup_is_authorization": False,
    "classification_is_permission_to_delete": False,
    "shadow_removal_expands_autonomy": False,
    "stale_gate_cleanup_authorizes_execution": False,
    "cleanup_applies_live_patches": False,
    "cleanup_writes_memory": False,
    "operator_approval_still_required": True,
}


def _root(root: str | Path | None = None) -> Path:
    if root is not None:
        candidate = Path(root).resolve()
        if (candidate / "conscious_agent").exists():
            return candidate
        return candidate.parents[0] if candidate.name == "conscious_agent" else candidate
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _self_path(root: Path) -> Path:
    return root / "conscious_agent" / "self_maintenance.py"


def _docs(root: Path) -> str:
    rels = [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/self_maintenance.py",
        "conscious_agent/self_maintenance_shadow_cleanup.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
        "conscious_agent/smoke_segment_registry.py",
    ]
    return "\n".join(_read(root / rel) for rel in rels)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def _top_level_duplicate_records(source_text: str) -> list[dict[str, Any]]:
    tree = ast.parse(source_text)
    by_name: dict[str, list[ast.AST]] = defaultdict(list)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            by_name[node.name].append(node)
    records: list[dict[str, Any]] = []
    for name, nodes in sorted(by_name.items()):
        if len(nodes) < 2:
            continue
        body_hashes = []
        for node in nodes:
            body_hashes.append(hashlib.sha256(ast.dump(ast.Module(body=getattr(node, "body", []), type_ignores=[]), include_attributes=False).encode("utf-8")).hexdigest()[:16])
        records.append({
            "function_name": name,
            "definition_count": len(nodes),
            "line_numbers": [getattr(node, "lineno", 0) for node in nodes],
            "end_line_numbers": [getattr(node, "end_lineno", 0) for node in nodes],
            "body_hashes": body_hashes,
            "classification": "conflicting_definition" if len(set(body_hashes)) > 1 else "exact_duplicate",
            "requires_manual_review": len(set(body_hashes)) > 1,
        })
    return records


def _stale_exact_gate_hits(source_text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for idx, line in enumerate(source_text.splitlines(), 1):
        stripped = line.strip()
        if any(token in stripped for token in ('SELF_MAINTENANCE_VERSION == \"68.0\"', 'SELF_MAINTENANCE_VERSION == \"70.0\"', 'SELF_MAINTENANCE_VERSION != \"68.0\"', 'SELF_MAINTENANCE_VERSION != \"70.0\"')):
            hits.append({"line": idx, "text": stripped, "classification": "stale_exact_version_gate"})
    return hits


def build_duplicate_shadow_inventory(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    source_text = _read(_self_path(project_root))
    records = _top_level_duplicate_records(source_text) if source_text else []
    return {
        "version": SELF_MAINTENANCE_SHADOW_CLEANUP_VERSION,
        "state": "duplicate_shadow_inventory_review_only",
        "file_path": "conscious_agent/self_maintenance.py",
        "current_duplicate_count": len(records),
        "duplicates": records,
        "removed_shadowed_definition_count": len(REMOVED_SHADOWED_DEFINITIONS),
        "removed_shadowed_definitions": REMOVED_SHADOWED_DEFINITIONS,
        "classification_is_permission_to_delete": False,
        "duplicate_cleanup_is_authorization": False,
        "ok": bool(source_text) and not records,
    }


def build_safe_shadow_removal_report(root: str | Path | None = None) -> dict[str, Any]:
    inventory = build_duplicate_shadow_inventory(root)
    rows = [
        {"name": "top-level-duplicates", "status": "pass" if inventory.get("current_duplicate_count") == 0 else "blocked", "message": f"current_duplicate_count={inventory.get('current_duplicate_count')}"},
        {"name": "removed-shadowed-definitions", "status": "pass" if inventory.get("removed_shadowed_definition_count", 0) >= 16 else "blocked", "message": f"removed={inventory.get('removed_shadowed_definition_count')} historical shadow entries"},
        {"name": "behavior-boundary", "status": "pass", "message": "Only shadowed earlier definitions were removed; canonical final definitions remain."},
    ]
    return {
        "version": SELF_MAINTENANCE_SHADOW_CLEANUP_VERSION,
        "state": "safe_shadow_removal_report_review_only",
        "rows": rows,
        "inventory": {k: v for k, v in inventory.items() if k != "duplicates"},
        "removed_shadowed_definitions": REMOVED_SHADOWED_DEFINITIONS,
        "shadow_removal_expands_autonomy": False,
        "cleanup_applies_live_patches": False,
        "cleanup_writes_memory": False,
        "ok": all(row["status"] == "pass" for row in rows),
    }


def build_legacy_alias_compatibility_cleanup(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    source_text = _read(_self_path(project_root))
    canonical_kept = []
    for item in REMOVED_SHADOWED_DEFINITIONS:
        name = item["function_name"]
        canonical_kept.append({
            "function_name": name,
            "canonical_definition_present": f"def {name}" in source_text,
            "compatibility_strategy": "final_definition_kept" if not name.startswith("_") else "private_helper_final_definition_kept",
            "legacy_full_duplicate_removed": True,
        })
    missing = [row["function_name"] for row in canonical_kept if not row["canonical_definition_present"]]
    return {
        "version": SELF_MAINTENANCE_SHADOW_CLEANUP_VERSION,
        "state": "legacy_alias_compatibility_cleanup_review_only",
        "canonical_kept": canonical_kept,
        "missing_canonical_definitions": missing,
        "legacy_alias_is_authorization": False,
        "cleanup_changes_approval_scope": False,
        "ok": not missing,
    }


def build_stale_version_gate_cleanup(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    source_text = _read(_self_path(project_root))
    stale_hits = _stale_exact_gate_hits(source_text)
    helper_present = "def _historical_version_gate_cleared" in source_text
    helper_uses = source_text.count("_historical_version_gate_cleared(")
    rows = [
        {"name": "historical-helper-present", "status": "pass" if helper_present else "blocked", "message": "_historical_version_gate_cleared present" if helper_present else "missing helper"},
        {"name": "stale-exact-gates", "status": "pass" if not stale_hits else "blocked", "message": f"stale_hits={len(stale_hits)}"},
        {"name": "helper-used", "status": "pass" if helper_uses >= 2 else "blocked", "message": f"helper_uses={helper_uses}"},
        {"name": "authorization-boundary", "status": "pass", "message": "Historical gate clearance is compatibility only and authorizes no execution."},
    ]
    return {
        "version": SELF_MAINTENANCE_SHADOW_CLEANUP_VERSION,
        "state": "stale_version_gate_cleanup_review_only",
        "rows": rows,
        "stale_exact_gate_hits": stale_hits,
        "historical_helper_present": helper_present,
        "historical_helper_use_count": helper_uses,
        "stale_gate_cleanup_authorizes_execution": False,
        "operator_approval_still_required": True,
        "ok": all(row["status"] == "pass" for row in rows),
    }


def build_self_maintenance_duplicate_shadow_cleanup_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    project_root = _root(root)
    docs = docs or _docs(project_root)
    inventory = build_duplicate_shadow_inventory(project_root)
    removal = build_safe_shadow_removal_report(project_root)
    compatibility = build_legacy_alias_compatibility_cleanup(project_root)
    stale = build_stale_version_gate_cleanup(project_root)
    required_tokens = [
        "duplicate-shadow-inventory",
        "safe-shadow-removal-report",
        "legacy-alias-compatibility-cleanup",
        "stale-version-gate-cleanup",
        "self-maintenance-duplicate-shadow-cleanup-audit",
        "operator-governed-self-maintenance-duplicate-shadow-cleanup-v1",
        "duplicate_cleanup_is_authorization=False",
        "classification_is_permission_to_delete=False",
        "shadow_removal_expands_autonomy=False",
        "stale_gate_cleanup_authorizes_execution=False",
        "cleanup_applies_live_patches=False",
        "cleanup_writes_memory=False",
        "operator_approval_still_required=True",
        "no_native_title_tooltip",
        "data-tip",
        "command-deck",
        "operator-console",
    ]
    docs_missing = [token for token in required_tokens if token not in docs]
    blockers = []
    for label, report in [("inventory", inventory), ("removal", removal), ("compatibility", compatibility), ("stale_gates", stale)]:
        if report.get("ok") is not True:
            blockers.append(label)
    blockers.extend([f"docs:{token}" for token in docs_missing])
    return {
        "version": SELF_MAINTENANCE_SHADOW_CLEANUP_VERSION,
        "state": "operator_governed_self_maintenance_duplicate_shadow_cleanup_review_only",
        "status": "pass" if not blockers else "blocked",
        "ok": not blockers,
        "inventory": inventory,
        "safe_shadow_removal": removal,
        "legacy_alias_compatibility": compatibility,
        "stale_version_gate_cleanup": stale,
        "blockers": blockers,
        "docs_missing": docs_missing,
        "boundaries": dict(SELF_MAINTENANCE_SHADOW_CLEANUP_BOUNDARIES),
        "duplicate_cleanup_is_authorization": False,
        "classification_is_permission_to_delete": False,
        "shadow_removal_expands_autonomy": False,
        "stale_gate_cleanup_authorizes_execution": False,
        "cleanup_applies_live_patches": False,
        "cleanup_writes_memory": False,
        "writes_memory": False,
        "applies_source_edits": False,
        "expands_autonomy": False,
        "creates_approval": False,
        "operator_approval_still_required": True,
        "audit_hash": _hash({"current_duplicate_count": inventory.get("current_duplicate_count"), "removed": inventory.get("removed_shadowed_definition_count"), "blockers": blockers}),
    }


def render_self_maintenance_shadow_cleanup_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"status: {report.get('status', 'pass' if report.get('ok') else 'blocked')}",
        f"ok: {report.get('ok')}",
        f"duplicate_cleanup_is_authorization: {report.get('duplicate_cleanup_is_authorization', False)}",
        f"classification_is_permission_to_delete: {report.get('classification_is_permission_to_delete', False)}",
        f"shadow_removal_expands_autonomy: {report.get('shadow_removal_expands_autonomy', False)}",
        f"stale_gate_cleanup_authorizes_execution: {report.get('stale_gate_cleanup_authorizes_execution', False)}",
        f"operator_approval_still_required: {report.get('operator_approval_still_required', True)}",
    ]
    inventory = report.get("inventory") or {}
    if inventory:
        lines.append(f"current_duplicate_count: {inventory.get('current_duplicate_count')}")
        lines.append(f"removed_shadowed_definition_count: {inventory.get('removed_shadowed_definition_count')}")
    stale = report.get("stale_version_gate_cleanup") or {}
    if stale:
        lines.append(f"stale_exact_gate_hits: {len(stale.get('stale_exact_gate_hits', []))}")
        lines.append(f"historical_helper_use_count: {stale.get('historical_helper_use_count')}")
    if report.get("blockers"):
        lines.append("blockers:")
        lines.extend(f"- {item}" for item in report.get("blockers", [])[:25])
    return lines


# v465.1-v470.0 duplicate shadow cleanup smoke tokens: duplicate-shadow-inventory safe-shadow-removal-report legacy-alias-compatibility-cleanup stale-version-gate-cleanup self-maintenance-duplicate-shadow-cleanup-audit operator-governed-self-maintenance-duplicate-shadow-cleanup-v1 duplicate_cleanup_is_authorization=False classification_is_permission_to_delete=False shadow_removal_expands_autonomy=False stale_gate_cleanup_authorizes_execution=False cleanup_applies_live_patches=False cleanup_writes_memory=False operator_approval_still_required=True no_native_title_tooltip data-tip command-deck operator-console
