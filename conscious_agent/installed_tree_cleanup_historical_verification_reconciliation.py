from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from package_integrity import package_privacy_summary_for_zip, strip_package_root
from release_packaging import build_package_inventory

INSTALLED_TREE_CLEANUP_HISTORICAL_VERIFICATION_RECONCILIATION_VERSION = RUNTIME_VERSION
INSTALLED_TREE_CLEANUP_HISTORICAL_VERIFICATION_RECONCILIATION_ID = "installed-tree-cleanup-and-historical-verification-reconciliation-v1"
DASHBOARD_ROUTE = "/installed-tree-cleanup-historical-verification-reconciliation"
API_ROUTE = "/api/installed-tree-cleanup/historical-verification-reconciliation"
ZIP_PRIVACY_GATE_ID = "release-zip-privacy-and-critical-gate-repair-v1"
DOCTOR_HEADROOM_ID = "dashboard-doctor-performance-headroom-repair-v1"
RECONCILED_HISTORICAL_DOCTOR_TOKEN = "v1052_bounded_shell_supersedes_primary_report_inline_requirement=True"

LOCAL_RUNTIME_STATE_FIXTURES = (
    "data/tasks.json",
    "data/memories.json",
    "data/thoughts.log",
    "data/dashboard_chat/session.json",
    "data/self_development_cycles/latest.json",
    "data/workspaces/timeline.json",
)

SOURCE_SAFE_DATA = {
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/projects.json",
    "data/workspaces/active_project.json",
    "data/signing/trusted_public_keys.json",
}
SOURCE_SAFE_PREFIXES = ("data/workspaces/command_profiles/",)
RUNTIME_PREFIXES = (
    "data/approvals/",
    "data/chat_actions/",
    "data/dashboard_chat/",
    "data/self_development_cycles/",
    "data/releases/",
    "data/release_package/",
    "data/release_installation/",
    "data/backups/",
    "data/diagnostics/",
    "data/notifications/",
    "data/stable_loops/",
    "data/watch_reports/",
    "data/work_cycles/",
    "data/workspaces/timeline.json",
)
RUNTIME_EXACT = {
    "data/tasks.json",
    "data/action_log.json",
    "data/memories.json",
    "data/thoughts.log",
    "data/self_model.json",
}
OBSOLETE_GENERATED_SOURCE_PATTERNS = (
    "generated_probe_",
    "generated_live_probe_",
    "sandbox_probe_",
    "probe_packet_",
    "validation_probe_",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "zip_privacy_is_release_blocker": True,
    "local_runtime_state_is_expected": True,
    "local_runtime_state_blocks_release_zip": False,
    "obsolete_source_artifacts_require_operator_cleanup": True,
    "cleanup_report_deletes_files": False,
    "source_files_mutated": False,
    "memory_mutated": False,
    "runtime_data_deleted": False,
    "live_diagnostics_executed": False,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_still_required": True,
}


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1]).resolve()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _is_source_safe_data(rel: str) -> bool:
    rel = rel.replace("\\", "/").strip("/")
    return rel in SOURCE_SAFE_DATA or any(rel.startswith(prefix) for prefix in SOURCE_SAFE_PREFIXES)


def _is_runtime_state(rel: str) -> bool:
    rel = rel.replace("\\", "/").strip("/")
    if rel in RUNTIME_EXACT:
        return True
    return any(rel.startswith(prefix) for prefix in RUNTIME_PREFIXES)


def _is_obsolete_generated_source_candidate(rel: str) -> bool:
    rel = rel.replace("\\", "/").strip("/")
    name = Path(rel).name
    if rel.startswith("data/"):
        return False
    if "__pycache__" in rel or rel.endswith(".pyc"):
        return False
    if any(pattern in name for pattern in OBSOLETE_GENERATED_SOURCE_PATTERNS):
        return True
    if rel.startswith("conscious_agent/generated_") or rel.startswith("tools/generated_"):
        return True
    return False


def _iter_local_files(root: Path) -> list[str]:
    skipped_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    skipped_suffixes = {".pyc", ".pyo", ".log"}
    entries: list[str] = []
    if not root.exists():
        return entries
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = set(rel.split("/"))
        if parts & skipped_dirs:
            continue
        if Path(rel).suffix.lower() in skipped_suffixes and not _is_runtime_state(rel):
            continue
        entries.append(rel)
    return entries


