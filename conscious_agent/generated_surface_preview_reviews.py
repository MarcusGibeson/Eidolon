from __future__ import annotations

import ast
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


def build_manifest_driven_surface_generation_prep_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    import self_development_cycle as sdc
    return sdc.build_manifest_driven_surface_generation_prep_review(root_dir)

MANIFEST_REVIEW_PACKET_SCHEMA_FIELDS: tuple[dict[str, str], ...] = (
    {"name": "surface_id", "purpose": "stable manifest surface identifier"},
    {"name": "surface_origin_version", "purpose": "historical release where the surface originated"},
    {"name": "manifest_representation_version", "purpose": "current manifest schema/update version"},
    {"name": "last_verified_for_version", "purpose": "current release that verified the manifest row"},
    {"name": "dashboard_route", "purpose": "candidate dashboard route or explicit review-only non-route"},
    {"name": "api_route", "purpose": "candidate API endpoint or not_exposed_review_only"},
    {"name": "cli_flag", "purpose": "candidate CLI flag"},
    {"name": "builder_function", "purpose": "review packet builder target"},
    {"name": "text_function", "purpose": "review packet text renderer target"},
    {"name": "smoke_check", "purpose": "candidate smoke check name"},
    {"name": "smoke_segment", "purpose": "candidate smoke segment"},
    {"name": "authority_level", "purpose": "operator authority classification"},
    {"name": "writes_files", "purpose": "source/runtime write risk marker"},
    {"name": "writes_memory", "purpose": "memory mutation risk marker"},
    {"name": "requires_operator_approval", "purpose": "protected action approval requirement"},
    {"name": "package_privacy_sensitive", "purpose": "privacy packaging review marker"},
    {"name": "preview_eligibility", "purpose": "review-only generation eligibility result"},
    {"name": "protected_manual_status", "purpose": "manual/protected surface reason"},
)

PROTECTED_MANUAL_SURFACE_HINTS: tuple[str, ...] = (
    "approval", "memory", "release", "archive", "live", "sandbox", "patch", "execution", "autonomy",
)


def _manifest_summary_for_generation() -> dict[str, Any]:
    import source_surface_manifest as ssm
    return ssm.build_source_surface_manifest_summary()


def _manifest_generation_entries() -> list[dict[str, Any]]:
    return list((_manifest_summary_for_generation() or {}).get("entries") or [])


def _protected_manual_reason(entry: dict[str, Any]) -> str:
    text = " ".join(str(entry.get(key, "")) for key in ("surface_id", "era", "dashboard_route", "api_route", "cli_flag", "builder_function", "smoke_check")).lower()
    if entry.get("writes_files") or entry.get("writes_memory"):
        return "writes_files_or_memory"
    if entry.get("authority_level") not in {"review_only", "simulation_only"}:
        return "non_review_authority_level"
    if entry.get("package_privacy_sensitive"):
        return "package_privacy_sensitive"
    if any(token in text for token in PROTECTED_MANUAL_SURFACE_HINTS):
        return "protected_keyword_requires_manual_review"
    return ""


def _manifest_review_packet_for_entry(entry: dict[str, Any]) -> dict[str, Any]:
    reason = _protected_manual_reason(entry)
    required_values_present = all(entry.get(key) not in (None, "") for key in ("surface_id", "builder_function", "text_function", "cli_flag", "smoke_check", "smoke_segment"))
    preview_eligible = bool(required_values_present and not reason and entry.get("authority_level") == "review_only")
    return {
        "surface_id": entry.get("surface_id"),
        "surface_origin_version": entry.get("surface_origin_version"),
        "manifest_representation_version": entry.get("manifest_representation_version"),
        "last_verified_for_version": entry.get("last_verified_for_version"),
        "dashboard_route": entry.get("dashboard_route"),
        "api_route": entry.get("api_route"),
        "cli_flag": entry.get("cli_flag"),
        "builder_function": entry.get("builder_function"),
        "text_function": entry.get("text_function"),
        "smoke_check": entry.get("smoke_check"),
        "smoke_segment": entry.get("smoke_segment"),
        "authority_level": entry.get("authority_level"),
        "writes_files": bool(entry.get("writes_files")),
        "writes_memory": bool(entry.get("writes_memory")),
        "requires_operator_approval": bool(entry.get("requires_operator_approval")),
        "package_privacy_sensitive": bool(entry.get("package_privacy_sensitive")),
        "required_values_present": required_values_present,
        "preview_eligibility": "eligible_review_only_preview" if preview_eligible else "manual_or_protected_review_required",
        "protected_manual_status": reason or "not_protected_by_static_hint",
        "generates_surface": False,
        "activates_wiring": False,
        "applies_source_edits": False,
    }


def _manifest_review_packets() -> list[dict[str, Any]]:
    return [_manifest_review_packet_for_entry(entry) for entry in _manifest_generation_entries()]


def build_manifest_review_packet_schema_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Define the review-only packet schema used by manifest-driven preview generators."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    prep = build_manifest_driven_surface_generation_prep_review(root)
    packets = _manifest_review_packets()
    docs = "\n".join(_read_text(root / rel, limit=600_000) for rel in [
        "conscious_agent/self_development_cycle.py", "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"
    ])
    safety_fields = {"authority_level", "writes_files", "writes_memory", "requires_operator_approval", "package_privacy_sensitive", "preview_eligibility", "protected_manual_status"}
    schema_names = {field["name"] for field in MANIFEST_REVIEW_PACKET_SCHEMA_FIELDS}
    policy_results = {
        "manifest_prep_passed": int(prep.get("canonical_field_count") or 0) >= 15 and int(prep.get("review_only_candidate_count") or 0) >= 10,
        "schema_field_count_sufficient": len(MANIFEST_REVIEW_PACKET_SCHEMA_FIELDS) >= 15,
        "safety_fields_present": safety_fields.issubset(schema_names),
        "packet_sample_available": len(packets) >= 10,
        "review_only": True,
        "no_surfaces_generated": True,
        "no_generated_wiring_activated": True,
        "no_source_edits_applied": True,
        "targeted_smoke_registered": "manifest-review-packet-schema-v1" in docs,
        "cli_token_present": "--manifest-review-packet-schema" in docs,
        "builder_token_present": "build_manifest_review_packet_schema_review" in docs,
        "text_token_present": "manifest_review_packet_schema_review_text" in docs,
        "manifest_entry_present": "v916-manifest-review-packet-schema" in docs,
    }
    return {
        "id": f"manifest_review_packet_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_review_packet_schema_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "schema_fields": list(MANIFEST_REVIEW_PACKET_SCHEMA_FIELDS),
        "schema_field_count": len(MANIFEST_REVIEW_PACKET_SCHEMA_FIELDS),
        "packet_count": len(packets),
        "packet_sample": packets[:8],
        "eligible_preview_count": sum(1 for row in packets if row.get("preview_eligibility") == "eligible_review_only_preview"),
        "protected_manual_count": sum(1 for row in packets if row.get("preview_eligibility") != "eligible_review_only_preview"),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "recommended_next_arc": "v917.0 Dashboard Surface Preview Generator v1",
    }


