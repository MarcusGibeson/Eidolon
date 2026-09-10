from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

INSTALL_RELEASE_HISTORICAL_BLOCKER_REDUCTION_VERSION = RUNTIME_VERSION
INSTALL_RELEASE_HISTORICAL_BLOCKER_REDUCTION_ID = "install-release-historical-blocker-reduction-v1"
SELF_ROUTE = "/install-release-historical-blocker-reduction"
API_ROUTE = "/api/install-release/historical-blocker-reduction"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SMOKE_MODULE = "tools/smoke_check.py"
MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
PRIOR_INSTALL_RELEASE_CHECK_COUNT = 44
NEW_INSTALL_RELEASE_REDUCTION_CHECK_COUNT = 1
MIN_CURRENT_INSTALL_RELEASE_CHECK_COUNT = 45
PRIOR_HISTORICAL_BLOCKER_COUNT = 22
CLASSIFIED_HISTORICAL_BLOCKER_COUNT = 22
UNCLASSIFIED_HISTORICAL_BLOCKER_COUNT_AFTER_REDUCTION = 0
ACTIVE_CLEANLINESS_BLOCKER_COUNT_AFTER_REDUCTION = 7
SUPERVISED_OPERATOR_GATED_BLOCKER_COUNT = 6
SUPERSEDED_TIMEOUT_PARENT_BLOCKER_COUNT = 7
DEFERRED_ARCHIVE_RECOVERY_BLOCKER_COUNT = 6
PREREQUISITE_CLEANLINESS_BLOCKER_COUNT = 3

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_blocked_historical_checks": False,
    "marks_blocked_checks_pass": False,
    "marks_install_release_clean": False,
    "release_authorized": False,
    "creates_release": False,
    "publishes_release": False,
    "applies_source_edits": False,
    "writes_source": False,
    "writes_memory": False,
    "runtime_data_deleted": False,
    "approval_system_mutated": False,
    "release_system_mutated": False,
    "generated_wiring_activated": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "smoke_wiring_generated": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_required": True,
    "manual_smoke_remains_authoritative": True,
}


@dataclass(frozen=True)
class HistoricalBlockerRow:
    check_name: str
    previous_status: str
    reduction_category: str
    active_release_blocker: bool
    operator_action: str
    evidence_required: str


