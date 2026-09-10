from __future__ import annotations

"""Targeted regressions for the pre-v1078.9 corrective release.

These tests use temporary fixtures only. They never inspect, move, or quarantine
an operator's real sandbox evidence.
"""

import argparse
import copy
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys

# Corrective verification must remain read-only even when invoked directly.
# Enforce this before importing any project module so Python cannot populate
# __pycache__ inside a clean source extraction.
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for entry in (str(AGENT), str(ROOT / "tools")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import smoke_check  # noqa: E402
import upgrade_migrate  # noqa: E402
from release_metadata import RUNTIME_VERSION  # noqa: E402
from verification_compile import run_disposable_compile  # noqa: E402
from version_metadata_inventory import _VERSION_ASSIGNMENT_HINT  # noqa: E402
from import_compatibility_regression import _run_case  # noqa: E402
from release_verify import _run_json_report  # noqa: E402
from package_integrity import (  # noqa: E402
    SOURCE_DATA_ALLOWLIST,
    forbidden_runtime_path_matches,
    iter_source_tree_entries,
)
from release_packaging import SOURCE_ONLY_DATA_FILES, build_package_inventory  # noqa: E402
from source_project_metadata import load_source_project_metadata  # noqa: E402
from verification_evidence import (  # noqa: E402
    DASHBOARD_ROUTE_TIMEOUTS,
    build_evidence_bundle,
    build_stage_receipt,
    expected_stage_commands,
    isoformat_utc,
    json_sha256,
    load_evidence_bundle,
    new_attestation_key,
    new_invocation_nonce,
    sign_attested_object,
    source_snapshot_digest,
    utc_now,
    write_evidence_bundle,
)

WINDOWS_CREATEPROCESS_COMMAND_LIMIT = 32767


def _surface_artifact(surface_id: str, *, version: str = RUNTIME_VERSION) -> dict[str, Any]:
    return {
        "schema_version": version,
        "artifact_type": "generated_surface_scaffold_preview_review_only",
        "surface_id": surface_id,
        "source_surface_manifest_id": surface_id,
        "dashboard_preview": {"route": f"/{surface_id}", "renderer": "render_preview", "style_contract": "command-deck/operator-console", "hover_contract": "data-tip", "native_title_tooltips_allowed": False, "wiring_activated": False},
        "cli_preview": {"flag": f"--{surface_id}", "builder": "build_preview", "text_renderer": "preview_text", "wiring_activated": False},
        "api_preview": {"route": f"/api/{surface_id}", "exposure": "preview_only", "wiring_activated": False},
        "smoke_preview": {"check": surface_id, "segment": "install-release", "expected_version_source": "EXPECTED_CURRENT_VERSION", "wiring_activated": False},
        "manual_builder": "build_preview",
        "manual_text_renderer": "preview_text",
        "authority_level": "review_only",
        "activation": {
            "generated_preview_authoritative": False,
            "generated_wiring_activated": False,
            "dashboard_wiring_activated": False,
            "api_wiring_activated": False,
            "cli_wiring_activated": False,
            "smoke_wiring_activated": False,
            "applies_source_edits": False,
            "release_authorized": False,
            "autonomy_expanded": False,
            "protected_systems_require_operator_approval": True,
        },
        "parity_anchor": "v930-multi-surface-generated-parity-batch-closure",
        "review_only": True,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "autonomy_expanded": False,
    }


def _wrapper_artifact(surface_id: str, *, version: str = RUNTIME_VERSION) -> dict[str, Any]:
    return {
        "schema_version": version,
        "artifact_type": "generated_scaffold_compatibility_wrapper_preview_review_only",
        "surface_id": surface_id,
        "source_artifact_path": f"sandbox/generated_surface_scaffold_previews/{surface_id}.json",
        "manual_builder": "build_preview",
        "manual_text_renderer": "preview_text",
        "dashboard_wrapper": {"manual_route": f"/{surface_id}", "wrapper_target": "preview_text", "style_contract": "command-deck/operator-console", "hover_contract": "data-tip", "native_title_tooltips_allowed": False, "wiring_activated": False},
        "cli_wrapper": {"manual_flag": f"--{surface_id}", "wrapper_target": "print_preview", "builder_target": "build_preview", "text_renderer": "preview_text", "wiring_activated": False},
        "api_wrapper": {"manual_route": f"/api/{surface_id}", "exposure": "preview_only", "wrapper_target": "build_preview", "wiring_activated": False},
        "smoke_wrapper": {"manual_check": surface_id, "wrapper_target": f"check_{surface_id.replace('-', '_')}", "segment": "install-release", "expected_version_source": "EXPECTED_CURRENT_VERSION", "wiring_activated": False},
        "rollback_expectation": {"manual_code_unchanged": True, "generated_wrapper_can_be_removed_by_deleting_sandbox_artifact": True, "live_wiring_rollback_required": False},
        "protected_manual_status": {"manual_code_replaced": False, "generated_wrapper_authoritative": False, "protected_systems_require_operator_approval": True},
        "review_only": True,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "autonomy_expanded": False,
    }


def write_valid_target(root: Path, target_index: int = 0) -> tuple[Path, Path, list[dict[str, str]]]:
    rel_dir, ledger_name, names = upgrade_migrate.TARGETS[target_index]
    base = root / rel_dir
    base.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str]] = []
    for name in names:
        surface_id = name.removesuffix(".wrapper.json") if name.endswith(".wrapper.json") else name.removesuffix(".json")
        payload = _wrapper_artifact(surface_id) if name.endswith(".wrapper.json") else _surface_artifact(surface_id)
        artifact = base / name
        artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        entries.append({"path": f"{rel_dir}/{name}", "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()})
    ledger_path = base / ledger_name
    ledger_path.write_text(json.dumps({
        "schema_version": RUNTIME_VERSION,
        "review_only": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "artifacts": entries,
    }, indent=2, sort_keys=True), encoding="utf-8")
    return base, ledger_path, entries


def _row(root: Path, target_index: int = 0) -> dict[str, Any]:
    report = upgrade_migrate.build_migration_report(root, apply=False)
    rel_dir = upgrade_migrate.TARGETS[target_index][0]
    return next(row for row in report["targets"] if row["path"] == rel_dir)


def _has_error(row: dict[str, Any], token: str) -> bool:
    return token.lower() in " ".join(str(item) for item in row.get("validation_errors", [])).lower()


def _fixture_case(mutator: Callable[[Path, Path, list[dict[str, str]]], None], predicate: Callable[[dict[str, Any]], bool]) -> bool:
    with tempfile.TemporaryDirectory(prefix="eidolon-evidence-fixture-") as temp_dir:
        root = Path(temp_dir)
        base, ledger, entries = write_valid_target(root)
        mutator(base, ledger, entries)
        return predicate(_row(root))


def _resign_test_bundle(bundle: dict[str, Any], key: str) -> dict[str, Any]:
    candidate = copy.deepcopy(bundle)
    candidate.pop("attestation", None)
    candidate.pop("bundle_sha256", None)
    candidate["bundle_sha256"] = json_sha256(candidate)
    return sign_attested_object(candidate, key)


def _synthetic_evidence_reports() -> dict[str, dict[str, Any]]:
    routes = {
        route: {"ok": True, "status": 200, "timeout_seconds": timeout}
        for route, timeout in DASHBOARD_ROUTE_TIMEOUTS.items()
    }
    return {
        "python-compile": {
            "ok": True,
            "status": "pass",
            "return_code": 0,
            "timed_out": False,
            "cache_cleanup_ok": True,
            "source_tree_bytecode_measured": True,
            "source_tree_bytecode_written": False,
            "source_tree_mutation_count": 0,
            "compile_execution_count": 1,
        },
        "version-inventory": {
            "ok": True,
            "status": "pass",
            "version": RUNTIME_VERSION,
            "scanned_source_scope_sha256": "a" * 64,
            "scanned_source_file_count": 1,
        },
        "corrective-suite": {
            "ok": True,
            "status": "pass",
            "checks": {"synthetic-attestation-fixture": True},
            "real_evidence_touched": False,
            "full_project_compile_execution_count": 0,
        },
        "import-compatibility": {
            "ok": True,
            "status": "pass",
            "mode": "imports",
            "check_count": 1,
            "passed_count": 1,
            "results": [{"ok": True, "label": "synthetic-import-fixture"}],
        },
        "dashboard-http-probe": {
            "ok": True,
            "status": "pass",
            "routes": routes,
            "stage_invocation_count": 1,
            "subprocess_execution_count": 1,
        },
    }


def _build_synthetic_evidence_bundle(
    *,
    producer: str,
    nonce: str,
    key: str,
    source_digest: str,
    generated: Any | None = None,
) -> dict[str, Any]:
    generated_time = generated or utc_now()
    started_at = isoformat_utc(generated_time - timedelta(seconds=2))
    finished_at = isoformat_utc(generated_time - timedelta(seconds=1))
    commands = expected_stage_commands(ROOT, purpose="release")
    reports = _synthetic_evidence_reports()
    receipts = {
        name: build_stage_receipt(
            name,
            producer=producer,
            invocation_nonce=nonce,
            source_snapshot_before=source_digest,
            source_snapshot_after=source_digest,
            commands=commands[name],
            report=report,
            started_at=started_at,
            finished_at=finished_at,
            elapsed_seconds=1.0,
            return_code=0,
            timed_out=False,
            subprocess_execution_count=len(commands[name]),
            attestation_key=key,
        )
        for name, report in reports.items()
    }
    return build_evidence_bundle(
        ROOT,
        producer=producer,
        invocation_nonce=nonce,
        source_snapshot_sha256=source_digest,
        attestation_key=key,
        stages=receipts,
        purpose="release",
        generated_at=isoformat_utc(generated_time),
    )



def run_targeted_regressions() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    # The old smoke command expanded every absolute file path. At a normal deep
    # Windows extraction root this exceeds CreateProcess's command-line limit.
    fake_windows_root = Path("C:/Users/FixtureUser/Documents/Software Development/Local Artificial Intelligence/Eidolon Release Candidates/Validated Source Builds/Eidolon_v1078_8_3_source_only")
    python_files = sorted((ROOT / "conscious_agent").glob("*.py"))
    old_args = [sys.executable, "-m", "py_compile", *[str(fake_windows_root / "conscious_agent" / path.name) for path in python_files]]
    old_length = len(subprocess.list2cmdline(old_args))
    new_command = smoke_check.build_compile_command()
    new_length = len(subprocess.list2cmdline(new_command))
    checks["winerror-206-command-length-regression"] = old_length > WINDOWS_CREATEPROCESS_COMMAND_LIMIT and new_length < 1024 and all(not Path(arg).is_absolute() for arg in new_command[3:])
    details["compile_command"] = {"legacy_character_count": old_length, "bounded_character_count": new_length, "targets": list(smoke_check.COMPILE_TARGETS)}

    with tempfile.TemporaryDirectory(prefix="eidolon-compile-helper-fixture-") as temp_dir:
        compile_fixture_root = Path(temp_dir)
        (compile_fixture_root / "conscious_agent").mkdir()
        (compile_fixture_root / "tools").mkdir()
        (compile_fixture_root / "conscious_agent" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
        (compile_fixture_root / "tools" / "sample_tool.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
        (compile_fixture_root / "eidolon.py").write_text("from conscious_agent.sample import VALUE\n", encoding="utf-8")
        before_pycache = sorted(path.relative_to(compile_fixture_root).as_posix() for path in compile_fixture_root.rglob("*.pyc"))
        compile_report = run_disposable_compile(compile_fixture_root, timeout=30)
        after_pycache = sorted(path.relative_to(compile_fixture_root).as_posix() for path in compile_fixture_root.rglob("*.pyc"))
        checks["disposable-bytecode-cache"] = (
            compile_report.get("ok") is True
            and compile_report.get("cache_cleanup_ok") is True
            and compile_report.get("source_tree_bytecode_measured") is True
            and compile_report.get("source_tree_bytecode_written") is False
            and compile_report.get("source_tree_mutation_count") == 0
            and compile_report.get("compile_execution_count") == 1
            and int(compile_report.get("cache_file_count") or 0) >= 3
            and before_pycache == after_pycache
        )
        details["disposable_compile_fixture"] = compile_report

    class _LowDisk:
        free = 1
        total = 2
        used = 1

    blocked_compile = run_disposable_compile(ROOT, timeout=5, disk_usage=lambda _path: _LowDisk())
    checks["compile-free-space-preflight"] = (
        blocked_compile.get("ok") is False
        and blocked_compile.get("status") == "blocked"
        and "insufficient free disk" in str(blocked_compile.get("reason", "")).lower()
    )


    representative_assignment_lines = (
        b'VERSION = "1.2.3"',
        b'VERSION: str = "1078.8.6"',
        b'VERSION = RUNTIME_VERSION',
        b'    NESTED_VERSION = "4.5"',
    )
    checks["version-inventory-prefilter-pattern"] = (
        all(_VERSION_ASSIGNMENT_HINT.search(line) for line in representative_assignment_lines)
        and _VERSION_ASSIGNMENT_HINT.search(b'print("version 1.2.3")') is None
    )


    nonzero_json_case = {
        "label": "nonzero-valid-json-fixture",
        "kind": "report_dependency",
        "surface": "synthetic",
        "command": (
            sys.executable,
            "-c",
            "import json,sys; print(json.dumps({'ok': False, 'status': 'blocked', 'reason': 'synthetic'})); sys.exit(7)",
        ),
        "timeout": 15,
        "performance_budget_seconds": 10,
    }
    nonzero_json_result = _run_case(nonzero_json_case)
    checks["nonzero-valid-json-is-parsed"] = (
        nonzero_json_result.get("parse_ok") is True
        and nonzero_json_result.get("parse_status") == "pass"
        and nonzero_json_result.get("exit_ok") is False
        and nonzero_json_result.get("exit_status") == "blocked"
        and nonzero_json_result.get("functional_ok") is False
        and nonzero_json_result.get("parsed_report_status") == "blocked"
    )
    details["nonzero_json_parse"] = nonzero_json_result

    logged_nonzero_step, logged_nonzero_report = _run_json_report(
        [
            sys.executable,
            "-c",
            "import json,sys; print('[info] synthetic human log'); print(json.dumps({'ok': False, 'status': 'blocked', 'reason': 'synthetic logged report'})); sys.exit(9)",
        ],
        timeout=15,
        performance_budget_seconds=10,
        allow_trailing_object=True,
    )
    logged_details = logged_nonzero_step.details if isinstance(logged_nonzero_step.details, dict) else {}
    checks["top-level-nonzero-logged-json-is-parsed"] = (
        logged_nonzero_step.status == "fail"
        and logged_nonzero_report.get("status") == "blocked"
        and logged_details.get("parse_status") == "pass"
        and logged_details.get("exit_status") == "blocked"
        and logged_details.get("functional_status") == "blocked"
        and logged_details.get("performance_status") == "pass"
    )
    details["top_level_nonzero_logged_json_parse"] = {
        "step": {
            "status": logged_nonzero_step.status,
            "summary": logged_nonzero_step.summary,
            "elapsed_seconds": logged_nonzero_step.elapsed_seconds,
        },
        "statuses": logged_details,
        "report": logged_nonzero_report,
    }

    producer = "pre_v1078_9_corrective_tests:attestation-fixture"
    nonce = new_invocation_nonce()
    key = new_attestation_key()
    source_digest = source_snapshot_digest(ROOT)
    valid_bundle = _build_synthetic_evidence_bundle(
        producer=producer,
        nonce=nonce,
        key=key,
        source_digest=source_digest,
    )

    def load_fixture(payload: dict[str, Any], **overrides: Any) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        with tempfile.TemporaryDirectory(prefix="eidolon-attested-bundle-") as temp_dir:
            path = Path(temp_dir) / "evidence.json"
            write_evidence_bundle(path, payload)
            expected_root = Path(overrides.get("expected_root", ROOT)).resolve()
            return load_evidence_bundle(
                path,
                expected_root=expected_root,
                expected_producer=overrides.get("expected_producer", producer),
                expected_invocation_nonce=overrides.get("expected_invocation_nonce", nonce),
                expected_source_snapshot=overrides.get("expected_source_snapshot", source_digest),
                attestation_key=overrides.get("attestation_key", key),
                expected_purpose="release",
                current_source_snapshot=source_digest if expected_root == ROOT.resolve() else None,
            )

    accepted, accepted_metadata = load_fixture(valid_bundle)
    checks["attested-evidence-valid-bundle-accepted"] = accepted is not None and accepted_metadata.get("valid") is True

    fabricated = {
        "schema": "eidolon-verification-evidence-v1",
        "root": str(ROOT),
        "producer": producer,
        "stages": {name: {"report": report} for name, report in _synthetic_evidence_reports().items()},
        "ok": True,
        "status": "pass",
    }
    rejected_fabricated, fabricated_metadata = load_fixture(fabricated)
    checks["fabricated-unsigned-evidence-rejected"] = rejected_fabricated is None and fabricated_metadata.get("valid") is False

    tampered = copy.deepcopy(valid_bundle)
    tampered["stages"]["version-inventory"]["report"]["ok"] = False
    rejected_tampered, tampered_metadata = load_fixture(tampered)
    checks["tampered-stage-report-rejected"] = rejected_tampered is None and any(
        "version-inventory" in str(error) or "bundle-attestation" in str(error)
        for error in tampered_metadata.get("errors", [])
    )

    stale_bundle = _build_synthetic_evidence_bundle(
        producer=producer,
        nonce=nonce,
        key=key,
        source_digest=source_digest,
        generated=utc_now() - timedelta(hours=2),
    )
    rejected_stale, stale_metadata = load_fixture(stale_bundle)
    checks["stale-attested-evidence-rejected"] = rejected_stale is None and "fresh" in stale_metadata.get("errors", [])

    missing_stage = copy.deepcopy(valid_bundle)
    missing_stage["stages"].pop("corrective-suite")
    missing_stage = _resign_test_bundle(missing_stage, key)
    rejected_missing, missing_metadata = load_fixture(missing_stage)
    checks["missing-stage-evidence-rejected"] = rejected_missing is None and "complete-stage-set" in missing_metadata.get("errors", [])

    unknown_stage = copy.deepcopy(valid_bundle)
    unknown_stage["stages"]["invented-passing-stage"] = copy.deepcopy(unknown_stage["stages"]["version-inventory"])
    unknown_stage = _resign_test_bundle(unknown_stage, key)
    rejected_unknown_stage, unknown_stage_metadata = load_fixture(unknown_stage)
    checks["unknown-stage-evidence-rejected"] = rejected_unknown_stage is None and "complete-stage-set" in unknown_stage_metadata.get("errors", [])

    rejected_producer, producer_metadata = load_fixture(valid_bundle, expected_producer="unknown-producer")
    checks["unknown-producer-evidence-rejected"] = rejected_producer is None and "producer" in producer_metadata.get("errors", [])

    with tempfile.TemporaryDirectory(prefix="eidolon-wrong-root-") as wrong_root:
        rejected_root, root_metadata = load_fixture(valid_bundle, expected_root=Path(wrong_root))
    checks["wrong-root-evidence-rejected"] = rejected_root is None and "root" in root_metadata.get("errors", [])

    rejected_source, source_metadata = load_fixture(valid_bundle, expected_source_snapshot="f" * 64)
    checks["wrong-source-digest-evidence-rejected"] = rejected_source is None and "source-expected" in source_metadata.get("errors", [])

    rejected_nonce, nonce_metadata = load_fixture(valid_bundle, expected_invocation_nonce="wrong-nonce")
    checks["wrong-nonce-evidence-rejected"] = rejected_nonce is None and "nonce" in nonce_metadata.get("errors", [])
    details["evidence_adversarial"] = {
        "valid_bundle": accepted_metadata,
        "fabricated": fabricated_metadata,
        "tampered": tampered_metadata,
        "stale": stale_metadata,
        "missing_stage": missing_metadata,
        "unknown_stage": unknown_stage_metadata,
        "unknown_producer": producer_metadata,
        "wrong_root": root_metadata,
        "wrong_source": source_metadata,
        "wrong_nonce": nonce_metadata,
    }

    import api_server as api_server_module

    captured_api_bind: dict[str, Any] = {}
    original_run_api_server = api_server_module.run_api_server
    try:
        def capture_api_bind(host: str | None = None, port: int | None = None) -> None:
            captured_api_bind.update({"host": host, "port": port})

        api_server_module.run_api_server = capture_api_bind
        api_exit = api_server_module.main(["--host", "127.0.0.9", "--port", "0"])
    finally:
        api_server_module.run_api_server = original_run_api_server
    api_source = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8", errors="replace")
    checks["api-cli-host-port-dispatch"] = (
        api_exit == 0
        and captured_api_bind == {"host": "127.0.0.9", "port": 0}
        and 'if __name__ == "__main__":' in api_source
        and "raise SystemExit(main())" in api_source
    )
    details["api_cli_dispatch"] = captured_api_bind


    with tempfile.TemporaryDirectory(prefix="eidolon-evidence-valid-") as temp_dir:
        root = Path(temp_dir)
        write_valid_target(root, 0)
        write_valid_target(root, 1)
        report = upgrade_migrate.build_migration_report(root, apply=False)
        checks["valid-complete-directory"] = report.get("ok") is True and all(row.get("status") == "current_complete" for row in report.get("targets", []))

    with tempfile.TemporaryDirectory(prefix="eidolon-evidence-empty-") as temp_dir:
        root = Path(temp_dir)
        rel_dir = upgrade_migrate.TARGETS[0][0]
        (root / rel_dir).mkdir(parents=True)
        row = _row(root)
        checks["empty-directory-quarantine"] = (
            row.get("status") == "quarantine_required"
            and row.get("needs_quarantine") is True
            and _has_error(row, "empty evidence directory")
        )

    # Windows developer accounts commonly lack SeCreateSymbolicLinkPrivilege.
    # Simulate the exact lstat/reparse payload consumed by the migration code so
    # rejection behavior is exercised without requiring privileged filesystem
    # operations or pretending an unavailable symlink was tested.
    with tempfile.TemporaryDirectory(prefix="eidolon-evidence-indirection-target-") as temp_dir:
        root = Path(temp_dir)
        target, _ledger, _entries = write_valid_target(root)
        original_lstat = upgrade_migrate._lstat_payload
        try:
            def target_reparse_lstat(path: Path) -> dict[str, int]:
                payload = dict(original_lstat(path))
                if Path(path) == target:
                    payload["file_attributes"] = int(payload.get("file_attributes", 0)) | upgrade_migrate._FILE_ATTRIBUTE_REPARSE_POINT
                return payload
            upgrade_migrate._lstat_payload = target_reparse_lstat
            row = _row(root)
            checks["symlink-target-rejected"] = row.get("status") == "blocked" and "indirection" in str(row.get("error", "")).lower()
        finally:
            upgrade_migrate._lstat_payload = original_lstat

    with tempfile.TemporaryDirectory(prefix="eidolon-evidence-indirection-artifact-") as temp_dir:
        root = Path(temp_dir)
        base, ledger, entries = write_valid_target(root)
        artifact = base / Path(entries[0]["path"]).name
        original_lstat = upgrade_migrate._lstat_payload
        try:
            def artifact_reparse_lstat(path: Path) -> dict[str, int]:
                payload = dict(original_lstat(path))
                if Path(path) == artifact:
                    payload["file_attributes"] = int(payload.get("file_attributes", 0)) | upgrade_migrate._FILE_ATTRIBUTE_REPARSE_POINT
                return payload
            upgrade_migrate._lstat_payload = artifact_reparse_lstat
            row = _row(root)
            checks["symlink-artifact-rejected"] = (
                row.get("status") == "quarantine_required"
                and (_has_error(row, "reparse") or _has_error(row, "indirection"))
            )
            details["artifact_indirection_fixture"] = {
                "method": "deterministic mocked lstat Windows reparse-point payload",
                "native_symlink_privilege_required": False,
            }
        finally:
            upgrade_migrate._lstat_payload = original_lstat

    with tempfile.TemporaryDirectory(prefix="eidolon-reparse-detector-") as temp_dir:
        probe = Path(temp_dir) / "probe"
        probe.mkdir()
        original_lstat = upgrade_migrate._lstat_payload
        try:
            payload = original_lstat(probe)
            def fake_lstat(path: Path) -> dict[str, int]:
                current = dict(original_lstat(path))
                if Path(path) == probe:
                    current["file_attributes"] = int(current.get("file_attributes", 0)) | upgrade_migrate._FILE_ATTRIBUTE_REPARSE_POINT
                return current
            upgrade_migrate._lstat_payload = fake_lstat
            indirect, reason = upgrade_migrate._is_indirection(probe)
            checks["windows-reparse-point-fixture"] = indirect is True and "reparse" in str(reason).lower()
        finally:
            upgrade_migrate._lstat_payload = original_lstat

    with tempfile.TemporaryDirectory(prefix="eidolon-migration-object-swap-") as temp_dir:
        root = Path(temp_dir)
        rel_dir = upgrade_migrate.TARGETS[0][0]
        target = root / rel_dir
        target.mkdir(parents=True)
        (target / "stale.json").write_text(json.dumps({"schema_version": "1032.0"}), encoding="utf-8")
        original = root / "original_target_saved"
        def swap_after_plan(_project_root: Path, _planned: list[dict[str, Any]]) -> None:
            target.rename(original)
            target.mkdir()
            (target / "different.json").write_text("{}", encoding="utf-8")
        report = upgrade_migrate.build_migration_report(root, apply=True, _before_apply=swap_after_plan)
        checks["inspection-apply-object-identity"] = (
            report.get("ok") is False
            and report.get("transaction_status") == "rolled_back"
            and "changed after inspection" in str(report.get("transaction_error", ""))
            and target.is_dir()
            and original.is_dir()
        )

    checks["unsafe-artifact-content"] = _fixture_case(
        lambda base, _ledger, _entries: _rewrite_json(base / upgrade_migrate.TARGETS[0][2][0], lambda data: data.__setitem__("release_authorized", True)),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "release_authorized"),
    )
    checks["unexpected-json-file"] = _fixture_case(
        lambda base, _ledger, _entries: (base / "unexpected.json").write_text("{}", encoding="utf-8"),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "unexpected physical artifacts"),
    )
    checks["stale-evidence"] = _fixture_case(
        lambda base, _ledger, _entries: _rewrite_and_rehash(base, _ledger, 0, lambda data: data.__setitem__("schema_version", "1032.0")),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "stale"),
    )
    checks["duplicate-references"] = _fixture_case(
        lambda _base, ledger, _entries: _rewrite_json(ledger, lambda data: data["artifacts"].__setitem__(1, dict(data["artifacts"][0]))),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "duplicate artifact path"),
    )
    checks["traversal-attempt"] = _fixture_case(
        lambda _base, ledger, _entries: _rewrite_json(ledger, lambda data: data["artifacts"][0].__setitem__("path", "../README.md")),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "escapes the project"),
    )
    checks["hash-mismatch"] = _fixture_case(
        lambda _base, ledger, _entries: _rewrite_json(ledger, lambda data: data["artifacts"][0].__setitem__("sha256", "0" * 64)),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "sha256 mismatch"),
    )
    checks["missing-artifact"] = _fixture_case(
        lambda base, _ledger, _entries: (base / upgrade_migrate.TARGETS[0][2][0]).unlink(),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "missing physical artifacts"),
    )
    checks["malformed-artifact-schema"] = _fixture_case(
        lambda base, ledger, _entries: _rewrite_and_rehash(
            base, ledger, 0, lambda data: data["dashboard_preview"].pop("route")
        ),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "dashboard_preview missing schema fields"),
    )
    checks["unreferenced-physical-artifact"] = _fixture_case(
        lambda _base, ledger, _entries: _rewrite_json(ledger, lambda data: data["artifacts"].pop()),
        lambda row: row.get("status") == "quarantine_required" and _has_error(row, "missing expected ledger paths"),
    )

    with tempfile.TemporaryDirectory(prefix="eidolon-migration-dry-run-") as temp_dir:
        root = Path(temp_dir)
        rel_dir = upgrade_migrate.TARGETS[0][0]
        stale = root / rel_dir
        stale.mkdir(parents=True)
        (stale / "stale.json").write_text(json.dumps({"schema_version": "1032.0"}), encoding="utf-8")
        before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        report = upgrade_migrate.build_migration_report(root, apply=False)
        after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        checks["default-migration-is-review-only"] = report.get("mode") == "dry_run" and report.get("quarantine_required_count") == 1 and before == after and stale.is_dir()

    with tempfile.TemporaryDirectory(prefix="eidolon-migration-rollback-") as temp_dir:
        root = Path(temp_dir)
        for rel_dir, _ledger, _names in upgrade_migrate.TARGETS:
            stale_dir = root / rel_dir
            stale_dir.mkdir(parents=True)
            (stale_dir / "stale.json").write_text(json.dumps({"schema_version": "1032.0"}), encoding="utf-8")
        move_calls = 0
        prepared_seen_before_first_move = False

        def fail_second_move(source: str, destination: str) -> Any:
            nonlocal move_calls, prepared_seen_before_first_move
            move_calls += 1
            manifests = list((root / "sandbox" / "retired_evidence_quarantine").glob("*/migration_manifest.json"))
            if move_calls == 1 and manifests:
                prepared = json.loads(manifests[0].read_text(encoding="utf-8"))
                prepared_seen_before_first_move = prepared.get("transaction_status") == "prepared" and len(prepared.get("planned", [])) == 2
            if move_calls == 2:
                raise OSError("simulated second move failure")
            return shutil.move(source, destination)

        report = upgrade_migrate.build_migration_report(root, apply=True, _move=fail_second_move)
        manifest_path = root / str(report.get("quarantine_root")) / "migration_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        sources_restored = all((root / rel_dir).is_dir() for rel_dir, _ledger, _names in upgrade_migrate.TARGETS)
        checks["prepared-manifest-and-rollback"] = (
            prepared_seen_before_first_move
            and report.get("transaction_status") == "rolled_back"
            and report.get("quarantined_count") == 0
            and report.get("files_deleted") == 0
            and sources_restored
            and manifest.get("transaction_status") == "rolled_back"
            and manifest.get("files_deleted") == 0
        )


    ps = (ROOT / "setup.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "setup.sh").read_text(encoding="utf-8")
    checks["standalone-bytecode-writing-disabled"] = (
        sys.dont_write_bytecode is True
        and os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    )

    with tempfile.TemporaryDirectory(prefix="eidolon-source-project-metadata-") as tmp:
        fixture_root = Path(tmp)
        fixture_workspaces = fixture_root / "data" / "workspaces"
        fixture_workspaces.mkdir(parents=True)
        runtime_projects = fixture_root / "data" / "projects.json"
        runtime_projects.write_text(
            json.dumps({"last_updated_for": "v0.0-runtime-fixture", "private_runtime_marker": True}),
            encoding="utf-8",
        )
        source_projects = load_source_project_metadata(fixture_root)
        checks["source-project-metadata-ignores-runtime-projects"] = (
            str(source_projects.get("last_updated_for") or "").removeprefix("v")
            == str(RUNTIME_VERSION).removeprefix("v")
            and source_projects.get("runtime_projects_packaged") is False
            and source_projects.get("source") == "data/workspaces/projects.json"
            and source_projects.get("private_runtime_marker") is None
        )

    with tempfile.TemporaryDirectory(prefix="eidolon-project-manager-runtime-") as tmp:
        environment = os.environ.copy()
        environment.update({
            "EIDOLON_DATA_DIR": str(Path(tmp) / "data"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join([str(AGENT), str(ROOT / "tools"), environment.get("PYTHONPATH", "")]),
        })
        fallback_process = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                (
                    "import json, project_manager; "
                    "data=project_manager.load_projects_data(); "
                    "print(json.dumps({'active_project': data.get('active_project'), "
                    "'project_count': len(data.get('projects', []))}))"
                ),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        fallback_payload = json.loads(fallback_process.stdout) if fallback_process.returncode == 0 else {}
        checks["project-manager-clean-install-source-fallback"] = (
            fallback_process.returncode == 0
            and fallback_payload.get("active_project") == source_projects.get("active_project")
            and fallback_payload.get("project_count") == len(source_projects.get("projects", []))
            and not (Path(tmp) / "data" / "projects.json").exists()
        )

    inventory = build_package_inventory(save=False)
    checks["runtime-projects-excluded-from-source-package"] = (
        "data/projects.json" not in SOURCE_DATA_ALLOWLIST
        and "data/projects.json" not in SOURCE_ONLY_DATA_FILES
        and "data/projects.json" not in iter_source_tree_entries(ROOT)
        and not any(row.get("path") == "data/projects.json" for row in inventory.get("included", []))
        and forbidden_runtime_path_matches(["Eidolon/data/projects.json"]) == ["Eidolon/data/projects.json"]
    )
    checks["current-state-smoke-does-not-require-runtime-projects"] = (
        'data/projects.json' not in inspect.getsource(smoke_check.check_current_state_integrity_staleness_hardening_v1)
    )

    checks["setup-explicit-migration-opt-in"] = (
        "[switch]$ApplyUpgradeMigration" in ps
        and "if ($ApplyUpgradeMigration)" in ps
        and "--apply-upgrade-migration" in sh
        and 'if [ "$APPLY_UPGRADE_MIGRATION" -eq 1 ]' in sh
        and "upgrade_migrate.py\") --apply --quiet" not in ps
        and 'upgrade_migrate.py" --apply --quiet' not in sh
    )

    return {
        "version": RUNTIME_VERSION,
        "status": "pass" if all(checks.values()) else "blocked",
        "ok": all(checks.values()),
        "checks": checks,
        "details": details,
        "real_evidence_touched": False,
        "full_project_compile_execution_count": 0,
        "fixture_compile_execution_count": 1,
        "temporary_fixture_count": len(checks),
    }


def _rewrite_json(path: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutator(data)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _rewrite_and_rehash(base: Path, ledger: Path, index: int, mutator: Callable[[dict[str, Any]], None]) -> None:
    ledger_data = json.loads(ledger.read_text(encoding="utf-8"))
    rel_path = ledger_data["artifacts"][index]["path"]
    artifact_path = base / Path(rel_path).name
    _rewrite_json(artifact_path, mutator)
    ledger_data["artifacts"][index]["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    ledger.write_text(json.dumps(ledger_data, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run targeted pre-v1078.9 corrective regressions using temporary fixtures only.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_targeted_regressions()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, passed in report["checks"].items():
            print(f"[{'ok' if passed else 'fail'}] {name}")
        print(f"Status: {report['status']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
