from __future__ import annotations
from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from causal_diagnostic_reasoning_foundations import CONTRACT_VERSION as F,AUTHORITY_FLAGS
from causal_diagnostic_reasoning import CONTRACT_VERSION as I
from causal_diagnostic_reasoning_reliability import CONTRACT_VERSION as R,inspect_causal_diagnostic_health
CONTRACT_VERSION="v1281.9"
def build_causal_diagnostic_reasoning_checkpoint(*,source_root=None):
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();h=inspect_causal_diagnostic_health(source_root=root);tests=["tools/v1281_0_2_causal_diagnostic_reasoning_foundations_tests.py","tools/v1281_3_5_causal_diagnostic_reasoning_integration_tests.py","tools/v1281_6_8_causal_diagnostic_reasoning_reliability_tests.py","tools/v1281_9_causal_diagnostic_reasoning_checkpoint_tests.py"];checks={"foundations_contract_current":F=="v1281.2","integration_contract_current":I=="v1281.5","reliability_contract_current":R=="v1281.8","health_ready":h.get('ok') is True,"all_v1281_test_surfaces_present":all((root/x).is_file() for x in tests),"v1257_diagnostic_lineage_present":(root/'conscious_agent/diagnostic_repair_reasoning_foundations.py').is_file(),"v1280_reliability_lineage_present":(root/'conscious_agent/reliability_checkpoint_foundations.py').is_file()}
 return build_read_only_checkpoint_report(version="1281.9",status="causal_diagnostic_reasoning_checkpoint_ready",checks=checks,source_root=root,details={"next_bounded_unit":"v1282 Calibrated Uncertainty","v1282_started":False,"symptom_cause_distinction_present":True,"discriminating_falsification_probe_required":True,"single_supporting_probe_does_not_prove_root_cause":True,"checkpoint_executes_diagnostics":False,"checkpoint_executes_provider":False,"checkpoint_executes_tests":False,"checkpoint_mutates_source":False,**AUTHORITY_FLAGS})
__all__=["CONTRACT_VERSION","build_causal_diagnostic_reasoning_checkpoint"]
