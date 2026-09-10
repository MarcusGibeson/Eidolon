from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

RESULTS: list[dict[str, object]] = []


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def check(name: str, fn) -> None:
    try:
        fn()
        RESULTS.append({"name": name, "ok": True})
    except Exception as exc:
        RESULTS.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


def main() -> int:
    import release_metadata
    from version_resolution import build_cross_surface_version_resolution

    def source_surfaces_align() -> None:
        state = build_cross_surface_version_resolution(ROOT)
        require(state.get("working_source_version") == release_metadata.WORKING_SOURCE_VERSION, state)
        require(state.get("drift_count") == 0, state.get("drift"))
        require(state.get("installed") is False and state.get("certified") is False, "authority overclaim")

    def dashboard_health_roles() -> None:
        import dashboard
        state = dashboard.dashboard_health_payload()
        require(state.get("working_source_version") == release_metadata.WORKING_SOURCE_VERSION, state)
        require(state.get("installed_version") == "" and state.get("candidate_version") == "", "dashboard invented state")
        require(state.get("installed") is False and state.get("certified") is False, "dashboard overclaim")

    def api_routes() -> None:
        import api_server
        status, payload = api_server.dispatch_api("GET", "/api/version-roles", query={})
        require(status == 200 and payload.get("ok"), payload)
        data = payload.get("data") or {}
        require(data.get("working_source_version") == release_metadata.WORKING_SOURCE_VERSION, "API role drift")
        status, payload = api_server.dispatch_api("GET", "/api/version-resolution", query={})
        require(status == 200 and (payload.get("data") or {}).get("drift_count") == 0, payload)

    def dashboard_routes_registered() -> None:
        source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
        require('/api/version-roles' in source and '/api/version-resolution' in source, "dashboard routes missing")
        require("build_cross_surface_version_resolution" in source, "dashboard does not use resolver")

    def conversation_omits_irrelevant_versions() -> None:
        import project_manager
        ordinary = project_manager.project_context_text(limit_items=1, include_version_roles=False)
        admin = project_manager.project_context_text(limit_items=1, include_version_roles=True)
        require(
            "Installed version:" not in ordinary
            and "Candidate version:" not in ordinary
            and "Working source version:" not in ordinary,
            "ordinary context polluted",
        )
        require(f"Working source version: {release_metadata.WORKING_SOURCE_VERSION}" in admin, "admin roles missing")
        runtime_source = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
        require("project_context_text(include_version_roles=False)" in runtime_source, "conversation runtime still injects release roles")

    def development_inventory_roles() -> None:
        from version_metadata_inventory import build_version_metadata_inventory
        report = build_version_metadata_inventory(ROOT)
        roles = report.get("version_roles") or {}
        require(roles.get("working_source_version") == release_metadata.WORKING_SOURCE_VERSION, roles)
        require(report.get("installed_version_claimed") is False, "inventory claims install")

    def package_report_not_installation() -> None:
        import release_packaging
        report = release_packaging.build_release_manifest_integrity(
            package_name=f"Eidolon_v{release_metadata.WORKING_SOURCE_VERSION.replace(chr(46), chr(95))}_candidate_source_only.zip", save=False
        )
        require(report.get("working_source_version") == release_metadata.WORKING_SOURCE_VERSION, report)
        require(report.get("installed") is False and report.get("certified") is False, "package overclaim")
        require((report.get("version_roles") or {}).get("candidate_version") == release_metadata.WORKING_SOURCE_VERSION, "candidate role missing")

    def explicit_mismatch_visible() -> None:
        state = build_cross_surface_version_resolution(
            ROOT, candidate_version="9999.2", packaged_archive_name=f"Eidolon_v{release_metadata.WORKING_SOURCE_VERSION.replace(chr(46), chr(95))}.zip"
        )
        require(not state.get("ok") and state.get("status") == "drift_detected", "explicit mismatch hidden")
        require(state.get("installed") is False, "mismatch invented installation")

    for name, fn in (
        ("current source surfaces resolve through working-source role", source_surfaces_align),
        ("dashboard health reports explicit roles without install claim", dashboard_health_roles),
        ("standalone API exposes version roles and resolution", api_routes),
        ("dashboard registers read-only version routes", dashboard_routes_registered),
        ("ordinary conversation omits irrelevant release metadata", conversation_omits_irrelevant_versions),
        ("development inventory includes version-role contract", development_inventory_roles),
        ("package reporting distinguishes candidate from installation", package_report_not_installation),
        ("explicit cross-role mismatch remains visible", explicit_mismatch_visible),
    ):
        check(name, fn)

    passed = sum(bool(row.get("ok")) for row in RESULTS)
    print(json.dumps({"version": "1095.1", "passed": passed, "failed": len(RESULTS) - passed, "total": len(RESULTS), "checks": RESULTS}, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
