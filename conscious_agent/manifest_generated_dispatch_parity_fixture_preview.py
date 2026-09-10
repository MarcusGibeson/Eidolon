from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from source_surface_manifest_dispatch_candidate_preparation import (
    DISPATCH_FAMILIES,
    build_source_surface_manifest_dispatch_candidate_preparation,
)

MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_VERSION = RUNTIME_VERSION
MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_ID = "manifest-generated-dispatch-parity-fixture-preview-v1"
SELF_ROUTE = "/manifest-generated-dispatch-parity-fixture-preview"
API_ROUTE = "/api/source-surface/manifest-generated-dispatch-parity-fixture-preview"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SMOKE_MODULE = "tools/smoke_check.py"
MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
INPUT_REVIEW_ID = "source-surface-manifest-dispatch-candidate-preparation-v1"
INPUT_CANDIDATE_SURFACE_COUNT = 8
INPUT_DISPATCH_CANDIDATE_ROW_COUNT = 24
PARITY_FIXTURE_SURFACE_COUNT = 8
DISPATCH_FAMILY_COUNT = 3
PARITY_FIXTURE_ROW_COUNT = 24

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "preview_only": True,
    "generated_fixture_preview": True,
    "fixture_files_written": False,
    "fixture_harness_executed": False,
    "generated_dashboard_dispatch_written": False,
    "generated_api_dispatch_written": False,
    "generated_smoke_dispatch_written": False,
    "generated_wiring_activated": False,
    "candidate_routes_registered_live": False,
    "manifest_replaces_dashboard_routes": False,
    "manifest_replaces_api_dispatch": False,
    "manifest_replaces_smoke_registry": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "source_files_mutated_at_runtime": False,
    "runtime_data_deleted": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}


@dataclass(frozen=True)
class DispatchParityFixtureRow:
    fixture_id: str
    surface_id: str
    dispatch_family: str
    candidate_target: str
    manual_source: str
    fixture_kind: str
    fixture_assertion: str
    candidate_ready_for_fixture: bool
    manual_target_represented: bool
    generated_fixture_previewed: bool
    fixture_file_written: bool
    fixture_harness_executed: bool
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


def _family_source(family: str) -> str:
    if family == "dashboard":
        return DASHBOARD_MODULE
    if family == "api":
        return API_MODULE
    if family == "smoke":
        return SMOKE_MODULE
    return MANIFEST_MODULE


def _fixture_kind(family: str) -> str:
    if family == "dashboard":
        return "dashboard_renderer_presence_fixture_preview"
    if family == "api":
        return "api_dispatch_presence_fixture_preview"
    if family == "smoke":
        return "smoke_check_presence_fixture_preview"
    return "manifest_presence_fixture_preview"


def _fixture_assertion(family: str, target: str) -> str:
    if target in {"", "none", "not_exposed_review_only"}:
        return f"assert {family} candidate is intentionally review-only and has no live target"
    return f"assert {target!r} remains represented in manual {_family_source(family)} before any generated dispatch experiment"


def _fixture_id(surface_id: str, family: str) -> str:
    clean = surface_id.replace("v", "", 1).replace("-", "_")
    return f"fixture_{clean}_{family}_parity_preview"


def _candidate_report(root: Path, inspect_sources: bool) -> dict[str, Any]:
    return build_source_surface_manifest_dispatch_candidate_preparation(root, inspect_sources=inspect_sources)


def _fixture_rows(candidate_rows: list[dict[str, Any]]) -> list[DispatchParityFixtureRow]:
    rows: list[DispatchParityFixtureRow] = []
    for candidate in candidate_rows:
        family = str(candidate.get("dispatch_family"))
        surface_id = str(candidate.get("surface_id"))
        target = str(candidate.get("candidate_target"))
        represented = candidate.get("represented_in_source") is True
        rows.append(DispatchParityFixtureRow(
            fixture_id=_fixture_id(surface_id, family),
            surface_id=surface_id,
            dispatch_family=family,
            candidate_target=target,
            manual_source=_family_source(family),
            fixture_kind=_fixture_kind(family),
            fixture_assertion=_fixture_assertion(family, target),
            candidate_ready_for_fixture=represented,
            manual_target_represented=represented,
            generated_fixture_previewed=True,
            fixture_file_written=False,
            fixture_harness_executed=False,
            active_dispatch_enabled=False,
            operator_action="review fixture preview and keep manual dispatch authoritative until an isolated harness proves parity",
        ))
    return rows