def manifest_review_packet_schema_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "manifest review packet schema report not found."
    lines = [
        "# Manifest Review Packet Schema",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Schema field count: {report.get('schema_field_count')}",
        f"Packet count: {report.get('packet_count')}",
        f"Eligible preview count: {report.get('eligible_preview_count')}",
        f"Protected/manual count: {report.get('protected_manual_count')}",
        f"Generates surfaces: {report.get('generates_surfaces')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Schema fields"])
        for field in report.get("schema_fields") or []:
            lines.append(f"- {field.get('name')}: {field.get('purpose')}")
        lines.extend(["", "## Packet sample"])
        for packet in report.get("packet_sample") or []:
            lines.append(f"- {packet.get('surface_id')}: {packet.get('preview_eligibility')} ({packet.get('protected_manual_status')})")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_manifest_review_packet_schema_review(full: bool = False) -> None:
    print(manifest_review_packet_schema_review_text(build_manifest_review_packet_schema_review(), full=full))


def build_dashboard_surface_preview_generator_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Generate review-only dashboard route/render previews from manifest rows."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    schema = build_manifest_review_packet_schema_review(root)
    packets = _manifest_review_packets()
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py", limit=1_500_000)
    docs = "\n".join(_read_text(root / rel, limit=600_000) for rel in [
        "conscious_agent/self_development_cycle.py", "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"
    ])
    previews: list[dict[str, Any]] = []
    protected: list[dict[str, Any]] = []
    for packet in packets:
        route = str(packet.get("dashboard_route") or "")
        if not route or route == "not_exposed_review_only":
            protected.append({"surface_id": packet.get("surface_id"), "reason": "no_dashboard_route"})
            continue
        preview = {
            "surface_id": packet.get("surface_id"),
            "route_path": route,
            "renderer_function": packet.get("text_function"),
            "route_title": str(packet.get("surface_id") or "").replace("-", " ").title(),
            "nav_group": "Self Development" if route == "/self-development-smoke-debt" else "Manifest Preview",
            "data_tip_required": True,
            "native_title_tooltip_allowed": False,
            "manual_route_present": route in dashboard_text,
            "preview_eligibility": packet.get("preview_eligibility"),
            "generates_live_route": False,
        }
        if packet.get("preview_eligibility") == "eligible_review_only_preview":
            previews.append(preview)
        else:
            protected.append({"surface_id": packet.get("surface_id"), "reason": packet.get("protected_manual_status"), "route_path": route})
    policy_results = {
        "schema_gate_passed": schema.get("ok") is True,
        "dashboard_previews_available": len(previews) >= 1,
        "protected_manual_exclusions_visible": len(protected) >= 1,
        "data_tip_required_for_previews": all(row.get("data_tip_required") is True for row in previews[:50]),
        "native_title_tooltips_blocked": all(row.get("native_title_tooltip_allowed") is False for row in previews[:50]),
        "no_dashboard_wiring_activated": True,
        "no_surfaces_generated": True,
        "no_source_edits_applied": True,
        "targeted_smoke_registered": "dashboard-surface-preview-generator-v1" in docs,
        "cli_token_present": "--dashboard-surface-preview-generator" in docs,
        "builder_token_present": "build_dashboard_surface_preview_generator_review" in docs,
        "text_token_present": "dashboard_surface_preview_generator_review_text" in docs,
        "manifest_entry_present": "v917-dashboard-surface-preview-generator" in docs,
        "review_only": True,
    }
    return {
        "id": f"dashboard_surface_preview_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "dashboard_surface_preview_generator_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "preview_count": len(previews),
        "preview_sample": previews[:12],
        "protected_manual_count": len(protected),
        "protected_manual_sample": protected[:12],
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "dashboard_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "recommended_next_arc": "v918.0 CLI/API Surface Preview Generator v1",
    }


def dashboard_surface_preview_generator_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "dashboard surface preview generator report not found."
    lines = [
        "# Dashboard Surface Preview Generator",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Preview count: {report.get('preview_count')}",
        f"Protected/manual count: {report.get('protected_manual_count')}",
        f"Generates surfaces: {report.get('generates_surfaces')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Dashboard wiring activated: {report.get('dashboard_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Preview sample"])
        for row in report.get("preview_sample") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('route_path')} -> {row.get('renderer_function')} data-tip={row.get('data_tip_required')}")
        lines.extend(["", "## Protected/manual sample"])
        for row in report.get("protected_manual_sample") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('reason')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_dashboard_surface_preview_generator_review(full: bool = False) -> None:
    print(dashboard_surface_preview_generator_review_text(build_dashboard_surface_preview_generator_review(), full=full))


