from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
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


def _copy_source(destination: Path) -> Path:
    target = destination / "Eidolon"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    return target


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    import release_metadata
    from package_integrity import iter_source_tree_entries, package_privacy_summary_for_zip
    from release_archive_coherence import build_candidate_archive, package_directory
    from release_candidate_coherence import candidate_package_handoff_status
    from release_candidate_identity import freeze_release_candidate
    from version_roles import build_version_role_contract

    temp = tempfile.TemporaryDirectory(prefix="eidolon_v1095_8_")
    base = Path(temp.name)
    source = _copy_source(base)
    runtime = base / "runtime"
    empty_runtime = base / "empty_runtime"
    empty_runtime.mkdir(parents=True, exist_ok=True)

    frozen = freeze_release_candidate(source, runtime_root=runtime, expected_version=release_metadata.WORKING_SOURCE_VERSION)
    require(frozen.get("ok"), frozen)
    packaged = build_candidate_archive(source, runtime_root=runtime)
    require(packaged.get("ok"), packaged)
    archive = package_directory(runtime) / "archives" / str(packaged["package_filename"])

    def metadata_contract() -> None:
        require(tuple(map(int, release_metadata.WORKING_SOURCE_VERSION.split("."))) >= (1095, 8), release_metadata.WORKING_SOURCE_VERSION)
        require(release_metadata.RUNTIME_MILESTONE.startswith(f"v{release_metadata.WORKING_SOURCE_VERSION} "), release_metadata.RUNTIME_MILESTONE)
        next_arc = release_metadata.NEXT_RECOMMENDED_ARC
        explicit_review_boundary = next_arc.startswith("Desktop Codex review of v") and " before v" in next_arc
        require(next_arc.startswith("v") or explicit_review_boundary, next_arc)
        roles = build_version_role_contract(ROOT)
        role_names = {row.get("role") for row in roles.get("roles", [])}
        require({"working_source", "candidate", "packaged_archive", "installed", "promoted_release", "certified_release"} <= role_names, role_names)
        require(roles.get("promoted_release_version") == "" and roles.get("certified_release_version") == "", "source invented release authority")

    def zip_does_not_create_candidate() -> None:
        archives = package_directory(empty_runtime) / "archives"
        archives.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archives / "Eidolon_v1095_8_candidate_fake_source_only.zip", "w") as handle:
            handle.writestr("Eidolon/README.md", "not evidence")
        status = candidate_package_handoff_status(ROOT, runtime_root=empty_runtime)
        require(status.get("status") == "not_frozen", status)
        require((status.get("frozen_candidate") or {}).get("candidate_inferred_from_archive") is False, status)
        require((status.get("packaged_archive") or {}).get("status") == "not_packaged", status)

    def coherent_handoff_is_bounded() -> None:
        status = candidate_package_handoff_status(source, runtime_root=runtime)
        require(status.get("ok") and status.get("status") == "candidate_and_package_coherent", status)
        candidate = status.get("frozen_candidate") or {}
        package = status.get("packaged_archive") or {}
        require(candidate.get("candidate_id") == package.get("candidate_id") == frozen.get("candidate_id"), status)
        require(package.get("archive_sha256") == packaged.get("archive_sha256"), status)
        require(status.get("content_free") and status.get("read_only"), status)
        require(status.get("provider_contacted") is False and status.get("ordinary_conversation_affected") is False, status)
        encoded = json.dumps(status, sort_keys=True)
        require(str(source) not in encoded and str(runtime) not in encoded, "absolute path leaked")
        require("missing_entries" not in encoded and "modified_entries" not in encoded, "entry details leaked")

    def direct_authority_is_never_invented() -> None:
        absent = candidate_package_handoff_status(source, runtime_root=runtime)
        for key in ("installed_version", "promoted_release", "certified_release"):
            row = absent.get(key) or {}
            require(row.get("status") == "unknown" and row.get("authoritative_evidence_supplied") is False, (key, row))
        declared = candidate_package_handoff_status(
            source,
            runtime_root=runtime,
            installed_version="1095.1",
            promoted_version="1095.0",
            certified_version="1094.9",
        )
        require((declared.get("installed_version") or {}).get("version") == "1095.1", declared)
        require((declared.get("promoted_release") or {}).get("version") == "1095.0", declared)
        require((declared.get("certified_release") or {}).get("version") == "1094.9", declared)
        require(declared.get("installation_changed") is False and declared.get("promotion_changed") is False, declared)
        require(declared.get("certification_performed") is False, declared)

    def stale_source_is_detected() -> None:
        path = source / "README.md"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n<!-- stale-candidate-fixture -->\n")
            status = candidate_package_handoff_status(source, runtime_root=runtime)
            require(status.get("status") == "attention_required", status)
            require((status.get("frozen_candidate") or {}).get("stale") is True, status)
            kinds = {row.get("kind") for row in status.get("contradictions", [])}
            require("candidate_source_stale" in kinds, kinds)
        finally:
            path.write_bytes(original)

    def package_record_contradiction_is_detected() -> None:
        record_path = package_directory(runtime) / "records" / f"{frozen['candidate_id']}.json"
        original = _read_json(record_path)
        broken = copy.deepcopy(original)
        broken["archive_sha256"] = "0" * 64
        _write_json(record_path, broken)
        try:
            status = candidate_package_handoff_status(source, runtime_root=runtime)
            require(status.get("status") == "attention_required", status)
            kinds = {row.get("kind") for row in status.get("contradictions", [])}
            require("package_record_archive_sha256_mismatch" in kinds, kinds)
        finally:
            _write_json(record_path, original)

    def dashboard_and_api_get_are_read_only() -> None:
        previous = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime)
        try:
            import api_server
            code, payload = api_server.dispatch_api("GET", "/api/release-candidate-package-status", query={})
            require(code == 200 and payload.get("ok"), payload)
            data = payload.get("data") or {}
            require(data.get("status") == "candidate_and_package_coherent", data)
            post_code, post_payload = api_server.dispatch_api("POST", "/api/release-candidate-package-status", body={})
            require(post_code == 404 and post_payload.get("ok") is False, post_payload)

            import dashboard
            from http.server import ThreadingHTTPServer
            server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.EidolonDashboardHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/api/release-candidate-package-status"
                with urlopen(url, timeout=15) as response:
                    dashboard_data = json.loads(response.read().decode("utf-8"))
                    require(response.status == 200 and dashboard_data.get("status") == "candidate_and_package_coherent", dashboard_data)
                request = Request(url, data=b"{}", method="POST", headers={"Content-Type": "application/json"})
                try:
                    urlopen(request, timeout=15)
                except HTTPError as error:
                    require(error.code == 404, error.code)
                else:
                    raise AssertionError("dashboard registered candidate status mutation")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)
        finally:
            if previous is None:
                os.environ.pop("EIDOLON_DATA_DIR", None)
            else:
                os.environ["EIDOLON_DATA_DIR"] = previous

    def ordinary_conversation_remains_clean() -> None:
        import project_manager
        ordinary = project_manager.project_context_text(limit_items=1, include_version_roles=False)
        for token in ("Frozen candidate:", "Packaged archive:", "Promoted release:", "Certified release:"):
            require(token not in ordinary, ordinary)
        runtime_source = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
        require("project_context_text(include_version_roles=False)" in runtime_source, "ordinary context changed")
        require("candidate_package_handoff_status" not in runtime_source, "candidate administration entered conversation runtime")

    def records_and_manifests_remain_external() -> None:
        source_entries = set(iter_source_tree_entries(source))
        require(not any(name.startswith("data/release_candidates/") for name in source_entries), "candidate records entered source")
        require(not any(name.startswith("data/candidate_packages/") for name in source_entries), "package records entered source")
        privacy = package_privacy_summary_for_zip(archive)
        require(privacy.get("ok") and privacy.get("source_only"), privacy)
        with zipfile.ZipFile(archive) as handle:
            names = handle.namelist()
        require(not any("release_candidates" in name or "candidate_packages" in name for name in names), "external records packaged")
        require(not any(name.endswith("active_candidate.json") or name.endswith("active_package.json") for name in names), "candidate pointers packaged")

    def complete_authoritative_reports_survive_wrapper_parsing() -> None:
        from post_review_development_verify import report_functional_ok
        require(report_functional_ok({"passed": 10, "failed": 0, "total": 10}), "complete report rejected")
        require(report_functional_ok({"passed": 8, "total": 8}), "historical count-only report rejected")
        require(not report_functional_ok({"passed": 7, "failed": 1, "total": 8}), "failed report accepted")

    def docs_and_registration_are_coherent() -> None:
        history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        require(history.count("## v1095.8 - Candidate Handoff and Daily-Use Coherence") == 1, "history missing or duplicate")
        require(history.index("## v1095.8") < history.index("## v1095.7") < history.index("## v1095.6"), "history not newest-first")
        next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
        require("v1150" in next_steps, "Desktop Codex schedule missing")
        registration = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
        require("v1095.8-candidate-handoff-daily-use-coherence" in registration, "suite not registered")

    for name, fn in (
        ("v1095.8 metadata and six explicit release roles", metadata_contract),
        ("ZIP existence never creates candidate or package authority", zip_does_not_create_candidate),
        ("coherent candidate handoff is bounded and content-free", coherent_handoff_is_bounded),
        ("installed promoted and certified authority is never invented", direct_authority_is_never_invented),
        ("source changes mark the frozen candidate stale", stale_source_is_detected),
        ("package record digest contradiction remains visible", package_record_contradiction_is_detected),
        ("dashboard and standalone API status are GET-only", dashboard_and_api_get_are_read_only),
        ("ordinary conversation remains free of candidate administration", ordinary_conversation_remains_clean),
        ("candidate records manifests and package state remain external", records_and_manifests_remain_external),
        ("complete authoritative reports survive wrapper parsing", complete_authoritative_reports_survive_wrapper_parsing),
        ("documentation ordering and verification registration stay coherent", docs_and_registration_are_coherent),
    ):
        check(name, fn)

    temp.cleanup()
    passed = sum(bool(row.get("ok")) for row in RESULTS)
    report = {"version": "1095.8", "passed": passed, "failed": len(RESULTS) - passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
