from __future__ import annotations
"""v1281.3-v1281.5 bridge from v1257 diagnostics to causal falsification models."""
from typing import Any,Mapping,Sequence
from causal_diagnostic_reasoning_foundations import *
CONTRACT_VERSION="v1281.5"
def causal_model_from_v1257(observation:Mapping[str,Any],hypotheses:Sequence[Mapping[str,Any]])->dict[str,Any]:
 symptoms=[str(observation.get("verification_status") or "verification_failed")]+[f"phase_{x}" for x in observation.get("failed_phase_classes") or []]+[f"exit_{x}" for x in observation.get("failed_exit_classes") or []]
 rows=[]
 # Convert each prior hypothesis to a falsifiable causal candidate. If multiple hypotheses use different probes,
 # add a common discriminator from cause class so the model can compare them without executing anything.
 for i,h in enumerate(list(hypotheses)[:8]):
  cause=str(h.get("cause_class") or "unknown");code=str(h.get("hypothesis_code") or f"hypothesis_{i}");basis=[str(x) for x in h.get("evidence_basis") or []];disproof=str(h.get("disproof_test") or "focused_disproof_probe")
  # Existing v1257 disproof descriptions become content-free probe codes. Expected outcomes are cause-class specific.
  probe="cause_class_discriminator" if len(hypotheses)>1 else disproof
  rows.append(build_causal_hypothesis(hypothesis_code=code,cause_class=cause,symptom_codes=symptoms,supporting_evidence=basis,probe_code=probe,expected_if_true=f"supports_{cause}",expected_if_false=f"contradicts_{cause}",confidence=str(h.get("confidence") or "medium")))
 return build_causal_diagnostic_model(symptom_codes=symptoms,hypotheses=rows,evidence_codes=["v1257_failure_observation"])
def choose_discriminating_diagnostic(model:Mapping[str,Any])->dict[str,Any]:
 if not validate_causal_diagnostic_model(model).get("ok"):return {"ok":False,"status":"causal_model_invalid",**AUTHORITY_FLAGS}
 probe=str(model.get("selected_probe_code") or "none");return {"ok":probe!="none","status":"discriminating_diagnostic_selected" if probe!="none" else "no_discriminating_diagnostic_available","probe_code":probe,"can_falsify_competing_explanation":probe!="none","diagnostic_executed":False,"provider_contacted":False,"tests_executed":False,"root_cause_proven":False,**AUTHORITY_FLAGS}
def causal_diagnostic_public_summary(model:Mapping[str,Any])->dict[str,Any]:
 valid=validate_causal_diagnostic_model(model);rows=[{"hypothesis_code":x.get("hypothesis_code"),"cause_class":x.get("cause_class"),"confidence":x.get("confidence"),"causal_status":x.get("causal_status"),"probe_code":x.get("probe_code")} for x in model.get("hypotheses") or []]
 return {"ok":valid.get("ok"),"status":"causal_diagnostic_summary_ready" if valid.get("ok") else "causal_diagnostic_summary_blocked","symptom_codes":list(model.get("symptom_codes") or []),"hypotheses":rows,"selected_probe_code":model.get("selected_probe_code"),"root_cause_proven":False,"content_minimized":True,**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","causal_model_from_v1257","choose_discriminating_diagnostic","causal_diagnostic_public_summary"]