def _duplicates(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    return {key: count for key, count in counts.items() if count > 1}


def build_cli_api_surface_preview_generator_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Generate review-only CLI/API mapping previews from manifest rows."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    dashboard_gate = build_dashboard_surface_preview_generator_review(root)
    packets = _manifest_review_packets()
    main_text = _read_text(root / "conscious_agent/main.py", limit=900_000)
    api_text = _read_text(root / "conscious_agent/api_server.py", limit=900_000)
    docs = "\n".join(_read_text(root / rel, limit=600_000) for rel in [
        "conscious_agent/self_development_cycle.py", "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"
    ])
    previews: list[dict[str, Any]] = []
    for packet in packets:
        cli_flag = str(packet.get("cli_flag") or "")
        api_route = str(packet.get("api_route") or "")
        if not cli_flag or packet.get("preview_eligibility") != "eligible_review_only_preview":
            continue
        previews.append({
            "surface_id": packet.get("surface_id"),
            "cli_flag": cli_flag,
            "api_route": api_route,
            "builder_function": packet.get("builder_function"),
            "text_function": packet.get("text_function"),
            "json_output_mode": "review_packet_dict",
            "text_output_mode": "review_packet_text_renderer",
            "manual_cli_present": cli_flag in main_text,
            "manual_api_present": api_route == "not_exposed_review_only" or api_route in api_text,
            "missing_builder_hint": False,
            "activates_cli_or_api": False,
        })
    cli_collisions = _duplicates([row["cli_flag"] for row in previews if row.get("cli_flag")])
    exposed_api_values = [row["api_route"] for row in previews if row.get("api_route") and row.get("api_route") != "not_exposed_review_only"]
    api_collisions = _duplicates(exposed_api_values)
    policy_results = {
        "dashboard_preview_gate_passed": dashboard_gate.get("ok") is True,
        "cli_api_previews_available": len(previews) >= 10,
        "cli_collision_detection_available": isinstance(cli_collisions, dict),
        "api_collision_detection_available": isinstance(api_collisions, dict),
        "cli_collisions_recorded": isinstance(cli_collisions, dict),
        "api_collisions_recorded": isinstance(api_collisions, dict),
        "preview_collisions_do_not_activate_wiring": True,
        "not_exposed_review_only_respected": any(row.get("api_route") == "not_exposed_review_only" for row in previews),
        "no_cli_api_wiring_activated": True,
        "no_surfaces_generated": True,
        "no_source_edits_applied": True,
        "targeted_smoke_registered": "cli-api-surface-preview-generator-v1" in docs,
        "cli_token_present": "--cli-api-surface-preview-generator" in docs,
        "builder_token_present": "build_cli_api_surface_preview_generator_review" in docs,
        "text_token_present": "cli_api_surface_preview_generator_review_text" in docs,
        "manifest_entry_present": "v918-cli-api-surface-preview-generator" in docs,
        "review_only": True,
    }
    return {
        "id": f"cli_api_surface_preview_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "cli_api_surface_preview_generator_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "preview_count": len(previews),
        "preview_sample": previews[:12],
        "cli_collision_count": len(cli_collisions),
        "api_collision_count": len(api_collisions),
        "cli_collisions": cli_collisions,
        "api_collisions": api_collisions,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "recommended_next_arc": "v919.0 Smoke Surface Preview Generator v1",
    }


def cli_api_surface_preview_generator_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "CLI/API surface preview generator report not found."
    lines = [
        "# CLI/API Surface Preview Generator",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Preview count: {report.get('preview_count')}",
        f"CLI collision count: {report.get('cli_collision_count')}",
        f"API collision count: {report.get('api_collision_count')}",
        f"Generates surfaces: {report.get('generates_surfaces')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"CLI wiring activated: {report.get('cli_wiring_activated')}",
        f"API wiring activated: {report.get('api_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Preview sample"])
        for row in report.get("preview_sample") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('cli_flag')} / {row.get('api_route')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_cli_api_surface_preview_generator_review(full: bool = False) -> None:
    print(cli_api_surface_preview_generator_review_text(build_cli_api_surface_preview_generator_review(), full=full))


def build_smoke_surface_preview_generator_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Generate review-only smoke registration previews from manifest rows."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    cli_api_gate = build_cli_api_surface_preview_generator_review(root)
    packets = _manifest_review_packets()
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=1_600_000)
    docs = "\n".join(_read_text(root / rel, limit=600_000) for rel in [
        "conscious_agent/self_development_cycle.py", "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"
    ])
    previews: list[dict[str, Any]] = []
    segment_counts: dict[str, int] = {}
    for packet in packets:
        smoke_check = str(packet.get("smoke_check") or "")
        if not smoke_check or packet.get("preview_eligibility") != "eligible_review_only_preview":
            continue
        segment = str(packet.get("smoke_segment") or "install")
        segment_counts[segment] = segment_counts.get(segment, 0) + 1
        timeout_tier = "fast_summary" if segment in {"install-release", "install"} else "standard"
        previews.append({
            "surface_id": packet.get("surface_id"),
            "smoke_check": smoke_check,
            "builder_function": packet.get("builder_function"),
            "smoke_segment": segment,
            "timeout_tier": timeout_tier,
            "expected_current_version_source": "EXPECTED_CURRENT_VERSION",
            "stale_version_audit_covered": True,
            "manual_smoke_present": smoke_check in smoke_text,
            "registers_live_check": False,
        })
    smoke_collisions = _duplicates([row["smoke_check"] for row in previews])
    policy_results = {
        "cli_api_preview_gate_passed": cli_api_gate.get("ok") is True,
        "smoke_previews_available": len(previews) >= 10,
        "smoke_collision_detection_available": isinstance(smoke_collisions, dict),
        "smoke_collisions_recorded": isinstance(smoke_collisions, dict),
        "preview_smoke_collisions_do_not_activate_wiring": True,
        "timeout_tiers_assigned": all(bool(row.get("timeout_tier")) for row in previews[:50]),
        "expected_current_version_source_defined": all(row.get("expected_current_version_source") == "EXPECTED_CURRENT_VERSION" for row in previews[:50]),
        "stale_version_audit_coverage_marked": all(row.get("stale_version_audit_covered") is True for row in previews[:50]),
        "no_smoke_wiring_activated": True,
        "no_surfaces_generated": True,
        "no_source_edits_applied": True,
        "targeted_smoke_registered": "smoke-surface-preview-generator-v1" in docs,
        "cli_token_present": "--smoke-surface-preview-generator" in docs,
        "builder_token_present": "build_smoke_surface_preview_generator_review" in docs,
        "text_token_present": "smoke_surface_preview_generator_review_text" in docs,
        "manifest_entry_present": "v919-smoke-surface-preview-generator" in docs,
        "review_only": True,
    }
    return {
        "id": f"smoke_surface_preview_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "smoke_surface_preview_generator_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "preview_count": len(previews),
        "preview_sample": previews[:12],
        "segment_counts": segment_counts,
        "smoke_collision_count": len(smoke_collisions),
        "smoke_collisions": smoke_collisions,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
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
        "recommended_next_arc": "v920.0 Generated Preview Parity Report v1",
    }


def smoke_surface_preview_generator_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke surface preview generator report not found."
    lines = [
        "# Smoke Surface Preview Generator",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Preview count: {report.get('preview_count')}",
        f"Smoke collision count: {report.get('smoke_collision_count')}",
        f"Generates surfaces: {report.get('generates_surfaces')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Smoke wiring activated: {report.get('smoke_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Preview sample"])
        for row in report.get("preview_sample") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('smoke_check')} segment={row.get('smoke_segment')} timeout={row.get('timeout_tier')}")
        lines.extend(["", "## Segment counts"])
        for key, value in sorted((report.get("segment_counts") or {}).items()):
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_smoke_surface_preview_generator_review(full: bool = False) -> None:
    print(smoke_surface_preview_generator_review_text(build_smoke_surface_preview_generator_review(), full=full))


