from __future__ import annotations

"""Structural and behavioral validation for the v1250.8 API catalog/runtime extraction."""

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "v1250.8"
BASELINE_PARENT_LINE_COUNT = 10377
BASELINE_NORMALIZED_INDEX_SHA256 = "c8750522096806b8aa334c1bc2a381bd52cf499f9d719b14bbb34d1f5e3d5027"
AUTHORITY_FLAGS = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _function_span(text: str, name: str) -> int:
    tree = ast.parse(text)
    node = next((row for row in tree.body if isinstance(row, ast.FunctionDef) and row.name == name), None)
    return 0 if node is None else int(node.end_lineno - node.lineno + 1)


def validate_api_surface_runtime_decomposition(*, source_root: str | Path | None = None) -> dict[str, Any]:
    import sys

    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    for value in (root / "conscious_agent", root):
        if str(value) not in sys.path:
            sys.path.insert(0, str(value))
    import api_catalog  # type: ignore
    import api_http_runtime  # type: ignore
    import api_server  # type: ignore

    parent_path = root / "conscious_agent/api_server.py"
    catalog_path = root / "conscious_agent/api_catalog.py"
    runtime_path = root / "conscious_agent/api_http_runtime.py"
    parent = parent_path.read_text(encoding="utf-8") if parent_path.is_file() else ""
    catalog = catalog_path.read_text(encoding="utf-8") if catalog_path.is_file() else ""
    runtime = runtime_path.read_text(encoding="utf-8") if runtime_path.is_file() else ""
    parent_lines = len(parent.splitlines())
    index = api_server._api_index()
    direct_index = api_catalog.build_api_index(api_server.API_VERSION)
    normalized = dict(index)
    normalized["version"] = "__VERSION__"
    index_sha = hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    root_status, root_payload = api_server.dispatch_api("GET", "/api")
    missing_status, missing_payload = api_server.dispatch_api("GET", "/api/definitely-not-a-route")
    checks = {
        "catalog_module_present": catalog_path.is_file(),
        "runtime_module_present": runtime_path.is_file(),
        "contracts_current": 'CONTRACT_VERSION = "v1250.8"' in catalog and 'CONTRACT_VERSION = "v1250.8"' in runtime,
        "catalog_wrapper_bounded": 5 <= _function_span(parent, "_api_index") <= 15,
        "catalog_extracted": _function_span(catalog, "build_api_index") >= 640,
        "runtime_factory_present": "def build_api_handler_class" in runtime and "class EidolonApiHandler" in runtime,
        "manual_dispatch_preserved": "def dispatch_api" in parent and "def handle_api_get" in parent and "def handle_api_post" in parent,
        "parent_reduced": parent_lines < BASELINE_PARENT_LINE_COUNT - 650,
        "catalog_parity": index == direct_index,
        "baseline_index_parity": index_sha == BASELINE_NORMALIZED_INDEX_SHA256,
        "endpoint_inventory_preserved": isinstance(index.get("endpoints"), dict) and len(index["endpoints"]) == 649,
        "root_route_operational": root_status == 200 and root_payload.get("ok") is True,
        "missing_route_controlled": missing_status == 404 and missing_payload.get("ok") is False,
        "handler_extracted": api_server.EidolonApiHandler.__module__ == "api_http_runtime",
        "handler_contract_preserved": api_server.EidolonApiHandler.server_version == "EidolonAPI/10.0",
        "transport_has_no_route_builders": "def handle_api_get" not in runtime and "def handle_api_post" not in runtime,
        "no_authority_expansion": '"release_authorized": False' in catalog,
    }
    passed = sum(bool(value) for value in checks.values())
    result: dict[str, Any] = {
        "ok": passed == len(checks),
        "status": "api_surface_runtime_decomposed" if passed == len(checks) else "api_surface_runtime_decomposition_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "parent_line_count": parent_lines,
        "baseline_parent_line_count": BASELINE_PARENT_LINE_COUNT,
        "catalog_line_count": len(catalog.splitlines()),
        "runtime_line_count": len(runtime.splitlines()),
        "normalized_index_sha256": index_sha,
        "endpoint_count": len(index.get("endpoints") or {}),
        "read_only": True,
        "content_free": True,
        **AUTHORITY_FLAGS,
    }
    result["validation_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "validate_api_surface_runtime_decomposition"]
