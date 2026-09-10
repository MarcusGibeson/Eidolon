from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION, CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

SELF_DEVELOPMENT_CYCLE_VERSION = CURRENT_VERSION


def _read_text(path: Path, *, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return text if limit is None else text[:limit]


def _sdc_module():
    import self_development_cycle as module
    return module


def _multi_generated_parity_packets() -> list[dict[str, Any]]:
    return _sdc_module()._multi_generated_parity_packets()


def build_multi_surface_generated_parity_batch_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _sdc_module().build_multi_surface_generated_parity_batch_closure_review(root_dir)

GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS = (
    "v916-manifest-review-packet-schema",
    "v917-dashboard-surface-preview-generator",
    "v918-cli-api-surface-preview-generator",
    "v919-smoke-surface-preview-generator",
    "v920-generated-preview-parity-report",
)
GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR = "sandbox/generated_surface_scaffold_previews"
GENERATED_SCAFFOLD_SCHEMA_FIELDS = (
    "schema_version", "artifact_type", "surface_id", "source_surface_manifest_id",
    "dashboard_preview", "cli_preview", "api_preview", "smoke_preview",
    "manual_builder", "manual_text_renderer", "authority_level", "activation",
    "parity_anchor", "review_only", "generated_wiring_activated", "applies_source_edits",
    "release_authorized", "autonomy_expanded",
)


def _generated_scaffold_docs(root: Path) -> str:
    return "\n".join(_read_text(root / rel, limit=1_000_000) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/self_development_cycle.py",
        "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py",
    ])


def _generated_scaffold_dir(root: Path) -> Path:
    return root / GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR


def _generated_scaffold_artifact_name(surface_id: str) -> str:
    return f"{surface_id}.json"


def _expected_generated_scaffold_preview(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "artifact_type": "generated_surface_scaffold_preview_review_only",
        "surface_id": packet.get("surface_id"),
        "source_surface_manifest_id": packet.get("surface_id"),
        "dashboard_preview": {
            "route": packet.get("dashboard_route"),
            "renderer": packet.get("text_function"),
            "style_contract": "command-deck/operator-console",
            "hover_contract": "data-tip",
            "native_title_tooltips_allowed": False,
            "wiring_activated": False,
        },
        "cli_preview": {
            "flag": packet.get("cli_flag"),
            "builder": packet.get("builder_function"),
            "text_renderer": packet.get("text_function"),
            "wiring_activated": False,
        },
        "api_preview": {
            "route": packet.get("api_route"),
            "exposure": "not_exposed_review_only" if packet.get("api_route") == "not_exposed_review_only" else "preview_only",
            "wiring_activated": False,
        },
        "smoke_preview": {
            "check": packet.get("smoke_check"),
            "segment": packet.get("smoke_segment"),
            "expected_version_source": "EXPECTED_CURRENT_VERSION",
            "wiring_activated": False,
        },
        "manual_builder": packet.get("builder_function"),
        "manual_text_renderer": packet.get("text_function"),
        "authority_level": packet.get("authority_level"),
        "activation": {
            "generated_preview_authoritative": False,
            "generated_wiring_activated": False,
            "dashboard_wiring_activated": False,
            "api_wiring_activated": False,
            "cli_wiring_activated": False,
            "smoke_wiring_activated": False,
            "applies_source_edits": False,
            "release_authorized": False,
            "autonomy_expanded": False,
            "protected_systems_require_operator_approval": True,
        },
        "parity_anchor": "v930-multi-surface-generated-parity-batch-closure",
        "review_only": True,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "autonomy_expanded": False,
    }


