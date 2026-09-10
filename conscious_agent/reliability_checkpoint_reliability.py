from __future__ import annotations
"""v1280.6-v1280.8 reliability-checkpoint hardening and native handoff."""
from pathlib import Path
from typing import Any
from reliability_checkpoint_foundations import AUTHORITY_FLAGS,REQUIRED_SCENARIOS
CONTRACT_VERSION="v1280.8"
def inspect_reliability_checkpoint_health(*,source_root:str|Path|None=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();required=["reliability_checkpoint_foundations.py","reliability_checkpoint.py","operator_experience.py","restart_crash_recovery.py","ownership_concurrency_foundations.py","development_observability.py","security_privacy_hardening.py"]
 checks={f"module_{x[:-3]}":(root/'conscious_agent'/x).is_file() for x in required};checks.update({"six_required_scenarios":len(REQUIRED_SCENARIOS)==6,"operator_dashboard_present":(root/'conscious_agent/dashboard_operator_experience_panel.py').is_file(),"source_package_writer_present":(root/'conscious_agent/dependency_packaging_reliability.py').is_file()})
 return {"ok":all(checks.values()),"status":"reliability_checkpoint_health_ready" if all(checks.values()) else "reliability_checkpoint_health_blocked","checks":checks,"read_only":True,"active_source_modified":False,**AUTHORITY_FLAGS}
def build_reliability_checkpoint_handoff(*,source_root:str|Path|None=None)->dict[str,Any]:
 h=inspect_reliability_checkpoint_health(source_root=source_root);return {"ok":h["ok"],"contract_version":CONTRACT_VERSION,"status":"reliability_checkpoint_handoff_ready" if h["ok"] else "reliability_checkpoint_handoff_blocked","next_bounded_unit":"v1281 Causal Diagnostic Reasoning","v1281_started":False,"native_windows_review":["repeat_full_campaigns","force_kill_between_stage_and_receipt","provider_outage_return","expired_owner_transfer","dashboard_process_restart","multi_tab_controls","locked_runtime_records","long_paths","private_data_scan_after_each_campaign"],"native_windows_execution_claimed":False,**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","inspect_reliability_checkpoint_health","build_reliability_checkpoint_handoff"]
