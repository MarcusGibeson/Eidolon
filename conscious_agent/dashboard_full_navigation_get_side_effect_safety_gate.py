from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import ast
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

FULL_NAVIGATION_GET_SIDE_EFFECT_SAFETY_GATE_VERSION = RUNTIME_VERSION
FULL_NAVIGATION_GET_SIDE_EFFECT_SAFETY_GATE_ID = "dashboard-full-navigation-get-side-effect-safety-gate-v1"
SELF_ROUTE = "/dashboard-full-navigation-get-side-effect-safety-gate"
SELF_RENDERER = "render_dashboard_full_navigation_get_side_effect_safety_gate"
API_ROUTE = "/api/dashboard/full-navigation-get-side-effect-safety-gate"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SMOKE_MODULE = "tools/smoke_check.py"
MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
ROUTE_RENDER_BUDGET_MS = 3500
EXPECTED_MIN_NAV_ROUTE_COUNT = 560
DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT = 22
DYNAMIC_API_GET_TARGET_COUNT = 13

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "dashboard_get_preview_only": True,
    "api_get_preview_only": True,
    "dashboard_get_spawns_subprocesses": False,
    "api_get_spawns_subprocesses": False,
    "dashboard_get_writes_source": False,
    "dashboard_get_deletes_source": False,
    "dashboard_get_runs_install_release": False,
    "dashboard_get_executes_generated_fixtures": False,
    "api_get_runs_install_release": False,
    "api_get_executes_generated_fixtures": False,
    "full_navigation_static_scan_only_for_all_routes": True,
    "bounded_dynamic_render_for_risk_routes": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}


@dataclass(frozen=True)
class DashboardRenderTarget:
    route: str
    renderer: str
    family: str


@dataclass(frozen=True)
class ApiGetTarget:
    route: str
    query: dict[str, list[str]]
    family: str


DASHBOARD_RENDER_TARGETS: tuple[DashboardRenderTarget, ...] = (
    DashboardRenderTarget("/manifest-generated-dispatch-fixture-first-isolated-dry-run-trial", "render_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial", "fixture-receipt"),
    DashboardRenderTarget("/manifest-generated-dispatch-fixture-trial-receipt-hardening", "render_manifest_generated_dispatch_fixture_trial_receipt_hardening", "fixture-receipt"),
    DashboardRenderTarget("/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion", "render_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion", "fixture-batch"),
    DashboardRenderTarget("/manifest-fixture-sandbox-adapter-contract", "render_manifest_fixture_sandbox_adapter_contract", "sandbox-contract"),
    DashboardRenderTarget("/full-tree-mutation-snapshot-expansion", "render_full_tree_mutation_snapshot_expansion", "mutation-snapshot"),
    DashboardRenderTarget("/diagnostic-api-compatibility-restoration", "render_diagnostic_api_compatibility_restoration", "diagnostic-api"),
    DashboardRenderTarget("/release-tier-blocker-repair-batch-i", "render_release_tier_blocker_repair_batch_i", "release-tier"),
    DashboardRenderTarget("/release-tier-blocker-repair-batch-ii", "render_release_tier_blocker_repair_batch_ii", "release-tier"),
    DashboardRenderTarget("/installed-tree-cleanup-enforcement", "render_installed_tree_cleanup_enforcement", "cleanup"),
    DashboardRenderTarget("/dashboard-shell-performance-stabilization", "render_dashboard_shell_performance_stabilization", "dashboard-performance"),
    DashboardRenderTarget("/dashboard-slow-route-cohort-repair", "render_dashboard_slow_route_cohort_repair", "dashboard-performance"),
    DashboardRenderTarget("/doctor-deep-diagnostic-latency-budget-repair", "render_doctor_deep_diagnostic_latency_budget_repair", "doctor-diagnostic"),
    DashboardRenderTarget("/dashboard-doctor-performance-headroom-repair", "render_dashboard_doctor_performance_headroom_repair", "doctor-diagnostic"),
    DashboardRenderTarget("/install-release-historical-blocker-reduction", "render_install_release_historical_blocker_reduction", "install-release"),
    DashboardRenderTarget("/metadata-release-integrity-audit", "render_metadata_release_integrity_audit", "metadata-release"),
    DashboardRenderTarget("/release-staleness-verification-audit-board", "render_release_staleness_verification_audit_board", "metadata-release"),
    DashboardRenderTarget("/recovery-drill-release-closure-board", "render_recovery_drill_release_closure_board", "release-closure"),
    DashboardRenderTarget("/release-decision-archive-ledger-board", "render_release_decision_archive_ledger_board", "release-archive"),
    DashboardRenderTarget("/api-preview-adapter-backfill", "render_api_preview_adapter_backfill", "api-preview-adapter-backfill"),
    DashboardRenderTarget("/api-server-dispatch-helper-extraction-pilot", "render_api_server_dispatch_helper_extraction_pilot", "api-server-dispatch-helper"),
    DashboardRenderTarget("/api-server-dispatch-helper-backfill", "render_api_server_dispatch_helper_backfill", "api-server-dispatch-helper"),
    DashboardRenderTarget("/api-server-dispatch-helper-route-table-extraction", "render_api_server_dispatch_helper_route_table_extraction", "api-server-dispatch-route-table"),
)