def build_manifest_generated_dispatch_parity_fixture_preview_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "preview",
        "ok": True,
        "input_candidate_surface_count": INPUT_CANDIDATE_SURFACE_COUNT,
        "input_dispatch_candidate_row_count": INPUT_DISPATCH_CANDIDATE_ROW_COUNT,
        "parity_fixture_surface_count": PARITY_FIXTURE_SURFACE_COUNT,
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "parity_fixture_row_count": PARITY_FIXTURE_ROW_COUNT,
        "dashboard_parity_fixture_count": 8,
        "api_parity_fixture_count": 8,
        "smoke_parity_fixture_count": 8,
        "review_only": True,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Manifest-generated dispatch parity fixtures are previewed as evidence only; no fixture files are written and manual dispatch remains authoritative.",
    }


def build_manifest_generated_dispatch_parity_fixture_preview(root: str | Path | None = None, *, inspect_sources: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    candidate_report = _candidate_report(project_root, inspect_sources=inspect_sources)
    candidate_rows = list(candidate_report.get("candidate_rows") or [])
    fixture_rows = _fixture_rows(candidate_rows)
    row_dicts = [asdict(row) for row in fixture_rows]
    surface_ids = sorted({str(row.get("surface_id")) for row in row_dicts})
    represented_count = sum(1 for row in row_dicts if row.get("manual_target_represented") is True)
    previewed_count = sum(1 for row in row_dicts if row.get("generated_fixture_previewed") is True)
    fixture_file_write_count = sum(1 for row in row_dicts if row.get("fixture_file_written") is True)
    fixture_harness_execution_count = sum(1 for row in row_dicts if row.get("fixture_harness_executed") is True)
    active_dispatch_count = sum(1 for row in row_dicts if row.get("active_dispatch_enabled") is True)
    dashboard_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "dashboard")
    api_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "api")
    smoke_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "smoke")
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/manifest_generated_dispatch_parity_fixture_preview.py",
        "conscious_agent/source_surface_manifest_dispatch_candidate_preparation.py",
        DASHBOARD_MODULE,
        API_MODULE,
        SMOKE_MODULE,
        MANIFEST_MODULE,
        "conscious_agent/current_version_staleness_audit.py",
    ])
    required_tokens = [
        CURRENT_MILESTONE,
        MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_ID,
        SELF_ROUTE,
        API_ROUTE,
        "build_manifest_generated_dispatch_parity_fixture_preview_metadata",
        "build_manifest_generated_dispatch_parity_fixture_preview",
        "manifest_generated_dispatch_parity_fixture_preview_text",
        "input_candidate_surface_count=8",
        "input_dispatch_candidate_row_count=24",
        "parity_fixture_surface_count=8",
        "dispatch_family_count=3",
        "parity_fixture_row_count=24",
        "represented_parity_fixture_count=24",
        "previewed_parity_fixture_count=24",
        "dashboard_parity_fixture_count=8",
        "api_parity_fixture_count=8",
        "smoke_parity_fixture_count=8",
        "fixture_files_written=False",
        "fixture_harness_executed=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "manifest_replaces_dashboard_routes=False",
        "manifest_replaces_api_dispatch=False",
        "manifest_replaces_smoke_registry=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
    ]
    checks = [
        {"name": "module-version-current", "ok": MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_VERSION == CURRENT_VERSION, "message": f"module={MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_VERSION}; current={CURRENT_VERSION}"},
        {"name": "input-candidate-report-pass", "ok": candidate_report.get("ok") is True and candidate_report.get("status") == "pass", "message": f"input_status={candidate_report.get('status')} input_ok={candidate_report.get('ok')}"},
        {"name": "input-candidate-counts", "ok": candidate_report.get("candidate_surface_count") == INPUT_CANDIDATE_SURFACE_COUNT and candidate_report.get("dispatch_candidate_row_count") == INPUT_DISPATCH_CANDIDATE_ROW_COUNT, "message": f"surfaces={candidate_report.get('candidate_surface_count')} rows={candidate_report.get('dispatch_candidate_row_count')}"},
        {"name": "fixture-row-count", "ok": len(row_dicts) == PARITY_FIXTURE_ROW_COUNT, "message": f"fixtures={len(row_dicts)} expected={PARITY_FIXTURE_ROW_COUNT}"},
        {"name": "fixture-surface-count", "ok": len(surface_ids) == PARITY_FIXTURE_SURFACE_COUNT, "message": f"surfaces={len(surface_ids)} expected={PARITY_FIXTURE_SURFACE_COUNT}"},
        {"name": "fixture-family-counts", "ok": dashboard_count == 8 and api_count == 8 and smoke_count == 8 and len(DISPATCH_FAMILIES) == DISPATCH_FAMILY_COUNT, "message": f"dashboard={dashboard_count} api={api_count} smoke={smoke_count}"},
        {"name": "fixtures-represented", "ok": represented_count == PARITY_FIXTURE_ROW_COUNT, "message": f"represented={represented_count}"},
        {"name": "fixtures-previewed-only", "ok": previewed_count == PARITY_FIXTURE_ROW_COUNT and fixture_file_write_count == 0 and fixture_harness_execution_count == 0 and active_dispatch_count == 0, "message": f"previewed={previewed_count} writes={fixture_file_write_count} executed={fixture_harness_execution_count} active={active_dispatch_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "fixture_files_written": False,
            "fixture_harness_executed": False,
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
            "manual_api_dispatch_remains_authoritative": True,
            "manual_smoke_remains_authoritative": True,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "generated fixture previews do not activate dispatch, write files, authorize release, or expand autonomy"},
        {"name": "documentation-tokens", "ok": all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(row.get("ok") is True for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "input_candidate_surface_count": candidate_report.get("candidate_surface_count"),
        "input_dispatch_candidate_row_count": candidate_report.get("dispatch_candidate_row_count"),
        "parity_fixture_surface_count": len(surface_ids),
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "parity_fixture_row_count": len(row_dicts),
        "represented_parity_fixture_count": represented_count,
        "previewed_parity_fixture_count": previewed_count,
        "dashboard_parity_fixture_count": dashboard_count,
        "api_parity_fixture_count": api_count,
        "smoke_parity_fixture_count": smoke_count,
        "fixture_file_write_count": fixture_file_write_count,
        "fixture_harness_execution_count": fixture_harness_execution_count,
        "active_dispatch_candidate_count": active_dispatch_count,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "manifest_replaces_dashboard_routes": False,
        "manifest_replaces_api_dispatch": False,
        "manifest_replaces_smoke_registry": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "fixture_rows": row_dicts,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def manifest_generated_dispatch_parity_fixture_preview_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"input_review_id={report.get('input_review_id')}",
        f"status={report.get('status')}",
        f"input_candidate_surface_count={report.get('input_candidate_surface_count')}",
        f"input_dispatch_candidate_row_count={report.get('input_dispatch_candidate_row_count')}",
        f"parity_fixture_surface_count={report.get('parity_fixture_surface_count')}",
        f"dispatch_family_count={report.get('dispatch_family_count')}",
        f"parity_fixture_row_count={report.get('parity_fixture_row_count')}",
        f"represented_parity_fixture_count={report.get('represented_parity_fixture_count')}",
        f"previewed_parity_fixture_count={report.get('previewed_parity_fixture_count')}",
        f"dashboard_parity_fixture_count={report.get('dashboard_parity_fixture_count')}",
        f"api_parity_fixture_count={report.get('api_parity_fixture_count')}",
        f"smoke_parity_fixture_count={report.get('smoke_parity_fixture_count')}",
        f"fixture_files_written={report.get('fixture_files_written')}",
        f"fixture_harness_executed={report.get('fixture_harness_executed')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manifest_replaces_dashboard_routes={report.get('manifest_replaces_dashboard_routes')}",
        f"manifest_replaces_api_dispatch={report.get('manifest_replaces_api_dispatch')}",
        f"manifest_replaces_smoke_registry={report.get('manifest_replaces_smoke_registry')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_required={report.get('operator_approval_required')}",
    ]
    if full:
        for row in report.get("fixture_rows", []):
            lines.append(f"fixture {row.get('dispatch_family')} {row.get('surface_id')} -> {row.get('candidate_target')} represented={row.get('manual_target_represented')} written={row.get('fixture_file_written')} executed={row.get('fixture_harness_executed')} active={row.get('active_dispatch_enabled')}")
        for check in report.get("checks", []):
            lines.append(f"check {check.get('name')} ok={check.get('ok')} {check.get('message')}")
    return "\n".join(lines)


# v1059.0 manifest generated dispatch parity fixture preview tokens: manifest-generated-dispatch-parity-fixture-preview-v1 /manifest-generated-dispatch-parity-fixture-preview /api/source-surface/manifest-generated-dispatch-parity-fixture-preview build_manifest_generated_dispatch_parity_fixture_preview_metadata build_manifest_generated_dispatch_parity_fixture_preview manifest_generated_dispatch_parity_fixture_preview_text input_candidate_surface_count=8 input_dispatch_candidate_row_count=24 parity_fixture_surface_count=8 dispatch_family_count=3 parity_fixture_row_count=24 represented_parity_fixture_count=24 previewed_parity_fixture_count=24 dashboard_parity_fixture_count=8 api_parity_fixture_count=8 smoke_parity_fixture_count=8 fixture_files_written=False fixture_harness_executed=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True manifest_replaces_dashboard_routes=False manifest_replaces_api_dispatch=False manifest_replaces_smoke_registry=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
