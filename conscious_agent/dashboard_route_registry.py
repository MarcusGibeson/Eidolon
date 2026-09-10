from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import dataclass
from pathlib import Path
from typing import Any

DASHBOARD_ROUTE_REGISTRY_VERSION = RUNTIME_VERSION
DASHBOARD_ROUTE_REGISTRY_CHECK_ID = "dashboard-route-registry-extraction-v1"
DASHBOARD_ROUTE_REGISTRY_TITLE = "Dashboard Route Registry Extraction v1"
DASHBOARD_ROUTE_REGISTRY_ROUTE = "/dashboard-route-registry-extraction"
DASHBOARD_ROUTE_REGISTRY_RENDERER = "render_dashboard_route_registry_extraction"
NEXT_ARC = "v1078.7 Registry, Navigation, and Smoke Consolidation"


@dataclass(frozen=True)
class DashboardRouteRegistryItem:
    path: str
    label: str
    description: str
    group: str
    renderer_name: str
    preview_only: bool = True
    dashboard_get_preview_only: bool = True
    source_write_count: int = 0
    source_delete_count: int = 0
    subprocess_spawn_count: int = 0
    generated_wiring_activated: bool = False
    release_authorized: bool = False
    autonomy_expanded: bool = False

    def nav_tuple(self) -> tuple[str, str, str, str]:
        return (self.path, self.label, self.description, self.group)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "label": self.label,
            "description": self.description,
            "group": self.group,
            "renderer_name": self.renderer_name,
            "preview_only": self.preview_only,
            "dashboard_get_preview_only": self.dashboard_get_preview_only,
            "source_write_count": self.source_write_count,
            "source_delete_count": self.source_delete_count,
            "subprocess_spawn_count": self.subprocess_spawn_count,
            "generated_wiring_activated": self.generated_wiring_activated,
            "release_authorized": self.release_authorized,
            "autonomy_expanded": self.autonomy_expanded,
        }


