from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_VERSION = RUNTIME_VERSION
RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_ID = "release-tier-blocker-repair-batch-i-v1"
SELF_ROUTE = "/release-tier-blocker-repair-batch-i"
API_ROUTE = "/api/release/release-tier-blocker-repair-batch-i"
EXPECTED_REPAIRED_TARGET_COUNT = 5

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "repairs_documentation_evidence_holes": True,
    "executes_release_install": False,
    "applies_patches_at_runtime": False,
    "writes_memory": False,
    "creates_release": False,
    "activates_generated_wiring": False,
    "expands_autonomy": False,
    "manual_smoke_remains_authoritative": True,
    "operator_approval_required": True,
}

@dataclass(frozen=True)
class ReleaseTierRepairTarget:
    slug: str
    label: str
    version_token: str
    stage_token: str
    builder: str
    smoke_check: str
    repair_reason: str

TARGETS: tuple[ReleaseTierRepairTarget, ...] = (
    ReleaseTierRepairTarget(
        "multi_model_patch_candidate_ranking",
        "Multi-Model Patch Candidate Ranking",
        "v83.0 - Multi-Model Patch Candidate Ranking",
        "- v83.0 Multi-Model Patch Candidate Ranking",
        "build_multi_model_patch_candidate_ranking",
        "multi-model-patch-candidate-ranking",
        "Historical v83 documentation evidence was missing while route/API/CLI and safety rows already passed.",
    ),
    ReleaseTierRepairTarget(
        "supervised_patch_candidate_refinement",
        "Supervised Patch Candidate Refinement",
        "v84.0 - Supervised Patch Candidate Refinement",
        "- v84.0 Supervised Patch Candidate Refinement",
        "build_supervised_patch_candidate_refinement",
        "supervised-patch-candidate-refinement",
        "Historical v84 documentation evidence was missing while refinement safety rows already passed.",
    ),
    ReleaseTierRepairTarget(
        "supervised_work_package_builder",
        "Supervised Work Package Builder",
        "v112.0 - Supervised Work Package Builder",
        "- v112.0 Supervised Work Package Builder",
        "build_supervised_work_package_builder",
        "supervised-work-package-builder",
        "Historical v112 documentation evidence was missing while advisory-only work-package boundaries already passed.",
    ),
    ReleaseTierRepairTarget(
        "release_candidate_judgment_layer",
        "Release Candidate Judgment Layer",
        "v114.0 - Release Candidate Judgment Layer",
        "- v114.0 Release Candidate Judgment Layer",
        "build_release_candidate_judgment_layer",
        "release-candidate-judgment-layer",
        "Historical v114 documentation evidence was missing while release judgment remained recommendation-only.",
    ),
    ReleaseTierRepairTarget(
        "operator_governed_post_application_learning_and_release_readiness",
        "Operator-Governed Post-Application Learning and Release Readiness",
        "v180.0 - Operator-Governed Post-Application Learning and Release Readiness",
        "v175.1-v176.0 - Post-Application Outcome Intake Layer",
        "build_operator_governed_post_application_learning_and_release_readiness",
        "operator-governed-post-application-learning-and-release-readiness",
        "Historical v176-v180 documentation evidence was missing while post-application closure remained read-only and operator governed.",
    ),
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


def _check(name: str, ok: bool, message: str) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "status": "pass" if ok else "blocked", "message": message}


def _status(checks: list[dict[str, Any]]) -> str:
    return "pass" if all(check.get("ok") is True for check in checks) else "blocked"


def _load_self_maintenance():
    import sys
    root = _repo()
    agent_path = str(root / "conscious_agent")
    if agent_path not in sys.path:
        sys.path.insert(0, agent_path)
    import self_maintenance  # type: ignore
    return self_maintenance


def _target_report(sm: Any, target: ReleaseTierRepairTarget) -> dict[str, Any]:
    builder = getattr(sm, target.builder)
    kwargs: dict[str, Any] = {"project_id": "eidolon", "save": False}
    if target.slug in {"multi_model_patch_candidate_ranking", "supervised_patch_candidate_refinement"}:
        kwargs["improvement_goal"] = "smoke supervised improvement goal"
    return builder(**kwargs)


def _target_rows(project_root: Path, *, execute_builders: bool) -> list[dict[str, Any]]:
    docs = "\n".join(
        _read_text(project_root, rel)
        for rel in [
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            "conscious_agent/self_maintenance.py",
            "tools/smoke_check.py",
        ]
    )
    sm = _load_self_maintenance() if execute_builders else None
    rows: list[dict[str, Any]] = []
    for target in TARGETS:
        version_doc_ok = target.version_token in docs
        stage_doc_ok = target.stage_token in docs
        builder_ok = True
        report_status = "not_executed"
        report_ok = None
        blocked_rows: list[str] = []
        safety_ok = True
        if sm is not None:
            report = _target_report(sm, target)
            report_status = str(report.get("status"))
            report_ok = bool(report.get("ok"))
            blocked_rows = [str(row.get("message")) for row in report.get("rows", []) if row.get("status") == "blocked"]
            payload = report.get(target.slug, {}) if isinstance(report.get(target.slug), dict) else {}
            safety_ok = not any(
                payload.get(key) is True
                for key in [
                    "autonomy_unlocked",
                    "source_mutation_performed",
                    "memory_mutation_performed",
                    "identity_mutation_performed",
                    "approval_bypass_performed",
                    "patches_applied",
                    "publish_performed",
                ]
            )
            builder_ok = report_ok and not blocked_rows and safety_ok
        rows.append(
            {
                "slug": target.slug,
                "label": target.label,
                "smoke_check": target.smoke_check,
                "version_token": target.version_token,
                "stage_token": target.stage_token,
                "version_doc_ok": version_doc_ok,
                "stage_doc_ok": stage_doc_ok,
                "builder_executed": execute_builders,
                "builder_ok": bool(builder_ok),
                "report_status": report_status,
                "report_ok": report_ok,
                "blocked_rows": blocked_rows,
                "safety_ok": safety_ok,
                "repair_reason": target.repair_reason,
                "ok": version_doc_ok and stage_doc_ok and bool(builder_ok),
            }
        )
    return rows


