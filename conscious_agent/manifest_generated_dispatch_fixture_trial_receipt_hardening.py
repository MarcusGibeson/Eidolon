from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from manifest_generated_dispatch_fixture_first_isolated_dry_run_trial import (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_ID,
    build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial,
)

MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_VERSION = RUNTIME_VERSION
MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_ID = "manifest-generated-dispatch-fixture-trial-receipt-hardening-v1"
SELF_ROUTE = "/manifest-generated-dispatch-fixture-trial-receipt-hardening"
API_ROUTE = "/api/source-surface/manifest-generated-dispatch-fixture-trial-receipt-hardening"
INPUT_REVIEW_ID = MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_ID
INPUT_TRIAL_RECEIPT_COUNT = 1
HARDENED_RECEIPT_COUNT = 1
RECEIPT_REQUIRED_FIELD_COUNT = 14
RECEIPT_BOUNDARY_FIELD_COUNT = 8
TRIAL_SUBPROCESS_SPAWN_COUNT = 1
SOURCE_MUTATION_COUNT = 0

RECEIPT_REQUIRED_FIELDS: tuple[str, ...] = (
    "trial_id",
    "execution_prep_id",
    "fixture_id",
    "surface_id",
    "dispatch_family",
    "candidate_target",
    "trial_mode",
    "receipt_marker_found",
    "receipt_ok",
    "network_policy_disabled",
    "pre_snapshot_hash",
    "post_snapshot_hash",
    "source_snapshot_changed",
    "subprocess_returncode",
)

RECEIPT_BOUNDARY_FIELDS: tuple[str, ...] = (
    "fixture_file_written",
    "generated_wiring_activated",
    "release_authorized",
    "autonomy_expanded",
    "source_snapshot_changed",
    "network_policy_disabled",
    "timed_out",
    "receipt_ok",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "receipt_hardening_only": True,
    "input_trial_receipt_executed": True,
    "hardened_receipts_generated": True,
    "fixture_files_written": False,
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
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}


@dataclass(frozen=True)
class HardenedTrialReceiptRow:
    hardened_receipt_id: str
    input_review_id: str
    trial_id: str
    fixture_id: str
    dispatch_family: str
    candidate_target: str
    receipt_required_field_count: int
    receipt_required_fields_present: bool
    receipt_boundary_field_count: int
    receipt_boundary_fields_valid: bool
    receipt_marker_found: bool
    receipt_ok: bool
    subprocess_returncode: int | None
    timed_out: bool
    network_policy_disabled: bool
    pre_snapshot_hash_present: bool
    post_snapshot_hash_present: bool
    source_snapshot_changed: bool
    source_mutation_count: int
    fixture_file_written: bool
    generated_wiring_activated: bool
    release_authorized: bool
    autonomy_expanded: bool
    operator_receipt_required: bool
    promotion_allowed_from_receipt: bool
    release_allowed_from_receipt: bool
    autonomy_allowed_from_receipt: bool
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


def _hash_present(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text.lower())


