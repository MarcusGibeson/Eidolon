from __future__ import annotations

import hashlib
import json
import shutil
import stat
import sys
import tempfile
from pathlib import Path
import warnings
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


def source_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def rewrite_archive(source: Path, target: Path, transform) -> None:
    with zipfile.ZipFile(source, "r") as original, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for info in original.infolist():
            if info.is_dir():
                continue
            name, payload = transform(info.filename, original.read(info))
            if name is None:
                continue
            new_info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            new_info.compress_type = zipfile.ZIP_DEFLATED
            new_info.create_system = 3
            new_info.external_attr = (stat.S_IFREG | 0o644) << 16
            output.writestr(new_info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    import release_metadata
    from release_archive_coherence import build_candidate_archive, verify_candidate_archive
    from release_candidate_identity import freeze_release_candidate

    with tempfile.TemporaryDirectory(prefix="eidolon-v1095-7-") as tmp:
        temp = Path(tmp)
        source = temp / "Eidolon"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", "*.pyc", "*.pyo", "*.zip"))
        runtime = temp / "runtime"
        frozen = freeze_release_candidate(source, runtime_root=runtime)
        require(frozen.get("ok"), frozen)
        built = build_candidate_archive(source, runtime_root=runtime)
        require(built.get("ok"), built)
        archive = runtime / "candidate_packages" / "archives" / str(built["package_filename"])
        initial_source_snapshot = source_snapshot(source)
        initial_archive_bytes = archive.read_bytes()

        def metadata_authority() -> None:
            require(tuple(map(int, release_metadata.WORKING_SOURCE_VERSION.split("."))) >= (1095, 7), release_metadata.WORKING_SOURCE_VERSION)
            import release_archive_coherence
            require(release_archive_coherence.ARCHIVE_COHERENCE_CONTRACT_VERSION == "1", "archive contract missing")

        def deterministic_coherent_package() -> None:
            second = build_candidate_archive(source, runtime_root=runtime)
            require(second.get("ok"), second)
            require(archive.read_bytes() == initial_archive_bytes, "archive bytes are not deterministic")
            require(second.get("archive_sha256") == hashlib.sha256(initial_archive_bytes).hexdigest(), second)
            require(second.get("candidate_id") == frozen.get("candidate_id"), second)
            require(second.get("source_manifest_sha256") == frozen.get("source_manifest_sha256"), second)
            require(second.get("installed") is False and second.get("promoted") is False and second.get("certified") is False, second)
            require(second.get("verification_is_native_certification") is False, second)
            require(source_snapshot(source) == initial_source_snapshot, "package build changed source")

        def exactly_one_root_and_exact_entries() -> None:
            with zipfile.ZipFile(archive) as zf:
                names = [info.filename for info in zf.infolist() if not info.is_dir()]
            require(names and {name.split("/", 1)[0] for name in names} == {"Eidolon"}, names[:5])
            require(len(names) == len(set(names)) == built.get("archive_entry_count"), "duplicate or count drift")
            verified = verify_candidate_archive(source, archive, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            require(verified.get("ok") and verified.get("status") == "coherent", verified)
            require(verified.get("missing_count") == verified.get("extra_count") == verified.get("modified_count") == verified.get("renamed_count") == 0, verified)
            require(verified.get("source_only") is True, verified)

        def modified_missing_extra_and_rename_detected() -> None:
            variants = {}
            modified = temp / "modified.zip"
            rewrite_archive(archive, modified, lambda name, payload: (name, payload + b"tampered") if name == "Eidolon/README.md" else (name, payload))
            variants["modified"] = verify_candidate_archive(source, modified, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            missing = temp / "missing.zip"
            rewrite_archive(archive, missing, lambda name, payload: (None, payload) if name == "Eidolon/README.md" else (name, payload))
            variants["missing"] = verify_candidate_archive(source, missing, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            extra = temp / "extra.zip"
            rewrite_archive(archive, extra, lambda name, payload: (name, payload))
            with zipfile.ZipFile(extra, "a", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("Eidolon/extra.txt", b"extra")
            variants["extra"] = verify_candidate_archive(source, extra, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            renamed = temp / "renamed.zip"
            rewrite_archive(archive, renamed, lambda name, payload: ("Eidolon/README-renamed.md", payload) if name == "Eidolon/README.md" else (name, payload))
            variants["renamed"] = verify_candidate_archive(source, renamed, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            require(variants["modified"].get("modified_count") == 1, variants["modified"])
            require(variants["missing"].get("missing_count") == 1, variants["missing"])
            require(variants["extra"].get("extra_count") == 1, variants["extra"])
            require(variants["renamed"].get("renamed_count") == 1, variants["renamed"])
            require(all(not row.get("ok") for row in variants.values()), variants)

        def malicious_archive_structure_rejected() -> None:
            bad = temp / "malicious.zip"
            shutil.copy2(archive, bad)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with zipfile.ZipFile(bad, "a", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("Eidolon/../escape.txt", b"x")
                    zf.writestr("/absolute.txt", b"x")
                    zf.writestr("Eidolon/README.md", b"duplicate")
                    link = zipfile.ZipInfo("Eidolon/link")
                    link.create_system = 3
                    link.external_attr = (stat.S_IFLNK | 0o777) << 16
                    zf.writestr(link, b"README.md")
                    zf.writestr("Eidolon/nested.zip", b"PK")
                    zf.writestr("Eidolon/__pycache__/bad.pyc", b"bytecode")
                    zf.writestr("Eidolon/private.bak", b"backup")
                    zf.writestr("Eidolon/.env", b"SECRET=x")
                    zf.writestr("Eidolon/data/memories.json", b"{}")
            result = verify_candidate_archive(source, bad, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            kinds = {row.get("kind") for row in result.get("structure_findings") or []}
            for expected in ("traversal_path", "absolute_path", "duplicate_entry", "symlink_entry", "nested_archive", "bytecode_entry", "private_backup", "credential_entry", "source_only_privacy_failure"):
                require(expected in kinds, (expected, kinds))
            require(not result.get("ok"), result)

        def filename_root_and_internal_metadata_contradictions() -> None:
            wrong_name = temp / "Eidolon_v9999_1_candidate_deadbeef_source_only.zip"
            shutil.copy2(archive, wrong_name)
            name_result = verify_candidate_archive(source, wrong_name, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            require("archive_filename_version_mismatch" in {row.get("kind") for row in name_result.get("contradictions") or []}, name_result)

            wrong_root = temp / "wrong-root.zip"
            rewrite_archive(archive, wrong_root, lambda name, payload: (name.replace("Eidolon/", "WrongRoot/", 1), payload))
            root_result = verify_candidate_archive(source, wrong_root, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            require("archive_root_mismatch" in {row.get("kind") for row in root_result.get("contradictions") or []}, root_result)

            wrong_meta = temp / "wrong-metadata.zip"
            current_assignment = f'WORKING_SOURCE_VERSION = "{release_metadata.WORKING_SOURCE_VERSION}"'.encode("utf-8")
            rewrite_archive(archive, wrong_meta, lambda name, payload: (name, payload.replace(current_assignment, b'WORKING_SOURCE_VERSION = "9999.1"')) if name == "Eidolon/conscious_agent/release_metadata.py" else (name, payload))
            meta_result = verify_candidate_archive(source, wrong_meta, runtime_root=runtime, candidate_id=frozen["candidate_id"])
            require("internal_release_metadata_version_mismatch" in {row.get("kind") for row in meta_result.get("contradictions") or []}, meta_result)

        def package_records_external_content_free() -> None:
            require(not (source / "data" / "candidate_packages").exists(), "package record entered source")
            record = json.loads(next((runtime / "candidate_packages" / "records").glob("*.json")).read_text(encoding="utf-8"))
            encoded = json.dumps(record, sort_keys=True)
            require(record.get("content_free") is True and "entries" not in record, record)
            require(str(source) not in encoded and str(runtime) not in encoded, record)
            require(record.get("installed") is False and record.get("promoted") is False and record.get("certified") is False, record)

        def old_packaging_uses_canonical_bytes() -> None:
            import release_packaging
            from package_integrity import source_package_bytes
            rel = "data/settings.json"
            require(release_packaging._package_bytes_for_file(rel, ROOT / rel) == source_package_bytes(ROOT, rel), "legacy package-byte drift")

        for name, fn in (
            ("metadata-authority", metadata_authority),
            ("deterministic-coherent-package", deterministic_coherent_package),
            ("one-root-exact-entries", exactly_one_root_and_exact_entries),
            ("tampering-detected", modified_missing_extra_and_rename_detected),
            ("malicious-structure-rejected", malicious_archive_structure_rejected),
            ("filename-root-metadata-contradictions", filename_root_and_internal_metadata_contradictions),
            ("external-content-free-records", package_records_external_content_free),
            ("legacy-package-byte-coherence", old_packaging_uses_canonical_bytes),
        ):
            check(name, fn)

    passed = sum(bool(row.get("ok")) for row in RESULTS)
    report = {"suite": "v1095.7-archive-manifest-coherence", "version": "1095.7", "passed": passed, "failed": len(RESULTS)-passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
