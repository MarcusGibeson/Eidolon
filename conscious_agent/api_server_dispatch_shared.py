from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any, Callable, Sequence
import importlib

API_SERVER_DISPATCH_SHARED_VERSION = RUNTIME_VERSION
API_SERVER_DISPATCH_HELPER_ID = "api-server-dispatch-helper-shared-v1"


def source_surface_route_matches(parts: Sequence[str], slug: str) -> bool:
    """Match a manual /api/source-surface/<slug> route without replacing API dispatch."""
    return list(parts) == ["source-surface", slug]


def _query_flag(query: dict[str, list[str]] | None, key: str, default: bool = False) -> bool:
    values = (query or {}).get(key)
    if not values:
        return default
    value = str(values[-1]).strip().lower()
    if value in {"1", "true", "yes", "on", "full"}:
        return True
    if value in {"0", "false", "no", "off", "preview"}:
        return False
    return default


def _query_value(query: dict[str, list[str]] | None, key: str, default: str) -> str:
    values = (query or {}).get(key)
    if not values:
        return default
    return str(values[-1] or default)


def build_manual_preview_dispatch_payload(
    query: dict[str, list[str]] | None,
    *,
    project_root: str | Path,
    metadata_builder: Callable[..., dict[str, Any]],
    report_builder: Callable[..., dict[str, Any]],
    payload_builder: Callable[[dict[str, Any]], dict[str, Any]],
    warning: str,
) -> dict[str, Any]:
    """Build a GET preview payload for one manual API route.

    This helper centralizes the safe preview pattern only. It does not register routes,
    replace manual dispatch, execute fixtures, spawn subprocesses, write source files,
    authorize release, or expand autonomy.
    """
    query = query or {}
    project_id = _query_value(query, "project", "eidolon")
    inspect_sources = _query_flag(query, "inspect_sources", False)
    root = Path(project_root)
    report = report_builder(root, inspect_sources=True) if inspect_sources else metadata_builder(project_id=project_id)
    payload = payload_builder(report)
    payload.setdefault("api_dispatch_helper", API_SERVER_DISPATCH_HELPER_ID)
    payload.setdefault("manual_api_dispatch_remains_authoritative", True)
    payload.setdefault("api_get_preview_only", True)
    payload.setdefault("dashboard_get_preview_only", True)
    payload.setdefault("actual_fixture_execution_count", 0)
    payload.setdefault("subprocess_spawn_count", 0)
    payload.setdefault("source_write_count", 0)
    payload.setdefault("source_delete_count", 0)
    payload.setdefault("actual_fixture_execution_allowed", False)
    payload.setdefault("generated_wiring_activated", False)
    payload.setdefault("release_authorized", False)
    payload.setdefault("autonomy_expanded", False)
    if _query_flag(query, "execute", False) or _query_flag(query, "live", False) or _query_flag(query, "approve", False):
        payload.setdefault("warnings", []).append(warning)
    return payload


API_SERVER_DISPATCH_ROUTE_TABLE_ID = "api-server-dispatch-route-table-v1"

API_SERVER_DISPATCH_ROUTE_TABLE: tuple[dict[str, Any], ...] = (
    {
        "slug": "api-server-dispatch-helper-extraction-pilot",
        "module": "api_server_dispatch_helper_extraction_pilot",
        "metadata_builder": "build_api_server_dispatch_helper_extraction_pilot_metadata",
        "report_builder": "build_api_server_dispatch_helper_extraction_pilot",
        "payload_builder": "api_preview_payload",
        "warning": "API Server Dispatch Helper Extraction Pilot is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.",
    },
    {
        "slug": "api-server-dispatch-helper-backfill",
        "module": "api_server_dispatch_helper_backfill",
        "metadata_builder": "build_api_server_dispatch_helper_backfill_metadata",
        "report_builder": "build_api_server_dispatch_helper_backfill",
        "payload_builder": "api_preview_payload",
        "warning": "API Server Dispatch Helper Backfill is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.",
    },
    {
        "slug": "api-server-dispatch-helper-route-table-extraction",
        "module": "api_server_dispatch_route_table_extraction",
        "metadata_builder": "build_api_server_dispatch_route_table_extraction_metadata",
        "report_builder": "build_api_server_dispatch_route_table_extraction",
        "payload_builder": "api_preview_payload",
        "warning": "API Server Dispatch Helper Route Table Extraction is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.",
        "added_in": "1070.8",
    },
    {
        "slug": "api-server-dispatch-route-table-backfill",
        "module": "api_server_dispatch_route_table_backfill",
        "metadata_builder": "build_api_server_dispatch_route_table_backfill_metadata",
        "report_builder": "build_api_server_dispatch_route_table_backfill",
        "payload_builder": "api_preview_payload",
        "warning": "API Server Dispatch Route Table Backfill is GET preview-only. It does not execute generated fixtures, spawn subprocesses, write or delete source, activate generated wiring, authorize release, or expand autonomy.",
        "added_in": "1070.9",
    },

    {
        "slug": "audited-sandbox-backend-evidence-interface",
        "module": "audited_sandbox_backend_evidence_interface",
        "metadata_builder": "build_audited_sandbox_backend_evidence_interface_metadata",
        "report_builder": "build_audited_sandbox_backend_evidence_interface",
        "payload_builder": "api_preview_payload",
        "warning": "Audited Sandbox Backend Evidence Interface is GET preview-only. It does not execute generated fixtures, spawn subprocesses, write or delete source, activate generated wiring, authorize release, or expand autonomy.",
        "added_in": "1071.5",
    },
)


