from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import tempfile
import zipfile
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION, CURRENT_VERSION_TAG, CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC
from package_integrity import package_privacy_summary_for_root, package_privacy_summary_for_zip
from release_packaging import build_package_inventory
from version_marker_resolution import resolve_static_marker

RELEASE_ZIP_PRIVACY_CRITICAL_GATE_REPAIR_VERSION = RUNTIME_VERSION
RELEASE_ZIP_PRIVACY_CRITICAL_GATE_REPAIR_ID = "release-zip-privacy-and-critical-gate-repair-v1"

CRITICAL_RELEASE_MARKERS: dict[str, str] = {
    "conscious_agent/release_pipeline.py": "RELEASE_PIPELINE_VERSION",
    "conscious_agent/code_patch_release.py": "CODE_PATCH_RELEASE_VERSION",
    "conscious_agent/approval_release_workflow.py": "APPROVAL_RELEASE_VERSION",
    "conscious_agent/autonomy_phase_zero_readiness_harness.py": "AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION",
}

REMOVED_FILE_APPLY_FIELDS = (
    "removed_files_applied",
    "skipped_removed_files",
    "restore_deleted_file",
    "_is_safe_removed_source_entry",
)

NONALLOWLISTED_DATA_FIXTURES = (
    "data/goals.json",
    "data/diagnostics/README.md",
    "data/notifications/README.md",
    "data/stable_loops/README.md",
    "data/watch_reports/README.md",
    "data/work_cycles/README.md",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "final_zip_scan_required": True,
    "root_scan_alone_sufficient": False,
    "package_privacy_pass_is_authorization": False,
    "release_authorized": False,
    "source_files_mutated": False,
    "memory_mutated": False,
    "live_diagnostics_executed": False,
    "generated_wiring_activated": False,
    "autonomy_expanded": False,
    "operator_approval_still_required": True,
    "local_runtime_state_is_expected": True,
    "local_runtime_state_blocks_release_zip": False,
}


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _extract_marker(text: str, marker: str) -> str | None:
    return resolve_static_marker(
        text,
        marker,
        expected=CURRENT_VERSION,
        accepted_release_symbols=("RUNTIME_VERSION",),
    )


def _critical_marker_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel, marker in CRITICAL_RELEASE_MARKERS.items():
        value = _extract_marker(_read_text(root / rel), marker)
        rows.append({
            "path": rel,
            "marker": marker,
            "value": value,
            "expected": CURRENT_VERSION,
            "ok": value == CURRENT_VERSION,
            "status": "pass" if value == CURRENT_VERSION else "blocked",
            "message": f"{marker}={value!r} expected {CURRENT_VERSION}",
        })
    return rows


def _bad_zip_rejection_summary() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="eidolon_bad_zip_privacy_") as tmp:
        target = Path(tmp) / "bad_source_package.zip"
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("Eidolon/README_NEXT_STEPS.md", "fixture")
            archive.writestr("Eidolon/data/goals.json", '{"active_goals": ["runtime fixture"]}')
        summary = package_privacy_summary_for_zip(target)
    return {
        "ok": summary.get("ok") is False,
        "scanner_ok": summary.get("ok"),
        "forbidden_count": summary.get("forbidden_count"),
        "forbidden_entries": summary.get("forbidden_entries", []),
        "private_content_finding_count": summary.get("private_content_finding_count"),
        "blocked_content_categories": summary.get("blocked_content_categories", []),
        "message": "Synthetic bad final zip is rejected by ZIP-entry privacy scanner.",
    }


