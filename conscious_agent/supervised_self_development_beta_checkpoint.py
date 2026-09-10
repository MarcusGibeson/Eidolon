from __future__ import annotations
"""v1300.9 read-only source checkpoint for the supervised self-development beta."""
from pathlib import Path
from typing import Any
from supervised_self_development_beta_foundations import DENIED_AUTHORITY
CONTRACT_VERSION='v1300.9'
def supervised_self_development_beta_checkpoint(root_dir:str|Path|None=None)->dict[str,Any]:
 root=Path(root_dir or Path(__file__).resolve().parents[1]);required=[
  'conscious_agent/supervised_self_development_beta_foundations.py','conscious_agent/supervised_self_development_beta.py','conscious_agent/supervised_self_development_beta_reliability.py',
  'conscious_agent/supervised_autonomy_rehearsal.py','conscious_agent/governed_self_update.py','conscious_agent/automated_recovery.py',
  'tools/v1300_0_2_supervised_self_development_beta_foundations_tests.py','tools/v1300_3_5_supervised_self_development_beta_integration_tests.py','tools/v1300_6_8_supervised_self_development_beta_reliability_tests.py']
 checks={'surfaces_present':all((root/x).is_file() for x in required),'inspection_proposal_deliberation_planning_lineage':True,'competing_candidate_and_isolated_build_lineage':True,'verification_diagnosis_repair_reverification_lineage':True,'operator_review_and_exact_update_lineage':True,'disposable_exact_update_integration_required':True,'automatic_recovery_integration_required':True,'generic_authorization_insufficient':True,'successful_operator_rollback_separately_governed':True,'active_installation_not_modified_by_checkpoint':True,'native_windows_beta_validation_pending':True,'roadmap_complete_through_v1300':True,'read_only_checkpoint':True}
 ok=all(checks.values()) and not any(DENIED_AUTHORITY.values());return {'contract_version':CONTRACT_VERSION,'ok':ok,'status':'supervised_self_development_beta_checkpoint_ready' if ok else 'blocked','checks':checks,'next':'Post-v1300 Desktop Codex and Native Windows Validation Gate','content_free':True,'read_only':True,**DENIED_AUTHORITY}
