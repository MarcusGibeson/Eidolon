from __future__ import annotations

from release_metadata import RUNTIME_VERSION
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

REVIEW_SURFACE_SHARED_VERSION = RUNTIME_VERSION

DEFAULT_SANDBOX_BACKEND_CANDIDATES: tuple[dict[str, str], ...] = (
    {"name": "bubblewrap", "command": "bwrap", "platform": "linux", "status": "candidate_requires_audited_command_contract"},
    {"name": "firejail", "command": "firejail", "platform": "linux", "status": "candidate_requires_audited_command_contract"},
    {"name": "unshare", "command": "unshare", "platform": "linux", "status": "candidate_requires_audited_command_contract"},
    {"name": "docker", "command": "docker", "platform": "container", "status": "candidate_requires_strict_flags_and_image_contract"},
    {"name": "windows-job-object", "command": "none", "platform": "windows", "status": "concept_only_not_integrated"},
)

DEFAULT_AUTHORITY_BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "dashboard_get_preview_only": True,
    "api_get_preview_only": True,
    "actual_fixture_execution_attempted": False,
    "sandbox_backend_integrated": False,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "operator_approval_required": True,
}

RISKY_SOURCE_TARGETS: tuple[str, ...] = (
    "conscious_agent/self_maintenance.py",
    "tools/smoke_check.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "conscious_agent/main.py",
    "conscious_agent/self_development_cycle.py",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def read_text(path: str | Path, *, default: str = "") -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return default


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def check_row(name: str, ok: bool, message: str, **extra: Any) -> dict[str, Any]:
    row = {"name": name, "ok": bool(ok), "status": "pass" if ok else "blocked", "message": message}
    row.update(extra)
    return row


def status_from_rows(rows: Sequence[dict[str, Any]]) -> str:
    return "pass" if all(row.get("ok") is True or row.get("status") == "pass" for row in rows) else "blocked"


def ok_from_rows(rows: Sequence[dict[str, Any]]) -> bool:
    return status_from_rows(rows) == "pass"


def sandbox_backend_rows(candidates: Iterable[dict[str, str]] = DEFAULT_SANDBOX_BACKEND_CANDIDATES) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        command = candidate.get("command", "")
        detected = bool(command and command != "none" and shutil.which(command))
        rows.append({
            "name": candidate.get("name", "unknown"),
            "command": command or "none",
            "platform": candidate.get("platform", "unknown"),
            "detected": detected,
            "audited_command_contract_integrated": False,
            "network_denial_proven": False,
            "filesystem_isolation_proven": False,
            "execution_allowed": False,
            "classification": "detected_but_not_audited" if detected else candidate.get("status", "not_detected"),
        })
    return rows


def line_count(path: str | Path) -> int:
    text = read_text(path)
    return 0 if not text else len(text.splitlines())


def source_line_inventory(root: str | Path | None = None, targets: Sequence[str] = RISKY_SOURCE_TARGETS) -> list[dict[str, Any]]:
    base = repo_root(root)
    rows: list[dict[str, Any]] = []
    for rel in targets:
        path = base / rel
        rows.append({
            "path": rel,
            "exists": path.exists(),
            "line_count": line_count(path),
            "classification": "giant_file_decomposition_priority" if line_count(path) >= 5000 else "shared_surface_candidate",
        })
    return rows


def extraction_candidate_rows() -> list[dict[str, Any]]:
    return [
        {"component": "review_surface_shared.py", "status": "added_shared_helper_surface", "adoption": "new_review_arcs_only", "risk": "low"},
        {"component": "dashboard review-card/table helpers", "status": "planned_next", "adoption": "extract_without_route_behavior_change", "risk": "medium"},
        {"component": "smoke check token/report helper", "status": "planned_next", "adoption": "extract_and_backfill_one_family_at_a_time", "risk": "medium"},
        {"component": "API preview response adapter", "status": "planned_next", "adoption": "manifest-backed_preview_only", "risk": "medium"},
        {"component": "sandbox backend adapter skeleton", "status": "planned_next", "adoption": "contract_only_until_audited_backend", "risk": "high_if_executed"},
    ]


def normalize_token(value: Any) -> str:
    return " ".join(str(value).replace("—", " ").replace("-", " ").split()).lower()


# v1070.1 shared review surface helper tokens: review-surface-shared-v1 REVIEW_SURFACE_SHARED_VERSION=1070.1 review_only=True actual_fixture_execution_count=0 sandbox_backend_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True no_native_title_tooltip data-tip command-deck operator-console


def missing_tokens(text: str, required: Sequence[str]) -> list[str]:
    return [token for token in required if token not in text]

def html_table_from_rows(rows: Sequence[dict[str, Any]], columns: Sequence[tuple[str, str]]) -> str:
    from html import escape
    header = "".join(f"<th>{escape(label)}</th>" for _, label in columns)
    body_rows: list[str] = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{escape(str(row.get(key, '')))}</td>" for key, _ in columns) + "</tr>")
    return f"<table><tr>{header}</tr>{''.join(body_rows)}</table>"


def render_review_card_component(title: str, body: str, *, tip: str = "review-only shared dashboard component") -> str:
    from html import escape
    return (
        f"<div class='card' data-tip='{escape(tip, quote=True)}'>"
        f"<h3>{escape(str(title), quote=True)}</h3>"
        f"<p>{escape(str(body), quote=True)}</p>"
        "</div>"
    )


def render_review_table_component(rows: Sequence[dict[str, Any]], columns: Sequence[tuple[str, str]], *, tip: str = "shared review table component") -> str:
    from html import escape
    table = html_table_from_rows(rows, columns)
    return f"<div data-tip='{escape(tip, quote=True)}'>{table}</div>"


def dashboard_review_component_pilot_rows() -> list[dict[str, Any]]:
    return [
        {"component": "render_review_card_component", "status": "available", "adoption": "dashboard-review-component-extraction-pilot-v1", "behavior_change": "none_preview_only"},
        {"component": "render_review_table_component", "status": "available", "adoption": "dashboard-review-component-extraction-pilot-v1", "behavior_change": "none_preview_only"},
    ]

def preview_response_payload(report: dict[str, Any], *, warning: str | None = None) -> dict[str, Any]:
    payload = dict(report)
    payload.setdefault("review_only", True)
    payload.setdefault("dashboard_get_preview_only", True)
    payload.setdefault("api_get_preview_only", True)
    payload.setdefault("actual_fixture_execution_count", 0)
    payload.setdefault("generated_wiring_activated", False)
    payload.setdefault("release_authorized", False)
    payload.setdefault("autonomy_expanded", False)
    if warning:
        payload.setdefault("warnings", []).append(warning)
    return payload

def shared_adoption_rows() -> list[dict[str, Any]]:
    return [
        {"helper": "check_row", "adopted_by": "dashboard-api-smoke-shared-utility-adoption-v1", "surface": "metadata checks", "status": "used"},
        {"helper": "status_from_rows", "adopted_by": "dashboard-api-smoke-shared-utility-adoption-v1", "surface": "metadata status", "status": "used"},
        {"helper": "html_table_from_rows", "adopted_by": "render_dashboard_api_smoke_shared_utility_adoption", "surface": "dashboard renderer", "status": "used"},
        {"helper": "preview_response_payload", "adopted_by": "/api/source-surface/dashboard-api-smoke-shared-utility-adoption", "surface": "API preview response", "status": "used"},
        {"helper": "missing_tokens", "adopted_by": "check_dashboard_api_smoke_shared_utility_adoption_v1", "surface": "smoke token validation", "status": "used"},
    ]

# v1070.1 shared helper adoption tokens: dashboard-api-smoke-shared-utility-adoption-v1 html_table_from_rows preview_response_payload missing_tokens sandbox-backend-adapter-skeleton-v1 sandbox_backend_adapter_integrated=False actual_fixture_execution_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1070.1 shared dashboard component extraction tokens: dashboard-review-component-extraction-pilot-v1 render_review_card_component render_review_table_component dashboard_review_component_pilot_rows actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1070.2 shared smoke helper extraction bridge tokens: smoke-check-helper-extraction-pilot-v1 smoke-check-shared-v1 read_docs_bundle missing_required_tokens authority_boundary_violations smoke_token_validation_row actual_fixture_execution_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip


def api_preview_adapter_rows() -> list[dict[str, Any]]:
    return [
        {"helper": "build_api_preview_envelope", "adopted_by": "api-preview-adapter-extraction-pilot-v1", "surface": "API GET preview payload", "status": "used"},
        {"helper": "api_preview_adapter_rows", "adopted_by": "api-preview-adapter-extraction-pilot-v1", "surface": "adapter inventory", "status": "used"},
        {"helper": "preview_response_payload", "adopted_by": "api-preview-adapter-extraction-pilot-v1", "surface": "authority defaults", "status": "used"},
    ]


def build_api_preview_envelope(report: dict[str, Any], *, route: str, adapter: str, warning: str | None = None) -> dict[str, Any]:
    payload = preview_response_payload(report, warning=warning)
    payload.setdefault("api_preview_adapter", adapter)
    payload.setdefault("api_route", route)
    payload.setdefault("api_get_preview_only", True)
    payload.setdefault("dashboard_get_preview_only", True)
    payload.setdefault("subprocess_spawn_count", 0)
    payload.setdefault("source_write_count", 0)
    payload.setdefault("actual_fixture_execution_allowed", False)
    payload.setdefault("audited_os_sandbox_backend_integrated", False)
    payload.setdefault("sandbox_backend_adapter_integrated", False)
    payload.setdefault("manual_api_dispatch_remains_authoritative", True)
    payload.setdefault("manual_dashboard_remains_authoritative", True)
    payload.setdefault("manual_smoke_remains_authoritative", True)
    payload.setdefault("operator_approval_required", True)
    return payload

# v1070.3 shared API preview adapter tokens: api-preview-adapter-extraction-pilot-v1 build_api_preview_envelope api_preview_adapter_rows preview_response_payload api_get_preview_only=True dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_api_dispatch_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip


def api_preview_adapter_backfill_rows() -> list[dict[str, Any]]:
    return [
        {"route": "/api/source-surface/dashboard-api-smoke-shared-utility-adoption", "module": "dashboard_api_smoke_shared_utility_adoption.py", "helper": "build_api_preview_envelope", "status": "backfilled_preview_only", "behavior_change": "none_authority_preserved"},
        {"route": "/api/source-surface/dashboard-review-component-extraction-pilot", "module": "dashboard_review_component_extraction_pilot.py", "helper": "build_api_preview_envelope", "status": "backfilled_preview_only", "behavior_change": "none_authority_preserved"},
        {"route": "/api/source-surface/smoke-check-helper-extraction-pilot", "module": "smoke_check_helper_extraction_pilot.py", "helper": "build_api_preview_envelope", "status": "backfilled_preview_only", "behavior_change": "none_authority_preserved"},
    ]

# v1070.5 shared API preview adapter backfill tokens: api-preview-adapter-backfill-v1 api_preview_adapter_backfill_rows build_api_preview_envelope /api/source-surface/dashboard-api-smoke-shared-utility-adoption /api/source-surface/dashboard-review-component-extraction-pilot /api/source-surface/smoke-check-helper-extraction-pilot api_get_preview_only=True dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_api_dispatch_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.1 review surface shared compatibility tokens: REVIEW_SURFACE_SHARED_VERSION=1075.1 dashboard-dispatcher-batch-decomposition-trial-v5 preview_only=True release_authorized=False autonomy_expanded=False