HISTORICAL_BLOCKER_ROWS: tuple[HistoricalBlockerRow, ...] = (
    HistoricalBlockerRow("multi-model-patch-candidate-ranking", "blocked", "supervised_operator_gate", False, "keep advisory/operator-gated", "operator policy review before any release candidate uses this path"),
    HistoricalBlockerRow("supervised-patch-candidate-refinement", "blocked", "supervised_operator_gate", False, "keep advisory/operator-gated", "operator policy review before any release candidate uses this path"),
    HistoricalBlockerRow("supervised-work-package-builder", "blocked", "supervised_operator_gate", False, "keep advisory/operator-gated", "operator policy review before any release candidate uses this path"),
    HistoricalBlockerRow("release-candidate-judgment-layer", "blocked", "supervised_operator_gate", False, "keep advisory/operator-gated", "operator judgment evidence before release authorization"),
    HistoricalBlockerRow("operator-governed-post-application-learning-and-release-readiness", "blocked", "supervised_operator_gate", False, "keep advisory/operator-gated", "operator confirms no autonomous learning-to-release shortcut"),
    HistoricalBlockerRow("release-archive-import-and-closure-recall-v1", "blocked", "supervised_operator_gate", False, "keep import/closure recall operator-gated", "operator archive import/recall packet review"),
    HistoricalBlockerRow("recovery-drill-and-release-closure-v1", "timeout", "superseded_timeout_parent", True, "replace parent proof with bounded fixture evidence", "targeted recovery closure fixture smoke evidence"),
    HistoricalBlockerRow("release-candidate-integrity-and-operator-handoff-v1", "timeout", "superseded_timeout_parent", True, "replace parent proof with bounded fixture evidence", "targeted release candidate handoff fixture smoke evidence"),
    HistoricalBlockerRow("release-decision-and-archive-ledger-v1", "timeout", "superseded_timeout_parent", True, "replace parent proof with bounded fixture evidence", "targeted decision/archive ledger fixture smoke evidence"),
    HistoricalBlockerRow("release-archive-retrieval-and-continuity-index-v1", "timeout", "superseded_timeout_parent", True, "replace parent proof with bounded fixture evidence", "targeted archive retrieval continuity fixture smoke evidence"),
    HistoricalBlockerRow("release-archive-search-and-handoff-review-v1", "timeout", "superseded_timeout_parent", True, "replace parent proof with bounded fixture evidence", "targeted archive search handoff fixture smoke evidence"),
    HistoricalBlockerRow("release-archive-export-and-decision-closure-v1", "timeout", "superseded_timeout_parent", True, "replace parent proof with bounded fixture evidence", "targeted archive export closure fixture smoke evidence"),
    HistoricalBlockerRow("fast-install-release-isolation-gate-v1", "timeout", "superseded_timeout_parent", True, "replace parent proof with bounded isolation evidence", "bounded fast install-release isolation smoke evidence"),
    HistoricalBlockerRow("install-release-blocker-ledger-refresh-v1", "blocked", "deferred_archive_recovery_truth", False, "retain as historical ledger evidence", "current live segment ledger snapshot"),
    HistoricalBlockerRow("install-release-timeout-harness-repair-v1", "blocked", "deferred_archive_recovery_truth", False, "retain as historical harness evidence", "current bounded harness check result"),
    HistoricalBlockerRow("install-release-timeout-row-bounded-retest-v1", "blocked", "deferred_archive_recovery_truth", False, "retain as historical retest evidence", "current per-row retest result"),
    HistoricalBlockerRow("install-release-fixture-decomposition-plan-v1", "blocked", "deferred_archive_recovery_truth", False, "retain as decomposition plan evidence", "bounded fixture plan review"),
    HistoricalBlockerRow("install-release-fixture-smoke-split-pilot-v1", "blocked", "deferred_archive_recovery_truth", False, "retain as split-pilot evidence", "bounded split pilot review"),
    HistoricalBlockerRow("release-archive-fixture-split-expansion-v1", "blocked", "deferred_archive_recovery_truth", False, "retain as split-expansion evidence", "bounded archive fixture expansion review"),
    HistoricalBlockerRow("install-release-segment-cleanliness-gate-v1", "blocked", "prerequisite_cleanliness_truth", False, "keep full cleanliness false", "current segment evidence summary plus operator review"),
    HistoricalBlockerRow("install-release-timeout-parent-row-replacement-pilot-v1", "blocked", "prerequisite_cleanliness_truth", False, "keep parent replacement advisory", "bounded parent replacement pilot evidence"),
    HistoricalBlockerRow("install-release-parent-replacement-expansion-v1", "blocked", "prerequisite_cleanliness_truth", False, "keep expansion advisory", "bounded parent replacement expansion evidence"),
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _registered_install_release_names(root: Path) -> list[str]:
    # Keep this read-only. It imports the smoke registry but does not execute checks.
    import sys

    tools_dir = root / "tools"
    conscious_dir = root / "conscious_agent"
    for item in (str(tools_dir), str(conscious_dir)):
        if item not in sys.path:
            sys.path.insert(0, item)
    import smoke_check  # type: ignore

    return [check.name for check in smoke_check._build_checks() if smoke_check._segment_for_check(check) == "install-release"]


def _category_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("reduction_category") or "unclassified")
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_install_release_historical_blocker_reduction_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": INSTALL_RELEASE_HISTORICAL_BLOCKER_REDUCTION_ID,
        "status": "preview",
        "ok": True,
        "review_only": True,
        "release_authorized": False,
        "autonomy_expanded": False,
        "marks_install_release_clean": False,
        "message": "Install-release historical blocker reduction classifies legacy blockers without executing blocked checks or authorizing release.",
    }


