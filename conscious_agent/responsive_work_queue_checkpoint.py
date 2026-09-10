from __future__ import annotations
"""Read-only v1191.2 Responsiveness and Background-Work Foundations checkpoint."""
import hashlib, json, os
from pathlib import Path
from typing import Any
from package_integrity import package_privacy_summary_for_root
from checkpoint_registry import inspect_checkpoint_registry
from responsive_work_queue import create_work_item, validate_work_queue, public_queue_summary
CONTRACT_VERSION="v1191.2"
_CHECKPOINT_ID="responsive-work-queue:v1191.2"
_LIMITATIONS=("Queue evidence is caller-supplied and content-free.","No queued work is executed, paused, cancelled, resumed, superseded, or completed.","No thread, process, provider, model, shell command, arbitrary tool, source, runtime, approval, or authority mutation occurs.","Operator queue review and cancellation are deferred to v1191.3-v1191.5.","Desktop Codex and native-provider review remain deferred until v1200.")
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _tree(root:Path):
 h=hashlib.sha256();n=0
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
  for f in sorted(files):
   x=Path(base)/f
   if x.suffix.lower() in {'.pyc','.pyo'}:continue
   try:b=x.read_bytes();rel=x.relative_to(root).as_posix()
   except OSError:continue
   n+=1;h.update(rel.encode());h.update(b'\0');h.update(hashlib.sha256(b).digest())
 return h.hexdigest(),n
def _rows(snap,ctx):
 specs=[('work-foreground-0001','conversation','conversation_runtime','operator_response','foreground_interaction',9,30),('work-cognition-0002','cognition','cognition_runtime','bounded_reflection','background_cognition',6,5000),('work-campaign-0003','campaign','campaign_supervisor','campaign_review','background_campaign_review',5,10000),('work-maintenance-0004','reasoning','maintenance_supervisor','deferred_integrity_review','deferred_maintenance',1,60000)]
 out=[];prev=''
 for i,(wid,dom,own,purpose,cls,priority,latency) in enumerate(specs):
  row=create_work_item(work_id=wid,unified_snapshot_digest=snap,domain=dom,owner=own,context_digest=ctx,artifact_digest=_h(wid+':artifact'),receipt_digest=_h(wid+':receipt'),purpose_code=purpose,work_class=cls,queue_position=i,priority=priority,creation_sequence=i,latency_budget_ms=latency,has_deadline=(i==0),deadline_sequence=(1 if i==0 else 0),lifecycle_state=('queued_not_running' if i==0 else 'review_required'),queue_eligible=True,operator_approved=(i==0),previous_work_digest=prev)
  out.append(row);prev=row['work_digest']
 return out
def build_responsive_work_queue_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda x:checks.append(bool(x));snap=_h('v1190.9:unified-snapshot');ctx=_h('v1191.2:context');rows=_rows(snap,ctx)
 good=validate_work_queue(queue_id='responsive-work-queue-0001',unified_snapshot_digest=snap,context_digest=ctx,items=rows)
 for v in (good.get('status')=='ready_for_review',good.get('item_count')==4,good.get('foreground_unblocked') is True,good.get('deterministic_order') is True,set(good.get('work_classes',[]))=={'foreground_interaction','background_cognition','background_campaign_review','deferred_maintenance'}):req(v)
 summary=public_queue_summary(good);req(summary.get('content_free') is True);req(summary.get('execution_invoked') is False);req(summary.get('authority_granted') is False)
 blocked={}
 def case(name,mut):
  x=[dict(r) for r in rows];mut(x);blocked[name]=validate_work_queue(queue_id='responsive-work-queue-'+name,unified_snapshot_digest=snap,context_digest=ctx,items=x)
 def resign(r):
  r.pop('work_digest',None);r['work_digest']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
 case('duplicate-id',lambda x:(x.__setitem__(1,{**x[1],'work_id':x[0]['work_id']}),resign(x[1])))
 case('duplicate-position',lambda x:(x.__setitem__(1,{**x[1],'queue_position':0}),resign(x[1])))
 case('stale-snapshot',lambda x:(x.__setitem__(1,{**x[1],'unified_snapshot_digest':_h('stale')}),resign(x[1])))
 case('bad-priority',lambda x:(x.__setitem__(1,{**x[1],'priority':99}),resign(x[1])))
 case('hidden-execution',lambda x:(x.__setitem__(1,{**x[1],'execution_invoked':True}),resign(x[1])))
 case('automatic-continuation',lambda x:(x.__setitem__(1,{**x[1],'automatic_continuation':True}),resign(x[1])))
 case('private-field',lambda x:(x.__setitem__(1,{**x[1],'message_text':'secret'}),resign(x[1])))
 case('bad-owner',lambda x:(x.__setitem__(1,{**x[1],'owner':'autonomous_agent'}),resign(x[1])))
 for r in blocked.values():req(r.get('status')=='blocked');req(r.get('error_count',0)>0);req(r.get('execution_invoked') is False);req(r.get('authority_granted') is False)
 registry=inspect_checkpoint_registry(source_root=source);req(any(x.get('checkpoint_id')=='responsive-work-queue-checkpoint' for x in registry.get('checkpoints',[])))
 privacy=package_privacy_summary_for_root(source);req(privacy.get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 return {"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":_CHECKPOINT_ID,"read_only":True,"post_available":False,"content_free":True,"summary":summary,"blocked_cases":{k:v.get('errors',[]) for k,v in blocked.items()},"limitations":list(_LIMITATIONS),"source_unchanged":before==after,"source_file_count":count,"provider_contacted":False,"model_contacted":False,"thread_started":False,"process_started":False,"execution_invoked":False,"cancellation_invoked":False,"approval_consumed":False,"authority_granted":False}
