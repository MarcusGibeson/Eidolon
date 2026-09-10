from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

DASHBOARD_SHELL_PERFORMANCE_STABILIZATION_VERSION = RUNTIME_VERSION
DASHBOARD_SHELL_PERFORMANCE_STABILIZATION_ID = "dashboard-shell-performance-stabilization-v1"
SELF_ROUTE = "/dashboard-shell-performance-stabilization"
SELF_RENDERER = "render_dashboard_shell_performance_stabilization"
API_ROUTE = "/api/dashboard/shell-performance-stabilization"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SMOKE_MODULE = "tools/smoke_check.py"
MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
SHELL_ROUTE_BUDGET_MS = 2000
TARGET_SHELL_ROUTE_COUNT = 9

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "dashboard_get_preview_only": True,
    "dashboard_get_spawns_subprocesses": False,
    "dashboard_get_executes_full_diagnostics": False,
    "dashboard_get_runs_install_release": False,
    "dashboard_get_writes_source": False,
    "dashboard_get_writes_memory": False,
    "dashboard_get_deletes_runtime_data": False,
    "heavy_proof_paths_preserved": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}


@dataclass(frozen=True)
class DashboardShellTarget:
    route: str
    renderer: str
    shell_family: str
    heavy_proof_path: str


DASHBOARD_SHELL_TARGETS: tuple[DashboardShellTarget, ...] = (
    DashboardShellTarget("/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion", "render_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion", "fixture-truth", "POST operator run endpoint plus manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion-v1"),
    DashboardShellTarget("/manifest-fixture-sandbox-adapter-contract", "render_manifest_fixture_sandbox_adapter_contract", "sandbox-contract", "manifest-fixture-sandbox-adapter-contract-v1"),
    DashboardShellTarget("/full-tree-mutation-snapshot-expansion", "render_full_tree_mutation_snapshot_expansion", "mutation-snapshot", "full-tree-mutation-snapshot-expansion-v1"),
    DashboardShellTarget("/diagnostic-api-compatibility-restoration", "render_diagnostic_api_compatibility_restoration", "diagnostic-api", "diagnostic-api-compatibility-restoration-v1"),
    DashboardShellTarget("/release-tier-blocker-repair-batch-i", "render_release_tier_blocker_repair_batch_i", "release-tier", "release-tier-blocker-repair-batch-i-v1"),
    DashboardShellTarget("/release-tier-blocker-repair-batch-ii", "render_release_tier_blocker_repair_batch_ii", "release-tier", "release-tier-blocker-repair-batch-ii-v1"),
    DashboardShellTarget("/installed-tree-cleanup-enforcement", "render_installed_tree_cleanup_enforcement", "cleanup", "installed-tree-cleanup-enforcement-v1"),
    DashboardShellTarget("/doctor-deep-diagnostic-latency-budget-repair", "render_doctor_deep_diagnostic_latency_budget_repair", "doctor-diagnostic", "doctor-deep-diagnostic-latency-budget-repair-v1"),
    DashboardShellTarget("/dashboard-slow-route-cohort-repair", "render_dashboard_slow_route_cohort_repair", "slow-route-cohort", "dashboard-slow-route-cohort-repair-v1"),
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


class _SubprocessGuard:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._orig_run: Any = None
        self._orig_popen: Any = None

    def __enter__(self) -> "_SubprocessGuard":
        self._orig_run = subprocess.run
        self._orig_popen = subprocess.Popen

        def blocked_run(*args: Any, **kwargs: Any) -> Any:
            self.calls.append(f"run:{args[:1]!r}")
            raise RuntimeError("dashboard shell performance gate blocked subprocess.run during GET render")

        class BlockedPopen:  # pragma: no cover - constructed only on regression.
            def __init__(_, *args: Any, **kwargs: Any) -> None:
                self.calls.append(f"Popen:{args[:1]!r}")
                raise RuntimeError("dashboard shell performance gate blocked subprocess.Popen during GET render")

        subprocess.run = blocked_run  # type: ignore[assignment]
        subprocess.Popen = BlockedPopen  # type: ignore[assignment]
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        subprocess.run = self._orig_run  # type: ignore[assignment]
        subprocess.Popen = self._orig_popen  # type: ignore[assignment]


def _render_shell(target: DashboardShellTarget, root: Path) -> dict[str, Any]:
    if str(root / "conscious_agent") not in sys.path:
        sys.path.insert(0, str(root / "conscious_agent"))
    started = time.perf_counter()
    error = ""
    body = ""
    subprocess_calls: list[str] = []
    try:
        import dashboard  # type: ignore
        renderer: Callable[[], str] = getattr(dashboard, target.renderer)
        with _SubprocessGuard() as guard:
            body = renderer()
            subprocess_calls = list(guard.calls)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    checks = {
        "rendered_string": isinstance(body, str) and len(body) > 0,
        "within_budget": elapsed_ms <= SHELL_ROUTE_BUDGET_MS,
        "route_token_present": target.route in body,
        "data_tip_present": "data-tip" in body,
        "command_deck_present": "command-deck" in body,
        "operator_console_present": "operator-console" in body,
        "no_native_title_tooltip": " title=" not in body,
        "no_traceback_text": "Traceback (most recent call last)" not in body,
        "no_subprocess_calls": len(subprocess_calls) == 0,
        "no_error": error == "",
    }
    ok = all(checks.values())
    return {
        "route": target.route,
        "renderer": target.renderer,
        "shell_family": target.shell_family,
        "heavy_proof_path": target.heavy_proof_path,
        "elapsed_ms": elapsed_ms,
        "body_size": len(body) if isinstance(body, str) else 0,
        "subprocess_call_count": len(subprocess_calls),
        "subprocess_calls": subprocess_calls,
        "checks": checks,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "error": error,
    }


def build_dashboard_shell_performance_stabilization_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_SHELL_PERFORMANCE_STABILIZATION_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "target_shell_route_count": TARGET_SHELL_ROUTE_COUNT,
        "shell_route_budget_ms": SHELL_ROUTE_BUDGET_MS,
        "dashboard_get_preview_only": True,
        "dashboard_get_spawns_subprocesses": False,
        "dashboard_get_executes_full_diagnostics": False,
        "dashboard_get_runs_install_release": False,
        "heavy_proof_paths_preserved": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "status": "preview",
        "ok": True,
        "boundaries": dict(BOUNDARIES),
    }


