from __future__ import annotations
"""Read-only v1191.5 operator queue review and accountable presentation checkpoint."""
import hashlib,os
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from responsive_work_queue_review import create_queue_action_request, create_queue_action_review, review_queue_action, public_queue_action_summary
CONTRACT_VERSION="v1191.5";_CHECKPOINT_ID="responsive-work-queue-review:v1191.5"
_LIMITATIONS=("All transitions are content-free evidence only.","No real work is executed, paused, cancelled, superseded, or completed.","No approval is created or consumed and no cancellation or execution authority is granted.","Interruption, restart, stale-work, outage, starvation, fairness, and latency hardening remain for v1191.6-v1191.8.","Desktop Codex and native-provider review remain deferred until v1200.")
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
def build_responsive_work_queue_review_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];reqq=lambda x:checks.append(bool(x));snap=_h('v1190.9:snapshot');ctx=_h('v1191.5:context');work=_h('v1191.5:work')
 cases=[('queue','review_required','operator_review'),('pause','queued_not_running','operator_pause'),('cancel','paused','operator_cancellation'),('supersede','queued_not_running','operator_supersession'),('complete','running_evidence_only','operator_completion'),('present_result','completed','operator_presentation')]
 approved={}
 for i,(action,state,reason) in enumerate(cases):
  request=create_queue_action_request(request_id=f'queue-action-{action}-1191',queue_id='responsive-work-queue-0001',work_id='work-item-1191-0001',work_digest=work,unified_snapshot_digest=snap,context_digest=ctx,current_lifecycle_state=state,action=action,target_work_digest=(_h('replacement') if action=='supersede' else ''),result_receipt_digest=(_h('result') if action in {'complete','present_result'} else ''),operator_visible_reason_code=reason)
  review=create_queue_action_review(request_digest=request['request_digest'],decision='approve',review_id=f'queue-review-{action}-1191',operator_review_digest=_h('review:'+action))
  result=review_queue_action(request=request,review=review,current_snapshot_digest=snap,current_context_digest=ctx,current_work_digest=work);approved[action]=result
  reqq(result.get('status')=='transition_ready');reqq(result.get('transition_recorded') is True);reqq(result.get('execution_invoked') is False);reqq(result.get('authority_granted') is False)
 reqq(approved['cancel'].get('presented_lifecycle_state')=='cancelled');reqq(approved['pause'].get('presented_lifecycle_state')=='paused');reqq(approved['supersede'].get('presented_lifecycle_state')=='superseded');reqq(approved['complete'].get('presented_lifecycle_state')=='completed');reqq(approved['present_result'].get('result_presented') is True)
 base=create_queue_action_request(request_id='queue-action-review-1191',queue_id='responsive-work-queue-0001',work_id='work-item-1191-0001',work_digest=work,unified_snapshot_digest=snap,context_digest=ctx,current_lifecycle_state='review_required',action='queue')
 outcomes={}
 for decision in ('reject','defer'):
  rv=create_queue_action_review(request_digest=base['request_digest'],decision=decision,review_id='queue-review-'+decision+'-1191',operator_review_digest=_h(decision));outcomes[decision]=review_queue_action(request=base,review=rv,current_snapshot_digest=snap,current_context_digest=ctx,current_work_digest=work);reqq(outcomes[decision].get('transition_recorded') is False)
 blocked={}
 def run(name,rq,rv=None,**current):
  if rv is None:rv=create_queue_action_review(request_digest=rq['request_digest'],decision='approve',review_id='queue-review-'+name+'-1191',operator_review_digest=_h(name))
  blocked[name]=review_queue_action(request=rq,review=rv,current_snapshot_digest=current.get('snap',snap),current_context_digest=current.get('ctx',ctx),current_work_digest=current.get('work',work))
 stale=dict(base);run('stale-snapshot',stale,snap=_h('stale'))
 run('stale-context',base,ctx=_h('stale'))
 run('stale-work',base,work=_h('stale'))
 bad=dict(base);bad['action']='execute';run('unsupported-action',bad)
 bad2=dict(base);bad2['execution_requested']=True;run('hidden-execution',bad2)
 bad3=dict(base);bad3['message_text']='private';run('private-field',bad3)
 bad4=dict(base);bad4['current_lifecycle_state']='completed';run('bad-transition',bad4)
 bad5=dict(base);bad5['request_digest']='0'*64;run('tamper',bad5)
 for x in blocked.values():reqq(x.get('status')=='blocked');reqq(x.get('transition_recorded') is False);reqq(x.get('execution_invoked') is False);reqq(x.get('authority_granted') is False)
 summary=public_queue_action_summary(approved['cancel']);reqq(summary.get('content_free') is True);reqq(summary.get('authority_granted') is False)
 registry=inspect_checkpoint_registry(source_root=source);reqq(any(x.get('checkpoint_id')=='responsive-work-queue-review-checkpoint' for x in registry.get('checkpoints',[])))
 privacy=package_privacy_summary_for_root(source);reqq(privacy.get('ok') is True)
 after,after_count=_tree(source);reqq(before==after);reqq(count==after_count)
 return {"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":_CHECKPOINT_ID,"read_only":True,"post_available":False,"content_free":True,"summary":{"approved_action_count":len(approved),"rejected_action_count":1,"deferred_action_count":1,"blocked_case_count":len(blocked),"actions":sorted(approved),"cancel_presented_state":approved['cancel'].get('presented_lifecycle_state'),"result_presented":approved['present_result'].get('result_presented')},"blocked_cases":{k:v.get('errors',[]) for k,v in blocked.items()},"limitations":list(_LIMITATIONS),"source_unchanged":before==after,"source_file_count":count,"provider_contacted":False,"model_contacted":False,"thread_started":False,"process_started":False,"execution_invoked":False,"real_work_paused":False,"real_work_cancelled":False,"approval_created":False,"approval_consumed":False,"authority_granted":False}
