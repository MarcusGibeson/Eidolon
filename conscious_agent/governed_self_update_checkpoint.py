from __future__ import annotations
"""v1269.9 read-only Governed Self-Update checkpoint."""
from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from governed_self_update_foundations import DENIED_AUTHORITY
from governed_self_update_reliability import inspect_governed_self_update_surface_health
CONTRACT_VERSION="v1269.9"
def build_governed_self_update_checkpoint(*,source_root:str|Path|None=None)->dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();health=inspect_governed_self_update_surface_health(source_root=root)
    checks={"foundations_present":(root/'conscious_agent/governed_self_update_foundations.py').is_file(),"integration_present":(root/'conscious_agent/governed_self_update.py').is_file(),"reliability_present":(root/'conscious_agent/governed_self_update_reliability.py').is_file(),"v1268_review_retained":(root/'conscious_agent/operator_review_handoff.py').is_file(),"health_checks_pass":health.get('ok') is True}
    details={"behavioral_evidence":["tools/v1269_0_2_governed_self_update_foundations_tests.py","tools/v1269_3_5_governed_self_update_integration_tests.py","tools/v1269_6_8_governed_self_update_reliability_tests.py"],"contract":["fresh_v1268_handoff","exact_one_time_update_authorization","backup_before_write","reviewed_paths_only","restart_health_verification","automatic_failure_rollback","separate_success_rollback_authorization"],"checkpoint_executes_update":False,"checkpoint_restarts_process":False,"checkpoint_mutates_source":False,"next_bounded_unit":"v1270 Self-Development Alpha Checkpoint","native_windows_validation":"desktop_review_required",**DENIED_AUTHORITY}
    return build_read_only_checkpoint_report(version='1269.9',status='governed_self_update_checkpoint_ready',checks=checks,details=details,source_root=root)
__all__=["build_governed_self_update_checkpoint"]
