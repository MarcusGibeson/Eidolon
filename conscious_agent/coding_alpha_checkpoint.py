from __future__ import annotations

"""v1260.9 read-only Coding Alpha checkpoint."""
from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from coding_alpha_checkpoint_foundations import DENIED_AUTHORITY, build_coding_alpha_contract
from coding_alpha_reliability import inspect_coding_alpha_health

CONTRACT_VERSION="v1260.9"

def build_coding_alpha_checkpoint(*,source_root:str|Path|None=None)->dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    contract=build_coding_alpha_contract(); health=inspect_coding_alpha_health(source_root=root)
    checks={
      "canonical_campaign_contract_ready":contract.get("ok") is True,
      "all_integration_surfaces_present":health.get("ok") is True,
      "calculator_scenario_exact":contract.get("scenario_id")=="calculator_webpage_supervised_end_to_end",
      "repair_required":contract.get("mandatory_failure_repair_evidence") is True,
      "restart_required":bool(contract.get("restart_required_between")),
      "project_immutable_until_apply":contract.get("selected_project_must_remain_unchanged_until_application") is True,
      "separate_apply_rollback_authority":contract.get("application_and_rollback_require_distinct_exact_authorizations") is True,
      "rollback_exact_restoration_required":contract.get("rollback_must_restore_pre_apply_tree_digest") is True,
      "generic_authority_denied":contract.get("generic_authorization_must_never_be_consumed") is True,
    }
    details={"scenario_id":contract.get("scenario_id"),"stage_count":contract.get("stage_count"),"behavioral_evidence":[
                "tools/v1260_0_2_coding_alpha_foundations_tests.py","tools/v1260_3_5_coding_alpha_campaign_tests.py","tools/v1260_6_8_coding_alpha_reliability_tests.py"],
                "native_windows_multi_process_validation":"desktop_review_required","next_bounded_unit":"v1261 Evidence-Based Project Inspection",
                "provider_contacted":False,"commands_executed":False,"tests_executed":False,**DENIED_AUTHORITY}
    return build_read_only_checkpoint_report(version="1260.9",status="coding_alpha_checkpoint_ready",checks=checks,details=details,source_root=root)

__all__=["CONTRACT_VERSION","build_coding_alpha_checkpoint"]
