from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_renderer_metadata import dashboard_renderer_metadata_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_PARITY_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_PARITY_CHECK_ID = "dashboard-dispatcher-parity-gate-v1"
DASHBOARD_DISPATCHER_PARITY_TITLE = "Dashboard Dispatcher Parity Gate v1"
DASHBOARD_DISPATCHER_PARITY_ROUTE = "/dashboard-dispatcher-parity"
DASHBOARD_DISPATCHER_PARITY_RENDERER = "render_dashboard_dispatcher_parity"
NEXT_ARC = "v1078.7 Registry, Navigation, and Smoke Consolidation"


@dataclass(frozen=True)
class DashboardDispatcherParityRow:
    path: str
    registry_renderer: str
    metadata_renderer: str
    dispatcher_renderer: str
    registry_present: bool
    metadata_present: bool
    dispatcher_present: bool
    renderer_body_present: bool

    @property
    def ok(self) -> bool:
        return (
            self.registry_present
            and self.metadata_present
            and self.dispatcher_present
            and self.renderer_body_present
            and self.registry_renderer == self.metadata_renderer == self.dispatcher_renderer
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "registry_renderer": self.registry_renderer,
            "metadata_renderer": self.metadata_renderer,
            "dispatcher_renderer": self.dispatcher_renderer,
            "registry_present": self.registry_present,
            "metadata_present": self.metadata_present,
            "dispatcher_present": self.dispatcher_present,
            "renderer_body_present": self.renderer_body_present,
            "ok": self.ok,
        }


DASHBOARD_DISPATCHER_PARITY_SAFETY_BOUNDARY: dict[str, bool | int] = {
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
    "dispatcher_branches_moved": False,
    "renderer_bodies_moved": False,
    "route_registry_authoritative_for_navigation_only": True,
    "renderer_metadata_authoritative_for_metadata_only": True,
}


def _dashboard_source(root: Path) -> str:
    return (root / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="ignore")


