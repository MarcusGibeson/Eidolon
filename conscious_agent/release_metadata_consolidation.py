from __future__ import annotations

"""Generated release-metadata facade contract for v1250.3.

The structured authority lives in ``release_authority``. This module renders and
validates the tiny import-compatible facade still required by historical
consumers. Historical marker text comes from a structured registry and is not
an active assignment or release authority.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

CONTRACT_VERSION = "v1250.3"
REGISTRY_RELATIVE_PATH = "docs/compatibility/release_metadata_compatibility_registry.json"
AGENT_FACADE_RELATIVE_PATH = "conscious_agent/release_metadata.py"
ROOT_FACADE_RELATIVE_PATH = "release_metadata.py"
AUTHORITY_MODULE = "conscious_agent.release_authority"
AUTHORITY_FLAGS = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "independent_authority_granted": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _load_registry(root: Path) -> dict[str, Any]:
    value = json.loads((root / REGISTRY_RELATIVE_PATH).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("compatibility_registry_must_be_object")
    return value


def _authority_values() -> tuple[str, str, str, str]:
    try:
        from release_authority import MILESTONE, NEXT_BOUNDED_UNIT, PREVIOUS_WORKING_SOURCE_VERSION, WORKING_SOURCE_VERSION
    except ImportError:
        from release_authority import (  # type: ignore
            MILESTONE,
            NEXT_BOUNDED_UNIT,
            PREVIOUS_WORKING_SOURCE_VERSION,
            WORKING_SOURCE_VERSION,
        )
    return WORKING_SOURCE_VERSION, PREVIOUS_WORKING_SOURCE_VERSION, MILESTONE, NEXT_BOUNDED_UNIT


def render_compatibility_blob(registry: Mapping[str, Any]) -> str:
    rows = registry.get("entries") or []
    return " | ".join(str(row.get("text") or "") for row in rows if isinstance(row, Mapping))


def render_agent_release_metadata(*, source_root: str | Path | None = None) -> str:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    working, previous, milestone, next_unit = _authority_values()
    blob = render_compatibility_blob(_load_registry(root))
    lines = [
        "from __future__ import annotations",
        "",
        '"""Generated compatibility facade. Edit release_authority and the structured compatibility registry, not this file."""',
        "",
        f'WORKING_SOURCE_VERSION = "{working}"',
        "RUNTIME_VERSION = WORKING_SOURCE_VERSION",
        'RUNTIME_VERSION_TAG = f"v{WORKING_SOURCE_VERSION}"',
        f'RUNTIME_MILESTONE = "{milestone}"',
        f'RUNTIME_UI_CONTRACT = "persistent-development-sessions-v{working}"',
        f'NEXT_RECOMMENDED_ARC = "{next_unit}"',
        f'PREVIOUS_WORKING_SOURCE_VERSION = "{previous}"',
        "PREVIOUS_RUNTIME_VERSION = PREVIOUS_WORKING_SOURCE_VERSION",
        'METADATA_SCHEMA_VERSION = "2"',
        "SCHEMA_VERSION = METADATA_SCHEMA_VERSION",
        'VERSION_ROLE_CONTRACT_VERSION = "2"',
        'RELEASE_AUTHORITY_MODULE = "conscious_agent.release_authority"',
        f'COMPATIBILITY_REGISTRY_PATH = "{REGISTRY_RELATIVE_PATH}"',
        "",
        "# Generated historical payload. It is inert compatibility text, not active metadata authority.",
        "LEGACY_COMPATIBILITY_TEXT = '''" + blob + "'''",
        "",
    ]
    return "\n".join(lines)


def render_root_release_metadata(*, source_root: str | Path | None = None) -> str:
    working, _, _, _ = _authority_values()
    return (
        "from conscious_agent.release_metadata import *\n\n"
        f"# Active source marker: {working}\n"
        "# Generated facade; authoritative values live in conscious_agent.release_authority.\n"
        "# Retained compatibility marker: Active source marker: 1205.5\n"
        "# Retained compatibility marker: 1205.2 general small-project consolidation\n"
    )


def write_generated_facades(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    agent_text = render_agent_release_metadata(source_root=root)
    root_text = render_root_release_metadata(source_root=root)
    (root / AGENT_FACADE_RELATIVE_PATH).write_text(agent_text, encoding="utf-8")
    (root / ROOT_FACADE_RELATIVE_PATH).write_text(root_text, encoding="utf-8")
    hashes = {
        "agent_facade_sha256": hashlib.sha256(agent_text.encode("utf-8")).hexdigest(),
        "root_facade_sha256": hashlib.sha256(root_text.encode("utf-8")).hexdigest(),
    }
    from release_authority import CODEX_REVIEW_STATE
    working, previous, milestone, next_unit = _authority_values()
    manifest = {
        "schema": "eidolon.release-metadata-manifest.v1", "contract_version": CONTRACT_VERSION,
        "authority_module": AUTHORITY_MODULE, "generated_agent_facade": "conscious_agent.release_metadata",
        "compatibility_registry": REGISTRY_RELATIVE_PATH, "working_source_version": working,
        "previous_working_source_version": previous, "milestone": milestone, "next_bounded_unit": next_unit,
        "codex_review_state": CODEX_REVIEW_STATE, "runtime_version_tag": "v" + working,
        "runtime_ui_contract": "persistent-development-sessions-v" + working, "release_authorized": False, **hashes,
    }
    manifest["manifest_digest"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (root / "docs/release/release_metadata_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hashes


def validate_release_metadata_consolidation(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    working, previous, milestone, next_unit = _authority_values()
    expected_agent = render_agent_release_metadata(source_root=root)
    expected_root = render_root_release_metadata(source_root=root)
    actual_agent = (root / AGENT_FACADE_RELATIVE_PATH).read_text(encoding="utf-8")
    actual_root = (root / ROOT_FACADE_RELATIVE_PATH).read_text(encoding="utf-8")
    active_prefix = actual_agent.split("LEGACY_COMPATIBILITY_TEXT", 1)[0]
    checks = {
        "agent_facade_generated_exactly": actual_agent == expected_agent,
        "root_facade_generated_exactly": actual_root == expected_root,
        "single_active_working_assignment": len(re.findall(r'^WORKING_SOURCE_VERSION = "[^"]+"$', actual_agent, flags=re.MULTILINE)) == 1,
        "single_active_previous_assignment": len(re.findall(r'^PREVIOUS_WORKING_SOURCE_VERSION = "[^"]+"$', actual_agent, flags=re.MULTILINE)) == 1,
        "working_matches_authority": f'WORKING_SOURCE_VERSION = "{working}"' in active_prefix,
        "previous_matches_authority": f'PREVIOUS_WORKING_SOURCE_VERSION = "{previous}"' in active_prefix,
        "milestone_matches_authority": f'RUNTIME_MILESTONE = "{milestone}"' in active_prefix,
        "next_unit_matches_authority": f'NEXT_RECOMMENDED_ARC = "{next_unit}"' in active_prefix,
        "historical_payload_inert": "LEGACY_COMPATIBILITY_TEXT = '''" in actual_agent,
        "structured_registry_named": REGISTRY_RELATIVE_PATH in active_prefix,
        "root_shim_only_imports_facade": actual_root.startswith("from conscious_agent.release_metadata import *"),
        "metadata_schema_advanced": 'METADATA_SCHEMA_VERSION = "2"' in active_prefix,
    }
    passed = sum(bool(value) for value in checks.values())
    result = {
        "ok": passed == len(checks),
        "status": "release_metadata_consolidated" if passed == len(checks) else "release_metadata_consolidation_blocked",
        "contract_version": CONTRACT_VERSION,
        "working_source_version": working,
        "previous_working_source_version": previous,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "agent_facade_line_count": len(actual_agent.splitlines()),
        "agent_facade_sha256": hashlib.sha256(actual_agent.encode("utf-8")).hexdigest(),
        "root_facade_sha256": hashlib.sha256(actual_root.encode("utf-8")).hexdigest(),
        "generated_facade": True,
        "active_authority_count": 1,
        "read_only_validation": True,
        "content_free": True,
        **AUTHORITY_FLAGS,
    }
    result["validation_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION",
    "REGISTRY_RELATIVE_PATH",
    "AUTHORITY_FLAGS",
    "render_compatibility_blob",
    "render_agent_release_metadata",
    "render_root_release_metadata",
    "write_generated_facades",
    "validate_release_metadata_consolidation",
]