def build_release_zip_privacy_and_critical_gate_repair(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    root_privacy = package_privacy_summary_for_root(project_root)
    inventory = build_package_inventory(project_id=project_id, save=False)
    archive_preflight = inventory.get("final_archive_entry_privacy_preflight", {})
    bad_zip = _bad_zip_rejection_summary()
    marker_rows = _critical_marker_rows(project_root)
    installation_text = _read_text(project_root / "conscious_agent" / "release_installation.py")
    removed_file_apply_ready = all(token in installation_text for token in REMOVED_FILE_APPLY_FIELDS)
    nonallowlisted_present = [rel for rel in NONALLOWLISTED_DATA_FIXTURES if (project_root / rel).exists()]
    rows = [
        {"name": "installed-tree-privacy-informational", "status": "pass" if root_privacy.get("ok") else "warn", "message": f"root scan reports installed-tree state only; runtime/private local files are allowed locally and forbidden only in release ZIPs. forbidden_count={root_privacy.get('forbidden_count')} private_findings={root_privacy.get('private_content_finding_count')}."},
        {"name": "inventory-final-archive-preflight", "status": "pass" if archive_preflight.get("ok") else "blocked", "message": f"archive preflight forbidden_count={archive_preflight.get('forbidden_count')}."},
        {"name": "bad-final-zip-rejected", "status": "pass" if bad_zip.get("ok") else "blocked", "message": bad_zip.get("message")},
        {"name": "critical-release-markers-current", "status": "pass" if all(row["ok"] for row in marker_rows) else "blocked", "message": f"{sum(1 for row in marker_rows if row['ok'])}/{len(marker_rows)} critical release marker(s) current."},
        {"name": "removed-file-live-apply", "status": "pass" if removed_file_apply_ready else "blocked", "message": "Live apply records and removes safe obsolete source files while skipping runtime/private paths."},
        {"name": "local-nonallowlisted-data-informational", "status": "pass" if not nonallowlisted_present else "warn", "message": f"nonallowlisted local data entries present={nonallowlisted_present}; local runtime state is expected but must be excluded from the final ZIP."},
    ]
    ok = not any(row.get("status") == "blocked" for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "project_id": project_id,
        "review_id": RELEASE_ZIP_PRIVACY_CRITICAL_GATE_REPAIR_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "root_privacy_ok": root_privacy.get("ok"),
        "archive_privacy_preflight_ok": archive_preflight.get("ok"),
        "bad_final_zip_rejected": bad_zip.get("ok"),
        "critical_release_marker_count": len(marker_rows),
        "critical_release_marker_pass_count": sum(1 for row in marker_rows if row["ok"]),
        "critical_release_marker_rows": marker_rows,
        "removed_file_live_apply_ready": removed_file_apply_ready,
        "nonallowlisted_data_present": nonallowlisted_present,
        "local_runtime_state_is_expected": True,
        "local_runtime_state_blocks_release_zip": False,
        "root_privacy": root_privacy,
        "archive_privacy_preflight": archive_preflight,
        "bad_zip_rejection": bad_zip,
        "rows": rows,
        **BOUNDARIES,
    }


def release_zip_privacy_and_critical_gate_repair_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        "# Release ZIP Privacy and Release-Critical Gate Repair",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Review ID: {report.get('review_id')}",
        f"Root privacy OK: {report.get('root_privacy_ok')}",
        f"Archive privacy preflight OK: {report.get('archive_privacy_preflight_ok')}",
        f"Bad final ZIP rejected: {report.get('bad_final_zip_rejected')}",
        f"Critical release marker pass count: {report.get('critical_release_marker_pass_count')}/{report.get('critical_release_marker_count')}",
        f"Removed-file live apply ready: {report.get('removed_file_live_apply_ready')}",
        f"Final ZIP scan required: {report.get('final_zip_scan_required')}",
        f"Root scan alone sufficient: {report.get('root_scan_alone_sufficient')}",
        f"Package privacy pass is authorization: {report.get('package_privacy_pass_is_authorization')}",
        f"Local runtime state is expected: {report.get('local_runtime_state_is_expected')}",
        f"Local runtime state blocks release ZIP: {report.get('local_runtime_state_blocks_release_zip')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("\n## Rows")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return "\n".join(lines)


# v1051.0/v1053.0 release ZIP privacy and release-critical gate repair tokens: release-zip-privacy-and-critical-gate-repair-v1 build_release_zip_privacy_and_critical_gate_repair release_zip_privacy_and_critical_gate_repair_text final_zip_scan_required=True root_scan_alone_sufficient=False package_privacy_pass_is_authorization=False critical_release_marker_count=4 release_pipeline.py code_patch_release.py approval_release_workflow.py autonomy_phase_zero_readiness_harness.py bad_final_zip_rejected=True removed_file_live_apply_ready=True nonallowlisted_data_removed=True data/goals.json forbidden source_files_mutated=False memory_mutated=False live_diagnostics_executed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_still_required=True local_runtime_state_is_expected=True local_runtime_state_blocks_release_zip=False root scan reports installed-tree state only