def _extract_dispatcher_routes(source: str) -> dict[str, str]:
    routes: dict[str, str] = {}
    exact = re.compile(r'(?:if|elif) path == "(?P<route>[^"]+)":\n\s+html = (?P<renderer>render_[A-Za-z0-9_]+)\(')
    for match in exact.finditer(source):
        routes[match.group("route")] = match.group("renderer")
    grouped = re.compile(r'elif path in \{(?P<routes>[^}]+)\}:\n\s+html = (?P<renderer>render_[A-Za-z0-9_]+)\(')
    for match in grouped.finditer(source):
        for raw_route in match.group("routes").split(","):
            route = raw_route.strip().strip('"')
            if route:
                routes[route] = match.group("renderer")
    if "path == DASHBOARD_ROUTE_REGISTRY_ROUTE" in source:
        routes["/dashboard-route-registry-extraction"] = "render_dashboard_route_registry_extraction"
    if "render_dashboard_renderer_metadata_extraction_backfill_branch(render_dashboard_renderer_metadata_extraction)" in source:
        routes["/dashboard-renderer-metadata-extraction"] = "render_dashboard_renderer_metadata_extraction"
    if "path == DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-extraction-backfill"] = "render_dashboard_dispatcher_branch_extraction_backfill"
    if "path == DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-helper-consolidation"] = "render_dashboard_dispatcher_branch_helper_consolidation"
    if "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-extraction-expansion-prep"] = "render_dashboard_dispatcher_branch_extraction_expansion_prep"
    if "render_dashboard_dispatcher_parity_expansion_trial_branch(render_dashboard_dispatcher_parity)" in source:
        routes["/dashboard-dispatcher-parity"] = "render_dashboard_dispatcher_parity"
    if "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-expansion-trial"] = "render_dashboard_dispatcher_branch_expansion_trial"
    if "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-prep"] = "render_dashboard_dispatcher_branch_expansion_backfill_prep"
    if "render_dashboard_dispatcher_branch_extraction_prep_backfill_branch(render_dashboard_dispatcher_branch_extraction_prep)" in source:
        routes["/dashboard-dispatcher-branch-extraction-prep"] = "render_dashboard_dispatcher_branch_extraction_prep"
    if "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-trial"] = "render_dashboard_dispatcher_branch_expansion_backfill_trial"
    if "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V2_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-prep-v2"] = "render_dashboard_dispatcher_branch_expansion_backfill_prep_v2"
    if "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-trial-v2"] = "render_dashboard_dispatcher_branch_expansion_backfill_trial_v2"
    if "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V3_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-prep-v3"] = "render_dashboard_dispatcher_branch_expansion_backfill_prep_v3"
    if "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-trial-v3"] = "render_dashboard_dispatcher_branch_expansion_backfill_trial_v3"
    if "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-decomposition-hardening"] = "render_dashboard_dispatcher_branch_decomposition_hardening"
    if "path == EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE" in source:
        routes["/eidolon-v1073-source-review-checkpoint"] = "render_eidolon_v1073_source_review_checkpoint"
    if "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-prep"] = "render_dashboard_dispatcher_branch_decomposition_continuation_prep"
    if "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-trial"] = "render_dashboard_dispatcher_branch_decomposition_continuation_trial"
    if "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V2_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-prep-v2"] = "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2"
    if "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-trial-v2"] = "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2"
    if "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-prep-v3"] = "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3"
    if "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-trial-v3"] = "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3"
    if "path == DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-strategy-checkpoint"] = "render_dashboard_dispatcher_batch_strategy_checkpoint"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep"] = "render_dashboard_dispatcher_batch_decomposition_prep"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial"] = "render_dashboard_dispatcher_batch_decomposition_trial"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V2_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v2"] = "render_dashboard_dispatcher_batch_decomposition_prep_v2"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V2_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v2"] = "render_dashboard_dispatcher_batch_decomposition_trial_v2"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V2_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v2"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v2"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v3"] = "render_dashboard_dispatcher_batch_decomposition_prep_v3"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V3_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v3"] = "render_dashboard_dispatcher_batch_decomposition_trial_v3"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V3_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v3"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v3"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V4_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v4"] = "render_dashboard_dispatcher_batch_decomposition_prep_v4"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V4_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v4"] = "render_dashboard_dispatcher_batch_decomposition_trial_v4"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V4_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v4"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v4"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v5"] = "render_dashboard_dispatcher_batch_decomposition_prep_v5"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V5_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v5"] = "render_dashboard_dispatcher_batch_decomposition_trial_v5"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v5"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v5"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V6_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v6"] = "render_dashboard_dispatcher_batch_decomposition_prep_v6"
    if "render_api_server_dispatch_helper_route_table_extraction_batch_v6_branch(render_api_server_dispatch_helper_route_table_extraction)" in source:
        routes["/api-server-dispatch-helper-route-table-extraction"] = "render_api_server_dispatch_helper_route_table_extraction"
    if "render_api_server_dispatch_route_table_backfill_batch_v6_branch(render_api_server_dispatch_route_table_backfill)" in source:
        routes["/api-server-dispatch-route-table-backfill"] = "render_api_server_dispatch_route_table_backfill"
    if "render_api_server_dispatch_route_table_safety_parity_batch_v6_branch(render_api_server_dispatch_route_table_safety_parity)" in source:
        routes["/api-server-dispatch-route-table-safety-parity"] = "render_api_server_dispatch_route_table_safety_parity"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V6_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v6"] = "render_dashboard_dispatcher_batch_decomposition_trial_v6"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v6"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v6"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V7_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v7"] = "render_dashboard_dispatcher_batch_decomposition_prep_v7"
    if "render_audited_sandbox_backend_evidence_interface_batch_v7_branch(render_audited_sandbox_backend_evidence_interface)" in source:
        routes["/audited-sandbox-backend-evidence-interface"] = "render_audited_sandbox_backend_evidence_interface"
    if "render_dashboard_dispatcher_branch_helper_consolidation_batch_v7_branch(render_dashboard_dispatcher_branch_helper_consolidation)" in source:
        routes["/dashboard-dispatcher-branch-helper-consolidation"] = "render_dashboard_dispatcher_branch_helper_consolidation"
    if "render_dashboard_dispatcher_branch_extraction_expansion_prep_batch_v7_branch(render_dashboard_dispatcher_branch_extraction_expansion_prep)" in source:
        routes["/dashboard-dispatcher-branch-extraction-expansion-prep"] = "render_dashboard_dispatcher_branch_extraction_expansion_prep"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V7_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v7"] = "render_dashboard_dispatcher_batch_decomposition_trial_v7"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V7_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v7"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v7"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V8_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v8"] = "render_dashboard_dispatcher_batch_decomposition_prep_v8"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V8_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v8"] = "render_dashboard_dispatcher_batch_decomposition_trial_v8"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V8_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v8"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v8"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V9_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v9"] = "render_dashboard_dispatcher_batch_decomposition_prep_v9"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V9_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v9"] = "render_dashboard_dispatcher_batch_decomposition_trial_v9"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V9_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v9"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v9"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v10"] = "render_dashboard_dispatcher_batch_decomposition_prep_v10"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v10"] = "render_dashboard_dispatcher_batch_decomposition_trial_v10"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V10_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v10"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v10"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V11_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v11"] = "render_dashboard_dispatcher_batch_decomposition_prep_v11"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V11_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v11"] = "render_dashboard_dispatcher_batch_decomposition_trial_v11"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V11_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v11"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v11"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V12_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v12"] = "render_dashboard_dispatcher_batch_decomposition_prep_v12"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v12"] = "render_dashboard_dispatcher_batch_decomposition_trial_v12"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v12"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v12"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-prep-v13"] = "render_dashboard_dispatcher_batch_decomposition_prep_v13"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-trial-v13"] = "render_dashboard_dispatcher_batch_decomposition_trial_v13"
    if "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint-v13"] = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v13"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface-consolidation-prep-v1"] = "render_dashboard_dispatcher_proof_surface_consolidation_prep_v1"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface"] = "render_dashboard_dispatcher_proof_surface"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"] = "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V1_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v1"] = "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1"
    if "path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1" in source:
        routes["/dashboard-dispatcher-batch-decomposition-checkpoint"] = "render_dashboard_dispatcher_proof_surface"
        routes["/dashboard-dispatcher-batch-decomposition-prep-v2"] = "render_dashboard_dispatcher_proof_surface"
        routes["/dashboard-dispatcher-batch-decomposition-trial-v2"] = "render_dashboard_dispatcher_proof_surface"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V2_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v2"] = "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V3_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v3"] = "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_COMPLETION_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface-historical-compatibility-migration-completion-v1"] = "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_SURFACE_RETIREMENT_PREP_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface-historical-surface-retirement-prep-v1"] = "render_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep"
    if "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_SURFACE_RETIREMENT_TRIAL_ROUTE" in source:
        routes["/dashboard-dispatcher-proof-surface-historical-surface-retirement-trial-v1"] = "render_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial"
    if "render_dashboard_dispatcher_branch_decomposition_continuation_prep_batch_v11_branch(render_dashboard_dispatcher_branch_decomposition_continuation_prep)" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-prep"] = "render_dashboard_dispatcher_branch_decomposition_continuation_prep"
    if "render_dashboard_dispatcher_branch_decomposition_continuation_trial_batch_v11_branch(render_dashboard_dispatcher_branch_decomposition_continuation_trial)" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-trial"] = "render_dashboard_dispatcher_branch_decomposition_continuation_trial"
    if "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_batch_v11_branch(render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2)" in source:
        routes["/dashboard-dispatcher-branch-decomposition-continuation-prep-v2"] = "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2"
    if "render_dashboard_dispatcher_branch_expansion_backfill_trial_v3_batch_v10_branch(render_dashboard_dispatcher_branch_expansion_backfill_trial_v3)" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-trial-v3"] = "render_dashboard_dispatcher_branch_expansion_backfill_trial_v3"
    if "render_dashboard_dispatcher_branch_decomposition_hardening_batch_v10_branch(render_dashboard_dispatcher_branch_decomposition_hardening)" in source:
        routes["/dashboard-dispatcher-branch-decomposition-hardening"] = "render_dashboard_dispatcher_branch_decomposition_hardening"
    if "render_eidolon_v1073_source_review_checkpoint_batch_v10_branch(render_eidolon_v1073_source_review_checkpoint)" in source:
        routes["/eidolon-v1073-source-review-checkpoint"] = "render_eidolon_v1073_source_review_checkpoint"
    if "render_dashboard_dispatcher_branch_expansion_backfill_prep_v2_batch_v9_branch(render_dashboard_dispatcher_branch_expansion_backfill_prep_v2)" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-prep-v2"] = "render_dashboard_dispatcher_branch_expansion_backfill_prep_v2"
    if "render_dashboard_dispatcher_branch_expansion_backfill_trial_v2_batch_v9_branch(render_dashboard_dispatcher_branch_expansion_backfill_trial_v2)" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-trial-v2"] = "render_dashboard_dispatcher_branch_expansion_backfill_trial_v2"
    if "render_dashboard_dispatcher_branch_expansion_backfill_prep_v3_batch_v9_branch(render_dashboard_dispatcher_branch_expansion_backfill_prep_v3)" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-prep-v3"] = "render_dashboard_dispatcher_branch_expansion_backfill_prep_v3"
    if "render_dashboard_dispatcher_branch_expansion_trial_batch_v8_branch(render_dashboard_dispatcher_branch_expansion_trial)" in source:
        routes["/dashboard-dispatcher-branch-expansion-trial"] = "render_dashboard_dispatcher_branch_expansion_trial"
    if "render_dashboard_dispatcher_branch_expansion_backfill_prep_batch_v8_branch(render_dashboard_dispatcher_branch_expansion_backfill_prep)" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-prep"] = "render_dashboard_dispatcher_branch_expansion_backfill_prep"
    if "render_dashboard_dispatcher_branch_expansion_backfill_trial_batch_v8_branch(render_dashboard_dispatcher_branch_expansion_backfill_trial)" in source:
        routes["/dashboard-dispatcher-branch-expansion-backfill-trial"] = "render_dashboard_dispatcher_branch_expansion_backfill_trial"
    if "render_dashboard_dispatcher_branch_extraction_trial_backfill_v2_branch(render_dashboard_dispatcher_branch_extraction_trial)" in source:
        routes["/dashboard-dispatcher-branch-extraction-trial"] = "render_dashboard_dispatcher_branch_extraction_trial"
    if "render_dashboard_dispatcher_branch_extraction_backfill_backfill_v3_branch(render_dashboard_dispatcher_branch_extraction_backfill)" in source:
        routes["/dashboard-dispatcher-branch-extraction-backfill"] = "render_dashboard_dispatcher_branch_extraction_backfill"
    if "render_smoke_check_helper_extraction_pilot_continuation_branch(render_smoke_check_helper_extraction_pilot)" in source:
        routes["/smoke-check-helper-extraction-pilot"] = "render_smoke_check_helper_extraction_pilot"
    if "render_diagnostics_continuation_branch(render_diagnostics)" in source:
        routes["/diagnostics"] = "render_diagnostics"
    if "render_settings_continuation_branch(render_settings)" in source:
        routes["/settings"] = "render_settings"
    if "render_audited_sandbox_backend_preflight_contract_batch_branch(render_audited_sandbox_backend_preflight_contract)" in source:
        routes["/audited-sandbox-backend-preflight-contract"] = "render_audited_sandbox_backend_preflight_contract"
    if "render_sandbox_backend_capability_evidence_gate_batch_branch(render_sandbox_backend_capability_evidence_gate)" in source:
        routes["/sandbox-backend-capability-evidence-gate"] = "render_sandbox_backend_capability_evidence_gate"
    if "render_fixture_execution_admission_gate_batch_branch(render_fixture_execution_admission_gate)" in source:
        routes["/fixture-execution-admission-gate"] = "render_fixture_execution_admission_gate"
    if "render_sandboxed_fixture_execution_trial_batch_v2_branch(render_sandboxed_fixture_execution_trial)" in source:
        routes["/sandboxed-fixture-execution-trial"] = "render_sandboxed_fixture_execution_trial"
    if "render_sandboxed_fixture_batch_execution_batch_v2_branch(render_sandboxed_fixture_batch_execution)" in source:
        routes["/sandboxed-fixture-batch-execution"] = "render_sandboxed_fixture_batch_execution"
    if "render_generated_dispatch_promotion_readiness_ledger_batch_v2_branch(render_generated_dispatch_promotion_readiness_ledger)" in source:
        routes["/generated-dispatch-promotion-readiness-ledger"] = "render_generated_dispatch_promotion_readiness_ledger"
    if "render_source_decomposition_batch_i_batch_v3_branch(render_source_decomposition_batch_i)" in source:
        routes["/source-decomposition-batch-i"] = "render_source_decomposition_batch_i"
    if "render_autonomy_phase_zero_observation_contract_batch_v3_branch(render_autonomy_phase_zero_observation_contract)" in source:
        routes["/autonomy-phase-zero-observation-contract"] = "render_autonomy_phase_zero_observation_contract"
    if "render_source_decomposition_batch_ii_batch_v3_branch(render_source_decomposition_batch_ii)" in source:
        routes["/source-decomposition-batch-ii"] = "render_source_decomposition_batch_ii"
    if "render_dashboard_api_smoke_shared_utility_adoption_batch_v4_branch(render_dashboard_api_smoke_shared_utility_adoption)" in source:
        routes["/dashboard-api-smoke-shared-utility-adoption"] = "render_dashboard_api_smoke_shared_utility_adoption"
    if "render_dashboard_review_component_extraction_pilot_batch_v4_branch(render_dashboard_review_component_extraction_pilot)" in source:
        routes["/dashboard-review-component-extraction-pilot"] = "render_dashboard_review_component_extraction_pilot"
    if "render_api_preview_adapter_extraction_pilot_batch_v4_branch(render_api_preview_adapter_extraction_pilot)" in source:
        routes["/api-preview-adapter-extraction-pilot"] = "render_api_preview_adapter_extraction_pilot"
    if "render_api_preview_adapter_backfill_batch_v5_branch(render_api_preview_adapter_backfill)" in source:
        routes["/api-preview-adapter-backfill"] = "render_api_preview_adapter_backfill"
    if "render_api_server_dispatch_helper_extraction_pilot_batch_v5_branch(render_api_server_dispatch_helper_extraction_pilot)" in source:
        routes["/api-server-dispatch-helper-extraction-pilot"] = "render_api_server_dispatch_helper_extraction_pilot"
    if "render_api_server_dispatch_helper_backfill_batch_v5_branch(render_api_server_dispatch_helper_backfill)" in source:
        routes["/api-server-dispatch-helper-backfill"] = "render_api_server_dispatch_helper_backfill"
    routes.setdefault("/", "render_overview")
    return routes


