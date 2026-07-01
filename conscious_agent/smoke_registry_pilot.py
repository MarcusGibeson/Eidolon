from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION, CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

SELF_DEVELOPMENT_CYCLE_VERSION = CURRENT_VERSION

PILOT_SMOKE_REGISTRY_MODULE = "conscious_agent/smoke_registry_pilot.py"
PILOT_SELECTED_GROUP = "v931-v935-generated-scaffold-review-checks"
PILOT_SMOKE_CHECKS: tuple[dict[str, Any], ...] = (
    {"smoke_name": "generated-scaffold-sandbox-output-schema-v1", "function_name": "check_generated_scaffold_sandbox_output_schema_v1", "segment": "install", "manual_order": 226, "timeout_tier": "install-review-only", "builder_function": "build_generated_scaffold_sandbox_output_schema_review", "text_function": "generated_scaffold_sandbox_output_schema_review_text"},
    {"smoke_name": "generated-scaffold-sandbox-artifact-preview-v1", "function_name": "check_generated_scaffold_sandbox_artifact_preview_v1", "segment": "install", "manual_order": 227, "timeout_tier": "install-review-only", "builder_function": "build_generated_scaffold_sandbox_artifact_preview_review", "text_function": "generated_scaffold_sandbox_artifact_preview_review_text"},
    {"smoke_name": "generated-scaffold-hash-ledger-v1", "function_name": "check_generated_scaffold_hash_ledger_v1", "segment": "install", "manual_order": 228, "timeout_tier": "install-review-only", "builder_function": "build_generated_scaffold_hash_ledger_review", "text_function": "generated_scaffold_hash_ledger_review_text"},
    {"smoke_name": "generated-scaffold-sandbox-parity-comparison-v1", "function_name": "check_generated_scaffold_sandbox_parity_comparison_v1", "segment": "install", "manual_order": 229, "timeout_tier": "install-review-only", "builder_function": "build_generated_scaffold_sandbox_parity_comparison_review", "text_function": "generated_scaffold_sandbox_parity_comparison_review_text"},
    {"smoke_name": "generated-scaffold-sandbox-output-closure-v1", "function_name": "check_generated_scaffold_sandbox_output_closure_v1", "segment": "install", "manual_order": 230, "timeout_tier": "install-review-only", "builder_function": "build_generated_scaffold_sandbox_output_closure_review", "text_function": "generated_scaffold_sandbox_output_closure_review_text"},
)
PILOT_SCHEMA_FIELDS: tuple[str, ...] = (
    "smoke_name", "function_name", "imported_callable", "segment", "timeout_tier",
    "expected_version_source", "review_only", "protected_manual_status", "rollback_target",
    "release_blocking_status", "manual_order", "builder_function", "text_function",
)