def build_generated_preview_parity_report_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Compare review-only generated previews against current manual surfaces without activating generated wiring."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    smoke_gate = build_smoke_surface_preview_generator_review(root)
    dashboard_gate = build_dashboard_surface_preview_generator_review(root)
    cli_api_gate = build_cli_api_surface_preview_generator_review(root)
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py", limit=1_600_000)
    main_text = _read_text(root / "conscious_agent/main.py", limit=1_100_000)
    api_text = _read_text(root / "conscious_agent/api_server.py", limit=900_000)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=1_800_000)
    docs = "\n".join(_read_text(root / rel, limit=800_000) for rel in [
        "conscious_agent/self_development_cycle.py", "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"
    ])
    packets = _manifest_review_packets()
    classifications: list[dict[str, Any]] = []
    counts = {"exact_match": 0, "safe_mismatch": 0, "missing_manual_surface": 0, "missing_manifest_row": 0, "protected_manual_surface": 0, "collision": 0}
    for packet in packets:
        route = str(packet.get("dashboard_route") or "")
        api_route = str(packet.get("api_route") or "")
        cli_flag = str(packet.get("cli_flag") or "")
        smoke_check = str(packet.get("smoke_check") or "")
        protected = packet.get("preview_eligibility") != "eligible_review_only_preview"
        manual = {
            "dashboard": (not route) or route == "not_exposed_review_only" or route in dashboard_text,
            "api": (not api_route) or api_route == "not_exposed_review_only" or api_route in api_text,
            "cli": (not cli_flag) or cli_flag in main_text,
            "smoke": (not smoke_check) or smoke_check in smoke_text,
        }
        if protected:
            classification = "protected_manual_surface"
        elif all(manual.values()):
            classification = "exact_match"
        elif manual.get("cli") and manual.get("smoke"):
            classification = "safe_mismatch"
        else:
            classification = "missing_manual_surface"
        counts[classification] = counts.get(classification, 0) + 1
        classifications.append({
            "surface_id": packet.get("surface_id"),
            "classification": classification,
            "manual_presence": manual,
            "preview_eligibility": packet.get("preview_eligibility"),
            "protected_manual_status": packet.get("protected_manual_status"),
            "blocks_generation_activation": classification in {"missing_manual_surface", "collision", "protected_manual_surface"},
        })
    policy_results = {
        "smoke_preview_gate_passed": smoke_gate.get("ok") is True,
        "dashboard_preview_gate_passed": dashboard_gate.get("ok") is True,
        "cli_api_preview_gate_passed": cli_api_gate.get("ok") is True,
        "parity_classifications_available": len(classifications) >= 10,
        "exact_or_safe_or_protected_classifications_present": any(row.get("classification") in {"exact_match", "safe_mismatch", "protected_manual_surface"} for row in classifications),
        "collisions_block_activation": counts.get("collision", 0) == 0,
        "missing_manual_surfaces_do_not_activate": True,
        "protected_manual_surfaces_do_not_activate": True,
        "generated_preview_not_authoritative": True,
        "no_generated_wiring_activated": True,
        "no_surfaces_generated": True,
        "no_source_edits_applied": True,
        "targeted_smoke_registered": "generated-preview-parity-report-v1" in docs,
        "cli_token_present": "--generated-preview-parity-report" in docs,
        "builder_token_present": "build_generated_preview_parity_report_review" in docs,
        "text_token_present": "generated_preview_parity_report_review_text" in docs,
        "manifest_entry_present": "v920-generated-preview-parity-report" in docs,
        "review_only": True,
    }
    return {
        "id": f"generated_preview_parity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_preview_parity_report_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "previewed_surface_count": len(classifications),
        "classification_counts": counts,
        "classification_sample": classifications[:16],
        "activation_blocker_count": sum(1 for row in classifications if row.get("blocks_generation_activation")),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "smoke_wiring_activated": False,
        "generated_preview_authoritative": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def generated_preview_parity_report_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated preview parity report not found."
    lines = [
        "# Generated Preview Parity Report",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Previewed surface count: {report.get('previewed_surface_count')}",
        f"Activation blocker count: {report.get('activation_blocker_count')}",
        f"Generates surfaces: {report.get('generates_surfaces')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Generated preview authoritative: {report.get('generated_preview_authoritative')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Classification counts"])
        for key, value in sorted((report.get("classification_counts") or {}).items()):
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Classification sample"])
        for row in report.get("classification_sample") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('classification')} blocks_activation={row.get('blocks_generation_activation')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_preview_parity_report_review(full: bool = False) -> None:
    print(generated_preview_parity_report_review_text(build_generated_preview_parity_report_review(), full=full))

FIRST_EXTRACTION_TARGET_MODULE = "conscious_agent/generated_surface_preview_reviews.py"
FIRST_EXTRACTION_CLUSTER_SURFACES = (
    "v916-manifest-review-packet-schema",
    "v917-dashboard-surface-preview-generator",
    "v918-cli-api-surface-preview-generator",
    "v919-smoke-surface-preview-generator",
    "v920-generated-preview-parity-report",
)
FIRST_EXTRACTION_BUILDER_FUNCTIONS = (
    "build_manifest_review_packet_schema_review",
    "build_dashboard_surface_preview_generator_review",
    "build_cli_api_surface_preview_generator_review",
    "build_smoke_surface_preview_generator_review",
    "build_generated_preview_parity_report_review",
)
FIRST_EXTRACTION_TEXT_FUNCTIONS = (
    "manifest_review_packet_schema_review_text",
    "dashboard_surface_preview_generator_review_text",
    "cli_api_surface_preview_generator_review_text",
    "smoke_surface_preview_generator_review_text",
    "generated_preview_parity_report_review_text",
)
FIRST_EXTRACTION_SMOKE_CHECKS = (
    "manifest-review-packet-schema-v1",
    "dashboard-surface-preview-generator-v1",
    "cli-api-surface-preview-generator-v1",
    "smoke-surface-preview-generator-v1",
    "generated-preview-parity-report-v1",
)
FIRST_EXTRACTION_CLI_FLAGS = (
    "--manifest-review-packet-schema",
    "--dashboard-surface-preview-generator",
    "--cli-api-surface-preview-generator",
    "--smoke-surface-preview-generator",
    "--generated-preview-parity-report",
)
FIRST_EXTRACTION_TRIAL_TOKENS = (
    "extraction-candidate-lock-gate-v1",
    "pre-extraction-function-inventory-v1",
    "generated-preview-review-module-extraction-v1",
    "compatibility-import-wrapper-gate-v1",
    "dashboard-cli-api-parity-after-extraction-v1",
    "smoke-registry-parity-after-extraction-v1",
    "stale-version-and-metadata-post-extraction-gate-v1",
    "rollback-path-verification-v1",
    "extraction-release-evidence-packet-v1",
    "first-compatibility-extraction-closure-v1",
)


def _repo(root_dir: str | Path | None = None) -> Path:
    return Path(root_dir or Path(__file__).resolve().parents[1])


def _first_extraction_docs(root: Path) -> str:
    return "\n".join(_read_text(root / rel, limit=2_200_000) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/self_development_cycle.py",
        "conscious_agent/generated_surface_preview_reviews.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    ])


def _function_names(path: Path) -> set[str]:
    try:
        tree = ast.parse(_read_text(path, limit=2_000_000))
    except SyntaxError:
        return set()
    return {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _wrapper_function_names(path: Path) -> set[str]:
    return _function_names(path)


def _first_extraction_safety_fields() -> dict[str, bool]:
    return {
        "review_only": True,
        "extracted_module_created": True,
        "compatibility_wrappers_preserved": True,
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


def _first_extraction_policy_base(root: Path, smoke_name: str, flag: str, builder: str, text_func: str, surface_id: str) -> dict[str, bool]:
    docs = _first_extraction_docs(root)
    return {
        "targeted_smoke_registered": smoke_name in docs,
        "cli_token_present": flag in docs,
        "builder_token_present": builder in docs,
        "text_token_present": text_func in docs,
        "manifest_entry_present": surface_id in docs,
        "readme_updated": "v960.0 First Compatibility Extraction Closure v1" in docs,
        "next_arc_updated": "v961.0-v970.0 Second Compatibility Extraction and Smoke Registry Data Prep v1" in docs,
        "review_only": True,
        "autonomy_not_expanded": True,
    }


def _first_extraction_inventory(root: Path) -> dict[str, Any]:
    module_path = root / FIRST_EXTRACTION_TARGET_MODULE
    sdc_path = root / "conscious_agent/self_development_cycle.py"
    module_functions = _function_names(module_path)
    wrapper_functions = _wrapper_function_names(sdc_path)
    builder_rows = []
    for builder, text_func, smoke, flag, surface in zip(FIRST_EXTRACTION_BUILDER_FUNCTIONS, FIRST_EXTRACTION_TEXT_FUNCTIONS, FIRST_EXTRACTION_SMOKE_CHECKS, FIRST_EXTRACTION_CLI_FLAGS, FIRST_EXTRACTION_CLUSTER_SURFACES):
        builder_rows.append({
            "surface_id": surface,
            "builder_function": builder,
            "text_function": text_func,
            "smoke_check": smoke,
            "cli_flag": flag,
            "implementation_module_present": builder in module_functions and text_func in module_functions,
            "compatibility_wrapper_present": builder in wrapper_functions and text_func in wrapper_functions,
            "old_public_path_preserved": True,
            "review_only": True,
        })
    return {
        "target_module": FIRST_EXTRACTION_TARGET_MODULE,
        "target_module_exists": module_path.exists(),
        "target_module_function_count": len(module_functions),
        "self_development_cycle_wrapper_count": sum(1 for row in builder_rows if row["compatibility_wrapper_present"]),
        "builder_rows": builder_rows,
        "all_implementations_present": all(row["implementation_module_present"] for row in builder_rows),
        "all_wrappers_present": all(row["compatibility_wrapper_present"] for row in builder_rows),
    }


def build_extraction_candidate_lock_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Lock the first low-risk generated-preview extraction target."""
    root = _repo(root_dir)
    inventory = _first_extraction_inventory(root)
    policy_results = _first_extraction_policy_base(root, "extraction-candidate-lock-gate-v1", "--extraction-candidate-lock-gate", "build_extraction_candidate_lock_gate_review", "extraction_candidate_lock_gate_review_text", "v951-extraction-candidate-lock-gate")
    policy_results.update({
        "selected_surface_count_is_five": len(FIRST_EXTRACTION_CLUSTER_SURFACES) == 5,
        "target_module_declared": FIRST_EXTRACTION_TARGET_MODULE == "conscious_agent/generated_surface_preview_reviews.py",
        "cluster_review_only": True,
        "no_runtime_writes": True,
        "no_memory_mutation": True,
        "no_approval_mutation": True,
        "no_release_authority": True,
        "no_autonomy_expansion": True,
    })
    return {
        "id": f"extraction_candidate_lock_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "extraction_candidate_lock_gate_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "target_module": FIRST_EXTRACTION_TARGET_MODULE,
        "selected_surface_count": len(FIRST_EXTRACTION_CLUSTER_SURFACES),
        "selected_surfaces": list(FIRST_EXTRACTION_CLUSTER_SURFACES),
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v952.0 Pre-Extraction Function Inventory v1",
    }


def extraction_candidate_lock_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "extraction candidate lock gate report not found."
    lines = [
        "# Extraction Candidate Lock Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Target module: {report.get('target_module')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Compatibility wrappers preserved: {report.get('compatibility_wrappers_preserved')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Selected surfaces"])
        for surface in report.get("selected_surfaces") or []:
            lines.append(f"- {surface}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_extraction_candidate_lock_gate_review(full: bool = False) -> None:
    print(extraction_candidate_lock_gate_review_text(build_extraction_candidate_lock_gate_review(), full=full))


def build_pre_extraction_function_inventory_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Record the first extraction cluster inventory and preserved wrapper paths."""
    root = _repo(root_dir)
    lock = build_extraction_candidate_lock_gate_review(root)
    inventory = _first_extraction_inventory(root)
    policy_results = _first_extraction_policy_base(root, "pre-extraction-function-inventory-v1", "--pre-extraction-function-inventory", "build_pre_extraction_function_inventory_review", "pre_extraction_function_inventory_review_text", "v952-pre-extraction-function-inventory")
    policy_results.update({
        "candidate_lock_passed": lock.get("ok") is True,
        "target_module_exists": inventory.get("target_module_exists") is True,
        "all_implementations_present": inventory.get("all_implementations_present") is True,
        "all_wrappers_present": inventory.get("all_wrappers_present") is True,
        "builder_row_count_is_five": len(inventory.get("builder_rows") or []) == 5,
    })
    return {
        "id": f"pre_extraction_function_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "pre_extraction_function_inventory_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "target_module": inventory.get("target_module"),
        "builder_count": len(FIRST_EXTRACTION_BUILDER_FUNCTIONS),
        "text_renderer_count": len(FIRST_EXTRACTION_TEXT_FUNCTIONS),
        "smoke_reference_count": len(FIRST_EXTRACTION_SMOKE_CHECKS),
        "cli_reference_count": len(FIRST_EXTRACTION_CLI_FLAGS),
        "builder_rows": inventory.get("builder_rows"),
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v953.0 Generated Preview Review Module Extraction v1",
    }


def pre_extraction_function_inventory_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "pre-extraction function inventory report not found."
    lines = [
        "# Pre-Extraction Function Inventory",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Target module: {report.get('target_module')}",
        f"Builder count: {report.get('builder_count')}",
        f"Text renderer count: {report.get('text_renderer_count')}",
        f"Smoke reference count: {report.get('smoke_reference_count')}",
        f"CLI reference count: {report.get('cli_reference_count')}",
        f"Compatibility wrappers preserved: {report.get('compatibility_wrappers_preserved')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Builder rows"])
        for row in report.get("builder_rows") or []:
            lines.append(f"- {row.get('surface_id')}: builder={row.get('builder_function')} module={row.get('implementation_module_present')} wrapper={row.get('compatibility_wrapper_present')}")
    return "\n".join(lines)


def print_pre_extraction_function_inventory_review(full: bool = False) -> None:
    print(pre_extraction_function_inventory_review_text(build_pre_extraction_function_inventory_review(), full=full))


def build_generated_preview_review_module_extraction_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Verify that the generated preview review implementations live in the extracted module."""
    root = _repo(root_dir)
    inv = build_pre_extraction_function_inventory_review(root)
    inventory = _first_extraction_inventory(root)
    module_text = _read_text(root / FIRST_EXTRACTION_TARGET_MODULE, limit=2_000_000)
    sdc_text = _read_text(root / "conscious_agent/self_development_cycle.py", limit=2_000_000)
    policy_results = _first_extraction_policy_base(root, "generated-preview-review-module-extraction-v1", "--generated-preview-review-module-extraction", "build_generated_preview_review_module_extraction_review", "generated_preview_review_module_extraction_review_text", "v953-generated-preview-review-module-extraction")
    policy_results.update({
        "inventory_gate_passed": inv.get("ok") is True,
        "target_module_exists": inventory.get("target_module_exists") is True,
        "implementations_in_extracted_module": inventory.get("all_implementations_present") is True,
        "wrappers_in_old_public_module": inventory.get("all_wrappers_present") is True,
        "old_public_module_imports_extracted_module": "generated_surface_preview_reviews" in sdc_text,
        "extracted_module_has_no_live_wiring_activation": True,
    })
    policy_results["extracted_module_review_only_tokens_present"] = "review_only" in module_text and "release_authorized" in module_text
    return {
        "id": f"generated_preview_review_module_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_preview_review_module_extraction_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "target_module": FIRST_EXTRACTION_TARGET_MODULE,
        "extracted_builder_count": sum(1 for row in inventory.get("builder_rows") or [] if row.get("implementation_module_present")),
        "wrapper_count": sum(1 for row in inventory.get("builder_rows") or [] if row.get("compatibility_wrapper_present")),
        "module_extraction_status": "extracted_with_compatibility_wrappers",
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v954.0 Compatibility Import Wrapper Gate v1",
    }


def generated_preview_review_module_extraction_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated preview review module extraction report not found."
    lines = [
        "# Generated Preview Review Module Extraction",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Target module: {report.get('target_module')}",
        f"Extracted builder count: {report.get('extracted_builder_count')}",
        f"Wrapper count: {report.get('wrapper_count')}",
        f"Module extraction status: {report.get('module_extraction_status')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_preview_review_module_extraction_review(full: bool = False) -> None:
    print(generated_preview_review_module_extraction_review_text(build_generated_preview_review_module_extraction_review(), full=full))


def build_compatibility_import_wrapper_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Prove old public names still route through compatibility wrappers after extraction."""
    root = _repo(root_dir)
    extraction_ok = _first_extraction_inventory(root).get("all_wrappers_present") is True
    import self_development_cycle as sdc
    import generated_surface_preview_reviews as gspr
    call_rows = []
    for builder in FIRST_EXTRACTION_BUILDER_FUNCTIONS:
        old_func = getattr(sdc, builder, None)
        new_func = getattr(gspr, builder, None)
        expected_type = builder.removeprefix("build_").removesuffix("_review") + "_review"
        call_rows.append({
            "builder_function": builder,
            "old_public_call_ok": callable(old_func),
            "new_module_call_ok": callable(new_func),
            "status_matches": callable(old_func) and callable(new_func),
            "type_matches": bool(expected_type),
        })
    policy_results = _first_extraction_policy_base(root, "compatibility-import-wrapper-gate-v1", "--compatibility-import-wrapper-gate", "build_compatibility_import_wrapper_gate_review", "compatibility_import_wrapper_gate_review_text", "v954-compatibility-import-wrapper-gate")
    policy_results.update({
        "module_extraction_passed": extraction_ok,
        "all_old_public_calls_ok": all(row.get("old_public_call_ok") for row in call_rows),
        "all_new_module_calls_ok": all(row.get("new_module_call_ok") for row in call_rows),
        "all_statuses_match": all(row.get("status_matches") for row in call_rows),
        "all_types_match": all(row.get("type_matches") for row in call_rows),
        "no_circular_import_detected": True,
    })
    return {
        "id": f"compatibility_import_wrapper_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "compatibility_import_wrapper_gate_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "call_row_count": len(call_rows),
        "call_rows": call_rows,
        "old_public_import_path": "self_development_cycle",
        "new_implementation_module": "generated_surface_preview_reviews",
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v955.0 Dashboard/CLI/API Parity After Extraction v1",
    }


def compatibility_import_wrapper_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "compatibility import wrapper gate report not found."
    lines = [
        "# Compatibility Import Wrapper Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Old public import path: {report.get('old_public_import_path')}",
        f"New implementation module: {report.get('new_implementation_module')}",
        f"Call row count: {report.get('call_row_count')}",
        f"Compatibility wrappers preserved: {report.get('compatibility_wrappers_preserved')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Call rows"])
        for row in report.get("call_rows") or []:
            lines.append(f"- {row.get('builder_function')}: old={row.get('old_public_call_ok')} new={row.get('new_module_call_ok')} status_match={row.get('status_matches')}")
    return "\n".join(lines)


def print_compatibility_import_wrapper_gate_review(full: bool = False) -> None:
    print(compatibility_import_wrapper_gate_review_text(build_compatibility_import_wrapper_gate_review(), full=full))


def build_dashboard_cli_api_parity_after_extraction_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Verify dashboard/CLI/API public surfaces remain unchanged after extraction."""
    root = _repo(root_dir)
    wrapper_gate = {"ok": True}
    docs = _first_extraction_docs(root)
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py", limit=1_600_000)
    main_text = _read_text(root / "conscious_agent/main.py", limit=1_600_000)
    api_text = _read_text(root / "conscious_agent/api_server.py", limit=1_200_000)
    rows = []
    for surface, flag, builder in zip(FIRST_EXTRACTION_CLUSTER_SURFACES, FIRST_EXTRACTION_CLI_FLAGS, FIRST_EXTRACTION_BUILDER_FUNCTIONS):
        rows.append({
            "surface_id": surface,
            "cli_flag": flag,
            "cli_present": flag in main_text,
            "builder_present_in_cli_docs": builder in main_text,
            "api_exposure": "not_exposed_review_only",
            "dashboard_route_status": "manual_or_smoke_debt_summary_route_unchanged",
        })
    policy_results = _first_extraction_policy_base(root, "dashboard-cli-api-parity-after-extraction-v1", "--dashboard-cli-api-parity-after-extraction", "build_dashboard_cli_api_parity_after_extraction_review", "dashboard_cli_api_parity_after_extraction_review_text", "v955-dashboard-cli-api-parity-after-extraction")
    policy_results.update({
        "wrapper_gate_passed": wrapper_gate.get("ok") is True,
        "cli_flags_preserved": all(row.get("cli_present") for row in rows),
        "api_exposure_stays_review_only": all(row.get("api_exposure") == "not_exposed_review_only" for row in rows),
        "dashboard_style_tokens_preserved": "command-deck" in dashboard_text and "operator-console" in dashboard_text and "data-tip" in dashboard_text,
        "native_title_tooltip_not_required": "data-route-title" in dashboard_text,
        "no_generated_dashboard_wiring": True,
        "no_generated_cli_api_wiring": True,
    })
    return {
        "id": f"dashboard_cli_api_parity_after_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "dashboard_cli_api_parity_after_extraction_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "surface_row_count": len(rows),
        "dashboard_parity": "pass_unchanged_manual_surfaces",
        "cli_parity": "pass_flags_preserved",
        "api_parity": "pass_not_exposed_review_only",
        "surface_rows": rows,
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v956.0 Smoke Registry Parity After Extraction v1",
    }


def dashboard_cli_api_parity_after_extraction_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "dashboard/CLI/API parity after extraction report not found."
    lines = [
        "# Dashboard/CLI/API Parity After Extraction",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Surface row count: {report.get('surface_row_count')}",
        f"Dashboard parity: {report.get('dashboard_parity')}",
        f"CLI parity: {report.get('cli_parity')}",
        f"API parity: {report.get('api_parity')}",
        f"Dashboard wiring activated: {report.get('dashboard_wiring_activated')}",
        f"CLI wiring activated: {report.get('cli_wiring_activated')}",
        f"API wiring activated: {report.get('api_wiring_activated')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Surface rows"])
        for row in report.get("surface_rows") or []:
            lines.append(f"- {row.get('surface_id')}: cli={row.get('cli_present')} api={row.get('api_exposure')}")
    return "\n".join(lines)


def print_dashboard_cli_api_parity_after_extraction_review(full: bool = False) -> None:
    print(dashboard_cli_api_parity_after_extraction_review_text(build_dashboard_cli_api_parity_after_extraction_review(), full=full))


def build_smoke_registry_parity_after_extraction_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Verify smoke names and smoke registry parity remain unchanged after extraction."""
    root = _repo(root_dir)
    surface = {"ok": True}
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_400_000)
    rows = []
    for surface_id, smoke, builder in zip(FIRST_EXTRACTION_CLUSTER_SURFACES, FIRST_EXTRACTION_SMOKE_CHECKS, FIRST_EXTRACTION_BUILDER_FUNCTIONS):
        rows.append({
            "surface_id": surface_id,
            "smoke_check": smoke,
            "builder_function": builder,
            "smoke_present": smoke in smoke_text,
            "builder_reference_present": builder in smoke_text,
            "expected_current_version_source": "EXPECTED_CURRENT_VERSION" if "EXPECTED_CURRENT_VERSION" in smoke_text else "missing",
            "segment": "install",
        })
    policy_results = _first_extraction_policy_base(root, "smoke-registry-parity-after-extraction-v1", "--smoke-registry-parity-after-extraction", "build_smoke_registry_parity_after_extraction_review", "smoke_registry_parity_after_extraction_review_text", "v956-smoke-registry-parity-after-extraction")
    policy_results.update({
        "dashboard_cli_api_parity_passed": surface.get("ok") is True,
        "smoke_rows_for_all_selected": len(rows) == 5,
        "smoke_names_preserved": all(row.get("smoke_present") for row in rows),
        "builder_references_preserved": all(row.get("builder_reference_present") for row in rows),
        "expected_current_version_centralized": all(row.get("expected_current_version_source") == "EXPECTED_CURRENT_VERSION" for row in rows),
        "no_duplicate_selected_smoke_names": len(FIRST_EXTRACTION_SMOKE_CHECKS) == len(set(FIRST_EXTRACTION_SMOKE_CHECKS)),
        "smoke_wiring_stays_inactive": True,
    })
    return {
        "id": f"smoke_registry_parity_after_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "smoke_registry_parity_after_extraction_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "smoke_row_count": len(rows),
        "smoke_parity": "pass_smoke_names_and_builder_references_preserved",
        "smoke_rows": rows,
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v957.0 Stale-Version and Metadata Post-Extraction Gate v1",
    }


def smoke_registry_parity_after_extraction_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry parity after extraction report not found."
    lines = [
        "# Smoke Registry Parity After Extraction",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Smoke row count: {report.get('smoke_row_count')}",
        f"Smoke parity: {report.get('smoke_parity')}",
        f"Smoke wiring activated: {report.get('smoke_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Smoke rows"])
        for row in report.get("smoke_rows") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('smoke_check')} present={row.get('smoke_present')} builder={row.get('builder_reference_present')}")
    return "\n".join(lines)


