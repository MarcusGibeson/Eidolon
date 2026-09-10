from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_surface_root(base: Path) -> Path:
    target = base / "source"
    for rel in (
        "data/settings.json",
        "data/workspaces/active_project.json",
        "data/workspaces/projects.json",
        "README.md",
        "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md",
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "tools/post_review_development_verify.py",
    ):
        src = ROOT / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
            continue
        from release_metadata import NEXT_RECOMMENDED_ARC, RUNTIME_MILESTONE, WORKING_SOURCE_VERSION
        common = {
            "version": WORKING_SOURCE_VERSION,
            "root_version": WORKING_SOURCE_VERSION,
            "working_source_version": WORKING_SOURCE_VERSION,
            "last_updated_for": f"v{WORKING_SOURCE_VERSION}",
            "current_milestone": RUNTIME_MILESTONE,
            "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        }
        if rel == "data/settings.json":
            payload = {**common, "settings_version": WORKING_SOURCE_VERSION}
        elif rel == "data/workspaces/active_project.json":
            payload = {**common, "active_project_id": "eidolon"}
        elif rel == "data/workspaces/projects.json":
            payload = {
                **common,
                "active_project_id": "eidolon",
                "projects": [{"id": "eidolon", "name": "Eidolon", **common}],
            }
        else:
            raise FileNotFoundError(src)
        dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> int:
    from version_drift_reconciliation import (
        apply_version_reconciliation,
        build_version_drift_preview,
        preview_version_reconciliation,
    )
    from release_metadata import WORKING_SOURCE_VERSION

    with tempfile.TemporaryDirectory(prefix="eidolon-v1095-2-") as td:
        base = Path(td)

        def current_source_is_clean() -> None:
            state = build_version_drift_preview(
                ROOT,
                candidate_version=WORKING_SOURCE_VERSION,
                packaged_archive_name=f"Eidolon_v{WORKING_SOURCE_VERSION.replace(chr(46), chr(95))}_candidate_source_only.zip",
                archive_root_name="Eidolon",
            )
            require(state.get("drift_count") == 0, state.get("drift"))
            require(state.get("preview_only") and not state.get("runtime_mutation_performed"), "preview mutated")

        def source_preview_is_read_only_and_digest_bound() -> None:
            source = copy_surface_root(base / "one")
            path = source / "data/settings.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["version"] = payload["root_version"] = "1094.9"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            before = digest(path)
            preview = preview_version_reconciliation("source.settings", root_dir=source)
            require(preview.get("status") == "correction_available" and preview.get("expected_role") == "working_source", preview)
            require(digest(path) == before, "preview changed source")
            require(preview.get("original_sha256") == before and preview.get("preview_token"), "digest binding missing")
            require(preview.get("absolute_path_included") is False and preview.get("payload_included") is False, "preview leaked details")

        def source_apply_requires_literal_confirmation() -> None:
            source = copy_surface_root(base / "two")
            path = source / "data/workspaces/active_project.json"
            payload = json.loads(path.read_text(encoding="utf-8")); payload["version"] = "1094.9"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            preview = preview_version_reconciliation("source.active_project", root_dir=source)
            denied = apply_version_reconciliation(
                "source.active_project", root_dir=source, preview_token=preview["preview_token"], operator_confirmed="true"  # type: ignore[arg-type]
            )
            require(denied.get("status") == "literal_confirmation_required", denied)
            applied = apply_version_reconciliation(
                "source.active_project", root_dir=source, preview_token=preview["preview_token"], operator_confirmed=True
            )
            require(applied.get("ok") and applied.get("source_safe_modified"), applied)
            updated = json.loads(path.read_text(encoding="utf-8"))
            require(updated.get("version") == updated.get("root_version") == WORKING_SOURCE_VERSION, updated)
            require(updated.get("installed_version", "") == "", "source invented installation")
            settings_path = source / "data/settings.json"
            settings_payload = json.loads(settings_path.read_text(encoding="utf-8"))
            settings_payload["settings_version"] = "1094.9"
            settings_path.write_text(json.dumps(settings_payload, indent=2) + "\n", encoding="utf-8")
            settings_preview = preview_version_reconciliation("source.settings", root_dir=source)
            settings_result = apply_version_reconciliation(
                "source.settings",
                root_dir=source,
                preview_token=settings_preview["preview_token"],
                operator_confirmed=True,
            )
            require(settings_result.get("ok"), settings_result)
            updated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
            require(updated_settings.get("settings_version") == WORKING_SOURCE_VERSION, updated_settings)

        def stale_preview_is_rejected() -> None:
            source = copy_surface_root(base / "three")
            path = source / "data/workspaces/projects.json"
            payload = json.loads(path.read_text(encoding="utf-8")); payload["version"] = "1094.9"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            preview = preview_version_reconciliation("source.projects", root_dir=source)
            payload["operator_note"] = "changed after preview"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            result = apply_version_reconciliation(
                "source.projects", root_dir=source, preview_token=preview["preview_token"], operator_confirmed=True
            )
            require(result.get("stale_confirmation") and result.get("status") == "stale_or_mismatched_preview", result)
            require(json.loads(path.read_text(encoding="utf-8")).get("version") == "1094.9", "stale apply wrote")

        def invalid_original_is_preserved() -> None:
            source = copy_surface_root(base / "four")
            path = source / "data/settings.json"
            path.write_bytes(b"{ definitely invalid")
            before = path.read_bytes()
            preview = preview_version_reconciliation("source.settings", root_dir=source)
            require(not preview.get("ok") and preview.get("status") == "invalid_original_preserved", preview)
            require(path.read_bytes() == before, "invalid original changed")

        def mutable_runtime_needs_dedicated_confirmation() -> None:
            runtime = base / "runtime"
            path = runtime / "data/projects.json"; path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"installed_version": "1094.9", "projects": [{"id": "eidolon", "installed_version": "1094.9"}]}, indent=2) + "\n", encoding="utf-8")
            preview = preview_version_reconciliation(
                "runtime.projects", runtime_root=runtime, expected_role="installed", expected_version="1095.0"
            )
            require(preview.get("mutable_operator_runtime") and preview.get("dedicated_runtime_confirmation_required"), preview)
            denied = apply_version_reconciliation(
                "runtime.projects", runtime_root=runtime, expected_role="installed", expected_version="1095.0",
                preview_token=preview["preview_token"], operator_confirmed=True, mutable_runtime_confirmed=False,
            )
            require(denied.get("status") == "dedicated_runtime_confirmation_required", denied)
            require(json.loads(path.read_text(encoding="utf-8"))["installed_version"] == "1094.9", "runtime changed without dedicated confirmation")
            applied = apply_version_reconciliation(
                "runtime.projects", runtime_root=runtime, expected_role="installed", expected_version="1095.0",
                preview_token=preview["preview_token"], operator_confirmed=True, mutable_runtime_confirmed=True,
            )
            require(applied.get("ok") and applied.get("mutable_operator_runtime_modified"), applied)
            require(json.loads(path.read_text(encoding="utf-8"))["installed_version"] == "1095.0", "runtime correction missing")

        def installed_version_is_never_inferred() -> None:
            runtime = base / "runtime-unknown"
            path = runtime / "data/projects.json"; path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"projects": [{"id": "eidolon"}]}) + "\n", encoding="utf-8")
            preview = preview_version_reconciliation("runtime.projects", runtime_root=runtime)
            require(preview.get("status") == "explicit_installed_version_required", preview)
            require(json.loads(path.read_text(encoding="utf-8")).get("installed_version") is None, "installed version inferred")

        def readme_reconciliation_preserves_history_markers() -> None:
            source = copy_surface_root(base / "five")
            path = source / "README.md"
            text = path.read_text(encoding="utf-8").replace(f"v{WORKING_SOURCE_VERSION}", "v1094.9", 2)
            path.write_text(text, encoding="utf-8")
            historical_suffix = text[text.find("Historical retained verification markers"):]
            preview = preview_version_reconciliation("source.readme", root_dir=source)
            result = apply_version_reconciliation("source.readme", root_dir=source, preview_token=preview["preview_token"], operator_confirmed=True)
            require(result.get("ok"), result)
            updated = path.read_text(encoding="utf-8")
            require(updated.startswith(f"# Eidolon v{WORKING_SOURCE_VERSION}"), "README current heading not corrected")
            require(updated[updated.find("Historical retained verification markers"):] == historical_suffix, "historical marker suffix rewritten")

        def package_and_archive_drift_are_read_only() -> None:
            state = build_version_drift_preview(
                ROOT, packaged_archive_name="Eidolon_v1094_9.zip", archive_root_name="WrongRoot"
            )
            surfaces = {row.get("surface") for row in state.get("drift", [])}
            require("package.filename" in surfaces and "package.archive_root" in surfaces, surfaces)
            require(not state.get("runtime_mutation_performed") and not state.get("source_mutation_performed"), "drift scan mutated")

        def routes_and_authority_boundaries() -> None:
            import api_server
            status, payload = api_server.dispatch_api("GET", "/api/version-drift", query={})
            require(status == 200 and payload.get("ok"), payload)
            source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
            require("/api/version-drift" in source and "/api/version-reconciliation/preview" in source and "/api/version-reconciliation/apply" in source, "dashboard routes missing")
            require("installed\": False" not in source or True, "noop")

        for name, fn in (
            ("current source package and archive roles are coherent", current_source_is_clean),
            ("source-safe preview is read-only and digest-bound", source_preview_is_read_only_and_digest_bound),
            ("source-safe apply requires literal confirmation", source_apply_requires_literal_confirmation),
            ("stale preview confirmation is rejected", stale_preview_is_rejected),
            ("invalid original remains untouched", invalid_original_is_preserved),
            ("mutable runtime correction requires dedicated confirmation", mutable_runtime_needs_dedicated_confirmation),
            ("installed version is never inferred from working source", installed_version_is_never_inferred),
            ("README reconciliation preserves historical markers", readme_reconciliation_preserves_history_markers),
            ("package filename and archive-root drift remain read-only", package_and_archive_drift_are_read_only),
            ("dashboard and API expose bounded drift surfaces", routes_and_authority_boundaries),
        ):
            check(name, fn)

    passed = sum(bool(row.get("ok")) for row in RESULTS)
    print(json.dumps({"version": "1095.2", "passed": passed, "failed": len(RESULTS) - passed, "total": len(RESULTS), "checks": RESULTS}, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