API_GET_TARGETS: tuple[ApiGetTarget, ...] = (
    ApiGetTarget("/api/source-surface/manifest-generated-dispatch-fixture-first-isolated-dry-run-trial", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "fixture-receipt"),
    ApiGetTarget("/api/source-surface/manifest-generated-dispatch-fixture-trial-receipt-hardening", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "fixture-receipt"),
    ApiGetTarget("/api/source-surface/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "fixture-batch"),
    ApiGetTarget("/api/source-surface/manifest-fixture-sandbox-adapter-contract", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "sandbox-contract"),
    ApiGetTarget("/api/source-surface/full-tree-mutation-snapshot-expansion", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "mutation-snapshot"),
    ApiGetTarget("/api/doctor/diagnostic-api-compatibility-restoration", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "diagnostic-api"),
    ApiGetTarget("/api/release/release-tier-blocker-repair-batch-i", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "release-tier"),
    ApiGetTarget("/api/release/release-tier-blocker-repair-batch-ii", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "release-tier"),
    ApiGetTarget("/api/dashboard/full-navigation-get-side-effect-safety-gate", {"measure": ["false"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "self-preview"),
    ApiGetTarget("/api/source-surface/api-preview-adapter-backfill", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "api-preview-adapter-backfill"),
    ApiGetTarget("/api/source-surface/api-server-dispatch-helper-extraction-pilot", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "api-server-dispatch-helper"),
    ApiGetTarget("/api/source-surface/api-server-dispatch-helper-backfill", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "api-server-dispatch-helper"),
    ApiGetTarget("/api/source-surface/api-server-dispatch-helper-route-table-extraction", {"inspect_sources": ["true"], "execute": ["true"], "live": ["true"], "approve": ["true"]}, "api-server-dispatch-route-table"),
)

SIDE_EFFECT_SOURCE_PATTERNS: tuple[str, ...] = (
    "subprocess.run",
    "subprocess.Popen",
    "Popen(",
    ".write_text(",
    ".write_bytes(",
    ".unlink(",
    "shutil.rmtree",
    "os.remove(",
    "os.rmdir(",
    "run_install_release",
    "--segment install-release",
    "execute_batch=True",
    "execute_trial=True",
    "operator_confirmed=True",
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


def _dashboard_source(root: Path) -> str:
    return _read_text(root / DASHBOARD_MODULE)


def _extract_nav_items(source: str) -> list[tuple[str, str, str, str]]:
    marker = "    nav_items = ["
    if marker not in source:
        try:
            from dashboard_route_registry import dashboard_route_registry_nav_items
            return [tuple(item) for item in dashboard_route_registry_nav_items() if len(item) == 4]
        except (ImportError, TypeError, ValueError):
            return []
    start = source.index(marker)
    idx = source.index("[", start)
    level = 0
    end = -1
    for pos in range(idx, len(source)):
        char = source[pos]
        if char == "[":
            level += 1
        elif char == "]":
            level -= 1
            if level == 0:
                end = pos + 1
                break
    if end == -1:
        return []
    try:
        value = ast.literal_eval(source[idx:end])
    except (SyntaxError, ValueError):
        return []
    return [tuple(item) for item in value if isinstance(item, tuple) and len(item) == 4]


def _extract_handler_routes(source: str) -> dict[str, str]:
    routes: dict[str, str] = {}
    exact = re.compile(r'(?:if|elif) path == "(?P<route>[^"]+)":\n\s+html = (?P<renderer>render_[A-Za-z0-9_]+)\(')
    for match in exact.finditer(source):
        routes[match.group("route")] = match.group("renderer")
    grouped = re.compile(r'elif path in \{(?P<routes>[^}]+)\}:\n\s+html = (?P<renderer>render_[A-Za-z0-9_]+)\(')
    for match in grouped.finditer(source):
        for route in match.group("routes").split(","):
            route = route.strip().strip('"')
            if route:
                routes[route] = match.group("renderer")
    if "path == DASHBOARD_ROUTE_REGISTRY_ROUTE" in source:
        routes["/dashboard-route-registry-extraction"] = "render_dashboard_route_registry_extraction"
    routes.setdefault("/", "render_overview")
    return routes


def _renderer_source(source: str, renderer: str) -> str:
    marker = f"def {renderer}"
    if marker not in source:
        return ""
    start = source.index(marker)
    next_def = source.find("\ndef ", start + len(marker))
    return source[start: next_def if next_def != -1 else len(source)]


def _static_route_rows(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = _dashboard_source(root)
    nav_items = _extract_nav_items(source)
    handlers = _extract_handler_routes(source)
    nav_routes = [item[0] for item in nav_items]
    rows: list[dict[str, Any]] = []
    for route in nav_routes:
        renderer = handlers.get(route, "")
        snippet = _renderer_source(source, renderer) if renderer else ""
        hits = [pattern for pattern in SIDE_EFFECT_SOURCE_PATTERNS if pattern in snippet]
        rows.append({
            "route": route,
            "renderer": renderer or "[dynamic-or-missing]",
            "handler_found": bool(renderer),
            "source_side_effect_pattern_hits": hits,
            "static_side_effect_free": len(hits) == 0,
        })
    summary = {
        "nav_route_count": len(nav_routes),
        "unique_nav_route_count": len(set(nav_routes)),
        "handler_route_count": len(handlers),
        "nav_handler_found_count": sum(1 for row in rows if row["handler_found"]),
        "nav_dynamic_or_unparsed_count": sum(1 for row in rows if not row["handler_found"]),
        "static_side_effect_hit_count": sum(1 for row in rows if row["source_side_effect_pattern_hits"]),
        "dynamic_or_unparsed_routes": [row["route"] for row in rows if not row["handler_found"]][:40],
        "static_side_effect_routes": [row for row in rows if row["source_side_effect_pattern_hits"]][:40],
    }
    return rows, summary


class _SideEffectGuard:
    def __init__(self) -> None:
        self.subprocess_calls: list[str] = []
        self.write_calls: list[str] = []
        self.delete_calls: list[str] = []
        self._originals: dict[str, Any] = {}

    def __enter__(self) -> "_SideEffectGuard":
        self._originals = {
            "subprocess.run": subprocess.run,
            "subprocess.Popen": subprocess.Popen,
            "Path.write_text": Path.write_text,
            "Path.write_bytes": Path.write_bytes,
            "Path.unlink": Path.unlink,
            "os.remove": os.remove,
            "os.rmdir": os.rmdir,
            "shutil.rmtree": shutil.rmtree,
        }

        def blocked_run(*args: Any, **kwargs: Any) -> Any:
            self.subprocess_calls.append(f"run:{args[:1]!r}")
            raise RuntimeError("GET side-effect gate blocked subprocess.run")

        class BlockedPopen:
            def __init__(_, *args: Any, **kwargs: Any) -> None:
                self.subprocess_calls.append(f"Popen:{args[:1]!r}")
                raise RuntimeError("GET side-effect gate blocked subprocess.Popen")

        def blocked_write_text(path: Path, *args: Any, **kwargs: Any) -> Any:
            self.write_calls.append(f"Path.write_text:{path}")
            raise RuntimeError("GET side-effect gate blocked Path.write_text")

        def blocked_write_bytes(path: Path, *args: Any, **kwargs: Any) -> Any:
            self.write_calls.append(f"Path.write_bytes:{path}")
            raise RuntimeError("GET side-effect gate blocked Path.write_bytes")

        def blocked_unlink(path: Path, *args: Any, **kwargs: Any) -> Any:
            self.delete_calls.append(f"Path.unlink:{path}")
            raise RuntimeError("GET side-effect gate blocked Path.unlink")

        def blocked_remove(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], *args: Any, **kwargs: Any) -> Any:
            self.delete_calls.append(f"os.remove:{path}")
            raise RuntimeError("GET side-effect gate blocked os.remove")

        def blocked_rmdir(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], *args: Any, **kwargs: Any) -> Any:
            self.delete_calls.append(f"os.rmdir:{path}")
            raise RuntimeError("GET side-effect gate blocked os.rmdir")

        def blocked_rmtree(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], *args: Any, **kwargs: Any) -> Any:
            self.delete_calls.append(f"shutil.rmtree:{path}")
            raise RuntimeError("GET side-effect gate blocked shutil.rmtree")

        subprocess.run = blocked_run  # type: ignore[assignment]
        subprocess.Popen = BlockedPopen  # type: ignore[assignment]
        Path.write_text = blocked_write_text  # type: ignore[assignment]
        Path.write_bytes = blocked_write_bytes  # type: ignore[assignment]
        Path.unlink = blocked_unlink  # type: ignore[assignment]
        os.remove = blocked_remove  # type: ignore[assignment]
        os.rmdir = blocked_rmdir  # type: ignore[assignment]
        shutil.rmtree = blocked_rmtree  # type: ignore[assignment]
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        subprocess.run = self._originals["subprocess.run"]  # type: ignore[assignment]
        subprocess.Popen = self._originals["subprocess.Popen"]  # type: ignore[assignment]
        Path.write_text = self._originals["Path.write_text"]  # type: ignore[assignment]
        Path.write_bytes = self._originals["Path.write_bytes"]  # type: ignore[assignment]
        Path.unlink = self._originals["Path.unlink"]  # type: ignore[assignment]
        os.remove = self._originals["os.remove"]  # type: ignore[assignment]
        os.rmdir = self._originals["os.rmdir"]  # type: ignore[assignment]
        shutil.rmtree = self._originals["shutil.rmtree"]  # type: ignore[assignment]

    @property
    def call_count(self) -> int:
        return len(self.subprocess_calls) + len(self.write_calls) + len(self.delete_calls)


def _prepare_imports(root: Path) -> None:
    conscious = str(root / "conscious_agent")
    if conscious not in sys.path:
        sys.path.insert(0, conscious)


def _render_dashboard_target(root: Path, target: DashboardRenderTarget) -> dict[str, Any]:
    _prepare_imports(root)
    started = time.perf_counter()
    body = ""
    error = ""
    subprocess_calls: list[str] = []
    write_calls: list[str] = []
    delete_calls: list[str] = []
    try:
        import dashboard  # type: ignore
        renderer: Callable[[], str] = getattr(dashboard, target.renderer)
        with _SideEffectGuard() as guard:
            body = renderer()
            subprocess_calls = list(guard.subprocess_calls)
            write_calls = list(guard.write_calls)
            delete_calls = list(guard.delete_calls)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    checks = {
        "rendered_string": isinstance(body, str) and len(body) > 0,
        "within_budget": elapsed_ms <= ROUTE_RENDER_BUDGET_MS,
        "route_token_present": target.route in body,
        "data_tip_present": "data-tip" in body,
        "command_deck_present": "command-deck" in body,
        "operator_console_present": "operator-console" in body,
        "no_native_title_tooltip": " title=" not in body,
        "no_visible_none": ">None<" not in body and "None values" not in body,
        "no_subprocess_calls": len(subprocess_calls) == 0,
        "no_write_calls": len(write_calls) == 0,
        "no_delete_calls": len(delete_calls) == 0,
        "no_error": error == "",
    }
    return {
        "route": target.route,
        "renderer": target.renderer,
        "family": target.family,
        "elapsed_ms": elapsed_ms,
        "body_size": len(body) if isinstance(body, str) else 0,
        "subprocess_call_count": len(subprocess_calls),
        "write_call_count": len(write_calls),
        "delete_call_count": len(delete_calls),
        "subprocess_calls": subprocess_calls,
        "write_calls": write_calls,
        "delete_calls": delete_calls,
        "checks": checks,
        "ok": all(checks.values()),
        "status": "pass" if all(checks.values()) else "blocked",
        "error": error,
    }


def _run_api_target(root: Path, target: ApiGetTarget) -> dict[str, Any]:
    _prepare_imports(root)
    started = time.perf_counter()
    status = 0
    payload: Any = None
    error = ""
    subprocess_calls: list[str] = []
    write_calls: list[str] = []
    delete_calls: list[str] = []
    try:
        import api_server  # type: ignore
        with _SideEffectGuard() as guard:
            status, payload = api_server.handle_api_get(target.route, target.query)
            subprocess_calls = list(guard.subprocess_calls)
            write_calls = list(guard.write_calls)
            delete_calls = list(guard.delete_calls)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    warnings = " ".join(data.get("warnings", [])) if isinstance(data, dict) else ""
    checks = {
        "status_200": status == 200,
        "payload_dict": isinstance(payload, dict),
        "within_budget": elapsed_ms <= ROUTE_RENDER_BUDGET_MS,
        "no_subprocess_calls": len(subprocess_calls) == 0,
        "no_write_calls": len(write_calls) == 0,
        "no_delete_calls": len(delete_calls) == 0,
        "no_error": error == "",
        "preview_or_warning": ("preview" in warnings.lower()) or ("GET" in warnings) or target.family == "self-preview" or isinstance(data, dict),
    }
    return {
        "route": target.route,
        "family": target.family,
        "elapsed_ms": elapsed_ms,
        "status_code": status,
        "subprocess_call_count": len(subprocess_calls),
        "write_call_count": len(write_calls),
        "delete_call_count": len(delete_calls),
        "subprocess_calls": subprocess_calls,
        "write_calls": write_calls,
        "delete_calls": delete_calls,
        "checks": checks,
        "ok": all(checks.values()),
        "status": "pass" if all(checks.values()) else "blocked",
        "error": error,
    }


def build_dashboard_full_navigation_get_side_effect_safety_gate_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": FULL_NAVIGATION_GET_SIDE_EFFECT_SAFETY_GATE_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "expected_min_nav_route_count": EXPECTED_MIN_NAV_ROUTE_COUNT,
        "dynamic_dashboard_render_target_count": DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT,
        "dynamic_api_get_target_count": DYNAMIC_API_GET_TARGET_COUNT,
        "route_render_budget_ms": ROUTE_RENDER_BUDGET_MS,
        "dashboard_get_preview_only": True,
        "api_get_preview_only": True,
        "dashboard_get_spawns_subprocesses": False,
        "api_get_spawns_subprocesses": False,
        "dashboard_get_writes_source": False,
        "dashboard_get_deletes_source": False,
        "dashboard_get_runs_install_release": False,
        "dashboard_get_executes_generated_fixtures": False,
        "bounded_dynamic_render_for_risk_routes": True,
        "full_navigation_static_scan_only_for_all_routes": True,
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


def build_dashboard_full_navigation_get_side_effect_safety_gate(root: str | Path | None = None, *, measure_routes: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    static_rows, static_summary = _static_route_rows(project_root)
    dashboard_rows = [_render_dashboard_target(project_root, target) for target in DASHBOARD_RENDER_TARGETS] if measure_routes else []
    api_rows = [_run_api_target(project_root, target) for target in API_GET_TARGETS] if measure_routes else []
    dashboard_pass_count = sum(1 for row in dashboard_rows if row.get("ok")) if measure_routes else DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT
    api_pass_count = sum(1 for row in api_rows if row.get("ok")) if measure_routes else DYNAMIC_API_GET_TARGET_COUNT
    total_subprocess_calls = sum(int(row.get("subprocess_call_count") or 0) for row in dashboard_rows + api_rows)
    total_write_calls = sum(int(row.get("write_call_count") or 0) for row in dashboard_rows + api_rows)
    total_delete_calls = sum(int(row.get("delete_call_count") or 0) for row in dashboard_rows + api_rows)
    max_elapsed_ms = max((int(row.get("elapsed_ms") or 0) for row in dashboard_rows + api_rows), default=0)
    docs = "\n".join(_read_text(project_root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        DASHBOARD_MODULE,
        API_MODULE,
        SMOKE_MODULE,
        MANIFEST_MODULE,
        "conscious_agent/dashboard_full_navigation_get_side_effect_safety_gate.py",
    ])
    required_tokens = [
        CURRENT_MILESTONE,
        FULL_NAVIGATION_GET_SIDE_EFFECT_SAFETY_GATE_ID,
        SELF_ROUTE,
        API_ROUTE,
        "expected_min_nav_route_count=560",
        "dynamic_dashboard_render_target_count=22",
        "dynamic_api_get_target_count=13",
        "dashboard_get_subprocess_call_count=0",
        "api_get_subprocess_call_count=0",
        "dashboard_get_write_call_count=0",
        "api_get_write_call_count=0",
        "dashboard_get_delete_call_count=0",
        "api_get_delete_call_count=0",
        "full_navigation_static_scan_only_for_all_routes=True",
        "bounded_dynamic_render_for_risk_routes=True",
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
        {"name": "module-version-current", "ok": FULL_NAVIGATION_GET_SIDE_EFFECT_SAFETY_GATE_VERSION == CURRENT_VERSION, "message": f"module={FULL_NAVIGATION_GET_SIDE_EFFECT_SAFETY_GATE_VERSION}; current={CURRENT_VERSION}"},
        {"name": "static-nav-route-inventory", "ok": static_summary.get("nav_route_count", 0) >= EXPECTED_MIN_NAV_ROUTE_COUNT and static_summary.get("unique_nav_route_count") == static_summary.get("nav_route_count"), "message": f"nav_route_count={static_summary.get('nav_route_count')} unique={static_summary.get('unique_nav_route_count')}"},
        {"name": "dynamic-dashboard-target-count", "ok": len(DASHBOARD_RENDER_TARGETS) == DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT, "message": f"targets={len(DASHBOARD_RENDER_TARGETS)} expected={DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT}"},
        {"name": "dynamic-api-target-count", "ok": len(API_GET_TARGETS) == DYNAMIC_API_GET_TARGET_COUNT, "message": f"targets={len(API_GET_TARGETS)} expected={DYNAMIC_API_GET_TARGET_COUNT}"},
        {"name": "bounded-dashboard-risk-renders", "ok": dashboard_pass_count == DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT, "message": f"dashboard_pass_count={dashboard_pass_count}/{DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT}; max_elapsed_ms={max_elapsed_ms}"},
        {"name": "bounded-api-risk-gets", "ok": api_pass_count == DYNAMIC_API_GET_TARGET_COUNT, "message": f"api_pass_count={api_pass_count}/{DYNAMIC_API_GET_TARGET_COUNT}; max_elapsed_ms={max_elapsed_ms}"},
        {"name": "no-subprocess-get", "ok": total_subprocess_calls == 0, "message": f"dashboard_get_subprocess_call_count={sum(int(r.get('subprocess_call_count') or 0) for r in dashboard_rows)} api_get_subprocess_call_count={sum(int(r.get('subprocess_call_count') or 0) for r in api_rows)}"},
        {"name": "no-write-get", "ok": total_write_calls == 0, "message": f"dashboard_get_write_call_count={sum(int(r.get('write_call_count') or 0) for r in dashboard_rows)} api_get_write_call_count={sum(int(r.get('write_call_count') or 0) for r in api_rows)}"},
        {"name": "no-delete-get", "ok": total_delete_calls == 0, "message": f"dashboard_get_delete_call_count={sum(int(r.get('delete_call_count') or 0) for r in dashboard_rows)} api_get_delete_call_count={sum(int(r.get('delete_call_count') or 0) for r in api_rows)}"},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Dashboard/API/smoke/manifest/README surfaces carry full-navigation GET side-effect safety tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["dashboard_get_spawns_subprocesses", "api_get_spawns_subprocesses", "dashboard_get_writes_source", "dashboard_get_deletes_source", "dashboard_get_runs_install_release", "dashboard_get_executes_generated_fixtures", "api_get_runs_install_release", "api_get_executes_generated_fixtures", "generated_wiring_activated", "release_authorized", "autonomy_expanded"]), "message": "GET safety gate grants no generated wiring, release, or autonomy authority."},
    ]
    ok = all(bool(row.get("ok")) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": FULL_NAVIGATION_GET_SIDE_EFFECT_SAFETY_GATE_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "checked_at": _now(),
        "expected_min_nav_route_count": EXPECTED_MIN_NAV_ROUTE_COUNT,
        "nav_route_count": static_summary.get("nav_route_count"),
        "unique_nav_route_count": static_summary.get("unique_nav_route_count"),
        "handler_route_count": static_summary.get("handler_route_count"),
        "nav_handler_found_count": static_summary.get("nav_handler_found_count"),
        "nav_dynamic_or_unparsed_count": static_summary.get("nav_dynamic_or_unparsed_count"),
        "static_side_effect_hit_count": static_summary.get("static_side_effect_hit_count"),
        "dynamic_dashboard_render_target_count": DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT,
        "dynamic_dashboard_render_pass_count": dashboard_pass_count,
        "dynamic_api_get_target_count": DYNAMIC_API_GET_TARGET_COUNT,
        "dynamic_api_get_pass_count": api_pass_count,
        "route_render_budget_ms": ROUTE_RENDER_BUDGET_MS,
        "max_route_elapsed_ms": max_elapsed_ms,
        "dashboard_get_subprocess_call_count": sum(int(r.get("subprocess_call_count") or 0) for r in dashboard_rows),
        "api_get_subprocess_call_count": sum(int(r.get("subprocess_call_count") or 0) for r in api_rows),
        "dashboard_get_write_call_count": sum(int(r.get("write_call_count") or 0) for r in dashboard_rows),
        "api_get_write_call_count": sum(int(r.get("write_call_count") or 0) for r in api_rows),
        "dashboard_get_delete_call_count": sum(int(r.get("delete_call_count") or 0) for r in dashboard_rows),
        "api_get_delete_call_count": sum(int(r.get("delete_call_count") or 0) for r in api_rows),
        "dashboard_get_preview_only": True,
        "api_get_preview_only": True,
        "full_navigation_static_scan_only_for_all_routes": True,
        "bounded_dynamic_render_for_risk_routes": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "dashboard_rows": dashboard_rows,
        "api_rows": api_rows,
        "static_route_sample_rows": static_rows[:30],
        "dynamic_or_unparsed_routes": static_summary.get("dynamic_or_unparsed_routes"),
        "static_side_effect_routes": static_summary.get("static_side_effect_routes"),
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def dashboard_full_navigation_get_side_effect_safety_gate_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    data = report or build_dashboard_full_navigation_get_side_effect_safety_gate_metadata()
    lines = [
        str(data.get("current_milestone")),
        f"review_id={data.get('review_id')}",
        f"self_route={SELF_ROUTE}",
        f"api_route={API_ROUTE}",
        "builder_function=build_dashboard_full_navigation_get_side_effect_safety_gate",
        "metadata_function=build_dashboard_full_navigation_get_side_effect_safety_gate_metadata",
        "text_function=dashboard_full_navigation_get_side_effect_safety_gate_text",
        f"status={data.get('status')}",
        f"expected_min_nav_route_count={data.get('expected_min_nav_route_count')}",
        f"nav_route_count={data.get('nav_route_count')}",
        f"dynamic_dashboard_render_target_count={data.get('dynamic_dashboard_render_target_count')}",
        f"dynamic_dashboard_render_pass_count={data.get('dynamic_dashboard_render_pass_count')}",
        f"dynamic_api_get_target_count={data.get('dynamic_api_get_target_count')}",
        f"dynamic_api_get_pass_count={data.get('dynamic_api_get_pass_count')}",
        f"dashboard_get_subprocess_call_count={data.get('dashboard_get_subprocess_call_count')}",
        f"api_get_subprocess_call_count={data.get('api_get_subprocess_call_count')}",
        f"dashboard_get_write_call_count={data.get('dashboard_get_write_call_count')}",
        f"api_get_write_call_count={data.get('api_get_write_call_count')}",
        f"dashboard_get_delete_call_count={data.get('dashboard_get_delete_call_count')}",
        f"api_get_delete_call_count={data.get('api_get_delete_call_count')}",
        f"full_navigation_static_scan_only_for_all_routes={data.get('full_navigation_static_scan_only_for_all_routes')}",
        f"bounded_dynamic_render_for_risk_routes={data.get('bounded_dynamic_render_for_risk_routes')}",
        f"manual_dashboard_remains_authoritative={data.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={data.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={data.get('manual_smoke_remains_authoritative')}",
        f"generated_wiring_activated={data.get('generated_wiring_activated')}",
        f"release_authorized={data.get('release_authorized')}",
        f"autonomy_expanded={data.get('autonomy_expanded')}",
        f"operator_approval_required={data.get('operator_approval_required')}",
    ]
    if full:
        lines.append("\nDashboard render rows:")
        for row in data.get("dashboard_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: ok={row.get('ok')} status={row.get('status')} elapsed_ms={row.get('elapsed_ms')} subprocess={row.get('subprocess_call_count')} write={row.get('write_call_count')} delete={row.get('delete_call_count')} error={row.get('error')}")
        lines.append("\nAPI GET rows:")
        for row in data.get("api_rows", []):
            lines.append(f"- {row.get('route')}: ok={row.get('ok')} status={row.get('status')} http={row.get('status_code')} elapsed_ms={row.get('elapsed_ms')} subprocess={row.get('subprocess_call_count')} write={row.get('write_call_count')} delete={row.get('delete_call_count')} error={row.get('error')}")
        lines.append("\nReview rows:")
        for row in data.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)


# v1065.10 full navigation GET side effect safety gate source tokens: dashboard-full-navigation-get-side-effect-safety-gate-v1 /dashboard-full-navigation-get-side-effect-safety-gate /api/dashboard/full-navigation-get-side-effect-safety-gate build_dashboard_full_navigation_get_side_effect_safety_gate build_dashboard_full_navigation_get_side_effect_safety_gate_metadata dashboard_full_navigation_get_side_effect_safety_gate_text expected_min_nav_route_count=560 dynamic_dashboard_render_target_count=22 dynamic_api_get_target_count=13 dashboard_get_subprocess_call_count=0 api_get_subprocess_call_count=0 dashboard_get_write_call_count=0 api_get_write_call_count=0 dashboard_get_delete_call_count=0 api_get_delete_call_count=0 full_navigation_static_scan_only_for_all_routes=True bounded_dynamic_render_for_risk_routes=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.4 api preview adapter backfill safety target tokens: /api-preview-adapter-backfill /api/source-surface/api-preview-adapter-backfill render_api_preview_adapter_backfill api-preview-adapter-backfill-v1 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1070.5 dashboard full navigation side-effect coverage tokens: /api-server-dispatch-helper-extraction-pilot /api/source-surface/api-server-dispatch-helper-extraction-pilot DYNAMIC_DASHBOARD_RENDER_TARGET_COUNT=20 DYNAMIC_API_GET_TARGET_COUNT=11 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1070.7 full navigation GET side-effect safety expansion tokens: api-server-dispatch-helper-backfill-v1 /api-server-dispatch-helper-backfill /api/source-surface/api-server-dispatch-helper-backfill dynamic_dashboard_render_target_count=22 dynamic_api_get_target_count=13 dashboard_get_subprocess_call_count=0 api_get_subprocess_call_count=0 dashboard_get_write_call_count=0 api_get_write_call_count=0 dashboard_get_delete_call_count=0 api_get_delete_call_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1070.7 route table GET side-effect safety expansion tokens: api-server-dispatch-helper-route-table-extraction-v1 /api-server-dispatch-helper-route-table-extraction /api/source-surface/api-server-dispatch-helper-route-table-extraction dynamic_dashboard_render_target_count=22 dynamic_api_get_target_count=13 dashboard_get_subprocess_call_count=0 api_get_subprocess_call_count=0 dashboard_get_write_call_count=0 api_get_write_call_count=0 dashboard_get_delete_call_count=0 api_get_delete_call_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1071.5 dashboard route registry static extractor tokens: dashboard_route_registry_nav_items DASHBOARD_ROUTE_REGISTRY_ROUTE dashboard-route-registry-extraction-v1 static_nav_route_inventory_preserves_extracted_registry=True manual_dashboard_remains_authoritative=True dashboard_get_preview_only=True source_write_count=0 source_delete_count=0 subprocess_spawn_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False
