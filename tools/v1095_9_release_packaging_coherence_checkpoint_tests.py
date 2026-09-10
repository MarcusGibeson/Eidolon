from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
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


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    import release_metadata
    from package_integrity import iter_source_tree_entries, package_privacy_summary_for_zip
    from release_archive_coherence import build_candidate_archive, package_directory, verify_candidate_archive
    from release_candidate_coherence import (
        RELEASE_PACKAGING_COHERENCE_CHECKPOINT_VERSION,
        candidate_package_handoff_status,
        release_packaging_coherence_checkpoint,
    )
    from release_candidate_identity import freeze_release_candidate

    with tempfile.TemporaryDirectory(prefix="eidolon-v1095-9-") as temporary:
        base = Path(temporary)
        source = base / "Eidolon"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", "*.pyc", "*.pyo", "*.zip"))
        runtime = base / "runtime"
        frozen = freeze_release_candidate(source, runtime_root=runtime, expected_version=release_metadata.WORKING_SOURCE_VERSION)
        require(frozen.get("ok"), frozen)
        packaged = build_candidate_archive(source, runtime_root=runtime)
        require(packaged.get("ok"), packaged)
        archive = package_directory(runtime) / "archives" / str(packaged["package_filename"])
        archive_bytes = archive.read_bytes()
        source_before = snapshot(source)

        def metadata_and_contract() -> None:
            require(tuple(map(int, release_metadata.WORKING_SOURCE_VERSION.split("."))) >= (1095, 9), release_metadata.WORKING_SOURCE_VERSION)
            require(release_metadata.RUNTIME_MILESTONE.startswith(f"v{release_metadata.WORKING_SOURCE_VERSION} "), release_metadata.RUNTIME_MILESTONE)
            next_arc = release_metadata.NEXT_RECOMMENDED_ARC
            explicit_review_boundary = next_arc.startswith("Desktop Codex review of v") and " before v" in next_arc
            require(next_arc.startswith("v") or explicit_review_boundary, next_arc)
            require(RELEASE_PACKAGING_COHERENCE_CHECKPOINT_VERSION == "1", RELEASE_PACKAGING_COHERENCE_CHECKPOINT_VERSION)
            projects = json.loads((ROOT / "data" / "workspaces" / "projects.json").read_text(encoding="utf-8"))
            eidolon = next(row for row in projects.get("projects", []) if row.get("id") == "eidolon")
            require(eidolon.get("working_version") == release_metadata.WORKING_SOURCE_VERSION, eidolon.get("working_version"))

        def exact_checkpoint_is_coherent() -> None:
            result = release_packaging_coherence_checkpoint(source, runtime_root=runtime)
            require(result.get("ok") and result.get("status") == "coherent", result)
            require(result.get("candidate_id") == frozen.get("candidate_id") == packaged.get("candidate_id"), result)
            require(result.get("source_manifest_sha256") == frozen.get("source_manifest_sha256"), result)
            require(result.get("archive_manifest_sha256") == packaged.get("archive_manifest_sha256"), result)
            require(result.get("archive_sha256") == packaged.get("archive_sha256"), result)
            require(all((result.get("checks") or {}).values()), result)
            encoded = json.dumps(result, sort_keys=True)
            require(str(source) not in encoded and str(runtime) not in encoded, "checkpoint leaked private paths")

        def zip_existence_grants_no_authority() -> None:
            empty_runtime = base / "empty-runtime"
            archives = package_directory(empty_runtime) / "archives"
            archives.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archives / "Eidolon_v1095_9_candidate_fake_source_only.zip", "w") as handle:
                handle.writestr("Eidolon/README.md", "not candidate evidence")
            handoff = candidate_package_handoff_status(source, runtime_root=empty_runtime)
            checkpoint = release_packaging_coherence_checkpoint(source, runtime_root=empty_runtime)
            require(handoff.get("status") == "not_frozen", handoff)
            require((handoff.get("packaged_archive") or {}).get("status") == "not_packaged", handoff)
            require(checkpoint.get("ok") is False and checkpoint.get("status") == "attention_required", checkpoint)
            require(checkpoint.get("installation_changed") is False and checkpoint.get("promotion_changed") is False, checkpoint)

        def missing_archive_is_contradiction() -> None:
            backup = archive.with_suffix(".saved")
            archive.replace(backup)
            try:
                handoff = candidate_package_handoff_status(source, runtime_root=runtime)
                kinds = {row.get("kind") for row in handoff.get("contradictions") or []}
                require(handoff.get("status") == "attention_required", handoff)
                require("package_archive_missing" in kinds, kinds)
                checkpoint = release_packaging_coherence_checkpoint(source, runtime_root=runtime)
                require(not checkpoint.get("ok") and "package_coherent" in checkpoint.get("failed_checks", []), checkpoint)
            finally:
                backup.replace(archive)

        def unreadable_archive_is_contradiction() -> None:
            archive.write_bytes(b"not-a-zip")
            try:
                handoff = candidate_package_handoff_status(source, runtime_root=runtime)
                kinds = {row.get("kind") for row in handoff.get("contradictions") or []}
                require(handoff.get("status") == "attention_required", handoff)
                require("package_archive_unreadable" in kinds, kinds)
            finally:
                archive.write_bytes(archive_bytes)

        def stale_source_is_contradiction() -> None:
            readme = source / "README.md"
            original = readme.read_bytes()
            readme.write_bytes(original + b"\n<!-- v1095.9 stale-source fixture -->\n")
            try:
                result = release_packaging_coherence_checkpoint(source, runtime_root=runtime)
                kinds = {row.get("kind") for row in result.get("contradictions") or []}
                require(not result.get("ok") and "candidate_source_stale" in kinds, result)
                require("candidate_source_fresh" in result.get("failed_checks", []), result)
            finally:
                readme.write_bytes(original)

        def package_record_tampering_is_visible() -> None:
            record_path = package_directory(runtime) / "records" / f"{frozen['candidate_id']}.json"
            original = json.loads(record_path.read_text(encoding="utf-8"))
            broken = copy.deepcopy(original)
            broken["archive_sha256"] = "0" * 64
            write_json(record_path, broken)
            try:
                result = release_packaging_coherence_checkpoint(source, runtime_root=runtime)
                kinds = {row.get("kind") for row in result.get("contradictions") or []}
                require(not result.get("ok") and "package_record_archive_sha256_mismatch" in kinds, result)
            finally:
                write_json(record_path, original)

        def deterministic_rebuild_is_source_immutable() -> None:
            rebuilt = build_candidate_archive(source, runtime_root=runtime)
            require(rebuilt.get("ok"), rebuilt)
            require(archive.read_bytes() == archive_bytes, "deterministic rebuild changed archive bytes")
            require(snapshot(source) == source_before, "package rebuild changed source")
            require(rebuilt.get("verification_is_native_certification") is False, rebuilt)

        def fresh_extraction_reproduces_identity() -> None:
            extraction = base / "fresh"
            extraction.mkdir()
            with zipfile.ZipFile(archive, "r") as handle:
                handle.extractall(extraction)
            fresh_source = extraction / "Eidolon"
            fresh_runtime = base / "fresh-runtime"
            fresh_frozen = freeze_release_candidate(fresh_source, runtime_root=fresh_runtime, expected_version=release_metadata.WORKING_SOURCE_VERSION)
            require(fresh_frozen.get("ok"), fresh_frozen)
            require(fresh_frozen.get("candidate_id") == frozen.get("candidate_id"), (fresh_frozen, frozen))
            require(fresh_frozen.get("source_manifest_sha256") == frozen.get("source_manifest_sha256"), (fresh_frozen, frozen))
            fresh_package = build_candidate_archive(fresh_source, runtime_root=fresh_runtime)
            require(fresh_package.get("ok"), fresh_package)
            fresh_archive = package_directory(fresh_runtime) / "archives" / str(fresh_package["package_filename"])
            require(fresh_archive.read_bytes() == archive_bytes, "fresh deterministic package bytes differ")
            verified = verify_candidate_archive(fresh_source, fresh_archive, runtime_root=fresh_runtime, candidate_id=fresh_frozen["candidate_id"])
            require(verified.get("ok") and verified.get("status") == "coherent", verified)

        def authority_and_certification_remain_separate() -> None:
            absent = release_packaging_coherence_checkpoint(source, runtime_root=runtime)
            require(absent.get("installation_claimed") is False and absent.get("promotion_claimed") is False, absent)
            require(absent.get("certification_claimed") is False and absent.get("certification_performed") is False, absent)
            require(absent.get("verification_is_native_certification") is False, absent)
            declared = release_packaging_coherence_checkpoint(
                source,
                runtime_root=runtime,
                installed_version="1095.1",
                promoted_version="1095.0",
                certified_version="1094.9",
            )
            require(declared.get("ok"), declared)
            require(declared.get("installation_claimed") and declared.get("promotion_claimed") and declared.get("certification_claimed"), declared)
            require(declared.get("installation_changed") is False and declared.get("promotion_changed") is False, declared)
            require(declared.get("certification_performed") is False, declared)

        def records_and_privacy_remain_external() -> None:
            require(not (source / "data" / "release_candidates").exists(), "candidate records entered source")
            require(not (source / "data" / "candidate_packages").exists(), "package records entered source")
            source_entries = iter_source_tree_entries(source)
            require(not any("release_candidates" in row or "candidate_packages" in row for row in source_entries), "external state entered source inventory")
            privacy = package_privacy_summary_for_zip(archive)
            require(privacy.get("ok") and privacy.get("source_only"), privacy)
            require(privacy.get("forbidden_count") == 0 and privacy.get("private_content_finding_count") == 0, privacy)

        def docs_history_and_registration_are_coherent() -> None:
            history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
            require(history.count("## v1095.9 - Release and Packaging Coherence Checkpoint") == 1, "v1095.9 history missing or duplicated")
            require(history.index("## v1095.9") < history.index("## v1095.8") < history.index("## v1095.7"), "history is not newest-first")
            next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
            require(release_metadata.NEXT_RECOMMENDED_ARC in next_steps, "current next arc missing")
            explicit_review_boundary = release_metadata.NEXT_RECOMMENDED_ARC.startswith("Desktop Codex review of v") and " before v" in release_metadata.NEXT_RECOMMENDED_ARC
            require("v1150" in next_steps or explicit_review_boundary, "Desktop Codex schedule changed without an exact operator-selected review boundary")
            registration = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
            require("v1095.9-release-packaging-coherence-checkpoint" in registration, "v1095.9 suite unregistered")

        for name, fn in (
            ("v1095.9 metadata and checkpoint contract", metadata_and_contract),
            ("exact candidate package checkpoint is coherent", exact_checkpoint_is_coherent),
            ("ZIP existence grants no candidate or package authority", zip_existence_grants_no_authority),
            ("missing recorded archive is an explicit contradiction", missing_archive_is_contradiction),
            ("unreadable recorded archive is an explicit contradiction", unreadable_archive_is_contradiction),
            ("source changes stale the checkpoint", stale_source_is_contradiction),
            ("package record tampering remains visible", package_record_tampering_is_visible),
            ("deterministic rebuild preserves source and archive bytes", deterministic_rebuild_is_source_immutable),
            ("fresh extraction reproduces candidate and package identity", fresh_extraction_reproduces_identity),
            ("installation promotion certification and native certification stay separate", authority_and_certification_remain_separate),
            ("candidate package records and private state stay external", records_and_privacy_remain_external),
            ("documentation history and verification registration remain coherent", docs_history_and_registration_are_coherent),
        ):
            check(name, fn)

    passed = sum(bool(row.get("ok")) for row in RESULTS)
    report = {"version": "1095.9", "passed": passed, "failed": len(RESULTS) - passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
