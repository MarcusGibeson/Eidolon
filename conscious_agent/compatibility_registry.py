from __future__ import annotations

"""Structured historical compatibility registry for v1250.5."""

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

CONTRACT_VERSION = "v1250.5"
REGISTRY_RELATIVE_PATH = "docs/compatibility/release_metadata_compatibility_registry.json"
LEGACY_FACADE_RELATIVE_PATH = "docs/legacy/release_metadata_v1250_2_facade.py.txt"
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
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def load_compatibility_registry(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    value = json.loads((root / REGISTRY_RELATIVE_PATH).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("compatibility_registry_must_be_object")
    return value


def compatibility_text(*, source_root: str | Path | None = None) -> str:
    registry = load_compatibility_registry(source_root=source_root)
    return " | ".join(
        str(row.get("text") or "")
        for row in registry.get("entries") or []
        if isinstance(row, Mapping)
    )


def validate_compatibility_registry(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    registry = load_compatibility_registry(source_root=root)
    rows = registry.get("entries") or []
    ordinals = [row.get("ordinal") for row in rows if isinstance(row, Mapping)]
    texts = [str(row.get("text") or "") for row in rows if isinstance(row, Mapping)]
    row_hashes_valid = all(
        row.get("sha256") == hashlib.sha256(str(row.get("text") or "").encode("utf-8")).hexdigest()
        for row in rows
        if isinstance(row, Mapping)
    )
    legacy_path = root / LEGACY_FACADE_RELATIVE_PATH
    legacy_hash = hashlib.sha256(legacy_path.read_bytes()).hexdigest() if legacy_path.is_file() else ""
    facade_text = (root / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
    active_prefix, _, payload_suffix = facade_text.partition("LEGACY_COMPATIBILITY_TEXT = '''")
    payload = payload_suffix.rsplit("'''", 1)[0] if payload_suffix else ""
    digest_payload = {key: value for key, value in registry.items() if key != "registry_digest"}
    checks = {
        "schema_current": registry.get("schema") == "eidolon.release-metadata-compatibility-registry.v1",
        "contract_current": registry.get("contract_version") == CONTRACT_VERSION,
        "entry_count_exact": registry.get("entry_count") == len(rows) and len(rows) > 300,
        "ordinals_contiguous": ordinals == list(range(1, len(rows) + 1)),
        "row_hashes_valid": row_hashes_valid,
        "registry_digest_valid": registry.get("registry_digest") == _digest(digest_payload),
        "legacy_facade_hash_bound": registry.get("source_sha256") == legacy_hash,
        "generated_payload_exact": payload == compatibility_text(source_root=root),
        "payload_not_active_prefix": all(text not in active_prefix for text in texts if text.startswith("# Compatibility marker:")),
        "historical_working_version_preserved": 'WORKING_SOURCE_VERSION = "1249.9"' in payload,
        "bundle_a_version_preserved": 'WORKING_SOURCE_VERSION = "1250.2"' in payload,
        "historical_previous_version_preserved": 'PREVIOUS_WORKING_SOURCE_VERSION = "1249.9"' in payload,
        "postponed_review_marker_preserved": "Desktop Codex review postponed" in payload,
        "migration_state_explicit": registry.get("migration_state") == "structured_registry_primary_generated_facade_retained_for_historical_tests",
        "registry_content_free": registry.get("content_free") is True,
    }
    passed = sum(bool(value) for value in checks.values())
    result = {
        "ok": passed == len(checks),
        "status": "compatibility_registry_migrated" if passed == len(checks) else "compatibility_registry_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "entry_count": len(rows),
        "category_count": len(registry.get("categories") or {}),
        "legacy_facade_sha256": legacy_hash,
        "compatibility_payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "structured_registry_primary": True,
        "generated_facade_retained": True,
        "read_only": True,
        "content_free": True,
        **AUTHORITY_FLAGS,
    }
    result["validation_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION",
    "REGISTRY_RELATIVE_PATH",
    "LEGACY_FACADE_RELATIVE_PATH",
    "AUTHORITY_FLAGS",
    "load_compatibility_registry",
    "compatibility_text",
    "validate_compatibility_registry",
]