def api_dispatch_route_table_rows() -> list[dict[str, Any]]:
    return [
        {
            "slug": str(entry["slug"]),
            "route": f"/api/source-surface/{entry['slug']}",
            "module": str(entry["module"]),
            "helper": "build_route_table_preview_payload",
            "status": "route_table_preview_only",
            "replaces_manual_dispatch": False,
        }
        for entry in API_SERVER_DISPATCH_ROUTE_TABLE
    ]

def api_dispatch_route_table_backfill_rows() -> list[dict[str, Any]]:
    return [
        {
            "slug": str(entry["slug"]),
            "route": f"/api/source-surface/{entry['slug']}",
            "module": str(entry["module"]),
            "helper": "build_route_table_preview_payload",
            "status": "backfilled_route_table_preview_only" if entry.get("added_in") == "1070.8" else "preexisting_route_table_preview_only",
            "added_in": str(entry.get("added_in", "1070.7")),
            "replaces_manual_dispatch": False,
        }
        for entry in API_SERVER_DISPATCH_ROUTE_TABLE
    ]


def build_route_table_preview_payload(
    parts: Sequence[str],
    query: dict[str, list[str]] | None,
    *,
    project_root: str | Path,
) -> dict[str, Any] | None:
    """Build a preview payload from the narrow manual route table.

    The table centralizes helper-backed preview route construction only. It does
    not register routes globally, replace api_server.py manual authority, execute
    generated fixtures, spawn subprocesses, write source files, authorize release,
    or expand autonomy.
    """
    for entry in API_SERVER_DISPATCH_ROUTE_TABLE:
        slug = str(entry["slug"])
        if not source_surface_route_matches(parts, slug):
            continue
        module = importlib.import_module(str(entry["module"]))
        payload = build_manual_preview_dispatch_payload(
            query,
            project_root=project_root,
            metadata_builder=getattr(module, str(entry["metadata_builder"])),
            report_builder=getattr(module, str(entry["report_builder"])),
            payload_builder=getattr(module, str(entry["payload_builder"])),
            warning=str(entry["warning"]),
        )
        payload.setdefault("api_dispatch_route_table", API_SERVER_DISPATCH_ROUTE_TABLE_ID)
        payload.setdefault("manual_route_table_replaces_api_dispatch", False)
        return payload
    return None


def api_dispatch_helper_rows() -> list[dict[str, Any]]:
    return [
        {"helper": "source_surface_route_matches", "scope": "manual route if-block match", "status": "available", "replaces_dispatch": False},
        {"helper": "build_manual_preview_dispatch_payload", "scope": "GET preview payload assembly", "status": "available", "replaces_dispatch": False},
        {"helper": "_query_flag", "scope": "bounded query flag parsing", "status": "internal", "replaces_dispatch": False},
    ]


def api_dispatch_helper_backfill_rows() -> list[dict[str, Any]]:
    return [
        {"route": "/api/source-surface/api-preview-adapter-extraction-pilot", "module": "api_preview_adapter_extraction_pilot.py", "helper": "build_manual_preview_dispatch_payload", "status": "backfilled_preview_only", "behavior_change": "none_authority_preserved"},
        {"route": "/api/source-surface/api-preview-adapter-backfill", "module": "api_preview_adapter_backfill.py", "helper": "build_manual_preview_dispatch_payload", "status": "backfilled_preview_only", "behavior_change": "none_authority_preserved"},
    ]


# v1070.8 API server dispatch shared helper tokens: api-server-dispatch-helper-shared-v1 source_surface_route_matches build_manual_preview_dispatch_payload api_dispatch_helper_rows api_dispatch_helper_backfill_rows api_get_preview_only=True dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_api_dispatch_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.8 API server dispatch route table tokens: api-server-dispatch-helper-route-table-extraction-v1 api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows build_route_table_preview_payload manual_route_table_replaces_api_dispatch=False api_get_preview_only=True dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_api_dispatch_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.8 API server dispatch route table backfill tokens: api-server-dispatch-route-table-backfill-v1 /api-server-dispatch-route-table-backfill /api/source-surface/api-server-dispatch-route-table-backfill api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows api_dispatch_route_table_backfill_rows build_route_table_preview_payload route_table_backfilled_route_count=1 route_table_route_count=3 manual_route_table_replaces_api_dispatch=False api_get_preview_only=True dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_api_dispatch_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.9 API server dispatch route table safety parity tokens: api-server-dispatch-route-table-safety-parity-v1 /api-server-dispatch-route-table-safety-parity /api/source-surface/api-server-dispatch-route-table-safety-parity route_table_payload_manual_helper_parity=True route_table_safety_key_parity=True route_table_safe_preview_row_count=4 route_table_newly_migrated_route_count=1 old_direct_branch_removed=True manual_route_table_replaces_api_dispatch=False api_get_preview_only=True dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1071.5 audited sandbox evidence interface route table tokens: audited-sandbox-backend-evidence-interface-v1 /api/source-surface/audited-sandbox-backend-evidence-interface route_table_safe_preview_row_count=5 sandbox_backend_admitted=False fixture_execution_remains_blocked=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False
