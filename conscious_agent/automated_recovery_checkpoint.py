from __future__ import annotations
"""v1297.9 read-only Automated Recovery checkpoint."""
from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from automated_recovery_foundations import DENIED_AUTHORITY
from automated_recovery_reliability import inspect_automated_recovery_surface_health
CONTRACT_VERSION='v1297.9'
def build_automated_recovery_checkpoint(*,source_root:str|Path|None=None):
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();h=inspect_automated_recovery_surface_health(source_root=root);checks={'foundations_present':(root/'conscious_agent/automated_recovery_foundations.py').is_file(),'integration_present':(root/'conscious_agent/automated_recovery.py').is_file(),'reliability_present':(root/'conscious_agent/automated_recovery_reliability.py').is_file(),'v1269_update_retained':(root/'conscious_agent/governed_self_update.py').is_file(),'v1296_canary_retained':(root/'conscious_agent/canary_self_updates.py').is_file(),'surface_health':h.get('ok') is True};details={'behavioral_evidence':['tools/v1297_0_2_automated_recovery_foundations_tests.py','tools/v1297_3_5_automated_recovery_integration_tests.py','tools/v1297_6_8_automated_recovery_reliability_tests.py'],'contract':['consumed_v1269_update_only','defined_post_update_failure_only','bounded_observation_window','exact_pre_update_backup_only','candidate_state_only','separate_operator_rollback_preserved'],'checkpoint_executes_recovery':False,'checkpoint_mutates_source':False,'next_bounded_unit':'v1298 Repeated Self-Maintenance Cycles','native_windows_validation':'desktop_review_required',**DENIED_AUTHORITY};return build_read_only_checkpoint_report(version='1297.9',status='automated_recovery_checkpoint_ready',checks=checks,details=details,source_root=root)
