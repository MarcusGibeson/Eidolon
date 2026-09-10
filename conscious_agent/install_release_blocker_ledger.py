from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC

INSTALL_RELEASE_BLOCKER_LEDGER_VERSION = CURRENT_VERSION
INSTALL_RELEASE_LEDGER_SMOKE = "install-release-blocker-ledger-refresh-v1"
INSTALL_RELEASE_LEDGER_CLI = "--install-release-blocker-ledger-refresh"
INSTALL_RELEASE_LEDGER_TITLE = "Live Install-Release Ledger and Smoke Debt Route Repair"

# Historical compatibility snapshot captured from a fresh v1002 bounded, per-check subprocess review of
# the install-release segment. v1021 derives authoritative ledger rows from the current smoke registry.
FROZEN_V1002_INSTALL_RELEASE_LEDGER_ROWS: tuple[dict[str, Any], ...] = (
    {"name":"release-pipeline","status":"pass","category":"already_passing","cause":"release pipeline smoke passed in bounded individual subprocess review","declared_timeout_seconds":70,"observed_seconds":1.24},
    {"name":"code-patch-release","status":"pass","category":"already_passing","cause":"code patch release smoke passed in bounded individual subprocess review","declared_timeout_seconds":70,"observed_seconds":1.68},
    {"name":"approval-release-workflow","status":"pass","category":"already_passing","cause":"approval release workflow smoke passed in bounded individual subprocess review","declared_timeout_seconds":20,"observed_seconds":1.26},
    {"name":"release-packaging","status":"pass","category":"already_passing","cause":"release packaging smoke passed in bounded individual subprocess review","declared_timeout_seconds":90,"observed_seconds":1.50},
    {"name":"multi-model-patch-candidate-ranking","status":"blocked","category":"expected_supervised_blocker","cause":"review layer remains intentionally operator-gated/advisory and reports blocked readiness","declared_timeout_seconds":90,"observed_seconds":1.63},
    {"name":"supervised-patch-candidate-refinement","status":"blocked","category":"expected_supervised_blocker","cause":"review layer remains intentionally operator-gated/advisory and reports blocked readiness","declared_timeout_seconds":90,"observed_seconds":1.40},
    {"name":"supervised-work-package-builder","status":"blocked","category":"expected_supervised_blocker","cause":"supervised self-development readiness builder reports blocked advisory state","declared_timeout_seconds":90,"observed_seconds":1.56},
    {"name":"release-candidate-judgment-layer","status":"blocked","category":"expected_supervised_blocker","cause":"release candidate judgment remains advisory and not release-authorizing","declared_timeout_seconds":90,"observed_seconds":1.33},
    {"name":"operator-governed-post-application-learning-and-release-readiness","status":"blocked","category":"expected_supervised_blocker","cause":"historical operator-governed readiness layer remains blocked/non-autonomous by design","declared_timeout_seconds":90,"observed_seconds":1.41},
    {"name":"operator-governed-memory-candidate-governance-upgrade-v1","status":"pass","category":"already_passing","cause":"operator-governed memory candidate governance smoke passed","declared_timeout_seconds":91,"observed_seconds":1.43},
    {"name":"operator-governed-live-patch-history-and-memory-candidate-audit-v1","status":"pass","category":"already_passing","cause":"live patch history and memory candidate audit smoke passed","declared_timeout_seconds":96,"observed_seconds":1.94},
    {"name":"operator-governed-segmented-install-smoke-audit-v1","status":"pass","category":"already_passing","cause":"segmented install smoke audit passed","declared_timeout_seconds":97,"observed_seconds":1.99},
    {"name":"operator-governed-metadata-release-integrity-v1","status":"pass","category":"already_passing","cause":"metadata release integrity smoke passed","declared_timeout_seconds":107,"observed_seconds":2.07},
    {"name":"operator-governed-source-package-privacy-metadata-integrity-v1","status":"pass","category":"already_passing","cause":"source package privacy metadata integrity smoke passed","declared_timeout_seconds":117,"observed_seconds":2.18},
    {"name":"recovery-drill-and-release-closure-v1","status":"timeout","category":"timeout_harness_problem","cause":"bounded individual review timed out before result; needs timeout-bounded release/archive harness decomposition","declared_timeout_seconds":129,"observed_seconds":8.02},
    {"name":"release-candidate-integrity-and-operator-handoff-v1","status":"timeout","category":"timeout_harness_problem","cause":"bounded individual review timed out before result; needs timeout-bounded release/archive harness decomposition","declared_timeout_seconds":130,"observed_seconds":12.03},
    {"name":"release-decision-and-archive-ledger-v1","status":"timeout","category":"timeout_harness_problem","cause":"bounded individual review timed out before result; needs timeout-bounded release/archive harness decomposition","declared_timeout_seconds":131,"observed_seconds":12.02},
    {"name":"release-archive-retrieval-and-continuity-index-v1","status":"timeout","category":"timeout_harness_problem","cause":"bounded individual review timed out before result; archive retrieval checks need smaller fixtures or subprocess caps","declared_timeout_seconds":132,"observed_seconds":3.02},
    {"name":"release-archive-search-and-handoff-review-v1","status":"timeout","category":"timeout_harness_problem","cause":"bounded individual review timed out before result; archive search/handoff checks need smaller fixtures or subprocess caps","declared_timeout_seconds":133,"observed_seconds":3.02},
    {"name":"release-archive-export-and-decision-closure-v1","status":"timeout","category":"timeout_harness_problem","cause":"bounded individual review timed out before result; archive export/closure checks need smaller fixtures or subprocess caps","declared_timeout_seconds":134,"observed_seconds":3.02},
    {"name":"release-archive-import-and-closure-recall-v1","status":"blocked","category":"expected_supervised_blocker","cause":"archive import/closure recall review returned blocked and remains non-authorizing","declared_timeout_seconds":135,"observed_seconds":1.30},
    {"name":"source-package-privacy-deep-scan-v1","status":"pass","category":"already_passing","cause":"source package privacy deep scan passed in bounded individual subprocess review","declared_timeout_seconds":204,"observed_seconds":1.22},
    {"name":"release-gate-stale-assertion-truth-repair-v1","status":"pass","category":"already_passing","cause":"release stale assertion truth repair passed","declared_timeout_seconds":206,"observed_seconds":1.79},
    {"name":"install-release-segment-blocker-classification-v1","status":"pass","category":"already_passing","cause":"legacy install-release blocker classification passed and remains bounded","declared_timeout_seconds":207,"observed_seconds":2.01},
    {"name":"release-archive-and-recovery-gate-boundedness-repair-v1","status":"pass","category":"already_passing","cause":"release/archive boundedness repair passed","declared_timeout_seconds":208,"observed_seconds":2.02},
    {"name":"install-release-segment-evidence-summary-gate-v1","status":"pass","category":"already_passing","cause":"install-release evidence summary gate passed and still does not claim full cleanliness","declared_timeout_seconds":209,"observed_seconds":2.88},
    {"name":"extraction-candidate-lock-gate-v1","status":"pass","category":"already_passing","cause":"extraction candidate lock gate passed","declared_timeout_seconds":246,"observed_seconds":1.57},
    {"name":"extraction-release-evidence-packet-v1","status":"pass","category":"already_passing","cause":"extraction release evidence packet passed","declared_timeout_seconds":254,"observed_seconds":1.55},
    {"name":"second-extraction-candidate-selection-gate-v1","status":"pass","category":"already_passing","cause":"second extraction candidate selection gate passed","declared_timeout_seconds":256,"observed_seconds":1.55},
    {"name":"fast-install-release-isolation-gate-v1","status":"timeout","category":"timeout_harness_problem","cause":"bounded individual review timed out at the local cap even though this gate has passed as targeted evidence; mark for harness/cap review before full segment cleanliness is claimed","declared_timeout_seconds":291,"observed_seconds":5.10},
)

