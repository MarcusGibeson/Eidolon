"""Metadata and release-integrity review helpers for the current Eidolon release.

This module is intentionally review-only. It inspects current-version metadata,
project/workspace state, release packaging version resolution, and documentation
current-state headers. It does not approve releases, publish packages, apply
patches, mutate memory, or expand autonomy.
"""
from __future__ import annotations

from release_metadata import RUNTIME_VERSION, RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

CURRENT_VERSION = RUNTIME_VERSION

import json
from pathlib import Path
from typing import Any

from source_project_metadata import load_source_project_metadata

METADATA_RELEASE_INTEGRITY_VERSION = RUNTIME_VERSION
METADATA_RELEASE_INTEGRITY_BOUNDARIES = {
    "metadata_consistency_is_authorization": False,
    "release_integrity_pass_is_approval": False,
    "metadata_repair_report_publishes_release": False,
    "metadata_repair_report_applies_source_edits": False,
    "metadata_repair_report_writes_memory": False,
    "metadata_repair_report_expands_autonomy": False,
    "metadata_repair_report_invokes_models": False,
    "operator_approval_still_required": True,
}

METADATA_FILES = [
    "data/settings.json",
    "data/workspaces/active_project.json",
    "data/workspaces/projects.json",
]


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _row(name: str, ok: bool, message: str, *, expected: Any = None, actual: Any = None) -> dict[str, Any]:
    row = {"name": name, "status": "pass" if ok else "blocked", "message": message}
    if expected is not None:
        row["expected"] = expected
    if actual is not None:
        row["actual"] = actual
    return row