def _harden_row(row: dict[str, Any]) -> HardenedTrialReceiptRow:
    required_present = all(field in row for field in RECEIPT_REQUIRED_FIELDS)
    boundary_valid = (
        row.get("fixture_file_written") is False
        and row.get("generated_wiring_activated") is False
        and row.get("release_authorized") is False
        and row.get("autonomy_expanded") is False
        and row.get("source_snapshot_changed") is False
        and row.get("network_policy_disabled") is True
        and row.get("timed_out") is False
        and row.get("receipt_ok") is True
    )
    source_mutation_count = 1 if row.get("source_snapshot_changed") is True else 0
    return HardenedTrialReceiptRow(
        hardened_receipt_id=f"hardened_receipt_{row.get('trial_id')}",
        input_review_id=INPUT_REVIEW_ID,
        trial_id=str(row.get("trial_id")),
        fixture_id=str(row.get("fixture_id")),
        dispatch_family=str(row.get("dispatch_family")),
        candidate_target=str(row.get("candidate_target")),
        receipt_required_field_count=len(RECEIPT_REQUIRED_FIELDS),
        receipt_required_fields_present=required_present,
        receipt_boundary_field_count=len(RECEIPT_BOUNDARY_FIELDS),
        receipt_boundary_fields_valid=boundary_valid,
        receipt_marker_found=row.get("receipt_marker_found") is True,
        receipt_ok=row.get("receipt_ok") is True,
        subprocess_returncode=row.get("subprocess_returncode") if isinstance(row.get("subprocess_returncode"), int) else None,
        timed_out=row.get("timed_out") is True,
        network_policy_disabled=row.get("network_policy_disabled") is True,
        pre_snapshot_hash_present=_hash_present(row.get("pre_snapshot_hash")),
        post_snapshot_hash_present=_hash_present(row.get("post_snapshot_hash")),
        source_snapshot_changed=row.get("source_snapshot_changed") is True,
        source_mutation_count=source_mutation_count,
        fixture_file_written=row.get("fixture_file_written") is True,
        generated_wiring_activated=row.get("generated_wiring_activated") is True,
        release_authorized=row.get("release_authorized") is True,
        autonomy_expanded=row.get("autonomy_expanded") is True,
        operator_receipt_required=True,
        promotion_allowed_from_receipt=False,
        release_allowed_from_receipt=False,
        autonomy_allowed_from_receipt=False,
        operator_action="review hardened dry-run receipt; require separate operator approval before any wider fixture execution, generated dispatch promotion, release, or autonomy phase change",
    )


def build_manifest_generated_dispatch_fixture_trial_receipt_hardening_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "preview",
        "ok": True,
        "input_trial_receipt_count": INPUT_TRIAL_RECEIPT_COUNT,
        "hardened_receipt_count": 0,
        "receipt_required_field_count": RECEIPT_REQUIRED_FIELD_COUNT,
        "receipt_boundary_field_count": RECEIPT_BOUNDARY_FIELD_COUNT,
        "receipt_hardening_available": True,
        "fixture_files_written": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Manifest-generated dispatch fixture trial receipt hardening is preview-only until inspect_sources=true; hardened receipts never authorize release, generated dispatch, or autonomy.",
    }


