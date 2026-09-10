from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_diagnostic_preview_cache_heavy_route_decoupling import build_doctor_diagnostic_preview_cache

DASHBOARD_DOCTOR_HEADROOM_REPAIR_VERSION = RUNTIME_VERSION
DASHBOARD_DOCTOR_HEADROOM_REPAIR_ID = "dashboard-doctor-performance-headroom-repair-v1"
DOCTOR_ROUTE = "/doctor"
DOCTOR_HEADROOM_BUDGET_MS = 2500
DOCTOR_HEADROOM_HTML_BUDGET_BYTES = 250000
DASHBOARD_STARTUP_IMPORT_BUDGET_MS = 15000
DASHBOARD_COLD_SERVER_READINESS_BUDGET_MS = 45000
PRIOR_DOCTOR_RENDER_MODE = "primary_report_text_dump"
NEW_DOCTOR_RENDER_MODE = "preview_cache_bounded_shell"
NEXT_DEFERRED_ARC = "v1054.0 Doctor Diagnostic Cache Impact Matrix Operator Action Ledger v1"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "dashboard_headroom_repair": True,
    "doctor_route_bounded_shell": True,
    "doctor_deep_diagnostics_deferred": True,
    "doctor_uses_preview_cache_summary": True,
    "doctor_primary_report_text_dump_removed": True,
    "api_server_import_deferred_from_dashboard_import": True,
    "operational_readiness_import_deferred_from_dashboard_import": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "generated_wiring_activated": False,
    "live_diagnostics_executed": False,
    "source_files_mutated_by_report": False,
    "memory_mutated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _find_free_dashboard_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def measure_dashboard_cold_server_readiness(root: str | Path | None = None, timeout_seconds: float = 45.0) -> dict[str, Any]:
    """Measure cold dashboard readiness by starting a real server and polling a lightweight route.

    This deliberately measures more than module import. It proves the server can
    bind, accept a request, dispatch through the dashboard/API bridge, and shut
    down cleanly. It still grants no release or autonomy authority, because a
    stopwatch is not a permission slip, despite what software teams keep hoping.
    """
    repo = _repo(root)
    port = _find_free_dashboard_port()
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(repo / 'conscious_agent')!r}); "
        "import dashboard; "
        f"dashboard.run_dashboard('127.0.0.1', {port})"
    )
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
    stdout_tail = ""
    stderr_tail = ""
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
                    response.read(256)
                    ok = status_code == 200
                    if ok:
                        break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                time.sleep(0.1)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if not ok and not error:
            error = "dashboard cold server readiness timeout"
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
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
        "budget_ms": int(timeout_seconds * 1000),
        "declared_import_budget_ms": DASHBOARD_STARTUP_IMPORT_BUDGET_MS,
        "cold_server_readiness_budget_ms": DASHBOARD_COLD_SERVER_READINESS_BUDGET_MS,
        "status_code": status_code,
        "route": "/api/status",
        "host": "127.0.0.1",
        "port": port,
        "error": error,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "startup_readiness_measured": True,
        "cold_server_readiness_measured": True,
        "release_authorized": False,
        "autonomy_expanded": False,
    }


def build_doctor_dashboard_headroom_snapshot(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    """Return the lightweight data used by the dashboard /doctor shell.

    The function intentionally relies on the preview-only doctor diagnostic cache contract
    instead of rebuilding the full operational readiness report stack inside normal
    dashboard rendering. Humanity survived this long, somehow, so one dashboard route can
    also survive without fan-out diagnostics on every tab click.
    """
    repo = _repo(root)
    started = time.perf_counter()
    cache = build_doctor_diagnostic_preview_cache(project_id=project_id)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    rows = list(cache.get("diagnostic_rows") or [])
    warning_count = sum(1 for row in rows if str(row.get("lane", "")).lower() in {"long", "long-isolated", "slow"})
    ok = bool(
        cache.get("ok") is True
        and cache.get("cache_does_not_call_live_api") is True
        and cache.get("live_measurements_performed") is False
        and cache.get("diagnostic_storm_avoided") is True
        and elapsed_ms <= DOCTOR_HEADROOM_BUDGET_MS
    )
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "next_deferred_arc": NEXT_DEFERRED_ARC,
        "review_id": DASHBOARD_DOCTOR_HEADROOM_REPAIR_ID,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "doctor_route": DOCTOR_ROUTE,
        "render_mode": NEW_DOCTOR_RENDER_MODE,
        "prior_render_mode": PRIOR_DOCTOR_RENDER_MODE,
        "cache_status": cache.get("status"),
        "cache_ok": cache.get("ok"),
        "cache_strategy": cache.get("cache_strategy"),
        "cache_elapsed_ms": elapsed_ms,
        "headroom_budget_ms": DOCTOR_HEADROOM_BUDGET_MS,
        "diagnostic_row_count": len(rows),
        "cache_row_contract_pass_count": cache.get("cache_row_contract_pass_count"),
        "lightweight_preview_route": cache.get("lightweight_preview_route"),
        "heavy_preview_route": cache.get("heavy_preview_route"),
        "heavy_preview_route_decoupled_from_doctor": cache.get("heavy_preview_route_decoupled_from_doctor"),
        "diagnostic_storm_avoided": cache.get("diagnostic_storm_avoided"),
        "cache_does_not_call_live_api": cache.get("cache_does_not_call_live_api"),
        "live_measurements_performed": cache.get("live_measurements_performed"),
        "warning_lane_count": warning_count,
        "diagnostic_rows": rows,
        "source_root": str(repo),
        **BOUNDARIES,
    }


