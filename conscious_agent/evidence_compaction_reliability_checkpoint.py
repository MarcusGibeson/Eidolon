from __future__ import annotations
"""Read-only v1192.8 evidence compaction reliability checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from evidence_compaction_reliability import create_reliability_record, assess_compaction_reliability, public_reliability_summary
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
CONTRACT_VERSION='v1192.8'; _CHECKPOINT_ID='evidence-compaction-reliability:v1192.8'
def _h(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
def _tree(root:Path):
 h=hashlib.sha256();c=0
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
  for n in sorted(files):
   p=Path(base)/n
   if p.suffix.lower() in {'.pyc','.pyo'}:continue
   try:b=p.read_bytes();r=p.relative_to(root).as_posix()
   except OSError:continue
   c+=1;h.update(r.encode());h.update(b'\0');h.update(hashlib.sha256(b).digest())
 return h.hexdigest(),c
def build_evidence_compaction_reliability_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda x:checks.append(bool(x)); comp=_h('comp');term=_h('term');snap=_h('snap');ctx=_h('ctx');rows=[];prev=''
 for i,(event,action) in enumerate((('interruption','preserve'),('restart','review_required'),('outage','defer'))):
  row=create_reliability_record(record_id=f'reliability-record-{i}',event_type=event,action=action,compaction_digest=comp,terminal_evidence_digest=term,snapshot_digest=snap,context_digest=ctx,review_digest=_h(f'review-{i}'),sequence=i,previous_record_digest=prev);rows.append(row);prev=row['record_digest']
 good=assess_compaction_reliability(records=rows,current_compaction_digest=comp,current_terminal_evidence_digest=term,current_snapshot_digest=snap,current_context_digest=ctx);req(good['ok']);req(good['automatic_recovery'] is False);req(good['authority_granted'] is False)
 blocked={}
 def run(name,records=rows,**cur):blocked[name]=assess_compaction_reliability(records=records,current_compaction_digest=cur.get('comp',comp),current_terminal_evidence_digest=cur.get('term',term),current_snapshot_digest=cur.get('snap',snap),current_context_digest=cur.get('ctx',ctx))
 run('stale-compaction',comp=_h('x'));run('stale-terminal',term=_h('x'));run('stale-snapshot',snap=_h('x'));run('stale-context',ctx=_h('x'))
 bad=[dict(x) for x in rows];bad[1]['record_digest']='0'*64;run('tamper',bad)
 bad=[dict(x) for x in rows];bad[1]['prompt']='private';run('private',bad)
 bad=[dict(x) for x in rows];bad[1]['review_digest']=bad[0]['review_digest'];bad[1].pop('record_digest');from evidence_compaction_reliability import _digest;bad[1]['record_digest']=_digest(bad[1]);run('replay',bad)
 for x in blocked.values():req(x['status']=='blocked');req(x['execution_invoked'] is False);req(x['authority_granted'] is False)
 req(public_reliability_summary(good)['content_free'] is True)
 reg=inspect_checkpoint_registry(source_root=source);req(any(r.get('checkpoint_id')=='evidence-compaction-reliability-checkpoint' for r in reg.get('checkpoints',[])))
 req(package_privacy_summary_for_root(source).get('ok') is True);after,after_count=_tree(source);req(before==after);req(count==after_count)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':_CHECKPOINT_ID,'read_only':True,'post_available':False,'content_free':True,'summary':public_reliability_summary(good),'blocked_cases':{k:v['errors'] for k,v in blocked.items()},'source_unchanged':before==after,'source_file_count':count,'replacement_performed':False,'deletion_performed':False,'execution_invoked':False,'approval_created':False,'approval_consumed':False,'authority_granted':False}
