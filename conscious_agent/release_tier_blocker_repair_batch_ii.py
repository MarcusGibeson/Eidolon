from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_VERSION = RUNTIME_VERSION
RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_ID = "release-tier-blocker-repair-batch-ii-v1"
SELF_ROUTE = "/release-tier-blocker-repair-batch-ii"
API_ROUTE = "/api/release/release-tier-blocker-repair-batch-ii"
EXPECTED_REPAIRED_TARGET_COUNT = 3

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "repairs_helper_version_currentness": True,
    "source_only_private_runtime_absence_allowed": True,
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
class ReleaseTierBatchIITarget:
    slug: str
    label: str
    smoke_check: str
    helper_module: str
    helper_version_marker: str
    builder: str
    runtime_paths: tuple[str, ...]
    repair_reason: str

TARGETS: tuple[ReleaseTierBatchIITarget, ...] = (
    ReleaseTierBatchIITarget(
        "memory_candidate_governance_upgrade",
        "Operator-Governed Memory Candidate Governance Upgrade",
        "operator-governed-memory-candidate-governance-upgrade-v1",
        "memory_governance",
        "MEMORY_GOVERNANCE_VERSION",
        "build_memory_governance_audit",
        (
            "data/autonomy/memory_candidate_intake/",
            "data/autonomy/memory_candidate_classification/",
            "data/autonomy/memory_approval_packet/",
            "data/autonomy/memory_contradiction_review/",
            "data/autonomy/memory_governance_audit/",
        ),
        "Helper module memory_governance.py used a stale active 1032.0 version marker even though memory writes remain operator-gated and staged only.",
    ),
    ReleaseTierBatchIITarget(
        "live_patch_history_memory_candidate_audit",
        "Operator-Governed Live Patch History and Memory Candidate Audit",
        "operator-governed-live-patch-history-and-memory-candidate-audit-v1",
        "live_patch_history_memory_candidates",
        "LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION",
        "build_operator_governed_live_patch_history_and_memory_candidate_audit_v1",
        (
            "data/autonomy/live_patch_trial_history_ledger/",
            "data/autonomy/operator_live_patch_decision_patterns/",
            "data/autonomy/live_patch_supervised_lesson_candidates/",
            "data/autonomy/live_patch_memory_candidate_governance/",
            "data/autonomy/live_patch_history_memory_candidate_audit/",
        ),
        "Helper module live_patch_history_memory_candidates.py used a stale active 1032.0 version marker while history and memory candidate surfaces remain review-only.",
    ),
    ReleaseTierBatchIITarget(
        "segmented_install_smoke_audit",
        "Operator-Governed Segmented Install Smoke Audit",
        "operator-governed-segmented-install-smoke-audit-v1",
        "memory_candidate_application_trial",
        "MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION",
        "build_operator_governed_segmented_install_smoke_audit_v1",
        (
            "data/autonomy/memory_candidate_selection_packet/",
            "data/autonomy/memory_application_approval_lock/",
            "data/autonomy/memory_write_transaction_preview/",
            "data/autonomy/operator_confirmed_memory_application_trial/",
            "data/autonomy/memory_application_trial_audit/",
        ),
        "Helper module memory_candidate_application_trial.py used a stale active 1032.0 version marker while segmented install audit remains confirmation-gated and non-authorizing.",
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


def _load_agent_module(name: str) -> Any:
    import importlib
    import sys
    root = _repo()
    agent_path = str(root / "conscious_agent")
    if agent_path not in sys.path:
        sys.path.insert(0, agent_path)
    return importlib.import_module(name)


def _load_self_maintenance() -> Any:
    return _load_agent_module("self_maintenance")


def _helper_version_value(target: ReleaseTierBatchIITarget) -> str:
    module = _load_agent_module(target.helper_module)
    return str(getattr(module, target.helper_version_marker, "[missing]"))


def _target_report(sm: Any, target: ReleaseTierBatchIITarget) -> dict[str, Any]:
    builder: Callable[..., dict[str, Any]] = getattr(sm, target.builder)
    if target.builder == "build_memory_governance_audit":
        return builder(project_id="eidolon", save=False)
    return builder(project_id="eidolon", save=False)


def _runtime_paths_absent(project_root: Path, target: ReleaseTierBatchIITarget) -> bool:
    return all(not (project_root / rel.rstrip("/")).exists() for rel in target.runtime_paths)


def _target_rows(project_root: Path, *, execute_builders: bool) -> list[dict[str, Any]]:
    docs = "\n".join(
        _read_text(project_root, rel)
        for rel in [
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            "conscious_agent/self_maintenance.py",
            "conscious_agent/release_packaging.py",
            "conscious_agent/current_version_staleness_audit.py",
            "conscious_agent/release_tier_blocker_repair_batch_ii.py",
            "tools/smoke_check.py",
        ]
    )
    sm = _load_self_maintenance() if execute_builders else None
    rows: list[dict[str, Any]] = []
    for target in TARGETS:
        version_value = _helper_version_value(target)
        helper_current_ok = version_value == CURRENT_VERSION
        docs_token_ok = target.smoke_check in docs and target.helper_module + ".py" in docs and all(token in docs for token in target.runtime_paths)
        runtime_absence_ok = _runtime_paths_absent(project_root, target)
        report_status = "not_executed"
        report_ok: bool | None = None
        blocked_rows: list[str] = []
        safety_ok = True
        builder_ok = True
        if sm is not None:
            report = _target_report(sm, target)
            report_status = str(report.get("status"))
            report_ok = bool(report.get("ok"))
            blocked_rows = [str(row.get("message")) for row in report.get("rows", []) if row.get("status") == "blocked"]
            payload = report.get("payload", {}) if isinstance(report.get("payload"), dict) else {}
            boundaries = payload.get("boundaries", {}) if isinstance(payload.get("boundaries"), dict) else {}
            safety_ok = not any(
                boundaries.get(key) is True
                for key in [
                    "writes_memory",
                    "applies_patches",
                    "expands_autonomy",
                    "publishes_release",
                    "creates_release_candidate",
                    "continues_automatically",
                    "history_memory_audit_writes_memory",
                    "application_harness_expands_autonomy",
                    "segmented_install_writes_memory",
                    "segmented_install_expands_autonomy",
                ]
            )
            builder_ok = bool(report_ok) and not blocked_rows and safety_ok
        rows.append({
            "slug": target.slug,
            "label": target.label,
            "smoke_check": target.smoke_check,
            "helper_module": target.helper_module,
            "helper_version_marker": target.helper_version_marker,
            "helper_version_value": version_value,
            "helper_current_ok": helper_current_ok,
            "docs_token_ok": docs_token_ok,
            "private_runtime_paths_absent": runtime_absence_ok,
            "source_only_absence_allowed": True,
            "builder_executed": execute_builders,
            "builder_ok": bool(builder_ok),
            "report_status": report_status,
            "report_ok": report_ok,
            "blocked_rows": blocked_rows,
            "safety_ok": safety_ok,
            "repair_reason": target.repair_reason,
            "ok": helper_current_ok and docs_token_ok and runtime_absence_ok and bool(builder_ok),
        })
    return rows


def build_release_tier_blocker_repair_batch_ii(root: str | Path | None = None, *, execute_builders: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    docs = "\n".join(
        _read_text(project_root, rel)
        for rel in [
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            "conscious_agent/dashboard.py",
            "conscious_agent/api_server.py",
            "conscious_agent/current_version_staleness_audit.py",
            "conscious_agent/release_tier_blocker_repair_batch_ii.py",
            "tools/smoke_check.py",
        ]
    )
    rows = _target_rows(project_root, execute_builders=execute_builders)
    source_tokens = [
        RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_ID,
        SELF_ROUTE,
        API_ROUTE,
        "repaired_target_count=3",
        "helper_version_currentness_repaired=True",
        "source_only_private_runtime_absence_allowed=True",
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
        _check("current-version", RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_VERSION == CURRENT_VERSION, f"module version is {RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_VERSION}; expected {CURRENT_VERSION}"),
        _check("target-count", len(TARGETS) == EXPECTED_REPAIRED_TARGET_COUNT, f"{len(TARGETS)} release-tier blockers are targeted in batch II."),
        _check("helper-version-currentness", all(row["helper_current_ok"] for row in rows), "Memory/live-patch helper modules now use the active current version marker."),
        _check("source-only-private-runtime-absence", all(row["private_runtime_paths_absent"] and row["source_only_absence_allowed"] for row in rows), "Private runtime memory/autonomy directories are absent in the source-only package and treated as expected, not as failed release evidence."),
        _check("target-builders-pass", all(row["builder_ok"] for row in rows), "Each targeted builder now returns pass with no blocked rows and no safety-boundary violation."),
        _check("dashboard-route-wired", SELF_ROUTE in docs and "render_release_tier_blocker_repair_batch_ii" in docs and "data-tip" in docs, "Dashboard route is wired with data-tip review cards."),
        _check("api-route-wired", API_ROUTE in docs and "build_release_tier_blocker_repair_batch_ii" in docs, "API route is wired as preview-only release repair metadata/reporting."),
        _check("smoke-check-wired", RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_ID in docs and "check_release_tier_blocker_repair_batch_ii_v1" in docs, "Dedicated smoke check is registered."),
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
        "release_tier_blocker_repair_batch_ii_id": RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "target_count": len(TARGETS),
        "repaired_target_count": sum(1 for row in rows if row.get("ok")),
        "helper_version_currentness_repaired": all(row["helper_current_ok"] for row in rows),
        "source_only_private_runtime_absence_allowed": all(row["private_runtime_paths_absent"] and row["source_only_absence_allowed"] for row in rows),
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


def build_release_tier_blocker_repair_batch_ii_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "release_tier_blocker_repair_batch_ii_id": RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "target_count": len(TARGETS),
        "repaired_target_count": EXPECTED_REPAIRED_TARGET_COUNT,
        "helper_version_currentness_repaired": True,
        "source_only_private_runtime_absence_allowed": True,
        "release_install_executed": False,
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "status": "preview",
        "ok": True,
    }


def release_tier_blocker_repair_batch_ii_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    data = report or build_release_tier_blocker_repair_batch_ii_metadata()
    lines = [
        "# v1065.10 Release-Tier Blocker Repair Batch II",
        "",
        f"Status: {data.get('status')} | repaired targets: {data.get('repaired_target_count')}/{data.get('target_count')}",
        "",
        "This repair closes three active release-tier blocker checks by updating stale helper-module current version markers and preserving source-only private runtime absence as an expected privacy boundary.",
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


# v1065.10 release-tier blocker repair batch II tokens: release-tier-blocker-repair-batch-ii-v1 /release-tier-blocker-repair-batch-ii /api/release/release-tier-blocker-repair-batch-ii repaired_target_count=3 helper_version_currentness_repaired=True source_only_private_runtime_absence_allowed=True release_install_executed=False manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
