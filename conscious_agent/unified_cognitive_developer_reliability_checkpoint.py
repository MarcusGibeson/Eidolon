from __future__ import annotations
"""Read-only v1194.8 Unified Experience Reliability checkpoint."""
import hashlib,os
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_cognitive_developer_coordination_checkpoint import build_unified_cognitive_developer_coordination_checkpoint
from unified_cognitive_developer_reliability import *
from unified_cognitive_developer_reliability import _d
CONTRACT_VERSION='v1194.8';_CHECKPOINT_ID='unified-cognitive-developer-reliability-checkpoint'
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
def build_unified_cognitive_developer_reliability_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda x:checks.append(bool(x));base=build_unified_cognitive_developer_coordination_checkpoint(source_root=source)
 snapshot=_h('v1194.8:snapshot');context=_h('v1194.8:context');focus=_h('v1194.8:focus');coord=dict(base['summary'])
 outcomes={};prev=''
 for i,event_class in enumerate(sorted(EVENTS)):
  e=create_reliability_event(event_id=f'event:{i}',event_class=event_class,snapshot_digest=snapshot,context_digest=context,focus_digest=focus,artifact_digest=_h('artifact'+str(i)),receipt_digest=_h('receipt'+str(i)),latency_budget_ms=250,observed_latency_ms=25,sequence=i,previous_event_digest=prev);prev=e['event_digest'];outcomes[event_class]=assess_unified_reliability(coordination=coord,event=e,current_snapshot_digest=snapshot,current_context_digest=context,current_focus_digest=focus)
 for r in outcomes.values():
  req(r['status']=='reliability_ready')
  for k,v in (('content_free',True),('foreground_path_available',True),('original_evidence_preserved',True),('inherited_debt_visible',True),('recovery_executed',False),('execution_invoked',False),('runtime_mutated',False),('provider_contacted',False),('model_contacted',False),('thread_started',False),('process_started',False),('approval_consumed',False),('authority_granted',False)):req(r.get(k)==v)
 blocked={}
 def make():return create_reliability_event(event_id='blocked',event_class='restart',snapshot_digest=snapshot,context_digest=context,focus_digest=focus,artifact_digest=_h('artifact'),receipt_digest=_h('receipt'),latency_budget_ms=250,observed_latency_ms=25,sequence=0)
 def resign(e):e.pop('event_digest',None);e['event_digest']=_d(e)
 def case(name,mut,coord_mut=None):
  e=make();c=dict(coord);mut(e);resign(e)
  if coord_mut:coord_mut(c)
  blocked[name]=assess_unified_reliability(coordination=c,event=e,current_snapshot_digest=snapshot,current_context_digest=context,current_focus_digest=focus)
 case('stale-snapshot',lambda e:e.__setitem__('snapshot_digest',_h('stale')))
 case('stale-context',lambda e:e.__setitem__('context_digest',_h('stale')))
 case('stale-focus',lambda e:e.__setitem__('focus_digest',_h('stale')))
 case('private-field',lambda e:e.__setitem__('prompt','secret'))
 case('hidden-recovery',lambda e:e.__setitem__('recovery_executed',True))
 case('automatic-continuation',lambda e:e.__setitem__('automatic_continuation',True))
 case('provider-contact',lambda e:e.__setitem__('provider_contacted',True))
 case('authority',lambda e:e.__setitem__('authority_granted',True))
 case('latency',lambda e:e.__setitem__('observed_latency_ms',251))
 case('unsupported-event',lambda e:e.__setitem__('event_class','magic'))
 case('foreground-block',lambda e:None,lambda c:c.__setitem__('foreground_path_available',False))
 case('evidence-loss',lambda e:None,lambda c:c.__setitem__('original_evidence_preserved',False))
 case('debt-hidden',lambda e:None,lambda c:c.__setitem__('inherited_debt_visible',False))
 e=make();e['event_class']='tampered';blocked['tamper']=assess_unified_reliability(coordination=coord,event=e,current_snapshot_digest=snapshot,current_context_digest=context,current_focus_digest=focus)
 for r in blocked.values():req(r['status']=='blocked');req(r['error_count']>0);req(r['execution_invoked'] is False);req(r['authority_granted'] is False)
 reg=inspect_checkpoint_registry(source_root=source);d=next((x for x in reg['checkpoints'] if x['checkpoint_id']==_CHECKPOINT_ID),None);req(d is not None);req((d or {}).get('builder')=='build_unified_cognitive_developer_reliability_checkpoint');req(not reg['duplicate_checkpoint_ids']);req(package_privacy_summary_for_root(source).get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 summary=public_reliability_summary(outcomes['restart']);summary.update({'event_class_count':len(EVENTS),'blocked_case_count':len(blocked),'domain_count':9,'global_profile_pass_claimed':False})
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':'unified-cognitive-developer-reliability:v1194.8','read_only':True,'post_available':False,'content_free':True,'summary':summary,'blocked_cases':{k:v['errors'] for k,v in blocked.items()},'limitations':['Reliability evidence only.','No automatic recovery or continuation.','No subsystem mutation or execution.','No provider/model contact or approval consumption.','v1194.9 checkpoint remains separate.'],'source_unchanged':before==after,'runtime_mutated':False,'production_source_modified':False,'approval_created':False,'approval_consumed':False,'execution_invoked':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'authority_granted':False}
