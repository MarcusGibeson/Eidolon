from __future__ import annotations
"""Read-only v1194.5 Operator Coordination and Accountable Navigation checkpoint."""
import hashlib,os
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_cognitive_developer_experience_checkpoint import build_unified_cognitive_developer_experience_checkpoint
from unified_cognitive_developer_coordination import *
CONTRACT_VERSION='v1194.5';_CHECKPOINT_ID='unified-cognitive-developer-coordination-checkpoint'
def _h(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
def _tree(root:Path):
 h=hashlib.sha256();n=0
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
  for name in sorted(files):
   p=Path(base)/name
   if p.suffix.lower() in {'.pyc','.pyo'}:continue
   b=p.read_bytes();n+=1;h.update(p.relative_to(root).as_posix().encode());h.update(hashlib.sha256(b).digest())
 return h.hexdigest(),n
def build_unified_cognitive_developer_coordination_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda x:checks.append(bool(x));base=build_unified_cognitive_developer_experience_checkpoint(source_root=source)
 snapshot=_h('v1194.5:snapshot');context=_h('v1194.5:context');view={'summary':dict(base['summary'],global_profile_pass_claimed=False)}
 def make(decision='approve',to_domain='campaign'):
  q=create_coordination_request(coordination_id='coordination:1194.5',snapshot_digest=snapshot,context_digest=context,from_domain='conversation',to_domain=to_domain,purpose_code='operator_navigation',artifact_digest=_h('artifact'),receipt_digest=_h('receipt'))
  rv=create_coordination_review(request_digest=q['request_digest'],decision=decision,review_id='review:1194.5',operator_review_digest=_h('review'))
  return q,rv
 outcomes={}
 for decision in ('approve','reject','defer'):
  q,rv=make(decision);outcomes[decision]=coordinate_operator_navigation(view=view,request=q,review=rv,current_snapshot_digest=snapshot,current_context_digest=context)
 req(outcomes['approve']['status']=='navigation_ready');req(outcomes['approve']['focus_changed'] is True);req(outcomes['reject']['status']=='navigation_rejected');req(outcomes['defer']['status']=='navigation_deferred')
 for r in outcomes.values():
  for k,v in (('content_free',True),('foreground_path_available',True),('original_evidence_preserved',True),('inherited_debt_visible',True),('subsystem_state_changed',False),('approval_consumed',False),('execution_invoked',False),('runtime_mutated',False),('provider_contacted',False),('model_contacted',False),('thread_started',False),('process_started',False),('authority_granted',False)):req(r.get(k)==v)
 blocked={}
 def case(name,mut):
  q,rv=make();vv={'summary':dict(view['summary'])};mut(q,rv,vv);blocked[name]=coordinate_operator_navigation(view=vv,request=q,review=rv,current_snapshot_digest=snapshot,current_context_digest=context)
 def resign(row,field):row.pop(field,None);row[field]=__import__('conscious_agent.unified_cognitive_developer_coordination',fromlist=['_d'])._d(row)
 case('stale-snapshot',lambda q,r,v:(q.__setitem__('snapshot_digest',_h('stale')),resign(q,'request_digest')))
 case('stale-context',lambda q,r,v:(q.__setitem__('context_digest',_h('stale')),resign(q,'request_digest')))
 case('private-field',lambda q,r,v:(q.__setitem__('prompt','secret'),resign(q,'request_digest')))
 case('hidden-execution',lambda q,r,v:(q.__setitem__('execution_requested',True),resign(q,'request_digest')))
 case('automatic-continuation',lambda q,r,v:(q.__setitem__('automatic_continuation_requested',True),resign(q,'request_digest')))
 case('authority',lambda q,r,v:(r.__setitem__('authority_granted',True),resign(r,'review_digest')))
 case('foreground-block',lambda q,r,v:v['summary'].__setitem__('foreground_path_available',False))
 case('evidence-loss',lambda q,r,v:v['summary'].__setitem__('original_evidence_preserved',False))
 case('global-pass',lambda q,r,v:v['summary'].__setitem__('global_profile_pass_claimed',True))
 case('tamper',lambda q,r,v:q.__setitem__('purpose_code','tampered'))
 for r in blocked.values():req(r['status']=='blocked');req(r['error_count']>0);req(r['execution_invoked'] is False);req(r['authority_granted'] is False)
 reg=inspect_checkpoint_registry(source_root=source);d=next((x for x in reg['checkpoints'] if x['checkpoint_id']==_CHECKPOINT_ID),None);req(d is not None);req((d or {}).get('builder')=='build_unified_cognitive_developer_coordination_checkpoint');req(not reg['duplicate_checkpoint_ids']);req(package_privacy_summary_for_root(source).get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 summary=public_coordination_summary(outcomes['approve']);summary.update({'domain_count':9,'decision_count':3,'blocked_case_count':len(blocked),'current_regressions_separate':True,'global_profile_pass_claimed':False})
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':'unified-cognitive-developer-coordination:v1194.5','read_only':True,'post_available':False,'content_free':True,'summary':summary,'blocked_cases':{k:v['errors'] for k,v in blocked.items()},'limitations':['Presentation-only coordination.','No subsystem mutation or execution.','No approval creation or consumption.','No automatic continuation or authority expansion.','Reliability hardening remains for v1194.6-v1194.8.'],'source_unchanged':before==after,'runtime_mutated':False,'production_source_modified':False,'approval_created':False,'approval_consumed':False,'execution_invoked':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'authority_granted':False}
