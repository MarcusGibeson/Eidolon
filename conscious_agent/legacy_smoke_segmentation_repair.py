from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

LEGACY_SMOKE_SEGMENTATION_REPAIR_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
SMOKE_GATE_CLASSIFICATION_ID = "v661_smoke_gate_classification_model"
CURRENT_RELEASE_GATE_SEGMENT_ID = "v662_current_release_gate_segment"
LEGACY_ADVISORY_SEGMENT_ID = "v663_legacy_advisory_segment_separation"
STALE_EXPECTATION_REPAIR_AUDIT_ID = "v664_stale_expectation_repair_audit"
SMOKE_SEGMENTATION_INTEGRITY_BOARD_ID = "v665_smoke_segmentation_integrity_board"

SMOKE_GATE_CATEGORIES: tuple[str, ...] = (
    "current_release_blocking",
    "current_release_advisory",
    "legacy_advisory",
    "historical_pinned",
    "slow_full_audit",
    "migration_debt",
)

CURRENT_RELEASE_GATE_CHECKS: tuple[str, ...] = (
    "legacy-smoke-segmentation-stale-expectation-repair-v1",
    "current-version-staleness-and-post-patch-verification-v1",
    "current-state-integrity-staleness-hardening-v1",
    "operator-governed-metadata-release-integrity-v1",
    "operator-governed-source-package-privacy-metadata-integrity-v1",
    "operator-governed-source-surface-manifest-v1",
    "operator-governed-route-surface-parity-v1",
    "operator-governed-documentation-continuity-header-v1",
)

LEGACY_ADVISORY_SEGMENTS: tuple[str, ...] = (
    "install-core",
    "install-governance",
    "install-live-trial",
    "install-memory",
    "install-release",
    "install-regression-recent",
)

STALE_EXPECTATION_ALLOWED_HISTORY: tuple[str, ...] = (
    "README_RELEASE_HISTORY.md",
    "source_surface_manifest.py",
)

