from __future__ import annotations
"""Read-only v1194.2 Unified Cognitive and Developer Experience Foundations checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_cognitive_developer_experience import DOMAINS, build_unified_view, create_experience_record, public_unified_summary
CONTRACT_VERSION="v1194.2"
_CHECKPOINT_ID="unified-cognitive-developer-experience-checkpoint"
_LIMITATIONS=("All subsystem observations are caller-supplied content-free evidence.","No live private subsystem state is fetched.","No queue item, approval, action, campaign, compaction, or verifier is executed or mutated.","Operator navigation and reliability hardening are deferred to v1194.3-v1194.8.","Desktop Codex and native-provider review remain scheduled for v1200.")
def _h(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
def _tree(root:Path):
 h=hashlib.sha256();n=0
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
  for name in sorted(files):
   p=Path(base)/name
   if p.suffix.lower() in {'.pyc','.pyo'}:continue
   try:b=p.read_bytes();rel=p.relative_to(root).as_posix()
   except OSError:continue
   n+=1;h.update(rel.encode());h.update(b'\0');h.update(hashlib.sha256(b).digest())
 return h.hexdigest(),n
def _records(snapshot:str,context:str):
 rows=[];previous=''
 for i,domain in enumerate(DOMAINS):
  row=create_experience_record(domain=domain,sequence=i,previous_record_digest=previous,snapshot_digest=snapshot,context_digest=context,artifact_digest=_h(domain+':artifact'),receipt_digest=_h(domain+':receipt'),purpose_code='operator_unified_view',background_status='queued_not_running' if domain in {'cognition','campaign','learning'} else 'none')
  rows.append(row);previous=row['record_digest']
 return rows
def build_unified_cognitive_developer_experience_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda x:checks.append(bool(x));snapshot=_h('v1194.2:snapshot');context=_h('v1194.2:context');rows=_records(snapshot,context)
 queue={"content_free":True,"foreground_path_available":True,"queued_item_count":3,"execution_invoked":False}
 compaction={"content_free":True,"record_count":9,"exact_expansion_verified":True,"original_evidence_preserved":True}
 verification={"content_free":True,"current_regressions_separate":True,"inherited_debt_visible":True,"global_profile_pass_claimed":False}
 report=build_unified_view(rows,current_snapshot_digest=snapshot,current_context_digest=context,queue_summary=queue,compaction_summary=compaction,verification_summary=verification);summary=public_unified_summary(report)
 for value in (report['status']=='ready_for_operator_view',report['errors']==[],summary['domain_count']==9,summary['foreground_path_available'] is True,summary['background_work_separate'] is True,summary['exact_expansion_verified'] is True,summary['original_evidence_preserved'] is True,summary['current_regressions_separate'] is True,summary['inherited_debt_visible'] is True,summary['approval_separate'] is True,summary['execution_invoked'] is False,summary['authority_granted'] is False):req(value)
 blocked={}
 def case(name,mut):
  altered=[dict(x) for x in rows];q=dict(queue);c=dict(compaction);v=dict(verification);mut(altered,q,c,v);blocked[name]=build_unified_view(altered,current_snapshot_digest=snapshot,current_context_digest=context,queue_summary=q,compaction_summary=c,verification_summary=v)
 def resign(r):r.pop('record_digest',None);from unified_cognitive_developer_experience import _digest;r['record_digest']=_digest(r)
 case('stale-snapshot',lambda r,q,c,v:(r[0].__setitem__('snapshot_digest',_h('stale')),resign(r[0])))
 case('private-field',lambda r,q,c,v:(r[1].__setitem__('prompt','secret'),resign(r[1])))
 case('hidden-execution',lambda r,q,c,v:(r[2].__setitem__('execution_state','executed'),resign(r[2])))
 case('authority',lambda r,q,c,v:(r[3].__setitem__('authority_state','granted'),resign(r[3])))
 case('foreground-block',lambda r,q,c,v:q.__setitem__('foreground_path_available',False))
 case('evidence-loss',lambda r,q,c,v:c.__setitem__('original_evidence_preserved',False))
 case('global-pass',lambda r,q,c,v:v.__setitem__('global_profile_pass_claimed',True))
 case('tamper',lambda r,q,c,v:r[4].__setitem__('purpose_code','tampered'))
 for value in blocked.values():req(value['status']=='blocked');req(value['error_count']>0);req(value['execution_invoked'] is False);req(value['authority_granted'] is False)
 registry=inspect_checkpoint_registry(source_root=source);descriptor=next((x for x in registry['checkpoints'] if x['checkpoint_id']==_CHECKPOINT_ID),None);req(descriptor is not None);req((descriptor or {}).get('builder')=='build_unified_cognitive_developer_experience_checkpoint');req(not registry['duplicate_checkpoint_ids'])
 privacy=package_privacy_summary_for_root(source);req(privacy.get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 return {"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"unified-cognitive-developer-experience:v1194.2","read_only":True,"post_available":False,"content_free":True,"summary":summary,"blocked_cases":{k:v['errors'] for k,v in blocked.items()},"limitations":list(_LIMITATIONS),"source_unchanged":before==after,"runtime_mutated":False,"production_source_modified":False,"approval_created":False,"approval_consumed":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"thread_started":False,"process_started":False,"authority_granted":False}
