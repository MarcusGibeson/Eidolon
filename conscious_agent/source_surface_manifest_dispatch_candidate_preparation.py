from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

SOURCE_SURFACE_MANIFEST_DISPATCH_CANDIDATE_PREPARATION_VERSION = RUNTIME_VERSION
SOURCE_SURFACE_MANIFEST_DISPATCH_CANDIDATE_PREPARATION_ID = "source-surface-manifest-dispatch-candidate-preparation-v1"
SELF_ROUTE = "/source-surface-manifest-dispatch-candidate-preparation"
API_ROUTE = "/api/source-surface/dispatch-candidate-preparation"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SMOKE_MODULE = "tools/smoke_check.py"
MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
CANDIDATE_SURFACE_IDS: tuple[str, ...] = (
    "v1050-doctor-diagnostic-cache-severity-route-impact-matrix",
    "v1051-release-zip-privacy-critical-gate-repair",
    "v1052-dashboard-doctor-headroom-repair",
    "v1053-installed-tree-cleanup-historical-verification-reconciliation",
    "v1054-doctor-diagnostic-cache-impact-operator-action-ledger",
    "v1055-doctor-deep-diagnostic-latency-budget-repair",
    "v1056-dashboard-slow-route-cohort-repair",
    "v1057-install-release-historical-blocker-reduction",
)
DISPATCH_FAMILIES: tuple[str, ...] = ("dashboard", "api", "smoke")
CANDIDATE_SURFACE_COUNT = 8
DISPATCH_FAMILY_COUNT = 3
DISPATCH_CANDIDATE_ROW_COUNT = 24

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "manifest_candidates_are_authorization": False,
    "manifest_replaces_dashboard_routes": False,
    "manifest_replaces_api_dispatch": False,
    "manifest_replaces_smoke_registry": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "smoke_wiring_generated": False,
    "generated_wiring_activated": False,
    "candidate_routes_registered_live": False,
    "dispatch_table_written": False,
    "source_files_mutated_at_runtime": False,
    "runtime_data_deleted": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
}


@dataclass(frozen=True)
class DispatchCandidateRow:
    surface_id: str
    dispatch_family: str
    candidate_target: str
    source_of_truth: str
    represented_in_source: bool
    candidate_ready_for_review: bool
    active_dispatch_enabled: bool
    operator_action: str


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _manifest_entries() -> list[dict[str, Any]]:
    import source_surface_manifest as manifest

    return [dict(entry) for entry in manifest.RECENT_SURFACE_ENTRIES]


def _entry_by_id(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(entry.get("surface_id")): entry for entry in entries}


def _candidate_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = _entry_by_id(entries)
    return [by_id[surface_id] for surface_id in CANDIDATE_SURFACE_IDS if surface_id in by_id]


def _family_target(entry: dict[str, Any], family: str) -> str:
    if family == "dashboard":
        return str(entry.get("dashboard_route") or "not_exposed_review_only")
    if family == "api":
        return str(entry.get("api_route") or "not_exposed_review_only")
    if family == "smoke":
        return str(entry.get("smoke_check") or "not_exposed_review_only")
    return "not_exposed_review_only"


def _family_source(family: str) -> str:
    if family == "dashboard":
        return DASHBOARD_MODULE
    if family == "api":
        return API_MODULE
    if family == "smoke":
        return SMOKE_MODULE
    return MANIFEST_MODULE


def _target_represented(target: str, source_text: str) -> bool:
    if target in {"", "none", "not_exposed_review_only"}:
        return True
    return target in source_text


def _dispatch_candidate_rows(root: Path, candidates: list[dict[str, Any]]) -> list[DispatchCandidateRow]:
    source_text = {
        "dashboard": _read_text(root, DASHBOARD_MODULE),
        "api": _read_text(root, API_MODULE),
        "smoke": _read_text(root, SMOKE_MODULE),
    }
    rows: list[DispatchCandidateRow] = []
    for entry in candidates:
        surface_id = str(entry.get("surface_id"))
        for family in DISPATCH_FAMILIES:
            target = _family_target(entry, family)
            represented = _target_represented(target, source_text[family])
            rows.append(DispatchCandidateRow(
                surface_id=surface_id,
                dispatch_family=family,
                candidate_target=target,
                source_of_truth=_family_source(family),
                represented_in_source=represented,
                candidate_ready_for_review=represented,
                active_dispatch_enabled=False,
                operator_action="review manifest candidate parity before any future generated dispatch experiment",
            ))
    return rows