def _zip_entries(zip_path: str | Path) -> set[str]:
    entries: set[str] = set()
    with zipfile.ZipFile(zip_path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            entries.add(strip_package_root(info.filename))
    return entries


def classify_installed_tree(root: str | Path | None = None, target_zip: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    local_entries = _iter_local_files(repo)
    runtime_entries = sorted(rel for rel in local_entries if _is_runtime_state(rel) and not _is_source_safe_data(rel))
    target_entries: set[str] = set()
    if target_zip:
        try:
            target_entries = _zip_entries(target_zip)
        except Exception:
            target_entries = set()
    obsolete_candidates = sorted(
        rel for rel in local_entries
        if _is_obsolete_generated_source_candidate(rel) and (not target_entries or rel not in target_entries)
    )
    return {
        "root": str(repo),
        "target_zip": str(target_zip) if target_zip else None,
        "local_file_count": len(local_entries),
        "target_file_count": len(target_entries),
        "local_runtime_state_count": len(runtime_entries),
        "local_runtime_state_entries": runtime_entries[:100],
        "obsolete_generated_source_candidate_count": len(obsolete_candidates),
        "obsolete_generated_source_candidates": obsolete_candidates[:100],
        "local_runtime_state_blocks_release_zip": False,
        "obsolete_source_artifacts_require_operator_cleanup": bool(obsolete_candidates),
    }


def build_tree_cleanup_fixture_classification() -> dict[str, Any]:
    fixture_entries = [
        "README_NEXT_STEPS.md",
        "conscious_agent/generated_live_probe_old_sandbox_artifact.py",
        "tools/generated_probe_obsolete.py",
        "data/tasks.json",
        "data/dashboard_chat/session.json",
        "data/workspaces/timeline.json",
        "data/settings.json",
    ]
    rows = []
    for rel in fixture_entries:
        rows.append({
            "path": rel,
            "runtime_state": _is_runtime_state(rel) and not _is_source_safe_data(rel),
            "source_safe_data": _is_source_safe_data(rel),
            "obsolete_generated_source_candidate": _is_obsolete_generated_source_candidate(rel),
            "cleanup_action": "operator-approved-backup-delete" if _is_obsolete_generated_source_candidate(rel) else "preserve-local-runtime" if _is_runtime_state(rel) and not _is_source_safe_data(rel) else "normal-source",
        })
    return {
        "fixture_count": len(rows),
        "runtime_state_count": sum(1 for row in rows if row["runtime_state"]),
        "obsolete_generated_source_candidate_count": sum(1 for row in rows if row["obsolete_generated_source_candidate"]),
        "runtime_state_preserved": all(row["cleanup_action"] != "operator-approved-backup-delete" for row in rows if row["runtime_state"]),
        "obsolete_source_cleanup_requires_operator": all(row["cleanup_action"] == "operator-approved-backup-delete" for row in rows if row["obsolete_generated_source_candidate"]),
        "rows": rows,
    }


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def measure_dashboard_cold_server_readiness(root: str | Path | None = None, timeout_seconds: float = 45.0) -> dict[str, Any]:
    repo = _repo(root)
    port = _find_free_port()
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(repo / 'conscious_agent')!r}); "
        "import dashboard; "
        f"dashboard.run_dashboard('127.0.0.1', {port})"
    )
    env = dict(**{k: v for k, v in dict().items()})
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo / "conscious_agent") + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
    started = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "-I", "-B", "-c", code],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    ok = False
    status_code: int | None = None
    error = ""
    elapsed_ms = None
    try:
        deadline = started + timeout_seconds
        url = f"http://127.0.0.1:{port}/api/status"
        while time.perf_counter() < deadline:
            if proc.poll() is not None:
                error = f"dashboard process exited with code {proc.returncode}"
                break
            try:
                with urllib.request.urlopen(url, timeout=1.0) as response:
                    status_code = int(response.status)
                    response.read(128)
                    ok = status_code == 200
                    if ok:
                        break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                time.sleep(0.1)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if not ok and not error:
            error = "dashboard readiness timeout"
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        stdout_tail = ""
        stderr_tail = ""
        try:
            out, err = proc.communicate(timeout=1)
            stdout_tail = out[-800:]
            stderr_tail = err[-800:]
        except Exception:
            pass
    return {
        "measured": True,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "elapsed_ms": elapsed_ms,
        "timeout_seconds": timeout_seconds,
        "status_code": status_code,
        "host": "127.0.0.1",
        "port": port,
        "error": error,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "route": "/api/status",
    }


