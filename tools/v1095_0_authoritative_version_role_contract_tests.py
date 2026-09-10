from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

RESULTS: list[dict[str, object]] = []


def require(value: object, message: str) -> None:
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
    from version_roles import build_version_role_contract, project_version_roles
    import release_packaging

    def authority_and_aliases() -> None:
        require(tuple(map(int, release_metadata.WORKING_SOURCE_VERSION.split("."))) >= (1095, 0), release_metadata.WORKING_SOURCE_VERSION)
        require(release_metadata.RUNTIME_VERSION == release_metadata.WORKING_SOURCE_VERSION, "runtime alias drift")
        require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.WORKING_SOURCE_VERSION}", "tag drift")
        require(release_metadata.SCHEMA_VERSION == release_metadata.METADATA_SCHEMA_VERSION == "1", "schema alias drift")
        import importlib
        facade = importlib.import_module("release_metadata")
        require(facade.WORKING_SOURCE_VERSION == release_metadata.WORKING_SOURCE_VERSION, "root facade role drift")

    def roles_are_separate() -> None:
        state = build_version_role_contract(
            ROOT,
            installed_version="1094.9",
            candidate_version=release_metadata.WORKING_SOURCE_VERSION,
            packaged_archive_name=f"Eidolon_v{release_metadata.WORKING_SOURCE_VERSION.replace(chr(46), chr(95))}_candidate_source_only.zip",
        )
        require(state.get("ok"), state)
        require(state.get("installed_version") == "1094.9", "installed role lost")
        require(state.get("working_source_version") == release_metadata.WORKING_SOURCE_VERSION, "working role lost")
        require(state.get("candidate_version") == release_metadata.WORKING_SOURCE_VERSION, "candidate role lost")
        require(state.get("packaged_archive_version") == release_metadata.WORKING_SOURCE_VERSION, "package role lost")
        require(state.get("metadata_schema_version") == "1", "schema role lost")

    def source_does_not_claim_installation() -> None:
        state = build_version_role_contract(ROOT)
        require(state.get("installed_version") == "", "source invented installed version")
        require(state.get("installed_claimed_by_source") is False, "source claims install")
        require(state.get("candidate_version") == "", "source invented candidate")

    def package_uses_working_source() -> None:
        require(release_packaging._current_version() == release_metadata.WORKING_SOURCE_VERSION, "package version not authoritative source")
        require(release_packaging._package_name() == f"Eidolon_v{release_metadata.WORKING_SOURCE_VERSION.replace(chr(46), chr(95))}.zip", release_packaging._package_name())

    def schema_does_not_impersonate_release() -> None:
        settings = json.loads((ROOT / "data/settings.json").read_text(encoding="utf-8"))
        require(settings.get("settings_version") != release_metadata.RUNTIME_VERSION, "fixture no longer distinguishes roles")
        require(release_packaging._current_version() != settings.get("settings_version"), "schema named release")

    def project_roles_preserved() -> None:
        roles = project_version_roles({
            "installed_version": "1094.9",
            "working_version": "1095.0",
            "candidate_version": "1095.1",
            "root_version": "1095.0",
        })
        require(roles.get("installed_version") == "1094.9", "installed overwritten")
        require(roles.get("working_source_version") == "1095.0", "working overwritten")
        require(roles.get("candidate_version") == "1095.1", "candidate overwritten")
        require(roles.get("roles_separate"), "roles not explicit")

    def mismatch_fails_closed() -> None:
        state = build_version_role_contract(ROOT, candidate_version="9999.1", packaged_archive_name=f"Eidolon_v{release_metadata.WORKING_SOURCE_VERSION.replace(chr(46), chr(95))}.zip")
        require(not state.get("ok") and state.get("status") == "drift_detected", "mismatch accepted")
        kinds = {row.get("kind") for row in state.get("contradictions", [])}
        require("candidate_working_mismatch" in kinds and "candidate_package_mismatch" in kinds, kinds)

    for name, fn in (
        ("authoritative working-source version and compatibility aliases", authority_and_aliases),
        ("installed working candidate package historical and schema roles stay separate", roles_are_separate),
        ("source does not claim installation or candidacy", source_does_not_claim_installation),
        ("package identity uses working-source authority", package_uses_working_source),
        ("metadata schema cannot impersonate release version", schema_does_not_impersonate_release),
        ("project version roles remain distinct", project_roles_preserved),
        ("candidate and package mismatches fail closed", mismatch_fails_closed),
    ):
        check(name, fn)

    passed = sum(bool(row.get("ok")) for row in RESULTS)
    report = {"version": "1095.0", "passed": passed, "failed": len(RESULTS) - passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