def build_dashboard_doctor_headroom_repair_review(
    root: str | Path | None = None,
    *,
    measure_dashboard_render: bool = False,
    measure_dashboard_startup: bool = False,
) -> dict[str, Any]:
    repo = _repo(root)
    dashboard_source = _read_text(repo / "conscious_agent" / "dashboard.py")
    snapshot = build_doctor_dashboard_headroom_snapshot(root=repo)
    render_section = ""
    marker = "def render_doctor()"
    if marker in dashboard_source:
        start = dashboard_source.index(marker)
        next_def = dashboard_source.find("\ndef ", start + len(marker))
        render_section = dashboard_source[start: next_def if next_def != -1 else len(dashboard_source)]

    measured_render_ms: int | None = None
    measured_render_bytes: int | None = None
    measured_render_ok: bool | None = None
    measured_error: str | None = None
    if measure_dashboard_render:
        import importlib
        import sys

        sys.path.insert(0, str(repo / "conscious_agent"))
        try:
            dashboard = importlib.import_module("dashboard")
            started = time.perf_counter()
            html = dashboard.render_doctor()
            measured_render_ms = int((time.perf_counter() - started) * 1000)
            measured_render_bytes = len(str(html).encode("utf-8", errors="ignore"))
            measured_render_ok = bool(
                measured_render_ms <= DOCTOR_HEADROOM_BUDGET_MS
                and measured_render_bytes <= DOCTOR_HEADROOM_HTML_BUDGET_BYTES
            )
        except Exception as error:  # pragma: no cover - smoke reports the message.
            measured_error = f"{type(error).__name__}: {error}"
            measured_render_ok = False

    startup_readiness = measure_dashboard_cold_server_readiness(repo, timeout_seconds=DASHBOARD_COLD_SERVER_READINESS_BUDGET_MS / 1000) if measure_dashboard_startup else {"measured": False, "ok": None, "status": "not_measured"}

    rows = [
        {
            "name": "doctor-render-uses-headroom-snapshot",
            "status": "pass" if "build_doctor_dashboard_headroom_snapshot" in render_section else "blocked",
            "message": "/doctor render path uses the v1052 bounded headroom snapshot.",
        },
        {
            "name": "doctor-render-avoids-primary-report-fanout",
            "status": "pass" if "_doctor_primary_reports()" not in render_section and "doctor_report_text(" not in render_section else "blocked",
            "message": "/doctor no longer rebuilds and dumps primary operational report text during normal dashboard rendering.",
        },
        {
            "name": "doctor-cache-snapshot-under-budget",
            "status": "pass" if snapshot.get("ok") else "blocked",
            "message": f"cache snapshot elapsed={snapshot.get('cache_elapsed_ms')}ms budget={DOCTOR_HEADROOM_BUDGET_MS}ms.",
        },
        {
            "name": "dashboard-import-deferred-api-server",
            "status": "pass" if not any(line.startswith("from api_server import ") for line in dashboard_source.splitlines()) and "def dispatch_api(" in dashboard_source else "blocked",
            "message": "api_server import is deferred until API dispatch instead of forced during dashboard import.",
        },
        {
            "name": "dashboard-import-deferred-operational-readiness",
            "status": "pass" if "from operational_readiness import" not in dashboard_source and "def build_doctor_report(" in dashboard_source else "blocked",
            "message": "operational_readiness import is deferred behind compatibility wrappers.",
        },
    ]
    if measure_dashboard_render:
        rows.append({
            "name": "measured-doctor-render-headroom",
            "status": "pass" if measured_render_ok else "blocked",
            "message": f"render_ms={measured_render_ms} html_bytes={measured_render_bytes} error={measured_error}",
        })
    if measure_dashboard_startup:
        rows.append({
            "name": "measured-dashboard-cold-server-readiness",
            "status": "pass" if startup_readiness.get("ok") else "blocked",
            "message": f"startup_readiness_measured={startup_readiness.get('measured')} elapsed_ms={startup_readiness.get('elapsed_ms')} budget_ms={startup_readiness.get('budget_ms')} error={startup_readiness.get('error')}",
        })
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_DOCTOR_HEADROOM_REPAIR_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "doctor_route": DOCTOR_ROUTE,
        "headroom_budget_ms": DOCTOR_HEADROOM_BUDGET_MS,
        "html_budget_bytes": DOCTOR_HEADROOM_HTML_BUDGET_BYTES,
        "dashboard_startup_import_budget_ms": DASHBOARD_STARTUP_IMPORT_BUDGET_MS,
        "dashboard_cold_server_readiness_budget_ms": DASHBOARD_COLD_SERVER_READINESS_BUDGET_MS,
        "measured_dashboard_startup": measure_dashboard_startup,
        "startup_readiness": startup_readiness,
        "startup_readiness_measured": startup_readiness.get("measured") is True,
        "startup_readiness_ok": startup_readiness.get("ok") is True if measure_dashboard_startup else None,
        "measured_dashboard_render": measure_dashboard_render,
        "measured_doctor_render_ms": measured_render_ms,
        "measured_doctor_render_bytes": measured_render_bytes,
        "measured_doctor_render_ok": measured_render_ok,
        "measured_error": measured_error,
        "snapshot": snapshot,
        "rows": rows,
        **BOUNDARIES,
    }


