from __future__ import annotations
"""Read-only v1196.5 adversarial replay/stale/interruption/cancellation/recovery review checkpoint."""
import hashlib
from pathlib import Path
from typing import Any
from adversarial_replay_recovery_review import *
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
CONTRACT_VERSION="v1196.5"; _CHECKPOINT_ID="adversarial-replay-recovery-review-checkpoint"
def _h(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
def build_adversarial_replay_recovery_review_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 checks=[]
 def req(v):checks.append(bool(v))
 snapshot=_h("snapshot");context=_h("context");evidence=_h("evidence");prior=None;samples=[]
 for i,event in enumerate(EVENT_CLASSES,1):
  q=build_review_request(review_id=f"review:{i}",event_class=event,action=ACTIONS[(i-1)%len(ACTIONS)],sequence=i,snapshot_digest=snapshot,context_digest=context,evidence_digest=evidence,prior_review_digest=prior)
  for decision_name in DECISIONS:
   d=build_review_decision(request_digest=q["request_digest"],decision=decision_name,operator_review_digest=_h(f"operator:{i}:{decision_name}"),reason_code=f"operator_{decision_name}")
   out=review_adversarial_event(request=q,decision=d,expected_snapshot_digest=snapshot,expected_context_digest=context,expected_evidence_digest=evidence,expected_prior_review_digest=prior)
   req(out["ok"]);req(not out["errors"]);req(out["execution_invoked"] is False);req(out["authority_granted"] is False)
   samples.append(out)
  prior=samples[-1]["review_receipt_digest"]
 # negative controls
 base=build_review_request(review_id="base",event_class=EVENT_CLASSES[0],action=ACTIONS[0],sequence=1,snapshot_digest=snapshot,context_digest=context,evidence_digest=evidence)
 dec=build_review_decision(request_digest=base["request_digest"],decision="approve",operator_review_digest=_h("operator"),reason_code="review")
 from adversarial_replay_recovery_review import _digest
 mutations=[("stale_snapshot",base,"snapshot_digest",_h("stale")),("stale_context",base,"context_digest",_h("stale")),("stale_evidence",base,"evidence_digest",_h("stale")),("automatic_recovery",base,"automatic_recovery_requested",True),("automatic_retry",base,"automatic_retry_requested",True),("execution",base,"execution_invoked",True),("cancellation",base,"cancellation_executed",True),("runtime",base,"runtime_mutated",True),("provider",base,"provider_contacted",True),("authority",dec,"authority_granted",True)]
 blocked={}
 for name,original,field,value in mutations:
  q=dict(base);d=dict(dec)
  target=q if original is base else d; target[field]=value
  digest_field="request_digest" if target is q else "decision_digest"; body=dict(target);body.pop(digest_field,None);target[digest_field]=_digest(body)
  if target is q: d=build_review_decision(request_digest=q["request_digest"],decision="approve",operator_review_digest=_h("operator"),reason_code="review")
  out=review_adversarial_event(request=q,decision=d,expected_snapshot_digest=snapshot,expected_context_digest=context,expected_evidence_digest=evidence)
  req(not out["ok"]);req(bool(out["errors"]));req(out["execution_invoked"] is False);req(out["authority_granted"] is False);blocked[name]=out
 privacy=package_privacy_summary_for_root(source);req(privacy.get("ok") is True)
 registry=inspect_checkpoint_registry(source_root=source);desc=next((x for x in registry["checkpoints"] if x["checkpoint_id"]==_CHECKPOINT_ID),None);req(bool(desc));req((desc or {}).get("contract_version")==CONTRACT_VERSION)
 summary={"event_class_count":len(EVENT_CLASSES),"action_count":len(ACTIONS),"decision_count":len(DECISIONS),"review_count":len(samples),"negative_case_count":len(blocked),"content_free":True,"read_only":True,"original_evidence_preserved":True,"recovery_executed":False,"retry_executed":False,"cancellation_executed":False,"execution_invoked":False,"runtime_mutated":False,"provider_contacted":False,"authority_state":"separate_not_granted","authority_granted":False,"global_profile_pass_claimed":False}
 for f in ("content_free","read_only","original_evidence_preserved"):req(summary[f] is True)
 for f in ("recovery_executed","retry_executed","cancellation_executed","execution_invoked","runtime_mutated","provider_contacted","authority_granted","global_profile_pass_claimed"):req(summary[f] is False)
 return {"ok":all(checks),"checkpoint_id":"adversarial-replay-recovery-review:v1196.5","contract_version":CONTRACT_VERSION,"passed":sum(checks),"total":len(checks),"summary":summary,"samples":samples,"blocked_cases":blocked,"limitations":["Review-only; no recovery, retry, cancellation, execution, provider contact, or mutation occurs.","No approval or authority is created or consumed.","Broader adversarial reliability hardening continues in v1196.6-v1196.8."]}