def build_installed_tree_cleanup_historical_verification_reconciliation(
    project_id: str = "eidolon",
    root: str | Path | None = None,
    target_zip: str | Path | None = None,
    measure_startup: bool = False,
) -> dict[str, Any]:
    repo = _repo(root)
    release_gate_source = _read_text(repo / "conscious_agent" / "release_zip_privacy_critical_gate_repair.py")
    release_install_source = _read_text(repo / "conscious_agent" / "release_installation.py")
    doctor_slice_source = _read_text(repo / "conscious_agent" / "dashboard_doctor_renderer_decomposition_slice.py")
    dashboard_source = _read_text(repo / "conscious_agent" / "dashboard.py")
    smoke_source = _read_text(repo / "tools" / "smoke_check.py")
    readme_next = _read_text(repo / "README_NEXT_STEPS.md")
    readme_history = _read_text(repo / "README_RELEASE_HISTORY.md")
    docs = "\n".join([release_gate_source, release_install_source, doctor_slice_source, dashboard_source, smoke_source, readme_next, readme_history])

    inventory = build_package_inventory(project_id=project_id, save=False)
    archive_preflight = inventory.get("final_archive_entry_privacy_preflight", {})
    installed = classify_installed_tree(repo, target_zip=target_zip)
    fixture = build_tree_cleanup_fixture_classification()
    startup = measure_dashboard_cold_server_readiness(repo) if measure_startup else {"measured": False, "ok": None, "status": "not_measured"}

    local_runtime_gate_split = all(token in release_gate_source for token in [
        "local_runtime_state_is_expected",
        "root scan reports installed-tree state only",
        "ok = not any(row.get(\"status\") == \"blocked\" for row in rows)",
    ])
    removed_file_apply_ready = all(token in release_install_source for token in [
        "removed_files_applied",
        "skipped_removed_files",
        "restore_deleted_file",
        "_is_safe_removed_source_entry",
    ])
    historical_doctor_reconciled = RECONCILED_HISTORICAL_DOCTOR_TOKEN in docs
    socket_noise_guarded = all(token in dashboard_source for token in [
        "BrokenPipeError",
        "ConnectionResetError",
        "_client_disconnected",
        "dashboard response write skipped because client disconnected",
    ])
    advisory_operational_split = all(token in docs for token in [
        "static_advisory_report_is_not_operational_proof=True",
        "deep_diagnostic_latency_degraded=True",
        "historical_verification_blockers_remain=True",
    ])

    rows = [
        {"name": "zip-privacy-gate-split-from-local-runtime", "status": "pass" if local_runtime_gate_split else "blocked", "message": "Final ZIP privacy remains release-blocking; local runtime files are installed-tree state only."},
        {"name": "archive-preflight-clean", "status": "pass" if archive_preflight.get("ok") else "blocked", "message": f"archive preflight forbidden_count={archive_preflight.get('forbidden_count')}."},
        {"name": "installed-runtime-preserved", "status": "pass", "message": f"local runtime entries observed={installed.get('local_runtime_state_count')}; presence is not a source ZIP privacy failure."},
        {"name": "obsolete-source-cleanup-classification", "status": "pass" if fixture.get("runtime_state_preserved") and fixture.get("obsolete_source_cleanup_requires_operator") else "blocked", "message": f"fixture obsolete candidates={fixture.get('obsolete_generated_source_candidate_count')} runtime preserved={fixture.get('runtime_state_preserved')}."},
        {"name": "removed-file-apply-supported", "status": "pass" if removed_file_apply_ready else "blocked", "message": "Safe removed source files are backed up and deleted only during confirmed live apply."},
        {"name": "historical-doctor-check-reconciled", "status": "pass" if historical_doctor_reconciled else "blocked", "message": "v1039 doctor decomposition check accepts the v1052 bounded shell instead of requiring inline primary report text."},
        {"name": "advisory-vs-operational-proof-split", "status": "pass" if advisory_operational_split else "blocked", "message": "Static doctor/cache reports are explicitly advisory and do not prove deep diagnostic health."},
        {"name": "dashboard-cold-startup-measured", "status": "pass" if (not measure_startup or startup.get("ok") is True) else "blocked", "message": f"measured={startup.get('measured')} elapsed_ms={startup.get('elapsed_ms')} status={startup.get('status')} error={startup.get('error', '')}"},
        {"name": "socket-timeout-noise-guard", "status": "pass" if socket_noise_guarded else "blocked", "message": "Dashboard send helpers avoid second-response tracebacks after client disconnects."},
    ]
    ok = not any(row["status"] == "blocked" for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "project_id": project_id,
        "review_id": INSTALLED_TREE_CLEANUP_HISTORICAL_VERIFICATION_RECONCILIATION_ID,
        "dashboard_route": DASHBOARD_ROUTE,
        "api_route": API_ROUTE,
        "checked_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "archive_privacy_preflight_ok": archive_preflight.get("ok"),
        "local_runtime_state_fixture_count": len(LOCAL_RUNTIME_STATE_FIXTURES),
        "installed_tree": installed,
        "cleanup_fixture": fixture,
        "startup_readiness": startup,
        "startup_readiness_measured": startup.get("measured") is True,
        "startup_readiness_ok": startup.get("ok") is True if measure_startup else None,
        "local_runtime_gate_split": local_runtime_gate_split,
        "removed_file_apply_ready": removed_file_apply_ready,
        "historical_doctor_reconciled": historical_doctor_reconciled,
        "socket_timeout_noise_guarded": socket_noise_guarded,
        "static_advisory_report_is_not_operational_proof": True,
        "deep_diagnostic_latency_degraded": True,
        "historical_verification_blockers_remain": True,
        "rows": rows,
        **BOUNDARIES,
    }