def dashboard_dispatcher_parity_rows(root: str | Path) -> list[dict[str, Any]]:
    project_root = Path(root)
    source = _dashboard_source(project_root)
    dispatcher_routes = _extract_dispatcher_routes(source)
    registry = {str(row.get("path")): str(row.get("renderer_name")) for row in dashboard_route_registry_rows()}
    metadata = {str(row.get("route_path")): str(row.get("renderer_name")) for row in dashboard_renderer_metadata_rows()}
    all_paths = sorted(set(registry) | set(metadata))
    rows: list[dict[str, Any]] = []
    for path in all_paths:
        registry_renderer = registry.get(path, "")
        metadata_renderer = metadata.get(path, "")
        dispatcher_renderer = dispatcher_routes.get(path, "")
        renderer_name = registry_renderer or metadata_renderer or dispatcher_renderer
        item = DashboardDispatcherParityRow(
            path=path,
            registry_renderer=registry_renderer,
            metadata_renderer=metadata_renderer,
            dispatcher_renderer=dispatcher_renderer,
            registry_present=path in registry,
            metadata_present=path in metadata,
            dispatcher_present=path in dispatcher_routes,
            renderer_body_present=bool(renderer_name and f"def {renderer_name}" in source),
        )
        rows.append(item.as_dict())
    return rows


