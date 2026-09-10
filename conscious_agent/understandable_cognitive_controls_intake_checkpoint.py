from __future__ import annotations

"""Strictly read-only v1146.2 Understandable Cognitive Controls intake checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from understandable_cognitive_control_definitions import AUTHORITY_BOUNDARY, CONTROL_DOMAINS, SAFE_DEFAULTS, build_understandable_cognitive_control_definitions
from understandable_cognitive_control_configuration import build_cognitive_control_configuration_inspection

CONTRACT_VERSION = "v1146.2"


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix not in {".pyc", ".pyo"} and "__pycache__" not in p.parts):
            stat = path.stat(); digest.update(path.relative_to(root).as_posix().encode()); digest.update(str(stat.st_size).encode()); digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()


def build_understandable_cognitive_controls_intake_checkpoint(runtime_root: Path | str | None = None, *, source_root: Path | str | None = None) -> dict[str, Any]:
    runtime = Path(runtime_root).resolve() if runtime_root else (Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").resolve() / "cognition")
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    rb, sb = _tree_signature(runtime), _tree_signature(source)
    definitions = build_understandable_cognitive_control_definitions()
    configurations = build_cognitive_control_configuration_inspection(runtime)
    rows = definitions.get("definitions") or []
    records = configurations.get("recent_records") or []
    checks = [
        ("definition_contract", definitions.get("contract_version") == "v1146.0"),
        ("configuration_contract", configurations.get("contract_version") == "v1146.1"),
        ("complete_control_domains", tuple(definitions.get("control_domains") or []) == CONTROL_DOMAINS),
        ("exact_owner_scope", all(row.get("owner") and row.get("scope") and row.get("control_id") for row in rows)),
        ("safe_defaults_complete", set(SAFE_DEFAULTS) == set(CONTROL_DOMAINS)),
        ("safe_defaults_bounded", all(0 <= float(value.get("intensity", -1)) <= 1 for value in SAFE_DEFAULTS.values())),
        ("preview_only_definitions", definitions.get("preview_only") and not definitions.get("mutation_available")),
        ("durable_exact_lineage", all(row.get("configuration_id") and int(row.get("revision") or 0) > 0 and row.get("structural_digest") for row in records)),
        ("prior_lineage_visible", all("prior_configuration_id" in row and "prior_structural_digest" in row for row in records)),
        ("configuration_not_applied", all(row.get("state") == "preview_only" and not row.get("applied") and not row.get("active") for row in records)),
        ("explicit_confirmation_required", all(row.get("requires_explicit_confirmation") for row in records) if records else True),
        ("attention_control_bounded", SAFE_DEFAULTS["attention"]["mode"] == "bounded"),
        ("thought_activity_control_bounded", SAFE_DEFAULTS["thought_activity"]["mode"] == "bounded"),
        ("initiative_control_restrained", SAFE_DEFAULTS["initiative"]["mode"] == "suggest_only"),
        ("privacy_control_strict", SAFE_DEFAULTS["privacy"]["mode"] == "strict"),
        ("resource_control_conservative", SAFE_DEFAULTS["resource_use"]["mode"] == "conservative"),
        ("development_control_disabled", SAFE_DEFAULTS["development_proposals"]["mode"] == "disabled"),
        ("no_apply_authority", not configurations.get("apply_authority_available")),
        ("no_mutation_route", not configurations.get("mutation_route_available")),
        ("authority_separation", all(value is False for value in AUTHORITY_BOUNDARY.values())),
        ("content_free", all(row.get("content_free") for row in rows)),
        ("privacy_boundary", not any(any(key in row for key in ("text", "content", "prompt", "message", "reasoning", "provider_payload")) for row in rows + records)),
        ("source_runtime_separation", str(runtime) != str(source) and source not in runtime.parents),
        ("desktop_verification_pending", True),
    ]
    ra, sa = _tree_signature(runtime), _tree_signature(source)
    checks.extend([("runtime_read_only", rb == ra), ("source_read_only", sb == sa)])
    passed = sum(1 for _, ok in checks if ok)
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": passed == len(checks),
        "passed": passed,
        "total": len(checks),
        "checks": [{"name": name, "passed": bool(ok)} for name, ok in checks],
        "summary": {"control_domain_count": len(rows), "configuration_preview_count": configurations.get("record_count", 0), "safe_default_count": len(SAFE_DEFAULTS)},
        "definitions": definitions,
        "configuration_inspection": configurations,
        "read_only": True,
        "post_available": False,
        "desktop_verification": "pending",
        "authority_boundary": AUTHORITY_BOUNDARY,
    }
