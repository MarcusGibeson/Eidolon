from __future__ import annotations
"""Read-only v1191.8 responsiveness and background-work reliability checkpoint."""
import hashlib,os
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from responsive_work_queue_reliability import create_reliability_observation, review_reliability_observation, public_reliability_summary
CONTRACT_VERSION='v1191.8';_CHECKPOINT_ID='responsive-work-queue-reliability:v1191.8'
_LIMITATIONS=('Evidence only; no work is executed, retried, paused, or cancelled.','No provider or model is contacted.','No restart recovery mutates runtime state.','v1191.9 checkpoint remains next.','Desktop Codex and native-provider review remain deferred until v1200.')
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _tree(root:Path):
 h=hashlib.sha256();n=0
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
  for f in sorted(files):
   p=Path(base)/f
   if p.suffix.lower() in {'.pyc','.pyo'}:continue
   try:b=p.read_bytes();rel=p.relative_to(root).as_posix()
   except OSError:continue
   n+=1;h.update(rel.encode());h.update(b'\0');h.update(hashlib.sha256(b).digest())
 return h.hexdigest(),n
def build_responsive_work_queue_reliability_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda x:checks.append(bool(x));snap=_h('v1190.9:snapshot');ctx=_h('v1191.8:context');queue=_h('v1191.8:queue')
 results={}
 for i,event in enumerate(sorted({'interruption','restart','stale_work','provider_outage','starvation','fairness','privacy','latency'})):
  o=create_reliability_observation(observation_id=f'reliability-{event}-1191',queue_digest=queue,unified_snapshot_digest=snap,context_digest=ctx,event_class=event,foreground_sequence=0,background_sequences=[1,2,3],latency_budget_ms=250,observed_foreground_latency_ms=25,interruption_code='bounded' if event=='interruption' else 'none',provider_available=event!='provider_outage',restart_generation=1 if event=='restart' else 0)
  r=review_reliability_observation(observation=o,current_snapshot_digest=snap,current_context_digest=ctx,current_queue_digest=queue);results[event]=r
  req(r.get('status')=='reliability_evidence_ready');req(r.get('foreground_first') is True);req(r.get('foreground_latency_within_budget') is True);req(r.get('execution_invoked') is False);req(r.get('authority_granted') is False)
 blocked={}
 base=create_reliability_observation(observation_id='reliability-base-1191',queue_digest=queue,unified_snapshot_digest=snap,context_digest=ctx,event_class='latency',foreground_sequence=0,background_sequences=[1],latency_budget_ms=100,observed_foreground_latency_ms=10)
 def run(name,row,**cur):blocked[name]=review_reliability_observation(observation=row,current_snapshot_digest=cur.get('snap',snap),current_context_digest=cur.get('ctx',ctx),current_queue_digest=cur.get('queue',queue))
 run('stale-snapshot',base,snap=_h('stale'));run('stale-context',base,ctx=_h('stale'));run('stale-queue',base,queue=_h('stale'))
 x=dict(base);x['event_class']='execute';run('unsupported-event',x)
 x=dict(base);x['execution_requested']=True;run('hidden-execution',x)
 x=dict(base);x['message_text']='private';run('private-field',x)
 x=dict(base);x['latency_budget_ms']=0;run('bad-budget',x)
 x=dict(base);x['background_sequences']=[1,1];run('duplicate-order',x)
 x=dict(base);x['observation_digest']='0'*64;run('tamper',x)
 for r in blocked.values():req(r.get('status')=='blocked');req(r.get('execution_invoked') is False);req(r.get('authority_granted') is False)
 summary=public_reliability_summary(results['latency']);req(summary.get('content_free') is True);req(summary.get('authority_granted') is False)
 reg=inspect_checkpoint_registry(source_root=source);req(any(x.get('checkpoint_id')=='responsive-work-queue-reliability-checkpoint' for x in reg.get('checkpoints',[])))
 privacy=package_privacy_summary_for_root(source);req(privacy.get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':_CHECKPOINT_ID,'read_only':True,'post_available':False,'content_free':True,'summary':{'event_count':len(results),'blocked_case_count':len(blocked),'foreground_first_count':sum(bool(x.get('foreground_first')) for x in results.values()),'latency_within_budget_count':sum(bool(x.get('foreground_latency_within_budget')) for x in results.values()),'restart_reconciled':results['restart'].get('restart_reconciled'),'provider_outage_deferred':results['provider_outage'].get('provider_outage_deferred')},'blocked_cases':{k:v.get('errors',[]) for k,v in blocked.items()},'limitations':list(_LIMITATIONS),'source_unchanged':before==after,'source_file_count':count,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'execution_invoked':False,'real_work_cancelled':False,'automatic_retry':False,'automatic_continuation':False,'authority_granted':False}