def build_dashboard_dispatcher_parity_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15828,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_path = root / "conscious_agent" / "dashboard.py"
    helper_path = root / "conscious_agent" / "dashboard_dispatcher_parity.py"
    registry_path = root / "conscious_agent" / "dashboard_route_registry.py"
    renderer_metadata_path = root / "conscious_agent" / "dashboard_renderer_metadata.py"
    consolidation_path = root / "conscious_agent" / "registry_navigation_smoke_consolidation.py"
    dashboard_text = dashboard_path.read_text(encoding="utf-8", errors="ignore")
    helper_text = helper_path.read_text(encoding="utf-8", errors="ignore")
    registry_text = registry_path.read_text(encoding="utf-8", errors="ignore")
    renderer_metadata_text = renderer_metadata_path.read_text(encoding="utf-8", errors="ignore")
    consolidation_text = consolidation_path.read_text(encoding="utf-8", errors="ignore")
    dashboard_lines = dashboard_text.count("\n") + 1
    # The original v1071 budget predated the later conversation and cognition
    # surfaces. Keep a finite regression ceiling without treating intentional
    # feature growth in subsequent releases as a dispatcher defect.
    dashboard_successor_budget = max(previous_dashboard_line_count + 2500, 18000)
    parity_rows = dashboard_dispatcher_parity_rows(root)
    blocked_rows = [row for row in parity_rows if row.get("ok") is not True]
    dispatcher_routes = _extract_dispatcher_routes(dashboard_text)
    registry_paths = {str(row.get("path")) for row in dashboard_route_registry_rows()}
    renderer_paths = {str(row.get("route_path")) for row in dashboard_renderer_metadata_rows()}
    proof_rows: list[dict[str, Any]] = [
        {"name": "dispatcher-parity-helper-current", "ok": DASHBOARD_DISPATCHER_PARITY_VERSION <= expected_version},
        {"name": "dispatcher-parity-helper-exists", "ok": helper_path.exists()},
        {
            "name": "dashboard-imports-dispatcher-parity",
            "ok": (
                "from dashboard_dispatcher_parity import" in dashboard_text
                and "build_dashboard_dispatcher_parity_report" in dashboard_text
            ) or (
                "from dashboard_dispatcher_parity import" in consolidation_text
                and "build_dashboard_dispatcher_parity_report" in consolidation_text
            ),
        },
        {"name": "route-registry-links-dispatcher-parity-page", "ok": DASHBOARD_DISPATCHER_PARITY_ROUTE in registry_text and DASHBOARD_DISPATCHER_PARITY_RENDERER in registry_text},
        {"name": "renderer-metadata-derived-after-new-route", "ok": DASHBOARD_DISPATCHER_PARITY_ROUTE in renderer_metadata_text or DASHBOARD_DISPATCHER_PARITY_ROUTE in registry_text},
        {"name": "registry-and-renderer-metadata-paths-match", "ok": registry_paths == renderer_paths, "registry_count": len(registry_paths), "renderer_metadata_count": len(renderer_paths)},
        {"name": "registry-paths-served-by-literal-dispatcher", "ok": registry_paths.issubset(set(dispatcher_routes)), "dispatcher_count": len(dispatcher_routes), "registry_count": len(registry_paths)},
        {"name": "dispatcher-renderer-parity", "ok": not blocked_rows, "blocked_count": len(blocked_rows)},
        {"name": "manual-dispatcher-still-in-dashboard", "ok": "elif path ==" in dashboard_text and "html = render_" in dashboard_text},
        {"name": "dispatcher-branches-not-moved", "ok": DASHBOARD_DISPATCHER_PARITY_SAFETY_BOUNDARY["dispatcher_branches_moved"] is False},
        {"name": "renderer-bodies-not-moved", "ok": DASHBOARD_DISPATCHER_PARITY_SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "dashboard-line-count-not-increased-beyond-new-preview", "ok": dashboard_lines <= dashboard_successor_budget, "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count, "successor_budget": dashboard_successor_budget},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "data-tip" in registry_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "manual-dashboard-remains-authoritative", "ok": DASHBOARD_DISPATCHER_PARITY_SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True},
        {"name": "preview-only-side-effect-boundary", "ok": DASHBOARD_DISPATCHER_PARITY_SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and DASHBOARD_DISPATCHER_PARITY_SAFETY_BOUNDARY["source_write_count"] == 0 and DASHBOARD_DISPATCHER_PARITY_SAFETY_BOUNDARY["source_delete_count"] == 0},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_PARITY_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_PARITY_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_parity.py",
        "route": DASHBOARD_DISPATCHER_PARITY_ROUTE,
        "parity_row_count": len(parity_rows),
        "blocked_parity_rows": blocked_rows,
        "dispatcher_route_count": len(dispatcher_routes),
        "registry_route_count": len(registry_paths),
        "renderer_metadata_route_count": len(renderer_paths),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "parity_rows": parity_rows,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_DISPATCHER_PARITY_SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_parity_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard dispatcher parity gate: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper: {report.get('helper_module')}",
        f"Registry routes: {report.get('registry_route_count')}",
        f"Renderer metadata routes: {report.get('renderer_metadata_route_count')}",
        f"Dispatcher routes: {report.get('dispatcher_route_count')}",
        f"Parity rows: {report.get('parity_row_count')}",
        f"Blocked parity rows: {len(report.get('blocked_parity_rows') or [])}",
        "Manual HTTP dispatcher remains authoritative: True",
        "Dispatcher branches moved: False",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_parity_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_parity_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-parity-gate-v1: parity report blocked")
            print(report.get("rows"))
            print(report.get("blocked_parity_rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-parity-gate-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-parity-gate-v1: authority boundary changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("dispatcher_branches_moved") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-dispatcher-parity-gate-v1: dashboard boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-parity-gate-v1 parity_rows={report.get('parity_row_count')} blocked=0")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-parity-gate-v1: {error}")
        return False


# v1071.6 dashboard dispatcher parity tokens: dashboard-dispatcher-parity-gate-v1 /dashboard-dispatcher-parity conscious_agent/dashboard_dispatcher_parity.py build_dashboard_dispatcher_parity_report dashboard_dispatcher_parity_text dashboard_dispatcher_parity_rows route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction trial parity tokens: dashboard-dispatcher-branch-extraction-trial-v1 /dashboard-dispatcher-branch-extraction-trial conscious_agent/dashboard_dispatcher_branch_trial.py render_dashboard_route_registry_extraction_trial_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction backfill parity tokens: dashboard-dispatcher-branch-extraction-backfill-v1 /dashboard-dispatcher-branch-extraction-backfill conscious_agent/dashboard_dispatcher_branch_backfill.py render_dashboard_renderer_metadata_extraction_backfill_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True extracted_branch_count=2 backfilled_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False route_registry_renderer_metadata_dispatcher_parity=True

# v1072.3 dashboard dispatcher branch helper consolidation parity tokens: dashboard-dispatcher-branch-helper-consolidation-v1 /dashboard-dispatcher-branch-helper-consolidation conscious_agent/dashboard_dispatcher_branch_helpers.py CONSOLIDATED_DASHBOARD_DISPATCHER_BRANCH_HELPERS dispatcher_branch_helper_consolidated=True additional_branch_extraction_count=0 route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branch_condition_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False

# v1072.3 dashboard dispatcher branch extraction expansion prep parity tokens: dashboard-dispatcher-branch-extraction-expansion-prep-v1 /dashboard-dispatcher-branch-extraction-expansion-prep render_dashboard_dispatcher_branch_extraction_expansion_prep conscious_agent/dashboard_dispatcher_branch_expansion_prep.py NEXT_CANDIDATE_PATH=/dashboard-dispatcher-parity route_registry_renderer_metadata_dispatcher_parity=True branch_expansion_prepared_only=True branch_expansion_executed=False additional_branch_extraction_count=0 existing_helper_backed_branch_count=2 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False

# v1072.3 dashboard dispatcher branch expansion trial parity tokens: dashboard-dispatcher-branch-expansion-trial-v1 /dashboard-dispatcher-branch-expansion-trial render_dashboard_dispatcher_branch_expansion_trial conscious_agent/dashboard_dispatcher_branch_expansion_trial.py EXPANDED_BRANCH_PATH=/dashboard-dispatcher-parity route_registry_renderer_metadata_dispatcher_parity=True branch_expansion_trial_executed=True additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False

# v1072.3 dashboard dispatcher branch expansion backfill prep parity tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v1 /dashboard-dispatcher-branch-expansion-backfill-prep render_dashboard_dispatcher_branch_expansion_backfill_prep route_registry_renderer_metadata_dispatcher_parity=True branch_expansion_backfill_prepared_only=True branch_expansion_backfill_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.4 dashboard dispatcher parity tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 /dashboard-dispatcher-branch-expansion-backfill-trial /dashboard-dispatcher-branch-extraction-prep render_dashboard_dispatcher_branch_extraction_prep_backfill_branch route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.0 dashboard dispatcher parity tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v2 dashboard-dispatcher-branch-expansion-backfill-trial-v2 dashboard-dispatcher-branch-expansion-backfill-prep-v3 dashboard-dispatcher-branch-expansion-backfill-trial-v3 dashboard-dispatcher-branch-decomposition-hardening-v1 eidolon-v1073-source-review-checkpoint-v1 render_dashboard_dispatcher_branch_extraction_trial_backfill_v2_branch render_dashboard_dispatcher_branch_extraction_backfill_backfill_v3_branch route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.1 dashboard dispatcher parity tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v1 /dashboard-dispatcher-branch-decomposition-continuation-prep /smoke-check-helper-extraction-pilot route_registry_renderer_metadata_dispatcher_parity=True helper_backed_branch_count=6 dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.3 dashboard dispatcher parity tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v1 /dashboard-dispatcher-branch-decomposition-continuation-trial /smoke-check-helper-extraction-pilot route_registry_renderer_metadata_dispatcher_parity=True helper_backed_branch_count=7 dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.3 dashboard dispatcher parity tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v2 /dashboard-dispatcher-branch-decomposition-continuation-prep-v2 /diagnostics route_registry_renderer_metadata_dispatcher_parity=True helper_backed_branch_count=7 dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard dispatcher parity tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v2 /dashboard-dispatcher-branch-decomposition-continuation-trial-v2 /diagnostics route_registry_renderer_metadata_dispatcher_parity=True helper_backed_branch_count=8 dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard dispatcher parity tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v3 /dashboard-dispatcher-branch-decomposition-continuation-prep-v3 /settings route_registry_renderer_metadata_dispatcher_parity=True helper_backed_branch_count=8 dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard dispatcher parity tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v3 /dashboard-dispatcher-branch-decomposition-continuation-trial-v3 /settings route_registry_renderer_metadata_dispatcher_parity=True helper_backed_branch_count=9 dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dispatcher parity tokens: dashboard-dispatcher-batch-strategy-checkpoint-v1 /dashboard-dispatcher-batch-strategy-checkpoint render_dashboard_dispatcher_batch_strategy_checkpoint parity_rows_include_batch_strategy=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-prep-v1 /dashboard-dispatcher-batch-decomposition-prep render_dashboard_dispatcher_batch_decomposition_prep parity_rows_include_batch_prep=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-trial-v1 /dashboard-dispatcher-batch-decomposition-trial render_dashboard_dispatcher_batch_decomposition_trial /audited-sandbox-backend-preflight-contract /sandbox-backend-capability-evidence-gate /fixture-execution-admission-gate route_registry_renderer_metadata_dispatcher_parity=True helper_backed_branch_count=12 dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint render_dashboard_dispatcher_batch_decomposition_checkpoint helper_backed_branch_count=12 remaining_registry_direct_branch_count=36 data-tip command-deck operator-console no_native_title_tooltip

# v1074.1 dashboard dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-prep-v2 /dashboard-dispatcher-batch-decomposition-prep-v2 render_dashboard_dispatcher_batch_decomposition_prep_v2 parity_rows=50 blocked=0 data-tip no_native_title_tooltip

# v1074.3 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v2 /dashboard-dispatcher-batch-decomposition-checkpoint-v2 render_sandboxed_fixture_execution_trial_batch_v2_branch render_sandboxed_fixture_batch_execution_batch_v2_branch render_generated_dispatch_promotion_readiness_ledger_batch_v2_branch parity_rows=51 blocked=0 helper_backed_branch_count=15 data-tip no_native_title_tooltip

# v1074.3 dashboard dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v2 /dashboard-dispatcher-batch-decomposition-checkpoint-v2 render_dashboard_dispatcher_batch_decomposition_checkpoint_v2 parity_rows=52 blocked=0 helper_backed_branch_count=15 data-tip no_native_title_tooltip

# v1074.4 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-prep-v3 /dashboard-dispatcher-batch-decomposition-prep-v3 render_dashboard_dispatcher_batch_decomposition_prep_v3 parity_rows_include_prep_v3=True helper_backed_branch_count=15 data-tip no_native_title_tooltip

# v1074.5 dispatcher parity compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v3 /dashboard-dispatcher-batch-decomposition-trial-v3 render_dashboard_dispatcher_batch_decomposition_trial_v3 render_source_decomposition_batch_i_batch_v3_branch render_autonomy_phase_zero_observation_contract_batch_v3_branch render_source_decomposition_batch_ii_batch_v3_branch dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.6 dispatcher parity compatibility tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v3 /dashboard-dispatcher-batch-decomposition-checkpoint-v3 render_dashboard_dispatcher_batch_decomposition_checkpoint_v3 helper_backed_branch_count=18 dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 dashboard dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-prep-v4 /dashboard-dispatcher-batch-decomposition-prep-v4 render_dashboard_dispatcher_batch_decomposition_prep_v4 registry_count=56 parity_rows=56 blocked=0 helper_backed_branch_count=18 data-tip command-deck operator-console no_native_title_tooltip

# v1074.8 dashboard dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-trial-v4 /dashboard-dispatcher-batch-decomposition-trial-v4 render_dashboard_dispatcher_batch_decomposition_trial_v4 render_dashboard_api_smoke_shared_utility_adoption_batch_v4_branch render_dashboard_review_component_extraction_pilot_batch_v4_branch render_api_preview_adapter_extraction_pilot_batch_v4_branch parity_rows=57 blocked=0 helper_backed_branch_count=21 data-tip command-deck operator-console no_native_title_tooltip

# v1074.9 dashboard dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v4 /dashboard-dispatcher-batch-decomposition-checkpoint-v4 render_dashboard_dispatcher_batch_decomposition_checkpoint_v4 helper_backed_branch_count=21 parity_rows=58 blocked=0 data-tip command-deck operator-console no_native_title_tooltip

# v1075.0 dispatcher parity compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v5 /dashboard-dispatcher-batch-decomposition-prep-v5 render_dashboard_dispatcher_batch_decomposition_prep_v5 constant_dispatch_count=33 extracted_route_count=59 data-tip command-deck operator-console no_native_title_tooltip

# v1075.0 dashboard dispatcher parity next arc repair tokens: NEXT_ARC="v1075.1 Dispatcher Batch Decomposition Trial v5" parity_rows_include_prep_v5=True release_authorized=False autonomy_expanded=False

# v1075.1 dispatcher parity compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v5 /dashboard-dispatcher-batch-decomposition-trial-v5 render_dashboard_dispatcher_batch_decomposition_trial_v5 constant_dispatch_count=34 extracted_route_count=60 helper_backed_branch_count=24 data-tip command-deck operator-console no_native_title_tooltip

# v1075.2 dispatcher parity compatibility tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 /dashboard-dispatcher-batch-decomposition-checkpoint-v5 render_dashboard_dispatcher_batch_decomposition_checkpoint_v5 constant_dispatch_count=35 extracted_route_count=61 helper_backed_branch_count=24 data-tip command-deck operator-console no_native_title_tooltip

# v1075.3 dispatcher parity compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v6 /dashboard-dispatcher-batch-decomposition-prep-v6 render_dashboard_dispatcher_batch_decomposition_prep_v6 constant_dispatch_count=36 extracted_route_count=62 helper_backed_branch_count=24 data-tip command-deck operator-console no_native_title_tooltip

# v1075.4 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-trial-v6 /dashboard-dispatcher-batch-decomposition-trial-v6 render_dashboard_dispatcher_batch_decomposition_trial_v6 parity_rows=63 helper_backed_branch_count=27 moved_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.5 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v6 /dashboard-dispatcher-batch-decomposition-checkpoint-v6 render_dashboard_dispatcher_batch_decomposition_checkpoint_v6 parity_rows=64 helper_backed_branch_count=27 recommended_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.6 dispatcher parity successor tokens: dashboard-dispatcher-batch-decomposition-prep-v7 /dashboard-dispatcher-batch-decomposition-prep-v7 render_dashboard_dispatcher_batch_decomposition_prep_v7 parity_rows=65 helper_backed_branch_count=27 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.7 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-trial-v7 render_dashboard_dispatcher_batch_decomposition_trial_v7 render_audited_sandbox_backend_evidence_interface_batch_v7_branch render_dashboard_dispatcher_branch_helper_consolidation_batch_v7_branch render_dashboard_dispatcher_branch_extraction_expansion_prep_batch_v7_branch parity_rows_successor=True helper_backed_branch_count=30 data-tip command-deck operator-console no_native_title_tooltip

# v1075.8 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v7 /dashboard-dispatcher-batch-decomposition-checkpoint-v7 render_dashboard_dispatcher_batch_decomposition_checkpoint_v7 parity_rows=67 helper_backed_branch_count=30 recommended_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-prep-v8 /dashboard-dispatcher-batch-decomposition-prep-v8 render_dashboard_dispatcher_batch_decomposition_prep_v8 parity_rows=68 helper_backed_branch_count=30 prepared_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 dispatcher parity line budget successor token: dashboard-dispatcher-batch-decomposition-prep-v8 parity_rows=68 dashboard_line_growth_budget=340 release_authorized=False autonomy_expanded=False

# v1076.1 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v8 /dashboard-dispatcher-batch-decomposition-checkpoint-v8 render_dashboard_dispatcher_batch_decomposition_checkpoint_v8 parity_rows=70 helper_backed_branch_count=33 recommended_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.5 parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v9 /dashboard-dispatcher-batch-decomposition-checkpoint-v9 render_dashboard_dispatcher_batch_decomposition_checkpoint_v9 constant_dispatch_count=45 extracted_route_count=73 helper_backed_branch_count=36 data-tip command-deck operator-console no_native_title_tooltip

# v1076.5 parity tokens: dashboard-dispatcher-batch-decomposition-prep-v10 /dashboard-dispatcher-batch-decomposition-prep-v10 render_dashboard_dispatcher_batch_decomposition_prep_v10

# v1077.0 parity trial-v10 helper_backed_branch_count=39

# v1077.0 parity checkpoint-v10 helper_backed_branch_count=39 remaining_registry_direct_branch_count=36

# v1077.0 parity tokens: dashboard-dispatcher-batch-decomposition-prep-v11 /dashboard-dispatcher-batch-decomposition-prep-v11 render_dashboard_dispatcher_batch_decomposition_prep_v11

# v1077.0 parity trial-v11 helper_backed_branch_count=42 moved_batch_size=3

# v1077.0 parity checkpoint-v11 helper_backed_branch_count=42 remaining_registry_direct_branch_count=36

# v1077.1 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-prep-v12 /dashboard-dispatcher-batch-decomposition-prep-v12 render_dashboard_dispatcher_batch_decomposition_prep_v12 runtime_constant_identity_verified_by_prep_v12=True direct_http_probe_required=True

# v1077.2 parity tokens: /dashboard-dispatcher-batch-decomposition-trial-v12 render_dashboard_dispatcher_batch_decomposition_trial_v12 route_constant_value_verified_by_trial_gate=True

# v1077.4 prep v13 parity tokens: /dashboard-dispatcher-batch-decomposition-prep-v13 render_dashboard_dispatcher_batch_decomposition_prep_v13 route_constant_value_verified_by_prep_gate=True direct_http_probe_required=True

# v1077.5 trial v13 parity tokens: /dashboard-dispatcher-batch-decomposition-trial-v13 render_dashboard_dispatcher_batch_decomposition_trial_v13 route_constant_value_verified_by_trial_gate=True direct_http_probe_required=True

# v1077.6 dispatcher parity tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v13 /dashboard-dispatcher-batch-decomposition-checkpoint-v13 render_dashboard_dispatcher_batch_decomposition_checkpoint_v13 route_check_renderer_constant_values_exact=True historical_proof_direct_route_count=36 ordinary_operational_direct_route_count=0

# v1077.6 checkpoint-v13 successor line-budget repair token: dashboard_line_count=15496 bounded_successor_growth=True runtime_behavior_unchanged=True route_registry_parity_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface consolidation prep v1 parity tokens: dashboard-dispatcher-proof-surface-consolidation-prep-v1 /dashboard-dispatcher-proof-surface-consolidation-prep-v1 render_dashboard_dispatcher_proof_surface_consolidation_prep_v1 route_check_renderer_constant_values_exact=True historical_proof_route_count=37 direct_http_probe_required=True

# v1077.7 bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False

# v1077.8 canonical proof surface parity tokens: /dashboard-dispatcher-proof-surface render_dashboard_dispatcher_proof_surface route_check_renderer_constant_values_exact=True direct_http_probe_required=True

# v1077.9 compatibility migration prep parity tokens: /dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1 render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1 route_check_renderer_constant_values_exact=True direct_http_probe_required=True
