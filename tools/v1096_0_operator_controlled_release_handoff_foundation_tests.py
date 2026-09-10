from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

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


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def write_zip(path: Path, entries: list[tuple[zipfile.ZipInfo | str, bytes]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)


def rewrite_zip(source: Path, destination: Path, mutate) -> None:
    with zipfile.ZipFile(source, "r") as original:
        rows = [(copy.copy(info), original.read(info)) for info in original.infolist() if not info.is_dir()]
    changed = mutate(rows)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info, payload in changed:
            target.writestr(info, payload)


def main() -> int:
    import release_metadata
    from package_integrity import iter_source_tree_entries, package_privacy_summary_for_zip
    from release_archive_coherence import build_candidate_archive, package_directory
    from release_candidate_identity import candidate_directory, freeze_release_candidate
    from release_handoff_inspection import (
        HANDOFF_INSPECTION_CONTRACT_VERSION,
        handoff_directory,
        inspect_selected_candidate_archive,
        operator_selected_handoff_status,
    )

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-0-") as temporary:
        base = Path(temporary)
        source = base / "Eidolon"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", "*.pyc", "*.pyo", "*.zip"))
        build_runtime = base / "build-runtime"
        frozen = freeze_release_candidate(source, runtime_root=build_runtime, expected_version=release_metadata.WORKING_SOURCE_VERSION)
        require(frozen.get("ok"), frozen)
        packaged = build_candidate_archive(source, runtime_root=build_runtime)
        require(packaged.get("ok"), packaged)
        archive = package_directory(build_runtime) / "archives" / str(packaged["package_filename"])
        archive_bytes = archive.read_bytes()
        source_before = snapshot(source)

        def metadata_and_contract() -> None:
            require(tuple(map(int, release_metadata.WORKING_SOURCE_VERSION.split("."))) >= (1096, 0), release_metadata.WORKING_SOURCE_VERSION)
            require(release_metadata.RUNTIME_MILESTONE.startswith(f"v{release_metadata.WORKING_SOURCE_VERSION} "), release_metadata.RUNTIME_MILESTONE)
            next_arc = release_metadata.NEXT_RECOMMENDED_ARC
            explicit_review_boundary = next_arc.startswith("Desktop Codex review of v") and " before v" in next_arc
            require(next_arc.startswith("v") or explicit_review_boundary, next_arc)
            require(HANDOFF_INSPECTION_CONTRACT_VERSION == "1", HANDOFF_INSPECTION_CONTRACT_VERSION)
            projects = json.loads((ROOT / "data" / "workspaces" / "projects.json").read_text(encoding="utf-8"))
            eidolon = next(row for row in projects["projects"] if row.get("id") == "eidolon")
            require(eidolon.get("working_version") == release_metadata.WORKING_SOURCE_VERSION, eidolon.get("working_version"))
            require("operator_selected_external_candidate_handoff_inspection" in eidolon.get("capabilities", []), eidolon.get("capabilities"))

        def explicit_selection_only_and_exact_archive() -> None:
            runtime = base / "selection-runtime"
            sibling = archive.with_name("Eidolon_v9999_9_candidate_fake_source_only.zip")
            sibling.write_bytes(b"not a candidate")
            try:
                try:
                    inspect_selected_candidate_archive("", runtime_root=runtime)
                except ValueError as error:
                    require("archive_path is required" in str(error), error)
                else:
                    raise AssertionError("blank selection was accepted")
                result = inspect_selected_candidate_archive(archive, runtime_root=runtime)
                require(result.get("ok") and result.get("status") == "coherent_preview", result)
                require(result.get("archive_selected_explicitly") is True, result)
                require(result.get("directory_scan_performed") is False and result.get("automatic_selection_performed") is False, result)
                require(result.get("package_filename") == archive.name, result)
                require(result.get("candidate_id") == frozen.get("candidate_id"), (result, frozen))
            finally:
                sibling.unlink(missing_ok=True)

        def reconstructed_identity_and_manifest_are_exact() -> None:
            runtime = base / "identity-runtime"
            result = inspect_selected_candidate_archive(archive, runtime_root=runtime)
            require(result.get("ok"), result)
            require(result.get("candidate_id") == frozen.get("candidate_id") == packaged.get("candidate_id"), result)
            require(result.get("source_manifest_sha256") == frozen.get("source_manifest_sha256"), result)
            require(result.get("archive_manifest_sha256") == packaged.get("archive_manifest_sha256"), result)
            require(result.get("archive_sha256") == packaged.get("archive_sha256"), result)
            require(result.get("archive_root") == "Eidolon" and result.get("packaged_version") == release_metadata.WORKING_SOURCE_VERSION, result)
            require(result.get("candidate_fresh") and result.get("package_coherent") and result.get("source_only"), result)

        def private_paths_are_external_and_public_summary_is_content_free() -> None:
            runtime = base / "path-runtime"
            result = inspect_selected_candidate_archive(archive, runtime_root=runtime)
            encoded = json.dumps(result, sort_keys=True)
            require(str(base) not in encoded and str(archive) not in encoded, encoded)
            require(result.get("archive_path_suppressed") is True, result)
            records = list((handoff_directory(runtime) / "records").glob("*.json"))
            require(len(records) == 1, records)
            private = json.loads(records[0].read_text(encoding="utf-8"))
            require(private.get("selected_archive_path") == str(archive.absolute()), private)
            require(Path(str(private.get("extracted_root_path"))).is_dir(), private)
            require(not (source / "data" / "release_handoffs").exists(), "handoff state entered source")
            entries = iter_source_tree_entries(source)
            require(not any("release_handoffs" in entry for entry in entries), "handoff state entered source inventory")

        def dashboard_and_api_selection_surfaces_are_bounded() -> None:
            runtime = base / "api-runtime"
            previous = os.environ.get("EIDOLON_DATA_DIR")
            os.environ["EIDOLON_DATA_DIR"] = str(runtime)
            try:
                import api_server
                code, payload = api_server.dispatch_api("POST", "/api/release-handoff/inspect", body={"archive_path": str(archive)})
                require(code == 200 and payload.get("ok"), payload)
                data = payload.get("data") or {}
                require(data.get("ok") and data.get("archive_path_suppressed"), data)
                require(str(archive) not in json.dumps(data), data)
                code, payload = api_server.dispatch_api("GET", "/api/release-handoff/status", query={})
                require(code == 200 and (payload.get("data") or {}).get("status") == "coherent_preview", payload)
                code, payload = api_server.dispatch_api("GET", "/api/release-handoff/inspect", query={})
                require(code == 404 and payload.get("ok") is False, payload)

                import dashboard
                from http.server import ThreadingHTTPServer
                server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.EidolonDashboardHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    status_url = f"http://127.0.0.1:{server.server_port}/api/release-handoff/status"
                    with urlopen(status_url, timeout=20) as response:
                        body = json.loads(response.read().decode("utf-8"))
                        require(response.status == 200 and body.get("status") == "coherent_preview", body)
                        require(str(archive) not in json.dumps(body), body)
                    inspect_url = f"http://127.0.0.1:{server.server_port}/api/release-handoff/inspect"
                    request = Request(
                        inspect_url,
                        data=json.dumps({"archive_path": str(archive)}).encode("utf-8"),
                        method="POST",
                        headers={"Content-Type": "application/json"},
                    )
                    with urlopen(request, timeout=30) as response:
                        body = json.loads(response.read().decode("utf-8"))
                        require(response.status == 200 and (body.get("data") or body).get("ok"), body)
                finally:
                    server.shutdown(); server.server_close(); thread.join(timeout=10)
            finally:
                if previous is None:
                    os.environ.pop("EIDOLON_DATA_DIR", None)
                else:
                    os.environ["EIDOLON_DATA_DIR"] = previous

        def missing_unreadable_and_malformed_archives_fail_closed() -> None:
            missing = inspect_selected_candidate_archive(base / "missing.zip", runtime_root=base / "missing-runtime")
            require(not missing.get("ok") and missing.get("status") == "archive_missing", missing)
            directory = base / "not-file.zip"; directory.mkdir()
            unreadable = inspect_selected_candidate_archive(directory, runtime_root=base / "unreadable-runtime")
            require(not unreadable.get("ok") and unreadable.get("status") == "archive_unreadable", unreadable)
            malformed_path = base / "malformed.zip"; malformed_path.write_bytes(b"not a zip")
            malformed = inspect_selected_candidate_archive(malformed_path, runtime_root=base / "malformed-runtime")
            require(not malformed.get("ok") and malformed.get("status") == "archive_unreadable", malformed)

        def unsafe_archive_structures_and_private_state_are_rejected() -> None:
            fixtures: list[tuple[str, list[tuple[zipfile.ZipInfo | str, bytes]], str]] = []
            fixtures.append(("multi-root.zip", [("Eidolon/README.md", b"a"), ("Other/README.md", b"b")], "archive_root_mismatch"))
            fixtures.append(("traversal.zip", [("Eidolon/../escape.txt", b"x")], "traversal_path"))
            fixtures.append(("nested.zip", [("Eidolon/nested.zip", b"x")], "nested_archive"))
            fixtures.append(("bytecode.zip", [("Eidolon/a.pyc", b"x")], "bytecode_entry"))
            fixtures.append(("credential.zip", [("Eidolon/.env", b"TOKEN=x")], "credential_entry"))
            fixtures.append(("backup.zip", [("Eidolon/private.backup", b"x")], "private_backup"))
            fixtures.append(("runtime.zip", [("Eidolon/data/tasks.json", b"{}")], "source_only_privacy_failure"))
            symlink = zipfile.ZipInfo("Eidolon/link")
            symlink.create_system = 3
            symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
            fixtures.append(("symlink.zip", [(symlink, b"target")], "symlink_entry"))
            for filename, entries, expected in fixtures:
                path = base / "unsafe" / filename
                write_zip(path, entries)
                result = inspect_selected_candidate_archive(path, runtime_root=base / "unsafe-runtime" / filename)
                kinds = {row.get("kind") for row in result.get("contradictions", []) + result.get("structure_findings", [])}
                require(not result.get("ok") and expected in kinds, (filename, expected, result))

        def duplicate_entries_are_rejected() -> None:
            path = base / "duplicate.zip"
            with zipfile.ZipFile(path, "w") as target:
                target.writestr("Eidolon/README.md", b"first")
                target.writestr("Eidolon/README.md", b"second")
            result = inspect_selected_candidate_archive(path, runtime_root=base / "duplicate-runtime")
            kinds = {row.get("kind") for row in result.get("structure_findings", [])}
            require(not result.get("ok") and "duplicate_entry" in kinds, result)

        def filename_metadata_and_archive_tampering_are_visible() -> None:
            wrong_name = archive.with_name("Eidolon_v1096_0_candidate_wrong_source_only.zip")
            wrong_name.write_bytes(archive_bytes)
            try:
                result = inspect_selected_candidate_archive(wrong_name, runtime_root=base / "filename-runtime")
                kinds = {row.get("kind") for row in result.get("contradictions", [])}
                require(not result.get("ok") and "archive_filename_identity_mismatch" in kinds, result)
            finally:
                wrong_name.unlink(missing_ok=True)

            metadata_tampered = base / "tampered" / archive.name
            def mutate_metadata(rows):
                output = []
                for info, payload in rows:
                    if info.filename == "Eidolon/data/settings.json":
                        value = json.loads(payload.decode("utf-8")); value["working_source_version"] = "1095.9"
                        payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
                    output.append((info, payload))
                return output
            rewrite_zip(archive, metadata_tampered, mutate_metadata)
            result = inspect_selected_candidate_archive(metadata_tampered, runtime_root=base / "metadata-runtime")
            kinds = {row.get("kind") for row in result.get("contradictions", [])}
            require(not result.get("ok") and "settings_metadata_version_mismatch" in kinds, result)
            require("archive_filename_identity_mismatch" in kinds, result)

        def stale_extraction_and_changed_archive_digest_are_detected() -> None:
            selected = base / "status" / archive.name
            selected.parent.mkdir(parents=True)
            selected.write_bytes(archive_bytes)
            runtime = base / "status-runtime"
            result = inspect_selected_candidate_archive(selected, runtime_root=runtime)
            require(result.get("ok"), result)
            record_path = next((handoff_directory(runtime) / "records").glob("*.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            extracted_readme = Path(record["extracted_root_path"]) / "README.md"
            extracted_readme.write_bytes(extracted_readme.read_bytes() + b"\n<!-- stale inspection -->\n")
            stale = operator_selected_handoff_status(runtime_root=runtime)
            kinds = {row.get("kind") for row in stale.get("contradictions", [])}
            require(not stale.get("ok") and "candidate_source_stale" in kinds, stale)

            # Reinspect cleanly, then alter the selected archive bytes after the record is complete.
            selected.write_bytes(archive_bytes)
            result = inspect_selected_candidate_archive(selected, runtime_root=runtime)
            require(result.get("ok"), result)
            selected.write_bytes(archive_bytes + b"changed")
            changed = operator_selected_handoff_status(runtime_root=runtime)
            kinds = {row.get("kind") for row in changed.get("contradictions", [])}
            require(not changed.get("ok") and "selected_archive_digest_changed" in kinds, changed)

        def inspection_never_claims_or_performs_authority_actions() -> None:
            operator_registry = base / "operator" / "data" / "projects.json"
            operator_registry.parent.mkdir(parents=True)
            operator_registry.write_text('{"operator":"unchanged"}\n', encoding="utf-8")
            before = operator_registry.read_bytes()
            result = inspect_selected_candidate_archive(archive, runtime_root=base / "authority-runtime")
            require(result.get("ok"), result)
            for key in ("installed", "promoted", "certified", "installation_changed", "promotion_changed", "certification_performed", "project_registry_changed", "operator_project_root_modified", "verification_is_native_certification"):
                require(result.get(key) is False, (key, result.get(key)))
            require(operator_registry.read_bytes() == before, "operator registry changed")
            require(snapshot(source) == source_before, "source changed during inspection")

        def deterministic_rebuild_and_privacy_remain_coherent() -> None:
            rebuilt = build_candidate_archive(source, runtime_root=build_runtime)
            require(rebuilt.get("ok"), rebuilt)
            require(archive.read_bytes() == archive_bytes, "deterministic rebuild changed archive")
            privacy = package_privacy_summary_for_zip(archive)
            require(privacy.get("ok") and privacy.get("source_only"), privacy)
            require(privacy.get("forbidden_count") == 0 and privacy.get("private_content_finding_count") == 0, privacy)
            require(not (source / "data" / "release_candidates").exists(), "candidate records entered source")
            require(not (source / "data" / "candidate_packages").exists(), "package records entered source")
            require(not (source / "data" / "release_handoffs").exists(), "handoff records entered source")
            require(candidate_directory(build_runtime).is_dir(), "candidate runtime record missing")

        def documentation_and_verification_registration_are_coherent() -> None:
            history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
            require(history.count("## v1096.0 - Operator-Controlled Release Handoff Foundation") == 1, "v1096.0 history missing or duplicated")
            require(history.index("## v1096.1") < history.index("## v1096.0") < history.index("## v1095.9"), "history is not newest-first")
            next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
            require(release_metadata.NEXT_RECOMMENDED_ARC in next_steps, "current next arc missing")
            require("v1150" in next_steps, "Desktop Codex review schedule changed")
            registration = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
            require("v1096.0-operator-controlled-release-handoff-foundation" in registration, "v1096.0 suite unregistered")
            release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
            require("v1096.0-operator-controlled-release-handoff-foundation" in release_verify, "v1096.0 release verification unregistered")

        for name, fn in (
            ("v1096.0 metadata and handoff inspection contract", metadata_and_contract),
            ("archive selection is explicit and exact with no scanning", explicit_selection_only_and_exact_archive),
            ("candidate identity and manifests are reconstructed from extracted source", reconstructed_identity_and_manifest_are_exact),
            ("private archive and extraction paths remain only in external records", private_paths_are_external_and_public_summary_is_content_free),
            ("dashboard and standalone API handoff surfaces remain bounded", dashboard_and_api_selection_surfaces_are_bounded),
            ("missing unreadable and malformed archives fail closed", missing_unreadable_and_malformed_archives_fail_closed),
            ("unsafe archive structures private state and credentials are rejected", unsafe_archive_structures_and_private_state_are_rejected),
            ("duplicate archive entries are rejected", duplicate_entries_are_rejected),
            ("filename metadata manifest identity and tampering contradictions remain visible", filename_metadata_and_archive_tampering_are_visible),
            ("stale extracted candidates and changed archive digests are detected", stale_extraction_and_changed_archive_digest_are_detected),
            ("inspection never installs promotes certifies or mutates operator registries", inspection_never_claims_or_performs_authority_actions),
            ("deterministic package privacy and source-only exclusions remain coherent", deterministic_rebuild_and_privacy_remain_coherent),
            ("documentation history and verification registration remain coherent", documentation_and_verification_registration_are_coherent),
        ):
            check(name, fn)

    passed = sum(bool(row.get("ok")) for row in RESULTS)
    report = {"version": "1096.0", "passed": passed, "failed": len(RESULTS) - passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