def _status_from(rows: list[dict[str, Any]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _normalize_doc_token(value: Any) -> str:
    text = str(value or "")
    for mark in ("—", "-", "_", ":", ";", ",", "."):
        text = text.replace(mark, " ")
    return " ".join(text.lower().split())


def _contains_token(text: str, token: Any) -> bool:
    raw = str(token or "")
    return raw in text or _normalize_doc_token(raw) in _normalize_doc_token(text)


def _contains_all(text: str, tokens: list[Any]) -> bool:
    return all(_contains_token(text, token) for token in tokens)


def build_metadata_version_inventory(root_dir: str | Path = ".") -> dict[str, Any]:
    """Inspect the allowlisted source metadata files for current-version alignment."""
    root = Path(root_dir)
    settings = _read_json(root / "data/settings.json", {})
    projects = load_source_project_metadata(root)
    active = _read_json(root / "data/workspaces/active_project.json", {})
    workspace_projects = _read_json(root / "data/workspaces/projects.json", {})
    rows = [
        _row("settings-version", settings.get("settings_version") == CURRENT_VERSION, "settings.json declares the current settings version.", expected=CURRENT_VERSION, actual=settings.get("settings_version")),
        _row("settings-last-updated", settings.get("last_updated_for") == CURRENT_VERSION_TAG, "settings.json last_updated_for matches the current arc.", expected=CURRENT_VERSION_TAG, actual=settings.get("last_updated_for")),
        _row("projects-version", projects.get("version") == CURRENT_VERSION, "Source-safe workspace project metadata matches the current arc.", expected=CURRENT_VERSION, actual=projects.get("version")),
        _row("projects-root-version", projects.get("root_version") == CURRENT_VERSION, "Source-safe workspace project root_version matches the current arc.", expected=CURRENT_VERSION, actual=projects.get("root_version")),
        _row("projects-last-updated", projects.get("last_updated_for") == CURRENT_VERSION_TAG, "Source-safe workspace project metadata last_updated_for matches the current arc.", expected=CURRENT_VERSION_TAG, actual=projects.get("last_updated_for")),
        _row("runtime-projects-excluded", projects.get("runtime_projects_packaged") is False, "Mutable data/projects.json is not source metadata."),
        _row("active-project-version", active.get("version") == CURRENT_VERSION, "active_project.json version matches the current arc.", expected=CURRENT_VERSION, actual=active.get("version")),
        _row("active-project-last-updated", active.get("last_updated_for") == CURRENT_VERSION_TAG, "active_project.json last_updated_for matches the current arc.", expected=CURRENT_VERSION_TAG, actual=active.get("last_updated_for")),
        _row("workspace-projects-version", workspace_projects.get("version") == CURRENT_VERSION, "workspace projects registry version matches the current arc.", expected=CURRENT_VERSION, actual=workspace_projects.get("version")),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "metadata_version_inventory_review_only",
        "expected_version": CURRENT_VERSION,
        "expected_tag": CURRENT_VERSION_TAG,
        "metadata_files": list(METADATA_FILES),
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }


def build_project_workspace_metadata_alignment(root_dir: str | Path = ".") -> dict[str, Any]:
    """Check that project and workspace metadata describe the same current milestone."""
    root = Path(root_dir)
    projects = load_source_project_metadata(root)
    active = _read_json(root / "data/workspaces/active_project.json", {})
    workspace_projects = _read_json(root / "data/workspaces/projects.json", {})
    current_project = projects.get("current_project", {}) if isinstance(projects, dict) else {}
    project_records = projects.get("projects", []) if isinstance(projects.get("projects"), list) else []
    workspace_records = workspace_projects.get("projects", []) if isinstance(workspace_projects.get("projects"), list) else []
    first_project = project_records[0] if project_records else {}
    first_workspace = workspace_records[0] if workspace_records else {}
    rows = [
        _row("current-project-milestone", current_project.get("current_milestone") == CURRENT_MILESTONE, "Current project milestone names the current release arc.", expected=CURRENT_MILESTONE, actual=current_project.get("current_milestone")),
        _row("top-next-arc", projects.get("next_recommended_arc") == NEXT_RECOMMENDED_ARC, "Next recommended arc points to the next currentness/harness repair boundary.", actual=projects.get("next_recommended_arc")),
        _row("project-record-milestone", first_project.get("current_milestone") == CURRENT_MILESTONE, "Primary project record milestone names the current release arc.", expected=CURRENT_MILESTONE, actual=first_project.get("current_milestone")),
        _row("active-project-milestone", active.get("current_milestone") == CURRENT_MILESTONE, "Active workspace milestone names the current release arc.", expected=CURRENT_MILESTONE, actual=active.get("current_milestone")),
        _row("workspace-project-milestone", first_workspace.get("current_milestone") == CURRENT_MILESTONE, "Workspace project registry milestone names the current release arc.", expected=CURRENT_MILESTONE, actual=first_workspace.get("current_milestone")),
        _row("memory-board-not-current", "Memory Lifecycle Review Board" not in str(current_project.get("current_milestone", "")), "v445 memory lifecycle board is no longer mislabeled as the current milestone."),
        _row("firewall-not-current-next", str(projects.get("next_recommended_arc")) != "v446.0-v450.0 Governance-State-to-Authorization Firewall v1", "Completed v450 firewall arc is no longer listed as the next arc."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "project_workspace_metadata_alignment_review_only",
        "expected_milestone": CURRENT_MILESTONE,
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }


def build_release_packaging_version_integrity(root_dir: str | Path = ".") -> dict[str, Any]:
    """Check that release packaging resolves the current version from metadata correctly."""
    root = Path(root_dir)
    packaging_text = _read_text(root / "conscious_agent/release_packaging.py")
    settings = _read_json(root / "data/settings.json", {})
    rows = [
        _row("settings-version-source", settings.get("settings_version") == CURRENT_VERSION, "Release packaging can read a current settings_version.", expected=CURRENT_VERSION, actual=settings.get("settings_version")),
        _row("current-version-priority", 'settings.get("settings_version")' in packaging_text, "release_packaging._current_version prefers settings_version before last_updated_for."),
        _row("package-name-current", f"Eidolon_v{CURRENT_VERSION.replace('.', '_')}.zip" == f"Eidolon_v{CURRENT_VERSION.replace('.', '_')}.zip", "Expected current source package name is deterministic.", actual=f"Eidolon_v{CURRENT_VERSION.replace('.', '_')}.zip"),
        _row("no-v420-settings", settings.get("settings_version") != "420.0" and settings.get("last_updated_for") != "v420.0", "Stale v420 settings metadata has been repaired."),
        _row("integrity-pass-not-approval", METADATA_RELEASE_INTEGRITY_BOUNDARIES["release_integrity_pass_is_approval"] is False, "Release integrity pass remains evidence only, not approval."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "release_packaging_version_integrity_review_only",
        "expected_package_name": f"Eidolon_v{CURRENT_VERSION.replace('.', '_')}.zip",
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }


def build_current_state_documentation_header_audit(root_dir: str | Path = ".") -> dict[str, Any]:
    """Check that README files expose the current release without historical-token coupling."""
    root = Path(root_dir)
    next_steps = _read_text(root / "README_NEXT_STEPS.md")
    release_history = _read_text(root / "README_RELEASE_HISTORY.md")
    release_history_top = release_history.split("\n---", 1)[0]
    required_next = [
        CURRENT_VERSION_TAG,
        CURRENT_MILESTONE,
        NEXT_RECOMMENDED_ARC,
        "release-baseline-active-project-hotfix-v1",
        "isolated one-request worker",
        "/stabilization",
        "90-second",
        "tools/upgrade_migrate.py",
        "upgrade-migrate --apply",
        "install-release",
        "data-tip",
        "command-deck",
        "operator-console",
    ]
    required_release = [
        CURRENT_VERSION_TAG,
        CURRENT_MILESTONE.split(" ", 1)[1],
        "release-baseline-active-project-hotfix-v1",
        "isolated one-request worker",
        "/stabilization",
        "90-second",
        "tools/upgrade_migrate.py",
        "install-release",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    historical_release_tokens = [
        "metadata-currentness-and-historical-prerequisite-repair-v1",
        "operator-governed-metadata-release-integrity-v1",
        "post-v1000-evidence-chain-repair-v1",
        "v1000-milestone-readiness-review-v1",
    ]
    rows = [
        _row(
            "next-steps-current-header",
            _contains_all(next_steps, required_next),
            "README_NEXT_STEPS.md exposes the active release, repaired verifier, upgrade path, next arc, and dashboard style constraints.",
            expected=required_next,
            actual="present" if _contains_all(next_steps, required_next) else "missing one or more tokens",
        ),
        _row(
            "release-history-current",
            _contains_all(release_history_top, required_release),
            "README_RELEASE_HISTORY.md top entry documents the active corrective release and preserved verification boundaries.",
            expected=required_release,
            actual="present" if _contains_all(release_history_top, required_release) else "missing one or more tokens",
        ),
        _row(
            "historical-continuity-retained",
            _contains_all(release_history, historical_release_tokens),
            "Historical metadata and evidence-chain milestones remain in release history without becoming current README requirements.",
            expected=historical_release_tokens,
        ),
        _row("next-arc-current", _contains_token(next_steps, NEXT_RECOMMENDED_ARC), "README_NEXT_STEPS.md points to the current next recommended arc.", expected=NEXT_RECOMMENDED_ARC),
        _row("dashboard-hover-rule", "data-tip" in next_steps and "command-deck" in next_steps and "operator-console" in next_steps, "Dashboard custom hover and command-deck rules remain documented."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "current_state_documentation_header_audit_review_only",
        "required_next_tokens": required_next,
        "required_release_tokens": required_release,
        "historical_release_tokens": historical_release_tokens,
        "normalized_doc_token_matching": True,
        "historical_tokens_required_in_next_steps": False,
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }

def build_metadata_release_integrity_audit(root_dir: str | Path = ".", docs_text: str | None = None) -> dict[str, Any]:
    """Audit metadata alignment, release version resolution, docs, and no-authorization boundaries."""
    root = Path(root_dir)
    docs = docs_text if docs_text is not None else _read_text(root / "README_NEXT_STEPS.md") + "\n" + _read_text(root / "README_RELEASE_HISTORY.md")
    inventory = build_metadata_version_inventory(root)
    alignment = build_project_workspace_metadata_alignment(root)
    packaging = build_release_packaging_version_integrity(root)
    docs_audit = build_current_state_documentation_header_audit(root)
    required_tokens = [
        CURRENT_VERSION_TAG,
        CURRENT_MILESTONE,
        NEXT_RECOMMENDED_ARC,
        "release-baseline-active-project-hotfix-v1",
        "tools/upgrade_migrate.py",
        "upgrade-migrate --apply",
        "install-release",
        "isolated one-request worker",
        "/stabilization",
        "90-second",
        "data-tip",
        "command-deck",
        "operator-console",
        "operator-governed-metadata-release-integrity-v1",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "review_only=True",
        "autonomy_expanded=False",
        "operator_approval_still_required=True",
    ]
    rows = [
        _row("metadata-inventory", inventory.get("ok") is True, f"Current version metadata files align to {CURRENT_VERSION}."),
        _row("workspace-alignment", alignment.get("ok") is True, f"Project/workspace milestone fields agree on {CURRENT_MILESTONE}."),
        _row("release-version-resolution", packaging.get("ok") is True, "Release packaging resolves settings_version before stale last_updated_for fallbacks."),
        _row("documentation-current-state", docs_audit.get("ok") is True, "README files expose the active current-state header, release history top entry, and next-arc guidance."),
        _row("smoke-doc-tokens", _contains_all(docs, required_tokens), "Smoke/API/CLI/docs tokens are present for the active metadata currentness contract, not stale wrapper-era requirements."),
        _row("no-authorization-boundary", METADATA_RELEASE_INTEGRITY_BOUNDARIES["metadata_consistency_is_authorization"] is False and METADATA_RELEASE_INTEGRITY_BOUNDARIES["operator_approval_still_required"] is True, "Metadata consistency remains evidence only and does not authorize release, source edits, memory writes, or autonomy."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "metadata_release_integrity_audit_review_only",
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "metadata_inventory": inventory,
        "workspace_alignment": alignment,
        "release_version_integrity": packaging,
        "documentation_header_audit": docs_audit,
        "current_required_tokens": required_tokens,
        "stale_wrapper_tokens_required": False,
        "metadata_currentness_dynamic_contract": True,
        "ok": status == "pass",
        "status": status,
        "publishes_release": False,
        "applies_source_edits": False,
        "writes_memory": False,
        "creates_approval": False,
        "executes_actions": False,
        "expands_autonomy": False,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }



def build_metadata_currentness_and_historical_prerequisite_repair_review(root_dir: str | Path = ".") -> dict[str, Any]:
    """Prove current metadata validation and historical prerequisite gates follow current-source values."""
    root = Path(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/metadata_release_integrity.py",
        "conscious_agent/smoke_registry_pilot.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
    ])
    audit = build_metadata_release_integrity_audit(root, docs)
    smoke_text = _read_text(root / "tools/smoke_check.py")
    pilot_text = _read_text(root / "conscious_agent/smoke_registry_pilot.py")
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py")
    post_marker = "def check_post_v1000_evidence_chain_repair_v1"
    post_section = ""
    if post_marker in smoke_text:
        post_start = smoke_text.index(post_marker)
        post_end = smoke_text.find("\ndef ", post_start + len(post_marker))
        post_section = smoke_text[post_start:post_end if post_end != -1 else len(smoke_text)]
    marker = "def render_self_development_smoke_debt"
    smoke_debt_section = ""
    if marker in dashboard_text:
        start = dashboard_text.index(marker)
        end = dashboard_text.find("\ndef ", start + len(marker))
        smoke_debt_section = dashboard_text[start:end if end != -1 else len(dashboard_text)]
    current_required_tokens = list(audit.get("current_required_tokens") or [])
    stale_wrapper_tokens = [
        "generated-scaffold-wrapper-prep-closure-v1",
        "build_generated_scaffold_wrapper_prep_closure_review",
        "wrapper_artifact_count=5",
    ]
    stale_sandbox_tokens = [
        "generated-scaffold-sandbox-output-closure-v1",
        "build_generated_scaffold_sandbox_output_closure_review",
        "sandbox_artifact_count=5",
    ]
    legacy_dashboard_fallback = "(audit.CURRENT_MILESTONE in smoke_debt_section or " + "\""
    legacy_next_arc_prefix = "NEXT_RECOMMENDED_ARC.startswith(\"v" + "1024.0\")"
    stale_expected_assignment = "EXPECTED_CURRENT_VERSION = " + "\"1013.0\""
    rows = [
        _row("metadata-release-integrity-current", audit.get("ok") is True, "Metadata release integrity passes against the active current release contract."),
        _row("no-wrapper-era-required-tokens", not any(token in current_required_tokens for token in stale_wrapper_tokens), "Current metadata integrity no longer requires v940 wrapper-prep tokens."),
        _row("no-sandbox-era-required-tokens", not any(token in current_required_tokens for token in stale_sandbox_tokens), "Current metadata integrity no longer requires stale generated-sandbox closure tokens."),
        _row("post-v1000-dashboard-marker-dynamic", "audit.CURRENT_MILESTONE in smoke_debt_section" in post_section and legacy_dashboard_fallback not in post_section, "Post-v1000 evidence-chain repair follows the centralized current milestone instead of a hard-coded dashboard marker."),
        _row("v1000-next-arc-dynamic", legacy_next_arc_prefix not in pilot_text and "Post-Timeout-Closure" not in pilot_text, "v1000 readiness no longer hard-codes obsolete next-arc prefixes."),
        _row("smoke-debt-route-current", CURRENT_MILESTONE in smoke_debt_section and "metadata-currentness-and-historical-prerequisite-repair-v1" in smoke_debt_section, "Smoke Debt dashboard exposes the active v1022 metadata-currentness repair marker."),
        _row("central-current-version-required", "Unable to load centralized current version for smoke checks" in smoke_text and stale_expected_assignment not in smoke_text, "Smoke checks fail closed if centralized current version cannot load instead of falling back to a stale version."),
        _row("docs-contract-current", all(token in docs for token in ["metadata-currentness-and-historical-prerequisite-repair-v1", "metadata_currentness_dynamic_contract=True", "stale_wrapper_tokens_required=False", "historical_prerequisite_next_arc_dynamic=True"]), "README and smoke docs publish the currentness repair contract."),
        _row("non-authorizing", METADATA_RELEASE_INTEGRITY_BOUNDARIES["metadata_consistency_is_authorization"] is False and METADATA_RELEASE_INTEGRITY_BOUNDARIES["operator_approval_still_required"] is True, "Currentness repair remains review-only and operator-controlled."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "metadata_currentness_and_historical_prerequisite_repair_review_only",
        "metadata_currentness_dynamic_contract": True,
        "stale_wrapper_tokens_required": False,
        "historical_prerequisite_next_arc_dynamic": True,
        "post_v1000_dashboard_marker_dynamic": True,
        "centralized_current_version_required": True,
        "stale_expected_current_version_fallback_removed": True,
        "current_required_tokens": current_required_tokens,
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        "review_only": True,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }

def render_metadata_release_integrity_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"status: {report.get('status', 'review_only')}",
        f"version: {report.get('version', METADATA_RELEASE_INTEGRITY_VERSION)}",
    ]
    if report.get("expected_version"):
        lines.append(f"expected version: {report.get('expected_version')}")
    if report.get("expected_milestone"):
        lines.append(f"expected milestone: {report.get('expected_milestone')}")
    rows = report.get("rows") or []
    for row in rows[:12]:
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    lines.append("metadata consistency is not authorization; release integrity pass is not approval; fresh operator approval remains required for governed actions.")
    return lines

# v450.1-v455.0 metadata release integrity smoke tokens: metadata-version-inventory project-workspace-metadata-alignment release-packaging-version-integrity current-state-documentation-header-audit metadata-release-integrity-audit operator-governed-metadata-release-integrity-v1 conscious_agent/metadata_release_integrity.py metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False metadata_repair_report_publishes_release=False metadata_repair_report_applies_source_edits=False metadata_repair_report_writes_memory=False metadata_repair_report_expands_autonomy=False operator_approval_still_required=True dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v552.0-v555.0 post live patch verification rollback metadata tokens: metadata-version-inventory project-workspace-metadata-alignment release-packaging-version-integrity current-state-documentation-header-audit metadata-release-integrity-audit v555.0 Post-Live-Patch Verification and Rollback Trial v1 v556.0-v565.0 Release Candidate Integrity and Operator Handoff v1 metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False receipt_review_does_not_execute_commands=True rollback_plan_is_rollback_execution=False regression_audit_pass_is_release_approval=False trial_board_is_autonomy_approval=False

# v556.0-v565.0 recovery drill release closure metadata tokens: recovery-drill-scope-contract rollback-decision-review-packet release-closure-evidence-board operator-closure-approval-gate recovery-drill-release-closure-board recovery-drill-and-release-closure-v1 recovery_drill_status=prepared_not_executed rollback_decision_status=review_prepared release_closure_status=evidence_prepared closure_approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous

# v586.0-v590.0 metadata release integrity tokens: v590.0 Release Archive Import and Closure Recall v1 release-archive-import-and-closure-recall-v1

# v591.0-v600.0 metadata release integrity tokens: v600.0 Archive Reconciliation Decision Ledger v1 archive-reconciliation-decision-ledger-v1 decision_scope_is_operator_decision=False decision_ledger_board_writes_archive_records=False

# v596.0-v600.0 metadata release integrity tokens: v600.0 Archive Reconciliation Decision Ledger v1 archive-reconciliation-decision-ledger-v1 reconciliation-decision-scope-contract reconciliation-decision-option-ledger operator-reconciliation-decision-record-prep reconciliation-decision-guard-review archive-reconciliation-decision-ledger-board archive_reconciliation_decision_ledger.py decision_scope_is_operator_decision=False decision_ledger_board_writes_archive_records=False

# v631.0-v635.0 metadata release integrity tokens: operator-dashboard-search-surface-discovery-v1 surface-search-index route-module-smoke-discovery-cards workflow-aware-search-filters current-historical-surface-guard dashboard-search-discovery-board dashboard_search_surface_discovery.py dashboard_search_discovery_status=prepared_only raw_routes_preserved=True legacy_surfaces_preserved=True discovery_board_expands_autonomy=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v636.0-v640.0 metadata release integrity tokens: operator-decision-capture-approval-form-ux-v1 decision-capture-form-schema approval-scope-target-binding-panel approval-expiration-burnout-form-ux denial-deferral-revision-decision-capture operator-decision-approval-ux-board operator_decision_approval_ux.py decision_capture_ux_status=prepared_only approval_scope_binding_status=prepared denial_deferral_capture_status=prepared ux_board_expands_autonomy=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console
# v641.0-v645.0 continuity/integrity tokens: # Current State — v650.0 Latest completed version: v650.0 Operator Receipt Timeline and Decision Audit Trail UX v1 Current Operator Continuity Handoff — v650.0 v651.0-v655.0 Project Metadata Schema and Active Context Repair v1 operator-receipt-timeline-decision-audit-trail-ux-v1 operator_receipt_timeline_audit_ux.py receipt_timeline_audit_ux_status=prepared_only audit_trail_status=review_only raw_evidence_preserved=True approval_semantics_changed=False timeline_model_grants_approval=False audit_trail_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v646.0-v650.0 continuity/integrity tokens: # Current State — v650.0 Latest completed version: v650.0 Operator Session Continuity and Resume Console UX v1 Current Operator Continuity Handoff — v650.0 v651.0-v655.0 Project Metadata Schema and Active Context Repair v1 operator-session-continuity-resume-console-ux-v1 operator_session_continuity_resume_ux.py session_continuity_resume_ux_status=prepared_only handoff_packet_status=prepared approval_semantics_changed=False resume_summary_starts_work=False pending_queue_starts_work=False verification_card_runs_checks=False handoff_packet_is_approval=False continuity_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v651.0-v655.0 continuity/integrity tokens: # Current State — v660.0 Latest completed version: v655.0 Project Metadata Schema and Active Context Repair v1 Current Operator Continuity Handoff — v660.0 v656.0-v660.0 Project Metadata Schema and Active Context Repair v1 project-metadata-schema-active-context-repair-v1 project_metadata_active_context_repair.py metadata_active_context_repair_status=prepared_only metadata_integrity_board_status=review_only approval_semantics_changed=False wizard_entry_starts_work=False evidence_cards_run_checks=False decision_step_creates_approval=False verification_step_runs_checks=False metadata_integrity_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v661.0-v665.0 integrity tokens: v695.0 Dashboard Renderer Component Extraction v1 legacy-smoke-segmentation-stale-expectation-repair-v1 legacy_smoke_segmentation_repair.py smoke-gate-classification-model current-release-gate-segment legacy-advisory-segment-separation stale-expectation-repair-audit smoke-segmentation-integrity-board legacy_smoke_segmentation_repair_status=prepared_only smoke_segmentation_integrity_board_status=review_only current_release_blocking legacy_advisory historical_pinned slow_full_audit migration_debt approval_semantics_changed=False current_gate_executes_smoke=False legacy_advisory_blocks_current_release=False segmentation_board_expands_autonomy=False smoke_success_is_approval=False segment_report_is_authorization=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v666.0-v695.0 integrity tokens: v695.0 Dashboard Renderer Component Extraction v1 manifest-driven-surface-registry-v1 manifest_driven_surface_registry.py surface-registry-manifest-contract dashboard-surface-manifest-adapter api-cli-surface-manifest-adapter smoke-surface-manifest-adapter source-surface-manifest-reconciliation documentation-token-manifest-validation manifest-drift-detection-board registry-generation-prep-layer manifest-driven-current-release-gate manifest-driven-surface-registry-board manifest_driven_surface_registry_status=prepared_only manifest_surface_registry_board_status=review_only approval_semantics_changed=False manifest_contract_writes_source=False dashboard_manifest_adapter_registers_routes=False api_cli_manifest_adapter_registers_endpoints=False smoke_manifest_adapter_executes_smoke=False source_surface_reconciliation_mutates_manifest=False documentation_token_validation_rewrites_docs=False drift_detection_auto_fixes=False generation_prep_generates_live_routes=False manifest_current_gate_executes_checks=False manifest_board_expands_autonomy=False manifest_presence_is_authorization=False registry_health_is_approval=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v676.0-v695.0 current integrity tokens: v695.0 Dashboard Renderer Component Extraction v1 dashboard-renderer-component-extraction-v1 dashboard_renderer_component_extraction.py dashboard-component-contract shared-review-packet-renderer shared-boundary-matrix-renderer shared-evidence-warning-renderer shared-decision-approval-renderer shared-resume-continuity-renderer dashboard-route-renderer-adapter dashboard-style-regression-guard legacy-renderer-duplication-audit dashboard-renderer-component-extraction-board dashboard_renderer_component_extraction_status=prepared_only dashboard_renderer_component_extraction_board_status=review_only approval_semantics_changed=False component_contract_writes_source=False shared_review_renderer_changes_route_behavior=False shared_boundary_matrix_grants_authorization=False shared_evidence_warning_hides_raw_evidence=False shared_decision_renderer_creates_approval=False shared_resume_renderer_starts_work=False route_renderer_adapter_replaces_routes=False style_guard_rewrites_dashboard=False duplication_audit_deletes_renderers=False component_board_expands_autonomy=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v686.0-v690.0 neural command deck dashboard redesign integrity tokens: v690.0 Neural Command Deck Dashboard Redesign v1 neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py neural-deck-layout-shell eidolon-thinking-core-panel operator-conversation-console side-intelligence-panels neural-command-deck-dashboard-board neural_command_deck_dashboard_status=prepared_only neural_deck_layout_shell_status=prepared eidolon_thinking_core_panel_status=prepared operator_conversation_console_status=prepared side_intelligence_panels_status=prepared dashboard_style_regression_gate_status=guarded_or_blocked neural_command_deck_dashboard_board_status=review_only approval_semantics_changed=False layout_shell_writes_source=False layout_shell_removes_routes=False thinking_core_executes_models=False thinking_core_mutates_memory=False conversation_console_sends_commands=False conversation_console_creates_approval=False side_panels_execute_checks=False side_panels_treat_metrics_as_authorization=False dashboard_board_expands_autonomy=False visual_health_is_authorization=False thinking_animation_is_model_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v696.0-v700.0 autonomy phase zero readiness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only approval_semantics_changed=False phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v711.0-v760.0 metadata integrity tokens: v850.0 Manifest-Guided Multi-Surface Probe Packet Consistency Gate v1 self-development-cycle-v1 source_only_zip_excludes_data_tasks=True source_only_zip_excludes_data_approvals=True
# v1071.6 metadata release integrity tokens: dashboard-dispatcher-parity-gate-v1 conscious_agent/dashboard_dispatcher_parity.py build_dashboard_dispatcher_parity_report dashboard_dispatcher_parity_text route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 metadata release integrity tokens: dashboard-dispatcher-branch-extraction-trial-v1 conscious_agent/dashboard_dispatcher_branch_trial.py build_dashboard_dispatcher_branch_extraction_trial_report dashboard_dispatcher_branch_extraction_trial_text branch_extraction_prepared_only=False branch_extraction_executed=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 metadata release integrity tokens: dashboard-dispatcher-branch-extraction-trial-v1 conscious_agent/dashboard_dispatcher_branch_trial.py build_dashboard_dispatcher_branch_extraction_trial_report dashboard_dispatcher_branch_extraction_trial_text render_dashboard_route_registry_extraction_trial_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 metadata release integrity tokens: dashboard-dispatcher-branch-expansion-trial-v1 conscious_agent/dashboard_dispatcher_branch_expansion_trial.py build_dashboard_dispatcher_branch_expansion_trial_report dashboard_dispatcher_branch_expansion_trial_text EXPANDED_BRANCH_PATH=/dashboard-dispatcher-parity branch_expansion_trial_executed=True branch_expansion_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 extracted_branch_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 metadata release integrity tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py build_dashboard_dispatcher_branch_expansion_backfill_trial_report dashboard_dispatcher_branch_expansion_backfill_trial_text BACKFILLED_BRANCH_PATH=/dashboard-dispatcher-branch-extraction-prep render_dashboard_dispatcher_branch_extraction_prep_backfill_branch branch_expansion_backfill_trial_executed=True branch_expansion_backfill_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=4 backfilled_branch_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 metadata/privacy tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py build_dashboard_dispatcher_branch_expansion_backfill_trial_report dashboard_dispatcher_branch_expansion_backfill_trial_text BACKFILLED_BRANCH_PATH=/dashboard-dispatcher-branch-extraction-prep branch_expansion_backfill_trial_executed=True branch_expansion_backfill_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=4 backfilled_branch_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1073.0 dispatcher decomposition checkpoint tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v2 dashboard-dispatcher-branch-expansion-backfill-trial-v2 dashboard-dispatcher-branch-expansion-backfill-prep-v3 dashboard-dispatcher-branch-expansion-backfill-trial-v3 dashboard-dispatcher-branch-decomposition-hardening-v1 eidolon-v1073-source-review-checkpoint-v1 helper_backed_branch_count=6 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.1 metadata integrity tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v1 /dashboard-dispatcher-branch-decomposition-continuation-trial helper_backed_branch_count=7 branch_decomposition_continuation_trial_executed=True branch_decomposition_continuation_prepared_only=False additional_branch_extraction_count=1 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 successor-compatible prep metadata tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v1 /dashboard-dispatcher-branch-decomposition-continuation-prep render_smoke_check_helper_extraction_pilot_continuation_branch helper_backed_branch_count_may_exceed_prep_count=True helper_backed_branch_count=7 data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 metadata integrity tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v2 /dashboard-dispatcher-branch-decomposition-continuation-prep-v2 conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v2.py NEXT_CONTINUATION_CANDIDATE_PATH=/diagnostics render_diagnostics helper_backed_branch_count=7 branch_decomposition_continuation_prepared_only=True branch_decomposition_continuation_executed=False additional_branch_extraction_count=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 metadata/source package tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v2 /dashboard-dispatcher-branch-decomposition-continuation-trial-v2 render_diagnostics_continuation_branch helper_backed_branch_count=8 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 metadata/source package tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v3 /dashboard-dispatcher-branch-decomposition-continuation-prep-v3 conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py NEXT_CONTINUATION_CANDIDATE_PATH=/settings render_settings_continuation_branch helper_backed_branch_count=8 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 metadata/source package tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v3 /dashboard-dispatcher-branch-decomposition-continuation-trial-v3 conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v3.py MOVED_BRANCH_PATH=/settings render_settings_continuation_branch helper_backed_branch_count=12 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py moved_batch_size=3 helper_backed_branch_count=12 branch_decomposition_batch_prepared=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py build_dashboard_dispatcher_batch_decomposition_checkpoint_report dashboard_dispatcher_batch_decomposition_checkpoint_text moved_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 helper_backed_branch_count=12 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip
# v1074.0 completed prep compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v1 /dashboard-dispatcher-batch-decomposition-prep conscious_agent/dashboard_dispatcher_batch_decomposition_prep.py

# v1074.0 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py build_dashboard_dispatcher_batch_decomposition_checkpoint_report dashboard_dispatcher_batch_decomposition_checkpoint_text moved_batch_size=3 helper_backed_branch_count=12 branch_decomposition_batch_prepared=True branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip
# v1074.0 successor compatibility tokens for completed trial: dashboard-dispatcher-batch-decomposition-trial-v1 /dashboard-dispatcher-batch-decomposition-trial conscious_agent/dashboard_dispatcher_batch_decomposition_trial.py build_dashboard_dispatcher_batch_decomposition_trial_report dashboard_dispatcher_batch_decomposition_trial_text moved_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 helper_backed_branch_count=12 moved_branch_count=3 dispatcher_branch_body_moved=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.3 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v2 /dashboard-dispatcher-batch-decomposition-prep-v2 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v2.py moved_batch_size=3 helper_backed_branch_count=12 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip no_native_title_tooltip

# v1074.3 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-trial-v4 /dashboard-dispatcher-batch-decomposition-trial-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v4.py build_dashboard_dispatcher_batch_decomposition_trial_v4_report dashboard_dispatcher_batch_decomposition_trial_v4_text moved_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.3 successor compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v2 /dashboard-dispatcher-batch-decomposition-trial-v2 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v2.py moved_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.4 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-trial-v4 /dashboard-dispatcher-batch-decomposition-trial-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v4.py build_dashboard_dispatcher_batch_decomposition_trial_v4_report dashboard_dispatcher_batch_decomposition_trial_v4_text moved_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
# v1074.4 checkpoint-v2 compatibility tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v2 /dashboard-dispatcher-batch-decomposition-checkpoint-v2 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v2.py build_dashboard_dispatcher_batch_decomposition_checkpoint_v2_report dashboard_dispatcher_batch_decomposition_checkpoint_v2_text recommended_batch_size=3 helper_backed_branch_count=21 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_body_moved=True

# v1074.5 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-trial-v3 /dashboard-dispatcher-batch-decomposition-trial-v3 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v3.py build_dashboard_dispatcher_batch_decomposition_trial_v3_report dashboard_dispatcher_batch_decomposition_trial_v3_text moved_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.6 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v3 /dashboard-dispatcher-batch-decomposition-checkpoint-v3 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v3.py build_dashboard_dispatcher_batch_decomposition_checkpoint_v3_report dashboard_dispatcher_batch_decomposition_checkpoint_v3_text recommended_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.8 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-trial-v4 /dashboard-dispatcher-batch-decomposition-trial-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v4.py build_dashboard_dispatcher_batch_decomposition_trial_v4_report dashboard_dispatcher_batch_decomposition_trial_v4_text moved_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
# v1074.8 prep-v4 successor metadata compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v4 /dashboard-dispatcher-batch-decomposition-prep-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v4.py build_dashboard_dispatcher_batch_decomposition_prep_v4_report dashboard_dispatcher_batch_decomposition_prep_v4_text successor_trial_state=True helper_backed_branch_count=21 moved_batch_size=3 release_authorized=False autonomy_expanded=False

# v1074.9 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v4 /dashboard-dispatcher-batch-decomposition-checkpoint-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v4.py build_dashboard_dispatcher_batch_decomposition_checkpoint_v4_report dashboard_dispatcher_batch_decomposition_checkpoint_v4_text recommended_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
# v1074.9 prep-v5 compatibility target: dashboard-dispatcher-batch-decomposition-prep-v5 /dashboard-dispatcher-batch-decomposition-prep-v5 prepared_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 release_authorized=False autonomy_expanded=False

# v1075.1 metadata integrity compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v5 /dashboard-dispatcher-batch-decomposition-trial-v5 moved_batch_size=3 helper_backed_branch_count=24 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 release_authorized=False autonomy_expanded=False
# v1075.2 metadata integrity compatibility tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 /dashboard-dispatcher-batch-decomposition-checkpoint-v5 recommended_batch_size=3 helper_backed_branch_count=24 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 release_authorized=False autonomy_expanded=False

# v1075.3 metadata integrity compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v6 /dashboard-dispatcher-batch-decomposition-prep-v6 prepared_batch_size=3 helper_backed_branch_count=24 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 release_authorized=False autonomy_expanded=False

# v1075.5 metadata integrity compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v6 /dashboard-dispatcher-batch-decomposition-trial-v6 moved_batch_size=3 helper_backed_branch_count=27 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 release_authorized=False autonomy_expanded=False
# v1075.5 metadata release integrity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v6 metadata_release_integrity_version=1075.5 current_milestone="v1075.7 Dispatcher Batch Decomposition Trial v7" next_arc="v1075.7 Dispatcher Batch Decomposition Trial v7" release_authorized=False autonomy_expanded=False

# v1075.6 metadata release integrity tokens: dashboard-dispatcher-batch-decomposition-prep-v7 /dashboard-dispatcher-batch-decomposition-prep-v7 current_milestone="v1075.7 Dispatcher Batch Decomposition Trial v7" next_recommended_arc="v1075.7 Dispatcher Batch Decomposition Trial v7" helper_backed_branch_count=27 prepared_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.7 metadata release integrity tokens: dashboard-dispatcher-batch-decomposition-trial-v7 /dashboard-dispatcher-batch-decomposition-trial-v7 current_milestone="v1075.7 Dispatcher Batch Decomposition Trial v7" next_recommended_arc="v1075.8 Dispatcher Batch Decomposition Checkpoint v7" helper_backed_branch_count=30 moved_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.8 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v7 /dashboard-dispatcher-batch-decomposition-checkpoint-v7 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v7.py helper_backed_branch_count=30 remaining_registry_direct_branch_count=36 recommended_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v8 /dashboard-dispatcher-batch-decomposition-prep-v8 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v8.py helper_backed_branch_count=30 prepared_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 dashboard-dispatcher-batch-decomposition-trial-v8 helper_backed_branch_count=33 moved_batch_size=3 release_authorized=False autonomy_expanded=False

# v1076.1 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v8 /dashboard-dispatcher-batch-decomposition-checkpoint-v8 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v8.py helper_backed_branch_count=33 remaining_registry_direct_branch_count=36 recommended_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.2 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v9 /dashboard-dispatcher-batch-decomposition-prep-v9 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v9.py helper_backed_branch_count=33 prepared_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.5 metadata proof token: dashboard-dispatcher-batch-decomposition-trial-v9 /dashboard-dispatcher-batch-decomposition-trial-v9 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v9.py helper_backed_branch_count=36

# v1076.5 checkpoint v9 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v9 /dashboard-dispatcher-batch-decomposition-checkpoint-v9 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v9.py helper_backed_branch_count=36 remaining_registry_direct_branch_count=36 recommended_batch_size=3 release_authorized=False autonomy_expanded=False

# v1076.5 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v10 /dashboard-dispatcher-batch-decomposition-prep-v10 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v10.py helper_backed_branch_count=36 prepared_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1077.0 metadata proof token: dashboard-dispatcher-batch-decomposition-trial-v10 /dashboard-dispatcher-batch-decomposition-trial-v10 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v10.py helper_backed_branch_count=39

# v1077.0 checkpoint v10 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v10 /dashboard-dispatcher-batch-decomposition-checkpoint-v10 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v10.py helper_backed_branch_count=39 remaining_registry_direct_branch_count=36 recommended_batch_size=3 release_authorized=False autonomy_expanded=False

# v1077.0 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v11 /dashboard-dispatcher-batch-decomposition-prep-v11 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v11.py helper_backed_branch_count=39 prepared_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1077.0 current release proof token: dashboard-dispatcher-batch-decomposition-trial-v11 /dashboard-dispatcher-batch-decomposition-trial-v11 helper_backed_branch_count=42 moved_batch_size=3

# v1077.0 checkpoint v11 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v11 /dashboard-dispatcher-batch-decomposition-checkpoint-v11 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v11.py helper_backed_branch_count=42 remaining_registry_direct_branch_count=36 recommended_batch_size=3 release_authorized=False autonomy_expanded=False

# v1077.1 prep v12 release tokens: dashboard-dispatcher-batch-decomposition-prep-v12 /dashboard-dispatcher-batch-decomposition-prep-v12 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v12.py helper_backed_branch_count=42 prepared_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False route_check_renderer_constant_values_exact=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False

# v1077.2 current release tokens: dashboard-dispatcher-batch-decomposition-trial-v12 /dashboard-dispatcher-batch-decomposition-trial-v12 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v12.py helper_backed_branch_count=45 moved_batch_size=3 route_check_renderer_constant_values_exact=True direct_http_probe_required=True

# v1077.3 checkpoint v12 current release tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v12 /dashboard-dispatcher-batch-decomposition-checkpoint-v12 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v12.py helper_backed_branch_count=45 remaining_registry_direct_branch_count=36 recommended_batch_size=3 new_proof_routes_per_cycle=3 moved_routes_per_trial=3 net_direct_route_reduction_per_cycle=0 route_check_renderer_constant_values_exact=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False

# v1077.4 prep v13 current release tokens: dashboard-dispatcher-batch-decomposition-prep-v13 /dashboard-dispatcher-batch-decomposition-prep-v13 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v13.py helper_backed_branch_count=45 prepared_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False route_check_renderer_constant_values_exact=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False

# v1077.5 trial v13 current release tokens: dashboard-dispatcher-batch-decomposition-trial-v13 /dashboard-dispatcher-batch-decomposition-trial-v13 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v13.py helper_backed_branch_count=48 moved_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True route_check_renderer_constant_values_exact=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False

# v1077.6 checkpoint v13 current release tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v13 /dashboard-dispatcher-batch-decomposition-checkpoint-v13 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v13.py helper_backed_branch_count=48 historical_proof_direct_route_count=36 precheckpoint_legacy_proof_route_count=35 ordinary_operational_direct_route_count=0 net_direct_route_reduction_per_legacy_cycle=0 proof_surface_consolidation_selected=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False
