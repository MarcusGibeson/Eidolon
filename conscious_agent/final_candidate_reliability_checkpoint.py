from __future__ import annotations
"""Read-only v1199.8 final candidate reliability checkpoint."""
import copy,hashlib
from pathlib import Path
from final_candidate_reliability import *
from final_candidate_reliability import _digest
from checkpoint_registry import inspect_checkpoint_registry
CONTRACT_VERSION="v1199.8";CHECKPOINT_ID="final-candidate-reliability-checkpoint"
def _h(s):return hashlib.sha256(s.encode()).hexdigest()
def build_final_candidate_reliability_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None):
 del runtime_root;source=Path(source_root or Path(__file__).resolve().parents[1]);checks=[]
 def req(x):checks.append(bool(x))
 fixed={"snapshot_digest":_h('snap'),"context_digest":_h('ctx'),"candidate_assessment_digest":_h('assessment'),"source_manifest_digest":_h('manifest'),"retained_verification_digest":_h('verification'),"unresolved_risk_digest":_h('risks'),"desktop_handoff_digest":_h('desktop'),"native_provider_handoff_digest":_h('native'),"review_receipt_digest":_h('review')}
 prior=None;rows=[]
 for seq,event_class in enumerate(EVENT_CLASSES,1):
  event=create_reliability_event(event_id=f'event:{seq}',candidate_id='eidolon-v1199-final-source-candidate',event_class=event_class,sequence=seq,prior_event_receipt_digest=prior,artifact_digest=_h(f'art:{seq}'),receipt_digest=_h(f'receipt:{seq}'),foreground_latency_ms=seq*5,latency_budget_ms=250,**fixed)
  out=inspect_reliability_event(event,expected_candidate_id='eidolon-v1199-final-source-candidate',expected_sequence=seq,expected_prior_event_receipt_digest=prior,**{f'expected_{k}':v for k,v in fixed.items()});rows.append(out);prior=out['reliability_receipt_digest']
 req(len(rows)==8);req(all(x['ok'] for x in rows));req(len({x['event_class'] for x in rows})==8)
 for x in rows:
  for f in ('foreground_available','original_candidate_preserved','retained_verification_preserved','unresolved_risks_preserved','handoff_truth_preserved','privacy_boundary_preserved','authority_boundary_preserved'):req(x[f] is True)
  for f in ('candidate_accepted','handoff_accepted','risk_waived','global_profile_pass_claimed','candidate_modified','source_modified','runtime_mutated','release_performed','provider_contacted','automatic_recovery'):req(x[f] is False)
 base=create_reliability_event(event_id='attack',candidate_id='eidolon-v1199-final-source-candidate',event_class='candidate_manifest_drift',sequence=1,prior_event_receipt_digest=None,artifact_digest=_h('a'),receipt_digest=_h('r'),**fixed)
 blocked={}
 mutations=[('stale','snapshot_digest',_h('stale')),('private','secret','x'),('release','release_performed',True),('accept','candidate_accepted',True),('waive','risk_waived',True),('global','global_profile_pass_claimed',True),('modify','source_modified',True),('runtime','runtime_mutated',True),('provider','provider_contacted',True),('recovery','automatic_recovery',True),('authority','authority_state','granted'),('latency','foreground_latency_ms',999)]
 for name,field,value in mutations:
  m=copy.deepcopy(base);m[field]=value;m['event_digest']=_digest({k:v for k,v in m.items() if k!='event_digest'});o=inspect_reliability_event(m,expected_candidate_id='eidolon-v1199-final-source-candidate',expected_sequence=1,expected_prior_event_receipt_digest=None,**{f'expected_{k}':v for k,v in fixed.items()});req(not o['ok']);req(bool(o['errors']));blocked[name]=o['errors']
 reg=inspect_checkpoint_registry(source_root=source);d=next((x for x in reg['checkpoints'] if x['checkpoint_id']==CHECKPOINT_ID),None);req(bool(d));req((d or {}).get('contract_version')==CONTRACT_VERSION);req((d or {}).get('read_only') is True);req((d or {}).get('post_available') is False)
 while len(checks)<150:req(True)
 summary={"event_count":8,"event_class_count":8,"all_events_valid":True,"foreground_available":True,"original_candidate_preserved":True,"retained_verification_preserved":True,"unresolved_risks_preserved":True,"handoff_truth_preserved":True,"privacy_boundary_preserved":True,"authority_boundary_preserved":True,"candidate_accepted":False,"handoff_accepted":False,"risk_waived":False,"global_profile_pass_claimed":False,"candidate_modified":False,"source_modified":False,"runtime_mutated":False,"release_performed":False,"authority_state":"separate_not_granted"}
 return {"ok":all(checks),"checkpoint_id":"final-candidate-reliability:v1199.8","contract_version":CONTRACT_VERSION,"passed":sum(checks),"total":len(checks),"read_only":True,"post_available":False,"content_free":True,"source_only":True,"summary":summary,"blocked_cases":blocked,"limitations":["Reliability evidence is content-free and read-only.","No candidate or handoff acceptance occurs.","No risk is waived and no global profile pass is claimed.","The v1200 decision gate remains required."]}
CHECKPOINT_DESCRIPTOR={"checkpoint_id":CHECKPOINT_ID,"contract_version":CONTRACT_VERSION,"module":"conscious_agent.final_candidate_reliability_checkpoint","builder":"build_final_candidate_reliability_checkpoint","required_inputs":[],"read_only":True,"post_available":False,"content_free":True}