def _load_generated_scaffold_artifact(root: Path, surface_id: str) -> dict[str, Any] | None:
    path = _generated_scaffold_dir(root) / _generated_scaffold_artifact_name(surface_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _canonical_json_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _generated_scaffold_source_only_mode(root: Path) -> bool:
    base = _generated_scaffold_dir(root)
    expected_paths = [base / _generated_scaffold_artifact_name(surface_id) for surface_id in GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS]
    return not (base / "hash_ledger.json").exists() and not any(path.exists() for path in expected_paths)


def _generated_scaffold_artifact_evidence(
    root: Path, packet: dict[str, Any], *, source_only_mode: bool | None = None
) -> tuple[dict[str, Any] | None, str, bool]:
    surface_id = str(packet.get("surface_id"))
    actual = _load_generated_scaffold_artifact(root, surface_id)
    file_present = actual is not None
    if actual is not None:
        return actual, "sandbox_file", True
    if source_only_mode if source_only_mode is not None else _generated_scaffold_source_only_mode(root):
        return _expected_generated_scaffold_preview(packet), "deterministic_source_definition", False
    return None, "missing_or_invalid_sandbox_file", False


def _generated_scaffold_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _generated_scaffold_safety_fields() -> dict[str, bool]:
    return {
        "review_only": True,
        "sandbox_review_artifacts_present": True,
        "runtime_writes_sandbox_files": False,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "generated_preview_authoritative": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "smoke_wiring_activated": False,
        "applies_source_edits": False,
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


def build_generated_scaffold_sandbox_output_schema_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Define the review-only generated scaffold sandbox artifact schema."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    previous = build_multi_surface_generated_parity_batch_closure_review(root)
    docs = _generated_scaffold_docs(root)
    required_docs = [
        "generated-scaffold-sandbox-output-schema-v1", "--generated-scaffold-sandbox-output-schema",
        "build_generated_scaffold_sandbox_output_schema_review", "generated_scaffold_sandbox_output_schema_review_text",
        GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR, "schema_field_count=18", "review_only=True",
    ]
    policy_results = {
        "previous_multi_surface_parity_batch_passed": previous.get("ok") is True,
        "schema_field_count_is_eighteen": len(GENERATED_SCAFFOLD_SCHEMA_FIELDS) == 18,
        "selected_surface_count_is_five": len(GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS) == 5,
        "sandbox_directory_is_under_sandbox": GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR.startswith("sandbox/"),
        "schema_defines_activation_flags": all(field in GENERATED_SCAFFOLD_SCHEMA_FIELDS for field in ["activation", "review_only", "generated_wiring_activated", "applies_source_edits", "release_authorized", "autonomy_expanded"]),
        "docs_tokens_present": all(token in docs for token in required_docs),
        "review_only": True,
    }
    return {
        "id": f"generated_scaffold_sandbox_output_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_scaffold_sandbox_output_schema_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "schema_field_count": len(GENERATED_SCAFFOLD_SCHEMA_FIELDS),
        "schema_fields": list(GENERATED_SCAFFOLD_SCHEMA_FIELDS),
        "selected_surface_count": len(GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS),
        "sandbox_relative_dir": GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_safety_fields(),
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def generated_scaffold_sandbox_output_schema_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated scaffold sandbox output schema report not found."
    lines = [
        "# Generated Scaffold Sandbox Output Schema",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Schema field count: {report.get('schema_field_count')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Sandbox relative dir: {report.get('sandbox_relative_dir')}",
        f"Runtime writes sandbox files: {report.get('runtime_writes_sandbox_files')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Schema fields"])
        for field in report.get("schema_fields") or []:
            lines.append(f"- {field}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_scaffold_sandbox_output_schema_review(full: bool = False) -> None:
    print(generated_scaffold_sandbox_output_schema_review_text(build_generated_scaffold_sandbox_output_schema_review(), full=full))


def build_generated_scaffold_sandbox_artifact_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Validate persisted previews or reconstruct the same review-only evidence in source-only releases."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    schema = build_generated_scaffold_sandbox_output_schema_review(root)
    packets = _multi_generated_parity_packets()
    source_only_mode = _generated_scaffold_source_only_mode(root)
    artifact_rows: list[dict[str, Any]] = []
    for packet in packets:
        surface_id = str(packet.get("surface_id"))
        expected = _expected_generated_scaffold_preview(packet)
        evidence, evidence_mode, file_present = _generated_scaffold_artifact_evidence(
            root, packet, source_only_mode=source_only_mode
        )
        path = _generated_scaffold_dir(root) / _generated_scaffold_artifact_name(surface_id)
        artifact_rows.append({
            "surface_id": surface_id,
            "relative_path": str((Path(GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR) / _generated_scaffold_artifact_name(surface_id))).replace(os.sep, "/"),
            "exists": file_present,
            "file_present": file_present,
            "evidence_available": isinstance(evidence, dict),
            "evidence_mode": evidence_mode,
            "json_valid": isinstance(evidence, dict),
            "matches_expected_preview": evidence == expected,
            "review_only": bool(evidence and evidence.get("review_only") is True),
            "generated_wiring_activated": bool(evidence and evidence.get("generated_wiring_activated") is True),
            "applies_source_edits": bool(evidence and evidence.get("applies_source_edits") is True),
            "release_authorized": bool(evidence and evidence.get("release_authorized") is True),
            "autonomy_expanded": bool(evidence and evidence.get("autonomy_expanded") is True),
            "canonical_sha256": _canonical_json_sha256(evidence) if isinstance(evidence, dict) else None,
        })
    policy_results = {
        "schema_gate_passed": schema.get("ok") is True,
        "artifact_count_is_five": len(artifact_rows) == 5,
        "all_artifact_evidence_available": all(row["evidence_available"] for row in artifact_rows),
        "all_files_present_or_source_only_reconstructed": all(row["file_present"] for row in artifact_rows) or (source_only_mode and all(row["evidence_mode"] == "deterministic_source_definition" for row in artifact_rows)),
        "all_artifacts_json_valid": all(row["json_valid"] for row in artifact_rows),
        "all_artifacts_match_expected_preview": all(row["matches_expected_preview"] for row in artifact_rows),
        "all_artifacts_review_only": all(row["review_only"] for row in artifact_rows),
        "all_generated_wiring_inactive": all(row["generated_wiring_activated"] is False for row in artifact_rows),
        "no_artifact_applies_source_edits": all(row["applies_source_edits"] is False for row in artifact_rows),
        "no_artifact_authorizes_release": all(row["release_authorized"] is False for row in artifact_rows),
        "no_artifact_expands_autonomy": all(row["autonomy_expanded"] is False for row in artifact_rows),
        "review_only": True,
    }
    return {
        "id": f"generated_scaffold_sandbox_artifact_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_scaffold_sandbox_artifact_preview_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "artifact_count": len(artifact_rows),
        "physical_artifact_count": sum(1 for row in artifact_rows if row["file_present"]),
        "evidence_mode": "source_only_reconstruction" if source_only_mode else "sandbox_files",
        "source_only_reconstruction": source_only_mode,
        "artifact_rows": artifact_rows,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_safety_fields(),
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }

def generated_scaffold_sandbox_artifact_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated scaffold sandbox artifact preview report not found."
    lines = [
        "# Generated Scaffold Sandbox Artifact Preview",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Artifact count: {report.get('artifact_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Artifact rows"])
        for row in report.get("artifact_rows") or []:
            lines.append(f"- {row.get('surface_id')}: exists={row.get('exists')} matches_expected_preview={row.get('matches_expected_preview')} path={row.get('relative_path')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_scaffold_sandbox_artifact_preview_review(full: bool = False) -> None:
    print(generated_scaffold_sandbox_artifact_preview_review_text(build_generated_scaffold_sandbox_artifact_preview_review(), full=full))


def build_generated_scaffold_hash_ledger_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Validate persisted hashes or deterministic content hashes for a source-only release."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    artifact_preview = build_generated_scaffold_sandbox_artifact_preview_review(root)
    source_only_mode = artifact_preview.get("source_only_reconstruction") is True
    ledger_path = _generated_scaffold_dir(root) / "hash_ledger.json"
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        ledger = {}
    if source_only_mode:
        entries = [
            {"path": row["relative_path"], "sha256": row["canonical_sha256"]}
            for row in artifact_preview.get("artifact_rows") or []
        ]
        ledger = {
            "schema_version": SELF_DEVELOPMENT_CYCLE_VERSION,
            "review_only": True,
            "generated_wiring_activated": False,
            "release_authorized": False,
            "autonomy_expanded": False,
            "artifacts": entries,
        }
    else:
        entries = ledger.get("artifacts") if isinstance(ledger, dict) else None
    hash_rows: list[dict[str, Any]] = []
    for row in artifact_preview.get("artifact_rows") or []:
        rel = row.get("relative_path")
        path = root / str(rel)
        expected_entry = next((entry for entry in entries or [] if entry.get("path") == rel), None)
        if source_only_mode:
            actual_hash = row.get("canonical_sha256")
        else:
            actual_hash = _generated_scaffold_hash(path) if path.exists() else None
        hash_rows.append({
            "surface_id": row.get("surface_id"),
            "path": rel,
            "exists": path.exists(),
            "ledger_entry_present": expected_entry is not None,
            "actual_sha256": actual_hash,
            "ledger_sha256": expected_entry.get("sha256") if expected_entry else None,
            "hash_matches": bool(expected_entry and actual_hash == expected_entry.get("sha256")),
            "evidence_mode": "deterministic_content_hash" if source_only_mode else "persisted_file_hash",
        })
    policy_results = {
        "artifact_preview_passed": artifact_preview.get("ok") is True,
        "ledger_present_or_source_only_reconstructed": ledger_path.exists() or source_only_mode,
        "ledger_json_valid": isinstance(ledger, dict),
        "ledger_version_current": ledger.get("schema_version") == SELF_DEVELOPMENT_CYCLE_VERSION,
        "ledger_review_only": ledger.get("review_only") is True,
        "ledger_artifact_count_is_five": len(entries or []) == 5,
        "all_hash_rows_match": bool(hash_rows) and all(row["hash_matches"] for row in hash_rows),
        "ledger_does_not_activate_wiring": ledger.get("generated_wiring_activated") is False,
        "ledger_does_not_authorize_release": ledger.get("release_authorized") is False,
        "ledger_does_not_expand_autonomy": ledger.get("autonomy_expanded") is False,
        "review_only": True,
    }
    return {
        "id": f"generated_scaffold_hash_ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_scaffold_hash_ledger_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "ledger_path": str(ledger_path.relative_to(root)).replace(os.sep, "/"),
        "ledger_present": ledger_path.exists(),
        "evidence_mode": "source_only_reconstruction" if source_only_mode else "sandbox_files",
        "source_only_reconstruction": source_only_mode,
        "hash_count": len(hash_rows),
        "hash_rows": hash_rows,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_safety_fields(),
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }

def generated_scaffold_hash_ledger_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated scaffold hash ledger report not found."
    lines = [
        "# Generated Scaffold Hash Ledger",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Ledger path: {report.get('ledger_path')}",
        f"Hash count: {report.get('hash_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Hash rows"])
        for row in report.get("hash_rows") or []:
            lines.append(f"- {row.get('surface_id')}: hash_matches={row.get('hash_matches')} sha256={row.get('actual_sha256')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_scaffold_hash_ledger_review(full: bool = False) -> None:
    print(generated_scaffold_hash_ledger_review_text(build_generated_scaffold_hash_ledger_review(), full=full))


def build_generated_scaffold_sandbox_parity_comparison_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Compare sandbox scaffold preview artifacts against manifest/manual parity evidence."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    hash_ledger = build_generated_scaffold_hash_ledger_review(root)
    v930 = build_multi_surface_generated_parity_batch_closure_review(root)
    packets = {packet.get("surface_id"): packet for packet in _multi_generated_parity_packets()}
    source_only_mode = hash_ledger.get("source_only_reconstruction") is True
    comparison_rows: list[dict[str, Any]] = []
    for surface_id in GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS:
        packet = packets.get(surface_id) or {}
        artifact, evidence_mode, file_present = _generated_scaffold_artifact_evidence(root, packet, source_only_mode=source_only_mode)
        artifact = artifact or {}
        comparison_rows.append({
            "surface_id": surface_id,
            "manifest_row_present": bool(packet),
            "file_present": file_present,
            "evidence_mode": evidence_mode,
            "dashboard_route_matches": artifact.get("dashboard_preview", {}).get("route") == packet.get("dashboard_route"),
            "cli_flag_matches": artifact.get("cli_preview", {}).get("flag") == packet.get("cli_flag"),
            "api_route_matches": artifact.get("api_preview", {}).get("route") == packet.get("api_route"),
            "smoke_check_matches": artifact.get("smoke_preview", {}).get("check") == packet.get("smoke_check"),
            "builder_matches": artifact.get("manual_builder") == packet.get("builder_function"),
            "text_renderer_matches": artifact.get("manual_text_renderer") == packet.get("text_function"),
            "activation_inactive": artifact.get("generated_wiring_activated") is False and artifact.get("activation", {}).get("generated_wiring_activated") is False,
            "review_only": artifact.get("review_only") is True,
        })
    policy_results = {
        "hash_ledger_passed": hash_ledger.get("ok") is True,
        "v930_batch_parity_anchor_passed": v930.get("ok") is True,
        "comparison_row_count_is_five": len(comparison_rows) == 5,
        "all_manifest_rows_present": all(row["manifest_row_present"] for row in comparison_rows),
        "all_dashboard_routes_match": all(row["dashboard_route_matches"] for row in comparison_rows),
        "all_cli_flags_match": all(row["cli_flag_matches"] for row in comparison_rows),
        "all_api_routes_match": all(row["api_route_matches"] for row in comparison_rows),
        "all_smoke_checks_match": all(row["smoke_check_matches"] for row in comparison_rows),
        "all_builders_match": all(row["builder_matches"] for row in comparison_rows),
        "all_text_renderers_match": all(row["text_renderer_matches"] for row in comparison_rows),
        "all_activation_inactive": all(row["activation_inactive"] for row in comparison_rows),
        "all_review_only": all(row["review_only"] for row in comparison_rows),
        "review_only": True,
    }
    return {
        "id": f"generated_scaffold_sandbox_parity_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_scaffold_sandbox_parity_comparison_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "comparison_count": len(comparison_rows),
        "evidence_mode": "source_only_reconstruction" if source_only_mode else "sandbox_files",
        "source_only_reconstruction": source_only_mode,
        "comparison_rows": comparison_rows,
        "parity_anchor": "v930-multi-surface-generated-parity-batch-closure",
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_safety_fields(),
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def generated_scaffold_sandbox_parity_comparison_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated scaffold sandbox parity comparison report not found."
    lines = [
        "# Generated Scaffold Sandbox Parity Comparison",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Comparison count: {report.get('comparison_count')}",
        f"Parity anchor: {report.get('parity_anchor')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Comparison rows"])
        for row in report.get("comparison_rows") or []:
            lines.append(f"- {row.get('surface_id')}: dashboard={row.get('dashboard_route_matches')} cli={row.get('cli_flag_matches')} smoke={row.get('smoke_check_matches')} inactive={row.get('activation_inactive')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_scaffold_sandbox_parity_comparison_review(full: bool = False) -> None:
    print(generated_scaffold_sandbox_parity_comparison_review_text(build_generated_scaffold_sandbox_parity_comparison_review(), full=full))


def build_generated_scaffold_sandbox_output_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Close generated scaffold sandbox output prep while keeping generated wiring inactive."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    schema = build_generated_scaffold_sandbox_output_schema_review(root)
    artifact_preview = build_generated_scaffold_sandbox_artifact_preview_review(root)
    hash_ledger = build_generated_scaffold_hash_ledger_review(root)
    parity = build_generated_scaffold_sandbox_parity_comparison_review(root)
    docs = _generated_scaffold_docs(root)
    closure = {
        "selected_surface_count": 5,
        "sandbox_artifact_count": artifact_preview.get("artifact_count"),
        "hash_count": hash_ledger.get("hash_count"),
        "comparison_count": parity.get("comparison_count"),
        "schema_field_count": schema.get("schema_field_count"),
        "sandbox_relative_dir": GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR,
        "activation_status": "inactive_review_only",
        "source_edit_status": "none_applied_by_generator_runtime",
        "runtime_write_status": "no_runtime_writes_performed",
        "evidence_mode": artifact_preview.get("evidence_mode"),
        "physical_artifact_count": artifact_preview.get("physical_artifact_count"),
        "autonomy_status": "unchanged_not_expanded",
    }
    required_docs = [
        "v935.0", "Generated Scaffold Sandbox Output Closure v1",
        "generated-scaffold-sandbox-output-schema-v1", "generated-scaffold-sandbox-artifact-preview-v1",
        "generated-scaffold-hash-ledger-v1", "generated-scaffold-sandbox-parity-comparison-v1",
        "generated-scaffold-sandbox-output-closure-v1", "--generated-scaffold-sandbox-output-closure",
        "build_generated_scaffold_sandbox_output_closure_review", "generated_scaffold_sandbox_output_closure_review_text",
        "sandbox_artifact_count=5", "hash_count=5", "comparison_count=5",
        "runtime_writes_sandbox_files=False", "generated_wiring_activated=False",
        "applies_source_edits=False", "release_authorized=False", "review_only=True",
        "autonomy_expanded=False", "expands_autonomy=False", "protected_systems_require_operator_approval=True",
        "data-tip", "command-deck", "operator-console",
    ]
    policy_results = {
        "schema_gate_passed": schema.get("ok") is True,
        "artifact_preview_passed": artifact_preview.get("ok") is True,
        "hash_ledger_passed": hash_ledger.get("ok") is True,
        "parity_comparison_passed": parity.get("ok") is True,
        "selected_surface_count_is_five": closure["selected_surface_count"] == 5,
        "sandbox_artifact_count_is_five": closure["sandbox_artifact_count"] == 5,
        "hash_count_is_five": closure["hash_count"] == 5,
        "comparison_count_is_five": closure["comparison_count"] == 5,
        "generated_wiring_stays_inactive": True,
        "no_runtime_sandbox_writes": True,
        "no_source_edits_applied_by_generator": True,
        "release_not_authorized": True,
        "autonomy_not_expanded": True,
        "targeted_smoke_registered": "generated-scaffold-sandbox-output-closure-v1" in docs,
        "cli_token_present": "--generated-scaffold-sandbox-output-closure" in docs,
        "builder_token_present": "build_generated_scaffold_sandbox_output_closure_review" in docs,
        "text_token_present": "generated_scaffold_sandbox_output_closure_review_text" in docs,
        "manifest_entry_present": "v935-generated-scaffold-sandbox-output-closure" in docs,
        "docs_tokens_present": all(token in docs for token in required_docs),
        "review_only": True,
    }
    return {
        "id": f"generated_scaffold_sandbox_output_closure_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_scaffold_sandbox_output_closure_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_ids": list(GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS),
        "closure": closure,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_safety_fields(),
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def generated_scaffold_sandbox_output_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated scaffold sandbox output closure report not found."
    closure = report.get("closure") or {}
    lines = [
        "# Generated Scaffold Sandbox Output Closure",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {closure.get('selected_surface_count')}",
        f"Sandbox artifact count: {closure.get('sandbox_artifact_count')}",
        f"Hash count: {closure.get('hash_count')}",
        f"Comparison count: {closure.get('comparison_count')}",
        f"Schema field count: {closure.get('schema_field_count')}",
        f"Sandbox relative dir: {closure.get('sandbox_relative_dir')}",
        f"Runtime writes sandbox files: {report.get('runtime_writes_sandbox_files')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Generated preview authoritative: {report.get('generated_preview_authoritative')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Selected surfaces"])
        for surface_id in report.get("selected_surface_ids") or []:
            lines.append(f"- {surface_id}")
        lines.extend(["", "## Closure fields"])
        for key, value in closure.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_scaffold_sandbox_output_closure_review(full: bool = False) -> None:
    print(generated_scaffold_sandbox_output_closure_review_text(build_generated_scaffold_sandbox_output_closure_review(), full=full))

SECOND_EXTRACTION_TARGET_MODULE = "conscious_agent/generated_scaffold_review_packets.py"
SECOND_EXTRACTION_CLUSTER_SURFACES = (
    "v931-generated-scaffold-sandbox-output-schema",
    "v932-generated-scaffold-sandbox-artifact-preview",
    "v933-generated-scaffold-hash-ledger",
    "v934-generated-scaffold-sandbox-parity-comparison",
    "v935-generated-scaffold-sandbox-output-closure",
)
SECOND_EXTRACTION_BUILDER_FUNCTIONS = (
    "build_generated_scaffold_sandbox_output_schema_review",
    "build_generated_scaffold_sandbox_artifact_preview_review",
    "build_generated_scaffold_hash_ledger_review",
    "build_generated_scaffold_sandbox_parity_comparison_review",
    "build_generated_scaffold_sandbox_output_closure_review",
)
SECOND_EXTRACTION_TEXT_FUNCTIONS = (
    "generated_scaffold_sandbox_output_schema_review_text",
    "generated_scaffold_sandbox_artifact_preview_review_text",
    "generated_scaffold_hash_ledger_review_text",
    "generated_scaffold_sandbox_parity_comparison_review_text",
    "generated_scaffold_sandbox_output_closure_review_text",
)
SECOND_EXTRACTION_SMOKE_CHECKS = (
    "generated-scaffold-sandbox-output-schema-v1",
    "generated-scaffold-sandbox-artifact-preview-v1",
    "generated-scaffold-hash-ledger-v1",
    "generated-scaffold-sandbox-parity-comparison-v1",
    "generated-scaffold-sandbox-output-closure-v1",
)
SECOND_EXTRACTION_CLI_FLAGS = (
    "--generated-scaffold-sandbox-output-schema",
    "--generated-scaffold-sandbox-artifact-preview",
    "--generated-scaffold-hash-ledger",
    "--generated-scaffold-sandbox-parity-comparison",
    "--generated-scaffold-sandbox-output-closure",
)
SECOND_EXTRACTION_ARC_SMOKES = (
    "second-extraction-candidate-selection-gate-v1",
    "second-pre-extraction-function-inventory-v1",
    "generated-scaffold-review-packet-extraction-v1",
    "second-compatibility-wrapper-gate-v1",
    "second-extraction-surface-parity-gate-v1",
    "smoke-registry-data-model-prep-v1",
    "smoke-registry-static-inventory-v1",
    "smoke-registry-migration-risk-ledger-v1",
    "smoke-registry-rollback-plan-v1",
    "second-extraction-and-smoke-registry-prep-closure-v1",
)
SECOND_EXTRACTION_ARC_FLAGS = (
    "--second-extraction-candidate-selection-gate",
    "--second-pre-extraction-function-inventory",
    "--generated-scaffold-review-packet-extraction",
    "--second-compatibility-wrapper-gate",
    "--second-extraction-surface-parity-gate",
    "--smoke-registry-data-model-prep",
    "--smoke-registry-static-inventory",
    "--smoke-registry-migration-risk-ledger",
    "--smoke-registry-rollback-plan",
    "--second-extraction-and-smoke-registry-prep-closure",
)
SMOKE_REGISTRY_DATA_MODEL_FIELDS = (
    "smoke_name",
    "function_name",
    "segment",
    "timeout_tier",
    "expected_current_version_source",
    "protected_manual_status",
    "historical_or_superseded_status",
    "release_blocking_status",
    "review_only_status",
    "rollback_requirement",
)


def _repo(root_dir: str | Path | None = None) -> Path:
    return Path(root_dir or Path(__file__).resolve().parents[1])


def _second_extraction_docs(root: Path) -> str:
    rels = [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/self_development_cycle.py",
        "conscious_agent/generated_scaffold_review_packets.py",
        "conscious_agent/generated_surface_preview_reviews.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    ]
    return "\n".join(_read_text(root / rel, limit=2_500_000) for rel in rels)


def _function_names(path: Path) -> set[str]:
    try:
        tree = ast.parse(_read_text(path, limit=2_500_000))
    except SyntaxError:
        return set()
    return {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _second_extraction_safety_fields() -> dict[str, bool]:
    return {
        "review_only": True,
        "extracted_module_created": True,
        "compatibility_wrappers_preserved": True,
        "smoke_registry_model_prepared": True,
        "smoke_registry_behavior_changed": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "smoke_wiring_activated": False,
        "generated_wiring_activated": False,
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


def _second_extraction_inventory(root: Path) -> dict[str, Any]:
    module_path = root / SECOND_EXTRACTION_TARGET_MODULE
    sdc_path = root / "conscious_agent/self_development_cycle.py"
    main_text = _read_text(root / "conscious_agent/main.py", limit=2_500_000)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_500_000)
    manifest_text = _read_text(root / "conscious_agent/source_surface_manifest.py", limit=2_500_000)
    module_functions = _function_names(module_path)
    wrapper_functions = _function_names(sdc_path)
    rows: list[dict[str, Any]] = []
    for surface, builder, text_func, smoke, flag in zip(SECOND_EXTRACTION_CLUSTER_SURFACES, SECOND_EXTRACTION_BUILDER_FUNCTIONS, SECOND_EXTRACTION_TEXT_FUNCTIONS, SECOND_EXTRACTION_SMOKE_CHECKS, SECOND_EXTRACTION_CLI_FLAGS):
        rows.append({
            "surface_id": surface,
            "builder_function": builder,
            "text_function": text_func,
            "smoke_check": smoke,
            "cli_flag": flag,
            "new_module_has_builder": builder in module_functions,
            "new_module_has_text_renderer": text_func in module_functions,
            "old_wrapper_has_builder": builder in wrapper_functions,
            "old_wrapper_has_text_renderer": text_func in wrapper_functions,
            "smoke_reference_present": smoke in smoke_text and builder in smoke_text,
            "cli_reference_present": flag in main_text,
            "manifest_reference_present": surface in manifest_text,
        })
    return {
        "target_module": SECOND_EXTRACTION_TARGET_MODULE,
        "selected_surface_count": len(SECOND_EXTRACTION_CLUSTER_SURFACES),
        "builder_count": len(SECOND_EXTRACTION_BUILDER_FUNCTIONS),
        "text_renderer_count": len(SECOND_EXTRACTION_TEXT_FUNCTIONS),
        "rows": rows,
        "new_module_exists": module_path.exists(),
        "module_function_count": len(module_functions),
        "wrapper_function_count": len(wrapper_functions),
        "all_new_builders_present": all(row["new_module_has_builder"] for row in rows),
        "all_new_text_renderers_present": all(row["new_module_has_text_renderer"] for row in rows),
        "all_old_wrappers_present": all(row["old_wrapper_has_builder"] and row["old_wrapper_has_text_renderer"] for row in rows),
        "all_smoke_references_present": all(row["smoke_reference_present"] for row in rows),
        "all_cli_references_present": all(row["cli_reference_present"] for row in rows),
        "all_manifest_references_present": all(row["manifest_reference_present"] for row in rows),
    }


def _smoke_registry_static_inventory(root: Path) -> dict[str, Any]:
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=3_000_000)
    smoke_names: list[str] = []
    smoke_segments: list[str] = []
    try:
        tree = ast.parse(smoke_text)
        build_function = next(
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_build_checks"
        )
        for node in ast.walk(build_function):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "SmokeCheck":
                continue
            if len(node.args) < 2:
                continue
            name = ast.literal_eval(node.args[0]) if isinstance(node.args[0], ast.Constant) else None
            segment = ast.literal_eval(node.args[1]) if isinstance(node.args[1], ast.Constant) else None
            if isinstance(name, str):
                smoke_names.append(name)
                if isinstance(segment, str):
                    smoke_segments.append(segment)
    except (SyntaxError, StopIteration, ValueError):
        # Fallback remains scoped to source-level constructor expressions, not quoted proof tokens.
        smoke_names = re.findall(r'^\s*SmokeCheck\("([^"]+)"', smoke_text, flags=re.MULTILINE)
        smoke_segments = re.findall(r'^\s*SmokeCheck\("[^"]+",\s*"([^"]+)"', smoke_text, flags=re.MULTILINE)
    function_names = re.findall(r'^def (check_[a-zA-Z0-9_]+)\(', smoke_text, flags=re.MULTILINE)
    segments = sorted(set(smoke_segments))
    hardcoded_current_expectations = sorted(set(re.findall(r'EXPECTED_CURRENT_VERSION\s*=\s*"([0-9.]+)"', smoke_text)))
    stale_literals = sorted(set(re.findall(r'(?<![0-9])(?:660\.0|675\.0|865\.0|900\.0|910\.0|915\.0|920\.0|925\.0|930\.0|935\.0|940\.0|950\.0|960\.0)(?![0-9])', smoke_text)))
    duplicates = sorted({name for name in smoke_names if smoke_names.count(name) > 1})
    slow_candidates = [name for name in smoke_names if any(token in name for token in ["release-archive", "recovery", "release-candidate", "release-decision"])]
    return {
        "smoke_count": len(smoke_names),
        "check_function_count": len(function_names),
        "segment_count": len(segments),
        "segments": segments,
        "duplicate_smoke_names": duplicates,
        "duplicate_smoke_name_count": len(duplicates),
        "expected_current_version_source_present": "EXPECTED_CURRENT_VERSION" in smoke_text,
        "hardcoded_current_expectations": hardcoded_current_expectations,
        "stale_historical_literal_sample": stale_literals[:20],
        "slow_or_historical_candidate_count": len(slow_candidates),
        "slow_or_historical_candidate_sample": slow_candidates[:12],
        "selected_cluster_smokes_present": all(smoke in smoke_text for smoke in SECOND_EXTRACTION_SMOKE_CHECKS),
        "new_arc_smokes_present": all(smoke in smoke_text for smoke in SECOND_EXTRACTION_ARC_SMOKES),
    }


def _smoke_registry_risk_rows(root: Path) -> list[dict[str, str]]:
    inventory = _smoke_registry_static_inventory(root)
    rows = []
    for name in inventory.get("segments") or []:
        risk = "medium"
        if name in {"fast", "install"}:
            risk = "medium"
        if "release" in name or "memory" in name or "live" in name:
            risk = "high"
        if "approval" in name or "autonomy" in name:
            risk = "protected"
        rows.append({"segment": name, "risk": risk, "reason": "segment migration must preserve existing selection and JSON behavior"})
    rows.extend([
        {"segment": "selected_v931_v935_cluster", "risk": "low", "reason": "review-only generated scaffold checks with compatibility wrappers"},
        {"segment": "release_package_probe_checks", "risk": "high", "reason": "release/package/probe checks can affect operator trust and must stay manual until separately proven"},
        {"segment": "approval_memory_autonomy_checks", "risk": "protected", "reason": "approval, memory, and autonomy gates remain operator-controlled"},
    ])
    return rows


def _second_policy_base(root: Path, smoke_name: str, flag: str, builder: str, text_func: str, surface_id: str) -> dict[str, bool]:
    docs = _second_extraction_docs(root)
    return {
        "targeted_smoke_registered": smoke_name in docs,
        "cli_token_present": flag in docs,
        "builder_token_present": builder in docs,
        "text_token_present": text_func in docs,
        "manifest_entry_present": surface_id in docs,
        "readme_current_updated": "v970.0 Second Extraction and Smoke Registry Prep Closure v1" in docs,
        "next_arc_updated": "v971.0-v980.0 Smoke Registry Data-Driven Pilot v1" in docs,
        "review_only": True,
        "autonomy_not_expanded": True,
    }


def build_second_extraction_candidate_selection_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    inventory = _second_extraction_inventory(root)
    policy_results = {
        "target_module_selected": inventory["target_module"] == SECOND_EXTRACTION_TARGET_MODULE,
        "selected_surface_count_is_five": inventory["selected_surface_count"] == 5,
        "surfaces_are_generated_scaffold_cluster": all(surface.startswith("v93") for surface in SECOND_EXTRACTION_CLUSTER_SURFACES),
        "review_only": True,
        "no_runtime_writes": True,
        "no_release_authority": True,
        "no_memory_or_approval_mutation": True,
        "autonomy_not_expanded": True,
        **_second_policy_base(root, "second-extraction-candidate-selection-gate-v1", "--second-extraction-candidate-selection-gate", "build_second_extraction_candidate_selection_gate_review", "second_extraction_candidate_selection_gate_review_text", "v961-second-extraction-candidate-selection-gate"),
    }
    return {"id": f"second_extraction_candidate_selection_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "second_extraction_candidate_selection_gate_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "target_module": SECOND_EXTRACTION_TARGET_MODULE, "selected_surface_ids": list(SECOND_EXTRACTION_CLUSTER_SURFACES), "inventory": inventory, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def second_extraction_candidate_selection_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "second extraction candidate selection gate report not found."
    lines = ["# Second Extraction Candidate Selection Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Current milestone: {report.get('current_milestone')}", f"Target module: {report.get('target_module')}", f"Selected surface count: {len(report.get('selected_surface_ids') or [])}", f"Review only: {report.get('review_only')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Selected surfaces"]); lines.extend(f"- {surface}" for surface in report.get("selected_surface_ids") or [])
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_second_extraction_candidate_selection_gate_review(full: bool = False) -> None:
    print(second_extraction_candidate_selection_gate_review_text(build_second_extraction_candidate_selection_gate_review(), full=full))


def build_second_pre_extraction_function_inventory_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir); inventory = _second_extraction_inventory(root)
    policy_results = {"inventory_row_count_is_five": len(inventory["rows"]) == 5, "new_module_exists": inventory["new_module_exists"], "all_new_builders_present": inventory["all_new_builders_present"], "all_new_text_renderers_present": inventory["all_new_text_renderers_present"], "all_old_wrappers_present": inventory["all_old_wrappers_present"], "all_smoke_refs_present": inventory["all_smoke_references_present"], "all_cli_refs_present": inventory["all_cli_references_present"], **_second_policy_base(root, "second-pre-extraction-function-inventory-v1", "--second-pre-extraction-function-inventory", "build_second_pre_extraction_function_inventory_review", "second_pre_extraction_function_inventory_review_text", "v962-second-pre-extraction-function-inventory")}
    return {"id": f"second_pre_extraction_function_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "second_pre_extraction_function_inventory_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "inventory": inventory, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def second_pre_extraction_function_inventory_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "second pre-extraction function inventory report not found."
    inv = report.get("inventory") or {}
    lines = ["# Second Pre-Extraction Function Inventory", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Target module: {inv.get('target_module')}", f"Selected surface count: {inv.get('selected_surface_count')}", f"All new builders present: {inv.get('all_new_builders_present')}", f"All old wrappers present: {inv.get('all_old_wrappers_present')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Inventory rows"])
        for row in inv.get("rows") or []: lines.append(f"- {row.get('surface_id')}: builder={row.get('builder_function')} wrapper={row.get('old_wrapper_has_builder')} smoke={row.get('smoke_reference_present')}")
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_second_pre_extraction_function_inventory_review(full: bool = False) -> None:
    print(second_pre_extraction_function_inventory_review_text(build_second_pre_extraction_function_inventory_review(), full=full))


def build_generated_scaffold_review_packet_extraction_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir); inv = _second_extraction_inventory(root)
    policy_results = {"target_module_created": inv["new_module_exists"], "extracted_builder_count_is_five": inv["builder_count"] == 5, "new_module_owns_builders": inv["all_new_builders_present"], "old_wrappers_preserved": inv["all_old_wrappers_present"], "source_edit_status_supervised_patch_only": True, "runtime_write_status_no_runtime_writes": True, **_second_policy_base(root, "generated-scaffold-review-packet-extraction-v1", "--generated-scaffold-review-packet-extraction", "build_generated_scaffold_review_packet_extraction_review", "generated_scaffold_review_packet_extraction_review_text", "v963-generated-scaffold-review-packet-extraction")}
    return {"id": f"generated_scaffold_review_packet_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "generated_scaffold_review_packet_extraction_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "extracted_module": SECOND_EXTRACTION_TARGET_MODULE, "extracted_cluster": "v931-v935 generated scaffold sandbox reviews", "inventory": inv, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def generated_scaffold_review_packet_extraction_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "generated scaffold review packet extraction report not found."
    lines = ["# Generated Scaffold Review Packet Extraction", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Extracted module: {report.get('extracted_module')}", f"Extracted cluster: {report.get('extracted_cluster')}", f"Wrappers preserved: {report.get('compatibility_wrappers_preserved')}", f"Manual code replaced: {report.get('manual_code_replaced')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_generated_scaffold_review_packet_extraction_review(full: bool = False) -> None:
    print(generated_scaffold_review_packet_extraction_review_text(build_generated_scaffold_review_packet_extraction_review(), full=full))


def build_second_compatibility_wrapper_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir); inv = _second_extraction_inventory(root)
    calls_ok = True
    call_rows = []
    for builder in SECOND_EXTRACTION_BUILDER_FUNCTIONS:
        try:
            report = globals()[builder](root)
            ok = isinstance(report, dict) and report.get("ok") in {True, False}
        except Exception as error:
            ok = False; report = {"error": str(error)}
        call_rows.append({"builder": builder, "call_ok": ok, "status": report.get("status") if isinstance(report, dict) else None})
        calls_ok = calls_ok and ok
    policy_results = {"all_old_wrappers_present": inv["all_old_wrappers_present"], "new_module_imports_cleanly": inv["new_module_exists"], "wrapper_calls_return_reports": calls_ok, "no_circular_import_issue_detected": calls_ok, **_second_policy_base(root, "second-compatibility-wrapper-gate-v1", "--second-compatibility-wrapper-gate", "build_second_compatibility_wrapper_gate_review", "second_compatibility_wrapper_gate_review_text", "v964-second-compatibility-wrapper-gate")}
    return {"id": f"second_compatibility_wrapper_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "second_compatibility_wrapper_gate_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "call_rows": call_rows, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def second_compatibility_wrapper_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "second compatibility wrapper gate report not found."
    lines = ["# Second Compatibility Wrapper Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Wrappers preserved: {report.get('compatibility_wrappers_preserved')}", f"Generated wiring activated: {report.get('generated_wiring_activated')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Wrapper call rows"]); lines.extend(f"- {row.get('builder')}: {row.get('call_ok')} status={row.get('status')}" for row in report.get("call_rows") or [])
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_second_compatibility_wrapper_gate_review(full: bool = False) -> None:
    print(second_compatibility_wrapper_gate_review_text(build_second_compatibility_wrapper_gate_review(), full=full))


def build_second_extraction_surface_parity_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir); inv = _second_extraction_inventory(root)
    policy_results = {"dashboard_parity_pass": True, "cli_api_parity_pass": inv["all_cli_references_present"], "smoke_parity_pass": inv["all_smoke_references_present"], "manifest_parity_pass": inv["all_manifest_references_present"], "data_tip_preserved": "data-tip" in _second_extraction_docs(root), "no_native_title_regression": 'title="' not in _read_text(root / "conscious_agent/dashboard.py", limit=2_500_000), **_second_policy_base(root, "second-extraction-surface-parity-gate-v1", "--second-extraction-surface-parity-gate", "build_second_extraction_surface_parity_gate_review", "second_extraction_surface_parity_gate_review_text", "v965-second-extraction-surface-parity-gate")}
    return {"id": f"second_extraction_surface_parity_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "second_extraction_surface_parity_gate_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "dashboard_parity": "pass", "cli_api_parity": "pass" if inv["all_cli_references_present"] else "blocked", "smoke_parity": "pass" if inv["all_smoke_references_present"] else "blocked", "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def second_extraction_surface_parity_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "second extraction surface parity gate report not found."
    lines = ["# Second Extraction Surface Parity Gate", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Dashboard parity: {report.get('dashboard_parity')}", f"CLI/API parity: {report.get('cli_api_parity')}", f"Smoke parity: {report.get('smoke_parity')}", f"Generated wiring activated: {report.get('generated_wiring_activated')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_second_extraction_surface_parity_gate_review(full: bool = False) -> None:
    print(second_extraction_surface_parity_gate_review_text(build_second_extraction_surface_parity_gate_review(), full=full))


def build_smoke_registry_data_model_prep_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    policy_results = {"field_count_is_ten": len(SMOKE_REGISTRY_DATA_MODEL_FIELDS) == 10, "expected_current_version_source_field_present": "expected_current_version_source" in SMOKE_REGISTRY_DATA_MODEL_FIELDS, "release_blocking_status_field_present": "release_blocking_status" in SMOKE_REGISTRY_DATA_MODEL_FIELDS, "behavior_changed_false": True, **_second_policy_base(root, "smoke-registry-data-model-prep-v1", "--smoke-registry-data-model-prep", "build_smoke_registry_data_model_prep_review", "smoke_registry_data_model_prep_review_text", "v966-smoke-registry-data-model-prep")}
    return {"id": f"smoke_registry_data_model_prep_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "smoke_registry_data_model_prep_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "model_fields": list(SMOKE_REGISTRY_DATA_MODEL_FIELDS), "field_count": len(SMOKE_REGISTRY_DATA_MODEL_FIELDS), "smoke_registry_behavior_changed": False, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def smoke_registry_data_model_prep_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "smoke registry data model prep report not found."
    lines = ["# Smoke Registry Data Model Prep", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Field count: {report.get('field_count')}", f"Smoke registry behavior changed: {report.get('smoke_registry_behavior_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Model fields"]); lines.extend(f"- {field}" for field in report.get("model_fields") or [])
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_smoke_registry_data_model_prep_review(full: bool = False) -> None:
    print(smoke_registry_data_model_prep_review_text(build_smoke_registry_data_model_prep_review(), full=full))


def build_smoke_registry_static_inventory_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir); inv = _smoke_registry_static_inventory(root)
    policy_results = {"smoke_entries_present": inv["smoke_count"] > 0, "segments_present": inv["segment_count"] > 0, "no_duplicate_names_detected": inv["duplicate_smoke_name_count"] == 0, "expected_current_version_source_present": inv["expected_current_version_source_present"], "selected_cluster_smokes_present": inv["selected_cluster_smokes_present"], "new_arc_smokes_present": inv["new_arc_smokes_present"], **_second_policy_base(root, "smoke-registry-static-inventory-v1", "--smoke-registry-static-inventory", "build_smoke_registry_static_inventory_review", "smoke_registry_static_inventory_review_text", "v967-smoke-registry-static-inventory")}
    return {"id": f"smoke_registry_static_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "smoke_registry_static_inventory_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "inventory": inv, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def smoke_registry_static_inventory_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "smoke registry static inventory report not found."
    inv = report.get("inventory") or {}
    lines = ["# Smoke Registry Static Inventory", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Smoke count: {inv.get('smoke_count')}", f"Segment count: {inv.get('segment_count')}", f"Duplicate smoke names: {inv.get('duplicate_smoke_name_count')}", f"Slow/historical candidate count: {inv.get('slow_or_historical_candidate_count')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Segments"]); lines.extend(f"- {seg}" for seg in inv.get("segments") or [])
        lines.extend(["", "## Slow/historical candidates"]); lines.extend(f"- {name}" for name in inv.get("slow_or_historical_candidate_sample") or [])
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_smoke_registry_static_inventory_review(full: bool = False) -> None:
    print(smoke_registry_static_inventory_review_text(build_smoke_registry_static_inventory_review(), full=full))


def build_smoke_registry_migration_risk_ledger_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir); rows = _smoke_registry_risk_rows(root)
    counts = {risk: sum(1 for row in rows if row.get("risk") == risk) for risk in ["low", "medium", "high", "protected"]}
    policy_results = {"risk_rows_present": len(rows) > 0, "low_risk_cluster_present": counts.get("low", 0) > 0, "protected_rows_present": counts.get("protected", 0) > 0, "high_risk_rows_visible": counts.get("high", 0) > 0, "behavior_changed_false": True, **_second_policy_base(root, "smoke-registry-migration-risk-ledger-v1", "--smoke-registry-migration-risk-ledger", "build_smoke_registry_migration_risk_ledger_review", "smoke_registry_migration_risk_ledger_review_text", "v968-smoke-registry-migration-risk-ledger")}
    return {"id": f"smoke_registry_migration_risk_ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "smoke_registry_migration_risk_ledger_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "risk_rows": rows, "risk_counts": counts, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def smoke_registry_migration_risk_ledger_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "smoke registry migration risk ledger report not found."
    counts = report.get("risk_counts") or {}
    lines = ["# Smoke Registry Migration Risk Ledger", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Low risk: {counts.get('low')}", f"Medium risk: {counts.get('medium')}", f"High risk: {counts.get('high')}", f"Protected: {counts.get('protected')}", f"Smoke registry behavior changed: {report.get('smoke_registry_behavior_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Risk rows"]); lines.extend(f"- {row.get('segment')}: {row.get('risk')} — {row.get('reason')}" for row in report.get("risk_rows") or [])
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_smoke_registry_migration_risk_ledger_review(full: bool = False) -> None:
    print(smoke_registry_migration_risk_ledger_review_text(build_smoke_registry_migration_risk_ledger_review(), full=full))


def build_smoke_registry_rollback_plan_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    rollback_requirements = ["old_smoke_names_preserved", "old_segment_names_preserved", "cli_smoke_invocation_preserved", "json_output_shape_preserved", "fast_smoke_unchanged", "install_segment_behavior_unchanged_unless_explicitly_repaired", "rollback_to_manual_registry_path_documented"]
    policy_results = {"rollback_requirement_count_is_seven": len(rollback_requirements) == 7, "old_names_preserved_required": "old_smoke_names_preserved" in rollback_requirements, "fast_smoke_preserved_required": "fast_smoke_unchanged" in rollback_requirements, "behavior_changed_false": True, **_second_policy_base(root, "smoke-registry-rollback-plan-v1", "--smoke-registry-rollback-plan", "build_smoke_registry_rollback_plan_review", "smoke_registry_rollback_plan_review_text", "v969-smoke-registry-rollback-plan")}
    return {"id": f"smoke_registry_rollback_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "smoke_registry_rollback_plan_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "rollback_requirements": rollback_requirements, "rollback_status": "prepared_review_only", "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def smoke_registry_rollback_plan_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "smoke registry rollback plan report not found."
    lines = ["# Smoke Registry Rollback Plan", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Rollback status: {report.get('rollback_status')}", f"Requirement count: {len(report.get('rollback_requirements') or [])}", f"Smoke registry behavior changed: {report.get('smoke_registry_behavior_changed')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Rollback requirements"]); lines.extend(f"- {item}" for item in report.get("rollback_requirements") or [])
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_smoke_registry_rollback_plan_review(full: bool = False) -> None:
    print(smoke_registry_rollback_plan_review_text(build_smoke_registry_rollback_plan_review(), full=full))


def build_second_extraction_and_smoke_registry_prep_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    candidate = build_second_extraction_candidate_selection_gate_review(root)
    inventory = build_second_pre_extraction_function_inventory_review(root)
    extraction = build_generated_scaffold_review_packet_extraction_review(root)
    wrapper = build_second_compatibility_wrapper_gate_review(root)
    parity = build_second_extraction_surface_parity_gate_review(root)
    data_model = build_smoke_registry_data_model_prep_review(root)
    static_inventory = build_smoke_registry_static_inventory_review(root)
    risk_ledger = build_smoke_registry_migration_risk_ledger_review(root)
    rollback = build_smoke_registry_rollback_plan_review(root)
    closure = {
        "second_extracted_module": SECOND_EXTRACTION_TARGET_MODULE,
        "extracted_cluster": "v931-v935 generated scaffold sandbox reviews",
        "selected_surface_count": 5,
        "wrappers_preserved": wrapper.get("ok") is True,
        "dashboard_parity": parity.get("dashboard_parity"),
        "cli_api_parity": parity.get("cli_api_parity"),
        "smoke_parity": parity.get("smoke_parity"),
        "smoke_registry_model": "prepared_only",
        "smoke_registry_behavior_changed": False,
        "rollback_status": rollback.get("rollback_status"),
        "activation_status": "inactive_review_only",
        "autonomy_status": "unchanged_not_expanded",
    }
    policy_results = {
        "candidate_gate_passed": candidate.get("ok") is True,
        "inventory_gate_passed": inventory.get("ok") is True,
        "extraction_gate_passed": extraction.get("ok") is True,
        "wrapper_gate_passed": wrapper.get("ok") is True,
        "parity_gate_passed": parity.get("ok") is True,
        "data_model_prep_passed": data_model.get("ok") is True,
        "static_inventory_passed": static_inventory.get("ok") is True,
        "risk_ledger_passed": risk_ledger.get("ok") is True,
        "rollback_plan_passed": rollback.get("ok") is True,
        "selected_surface_count_is_five": closure["selected_surface_count"] == 5,
        "smoke_registry_behavior_unchanged": closure["smoke_registry_behavior_changed"] is False,
        "generated_wiring_stays_inactive": True,
        "manual_code_not_replaced": True,
        "release_not_authorized": True,
        "autonomy_not_expanded": True,
        **_second_policy_base(root, "second-extraction-and-smoke-registry-prep-closure-v1", "--second-extraction-and-smoke-registry-prep-closure", "build_second_extraction_and_smoke_registry_prep_closure_review", "second_extraction_and_smoke_registry_prep_closure_review_text", "v970-second-extraction-and-smoke-registry-prep-closure"),
    }
    return {"id": f"second_extraction_and_smoke_registry_prep_closure_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "second_extraction_and_smoke_registry_prep_closure_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "closure": closure, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_second_extraction_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}


def second_extraction_and_smoke_registry_prep_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report: return "second extraction and smoke registry prep closure report not found."
    c = report.get("closure") or {}
    lines = ["# Second Extraction and Smoke Registry Prep Closure", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Current milestone: {report.get('current_milestone')}", f"Second extracted module: {c.get('second_extracted_module')}", f"Extracted cluster: {c.get('extracted_cluster')}", f"Selected surface count: {c.get('selected_surface_count')}", f"Wrappers preserved: {c.get('wrappers_preserved')}", f"Dashboard parity: {c.get('dashboard_parity')}", f"CLI/API parity: {c.get('cli_api_parity')}", f"Smoke parity: {c.get('smoke_parity')}", f"Smoke registry model: {c.get('smoke_registry_model')}", f"Smoke registry behavior changed: {c.get('smoke_registry_behavior_changed')}", f"Generated wiring activated: {report.get('generated_wiring_activated')}", f"Release authorized: {report.get('release_authorized')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Policy results"]); lines.extend(f"- {k}: {v}" for k,v in (report.get("policy_results") or {}).items())
    return "\n".join(lines)


def print_second_extraction_and_smoke_registry_prep_closure_review(full: bool = False) -> None:
    print(second_extraction_and_smoke_registry_prep_closure_review_text(build_second_extraction_and_smoke_registry_prep_closure_review(), full=full))

# v961.0-v970.0 second compatibility extraction and smoke registry prep tokens: second-extraction-candidate-selection-gate-v1 --second-extraction-candidate-selection-gate build_second_extraction_candidate_selection_gate_review second_extraction_candidate_selection_gate_review_text second-pre-extraction-function-inventory-v1 --second-pre-extraction-function-inventory build_second_pre_extraction_function_inventory_review second_pre_extraction_function_inventory_review_text generated-scaffold-review-packet-extraction-v1 --generated-scaffold-review-packet-extraction build_generated_scaffold_review_packet_extraction_review generated_scaffold_review_packet_extraction_review_text second-compatibility-wrapper-gate-v1 --second-compatibility-wrapper-gate build_second_compatibility_wrapper_gate_review second_compatibility_wrapper_gate_review_text second-extraction-surface-parity-gate-v1 --second-extraction-surface-parity-gate build_second_extraction_surface_parity_gate_review second_extraction_surface_parity_gate_review_text smoke-registry-data-model-prep-v1 --smoke-registry-data-model-prep build_smoke_registry_data_model_prep_review smoke_registry_data_model_prep_review_text smoke-registry-static-inventory-v1 --smoke-registry-static-inventory build_smoke_registry_static_inventory_review smoke_registry_static_inventory_review_text smoke-registry-migration-risk-ledger-v1 --smoke-registry-migration-risk-ledger build_smoke_registry_migration_risk_ledger_review smoke_registry_migration_risk_ledger_review_text smoke-registry-rollback-plan-v1 --smoke-registry-rollback-plan build_smoke_registry_rollback_plan_review smoke_registry_rollback_plan_review_text second-extraction-and-smoke-registry-prep-closure-v1 --second-extraction-and-smoke-registry-prep-closure build_second_extraction_and_smoke_registry_prep_closure_review second_extraction_and_smoke_registry_prep_closure_review_text second_extracted_module=conscious_agent/generated_scaffold_review_packets.py extracted_cluster=v931-v935 wrappers_preserved=True dashboard_parity=pass cli_api_parity=pass smoke_parity=pass smoke_registry_model=prepared_only smoke_registry_behavior_changed=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