def build_manifest_generated_dispatch_fixture_trial_receipt_hardening(root: str | Path | None = None, *, inspect_sources: bool = True, execute_trial: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    trial_report = build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial(project_root, inspect_sources=inspect_sources, execute_trial=execute_trial)
    trial_rows = list(trial_report.get("trial_rows") or [])
    hardened_rows = [_harden_row(row) for row in trial_rows]
    row_dicts = [asdict(row) for row in hardened_rows]
    required_present_count = sum(1 for row in row_dicts if row.get("receipt_required_fields_present") is True)
    boundary_valid_count = sum(1 for row in row_dicts if row.get("receipt_boundary_fields_valid") is True)
    marker_count = sum(1 for row in row_dicts if row.get("receipt_marker_found") is True)
    hash_pair_count = sum(1 for row in row_dicts if row.get("pre_snapshot_hash_present") is True and row.get("post_snapshot_hash_present") is True)
    source_mutation_count = sum(int(row.get("source_mutation_count") or 0) for row in row_dicts)
    promotion_allowed_count = sum(1 for row in row_dicts if row.get("promotion_allowed_from_receipt") is True)
    release_allowed_count = sum(1 for row in row_dicts if row.get("release_allowed_from_receipt") is True)
    autonomy_allowed_count = sum(1 for row in row_dicts if row.get("autonomy_allowed_from_receipt") is True)
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/manifest_generated_dispatch_fixture_trial_receipt_hardening.py",
        "conscious_agent/manifest_generated_dispatch_fixture_first_isolated_dry_run_trial.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/current_version_staleness_audit.py",
        "tools/smoke_check.py",
    ])
    required_tokens = [
        CURRENT_MILESTONE,
        MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_ID,
        SELF_ROUTE,
        API_ROUTE,
        "build_manifest_generated_dispatch_fixture_trial_receipt_hardening_metadata",
        "build_manifest_generated_dispatch_fixture_trial_receipt_hardening",
        "manifest_generated_dispatch_fixture_trial_receipt_hardening_text",
        "input_trial_receipt_count=1",
        "hardened_receipt_count=1",
        "receipt_required_field_count=14",
        "receipt_boundary_field_count=8",
        "receipt_required_fields_present_count=1",
        "receipt_boundary_fields_valid_count=1",
        "receipt_marker_found_count=1",
        "snapshot_hash_pair_count=1",
        "source_mutation_count=0",
        "promotion_allowed_from_receipt_count=0",
        "release_allowed_from_receipt_count=0",
        "autonomy_allowed_from_receipt_count=0",
        "fixture_files_written=False",
        "generated_wiring_activated=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "manifest_replaces_dashboard_routes=False",
        "manifest_replaces_api_dispatch=False",
        "manifest_replaces_smoke_registry=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
    ]
    checks = [
        {"name": "module-version-current", "ok": MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_VERSION == CURRENT_VERSION, "message": f"module={MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_VERSION}; current={CURRENT_VERSION}"},
        {"name": "input-trial-pass", "ok": trial_report.get("ok") is True and trial_report.get("status") == "pass" and trial_report.get("trial_pass_count") == 1, "message": f"input_status={trial_report.get('status')} input_pass={trial_report.get('trial_pass_count')}"},
        {"name": "receipt-count", "ok": len(row_dicts) == HARDENED_RECEIPT_COUNT, "message": f"hardened_receipts={len(row_dicts)} expected={HARDENED_RECEIPT_COUNT}"},
        {"name": "receipt-required-fields", "ok": required_present_count == HARDENED_RECEIPT_COUNT and all(row.get("receipt_required_field_count") == RECEIPT_REQUIRED_FIELD_COUNT for row in row_dicts), "message": f"required_present={required_present_count} required_fields={RECEIPT_REQUIRED_FIELD_COUNT}"},
        {"name": "receipt-boundary-fields", "ok": boundary_valid_count == HARDENED_RECEIPT_COUNT and all(row.get("receipt_boundary_field_count") == RECEIPT_BOUNDARY_FIELD_COUNT for row in row_dicts), "message": f"boundary_valid={boundary_valid_count} boundary_fields={RECEIPT_BOUNDARY_FIELD_COUNT}"},
        {"name": "receipt-marker-and-hashes", "ok": marker_count == HARDENED_RECEIPT_COUNT and hash_pair_count == HARDENED_RECEIPT_COUNT, "message": f"markers={marker_count} hash_pairs={hash_pair_count}"},
        {"name": "no-source-or-fixture-mutation", "ok": source_mutation_count == 0 and all(row.get("fixture_file_written") is False and row.get("generated_wiring_activated") is False for row in row_dicts), "message": f"source_mutations={source_mutation_count}"},
        {"name": "receipt-cannot-authorize", "ok": promotion_allowed_count == 0 and release_allowed_count == 0 and autonomy_allowed_count == 0, "message": f"promotion={promotion_allowed_count} release={release_allowed_count} autonomy={autonomy_allowed_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "receipt_hardening_only": True,
            "input_trial_receipt_executed": True,
            "hardened_receipts_generated": True,
            "fixture_files_written": False,
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
            "manual_api_dispatch_remains_authoritative": True,
            "manual_smoke_remains_authoritative": True,
            "manifest_replaces_dashboard_routes": False,
            "manifest_replaces_api_dispatch": False,
            "manifest_replaces_smoke_registry": False,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "Hardened receipts are evidence only and cannot promote generated dispatch, authorize release, or expand autonomy."},
        {"name": "documentation-tokens", "ok": all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(row.get("ok") is True for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "receipt_hardening_only": True,
        "input_trial_receipt_count": len(trial_rows),
        "hardened_receipt_count": len(row_dicts),
        "receipt_required_field_count": RECEIPT_REQUIRED_FIELD_COUNT,
        "receipt_boundary_field_count": RECEIPT_BOUNDARY_FIELD_COUNT,
        "receipt_required_fields_present_count": required_present_count,
        "receipt_boundary_fields_valid_count": boundary_valid_count,
        "receipt_marker_found_count": marker_count,
        "snapshot_hash_pair_count": hash_pair_count,
        "source_mutation_count": source_mutation_count,
        "promotion_allowed_from_receipt_count": promotion_allowed_count,
        "release_allowed_from_receipt_count": release_allowed_count,
        "autonomy_allowed_from_receipt_count": autonomy_allowed_count,
        "trial_subprocess_spawn_count": trial_report.get("subprocess_spawn_count"),
        "trial_temp_workspace_count": trial_report.get("temp_workspace_count"),
        "fixture_files_written": False,
        "generated_dashboard_dispatch_written": False,
        "generated_api_dispatch_written": False,
        "generated_smoke_dispatch_written": False,
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
        "hardened_receipt_rows": row_dicts,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def manifest_generated_dispatch_fixture_trial_receipt_hardening_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"input_review_id={report.get('input_review_id')}",
        f"status={report.get('status')}",
        f"input_trial_receipt_count={report.get('input_trial_receipt_count')}",
        f"hardened_receipt_count={report.get('hardened_receipt_count')}",
        f"receipt_required_field_count={report.get('receipt_required_field_count')}",
        f"receipt_boundary_field_count={report.get('receipt_boundary_field_count')}",
        f"receipt_required_fields_present_count={report.get('receipt_required_fields_present_count')}",
        f"receipt_boundary_fields_valid_count={report.get('receipt_boundary_fields_valid_count')}",
        f"receipt_marker_found_count={report.get('receipt_marker_found_count')}",
        f"snapshot_hash_pair_count={report.get('snapshot_hash_pair_count')}",
        f"source_mutation_count={report.get('source_mutation_count')}",
        f"promotion_allowed_from_receipt_count={report.get('promotion_allowed_from_receipt_count')}",
        f"release_allowed_from_receipt_count={report.get('release_allowed_from_receipt_count')}",
        f"autonomy_allowed_from_receipt_count={report.get('autonomy_allowed_from_receipt_count')}",
        f"fixture_files_written={report.get('fixture_files_written')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manifest_replaces_dashboard_routes={report.get('manifest_replaces_dashboard_routes')}",
        f"manifest_replaces_api_dispatch={report.get('manifest_replaces_api_dispatch')}",
        f"manifest_replaces_smoke_registry={report.get('manifest_replaces_smoke_registry')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_required={report.get('operator_approval_required')}",
    ]
    if full:
        for row in report.get("hardened_receipt_rows", []):
            lines.append(
                f"hardened_receipt={row.get('hardened_receipt_id')} family={row.get('dispatch_family')} fixture={row.get('fixture_id')} "
                f"target={row.get('candidate_target')} required_fields={row.get('receipt_required_fields_present')} "
                f"boundary_valid={row.get('receipt_boundary_fields_valid')} marker={row.get('receipt_marker_found')} "
                f"source_mutations={row.get('source_mutation_count')} release_allowed={row.get('release_allowed_from_receipt')} autonomy_allowed={row.get('autonomy_allowed_from_receipt')}"
            )
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1064.0 manifest generated dispatch fixture trial receipt hardening tokens: manifest-generated-dispatch-fixture-trial-receipt-hardening-v1 /manifest-generated-dispatch-fixture-trial-receipt-hardening /api/source-surface/manifest-generated-dispatch-fixture-trial-receipt-hardening build_manifest_generated_dispatch_fixture_trial_receipt_hardening_metadata build_manifest_generated_dispatch_fixture_trial_receipt_hardening manifest_generated_dispatch_fixture_trial_receipt_hardening_text input_trial_receipt_count=1 hardened_receipt_count=1 receipt_required_field_count=14 receipt_boundary_field_count=8 receipt_required_fields_present_count=1 receipt_boundary_fields_valid_count=1 receipt_marker_found_count=1 snapshot_hash_pair_count=1 source_mutation_count=0 promotion_allowed_from_receipt_count=0 release_allowed_from_receipt_count=0 autonomy_allowed_from_receipt_count=0 fixture_files_written=False generated_wiring_activated=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True manifest_replaces_dashboard_routes=False manifest_replaces_api_dispatch=False manifest_replaces_smoke_registry=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