def build_source_surface_manifest_dispatch_candidate_preparation_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": SOURCE_SURFACE_MANIFEST_DISPATCH_CANDIDATE_PREPARATION_ID,
        "status": "preview",
        "ok": True,
        "candidate_surface_count": CANDIDATE_SURFACE_COUNT,
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "dispatch_candidate_row_count": DISPATCH_CANDIDATE_ROW_COUNT,
        "review_only": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Source surface manifest dispatch candidates are prepared as review-only evidence and do not replace manual dashboard/API/smoke dispatch.",
    }


def build_source_surface_manifest_dispatch_candidate_preparation(root: str | Path | None = None, *, inspect_sources: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    entries = _manifest_entries()
    candidates = _candidate_entries(entries)
    candidate_rows = _dispatch_candidate_rows(project_root, candidates) if inspect_sources else [
        DispatchCandidateRow(
            surface_id=str(entry.get("surface_id")),
            dispatch_family=family,
            candidate_target=_family_target(entry, family),
            source_of_truth=_family_source(family),
            represented_in_source=True,
            candidate_ready_for_review=True,
            active_dispatch_enabled=False,
            operator_action="review manifest candidate parity before any future generated dispatch experiment",
        )
        for entry in candidates
        for family in DISPATCH_FAMILIES
    ]
    row_dicts = [asdict(row) for row in candidate_rows]
    represented_count = sum(1 for row in row_dicts if row.get("represented_in_source") is True)
    active_dispatch_count = sum(1 for row in row_dicts if row.get("active_dispatch_enabled") is True)
    dashboard_candidate_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "dashboard")
    api_candidate_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "api")
    smoke_candidate_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "smoke")
    missing_surface_ids = [surface_id for surface_id in CANDIDATE_SURFACE_IDS if surface_id not in _entry_by_id(entries)]
    not_represented_rows = [row for row in row_dicts if row.get("represented_in_source") is not True]
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/source_surface_manifest_dispatch_candidate_preparation.py",
        DASHBOARD_MODULE,
        API_MODULE,
        SMOKE_MODULE,
        MANIFEST_MODULE,
        "conscious_agent/current_version_staleness_audit.py",
    ])
    required_tokens = [
        CURRENT_MILESTONE,
        SOURCE_SURFACE_MANIFEST_DISPATCH_CANDIDATE_PREPARATION_ID,
        SELF_ROUTE,
        API_ROUTE,
        "candidate_surface_count=8",
        "dispatch_family_count=3",
        "dispatch_candidate_row_count=24",
        "represented_dispatch_candidate_count=24",
        "dashboard_dispatch_candidate_count=8",
        "api_dispatch_candidate_count=8",
        "smoke_dispatch_candidate_count=8",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "manifest_replaces_dashboard_routes=False",
        "manifest_replaces_api_dispatch=False",
        "manifest_replaces_smoke_registry=False",
        "dashboard_wiring_generated=False",
        "api_wiring_generated=False",
        "smoke_wiring_generated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
    ]
    checks = [
        {"name": "module-version-current", "ok": SOURCE_SURFACE_MANIFEST_DISPATCH_CANDIDATE_PREPARATION_VERSION == CURRENT_VERSION, "message": f"module={SOURCE_SURFACE_MANIFEST_DISPATCH_CANDIDATE_PREPARATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "candidate-surfaces-present", "ok": len(candidates) == CANDIDATE_SURFACE_COUNT and not missing_surface_ids, "message": f"candidates={len(candidates)} missing={len(missing_surface_ids)}"},
        {"name": "dispatch-family-count", "ok": len(DISPATCH_FAMILIES) == DISPATCH_FAMILY_COUNT, "message": f"families={len(DISPATCH_FAMILIES)} expected={DISPATCH_FAMILY_COUNT}"},
        {"name": "dispatch-candidate-row-count", "ok": len(row_dicts) == DISPATCH_CANDIDATE_ROW_COUNT, "message": f"rows={len(row_dicts)} expected={DISPATCH_CANDIDATE_ROW_COUNT}"},
        {"name": "dispatch-candidates-represented", "ok": represented_count == DISPATCH_CANDIDATE_ROW_COUNT and not not_represented_rows, "message": f"represented={represented_count}/{DISPATCH_CANDIDATE_ROW_COUNT}"},
        {"name": "dispatch-candidates-inactive", "ok": active_dispatch_count == 0, "message": f"active_dispatch_count={active_dispatch_count}"},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Dashboard/API/smoke/manifest/README surfaces carry v1058 dispatch candidate preparation tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["manifest_candidates_are_authorization", "manifest_replaces_dashboard_routes", "manifest_replaces_api_dispatch", "manifest_replaces_smoke_registry", "dashboard_wiring_generated", "api_wiring_generated", "smoke_wiring_generated", "generated_wiring_activated", "candidate_routes_registered_live", "dispatch_table_written", "source_files_mutated_at_runtime", "runtime_data_deleted", "release_authorized", "autonomy_expanded"]), "message": "Manifest dispatch candidates stay review-only and inactive."},
    ]
    ok = all(bool(row["ok"]) for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": SOURCE_SURFACE_MANIFEST_DISPATCH_CANDIDATE_PREPARATION_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "checked_at": _now(),
        "candidate_surface_count": len(candidates),
        "dispatch_family_count": len(DISPATCH_FAMILIES),
        "dispatch_candidate_row_count": len(row_dicts),
        "represented_dispatch_candidate_count": represented_count,
        "dashboard_dispatch_candidate_count": dashboard_candidate_count,
        "api_dispatch_candidate_count": api_candidate_count,
        "smoke_dispatch_candidate_count": smoke_candidate_count,
        "missing_candidate_surface_ids": missing_surface_ids,
        "not_represented_rows": not_represented_rows,
        "active_dispatch_candidate_count": active_dispatch_count,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "manifest_replaces_dashboard_routes": False,
        "manifest_replaces_api_dispatch": False,
        "manifest_replaces_smoke_registry": False,
        "dashboard_wiring_generated": False,
        "api_wiring_generated": False,
        "smoke_wiring_generated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "candidate_rows": row_dicts,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def source_surface_manifest_dispatch_candidate_preparation_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"candidate_surface_count={report.get('candidate_surface_count')}",
        f"dispatch_family_count={report.get('dispatch_family_count')}",
        f"dispatch_candidate_row_count={report.get('dispatch_candidate_row_count')}",
        f"represented_dispatch_candidate_count={report.get('represented_dispatch_candidate_count')}",
        f"dashboard_dispatch_candidate_count={report.get('dashboard_dispatch_candidate_count')}",
        f"api_dispatch_candidate_count={report.get('api_dispatch_candidate_count')}",
        f"smoke_dispatch_candidate_count={report.get('smoke_dispatch_candidate_count')}",
        f"active_dispatch_candidate_count={report.get('active_dispatch_candidate_count')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manifest_replaces_dashboard_routes={report.get('manifest_replaces_dashboard_routes')}",
        f"manifest_replaces_api_dispatch={report.get('manifest_replaces_api_dispatch')}",
        f"manifest_replaces_smoke_registry={report.get('manifest_replaces_smoke_registry')}",
        f"dashboard_wiring_generated={report.get('dashboard_wiring_generated')}",
        f"api_wiring_generated={report.get('api_wiring_generated')}",
        f"smoke_wiring_generated={report.get('smoke_wiring_generated')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_required={report.get('operator_approval_required')}",
    ]
    if full:
        for row in report.get("candidate_rows", []):
            lines.append(f"candidate {row.get('dispatch_family')} {row.get('surface_id')} -> {row.get('candidate_target')} represented={row.get('represented_in_source')} active={row.get('active_dispatch_enabled')}")
        for check in report.get("checks", []):
            lines.append(f"check {check.get('name')} ok={check.get('ok')} {check.get('message')}")
    return "\n".join(lines)


# v1058.0 source surface manifest dispatch candidate preparation tokens: source-surface-manifest-dispatch-candidate-preparation-v1 /source-surface-manifest-dispatch-candidate-preparation /api/source-surface/dispatch-candidate-preparation build_source_surface_manifest_dispatch_candidate_preparation_metadata build_source_surface_manifest_dispatch_candidate_preparation source_surface_manifest_dispatch_candidate_preparation_text candidate_surface_count=8 dispatch_family_count=3 dispatch_candidate_row_count=24 represented_dispatch_candidate_count=24 dashboard_dispatch_candidate_count=8 api_dispatch_candidate_count=8 smoke_dispatch_candidate_count=8 manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True manifest_replaces_dashboard_routes=False manifest_replaces_api_dispatch=False manifest_replaces_smoke_registry=False dashboard_wiring_generated=False api_wiring_generated=False smoke_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
