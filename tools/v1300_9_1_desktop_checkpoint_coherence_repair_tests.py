from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bounded_development_campaigns_checkpoint import bounded_development_campaigns_checkpoint
from cognitive_coding_checkpoint import cognitive_coding_checkpoint
from competing_candidate_evaluation_checkpoint import competing_candidate_evaluation_checkpoint
from comprehensive_verification_checkpoint import comprehensive_verification_checkpoint
from independent_improvement_proposals_checkpoint import independent_improvement_proposals_checkpoint
from product_quality_judgment_checkpoint import product_quality_judgment_checkpoint
from provider_aware_performance_checkpoint import provider_aware_performance_checkpoint
from release_authority import CHECKPOINT_HISTORY, WORKING_SOURCE_VERSION
from checkpoint_progress import retained_checkpoint_progress
from performance_budgets import DEFAULT_BUDGETS
from segmented_release_verifier import DEFAULT_SUITE_TIMEOUT_SECONDS, SUITE_TIMEOUT_OVERRIDES
from supervised_autonomy_rehearsal_checkpoint import supervised_autonomy_rehearsal_checkpoint
from value_risk_deliberation_checkpoint import value_risk_deliberation_checkpoint
from release_verify import QUICK_STAGE_NAMES, FULL_STAGE_NAMES
from segmented_release_verifier import DEFAULT_STAGES


checks: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    checks.append(label)


checkpoint_builders = (
    (provider_aware_performance_checkpoint, "v1289_started", "v1289_transition_coherent"),
    (product_quality_judgment_checkpoint, "v1290_started", "v1290_transition_coherent"),
    (cognitive_coding_checkpoint, "v1291_started", "v1291_transition_coherent"),
    (independent_improvement_proposals_checkpoint, "v1292_started", "v1292_transition_coherent"),
    (value_risk_deliberation_checkpoint, "v1293_started", "v1293_transition_coherent"),
    (bounded_development_campaigns_checkpoint, "v1294_started", "v1294_transition_coherent"),
    (competing_candidate_evaluation_checkpoint, "v1295_started", "v1295_transition_coherent"),
    (comprehensive_verification_checkpoint, "v1296_started", "v1296_transition_coherent"),
    (supervised_autonomy_rehearsal_checkpoint, "v1300_started", "v1300_transition_coherent"),
)

for builder, started_key, transition_key in checkpoint_builders:
    report = builder(ROOT)
    require(report["ok"], f"{builder.__name__}_ready")
    require(report[started_key] is True, f"{builder.__name__}_successor_started")
    require(report["checks"][transition_key] is True, f"{builder.__name__}_transition_coherent")

require(tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1300, 9, 1), "working_version_retains_repair_lineage")
require(any(version == "1300.9.1" for version, _title in CHECKPOINT_HISTORY), "repair_version_retained_in_history")
historical_suite_inventory = {suite for stage in DEFAULT_STAGES for suite in stage.suites}
require(len(historical_suite_inventory) >= 40, "historical_suite_inventory_retained_in_segmented_verifier")
require(len(QUICK_STAGE_NAMES) <= 20, "quick_profile_is_bounded")
require("v1300.9.1-desktop-checkpoint-coherence-repair" in FULL_STAGE_NAMES, "repair_retained_in_full_profile")
require("runtime-status" not in QUICK_STAGE_NAMES, "duplicate_runtime_status_removed_from_active_quick")
require(any("runtime" in suite for suite in historical_suite_inventory), "runtime_coverage_retained_in_historical_inventory")
require(DEFAULT_SUITE_TIMEOUT_SECONDS == 240, "ordinary_suite_timeout_bounded")
require(
    SUITE_TIMEOUT_OVERRIDES.get("tools/v1252_9_persistent_state_performance_checkpoint_tests.py") == 600,
    "persistent_scale_suite_has_explicit_windows_budget",
)
require(DEFAULT_BUDGETS["warm_pre_provider_ms"]["median_max"] == 125.0, "ordinary_warm_latency_budget_preserved")
require(DEFAULT_BUDGETS["contention_warm_pre_provider_ms"]["median_max"] == 250.0, "contention_latency_budget_explicit")

retained = retained_checkpoint_progress(
    ROOT,
    checkpoint_version="1253.9",
    successor_version="1254.0",
    successor_surface="conscious_agent/isolated_coding_execution.py",
)
require(retained["checkpoint_retained"] is True, "v1253_checkpoint_retained")
require(retained["started"] is True and retained["coherent"] is True, "v1254_successor_state_coherent")

hermetic_runtime = (ROOT / "conscious_agent/hermetic_verification_runtime.py").read_text(encoding="utf-8")
segmented_runtime = (ROOT / "conscious_agent/segmented_release_verifier.py").read_text(encoding="utf-8")
dashboard_timing = (ROOT / "tools/v1251_6_8_dashboard_response_time_tests.py").read_text(encoding="utf-8")
require("_windows_kill_on_close_job" in hermetic_runtime, "windows_job_object_process_containment_present")
require('runtime_data / f"s{position + 1:02d}-{suite_index:02d}"' in segmented_runtime, "windows_suite_paths_bounded")
require('env["EIDOLON_V1252_BENCHMARK_PROFILE"] = "medium"' in segmented_runtime, "segmented_persistent_scale_profile_bounded")
require("encoding='utf-8'" in dashboard_timing and "deadline=time.time()+15" in dashboard_timing, "dashboard_timing_fixture_windows_safe")

required_markers = ("v1254.9", "v1255.9", "v1265.9", "v1270.9", "v1280.9", "v1290.9", "v1300.9")
for name in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md"):
    text = (ROOT / name).read_text(encoding="utf-8").split('<details id="retained-pre-v1250-compatibility">', 1)[0]
    require(all(marker in text for marker in required_markers), f"{name}_roadmap_lineage_visible")

require((ROOT / "archive/docs/legacy_dependencies/validation/Eidolon_v1300_9_1_DESKTOP_REPAIR_VALIDATION.md").is_file(), "desktop_repair_validation_present")

print(
    json.dumps(
        {
            "suite": "v1300.9.1-desktop-checkpoint-coherence-repair",
            "ok": True,
            "passed": len(checks),
            "failed": 0,
            "checks": checks,
            "provider_contacted": False,
            "project_mutation_authorized": False,
            "release_authorized": False,
        },
        indent=2,
        sort_keys=True,
    )
)
