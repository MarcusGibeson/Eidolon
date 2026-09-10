from __future__ import annotations
"""v1271.9 read-only Long-Running Work Sessions checkpoint."""
from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from long_running_work_sessions_foundations import AUTHORITY_FLAGS
from long_running_work_sessions_reliability import inspect_long_running_work_sessions_health
CONTRACT_VERSION="v1271.9"

def build_long_running_work_sessions_checkpoint(*, source_root: str|Path|None=None) -> dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();health=inspect_long_running_work_sessions_health(source_root=root)
    checks={"foundations_present":(root/'conscious_agent/long_running_work_sessions_foundations.py').is_file(),"integration_present":(root/'conscious_agent/long_running_work_sessions.py').is_file(),"reliability_present":(root/'conscious_agent/long_running_work_sessions_reliability.py').is_file(),"v1270_campaign_integration_retained":(root/'conscious_agent/self_development_alpha.py').is_file(),"checkpoint_is_read_only":True,"health_checks_pass":health.get('ok') is True}
    details={"behavioral_evidence":["tools/v1271_0_2_long_running_work_sessions_foundations_tests.py","tools/v1271_3_5_long_running_work_sessions_integration_tests.py","tools/v1271_6_8_long_running_work_sessions_reliability_tests.py"],"contract":["durable_campaign_checkpoints","bounded_summaries","phase_timing_receipts","pause_interrupt_cancel_resume","attempted_not_completed_distinction","no_duplicate_stage_activity_after_resume","bounded_heartbeat_lease","operator_current_phase_next_authorization","verification_budget_split_not_global_timeout_increase"],"v1270_harness_duration_finding_preserved":True,"checkpoint_executes_provider":False,"checkpoint_executes_tests":False,"checkpoint_mutates_source":False,"checkpoint_resumes_work":False,"next_bounded_unit":"v1272 Restart and Crash Recovery","native_windows_validation":"desktop_review_required",**AUTHORITY_FLAGS}
    return build_read_only_checkpoint_report(version="1271.9",status="long_running_work_sessions_checkpoint_ready",checks=checks,details=details,source_root=root)

__all__=["build_long_running_work_sessions_checkpoint"]