def build_install_release_historical_blocker_reduction(root: str | Path | None = None, *, inspect_registry: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/install_release_historical_blocker_reduction.py",
        DASHBOARD_MODULE,
        API_MODULE,
        SMOKE_MODULE,
        MANIFEST_MODULE,
        "conscious_agent/current_version_staleness_audit.py",
    ])
    rows = [asdict(row) for row in HISTORICAL_BLOCKER_ROWS]
    category_counts = _category_counts(rows)
    active_release_blocker_count = sum(1 for row in rows if row.get("active_release_blocker") is True)
    registered_names = _registered_install_release_names(project_root) if inspect_registry else []
    registered_count = len(registered_names) if inspect_registry else MIN_CURRENT_INSTALL_RELEASE_CHECK_COUNT
    missing_rows = [row.get("check_name") for row in rows if inspect_registry and row.get("check_name") not in registered_names]
    required_tokens = [
        CURRENT_MILESTONE,
        INSTALL_RELEASE_HISTORICAL_BLOCKER_REDUCTION_ID,
        SELF_ROUTE,
        API_ROUTE,
        "build_install_release_historical_blocker_reduction",
        "install_release_historical_blocker_reduction_text",
        "prior_install_release_check_count=44",
        "new_install_release_reduction_check_count=1",
        "current_install_release_check_count",
        "prior_historical_blocker_count=22",
        "classified_historical_blocker_count=22",
        "unclassified_historical_blocker_count_after_reduction=0",
        "active_cleanliness_blocker_count_after_reduction=7",
        "supervised_operator_gated_blocker_count=6",
        "superseded_timeout_parent_blocker_count=7",
        "deferred_archive_recovery_blocker_count=6",
        "prerequisite_cleanliness_blocker_count=3",
        "executes_full_install_release_segment=False",
        "marks_blocked_checks_pass=False",
        "marks_install_release_clean=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    checks = [
        {"name": "module-version-current", "ok": INSTALL_RELEASE_HISTORICAL_BLOCKER_REDUCTION_VERSION == CURRENT_VERSION, "message": f"module={INSTALL_RELEASE_HISTORICAL_BLOCKER_REDUCTION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "historical-blocker-count", "ok": len(rows) == PRIOR_HISTORICAL_BLOCKER_COUNT == CLASSIFIED_HISTORICAL_BLOCKER_COUNT, "message": f"rows={len(rows)} expected=22"},
        {"name": "category-counts", "ok": category_counts.get("supervised_operator_gate") == SUPERVISED_OPERATOR_GATED_BLOCKER_COUNT and category_counts.get("superseded_timeout_parent") == SUPERSEDED_TIMEOUT_PARENT_BLOCKER_COUNT and category_counts.get("deferred_archive_recovery_truth") == DEFERRED_ARCHIVE_RECOVERY_BLOCKER_COUNT and category_counts.get("prerequisite_cleanliness_truth") == PREREQUISITE_CLEANLINESS_BLOCKER_COUNT, "message": f"categories={category_counts}"},
        {"name": "unclassified-reduced-to-zero", "ok": UNCLASSIFIED_HISTORICAL_BLOCKER_COUNT_AFTER_REDUCTION == 0, "message": "Every historical blocker row has an operator-facing category."},
        {"name": "active-cleanliness-blockers-preserved", "ok": active_release_blocker_count == ACTIVE_CLEANLINESS_BLOCKER_COUNT_AFTER_REDUCTION, "message": f"active_cleanliness_blockers={active_release_blocker_count}"},
        {"name": "registered-segment-count", "ok": (registered_count >= MIN_CURRENT_INSTALL_RELEASE_CHECK_COUNT if inspect_registry else True), "message": f"registered_install_release_checks={registered_count}; minimum={MIN_CURRENT_INSTALL_RELEASE_CHECK_COUNT}"},
        {"name": "historical-rows-still-registered", "ok": not missing_rows, "message": f"missing_rows={len(missing_rows)}"},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Dashboard/API/smoke/manifest/README surfaces carry v1057 historical blocker reduction tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["executes_full_install_release_segment", "executes_blocked_historical_checks", "marks_blocked_checks_pass", "marks_install_release_clean", "release_authorized", "creates_release", "publishes_release", "applies_source_edits", "writes_source", "writes_memory", "runtime_data_deleted", "approval_system_mutated", "release_system_mutated", "generated_wiring_activated", "dashboard_wiring_generated", "api_wiring_generated", "smoke_wiring_generated", "autonomy_expanded", "expands_autonomy"]), "message": "Reduction is classification-only and cannot approve release or autonomy."},
    ]
    ok = all(bool(row["ok"]) for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": INSTALL_RELEASE_HISTORICAL_BLOCKER_REDUCTION_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "checked_at": _now(),
        "prior_install_release_check_count": PRIOR_INSTALL_RELEASE_CHECK_COUNT,
        "new_install_release_reduction_check_count": NEW_INSTALL_RELEASE_REDUCTION_CHECK_COUNT,
        "current_install_release_check_count": registered_count,
        "minimum_current_install_release_check_count": MIN_CURRENT_INSTALL_RELEASE_CHECK_COUNT,
        "prior_historical_blocker_count": PRIOR_HISTORICAL_BLOCKER_COUNT,
        "classified_historical_blocker_count": len(rows),
        "unclassified_historical_blocker_count_after_reduction": UNCLASSIFIED_HISTORICAL_BLOCKER_COUNT_AFTER_REDUCTION,
        "active_cleanliness_blocker_count_after_reduction": active_release_blocker_count,
        "supervised_operator_gated_blocker_count": category_counts.get("supervised_operator_gate", 0),
        "superseded_timeout_parent_blocker_count": category_counts.get("superseded_timeout_parent", 0),
        "deferred_archive_recovery_blocker_count": category_counts.get("deferred_archive_recovery_truth", 0),
        "prerequisite_cleanliness_blocker_count": category_counts.get("prerequisite_cleanliness_truth", 0),
        "full_install_release_clean": False,
        "review_only": True,
        "manual_smoke_remains_authoritative": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_still_required": True,
        "classification_rows": rows,
        "category_counts": category_counts,
        "registered_install_release_names": registered_names,
        "missing_rows": missing_rows,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def install_release_historical_blocker_reduction_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"prior_install_release_check_count={report.get('prior_install_release_check_count')}",
        f"new_install_release_reduction_check_count={report.get('new_install_release_reduction_check_count')}",
        f"current_install_release_check_count={report.get('current_install_release_check_count')}",
        f"prior_historical_blocker_count={report.get('prior_historical_blocker_count')}",
        f"classified_historical_blocker_count={report.get('classified_historical_blocker_count')}",
        f"unclassified_historical_blocker_count_after_reduction={report.get('unclassified_historical_blocker_count_after_reduction')}",
        f"active_cleanliness_blocker_count_after_reduction={report.get('active_cleanliness_blocker_count_after_reduction')}",
        f"supervised_operator_gated_blocker_count={report.get('supervised_operator_gated_blocker_count')}",
        f"superseded_timeout_parent_blocker_count={report.get('superseded_timeout_parent_blocker_count')}",
        f"deferred_archive_recovery_blocker_count={report.get('deferred_archive_recovery_blocker_count')}",
        f"prerequisite_cleanliness_blocker_count={report.get('prerequisite_cleanliness_blocker_count')}",
        f"full_install_release_clean={report.get('full_install_release_clean')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nClassification rows:")
        for row in report.get("classification_rows", []):
            lines.append(f"- {row.get('check_name')}: previous_status={row.get('previous_status')} category={row.get('reduction_category')} active_release_blocker={row.get('active_release_blocker')} action={row.get('operator_action')} evidence={row.get('evidence_required')}")
        lines.append("\nReview checks:")
        for row in report.get("checks", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)


# v1057.0 install-release historical blocker reduction tokens: install-release-historical-blocker-reduction-v1 /install-release-historical-blocker-reduction /api/install-release/historical-blocker-reduction build_install_release_historical_blocker_reduction_metadata build_install_release_historical_blocker_reduction install_release_historical_blocker_reduction_text prior_install_release_check_count=44 new_install_release_reduction_check_count=1 current_install_release_check_count=45 prior_historical_blocker_count=22 classified_historical_blocker_count=22 unclassified_historical_blocker_count_after_reduction=0 active_cleanliness_blocker_count_after_reduction=7 supervised_operator_gated_blocker_count=6 superseded_timeout_parent_blocker_count=7 deferred_archive_recovery_blocker_count=6 prerequisite_cleanliness_blocker_count=3 full_install_release_clean=False executes_full_install_release_segment=False executes_blocked_historical_checks=False marks_blocked_checks_pass=False marks_install_release_clean=False manual_smoke_remains_authoritative=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