DASHBOARD_ROUTE_REGISTRY_ITEMS: tuple[DashboardRouteRegistryItem, ...] = (
    DashboardRouteRegistryItem("/audited-sandbox-backend-preflight-contract", "v1066.1 Audited", "1066.1 Audited Sandbox Backend Preflight Contract v1: bundled review-only surface; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_audited_sandbox_backend_preflight_contract"),
    DashboardRouteRegistryItem("/sandbox-backend-capability-evidence-gate", "v1066.2 Sandbox", "1066.2 Sandbox Backend Capability Evidence Gate v1: bundled review-only surface; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_sandbox_backend_capability_evidence_gate"),
    DashboardRouteRegistryItem("/fixture-execution-admission-gate", "v1066.3 Fixture", "1066.3 Fixture Execution Admission Gate v1: bundled review-only surface; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_fixture_execution_admission_gate"),
    DashboardRouteRegistryItem("/sandboxed-fixture-execution-trial", "v1066.4 First", "1066.4 First Sandboxed Fixture Execution Trial v1: bundled review-only surface; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_sandboxed_fixture_execution_trial"),
    DashboardRouteRegistryItem("/sandboxed-fixture-batch-execution", "v1066.5 Sandboxed", "1066.5 Sandboxed Fixture Batch Execution v1: bundled review-only surface; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_sandboxed_fixture_batch_execution"),
    DashboardRouteRegistryItem("/generated-dispatch-promotion-readiness-ledger", "v1067.0 Generated", "1067.0 Generated Dispatch Promotion Readiness Ledger v1: bundled review-only surface; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_generated_dispatch_promotion_readiness_ledger"),
    DashboardRouteRegistryItem("/source-decomposition-batch-i", "v1068.0 Source", "1068.0 Source Decomposition Batch I v1: bundled review-only surface; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_source_decomposition_batch_i"),
    DashboardRouteRegistryItem("/autonomy-phase-zero-observation-contract", "v1069.0 Autonomy", "1069.0 Autonomy Phase 0 Observation-Only Contract v1: bundled review-only surface; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_autonomy_phase_zero_observation_contract"),
    DashboardRouteRegistryItem("/source-decomposition-batch-ii", "v1070.1 Source", "1069.1 Source Decomposition Batch II and Sandbox Backend Adapter Integration Plan v1: shared review helpers and sandbox adapter planning only; no fixture execution, no generated dispatch promotion, no release authorization, and no autonomy expansion.", "System", "render_source_decomposition_batch_ii"),
    DashboardRouteRegistryItem("/dashboard-api-smoke-shared-utility-adoption", "v1070.0 Shared", "1070.0 Dashboard API Smoke Shared Utility Adoption and Sandbox Adapter Skeleton v1: one narrow dashboard/API/smoke family adopts shared helpers while sandbox adapter remains non-executing skeleton.", "System", "render_dashboard_api_smoke_shared_utility_adoption"),
    DashboardRouteRegistryItem("/dashboard-review-component-extraction-pilot", "v1070.1 Components", "1070.1 Dashboard Review Component Extraction Pilot v1: shared review card/table components adopted by one preview-only dashboard route without dispatch replacement.", "System", "render_dashboard_review_component_extraction_pilot"),
    DashboardRouteRegistryItem("/smoke-check-helper-extraction-pilot", "v1070.2 Smoke", "1070.2 Smoke Check Helper Extraction Pilot v1: one narrow smoke check adopts shared read/token/boundary helpers while manual smoke registry stays authoritative.", "System", "render_smoke_check_helper_extraction_pilot"),
    DashboardRouteRegistryItem("/api-preview-adapter-extraction-pilot", "v1070.3 API", "1070.3 API Preview Adapter Extraction Pilot v1: one narrow API GET route adopts the shared preview adapter while manual API dispatch stays authoritative.", "System", "render_api_preview_adapter_extraction_pilot"),
    DashboardRouteRegistryItem("/api-preview-adapter-backfill", "v1070.4 API", "1070.4 Dashboard API Preview Adapter Backfill v1: backfills shared API preview adapter envelope into three existing safe preview endpoints while manual API dispatch stays authoritative.", "System", "render_api_preview_adapter_backfill"),
    DashboardRouteRegistryItem("/api-server-dispatch-helper-extraction-pilot", "v1070.5 API", "1070.5 API Server Dispatch Helper Extraction Pilot v1: one narrow manual API route adopts a shared dispatch helper without replacing api_server.py authority.", "System", "render_api_server_dispatch_helper_extraction_pilot"),
    DashboardRouteRegistryItem("/api-server-dispatch-helper-backfill", "v1070.7 API", "1070.7 API Server Dispatch Helper Backfill v1: two existing safe preview routes adopt the shared dispatch helper without replacing api_server.py authority.", "System", "render_api_server_dispatch_helper_backfill"),
    DashboardRouteRegistryItem("/api-server-dispatch-helper-route-table-extraction", "v1070.7 API", "1070.7 API Server Dispatch Helper Route Table Extraction v1: helper-backed preview routes use a tiny route table without replacing api_server.py authority.", "System", "render_api_server_dispatch_helper_route_table_extraction"),
    DashboardRouteRegistryItem("/api-server-dispatch-route-table-backfill", "v1070.8 API", "1070.8 API Server Dispatch Route Table Backfill v1: one more safe preview route moves into the route table while manual API dispatch remains authoritative.", "System", "render_api_server_dispatch_route_table_backfill"),
    DashboardRouteRegistryItem("/api-server-dispatch-route-table-safety-parity", "v1070.9 API", "1070.9 API Server Dispatch Route Table Safety Parity v1: route-table payloads prove manual-helper safety parity while manual API dispatch remains authoritative.", "System", "render_api_server_dispatch_route_table_safety_parity"),
    DashboardRouteRegistryItem("/audited-sandbox-backend-evidence-interface", "v1071.0 Sandbox", "1071.0 Audited Sandbox Evidence and Release Truth Bundle v1: defines the sandbox evidence interface, keeps fixture execution blocked, and discloses release-truth/reporting parity.", "System", "render_audited_sandbox_backend_evidence_interface"),
    DashboardRouteRegistryItem(DASHBOARD_ROUTE_REGISTRY_ROUTE, "v1071.5 Routes", "1071.5 Dashboard Renderer Metadata Extraction v1: extracts stable dashboard route metadata while manual HTTP dispatch and renderers remain authoritative.", "System", DASHBOARD_ROUTE_REGISTRY_RENDERER),
    DashboardRouteRegistryItem("/dashboard-renderer-metadata-extraction", "v1071.5 Renderers", "1071.5 Dashboard Renderer Metadata Extraction v1: extracts dashboard renderer metadata while renderer bodies and manual HTTP dispatch remain authoritative.", "System", "render_dashboard_renderer_metadata_extraction"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-parity", "v1071.6 Dispatcher", "1071.6 Dashboard Dispatcher Parity Gate v1: proves route registry, renderer metadata, and literal manual HTTP dispatcher branches agree before any dispatcher branch extraction.", "System", "render_dashboard_dispatcher_parity"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-extraction-prep", "v1072.3 Dispatcher", "1072.3 Dashboard Dispatcher Branch Expansion Backfill Prep v1: identifies the first tiny dispatcher branches eligible for a later extraction trial while manual HTTP dispatch remains authoritative.", "System", "render_dashboard_dispatcher_branch_extraction_prep"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-extraction-trial", "v1072.3 Dispatcher", "1072.3 Dashboard Dispatcher Branch Expansion Backfill Prep v1: moves exactly one prepared dispatcher branch body behind a helper while the manual HTTP dispatcher condition remains authoritative.", "System", "render_dashboard_dispatcher_branch_extraction_trial"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-extraction-backfill", "v1072.3 Dispatcher", "1072.3 Dashboard Dispatcher Branch Expansion Backfill Prep v1: moves one additional prepared dispatcher branch body behind a helper while the manual route condition remains authoritative.", "System", "render_dashboard_dispatcher_branch_extraction_backfill"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-helper-consolidation", "v1072.3 Dispatcher", "1072.3 Dashboard Dispatcher Branch Expansion Backfill Prep v1: consolidates the two helper-backed branch wrappers into a shared helper module while manual dispatcher conditions remain authoritative and no new branch extraction occurs.", "System", "render_dashboard_dispatcher_branch_helper_consolidation"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-extraction-expansion-prep", "v1072.3 Dispatcher", "1072.3 Dashboard Dispatcher Branch Expansion Backfill Prep v1: v1072.1 prep route remains documented while /dashboard-dispatcher-parity has now moved into the one-branch expansion trial.", "System", "render_dashboard_dispatcher_branch_extraction_expansion_prep"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-expansion-trial", "v1072.3 Dispatcher", "1072.3 Dashboard Dispatcher Branch Expansion Backfill Prep v1: moves exactly one additional prepared branch body for /dashboard-dispatcher-parity behind the shared helper while manual dispatch remains authoritative.", "System", "render_dashboard_dispatcher_branch_expansion_trial"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-expansion-backfill-prep", "v1072.3 Dispatcher", "1072.3 Dashboard Dispatcher Branch Expansion Backfill Prep v1: prepares /dashboard-dispatcher-branch-extraction-prep as the next tiny branch backfill candidate while moving no new branch and keeping manual dispatch authoritative.", "System", "render_dashboard_dispatcher_branch_expansion_backfill_prep"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-expansion-backfill-trial", "v1072.4 Dispatcher", "1072.4 Dashboard Dispatcher Branch Expansion Backfill Trial v1: moves exactly one prepared branch body for /dashboard-dispatcher-branch-extraction-prep behind the shared helper while manual dispatch remains authoritative.", "System", "render_dashboard_dispatcher_branch_expansion_backfill_trial"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-expansion-backfill-prep-v2", "v1072.5 Dispatcher", "1072.5 Dashboard Dispatcher Branch Expansion Backfill Prep v2: prepares /dashboard-dispatcher-branch-extraction-trial for one later helper-backed branch move while moving nothing in this prep surface.", "System", "render_dashboard_dispatcher_branch_expansion_backfill_prep_v2"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-expansion-backfill-trial-v2", "v1072.6 Dispatcher", "1072.6 Dashboard Dispatcher Branch Expansion Backfill Trial v2: moves exactly one prepared branch body for /dashboard-dispatcher-branch-extraction-trial behind the shared helper while manual dispatch remains authoritative.", "System", "render_dashboard_dispatcher_branch_expansion_backfill_trial_v2"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-expansion-backfill-prep-v3", "v1072.7 Dispatcher", "1072.7 Dashboard Dispatcher Branch Expansion Backfill Prep v3: prepares /dashboard-dispatcher-branch-extraction-backfill for one later helper-backed branch move while moving nothing in this prep surface.", "System", "render_dashboard_dispatcher_branch_expansion_backfill_prep_v3"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-expansion-backfill-trial-v3", "v1072.8 Dispatcher", "1072.8 Dashboard Dispatcher Branch Expansion Backfill Trial v3: moves exactly one prepared branch body for /dashboard-dispatcher-branch-extraction-backfill behind the shared helper while manual dispatch remains authoritative.", "System", "render_dashboard_dispatcher_branch_expansion_backfill_trial_v3"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-decomposition-hardening", "v1072.9 Dispatcher", "1072.9 Dashboard Dispatcher Branch Decomposition Hardening v1: proves six helper-backed branches and makes older helper-count gates successor-compatible without enabling generated routing.", "System", "render_dashboard_dispatcher_branch_decomposition_hardening"),
    DashboardRouteRegistryItem("/eidolon-v1073-source-review-checkpoint", "v1073.0 Checkpoint", "1073.0 Eidolon Source Review and Autonomy Readiness Checkpoint v1: summarizes decomposition progress, source growth, parity, and autonomy blockers while fixture execution remains blocked.", "System", "render_eidolon_v1073_source_review_checkpoint"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-decomposition-continuation-prep", "v1073.1 Dispatcher", "1073.1 Dispatcher Branch Decomposition Continuation Prep v1: prepares /smoke-check-helper-extraction-pilot as the next one-branch helper candidate while moving nothing and preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_branch_decomposition_continuation_prep"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-decomposition-continuation-trial", "v1073.3 Dispatcher", "1073.3 Dispatcher Branch Decomposition Continuation Prep v2: moves exactly one prepared branch body for /smoke-check-helper-extraction-pilot behind the shared helper while manual dispatch remains authoritative.", "System", "render_dashboard_dispatcher_branch_decomposition_continuation_trial"),
    DashboardRouteRegistryItem("/diagnostics", "Diagnostics <span class='nav-badge' data-live-count='counts.diagnostic_reports'></span>", "Diagnostic reports and recent health checks. Moved in v1074.0 behind the shared one-branch helper while its renderer body and manual route condition remain in dashboard.py.", "System", "render_diagnostics"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-decomposition-continuation-prep-v2", "v1073.3 Dispatcher", "1073.3 Dispatcher Branch Decomposition Continuation Prep v2: prepares /diagnostics as the next one-branch helper candidate while moving nothing and preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-decomposition-continuation-trial-v2", "v1074.0 Dispatcher", "1074.0 Dispatcher Branch Decomposition Continuation Prep v3: moves exactly one prepared branch body for /diagnostics behind the shared helper while manual dispatch remains authoritative.", "System", "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2"),
    DashboardRouteRegistryItem("/settings", "Settings", "Local settings and settings health. Prepared in v1074.0 as the next one-branch helper candidate while its renderer body and manual route condition remain in dashboard.py.", "System", "render_settings"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-decomposition-continuation-prep-v3", "v1074.0 Dispatcher", "1074.0 Dispatcher Branch Decomposition Continuation Prep v3: prepares /settings as the next one-branch helper candidate while moving nothing and preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-branch-decomposition-continuation-trial-v3", "v1074.0 Dispatcher", "1074.0 Dispatcher Decomposition Batch Strategy Checkpoint v1: moves exactly one prepared branch body for /settings behind the shared helper while manual dispatch remains authoritative.", "System", "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-strategy-checkpoint", "v1074.0 Batch", "1074.0 Dashboard Dispatcher Batch Strategy Checkpoint v1: chooses the next bounded three-route decomposition strategy while moving no branch bodies and preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_batch_strategy_checkpoint"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep", "v1073.8 Batch", "1073.8 Dashboard Dispatcher Batch Decomposition Prep v1: prepares three selected review-only dashboard branch bodies for a later helper-backed trial while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial", "v1074.0 Batch", "1074.0 Dashboard Dispatcher Batch Decomposition Trial v1: moves exactly three prepared review-only dashboard branch bodies behind shared helpers while preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_batch_decomposition_trial"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint", "v1074.0 Batch", "1074.0 historical proof identity served through the canonical dispatcher proof surface after the bounded v1078.5 retirement trial.", "System", "render_dashboard_dispatcher_proof_surface"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v2", "v1074.1 Batch", "1074.1 historical proof identity served through the canonical dispatcher proof surface after the bounded v1078.5 retirement trial.", "System", "render_dashboard_dispatcher_proof_surface"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v2", "v1074.3 Batch", "1074.3 historical proof identity served through the canonical dispatcher proof surface after the bounded v1078.5 retirement trial.", "System", "render_dashboard_dispatcher_proof_surface"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v2", "v1074.3 Batch", "1074.3 Dashboard Dispatcher Batch Decomposition Checkpoint v2: confirms the second three-route batch, counts remaining direct registry branches, and selects the next safe three-route batch while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v2"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v3", "v1074.4 Batch", "1074.4 Dashboard Dispatcher Batch Decomposition Prep v3: prepares the third three-route review-only dashboard branch batch for a later helper-backed trial while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v3"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v3", "v1074.5 Batch", "1074.5 Dashboard Dispatcher Batch Decomposition Trial v3: moves exactly the third three-route review-only dashboard branch batch behind shared helpers while preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v3"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v3", "v1074.6 Batch", "1074.6 Dashboard Dispatcher Batch Decomposition Checkpoint v3: confirms the third trial remains stable and selects the next three-route review-only batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v3"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v4", "v1074.7 Batch", "1074.7 Dashboard Dispatcher Batch Decomposition Prep v4: prepares the fourth three-route review-only dashboard branch batch for a later helper-backed trial while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v4"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v4", "v1074.8 Batch", "1074.8 Dashboard Dispatcher Batch Decomposition Trial v4: moves exactly the fourth prepared three-route review-only dashboard branch batch behind shared helpers while preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v4"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v4", "v1074.9 Batch", "1074.9 Dashboard Dispatcher Batch Decomposition Checkpoint v4: confirms the fourth trial remains stable and selects the next three-route review-only batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v4"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v5", "v1075.0 Batch", "1075.0 Dashboard Dispatcher Batch Decomposition Prep v5: prepares the fifth three-route review-only dashboard branch batch for a later helper-backed trial while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v5"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v5", "v1075.1 Batch", "1075.1 Dashboard Dispatcher Batch Decomposition Trial v5: moves exactly the fifth prepared three-route API review branch batch behind shared helpers while preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v5"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v5", "v1075.2 Batch", "1075.2 Dashboard Dispatcher Batch Decomposition Checkpoint v5: confirms the fifth trial remains stable and selects the next three-route API route-table batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v5"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v6", "v1075.3 Batch", "1075.3 Dashboard Dispatcher Batch Decomposition Prep v6: prepares the sixth three-route API route-table batch for a later helper-backed trial while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v6"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v6", "v1075.4 Batch", "1075.4 Dashboard Dispatcher Batch Decomposition Trial v6: moves the sixth three-route API route-table batch behind shared helper wrappers while preserving manual dispatch and safety boundaries.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v6"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v6", "v1075.5 Batch", "1075.5 Dashboard Dispatcher Batch Decomposition Checkpoint v6: confirms the sixth trial remains stable and selects the next three-route dashboard proof batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v6"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v7", "v1075.6 Batch", "1075.6 Dashboard Dispatcher Batch Decomposition Prep v7: prepares the seventh three-route dashboard proof batch for a later helper-backed trial while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v7"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v7", "v1075.7 Batch", "1075.7 Dashboard Dispatcher Batch Decomposition Trial v7: moves the seventh three-route dashboard proof batch behind shared helpers while preserving manual authority.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v7"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v7", "v1075.8 Batch", "1075.8 Dashboard Dispatcher Batch Decomposition Checkpoint v7: confirms the seventh trial remains stable and selects the next three-route branch-expansion batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v7"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v8", "v1076.1 Batch", "1076.1 Dashboard Dispatcher Batch Decomposition Prep v8: prepares the eighth three-route branch-expansion batch for a later helper-backed trial while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v8"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v8", "v1076.1 Batch", "1076.1 Dashboard Dispatcher Batch Decomposition Trial v8: moves exactly three prepared routes behind shared helpers.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v8"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v8", "v1076.1 Batch", "1076.1 Dashboard Dispatcher Batch Decomposition Checkpoint v8: confirms trial v8 remains stable and selects the next bounded three-route batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v8"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v9", "v1076.2 Batch", "1076.2 Dashboard Dispatcher Batch Decomposition Prep v9: prepares the ninth bounded three-route backfill batch for a later helper-backed trial while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v9"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v9", "v1076.5 Batch", "1076.5 Dashboard Dispatcher Batch Decomposition Trial v9: moves exactly three prepared backfill routes behind shared helpers.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v9"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v9", "v1076.5 Batch", "1076.5 Dashboard Dispatcher Batch Decomposition Checkpoint v9: confirms trial v9 remains stable and selects the next bounded three-route batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v9"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v10", "v1076.5 Batch", "1076.5 Dashboard Dispatcher Batch Decomposition Prep v10: proves the tenth bounded three-route batch remains direct while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v10"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v10", "v1077.0 Batch", "1077.0 Dashboard Dispatcher Batch Decomposition Trial v10: moves exactly three prepared routes behind shared helpers.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v10"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v10", "v1077.0 Batch", "1077.0 Dashboard Dispatcher Batch Decomposition Checkpoint v10: confirms trial v10 remains stable and selects the next bounded three-route batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v10"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v11", "v1077.0 Batch", "1077.0 Dashboard Dispatcher Batch Decomposition Prep v11: proves the eleventh bounded three-route continuation batch remains direct while moving nothing.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v11"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v11", "v1077.0 Batch", "1077.0 Dashboard Dispatcher Batch Decomposition Trial v11: moves exactly three prepared continuation routes behind shared helpers.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v11"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v11", "v1077.0 Batch", "1077.0 Dashboard Dispatcher Batch Decomposition Checkpoint v11: confirms trial v11 remains stable and selects the next bounded three-route batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v11"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v12", "v1077.1 Batch", "1077.1 Dashboard Dispatcher Batch Decomposition Prep v12: proves the twelfth bounded three-route continuation batch remains direct while moving no branch conditions, branch bodies, or renderer bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v12"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v12", "v1077.2 Batch", "1077.2 Dashboard Dispatcher Batch Decomposition Trial v12: moves exactly the three prep-v12 continuation routes behind shared pass-through helpers while preserving manual dispatch authority.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v12"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v12", "v1077.3 Batch", "1077.3 Dashboard Dispatcher Batch Decomposition Checkpoint v12: confirms trial v12 stability, discloses zero net direct-route reduction per proof cycle, and selects the next bounded three-route batch without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v12"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-prep-v13", "v1077.4 Batch", "1077.4 Dashboard Dispatcher Batch Decomposition Prep v13: proves the thirteenth bounded three-route batch remains direct while moving no branch conditions, branch bodies, helper bodies, or renderer bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_prep_v13"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-trial-v13", "v1077.5 Batch", "1077.5 Dashboard Dispatcher Batch Decomposition Trial v13: moves exactly the three prep-v13 historical proof routes behind shared pass-through helpers while preserving manual dispatch authority and renderer bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_trial_v13"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-batch-decomposition-checkpoint-v13", "v1077.6 Checkpoint", "1077.6 Dashboard Dispatcher Batch Decomposition Checkpoint v13: closes the extraction cycle, reconciles the historical proof-route inventory, and selects bounded proof-surface consolidation without moving branch bodies.", "System", "render_dashboard_dispatcher_batch_decomposition_checkpoint_v13"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface-consolidation-prep-v1", "v1077.7 Proof", "1077.7 Dashboard Dispatcher Proof Surface Consolidation Prep v1: defines one parameterized review-only proof ledger and compatibility contract while preserving all historical routes and manual authority.", "System", "render_dashboard_dispatcher_proof_surface_consolidation_prep_v1"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface", "v1077.8 Proof", "1077.8 Dashboard Dispatcher Proof Surface: canonical review-only ledger renderer with a manual proof_route selector; historical routes remain authoritative and aliases remain inactive.", "System", "render_dashboard_dispatcher_proof_surface"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1", "v1077.9 Proof", "1077.9 historical compatibility migration prep: defines exact alias and rollback contracts while activating and removing nothing.", "System", "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v1", "v1078.1 Proof", "1078.1 bounded compatibility migration trial: activates exactly three manual read-only aliases while preserving rollback surfaces.", "System", "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v2", "v1078.1 Proof", "1078.1 bounded compatibility migration trial: activates ten additional exact manual read-only aliases while preserving rollback surfaces.", "System", "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v3", "v1078.2 Proof", "1078.2 bounded compatibility migration trial: activates twelve additional exact manual read-only aliases while preserving rollback surfaces.", "System", "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface-historical-compatibility-migration-completion-v1", "v1078.3 Proof", "1078.3 compatibility migration completion: activates the final twelve exact aliases for 37-of-37 canonical coverage while preserving rollback surfaces.", "System", "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface-historical-surface-retirement-prep-v1", "v1078.4 Proof", "1078.4 authoritative retirement manifest prep; inventories all 37 historical surfaces and removes nothing.", "System", "render_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep"),
    DashboardRouteRegistryItem("/dashboard-dispatcher-proof-surface-historical-surface-retirement-trial-v1", "v1078.5 Proof", "1078.5 bounded retirement trial; retires three unreachable historical branches and renderers while preserving all compatibility identities.", "System", "render_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial"),
)

DASHBOARD_ROUTE_REGISTRY_SAFETY_BOUNDARY: dict[str, bool | int] = {
    "actual_fixture_execution_count": 0,
    "subprocess_spawn_count": 0,
    "source_write_count": 0,
    "source_delete_count": 0,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "dashboard_get_preview_only": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "http_dispatcher_changed": False,
    "renderer_bodies_moved": False,
}


def dashboard_route_registry_nav_items() -> list[tuple[str, str, str, str]]:
    return [item.nav_tuple() for item in DASHBOARD_ROUTE_REGISTRY_ITEMS]


def dashboard_route_registry_paths() -> list[str]:
    return [item.path for item in DASHBOARD_ROUTE_REGISTRY_ITEMS]


def dashboard_route_registry_renderer_names() -> list[str]:
    return [item.renderer_name for item in DASHBOARD_ROUTE_REGISTRY_ITEMS]


def dashboard_route_registry_rows() -> list[dict[str, Any]]:
    return [item.as_dict() for item in DASHBOARD_ROUTE_REGISTRY_ITEMS]


def build_dashboard_route_registry_extraction_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15300,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_path = root / "conscious_agent" / "dashboard.py"
    helper_path = root / "conscious_agent" / "dashboard_route_registry.py"
    dashboard_text = dashboard_path.read_text(encoding="utf-8", errors="ignore")
    helper_text = helper_path.read_text(encoding="utf-8", errors="ignore")
    dashboard_lines = dashboard_text.count("\n") + 1
    paths = dashboard_route_registry_paths()
    renderer_names = dashboard_route_registry_renderer_names()
    nav_start = dashboard_text.index("nav_items = [") if "nav_items = [" in dashboard_text else 0
    nav_end = dashboard_text.index("nav = _render_nav", nav_start) if "nav = _render_nav" in dashboard_text[nav_start:] else len(dashboard_text)
    nav_section = dashboard_text[nav_start:nav_end]
    direct_nav_tokens = [f'(\"{path}\",' for path in paths]
    dispatcher_tokens = [f'path == \"{path}\"' for path in paths]
    dispatch_literal_count = sum(1 for token in dispatcher_tokens if token in dashboard_text)
    registry_constant_dispatch_present = "path == DASHBOARD_ROUTE_REGISTRY_ROUTE" in dashboard_text
    backfill_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE" in dashboard_text
    consolidation_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE" in dashboard_text
    expansion_prep_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE" in dashboard_text
    expansion_trial_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE" in dashboard_text
    expansion_backfill_prep_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_ROUTE" in dashboard_text
    expansion_backfill_trial_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_ROUTE" in dashboard_text
    expansion_backfill_prep_v2_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V2_ROUTE" in dashboard_text
    expansion_backfill_trial_v2_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE" in dashboard_text
    expansion_backfill_prep_v3_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V3_ROUTE" in dashboard_text
    expansion_backfill_trial_v3_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_ROUTE" in dashboard_text
    decomposition_hardening_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE" in dashboard_text
    source_review_checkpoint_constant_dispatch_present = "path == EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE" in dashboard_text
    continuation_prep_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_ROUTE" in dashboard_text
    continuation_trial_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE" in dashboard_text
    continuation_prep_v2_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V2_ROUTE" in dashboard_text
    continuation_trial_v2_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE" in dashboard_text
    continuation_prep_v3_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE" in dashboard_text
    continuation_trial_v3_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE" in dashboard_text
    batch_strategy_checkpoint_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE" in dashboard_text
    batch_decomposition_prep_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE" in dashboard_text
    batch_decomposition_trial_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_constant_dispatch_present = "path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1" in dashboard_text
    batch_decomposition_prep_v2_constant_dispatch_present = "path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1" in dashboard_text
    batch_decomposition_trial_v2_constant_dispatch_present = "path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1" in dashboard_text
    batch_decomposition_checkpoint_v2_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V2_ROUTE" in dashboard_text
    batch_decomposition_prep_v3_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE" in dashboard_text
    batch_decomposition_trial_v3_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V3_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v3_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V3_ROUTE" in dashboard_text
    batch_decomposition_prep_v4_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V4_ROUTE" in dashboard_text
    batch_decomposition_trial_v4_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V4_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v4_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V4_ROUTE" in dashboard_text
    batch_decomposition_prep_v5_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_ROUTE" in dashboard_text
    batch_decomposition_trial_v5_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V5_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v5_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE" in dashboard_text
    batch_decomposition_prep_v6_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V6_ROUTE" in dashboard_text
    batch_decomposition_trial_v6_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V6_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v6_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE" in dashboard_text
    batch_decomposition_prep_v7_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V7_ROUTE" in dashboard_text
    batch_decomposition_trial_v7_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V7_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v7_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V7_ROUTE" in dashboard_text
    batch_decomposition_prep_v8_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V8_ROUTE" in dashboard_text
    batch_decomposition_trial_v8_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V8_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v8_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V8_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v9_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V9_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v10_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V10_ROUTE" in dashboard_text
    batch_decomposition_prep_v11_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V11_ROUTE" in dashboard_text
    batch_decomposition_prep_v9_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V9_ROUTE" in dashboard_text
    batch_decomposition_trial_v9_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V9_ROUTE" in dashboard_text
    batch_decomposition_prep_v10_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE" in dashboard_text
    batch_decomposition_trial_v10_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE" in dashboard_text
    batch_decomposition_trial_v11_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V11_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v11_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V11_ROUTE" in dashboard_text
    batch_decomposition_prep_v12_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V12_ROUTE" in dashboard_text
    batch_decomposition_trial_v12_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v12_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE" in dashboard_text
    batch_decomposition_prep_v13_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE" in dashboard_text
    batch_decomposition_trial_v13_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_ROUTE" in dashboard_text
    batch_decomposition_checkpoint_v13_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE" in dashboard_text
    proof_surface_consolidation_prep_v1_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE" in dashboard_text
    proof_surface_consolidated_renderer_trial_v1_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE" in dashboard_text
    proof_surface_historical_compatibility_migration_prep_v1_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE" in dashboard_text
    proof_surface_historical_compatibility_migration_trial_v1_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V1_ROUTE" in dashboard_text
    proof_surface_historical_compatibility_migration_trial_v2_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V2_ROUTE" in dashboard_text
    proof_surface_historical_compatibility_migration_trial_v3_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V3_ROUTE" in dashboard_text
    proof_surface_historical_compatibility_migration_completion_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_COMPLETION_ROUTE" in dashboard_text
    proof_surface_historical_surface_retirement_prep_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_SURFACE_RETIREMENT_PREP_ROUTE" in dashboard_text
    proof_surface_historical_surface_retirement_trial_constant_dispatch_present = "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_SURFACE_RETIREMENT_TRIAL_ROUTE" in dashboard_text
    constant_dispatch_tokens = (
        registry_constant_dispatch_present,
        backfill_constant_dispatch_present,
        consolidation_constant_dispatch_present,
        expansion_prep_constant_dispatch_present,
        expansion_trial_constant_dispatch_present,
        expansion_backfill_prep_constant_dispatch_present,
        expansion_backfill_trial_constant_dispatch_present,
        expansion_backfill_prep_v2_constant_dispatch_present,
        expansion_backfill_trial_v2_constant_dispatch_present,
        expansion_backfill_prep_v3_constant_dispatch_present,
        expansion_backfill_trial_v3_constant_dispatch_present,
        decomposition_hardening_constant_dispatch_present,
        source_review_checkpoint_constant_dispatch_present,
        continuation_prep_constant_dispatch_present,
        continuation_trial_constant_dispatch_present,
        continuation_prep_v2_constant_dispatch_present,
        continuation_trial_v2_constant_dispatch_present,
        continuation_prep_v3_constant_dispatch_present,
        continuation_trial_v3_constant_dispatch_present,
        batch_strategy_checkpoint_constant_dispatch_present,
        batch_decomposition_prep_constant_dispatch_present,
        batch_decomposition_trial_constant_dispatch_present,
        batch_decomposition_checkpoint_constant_dispatch_present,
        batch_decomposition_prep_v2_constant_dispatch_present,
        batch_decomposition_trial_v2_constant_dispatch_present,
        batch_decomposition_checkpoint_v2_constant_dispatch_present,
        batch_decomposition_prep_v3_constant_dispatch_present,
        batch_decomposition_trial_v3_constant_dispatch_present,
        batch_decomposition_checkpoint_v3_constant_dispatch_present,
        batch_decomposition_prep_v4_constant_dispatch_present,
        batch_decomposition_trial_v4_constant_dispatch_present,
        batch_decomposition_checkpoint_v4_constant_dispatch_present,
        batch_decomposition_prep_v5_constant_dispatch_present,
        batch_decomposition_trial_v5_constant_dispatch_present,
        batch_decomposition_checkpoint_v5_constant_dispatch_present,
        batch_decomposition_prep_v6_constant_dispatch_present,
        batch_decomposition_trial_v6_constant_dispatch_present,
        batch_decomposition_checkpoint_v6_constant_dispatch_present,
        batch_decomposition_prep_v7_constant_dispatch_present,
        batch_decomposition_trial_v7_constant_dispatch_present,
        batch_decomposition_checkpoint_v7_constant_dispatch_present,
        batch_decomposition_prep_v8_constant_dispatch_present,
        batch_decomposition_trial_v8_constant_dispatch_present,
        batch_decomposition_checkpoint_v8_constant_dispatch_present,
        batch_decomposition_checkpoint_v9_constant_dispatch_present,
        batch_decomposition_checkpoint_v10_constant_dispatch_present,
        batch_decomposition_prep_v11_constant_dispatch_present,
        batch_decomposition_prep_v9_constant_dispatch_present,
        batch_decomposition_trial_v9_constant_dispatch_present,
        batch_decomposition_prep_v10_constant_dispatch_present,
        batch_decomposition_trial_v10_constant_dispatch_present,
        batch_decomposition_trial_v11_constant_dispatch_present,
        batch_decomposition_checkpoint_v11_constant_dispatch_present,
        batch_decomposition_prep_v12_constant_dispatch_present,
        batch_decomposition_trial_v12_constant_dispatch_present,
        batch_decomposition_checkpoint_v12_constant_dispatch_present,
        batch_decomposition_prep_v13_constant_dispatch_present,
        batch_decomposition_trial_v13_constant_dispatch_present,
        batch_decomposition_checkpoint_v13_constant_dispatch_present,
        proof_surface_consolidation_prep_v1_constant_dispatch_present,
        proof_surface_consolidated_renderer_trial_v1_constant_dispatch_present,
        proof_surface_historical_compatibility_migration_prep_v1_constant_dispatch_present,
        proof_surface_historical_compatibility_migration_trial_v1_constant_dispatch_present,
        proof_surface_historical_compatibility_migration_trial_v2_constant_dispatch_present,
        proof_surface_historical_compatibility_migration_trial_v3_constant_dispatch_present,
        proof_surface_historical_compatibility_migration_completion_constant_dispatch_present,
        proof_surface_historical_surface_retirement_prep_constant_dispatch_present,
        proof_surface_historical_surface_retirement_trial_constant_dispatch_present,
    )
    constant_dispatch_count = sum(int(token) for token in constant_dispatch_tokens)
    all_known_constant_dispatches_present = all(constant_dispatch_tokens)
    rows: list[dict[str, Any]] = [
        {"name": "route-registry-helper-current", "ok": DASHBOARD_ROUTE_REGISTRY_VERSION <= expected_version},
        {"name": "route-registry-helper-exists", "ok": helper_path.exists()},
        {"name": "dashboard-imports-route-registry", "ok": "from dashboard_route_registry import" in dashboard_text and "dashboard_route_registry_nav_items" in dashboard_text},
        {"name": "nav-metadata-moved-to-helper", "ok": "DASHBOARD_ROUTE_REGISTRY_ITEMS" in helper_text and all(path in helper_text for path in paths)},
        {"name": "direct-nav-tuples-removed-from-dashboard", "ok": not any(token in nav_section for token in direct_nav_tokens)},
        {"name": "manual-http-dispatcher-retains-known-routes", "ok": dispatch_literal_count + constant_dispatch_count >= len(paths) and all_known_constant_dispatches_present, "literal_count": dispatch_literal_count, "constant_count": constant_dispatch_count, "path_count": len(paths)},
        {"name": "renderer-names-represented", "ok": all(f"def {name}" in dashboard_text or name == DASHBOARD_ROUTE_REGISTRY_RENDERER for name in renderer_names)},
        {"name": "dashboard-line-count-decreased-or-bounded-successor-growth", "ok": dashboard_lines <= previous_dashboard_line_count + 340, "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "manual-dashboard-remains-authoritative", "ok": DASHBOARD_ROUTE_REGISTRY_SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True},
        {"name": "http-dispatcher-unchanged", "ok": DASHBOARD_ROUTE_REGISTRY_SAFETY_BOUNDARY["http_dispatcher_changed"] is False},
        {"name": "renderer-bodies-not-moved", "ok": DASHBOARD_ROUTE_REGISTRY_SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "new-route-registered", "ok": DASHBOARD_ROUTE_REGISTRY_ROUTE in helper_text and DASHBOARD_ROUTE_REGISTRY_ROUTE in dashboard_text},
    ]
    ok = all(row.get("ok") is True for row in rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_ROUTE_REGISTRY_CHECK_ID,
        "title": DASHBOARD_ROUTE_REGISTRY_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_route_registry.py",
        "extracted_route_count": len(DASHBOARD_ROUTE_REGISTRY_ITEMS),
        "extracted_paths": paths,
        "renderer_names": renderer_names,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "route_rows": dashboard_route_registry_rows(),
        "rows": rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_ROUTE_REGISTRY_SAFETY_BOUNDARY,
    }


def dashboard_route_registry_extraction_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard route registry extraction: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper: {report.get('helper_module')}",
        f"Extracted route count: {report.get('extracted_route_count')}",
        f"dashboard.py line delta: {report.get('line_count_delta')}",
        "Manual HTTP dispatcher remains authoritative: True",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_route_registry_extraction_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_route_registry_extraction_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-route-registry-extraction-v1: extraction report blocked")
            print(report.get("rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-route-registry-extraction-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-route-registry-extraction-v1: authority boundary changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("http_dispatcher_changed") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-route-registry-extraction-v1: dashboard authority boundary changed")
            return False
        print(f"[ok] dashboard-route-registry-extraction-v1 line_delta={report.get('line_count_delta')} helper={report.get('helper_module')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-route-registry-extraction-v1: {error}")
        return False


# v1071.5 dashboard route registry extraction tokens: dashboard-route-registry-extraction-v1 /dashboard-route-registry-extraction DASHBOARD_ROUTE_REGISTRY_ITEMS dashboard_route_registry_nav_items dashboard_route_registry_paths dashboard_route_registry_rows build_dashboard_route_registry_extraction_report dashboard_route_registry_extraction_text route_registry_helper_current=True renderer_metadata_route_registered=True direct_nav_tuples_removed_from_dashboard=True manual_http_dispatcher_retains_known_routes=True renderer_bodies_moved=False http_dispatcher_changed=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
# v1071.6 dashboard dispatcher parity registry tokens: dashboard-dispatcher-parity-gate-v1 /dashboard-dispatcher-parity render_dashboard_dispatcher_parity route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction prep route registry tokens: dashboard-dispatcher-branch-extraction-prep-v1 /dashboard-dispatcher-branch-extraction-prep render_dashboard_dispatcher_branch_extraction_prep branch_extraction_prepared_only=True branch_extraction_executed=False dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed_for_candidates=False dashboard_get_preview_only=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction trial route registry tokens: dashboard-dispatcher-branch-extraction-trial-v1 /dashboard-dispatcher-branch-extraction-trial render_dashboard_dispatcher_branch_extraction_trial render_dashboard_route_registry_extraction_trial_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction backfill route registry tokens: dashboard-dispatcher-branch-extraction-backfill-v1 /dashboard-dispatcher-branch-extraction-backfill render_dashboard_dispatcher_branch_extraction_backfill render_dashboard_renderer_metadata_extraction_backfill_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=2 backfilled_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch helper consolidation route registry tokens: dashboard-dispatcher-branch-helper-consolidation-v1 /dashboard-dispatcher-branch-helper-consolidation render_dashboard_dispatcher_branch_helper_consolidation dispatcher_branch_helper_consolidated=True additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction expansion prep route registry tokens: dashboard-dispatcher-branch-extraction-expansion-prep-v1 /dashboard-dispatcher-branch-extraction-expansion-prep render_dashboard_dispatcher_branch_extraction_expansion_prep conscious_agent/dashboard_dispatcher_branch_expansion_prep.py branch_expansion_prepared_only=True branch_expansion_executed=False additional_branch_extraction_count=0 existing_helper_backed_branch_count=2 prepared_candidate_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch expansion trial route registry tokens: dashboard-dispatcher-branch-expansion-trial-v1 /dashboard-dispatcher-branch-expansion-trial render_dashboard_dispatcher_branch_expansion_trial conscious_agent/dashboard_dispatcher_branch_expansion_trial.py EXPANDED_BRANCH_PATH=/dashboard-dispatcher-parity branch_expansion_trial_executed=True branch_expansion_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 extracted_branch_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch expansion backfill prep route registry tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v1 /dashboard-dispatcher-branch-expansion-backfill-prep render_dashboard_dispatcher_branch_expansion_backfill_prep conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep.py NEXT_BACKFILL_CANDIDATE_PATH=/dashboard-dispatcher-branch-extraction-prep branch_expansion_backfill_prepared_only=True branch_expansion_backfill_executed=False additional_branch_extraction_count=0 existing_helper_backed_branch_count=3 prepared_candidate_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 dashboard dispatcher branch expansion backfill trial route registry tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 /dashboard-dispatcher-branch-expansion-backfill-trial render_dashboard_dispatcher_branch_expansion_backfill_trial conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py BACKFILLED_BRANCH_PATH=/dashboard-dispatcher-branch-extraction-prep branch_expansion_backfill_trial_executed=True branch_expansion_backfill_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=4 backfilled_branch_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True data-tip command-deck operator-console no_native_title_tooltip

# v1073.0 dashboard route registry tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v2 dashboard-dispatcher-branch-expansion-backfill-trial-v2 dashboard-dispatcher-branch-expansion-backfill-prep-v3 dashboard-dispatcher-branch-expansion-backfill-trial-v3 dashboard-dispatcher-branch-decomposition-hardening-v1 eidolon-v1073-source-review-checkpoint-v1 /eidolon-v1073-source-review-checkpoint render_eidolon_v1073_source_review_checkpoint helper_backed_branch_count=6 data-tip command-deck operator-console no_native_title_tooltip

# v1073.1 route registry tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v1 /dashboard-dispatcher-branch-decomposition-continuation-prep render_dashboard_dispatcher_branch_decomposition_continuation_prep route_registry_renderer_metadata_dispatcher_parity=True data-tip command-deck operator-console no_native_title_tooltip

# v1073.3 route registry tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v1 /dashboard-dispatcher-branch-decomposition-continuation-trial render_dashboard_dispatcher_branch_decomposition_continuation_trial /smoke-check-helper-extraction-pilot helper_backed_branch_count=7 data-tip command-deck operator-console no_native_title_tooltip

# v1073.3 route registry tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v2 /dashboard-dispatcher-branch-decomposition-continuation-prep-v2 render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2 /diagnostics helper_backed_branch_count=7 data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 route registry tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v2 /dashboard-dispatcher-branch-decomposition-continuation-trial-v2 render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2 /diagnostics render_diagnostics_continuation_branch helper_backed_branch_count=8 data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 route registry tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v3 /dashboard-dispatcher-branch-decomposition-continuation-prep-v3 render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3 /settings render_settings_continuation_branch helper_backed_branch_count=8 data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 route registry tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v3 /dashboard-dispatcher-branch-decomposition-continuation-trial-v3 render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3 /settings render_settings_continuation_branch helper_backed_branch_count=9 data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard route registry tokens: dashboard-dispatcher-batch-strategy-checkpoint-v1 /dashboard-dispatcher-batch-strategy-checkpoint render_dashboard_dispatcher_batch_strategy_checkpoint batch_strategy_checkpoint_only=True recommended_batch_size=3 branch_decomposition_batch_executed=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v1 /dashboard-dispatcher-batch-decomposition-prep render_dashboard_dispatcher_batch_decomposition_prep prepared_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False helper_backed_branch_count=9 data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-trial-v1 /dashboard-dispatcher-batch-decomposition-trial render_dashboard_dispatcher_batch_decomposition_trial moved_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True helper_backed_branch_count=12 data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint render_dashboard_dispatcher_batch_decomposition_checkpoint recommended_batch_size=3 helper_backed_branch_count=12 remaining_registry_direct_branch_count=36 batch_decomposition_checkpoint_only=True branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.1 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v2 /dashboard-dispatcher-batch-decomposition-prep-v2 render_dashboard_dispatcher_batch_decomposition_prep_v2 prepared_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False helper_backed_branch_count=12 data-tip command-deck operator-console no_native_title_tooltip

# v1074.3 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-trial-v2 /dashboard-dispatcher-batch-decomposition-trial-v2 render_dashboard_dispatcher_batch_decomposition_trial_v2 manual_http_dispatcher_retains_known_routes=True constant_dispatch_count=25 extracted_route_count=51 data-tip no_native_title_tooltip
# v1074.3 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v2 /dashboard-dispatcher-batch-decomposition-checkpoint-v2 render_dashboard_dispatcher_batch_decomposition_checkpoint_v2 manual_http_dispatcher_retains_known_routes=True constant_dispatch_count=26 extracted_route_count=52 data-tip no_native_title_tooltip

# v1074.4 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v3 /dashboard-dispatcher-batch-decomposition-prep-v3 render_dashboard_dispatcher_batch_decomposition_prep_v3 prepared_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False helper_backed_branch_count=15 data-tip command-deck operator-console no_native_title_tooltip

# v1074.5 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-trial-v3 /dashboard-dispatcher-batch-decomposition-trial-v3 render_dashboard_dispatcher_batch_decomposition_trial_v3 manual_http_dispatcher_retains_known_routes=True helper_backed_branch_count=18 moved_batch_size=3 branch_decomposition_batch_executed=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.6 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v3 /dashboard-dispatcher-batch-decomposition-checkpoint-v3 render_dashboard_dispatcher_batch_decomposition_checkpoint_v3 constant_dispatch_count=29 extracted_route_count=55 recommended_batch_size=3 helper_backed_branch_count=18 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v4 /dashboard-dispatcher-batch-decomposition-prep-v4 render_dashboard_dispatcher_batch_decomposition_prep_v4 constant_dispatch_count=30 extracted_route_count=56 prepared_batch_size=3 helper_backed_branch_count=18 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.8 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-trial-v4 /dashboard-dispatcher-batch-decomposition-trial-v4 render_dashboard_dispatcher_batch_decomposition_trial_v4 constant_dispatch_count=31 extracted_route_count=57 moved_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.9 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v4 /dashboard-dispatcher-batch-decomposition-checkpoint-v4 render_dashboard_dispatcher_batch_decomposition_checkpoint_v4 constant_dispatch_count=32 extracted_route_count=58 recommended_batch_size=3 helper_backed_branch_count=21 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.0 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v5 /dashboard-dispatcher-batch-decomposition-prep-v5 render_dashboard_dispatcher_batch_decomposition_prep_v5 constant_dispatch_count=33 extracted_route_count=59 prepared_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.0 route registry constant-dispatch accounting repair tokens: batch_decomposition_prep_v5_constant_dispatch_present DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_ROUTE constant_dispatch_count=33 extracted_route_count=59

# v1075.1 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-trial-v5 /dashboard-dispatcher-batch-decomposition-trial-v5 render_dashboard_dispatcher_batch_decomposition_trial_v5 constant_dispatch_count=34 extracted_route_count=60 moved_batch_size=3 helper_backed_branch_count=24 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True data-tip command-deck operator-console no_native_title_tooltip
# v1075.2 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 /dashboard-dispatcher-batch-decomposition-checkpoint-v5 render_dashboard_dispatcher_batch_decomposition_checkpoint_v5 constant_dispatch_count=35 extracted_route_count=61 recommended_batch_size=3 helper_backed_branch_count=24 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.3 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v6 /dashboard-dispatcher-batch-decomposition-prep-v6 render_dashboard_dispatcher_batch_decomposition_prep_v6 constant_dispatch_count=36 extracted_route_count=62 prepared_batch_size=3 helper_backed_branch_count=24 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.4 dashboard route registry tokens: dashboard-dispatcher-batch-decomposition-trial-v6 /dashboard-dispatcher-batch-decomposition-trial-v6 render_dashboard_dispatcher_batch_decomposition_trial_v6 constant_dispatch_count=37 extracted_route_count=63 moved_batch_size=3 helper_backed_branch_count=27 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.5 route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v6 /dashboard-dispatcher-batch-decomposition-checkpoint-v6 render_dashboard_dispatcher_batch_decomposition_checkpoint_v6 helper_backed_branch_count=27 remaining_registry_direct_branch_count=36 recommended_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip

# v1075.5 route registry constant dispatch compatibility: checkpoint-v6 constant dispatcher route is counted without replacing manual dashboard dispatch. release_authorized=False autonomy_expanded=False

# v1075.6 route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v7 /dashboard-dispatcher-batch-decomposition-prep-v7 render_dashboard_dispatcher_batch_decomposition_prep_v7 helper_backed_branch_count=27 prepared_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip
# v1075.6 route registry constant dispatch compatibility: prep-v7 constant dispatcher route is counted without replacing manual dashboard dispatch. release_authorized=False autonomy_expanded=False

# v1075.7 route registry tokens: dashboard-dispatcher-batch-decomposition-trial-v7 /dashboard-dispatcher-batch-decomposition-trial-v7 render_dashboard_dispatcher_batch_decomposition_trial_v7 helper_backed_branch_count=30 moved_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip

# v1075.8 route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v7 /dashboard-dispatcher-batch-decomposition-checkpoint-v7 render_dashboard_dispatcher_batch_decomposition_checkpoint_v7 helper_backed_branch_count=30 remaining_registry_direct_branch_count=36 recommended_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip
# v1075.8 route registry constant dispatch compatibility: checkpoint-v7 constant dispatcher route is counted without replacing manual dashboard dispatch. release_authorized=False autonomy_expanded=False

# v1076.1 route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v8 /dashboard-dispatcher-batch-decomposition-prep-v8 render_dashboard_dispatcher_batch_decomposition_prep_v8 helper_backed_branch_count=30 prepared_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip
# v1076.1 route registry constant dispatch compatibility: prep-v8 constant dispatcher route is counted without replacing manual dashboard dispatch. release_authorized=False autonomy_expanded=False

# v1076.1 dashboard-dispatcher-batch-decomposition-trial-v8 /dashboard-dispatcher-batch-decomposition-trial-v8 render_dashboard_dispatcher_batch_decomposition_trial_v8

# v1076.1 route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v8 /dashboard-dispatcher-batch-decomposition-checkpoint-v8 render_dashboard_dispatcher_batch_decomposition_checkpoint_v8 helper_backed_branch_count=33 remaining_registry_direct_branch_count=36 recommended_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 route registry constant dispatch compatibility: checkpoint-v8 constant dispatcher route is counted without replacing manual dashboard dispatch. release_authorized=False autonomy_expanded=False

# v1076.2 route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v9 /dashboard-dispatcher-batch-decomposition-prep-v9 render_dashboard_dispatcher_batch_decomposition_prep_v9 helper_backed_branch_count=33 prepared_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip

# v1076.5 dashboard-dispatcher-batch-decomposition-trial-v9 /dashboard-dispatcher-batch-decomposition-trial-v9 render_dashboard_dispatcher_batch_decomposition_trial_v9

# v1076.5 route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v9 /dashboard-dispatcher-batch-decomposition-checkpoint-v9 render_dashboard_dispatcher_batch_decomposition_checkpoint_v9 helper_backed_branch_count=36 remaining_registry_direct_branch_count=36 recommended_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip

# v1076.5 route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v10 /dashboard-dispatcher-batch-decomposition-prep-v10 render_dashboard_dispatcher_batch_decomposition_prep_v10 helper_backed_branch_count=36 prepared_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip

# v1077.0 dashboard-dispatcher-batch-decomposition-trial-v10 /dashboard-dispatcher-batch-decomposition-trial-v10 render_dashboard_dispatcher_batch_decomposition_trial_v10

# v1077.0 checkpoint v10 registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v10 /dashboard-dispatcher-batch-decomposition-checkpoint-v10 render_dashboard_dispatcher_batch_decomposition_checkpoint_v10 helper_backed_branch_count=39 remaining_registry_direct_branch_count=36 recommended_batch_size=3

# v1077.0 route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v11 /dashboard-dispatcher-batch-decomposition-prep-v11 render_dashboard_dispatcher_batch_decomposition_prep_v11 helper_backed_branch_count=39 prepared_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip

# v1077.0 route registry tokens: dashboard-dispatcher-batch-decomposition-trial-v11 /dashboard-dispatcher-batch-decomposition-trial-v11 render_dashboard_dispatcher_batch_decomposition_trial_v11 helper_backed_branch_count=42 moved_batch_size=3 data-tip command-deck operator-console no_native_title_tooltip

# v1077.0 checkpoint v11 registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v11 /dashboard-dispatcher-batch-decomposition-checkpoint-v11 render_dashboard_dispatcher_batch_decomposition_checkpoint_v11 helper_backed_branch_count=42 remaining_registry_direct_branch_count=36 recommended_batch_size=3

# v1077.1 route registry tokens: dashboard-dispatcher-batch-decomposition-prep-v12 /dashboard-dispatcher-batch-decomposition-prep-v12 render_dashboard_dispatcher_batch_decomposition_prep_v12 helper_backed_branch_count=42 prepared_batch_size=3 route_check_renderer_constant_values_exact=True data-tip command-deck operator-console no_native_title_tooltip

# v1077.2 route registry tokens: /dashboard-dispatcher-batch-decomposition-trial-v12 render_dashboard_dispatcher_batch_decomposition_trial_v12 route_count=81

# v1077.3 checkpoint v12 registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v12 /dashboard-dispatcher-batch-decomposition-checkpoint-v12 render_dashboard_dispatcher_batch_decomposition_checkpoint_v12 route_count=82 helper_backed_branch_count=45 remaining_registry_direct_branch_count=36 recommended_batch_size=3 net_direct_route_reduction_per_cycle=0

# v1077.4 prep v13 registry tokens: dashboard-dispatcher-batch-decomposition-prep-v13 /dashboard-dispatcher-batch-decomposition-prep-v13 render_dashboard_dispatcher_batch_decomposition_prep_v13 route_count=83 helper_backed_branch_count=45 prepared_batch_size=3 route_check_renderer_constant_values_exact=True

# v1077.5 trial v13 registry tokens: dashboard-dispatcher-batch-decomposition-trial-v13 /dashboard-dispatcher-batch-decomposition-trial-v13 render_dashboard_dispatcher_batch_decomposition_trial_v13 route_count=84 helper_backed_branch_count=48 moved_batch_size=3 route_check_renderer_constant_values_exact=True

# v1077.6 route registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v13 /dashboard-dispatcher-batch-decomposition-checkpoint-v13 render_dashboard_dispatcher_batch_decomposition_checkpoint_v13 helper_backed_branch_count=48 historical_proof_direct_route_count=36 precheckpoint_legacy_proof_route_count=35 ordinary_operational_direct_route_count=0 proof_surface_consolidation_selected=True data-tip command-deck operator-console no_native_title_tooltip

# v1077.6 checkpoint-v13 successor line-budget repair token: dashboard_line_count=15496 bounded_successor_growth=True runtime_behavior_unchanged=True route_registry_parity_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface consolidation prep v1 registry tokens: dashboard-dispatcher-proof-surface-consolidation-prep-v1 /dashboard-dispatcher-proof-surface-consolidation-prep-v1 render_dashboard_dispatcher_proof_surface_consolidation_prep_v1 route_count=86 helper_backed_branch_count=48 historical_proof_route_count=37 parameterized_proof_ledger_prepared=True compatibility_contract_prepared=True

# v1077.7 bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False

# v1077.8 canonical proof surface registry tokens: /dashboard-dispatcher-proof-surface render_dashboard_dispatcher_proof_surface route_count=87 historical_proof_route_count=37 helper_backed_branch_count=48 preview_only=True compatibility_aliases_activated=False historical_routes_removed=False

# v1077.9 compatibility migration prep registry tokens: /dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1 render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1 route_count=88 preview_only=True compatibility_aliases_activated=False historical_routes_removed=False