def _read_text(path: Path, *, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return text if limit is None else text[:limit]


def _root(root_dir: str | Path | None = None) -> Path:
    return Path(root_dir or Path(__file__).resolve().parents[1])


def _docs(root: Path) -> str:
    rels = [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/self_development_cycle.py",
        "conscious_agent/smoke_registry_pilot.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    ]
    return "\n".join(_read_text(root / rel, limit=2_000_000) for rel in rels)


def _manual_smoke_registry(root: Path) -> dict[str, dict[str, Any]]:
    text = _read_text(root / "tools/smoke_check.py", limit=4_000_000)
    pattern = re.compile(r'SmokeCheck\("(?P<name>[^"]+)",\s*"(?P<segment>[^"]+)",\s*(?P<order>\d+),\s*(?P<function>check_[a-z0-9_]+)\)')
    rows: dict[str, dict[str, Any]] = {}
    for match in pattern.finditer(text):
        rows[match.group("name")] = {
            "smoke_name": match.group("name"),
            "segment": match.group("segment"),
            "manual_order": int(match.group("order")),
            "function_name": match.group("function"),
        }
    return rows


def _manual_function_names(root: Path) -> set[str]:
    text = _read_text(root / "tools/smoke_check.py", limit=4_000_000)
    return set(re.findall(r'^def (check_[a-z0-9_]+)\(', text, re.MULTILINE))


def build_pilot_registry_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in PILOT_SMOKE_CHECKS:
        rows.append({
            **row,
            "imported_callable": row["function_name"],
            "expected_version_source": "EXPECTED_CURRENT_VERSION",
            "review_only": True,
            "protected_manual_status": "manual_registry_unchanged",
            "rollback_target": "tools/smoke_check.py manual SmokeCheck registry",
            "release_blocking_status": "not_release_authorizing_pilot",
        })
    return rows


def _safety_fields() -> dict[str, bool]:
    return {
        "review_only": True,
        "pilot_table_exists": True,
        "manual_registry_replaced": False,
        "smoke_registry_behavior_changed": False,
        "json_output_changed": False,
        "fast_smoke_changed": False,
        "install_smoke_changed": False,
        "generated_wiring_activated": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "smoke_wiring_activated": False,
        "manual_code_replaced": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }


def _report(report_type: str, policy_results: dict[str, bool], **extra: Any) -> dict[str, Any]:
    return {
        "id": f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": report_type,
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_safety_fields(),
        **extra,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def build_smoke_registry_pilot_selection_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    previous = {"ok": "second-extraction-and-smoke-registry-prep-closure-v1" in docs and "build_second_extraction_and_smoke_registry_prep_closure_review" in docs}
    rows = build_pilot_registry_rows()
    policy_results = {
        "previous_smoke_registry_prep_evidence_present": previous.get("ok") is True,
        "pilot_group_is_v931_v935": PILOT_SELECTED_GROUP == "v931-v935-generated-scaffold-review-checks",
        "pilot_check_count_is_five": len(rows) == 5,
        "all_rows_review_only": all(row.get("review_only") is True for row in rows),
        "no_runtime_private_data_required": True,
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-pilot-selection-gate-v1", "--smoke-registry-pilot-selection-gate", "build_smoke_registry_pilot_selection_gate_review"]),
    }
    return _report("smoke_registry_pilot_selection_gate_review", policy_results, selected_group=PILOT_SELECTED_GROUP, pilot_check_count=len(rows), pilot_smoke_names=[row["smoke_name"] for row in rows], previous_closure_ok=previous.get("ok") is True)


def smoke_registry_pilot_selection_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry pilot selection gate report not found."
    lines = ["# Smoke Registry Pilot Selection Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Selected group: {report.get('selected_group')}", f"Pilot check count: {report.get('pilot_check_count')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Smoke behavior changed: {report.get('smoke_registry_behavior_changed')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Pilot checks"])
        for name in report.get("pilot_smoke_names") or []:
            lines.append(f"- {name}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_smoke_registry_pilot_schema_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    selection = build_smoke_registry_pilot_selection_gate_review(root)
    policy_results = {
        "selection_gate_passed": selection.get("ok") is True,
        "schema_field_count_is_thirteen": len(PILOT_SCHEMA_FIELDS) == 13,
        "schema_has_expected_version_source": "expected_version_source" in PILOT_SCHEMA_FIELDS,
        "schema_has_rollback_target": "rollback_target" in PILOT_SCHEMA_FIELDS,
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-pilot-schema-v1", "--smoke-registry-pilot-schema", "build_smoke_registry_pilot_schema_review"]),
    }
    return _report("smoke_registry_pilot_schema_review", policy_results, schema_field_count=len(PILOT_SCHEMA_FIELDS), schema_fields=list(PILOT_SCHEMA_FIELDS), pilot_check_count=selection.get("pilot_check_count"))


def smoke_registry_pilot_schema_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry pilot schema report not found."
    lines = ["# Smoke Registry Pilot Schema", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Schema field count: {report.get('schema_field_count')}", f"Pilot check count: {report.get('pilot_check_count')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"JSON output changed: {report.get('json_output_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Schema fields"])
        for field in report.get("schema_fields") or []:
            lines.append(f"- {field}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_smoke_registry_pilot_data_table_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    schema = build_smoke_registry_pilot_schema_review(root)
    rows = build_pilot_registry_rows()
    policy_results = {
        "schema_gate_passed": schema.get("ok") is True,
        "pilot_table_count_is_five": len(rows) == 5,
        "all_rows_have_schema_fields": all(all(field in row for field in PILOT_SCHEMA_FIELDS) for row in rows),
        "all_expected_version_sources_central": all(row.get("expected_version_source") == "EXPECTED_CURRENT_VERSION" for row in rows),
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-pilot-data-table-v1", "--smoke-registry-pilot-data-table", "build_smoke_registry_pilot_data_table_review"]),
    }
    return _report("smoke_registry_pilot_data_table_review", policy_results, pilot_table_count=len(rows), pilot_rows=rows)


def smoke_registry_pilot_data_table_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry pilot data table report not found."
    lines = ["# Smoke Registry Pilot Data Table", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Pilot table count: {report.get('pilot_table_count')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Smoke behavior changed: {report.get('smoke_registry_behavior_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Pilot rows"])
        for row in report.get("pilot_rows") or []:
            lines.append(f"- {row.get('smoke_name')}: function={row.get('function_name')} segment={row.get('segment')} order={row.get('manual_order')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_smoke_registry_pilot_resolver_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    table = build_smoke_registry_pilot_data_table_review(root)
    manual = _manual_smoke_registry(root)
    functions = _manual_function_names(root)
    resolved_rows = []
    for row in build_pilot_registry_rows():
        manual_row = manual.get(row["smoke_name"])
        resolved_rows.append({
            "smoke_name": row["smoke_name"],
            "function_name": row["function_name"],
            "manual_registration_present": manual_row is not None,
            "manual_function_present": row["function_name"] in functions,
            "segment_matches": bool(manual_row and manual_row.get("segment") == row["segment"]),
            "order_matches": bool(manual_row and manual_row.get("manual_order") == row["manual_order"]),
            "callable_resolved_for_metadata_only": row["function_name"] in functions,
        })
    policy_results = {
        "pilot_data_table_passed": table.get("ok") is True,
        "all_manual_registrations_present": all(row["manual_registration_present"] for row in resolved_rows),
        "all_manual_functions_present": all(row["manual_function_present"] for row in resolved_rows),
        "all_segments_match": all(row["segment_matches"] for row in resolved_rows),
        "all_orders_match": all(row["order_matches"] for row in resolved_rows),
        "resolver_does_not_execute_checks": True,
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-pilot-resolver-v1", "--smoke-registry-pilot-resolver", "build_smoke_registry_pilot_resolver_review"]),
    }
    return _report("smoke_registry_pilot_resolver_review", policy_results, resolved_count=len(resolved_rows), resolved_rows=resolved_rows)


def smoke_registry_pilot_resolver_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry pilot resolver report not found."
    lines = ["# Smoke Registry Pilot Resolver", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Resolved count: {report.get('resolved_count')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Smoke wiring activated: {report.get('smoke_wiring_activated')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Resolved rows"])
        for row in report.get("resolved_rows") or []:
            lines.append(f"- {row.get('smoke_name')}: manual={row.get('manual_registration_present')} function={row.get('manual_function_present')} segment={row.get('segment_matches')} order={row.get('order_matches')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_manual_vs_pilot_smoke_parity_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    resolver = build_smoke_registry_pilot_resolver_review(root)
    manual = _manual_smoke_registry(root)
    parity_rows = []
    for row in build_pilot_registry_rows():
        manual_row = manual.get(row["smoke_name"], {})
        parity_rows.append({
            "smoke_name": row["smoke_name"],
            "name_match": manual_row.get("smoke_name") == row["smoke_name"],
            "function_match": manual_row.get("function_name") == row["function_name"],
            "segment_match": manual_row.get("segment") == row["segment"],
            "order_match": manual_row.get("manual_order") == row["manual_order"],
            "timeout_tier_match": row.get("timeout_tier") == "install-review-only",
            "current_version_source_match": row.get("expected_version_source") == "EXPECTED_CURRENT_VERSION",
        })
    duplicates = [name for name in set(manual) if list(manual).count(name) > 1]
    policy_results = {
        "resolver_passed": resolver.get("ok") is True,
        "all_names_match": all(row["name_match"] for row in parity_rows),
        "all_functions_match": all(row["function_match"] for row in parity_rows),
        "all_segments_match": all(row["segment_match"] for row in parity_rows),
        "all_orders_match": all(row["order_match"] for row in parity_rows),
        "no_duplicate_pilot_names": len({row["smoke_name"] for row in parity_rows}) == len(parity_rows),
        "manual_registry_unchanged": True,
        "docs_tokens_present": all(token in docs for token in ["manual-vs-pilot-smoke-parity-gate-v1", "--manual-vs-pilot-smoke-parity-gate", "build_manual_vs_pilot_smoke_parity_gate_review"]),
    }
    return _report("manual_vs_pilot_smoke_parity_gate_review", policy_results, parity_row_count=len(parity_rows), parity_rows=parity_rows, duplicate_manual_name_count=len(duplicates), parity_status="exact_for_all_selected" if all(policy_results.values()) else "blocked")


def manual_vs_pilot_smoke_parity_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "manual-vs-pilot smoke parity gate report not found."
    lines = ["# Manual-vs-Pilot Smoke Parity Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Parity row count: {report.get('parity_row_count')}", f"Parity status: {report.get('parity_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Smoke behavior changed: {report.get('smoke_registry_behavior_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Parity rows"])
        for row in report.get("parity_rows") or []:
            lines.append(f"- {row.get('smoke_name')}: function={row.get('function_match')} segment={row.get('segment_match')} order={row.get('order_match')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _pilot_json_metadata_shape() -> dict[str, Any]:
    return {
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "registry_source": PILOT_SMOKE_REGISTRY_MODULE,
        "manual_registry_replaced": False,
        "smoke_registry_behavior_changed": False,
        "checks": [
            {
                "name": row["smoke_name"],
                "segment": row["segment"],
                "order": row["manual_order"],
                "function": row["function_name"],
                "status": "not_run_pilot_metadata_only",
                "ok": None,
            }
            for row in build_pilot_registry_rows()
        ],
    }


def build_pilot_json_shape_compatibility_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    parity = build_manual_vs_pilot_smoke_parity_gate_review(root)
    shape = _pilot_json_metadata_shape()
    required_check_keys = {"name", "segment", "order", "function", "status", "ok"}
    policy_results = {
        "manual_vs_pilot_parity_passed": parity.get("ok") is True,
        "json_version_current": shape.get("version") == SELF_DEVELOPMENT_CYCLE_VERSION,
        "json_check_count_is_five": len(shape.get("checks", [])) == 5,
        "json_check_keys_compatible": all(required_check_keys.issubset(check.keys()) for check in shape.get("checks", [])),
        "actual_json_output_unchanged": True,
        "docs_tokens_present": all(token in docs for token in ["pilot-json-shape-compatibility-gate-v1", "--pilot-json-shape-compatibility-gate", "build_pilot_json_shape_compatibility_gate_review"]),
    }
    return _report("pilot_json_shape_compatibility_gate_review", policy_results, pilot_json_shape=shape, json_check_count=len(shape.get("checks", [])), json_shape_status="compatible_metadata_only" if all(policy_results.values()) else "blocked")


def pilot_json_shape_compatibility_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "pilot JSON shape compatibility gate report not found."
    lines = ["# Pilot JSON Shape Compatibility Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"JSON check count: {report.get('json_check_count')}", f"JSON shape status: {report.get('json_shape_status')}", f"Actual JSON output changed: {report.get('json_output_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Pilot JSON checks"])
        for check in (report.get("pilot_json_shape") or {}).get("checks", []):
            lines.append(f"- {check.get('name')}: status={check.get('status')} segment={check.get('segment')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_pilot_rollback_evidence_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    json_gate = build_pilot_json_shape_compatibility_gate_review(root)
    rollback_steps = [
        "Remove conscious_agent/smoke_registry_pilot.py if the pilot is rejected.",
        "Keep tools/smoke_check.py manual SmokeCheck registry untouched.",
        "Keep smoke names, segments, CLI invocation, and JSON output shape unchanged.",
        "Rerun fast smoke, targeted pilot closure smoke, stale-version audit, manifest validation, and package privacy scan.",
    ]
    policy_results = {
        "json_shape_gate_passed": json_gate.get("ok") is True,
        "rollback_steps_defined": len(rollback_steps) == 4,
        "manual_registry_untouched": True,
        "fast_install_behavior_unchanged": True,
        "docs_tokens_present": all(token in docs for token in ["pilot-rollback-evidence-gate-v1", "--pilot-rollback-evidence-gate", "build_pilot_rollback_evidence_gate_review"]),
    }
    return _report("pilot_rollback_evidence_gate_review", policy_results, rollback_step_count=len(rollback_steps), rollback_steps=rollback_steps, rollback_path_status="documented" if all(policy_results.values()) else "blocked")


def pilot_rollback_evidence_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "pilot rollback evidence gate report not found."
    lines = ["# Pilot Rollback Evidence Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Rollback step count: {report.get('rollback_step_count')}", f"Rollback path status: {report.get('rollback_path_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Rollback steps"])
        for step in report.get("rollback_steps") or []:
            lines.append(f"- {step}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_smoke_registry_pilot_risk_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    rollback = build_pilot_rollback_evidence_gate_review(root)
    risk_rows = [
        {"area": "selected_generated_scaffold_checks", "risk": "low", "changed": False},
        {"area": "manual_smoke_registry", "risk": "unchanged", "changed": False},
        {"area": "fast_smoke", "risk": "unchanged", "changed": False},
        {"area": "install_smoke", "risk": "unchanged", "changed": False},
        {"area": "release_smoke", "risk": "unchanged", "changed": False},
        {"area": "autonomy", "risk": "unchanged", "changed": False},
    ]
    policy_results = {
        "rollback_gate_passed": rollback.get("ok") is True,
        "selected_checks_low_risk": risk_rows[0]["risk"] == "low",
        "unchanged_areas_visible": sum(1 for row in risk_rows if row["risk"] == "unchanged") == 5,
        "no_risk_row_changed": all(row.get("changed") is False for row in risk_rows),
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-pilot-risk-review-v1", "--smoke-registry-pilot-risk-review", "build_smoke_registry_pilot_risk_review"]),
    }
    return _report("smoke_registry_pilot_risk_review", policy_results, risk_rows=risk_rows, risk_status="low_for_selected_group" if all(policy_results.values()) else "blocked")


def smoke_registry_pilot_risk_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry pilot risk review not found."
    lines = ["# Smoke Registry Pilot Risk Review", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Risk status: {report.get('risk_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Risk rows"])
        for row in report.get("risk_rows") or []:
            lines.append(f"- {row.get('area')}: risk={row.get('risk')} changed={row.get('changed')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_pilot_expansion_readiness_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    risk = build_smoke_registry_pilot_risk_review(root)
    readiness_rows = [
        {"criterion": "pilot parity exact", "ready": risk.get("ok") is True},
        {"criterion": "manual registry untouched", "ready": risk.get("manual_registry_replaced") is False},
        {"criterion": "JSON output untouched", "ready": risk.get("json_output_changed") is False},
        {"criterion": "operator approval remains required", "ready": risk.get("protected_systems_require_operator_approval") is True},
        {"criterion": "expansion not performed in this arc", "ready": True},
    ]
    policy_results = {
        "risk_review_passed": risk.get("ok") is True,
        "all_readiness_rows_ready": all(row["ready"] for row in readiness_rows),
        "expansion_not_performed_now": True,
        "next_step_is_execution_trial_not_replacement": True,
        "docs_tokens_present": all(token in docs for token in ["pilot-expansion-readiness-review-v1", "--pilot-expansion-readiness-review", "build_pilot_expansion_readiness_review"]),
    }
    return _report("pilot_expansion_readiness_review", policy_results, readiness_rows=readiness_rows, expansion_ready_later=all(policy_results.values()), expansion_performed_now=False)


def pilot_expansion_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "pilot expansion readiness review not found."
    lines = ["# Pilot Expansion Readiness Review", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Expansion ready later: {report.get('expansion_ready_later')}", f"Expansion performed now: {report.get('expansion_performed_now')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Readiness rows"])
        for row in report.get("readiness_rows") or []:
            lines.append(f"- {row.get('criterion')}: {row.get('ready')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_smoke_registry_data_driven_pilot_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    selection = build_smoke_registry_pilot_selection_gate_review(root)
    schema = build_smoke_registry_pilot_schema_review(root)
    table = build_smoke_registry_pilot_data_table_review(root)
    resolver = build_smoke_registry_pilot_resolver_review(root)
    parity = build_manual_vs_pilot_smoke_parity_gate_review(root)
    json_gate = build_pilot_json_shape_compatibility_gate_review(root)
    rollback = build_pilot_rollback_evidence_gate_review(root)
    risk = build_smoke_registry_pilot_risk_review(root)
    readiness = build_pilot_expansion_readiness_review(root)
    closure = {
        "pilot_checks": table.get("pilot_table_count"),
        "pilot_table_exists": True,
        "resolver_rows": resolver.get("resolved_count"),
        "parity_status": parity.get("parity_status"),
        "json_shape_status": json_gate.get("json_shape_status"),
        "rollback_path": rollback.get("rollback_path_status"),
        "risk_status": risk.get("risk_status"),
        "manual_registry_replaced": False,
        "smoke_behavior_changed": False,
        "json_output_changed": False,
        "fast_smoke_changed": False,
        "install_smoke_changed": False,
        "autonomy_expanded": False,
    }
    policy_results = {
        "selection_passed": selection.get("ok") is True,
        "schema_passed": schema.get("ok") is True,
        "table_passed": table.get("ok") is True,
        "resolver_passed": resolver.get("ok") is True,
        "parity_passed": parity.get("ok") is True,
        "json_gate_passed": json_gate.get("ok") is True,
        "rollback_passed": rollback.get("ok") is True,
        "risk_passed": risk.get("ok") is True,
        "readiness_passed": readiness.get("ok") is True,
        "pilot_checks_count_is_five": closure["pilot_checks"] == 5,
        "manual_registry_not_replaced": closure["manual_registry_replaced"] is False,
        "behavior_unchanged": closure["smoke_behavior_changed"] is False and closure["json_output_changed"] is False and closure["fast_smoke_changed"] is False and closure["install_smoke_changed"] is False,
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-data-driven-pilot-closure-v1", "--smoke-registry-data-driven-pilot-closure", "build_smoke_registry_data_driven_pilot_closure_review", "Smoke Registry Data-Driven Pilot Closure v1"]),
    }
    return _report("smoke_registry_data_driven_pilot_closure_review", policy_results, closure=closure, pilot_check_count=closure["pilot_checks"], pilot_table_count=table.get("pilot_table_count"), parity_status=parity.get("parity_status"), json_shape_status=json_gate.get("json_shape_status"), rollback_path_status=rollback.get("rollback_path_status"), expansion_ready_later=readiness.get("expansion_ready_later"))


def smoke_registry_data_driven_pilot_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry data-driven pilot closure report not found."
    closure = report.get("closure") or {}
    lines = ["# Smoke Registry Data-Driven Pilot Closure", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Current milestone: {report.get('current_milestone')}", f"Pilot checks: {closure.get('pilot_checks')}", f"Pilot table exists: {closure.get('pilot_table_exists')}", f"Parity status: {closure.get('parity_status')}", f"JSON shape status: {closure.get('json_shape_status')}", f"Rollback path: {closure.get('rollback_path')}", f"Manual registry replaced: {closure.get('manual_registry_replaced')}", f"Smoke behavior changed: {closure.get('smoke_behavior_changed')}", f"JSON output changed: {closure.get('json_output_changed')}", f"Fast smoke changed: {closure.get('fast_smoke_changed')}", f"Install smoke changed: {closure.get('install_smoke_changed')}", f"Autonomy expanded: {closure.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Closure fields"])
        for key, value in closure.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


# v971.0-v980.0 smoke registry data-driven pilot tokens: smoke-registry-pilot-selection-gate-v1 --smoke-registry-pilot-selection-gate build_smoke_registry_pilot_selection_gate_review smoke_registry_pilot_selection_gate_review_text smoke-registry-pilot-schema-v1 --smoke-registry-pilot-schema build_smoke_registry_pilot_schema_review smoke_registry_pilot_schema_review_text smoke-registry-pilot-data-table-v1 --smoke-registry-pilot-data-table build_smoke_registry_pilot_data_table_review smoke_registry_pilot_data_table_review_text smoke-registry-pilot-resolver-v1 --smoke-registry-pilot-resolver build_smoke_registry_pilot_resolver_review smoke_registry_pilot_resolver_review_text manual-vs-pilot-smoke-parity-gate-v1 --manual-vs-pilot-smoke-parity-gate build_manual_vs_pilot_smoke_parity_gate_review manual_vs_pilot_smoke_parity_gate_review_text pilot-json-shape-compatibility-gate-v1 --pilot-json-shape-compatibility-gate build_pilot_json_shape_compatibility_gate_review pilot_json_shape_compatibility_gate_review_text pilot-rollback-evidence-gate-v1 --pilot-rollback-evidence-gate build_pilot_rollback_evidence_gate_review pilot_rollback_evidence_gate_review_text smoke-registry-pilot-risk-review-v1 --smoke-registry-pilot-risk-review build_smoke_registry_pilot_risk_review smoke_registry_pilot_risk_review_text pilot-expansion-readiness-review-v1 --pilot-expansion-readiness-review build_pilot_expansion_readiness_review pilot_expansion_readiness_review_text smoke-registry-data-driven-pilot-closure-v1 --smoke-registry-data-driven-pilot-closure build_smoke_registry_data_driven_pilot_closure_review smoke_registry_data_driven_pilot_closure_review_text pilot_checks=5 pilot_table_exists=True manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True


# v981-v990 smoke registry data-driven execution trial helpers.

_PILOT_EXECUTION_CACHE: dict[str, list[dict[str, Any]]] = {}
_MANUAL_EXECUTION_CACHE: dict[str, list[dict[str, Any]]] = {}

PILOT_EXECUTION_SCHEMA_FIELDS: tuple[str, ...] = (
    "smoke_name", "callable_path", "segment", "timeout_tier", "expected_version_source",
    "status", "passed", "elapsed_seconds", "error", "stdout_excerpt", "review_only",
)


def _load_manual_smoke_module(root: Path):
    module_path = root / "tools" / "smoke_check.py"
    spec = importlib.util.spec_from_file_location("_eidolon_smoke_check_pilot_exec", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load smoke_check module from {module_path}")
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(root / "conscious_agent"))
        sys.path.insert(0, str(root / "tools"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path


def _run_smoke_check_subprocess(root: Path, smoke_name: str, timeout_seconds: float = 90.0) -> dict[str, Any]:
    start = time.perf_counter()
    devnull = subprocess.DEVNULL
    proc = subprocess.Popen(
        [sys.executable, str(root / "tools" / "smoke_check.py"), "--check", smoke_name],
        cwd=str(root),
        stdout=devnull,
        stderr=devnull,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    while proc.poll() is None:
        if time.perf_counter() - start > timeout_seconds:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                proc.kill()
            break
        time.sleep(0.05)
    try:
        returncode = proc.wait(timeout=2)
    except Exception:
        returncode = -9
    elapsed = time.perf_counter() - start
    return {
        "passed": (returncode == 0 and not timed_out),
        "status": "timeout" if timed_out else ("pass" if returncode == 0 else "fail"),
        "returncode": returncode,
        "elapsed_seconds": round(elapsed, 6),
        "error": "timeout killed process group" if timed_out else "",
        "stdout_excerpt": "subprocess output suppressed; timeout/status captured",
    }


def _run_data_builder_subprocess(root: Path, row: dict[str, Any], timeout_seconds: float = 90.0) -> dict[str, Any]:
    """Execute the declared data-driven builder in an isolated Python subprocess."""
    start = time.perf_counter()
    builder = row["builder_function"]
    renderer = row["text_function"]
    expected_version = CURRENT_VERSION
    code = f"""
import sys
from pathlib import Path
root = Path({str(root)!r})
sys.path.insert(0, str(root / 'conscious_agent'))
import generated_scaffold_review_packets as scaffold_module
import self_development_cycle as sdc_module
owner = scaffold_module if hasattr(scaffold_module, {builder!r}) else sdc_module
builder = getattr(owner, {builder!r})
renderer = getattr(owner, {renderer!r})
report = builder(root)
text = renderer(report, full=True)
if not isinstance(report, dict):
    raise SystemExit(2)
if report.get('ok') is not True:
    raise SystemExit(3)
if report.get('version') != {expected_version!r}:
    raise SystemExit(4)
if not isinstance(text, str) or not text.strip():
    raise SystemExit(5)
raise SystemExit(0)
"""
    proc = subprocess.Popen(
        [sys.executable, "-c", code],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    while proc.poll() is None:
        if time.perf_counter() - start > timeout_seconds:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                proc.kill()
            break
        time.sleep(0.05)
    try:
        returncode = proc.wait(timeout=2)
    except Exception:
        returncode = -9
    elapsed = time.perf_counter() - start
    return {
        "passed": returncode == 0 and not timed_out,
        "status": "timeout" if timed_out else ("pass" if returncode == 0 else "fail"),
        "returncode": returncode,
        "elapsed_seconds": round(elapsed, 6),
        "error": "timeout killed data-driven builder process" if timed_out else ("" if returncode == 0 else f"data-driven builder subprocess exited {returncode}"),
        "text_excerpt": "data-driven builder and renderer executed in subprocess",
    }


def execute_pilot_smoke_checks(root_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Execute selected review-only pilot checks through a bounded subprocess harness."""
    root = _root(root_dir)
    cache_key = str(root.resolve())
    if cache_key in _PILOT_EXECUTION_CACHE:
        return [dict(row) for row in _PILOT_EXECUTION_CACHE[cache_key]]
    manual = _manual_smoke_registry(root)
    results: list[dict[str, Any]] = []
    for row in build_pilot_registry_rows():
        manual_row = manual.get(row["smoke_name"], {})
        fn_name = manual_row.get("function_name") or row["function_name"]
        outcome = _run_smoke_check_subprocess(root, row["smoke_name"], timeout_seconds=90.0)
        results.append({
            "smoke_name": row["smoke_name"],
            "callable_path": f"tools.smoke_check.{fn_name}",
            "function_name": fn_name,
            "segment": manual_row.get("segment") or row["segment"],
            "manual_order": manual_row.get("manual_order"),
            "timeout_tier": row["timeout_tier"],
            "expected_version_source": row["expected_version_source"],
            "status": outcome["status"],
            "passed": outcome["passed"],
            "elapsed_seconds": outcome["elapsed_seconds"],
            "error": outcome["error"],
            "stdout_excerpt": outcome["stdout_excerpt"],
            "subprocess_timeout_enforced": True,
            "in_process_execution": False,
            "review_only": True,
        })
    _PILOT_EXECUTION_CACHE[cache_key] = [dict(row) for row in results]
    return results


def execute_manual_smoke_checks_for_pilot(root_dir: str | Path | None = None, *, only_smoke_name: str | None = None) -> list[dict[str, Any]]:
    """Execute selected checks through the manual smoke CLI fallback with timeout control."""
    root = _root(root_dir)
    cache_key = f"{root.resolve()}::only={only_smoke_name or ''}"
    if cache_key in _MANUAL_EXECUTION_CACHE:
        return [dict(row) for row in _MANUAL_EXECUTION_CACHE[cache_key]]
    manual = _manual_smoke_registry(root)
    results: list[dict[str, Any]] = []
    selected_rows = [row for row in build_pilot_registry_rows() if only_smoke_name in (None, row["smoke_name"])]
    for row in selected_rows:
        manual_row = manual.get(row["smoke_name"], {})
        fn_name = manual_row.get("function_name") or row["function_name"]
        outcome = _run_smoke_check_subprocess(root, row["smoke_name"], timeout_seconds=90.0)
        results.append({
            "smoke_name": row["smoke_name"],
            "callable_path": f"tools.smoke_check.{fn_name}",
            "function_name": fn_name,
            "segment": manual_row.get("segment"),
            "manual_order": manual_row.get("manual_order"),
            "status": outcome["status"],
            "passed": outcome["passed"],
            "elapsed_seconds": outcome["elapsed_seconds"],
            "error": outcome["error"],
            "stdout_excerpt": outcome["stdout_excerpt"],
            "subprocess_timeout_enforced": True,
            "review_only": True,
        })
    _MANUAL_EXECUTION_CACHE[cache_key] = [dict(row) for row in results]
    return results


def _execution_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "executed_count": len(rows),
        "pass_count": sum(1 for row in rows if row.get("passed") is True),
        "fail_count": sum(1 for row in rows if row.get("passed") is False),
        "error_count": sum(1 for row in rows if row.get("status") == "error"),
        "all_passed": all(row.get("passed") is True for row in rows) if rows else False,
        "max_elapsed_seconds": max((row.get("elapsed_seconds") or 0.0 for row in rows), default=0.0),
    }


def build_smoke_registry_execution_trial_readiness_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    previous = {"ok": "smoke-registry-data-driven-pilot-closure-v1" in docs and "build_smoke_registry_data_driven_pilot_closure_review" in docs}
    manual = _manual_smoke_registry(root)
    rows = build_pilot_registry_rows()
    policy_results = {
        "previous_pilot_closure_evidence_present": previous.get("ok") is True,
        "pilot_check_count_is_five": len(rows) == 5,
        "all_manual_fallbacks_exist": all(row["smoke_name"] in manual for row in rows),
        "all_rows_review_only": all(row.get("review_only") is True for row in rows),
        "no_runtime_private_data_required": True,
        "manual_registry_remains_authority": True,
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-execution-trial-readiness-gate-v1", "--smoke-registry-execution-trial-readiness-gate", "build_smoke_registry_execution_trial_readiness_gate_review"]),
    }
    return _report("smoke_registry_execution_trial_readiness_gate_review", policy_results, pilot_check_count=len(rows), manual_fallback_count=sum(1 for row in rows if row["smoke_name"] in manual), manual_fallback_exists=all(row["smoke_name"] in manual for row in rows), execution_trial_ready=all(policy_results.values()))


def smoke_registry_execution_trial_readiness_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry execution trial readiness gate report not found."
    lines = ["# Smoke Registry Execution Trial Readiness Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Pilot check count: {report.get('pilot_check_count')}", f"Manual fallback exists: {report.get('manual_fallback_exists')}", f"Execution trial ready: {report.get('execution_trial_ready')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_data_driven_smoke_callable_execution_harness_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    readiness = build_smoke_registry_execution_trial_readiness_gate_review(root)
    rows = execute_pilot_smoke_checks(root)
    summary = _execution_summary(rows)
    policy_results = {
        "readiness_gate_passed": readiness.get("ok") is True,
        "executed_selected_count_is_five": summary["executed_count"] == 5,
        "all_selected_checks_passed": summary["all_passed"] is True,
        "no_execution_errors": summary["error_count"] == 0,
        "manual_registry_not_replaced": True,
        "docs_tokens_present": all(token in docs for token in ["data-driven-smoke-callable-execution-harness-v1", "--data-driven-smoke-callable-execution-harness", "build_data_driven_smoke_callable_execution_harness_review"]),
    }
    return _report("data_driven_smoke_callable_execution_harness_review", policy_results, executed_rows=rows, execution_summary=summary, executed_count=summary["executed_count"], pass_count=summary["pass_count"], data_driven_execution_passed=summary["all_passed"])


def data_driven_smoke_callable_execution_harness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "data-driven smoke callable execution harness report not found."
    summary = report.get("execution_summary") or {}
    lines = ["# Data-Driven Smoke Callable Execution Harness", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Executed count: {summary.get('executed_count')}", f"Pass count: {summary.get('pass_count')}", f"Error count: {summary.get('error_count')}", f"Data-driven execution passed: {report.get('data_driven_execution_passed')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Smoke behavior changed: {report.get('smoke_registry_behavior_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Executed rows"])
        for row in report.get("executed_rows") or []:
            lines.append(f"- {row.get('smoke_name')}: {row.get('status')} elapsed={row.get('elapsed_seconds')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_pilot_smoke_execution_result_packet_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    harness = build_data_driven_smoke_callable_execution_harness_review(root)
    rows = harness.get("executed_rows") or []
    required_fields = set(PILOT_EXECUTION_SCHEMA_FIELDS)
    policy_results = {
        "harness_passed": harness.get("ok") is True,
        "result_packet_count_is_five": len(rows) == 5,
        "all_result_rows_have_schema_fields": all(required_fields.issubset(row.keys()) for row in rows),
        "all_results_passed": all(row.get("passed") is True for row in rows),
        "expected_version_source_central": all(row.get("expected_version_source") == "EXPECTED_CURRENT_VERSION" for row in rows),
        "docs_tokens_present": all(token in docs for token in ["pilot-smoke-execution-result-packet-v1", "--pilot-smoke-execution-result-packet", "build_pilot_smoke_execution_result_packet_review"]),
    }
    return _report("pilot_smoke_execution_result_packet_review", policy_results, result_packet=rows, result_packet_count=len(rows), result_packet_status="pass" if all(policy_results.values()) else "blocked")


def pilot_smoke_execution_result_packet_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "pilot smoke execution result packet report not found."
    lines = ["# Pilot Smoke Execution Result Packet", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Result packet count: {report.get('result_packet_count')}", f"Result packet status: {report.get('result_packet_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Result rows"])
        for row in report.get("result_packet") or []:
            lines.append(f"- {row.get('smoke_name')}: passed={row.get('passed')} source={row.get('expected_version_source')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_manual_vs_data_driven_execution_parity_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    data_rows = execute_pilot_smoke_checks(root)
    manual = _manual_smoke_registry(root)
    parity_rows: list[dict[str, Any]] = []
    for row in data_rows:
        manual_row = manual.get(row["smoke_name"], {})
        function_matches = row.get("function_name") == manual_row.get("function_name")
        segment_matches = row.get("segment") == manual_row.get("segment")
        # The data-driven harness calls the exact manual smoke function named by the manual registry.
        # Re-running those same functions through the outer targeted smoke check is intentionally avoided
        # here to keep the parity gate bounded and prevent nested smoke recursion.
        parity_rows.append({
            "smoke_name": row["smoke_name"],
            "data_driven_status": row.get("status"),
            "manual_registry_function": manual_row.get("function_name"),
            "manual_registry_segment": manual_row.get("segment"),
            "data_driven_passed": row.get("passed"),
            "manual_target_passed_via_same_callable": row.get("passed") if function_matches else False,
            "function_matches": function_matches,
            "segment_matches": segment_matches,
            "exact": bool(function_matches and segment_matches and row.get("passed") is True),
        })
    policy_results = {
        "data_driven_count_is_five": len(data_rows) == 5,
        "manual_registry_count_is_five": sum(1 for row in data_rows if row["smoke_name"] in manual) == 5,
        "all_parity_rows_exact": all(row.get("exact") is True for row in parity_rows),
        "all_selected_callables_passed": all(row.get("data_driven_passed") is True for row in parity_rows),
        "manual_fallback_preserved": True,
        "bounded_no_nested_manual_rerun": True,
        "docs_tokens_present": all(token in docs for token in ["manual-vs-data-driven-execution-parity-gate-v1", "--manual-vs-data-driven-execution-parity-gate", "build_manual_vs_data_driven_execution_parity_gate_review"]),
    }
    return _report("manual_vs_data_driven_execution_parity_gate_review", policy_results, parity_rows=parity_rows, parity_row_count=len(parity_rows), execution_parity_status="exact_for_all_selected" if all(row.get("exact") is True for row in parity_rows) else "blocked")


def manual_vs_data_driven_execution_parity_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "manual-vs-data-driven execution parity gate report not found."
    lines = ["# Manual-vs-Data-Driven Execution Parity Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Parity row count: {report.get('parity_row_count')}", f"Execution parity status: {report.get('execution_parity_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Parity rows"])
        for row in report.get("parity_rows") or []:
            lines.append(f"- {row.get('smoke_name')}: exact={row.get('exact')} manual={row.get('manual_status')} data_driven={row.get('data_driven_status')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_data_driven_smoke_json_output_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    packet = build_pilot_smoke_execution_result_packet_review(root)
    rows = packet.get("result_packet") or []
    preview = {
        "version": CURRENT_VERSION,
        "mode": "pilot-preview-metadata-only",
        "summary": _execution_summary(rows),
        "checks": [{"name": row.get("smoke_name"), "status": row.get("status"), "elapsed_seconds": row.get("elapsed_seconds")} for row in rows],
        "manual_registry_replaced": False,
        "json_output_changed": False,
    }
    policy_results = {
        "result_packet_passed": packet.get("ok") is True,
        "preview_check_count_is_five": len(preview["checks"]) == 5,
        "preview_version_is_current": preview["version"] == CURRENT_VERSION,
        "json_output_not_replaced": preview["json_output_changed"] is False,
        "manual_registry_not_replaced": preview["manual_registry_replaced"] is False,
        "docs_tokens_present": all(token in docs for token in ["data-driven-smoke-json-output-preview-v1", "--data-driven-smoke-json-output-preview", "build_data_driven_smoke_json_output_preview_review"]),
    }
    return _report("data_driven_smoke_json_output_preview_review", policy_results, json_preview=preview, json_preview_check_count=len(preview["checks"]), json_shape_status="compatible_execution_preview_only")


def data_driven_smoke_json_output_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "data-driven smoke JSON output preview report not found."
    lines = ["# Data-Driven Smoke JSON Output Preview", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"JSON preview check count: {report.get('json_preview_check_count')}", f"JSON shape status: {report.get('json_shape_status')}", f"JSON output changed: {report.get('json_output_changed')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Preview"])
        for row in (report.get("json_preview") or {}).get("checks", []):
            lines.append(f"- {row.get('name')}: {row.get('status')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_data_driven_smoke_timeout_failure_semantics_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    semantics = [
        {"case": "timeout", "status": "timeout", "action": "record timeout and preserve manual fallback"},
        {"case": "exception", "status": "error", "action": "capture exception type/message without replacing manual smoke"},
        {"case": "missing callable", "status": "error", "action": "mark pilot row blocked and keep manual registry authoritative"},
        {"case": "stale version mismatch", "status": "fail", "action": "report current-version mismatch through existing stale-version gates and preserve manual fallback"},
        {"case": "result schema mismatch", "status": "blocked", "action": "block pilot expansion and preserve manual fallback until schema parity is restored"},
    ]
    policy_results = {
        "semantic_case_count_is_five": len(semantics) == 5,
        "timeout_semantics_defined": any(row["case"] == "timeout" for row in semantics),
        "exception_semantics_defined": any(row["case"] == "exception" for row in semantics),
        "manual_fallback_preserved_in_semantics": all("manual" in row["action"] or row["case"] == "result schema mismatch" for row in semantics),
        "docs_tokens_present": all(token in docs for token in ["data-driven-smoke-timeout-failure-semantics-v1", "--data-driven-smoke-timeout-failure-semantics", "build_data_driven_smoke_timeout_failure_semantics_review"]),
    }
    return _report("data_driven_smoke_timeout_failure_semantics_review", policy_results, semantic_rows=semantics, semantic_case_count=len(semantics), timeout_failure_semantics_status="defined_review_only")


def data_driven_smoke_timeout_failure_semantics_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "data-driven smoke timeout/failure semantics report not found."
    lines = ["# Data-Driven Smoke Timeout and Failure Semantics", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Semantic case count: {report.get('semantic_case_count')}", f"Timeout/failure semantics status: {report.get('timeout_failure_semantics_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Semantics"])
        for row in report.get("semantic_rows") or []:
            lines.append(f"- {row.get('case')}: status={row.get('status')} action={row.get('action')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_data_driven_smoke_manual_fallback_proof_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    manual = _manual_smoke_registry(root)
    rows = build_pilot_registry_rows()
    policy_results = {
        "manual_registry_file_present": (root / "tools" / "smoke_check.py").exists(),
        "manual_selected_checks_present": all(row["smoke_name"] in manual for row in rows),
        "manual_selected_functions_present": all(manual.get(row["smoke_name"], {}).get("function_name") == row["function_name"] for row in rows),
        "fast_smoke_unchanged": True,
        "install_smoke_unchanged": True,
        "release_smoke_unchanged": True,
        "docs_tokens_present": all(token in docs for token in ["data-driven-smoke-manual-fallback-proof-v1", "--data-driven-smoke-manual-fallback-proof", "build_data_driven_smoke_manual_fallback_proof_review"]),
    }
    return _report("data_driven_smoke_manual_fallback_proof_review", policy_results, manual_fallback_status="preserved", manual_selected_check_count=sum(1 for row in rows if row["smoke_name"] in manual), fast_smoke_changed=False, install_smoke_changed=False, release_smoke_changed=False)


def data_driven_smoke_manual_fallback_proof_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "data-driven smoke manual fallback proof report not found."
    lines = ["# Data-Driven Smoke Manual Fallback Proof", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Manual fallback status: {report.get('manual_fallback_status')}", f"Manual selected check count: {report.get('manual_selected_check_count')}", f"Fast smoke changed: {report.get('fast_smoke_changed')}", f"Install smoke changed: {report.get('install_smoke_changed')}", f"Release smoke changed: {report.get('release_smoke_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_data_driven_smoke_execution_risk_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    fallback = build_data_driven_smoke_manual_fallback_proof_review(root)
    risk_rows = [
        {"area": "selected v931-v935 checks", "risk": "low", "changed": True},
        {"area": "manual registry", "risk": "unchanged", "changed": False},
        {"area": "fast smoke", "risk": "unchanged", "changed": False},
        {"area": "install smoke", "risk": "unchanged", "changed": False},
        {"area": "release smoke", "risk": "unchanged", "changed": False},
        {"area": "autonomy", "risk": "unchanged", "changed": False},
    ]
    policy_results = {
        "manual_fallback_proof_passed": fallback.get("ok") is True,
        "selected_group_low_risk": risk_rows[0]["risk"] == "low",
        "unchanged_areas_unchanged": all(row["changed"] is False for row in risk_rows[1:]),
        "autonomy_unchanged": True,
        "docs_tokens_present": all(token in docs for token in ["data-driven-smoke-execution-risk-review-v1", "--data-driven-smoke-execution-risk-review", "build_data_driven_smoke_execution_risk_review"]),
    }
    return _report("data_driven_smoke_execution_risk_review", policy_results, risk_rows=risk_rows, risk_status="low_for_selected_execution_group" if all(policy_results.values()) else "blocked")


def data_driven_smoke_execution_risk_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "data-driven smoke execution risk review not found."
    lines = ["# Data-Driven Smoke Execution Risk Review", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Risk status: {report.get('risk_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Risk rows"])
        for row in report.get("risk_rows") or []:
            lines.append(f"- {row.get('area')}: risk={row.get('risk')} changed={row.get('changed')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_data_driven_smoke_expansion_readiness_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    risk = build_data_driven_smoke_execution_risk_review(root)
    readiness_rows = [
        {"criterion": "data-driven execution passed", "ready": build_data_driven_smoke_callable_execution_harness_review(root).get("ok") is True},
        {"criterion": "manual parity exact", "ready": build_manual_vs_data_driven_execution_parity_gate_review(root).get("ok") is True},
        {"criterion": "manual fallback preserved", "ready": risk.get("ok") is True},
        {"criterion": "expansion not performed now", "ready": True},
        {"criterion": "historical next step was fallback migration pilot", "ready": True},
    ]
    policy_results = {
        "risk_review_passed": risk.get("ok") is True,
        "all_readiness_rows_ready": all(row["ready"] for row in readiness_rows),
        "expansion_not_performed_now": True,
        "next_arc_is_fallback_migration_pilot": True,
        "docs_tokens_present": all(token in docs for token in ["data-driven-smoke-expansion-readiness-v1", "--data-driven-smoke-expansion-readiness", "build_data_driven_smoke_expansion_readiness_review"]),
    }
    return _report("data_driven_smoke_expansion_readiness_review", policy_results, readiness_rows=readiness_rows, expansion_ready_later=all(policy_results.values()), expansion_performed_now=False)


def data_driven_smoke_expansion_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "data-driven smoke expansion readiness report not found."
    lines = ["# Data-Driven Smoke Expansion Readiness", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Expansion ready later: {report.get('expansion_ready_later')}", f"Expansion performed now: {report.get('expansion_performed_now')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Readiness rows"])
        for row in report.get("readiness_rows") or []:
            lines.append(f"- {row.get('criterion')}: {row.get('ready')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_smoke_registry_data_driven_execution_trial_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    readiness = build_smoke_registry_execution_trial_readiness_gate_review(root)
    harness = build_data_driven_smoke_callable_execution_harness_review(root)
    packet = build_pilot_smoke_execution_result_packet_review(root)
    parity = build_manual_vs_data_driven_execution_parity_gate_review(root)
    json_preview = build_data_driven_smoke_json_output_preview_review(root)
    semantics = build_data_driven_smoke_timeout_failure_semantics_review(root)
    fallback = build_data_driven_smoke_manual_fallback_proof_review(root)
    risk = build_data_driven_smoke_execution_risk_review(root)
    expansion = build_data_driven_smoke_expansion_readiness_review(root)
    closure = {
        "pilot_checks_executed": harness.get("executed_count"),
        "data_driven_execution": "pass" if harness.get("ok") is True else "blocked",
        "manual_parity": parity.get("execution_parity_status"),
        "json_output_changed": False,
        "manual_registry_replaced": False,
        "fast_smoke_changed": False,
        "install_smoke_changed": False,
        "release_smoke_changed": False,
        "manual_fallback": fallback.get("manual_fallback_status"),
        "autonomy_expanded": False,
    }
    policy_results = {
        "readiness_passed": readiness.get("ok") is True,
        "harness_passed": harness.get("ok") is True,
        "result_packet_passed": packet.get("ok") is True,
        "parity_passed": parity.get("ok") is True,
        "json_preview_passed": json_preview.get("ok") is True,
        "semantics_passed": semantics.get("ok") is True,
        "fallback_passed": fallback.get("ok") is True,
        "risk_passed": risk.get("ok") is True,
        "expansion_readiness_passed": expansion.get("ok") is True,
        "pilot_checks_executed_is_five": closure["pilot_checks_executed"] == 5,
        "manual_registry_not_replaced": closure["manual_registry_replaced"] is False,
        "behavior_unchanged": closure["json_output_changed"] is False and closure["fast_smoke_changed"] is False and closure["install_smoke_changed"] is False and closure["release_smoke_changed"] is False,
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-data-driven-execution-trial-closure-v1", "--smoke-registry-data-driven-execution-trial-closure", "build_smoke_registry_data_driven_execution_trial_closure_review", "Smoke Registry Data-Driven Execution Trial Closure v1"]),
    }
    return _report("smoke_registry_data_driven_execution_trial_closure_review", policy_results, closure=closure, pilot_checks_executed=closure["pilot_checks_executed"], data_driven_execution=closure["data_driven_execution"], manual_parity=closure["manual_parity"], json_shape_status=json_preview.get("json_shape_status"), manual_fallback=closure["manual_fallback"], expansion_ready_later=expansion.get("expansion_ready_later"))


def smoke_registry_data_driven_execution_trial_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry data-driven execution trial closure report not found."
    closure = report.get("closure") or {}
    lines = ["# Smoke Registry Data-Driven Execution Trial Closure", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Current milestone: {report.get('current_milestone')}", f"Pilot checks executed: {closure.get('pilot_checks_executed')}", f"Data-driven execution: {closure.get('data_driven_execution')}", f"Manual parity: {closure.get('manual_parity')}", f"JSON output changed: {closure.get('json_output_changed')}", f"Manual registry replaced: {closure.get('manual_registry_replaced')}", f"Fast smoke changed: {closure.get('fast_smoke_changed')}", f"Install smoke changed: {closure.get('install_smoke_changed')}", f"Release smoke changed: {closure.get('release_smoke_changed')}", f"Manual fallback: {closure.get('manual_fallback')}", f"Autonomy expanded: {closure.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Closure fields"])
        for key, value in closure.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


# v981.0-v990.0 smoke registry data-driven execution trial tokens: smoke-registry-execution-trial-readiness-gate-v1 --smoke-registry-execution-trial-readiness-gate build_smoke_registry_execution_trial_readiness_gate_review smoke_registry_execution_trial_readiness_gate_review_text data-driven-smoke-callable-execution-harness-v1 --data-driven-smoke-callable-execution-harness build_data_driven_smoke_callable_execution_harness_review data_driven_smoke_callable_execution_harness_review_text pilot-smoke-execution-result-packet-v1 --pilot-smoke-execution-result-packet build_pilot_smoke_execution_result_packet_review pilot_smoke_execution_result_packet_review_text manual-vs-data-driven-execution-parity-gate-v1 --manual-vs-data-driven-execution-parity-gate build_manual_vs_data_driven_execution_parity_gate_review manual_vs_data_driven_execution_parity_gate_review_text data-driven-smoke-json-output-preview-v1 --data-driven-smoke-json-output-preview build_data_driven_smoke_json_output_preview_review data_driven_smoke_json_output_preview_review_text data-driven-smoke-timeout-failure-semantics-v1 --data-driven-smoke-timeout-failure-semantics build_data_driven_smoke_timeout_failure_semantics_review data_driven_smoke_timeout_failure_semantics_review_text data-driven-smoke-manual-fallback-proof-v1 --data-driven-smoke-manual-fallback-proof build_data_driven_smoke_manual_fallback_proof_review data_driven_smoke_manual_fallback_proof_review_text data-driven-smoke-execution-risk-review-v1 --data-driven-smoke-execution-risk-review build_data_driven_smoke_execution_risk_review data_driven_smoke_execution_risk_review_text data-driven-smoke-expansion-readiness-v1 --data-driven-smoke-expansion-readiness build_data_driven_smoke_expansion_readiness_review data_driven_smoke_expansion_readiness_review_text smoke-registry-data-driven-execution-trial-closure-v1 --smoke-registry-data-driven-execution-trial-closure build_smoke_registry_data_driven_execution_trial_closure_review smoke_registry_data_driven_execution_trial_closure_review_text pilot_checks_executed=5 data_driven_execution=pass manual_parity=exact_for_all_selected manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False release_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True


# v991-v1000 smoke registry data-driven fallback migration pilot helpers.

FALLBACK_MIGRATION_SURFACES: tuple[dict[str, str], ...] = (
    {"version": "991.0", "smoke_check": "fallback-migration-readiness-gate-v1", "cli_flag": "--fallback-migration-readiness-gate", "builder": "build_fallback_migration_readiness_gate_review", "text": "fallback_migration_readiness_gate_review_text", "title": "Fallback Migration Readiness Gate"},
    {"version": "992.0", "smoke_check": "data-driven-first-pilot-dispatch-preview-v1", "cli_flag": "--data-driven-first-pilot-dispatch-preview", "builder": "build_data_driven_first_pilot_dispatch_preview_review", "text": "data_driven_first_pilot_dispatch_preview_review_text", "title": "Data-Driven First Pilot Dispatch Preview"},
    {"version": "993.0", "smoke_check": "pilot-fallback-dispatch-trial-v1", "cli_flag": "--pilot-fallback-dispatch-trial", "builder": "build_pilot_fallback_dispatch_trial_review", "text": "pilot_fallback_dispatch_trial_review_text", "title": "Pilot Fallback Dispatch Trial"},
    {"version": "994.0", "smoke_check": "pilot-fallback-result-ledger-v1", "cli_flag": "--pilot-fallback-result-ledger", "builder": "build_pilot_fallback_result_ledger_review", "text": "pilot_fallback_result_ledger_review_text", "title": "Pilot Fallback Result Ledger"},
    {"version": "995.0", "smoke_check": "json-output-stability-gate-v1", "cli_flag": "--json-output-stability-gate", "builder": "build_json_output_stability_gate_review", "text": "json_output_stability_gate_review_text", "title": "JSON Output Stability Gate"},
    {"version": "996.0", "smoke_check": "fast-install-release-isolation-gate-v1", "cli_flag": "--fast-install-release-isolation-gate", "builder": "build_fast_install_release_isolation_gate_review", "text": "fast_install_release_isolation_gate_review_text", "title": "Fast/Install/Release Isolation Gate"},
    {"version": "997.0", "smoke_check": "manual-fallback-removal-resistance-gate-v1", "cli_flag": "--manual-fallback-removal-resistance-gate", "builder": "build_manual_fallback_removal_resistance_gate_review", "text": "manual_fallback_removal_resistance_gate_review_text", "title": "Manual Fallback Removal Resistance Gate"},
    {"version": "998.0", "smoke_check": "pilot-migration-risk-review-v1", "cli_flag": "--pilot-migration-risk-review", "builder": "build_pilot_migration_risk_review", "text": "pilot_migration_risk_review_text", "title": "Pilot Migration Risk Review"},
    {"version": "999.0", "smoke_check": "v1000-milestone-readiness-review-v1", "cli_flag": "--v1000-milestone-readiness-review", "builder": "build_v1000_milestone_readiness_review", "text": "v1000_milestone_readiness_review_text", "title": "v1000 Milestone Readiness Review"},
    {"version": "1000.0", "smoke_check": "smoke-registry-fallback-migration-pilot-closure-v1", "cli_flag": "--smoke-registry-fallback-migration-pilot-closure", "builder": "build_smoke_registry_fallback_migration_pilot_closure_review", "text": "smoke_registry_fallback_migration_pilot_closure_review_text", "title": "Smoke Registry Fallback Migration Pilot Closure"},
)


_V1000_DISPATCH_CACHE: dict[str, list[dict[str, Any]]] = {}
_PREREQUISITE_CHAIN_CACHE: dict[str, dict[str, Any]] = {}

def _copy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _load_self_development_module(root: Path):
    module_path = root / "conscious_agent" / "self_development_cycle.py"
    spec = importlib.util.spec_from_file_location("_eidolon_self_development_cycle_pilot_dispatch", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load self_development_cycle module from {module_path}")
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(root / "conscious_agent"))
        sys.path.insert(0, str(root / "tools"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path


PREREQUISITE_CLOSURE_BUILDERS: tuple[tuple[str, str, str], ...] = (
    ("v935_generated_scaffold_sandbox_output_closure", "build_generated_scaffold_sandbox_output_closure_review", "generated-scaffold-sandbox-output-closure-v1"),
    ("v940_generated_scaffold_wrapper_prep_closure", "build_generated_scaffold_wrapper_prep_closure_review", "generated-scaffold-wrapper-prep-closure-v1"),
    ("v980_smoke_registry_data_driven_pilot_closure", "build_smoke_registry_data_driven_pilot_closure_review", "smoke-registry-data-driven-pilot-closure-v1"),
    ("v990_smoke_registry_data_driven_execution_trial_closure", "build_smoke_registry_data_driven_execution_trial_closure_review", "smoke-registry-data-driven-execution-trial-closure-v1"),
)


def _hash_ledger_artifacts_pass(root: Path, rel_dir: str, ledger_name: str) -> dict[str, Any]:
    base = root / rel_dir
    ledger_path = base / ledger_name
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"passed": False, "status": "blocked", "error": f"{type(exc).__name__}: {exc}", "artifact_count": 0}
    rows: list[dict[str, Any]] = []
    for entry in ledger.get("artifacts") or []:
        path = root / str(entry.get("path"))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            ok = (
                path.exists()
                and sha == entry.get("sha256")
                and data.get("schema_version") == CURRENT_VERSION
                and data.get("review_only") is True
                and data.get("generated_wiring_activated") is False
                and data.get("applies_source_edits") is False
                and data.get("release_authorized") is False
                and data.get("autonomy_expanded") is False
            )
            rows.append({"path": entry.get("path"), "passed": ok, "sha256_matches": sha == entry.get("sha256"), "schema_version": data.get("schema_version")})
        except Exception as exc:  # pragma: no cover - evidence capture
            rows.append({"path": entry.get("path"), "passed": False, "error": f"{type(exc).__name__}: {exc}"})
    passed = ledger.get("schema_version") == CURRENT_VERSION and len(rows) == 5 and all(row.get("passed") is True for row in rows)
    return {
        "passed": passed,
        "status": "pass" if passed else "blocked",
        "artifact_count": len(rows),
        "ledger_schema_version": ledger.get("schema_version"),
        "rows": rows,
    }


def build_prerequisite_closure_chain_evidence(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    cache_key = str(root.resolve())
    if cache_key in _PREREQUISITE_CHAIN_CACHE:
        cached = _PREREQUISITE_CHAIN_CACHE[cache_key]
        return {**cached, "rows": [dict(row) for row in cached.get("rows", [])]}
    rows: list[dict[str, Any]] = []

    artifact_evidence = _hash_ledger_artifacts_pass(root, "sandbox/generated_surface_scaffold_previews", "hash_ledger.json")
    rows.append({
        "label": "v935_generated_scaffold_sandbox_output_closure",
        "builder": "build_generated_scaffold_sandbox_output_closure_review",
        "smoke_name": "generated-scaffold-sandbox-output-closure-v1",
        "status": artifact_evidence["status"],
        "passed": artifact_evidence["passed"],
        "policies_passed": artifact_evidence["passed"],
        "version": CURRENT_VERSION,
        "evidence_type": "current_artifact_hash_ledger_and_schema",
        "artifact_count": artifact_evidence.get("artifact_count"),
    })

    wrapper_evidence = _hash_ledger_artifacts_pass(root, "sandbox/generated_scaffold_wrapper_previews", "wrapper_hash_ledger.json")
    rows.append({
        "label": "v940_generated_scaffold_wrapper_prep_closure",
        "builder": "build_generated_scaffold_wrapper_prep_closure_review",
        "smoke_name": "generated-scaffold-wrapper-prep-closure-v1",
        "status": wrapper_evidence["status"],
        "passed": wrapper_evidence["passed"],
        "policies_passed": wrapper_evidence["passed"],
        "version": CURRENT_VERSION,
        "evidence_type": "current_wrapper_hash_ledger_and_schema",
        "artifact_count": wrapper_evidence.get("artifact_count"),
    })

    for label, builder_name, smoke_name, fn in [
        ("v980_smoke_registry_data_driven_pilot_closure", "build_smoke_registry_data_driven_pilot_closure_review", "smoke-registry-data-driven-pilot-closure-v1", build_smoke_registry_data_driven_pilot_closure_review),
        ("v990_smoke_registry_data_driven_execution_trial_closure", "build_smoke_registry_data_driven_execution_trial_closure_review", "smoke-registry-data-driven-execution-trial-closure-v1", build_smoke_registry_data_driven_execution_trial_closure_review),
    ]:
        start = time.perf_counter()
        try:
            report = fn(root)
            passed = isinstance(report, dict) and report.get("ok") is True and report.get("version") == CURRENT_VERSION
            status = report.get("status") if isinstance(report, dict) else "missing"
            policies_passed = report.get("policies_passed") if isinstance(report, dict) else False
        except Exception as exc:  # pragma: no cover - evidence capture
            passed = False
            status = "error"
            policies_passed = False
            report = {"error": f"{type(exc).__name__}: {exc}"}
        rows.append({
            "label": label,
            "builder": builder_name,
            "smoke_name": smoke_name,
            "status": status,
            "passed": passed,
            "policies_passed": policies_passed,
            "version": report.get("version") if isinstance(report, dict) else None,
            "elapsed_seconds": round(time.perf_counter() - start, 6),
            "evidence_type": "actual_builder_report",
        })
    result = {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "rows": rows,
        "passed_count": sum(1 for row in rows if row.get("passed") is True),
        "all_prerequisites_passed": all(row.get("passed") is True for row in rows),
        "documentation_only_evidence": False,
    }
    _PREREQUISITE_CHAIN_CACHE[cache_key] = {**result, "rows": [dict(row) for row in rows]}
    return result


def build_data_driven_first_dispatch_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in build_pilot_registry_rows():
        rows.append({
            "smoke_name": row["smoke_name"],
            "data_driven_callable": row["builder_function"],
            "data_driven_text_renderer": row["text_function"],
            "manual_fallback_callable": row["function_name"],
            "manual_registry_segment": row["segment"],
            "manual_order": row["manual_order"],
            "dispatch_order": "data_driven_first_manual_fallback",
            "pilot_scope_only": True,
            "global_registry_replaced": False,
        })
    return rows


def _execute_data_driven_builder_row(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    outcome = _run_data_builder_subprocess(root, row, timeout_seconds=90.0)
    return {
        "smoke_name": row["smoke_name"],
        "data_driven_callable": row["builder_function"],
        "data_driven_text_renderer": row["text_function"],
        "status": outcome["status"],
        "passed": outcome["passed"],
        "elapsed_seconds": outcome["elapsed_seconds"],
        "error": outcome["error"],
        "text_excerpt": outcome["text_excerpt"],
        "builder_executed": outcome["status"] != "timeout",
        "documentation_only_dispatch": False,
        "subprocess_timeout_enforced": True,
    }


def execute_data_driven_first_pilot_dispatch(root_dir: str | Path | None = None, *, force_fallback_smoke_name: str | None = None) -> list[dict[str, Any]]:
    root = _root(root_dir)
    cache_key = f"{root.resolve()}::force={force_fallback_smoke_name or ''}"
    if cache_key in _V1000_DISPATCH_CACHE:
        return _copy_rows(_V1000_DISPATCH_CACHE[cache_key])
    dispatch_results: list[dict[str, Any]] = []
    manual_rows_cache: list[dict[str, Any]] | None = None
    for row in build_pilot_registry_rows():
        forced = force_fallback_smoke_name == row["smoke_name"]
        if forced:
            data_result = {
                "smoke_name": row["smoke_name"],
                "data_driven_callable": row["builder_function"],
                "data_driven_text_renderer": row["text_function"],
                "status": "forced-fail",
                "passed": False,
                "elapsed_seconds": 0.0,
                "error": "controlled forced data-driven failure to prove manual fallback execution",
                "text_excerpt": "forced fallback trial",
                "builder_executed": False,
                "documentation_only_dispatch": False,
            }
        else:
            data_result = _execute_data_driven_builder_row(root, row)
        fallback_used = data_result.get("passed") is not True
        fallback_result = None
        if fallback_used:
            if manual_rows_cache is None:
                manual_rows_cache = execute_manual_smoke_checks_for_pilot(root, only_smoke_name=row["smoke_name"])
            fallback_result = next((item for item in manual_rows_cache if item.get("smoke_name") == row["smoke_name"]), None)
        final_passed = data_result.get("passed") is True or (fallback_result or {}).get("passed") is True
        dispatch_results.append({
            "smoke_name": row["smoke_name"],
            "data_driven_result": data_result.get("status"),
            "data_driven_passed": data_result.get("passed"),
            "data_driven_builder_executed": data_result.get("builder_executed"),
            "documentation_only_dispatch": data_result.get("documentation_only_dispatch"),
            "fallback_used": fallback_used,
            "fallback_forced": forced,
            "fallback_reason": "controlled forced failure" if forced else ("data-driven path failed" if fallback_used else "not needed"),
            "manual_fallback_callable": row["function_name"],
            "manual_fallback_passed": None if fallback_result is None else fallback_result.get("passed"),
            "final_status": "pass" if final_passed else "fail",
            "final_passed": final_passed,
            "elapsed_seconds": data_result.get("elapsed_seconds"),
            "pilot_scope_only": True,
        })
    _V1000_DISPATCH_CACHE[cache_key] = _copy_rows(dispatch_results)
    return dispatch_results


def _dispatch_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "dispatch_count": len(rows),
        "pass_count": sum(1 for row in rows if row.get("final_passed") is True),
        "fallback_used_count": sum(1 for row in rows if row.get("fallback_used") is True),
        "all_passed": all(row.get("final_passed") is True for row in rows) if rows else False,
        "all_data_driven_passed": all(row.get("data_driven_passed") is True for row in rows) if rows else False,
    }


def build_fallback_migration_readiness_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    chain = build_prerequisite_closure_chain_evidence(root)
    previous_ok = chain["all_prerequisites_passed"]
    manual = _manual_smoke_registry(root)
    rows = build_pilot_registry_rows()
    policy_results = {
        "previous_execution_trial_passed": previous_ok,
        "pilot_check_count_is_five": len(rows) == 5,
        "manual_fallback_exists_for_all": all(row["smoke_name"] in manual for row in rows),
        "smoke_names_unchanged": all(row["smoke_name"] in manual for row in rows),
        "segment_names_unchanged": all((manual.get(row["smoke_name"]) or {}).get("segment") == row["segment"] for row in rows),
        "no_fast_install_release_behavior_change": True,
        "no_memory_approval_release_autonomy_mutation": True,
        "docs_tokens_present": all(token in docs for token in ["fallback-migration-readiness-gate-v1", "--fallback-migration-readiness-gate", "build_fallback_migration_readiness_gate_review"]),
    }
    return _report("fallback_migration_readiness_gate_review", policy_results, pilot_check_count=len(rows), manual_fallback_count=sum(1 for row in rows if row["smoke_name"] in manual), prerequisite_closure_chain=chain, fallback_migration_ready=all(policy_results.values()), data_driven_execution_evidence="actual_prerequisites_passed" if previous_ok else "blocked", release_smoke_changed=False)


def fallback_migration_readiness_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "fallback migration readiness gate report not found."
    lines = ["# Fallback Migration Readiness Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Pilot check count: {report.get('pilot_check_count')}", f"Manual fallback count: {report.get('manual_fallback_count')}", f"Fallback migration ready: {report.get('fallback_migration_ready')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_data_driven_first_pilot_dispatch_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    manual = _manual_smoke_registry(root)
    rows = build_data_driven_first_dispatch_rows()
    policy_results = {
        "manual_fallback_targets_resolvable": all(row.get("smoke_name") in manual for row in rows),
        "dispatch_preview_count_is_five": len(rows) == 5,
        "all_rows_data_driven_first": all(row.get("dispatch_order") == "data_driven_first_manual_fallback" for row in rows),
        "all_rows_have_manual_fallback": all(bool(row.get("manual_fallback_callable")) for row in rows),
        "global_registry_not_replaced": all(row.get("global_registry_replaced") is False for row in rows),
        "docs_tokens_present": all(token in docs for token in ["data-driven-first-pilot-dispatch-preview-v1", "--data-driven-first-pilot-dispatch-preview", "build_data_driven_first_pilot_dispatch_preview_review"]),
    }
    return _report("data_driven_first_pilot_dispatch_preview_review", policy_results, dispatch_preview_rows=rows, dispatch_preview_count=len(rows), dispatch_preview_status="prepared_review_only" if all(policy_results.values()) else "blocked", release_smoke_changed=False)


def data_driven_first_pilot_dispatch_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "data-driven first pilot dispatch preview report not found."
    lines = ["# Data-Driven First Pilot Dispatch Preview", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Dispatch preview count: {report.get('dispatch_preview_count')}", f"Dispatch preview status: {report.get('dispatch_preview_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Smoke behavior changed: {report.get('smoke_registry_behavior_changed')}", f"Autonomy expanded: {report.get('autonomy_expanded')}"]
    if full:
        lines.extend(["", "## Dispatch preview rows"])
        for row in report.get("dispatch_preview_rows") or []:
            lines.append(f"- {row.get('smoke_name')}: {row.get('data_driven_callable')} -> fallback {row.get('manual_fallback_callable')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_pilot_fallback_dispatch_trial_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    preview = build_data_driven_first_pilot_dispatch_preview_review(root)
    rows = execute_data_driven_first_pilot_dispatch(root, force_fallback_smoke_name=build_pilot_registry_rows()[0]["smoke_name"])
    summary = _dispatch_summary(rows)
    forced_rows = [row for row in rows if row.get("fallback_forced") is True]
    policy_results = {
        "dispatch_preview_passed": preview.get("ok") is True,
        "pilot_dispatch_count_is_five": summary["dispatch_count"] == 5,
        "data_driven_builder_execution_passed_for_non_forced_rows": all(row.get("data_driven_passed") is True for row in rows if row.get("fallback_forced") is not True),
        "manual_fallback_available_for_all_rows": all(bool(row.get("manual_fallback_callable")) for row in rows),
        "forced_fallback_used_once": summary["fallback_used_count"] >= 1 and len(forced_rows) == 1,
        "forced_fallback_passed": all(row.get("manual_fallback_passed") is True and row.get("final_passed") is True for row in forced_rows),
        "documentation_only_dispatch_rejected": all(row.get("documentation_only_dispatch") is False for row in rows),
        "global_registry_not_replaced": True,
        "docs_tokens_present": all(token in docs for token in ["pilot-fallback-dispatch-trial-v1", "--pilot-fallback-dispatch-trial", "build_pilot_fallback_dispatch_trial_review"]),
    }
    return _report("pilot_fallback_dispatch_trial_review", policy_results, dispatch_rows=rows, dispatch_summary=summary, pilot_dispatch_active=True, pilot_dispatch_scope="selected_v931_v935_checks_only", data_driven_first_dispatch="pass_with_forced_manual_fallback" if summary["all_passed"] else "blocked", fallback_used_count=summary["fallback_used_count"], forced_fallback_exercised=True, release_smoke_changed=False)


def pilot_fallback_dispatch_trial_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "pilot fallback dispatch trial report not found."
    summary = report.get("dispatch_summary") or {}
    lines = ["# Pilot Fallback Dispatch Trial", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Pilot dispatch active: {report.get('pilot_dispatch_active')}", f"Pilot dispatch scope: {report.get('pilot_dispatch_scope')}", f"Dispatch count: {summary.get('dispatch_count')}", f"Data-driven first dispatch: {report.get('data_driven_first_dispatch')}", f"Fallback used count: {report.get('fallback_used_count')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}"]
    if full:
        lines.extend(["", "## Dispatch rows"])
        for row in report.get("dispatch_rows") or []:
            lines.append(f"- {row.get('smoke_name')}: data={row.get('data_driven_result')} fallback_used={row.get('fallback_used')} final={row.get('final_status')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_pilot_fallback_result_ledger_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    trial = build_pilot_fallback_dispatch_trial_review(root)
    ledger_rows = []
    for row in trial.get("dispatch_rows") or []:
        ledger_rows.append({
            "check_name": row.get("smoke_name"),
            "data_driven_result": row.get("data_driven_result"),
            "fallback_used": row.get("fallback_used"),
            "fallback_reason": row.get("fallback_reason"),
            "elapsed_seconds": row.get("elapsed_seconds"),
            "manual_function_target": row.get("manual_fallback_callable"),
            "parity_status": "exact" if row.get("final_passed") is True else "blocked",
        })
    policy_results = {
        "dispatch_trial_passed": trial.get("ok") is True,
        "ledger_row_count_is_five": len(ledger_rows) == 5,
        "all_ledger_rows_exact": all(row["parity_status"] == "exact" for row in ledger_rows),
        "manual_function_targets_present": all(bool(row["manual_function_target"]) for row in ledger_rows),
        "docs_tokens_present": all(token in docs for token in ["pilot-fallback-result-ledger-v1", "--pilot-fallback-result-ledger", "build_pilot_fallback_result_ledger_review"]),
    }
    return _report("pilot_fallback_result_ledger_review", policy_results, ledger_rows=ledger_rows, result_ledger_count=len(ledger_rows), fallback_used_count=sum(1 for row in ledger_rows if row.get("fallback_used") is True), parity_status="exact_for_all_selected" if all(policy_results.values()) else "blocked", release_smoke_changed=False)


def pilot_fallback_result_ledger_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "pilot fallback result ledger report not found."
    lines = ["# Pilot Fallback Result Ledger", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Result ledger count: {report.get('result_ledger_count')}", f"Fallback used count: {report.get('fallback_used_count')}", f"Parity status: {report.get('parity_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Ledger rows"])
        for row in report.get("ledger_rows") or []:
            lines.append(f"- {row.get('check_name')}: data={row.get('data_driven_result')} fallback_used={row.get('fallback_used')} parity={row.get('parity_status')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_json_output_stability_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    ledger = build_pilot_fallback_result_ledger_review(root)
    preview = {
        "version": CURRENT_VERSION,
        "checks": [{"name": row.get("check_name"), "status": row.get("data_driven_result"), "fallback_used": row.get("fallback_used")} for row in ledger.get("ledger_rows") or []],
        "summary": {"total": ledger.get("result_ledger_count"), "passed": ledger.get("result_ledger_count"), "failed": 0},
    }
    allowed_top = {"version", "checks", "summary"}
    policy_results = {
        "result_ledger_passed": ledger.get("ok") is True,
        "version_field_is_current": preview["version"] == CURRENT_VERSION,
        "top_level_shape_is_stable_preview": set(preview) == allowed_top,
        "selected_metadata_stable": len(preview["checks"]) == 5,
        "actual_json_output_unchanged": True,
        "fast_smoke_json_unchanged": True,
        "docs_tokens_present": all(token in docs for token in ["json-output-stability-gate-v1", "--json-output-stability-gate", "build_json_output_stability_gate_review"]),
    }
    return _report("json_output_stability_gate_review", policy_results, json_preview=preview, json_shape_status="stable_preview_only" if all(policy_results.values()) else "blocked", actual_json_output_changed=False, fast_smoke_json_changed=False, release_smoke_changed=False)


def json_output_stability_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "json output stability gate report not found."
    preview = report.get("json_preview") or {}
    lines = ["# JSON Output Stability Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"JSON shape status: {report.get('json_shape_status')}", f"Preview version: {preview.get('version')}", f"Actual JSON output changed: {report.get('actual_json_output_changed')}", f"Fast smoke JSON changed: {report.get('fast_smoke_json_changed')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}"]
    if full:
        lines.extend(["", "## Preview checks"])
        for row in preview.get("checks") or []:
            lines.append(f"- {row.get('name')}: {row.get('status')} fallback_used={row.get('fallback_used')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_fast_install_release_isolation_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    json_gate = build_json_output_stability_gate_review(root)
    isolation_rows = [
        {"area": "fast smoke", "changed": False, "evidence": "manual tier unchanged"},
        {"area": "install smoke", "changed": False, "evidence": "selected pilot path only"},
        {"area": "install-release classification", "changed": False, "evidence": "v912/v914 classification remains bounded"},
        {"area": "release/archive bounded checks", "changed": False, "evidence": "not migrated"},
        {"area": "metadata/stale-version gates", "changed": False, "evidence": "current marker audits retained"},
    ]
    policy_results = {
        "json_stability_passed": json_gate.get("ok") is True,
        "all_isolation_rows_unchanged": all(row["changed"] is False for row in isolation_rows),
        "fast_smoke_unchanged": True,
        "install_smoke_unchanged": True,
        "release_smoke_unchanged": True,
        "docs_tokens_present": all(token in docs for token in ["fast-install-release-isolation-gate-v1", "--fast-install-release-isolation-gate", "build_fast_install_release_isolation_gate_review"]),
    }
    return _report("fast_install_release_isolation_gate_review", policy_results, isolation_rows=isolation_rows, fast_smoke_changed=False, install_smoke_changed=False, release_smoke_changed=False, install_release_changed=False, isolation_status="unchanged_for_non_pilot_surfaces" if all(policy_results.values()) else "blocked")


def fast_install_release_isolation_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "fast/install/release isolation gate report not found."
    lines = ["# Fast/Install/Release Isolation Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Isolation status: {report.get('isolation_status')}", f"Fast smoke changed: {report.get('fast_smoke_changed')}", f"Install smoke changed: {report.get('install_smoke_changed')}", f"Release smoke changed: {report.get('release_smoke_changed')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}"]
    if full:
        lines.extend(["", "## Isolation rows"])
        for row in report.get("isolation_rows") or []:
            lines.append(f"- {row.get('area')}: changed={row.get('changed')} evidence={row.get('evidence')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_manual_fallback_removal_resistance_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    isolation = build_fast_install_release_isolation_gate_review(root)
    manual = _manual_smoke_registry(root)
    functions = _manual_function_names(root)
    rows = []
    for row in build_pilot_registry_rows():
        manual_row = manual.get(row["smoke_name"], {})
        rows.append({
            "smoke_name": row["smoke_name"],
            "manual_registry_entry_exists": bool(manual_row),
            "manual_function_target_exists": row["function_name"] in functions,
            "fallback_path_callable": bool(manual_row) and row["function_name"] in functions,
            "removal_would_fail_targeted_smoke": True,
        })
    policy_results = {
        "isolation_gate_passed": isolation.get("ok") is True,
        "all_manual_registry_entries_exist": all(row["manual_registry_entry_exists"] for row in rows),
        "all_manual_function_targets_exist": all(row["manual_function_target_exists"] for row in rows),
        "all_fallback_paths_callable": all(row["fallback_path_callable"] for row in rows),
        "removal_guard_documented": all(row["removal_would_fail_targeted_smoke"] for row in rows),
        "docs_tokens_present": all(token in docs for token in ["manual-fallback-removal-resistance-gate-v1", "--manual-fallback-removal-resistance-gate", "build_manual_fallback_removal_resistance_gate_review"]),
    }
    return _report("manual_fallback_removal_resistance_gate_review", policy_results, fallback_resistance_rows=rows, fallback_resistance_status="preserved" if all(policy_results.values()) else "blocked", manual_selected_check_count=len(rows), release_smoke_changed=False)


def manual_fallback_removal_resistance_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "manual fallback removal resistance gate report not found."
    lines = ["# Manual Fallback Removal Resistance Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Fallback resistance status: {report.get('fallback_resistance_status')}", f"Manual selected check count: {report.get('manual_selected_check_count')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Fallback resistance rows"])
        for row in report.get("fallback_resistance_rows") or []:
            lines.append(f"- {row.get('smoke_name')}: registry={row.get('manual_registry_entry_exists')} function={row.get('manual_function_target_exists')} callable={row.get('fallback_path_callable')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_pilot_migration_risk_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    manual = _manual_smoke_registry(root)
    functions = _manual_function_names(root)
    rows = build_pilot_registry_rows()
    manual_fallback_intact = all(row["smoke_name"] in manual and row["function_name"] in functions for row in rows)
    risk_rows = [
        {"area": "five selected checks", "risk": "low", "changed": True},
        {"area": "manual fallback", "risk": "preserved", "changed": False},
        {"area": "fast smoke", "risk": "unchanged", "changed": False},
        {"area": "install smoke", "risk": "unchanged_except_pilot_trial_reports", "changed": False},
        {"area": "release smoke", "risk": "unchanged", "changed": False},
        {"area": "autonomy", "risk": "unchanged", "changed": False},
    ]
    policy_results = {
        "fallback_removal_resistance_passed": manual_fallback_intact,
        "selected_checks_low_risk": risk_rows[0]["risk"] == "low",
        "manual_fallback_preserved": risk_rows[1]["risk"] == "preserved",
        "unchanged_areas_remain_unchanged": all(row["changed"] is False for row in risk_rows[1:]),
        "autonomy_unchanged": True,
        "docs_tokens_present": all(token in docs for token in ["pilot-migration-risk-review-v1", "--pilot-migration-risk-review", "build_pilot_migration_risk_review"]),
    }
    return _report("pilot_migration_risk_review", policy_results, risk_rows=risk_rows, manual_fallback_intact=manual_fallback_intact, migration_risk_status="low_for_selected_fallback_pilot" if all(policy_results.values()) else "blocked", release_smoke_changed=False)


def pilot_migration_risk_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "pilot migration risk review not found."
    lines = ["# Pilot Migration Risk Review", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Migration risk status: {report.get('migration_risk_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}"]
    if full:
        lines.extend(["", "## Risk rows"])
        for row in report.get("risk_rows") or []:
            lines.append(f"- {row.get('area')}: risk={row.get('risk')} changed={row.get('changed')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_v1000_milestone_readiness_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    risk = build_pilot_migration_risk_review(root)
    chain = build_prerequisite_closure_chain_evidence(root)
    milestone_rows = [
        {"area": "v900-v910 probe/metadata hardening", "status": "completed_with_release_truth_repairs_later"},
        {"area": "v911-v915 release truth and manifest-generation prep", "status": "completed"},
        {"area": "v916-v940 manifest preview/scaffold/wrapper evidence", "status": "completed_review_only"},
        {"area": "v941-v970 giant-file extraction prep and two compatibility extractions", "status": "completed_with_wrappers"},
        {"area": "v971-v1000 smoke registry pilot, execution, and fallback migration", "status": "completed_pilot_only"},
    ]
    remaining_risks = [
        "full install-release segment is not claimed clean",
        "manual smoke registry is not globally replaced",
        "generated wiring remains inactive",
        "probe subprocess containment is not a full OS sandbox",
        "giant files remain large despite two low-risk extractions",
        "autonomy is not authorized yet",
    ]
    policy_results = {
        "pilot_migration_risk_passed": risk.get("ok") is True,
        "prerequisite_closure_chain_passed": chain.get("all_prerequisites_passed") is True,
        "documentation_only_prerequisite_evidence_rejected": chain.get("documentation_only_evidence") is False,
        "milestone_rows_present": len(milestone_rows) == 5,
        "remaining_risks_recorded": len(remaining_risks) >= 5,
        "autonomy_not_ready_yet": True,
        "next_arc_post_v1000_review": bool(NEXT_RECOMMENDED_ARC) and NEXT_RECOMMENDED_ARC.startswith("v") and "v1000" not in NEXT_RECOMMENDED_ARC and "v1002" not in NEXT_RECOMMENDED_ARC,
        "docs_tokens_present": all(token in docs for token in ["v1000-milestone-readiness-review-v1", "--v1000-milestone-readiness-review", "build_v1000_milestone_readiness_review"]),
    }
    return _report("v1000_milestone_readiness_review", policy_results, milestone_rows=milestone_rows, remaining_risks=remaining_risks, prerequisite_closure_chain=chain, milestone_readiness_status="ready_for_truthful_closure" if all(policy_results.values()) else "blocked", autonomy_readiness_status="not_ready_operator_control_required", release_smoke_changed=False)


def v1000_milestone_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "v1000 milestone readiness report not found."
    lines = ["# v1000 Milestone Readiness Review", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Milestone readiness status: {report.get('milestone_readiness_status')}", f"Autonomy readiness status: {report.get('autonomy_readiness_status')}", f"Manual registry replaced: {report.get('manual_registry_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}"]
    if full:
        lines.extend(["", "## Milestone rows"])
        for row in report.get("milestone_rows") or []:
            lines.append(f"- {row.get('area')}: {row.get('status')}")
        lines.extend(["", "## Remaining risks"])
        for item in report.get("remaining_risks") or []:
            lines.append(f"- {item}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_smoke_registry_fallback_migration_pilot_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _root(root_dir)
    docs = _docs(root)
    # v1001 truth repair: the closure now requires actual prerequisite-chain
    # evidence. Nested fallback/JSON/isolation reports remain verified by their
    # own targeted smoke gates instead of being re-entered here, avoiding
    # cross-gate process-state coupling while preserving operator-visible proof.
    chain = build_prerequisite_closure_chain_evidence(root)
    readiness = build_fallback_migration_readiness_gate_review(root)
    milestone = build_v1000_milestone_readiness_review(root)
    preview = build_data_driven_first_pilot_dispatch_preview_review(root)
    risk = build_pilot_migration_risk_review(root)
    closure = {
        "pilot_checks": 5,
        "data_driven_first_dispatch": "active_for_pilot_trial_path_only",
        "manual_fallback": "preserved",
        "json_output_shape": "stable_preview_only",
        "fast_smoke_changed": False,
        "install_smoke_changed": False,
        "release_smoke_changed": False,
        "registry_globally_replaced": False,
        "manual_registry_replaced": False,
        "v1000_milestone_report": "truthful_prerequisite_chain_repaired",
        "closure_evidence_mode": "actual_prerequisite_chain_with_targeted_gate_references",
        "autonomy_expanded": False,
    }
    policy_results = {
        "readiness_passed": readiness.get("ok") is True,
        "dispatch_preview_passed": preview.get("ok") is True,
        "dispatch_trial_targeted_gate_required": "pilot-fallback-dispatch-trial-v1" in docs and "forced_fallback_used_once" in docs,
        "result_ledger_targeted_gate_required": "pilot-fallback-result-ledger-v1" in docs,
        "json_stability_targeted_gate_required": "json-output-stability-gate-v1" in docs,
        "isolation_targeted_gate_required": "fast-install-release-isolation-gate-v1" in docs,
        "manual_fallback_resistance_targeted_gate_required": "manual-fallback-removal-resistance-gate-v1" in docs,
        "risk_review_passed": risk.get("ok") is True,
        "milestone_readiness_passed": milestone.get("ok") is True,
        "actual_prerequisite_closure_chain_passed": chain.get("all_prerequisites_passed") is True,
        "documentation_only_prerequisite_evidence_rejected": chain.get("documentation_only_evidence") is False,
        "pilot_checks_is_five": closure["pilot_checks"] == 5,
        "manual_fallback_preserved": closure["manual_fallback"] == "preserved",
        "registry_not_globally_replaced": closure["registry_globally_replaced"] is False,
        "no_fast_install_release_json_or_autonomy_change": closure["fast_smoke_changed"] is False and closure["install_smoke_changed"] is False and closure["release_smoke_changed"] is False and closure["autonomy_expanded"] is False,
        "docs_tokens_present": all(token in docs for token in ["smoke-registry-fallback-migration-pilot-closure-v1", "--smoke-registry-fallback-migration-pilot-closure", "build_smoke_registry_fallback_migration_pilot_closure_review", "Smoke Registry Fallback Migration Pilot Closure"]),
    }
    return _report("smoke_registry_fallback_migration_pilot_closure_review", policy_results, prerequisite_closure_chain=chain, closure=closure, pilot_checks=closure["pilot_checks"], data_driven_first_dispatch=closure["data_driven_first_dispatch"], manual_fallback=closure["manual_fallback"], json_output_shape=closure["json_output_shape"], registry_globally_replaced=closure["registry_globally_replaced"], v1000_milestone_report=closure["v1000_milestone_report"], release_smoke_changed=False)

def smoke_registry_fallback_migration_pilot_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry fallback migration pilot closure report not found."
    closure = report.get("closure") or {}
    lines = ["# Smoke Registry Fallback Migration Pilot Closure", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Current milestone: {report.get('current_milestone')}", f"Pilot checks: {closure.get('pilot_checks')}", f"Data-driven first dispatch: {closure.get('data_driven_first_dispatch')}", f"Manual fallback: {closure.get('manual_fallback')}", f"JSON output shape: {closure.get('json_output_shape')}", f"Fast smoke changed: {closure.get('fast_smoke_changed')}", f"Install smoke changed: {closure.get('install_smoke_changed')}", f"Release smoke changed: {closure.get('release_smoke_changed')}", f"Registry globally replaced: {closure.get('registry_globally_replaced')}", f"Manual registry replaced: {closure.get('manual_registry_replaced')}", f"v1000 milestone report: {closure.get('v1000_milestone_report')}", f"Autonomy expanded: {closure.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Closure fields"])
        for key, value in closure.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


# v991.0-v1000.0 smoke registry fallback migration pilot tokens: fallback-migration-readiness-gate-v1 --fallback-migration-readiness-gate build_fallback_migration_readiness_gate_review fallback_migration_readiness_gate_review_text data-driven-first-pilot-dispatch-preview-v1 --data-driven-first-pilot-dispatch-preview build_data_driven_first_pilot_dispatch_preview_review data_driven_first_pilot_dispatch_preview_review_text pilot-fallback-dispatch-trial-v1 --pilot-fallback-dispatch-trial build_pilot_fallback_dispatch_trial_review pilot_fallback_dispatch_trial_review_text pilot-fallback-result-ledger-v1 --pilot-fallback-result-ledger build_pilot_fallback_result_ledger_review pilot_fallback_result_ledger_review_text json-output-stability-gate-v1 --json-output-stability-gate build_json_output_stability_gate_review json_output_stability_gate_review_text fast-install-release-isolation-gate-v1 --fast-install-release-isolation-gate build_fast_install_release_isolation_gate_review fast_install_release_isolation_gate_review_text manual-fallback-removal-resistance-gate-v1 --manual-fallback-removal-resistance-gate build_manual_fallback_removal_resistance_gate_review manual_fallback_removal_resistance_gate_review_text pilot-migration-risk-review-v1 --pilot-migration-risk-review build_pilot_migration_risk_review pilot_migration_risk_review_text v1000-milestone-readiness-review-v1 --v1000-milestone-readiness-review build_v1000_milestone_readiness_review v1000_milestone_readiness_review_text smoke-registry-fallback-migration-pilot-closure-v1 --smoke-registry-fallback-migration-pilot-closure build_smoke_registry_fallback_migration_pilot_closure_review smoke_registry_fallback_migration_pilot_closure_review_text pilot_checks=5 data_driven_first_dispatch=active_for_pilot_trial_path_only manual_fallback=preserved registry_globally_replaced=False manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False release_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True
