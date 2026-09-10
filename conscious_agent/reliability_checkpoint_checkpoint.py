from __future__ import annotations
from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from reliability_checkpoint_foundations import CONTRACT_VERSION as F,AUTHORITY_FLAGS
from reliability_checkpoint import CONTRACT_VERSION as I
from reliability_checkpoint_reliability import CONTRACT_VERSION as R,inspect_reliability_checkpoint_health
CONTRACT_VERSION="v1280.9"
def build_reliability_checkpoint(*,source_root=None):
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();h=inspect_reliability_checkpoint_health(source_root=root);tests=["tools/v1280_0_2_reliability_checkpoint_foundations_tests.py","tools/v1280_3_5_reliability_checkpoint_integration_tests.py","tools/v1280_6_8_reliability_checkpoint_reliability_tests.py","tools/v1280_9_reliability_checkpoint_tests.py"]
 checks={"foundations_contract_current":F=="v1280.2","integration_contract_current":I=="v1280.5","reliability_contract_current":R=="v1280.8","health_ready":h.get("ok") is True,"all_v1280_test_surfaces_present":all((root/x).is_file() for x in tests),"v1279_operator_experience_retained":(root/'conscious_agent/operator_experience.py').is_file(),"v1278_security_retained":(root/'conscious_agent/security_privacy_hardening.py').is_file(),"v1273_ownership_retained":(root/'conscious_agent/ownership_concurrency_foundations.py').is_file(),"v1272_recovery_retained":(root/'conscious_agent/restart_crash_recovery.py').is_file()}
 return build_read_only_checkpoint_report(version="1280.9",status="reliability_checkpoint_ready",checks=checks,source_root=root,details={"next_bounded_unit":"v1281 Causal Diagnostic Reasoning","v1281_started":False,"repeated_campaign_evidence_model_present":True,"duplicate_provider_test_activity_must_be_zero":True,"unauthorized_action_count_must_be_zero":True,"stale_state_count_must_be_zero":True,"private_content_finding_count_must_be_zero":True,"native_windows_execution_claimed":False,"desktop_codex_native_windows_required":True,"checkpoint_executes_provider":False,"checkpoint_executes_commands":False,"checkpoint_executes_tests":False,"checkpoint_mutates_source":False,**AUTHORITY_FLAGS})
__all__=["CONTRACT_VERSION","build_reliability_checkpoint"]