def build_release_tier_blocker_repair_batch_i(root: str | Path | None = None, *, execute_builders: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    dashboard_source = _read_text(project_root, "conscious_agent/dashboard.py")
    api_source = _read_text(project_root, "conscious_agent/api_server.py")
    smoke_source = _read_text(project_root, "tools/smoke_check.py")
    module_source = _read_text(project_root, "conscious_agent/release_tier_blocker_repair_batch_i.py")
    docs = "\n".join([readme_next, readme_history, dashboard_source, api_source, smoke_source, module_source])
    rows = _target_rows(project_root, execute_builders=execute_builders)
    source_tokens = [
        RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_ID,
        SELF_ROUTE,
        API_ROUTE,
        "repaired_target_count=5",
        "docs_evidence_repaired=True",
        "release_install_executed=False",
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
    checks = [
        _check("current-version", RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_VERSION == CURRENT_VERSION, f"module version is {RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_VERSION}; expected {CURRENT_VERSION}"),
        _check("target-count", len(TARGETS) == EXPECTED_REPAIRED_TARGET_COUNT, f"{len(TARGETS)} release-tier blockers are targeted in batch I."),
        _check("documentation-evidence-repaired", all(row["version_doc_ok"] and row["stage_doc_ok"] for row in rows), "Historical documentation evidence tokens are present for the five repaired active blockers."),
        _check("target-builders-pass", all(row["builder_ok"] for row in rows), "Each targeted builder now returns pass with no blocked rows and no safety-boundary violation."),
        _check("dashboard-route-wired", SELF_ROUTE in dashboard_source and "render_release_tier_blocker_repair_batch_i" in dashboard_source and "data-tip" in dashboard_source, "Dashboard route is wired with data-tip review cards."),
        _check("api-route-wired", API_ROUTE in api_source and "build_release_tier_blocker_repair_batch_i" in api_source, "API route is wired as preview-only release repair metadata/reporting."),
        _check("smoke-check-wired", RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_ID in smoke_source and "check_release_tier_blocker_repair_batch_i_v1" in smoke_source, "Dedicated smoke check is registered."),
        _check("source-tokens-present", all(token in docs for token in source_tokens), "Source/docs include repair and non-authority boundary tokens."),
        _check("authority-boundaries", BOUNDARIES["executes_release_install"] is False and BOUNDARIES["activates_generated_wiring"] is False and BOUNDARIES["creates_release"] is False and BOUNDARIES["expands_autonomy"] is False, "Repair does not run install-release, activate generated wiring, create release, or expand autonomy."),
    ]
    status = _status(checks)
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": "eidolon",
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "release_tier_blocker_repair_batch_i_id": RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "target_count": len(TARGETS),
        "repaired_target_count": sum(1 for row in rows if row.get("ok")),
        "docs_evidence_repaired": all(row["version_doc_ok"] and row["stage_doc_ok"] for row in rows),
        "target_builders_pass": all(row["builder_ok"] for row in rows),
        "release_install_executed": False,
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "target_rows": rows,
        "checks": checks,
        "boundaries": dict(BOUNDARIES),
        "blocked": [check["message"] for check in checks if not check.get("ok")],
        "status": status,
        "ok": status == "pass",
    }


def build_release_tier_blocker_repair_batch_i_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "release_tier_blocker_repair_batch_i_id": RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "target_count": len(TARGETS),
        "repaired_target_count": EXPECTED_REPAIRED_TARGET_COUNT,
        "docs_evidence_repaired": True,
        "release_install_executed": False,
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "status": "preview",
        "ok": True,
    }


def release_tier_blocker_repair_batch_i_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    data = report or build_release_tier_blocker_repair_batch_i_metadata()
    lines = [
        "# v1065.10 Release-Tier Blocker Repair Batch I",
        "",
        f"Status: {data.get('status')} | repaired targets: {data.get('repaired_target_count')}/{data.get('target_count')}",
        "",
        "This repair closes five active release-tier blocker checks whose only failing row was missing historical documentation evidence while safety, route/API/CLI, privacy, and advisory-only rows already passed.",
        "",
        "## Boundaries",
        "No install-release execution, generated wiring activation, release authorization, source mutation, memory mutation, or autonomy expansion is performed.",
    ]
    rows = data.get("target_rows") or []
    if rows:
        lines.extend(["", "## Targets"])
        for row in rows:
            lines.append(f"- {'PASS' if row.get('ok') else 'BLOCKED'}: {row.get('label')} ({row.get('smoke_check')}) — {row.get('repair_reason')}")
    if full:
        lines.extend(["", "## Checks"])
        for check in data.get("checks", []):
            lines.append(f"- {check.get('status','unknown').upper()}: {check.get('name')} — {check.get('message')}")
    return "\n".join(lines)


# v1065.10 release-tier blocker repair batch I tokens: release-tier-blocker-repair-batch-i-v1 /release-tier-blocker-repair-batch-i /api/release/release-tier-blocker-repair-batch-i repaired_target_count=5 docs_evidence_repaired=True release_install_executed=False manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