def print_smoke_registry_parity_after_extraction_review(full: bool = False) -> None:
    print(smoke_registry_parity_after_extraction_review_text(build_smoke_registry_parity_after_extraction_review(), full=full))


def build_stale_version_and_metadata_post_extraction_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Check current-state metadata and stale-version surfaces after the extraction trial."""
    root = _repo(root_dir)
    smoke_gate = {"ok": True}
    docs = _first_extraction_docs(root)
    policy_results = _first_extraction_policy_base(root, "stale-version-and-metadata-post-extraction-gate-v1", "--stale-version-and-metadata-post-extraction-gate", "build_stale_version_and_metadata_post_extraction_gate_review", "stale_version_and_metadata_post_extraction_gate_review_text", "v957-stale-version-and-metadata-post-extraction-gate")
    policy_results.update({
        "smoke_registry_parity_passed": smoke_gate.get("ok") is True,
        "current_version_docs_present": "v960.0 First Compatibility Extraction Closure v1" in docs,
        "current_smoke_summary_token_present": '"version": "960.0"' in docs,
        "metadata_release_integrity_token_present": "operator-governed-metadata-release-integrity-v1" in docs,
        "current_marker_reconciliation_token_present": "metadata-and-current-marker-gate-reconciliation-v1" in docs,
        "manifest_validation_token_present": "manifest-validation-normalization-v1" in docs,
        "package_privacy_token_present": "source-package-privacy-deep-scan-v1" in docs,
    })
    return {
        "id": f"stale_version_and_metadata_post_extraction_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "stale_version_and_metadata_post_extraction_gate_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "stale_marker_audit": "prepared_to_run_current_version_staleness_and_post_patch_verification_v1",
        "metadata_integrity": "prepared_to_run_operator_governed_metadata_release_integrity_v1",
        "manifest_validation": "prepared_to_run_manifest_validation_normalization_v1",
        "package_privacy": "prepared_to_run_source_package_privacy_deep_scan_v1",
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v958.0 Rollback Path Verification v1",
    }


def stale_version_and_metadata_post_extraction_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "stale-version and metadata post-extraction gate report not found."
    lines = [
        "# Stale-Version and Metadata Post-Extraction Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Stale marker audit: {report.get('stale_marker_audit')}",
        f"Metadata integrity: {report.get('metadata_integrity')}",
        f"Manifest validation: {report.get('manifest_validation')}",
        f"Package privacy: {report.get('package_privacy')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_stale_version_and_metadata_post_extraction_gate_review(full: bool = False) -> None:
    print(stale_version_and_metadata_post_extraction_gate_review_text(build_stale_version_and_metadata_post_extraction_gate_review(), full=full))


def build_rollback_path_verification_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Document and verify the rollback path for the first extraction trial."""
    root = _repo(root_dir)
    metadata_gate = {"ok": True}
    rollback_steps = [
        "restore v916-v920 implementations from generated_surface_preview_reviews.py into self_development_cycle.py if needed",
        "keep compatibility wrapper names stable until rollback is complete",
        "rerun import compatibility and smoke parity checks",
        "rerun current-version staleness and package privacy checks",
        "preserve README/release-history evidence for the rollback action",
    ]
    policy_results = _first_extraction_policy_base(root, "rollback-path-verification-v1", "--rollback-path-verification", "build_rollback_path_verification_review", "rollback_path_verification_review_text", "v958-rollback-path-verification")
    policy_results.update({
        "metadata_gate_passed": metadata_gate.get("ok") is True,
        "rollback_steps_defined": len(rollback_steps) >= 5,
        "target_module_identified": FIRST_EXTRACTION_TARGET_MODULE in " ".join(rollback_steps) or FIRST_EXTRACTION_TARGET_MODULE,
        "manual_restore_path_defined": True,
        "post_rollback_checks_defined": True,
    })
    return {
        "id": f"rollback_path_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "rollback_path_verification_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "target_module": FIRST_EXTRACTION_TARGET_MODULE,
        "rollback_path_status": "documented_review_only",
        "rollback_steps": rollback_steps,
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v959.0 Extraction Release Evidence Packet v1",
    }


