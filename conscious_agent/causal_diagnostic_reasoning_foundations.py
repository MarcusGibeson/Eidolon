from __future__ import annotations
"""v1281.0-v1281.2 causal diagnostic reasoning foundations."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION="v1281.2";SCHEMA_VERSION="1";MAX_HYPOTHESES=8;MAX_EVIDENCE=24
_SAFE=re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
AUTHORITY_FLAGS={"causal_reasoning_is_diagnostic_execution_authority":False,"causal_reasoning_is_provider_authority":False,"causal_reasoning_is_test_authority":False,"causal_reasoning_is_repair_authority":False,"causal_reasoning_is_update_authority":False,"causal_reasoning_is_application_authority":False,"causal_reasoning_is_release_authority":False,"generic_approval_is_authorization":False,"permanent_approval_granted":False,"independent_authority_granted":False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _code(v:Any,fallback="unknown"):
 t=str(v or "").strip().lower().replace(" ","_");t=re.sub(r"[^a-z0-9_.:-]+","_",t).strip("_")[:128];return t if t and _SAFE.fullmatch(t) else fallback
def build_causal_hypothesis(*,hypothesis_code:str,cause_class:str,symptom_codes:Sequence[str],supporting_evidence:Sequence[str]=(),contradicting_evidence:Sequence[str]=(),probe_code:str,expected_if_true:str,expected_if_false:str,confidence:str="medium")->dict[str,Any]:
 row={"hypothesis_code":_code(hypothesis_code),"cause_class":_code(cause_class),"symptom_codes":[_code(x) for x in list(symptom_codes)[:12]],"supporting_evidence":[_code(x) for x in list(supporting_evidence)[:MAX_EVIDENCE]],"contradicting_evidence":[_code(x) for x in list(contradicting_evidence)[:MAX_EVIDENCE]],"probe_code":_code(probe_code),"expected_if_true":_code(expected_if_true),"expected_if_false":_code(expected_if_false),"confidence":_code(confidence),"causal_status":"unresolved","root_cause_proven":False,"raw_output_required":False,**AUTHORITY_FLAGS};row["hypothesis_digest"]=_digest(row);return row
def build_causal_diagnostic_model(*,symptom_codes:Sequence[str],hypotheses:Sequence[Mapping[str,Any]],evidence_codes:Sequence[str]=())->dict[str,Any]:
 rows=[dict(x) for x in list(hypotheses)[:MAX_HYPOTHESES]];probe_groups={}
 for h in rows:probe_groups.setdefault(str(h.get("probe_code") or "unknown"),[]).append(h)
 discriminating=[]
 for probe,group in probe_groups.items():
  true={str(x.get("expected_if_true")) for x in group};false={str(x.get("expected_if_false")) for x in group};
  if len(group)>=2 and (len(true)>1 or len(false)>1 or true!=false):discriminating.append(probe)
 if not discriminating:
  # A probe is still useful if hypotheses predict opposite outcomes on the same probe.
  all_probes=sorted(probe_groups)
  for p in all_probes:
   preds={str(x.get("expected_if_true")) for x in probe_groups[p]};
   if len(preds)>1:discriminating.append(p)
 row={"ok":bool(rows),"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"causal_diagnostic_model_ready" if rows else "causal_diagnostic_model_blocked","symptom_codes":[_code(x) for x in list(symptom_codes)[:16]],"hypotheses":rows,"hypothesis_count":len(rows),"evidence_codes":[_code(x) for x in list(evidence_codes)[:MAX_EVIDENCE]],"discriminating_probe_codes":sorted(set(discriminating)),"selected_probe_code":sorted(set(discriminating))[0] if discriminating else "none","selected_probe_can_falsify_competing_explanation":bool(discriminating),"root_cause_proven":False,"content_minimized":True,"raw_test_output_stored":False,"raw_provider_output_stored":False,**AUTHORITY_FLAGS};row["model_digest"]=_digest(row);return row
def validate_causal_diagnostic_model(row:Mapping[str,Any])->dict[str,Any]:
 digest_ok=row.get("model_digest")==_digest({k:v for k,v in row.items() if k!="model_digest"});auth_ok=all(row.get(k) is v for k,v in AUTHORITY_FLAGS.items());h=list(row.get("hypotheses") or []);hyp_ok=bool(h) and len(h)<=MAX_HYPOTHESES and all(x.get("root_cause_proven") is False and x.get("raw_output_required") is False for x in h);privacy=row.get("content_minimized") is True and row.get("raw_test_output_stored") is False and row.get("raw_provider_output_stored") is False;probe_ok=(row.get("selected_probe_code")!="none")==bool(row.get("selected_probe_can_falsify_competing_explanation"));ok=digest_ok and auth_ok and hyp_ok and privacy and probe_ok
 return {"ok":ok,"status":"causal_diagnostic_model_valid" if ok else "causal_diagnostic_model_invalid","digest_valid":digest_ok,"authority_contained":auth_ok,"hypotheses_valid":hyp_ok,"privacy_contained":privacy,"probe_semantics_valid":probe_ok}
def apply_probe_outcome(model:Mapping[str,Any],*,probe_code:str,observed_outcome:str,evidence_code:str)->dict[str,Any]:
 if not validate_causal_diagnostic_model(model).get("ok"):raise ValueError("valid_causal_diagnostic_model_required")
 probe=_code(probe_code);outcome=_code(observed_outcome);rows=[]
 for original in model.get("hypotheses") or []:
  h=dict(original);support=list(h.get("supporting_evidence") or []);contra=list(h.get("contradicting_evidence") or [])
  if h.get("probe_code")==probe:
   competing_predictions={str(x.get("expected_if_true")) for x in model.get("hypotheses") or [] if x.get("probe_code")==probe}
   if outcome==h.get("expected_if_true"):support.append(_code(evidence_code));h["causal_status"]="supported"
   elif outcome==h.get("expected_if_false") or (outcome in competing_predictions and outcome!=h.get("expected_if_true")):
    contra.append(_code(evidence_code));h["causal_status"]="falsified"
   else:h["causal_status"]="unresolved"
  h["supporting_evidence"]=support[:MAX_EVIDENCE];h["contradicting_evidence"]=contra[:MAX_EVIDENCE];h["root_cause_proven"]=False;h["hypothesis_digest"]=_digest({k:v for k,v in h.items() if k!="hypothesis_digest"});rows.append(h)
 evidence=list(model.get("evidence_codes") or [])+[_code(evidence_code)];updated=build_causal_diagnostic_model(symptom_codes=model.get("symptom_codes") or [],hypotheses=rows,evidence_codes=evidence);updated["last_probe_code"]=probe;updated["last_observed_outcome"]=outcome;updated["root_cause_proven"]=False;updated["model_digest"]=_digest({k:v for k,v in updated.items() if k!="model_digest"});return updated
__all__=["CONTRACT_VERSION","AUTHORITY_FLAGS","build_causal_hypothesis","build_causal_diagnostic_model","validate_causal_diagnostic_model","apply_probe_outcome"]
