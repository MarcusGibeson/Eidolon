from __future__ import annotations
import hashlib, os
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from soak_reliability_adversarial import EVENTS, create_soak_reliability_event, assess_soak_reliability, public_soak_reliability_summary
CONTRACT_VERSION='v1195.8'
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _tree(root:Path):
 d=hashlib.sha256();n=0
 for base,dirs,files in os.walk(root):
  dirs[:]=sorted(x for x in dirs if x not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'})
  for name in sorted(files):
   p=Path(base)/name
   if p.suffix.lower() in {'.pyc','.pyo'}:continue
   n+=1;d.update(p.relative_to(root).as_posix().encode());d.update(hashlib.sha256(p.read_bytes()).digest())
 return d.hexdigest(),n
def build_soak_reliability_adversarial_checkpoint(*,source_root=None,runtime_root=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();before,count=_tree(root);checks=[]
 req=lambda x:checks.append(bool(x));snap=_h('1195.8:snapshot');ctx=_h('1195.8:context')
 soak={'soak_digest':_h('soak'),'plan_digest':_h('plan'),'terminal_interval_digest':_h('terminal'),'foreground_path_available':True,'original_evidence_preserved':True}
 progression={'execution_invoked':False,'authority_granted':False}
 vals={'restart_storm':dict(restart_count=5),'resource_exhaustion':dict(resource_percent=95),'latency_degradation':dict(observed_latency_ms=900,latency_budget_ms=1000),'provider_outage':{},'queue_starvation':dict(starvation_cycles=8),'cancellation_race':dict(cancellation_observations=4),'privacy_attack':{},'long_duration_drift':dict(drift_score=25)}
 rows=[];prev=None
 for i,event_class in enumerate(sorted(EVENTS)):
  e=create_soak_reliability_event(event_id=f'event:{i}',event_class=event_class,soak_digest=soak['soak_digest'],plan_digest=soak['plan_digest'],terminal_interval_digest=soak['terminal_interval_digest'],snapshot_digest=snap,context_digest=ctx,artifact_digest=_h(f'a{i}'),receipt_digest=_h(f'r{i}'),sequence=i,previous_event_digest=prev['reliability_digest'] if prev else '',**vals[event_class])
  r=assess_soak_reliability(soak_summary=soak,progression_summary=progression,event=e,current_snapshot_digest=snap,current_context_digest=ctx,previous_event=prev);rows.append(r);prev=r
  for x in (r['status']=='reliability_ready',r['event_class']==event_class,r['exact_lineage_verified'],r['foreground_path_available'],r['original_evidence_preserved'],r['recovery_review_required'],not r['automatic_recovery'],not r['automatic_retry'],not r['cancellation_executed'],not r['execution_invoked'],not r['runtime_mutated'],not r['authority_granted']):req(x)
 # adversarial cases
 def blocked(name,mut):
  e=create_soak_reliability_event(event_id=name,event_class='provider_outage',soak_digest=soak['soak_digest'],plan_digest=soak['plan_digest'],terminal_interval_digest=soak['terminal_interval_digest'],snapshot_digest=snap,context_digest=ctx,artifact_digest=_h(name+'a'),receipt_digest=_h(name+'r'),sequence=0);mut(e);r=assess_soak_reliability(soak_summary=soak,progression_summary=progression,event=e,current_snapshot_digest=snap,current_context_digest=ctx);req(r['status']=='blocked');req(r['error_count']>0);return r
 cases={
 'tamper':lambda e:e.__setitem__('event_class','execute'),
 'private':lambda e:e.__setitem__('prompt','secret'),
 'stale_snapshot':lambda e:e.__setitem__('snapshot_digest',_h('stale')),
 'stale_context':lambda e:e.__setitem__('context_digest',_h('stale')),
 'stale_soak':lambda e:e.__setitem__('soak_digest',_h('stale')),
 'stale_plan':lambda e:e.__setitem__('plan_digest',_h('stale')),
 'stale_terminal':lambda e:e.__setitem__('terminal_interval_digest',_h('stale')),
 'automatic_recovery':lambda e:e.__setitem__('automatic_recovery',True),
 'automatic_retry':lambda e:e.__setitem__('automatic_retry',True),
 'cancel_execution':lambda e:e.__setitem__('cancellation_executed',True),
 'provider_contact':lambda e:e.__setitem__('provider_contacted',True),
 'runtime_mutation':lambda e:e.__setitem__('runtime_mutated',True),
 'authority':lambda e:e.__setitem__('authority_granted',True),
 'bad_digest':lambda e:e.__setitem__('artifact_digest','bad'),
 'bad_sequence':lambda e:e.__setitem__('sequence',-1),
 'latency':lambda e:(e.__setitem__('observed_latency_ms',2000),e.__setitem__('latency_budget_ms',1000)),
 }
 blocked_rows={k:blocked(k,v) for k,v in cases.items()}
 privacy=package_privacy_summary_for_root(root);registry=inspect_checkpoint_registry(source_root=root);after,after_count=_tree(root)
 for x in (before==after,count==after_count,privacy.get('source_only') is True,privacy.get('forbidden_entry_count',0)==0,registry.get('content_free') is True):req(x)
 summary={'contract_version':CONTRACT_VERSION,'event_class_count':len(EVENTS),'ready_count':len(rows),'blocked_count':len(blocked_rows),'content_free':True,'foreground_path_available':True,'original_evidence_preserved':True,'recovery_review_required':True,'automatic_recovery':False,'automatic_retry':False,'cancellation_executed':False,'execution_invoked':False,'runtime_mutated':False,'authority_granted':False}
 return {'ok':all(checks),'checkpoint_id':'soak-reliability-adversarial:v1195.8','contract_version':CONTRACT_VERSION,'passed':sum(checks),'total':len(checks),'summary':summary,'samples':[public_soak_reliability_summary(x) for x in rows],'blocked_cases':{k:public_soak_reliability_summary(v) for k,v in blocked_rows.items()},'limitations':['Evidence-only; no actual waiting, recovery, retry, cancellation, provider contact, execution, or mutation.','v1195.9 checkpoint remains next.']}
CHECKPOINT_DESCRIPTOR={'checkpoint_id':'soak-reliability-adversarial:v1195.8','module':'conscious_agent.soak_reliability_adversarial_checkpoint','builder':'build_soak_reliability_adversarial_checkpoint','contract_version':CONTRACT_VERSION,'required_inputs':[],'read_only':True,'content_free':True}