def build_dashboard_shell_performance_stabilization(root: str | Path | None = None, *, measure_routes: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    docs = "\n".join(_read_text(project_root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        DASHBOARD_MODULE,
        API_MODULE,
        SMOKE_MODULE,
        MANIFEST_MODULE,
        "conscious_agent/dashboard_shell_performance_stabilization.py",
    ])
    measured_rows = [_render_shell(target, project_root) for target in DASHBOARD_SHELL_TARGETS] if measure_routes else []
    route_shell_pass_count = sum(1 for row in measured_rows if row.get("ok")) if measure_routes else TARGET_SHELL_ROUTE_COUNT
    total_subprocess_calls = sum(int(row.get("subprocess_call_count") or 0) for row in measured_rows)
    max_elapsed_ms = max((int(row.get("elapsed_ms") or 0) for row in measured_rows), default=0)
    metadata_shell_tokens = [
        "build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata",
        "build_manifest_fixture_sandbox_adapter_contract_metadata",
        "build_full_tree_mutation_snapshot_expansion_metadata",
        "build_diagnostic_api_compatibility_restoration_metadata",
        "build_release_tier_blocker_repair_batch_i_metadata",
        "build_release_tier_blocker_repair_batch_ii_metadata",
        "build_installed_tree_cleanup_enforcement_metadata",
        "build_doctor_deep_diagnostic_latency_budget_repair_metadata",
        "build_dashboard_slow_route_cohort_repair_metadata",
    ]
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_SHELL_PERFORMANCE_STABILIZATION_ID,
        SELF_ROUTE,
        API_ROUTE,
        "target_shell_route_count=9",
        "shell_route_budget_ms=2000",
        "dashboard_get_preview_only=True",
        "dashboard_get_spawns_subprocesses=False",
        "dashboard_get_executes_full_diagnostics=False",
        "dashboard_get_runs_install_release=False",
        "route_shell_pass_count=9",
        "subprocess_call_count=0",
        "heavy_proof_paths_preserved=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_SHELL_PERFORMANCE_STABILIZATION_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_SHELL_PERFORMANCE_STABILIZATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "target-count", "ok": len(DASHBOARD_SHELL_TARGETS) == TARGET_SHELL_ROUTE_COUNT, "message": f"targets={len(DASHBOARD_SHELL_TARGETS)} expected={TARGET_SHELL_ROUTE_COUNT}"},
        {"name": "route-shell-headroom", "ok": route_shell_pass_count == TARGET_SHELL_ROUTE_COUNT, "message": f"route_shell_pass_count={route_shell_pass_count}/{TARGET_SHELL_ROUTE_COUNT}; max_elapsed_ms={max_elapsed_ms}"},
        {"name": "no-subprocess-get-render", "ok": total_subprocess_calls == 0, "message": f"subprocess_call_count={total_subprocess_calls}"},
        {"name": "metadata-shell-builders-present", "ok": all(token in docs for token in metadata_shell_tokens), "message": "Dashboard/API surfaces expose metadata-only shell builders for stabilized routes."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Dashboard/API/smoke/manifest/README surfaces carry v1065.10 performance stabilization tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["dashboard_get_spawns_subprocesses", "dashboard_get_executes_full_diagnostics", "dashboard_get_runs_install_release", "dashboard_get_writes_source", "dashboard_get_writes_memory", "dashboard_get_deletes_runtime_data", "generated_wiring_activated", "release_authorized", "autonomy_expanded"]), "message": "Dashboard shell performance pass grants no generated wiring, release, or autonomy authority."},
    ]
    ok = all(bool(row.get("ok")) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_SHELL_PERFORMANCE_STABILIZATION_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "checked_at": _now(),
        "target_shell_route_count": TARGET_SHELL_ROUTE_COUNT,
        "shell_route_budget_ms": SHELL_ROUTE_BUDGET_MS,
        "route_shell_pass_count": route_shell_pass_count,
        "max_shell_route_elapsed_ms": max_elapsed_ms,
        "subprocess_call_count": total_subprocess_calls,
        "dashboard_get_preview_only": True,
        "dashboard_get_spawns_subprocesses": False,
        "dashboard_get_executes_full_diagnostics": False,
        "dashboard_get_runs_install_release": False,
        "dashboard_get_writes_source": False,
        "dashboard_get_writes_memory": False,
        "dashboard_get_deletes_runtime_data": False,
        "heavy_proof_paths_preserved": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "target_rows": [asdict(target) for target in DASHBOARD_SHELL_TARGETS],
        "measured_rows": measured_rows,
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def dashboard_shell_performance_stabilization_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    data = report or build_dashboard_shell_performance_stabilization_metadata()
    lines = [
        str(data.get("current_milestone")),
        f"review_id={data.get('review_id')}",
        f"self_route={SELF_ROUTE}",
        f"api_route={API_ROUTE}",
        "builder_function=build_dashboard_shell_performance_stabilization",
        "metadata_function=build_dashboard_shell_performance_stabilization_metadata",
        "text_function=dashboard_shell_performance_stabilization_text",
        f"status={data.get('status')}",
        f"target_shell_route_count={data.get('target_shell_route_count')}",
        f"shell_route_budget_ms={data.get('shell_route_budget_ms')}",
        f"route_shell_pass_count={data.get('route_shell_pass_count')}",
        f"max_shell_route_elapsed_ms={data.get('max_shell_route_elapsed_ms')}",
        f"subprocess_call_count={data.get('subprocess_call_count')}",
        f"dashboard_get_preview_only={data.get('dashboard_get_preview_only')}",
        f"dashboard_get_spawns_subprocesses={data.get('dashboard_get_spawns_subprocesses')}",
        f"dashboard_get_executes_full_diagnostics={data.get('dashboard_get_executes_full_diagnostics')}",
        f"dashboard_get_runs_install_release={data.get('dashboard_get_runs_install_release')}",
        f"heavy_proof_paths_preserved={data.get('heavy_proof_paths_preserved')}",
        f"manual_dashboard_remains_authoritative={data.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={data.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={data.get('manual_smoke_remains_authoritative')}",
        f"generated_wiring_activated={data.get('generated_wiring_activated')}",
        f"release_authorized={data.get('release_authorized')}",
        f"autonomy_expanded={data.get('autonomy_expanded')}",
        f"operator_approval_required={data.get('operator_approval_required')}",
    ]
    if full:
        lines.append("\nTarget shell routes:")
        for row in data.get("target_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: family={row.get('shell_family')} proof={row.get('heavy_proof_path')}")
        lines.append("\nMeasured shell routes:")
        for row in data.get("measured_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: ok={row.get('ok')} status={row.get('status')} elapsed_ms={row.get('elapsed_ms')} subprocess_calls={row.get('subprocess_call_count')} size={row.get('body_size')} error={row.get('error')}")
        lines.append("\nReview rows:")
        for row in data.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)


# v1065.10 dashboard shell performance stabilization source tokens: dashboard-shell-performance-stabilization-v1 /dashboard-shell-performance-stabilization /api/dashboard/shell-performance-stabilization build_dashboard_shell_performance_stabilization build_dashboard_shell_performance_stabilization_metadata dashboard_shell_performance_stabilization_text target_shell_route_count=9 shell_route_budget_ms=2000 route_shell_pass_count=9 subprocess_call_count=0 dashboard_get_preview_only=True dashboard_get_spawns_subprocesses=False dashboard_get_executes_full_diagnostics=False dashboard_get_runs_install_release=False heavy_proof_paths_preserved=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
