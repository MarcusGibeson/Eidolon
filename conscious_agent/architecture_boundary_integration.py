from __future__ import annotations

"""v1276.3-.5 integration validation for extracted architecture boundaries."""

import ast
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from architecture_boundary_foundations import AUTHORITY_FLAGS, EXTRACTIONS, build_architecture_boundary_inventory

CONTRACT_VERSION = "v1276.5"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _normalized_def_hash(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name), None)
    if node is None:
        return ""
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def build_architecture_boundary_integration_report(source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    for p in (root / "conscious_agent", root):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    inventory = build_architecture_boundary_inventory(root)
    api = importlib.import_module("api_server")
    api_child = importlib.import_module("api_request_boundary")
    dashboard = importlib.import_module("dashboard")
    panel_child = importlib.import_module("dashboard_development_campaign_panel")
    maintenance = importlib.import_module("self_maintenance")
    release_child = importlib.import_module("release_evidence_boundary")

    panel = dashboard._development_campaign_panel()
    rows = {
        "inventory_ok": inventory.get("ok") is True,
        "api_error_reexport_identity": api.ApiError is api_child.ApiError,
        "api_parse_reexport_identity": api.parse_request_body is api_child.parse_request_body,
        "api_json_parse_behavior": api.parse_request_body(b'{"value": 7}', "application/json") == {"value": 7},
        "api_form_parse_behavior": api.parse_request_body(b"a=1&a=2&b=x", "application/x-www-form-urlencoded") == {"a": "2", "b": "x"},
        "api_path_parts_behavior": api._path_parts("/api/a/b") == ["a", "b"],
        "dashboard_panel_reexport_identity": dashboard._development_campaign_panel is panel_child._development_campaign_panel,
        "dashboard_panel_behavior": "Supervised Development Proposals" in panel and "/api/development-campaign/proposals" in panel and "confirm" in panel,
        "dashboard_panel_static_boundary": panel_child._development_campaign_panel.__code__.co_argcount == 0,
        "release_hash_reexport_identity": maintenance._canonical_json_hash is release_child._canonical_json_hash,
        "release_manifest_validator_reexport_identity": maintenance._validate_canonical_manifest_payload is release_child._validate_canonical_manifest_payload,
        "release_hash_behavior": maintenance._canonical_json_hash({"b": 2, "a": 1}) == hashlib.sha256(b'{"a":1,"b":2}').hexdigest(),
        "release_invalid_manifest_blocks": any(row.get("status") == "blocked" for row in maintenance._validate_canonical_manifest_payload({"schema_version": "bad"})),
        "release_boundary_no_authority": all(value is False for value in release_child.AUTHORITY_FLAGS.values()),
        "api_boundary_no_authority": all(value is False for value in api_child.AUTHORITY_FLAGS.values()),
        "dashboard_boundary_no_authority": all(value is False for value in panel_child.AUTHORITY_FLAGS.values()),
        "api_dispatch_still_parent_owned": getattr(api.handle_api_get, "__module__", "") == "api_server" and getattr(api.handle_api_post, "__module__", "") == "api_server",
        "dashboard_handler_still_parent_owned": getattr(dashboard.EidolonDashboardHandler, "__module__", "") == "dashboard",
        "self_maintenance_authority_still_parent_owned": hasattr(maintenance, "build_publish_approval_policy") and maintenance.build_publish_approval_policy.__module__ == "self_maintenance",
    }
    result = {
        "contract_version": CONTRACT_VERSION,
        "ok": all(rows.values()),
        "status": "architecture_boundary_integration_ready" if all(rows.values()) else "architecture_boundary_integration_blocked",
        "checks": rows,
        "inventory_digest": inventory.get("inventory_digest"),
        "dashboard_panel_sha256": hashlib.sha256(panel.encode()).hexdigest(),
        "parent_dispatch_ownership_preserved": True,
        "read_only": True,
        **AUTHORITY_FLAGS,
    }
    result["integration_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "build_architecture_boundary_integration_report"]
