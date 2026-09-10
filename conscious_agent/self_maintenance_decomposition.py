from __future__ import annotations

"""Structural validation for the v1250.6 self-maintenance decomposition."""

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "v1250.6"
BASELINE_PARENT_LINE_COUNT = 46910
EXTRACTED_NAMES = (
    "_is_hex_sha256",
    "_canonical_bytes",
    "_source_json_sanitized",
    "_read_signature_json",
    "_pem_body_bytes",
    "_der_len",
    "_der_tlv",
    "_der_integer",
    "_parse_rsa_public_key_from_der",
    "_load_public_rsa_key",
    "_mgf1",
    "_rsa_pss_sha256_verify",
    "_load_public_trust_root_config",
    "_trusted_fingerprints",
    "_signature_sidecar_validation_rows",
    "_signature_failure_codes",
    "_normalized_signature_trust_result",
    "_verify_signature_payload_fixture",
)
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


def _top_level_definitions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def validate_self_maintenance_decomposition(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    parent_path = root / "conscious_agent/self_maintenance.py"
    child_path = root / "conscious_agent/release_signature_primitives.py"
    parent = parent_path.read_text(encoding="utf-8") if parent_path.is_file() else ""
    child = child_path.read_text(encoding="utf-8") if child_path.is_file() else ""
    parent_defs = _top_level_definitions(parent) if parent else set()
    child_defs = _top_level_definitions(child) if child else set()
    parent_lines = len(parent.splitlines())
    child_lines = len(child.splitlines())
    checks = {
        "primitive_module_present": child_path.is_file(),
        "primitive_contract_current": 'CONTRACT_VERSION = "v1250.6"' in child,
        "parent_imports_primitives": "from release_signature_primitives import (" in parent,
        "moved_definitions_absent_from_parent": not (set(EXTRACTED_NAMES) & parent_defs),
        "moved_definitions_present_in_child": set(EXTRACTED_NAMES).issubset(child_defs),
        "parent_reduced": parent_lines < BASELINE_PARENT_LINE_COUNT - 150,
        "bounded_extraction": 300 <= child_lines <= 500,
        "no_private_key_fixture": "BEGIN PRIVATE KEY" not in child,
        "public_key_only_fixture": "BEGIN PUBLIC KEY" in child,
        "no_signing_action": "private_key_material_allowed" in child and "release_authorized" not in child,
        "parent_surface_preserved": all(name in parent for name in EXTRACTED_NAMES),
    }
    passed = sum(bool(value) for value in checks.values())
    result: dict[str, Any] = {
        "ok": passed == len(checks),
        "status": "self_maintenance_decomposed" if passed == len(checks) else "self_maintenance_decomposition_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "parent_line_count": parent_lines,
        "baseline_parent_line_count": BASELINE_PARENT_LINE_COUNT,
        "extracted_line_count": child_lines,
        "extracted_name_count": len(EXTRACTED_NAMES),
        "read_only": True,
        "content_free": True,
        **AUTHORITY_FLAGS,
    }
    result["validation_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "EXTRACTED_NAMES", "AUTHORITY_FLAGS", "validate_self_maintenance_decomposition"]