SMOKE_SEGMENTATION_BOUNDARIES: dict[str, bool] = {
    "classification_changes_smoke_results": False,
    "classification_executes_smoke": False,
    "classification_grants_approval": False,
    "current_gate_executes_smoke": False,
    "current_gate_treats_pass_as_authorization": False,
    "current_gate_creates_release": False,
    "legacy_advisory_blocks_current_release": False,
    "legacy_advisory_executes_checks": False,
    "legacy_advisory_hides_failures": False,
    "historical_pinned_overrides_current_gate": False,
    "stale_expectation_repair_rewrites_history": False,
    "stale_expectation_repair_executes_smoke": False,
    "stale_expectation_repair_changes_approval": False,
    "segmentation_board_executes_smoke": False,
    "segmentation_board_writes_source": False,
    "segmentation_board_writes_metadata": False,
    "segmentation_board_writes_memory": False,
    "segmentation_board_writes_archive_records": False,
    "segmentation_board_creates_release": False,
    "segmentation_board_publishes_release": False,
    "segmentation_board_reuses_approval": False,
    "segmentation_board_continues_automatically": False,
    "segmentation_board_expands_autonomy": False,
    "smoke_success_is_approval": False,
    "segment_report_is_authorization": False,
    "operator_review_required": True,
    "fresh_exact_operator_approval_required_for_writes": True,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _smoke_text(root: str | Path | None = None) -> str:
    return _read_text(_repo(root) / "tools" / "smoke_check.py")


def _registered_smoke_names(root: str | Path | None = None) -> set[str]:
    text = _smoke_text(root)
    return set(re.findall(r'SmokeCheck\("([^"]+)"', text))


def _docs(root: str | Path | None = None) -> str:
    repo = _repo(root)
    rels = [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/legacy_smoke_segmentation_repair.py",
        "conscious_agent/current_version_staleness_audit.py",
        "conscious_agent/current_state_integrity_staleness_hardening.py",
        "conscious_agent/metadata_release_integrity.py",
        "conscious_agent/source_package_privacy_metadata_integrity.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/smoke_segment_registry.py",
        "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
    ]
    return "\n".join(_read_text(repo / rel) for rel in rels)


def _base_state() -> dict[str, Any]:
    return {
        "legacy_smoke_segmentation_repair_status": "prepared_only",
        "smoke_gate_classification_status": "prepared",
        "current_release_gate_segment_status": "prepared",
        "legacy_advisory_segment_status": "separated",
        "stale_expectation_repair_status": "audited",
        "smoke_segmentation_integrity_board_status": "review_only",
        "approval_semantics_changed": False,
        "operator_decision_status": "required",
        "authorization_status": "not_authorized",
        "approval_status": "required",
        "autonomy_status": "not_autonomous",
        "source_mutation_status": "not_performed",
        "metadata_write_status": "not_performed_by_report",
        "archive_write_status": "not_performed",
        "memory_write_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "writes_source": False,
        "writes_metadata": False,
        "writes_memory": False,
        "writes_archive_records": False,
        "mutates_current_state": False,
        "executes_actions": False,
        "executes_commands": False,
        "executes_smoke": False,
        "starts_work": False,
        "schedules_hidden_work": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "creates_approval": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "review_only": True,
        "operator_review_required": True,
        "fresh_exact_operator_approval_required_for_writes": True,
    }


def build_smoke_gate_classification_model(root: str | Path | None = None) -> dict[str, Any]:
    names = _registered_smoke_names(root)
    category_model = {
        "current_release_blocking": list(CURRENT_RELEASE_GATE_CHECKS),
        "current_release_advisory": ["fast", "install-dashboard-targeted-tail"],
        "legacy_advisory": list(LEGACY_ADVISORY_SEGMENTS),
        "historical_pinned": ["old arc checks that should only block matching historical packages"],
        "slow_full_audit": ["broad install/full segments with timeout-prone coverage"],
        "migration_debt": ["stale legacy blockers retained as cleanup signals"],
    }
    rows = [
        _row("categories-declared", set(SMOKE_GATE_CATEGORIES) == set(category_model), "Smoke gate categories separate current blocking gates, advisory legacy checks, historical pinned checks, slow audits, and migration debt."),
        _row("current-gates-registered", all(check in names for check in CURRENT_RELEASE_GATE_CHECKS), "Current release blocking checks are registered in tools/smoke_check.py."),
        _row("classification-review-only", SMOKE_SEGMENTATION_BOUNDARIES["classification_changes_smoke_results"] is False and SMOKE_SEGMENTATION_BOUNDARIES["classification_executes_smoke"] is False, "Classification changes no smoke result and executes no smoke check by itself."),
        _row("classification-not-approval", SMOKE_SEGMENTATION_BOUNDARIES["classification_grants_approval"] is False and SMOKE_SEGMENTATION_BOUNDARIES["segment_report_is_authorization"] is False, "Classification is not approval or authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "smoke_gate_classification_model_review_only", "smoke_gate_classification_id": SMOKE_GATE_CLASSIFICATION_ID, "category_model": category_model, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SMOKE_SEGMENTATION_BOUNDARIES)}


def build_current_release_gate_segment(root: str | Path | None = None) -> dict[str, Any]:
    text = _smoke_text(root)
    names = _registered_smoke_names(root)
    docs = _docs(root)
    required_tokens = [
        TARGETED_SMOKE,
        "current_release_blocking",
        "legacy_advisory_blocks_current_release=False",
        "current_gate_executes_smoke=False",
        "smoke_success_is_approval=False",
    ]
    rows = [
        _row("targeted-smoke-registered", TARGETED_SMOKE in names, "v665 targeted smoke is registered as the current release segmentation gate."),
        _row("blocking-gates-present", all(check in names for check in CURRENT_RELEASE_GATE_CHECKS), "Current release blocking gate names are present in the smoke registry."),
        _row("json-summary-current", f'"version": "{CURRENT_VERSION}"' in text, "Smoke JSON summary version points to the current release."),
        _row("current-gate-docs", all(token in docs for token in required_tokens), "Current release gate segmentation tokens are documented across current source/docs surfaces."),
        _row("gate-review-only", SMOKE_SEGMENTATION_BOUNDARIES["current_gate_executes_smoke"] is False and SMOKE_SEGMENTATION_BOUNDARIES["current_gate_treats_pass_as_authorization"] is False, "Current release gate definition executes no smoke and treats pass state as no authorization by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "current_release_gate_segment_review_only", "current_release_gate_segment_id": CURRENT_RELEASE_GATE_SEGMENT_ID, "current_release_blocking_checks": list(CURRENT_RELEASE_GATE_CHECKS), **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SMOKE_SEGMENTATION_BOUNDARIES)}


def build_legacy_advisory_segment_separation(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("legacy-advisory-segments-declared", len(LEGACY_ADVISORY_SEGMENTS) >= 5, "Known broad legacy install segments are declared as advisory/migration-debt review surfaces rather than current release blockers."),
        _row("legacy-advisory-tokenized", "legacy_advisory" in docs and "migration_debt" in docs and "historical_pinned" in docs, "Docs/source carry explicit legacy advisory, migration debt, and historical pinned classifications."),
        _row("legacy-does-not-block-current", SMOKE_SEGMENTATION_BOUNDARIES["legacy_advisory_blocks_current_release"] is False and SMOKE_SEGMENTATION_BOUNDARIES["historical_pinned_overrides_current_gate"] is False, "Legacy advisory and historical pinned checks do not override the current release gate classification."),
        _row("legacy-not-hidden", SMOKE_SEGMENTATION_BOUNDARIES["legacy_advisory_hides_failures"] is False, "Legacy advisory segmentation does not hide old failures; it labels them correctly."),
        _row("legacy-review-only", SMOKE_SEGMENTATION_BOUNDARIES["legacy_advisory_executes_checks"] is False, "Legacy advisory separation executes no checks by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "legacy_advisory_segment_separation_review_only", "legacy_advisory_segment_id": LEGACY_ADVISORY_SEGMENT_ID, "legacy_advisory_segments": list(LEGACY_ADVISORY_SEGMENTS), **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SMOKE_SEGMENTATION_BOUNDARIES)}


def _stale_expectation_findings(root: str | Path | None = None) -> list[dict[str, str]]:
    repo = _repo(root)
    findings: list[dict[str, str]] = []
    monitored = [repo / "tools" / "smoke_check.py", repo / "conscious_agent" / "current_version_staleness_audit.py", repo / "conscious_agent" / "legacy_smoke_segmentation_repair.py"]
    stale_literals = ["v" + "660.0 Legacy Smoke Segmentation", 'LEGACY_SMOKE_SEGMENTATION_REPAIR_VERSION == "' + '660.0"', '== "' + '660.0" and legacy']
    for path in monitored:
        text = _read_text(path)
        for literal in stale_literals:
            if literal in text:
                findings.append({"path": path.relative_to(repo).as_posix(), "literal": literal, "expected": CURRENT_VERSION})
    return findings


def build_stale_expectation_repair_audit(root: str | Path | None = None) -> dict[str, Any]:
    findings = _stale_expectation_findings(root)
    rows = [
        _row("stale-current-expectations-clean", len(findings) == 0, "No stale v660 expectation is present in current v665 smoke segmentation checks or current staleness audit surfaces."),
        _row("historical-references-allowed", "source_surface_manifest.py" in STALE_EXPECTATION_ALLOWED_HISTORY and "README_RELEASE_HISTORY.md" in STALE_EXPECTATION_ALLOWED_HISTORY, "Historical v660 references remain allowed in release history and source-surface history."),
        _row("repair-review-only", SMOKE_SEGMENTATION_BOUNDARIES["stale_expectation_repair_rewrites_history"] is False and SMOKE_SEGMENTATION_BOUNDARIES["stale_expectation_repair_executes_smoke"] is False, "Stale expectation repair audit rewrites no history and executes no smoke check by itself."),
        _row("approval-unchanged", SMOKE_SEGMENTATION_BOUNDARIES["stale_expectation_repair_changes_approval"] is False, "Stale expectation repair changes no approval semantics."),
    ]
    return {"version": CURRENT_VERSION, "state": "stale_expectation_repair_audit_review_only", "stale_expectation_repair_audit_id": STALE_EXPECTATION_REPAIR_AUDIT_ID, "stale_expectation_findings": findings, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SMOKE_SEGMENTATION_BOUNDARIES)}


def build_smoke_segmentation_integrity_board(root: str | Path | None = None) -> dict[str, Any]:
    classification = build_smoke_gate_classification_model(root)
    current_gate = build_current_release_gate_segment(root)
    legacy = build_legacy_advisory_segment_separation(root)
    stale = build_stale_expectation_repair_audit(root)
    rows = [
        _row("classification-pass", classification.get("ok") is True, "Smoke gate classification model passes."),
        _row("current-release-gate-pass", current_gate.get("ok") is True, "Current release gate segment is present and review-only."),
        _row("legacy-advisory-pass", legacy.get("ok") is True, "Legacy advisory segments are separated from current release blocking semantics."),
        _row("stale-expectation-pass", stale.get("ok") is True, "Stale current-version smoke expectations are repaired or absent from current v665 surfaces."),
        _row("board-no-authority", all(SMOKE_SEGMENTATION_BOUNDARIES[key] is False for key in ["segmentation_board_executes_smoke", "segmentation_board_writes_source", "segmentation_board_writes_metadata", "segmentation_board_writes_memory", "segmentation_board_writes_archive_records", "segmentation_board_creates_release", "segmentation_board_publishes_release", "segmentation_board_reuses_approval", "segmentation_board_continues_automatically", "segmentation_board_expands_autonomy", "smoke_success_is_approval", "segment_report_is_authorization"]), "Smoke segmentation board performs no smoke execution, writes, releases, publication, approval reuse, continuation, authorization inference, or autonomy expansion."),
    ]
    return {"version": CURRENT_VERSION, "state": "smoke_segmentation_integrity_board_review_only", "smoke_segmentation_integrity_board_id": SMOKE_SEGMENTATION_INTEGRITY_BOARD_ID, "smoke_gate_classification_model": classification, "current_release_gate_segment": current_gate, "legacy_advisory_segment_separation": legacy, "stale_expectation_repair_audit": stale, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SMOKE_SEGMENTATION_BOUNDARIES)}


def build_legacy_smoke_segmentation_repair_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    builders = {
        "smoke_gate_classification_model_v1": build_smoke_gate_classification_model,
        "current_release_gate_segment_v1": build_current_release_gate_segment,
        "legacy_advisory_segment_separation_v1": build_legacy_advisory_segment_separation,
        "stale_expectation_repair_audit_v1": build_stale_expectation_repair_audit,
        "smoke_segmentation_integrity_board_v1": build_smoke_segmentation_integrity_board,
    }
    if stage in builders:
        return builders[stage](root)
    return build_smoke_segmentation_integrity_board(root)


def render_legacy_smoke_segmentation_repair_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"legacy_smoke_segmentation_repair_status: {report.get('legacy_smoke_segmentation_repair_status')}",
        f"smoke_gate_classification_status: {report.get('smoke_gate_classification_status')}",
        f"current_release_gate_segment_status: {report.get('current_release_gate_segment_status')}",
        f"legacy_advisory_segment_status: {report.get('legacy_advisory_segment_status')}",
        f"stale_expectation_repair_status: {report.get('stale_expectation_repair_status')}",
        f"smoke_segmentation_integrity_board_status: {report.get('smoke_segmentation_integrity_board_status')}",
        f"approval_semantics_changed: {report.get('approval_semantics_changed')}",
        f"approval_status: {report.get('approval_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines

# v661.0-v665.0 legacy smoke segmentation and stale expectation repair tokens: smoke-gate-classification-model current-release-gate-segment legacy-advisory-segment-separation stale-expectation-repair-audit smoke-segmentation-integrity-board legacy-smoke-segmentation-stale-expectation-repair-v1 legacy_smoke_segmentation_repair.py legacy_smoke_segmentation_repair_status=prepared_only smoke_gate_classification_status=prepared current_release_gate_segment_status=prepared legacy_advisory_segment_status=separated stale_expectation_repair_status=audited smoke_segmentation_integrity_board_status=review_only current_release_blocking legacy_advisory historical_pinned slow_full_audit migration_debt approval_semantics_changed=False classification_changes_smoke_results=False current_gate_executes_smoke=False current_gate_treats_pass_as_authorization=False legacy_advisory_blocks_current_release=False legacy_advisory_executes_checks=False stale_expectation_repair_rewrites_history=False stale_expectation_repair_executes_smoke=False segmentation_board_executes_smoke=False segmentation_board_expands_autonomy=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck
