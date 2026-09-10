from __future__ import annotations
from pathlib import Path
from typing import Any,Mapping
from calibrated_uncertainty_foundations import AUTHORITY_FLAGS,validate_uncertainty_claim
CONTRACT_VERSION="v1282.8"
def compare_uncertainty_claims(before:Mapping[str,Any],after:Mapping[str,Any])->dict[str,Any]:
 vb=validate_uncertainty_claim(before);va=validate_uncertainty_claim(after);delta=int(after.get("confidence") or 0)-int(before.get("confidence") or 0);return {"ok":vb.get("ok") and va.get("ok"),"status":"uncertainty_revision_ready","confidence_delta":delta,"state_changed":before.get("epistemic_state")!=after.get("epistemic_state"),"confidence_changed":delta!=0,"evidence_changed":before.get("evidence_codes")!=after.get("evidence_codes") or before.get("contradiction_codes")!=after.get("contradiction_codes"),"authority_changed":False,**AUTHORITY_FLAGS}
def inspect_calibrated_uncertainty_health(*,source_root:str|Path|None=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();checks={"foundations_present":(root/'conscious_agent/calibrated_uncertainty_foundations.py').is_file(),"integration_present":(root/'conscious_agent/calibrated_uncertainty.py').is_file(),"v1281_causal_lineage_present":(root/'conscious_agent/causal_diagnostic_reasoning_foundations.py').is_file(),"v1274_environment_lineage_present":(root/'conscious_agent/environment_awareness_foundations.py').is_file()};return {"ok":all(checks.values()),"status":"calibrated_uncertainty_health_ready" if all(checks.values()) else "calibrated_uncertainty_health_blocked","checks":checks,"read_only":True,**AUTHORITY_FLAGS}
def build_calibrated_uncertainty_handoff(*,source_root:str|Path|None=None)->dict[str,Any]:
 h=inspect_calibrated_uncertainty_health(source_root=source_root);return {"ok":h['ok'],"contract_version":CONTRACT_VERSION,"status":"calibrated_uncertainty_handoff_ready" if h['ok'] else "calibrated_uncertainty_handoff_blocked","next_bounded_unit":"v1283 Development Memory Relevance","v1283_started":False,"native_windows_review":["stale_environment_fact_confidence_drop","contradictory_runtime_evidence","restart_preserves_calibration","duplicate_evidence_no_double_count","unknown_not_false"],**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","compare_uncertainty_claims","inspect_calibrated_uncertainty_health","build_calibrated_uncertainty_handoff"]
