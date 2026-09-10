from __future__ import annotations
from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from calibrated_uncertainty_foundations import CONTRACT_VERSION as F,AUTHORITY_FLAGS
from calibrated_uncertainty import CONTRACT_VERSION as I
from calibrated_uncertainty_reliability import CONTRACT_VERSION as R,inspect_calibrated_uncertainty_health
CONTRACT_VERSION="v1282.9"
def build_calibrated_uncertainty_checkpoint(*,source_root=None):
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();h=inspect_calibrated_uncertainty_health(source_root=root);tests=["tools/v1282_0_2_calibrated_uncertainty_foundations_tests.py","tools/v1282_3_5_calibrated_uncertainty_integration_tests.py","tools/v1282_6_8_calibrated_uncertainty_reliability_tests.py","tools/v1282_9_calibrated_uncertainty_checkpoint_tests.py"];checks={"foundations_contract_current":F=="v1282.2","integration_contract_current":I=="v1282.5","reliability_contract_current":R=="v1282.8","health_ready":h.get('ok') is True,"all_v1282_test_surfaces_present":all((root/x).is_file() for x in tests),"v1281_causal_lineage_present":(root/'conscious_agent/causal_diagnostic_reasoning_foundations.py').is_file(),"v1274_environment_lineage_present":(root/'conscious_agent/environment_awareness_foundations.py').is_file()}
 return build_read_only_checkpoint_report(version="1282.9",status="calibrated_uncertainty_checkpoint_ready",checks=checks,source_root=root,details={"next_bounded_unit":"v1283 Development Memory Relevance","v1283_started":False,"epistemic_states_preserved":True,"confidence_changes_with_evidence":True,"assumption_confidence_capped":True,"unknown_not_treated_as_false":True,"duplicate_evidence_does_not_double_count":True,"checkpoint_executes_provider":False,"checkpoint_executes_tests":False,"checkpoint_mutates_source":False,**AUTHORITY_FLAGS})
__all__=["CONTRACT_VERSION","build_calibrated_uncertainty_checkpoint"]