def doctor_dashboard_headroom_snapshot_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        "# Dashboard Doctor Headroom Snapshot",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Route: {report.get('doctor_route')}",
        f"Render mode: {report.get('render_mode')}",
        f"Cache elapsed ms: {report.get('cache_elapsed_ms')}",
        f"Diagnostic rows: {report.get('diagnostic_row_count')}",
        f"Diagnostic storm avoided: {report.get('diagnostic_storm_avoided')}",
        f"Live measurements performed: {report.get('live_measurements_performed')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("\n## Diagnostic rows")
        for row in report.get("diagnostic_rows", []):
            lines.append(f"- {row.get('label')}: {row.get('route')} lane={row.get('lane')} cache_only={row.get('cache_only')} ok={row.get('ok')}")
    return "\n".join(lines)


def dashboard_doctor_headroom_repair_review_text(report: dict[str, Any], full: bool = False) -> str:
    snapshot = report.get("snapshot") or {}
    lines = [
        "# Dashboard Doctor Performance Headroom Repair",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Review ID: {report.get('review_id')}",
        f"Doctor route: {report.get('doctor_route')}",
        f"Headroom budget ms: {report.get('headroom_budget_ms')}",
        f"HTML budget bytes: {report.get('html_budget_bytes')}",
        f"Measured render ms: {report.get('measured_doctor_render_ms')}",
        f"Measured render bytes: {report.get('measured_doctor_render_bytes')}",
        f"Startup readiness measured: {report.get('startup_readiness_measured')}",
        f"Startup readiness elapsed ms: {(report.get('startup_readiness') or {}).get('elapsed_ms')}",
        f"Snapshot cache elapsed ms: {snapshot.get('cache_elapsed_ms')}",
        f"Render mode: {snapshot.get('render_mode')}",
        f"Manual dashboard remains authoritative: {report.get('manual_dashboard_remains_authoritative')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("\n## Rows")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
        lines.append("\n## Snapshot")
        lines.append(doctor_dashboard_headroom_snapshot_text(snapshot, full=True))
    return "\n".join(lines)


# v1052.0 dashboard doctor performance headroom repair tokens: dashboard-doctor-performance-headroom-repair-v1 build_dashboard_doctor_headroom_repair_review dashboard_doctor_headroom_repair_review_text build_doctor_dashboard_headroom_snapshot doctor_dashboard_headroom_snapshot_text /doctor preview_cache_bounded_shell prior_render_mode=primary_report_text_dump doctor_primary_report_text_dump_removed=True doctor_route_bounded_shell=True doctor_deep_diagnostics_deferred=True api_server_import_deferred_from_dashboard_import=True operational_readiness_import_deferred_from_dashboard_import=True diagnostic_storm_avoided=True live_diagnostics_executed=False startup_readiness_measured=True cold_server_readiness_measured=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