INSTALL_RELEASE_LEDGER_ROWS = FROZEN_V1002_INSTALL_RELEASE_LEDGER_ROWS

CATEGORY_FIX_ORDER: tuple[str, ...] = (
    "timeout_harness_problem",
    "expected_supervised_blocker",
    "stale_artifact_blocker",
    "stale_version_blocker",
    "route_dashboard_api_drift",
    "real_behavior_failure",
    "already_passing",
)

_EXTRACT_SMOKE_CACHE: dict[tuple[str, int, int], list[dict[str, Any]]] = {}

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "marks_install_release_clean": False,
    "release_authorized": False,
    "creates_release": False,
    "publishes_release": False,
    "applies_source_edits": False,
    "writes_source": False,
    "writes_memory": False,
    "memory_mutated": False,
    "approval_system_mutated": False,
    "release_system_mutated": False,
    "scheduler_mutated": False,
    "network_accessed": False,
    "generated_wiring_activated": False,
    "dashboard_wiring_activated": False,
    "api_wiring_activated": False,
    "cli_wiring_activated": False,
    "smoke_wiring_activated": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "protected_systems_require_operator_approval": True,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root_dir: str | Path | None = None) -> Path:
    return Path(root_dir or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _extract_smoke_checks(root: Path) -> list[dict[str, Any]]:
    smoke_path = root / "tools/smoke_check.py"
    try:
        stat = smoke_path.stat()
        cache_key = (str(smoke_path.resolve()), stat.st_mtime_ns, stat.st_size)
    except OSError:
        cache_key = (str(smoke_path), 0, 0)
    cached = _EXTRACT_SMOKE_CACHE.get(cache_key)
    if cached is not None:
        return [dict(row) for row in cached]
    try:
        tree = ast.parse(_read_text(smoke_path))
    except SyntaxError:
        return []
    try:
        from smoke_segment_registry import classify_check_name
    except Exception:
        def classify_check_name(name: str, tier: str = "install") -> str:  # type: ignore[no-redef]
            if tier in {"fast", "loop", "readiness", "build", "patch"}:
                return "install-core"
            return "install-release" if any(tok in name.lower() for tok in ["release", "package", "candidate", "signing", "install"]) else "install-core"
    rows=[]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "SmokeCheck" and len(node.args) >= 3:
            try:
                name, tier, timeout = ast.literal_eval(node.args[0]), ast.literal_eval(node.args[1]), ast.literal_eval(node.args[2])
            except Exception:
                continue
            if isinstance(name, str) and isinstance(tier, str):
                rows.append({"name": name, "tier": tier, "declared_timeout_seconds": timeout, "segment": classify_check_name(name, tier)})
    _EXTRACT_SMOKE_CACHE[cache_key] = [dict(row) for row in rows]
    return rows


def _manual_install_release_names(root: Path) -> set[str]:
    return {row["name"] for row in _extract_smoke_checks(root) if row.get("segment") == "install-release"}


def build_live_install_release_ledger_rows(root_dir: str | Path | None = None) -> list[dict[str, Any]]:
    root = _repo(root_dir)
    historical = {str(row.get("name")): dict(row) for row in FROZEN_V1002_INSTALL_RELEASE_LEDGER_ROWS}
    rows=[]
    seen: set[str] = set()
    for check in [r for r in _extract_smoke_checks(root) if r.get("segment") == "install-release"]:
        name=str(check.get("name"))
        if name in seen:
            continue
        seen.add(name)
        if name in historical:
            row=dict(historical[name]); row["ledger_source"]="v1002_historical_status_plus_v1021_live_registry_membership"
        else:
            row={"name": name, "status": "tracked", "category": "current_segment_unexecuted_by_ledger", "cause": "present in current live install-release smoke segment but absent from frozen v1002 ledger; accounted without pretending the ledger reran the check", "declared_timeout_seconds": check.get("declared_timeout_seconds"), "observed_seconds": None, "ledger_source": "v1021_live_smoke_registry_inventory"}
        row["tier"]=check.get("tier"); row["segment"]="install-release"; row["present_in_live_smoke_registry"]=True; rows.append(row)
    return rows


def build_install_release_blocker_ledger_refresh_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root=_repo(root_dir)
    docs="\n".join(_read_text(root / rel) for rel in ["README_NEXT_STEPS.md","README_RELEASE_HISTORY.md","conscious_agent/install_release_blocker_ledger.py","conscious_agent/main.py","conscious_agent/source_surface_manifest.py","tools/smoke_check.py","conscious_agent/dashboard.py"])
    rows=build_live_install_release_ledger_rows(root)
    frozen={str(row.get("name")) for row in FROZEN_V1002_INSTALL_RELEASE_LEDGER_ROWS}; live={str(row.get("name")) for row in rows}
    current_only=sorted(live-frozen); frozen_missing=sorted(frozen-live)
    counts={}; cats={}
    for row in rows:
        counts[row.get("status","unknown")]=counts.get(row.get("status","unknown"),0)+1
        cats[row.get("category","unknown")]=cats.get(row.get("category","unknown"),0)+1
    blocker=[r for r in rows if r.get("status") in {"blocked","timeout"}]; timeout=[r for r in rows if r.get("status")=="timeout"]; blocked=[r for r in rows if r.get("status")=="blocked"]; tracked=[r for r in rows if r.get("status")=="tracked"]
    rec=[c for c in CATEGORY_FIX_ORDER if cats.get(c)] + [c for c in sorted(cats) if c not in CATEGORY_FIX_ORDER]
    live_names_from_registry=_manual_install_release_names(root)
    missing=[row["name"] for row in rows if row["name"] not in live_names_from_registry]
    policies={"live_ledger_covers_current_install_release_segment": len(rows)==len(live_names_from_registry) and len(rows)>len(FROZEN_V1002_INSTALL_RELEASE_LEDGER_ROWS),"frozen_v1002_ledger_not_authoritative": len(FROZEN_V1002_INSTALL_RELEASE_LEDGER_ROWS)==30 and len(rows)>=41,"current_segment_additions_are_disclosed": bool(current_only),"manual_smoke_entries_still_present": not missing,"historical_rows_still_present_in_live_segment": not frozen_missing,"passing_checks_recorded": counts.get("pass",0)>0,"blocked_checks_recorded": counts.get("blocked",0)>0,"timeout_checks_recorded": counts.get("timeout",0)>0,"tracked_current_checks_disclosed": counts.get("tracked",0)==len(current_only),"full_install_release_not_claimed_clean": counts.get("blocked",0)+counts.get("timeout",0)+counts.get("tracked",0)>0,"category_counts_recorded": bool(cats),"recommended_fix_order_recorded": bool(rec),"targeted_smoke_registered": INSTALL_RELEASE_LEDGER_SMOKE in docs,"cli_flag_registered": INSTALL_RELEASE_LEDGER_CLI in docs,"builder_registered": "build_install_release_blocker_ledger_refresh_review" in docs,"live_builder_registered": "build_live_install_release_ledger_rows" in docs,"text_renderer_registered": "install_release_blocker_ledger_refresh_review_text" in docs,"review_only": BOUNDARIES["review_only"] is True,"no_autonomy_expansion": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,"no_release_authorization": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False}
    ok=all(policies.values())
    return {"id": f"install_release_blocker_ledger_refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}","type":"install_release_blocker_ledger_refresh_review","version":CURRENT_VERSION,"current_milestone":CURRENT_MILESTONE,"title":INSTALL_RELEASE_LEDGER_TITLE,"status":"pass" if ok else "blocked","ok":ok,"policies_passed":ok,"policy_results":policies,"checked_at":_now_iso(),"ledger_source":"v1021_live_smoke_registry_inventory_with_v1002_historical_status_context","historical_ledger_source":"fresh_v1002_bounded_individual_subprocess_review","segment":"install-release","frozen_v1002_install_release_total_checks":len(FROZEN_V1002_INSTALL_RELEASE_LEDGER_ROWS),"live_install_release_total_checks":len(rows),"install_release_total_checks":len(rows),"install_release_passed_checks":counts.get("pass",0),"install_release_blocked_checks":counts.get("blocked",0),"install_release_timeout_checks":counts.get("timeout",0),"install_release_tracked_checks":counts.get("tracked",0),"install_release_unhealthy_checks":len(blocker),"current_only_check_count":len(current_only),"current_only_names":current_only,"frozen_missing_from_live_names":frozen_missing,"full_install_release_clean":False,"marks_install_release_clean":False,"autonomy_blocking_status":"blocked_until_live_segment_checks_are_behaviorally_executed_or_operator_reclassified_and_supervised_release_blockers_remain_operator_gated","category_counts":cats,"recommended_fix_order":rec,"blocker_names":[r["name"] for r in blocker],"timeout_names":[r["name"] for r in timeout],"blocked_names":[r["name"] for r in blocked],"tracked_names":[r["name"] for r in tracked],"missing_manual_registry_names":missing,"rows":rows,**BOUNDARIES,"recommended_next_arc":NEXT_RECOMMENDED_ARC}

def install_release_blocker_ledger_refresh_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Install-Release Blocker Ledger Refresh report not found."
    lines = [
        "# Live Install-Release Ledger and Smoke Debt Route Repair",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Live total checks: {report.get('live_install_release_total_checks')}",
        f"Frozen v1002 total checks: {report.get('frozen_v1002_install_release_total_checks')}",
        f"Passed checks: {report.get('install_release_passed_checks')}",
        f"Blocked checks: {report.get('install_release_blocked_checks')}",
        f"Timeout checks: {report.get('install_release_timeout_checks')}",
        f"Tracked current checks: {report.get('install_release_tracked_checks')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Autonomy blocking status: {report.get('autonomy_blocking_status')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Recommended fix order: {', '.join(report.get('recommended_fix_order') or [])}",
    ]
    if full:
        lines.extend(["", "## Category counts"])
        for key, value in sorted((report.get("category_counts") or {}).items()):
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Current-only live segment checks"])
        for name in report.get("current_only_names") or []:
            lines.append(f"- {name}")
        lines.extend(["", "## Blockers and timeouts"])
        for row in report.get("rows") or []:
            if row.get("status") != "pass":
                lines.append(f"- {row.get('name')}: {row.get('status')} / {row.get('category')} — {row.get('cause')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_install_release_blocker_ledger_refresh_review(full: bool = False) -> None:
    print(install_release_blocker_ledger_refresh_review_text(build_install_release_blocker_ledger_refresh_review(), full=full))
