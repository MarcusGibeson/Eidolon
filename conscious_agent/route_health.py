from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ROUTE_HEALTH_VERSION = "1032.0"
CRITICAL_DASHBOARD_ROUTES: tuple[dict[str, str], ...] = (
    {"route": "/approved-application-binding", "arc": "v285", "label": "Approved Application Binding", "expected_status": "200", "governance": "review_only"},
    {"route": "/operator-execution-checklist", "arc": "v285", "label": "Operator Execution Checklist", "expected_status": "200", "governance": "review_only"},
    {"route": "/post-application-result-review", "arc": "v285", "label": "Post Application Result Review", "expected_status": "200", "governance": "review_only"},
    {"route": "/application-outcome-learning", "arc": "v285", "label": "Application Outcome Learning", "expected_status": "200", "governance": "review_only"},
    {"route": "/application-execution-refinement-audit", "arc": "v285", "label": "Application Execution Refinement Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/continuity-state-intake", "arc": "v300", "label": "Continuity State Intake", "expected_status": "200", "governance": "review_only"},
    {"route": "/self-model-snapshot-v2", "arc": "v300", "label": "Self-Model Snapshot v2", "expected_status": "200", "governance": "review_only"},
    {"route": "/purpose-coherence-review", "arc": "v300", "label": "Purpose Coherence Review", "expected_status": "200", "governance": "review_only"},
    {"route": "/supervised-growth-priorities", "arc": "v300", "label": "Supervised Growth Priorities", "expected_status": "200", "governance": "review_only"},
    {"route": "/continuity-kernel-v2-audit", "arc": "v300", "label": "Continuity Kernel v2 Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/identity-expression-boundary", "arc": "v305", "label": "Identity Expression Boundary", "expected_status": "200", "governance": "review_only"},
    {"route": "/personality-trait-ledger", "arc": "v305", "label": "Personality Trait Ledger", "expected_status": "200", "governance": "review_only"},
    {"route": "/voice-affect-style-map", "arc": "v305", "label": "Voice Affect Style Map", "expected_status": "200", "governance": "review_only"},
    {"route": "/coherence-expression-review", "arc": "v305", "label": "Coherence Expression Review", "expected_status": "200", "governance": "review_only"},
    {"route": "/identity-personality-coherence-audit", "arc": "v305", "label": "Identity Personality Coherence Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/dashboard-route-health", "arc": "v310", "label": "Dashboard Route Health", "expected_status": "200", "governance": "review_only"},
    {"route": "/runtime-test-visibility", "arc": "v310", "label": "Runtime Test Visibility", "expected_status": "200", "governance": "review_only"},
    {"route": "/behavioral-expression-preview", "arc": "v310", "label": "Behavioral Expression Preview", "expected_status": "200", "governance": "review_only"},
    {"route": "/style-delta-staging", "arc": "v310", "label": "Style Delta Staging", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-runtime-health-audit", "arc": "v310", "label": "Expression Runtime Health Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-profile-packets", "arc": "v315", "label": "Expression Profile Packets", "expected_status": "200", "governance": "review_only"},
    {"route": "/conversation-scenario-sandbox", "arc": "v315", "label": "Conversation Scenario Sandbox", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-regression-review", "arc": "v315", "label": "Expression Regression Review", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-operator-review-console", "arc": "v315", "label": "Expression Operator Review Console", "expected_status": "200", "governance": "review_only"},
    {"route": "/conversational-expression-sandbox-audit", "arc": "v315", "label": "Conversational Expression Sandbox Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-approval-criteria", "arc": "v320", "label": "Expression Approval Criteria", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-surface-impact-map", "arc": "v320", "label": "Expression Live Surface Impact Map", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-implementation-packet-draft", "arc": "v320", "label": "Expression Implementation Packet Draft", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-rollback-reversion-plan", "arc": "v320", "label": "Expression Rollback Reversion Plan", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-application-bridge-audit", "arc": "v320", "label": "Expression Application Bridge Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-patch-candidates", "arc": "v325", "label": "Expression Patch Candidates", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-diff-preview", "arc": "v325", "label": "Expression Sandbox Diff Preview", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-dry-run-verification-plan", "arc": "v325", "label": "Expression Dry-Run Verification Plan", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-dry-run-review-packet", "arc": "v325", "label": "Expression Dry-Run Review Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-patch-dry-run-audit", "arc": "v325", "label": "Expression Patch Dry-Run Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-trial-packet", "arc": "v330", "label": "Expression Sandbox Trial Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-workspace-plan", "arc": "v330", "label": "Expression Sandbox Workspace Plan", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-verification-matrix", "arc": "v330", "label": "Expression Sandbox Verification Matrix", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-result-review-prep", "arc": "v330", "label": "Expression Sandbox Result Review Prep", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-trial-harness-audit", "arc": "v330", "label": "Expression Sandbox Trial Harness Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-execution-approval-gate", "arc": "v335", "label": "Expression Sandbox Execution Approval Gate", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-workspace-execution-packet", "arc": "v335", "label": "Expression Sandbox Workspace Execution Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-patch-bundle-packet", "arc": "v335", "label": "Expression Sandbox Patch Bundle Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-verification-command-packet", "arc": "v335", "label": "Expression Sandbox Verification Command Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-execution-packet-bridge-audit", "arc": "v335", "label": "Expression Sandbox Execution Packet Bridge Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-trial-evidence-intake", "arc": "v340", "label": "Expression Sandbox Trial Evidence Intake", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-outcome-comparison", "arc": "v340", "label": "Expression Sandbox Outcome Comparison", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-regression-result-review", "arc": "v340", "label": "Expression Sandbox Regression Result Review", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-revision-recommendations", "arc": "v340", "label": "Expression Sandbox Revision Recommendations", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-sandbox-promotion-review-prep", "arc": "v340", "label": "Expression Sandbox Promotion Review Prep", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-promotion-evidence-binder", "arc": "v345", "label": "Expression Promotion Evidence Binder", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-promotion-scope-risk", "arc": "v345", "label": "Expression Live Promotion Scope Risk", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-promotion-verification-rollback", "arc": "v345", "label": "Expression Promotion Verification Rollback", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-promotion-decision-packet", "arc": "v345", "label": "Expression Promotion Decision Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-promotion-packet-assembly-audit", "arc": "v345", "label": "Expression Promotion Packet Assembly Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-application-eligibility-gate", "arc": "v350", "label": "Expression Live Application Eligibility Gate", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-source-change-manifest", "arc": "v350", "label": "Expression Live Source Change Manifest", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-patch-instruction-packet", "arc": "v350", "label": "Expression Live Patch Instruction Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-verification-rollback-packet", "arc": "v350", "label": "Expression Live Verification Rollback Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-application-packet-audit", "arc": "v350", "label": "Expression Live Application Packet Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-execution-approval-intake", "arc": "v355", "label": "Expression Live Execution Approval Intake", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-source-transaction-preimage", "arc": "v355", "label": "Expression Live Source Transaction Preimage", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-manual-execution-checklist", "arc": "v355", "label": "Expression Live Manual Execution Checklist", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-rollback-reversion-packet", "arc": "v355", "label": "Expression Live Rollback Reversion Packet", "expected_status": "200", "governance": "review_only"},
    {"route": "/expression-live-execution-prep-audit", "arc": "v355", "label": "Expression Live Execution Prep Audit", "expected_status": "200", "governance": "review_only"},
    {"route": "/minimal-live-expression-change-candidate", "arc": "v360", "label": "Minimal Live Expression Change Candidate", "expected_status": "200", "governance": "operator_approved_single_use"},
    {"route": "/minimal-live-expression-approval-lock", "arc": "v360", "label": "Minimal Live Expression Approval Lock", "expected_status": "200", "governance": "operator_approved_single_use"},
    {"route": "/minimal-live-expression-patch-transaction", "arc": "v360", "label": "Minimal Live Expression Patch Transaction", "expected_status": "200", "governance": "operator_approved_single_use"},
    {"route": "/minimal-live-expression-application-harness", "arc": "v360", "label": "Minimal Live Expression Application Harness", "expected_status": "200", "governance": "operator_approved_single_use"},
    {"route": "/minimal-live-expression-application-audit", "arc": "v360", "label": "Minimal Live Expression Application Audit", "expected_status": "200", "governance": "operator_approved_single_use"},
    {"route": "/self-maintenance-gate-registry", "arc": "v365", "label": "Self-Maintenance Gate Registry", "expected_status": "200", "governance": "review_only"},
    {"route": "/self-maintenance-version-expectations", "arc": "v365", "label": "Self-Maintenance Version Expectations", "expected_status": "200", "governance": "review_only"},
    {"route": "/governed-surface-metadata-registry", "arc": "v365", "label": "Governed Surface Metadata Registry", "expected_status": "200", "governance": "review_only"},
    {"route": "/smoke-check-legacy-gate-registry", "arc": "v365", "label": "Smoke Check Legacy Gate Registry", "expected_status": "200", "governance": "review_only"},
    {"route": "/self-maintenance-refactor-audit", "arc": "v365", "label": "Self-Maintenance Refactor Audit", "expected_status": "200", "governance": "review_only"},
)

ROUTE_HEALTH_BOUNDARIES = {
    "route_health_auto_fixes_routes": False,
    "route_health_executes_repair_work": False,
    "route_health_mutates_dashboard": False,
    "route_health_starts_server_loops": False,
    "route_health_infers_approval_from_clean_routes": False,
    "route_health_review_only": True,
    "route_health_requires_operator_review": True,
}


def route_registry() -> list[dict[str, str]]:
    return [dict(item) for item in CRITICAL_DASHBOARD_ROUTES]


def build_route_health_registry_summary(dashboard_text: str = "") -> dict[str, Any]:
    registry = route_registry()
    missing = []
    for item in registry:
        token = item["route"]
        if dashboard_text and token not in dashboard_text:
            missing.append(token)
    return {
        "version": ROUTE_HEALTH_VERSION,
        "route_count": len(registry),
        "registered_routes": registry,
        "missing_from_dashboard_text": missing,
        "expected_status": "200",
        "requires_http_probe": True,
        "html_shape_markers": ["command-deck", "operator-console", "data-tip"],
        "auto_fixes": False,
        "review_only": True,
        "boundaries": dict(ROUTE_HEALTH_BOUNDARIES),
    }


def build_smoke_visibility_summary() -> dict[str, Any]:
    return {
        "version": ROUTE_HEALTH_VERSION,
        "tier_manifest": ["version", "import", "dashboard-route-probe", "api-cli-parity", "metadata", "privacy", "extracted-zip"],
        "fast_critical_tier": ["version markers", "dashboard route registry", "metadata labels", "package privacy"],
        "timeout_reporting_required": True,
        "last_completed_stage_report_required": True,
        "route_probe_tier_required": True,
        "executes_commands": False,
        "review_only": True,
    }


def render_route_health_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            if value and isinstance(value[0], dict):
                lines.append(f"- {key}: {len(value)} item(s)")
            else:
                lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        elif isinstance(value, dict):
            lines.append(f"- {key}: {len(value)} field(s)")
        else:
            lines.append(f"- {key}: {value}")
    return lines

# v325.1-v330.0 expression patch sandbox trial harness route-health tokens: expression-sandbox-trial-packet expression-sandbox-workspace-plan expression-sandbox-verification-matrix expression-sandbox-result-review-prep expression-sandbox-trial-harness-audit operator-governed-expression-patch-sandbox-trial-harness-v1 dashboard_http_route_probe_required

# v330.1-v335.0 expression sandbox trial execution packet bridge route-health tokens: expression-sandbox-execution-approval-gate expression-sandbox-workspace-execution-packet expression-sandbox-patch-bundle-packet expression-sandbox-verification-command-packet expression-sandbox-execution-packet-bridge-audit operator-governed-expression-sandbox-trial-execution-packet-bridge-v1 dashboard_http_route_probe_required

# v335.1-v340.0 expression sandbox result intake route-health tokens: expression-sandbox-trial-evidence-intake expression-sandbox-outcome-comparison expression-sandbox-regression-result-review expression-sandbox-revision-recommendations expression-sandbox-promotion-review-prep operator-governed-expression-sandbox-trial-result-intake-and-promotion-review-prep-v1 dashboard_http_route_probe_required

# v340.1-v345.0 expression promotion packet assembly route-health tokens: expression-promotion-evidence-binder expression-live-promotion-scope-risk expression-promotion-verification-rollback expression-promotion-decision-packet expression-promotion-packet-assembly-audit operator-governed-expression-promotion-packet-assembly-layer-v1 dashboard_http_route_probe_required

# v345.1-v350.0 expression live application packet route-health tokens: expression-live-application-eligibility-gate expression-live-source-change-manifest expression-live-patch-instruction-packet expression-live-verification-rollback-packet expression-live-application-packet-audit operator-governed-expression-live-application-packet-drafting-layer-v1 dashboard_http_route_probe_required

# v350.1-v355.0 expression live application execution prep route-health tokens: expression-live-execution-approval-intake expression-live-source-transaction-preimage expression-live-manual-execution-checklist expression-live-rollback-reversion-packet expression-live-execution-prep-audit operator-governed-expression-live-application-execution-prep-v1 dashboard_http_route_probe_required

# v355.1-v360.0 minimal live expression application route-health tokens: minimal-live-expression-change-candidate minimal-live-expression-approval-lock minimal-live-expression-patch-transaction minimal-live-expression-application-harness minimal-live-expression-application-audit operator-approved-minimal-live-expression-application-audit-v1 dashboard_http_route_probe_required

# v365.1-v370.0 minimal live change replay route health tokens: /minimal-live-change-replay-packet /minimal-live-change-expected-actual-comparison /minimal-live-change-regression-drift-detector /minimal-live-change-recovery-recommendation /minimal-live-change-replay-regression-audit /api/minimal-live-change-replay-regression-audit/layer operator-governed-minimal-live-change-replay-and-regression-hardening-v1 dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v370.1-v375.0 modular extraction route health tokens: /self-maintenance-module-extraction-plan /self-maintenance-version-package-gates /self-maintenance-surface-gates /self-maintenance-governance-gates /self-maintenance-modular-extraction-audit /api/self-maintenance-modular-extraction-audit/layer operator-governed-self-maintenance-modular-extraction-v1 dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v375.1-v380.0 live change application trial route health tokens: /live-change-transaction-narrowing /live-change-approval-execution-lock /live-change-real-patch-trial-plan /live-change-operator-confirmed-application-trial /live-change-application-trial-audit /api/live-change-application-trial-audit/layer operator-governed-live-change-application-trial-audit-v1 dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console
# v380.1-v385.0 live patch trial closure route health tokens: /live-patch-trial-result-intake /live-patch-applied-diff-evidence /live-patch-approval-burnout /live-patch-post-trial-regression-review /live-patch-trial-closure-audit /api/live-patch-trial-closure-audit/layer operator-governed-live-patch-trial-closure-audit-v1 dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v385.1-v390.0 second live patch trial route health tokens: /second-minimal-live-patch-candidate /registry-driven-live-patch-approval-validation /registry-driven-live-patch-transaction-lock /second-live-patch-application-harness /second-live-patch-trial-registry-audit /api/second-live-patch-trial-registry-audit/layer operator-governed-second-live-patch-trial-registry-audit-v1 dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console
# v390.1-v395.0 live patch history memory candidate route health tokens: /live-patch-trial-history-ledger /operator-live-patch-decision-patterns /live-patch-supervised-lesson-candidates /live-patch-memory-candidate-governance /live-patch-history-memory-candidate-audit /api/live-patch-history-memory-candidate-audit/layer operator-governed-live-patch-history-and-memory-candidate-audit-v1 dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v395.1-v400.0 memory candidate application trial route health tokens: /memory-candidate-selection-packet /memory-application-approval-lock /memory-write-transaction-preview /operator-confirmed-memory-application-trial /memory-application-trial-audit /api/memory-application-trial-audit/layer operator-governed-memory-application-trial-audit-v1 dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console