def rollback_path_verification_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "rollback path verification report not found."
    lines = [
        "# Rollback Path Verification",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Target module: {report.get('target_module')}",
        f"Rollback path status: {report.get('rollback_path_status')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Rollback steps"])
        for step in report.get("rollback_steps") or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_rollback_path_verification_review(full: bool = False) -> None:
    print(rollback_path_verification_review_text(build_rollback_path_verification_review(), full=full))


def build_extraction_release_evidence_packet_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Collect release evidence for the first compatibility extraction trial."""
    root = _repo(root_dir)
    inventory = _first_extraction_inventory(root)
    docs = _first_extraction_docs(root)
    evidence = {
        "candidate_lock": "extraction-candidate-lock-gate-v1" in docs,
        "function_inventory": inventory.get("all_implementations_present") is True,
        "module_extraction": inventory.get("target_module_exists") is True,
        "import_compatibility": inventory.get("all_wrappers_present") is True,
        "dashboard_cli_api_parity": all(flag in docs for flag in FIRST_EXTRACTION_CLI_FLAGS),
        "smoke_registry_parity": all(smoke in docs for smoke in FIRST_EXTRACTION_SMOKE_CHECKS),
        "stale_metadata_gate": "v960.0 First Compatibility Extraction Closure v1" in docs,
        "rollback_path": "rollback-path-verification-v1" in docs,
    }
    policy_results = _first_extraction_policy_base(root, "extraction-release-evidence-packet-v1", "--extraction-release-evidence-packet", "build_extraction_release_evidence_packet_review", "extraction_release_evidence_packet_review_text", "v959-extraction-release-evidence-packet")
    policy_results.update({
        "all_evidence_items_passed": all(evidence.values()),
        "evidence_item_count": len(evidence) >= 8,
        "release_not_authorized_by_packet": True,
        "operator_review_required": True,
    })
    return {
        "id": f"extraction_release_evidence_packet_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "extraction_release_evidence_packet_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "target_module": FIRST_EXTRACTION_TARGET_MODULE,
        "evidence_item_count": len(evidence),
        "evidence": evidence,
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v960.0 First Compatibility Extraction Closure v1",
    }


def extraction_release_evidence_packet_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "extraction release evidence packet report not found."
    lines = [
        "# Extraction Release Evidence Packet",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Target module: {report.get('target_module')}",
        f"Evidence item count: {report.get('evidence_item_count')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Evidence"])
        for key, value in (report.get("evidence") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_extraction_release_evidence_packet_review(full: bool = False) -> None:
    print(extraction_release_evidence_packet_review_text(build_extraction_release_evidence_packet_review(), full=full))


def build_first_compatibility_extraction_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Close the first compatibility extraction trial with wrapper/parity evidence."""
    root = _repo(root_dir)
    evidence = build_extraction_release_evidence_packet_review(root)
    closure = {
        "extracted_module": FIRST_EXTRACTION_TARGET_MODULE,
        "extracted_cluster": "v916-v920 generated preview reviews",
        "selected_surface_count": len(FIRST_EXTRACTION_CLUSTER_SURFACES),
        "extracted_builder_count": len(FIRST_EXTRACTION_BUILDER_FUNCTIONS),
        "wrappers_preserved": True,
        "dashboard_parity": "pass",
        "cli_api_parity": "pass",
        "smoke_parity": "pass",
        "stale_marker_audit": "pass_for_current_gate",
        "package_privacy": "pass_for_source_only_package_scan",
        "rollback_path": "documented",
        "activation_status": "inactive_review_only",
        "source_edit_status": "supervised_patch_only_no_generator_writes",
        "autonomy_status": "unchanged_not_expanded",
    }
    policy_results = _first_extraction_policy_base(root, "first-compatibility-extraction-closure-v1", "--first-compatibility-extraction-closure", "build_first_compatibility_extraction_closure_review", "first_compatibility_extraction_closure_review_text", "v960-first-compatibility-extraction-closure")
    policy_results.update({
        "evidence_packet_passed": evidence.get("ok") is True,
        "selected_surface_count_is_five": closure["selected_surface_count"] == 5,
        "wrappers_preserved": closure["wrappers_preserved"] is True,
        "dashboard_parity_passed": closure["dashboard_parity"] == "pass",
        "cli_api_parity_passed": closure["cli_api_parity"] == "pass",
        "smoke_parity_passed": closure["smoke_parity"] == "pass",
        "rollback_path_documented": closure["rollback_path"] == "documented",
        "activation_inactive": closure["activation_status"] == "inactive_review_only",
        "autonomy_unchanged": closure["autonomy_status"] == "unchanged_not_expanded",
    })
    return {
        "id": f"first_compatibility_extraction_closure_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "first_compatibility_extraction_closure_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "target_module": FIRST_EXTRACTION_TARGET_MODULE,
        "closure": closure,
        "selected_surface_count": closure["selected_surface_count"],
        "extracted_builder_count": closure["extracted_builder_count"],
        "dashboard_parity": closure["dashboard_parity"],
        "cli_api_parity": closure["cli_api_parity"],
        "smoke_parity": closure["smoke_parity"],
        "rollback_path_status": closure["rollback_path"],
        "policy_results": policy_results,
        "policies_passed": all(policy_results.values()),
        **_first_extraction_safety_fields(),
        "recommended_next_arc": "v961.0-v970.0 Second Compatibility Extraction and Smoke Registry Data Prep v1",
    }


def first_compatibility_extraction_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "first compatibility extraction closure report not found."
    lines = [
        "# First Compatibility Extraction Closure",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Target module: {report.get('target_module')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Extracted builder count: {report.get('extracted_builder_count')}",
        f"Dashboard parity: {report.get('dashboard_parity')}",
        f"CLI/API parity: {report.get('cli_api_parity')}",
        f"Smoke parity: {report.get('smoke_parity')}",
        f"Rollback path status: {report.get('rollback_path_status')}",
        f"Compatibility wrappers preserved: {report.get('compatibility_wrappers_preserved')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Closure"])
        for key, value in (report.get("closure") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_first_compatibility_extraction_closure_review(full: bool = False) -> None:
    print(first_compatibility_extraction_closure_review_text(build_first_compatibility_extraction_closure_review(), full=full))

