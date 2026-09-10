from __future__ import annotations

import hashlib
import json
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


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def copy_source(parent: Path) -> Path:
    target = parent / "Eidolon"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", "*.pyc", "*.pyo", "*.zip"),
    )
    return target


def main() -> int:
    import release_metadata
    from package_integrity import source_package_bytes
    from release_candidate_identity import (
        build_source_manifest,
        candidate_status,
        freeze_release_candidate,
    )
    from version_roles import build_version_role_contract

    def metadata_authority() -> None:
        require(tuple(map(int, release_metadata.WORKING_SOURCE_VERSION.split("."))) >= (1095, 6), release_metadata.WORKING_SOURCE_VERSION)
        import release_candidate_identity
        require(release_candidate_identity.CANDIDATE_IDENTITY_CONTRACT_VERSION == "1", "identity contract missing")

    def manifest_is_exact_and_portable() -> None:
        manifest = build_source_manifest(ROOT)
        require(manifest.get("working_source_version") == release_metadata.WORKING_SOURCE_VERSION, manifest)
        require(manifest.get("file_count") == len(manifest.get("entries") or []), "count mismatch")
        require(manifest.get("manifest_sha256") == build_source_manifest(ROOT).get("manifest_sha256"), "nondeterministic manifest")
        for row in manifest.get("entries") or []:
            path = str(row.get("path") or "")
            require(path and not Path(path).is_absolute() and ".." not in Path(path).parts, path)
            require(len(str(row.get("raw_sha256") or "")) == 64, row)
            require(len(str(row.get("package_sha256") or "")) == 64, row)

    def freeze_records_external_and_content_free() -> None:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1095-6-") as tmp:
            temp = Path(tmp)
            source = copy_source(temp)
            runtime = temp / "runtime"
            before = snapshot(source)
            frozen = freeze_release_candidate(source, runtime_root=runtime, expected_version=release_metadata.WORKING_SOURCE_VERSION)
            require(frozen.get("ok") and frozen.get("status") == "frozen", frozen)
            require(snapshot(source) == before, "freeze changed source")
            require(not (source / "data" / "release_candidates").exists(), "candidate record entered source")
            record = json.loads(next((runtime / "release_candidates" / "records").glob("*.json")).read_text(encoding="utf-8"))
            encoded = json.dumps(record, sort_keys=True)
            require(record.get("content_free") is True, record)
            require("entries" not in record and str(source) not in encoded, record)
            require(record.get("installed") is False and record.get("promoted") is False and record.get("certified") is False, record)

    def archive_existence_does_not_create_candidate() -> None:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1095-6-zip-") as tmp:
            temp = Path(tmp)
            source = copy_source(temp)
            runtime = temp / "runtime"
            (runtime / "candidate_packages" / "archives").mkdir(parents=True)
            (runtime / "candidate_packages" / "archives" / "Eidolon_v1095_6_candidate_source_only.zip").write_bytes(b"not-a-candidate")
            status = candidate_status(source, runtime_root=runtime)
            require(status.get("status") == "not_frozen" and status.get("candidate_present") is False, status)
            require(status.get("candidate_inferred_from_archive") is False, status)

    def stale_after_source_change() -> None:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1095-6-stale-") as tmp:
            temp = Path(tmp)
            source = copy_source(temp)
            runtime = temp / "runtime"
            frozen = freeze_release_candidate(source, runtime_root=runtime)
            require(frozen.get("ok"), frozen)
            readme = source / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nfixture source change\n", encoding="utf-8")
            status = candidate_status(source, runtime_root=runtime)
            require(not status.get("ok") and status.get("status") == "stale", status)
            require(status.get("source_tree_matches_manifest") is False, status)

    def role_contract_never_infers_candidate_name() -> None:
        state = build_version_role_contract(ROOT, candidate_name="Eidolon_v1095_6_candidate_source_only.zip")
        require(state.get("candidate_version") == "", state)
        require(state.get("candidate_inferred_from_name") is False, state)
        require(state.get("packaged_archive_version") == "", "candidate_name impersonated package")

    def package_bytes_are_stable_without_source_write() -> None:
        path = ROOT / "data" / "settings.json"
        before = path.read_bytes()
        first = source_package_bytes(ROOT, "data/settings.json")
        second = source_package_bytes(ROOT, "data/settings.json")
        require(first == second, "packaged metadata bytes drift")
        require(path.read_bytes() == before, "packaging helper mutated settings")
        parsed = json.loads(first.decode("utf-8"))
        require("last_seen_at" not in parsed and "updated_at" not in parsed, parsed)

    def source_only_policy_excludes_candidate_runtime() -> None:
        from package_integrity import forbidden_runtime_path_matches
        matches = forbidden_runtime_path_matches([
            "Eidolon/data/release_candidates/active_candidate.json",
            "Eidolon/data/candidate_packages/records/example.json",
        ])
        require(len(matches) == 2, matches)

    for name, fn in (
        ("metadata-authority", metadata_authority),
        ("manifest-exact-portable", manifest_is_exact_and_portable),
        ("freeze-external-content-free", freeze_records_external_and_content_free),
        ("zip-does-not-create-candidate", archive_existence_does_not_create_candidate),
        ("source-change-stales-candidate", stale_after_source_change),
        ("candidate-name-not-authority", role_contract_never_infers_candidate_name),
        ("stable-package-bytes-no-write", package_bytes_are_stable_without_source_write),
        ("candidate-runtime-source-only-excluded", source_only_policy_excludes_candidate_runtime),
    ):
        check(name, fn)

    passed = sum(bool(row.get("ok")) for row in RESULTS)
    report = {
        "suite": "v1095.6-exact-candidate-identity-contract",
        "version": "1095.6",
        "passed": passed,
        "failed": len(RESULTS) - passed,
        "total": len(RESULTS),
        "checks": RESULTS,
    }
    print(json.dumps(report, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
