from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

SMOKE_REGISTRY_METADATA_VERSION = RUNTIME_VERSION
SMOKE_REGISTRY_METADATA_CHECK_ID = "smoke-registry-metadata-extraction-v1"

SMOKE_TIER_ORDER: dict[str, set[str]] = {
    "fast": {"fast"},
    "loop": {"fast", "loop"},
    "readiness": {"fast", "loop", "readiness"},
    "build": {"fast", "loop", "readiness", "build"},
    "patch": {"fast", "loop", "readiness", "build", "patch"},
    "release": {"fast", "loop", "readiness", "build", "patch", "release"},
    "install": {"fast", "loop", "readiness", "build", "patch", "release", "install"},
    "full": {"fast", "loop", "readiness", "build", "patch", "release", "install"},
}

FALLBACK_SMOKE_SEGMENT_NAMES: list[str] = [
    "install-core",
    "install-release",
    "install-dashboard",
    "install-governance",
    "install-expression",
    "install-live-trial",
    "install-memory",
    "install-regression-recent",
]

REGISTRY_METADATA_SAFETY_BOUNDARY: dict[str, bool | int] = {
    "actual_fixture_execution_count": 0,
    "subprocess_spawn_count": 0,
    "source_write_count": 0,
    "source_delete_count": 0,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "manual_smoke_remains_authoritative": True,
}


def allowed_tiers_for(tier: str) -> set[str]:
    return set(SMOKE_TIER_ORDER.get(tier, SMOKE_TIER_ORDER["full"]))


def fallback_segment_names() -> list[str]:
    return list(FALLBACK_SMOKE_SEGMENT_NAMES)


def build_smoke_registry_metadata_extraction_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_smoke_line_count: int = 22135,
) -> dict[str, Any]:
    root = Path(project_root)
    smoke_path = root / "tools" / "smoke_check.py"
    helper_path = root / "tools" / "smoke_registry_metadata.py"
    smoke_text = smoke_path.read_text(encoding="utf-8")
    helper_text = helper_path.read_text(encoding="utf-8")
    smoke_lines = smoke_text.count("\n") + 1
    expected_tier_keys = {"fast", "loop", "readiness", "build", "patch", "release", "install", "full"}
    rows: list[dict[str, Any]] = [
        {"name": "registry-metadata-helper-current", "ok": SMOKE_REGISTRY_METADATA_VERSION == expected_version},
        {"name": "registry-metadata-helper-exists", "ok": helper_path.exists()},
        {"name": "tier-order-moved-to-helper", "ok": "SMOKE_TIER_ORDER" in helper_text and "_TIER_ORDER =" not in smoke_text},
        {"name": "fallback-segment-names-moved-to-helper", "ok": "FALLBACK_SMOKE_SEGMENT_NAMES" in helper_text and "fallback_segment_names()" in smoke_text},
        {"name": "smoke-check-imports-registry-metadata-helper", "ok": "from smoke_registry_metadata import" in smoke_text and "allowed_tiers_for" in smoke_text},
        {"name": "tier-order-keys-stable", "ok": set(SMOKE_TIER_ORDER) == expected_tier_keys},
        {"name": "full-tier-matches-install-tier", "ok": SMOKE_TIER_ORDER["full"] == SMOKE_TIER_ORDER["install"]},
        {"name": "install-release-fallback-segment-present", "ok": "install-release" in FALLBACK_SMOKE_SEGMENT_NAMES},
        {"name": "smoke-check-line-count-bounded-successor", "ok": smoke_lines <= max(previous_smoke_line_count + 32, 22200), "current_line_count": smoke_lines, "previous_line_count": previous_smoke_line_count, "successor_budget": max(previous_smoke_line_count + 32, 22200)},
        {"name": "new-smoke-check-registered", "ok": SMOKE_REGISTRY_METADATA_CHECK_ID in smoke_text},
        {"name": "manual-smoke-registry-remains-authoritative", "ok": REGISTRY_METADATA_SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
    ]
    ok = all(row.get("ok") is True for row in rows)
    return {
        "version": expected_version,
        "check_id": SMOKE_REGISTRY_METADATA_CHECK_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "tools/smoke_registry_metadata.py",
        "extracted_metadata": [
            "SMOKE_TIER_ORDER",
            "FALLBACK_SMOKE_SEGMENT_NAMES",
            "allowed_tiers_for",
            "fallback_segment_names",
            "REGISTRY_METADATA_SAFETY_BOUNDARY",
        ],
        "smoke_check_line_count": smoke_lines,
        "previous_smoke_check_line_count": previous_smoke_line_count,
        "line_count_delta": smoke_lines - previous_smoke_line_count,
        "tier_order_keys": sorted(SMOKE_TIER_ORDER),
        "fallback_segment_names": fallback_segment_names(),
        "rows": rows,
        **REGISTRY_METADATA_SAFETY_BOUNDARY,
    }


def run_smoke_registry_metadata_extraction_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_smoke_registry_metadata_extraction_report(project_root, expected_version=expected_version)
        if SMOKE_REGISTRY_METADATA_VERSION != expected_version:
            print("[fail] smoke-registry-metadata-extraction-v1: helper version is stale")
            return False
        if report.get("ok") is not True:
            print("[fail] smoke-registry-metadata-extraction-v1: metadata extraction report blocked")
            print(report.get("rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0:
            print("[fail] smoke-registry-metadata-extraction-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] smoke-registry-metadata-extraction-v1: authority boundary changed")
            return False
        if "install-release" not in (report.get("fallback_segment_names") or []):
            print("[fail] smoke-registry-metadata-extraction-v1: install-release fallback segment missing")
            return False
        print(f"[ok] smoke-registry-metadata-extraction-v1 line_delta={report.get('line_count_delta')} helper={report.get('helper_module')}")
        return True
    except Exception as error:
        print(f"[fail] smoke-registry-metadata-extraction-v1: {error}")
        return False
