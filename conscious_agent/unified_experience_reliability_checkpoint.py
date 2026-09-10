from __future__ import annotations
"""Read-only v1190.8 Unified Experience Reliability and Privacy Hardening checkpoint."""
import hashlib, json, os
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_experience_navigation_checkpoint import _snapshot, _request
from unified_experience_navigation import create_navigation_review, coordinate_experience_navigation
from unified_experience_reliability import create_reliability_assessment, create_reliability_review, assess_unified_experience_reliability, reliability_public_summary
CONTRACT_VERSION="v1190.8"; _CHECKPOINT_ID="unified-experience-reliability:v1190.8"
_EXCLUDED={"data","sandbox",".git",".venv","venv","__pycache__",".pytest_cache",".mypy_cache",".ruff_cache","dist","build","reports"}
_LIMITATIONS=("Reliability observations remain caller-supplied content-free evidence.","Approved recovery remains presentation-only and is not executed.","Live subsystem refresh, queueing, cancellation, and latency hardening remain outside v1190.6-v1190.8.","No approval, action, provider, model, installation, promotion, certification, publication, release, or autonomous authority is invoked.","Desktop Codex and native-provider review remain deferred until v1200.")
def _h(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _tree_signature(root:Path)->tuple[str,int]:
 d=hashlib.sha256(); paths=[]
 for base,dirs,files in os.walk(root):
  dirs[:]=[x for x in dirs if x not in _EXCLUDED]
  paths += [Path(base)/n for n in files if Path(n).suffix.lower() not in {'.pyc','.pyo'}]
 count=0
 for path in sorted(paths):
  try:r=path.relative_to(root).as_posix(); b=path.read_bytes()
  except OSError:continue
  count+=1; d.update(r.encode()); d.update(b'\0'); d.update(hashlib.sha256(b).digest())
 return d.hexdigest(),count
def build_unified_experience_reliability_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); del runtime_root
 before,count=_tree_signature(source); checks=[]; req=lambda x:checks.append(bool(x))
 snap=_snapshot(); nav=_request(snap); navrev=create_navigation_review(navigation_digest=nav['navigation_digest'],decision='approve',review_id='reliability-nav-review',operator_review_digest=_h('nav-review'))
 trans=coordinate_experience_navigation(snapshot=snap,navigation=nav,review=navrev,current_context_digest=snap['context_digest'],current_snapshot_digest=snap['unified_experience_digest'])
 base=create_reliability_assessment(reliability_id='unified-reliability-1190-8',experience_id=snap['experience_id'],snapshot_digest=snap['unified_experience_digest'],transition_digest=trans['transition_digest'],expected_context_digest=snap['context_digest'],observed_context_digest=snap['context_digest'],expected_focus_surface_id=trans['presented_surface_id'],observed_focus_surface_id=trans['presented_surface_id'],interruption='none',privacy_finding_count=0,authority_claim_count=0)
 approved=create_reliability_review(reliability_digest=base['reliability_digest'],decision='approve',action='hold',review_id='reliability-review-approve',operator_review_digest=_h('approve'))
 good=assess_unified_experience_reliability(snapshot=snap,transition=trans,assessment=base,review=approved,current_snapshot_digest=snap['unified_experience_digest'],current_context_digest=snap['context_digest'],current_focus_surface_id=trans['presented_surface_id'])
 for k,v in [('status','reliability_ready'),('snapshot_current',True),('context_current',True),('focus_current',True),('privacy_clear',True),('authority_clear',True),('recovery_executed',False),('authority_granted',False)]:req(good.get(k)==v)
 pub=reliability_public_summary(good); req(pub.get('content_free') is True); req(pub.get('authority_granted') is False)
 outcomes={}
 for decision in ('reject','defer'):
  rev=create_reliability_review(reliability_digest=base['reliability_digest'],decision=decision,action='hold',review_id=f'reliability-review-{decision}',operator_review_digest=_h(decision))
  outcomes[decision]=assess_unified_experience_reliability(snapshot=snap,transition=trans,assessment=base,review=rev,current_snapshot_digest=snap['unified_experience_digest'],current_context_digest=snap['context_digest'],current_focus_surface_id=trans['presented_surface_id'])
  req(outcomes[decision]['status']==f"reliability_{'rejected' if decision=='reject' else 'deferred'}")
 blocked={}
 variants={
  'stale_snapshot':{'snapshot_digest':_h('stale')},'stale_context':{'observed_context_digest':_h('stale-context'),'interruption':'stale_context'},
  'stale_focus':{'observed_focus_surface_id':'experience-surface-planning','interruption':'stale_focus'},'privacy':{'privacy_finding_count':1,'interruption':'privacy_block'},
  'authority':{'authority_claim_count':1},'unsupported_interruption':{'interruption':'meteor'},'tampered':{'experience_id':'tampered-experience'},
 }
 for name,changes in variants.items():
  row=dict(base); row.update(changes)
  if name!='tampered': row['reliability_digest']=_digest({k:v for k,v in row.items() if k!='reliability_digest'})
  rev=create_reliability_review(reliability_digest=row['reliability_digest'],decision='approve',action='refresh_snapshot',review_id=f'review-{name}',operator_review_digest=_h(name))
  blocked[name]=assess_unified_experience_reliability(snapshot=snap,transition=trans,assessment=row,review=rev,current_snapshot_digest=snap['unified_experience_digest'],current_context_digest=snap['context_digest'],current_focus_surface_id=trans['presented_surface_id'])
  req(blocked[name]['status']=='blocked'); req(blocked[name]['error_count']>0); req(blocked[name]['authority_granted'] is False); req(blocked[name]['recovery_executed'] is False)
 registry=inspect_checkpoint_registry(source_root=source); desc=next((x for x in registry['checkpoints'] if x['checkpoint_id']=='unified-experience-reliability-checkpoint'),None)
 req(desc is not None); req((desc or {}).get('contract_version')==CONTRACT_VERSION); req(not registry['duplicate_checkpoint_ids']); req(not registry['duplicate_builder_targets'])
 privacy=package_privacy_summary_for_root(source); req(privacy.get('forbidden_entry_count',0)==0); req(privacy.get('private_content_finding_count',0)==0)
 after,after_count=_tree_signature(source); req(before==after); req(count==after_count)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':_CHECKPOINT_ID,'read_only':True,'post_available':False,'content_free':True,'source_modified':False,'runtime_mutated':False,'production_source_modified':False,'sandbox_modified':False,'provider_contacted':False,'model_contacted':False,'automatic_continuation':False,'approval_created':False,'approval_consumed':False,'execution_invoked':False,'recovery_executed':False,'authority_granted':False,'authority_preserved':True,'desktop_verification_deferred_until_v1200':True,'source_signature_before':before,'source_signature_after':after,'source_file_count':count,'summary':{'approved_reliability_count':1,'rejected_reliability_count':1,'deferred_reliability_count':1,'blocked_boundary_case_count':len(blocked),'interruption':'none','presented_domain':trans.get('presented_domain','')},'limitations':list(_LIMITATIONS),'structural_digest':_digest({'good':good['reliability_result_digest'],'blocked':{k:v['reliability_result_digest'] for k,v in sorted(blocked.items())}})}