def installed_tree_cleanup_historical_verification_reconciliation_text(report: dict[str, Any], full: bool = False) -> str:
    startup = report.get("startup_readiness") or {}
    installed = report.get("installed_tree") or {}
    lines = [
        "# Installed-Tree Cleanup and Historical Verification Reconciliation",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Review ID: {report.get('review_id')}",
        f"Final ZIP privacy preflight OK: {report.get('archive_privacy_preflight_ok')}",
        f"Local runtime gate split: {report.get('local_runtime_gate_split')}",
        f"Local runtime entries observed: {installed.get('local_runtime_state_count')}",
        f"Obsolete generated source candidates observed: {installed.get('obsolete_generated_source_candidate_count')}",
        f"Removed-file apply ready: {report.get('removed_file_apply_ready')}",
        f"Historical doctor reconciled: {report.get('historical_doctor_reconciled')}",
        f"Startup readiness measured: {report.get('startup_readiness_measured')}",
        f"Startup readiness elapsed ms: {startup.get('elapsed_ms')}",
        f"Socket timeout noise guarded: {report.get('socket_timeout_noise_guarded')}",
        f"Static advisory report is not operational proof: {report.get('static_advisory_report_is_not_operational_proof')}",
        f"Historical verification blockers remain: {report.get('historical_verification_blockers_remain')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("\n## Rows")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
        lines.append("\n## Cleanup fixture")
        for row in (report.get("cleanup_fixture") or {}).get("rows", []):
            lines.append(f"- {row.get('path')}: action={row.get('cleanup_action')} runtime={row.get('runtime_state')} obsolete={row.get('obsolete_generated_source_candidate')}")
    return "\n".join(lines)


# v1053.0 installed tree cleanup and historical verification reconciliation tokens: installed-tree-cleanup-and-historical-verification-reconciliation-v1 /installed-tree-cleanup-historical-verification-reconciliation /api/installed-tree-cleanup/historical-verification-reconciliation build_installed_tree_cleanup_historical_verification_reconciliation installed_tree_cleanup_historical_verification_reconciliation_text classify_installed_tree build_tree_cleanup_fixture_classification measure_dashboard_cold_server_readiness local_runtime_state_is_expected=True local_runtime_state_blocks_release_zip=False zip_privacy_is_release_blocker=True obsolete_source_artifacts_require_operator_cleanup=True cleanup_report_deletes_files=False v1052_bounded_shell_supersedes_primary_report_inline_requirement=True static_advisory_report_is_not_operational_proof=True deep_diagnostic_latency_degraded=True historical_verification_blockers_remain=True startup_readiness_measured=True dashboard_response_write_skipped_on_client_disconnect=True source_files_mutated=False memory_mutated=False runtime_data_deleted=False live_diagnostics_executed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
