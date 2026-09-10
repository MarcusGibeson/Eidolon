from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

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


def main() -> int:
    import release_metadata
    from api_server import handle_api_get, handle_api_post
    from release_archive_coherence import build_candidate_archive, package_directory
    from release_candidate_identity import freeze_release_candidate, read_json
    from release_handoff_inspection import (
        handoff_directory,
        handoff_record_binding,
        handoff_runtime_binding,
        inspect_selected_candidate_archive,
        operator_selected_handoff_status,
    )
    from release_handoff_recovery import (
        CLEANUP_CONFIRMATION_PHRASE,
        HANDOFF_RECOVERY_CONTRACT_VERSION,
        build_handoff_recovery_status,
        confirm_abandoned_handoff_cleanup,
        confirm_handoff_recovery,
        confirm_handoff_replacement,
        preview_abandoned_handoff_cleanup,
        preview_handoff_recovery,
        preview_handoff_replacement,
    )

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-1-") as temporary:
        base = Path(temporary)
        source_a = base / "source-a" / "Eidolon"
        source_b = base / "source-b" / "Eidolon"
        ignore = shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", "*.pyc", "*.pyo", "*.zip")
        shutil.copytree(ROOT, source_a, ignore=ignore)
        shutil.copytree(ROOT, source_b, ignore=ignore)
        (source_b / "README.md").write_bytes((source_b / "README.md").read_bytes() + b"\n<!-- alternate coherent candidate -->\n")

        build_a = base / "build-a"
        build_b = base / "build-b"
        frozen_a = freeze_release_candidate(source_a, runtime_root=build_a, expected_version=release_metadata.WORKING_SOURCE_VERSION)
        frozen_b = freeze_release_candidate(source_b, runtime_root=build_b, expected_version=release_metadata.WORKING_SOURCE_VERSION)
        require(frozen_a.get("ok") and frozen_b.get("ok"), (frozen_a, frozen_b))
        package_a = build_candidate_archive(source_a, runtime_root=build_a)
        package_b = build_candidate_archive(source_b, runtime_root=build_b)
        require(package_a.get("ok") and package_b.get("ok"), (package_a, package_b))
        archive_a = package_directory(build_a) / "archives" / str(package_a["package_filename"])
        archive_b = package_directory(build_b) / "archives" / str(package_b["package_filename"])
        root_before = snapshot(ROOT)

        def metadata_and_registration_contract() -> None:
            require(tuple(int(x) for x in release_metadata.WORKING_SOURCE_VERSION.split(".")) >= (1096, 1), release_metadata.WORKING_SOURCE_VERSION)
            require(release_metadata.RUNTIME_MILESTONE.startswith(f"v{release_metadata.WORKING_SOURCE_VERSION} "), release_metadata.RUNTIME_MILESTONE)
            next_arc = release_metadata.NEXT_RECOMMENDED_ARC
            explicit_review_boundary = next_arc.startswith("Desktop Codex review of v") and " before v" in next_arc
            require(next_arc.startswith("v") or explicit_review_boundary, next_arc)
            require(HANDOFF_RECOVERY_CONTRACT_VERSION == "1", HANDOFF_RECOVERY_CONTRACT_VERSION)
            projects = json.loads((ROOT / "data" / "workspaces" / "projects.json").read_text(encoding="utf-8"))
            project = next(row for row in projects["projects"] if row.get("id") == "eidolon")
            require(project.get("working_version") == release_metadata.WORKING_SOURCE_VERSION, project)
            require("generation_bound_external_handoff_recovery" in project.get("capabilities", []), project.get("capabilities"))
            post_review = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
            release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
            require("v1096.1-handoff-recovery-replacement-hardening" in post_review, "suite missing from post-review verification")
            require("v1096.1-handoff-recovery-replacement-hardening" in release_verify, "suite missing from release verification")

        def active_record_is_generation_and_runtime_bound() -> None:
            runtime = base / "binding-runtime"
            result = inspect_selected_candidate_archive(archive_a, runtime_root=runtime)
            require(result.get("ok") and result.get("record_generation") == 1, result)
            directory = handoff_directory(runtime)
            pointer = read_json(directory / "active_handoff.json")
            record = read_json(directory / "records" / f"{pointer['inspection_id']}.json")
            require(pointer.get("runtime_root_binding") == handoff_runtime_binding(runtime), pointer)
            require(record.get("runtime_root_binding") == handoff_runtime_binding(runtime), record)
            require(record.get("record_binding_sha256") == handoff_record_binding(record), record)
            require(pointer.get("record_binding_sha256") == record.get("record_binding_sha256"), (pointer, record))
            public = operator_selected_handoff_status(runtime_root=runtime)
            encoded = json.dumps(public)
            require(str(archive_a.parent) not in encoded and "extractions/" not in encoded, public)
            require(public.get("private_paths_returned") is False and public.get("content_free") is True, public)

        def different_archive_requires_preview_and_preserves_active() -> None:
            runtime = base / "direct-replacement-runtime"
            first = inspect_selected_candidate_archive(archive_a, runtime_root=runtime)
            require(first.get("ok"), first)
            blocked = inspect_selected_candidate_archive(archive_b, runtime_root=runtime)
            require(not blocked.get("ok") and blocked.get("status") == "replacement_preview_required", blocked)
            current = operator_selected_handoff_status(runtime_root=runtime)
            require(current.get("candidate_id") == frozen_a.get("candidate_id"), current)
            require(current.get("record_generation") == 1, current)

        def explicit_replacement_preview_and_confirmation() -> None:
            runtime = base / "replacement-runtime"
            first = inspect_selected_candidate_archive(archive_a, runtime_root=runtime)
            require(first.get("ok"), first)
            preview = preview_handoff_replacement(archive_b, runtime_root=runtime)
            require(preview.get("ok") and preview.get("status") == "replacement_confirmation_required", preview)
            require(preview.get("old_archive_sha256") == package_a.get("archive_sha256"), preview)
            require(preview.get("new_archive_sha256") == package_b.get("archive_sha256"), preview)
            require(preview.get("candidate_id") == frozen_b.get("candidate_id"), preview)
            truthy = confirm_handoff_replacement(preview_token=preview["preview_token"], operator_confirmed="true", runtime_root=runtime)  # type: ignore[arg-type]
            require(not truthy.get("ok") and truthy.get("status") == "literal_confirmation_required", truthy)
            applied = confirm_handoff_replacement(preview_token=preview["preview_token"], operator_confirmed=True, runtime_root=runtime)
            require(applied.get("ok") and applied.get("status") == "handoff_replaced", applied)
            require(applied.get("record_generation") == 2 and applied.get("candidate_id") == frozen_b.get("candidate_id"), applied)
            reused = confirm_handoff_replacement(preview_token=preview["preview_token"], operator_confirmed=True, runtime_root=runtime)
            require(not reused.get("ok") and reused.get("stale_confirmation") is True, reused)

        def failed_or_interrupted_replacement_preserves_active() -> None:
            runtime = base / "failed-replacement-runtime"
            first = inspect_selected_candidate_archive(archive_a, runtime_root=runtime)
            require(first.get("ok"), first)
            malformed = base / "malformed-replacement.zip"
            malformed.write_bytes(b"not a zip")
            failed = preview_handoff_replacement(malformed, runtime_root=runtime)
            require(not failed.get("ok") and failed.get("active_preserved") is True, failed)
            current = operator_selected_handoff_status(runtime_root=runtime)
            require(current.get("ok") and current.get("candidate_id") == frozen_a.get("candidate_id"), current)
            try:
                preview_handoff_replacement(
                    archive_b,
                    runtime_root=runtime,
                    fault_hook=lambda stage: (_ for _ in ()).throw(RuntimeError("interrupted")) if stage == "after_replacement_inspection" else None,
                )
            except RuntimeError:
                pass
            else:
                raise AssertionError("replacement interruption hook did not fire")
            current = operator_selected_handoff_status(runtime_root=runtime)
            require(current.get("ok") and current.get("candidate_id") == frozen_a.get("candidate_id"), current)

        def stale_cross_runtime_cross_record_and_mismatched_tokens_fail() -> None:
            runtime = base / "stale-token-runtime"
            other_runtime = base / "other-token-runtime"
            require(inspect_selected_candidate_archive(archive_a, runtime_root=runtime).get("ok"), "initial inspect failed")
            require(inspect_selected_candidate_archive(archive_a, runtime_root=other_runtime).get("ok"), "other inspect failed")
            preview = preview_handoff_replacement(archive_b, runtime_root=runtime)
            require(preview.get("ok"), preview)
            cross = confirm_handoff_replacement(preview_token=preview["preview_token"], operator_confirmed=True, runtime_root=other_runtime)
            require(not cross.get("ok") and cross.get("stale_confirmation") is True, cross)
            mismatch = confirm_handoff_replacement(preview_token="0" * 64, operator_confirmed=True, runtime_root=runtime)
            require(not mismatch.get("ok") and mismatch.get("stale_confirmation") is True, mismatch)
            # Refreshing the same exact archive advances the active generation and stales the preview.
            refreshed = inspect_selected_candidate_archive(archive_a, runtime_root=runtime)
            require(refreshed.get("ok") and refreshed.get("record_generation") == 2, refreshed)
            stale = confirm_handoff_replacement(preview_token=preview["preview_token"], operator_confirmed=True, runtime_root=runtime)
            require(not stale.get("ok") and stale.get("stale_confirmation") is True, stale)

        def missing_and_malformed_records_are_detected_and_recoverable() -> None:
            for label, mutate in (
                ("missing", lambda path: path.unlink()),
                ("malformed", lambda path: path.write_text("{broken", encoding="utf-8")),
            ):
                runtime = base / f"{label}-record-runtime"
                first = inspect_selected_candidate_archive(archive_a, runtime_root=runtime)
                require(first.get("ok"), first)
                directory = handoff_directory(runtime)
                pointer = read_json(directory / "active_handoff.json")
                mutate(directory / "records" / f"{pointer['inspection_id']}.json")
                status = build_handoff_recovery_status(runtime_root=runtime)
                require(not status.get("ok") and status.get("recovery_required") is True, status)
                require(status.get("recovery_available") is True, status)
                preview = preview_handoff_recovery(runtime_root=runtime)
                require(preview.get("ok") and preview.get("status") == "recovery_confirmation_required", preview)
                applied = confirm_handoff_recovery(preview_token=preview["preview_token"], operator_confirmed=True, runtime_root=runtime)
                require(applied.get("ok") and applied.get("status") == "handoff_recovered", applied)
                final = operator_selected_handoff_status(runtime_root=runtime)
                require(final.get("ok") and final.get("candidate_id") == frozen_a.get("candidate_id"), final)

        def stale_or_missing_extraction_is_recovered_only_from_exact_archive() -> None:
            runtime = base / "stale-extraction-runtime"
            first = inspect_selected_candidate_archive(archive_a, runtime_root=runtime)
            require(first.get("ok"), first)
            directory = handoff_directory(runtime)
            pointer = read_json(directory / "active_handoff.json")
            extracted = Path(pointer["extracted_root_path"])
            (extracted / "README.md").write_bytes((extracted / "README.md").read_bytes() + b"\nstale\n")
            status = operator_selected_handoff_status(runtime_root=runtime)
            kinds = {row.get("kind") for row in status.get("contradictions", [])}
            require(not status.get("ok") and "candidate_source_stale" in kinds, status)
            preview = preview_handoff_recovery(runtime_root=runtime)
            require(preview.get("ok"), preview)
            applied = confirm_handoff_recovery(preview_token=preview["preview_token"], operator_confirmed=True, runtime_root=runtime)
            require(applied.get("ok"), applied)
            final = operator_selected_handoff_status(runtime_root=runtime)
            require(final.get("ok") and final.get("candidate_fresh"), final)

        def archive_change_rejects_recovery_and_replacement() -> None:
            selected_a = base / archive_a.name
            selected_a.write_bytes(archive_a.read_bytes())
            runtime = base / "changed-archive-runtime"
            first = inspect_selected_candidate_archive(selected_a, runtime_root=runtime)
            require(first.get("ok"), first)
            selected_a.write_bytes(selected_a.read_bytes() + b"changed")
            recovery = preview_handoff_recovery(runtime_root=runtime)
            require(not recovery.get("ok") and recovery.get("status") == "explicit_archive_selection_required", recovery)

            runtime2 = base / "changed-replacement-runtime"
            require(inspect_selected_candidate_archive(archive_a, runtime_root=runtime2).get("ok"), "initial inspect failed")
            selected_b = base / archive_b.name
            selected_b.write_bytes(archive_b.read_bytes())
            preview = preview_handoff_replacement(selected_b, runtime_root=runtime2)
            require(preview.get("ok"), preview)
            selected_b.write_bytes(selected_b.read_bytes() + b"changed")
            applied = confirm_handoff_replacement(preview_token=preview["preview_token"], operator_confirmed=True, runtime_root=runtime2)
            require(not applied.get("ok") and applied.get("status") == "replacement_candidate_changed", applied)
            active = operator_selected_handoff_status(runtime_root=runtime2)
            require(active.get("ok") and active.get("candidate_id") == frozen_a.get("candidate_id"), active)

        def cleanup_is_preview_bound_exact_root_and_literal_confirmed() -> None:
            runtime = base / "cleanup-runtime"
            first = inspect_selected_candidate_archive(archive_a, runtime_root=runtime)
            require(first.get("ok"), first)
            directory = handoff_directory(runtime)
            orphan = directory / "extractions" / "abandoned-fixture"
            orphan.mkdir(parents=True)
            (orphan / "temporary.txt").write_text("abandoned", encoding="utf-8")
            outside = base / "outside-artifact"
            outside.mkdir()
            (outside / "keep.txt").write_text("keep", encoding="utf-8")
            preview = preview_abandoned_handoff_cleanup(runtime_root=runtime)
            require(preview.get("ok") and preview.get("artifact_count") == 1, preview)
            wrong_bool = confirm_abandoned_handoff_cleanup(
                preview_token=preview["preview_token"], operator_confirmed="true", confirmation_phrase=CLEANUP_CONFIRMATION_PHRASE, runtime_root=runtime  # type: ignore[arg-type]
            )
            require(not wrong_bool.get("ok") and wrong_bool.get("status") == "literal_confirmation_required", wrong_bool)
            wrong_phrase = confirm_abandoned_handoff_cleanup(
                preview_token=preview["preview_token"], operator_confirmed=True, confirmation_phrase="remove them", runtime_root=runtime
            )
            require(not wrong_phrase.get("ok") and wrong_phrase.get("status") == "literal_confirmation_required", wrong_phrase)
            applied = confirm_abandoned_handoff_cleanup(
                preview_token=preview["preview_token"], operator_confirmed=True, confirmation_phrase=CLEANUP_CONFIRMATION_PHRASE, runtime_root=runtime
            )
            require(applied.get("ok") and applied.get("removed_count") == 1, applied)
            require(not orphan.exists() and outside.is_dir(), (orphan.exists(), outside.exists()))
            require(operator_selected_handoff_status(runtime_root=runtime).get("ok"), "active handoff was removed")

        def api_and_dashboard_surfaces_are_post_bounded_and_path_suppressed() -> None:
            runtime = base / "api-runtime"
            old = os.environ.get("EIDOLON_DATA_DIR")
            os.environ["EIDOLON_DATA_DIR"] = str(runtime)
            try:
                status_code, initial = handle_api_post("/api/release-handoff/inspect", {"archive_path": str(archive_a)})
                require(status_code == 200 and initial.get("ok"), initial)
                code, replacement = handle_api_post("/api/release-handoff/replacement/preview", {"archive_path": str(archive_b)})
                require(code == 200 and replacement.get("ok"), replacement)
                code, status = handle_api_get("/api/release-handoff/status")
                require(code == 200 and status.get("ok"), status)
                encoded = json.dumps((initial, replacement, status))
                require(str(archive_a.parent) not in encoded and "extractions/" not in encoded, encoded)
                api_source = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
                dashboard_source = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
                for route in (
                    "/api/release-handoff/recovery/preview", "/api/release-handoff/recovery/apply",
                    "/api/release-handoff/replacement/preview", "/api/release-handoff/replacement/apply",
                    "/api/release-handoff/cleanup/preview", "/api/release-handoff/cleanup/apply",
                ):
                    require(route in api_source and route in dashboard_source, route)
            finally:
                if old is None:
                    os.environ.pop("EIDOLON_DATA_DIR", None)
                else:
                    os.environ["EIDOLON_DATA_DIR"] = old

        def authority_and_source_boundaries_remain_unchanged() -> None:
            runtime = base / "authority-runtime"
            registry = base / "operator" / "data" / "projects.json"
            registry.parent.mkdir(parents=True)
            registry.write_text('{"operator":"unchanged"}\n', encoding="utf-8")
            before = registry.read_bytes()
            require(inspect_selected_candidate_archive(archive_a, runtime_root=runtime).get("ok"), "initial inspection failed")
            preview = preview_handoff_replacement(archive_b, runtime_root=runtime)
            require(preview.get("ok"), preview)
            applied = confirm_handoff_replacement(preview_token=preview["preview_token"], operator_confirmed=True, runtime_root=runtime)
            require(applied.get("ok"), applied)
            for key in ("installed", "promoted", "certified", "project_registry_changed", "provider_contacted"):
                require(applied.get(key) in {False, None}, (key, applied.get(key)))
            require(registry.read_bytes() == before, "operator registry changed")
            require(snapshot(ROOT) == root_before, "source tree changed during external runtime tests")

        def documentation_is_newest_first_and_next_arc_is_bounded() -> None:
            history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
            require(history.count("## v1096.1 - Operator-Selected Handoff Recovery and Replacement Hardening") == 1, "v1096.1 history missing or duplicated")
            require(history.index("## v1096.1") < history.index("## v1096.0"), "release history not newest-first")
            next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
            require(release_metadata.NEXT_RECOMMENDED_ARC in next_steps, next_steps[:500])
            require("v1150" in next_steps, "Desktop Codex schedule changed")
            authority_docs = "\n".join(
                [
                    (ROOT / "README.md").read_text(encoding="utf-8"),
                    (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md").read_text(encoding="utf-8"),
                    next_steps,
                ]
            )
            require(all(term in authority_docs.lower() for term in ("installation", "promotion", "certification")), "release authority roles missing")
            require("separate" in authority_docs.lower() or "scope-separated" in authority_docs.lower(), "release authority separation missing")

        for name, fn in (
            ("v1096.1 metadata and verification registration contract", metadata_and_registration_contract),
            ("active handoff records are generation and runtime-root bound", active_record_is_generation_and_runtime_bound),
            ("direct selection of a different archive requires replacement preview", different_archive_requires_preview_and_preserves_active),
            ("explicit replacement preview confirmation and token burnout", explicit_replacement_preview_and_confirmation),
            ("failed or interrupted replacement preserves the coherent active handoff", failed_or_interrupted_replacement_preserves_active),
            ("stale cross-runtime cross-record and mismatched tokens fail closed", stale_cross_runtime_cross_record_and_mismatched_tokens_fail),
            ("missing and malformed records are detected and recoverable", missing_and_malformed_records_are_detected_and_recoverable),
            ("stale or missing extraction is recovered only from the exact archive", stale_or_missing_extraction_is_recovered_only_from_exact_archive),
            ("archive changes reject recovery and replacement", archive_change_rejects_recovery_and_replacement),
            ("abandoned cleanup is exact-root preview-bound and literal-confirmed", cleanup_is_preview_bound_exact_root_and_literal_confirmed),
            ("API and dashboard handoff surfaces are POST-bounded and path-suppressed", api_and_dashboard_surfaces_are_post_bounded_and_path_suppressed),
            ("installation promotion certification provider and source boundaries remain unchanged", authority_and_source_boundaries_remain_unchanged),
            ("documentation is newest-first and next arc remains bounded", documentation_is_newest_first_and_next_arc_is_bounded),
        ):
            check(name, fn)

    passed = sum(bool(row.get("ok")) for row in RESULTS)
    report = {"version": "1096.1", "passed": passed, "failed": len(RESULTS) - passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
