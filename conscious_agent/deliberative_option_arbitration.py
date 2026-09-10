from __future__ import annotations
"""Deterministic comparison of bounded deliberative options."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from deliberative_option_records import DeliberativeOptionStore
CONTRACT_VERSION="v1114.1"
OUTCOMES={"preferred","viable_alternative","deferred","blocked","dominated","incomparable","requires_more_evidence","requires_operator_review","deliberate_no_choice"}
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"comparisons":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"minimum_preferred_score":0.58,"minimum_viable_score":0.42,"max_preferred_risk":0.65,"max_preferred_uncertainty":0.70,"high_resource_cost":0.80},"authority_boundary":{"can_create_decision_commitment":False,"can_form_intention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False,"can_browse":False,"can_contact_provider":False}}
class DeliberativeOptionArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"deliberative_option_arbitration.json";self.clock=clock or _now;self.options=DeliberativeOptionStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def compare(self,event_id:str,*,option_ids:list[str],objective_alignment:dict[str,float]|None=None,evidence_quality:dict[str,float]|None=None,information_gain:dict[str,float]|None=None,conflict_penalty:dict[str,float]|None=None,operator_review_required:bool=False,missing_evidence:bool=False,force_incomparable:bool=False):
  event_id=_clean(event_id,180); ids=list(dict.fromkeys(_clean(x,220) for x in option_ids if _clean(x,220)))
  if not event_id or not ids:raise ValueError("event_id and option_ids required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   rows=[x for x in self.options.snapshot()["records"] if x.get("option_id") in ids and x.get("state")=="candidate"]
   if len(rows)!=len(ids):result={"status":"comparison_rejected","reason":"candidate_options_required","comparison_id":"","outcomes":{}}
   else:
    align=objective_alignment or {}; evidence=evidence_quality or {}; gain=information_gain or {}; conflict=conflict_penalty or {}; scored=[]
    for row in rows:
     oid=row["option_id"]; a=max(0,min(float(align.get(oid,.5)),1)); e=max(0,min(float(evidence.get(oid,.5)),1)); g=max(0,min(float(gain.get(oid,.5)),1)); c=max(0,min(float(conflict.get(oid,0)),1)); risk=float(row["risk_score"]); cost=float(row["resource_cost"]); uncertainty=float(row["uncertainty"]); reversible=float(row["reversibility"]); benefit=float(row["benefit_score"])
     score=round(.24*a+.20*e+.18*benefit+.10*g+.10*reversible-.08*risk-.06*cost-.08*uncertainty-.10*c,4); scored.append((score,oid,row))
    scored.sort(key=lambda x:(-x[0],x[1])); best=scored[0]; outcomes={}; reason="bounded_comparison"
    if operator_review_required: outcomes={oid:"requires_operator_review" for _,oid,_ in scored};reason="operator_constraint"
    elif missing_evidence: outcomes={oid:"requires_more_evidence" for _,oid,_ in scored};reason="missing_evidence_unknown"
    elif force_incomparable or (len(scored)>1 and abs(scored[0][0]-scored[1][0])<.02): outcomes={oid:"incomparable" for _,oid,_ in scored};reason="materially_incomparable"
    elif best[0] < s["controls"]["minimum_viable_score"]: outcomes={oid:"deliberate_no_choice" for _,oid,_ in scored};reason="no_viable_option"
    else:
     for score,oid,row in scored:
      if float(row["risk_score"])>.90:outcomes[oid]="blocked"
      elif oid==best[1] and score>=s["controls"]["minimum_preferred_score"] and float(row["risk_score"])<=s["controls"]["max_preferred_risk"] and float(row["uncertainty"])<=s["controls"]["max_preferred_uncertainty"]:outcomes[oid]="preferred"
      elif score>=s["controls"]["minimum_viable_score"]:outcomes[oid]="viable_alternative"
      else:outcomes[oid]="dominated"
     if "preferred" not in outcomes.values(): outcomes={oid:("deferred" if state=="viable_alternative" else state) for oid,state in outcomes.items()};reason="viable_but_not_preferred"
    now=self.clock();cid=f"option-comparison-{_digest(event_id,*ids)[:24]}"
    for oid,outcome in outcomes.items():self.options.apply_comparison(oid,comparison_id=cid,outcome=outcome)
    result={"status":"comparison_completed","comparison_id":cid,"outcomes":outcomes,"scores":{oid:score for score,oid,_ in scored},"reason":reason,"causation_claimed":False,"decision_id":"","intention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""};s["comparisons"]=(s["comparisons"]+[{**result,"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}])[-512:]
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for row in s["comparisons"]:
   for out in row.get("outcomes",{}).values():counts[out]=counts.get(out,0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"comparison_count":len(s["comparisons"]),"outcome_counts":counts,"recent_comparisons":[{k:x.get(k) for k in ("comparison_id","outcomes","scores","reason","causation_claimed","decision_id","intention_id","proposal_id","approval_id","authorization_id","action_id")} for x in s["comparisons"][-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_deliberative_option_arbitration_inspection(runtime_root=None):return DeliberativeOptionArbitrator(runtime_root).inspection_summary()
